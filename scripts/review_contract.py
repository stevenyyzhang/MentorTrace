"""One delivery contract for ordinary, resumed and bounded requests. No calls/judgments."""
import copy
import json

VERSION = 1
DOMAINS = {'manuscript', 'review_execution', 'report_correspondence'}
BASES = {'manuscript': {'manuscript', 'direct_derivation'},
         'review_execution': {'execution_record'}, 'report_correspondence': {'report_structure'}}
TEXT_FIELDS = ('reason', 'meaning_check', 'style_check')


def contract(tasks):
    """Machine-readable required fields; the same table drives inspection/prompting."""
    kinds = {t['kind'] for t in tasks}
    shapes = {
        'target': {'block': ['classification', *TEXT_FIELDS, 'assertions'],
                   'suggested_wording': [*TEXT_FIELDS, 'assertion_completeness'],
                   'assertion': {'required': ['quote', 'status', 'reason', 'domain'],
                       'status': ['supported', 'conditional', 'unresolved', 'reused_verified'],
                       'domains_and_evidence_bases': {k: sorted(v) for k, v in BASES.items()}}},
        'source_field': {'allowed': ['components', 'non_substantive_reason'],
                         'rule': 'substantive components XOR non-substantive reason'},
        'coverage': {'required': ['status', 'reason', 'target_quotes', 'report_quotes'],
                     'rule': 'Respect frozen assessment and each source-specific final-ID lineage'},
        'language': {'required': ['meaning', 'naturalness', 'feature_results'],
                     'rule': 'Each meaning/naturalness needs status and reason; nonuse_results is separate'},
        'global_scope': {'required': ['source_completeness', 'assertion_completeness', 'semantic_review', 'reason', 'issues'],
                         'rule': 'Inspect actual bound local completions; no inferred acceptance'}}
    return {'version': VERSION, 'reviewer_limits_type': 'string',
            'values': {k: shapes[k] for k in sorted(kinds & set(shapes))},
            'evidence_record': {'required': ['id', 'text'],
                'binding': 'numeric source_pages OR source_ref from supplied evidence_source_refs OR supplied source_paths + matching source_sha256s'},
            'semantics': 'Types/references are mechanical. No missing judgment may be invented.'}


def instructions(tasks):
    return ('CANONICAL DELIVERY CONTRACT v1 (also applies to every bounded repair):\n' +
            json.dumps(contract(tasks), ensure_ascii=False, separators=(',', ':')) +
            '\nExecution/report correspondence evidence never proves manuscript science. '
            'Use domain manuscript for scientific claims; future author actions are not implemented facts. '
            'Return exact $evidence_text/$page_text spans when available. Every assertion has its own '
            'reason, including reused_verified; never substitute a global clarity pass for a missing '
            'local judgment. Return concise strings, not pass/reason objects, for meaning_check, '
            'style_check and assertion_completeness. Nonuse is not a failed claimed realization.')


