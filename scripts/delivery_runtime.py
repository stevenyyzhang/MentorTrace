"""Native dependency scopes, actual completion barrier and source-bound records.

Preparation never calls a model. Returned indexes establish provenance, not truth.
"""
import copy
import hashlib
import json
import re
import shutil
from pathlib import Path
import validation_cache


def digest(value): return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def require(ok, message):
    if not ok: raise ValueError(message)


def report_groups(rows):
    section='other';parent='opening';groups={};display={}
    for row in rows:
        text=row.get('text','')
        if text.startswith('## '):
            section=next((s for s in ['content','organization','language'] if text[3:].lower().startswith(s)),'other');parent=row['context_id']
        elif text.startswith('### '):parent=row['context_id']
        groups.setdefault(parent,set()).add(row['context_id'])
        match=re.match(r'^#{3,4}\s+(\d+)\.',text)
        if match:display[(section,int(match[1]))]=parent
    return groups,display


def language_contexts(draft,response,rows):
    """Whole coordinated groups, including action-only groups; never word snippets."""
    from review_integrity import normalize_section
    groups,display=report_groups(rows);contexts=set();wanted=set(draft['verified_ids']);found=set()
    for mapping in response.get('delivery_map',[]):
        if mapping['verified_id'] not in wanted:continue
        parent=display.get((normalize_section(mapping['report_section']),mapping['display_number']))
        if parent:contexts.update(groups[parent]);found.add(mapping['verified_id'])
    if found==wanted and contexts:return contexts
    # Old prose-only records may lack delivery maps. Preserve conservative fallback.
    texts=[p['text'] for p in draft.get('passages',[])]
    return {r['context_id'] for r in rows if any(t in r['text'] or r['text'] in t for t in texts)}


def dependency_scopes(base,tasks,semantic_dependencies):
    """Close explicit dependencies plus mechanical group/source/route relationships.

    A signed complete assessment is mandatory; missing semantic links fall back to full.
    """
    if not semantic_dependencies or semantic_dependencies.get('status')!='complete':return {}
    require(semantic_dependencies.get('reviewer') and semantic_dependencies.get('reason'),'Dependency assessment missing actual reviewer/reason')
    target={r['id']:r for r in base['all_target_inventory']};by_context={}
    for row in target.values():by_context.setdefault(row['context_id'],[]).append(row)
    groups,_=report_groups([{**r,'text':base['report_text'][slice(*r['text_span'])] if r.get('text_span') else r.get('text','')} for r in target.values()])
    context_parent={c:p for p,cs in groups.items() for c in cs}
    edges=semantic_dependencies.get('context_dependencies',{});require(set(edges)<=set(by_context) and all(set(v)<=set(by_context) for v in edges.values()),'Unknown semantic dependency context')
    source_rows={r['id']:r for r in base['all_source_inventory']};all_finals=set(base['final_targets']);all_pages={p['page'] for p in base['manuscript']};scopes={}
    for group in {t['group'] for t in tasks if t['kind']!='global_scope'}:
        selected=[t for t in tasks if t['group']==group];contexts=set();sources=set();finals=set();pages=set()
        for t in selected:
            if t['kind']=='target':contexts.add(t['data']['context_id'])
            elif t['kind']=='source_field':sources.add(t['key'])
            elif t['kind']=='coverage':
                finals.update(base['routes'][t['data']['source_id']]['final_ids'])
                pages.update(e['page'] for e in t['data']['component'].get('evidence',[])+t['data']['component'].get('occurrences',[]) if 'page' in e)
            elif t['kind']=='language':finals.update(t['data']['realization']['verified_ids'])
        # A group's target tasks establish its coordinated report location. Without
        # such a location use the caller's source-bound semantic context links.
        contexts.update(semantic_dependencies.get('group_contexts',{}).get(group,[]))
        require(contexts<=set(by_context),'Unknown group dependency context')
        while True:
            old=set(contexts)
            for c in old:
                contexts.update(groups[context_parent[c]]);contexts.update(edges.get(c,[]))
            if contexts==old:break
        for sid,row in source_rows.items():
            ref=row.get('source_ref',{})
            if ref.get('id') in finals:sources.add(sid)
        for sid in sources:
            ref=source_rows[sid].get('source_ref',{})
            if ref:finals.add(ref['id'])
        for fid in list(finals):
            f=base['final_targets'][fid]
            def anchors(v):
                if isinstance(v,dict):
                    if 'page' in v and isinstance(v['page'],int):pages.add(v['page'])
                    for x in v.values():anchors(x)
                elif isinstance(v,list):
                    for x in v:anchors(x)
            anchors(f)
        # No partial projection without an actual report context and evidence pages.
        if not contexts or not pages:continue
        require(finals<=all_finals and pages<=all_pages,'Dependency closure references absent evidence')
        scopes[group]={'status':'complete','reviewer':semantic_dependencies['reviewer'],'reason':semantic_dependencies['reason'],
            'context_ids':sorted(contexts),'source_ids':sorted(sources),'final_ids':sorted(finals),'pages':sorted(pages)}
    return scopes


