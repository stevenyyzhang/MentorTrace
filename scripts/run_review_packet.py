"""Execute independent prepared checks, defaulting to three isolated workers.

Preparation and offline assembly never invoke this script automatically.
"""
import argparse
import json
import uuid
import time
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import codex_adapter
import execution_policy
import review_workflow as workflow
import run_authorized_stage as runner


class PacketCheckError(ValueError):
    def __init__(self, response, issues):
        self.response=str(response);self.issues=issues
        super().__init__('Saved actual result requires local repair: '+json.dumps(issues,ensure_ascii=False))


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
        from execution_trace import span
        with span(Path(calls)/'trace','provider:'+packet_id,'provider',model=args.model,effort=args.effort,service_tier=args.service_tier):
            raw,_=codex_adapter.invoke(attempt,request['prompt'],[Path(p['path']) for p in request['images']],
                 model=args.model,reasoning_effort=args.effort,service_tier=args.service_tier,
                 settings_authorization=authorization,context_window=policy['context_window'])
    result=m.read(raw)
    wire_metadata={}
    if request.get('wire_protocol'):
        import delivery_protocol
        audit_path=Path(raw).parent/'audit.json';actual_audit=m.read(audit_path)
        inventory={t['id']:t for t in m.read(bundle/'inventory.json')}
        if m.read(bundle/'context.json').get('delivery_focus'):result=__import__('review_contract').normalize_wire(result)
        result=delivery_protocol.materialize(result,[inventory[k] for k in request['task_ids']],delivery_protocol.expected_reviewer(args.model,actual_audit))
        wire_metadata={'wire_protocol':request['wire_protocol'],'audit_path':str(audit_path.resolve()),'audit_sha256':m.sha(audit_path)}
    # The program supplies identifiers, hashes and transport provenance; the actual model
    # supplies every judgment. Original output is retained byte-for-byte.
    for key in ['packet_id','request_sha256']:
        m.require(key not in result,'Model must not generate transport metadata')
    envelope={**result,'packet_id':packet_id,'request_sha256':request['request_sha256'],
              'transport_provenance':{'raw_path':str(raw.resolve()),'raw_sha256':m.sha(raw),'reused':bool(cached),**wire_metadata}}
    if output.exists():
        previous=m.read(output);m.require({k:v for k,v in previous.items() if k!='transport_provenance'}=={k:v for k,v in envelope.items() if k!='transport_provenance'},'Conflicting completed assembled result')
    else:workflow.audit.save_new(output,envelope)
    context=m.read(bundle/'context.json')
    if context.get('delivery_hardening') and manifest['phase']=='delivery':
        import review_contract
        normalized,changes=review_contract.normalize(envelope,context)
        if changes:
            normalized.pop('transport_provenance',None)
            normalized['offline_replay']={'new_model_calls':0,'not_new_semantic_review':True,
                'sources':[{'path':str(raw.resolve()),'sha256':m.sha(raw)}],
                'operation':'Canonical representation only; actual judgment/status/evidence unchanged.', 'changes':changes}
            canonical=folder/'canonical_response.json'
            if canonical.exists():m.require(m.read(canonical)==normalized,'Canonical result changed; inspect before resuming')
            else:m.save(canonical,normalized)
            output=canonical
        from execution_trace import span
        with span(Path(calls)/'trace','validation:'+packet_id,'deterministic_validation'):
            values,origins=workflow.collect(bundle,[output],allow_partial=True)
            tasks=[t for t in m.read(bundle/'inventory.json') if t['id'] in request['task_ids']]
            issues=review_contract.inspect(tasks,values,context)+workflow.delivery_efficiency.inspect_values(tasks,values)
            issues+=workflow.recovery.inspect(tasks,values,context,m.read(output).get('evidence_records',[]))
            for issue in review_contract.inspect_records(m.read(output),manifest['bindings'],context.get('page_images',[])):
                issues.extend({**issue,'task_id':t['id']} for t in tasks)
            issues += [{'task_id':tid,'problem':e['error'],'kind':'format'} for o in origins for e in o['collection_errors'] for tid in e['task_ids']]
            m.save(folder/'local_check.json',{'issues':issues,'pending_task_ids':sorted({i['task_id'] for i in issues}),
                'response':str(output),'response_sha256':m.sha(output),'new_model_calls':0})
        if issues:raise PacketCheckError(output,issues)
    return output


