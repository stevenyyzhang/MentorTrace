"""Exact output references and conservative reuse; no inferred review decisions."""
import copy
import json
from pathlib import Path

LITERALS='''EXACT OUTPUT REFERENCES v1: For a repeated literal quote from assigned task
data, use {"$literal":[answer_slot,["field",0,"subfield"]]} instead of retyping it.
The path starts at that task's data. Source packets without slots use the assigned
task_id instead. The referenced value must be a complete string; keep a shorter
literal excerpt when that is the actual claim. References do not supply judgments,
reasons or default passes. Write each independent judgment and condition explicitly.
Do not repeat the same explanation across fields: use the existing texts/$text
mechanism only when the COMPLETE actual text is identical and appropriate.
'''

SYNTHESIS='''HIERARCHICAL GLOBAL SYNTHESIS: inspect both actual completed specialist
views and the full report for cross-view conflicts, incompatible actions, missing
interfaces and unresolved issues. Do not repeat their clause-by-clause source,
Original, language or Expression review. These remain the specialists' responsibility.
Return the ordinary named global record, with your OWN semantic_review, reason and
issues. You must explicitly adopt source_completeness and assertion_completeness
using {$view:["source","source_completeness"]} and
{$view:["facts","assertion_completeness"]}. Explicitly adopt author_clarity and
report_economy with the corresponding facts references; return top-level
evidence_records:{$view:["facts","evidence_records"]} for their observations.
These references retain the complete actual specialist records and provenance.
An unchanged subrecord can use a path, e.g. {$view:["facts",["report_economy","original_results"]]}.
If you disagree, report the exact conflict in issues; do not silently rewrite their
verdicts. A failed/missing specialist view cannot be adopted. No final pass is
inferred by code. Check historical integration only if history_binding is present.
'''

VIEW_FIELDS={'source':{'source_completeness'},'facts':{'assertion_completeness','author_clarity','report_economy','evidence_records'}}

DEPENDENCIES='''For normal_flow_v1 report repair, semantic_dependencies may include
scope_units:[{group_id,change_kind:"wording_only|substantive",changed_component_ids:[],
reviewed_peer_group_ids:[],claims_and_conditions_review,reason}]. Cover EVERY changed
group. Review all groups sharing final/candidate IDs, preserve their genuine dependency
edges, and name changed requirements separately. wording_only requires identical
owned delivery records and preserved meaning/conditions, not just a stylistic label.
If scope is uncertain omit this optimization; conservative expansion remains.
Each changed group receives local review; a fresh global check still judges interfaces.
'''

def fine_dependencies(old,new,changed,semantic):
    rows=semantic.get('scope_units',[])
    if semantic.get('status')!='complete' or not rows:return None
    if len(rows)!=len(changed) or {r.get('group_id') for r in rows}!=changed:raise ValueError('Incomplete changed-group scope')
    edits=set()
    for r in rows:
        gid=r['group_id'];a,b=old[gid],new[gid]
        if r.get('change_kind') not in {'wording_only','substantive'} or not r.get('reason') or not r.get('claims_and_conditions_review'):
            raise ValueError('Missing actual claim/condition dependency assessment')
        ids=set(a['verified_ids']+a.get('candidate_ids',[]))|set(b['verified_ids']+b.get('candidate_ids',[]))
        peers={k for k in new if k!=gid and ids & set(new[k]['verified_ids']+new[k].get('candidate_ids',[]))}
        if set(r.get('reviewed_peer_group_ids',[]))!=peers:raise ValueError('Shared-opinion peer assessment incomplete')
        before={x['component_id']:x for x in a['delivery'].get('requirement_delivery',[])}
        after={x['component_id']:x for x in b['delivery'].get('requirement_delivery',[])}
        declared=r.get('changed_component_ids')
        if not isinstance(declared,list) or len(declared)!=len(set(declared)) or not set(declared)<=set(before)|set(after):raise ValueError('Unknown/duplicate changed component')
        actual={k for k in set(before)|set(after) if before.get(k)!=after.get(k)}
        if not actual<=set(declared):raise ValueError('Changed requirement omitted from scope')
        if r['change_kind']=='wording_only' and (a['delivery']!=b['delivery'] or declared):raise ValueError('Wording-only edit changed delivery semantics')
        edits.update(declared)
    return [(a,b) for c in edits for a in new for b in new if a!=b
            and any(x['component_id']==c for x in new[a]['delivery'].get('requirement_delivery',[]))
            and any(x['component_id']==c for x in new[b]['delivery'].get('requirement_delivery',[]))]

