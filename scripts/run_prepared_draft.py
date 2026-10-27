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
    for n,req in enumerate(requests,1):
        part=folder/'calls'/f'part-{n:03d}'
        cached=runner.find_cached(part,req,args.model,args.effort,args.service_tier)
        if cached:raw,audit=cached
        else:
            images=[m.safe_path(folder,p['path']) for p in req['images']]
            for path,item in zip(images,req['images']):m.require(m.sha(path)==item['sha256'],'Draft image changed')
            attempt=part/args.attempt_name;cap.preflight(req,policy,attempt/'capacity_preflight.json')
            raw,_=codex_adapter.invoke(attempt,req['prompt'],images,model=args.model,reasoning_effort=args.effort,
                 service_tier=args.service_tier,settings_authorization=authorization,context_window=policy['context_window'])
        responses.append(m.read(raw));calls.append({'raw_path':str(raw),'raw_sha256':m.sha(raw),'reused':bool(cached)})
    result=draft_capacity.combine(responses,plan) if plan else responses[0]
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