def provenance_index(origins):
    records={};tasks={}
    for origin in origins:
        compact={k:v for k,v in origin.items() if k!='task_ids'};key=digest(compact)
        records[key]=compact
        for tid in origin['task_ids']:tasks[tid]={'review_id':key}
    return {'records':records,'tasks':tasks}


def expand_provenance(reference,index):
    require(set(reference)=={'review_id'} and reference['review_id'] in index,'Missing review provenance')
    return copy.deepcopy(index[reference['review_id']])


def bind_global(bundle,paths,out):
    """Derive the dependent global request only from actual checked local outputs."""
    import mentortrace_v1 as m
    import review_workflow as w
    import review_contract as contract
    bundle=Path(bundle);manifest=w.verify_bundle(bundle);ctx=m.read(bundle/'context.json');inventory=m.read(bundle/'inventory.json')
    values,origins=w.collect(bundle,paths,allow_partial=True);local=[t for t in inventory if t['kind']!='global_scope']
    issues=contract.inspect(local,values,ctx)+w.delivery_efficiency.inspect_values(local,values)
    for path in paths:
        result=m.read(path);req=m.read(bundle/next(p['file'] for p in manifest['packets'] if p['id']==result['packet_id']))
        assigned=[t for t in local if t['id'] in req['task_ids']]
        issues+=w.recovery.inspect(assigned,values,ctx,result.get('evidence_records',[]))
    require(not issues,'Local results cannot release global barrier: '+json.dumps(issues,ensure_ascii=False))
    out=Path(out);signature=digest({'manifest':m.sha(bundle/'manifest.json'),'local_files':{str(Path(p).resolve()):m.sha(p) for p in paths},
        'handoff_rules':{name:m.sha(Path(__file__).parent/name) for name in ['delivery_runtime.py','review_workflow.py','lossless_delivery_wire.py']}});derived=out/signature[:20]
    if derived.exists():w.verify_bundle(derived);return derived
    ctx['completed_local_reviews']={
        'actual_values':{t['id']:copy.deepcopy(values[t['id']]) for t in local},
        'evidence_by_response':[{ 'path':str(Path(p).resolve()),'sha256':m.sha(p),
                                 'evidence_records':m.read(p).get('evidence_records',[])} for p in paths],
        'language':{k:v for k,v in values.items() if k.startswith('language:')},
        'completion_index':[{ 'task_id':t['id'],'kind':t['kind'],'actual_value_sha256':digest(values[t['id']]),'record_check':'valid','semantic_certification':False} for t in local],
        'provenance':provenance_index(origins),
        'scope':'Actual local completions, not automatic passes or independent rediscovery. Granular scientific/source judgments retain original provenance; global checks full report coherence, scope, conflicts and completeness.'}
    require(set(ctx['completed_local_reviews']['actual_values'])=={t['id'] for t in local},'Actual local judgment body omitted')
    prepared_requests={}
    for entry in manifest['packets']:
        request=m.read(bundle/entry['file'])
        if not any(t['kind']=='global_scope' and t['id'] in request['task_ids'] for t in inventory):continue
        require(len(request['task_ids'])==1,'Global tasks must have a separate dependent packet')
        # Keep the prepared complete global input, append actual completion records
        # with exact compact references; never trim evidence to force a fit.
        if ctx.get('delivery_compact'):
            import delivery_protocol
            tasks=[t for t in inventory if t['id'] in request['task_ids']]
            request['prompt']=w.encoded_request(delivery_protocol.instructions(tasks,ctx),delivery_protocol.project(ctx,tasks))
        else:request['prompt']+='\nBOUND ACTUAL LOCAL COMPLETIONS\n'+__import__('request_capacity').encode(ctx['completed_local_reviews'])
        request['request_sha256']=hashlib.sha256(request['prompt'].encode()).hexdigest()
        w.capacity.check_capacity(request['prompt'],len(request['images']),manifest['policy'])
        prepared_requests[entry['file']]=request;entry['sha256']=w.audit.value_digest(request)
    # Preflight all complete requests before creating a frozen bundle. A capacity
    # failure must not leave a corrupt resume target that needs manual reconstruction.
    shutil.copytree(bundle,derived)
    m.save(derived/'context.json',ctx)
    for name,request in prepared_requests.items():m.save(derived/name,request)
    manifest['context_sha256']=m.sha(derived/'context.json')
    for p in paths:manifest['bindings'][str(Path(p).resolve())]=m.sha(p)
    m.save(derived/'manifest.json',manifest);w.verify_bundle(derived)
    m.save(derived/'completion_barrier.json',{'source_bundle':str(bundle.resolve()),'signature':signature,'local_response_paths':[str(p) for p in paths],'new_model_calls':0})
    return derived


