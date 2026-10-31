"""Automatic consolidation partitions with full manuscript/evidence in each call.

Only the adjudication targets are partitioned. No source evidence is summarized;
cross-packet duplicates are retained rather than silently merged or discarded.
"""
import copy
from pathlib import Path

import mentortrace_v1 as m
import request_capacity as capacity


def prepare(run, stage, context, request, policy):
    m.require(stage in {'merge','verify'}, 'No safe task partition for this full-context stage')
    run=Path(run);folder=run/'capacity_plans'/stage
    items=[('input_findings',v) for v in context['input_findings']]
    items += [('input_organization_suggestions',v) for v in context.get('input_organization_suggestions',[])]
    items += [('excluded_organization_candidates',{'id':c['suggestion']['id'],**c}) for c in context.get('excluded_organization_candidates',[])]
    if context.get('delivery_reliability'):
        items += [('delivery_candidates',c) for c in context.get('delivery_candidates',[])]
        items += [('source_requirement',{'id':'requirement:'+u['source_id'],'unit':u,
                    'related_targets':context.get('source_requirement_routes',{}).get(u['source_id'],[])})
                  for u in context.get('initial_source_review',{}).get('source_requirements',[])]
    # Execution issues are adjudication targets, not shared evidence. Assign once.
    items += [('coverage_execution_issues',{'id':'execution_issue:'+v['id'],'issue':v})
              for v in context.get('coverage_execution_issues',[])]
    m.require(items,'No independent targets to partition')
    # Explicit cross-target references keep their complete records together.
    ids={v['id']:n for n,(_,v) in enumerate(items)};parents=list(range(len(items)))
    def root(n):
        while parents[n]!=n:n=parents[n]
        return n
    def strings(v):
        if isinstance(v,str):yield v
        elif isinstance(v,list):
            for x in v:yield from strings(x)
        elif isinstance(v,dict):
            for x in v.values():yield from strings(x)
    for n,(_,v) in enumerate(items):
        for value in strings(v):
            if value in ids:parents[root(n)]=root(ids[value])
    # Competing editorial alternatives require a joint decision, not one per shard.
    editorial=[n for n,(kind,_) in enumerate(items) if kind in {'input_organization_suggestions','excluded_organization_candidates'}]
    for n in editorial[1:]:parents[root(n)]=root(editorial[0])
    groups={}
    for n,item in enumerate(items):groups.setdefault(root(n),[]).append(item)
    groups=list(groups.values())
    def build(rows):
        ctx=copy.deepcopy(context)
        ctx['input_findings']=[v for k,v in rows if k=='input_findings']
        if 'coverage_execution_issues' in ctx:
            ctx['coverage_execution_issues']=[v['issue'] for k,v in rows if k=='coverage_execution_issues']
        if 'input_organization_suggestions' in ctx:
            ctx['input_organization_suggestions']=[v for k,v in rows if k=='input_organization_suggestions']
        if 'excluded_organization_candidates' in ctx:
            ctx['excluded_organization_candidates']=[{k:v for k,v in item.items() if k!='id'} for kind,item in rows if kind=='excluded_organization_candidates']
        if ctx.get('delivery_reliability'):
            ctx['delivery_candidates']=[v for k,v in rows if k=='delivery_candidates']
            if 'initial_source_review' in ctx:
                ctx['initial_source_review']['source_requirements']=[v['unit'] for k,v in rows if k=='source_requirement']
            selected_candidates={v['id'] for v in ctx['delivery_candidates']}
            ctx['prior_candidate_reviews']=[v for v in ctx.get('prior_candidate_reviews',[]) if v['candidate_id'] in selected_candidates]
        ctx['capacity_partition']={
            'assigned_ids':[v['id'] for _,v in rows],
            'all_target_ids':[v['id'] for _,v in items],
            'rule':'Judge every assigned complete target using the complete manuscript and shared evidence. Other target IDs are routing only, not evidence. Do not withdraw or merge an assigned requirement based on an unseen other target; retain it independently. Preserve all conditions and unresolved questions. Cross-partition duplicates may remain and are not permission to omit a requirement.'}
        req=m.prepare_stage_request(run,stage,_context_override=ctx,_planning=True)
        return ctx,req,capacity.capacity.estimate(req['prompt'],len(req['images']),policy)
    packets=[];pending=[]
    for group in groups:
        ctx,req,budget=build(pending+group)
        if budget['fits']:pending+=group;continue
        if pending:
            packets.append(build(pending));pending=[]
        ctx,req,budget=build(group)
        if not budget['fits']:
            m.save(run/'capacity_checks'/(stage+'.obstacle.json'),{'status':'infeasible','capacity':budget,
                'target_ids':[v['id'] for _,v in group],'complete_shared_evidence_retained':True,
                'user_confirmation_required':False,'model_calls_submitted_by_planner':0})
        m.require(budget['fits'],'One complete consolidation target plus full manuscript/shared evidence exceeds actual capacity; no evidence removed')
        pending=group
    if pending:packets.append(build(pending))
    entries=[]
    for n,(ctx,req,budget) in enumerate(packets,1):
        name=f'part-{n:03d}'
        entries.append({'id':name,'context':ctx,'request':req,'capacity':budget,
                        'target_ids':ctx['capacity_partition']['assigned_ids']})
    m.require(sorted(i for e in entries for i in e['target_ids'])==sorted(ids),'Partition coverage changed')
    plan={'version':1,'stage':stage,'source_context':context,'canonical_request':request,
          'policy':policy,'parts':entries,'user_confirmation_required':False,
          'assembly':'Exact union of validated returned records; no semantic deduplication or invented judgments.'}
    path=folder/'plan.json'
    if path.exists():m.require(m.read(path)==plan,'Frozen capacity plan changed')
    else:m.save(path,plan);m.freeze(folder)
    return path.relative_to(run).as_posix()


def validate_plan(run,request):
    path=m.safe_path(Path(run),request['capacity_plan']);m.verify_frozen(path.parent)
    plan=m.read(path)
    canonical={k:v for k,v in request.items() if k!='capacity_plan'}
    m.require(plan['canonical_request']==canonical,'Capacity plan request changed')
    m.require(plan['source_context']==m.context_for(Path(run),request['stage']),'Capacity source context changed')
    return plan


def combine(stage, parts, context):
    """Namespace only returned output IDs; preserve every field and every judgment."""
    def union(a,b):
        if isinstance(a,list) and isinstance(b,list):return a+b
        if isinstance(a,dict) and isinstance(b,dict):
            return {k:union(a[k],b[k]) if k in a and k in b else copy.deepcopy(a[k] if k in a else b[k]) for k in a.keys()|b.keys()}
        m.require(a==b,'Conflicting non-list partition output; do not discard content')
        return copy.deepcopy(a)
    result={}
    for n,(value,ctx) in enumerate(parts,1):
        m.validate(stage,value,ctx)
        rename={f['id']:stage+':'+('G' if field=='organization_suggestions' else 'F')+f'P{n}_'+str(i)
                for field in ['findings','organization_suggestions'] for i,f in enumerate(value.get(field,[]),1)}
        rename.update({g['id']:f'{stage}:EP{n}_{i}' for i,g in enumerate(value.get('editorial_selection',[]),1)})
        def visit(v):
            if isinstance(v,str):return rename.get(v,v)
            if isinstance(v,list):return [visit(x) for x in v]
            if isinstance(v,dict):return {k:visit(x) for k,x in v.items()}
            return v
        result=union(result,visit(value))
    m.validate(stage,result,context)
    return result
