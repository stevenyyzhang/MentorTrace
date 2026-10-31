"""Bounded packet projection, exact evidence references and recoverable result checks."""
import copy
import hashlib
import json
from pathlib import Path


def require(ok, message):
    if not ok: raise ValueError(message)


def scoped_payload(base, items):
    """Project only with an explicit complete dependency assessment. Otherwise full."""
    payload = {**base, 'tasks': items}
    if any(t['kind'] == 'global_scope' for t in items):
        return payload
    scopes = base.get('packet_scopes', {})
    groups = {t['group'] for t in items}
    if not groups <= set(scopes) or any(scopes[g].get('status') != 'complete' for g in groups):
        payload['scope_mode'] = 'full_context_dependencies_not_bounded'
        return payload
    chosen = [scopes[g] for g in groups]
    require(all(s.get('reason') and s.get('reviewer') for s in chosen), 'Dependency scope needs actual reviewer and reason')
    contexts = {v for s in chosen for v in s.get('context_ids', [])}
    sources = {v for s in chosen for v in s.get('source_ids', [])}
    finals = {v for s in chosen for v in s.get('final_ids', [])}
    pages = {v for s in chosen for v in s.get('pages', [])}
    target_rows = base.get('all_target_inventory', [])
    source_rows = base.get('all_source_inventory', [])
    require(contexts <= {r['context_id'] for r in target_rows}, 'Unknown dependency context')
    require(sources <= {r['id'] for r in source_rows}, 'Unknown dependency source')
    require(finals <= set(base.get('final_targets', {})), 'Unknown dependency final finding')
    require(pages <= {p['page'] for p in base['manuscript']} and pages, 'Missing/unknown evidence pages')
    for t in items:
        if t['kind'] == 'target': require(t['data']['context_id'] in contexts, 'Assigned target context omitted')
        if t['kind'] == 'source_field': require(t['key'] in sources, 'Assigned source field omitted')
        if t['kind'] == 'coverage':
            c=t['data']['component']
            required_pages={e['page'] for e in c.get('evidence',[])+c.get('occurrences',[]) if 'page' in e}
            require(required_pages <= pages, 'Coverage evidence omitted')
            require(set(base.get('routes',{}).get(t['data']['source_id'],{}).get('final_ids',[])) <= finals, 'Coverage final routes omitted')
        if t['kind'] == 'language':
            require(set(t['data']['realization']['verified_ids']) <= finals, 'Expression dependencies omitted')
    report = base['report_text']
    rows = [copy.deepcopy(r) for r in target_rows if r['context_id'] in contexts]
    for r in rows:
        if 'text_span' in r:
            start,end=r.pop('text_span');r['text']=report[start:end]
    payload['all_target_inventory']=rows
    payload['report_text']='\n\n'.join(r['text'] for r in rows if 'text' in r)
    payload['report_context_scope']=sorted(contexts)
    payload['all_source_inventory']=[r for r in source_rows if r['id'] in sources]
    for r in payload['all_source_inventory']:
        if r.get('source_ref'): require(r['source_ref']['id'] in finals, 'Source reference target omitted')
    payload['final_targets']={k:v for k,v in base.get('final_targets',{}).items() if k in finals}
    required_sources={t['data']['source_id'] for t in items if t['kind']=='coverage'}
    payload['routes']={k:v for k,v in base.get('routes',{}).items()
                       if k in required_sources or set(v.get('final_ids',[])) & finals}
    for key in ['manuscript','manuscript_evidence','page_images']:
        payload[key]=[r for r in base.get(key,[]) if r['page'] in pages]
    payload.pop('carried_reviews',None)
    payload.pop('delivery_carryover',None)
    payload.pop('revision_actions',None)  # Assigned language task contains its complete action.
    payload['scope_mode']='explicit_dependency_projection'
    payload['scope_limits']='Bounded local review only. Separate global task retains the full report and inventories.'
    return payload


def load_scope(path, report_sha256, bindings):
    data=json.loads(Path(path).read_text(encoding='utf-8-sig'))
    require(data.get('report_sha256')==report_sha256, 'Stale packet dependency assessment')
    require(data.get('source_bindings')==bindings, 'Dependency source bindings differ')
    require(isinstance(data.get('groups'),dict), 'Missing dependency groups')
    return data['groups']