def coverage_carryover(previous_b,previous_report,report,safe_context_texts,affected_component_ids=()):
    """Retain actual complete B rows only when their frozen routes/quotes still bind."""
    import audit_merge_obligations as audit
    previous_b=Path(previous_b);ledger=audit.read(previous_b);packet=audit.read(Path(ledger['audit_directory'])/'phase_b.packet.json')
    require(ledger['report']['sha256']==audit.digest(previous_report),'Previous B report changed')
    require(audit.value_digest(packet)==ledger['phase_b_packet_sha256'],'Previous B packet changed')
    current=Path(report).read_text(encoding='utf-8-sig');frozen={c['id']:(u['source_id'],c) for u in packet['frozen_adjudication']['units'] for c in u['components']};result=[]
    for row in ledger['components']:
        cid=row['component_id']
        if cid in affected_component_ids:continue
        sid,component=frozen[cid];status=row.get('status');assessment=component['assessment']
        if not row.get('reason'):continue
        if assessment in {'duplicate','already_answered','unsupported'}:
            valid=status=='not_required' and not row['target_quotes'] and not row['report_quotes']
        elif status=='kept' and assessment in {'required','optional'}:
            valid=bool(row['target_quotes']) and bool(row['report_quotes']) and all(q in current and any(q in t for t in safe_context_texts) for q in row['report_quotes'])
            for q in row['target_quotes']:
                valid=valid and q['target_id'] in packet['routes'][sid]['final_ids'] and q['quote'] in audit.target_text(packet['final_targets'][q['target_id']],q['field'])
        elif assessment=='optional' and status=='missing' and audit.digest(previous_report)==audit.digest(report):
            valid=not row['target_quotes'] and not row['report_quotes']
        else:valid=False  # Unknown/optional exclusions need fresh explicit visibility/selection checks.
        if valid:
            valid=audit.substantial(row['reason']) and all(audit.substantial(q) for q in row['report_quotes']) and all(audit.substantial(q['quote']) for q in row['target_quotes'])
        if valid:result.append(copy.deepcopy(row))
    return {'previous_b':str(previous_b.resolve()),'sha256':audit.digest(previous_b),'phase_a_sha256':ledger['phase_a_sha256'],
            'rows':result,'scope':'Reuse actual unchanged complete B judgments with valid source lineage; no new semantic review.'}