def execute_bundle(bundle,calls,args,authorization):
    """One frozen phase per wave. No next-stage launch, automatic retry or shared context."""
    if workflow.m.read(Path(bundle)/'context.json').get('delivery_hardening'):
        return execute_hardened_bundle(bundle,calls,args,authorization)
    started=datetime.datetime.now(datetime.timezone.utc).isoformat();timer=time.monotonic()
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
                values,_=workflow.collect(bundle,outputs,allow_partial=bool(m.read(bundle/'context.json').get('delivery_reliability')))
                collected=len(values)
                if m.read(bundle/'context.json').get('postprocess_efficiency'):
                    issues=workflow.delivery_efficiency.inspect_values(m.read(bundle/'inventory.json'),values)
                    if m.read(bundle/'context.json').get('delivery_reliability'):
                        inv={t['id']:t for t in m.read(bundle/'inventory.json')};ctx=m.read(bundle/'context.json')
                        for path in outputs:
                            response=m.read(path);entry=next(e for e in manifest['packets'] if e['id']==response['packet_id']);request=m.read(bundle/entry['file'])
                            issues+=workflow.recovery.inspect([inv[k] for k in request['task_ids']],values,ctx,response.get('evidence_records',[]))
                        m.save(calls/'local_check.json',{'issues':issues,'missing_ids':sorted(set(manifest['task_ids'])-set(values)),'new_model_calls':0})
                    if issues:failures.append({'phase':'local_result_check','issues':issues,
                        'action':'Preserve completed calls; address listed affected records before assembly. No automatic resubmission.'})
            except Exception as exc:failures.append({'phase':'complete_result_collection','error':str(exc)})
        receipt={'phase':manifest['phase'],'bundle':str(bundle),'workers':workers,
                 'started_utc':started,'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 'elapsed_wall_seconds':time.monotonic()-timer,
                 'expected_packets':ids,'responses':outputs,'failed':failures,
                 'complete_task_count':collected,'ready_for_assembly':not failures,
                 'independent_contexts':True,'automatic_retry':False,'downstream_started':False,
                 'note':'Complete accounting only; ordinary phase assembly and delivery validators remain required.'}
        path=calls/'execution_receipts'/(uuid.uuid4().hex+'.json')
        m.save(path,receipt)
        return {**receipt,'receipt':str(path)}
    finally:
        lock.unlink()


