"""Complete-target draft partitions; preserve source material and audit the union."""
import copy
from pathlib import Path
import mentortrace_v1 as m
import request_capacity as capacity
import writing_transfer as writing


def prepare(out,instruction,payload,images,policy,canonical_request,output_aware=False):
    out=Path(out)
    final=payload['verified_review']
    rows=[('findings',f) for f in final['findings']]+[('organization_suggestions',f) for f in final.get('organization_suggestions',[])]
    rows += [('candidate_reviews',r) for r in final.get('candidate_reviews',[]) if r['status'] in {'optional','author_confirmation'}]
    ident=lambda value:value.get('id',value.get('candidate_id'))
    m.require(rows,'No independent draft targets to partition')
    # Preserve explicit target dependencies and all changes at a common source page.
    # This conservative grouping prevents splitting potentially overlapping rewrites.
    parents=list(range(len(rows)));ids={ident(v):n for n,(_,v) in enumerate(rows)}
    def root(n):
        while parents[n]!=n:n=parents[n]
        return n
    def strings(v):
        if isinstance(v,str):yield v
        elif isinstance(v,list):
            for x in v:yield from strings(x)
        elif isinstance(v,dict):
            for x in v.values():yield from strings(x)
    pages={}
    for n,(_,row) in enumerate(rows):
        page=row.get('anchor',{}).get('page')
        if page in pages:parents[root(n)]=root(pages[page])
        elif page is not None:pages[page]=n
        for value in strings(row):
            if value in ids:parents[root(n)]=root(ids[value])
    groups={}
    for n,row in enumerate(rows):groups.setdefault(root(n),[]).append(row)
    def build(selected,index):
        data=copy.deepcopy(payload)
        data['verified_review']={**final,'findings':[v for k,v in selected if k=='findings'],
                                 'organization_suggestions':[v for k,v in selected if k=='organization_suggestions']}
        if final.get('candidate_reviews'):
            data['verified_review']['candidate_reviews']=[v for k,v in selected if k=='candidate_reviews']
        assigned=[ident(v) for _,v in selected]
        def owner(resolution):
            matches=[i for i in ids if i in resolution.get('output_ids',[])]
            m.require(bool(matches),'Draft requirement has no assigned final target: '+resolution.get('component_id','unknown'))
            return matches[0]
        owned=[r for r in final.get('source_requirement_resolutions',[]) if r['assessment'] in {'required','optional','unknown'} and owner(r) in assigned] if payload.get('delivery_hardening') else []
        if payload.get('delivery_hardening'):
            data['verified_review']['source_requirement_resolutions']=owned
            related={i for r in owned for i in r.get('output_ids',[])}
            data['related_verified_targets']=[v for _,v in rows if ident(v) in related and ident(v) not in assigned]
        data['draft_partition']={'assigned_ids':assigned,'all_ids':[ident(v) for _,v in rows],'assigned_verified_ids':[ident(v) for k,v in selected if k!='candidate_reviews'],'assigned_candidate_ids':[ident(v) for k,v in selected if k=='candidate_reviews'],
             'display_numbers':{ident(v):n for n,(_,v) in enumerate(rows,1) if 'id' in v},'part':index}
        rule=('\nCAPACITY DRAFT PART: Write only the assigned verified items, accounting for every one. '
              'Assigned candidate IDs require candidate_delivery_map, not delivery_map. Related targets supply complete dependency context but are not extra assigned prose. All manuscript, source evidence and conditions are still supplied. '
              'Use the assigned display numbers. Return the ordinary drafting JSON including report_markdown; '
              'all draft_label and generated passage IDs must begin with P'+str(index)+'_. '
              'For part 1 include title/metadata/usage once; other parts contain only their report body, '
              'without repeating the report introduction. Do not claim this partial report is a complete delivery. '
              'Do not resolve cross-part conflicts by omitting a requirement; record them in limits. '
              'The assembled report still needs both complete delivery audits.\n')
        if payload.get('delivery_hardening'):
            rule=rule.replace('Return the ordinary drafting JSON including report_markdown;', 'Return structured drafting JSON with report_fragments and only part 1 report_preamble; omit assembled report_markdown;')
        receipt=None
        if payload.get('draft_context_v1'):
            import draft_context
            data,receipt=draft_context.project(data,payload)
            if draft_context.INSTRUCTIONS not in instruction:
                rule+='\n'+draft_context.INSTRUCTIONS
        prompt=instruction+rule+'\n'+capacity.WIRE_RULE+'\nINPUT\n'+capacity.encode(data)
        req={'stage':'revision_proposals','prompt':prompt,'images':images,'tools_allowed':False}
        part={'request':req,'payload':data,'assigned_ids':assigned}
        if receipt is not None:part['input_scope_receipt']=receipt
        return part,capacity.capacity.estimate(prompt,len(images),policy)
    packets=[];pending=[]
    schedule={'mode':'input_capacity','parallel_workers':1,'measured_speedup':False}
    whole,whole_budget=build(rows,1)
    if output_aware and whole_budget['fits']:
        schedule={'mode':'single','parallel_workers':1,'reason':'No matched observed output/timing profile; preserve one call.','measured_speedup':False}
        profile=policy.get('draft_output_profile')
        if profile:
            import output_schedule
            schedule=output_schedule.choose(list(groups.values()),build,policy,images,profile)
            if schedule['parallel_workers']>1:
                packets=[build([r for index in bucket for r in list(groups.values())[index]],n)[0] for n,bucket in enumerate(schedule['buckets'],1)]
        m.save(out/'output_schedule.json',schedule)
        if not packets:return None
    if not packets:

        for group in groups.values():
            part,budget=build(pending+group,len(packets)+1)
            if budget['fits']:pending+=group;continue
            if pending:packets.append(build(pending,len(packets)+1)[0]);pending=[]
            part,budget=build(group,len(packets)+1)
            if not budget['fits']:
                m.save(out/'capacity_obstacle.json',{'status':'infeasible','capacity':budget,
                    'target_ids':part['assigned_ids'],'complete_shared_evidence_retained':True,
                    'user_confirmation_required':False,'model_calls_submitted_by_planner':0})
            m.require(budget['fits'],'One coordinated draft target group plus complete shared evidence exceeds actual capacity; no content removed')
            pending=group
        if pending:packets.append(build(pending,len(packets)+1)[0])
    m.require(sorted(i for p in packets for i in p['assigned_ids'])==sorted(ids),'Draft target coverage changed')
    plan={'version':2,'schedule':schedule,'stage':'revision_proposals','policy':policy,'parts':packets,
          'payload':payload,'canonical_request':canonical_request,'inputs_sha256':m.sha(out/'inputs/FREEZE.json'),
          'user_confirmation_required':False,'complete_report_review_required':True}
    m.save(out/'capacity_plan/plan.json',plan);m.freeze(out/'capacity_plan')
    return 'capacity_plan/plan.json'