def prepare_repair(bundle,responses,out,scope_plan=None):
    """Pure preparation: one canonical bundle for all actually pending local tasks."""
    import mentortrace_v1 as m
    import review_workflow as w
    import review_contract as contract
    bundle=Path(bundle);manifest=w.verify_bundle(bundle);ctx=m.read(bundle/'context.json');tasks=m.read(bundle/'inventory.json')
    values,origins=w.collect(bundle,responses,allow_partial=True)
    issues=contract.inspect(tasks,values,ctx)+w.delivery_efficiency.inspect_values(tasks,values)
    for p in responses:
        r=m.read(p);ids=m.read(bundle/next(x['file'] for x in manifest['packets'] if x['id']==r['packet_id']))['task_ids']
        issues+=w.recovery.inspect([t for t in tasks if t['id'] in ids],values,ctx,r.get('evidence_records',[]))
    pending={t['id'] for t in tasks if t['id'] not in values}|{i['task_id'] for i in issues}
    selected=[t for t in tasks if t['id'] in pending and t['kind']!='global_scope']
    require(selected,'No local repair task; use actual global barrier or ordinary assembly')
    if scope_plan:
        ledger=m.read(ctx['ledger_path'])
        ctx['packet_scopes']=w.recovery.load_scope(scope_plan,ledger['report_sha256'],{s['path']:s['sha256'] for s in ledger['sources']})
    result=w.prepare_bundle(out,'delivery',ctx,selected,manifest['bindings'],manifest['policy'])
    m.save(Path(out)/'repair_origin.json',{'source_bundle':str(bundle.resolve()),'source_manifest_sha256':m.sha(bundle/'manifest.json'),
        'actual_review_origins':origins,'pending_task_ids':[t['id'] for t in selected],'issues':issues,'new_model_calls':0,
        'assembly':'Repair outputs remain distinct actual requests. Use their checked results through a partial checkpoint/delta; never relabel them as original packet outputs.'})
    return result


def comparison_dispositions(rows):
    """Keep comparison categories separate; no lexical inference of correctness."""
    result=[]
    for row in rows:
        value=copy.deepcopy(row)
        if row.get('requirement_kind')=='workflow_instruction':value['comparison_status']='not_manuscript_requirement'
        elif row.get('action_present') is True and row.get('difference')=='priority_or_optional_status':value['comparison_status']='covered_with_status_difference'
        else:value['comparison_status']=row['decision']
        result.append(value)
    return result


def bind_history(independent_freeze,history,report,dispositions,reviewer,requirements):
    """Explicit post-freeze source for an integrated revision, not blind discovery."""
    import mentortrace_v1 as m
    freeze=m.read(independent_freeze)
    require(m.sha(freeze['report'])==freeze['report_sha256'],'Independent report changed before history binding')
    require(requirements.get('source')=={'path':str(Path(history).resolve()),'sha256':m.sha(history)},'Historical inventory belongs to another source')
    expected={r['id'] for r in requirements['requirements']};actual=[r.get('id') for r in dispositions]
    require(len(expected)==len(requirements['requirements']) and len(actual)==len(set(actual)) and set(actual)==expected,'Historical requirement accounting mismatch')
    require(reviewer and all(r.get('reason') and r.get('decision') in {'covered','recovered','rejected_with_evidence','unresolved','optional_excluded','not_manuscript_requirement'} for r in dispositions),'History requirements need explicit dispositions')
    for row in dispositions:
        require(row['decision'] not in {'rejected_with_evidence','optional_excluded'} or row.get('evidence'),'Historical exclusion needs concrete evidence')
        require(row['decision']!='optional_excluded' or not row.get('required'),'Required history cannot be silently downgraded')
    require(not any(r.get('decision')=='unresolved' and r.get('required') for r in dispositions),'Required historical omission blocks replacement approval')
    return {'independent_freeze':{'path':str(Path(independent_freeze).resolve()),'sha256':m.sha(independent_freeze)},
        'historical_source':{'path':str(Path(history).resolve()),'sha256':m.sha(history)},
        'integrated_report':{'path':str(Path(report).resolve()),'sha256':m.sha(report)},'dispositions':dispositions,'reviewer':reviewer,
        'requirements':requirements,'status':'requires_changed-text_and_dependency_review','independent_discovery':False}


