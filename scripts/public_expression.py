"""Read minimized Expression evidence without reconstructing private pages.

Local format/source-role checks are not publication permission or quality proof.
"""
import copy
import hashlib
import json
import re
from pathlib import Path

FORMAT = 'public_minimized_expression_v1'
ROLES = {'public_expression_candidate', 'public_advisor_expression'}
SCOPES = {'sentence', 'paragraph', 'argument_unit', 'section', 'cross_section', 'whole_paper'}
KINDS = {'verbatim_mentor_fragment', 'verbatim_mentor_prose',
         'verbatim_author_before', 'verbatim_author_deletion',
         'verbatim_editorial_instruction', 'adapted_example', 'synthetic_example'}
EXAMPLE_KINDS = {'mentor_wording': {'verbatim_mentor_fragment', 'verbatim_mentor_prose'},
                 'editorial_instruction': {'verbatim_editorial_instruction'},
                 'author_before': {'verbatim_author_before'},
                 'author_deletion': {'verbatim_author_deletion'},
                 'analyst_example': {'adapted_example', 'synthetic_example'}}
ACCOUNTS = {'before_account', 'observed_change', 'changed_relationship', 'after_account',
            'operations', 'transfer_conditions', 'do_not_transfer', 'facts_and_qualifications'}
RECORD_FIELDS = {'id', 'title', 'scope', 'scope_detail', 'section_task', 'before_account',
                 'observed_change', 'changed_relationship', 'after_account', 'operations',
                 'transfer_conditions', 'do_not_transfer', 'facts_and_qualifications',
                 'retrieval_terms', 'examples', 'language_features', 'limits',
                 'publication_permission', 'content_status', 'preference_status', 'concern_ids'}
EXAMPLE_FIELDS = {'id', 'kind', 'text', 'function', 'body_form_allowed', 'pair_id'}
FEATURE_FIELDS = {'id', 'kind', 'evidence_example_ids', 'function', 'frame', 'operation',
                  'conditions', 'do_not_transfer', 'evidence_status'}
SCHEMA = '''PUBLIC EXPRESSION v1/v2: A record with source_format="public_minimized_expression_v1"
contains minimized, separately labeled examples and analytical accounts. Original pages,
images, private locators and omitted context are NOT supplied. Use its stated conditions,
limits and the complete TARGET passage; do not infer what the omitted source contained.
For every transfer or expression_uses entry quoting such a record, add
expression_excerpt_basis:{kind:"mentor_wording|editorial_instruction|author_before|author_deletion|analyst_example",example_id:"EX...:E..."}
or expression_excerpt_basis:{kind:"analytical_account",field:"before_account|observed_change|changed_relationship|after_account|operations|transfer_conditions|do_not_transfer|facts_and_qualifications"}.
Quote a continuous exact span from that chosen example or field. Analytical accounts,
frames and generated examples are not mentor quotations. A literal mentor fragment alone
does not establish manuscript genre. Only admitted language_features with an actual
body_form_allowed=true mentor proposal can support manuscript language_form. Deleted
author text supports language_edit; comments support editorial_operation. No private
page access, accepted revision, general preference or disclosure permission is inferred.
Actual mentor title/heading fragments with body_form_allowed=false may support a
bounded editorial_operation. Their frames are withheld from body drafting; they
cannot support language_form or become body prose through a genre relabeling.
In v2, an admitted paragraph/sentence-order feature can instead bind evidence_account
to a supplied analytical operation. Its source_quote is an analyst account, not literal
mentor wording; evidence_kind="analytical_operation" supports editorial_operation only.
No omitted comment quotation or private source locator may be reconstructed.
Missing source evidence means narrower use, nonmatch or unfinished inspection, not a
new defect in the target. No example-count quota and no mandatory phrase copying.
'''


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def is_public(record):
    return record.get('source_format') == FORMAT


