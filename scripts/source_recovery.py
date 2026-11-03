"""Native source-only normalization, early validation and one affected-task correction."""
import copy
import json
import time
from pathlib import Path

INSTRUCTIONS = '''SOURCE RECORD CONTRACT:
reviewer.limits is a string. Each evidence/occurrences entry is {kind:"text",page,quote}
or {kind:"image",page,description}; source image hashes are supplied by the runner.
Use a source_field from source_field_maps for that source and quote its actual literal text.
Do not invent a field, infer an observation from a location label, or discard an occurrence.
Duplicate means the same independently answerable requirement AND complete occurrence scope;
otherwise retain separate components. Use a supplied canonical component; no duplicate chains.
During correction, return only assigned task IDs; prior valid peer judgments are read-only
context, not instructions to agree. Resolve every reported defect together, preserving all
independent requests, conditions and uncertainty. No downstream opinions or report are supplied.
'''


def fields(source):
    result={}
    def walk(value,path):
        if isinstance(value,str):result[path]=value
        elif isinstance(value,dict):
            for k,v in value.items():
                if k.replace('_','').isalnum():walk(v,path+'.'+k if path else k)
        elif isinstance(value,list):
            for i,v in enumerate(value):walk(v,path+'['+str(i)+']')
    walk(source.get('original',{}),'original');walk(source.get('checks',[]),'checks')
    return result


def normalize(response, context):
    """Reversible syntax only; no verdict, quote, duplicate link or occurrence invented."""
    import review_contract
    result,changes=review_contract.normalize(response,context)
    images={p['page']:p['sha256'] for p in context.get('page_images',[])}
    def walk(value,path):
        if isinstance(value,list):
            for i,v in enumerate(value):walk(v,path+'/'+str(i))
        elif isinstance(value,dict):
            if type(value.get('page')) is int:
                if 'kind' not in value and isinstance(value.get('quote'),str):
                    value['kind']='text';changes.append({'path':path,'operation':'type explicit page/quote'})
                elif 'kind' not in value and isinstance(value.get('description'),str) and value['page'] in images:
                    value['kind']='image';changes.append({'path':path,'operation':'type explicit page/description'})
                if value.get('kind')=='image' and 'image_sha256' not in value and value['page'] in images:
                    value['image_sha256']=images[value['page']];changes.append({'path':path,'operation':'bind actual supplied page hash'})
            for k,v in value.items():walk(v,path+'/'+k)
    walk(result.get('results',[]),'results');walk(result.get('judgments',{}),'judgments')
    return result,changes


def inspect(tasks,values,context,reviewer):
    import audit_merge_obligations as a
    import mentortrace_v1 as m
    issues=[];components={};owners={}
    def add(t,error):issues.append({'task_id':t['id'],'error':str(error)})
    for t in tasks:
        value=values.get(t['id'])
        if value is None:add(t,'Missing/invalid actual source review result');continue
        try:
            if t['kind']=='source':
                unit={**copy.deepcopy(value),'source_id':t['key'],'source_sha256':t['data']['source_sha256']}
                for c in unit.get('components',[]):
                    if c['id'] in components:
                        add(t,'Duplicate component ID');add(owners[c['id']],'Duplicate component ID')
                    components[c['id']]=copy.deepcopy(c);owners[c['id']]=t
                    # Validate all nonrelational fields now. Actual duplicate relations
                    # are checked below on original records, never changed in output.
                    if c.get('assessment')=='duplicate':c['assessment']='unknown';c.pop('duplicate_of',None)
                package={};snapshot={'sources':[t['data']],'manuscript':context['manuscript'],'page_images':context['page_images']}
                a.validate_a({'schema_version':a.SCHEMA,'phase':'A','package_sha256':a.value_digest(package),
                              'reviewer':reviewer,'units':[unit]},package,snapshot)
            elif t['kind']=='execution':
                m.require(value.get('status') in {'completed','unknown','unattempted','narrowed'} and a.substantial(value.get('reason'))
                          and isinstance(value.get('issues'),list),'Incomplete execution judgment')
            elif t['kind']=='stage_scope':
                m.require(value.get('status')=='completed' and a.substantial(value.get('reason')) and isinstance(value.get('issues'),list)
                          and isinstance(value.get('unresolved_ids'),list),'Incomplete stage scope judgment')
                if context.get('coverage_basis_v1'):
                    scope=next(s for s in context['original_stage_context'] if s['stage']==t['key'])
                    __import__('coverage_basis').validate_audit(value,scope,{p['page']:p['text'] for p in context['manuscript']},m.anchor)
        except (ValueError,TypeError,KeyError,StopIteration) as error:add(t,error)
    peers=context.get('source_peer_components',{})
    all_components={**peers,**components}
    for cid,c in components.items():
        if c.get('assessment')!='duplicate':continue
        canonical=all_components.get(c.get('duplicate_of'))
        if not canonical or canonical is c or c.get('duplicate_of')==cid or canonical.get('assessment')=='duplicate':
            add(owners[cid],'Duplicate requires an existing independent canonical component')
        elif c.get('occurrences')!=canonical.get('occurrences'):
            add(owners[cid],'Duplicate occurrences differ; semantically reassess, never union automatically')
    return issues