def normalize(response, context=None):
    """Only reversible, unambiguous representation changes. Raw output stays immutable."""
    result = copy.deepcopy(response); changes = []
    limits = result.get('reviewer', {}).get('limits')
    if isinstance(limits, list) and all(isinstance(s, str) for s in limits):
        result['reviewer']['limits'] = '\n'.join(limits)
        changes.append({'field': 'reviewer.limits', 'operation': 'join actual string list', 'original': limits})
    def visit(value, path):
        if isinstance(value, list):
            for i, item in enumerate(value): visit(item, path + '/' + str(i))
        elif isinstance(value, dict):
            notice_key={'conditional':'condition','unresolved':'unresolved_notice'}.get(value.get('status'))
            if notice_key and notice_key not in value and isinstance(value.get('notice'),dict):
                value[notice_key]=copy.deepcopy(value['notice'])
                changes.append({'field':path+'/'+notice_key,'operation':'Use actual explicitly supplied notice under its status-specific schema key','original':copy.deepcopy(value['notice'])})
            if value.get('status') == 'reused_verified' and not value.get('reason'):
                reason = value.get('reuse_reference', {}).get('comparison', {}).get('reason')
                if isinstance(reason, str) and reason.strip():
                    value['reason'] = reason
                    changes.append({'field': path + '/reason', 'operation': 'hoist actual reuse reason'})
            for key, item in list(value.items()): visit(item, path + '/' + key)
    visit(result.get('results', []), '/results'); visit(result.get('judgments', {}), '/judgments')
    if (context or {}).get('delivery_focus'):
        # Recover actual observations placed inside a named global value. Colliding
        # IDs must agree exactly; no evidence or verdict is manufactured.
        records = {r['id']: copy.deepcopy(r) for r in result.get('evidence_records', [])}
        if len(records) != len(result.get('evidence_records', [])):
            raise ValueError('Duplicate evidence IDs')
        globals_ = [r['value'] for r in result.get('results', [])
                    if any(t.startswith('global_scope:') for t in r.get('task_ids', [])) and isinstance(r.get('value'), dict)]
        for value in globals_:
            for record in value.get('evidence_records', []):
                ident = record['id']
                if ident in records and records[ident] != record:
                    raise ValueError('Conflicting nested evidence record')
                if ident not in records:
                    records[ident] = copy.deepcopy(record)
                    changes.append({'field': 'evidence_records/' + ident, 'operation': 'Hoist actual nested observation'})
        if records:
            result['evidence_records'] = list(records.values())
        for value in globals_:
            for kind in ['original_results', 'placeholder_results']:
                for row in value.get('report_economy', {}).get(kind, []):
                    for i, ref in enumerate(row.get('evidence', [])):
                        if isinstance(ref, str):
                            record = records.get(ref, {})
                            if not record.get('source_pages') or not record.get('text'):
                                raise ValueError('Original evidence reference lacks actual page observation')
                            row['evidence'][i] = {'evidence_record': ref, 'quote': record['text'], 'basis': 'manuscript'}
                            changes.append({'field': kind, 'operation': 'Expand explicit page-observation ID', 'original': ref})
    for record in result.get('evidence_records',[]):
        ref=(context or {}).get('evidence_source_refs',{}).get(record.get('source_ref'))
        if ref:
            require_existing=record.get('source_paths') or record.get('source_sha256s')
            if require_existing and (record.get('source_paths')!=[ref['path']] or record.get('source_sha256s')!=[ref['sha256']]):
                raise ValueError('Evidence symbolic reference conflicts with supplied binding')
            record['source_paths']=[ref['path']];record['source_sha256s']=[ref['sha256']]
            changes.append({'field':'evidence_records/'+record['id'],'operation':'Expand explicit frozen input document reference','source_ref':record['source_ref']})
    declarations={d['draft_label']:d for d in (context or {}).get('current_realization_declarations',[])}
    for row in result.get('results',[]):
        ids=row.get('task_ids',[]);labels=[i.split(':',1)[1] for i in ids if i.startswith('language:')]
        value=row.get('value',{})
        if len(labels)!=1 or labels[0] not in declarations or not isinstance(value,dict) or '$judgment' in value:continue
        declared={(f['expression_id'],f['feature_id']) for f in declarations[labels[0]]['feature_decisions']}
        extra=[r for r in value.get('nonuse_results',[]) if (r.get('expression_id'),r.get('feature_id')) not in declared]
        if extra:
            value['nonuse_results']=[r for r in value['nonuse_results'] if r not in extra]
            value.setdefault('context_nonuse_observations',[]).extend(extra)
            changes.append({'field':labels[0]+'/nonuse_results','operation':'Keep undeclared-source nonuse observations as context, not claimed-feature realization results','original':copy.deepcopy(extra)})
    return result, changes


def normalize_wire(response):
    """Transport-only coercion before v2 decoding; preserve every original character."""
    result = copy.deepcopy(response)
    if isinstance(result.get('limits'), str):
        original = result['limits']
        result['limits'] = [original] if original else []
        result.setdefault('representation_changes', []).append({'field': 'limits', 'original': original,
                                                              'operation': 'Wrap actual limit string'})
    return result


def inspect_records(response, bindings, page_images):
    issues=[];seen=set();images={p['page']:p for p in page_images}
    for r in response.get('evidence_records',[]):
        error=None
        if not isinstance(r.get('id'),str) or r['id'] in seen or not isinstance(r.get('text'),str) or not r['text'].strip():error='Duplicate/missing evidence ID or text'
        elif r.get('source_pages'):
            if any(type(p) is not int or p not in images for p in r['source_pages']):error='Unknown actual inspected page'
        else:
            paths=r.get('source_paths',[]);hashes=r.get('source_sha256s',[])
            if not paths or len(paths)!=len(hashes) or any(bindings.get(p)!=s for p,s in zip(paths,hashes)):error='Evidence must bind actual supplied documents'
        seen.add(r.get('id'))
        if error:issues.append({'field':'evidence_records/'+str(r.get('id')),'problem':error,'kind':'format'})
    return issues


