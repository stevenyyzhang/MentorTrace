"""Source-bound report transactions and automatic affected-scope preparation.

This module creates no scientific verdict. Actual model revisions remain subject to
all existing local, global, preservation and frozen-A comparison gates.
"""
import copy
import hashlib
import json
import shutil
from pathlib import Path
import mentortrace_v1 as m
import canonical_draft as canonical
import review_workflow as w
import prepare_delivery_delta as delta
import request_capacity

INSTRUCTION = '''Repair the current report from ALL supplied actual defects in one transaction.
Return JSON {replacements:[complete canonical v2 groups],semantic_dependencies:{
status:"complete|uncertain",reviewer,reason,reviewed_group_ids:[],affected_group_ids:[],
edges:[{from,to,reason}]},original_repairs:[]}.
Read the complete current report and frozen requirements. Return only changed groups.
Preserve group IDs, all opinion/requirement/candidate IDs and their ownership, independent
requests, optionality and author unknowns. Never invent facts to obtain acceptance.
Each changed group updates its seven owned lists together. List each action's own
condition and changed assertions with actual evidence. If a global concern affects
other groups, include those dependencies even when their wording is unchanged.
reviewed_group_ids accounts for all groups for cross-context dependency assessment;
uncertain means conservative full invalidation, never an invented complete graph.
Original stays verbatim. Only an actual quotation defect permits original_repairs:
[{group_id,old,new,page,reason}]; new must be an exact supplied manuscript text span.
A symbol not reliably represented in extracted text remains an explicit source issue,
not a guessed transcription. Do not relabel an unchanged failed report as accepted.
Write direct, concrete bilingual mentor comments; remove defensive caveats that add no
condition or author action. Preserve scientific qualifications and separate style
alignment from a claim of superior writing. No added independent review lane.
''' + canonical.INSTRUCTIONS_V2


def save_once(path, value):
    path=Path(path)
    if path.exists():m.require(m.read(path)==value,'Saved native transaction changed: '+str(path))
    else:m.save(path,value)


def group_contexts(response, rows):
    from delivery_runtime import language_contexts
    result={}
    for g in response['report_fragments']:
        located=language_contexts({'verified_ids':g['verified_ids'],'passages':[{'text':g['text']}]},response,rows)
        located|={r['context_id'] for r in rows if r['kind']=='block' and r['text'].strip() and r['text'].strip() in g['text']}
        result[g['group_id']]=located
    return result


def affected_groups(before, after, semantic, final):
    old={g['group_id']:g for g in before['report_fragments']};new={g['group_id']:g for g in after['report_fragments']}
    m.require(set(old)==set(new),'Group inventory changed')
    changed={i for i in old if old[i]!=new[i]}
    m.require(changed,'No progress: report transaction unchanged')
    known=set(new)
    m.require(semantic.get('status') in {'complete','uncertain'} and semantic.get('reviewer') and semantic.get('reason'),'Dependency assessment absent')
    m.require(set(semantic.get('reviewed_group_ids',[]))==known,'Cross-context group assessment incomplete')
    affected=set(semantic.get('affected_group_ids',[]))|changed
    m.require(affected<=known,'Unknown affected group')
    edges=[]
    for e in semantic.get('edges',[]):
        m.require(e.get('from') in known and e.get('to') in known and e.get('reason'),'Invalid semantic dependency')
        edges.append((e['from'],e['to']))
    # Shared frozen requirements couple groups even if a model forgets the edge.
    owner={}
    for i,g in new.items():
        for v in g['verified_ids']+g.get('candidate_ids',[]):owner.setdefault(v,set()).add(i)
    for owners in owner.values():edges.extend((a,b) for a in owners for b in owners if a!=b)
    for row in final.get('source_requirement_resolutions',[]):
        ids=set().union(*(owner.get(x,set()) for x in row.get('output_ids',[])))
        edges.extend((a,b) for a in ids for b in ids if a!=b)
    for i,g in new.items():
        linked=set(g.get('depends_on',[]))|{v for r in g['delivery']['requirement_delivery'] for v in r.get('quote_group_ids',[])}
        for other in linked:
            m.require(other in known,'Unknown mechanical dependency');edges.extend([(i,other),(other,i)])
    if semantic['status']=='uncertain':affected=known
    while True:
        expanded=affected|{b for a,b in edges if a in affected}
        if expanded==affected:break
        affected=expanded
    return changed,affected