def strings(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [s for item in value for s in strings(item)]
    if isinstance(value, dict) and set(value) == {'action', 'condition'}:
        return strings(value['action']) + strings(value['condition'])
    if isinstance(value, dict) and set(value) == {'action', 'target', 'conditions'}:
        return strings(value['action']) + strings(value['target']) + strings(value['conditions'])
    return []


def valid_operation(value):
    if isinstance(value, str):
        return bool(value.strip())
    if not isinstance(value, dict):
        return False
    if set(value) == {'action', 'condition'}:
        return all(isinstance(value[k], str) and value[k].strip() for k in ['action', 'condition'])
    if set(value) == {'action', 'target', 'conditions'}:
        return (all(isinstance(value[k], str) and value[k].strip() for k in ['action', 'target']) and
                isinstance(value['conditions'], list) and
                all(isinstance(s, str) and s.strip() for s in value['conditions']))
    return False


def check_records(records, concern_ids=None):
    require(isinstance(records, list) and len({r['id'] for r in records}) == len(records), 'Duplicate public Expression')
    for record in records:
        rid = record.get('id', '')
        require(re.fullmatch(r'EX\d{5}', rid), 'Invalid public Expression namespace')
        require(set(record) <= RECORD_FIELDS, 'Unexpected public Expression field')
        require(record.get('scope') in SCOPES, 'Invalid public Expression scope')
        for field in ['title', 'section_task', 'before_account', 'observed_change', 'changed_relationship', 'after_account']:
            require(isinstance(record.get(field), str) and record[field].strip(), 'Incomplete public Expression: ' + field)
        for field in ['transfer_conditions', 'do_not_transfer', 'facts_and_qualifications', 'retrieval_terms', 'limits', 'concern_ids']:
            require(isinstance(record.get(field), list) and all(isinstance(s, str) and s.strip() for s in record[field]), 'Invalid public Expression list: ' + field)
        require(isinstance(record.get('operations'), list) and all(valid_operation(op) for op in record['operations']), 'Invalid public Expression operations')
        require(record['operations'] and record['retrieval_terms'], 'Public Expression lacks usable operations/retrieval')
        if concern_ids is not None:
            require(set(record['concern_ids']) <= set(concern_ids), 'Public Expression links unknown Concern')
        examples = record.get('examples')
        require(isinstance(examples, list), 'Missing public examples')
        by_example = {e['id']: e for e in examples}
        require(len(by_example) == len(examples), 'Duplicate public example')
        for example in examples:
            require(set(example) == EXAMPLE_FIELDS, 'Unexpected/incomplete public example fields')
            require(re.fullmatch(re.escape(rid) + r':E\d+', example['id']), 'Invalid public example namespace')
            require(example['kind'] in KINDS and isinstance(example['text'], str) and example['text'].strip(), 'Invalid public example')
            require(type(example['body_form_allowed']) is bool, 'Invalid public body genre flag')
            require(not example['body_form_allowed'] or example['kind'] in EXAMPLE_KINDS['mentor_wording'], 'Non-mentor example promoted into manuscript prose')
            require(example['pair_id'] is None or isinstance(example['pair_id'], str) and example['pair_id'].startswith(rid + ':'), 'Invalid public pair namespace')
        features = record.get('language_features')
        require(isinstance(features, list) and len({f['id'] for f in features}) == len(features), 'Invalid public features')
        for feature in features:
            require(FEATURE_FIELDS <= set(feature) <= FEATURE_FIELDS | {'evidence_account'}, 'Unexpected/incomplete public feature fields')
            require(re.fullmatch(re.escape(rid) + r':L\d+', feature['id']), 'Invalid public feature namespace')
            require(feature['kind'] in {'lexical', 'syntax', 'qualification', 'transition', 'sentence_order', 'paragraph'}, 'Invalid public feature kind')
            require(isinstance(feature['evidence_example_ids'], list) and set(feature['evidence_example_ids']) <= by_example.keys(), 'Public feature lacks supplied example')
            for field in ['conditions', 'do_not_transfer']:
                require(isinstance(feature[field], list) and all(isinstance(s, str) and s.strip() for s in feature[field]), 'Invalid public feature conditions')
            for field in ['function', 'operation', 'evidence_status']:
                require(isinstance(feature[field], str) and feature[field].strip(), 'Incomplete public feature account')
            require(isinstance(feature['frame'], str), 'Invalid public analytical frame')
            if 'evidence_account' in feature:
                basis = feature['evidence_account']
                require(isinstance(basis, dict) and set(basis) == {'field', 'quote'} and basis['field'] == 'operations', 'Invalid public operation account origin')
                require(not feature['evidence_example_ids'] and feature['kind'] in {'paragraph', 'sentence_order'}, 'Analytical operation cannot establish manuscript wording')
                require(isinstance(basis['quote'], str) and basis['quote'].strip() and any(basis['quote'] in s for s in strings(record['operations'])), 'Public operation account quote absent')


def check_library(library, concern_ids=None):
    library = Path(library)
    required = {'records.json', 'index.json', 'manifest.json', 'FREEZE.json'}
    actual = {p.name for p in library.iterdir()}
    require(required <= actual <= required | {'README.md'} and all(p.is_file() for p in library.iterdir()), 'Unexpected public Expression package files')
    frozen = read(library / 'FREEZE.json')['files']
    require({'records.json', 'index.json', 'manifest.json'} <= set(frozen) <= required - {'FREEZE.json'} | {'README.md'}, 'Incomplete public Expression freeze')
    require(all(name in actual and hashlib.sha256((library / name).read_bytes()).hexdigest() == digest for name, digest in frozen.items()), 'Public Expression frozen file changed')
    manifest = read(library / 'manifest.json')
    require(manifest.get('role') in ROLES and manifest.get('schema_version') in {1, 2}, 'Wrong public Expression format')
    require(manifest.get('status') != 'local_candidate_incomplete', 'Public Expression preparation is incomplete')
    for field in ['private_raw_pages', 'private_original_mapping', 'private_images']:
        require(manifest.get(field) is False, 'Public Expression may contain private source material')
    require(not (library / 'episodes.json').exists(), 'Public Expression must not reconstruct private episodes')
    records = read(library / 'records.json')
    require(manifest.get('count') == len(records), 'Public Expression manifest count mismatch')
    check_records(records, concern_ids)
    if manifest['schema_version'] == 2:
        require(manifest.get('editorial_comment_policy') == 'analytical_operations_only', 'Missing public instruction policy')
        require(all(e['kind'] != 'verbatim_editorial_instruction' for r in records for e in r['examples']), 'Literal editorial comment in instruction-free package')
    return manifest


def project(record):
    """Bind existing realization fields to PUBLIC examples, without fake raw refs."""
    result = copy.deepcopy(record)
    result['source_format'] = FORMAT
    result['public_language_features'] = copy.deepcopy(record['language_features'])
    examples = {e['id']: e for e in record['examples']}
    admitted = []
    held = []
    for feature in record['language_features']:
        evidence = [examples[x] for x in feature['evidence_example_ids']]
        positive = [e for e in evidence if e['body_form_allowed'] and e['kind'] in EXAMPLE_KINDS['mentor_wording']]
        nonbody_mentor = [e for e in evidence if not e['body_form_allowed'] and e['kind'] in EXAMPLE_KINDS['mentor_wording']]
        analytical = feature.get('evidence_account')
        if analytical:
            kind = 'analytical_operation'
            source_ref = record['id'] + ':account:' + analytical['field'] + ':' + feature['id']
            source_quote = analytical['quote']
        elif positive:
            selected = positive[0]
            kind = 'mentor_prose' if selected['kind'] == 'verbatim_mentor_prose' else 'mentor_fragment'
        elif evidence and all(e['kind'] == 'verbatim_author_deletion' for e in evidence):
            selected = evidence[0]
            kind = 'deletion'
        elif nonbody_mentor:
            selected = nonbody_mentor[0]
            kind = 'mentor_prose' if selected['kind'] == 'verbatim_mentor_prose' else 'mentor_fragment'
        elif feature['kind'] in {'paragraph', 'sentence_order'} and any(e['kind'] == 'verbatim_editorial_instruction' for e in evidence):
            selected = next(e for e in evidence if e['kind'] == 'verbatim_editorial_instruction')
            kind = 'editorial_instruction'
        else:
            held.append({'feature_id': feature['id'], 'reason': 'No literal mentor-body, deletion or paragraph-instruction evidence for this realization feature.'})
            continue
        if not analytical:
            source_ref, source_quote = selected['id'], selected['text']
        conditions = feature['conditions'] or record['transfer_conditions']
        boundaries = feature['do_not_transfer'] or record['do_not_transfer']
        if not conditions or not boundaries:
            held.append({'feature_id': feature['id'], 'reason': 'Missing conditional transfer boundary; no universal preference inferred.'})
            continue
        admitted.append({**feature, 'evidence_kind': kind, 'source_ref': source_ref,
                         'source_quote': source_quote, 'conditions': conditions,
                         'do_not_transfer': boundaries,
                         'frame': '' if kind in {'editorial_instruction', 'analytical_operation'} or (nonbody_mentor and not positive) else feature['frame'],
                         'body_evidence': {'body_form_allowed': bool(positive),
                                           'basis': 'Source-reviewed analytical operation; no literal comment disclosed.' if analytical else 'Actual non-body mentor example; conditional editorial operation only, not body wording.' if nonbody_mentor and not positive else 'Minimized public example genre; omitted source pages unavailable, acceptance unconfirmed.'}})
    result['language_features'] = admitted
    result['withheld_realization_features'] = held
    result['source_context_limit'] = 'Only minimized examples and conditional analysis are available; original pages and private source mapping are absent.'
    return result


def excerpt_texts(record, basis=None):
    if basis is None:
        return [e['text'] for e in record['examples']] + [s for key in ACCOUNTS for s in strings(record[key])]
    require(isinstance(basis, dict), 'Public Expression excerpt must identify its evidence origin')
    kind = basis.get('kind')
    if kind == 'analytical_account':
        field = basis.get('field')
        require(field in ACCOUNTS and set(basis) == {'kind', 'field'}, 'Invalid public analytical excerpt origin')
        return strings(record[field])
    require(kind in EXAMPLE_KINDS and set(basis) == {'kind', 'example_id'}, 'Invalid public example excerpt origin')
    example = next((e for e in record['examples'] if e['id'] == basis['example_id']), None)
    require(example and example['kind'] in EXAMPLE_KINDS[kind], 'Public Expression excerpt changed evidence genre')
    return [example['text']]


def validate_excerpt(record, use):
    basis = use.get('expression_excerpt_basis')
    require(basis is not None, 'Public Expression excerpt must identify its evidence origin')
    text = use.get('source_excerpt')
    require(isinstance(text, str) and text.strip() and any(text in source for source in excerpt_texts(record, basis)), 'Public Expression excerpt absent from chosen evidence')


def check_feature(feature, record):
    if feature.get('evidence_kind') == 'analytical_operation':
        basis = feature.get('evidence_account')
        require(isinstance(basis, dict) and set(basis) == {'field', 'quote'} and basis['field'] == 'operations', 'Invalid analytical operation source')
        expected_ref = record['id'] + ':account:' + basis['field'] + ':' + feature['id']
        require(feature.get('source_ref') == expected_ref and feature.get('source_quote') == basis['quote'] and
                any(basis['quote'] in s for s in strings(record['operations'])), 'Analytical operation changed account binding')
        require(not feature.get('evidence_example_ids') and feature.get('kind') in {'paragraph', 'sentence_order'} and
                feature.get('body_evidence', {}).get('body_form_allowed') is False, 'Analytical operation cannot supply manuscript wording/syntax')
        return
    example = next((e for e in record['examples'] if e['id'] == feature.get('source_ref')), None)
    require(example and feature.get('source_quote') and feature['source_quote'] in example['text'], 'Public language feature quote/ref absent from supplied example')
    kind = feature.get('evidence_kind')
    expected = {'mentor_prose': {'verbatim_mentor_prose'},
                'mentor_fragment': {'verbatim_mentor_fragment'},
                'deletion': {'verbatim_author_deletion'},
                'editorial_instruction': {'verbatim_editorial_instruction'}}
    require(kind in expected and example['kind'] in expected[kind], 'Public language feature changed evidence genre')
    body = feature.get('body_evidence', {}).get('body_form_allowed', False)
    require(not body or example['body_form_allowed'] and kind in {'mentor_prose', 'mentor_fragment'}, 'Public comment cannot supply manuscript wording/syntax')