def execute_hardened_bundle(bundle,calls,args,authorization):
    """Locals -> validated actual completion barrier -> global. No implicit retries."""
    import delivery_runtime
    m=workflow.m;bundle=Path(bundle).resolve();calls=Path(calls).resolve()
    manifest=workflow.verify_bundle(bundle);inventory={t['id']:t for t in m.read(bundle/'inventory.json')}
    workers=getattr(args,'workers',3);m.require(type(workers) is int and 1<=workers<=3,'Use one to three workers')
    execution_policy.validate_authorization(authorization,args.model,args.effort,args.service_tier)
    m.require((manifest['policy']['model'],manifest['policy']['effort'])==(args.model,args.effort),'Settings differ from capacity policy')
    global_entries=[e for e in manifest['packets'] if any(inventory[t]['kind']=='global_scope' for t in m.read(bundle/e['file'])['task_ids'])]
    m.require(len(global_entries)<=1,'Exactly one dependent global packet is supported')
    if global_entries:m.require(len(m.read(bundle/global_entries[0]['file'])['task_ids'])==1,'Global packet contains local tasks')
    locals_=[e for e in manifest['packets'] if e not in global_entries];calls.mkdir(parents=True,exist_ok=True)
    from native_delivery import locked
    guard=locked(calls/'bundle-execution.lock');guard.__enter__();started=datetime.datetime.now(datetime.timezone.utc).isoformat();timer=time.monotonic();results={};failures=[];active_bundle=bundle
    try:
        binding={'bundle':str(bundle),'manifest_sha256':m.sha(bundle/'manifest.json'),'model':args.model,'effort':args.effort,'service_tier':args.service_tier}
        pinned=calls/'bundle_binding.json'
        if pinned.exists():m.require(m.read(pinned)==binding,'Calls folder belongs to different inputs/settings')
        else:m.save(pinned,binding)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures={pool.submit(execute,bundle,e['id'],calls,args,authorization):e['id'] for e in locals_}
            for future in as_completed(futures):
                ident=futures[future]
                try:results[ident]=str(future.result())
                except PacketCheckError as error:results[ident]=error.response;failures.append({'packet_id':ident,'phase':'local_result_check','issues':error.issues})
                except Exception as error:failures.append({'packet_id':ident,'phase':'transport_or_submission','error':str(error)})
        global_started=False
        if not failures and global_entries:
            try:
                paths=[results[e['id']] for e in locals_]
                entry=global_entries[0]
                try:
                    active_bundle=delivery_runtime.bind_global(bundle,paths,calls/'global-ready')
                except workflow.capacity.CapacityExceeded:
                    if not m.read(bundle/'context.json').get('native_report_repair'):raise
                    import delivery_global_views
                    try:active_bundle=delivery_global_views.capacity_fallback(bundle,paths,calls/'global-capacity',args,authorization)
                    except delivery_global_views.GlobalViewDefect as error:
                        failures.append({'phase':'global_result_check','actual_global_views':error.reviews})
                        active_bundle=bundle
                    else:
                        manifest=workflow.verify_bundle(active_bundle)
                        entry=next(e for e in manifest['packets'] if e['id']=='global-synthesis')
                global_started=True
                if not failures:results[entry['id']]=str(execute(active_bundle,entry['id'],calls,args,authorization))
            except PacketCheckError as error:results[entry['id']]=error.response;failures.append({'packet_id':entry['id'],'phase':'global_result_check','issues':error.issues})
            except Exception as error:failures.append({'phase':'global_barrier_or_transport','error':str(error)})
        outputs=[results[e['id']] for e in manifest['packets'] if e['id'] in results];collected=0
        if not failures:
            try:collected=len(workflow.collect(active_bundle,outputs)[0])
            except Exception as error:failures.append({'phase':'complete_result_collection','error':str(error)})
        receipt={'phase':manifest['phase'],'bundle':str(active_bundle),'original_bundle':str(bundle),'workers':workers,
            'started_utc':started,'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_wall_seconds':time.monotonic()-timer,
            'expected_packets':[e['id'] for e in manifest['packets']],'responses':outputs,'failed':failures,'complete_task_count':collected,
            'ready_for_assembly':not failures,'global_started':global_started,'actual_completion_barrier':True,'independent_contexts':True,
            'automatic_retry':False,'downstream_started':False,'note':'No semantic pass inferred. Original outputs and failed attempts remain saved.'}
        path=calls/'execution_receipts'/(uuid.uuid4().hex+'.json');m.save(path,receipt);return {**receipt,'receipt':str(path)}
    finally:guard.__exit__(None,None,None)


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
        if workflow.m.read(args.bundle/'context.json').get('delivery_compact'):
            import delivery_cycle
            result=delivery_cycle.execute(args.bundle,args.calls,args,authorization)
        else:result=execute_bundle(args.bundle,args.calls,args,authorization)
        print(json.dumps(result))
        if not result['ready_for_assembly']:raise SystemExit(1)


if __name__=='__main__':main()
