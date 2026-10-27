"""Complete-target draft partitions; preserve source material and audit the union."""
import copy
from pathlib import Path
import mentortrace_v1 as m
import request_capacity as capacity
import writing_transfer as writing


def prepare(out,instruction,payload,images,policy,canonical_request):
    out=Path(out)
    final=payload['verified_review']
    rows=[('findings',f) for f in final['findings']]+[('organization_suggestions',f) for f in final.get('organization_suggestions',[])]
    m.require(rows,'No independent draft targets to partition')
    # Preserve explicit target dependencies and all changes at a common source page.
    # This conservative grouping prevents splitting potentially overlapping rewrites.
    parents=list(range(len(rows)));ids={v['id']:n for n,(_,v) in enumerate(rows)}
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
        assigned=[v['id'] for _,v in selected]
        data['draft_partition']={'assigned_ids':assigned,'all_ids':[v['id'] for _,v in rows],
             'display_numbers':{v['id']:n for n,(_,v) in enumerate(rows,1)},'part':index}
        rule=('\nCAPACITY DRAFT PART: Write only the assigned verified items, accounting for every one. '
              'All manuscript, source evidence and conditions are still supplied. Other IDs are routing only. '
              'Use the assigned display numbers. Return the ordinary drafting JSON including report_markdown; '
              'all draft_label and generated passage IDs must begin with P'+str(index)+'_. '
              'For part 1 include title/metadata/usage once; other parts contain only their report body, '
              'without repeating the report introduction. Do not claim this partial report is a complete delivery. '
              'Do not resolve cross-part conflicts by omitting a requirement; record them in limits. '
              'The assembled report still needs both complete delivery audits.\n')
        prompt=instruction+rule+'\n'+capacity.WIRE_RULE+'\nINPUT\n'+capacity.encode(data)
        req={'stage':'revision_proposals','prompt':prompt,'images':images,'tools_allowed':False}
        return {'request':req,'payload':data,'assigned_ids':assigned},capacity.capacity.estimate(prompt,len(images),policy)
    packets=[];pending=[]
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
    plan={'version':1,'stage':'revision_proposals','policy':policy,'parts':packets,
          'payload':payload,'canonical_request':canonical_request,'inputs_sha256':m.sha(out/'inputs/FREEZE.json'),
          'user_confirmation_required':False,'complete_report_review_required':True}
    m.save(out/'capacity_plan/plan.json',plan);m.freeze(out/'capacity_plan')
    return 'capacity_plan/plan.json'


def combine(parts,plan):
    m.require(len(parts)==len(plan['parts']),'Missing draft partition')
    merged={};seen=[]
    for response,part in zip(parts,plan['parts']):
        actual=[r['verified_id'] for r in response['delivery_map']]
        m.require(len(actual)==len(set(actual)) and set(actual)==set(part['assigned_ids']),'Draft delivery coverage missing or duplicated')
        evidence=part['payload']['writing_evidence_linked_sources_not_target_facts']
        writing.validate_proposals(response,evidence,part['payload']['verified_review'],part['payload']['manuscript'],m.anchor)
        seen+=actual
        for key,value in response.items():
            if key=='report_markdown':merged[key]=merged.get(key,'')+('\n\n' if merged.get(key) else '')+value
            elif isinstance(value,list):merged.setdefault(key,[]).extend(copy.deepcopy(value))
            elif key not in merged:merged[key]=copy.deepcopy(value)
            else:m.require(merged[key]==value,'Conflicting draft metadata; do not discard content')
    expected=[f['id'] for key in ['findings','organization_suggestions'] for f in plan['payload']['verified_review'].get(key,[])]
    m.require(len(seen)==len(set(seen)) and set(seen)==set(expected),'Combined draft coverage mismatch')
    labels=[r['draft_label'] for r in merged['revision_actions']]
    m.require(len(labels)==len(set(labels)),'Partition draft labels collide')
    evidence=plan['payload']['writing_evidence_linked_sources_not_target_facts']
    writing.validate_proposals(merged,evidence,plan['payload']['verified_review'],plan['payload']['manuscript'],m.anchor)
    return merged