def expand(value,tasks,context):
    if not context.get('normal_flow_v1'):return copy.deepcopy(value)
    byid={t['id']:t for t in tasks}
    texts=value.get('texts',{}) if isinstance(value,dict) else {}
    def visit(v):
        if isinstance(v,list):return [visit(x) for x in v]
        if not isinstance(v,dict):return v
        if '$text' in v:
            if set(v)!={'$text'} or not isinstance(v['$text'],str) or not isinstance(texts.get(v['$text']),str):raise ValueError('Unknown shared literal text')
            return texts[v['$text']]
        if '$literal' in v:
            if set(v)!={'$literal'}:raise ValueError('Mixed literal reference')
            ref=v['$literal']
            if not isinstance(ref,list) or len(ref)!=2 or not isinstance(ref[1],list):raise ValueError('Invalid literal reference')
            owner,path=ref
            if type(owner) is int:
                if owner<0 or owner>=len(tasks):raise ValueError('Unassigned literal slot')
                t=tasks[owner]
            else:
                if not isinstance(owner,str) or owner not in byid:raise ValueError('Unassigned literal task')
                t=byid[owner]
            result=t['data']
            for key in path:
                if isinstance(result,list) and type(key) is int and 0<=key<len(result):result=result[key]
                elif isinstance(result,dict) and isinstance(key,str) and key in result:result=result[key]
                else:raise ValueError('Unknown literal path')
            if not isinstance(result,str):raise ValueError('Literal reference must address a string, never a verdict object')
            return result
        if '$view' in v:
            if set(v)!={'$view'} or not context.get('hierarchical_global_review'):raise ValueError('Unbound specialist adoption')
            ref=v['$view']
            if not isinstance(ref,list) or len(ref)!=2 or not isinstance(ref[0],str):raise ValueError('Unsupported specialist field')
            path=ref[1] if isinstance(ref[1],list) else [ref[1]]
            if not path or not isinstance(path[0],str) or path[0] not in VIEW_FIELDS.get(ref[0],set()):raise ValueError('Unsupported specialist field')
            import mentortrace_v1 as m
            matches=[r for r in context['hierarchical_global_review']['actual_reviews'] if r['role']==ref[0]]
            if len(matches)!=1:raise ValueError('Missing/ambiguous specialist')
            r=matches[0]
            m.require(m.sha(r['path'])==r['sha256'] and m.read(r['path'])==r['actual_review'],'Specialist source changed')
            actual=r['actual_review']
            m.require(actual.get('status')=='pass' and actual.get('issues')==[],'Cannot adopt a failed specialist view')
            for key in path:
                if isinstance(actual,dict) and isinstance(key,str) and key in actual:actual=actual[key]
                elif isinstance(actual,list) and type(key) is int and 0<=key<len(actual):actual=actual[key]
                else:raise ValueError('Specialist did not supply adopted field')
            return copy.deepcopy(actual)
        return {k:visit(x) for k,x in v.items()}
    return visit(value)


def reusable_global(previous,fresh,plan,assessment):
    """Only a previously accepted report with ALL actual dependencies unchanged."""
    if not plan['previous_valid'] or previous['report_sha256']!=fresh['report_sha256']:return False
    if previous.get('sources')!=fresh.get('sources'):return False
    if any(plan.get(k) for k in ['pending_source_ids','pending_target_ids','pending_language_draft_labels']):return False
    if any(assessment.get(k) for k in ['affected_source_ids','affected_target_ids','affected_component_ids','invalid_record_task_ids']):return False
    ref=fresh.get('coverage_carryover',{})
    if not ref or not ref.get('previous_b'):return False
    import mentortrace_v1 as m
    previous_b=m.read(ref['previous_b'])
    return ref.get('rows')==previous_b.get('components') and bool(previous.get('scope_review'))