def inspect(tasks, values, context, evidence_records=()):
    """Collect mechanically decidable defects without editing judgments."""
    issues=[]; records={}
    for r in evidence_records:
        if r.get('id') in records:issues.append({'kind':'duplicate_evidence_record','id':r.get('id')})
        records[r.get('id')]=r.get('text','')
    page_text={p['page']:p['text'] for p in context.get('manuscript',[])}
    def walk(v,tid,path='',domain='manuscript'):
        if isinstance(v,list):
            for i,x in enumerate(v):walk(x,tid,f'{path}/{i}',domain)
        elif isinstance(v,dict):
            domain=v.get('domain',domain)
            if 'evidence_record' in v:
                text=records.get(v['evidence_record'])
                if text is None or not isinstance(v.get('quote'),str) or v['quote'] not in text:
                    issues.append({'task_id':tid,'field':path,'kind':'nonliteral_or_missing_evidence_record'})
            elif v.get('basis')=='manuscript' and 'page' in v:
                if not isinstance(v.get('quote'),str) or v['quote'] not in page_text.get(v['page'],''):
                    issues.append({'task_id':tid,'field':path,'kind':'nonliteral_page_quote'})
            allowed=__import__('review_contract').BASES.get(domain,set()) if context.get('delivery_hardening') else {'manuscript','direct_derivation'}
            if 'basis' in v and v['basis'] not in allowed:
                issues.append({'task_id':tid,'field':path,'kind':'unsupported_evidence_basis'})
            for k,x in v.items():walk(x,tid,path+'/'+k,domain)
    for t in tasks:
        if t['id'] not in values:
            issues.append({'task_id':t['id'],'kind':'missing_result'});continue
        v=values[t['id']]
        if t['kind']=='coverage':
            for quote in v.get('report_quotes',[]):
                if not isinstance(quote,str) or quote not in context.get('report_text',''):
                    issues.append({'task_id':t['id'],'kind':'nonliteral_report_quote'})
            route=context.get('routes',{}).get(t['data']['source_id'],{}).get('final_ids',[])
            for target in v.get('target_quotes',[]):
                if not isinstance(target,dict) or target.get('target_id') not in route:
                    issues.append({'task_id':t['id'],'kind':'target_outside_source_lineage'});continue
                text=context.get('final_targets',{}).get(target['target_id'],{}).get(target.get('field'))
                if not isinstance(text,str) or not isinstance(target.get('quote'),str) or target['quote'] not in text:
                    issues.append({'task_id':t['id'],'kind':'nonliteral_final_quote'})
        if t['kind']=='source_field':
            for component in v.get('components',[]):
                for quote in component.get('target_quotes',[]):
                    if not isinstance(quote,str) or quote not in context.get('report_text',''):
                        issues.append({'task_id':t['id'],'kind':'nonliteral_report_quote'})
        walk(values[t['id']],t['id'])
    return issues


def expand_evidence(value, records, pages):
    """Literal excerpts of actual response records or supplied manuscript text."""
    if isinstance(value,list):return [expand_evidence(v,records,pages) for v in value]
    if not isinstance(value,dict):return value
    if '$evidence_text' in value or '$page_text' in value:
        key='$evidence_text' if '$evidence_text' in value else '$page_text'
        require(set(value)=={key,'span'},'Malformed exact evidence reference')
        table={r['id']:r['text'] for r in records} if key=='$evidence_text' else {p['page']:p['text'] for p in pages}
        require(value[key] in table,'Unknown evidence reference')
        text=table[value[key]];span=value['span']
        require(isinstance(span,list) and len(span)==2 and all(type(n) is int for n in span),'Invalid evidence span')
        start,end=span;require(0<=start<end<=len(text),'Evidence span out of range')
        return text[start:end]
    return {k:expand_evidence(v,records,pages) for k,v in value.items()}


def resume_inventory(bundle, responses):
    """No submission: recover all actual available judgments and list pending work."""
    import review_workflow as w
    values,provenance=w.collect(bundle,responses,allow_partial=True)
    tasks=w.m.read(Path(bundle)/'inventory.json')
    issues=w.delivery_efficiency.inspect_values(tasks,values)
    pending={t['id'] for t in tasks if t['id'] not in values}|{i['task_id'] for i in issues}
    return {'values':values,'provenance':provenance,'pending_task_ids':sorted(pending),
            'issues':issues,'delivery_ready':False,'new_model_calls':0,
            'note':'Recovered judgments are not fresh reviews; ordinary semantic and delivery gates remain required.'}


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',required=True);p.add_argument('--responses',nargs='+',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();out=Path(a.out);require(not out.exists(),'Preserve earlier recovery')
    out.write_text(json.dumps(resume_inventory(a.bundle,a.responses),ensure_ascii=False,indent=2),encoding='utf-8')
