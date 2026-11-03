"""Select complete linked sources for a report transaction; retain the whole report."""
import copy


def project(payload, context, before):
    import draft_context
    import report_revision
    selected=set();known={g['group_id'] for g in before['report_fragments']}
    rows=[{**r,'text':context.get('report_text','')[slice(*r['text_span'])] if 'text_span' in r else r.get('text','')}
          for r in context.get('all_target_inventory',[])]
    contexts=report_revision.group_contexts(before,rows)
    target_context={r['id']:r['context_id'] for r in rows}
    affected_targets=set();affected_finals=set()
    def scan(v):
        if isinstance(v,list):
            for item in v:scan(item)
        elif isinstance(v,dict):
            for tid in v.get('task_ids',[])+([v['task_id']] if v.get('task_id') else []):
                if tid.startswith('language:') and tid.split(':',1)[1] in known:selected.add(tid.split(':',1)[1])
                if tid.startswith('target:') and tid.split(':',1)[1] in target_context:affected_targets.add(tid.split(':',1)[1])
            affected_targets.update(x for x in v.get('target_ids',[]) if x in target_context)
            affected_finals.update(x for x in v.get('source_ids',[]) if isinstance(x,str))
            selected.update(x for x in v.get('group_ids',[]) if x in known)
            for item in v.values():scan(item)
    defects=payload['actual_defect_judgments']
    for key,value in defects.items():
        if key.startswith('target:'):affected_targets.add(key.split(':',1)[1])
        if key.startswith('language:') and key.split(':',1)[1] in known:selected.add(key.split(':',1)[1])
        scan(value)
    scan(payload.get('failures',[]))
    for gid,cs in contexts.items():
        if cs & {target_context[t] for t in affected_targets if t in target_context}:selected.add(gid)
    for g in before['report_fragments']:
        if set(g['verified_ids'])&affected_finals:selected.add(g['group_id'])
    if not selected:return payload,{'mode':'full','reason':'Defects lack explicit group/target binding'}
    assigned={x for g in before['report_fragments'] if g['group_id'] in selected for x in g['verified_ids']+g.get('candidate_ids',[])}
    view,receipt=draft_context.project({'draft_context_v1':1,'verified_review':payload['verified_review'],
        'draft_partition':{'assigned_ids':sorted(assigned)},
        'writing_evidence_linked_sources_not_target_facts':payload['writing_evidence']})
    if receipt['mode']!='linked_complete_sources':return payload,receipt
    active=assigned|set(receipt['dependency_ids'])
    selected|={g['group_id'] for g in before['report_fragments'] if set(g['verified_ids']+g.get('candidate_ids',[]))&active}
    # Explicit shared quotations and declared group dependencies remain in scope.
    while True:
        extra={other for g in before['report_fragments'] if g['group_id'] in selected
               for other in g.get('depends_on',[])+[q for r in g['delivery'].get('requirement_delivery',[]) for q in r.get('quote_group_ids',[])]}
        if extra<=selected:break
        # Further groups may need additional sources: safely retain full input rather
        # than claim a partial source selection is sufficient for them.
        return payload,{'mode':'full','reason':'Additional explicit group dependency requires full source view'}
    result=copy.deepcopy(payload)
    import writing_transfer
    # Use the same existing lossless source view as drafting: unselected ranking
    # rows and repeated raw diagnoses remain in the frozen full validation input.
    result['writing_evidence']=writing_transfer.draft_view(view['writing_evidence_linked_sources_not_target_facts'])
    # Unchanged groups supply complete prose for cross-context assessment; their
    # seven owned bookkeeping lists remain in before.json, not repeated in a repair
    # request that is prohibited from editing them. Changed groups keep every list.
    for group in result['current_draft'].get('report_fragments',[]):
        if group['group_id'] not in selected:
            group.pop('delivery',None)
            group['read_only']=True
    # Frozen source requirements are cheap and remain complete; source exemplars are
    # the expensive part. This is not evidence or requirement truncation.
    result['repair_source_scope']={'editable_group_ids':sorted(selected),'unrelated_groups_read_only':True,
        'instruction':'Whole report, final requests and frozen requirements remain visible. Only scoped groups may be rewritten; if another group needs editing, explicitly report missing dependency instead of inventing source context.'}
    return result,{**receipt,'editable_group_ids':sorted(selected),'whole_report_and_requirements_preserved':True}
