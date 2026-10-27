"""Execute independent prepared checks, defaulting to three isolated workers.

Preparation and offline assembly never invoke this script automatically.
"""
import argparse
import json
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import codex_adapter
import execution_policy
import review_workflow as workflow
import run_authorized_stage as runner


def execute(bundle, packet_id, calls, args, authorization):
    m=workflow.m;bundle=Path(bundle);manifest=workflow.verify_bundle(bundle)
    entry=next((p for p in manifest['packets'] if p['id']==packet_id),None)
    m.require(entry is not None,'Unknown prepared review packet')
    policy=manifest['policy']
    m.require((policy['model'],policy['effort'])==(args.model,args.effort),'Review settings differ from pinned capacity policy')
    execution_policy.validate_authorization(authorization,args.model,args.effort,args.service_tier)
    request=m.read(bundle/entry['file']);request['images']=[{'path':p['path'],'sha256':p['sha256']} for p in request['images']]
    folder=Path(calls)/packet_id;output=folder/'assembled_response.json'
    transport_request={'prompt':request['prompt'],'images':request['images']}
    cached=runner.find_cached(folder,transport_request,args.model,args.effort,args.service_tier)
    if cached:raw,audit=cached
    else:
        attempt=folder/args.attempt_name
        m.require(not (attempt/'START.json').exists(),'Existing attempt; inspect saved status before retry')
        raw,_=codex_adapter.invoke(attempt,request['prompt'],[Path(p['path']) for p in request['images']],
             model=args.model,reasoning_effort=args.effort,service_tier=args.service_tier,
             settings_authorization=authorization,context_window=policy['context_window'])
    result=m.read(raw)
    # The program supplies identifiers, hashes and transport provenance; the actual model
    # supplies every judgment. Original output is retained byte-for-byte.
    for key in ['packet_id','request_sha256']:
        m.require(key not in result,'Model must not generate transport metadata')
    envelope={**result,'packet_id':packet_id,'request_sha256':request['request_sha256'],
              'transport_provenance':{'raw_path':str(raw.resolve()),'raw_sha256':m.sha(raw),'reused':bool(cached)}}
    if output.exists():
        previous=m.read(output);m.require({k:v for k,v in previous.items() if k!='transport_provenance'}=={k:v for k,v in envelope.items() if k!='transport_provenance'},'Conflicting completed assembled result')
    else:workflow.audit.save_new(output,envelope)
    return output


def execute_bundle(bundle,calls,args,authorization):
    """One frozen phase per wave. No next-stage launch, automatic retry or shared context."""
    m=workflow.m;bundle=Path(bundle).resolve();calls=Path(calls).resolve()
    workers=getattr(args,'workers',3)
    m.require(type(workers) is int and 1<=workers<=3,'Use one to three post-processing workers')
    manifest=workflow.verify_bundle(bundle)  # Validate ALL inputs/capacities before any submission.
    m.require(manifest['phase'] in {'source','delivery'},'Unsupported independent review phase')
    policy=manifest['policy']
    m.require((policy['model'],policy['effort'])==(args.model,args.effort),'Review settings differ from pinned capacity policy')
    execution_policy.validate_authorization(authorization,args.model,args.effort,args.service_tier)
    ids=[p['id'] for p in manifest['packets']]
    m.require(ids and len(ids)==len(set(ids)),'Empty or duplicate review packet inventory')
    for entry in manifest['packets']:
        req=m.read(bundle/entry['file'])
        for item in req['images']:
            m.require(m.sha(item['path'])==item['sha256'],'Review image changed')
    calls.mkdir(parents=True,exist_ok=True)
    lock=calls/'bundle-execution.lock'
    # A second coordinator must not submit the same packets concurrently.
    with lock.open('x',encoding='utf-8') as stream:
        json.dump({'bundle':str(bundle),'workers':workers},stream)
    results={};failures=[]
    try:
        binding={'bundle':str(bundle),'manifest_sha256':m.sha(bundle/'manifest.json'),
                 'model':args.model,'effort':args.effort,'service_tier':args.service_tier}
        pinned=calls/'bundle_binding.json'
        if pinned.exists():m.require(m.read(pinned)==binding,'Calls folder belongs to another frozen bundle/settings')
        else:m.save(pinned,binding)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures={pool.submit(execute,bundle,ident,calls,args,authorization):ident for ident in ids}
            for future in as_completed(futures):
                ident=futures[future]
                try:results[ident]=str(future.result())
                except Exception as exc:failures.append({'packet_id':ident,'error':str(exc)})
        outputs=[results[i] for i in ids if i in results]
        collected=0
        if not failures:
            try:
                values,_=workflow.collect(bundle,outputs)
                collected=len(values)
            except Exception as exc:failures.append({'phase':'complete_result_collection','error':str(exc)})
        receipt={'phase':manifest['phase'],'bundle':str(bundle),'workers':workers,
                 'expected_packets':ids,'responses':outputs,'failed':failures,
                 'complete_task_count':collected,'ready_for_assembly':not failures,
                 'independent_contexts':True,'automatic_retry':False,'downstream_started':False,
                 'note':'Complete accounting only; ordinary phase assembly and delivery validators remain required.'}
        path=calls/'execution_receipts'/(uuid.uuid4().hex+'.json')
        m.save(path,receipt)
        return {**receipt,'receipt':str(path)}
    finally:
        lock.unlink()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['bundle','calls','settings-authorization']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--packet',help='Optional single packet; omit to run this frozen bundle with three workers')
    p.add_argument('--workers',type=int,choices=[1,2,3],default=3)
    p.add_argument('--model',required=True);p.add_argument('--effort',required=True)
    p.add_argument('--service-tier',choices=['default','fast','priority'],default='default')
    p.add_argument('--attempt-name',default='authorized-01');args=p.parse_args()
    workflow.m.require(Path(args.attempt_name).name==args.attempt_name and args.attempt_name not in {'','.','..'},'Attempt must be one directory name')
    authorization=workflow.m.read(args.settings_authorization)
    if args.packet:print(execute(args.bundle,args.packet,args.calls,args,authorization))
    else:
        result=execute_bundle(args.bundle,args.calls,args,authorization)
        print(json.dumps(result))
        if not result['ready_for_assembly']:raise SystemExit(1)


if __name__=='__main__':main()