def global_response(bundle,entry,settings):
    """Rebind an actual accepted global value, retaining its original provenance."""
    import mentortrace_v1 as m,review_workflow as w,delivery_efficiency as de
    bundle=Path(bundle);ctx=m.read(bundle/'context.json');candidate=ctx.get('global_reuse_candidate')
    if not ctx.get('normal_flow_v1') or not candidate:return None
    inventory=m.read(bundle/'inventory.json')
    if any(t['kind']!='global_scope' for t in inventory):return None
    ledger=m.read(ctx['ledger_path']);checked=de.checked_carryover(ledger,ctx.get('delivery_contract'))
    if checked.get('global')!=candidate:return None
    m.require(m.sha(candidate['path'])==candidate['sha256'],'Reused global ledger changed')
    old=m.read(candidate['path']);origin=old['scope_review']['provenance']
    if origin.get('review_id'):
        from delivery_runtime import expand_provenance
        origin=expand_provenance(origin,old['review_provenance_index'])
    m.require(m.sha(origin['path'])==origin['sha256'],'Original global output changed')
    actual=m.read(origin['path']);transport=actual.get('transport_provenance',{})
    # Canonical responses bind raw output through offline_replay instead of transport.
    raw=transport.get('raw_path')
    if raw:m.require(m.sha(raw)==transport.get('raw_sha256'),'Original global raw output changed')
    if not raw:
        sources=actual.get('offline_replay',{}).get('sources',[])
        if len(sources)!=1:return None
        raw=sources[0]['path'];m.require(m.sha(raw)==sources[0]['sha256'],'Original raw global changed')
    audit=Path(raw).parent/'audit.json'
    if not audit.is_file():return None
    audit_value=m.read(audit)
    m.require(audit_value.get('returncode')==0 and audit_value.get('output_sha256')==m.sha(raw),
              'Prior global execution is incomplete or output changed')
    if transport.get('audit_sha256'):m.require(m.sha(audit)==transport['audit_sha256'],'Prior global audit changed')
    if (audit_value.get('model'),audit_value.get('reasoning_effort'),audit_value.get('requested_service_tier'))!=settings:return None
    value={k:copy.deepcopy(v) for k,v in old['scope_review'].items() if k not in {'reviewer','provenance'}}
    # Old accepted global observations already have bound evidence files. Retain
    # those files only when their header, actual record and current page images
    # prove the same provenance; do not authorize arbitrary documentary paths.
    page_hashes={r['path']:r['sha256'] for r in ctx.get('page_images',[])}
    manuscript_paths={r['path'] for r in ctx.get('manuscript_evidence',[])}
    retained={}
    def evidence_refs(v):
        if isinstance(v,list):
            for x in v:evidence_refs(x)
        elif isinstance(v,dict):
            if v.get('basis')=='manuscript' and v.get('path') and v['path'] not in manuscript_paths:
                path=Path(v['path']);m.require(m.sha(path)==v.get('sha256'),'Prior page observation changed')
                header,body=path.read_text(encoding='utf-8-sig').split('\n',1);header=json.loads(header)
                m.require(header.get('actual_response')==origin['path'] and header.get('response_sha256')==origin['sha256'],
                          'Prior observation belongs to another response')
                sources=header.get('sources',{})
                m.require(sources and all(page_hashes.get(p)==s for p,s in sources.items()),'Prior observation page images changed')
                m.require(any(r.get('text')==body and r.get('source_pages') for r in actual.get('evidence_records',[])),
                          'Prior observation absent from actual global evidence')
                retained[str(path)]={'path':str(path),'sha256':m.sha(path)}
            for x in v.values():evidence_refs(x)
    evidence_refs(value)
    request=m.read(bundle/entry['file'])
    return {'packet_id':entry['id'],'request_sha256':request['request_sha256'],'reviewer':origin['reviewer'],
        'results':[{'task_ids':['global_scope:report'],'value':value}],
        'global_reuse':{'settings':list(settings),'ledger':candidate},
        'reused_manuscript_evidence':list(retained.values()),
        'offline_replay':{'new_model_calls':0,'not_new_semantic_review':True,
            'sources':[candidate,{'path':origin['path'],'sha256':origin['sha256']},{'path':str(audit),'sha256':m.sha(audit)},*retained.values()]}}