def inspect(tasks, values, context=None):
    """Collect all contract defects, never alter decisions or manufacture passes."""
    context = context or {}; issues = []
    def add(t, field, error, kind='format'):
        issues.append({'task_id': t['id'], 'field': field, 'problem': error, 'kind': kind})
    def text(t, value, key, path=''):
        if not isinstance(value.get(key), str) or not value[key].strip(): add(t, path + key, 'Required nonempty string')
    for t in tasks:
        value = values.get(t['id'])
        if not isinstance(value, dict): add(t, 'result', 'Missing/object judgment required'); continue
        kind = t['kind']
        if kind == 'target':
            for key in TEXT_FIELDS: text(t, value, key)
            if t['data'].get('kind') == 'suggested_wording': text(t, value, 'assertion_completeness')
            elif value.get('classification') not in {'factual', 'non_factual', 'action', 'explanatory'}:
                add(t, 'classification', 'Invalid target classification')
            assertions = value.get('assertions', [])
            if not isinstance(assertions, list): add(t, 'assertions', 'Expected list'); continue
            if value.get('classification') == 'factual' and not assertions: add(t, 'assertions', 'Factual block lacks assertions', 'needs_judgment')
            for i, assertion in enumerate(assertions):
                path = f'assertions[{i}].'
                if not isinstance(assertion, dict): add(t, path, 'Expected object'); continue
                for key in ['quote', 'reason']: text(t, assertion, key, path)
                status = assertion.get('status'); domain = assertion.get('domain')
                if status not in {'supported', 'conditional', 'unresolved', 'reused_verified'}: add(t, path+'status', 'Invalid assertion status')
                if domain not in DOMAINS: add(t, path+'domain', 'Explicit assertion domain required')
                if status == 'supported':
                    evidence = assertion.get('evidence', [])
                    if not evidence: add(t, path+'evidence', 'Supported assertion needs actual evidence', 'needs_judgment')
                    for e in evidence:
                        if e.get('basis') not in BASES.get(domain, set()): add(t, path+'evidence', 'Evidence basis/domain mismatch')
                if status == 'reused_verified' and domain != 'manuscript': add(t, path+'domain', 'Verified scientific reuse cannot establish execution metadata')
        elif kind == 'source_field':
            if set(value) - {'components', 'non_substantive_reason'}: add(t, 'result', 'Unexpected immutable-inventory/source keys')
            if bool(value.get('components')) == bool(value.get('non_substantive_reason')): add(t, 'components', 'Provide components XOR non-substantive reason')
        elif kind == 'coverage':
            assessment = t['data']['component']['assessment']; status = value.get('status')
            allowed = {'required': {'kept','missing','unresolved'}, 'optional': {'kept','missing','not_required','unresolved'},
                       'unknown': {'unresolved'}, 'duplicate': {'not_required'},
                       'already_answered': {'not_required'}, 'unsupported': {'not_required'}}
            if status not in allowed.get(assessment, set()): add(t, 'status', 'Conflicts with frozen assessment', 'needs_judgment')
            for key in ['reason']: text(t, value, key)
            for key in ['target_quotes','report_quotes']:
                if not isinstance(value.get(key), list): add(t, key, 'Required quote list')
        elif kind == 'language':
            for key in ['meaning','naturalness']:
                part = value.get(key, {})
                if part.get('status') not in {'pass','fail'} or not part.get('reason'): add(t, key, 'Missing actual language judgment', 'needs_judgment')
                elif part['status']=='fail':add(t,key,'Actual language review failed','needs_judgment')
            used={(f['expression_id'],f['feature_id']):f for f in t['data'].get('realization',{}).get('feature_decisions',[]) if f['decision']!='not_applicable'}
            feature_results=value.get('feature_results',[])
            if {(r.get('expression_id'),r.get('feature_id')) for r in feature_results}!=set(used):add(t,'feature_results','Claimed feature coverage mismatch')
            for r in feature_results:
                f=used.get((r.get('expression_id'),r.get('feature_id')),{});expected='partial' if f.get('claim_extent')=='partial' else 'confirmed'
                if r.get('status')!=expected:add(t,'feature_results','Actual feature realization not confirmed at claimed extent','needs_judgment')
        elif kind == 'global_scope':
            for key in ['source_completeness','assertion_completeness','semantic_review','reason']: text(t, value, key)
            if not isinstance(value.get('issues'), list): add(t, 'issues', 'Required explicit issues list')
            elif value['issues']:add(t,'issues','Actual global issues remain','needs_judgment')
            for key in ['author_clarity','report_economy']:
                if key in value and value[key].get('status')!='pass':add(t,key,'Actual global review failed','needs_judgment')
            if 'report_meta_candidates' in context:
                import report_concision
                try:report_concision.validate_meta(value.get('report_economy',{}),context['report_meta_candidates'])
                except ValueError as error:add(t,'report_economy.meta_results',str(error),'needs_judgment')
            if context.get('history_binding'):
                history=value.get('history_change_review',{})
                if history.get('status')!='completed' or not history.get('reason') or history.get('issues')!=[]:
                    add(t,'history_change_review','Actual integrated historical-source review required','needs_judgment')
    return issues
