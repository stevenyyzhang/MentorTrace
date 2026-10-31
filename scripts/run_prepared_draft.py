"""Authorized complete draft submission, including automatically prepared partitions."""
import argparse
from pathlib import Path
import mentortrace_v1 as m
import request_capacity as cap
import draft_capacity
import codex_adapter
import run_authorized_stage as runner
import writing_transfer as writing
from execution_policy import validate_authorization


def execute(folder,args,authorization):
    folder=Path(folder).resolve();m.verify_frozen(folder/'inputs')
    validate_authorization(authorization,args.model,args.effort,args.service_tier)
    request=m.read(folder/'request.json');policy=m.read(folder/'automatic_capacity.json')
    m.require((policy['model'],policy['effort'])==(args.model,args.effort),'Draft settings differ from detected capacity')
    plan=None
    if request.get('capacity_plan'):
        path=m.safe_path(folder,request['capacity_plan']);m.verify_frozen(path.parent);plan=m.read(path)
        m.require(plan['policy']==policy and plan['inputs_sha256']==m.sha(folder/'inputs/FREEZE.json'),'Draft plan sources changed')
        m.require(plan['canonical_request']=={k:v for k,v in request.items() if k!='capacity_plan'},'Draft plan request changed')
    requests=[p['request'] for p in plan['parts']] if plan else [request]
    for req in requests:cap.preflight(req,policy)
    responses=[];calls=[]
    def call(item):
        n,req=item
        part=folder/'calls'/f'part-{n:03d}'
        cached=runner.find_cached(part,req,args.model,args.effort,args.service_tier)
        if cached:raw,audit=cached
        else:
            images=[m.safe_path(folder,p['path']) for p in req['images']]
            for path,item in zip(images,req['images']):m.require(m.sha(path)==item['sha256'],'Draft image changed')
            attempt=part/args.attempt_name
            m.require(not attempt.exists(),'Uncertain draft attempt; inspect saved completion before resubmitting')
            cap.preflight(req,policy,attempt/'capacity_preflight.json')
            raw,_=codex_adapter.invoke(attempt,req['prompt'],images,model=args.model,reasoning_effort=args.effort,
                 service_tier=args.service_tier,settings_authorization=authorization,context_window=policy['context_window'])
        return m.read(raw),{'raw_path':str(raw),'raw_sha256':m.sha(raw),'reused':bool(cached)}
    from concurrent.futures import ThreadPoolExecutor
    workers=min(3,(plan or {}).get('schedule',{}).get('parallel_workers',1))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        completed=list(pool.map(call,enumerate(requests,1)))
    responses=[r for r,c in completed];calls=[c for r,c in completed]
    result=draft_capacity.combine(responses,plan) if plan else responses[0]
    protocol=m.read(folder/'inputs/delivery_protocol.json') if (folder/'inputs/delivery_protocol.json').exists() else {}
    if protocol.get('canonical_draft') and plan is None:result=__import__('canonical_draft').compile(result)
    if protocol.get('canonical_draft')==2:
        import canonical_draft
        m.require(result.get('canonical_draft')==2,'Expected atomic v2 draft')
        for g in result['report_fragments']:canonical_draft.validate_action_bindings(g)
    if protocol.get('delivery_hardening') and plan is None:
        import review_integrity
        result['report_markdown']=review_integrity.assemble_fragments([result])[0]
        review_integrity.draft_requirements(m.read(folder/'inputs/verified.json'),result)
    if protocol.get('delivery_hardening'):
        import review_integrity
        for row in result.get('delivery_map',[]):
            row['report_section']=review_integrity.normalize_section(row['report_section'])
            m.require(row['report_section'] in {'content','organization','language'},'Invalid draft section code')
    import delivery_reliability
    final_for_candidates=m.read(folder/'inputs/verified.json')
    required_candidates={r['candidate_id'] for r in final_for_candidates.get('candidate_reviews',[]) if r['status'] in {'optional','author_confirmation'}}
    if required_candidates:
        rows=result.get('candidate_delivery_map',[])
        m.require(len(rows)==len(required_candidates) and {r.get('candidate_id') for r in rows}==required_candidates,'Draft omitted candidate author action')
        report=result.get('report_markdown',result.get('report',''))
        m.require(all(r.get('report_excerpt') and r['report_excerpt'] in report for r in rows),'Candidate draft excerpt absent')
    if result.get('original_references'):
        import re
        pages=m.read(folder/'inputs/paper/body.json')
        def expand(v):
            if isinstance(v,str):return re.sub(r'\[\[ORIGINAL:([^\]]+)\]\]',lambda match:delivery_reliability.original_text(pages,result['original_references'][match[1]]),v)
            if isinstance(v,list):return [expand(x) for x in v]
            if isinstance(v,dict):return {k:expand(x) for k,x in v.items()}
            return v
        result=expand(result)
        if result.get('canonical_draft'):result=__import__('canonical_draft').compile(result)
    if plan is None:
        evidence=writing.draft_view(m.read(folder/'inputs/writing_evidence.json'))
        final=m.read(folder/'inputs/verified.json')
        expected={f['id'] for key in ['findings','organization_suggestions'] for f in final.get(key,[])}
        actual=[row['verified_id'] for row in result['delivery_map']]
        m.require(len(actual)==len(set(actual)) and set(actual)==expected,'Draft delivery coverage missing or duplicated')
        writing.validate_proposals(result,evidence,final,m.read(folder/'inputs/paper/body.json'),m.anchor)
    # A draft is never marked author-deliverable here; both report audits remain mandatory.
    out=folder/'response.json'
    if out.exists():m.require(m.read(out)==result,'Existing draft differs; preserve and inspect')
    else:m.save(out,result)
    m.save(folder/'submission_receipt.json',{'actual_model_calls':calls,'not_a_single_model_output':bool(plan),
          'response_sha256':m.sha(out),'complete_delivery_audits_required':True})
    return out


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--draft',type=Path,required=True);p.add_argument('--settings-authorization',type=Path,required=True)
    p.add_argument('--model',required=True);p.add_argument('--effort',required=True)
    p.add_argument('--service-tier',choices=['default','fast','priority'],default='default')
    p.add_argument('--attempt-name',default='authorized-01');args=p.parse_args()
    m.require(Path(args.attempt_name).name==args.attempt_name and args.attempt_name not in {'','.','..'},'Invalid attempt name')
    print(execute(args.draft,args,m.read(args.settings_authorization)))


if __name__=='__main__':main()