def apply_revision(before, value, manuscript):
    replacements=canonical.expand_wire({'report_fragments':value['replacements']})['report_fragments']
    errors=[]
    for g in replacements:
        for check in [canonical.validate_action_bindings,canonical.validate_related]:
            try:check(g)
            except (ValueError,KeyError,TypeError) as exc:errors.append({'group_id':g.get('group_id'),'check':check.__name__,'error':str(exc)})
    m.require(not errors,'Atomic group defects: '+json.dumps(errors,ensure_ascii=False))
    # Normal transactions prohibit changes to Original. Separately evidenced literal
    # repairs are applied to a temporary base first, then the same transaction gate.
    base=copy.deepcopy(before)
    repairs=value.get('original_repairs',[])
    if repairs:
        from review_integrity import _original_ranges
        pages=manuscript.get('pages',[]) if isinstance(manuscript,dict) else manuscript
        text_by_page={p.get('page',p.get('page_number')):p.get('text','') for p in pages}
        for repair in repairs:
            group=next((g for g in base['report_fragments'] if g['group_id']==repair.get('group_id')),None)
            m.require(group is not None and repair.get('reason') and repair.get('old') and repair.get('new'), 'Quotation repair incomplete')
            m.require(repair['new'] in text_by_page.get(repair.get('page'),''),'Quotation repair lacks literal manuscript evidence')
            ranges=[(a.end(),b.start() if b else len(group['text'])) for a,b in _original_ranges(group['text'])]
            m.require(any(repair['old'] in group['text'][a:b] for a,b in ranges),'Quotation repair outside Original')
            for a,b in reversed(ranges):
                group['text']=group['text'][:a]+group['text'][a:b].replace(repair['old'],repair['new'])+group['text'][b:]
        for k in (*canonical.fields_for(base['canonical_draft']),'report_markdown','canonical_groups_sha256'):base.pop(k,None)
        base=canonical.compile(base)
    after=canonical.replace_groups(base,replacements,canonical.digest(base))
    after['draft_transaction']['base_sha256']=canonical.digest(before)
    after['draft_transaction']['original_repairs']=copy.deepcopy(repairs)
    return after


def validate_revision(response, final, evidence, manuscript):
    import review_integrity, writing_transfer
    errors=[]
    checks=[('canonical',lambda:canonical.validate(response)),
            ('requirements',lambda:review_integrity.draft_requirements(final,response)),
            ('proposals_and_realization',lambda:writing_transfer.validate_proposals(response,writing_transfer.draft_view(evidence),final,manuscript,m.anchor))]
    for name,check in checks:
        try:check()
        except (ValueError,KeyError,TypeError) as exc:errors.append({'check':name,'error':str(exc)})
    m.require(not errors,'Revision local checks: '+json.dumps(errors,ensure_ascii=False))


def defect_values(values,failures):
    ids=set()
    def scan(value):
        if isinstance(value,dict):
            if value.get('task_id'):ids.add(value['task_id'])
            for x in value.values():scan(x)
        elif isinstance(value,list):
            for x in value:scan(x)
    scan(failures)
    def negative(value):
        if isinstance(value,dict):
            return value.get('status') in {'fail','rejected','missing','lost','unsupported'} or bool(value.get('issues')) or any(negative(x) for x in value.values())
        if isinstance(value,list):return any(negative(x) for x in value)
        return False
    return {k:v for k,v in values.items() if k in ids or negative(v)}