def historical_source(binding):
    """Additional preservation input, never an initial-review prompt or Original quote."""
    dispositions={r['id']:r for r in binding['dispositions']};findings=[];organization=[]
    for requirement in binding['requirements']['requirements']:
        d=dispositions[requirement['id']]
        if d['decision'] in {'not_manuscript_requirement','rejected_with_evidence','optional_excluded'}:continue
        require(requirement.get('old_quote') and requirement.get('requirement'),'Historical obligation needs exact old excerpt and explicit requirement')
        row={'id':'history:'+requirement['id'],'relation':requirement['requirement'],
             'closure_goal':requirement.get('author_action',requirement['requirement']),
             'conditions':requirement.get('condition','Preserve original applicable scope and optional status.'),
             'reason':{'old_report_excerpt':requirement['old_quote'],'disposition':d['decision'],
                       'source':binding['historical_source'],'not_manuscript_original':True}}
        (organization if requirement.get('kind')=='organization' else findings).append(row)
    return {'findings':findings,'organization_suggestions':organization,'provenance':binding}


def validate_history_delivery(ledger,report):
    import mentortrace_v1 as m
    binding=ledger.get('history_binding')
    if not binding:return
    require(binding['integrated_report']=={'path':str(Path(report).resolve()),'sha256':m.sha(report)},'Historical integrated report changed')
    source=binding.get('additional_preservation_source')
    require(source and source in ledger['sources'] and m.sha(source['path'])==source['sha256'],'Historical requirements are not a bound preservation source')
    require(m.sha(binding['historical_source']['path'])==binding['historical_source']['sha256'],'Historical report changed')
    freeze=m.read(binding['independent_freeze']['path'])
    require(m.sha(binding['independent_freeze']['path'])==binding['independent_freeze']['sha256'] and m.sha(freeze['report'])==freeze['report_sha256'],'Independent freeze changed')
    review=ledger.get('history_change_review',{})
    require(review.get('status')=='completed' and review.get('reason') and review.get('issues')==[],
            'Historical integration needs an actual changed-text/bilingual/dependency review')


def main():
    import argparse
    import mentortrace_v1 as m
    from review_integrity import safe_patch
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    repair=commands.add_parser('repair');repair.add_argument('--bundle',type=Path,required=True);repair.add_argument('--responses',nargs='+',type=Path,required=True);repair.add_argument('--out',type=Path,required=True)
    patch=commands.add_parser('patch');patch.add_argument('--response',type=Path,required=True);patch.add_argument('--edits',type=Path,required=True);patch.add_argument('--out',type=Path,required=True)
    history=commands.add_parser('history-bind')
    for name in ['freeze','history','report','requirements','dispositions','out']:history.add_argument('--'+name,type=Path,required=True)
    history.add_argument('--reviewer',required=True)
    args=parser.parse_args();require(not args.out.exists(),'Preserve existing prepared output')
    if args.command=='repair':result=prepare_repair(args.bundle,args.responses,args.out);print(json.dumps(result));return
    if args.command=='patch':
        result=safe_patch(m.read(args.response),m.read(args.edits));args.out.mkdir(parents=True)
        m.save(args.out/'response.json',result);(args.out/'report_bilingual.md').write_text(result['report_markdown'],encoding='utf-8')
        m.save(args.out/'patch_provenance.json',{'source':str(args.response.resolve()),'source_sha256':m.sha(args.response),
            'edits':m.read(args.edits),'status':'requires_affected_review','new_model_calls':0});return
    binding=bind_history(args.freeze,args.history,args.report,m.read(args.dispositions),args.reviewer,m.read(args.requirements))
    args.out.mkdir(parents=True);m.save(args.out/'history_obligations.json',historical_source(binding));binding['additional_preservation_source']={'path':str((args.out/'history_obligations.json').resolve()),'sha256':m.sha(args.out/'history_obligations.json')}
    m.save(args.out/'history_binding.json',binding)
    print('Prepared history source. Include it in the ordinary preservation ledger, set history_binding, and review changed text/dependencies; not deliverable yet.')


if __name__=='__main__':main()