def execute(bundle,calls,args,authorization):
    import run_review_packet as runner
    import review_workflow as w
    m=w.m;bundle=Path(bundle);calls=Path(calls);started=time.monotonic()
    first=runner.execute_bundle(bundle,calls,args,authorization,_source_once=True)
    # Transport uncertainty must not cause a blind resubmission.
    if first['failed']:return first
    tasks=m.read(bundle/'inventory.json');ctx=m.read(bundle/'context.json');manifest=w.verify_bundle(bundle)
    values,origins=w.collect(bundle,first['responses'],allow_partial=True)
    issues=inspect(tasks,values,ctx,origins[0]['reviewer'])
    m.save(calls/'source_check.json',{'issues':issues,'new_model_calls':0})
    if not issues:return first
    pending={i['task_id'] for i in issues};repair=calls/'source-correction-bundle'
    # Include only referenced canonical source context, not every successful peer.
    peer_ids={c.get('duplicate_of') for t in tasks if t['id'] in pending for c in values.get(t['id'],{}).get('components',[])}
    peers={c['id']:c for tid,v in values.items() if tid not in pending for c in v.get('components',[]) if c['id'] in peer_ids}
    peer_sources=[t for t in tasks if t['id'] not in pending and any(c['id'] in peers for c in values.get(t['id'],{}).get('components',[]))]
    repair_ctx={**ctx,'source_correction':{'issues':issues,'actual_prior_values':{k:v for k,v in values.items() if k in pending}},
                'source_peer_components':peers,'source_peer_inputs':peer_sources}
    bindings={**manifest['bindings'],str((bundle/'manifest.json').resolve()):m.sha(bundle/'manifest.json'),
              **{str(Path(p).resolve()):m.sha(p) for p in first['responses']}}
    if not repair.exists():w.prepare_bundle(repair,'source',repair_ctx,[t for t in tasks if t['id'] in pending],bindings,manifest['policy'])
    else:
        saved=w.verify_bundle(repair)
        m.require(saved['bindings']==bindings and m.read(repair/'context.json')==repair_ctx,'Saved source correction changed')
    second=runner.execute_bundle(repair,calls/'source-correction-calls',args,authorization,_source_once=True)
    if second['failed']:return {**first,'ready_for_assembly':False,'failed':second['failed'],'source_correction':second}
    fixed,fixed_origins=w.collect(repair,second['responses'],allow_partial=True)
    combined={**{k:v for k,v in values.items() if k not in pending},**fixed}
    issues=inspect(tasks,combined,ctx,origins[0]['reviewer'])
    if issues:
        return {**first,'ready_for_assembly':False,'failed':issues,'source_correction':second,
                'continuation':'Source correction limit reached; saved actual unresolved tasks, no scientific pass inferred'}
    # Rebind the actual corrected values to the original task inventory. Immutable
    # provenance includes both generations; collect verifies each constituent again.
    outputs=[];all_refs=[{'path':str(Path(p).resolve()),'sha256':m.sha(p)} for p in first['responses']+second['responses']]
    composed_reviewer={'name':'Composed source review with recorded local correction','kind':'self_review',
        'context_scope':'originals_and_full_manuscript','prior_outputs_seen':True,
        'limits':'Initial values and affected source-only follow-up retain constituent provenance; not fresh independent discovery.'}
    for entry in manifest['packets']:
        request=m.read(bundle/entry['file']);out=calls/'source-reconciled'/(entry['id']+'.json')
        response={'packet_id':entry['id'],'request_sha256':request['request_sha256'],'reviewer':composed_reviewer,
            'results':[{'task_ids':[tid],'value':combined[tid]} for tid in request['task_ids']],
            'source_reconciliation':{'original_bundle':str(bundle.resolve()),'repair_bundle':str(repair.resolve()),
                'original_responses':first['responses'],'repair_responses':second['responses'],'replaced_ids':sorted(pending)},
            'offline_replay':{'new_model_calls':0,'not_new_semantic_review':True,'sources':all_refs}}
        if out.exists():m.require(m.read(out)==response,'Reconciled source result changed')
        else:m.save(out,response)
        outputs.append(str(out))
    w.collect(bundle,outputs)
    receipt={**first,'responses':outputs,'source_correction':second,'corrected_task_ids':sorted(pending),
        'unaffected_task_count':len(tasks)-len(pending),'elapsed_wall_seconds':time.monotonic()-started,
        'record_correction_waves':1,'ready_for_assembly':True,'complete_task_count':len(tasks)}
    m.save(calls/'source_recovery_receipt.json',receipt)
    return receipt


def verify_reconciliation(response,folder):
    import review_workflow as w
    r=response['source_reconciliation']
    if Path(r['original_bundle']).resolve()!=Path(folder).resolve():raise ValueError('Wrong source reconciliation bundle')
    # Constituent originals cannot themselves be composite, preventing recursive provenance.
    for p in r['original_responses']+r['repair_responses']:
        if w.m.read(p).get('source_reconciliation'):raise ValueError('Nested source reconciliation is unsupported')
    original,_=w.collect(r['original_bundle'],r['original_responses'],allow_partial=True)
    repaired,_=w.collect(r['repair_bundle'],r['repair_responses'])
    pending=set(r['replaced_ids'])
    if set(repaired)!=pending:raise ValueError('Correction task inventory changed')
    actual={**{k:v for k,v in original.items() if k not in pending},**repaired}
    for row in response['results']:
        if len(row['task_ids'])!=1 or actual.get(row['task_ids'][0])!=row['value']:
            raise ValueError('Reconciled source judgment was not actually returned')