def prepare(bundle,responses,out,failures):
    import delivery_cycle
    out=Path(out).resolve();bundle=Path(bundle).resolve()
    manifest=w.verify_bundle(bundle);ctx=m.read(bundle/'context.json')
    binding={'bundle':str(bundle),'manifest_sha256':m.sha(bundle/'manifest.json'),
             'responses':{str(Path(p).resolve()):m.sha(p) for p in responses},'failures':failures}
    out.mkdir(parents=True,exist_ok=True);save_once(out/'binding.json',binding)
    for failure in failures:
        for view in failure.get('actual_global_views',[]):m.require(m.sha(view['path'])==view['sha256'] and m.read(view['path'])==view['actual_review'],'Actual global view changed')
    request_path=out/'request.json'
    if request_path.exists():
        m.verify_frozen(out/'inputs');return request_path
    cp=delivery_cycle.checkpoint(bundle,responses,out/'checkpoint')
    previous=m.read(cp);lang=previous.get('language_realization',{})
    m.require(lang.get('response') and lang.get('evidence'),'Native repair requires bound draft and writing evidence')
    for ref in [lang['response'],lang['evidence']]:m.require(m.sha(ref['path'])==ref['sha256'],'Repair source changed')
    before=m.read(lang['response']['path'])
    if before.get('canonical_draft')!=2:before=canonical.adopt(before)
    canonical.validate(before)
    package,snapshot=w.audit.verify_package(ctx['audit_directory'])
    final=m.read(Path(package['run'])/'final.json')
    values,_=w.collect(bundle,responses,allow_partial=True)
    selected=defect_values(values,failures)
    evidence_records=[{'path':str(p),'sha256':m.sha(p),'evidence_records':m.read(p).get('evidence_records',[])} for p in responses if any(tid in selected for row in m.read(p).get('results',[]) for tid in row.get('task_ids',[]))]
    payload={'current_draft':canonical.compact_wire(before),'actual_defect_judgments':selected,'actual_defect_evidence':evidence_records,'failures':failures,
             'verified_review':final,'writing_evidence':m.read(lang['evidence']['path']),
             'manuscript':ctx['manuscript'],'frozen_a':ctx['frozen_a']}
    # Full source scope is intentionally retained for this cross-context repair.
    inputs=out/'inputs';inputs.mkdir(exist_ok=True)
    save_once(inputs/'before.json',before);save_once(inputs/'payload.json',payload)
    save_once(inputs/'context.json',ctx);save_once(inputs/'policy.json',manifest['policy'])
    save_once(inputs/'origin.json',{'checkpoint':str(cp),'checkpoint_sha256':m.sha(cp),'language':lang,'bindings':manifest['bindings']})
    m.freeze(inputs)
    req={'stage':'report_revision','prompt':w.encoded_request(INSTRUCTION,payload), 'images':ctx['page_images'],'tools_allowed':False}
    request_capacity.preflight(req,manifest['policy'],out/'preflight.json')
    save_once(request_path,req)
    return request_path


def submit(out,args,authorization):
    import run_authorized_stage as runner, codex_adapter
    from execution_policy import validate_authorization
    out=Path(out);m.verify_frozen(out/'inputs')
    validate_authorization(authorization,args.model,args.effort,args.service_tier)
    req=m.read(out/'request.json');payload=m.read(out/'inputs/payload.json')
    m.require(req['prompt']==w.encoded_request(INSTRUCTION,payload) and req['images']==m.read(out/'inputs/context.json')['page_images'],'Native revision request changed')
    policy=m.read(out/'inputs/policy.json')
    m.require((args.model,args.effort)==(policy['model'],policy['effort']),'Repair settings changed')
    request_capacity.preflight(req,policy)
    origin=m.read(out/'inputs/origin.json')
    m.require(m.sha(origin['checkpoint'])==origin['checkpoint_sha256'],'Revision checkpoint changed')
    for path,sha in origin['bindings'].items():m.require(m.sha(path)==sha,'Frozen repair dependency changed')
    before=m.read(out/'inputs/before.json');payload=m.read(out/'inputs/payload.json')
    error=None
    for wave in range(2):
        active=copy.deepcopy(req)
        if wave:
            active['prompt']=req['prompt']+'\nLOCAL OUTPUT CORRECTION (same transaction, no new review):\n'+json.dumps({'saved_output':value,'all_detected_error':error},ensure_ascii=False)
        calls=out/('calls' if wave==0 else 'format-correction')
        cached=runner.find_cached(calls,active,args.model,args.effort,args.service_tier)
        if cached:raw,_=cached
        else:
            attempt=calls/args.attempt_name
            m.require(not attempt.exists(),'Uncertain prior repair submission; reconcile saved output before retry')
            images=[Path(i['path']) for i in active['images']]
            for path,item in zip(images,active['images']):m.require(m.sha(path)==item['sha256'],'Repair image changed')
            request_capacity.preflight(active,policy)
            raw,_=codex_adapter.invoke(attempt,active['prompt'],images,model=args.model,reasoning_effort=args.effort,service_tier=args.service_tier,settings_authorization=authorization,context_window=policy['context_window'])
        runner.validate_cached(m.read(Path(raw).parent/'audit.json'),active,args.model,args.effort,args.service_tier,raw)
        value=None
        try:
            value=m.read(raw)
            after=apply_revision(before,value,payload['manuscript'])
            changed,affected=affected_groups(before,after,value['semantic_dependencies'],payload['verified_review'])
            validate_revision(after,payload['verified_review'],payload['writing_evidence'],payload['manuscript'])
        except (ValueError,KeyError,TypeError) as exc:
            if value is None:value={'invalid_json':Path(raw).read_text(encoding='utf-8-sig')}
            error=str(exc);save_once(out/('local-error-'+str(wave)+'.json'),{'raw':str(raw),'sha256':m.sha(raw),'error':error})
            if wave:raise
            continue
        save_once(out/'transaction.json',{'raw':str(raw),'sha256':m.sha(raw),'changed_groups':sorted(changed),'affected_groups':sorted(affected),'semantic_dependencies':value['semantic_dependencies'],'schema_corrections':wave,'response_value_sha256':canonical.digest(after)})
        save_once(out/'response.json',after)
        report=out/'report_bilingual.md'
        if report.exists():m.require(report.read_text(encoding='utf-8')==after['report_markdown'],'Saved revised report changed')
        else:report.write_text(after['report_markdown'],encoding='utf-8')
        return after