def combine(parts,plan):
    m.require(len(parts)==len(plan['parts']),'Missing draft partition')
    merged={};seen=[];expanded_parts=[]
    for response,part in zip(parts,plan['parts']):
        if plan['payload'].get('canonical_draft'):response=__import__('canonical_draft').compile(response,partial=True)
        hard=bool(plan['payload'].get('delivery_hardening'))
        if hard:
            import review_integrity
            response=copy.deepcopy(response);response['report_markdown']=review_integrity.assemble_fragments([response],partial=True)[0]
            review_integrity.draft_requirements(part['payload']['verified_review'],response)
        expanded_parts.append(response)
        actual=[r['verified_id'] for r in response['delivery_map']]
        candidates=[r['candidate_id'] for r in response.get('candidate_delivery_map',[])]
        partition=part['payload']['draft_partition']
        required_candidates=partition.get('assigned_candidate_ids',[])
        m.require(len(candidates)==len(set(candidates)) and set(candidates)==set(required_candidates),'Draft candidate delivery coverage missing or duplicated')
        m.require(len(actual)==len(set(actual)) and set(actual)==set(partition.get('assigned_verified_ids',part['assigned_ids'])),'Draft delivery coverage missing or duplicated')
        evidence=part['payload']['writing_evidence_linked_sources_not_target_facts']
        writing.validate_proposals(response,evidence,part['payload']['verified_review'],part['payload']['manuscript'],m.anchor)
        seen+=actual
        for key,value in response.items():
            if key=='canonical_groups_sha256':continue
            if key=='report_markdown':merged[key]=merged.get(key,'')+('\n\n' if merged.get(key) else '')+value
            elif key=='original_references':
                current=merged.setdefault(key,{})
                m.require(not set(current)&set(value),'Original reference IDs collide across parts')
                current.update(copy.deepcopy(value))
            elif isinstance(value,list):merged.setdefault(key,[]).extend(copy.deepcopy(value))
            elif key=='report_preamble':
                if value:
                    m.require(not merged.get(key),'Repeated report preamble');merged[key]=value
            elif key not in merged:merged[key]=copy.deepcopy(value)
            else:m.require(merged[key]==value,'Conflicting draft metadata; do not discard content')
    expected=[f['id'] for key in ['findings','organization_suggestions'] for f in plan['payload']['verified_review'].get(key,[])]
    m.require(len(seen)==len(set(seen)) and set(seen)==set(expected),'Combined draft coverage mismatch')
    labels=[r['draft_label'] for r in merged['revision_actions']]
    m.require(len(labels)==len(set(labels)),'Partition draft labels collide')
    if plan['payload'].get('delivery_hardening'):
        import review_integrity
        merged['report_markdown']=review_integrity.assemble_fragments(expanded_parts)[0]
        review_integrity.draft_requirements(plan['payload']['verified_review'],merged)
    if plan['payload'].get('canonical_draft'):merged=__import__('canonical_draft').compile(merged)
    evidence=plan['payload']['writing_evidence_linked_sources_not_target_facts']
    writing.validate_proposals(merged,evidence,plan['payload']['verified_review'],plan['payload']['manuscript'],m.anchor)
    return merged