def recheck(out):
    out=Path(out).resolve();m.verify_frozen(out/'inputs')
    origin=m.read(out/'inputs/origin.json');ctx=m.read(out/'inputs/context.json');policy=m.read(out/'inputs/policy.json')
    transaction=m.read(out/'transaction.json');m.require(m.sha(transaction['raw'])==transaction['sha256'],'Revision output changed')
    before=m.read(out/'inputs/before.json');after=m.read(out/'response.json');report=out/'report_bilingual.md'
    m.require(canonical.digest(after)==transaction['response_value_sha256'],'Applied revision differs from actual transaction')
    canonical.validate(after);m.require(report.read_text(encoding='utf-8')==after['report_markdown'],'Revision report changed')
    payload=m.read(out/'inputs/payload.json');validate_revision(after,payload['verified_review'],payload['writing_evidence'],payload['manuscript'])
    _,affected=affected_groups(before,after,transaction['semantic_dependencies'],payload['verified_review'])
    previous=m.read(origin['checkpoint']);rows=w.preservation.target_inventory(report)
    contexts=group_contexts(after,rows)
    # Missing structural mapping cannot justify selective reuse.
    selected=set().union(*(contexts[g] for g in affected))
    if any(not contexts[g] for g in affected):selected={r['context_id'] for r in rows}
    component_ids={r['component_id'] for g in after['report_fragments'] if g['group_id'] in affected for r in g['delivery']['requirement_delivery']}
    affected_final={v for g in after['report_fragments'] if g['group_id'] in affected for v in g['verified_ids']}
    affected_sources={sid for sid,route in ctx['routes'].items() if set(route['final_ids'])&affected_final}
    source_ids=[r['id'] for r in previous['units'] if any(json.dumps(sid) in r.get('text','') for sid in affected_sources|affected_final)]
    # Quote mappings and target contexts are independently invalidated by delta too.
    b=Path(origin['checkpoint']).parent/'checkpoint_phase_b.json'
    assessment={'previous_ledger_sha256':m.sha(origin['checkpoint']),'report_sha256':m.sha(report),
        'reviewer':transaction['semantic_dependencies']['reviewer'],'reason':transaction['semantic_dependencies']['reason'],
        'cross_context_review':json.dumps(transaction['semantic_dependencies'],ensure_ascii=False),
        'affected_target_ids':[r['id'] for r in rows if r['context_id'] in selected],
        'affected_source_ids':source_ids,'affected_component_ids':sorted(component_ids),
        'language_response':{'path':str(out/'response.json'),'sha256':m.sha(out/'response.json')},
        'previous_phase_b':{'path':str(b),'sha256':m.sha(b)}}
    fresh,pending=delta.prepare(origin['checkpoint'],previous['report'],report,assessment=assessment)
    save_once(out/'delta.json',fresh);save_once(out/'pending.json',pending)
    audit_dir=out/'audit'
    if not audit_dir.exists():
        old=Path(ctx['audit_directory']);audit_dir.mkdir()
        for name in ['package.json','phase_a.packet.json','phase_a.template.json','phase_a.adjudicated.json','phase_a.freeze.json','schema.json','instructions.md']:
            shutil.copyfile(old/name,audit_dir/name)
        shutil.copytree(old/'phase_a.batches',audit_dir/'phase_a.batches')
    if not (audit_dir/'phase_b.packet.json').exists():w.audit.compare(audit_dir,report)
    bundle=out/'recheck'
    if not bundle.exists():
        contract=ctx.get('delivery_contract',{})
        w.prepare_delivery(audit_dir,out/'delta.json',bundle,policy,fidelity=contract.get('verified_delivery_fidelity',False),concise=contract.get('report_concision',False),recoverable=True)
    w.verify_bundle(bundle)
    return bundle
