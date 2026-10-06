"""Offline post-verification obligation audit; original review stages stay frozen.

A reviews original requirements against the full manuscript before B reveals
changed outputs/reasons. Validation checks records, not scientific truth.
"""
import argparse
import copy
import hashlib
import json
import unicodedata
from pathlib import Path

SCHEMA = 'mentortrace.merge-obligations.v1'
A_INSTRUCTIONS = '''Assess ORIGINAL source records against the CURRENT FULL manuscript.
Do not open later outputs, merge/verify dispositions or reasons during A.
Original source analyses are hypotheses, not authority. Source role, opinion and
number of supporting sources do not establish necessity. Identify independently
answerable requirements from original relation/gap/closure goals or organization
proposals, including qualifications and additional occurrence locations. Same
topic does not make requirements equal. Record exact source excerpts, typed
manuscript evidence and required/optional/already_answered/unsupported/unknown/
duplicate assessments. Extra occurrence suggestions are not automatically necessary
technical repairs. Evidence-supported withdrawals and duplicates are legitimate.
Explicitly assess whether the decomposition covers the complete source scope.
Component count and completeness declarations do not prove completeness. Use
concise evidence-focused explanations, not private deliberation. Unknown remains
unknown. Image evidence needs the supplied page image hash and focused description.
A locator does not prove its meaning. Record truthful reviewer identity, kind,
context scope, prior exposure and limitations. Previously exposed reviewers must
use self_review provenance. This utility invokes no models or semantic oracle.'''
B_INSTRUCTIONS = '''A is frozen. Compare EACH component to actual final outputs.
Only now examine original dispositions. If an author fully follows the final
output, decide whether any supported required component remains unanswered.
Keep independent closure goals and additional occurrence locations separate.
Existing quotes do not prove correspondence. Give focused exact target field
excerpts and concise component-specific explanations. Required missing/unresolved
and pending review block readiness. Unknown stays unresolved but may be delivered
when bound actual report excerpts and an explicit uncertainty visibility review
show that it is presented as unknown or awaiting author confirmation. It is never
converted into a confirmed error or a resolved requirement. Optional omissions remain
visible without becoming technical defects. Sound withdrawals are not missing
requirements. Duplicates reference a canonical component and same occurrence scope.
Do not revise A to fit B; corrections require a new audit package. If a report is
bound, every kept component needs focused exact actual report excerpts. Record
truthful reviewer provenance. Never edit original run artifacts. Acceptance means
records validated, not scientific or semantic certification.'''


def require(test, message):
    if not test:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def encoded(value):
    return json.dumps(value, ensure_ascii=False, indent=2).encode('utf-8')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def value_digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def save_new(path, value):
    path = Path(path)
    require(not path.exists(), 'Refuse to overwrite audit artifact: ' + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded(value))


def substantial(text):
    # Excerpt hygiene only, never a requirement-truth oracle.
    return isinstance(text, str) and len(text.strip()) >= 3 and sum(c.isalnum() for c in text) >= 2


def rows_by_id(rows, label):
    require(isinstance(rows, list), label + ' must be a list')
    require(all(isinstance(r, dict) and isinstance(r.get('id'), str) and r['id'] for r in rows), label + ' invalid IDs')
    require(len({r['id'] for r in rows}) == len(rows), label + ' duplicate IDs')
    return {r['id']: r for r in rows}


def path_under(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    require(path.is_relative_to(root), 'Source path escapes run: ' + relative)
    return path


def disposition_map(data, field, incoming, targets, label):
    rows = data.get(field, [])
    require(isinstance(rows, list) and len(rows) == len(incoming)
            and {r.get('input_id') for r in rows} == set(incoming), label + ' duplicate/missing source dispositions')
    for row in rows:
        require(isinstance(row.get('output_ids'), list) and len(row['output_ids']) == len(set(row['output_ids'])),
                label + ' duplicate/missing target IDs')
        require(set(row['output_ids']) <= set(targets), label + ' unknown target')
        require(row.get('status') in {'retained', 'merged', 'narrowed', 'withdrawn', 'unresolved', 'incorporated'},
                label + ' invalid disposition')
        if row['status'] in {'retained', 'merged', 'narrowed', 'incorporated'}:
            require(row['output_ids'], label + ' retained requirement without target')
        if row['status'] in {'withdrawn', 'unresolved'}:
            require(not row['output_ids'], label + ' withdrawn/unresolved requirement has target')
    return {row['input_id']: row for row in rows}


def load_run(run):
    """Read immutable sources and derive deterministic selection and lineage."""
    run = Path(run).resolve()
    files = {}
    def load(relative):
        path = path_under(run, relative)
        require(path.is_file(), 'Missing source file: ' + relative)
        files[relative] = digest(path)
        return read(path)
    def acceptance_sources(relative_record, record):
        folder = relative_record.rsplit('/', 1)[0]
        require(record.get('response_sha256') == files[folder + '/response.json'], 'Accepted response source hash mismatch')
        for field, filename in (('raw_response_sha256', 'raw_response.json'), ('request_sha256', 'request.json')):
            if record.get(field):
                relative = folder + '/' + filename
                path = path_under(run, relative)
                require(path.is_file() and digest(path) == record[field], 'Accepted ' + filename + ' source hash mismatch')
                files[relative] = digest(path)
    manuscript = load('inputs/paper/body.json')
    require(isinstance(manuscript, list) and manuscript, 'Empty manuscript')
    require([p.get('page') for p in manuscript] == list(range(1, len(manuscript) + 1))
            and all(isinstance(p.get('text'), str) for p in manuscript), 'Invalid manuscript pages')
    manifest = load('inputs/paper/manifest.json')
    require(manifest.get('pages') == len(manuscript), 'Manuscript manifest page count mismatch')
    images = {}
    for image in manifest.get('images', []):
        require(image.get('page') in {p['page'] for p in manuscript} and image['page'] not in images,
                'Duplicate/invalid image page')
        relative = 'inputs/paper/' + image['path']
        path = path_under(run, relative)
        require(path.is_file() and digest(path) == image.get('sha256'), 'Manuscript image changed: ' + relative)
        files[relative] = digest(path)
        images[image['page']] = {'page': image['page'], 'path': str(path), 'sha256': image['sha256']}
    require(set(images) == {p['page'] for p in manuscript}, 'Missing manuscript page images')
    raw = rows_by_id(load('findings_raw.json'), 'Raw findings')
    merged = load('calls/merge/response.json')
    final = load('final.json')
    require(final == load('calls/verify/response.json'), 'Final output differs from frozen verify response')
    for relative in ('RAW_FREEZE.json', 'RESULT_FREEZE.json', 'inputs/paper/FREEZE.json',
                     'calls/merge/record.json', 'calls/verify/record.json'):
        if (run / relative).exists():
            freeze = load(relative)
            if relative == 'RAW_FREEZE.json':
                require(freeze.get('sha256') == files['findings_raw.json'], 'Raw source freeze mismatch')
            if relative == 'RESULT_FREEZE.json':
                require(freeze.get('raw') == files['findings_raw.json'] and freeze.get('final') == files['final.json'],
                        'Result source freeze mismatch')
            if relative == 'inputs/paper/FREEZE.json':
                for name, expected in freeze.get('files', {}).items():
                    path = path_under(run, 'inputs/paper/' + name)
                    require(path.is_file() and digest(path) == expected, 'Frozen manuscript changed: ' + name)
                    files['inputs/paper/' + name] = expected
            if relative.endswith('/record.json'):
                acceptance_sources(relative, freeze)
    originals, checks, branch_findings = {}, {}, {}
    for folder in sorted((run / 'calls').iterdir(), key=lambda p: p.name):
        if not folder.is_dir() or folder.name in {'merge', 'verify', 'objects'} or not (folder / 'response.json').exists():
            continue
        response = load('calls/' + folder.name + '/response.json')
        relative_record = 'calls/' + folder.name + '/record.json'
        if (run / relative_record).exists():
            record = load(relative_record)
            acceptance_sources(relative_record, record)
        branch_checks = rows_by_id(response.get('checks', []), folder.name + ' checks')
        require(not set(branch_checks) & set(checks), 'Duplicate check IDs across sources')
        checks.update(branch_checks)
        for kind, field in (('finding', 'findings'), ('organization', 'organization_suggestions')):
            incoming = rows_by_id(response.get(field, []), folder.name + ' ' + field)
            for sid, item in incoming.items():
                require(sid not in originals, 'Duplicate original source ID: ' + sid)
                check_ids = item.get('check_ids', [])
                require(isinstance(check_ids, list) and len(set(check_ids)) == len(check_ids)
                        and set(check_ids) <= set(branch_checks), 'Missing/duplicate source check: ' + sid)
                if kind == 'organization' or item.get('finding_type') != 'surface':
                    require(check_ids, 'Original source has no source checks: ' + sid)
                originals[sid] = {'source_id': sid, 'source_type': kind, 'original': item,
                                  'checks': [branch_checks[cid] for cid in check_ids]}
                if kind == 'finding':
                    branch_findings[sid] = item
    require(branch_findings == raw, 'Raw source accounting differs from original branch responses')
    raw_org = {sid: s['original'] for sid, s in originals.items() if s['source_type'] == 'organization'}
    mf = rows_by_id(merged.get('findings', []), 'Merged findings')
    mo = rows_by_id(merged.get('organization_suggestions', []), 'Merged organization')
    ff = rows_by_id(final.get('findings', []), 'Final findings')
    fo = rows_by_id(final.get('organization_suggestions', []), 'Final organization')
    require(not set(mf) & set(mo) and not set(ff) & set(fo), 'Finding/organization target ID collision')
    mt, ft = {**mf, **mo}, {**ff, **fo}
    first = {**disposition_map(merged, 'dispositions', raw, mf, 'Merge'),
             **disposition_map(merged, 'organization_dispositions', raw_org, mt, 'Organization merge')}
    last = {**disposition_map(final, 'dispositions', mf, ff, 'Verify'),
            **disposition_map(final, 'organization_dispositions', mo, ft, 'Organization verify')}
    ancestors = {target: set() for target in mt}
    for sid, disposition in first.items():
        for target in disposition['output_ids']:
            ancestors[target].add(sid)
    for target, item in mt.items():
        if not ancestors[target]:
            require(item.get('new_in_stage') is True, 'Unaccounted merged source: ' + target)
            originals[target] = {'source_id': target, 'source_type': 'organization' if target in mo else 'finding',
                                 'original': item, 'checks': [], 'source_origin': 'merge addition; original input to verify'}
            ancestors[target] = {target}
    descendants = {sid: set() for sid in originals}
    final_ancestors = {target: set() for target in ft}
    for intermediate, disposition in last.items():
        for target in disposition['output_ids']:
            final_ancestors[target].update(ancestors[intermediate])
            for sid in ancestors[intermediate]:
                descendants[sid].add(target)
    eligible = {sid for sid, s in originals.items() if s['original'].get('finding_type') != 'surface'}
    changed = {'narrowed', 'withdrawn', 'unresolved'}
    selected = {sid for sid, d in first.items() if sid in eligible and d['status'] in changed}
    for intermediate, d in last.items():
        if d['status'] in changed:
            selected.update(ancestors[intermediate] & eligible)
    for lineage in list(ancestors.values()) + list(final_ancestors.values()):
        if len(lineage & eligible) > 1:
            selected.update(lineage & eligible)
    # A opaque group IDs hide selection labels and later outputs.
    lineages = {tuple(sorted(lineage & selected)) for lineage in final_ancestors.values() if lineage & selected}
    lineages.update(tuple(sorted(lineage & selected)) for lineage in ancestors.values() if len(lineage & selected) > 1)
    covered = {sid for lineage in lineages for sid in lineage}
    lineages.update((sid,) for sid in selected - covered)
    groups = [{'group_id': f'G{n:04d}', 'source_ids': list(lineage)} for n, lineage in enumerate(sorted(lineages), 1)]
    sources = []
    for sid in sorted(selected):
        source = copy.deepcopy(originals[sid])
        source['source_sha256'] = value_digest(source['original'])
        sources.append(source)
    routes = {sid: {'final_ids': sorted(descendants[sid]), 'merge_dispositions': [first[sid]] if sid in first else [],
                    'verify_dispositions': [last[t] for t in sorted(ancestors) if sid in ancestors[t]]} for sid in sorted(selected)}
    return {'run': str(run), 'source_files': dict(sorted(files.items())), 'manuscript': manuscript,
            'page_images': [images[p] for p in sorted(images)], 'sources': sources, 'groups': groups,
            'routes': routes, 'final_targets': ft}


def make_a_packet(snapshot):
    return {'schema_version': SCHEMA, 'phase': 'A', 'instructions': A_INSTRUCTIONS,
            'manuscript': snapshot['manuscript'], 'page_images': snapshot['page_images'],
            'groups': snapshot['groups'], 'sources': snapshot['sources'],
            'review_boundary': 'Original source opinions require examination; later outputs hidden.'}


def reviewer_template(scope):
    return {'name': '', 'kind': '', 'context_scope': scope, 'prior_outputs_seen': None, 'limits': ''}


def review_provenance(reviewer, phase):
    require(isinstance(reviewer, dict) and substantial(reviewer.get('name')), phase + ' reviewer identity missing')
    require(reviewer.get('kind') in {'human', 'model', 'self_review', 'synthetic_test'}, phase + ' reviewer kind invalid')
    require(reviewer.get('context_scope') == ('originals_and_full_manuscript' if phase == 'A' else 'frozen_a_and_final_outputs'),
            phase + ' context scope invalid')
    require(type(reviewer.get('prior_outputs_seen')) is bool and substantial(reviewer.get('limits')),
            phase + ' truthful exposure/limits record required')
    if phase == 'A' and reviewer['prior_outputs_seen']:
        require(reviewer['kind'] in {'self_review', 'synthetic_test'}, 'A exposed reviewer must be identified as self_review')
    return reviewer


def batch_packets(packet, max_batch_bytes):
    if max_batch_bytes is None:
        return [packet]
    require(isinstance(max_batch_bytes, int) and max_batch_bytes > 0, 'Invalid byte preflight limit')
    source_map = {s['source_id']: s for s in packet['sources']}
    base = {k: v for k, v in packet.items() if k not in {'groups', 'sources'}}
    def compose(groups):
        selected = {sid for g in groups for sid in g['source_ids']}
        return {**base, 'groups': groups, 'sources': [source_map[s] for s in sorted(selected)]}
    batches, current = [], []
    for group in packet['groups']:
        require(len(encoded(compose([group]))) <= max_batch_bytes,
                'One complete group plus full manuscript exceeds byte limit; never truncate')
        trial = current + [group]
        if current and len(encoded(compose(trial))) > max_batch_bytes:
            batches.append(compose(current))
            current = []
        current.append(group)
    if current or not packet['groups']:
        batches.append(compose(current))
    require(all(len(encoded(b)) <= max_batch_bytes for b in batches), 'Full manuscript exceeds byte limit; never truncate')
    return batches


def record_schema():
    """Portable JSON Schema for templates/records; runtime checks are stricter."""
    string = {'type': 'string'}
    sha = {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}
    def obj(properties, required):
        return {'type': 'object', 'properties': properties, 'required': required}
    anchor = {'oneOf': [
        obj({'kind': {'const': 'text'}, 'page': {'type': 'integer', 'minimum': 1}, 'quote': string}, ['kind', 'page', 'quote']),
        obj({'kind': {'const': 'image'}, 'page': {'type': 'integer', 'minimum': 1}, 'image_sha256': sha,
             'description': string}, ['kind', 'page', 'image_sha256', 'description'])]}
    anchor_list = {'type': 'array', 'items': {'$ref': '#/$defs/anchor'}}
    reviewer = obj({'name': string, 'kind': {'enum': ['human', 'model', 'self_review', 'synthetic_test', '']},
                    'context_scope': {'enum': ['originals_and_full_manuscript', 'frozen_a_and_final_outputs']},
                    'prior_outputs_seen': {'type': ['boolean', 'null']}, 'limits': string},
                   ['name', 'kind', 'context_scope', 'prior_outputs_seen', 'limits'])
    a_component = obj({'id': string, 'source_field': string, 'source_quote': string, 'requirement': string,
                       'assessment': {'enum': ['required', 'optional', 'already_answered', 'unsupported', 'unknown', 'duplicate']},
                       'reason': string, 'evidence': anchor_list, 'occurrences': anchor_list, 'duplicate_of': string},
                      ['id', 'source_field', 'source_quote', 'requirement', 'assessment', 'reason', 'evidence', 'occurrences'])
    a_component['description'] = 'Independent requirement; exact source field excerpt and manuscript evidence. Different occurrences are not automatically duplicates.'
    a_component['allOf'] = [{'if': {'properties': {'assessment': {'const': 'duplicate'}}}, 'then': {'required': ['duplicate_of']}}]
    visibility = obj({'status': {'enum': ['pending', 'completed']},
                      'presented_as': {'enum': ['unknown_or_author_confirmation', None]}, 'reason': string},
                     ['status', 'presented_as', 'reason'])
    b_component = obj({'component_id': string, 'status': {'enum': ['pending', 'kept', 'missing', 'not_required', 'unresolved']},
                       'reason': string, 'target_quotes': {'type': 'array', 'items': obj({'target_id': string, 'field': string,
                                                                                     'quote': string}, ['target_id', 'field', 'quote'])},
                       'report_quotes': {'type': 'array', 'items': string}, 'uncertainty_visibility_review': visibility},
                      ['component_id', 'status', 'reason', 'target_quotes', 'report_quotes'])
    b_component['description'] = 'Kept requires focused exact target and bound report excerpts. Unknown stays unresolved and needs explicit report visibility review to be deliverable.'
    a_unit = obj({'source_id': string, 'source_sha256': sha,
                  'coverage_review': obj({'status': {'enum': ['pending', 'completed']}, 'reason': string}, ['status', 'reason']),
                  'components': {'type': 'array', 'items': {'$ref': '#/$defs/a_component'}}},
                 ['source_id', 'source_sha256', 'coverage_review', 'components'])
    common = {'schema_version': {'const': SCHEMA}, 'package_sha256': sha, 'reviewer': {'$ref': '#/$defs/reviewer'}}
    phase_a = obj({**common, 'phase': {'const': 'A'}, 'units': {'type': 'array', 'items': a_unit}},
                  ['schema_version', 'phase', 'package_sha256', 'reviewer', 'units'])
    phase_b = obj({**common, 'phase': {'const': 'B'}, 'audit_directory': string, 'phase_a_sha256': sha,
                   'phase_b_packet_sha256': sha, 'report': {'oneOf': [{'type': 'null'}, obj({'path': string, 'sha256': sha}, ['path', 'sha256'])]},
                   'components': {'type': 'array', 'items': {'$ref': '#/$defs/b_component'}}},
                  ['schema_version', 'phase', 'package_sha256', 'reviewer', 'audit_directory', 'phase_a_sha256',
                   'phase_b_packet_sha256', 'report', 'components'])
    return {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'title': 'MentorTrace post-verification obligation records',
            'description': 'Templates may be pending. Runtime checks source IDs, hashes, excerpts and readiness. No semantic truth oracle.',
            'oneOf': [phase_a, phase_b], '$defs': {'anchor': anchor, 'reviewer': reviewer,
                                               'a_component': a_component, 'b_component': b_component}}


def prepare(run, output, max_batch_bytes=None):
    run, output = Path(run).resolve(), Path(output).resolve()
    require(not output.exists(), 'Audit output already exists')
    require(not output.is_relative_to(run), 'Audit output must be separate from immutable source run')
    snapshot = load_run(run)
    packet = make_a_packet(snapshot)
    batches = batch_packets(packet, max_batch_bytes)  # complete preflight before writes
    schema = record_schema()
    instructions = (A_INSTRUCTIONS + '\n\n' + B_INSTRUCTIONS +
        '\n\nCommands: prepare --run RUN --output AUDIT; fill a COPY of phase_a.template.json; '
        'adjudicate --audit AUDIT --ledger A.json; compare --audit AUDIT [--report REPORT]; '
        'fill a COPY of phase_b.template.json; check --ledger B.json [--report REPORT]. '
        '--allow-incomplete reports blockers without readiness. Byte limits measure UTF-8 '
        'payload bytes, not tokens; check actual model context limits separately.\n')
    batch_manifest = [{'file': f'phase_a.batches/batch_{n:04d}.json', 'sha256': value_digest(batch),
                       'utf8_bytes': len(encoded(batch))} for n, batch in enumerate(batches, 1)]
    package = {'schema_version': SCHEMA, 'run': str(run), 'source_files': snapshot['source_files'],
               'phase_a_packet_sha256': value_digest(packet), 'selected_source_ids': [s['source_id'] for s in snapshot['sources']],
               'phase_a_batches': batch_manifest, 'max_batch_bytes': max_batch_bytes,
               'support_files': {'schema.json': value_digest(schema),
                                 'instructions.md': hashlib.sha256(instructions.encode('utf-8')).hexdigest()},
               'selection': 'narrowed/withdrawn/unresolved and many-to-one finding/organization lineages; surface excluded',
               'semantic_correctness_verified': False}
    template = {'schema_version': SCHEMA, 'phase': 'A', 'package_sha256': value_digest(package),
                'reviewer': reviewer_template('originals_and_full_manuscript'),
                'units': [{'source_id': s['source_id'], 'source_sha256': s['source_sha256'],
                           'coverage_review': {'status': 'pending', 'reason': ''}, 'components': []} for s in snapshot['sources']]}
    save_new(output / 'package.json', package)
    save_new(output / 'phase_a.packet.json', packet)
    save_new(output / 'phase_a.template.json', template)
    for n, batch in enumerate(batches, 1):
        save_new(output / 'phase_a.batches' / f'batch_{n:04d}.json', batch)
    save_new(output / 'schema.json', schema)
    (output / 'instructions.md').write_bytes(instructions.encode('utf-8'))
    return {'status': 'pending_phase_a', 'selected_sources': len(snapshot['sources']), 'groups': len(snapshot['groups']),
            'batch_bytes': [len(encoded(b)) for b in batches], 'semantic_correctness_verified': False}


def verify_package(audit_dir):
    audit_dir = Path(audit_dir).resolve()
    package = read(audit_dir / 'package.json')
    require(package.get('schema_version') == SCHEMA, 'Invalid audit package schema')
    snapshot = load_run(package['run'])
    require(snapshot['source_files'] == package['source_files'], 'Audit source changed or source file accounting stale')
    packet = make_a_packet(snapshot)
    require(value_digest(packet) == package.get('phase_a_packet_sha256') and read(audit_dir / 'phase_a.packet.json') == packet,
            'Phase A source packet changed')
    require(package.get('selected_source_ids') == [s['source_id'] for s in snapshot['sources']], 'Selected source accounting mismatch')
    batches = batch_packets(packet, package.get('max_batch_bytes'))
    expected_batches = [{'file': f'phase_a.batches/batch_{n:04d}.json', 'sha256': value_digest(batch),
                         'utf8_bytes': len(encoded(batch))} for n, batch in enumerate(batches, 1)]
    require(package.get('phase_a_batches') == expected_batches, 'Phase A batch manifest changed')
    actual_files = {p.relative_to(audit_dir).as_posix() for p in (audit_dir / 'phase_a.batches').rglob('*') if p.is_file()}
    require(actual_files == {b['file'] for b in expected_batches}, 'Phase A duplicate/missing batch files')
    for batch in expected_batches:
        require(digest(audit_dir / batch['file']) == batch['sha256'], 'Phase A batch changed')
    support = package.get('support_files', {})
    require(set(support) == {'schema.json', 'instructions.md'}, 'Audit support file accounting mismatch')
    for relative, expected in support.items():
        path = audit_dir / relative
        require(path.is_file() and digest(path) == expected, 'Audit support file changed: ' + relative)
    return package, snapshot


def normalized(text):
    return ''.join(unicodedata.normalize('NFKC', text).split())


def evidence_anchor(anchor, snapshot):
    require(isinstance(anchor, dict) and anchor.get('kind') in {'text', 'image'}, 'Typed manuscript evidence required')
    pages = {p['page']: p['text'] for p in snapshot['manuscript']}
    require(type(anchor.get('page')) is int and anchor['page'] in pages, 'Invented manuscript evidence page')
    if anchor['kind'] == 'text':
        require(substantial(anchor.get('quote')), 'Empty/non-substantive manuscript evidence')
        text = pages[anchor['page']]
        joined = text.replace('-\n', '').replace('-\r\n', '')
        require(normalized(anchor['quote']) in normalized(text) or normalized(anchor['quote']) in normalized(joined),
                'Invented manuscript evidence quote')
    else:
        images = {i['page']: i for i in snapshot['page_images']}
        require(anchor.get('image_sha256') == images[anchor['page']]['sha256'], 'Image evidence hash mismatch')
        require(substantial(anchor.get('description')), 'Focused image evidence description required')


def validate_a(ledger, package, snapshot):
    require(ledger.get('schema_version') == SCHEMA and ledger.get('phase') == 'A', 'Invalid phase A ledger')
    require(ledger.get('package_sha256') == value_digest(package), 'Phase A package hash mismatch')
    provenance = review_provenance(ledger.get('reviewer'), 'A')
    sources = {s['source_id']: s for s in snapshot['sources']}
    units = ledger.get('units', [])
    require(isinstance(units, list) and len(units) == len(sources) and {u.get('source_id') for u in units} == set(sources),
            'Phase A duplicate/missing source accounting')
    components = {}
    for unit in units:
        source = sources[unit['source_id']]
        require(unit.get('source_sha256') == source['source_sha256'], 'Phase A source record hash mismatch')
        coverage = unit.get('coverage_review', {})
        require(coverage.get('status') == 'completed' and substantial(coverage.get('reason')), 'Phase A source decomposition review pending')
        require(isinstance(unit.get('components'), list) and unit['components'], 'Source needs obligation components')
        for component in unit['components']:
            require(isinstance(component, dict) and isinstance(component.get('id'), str) and component['id']
                    and component['id'] not in components, 'Duplicate/missing component IDs')
            field = component.get('source_field')
            original = source['original']
            require(field in original and isinstance(original[field], str), 'Unknown original source field')
            require(substantial(component.get('source_quote')) and component['source_quote'] in original[field],
                    'Source excerpt missing from original record')
            require(substantial(component.get('requirement')) and substantial(component.get('reason')),
                    'Concrete requirement and evidence-focused reason required')
            assessment = component.get('assessment')
            require(assessment in {'required', 'optional', 'already_answered', 'unsupported', 'unknown', 'duplicate'}, 'Invalid phase A assessment')
            evidence, occurrences = component.get('evidence'), component.get('occurrences')
            require(isinstance(evidence, list) and isinstance(occurrences, list), 'Component evidence/occurrences must be lists')
            if assessment not in {'unknown', 'duplicate'}:
                require(evidence, 'Supported assessment/withdrawal needs manuscript evidence')
            for anchor in evidence + occurrences:
                evidence_anchor(anchor, snapshot)
            components[component['id']] = (unit['source_id'], component)
    for cid, (_, component) in components.items():
        if component['assessment'] == 'duplicate':
            duplicate = component.get('duplicate_of')
            require(duplicate in components and duplicate != cid, 'Duplicate requires existing canonical component')
            canonical = components[duplicate][1]
            require(canonical['assessment'] != 'duplicate', 'Duplicate chains/cycles are not allowed')
            require(component['occurrences'] == canonical['occurrences'], 'Different occurrence locations cannot be silently deduplicated')
        else:
            require(not component.get('duplicate_of'), 'Nonduplicate component has duplicate target')
    return {'components': components, 'reviewer': provenance}


def adjudicate(audit_dir, ledger):
    audit_dir = Path(audit_dir).resolve()
    package, snapshot = verify_package(audit_dir)
    ledger = read(ledger) if isinstance(ledger, (str, Path)) else copy.deepcopy(ledger)
    result = validate_a(ledger, package, snapshot)
    require(not (audit_dir / 'phase_a.freeze.json').exists() and not (audit_dir / 'phase_a.adjudicated.json').exists(),
            'Phase A already frozen; create a new audit package for correction')
    save_new(audit_dir / 'phase_a.adjudicated.json', ledger)
    save_new(audit_dir / 'phase_a.freeze.json', {'sha256': digest(audit_dir / 'phase_a.adjudicated.json'),
              'package_sha256': value_digest(package), 'semantic_correctness_verified': False, 'reviewer': result['reviewer']})
    return {'status': 'phase_a_records_frozen', 'components': len(result['components']), 'semantic_correctness_verified': False}


def frozen_a(audit_dir, package, snapshot):
    audit_dir = Path(audit_dir).resolve()
    path = audit_dir / 'phase_a.adjudicated.json'
    require(path.exists() and (audit_dir / 'phase_a.freeze.json').exists(), 'Phase A not frozen; final comparisons remain hidden')
    freeze = read(audit_dir / 'phase_a.freeze.json')
    require(freeze.get('sha256') == digest(path) and freeze.get('package_sha256') == value_digest(package), 'Frozen phase A changed')
    ledger = read(path)
    return ledger, validate_a(ledger, package, snapshot), freeze['sha256']


def compare(audit_dir, report=None):
    audit_dir = Path(audit_dir).resolve()
    package, snapshot = verify_package(audit_dir)
    a_ledger, a_result, a_hash = frozen_a(audit_dir, package, snapshot)
    report = Path(report).resolve() if report is not None else None
    binding = {'path': str(report), 'sha256': digest(report)} if report else None
    packet = {'schema_version': SCHEMA, 'phase': 'B', 'instructions': B_INSTRUCTIONS, 'phase_a_sha256': a_hash,
              'frozen_adjudication': a_ledger, 'manuscript': snapshot['manuscript'], 'page_images': snapshot['page_images'],
              'routes': snapshot['routes'], 'final_targets': snapshot['final_targets'], 'report': binding,
              'comparison_groups': comparison_groups(snapshot, a_result['components'])}
    if report:
        packet['report_text'] = report.read_text(encoding='utf-8-sig')
    template = {'schema_version': SCHEMA, 'phase': 'B', 'audit_directory': str(audit_dir),
                'package_sha256': value_digest(package), 'phase_a_sha256': a_hash, 'phase_b_packet_sha256': value_digest(packet),
                'report': binding, 'reviewer': reviewer_template('frozen_a_and_final_outputs'),
                'components': [{'component_id': cid, 'status': 'pending', 'reason': '', 'target_quotes': [], 'report_quotes': [],
                                'uncertainty_visibility_review': {'status': 'pending', 'presented_as': None, 'reason': ''}}
                               for cid in a_result['components']]}
    require(not (audit_dir / 'phase_b.packet.json').exists() and not (audit_dir / 'phase_b.template.json').exists(),
            'Phase B already prepared; create a new audit package for changed comparisons')
    save_new(audit_dir / 'phase_b.packet.json', packet)
    save_new(audit_dir / 'phase_b.template.json', template)
    return {'status': 'pending_phase_b', 'components': len(template['components']), 'report_bound': bool(report),
            'semantic_correctness_verified': False}


def comparison_groups(snapshot, components):
    groups = []
    for target_id in sorted(snapshot['final_targets']):
        sources = sorted(sid for sid, route in snapshot['routes'].items() if target_id in route['final_ids'])
        if sources:
            groups.append({'target_id': target_id, 'source_ids': sources,
                           'component_ids': [cid for cid, (sid, _) in components.items() if sid in sources]})
    for sid, route in snapshot['routes'].items():
        if not route['final_ids']:
            groups.append({'target_id': None, 'source_ids': [sid],
                           'component_ids': [cid for cid, (source, _) in components.items() if source == sid]})
    return groups


def validate(ledger, report_path=None, require_ready=True):
    """Check B accounting, original hashes, frozen A, evidence and exact excerpts.

    Stale/invented/duplicate/missing records raise. require_ready=False exposes
    pending/missing/unresolved blockers for inspection. No semantic oracle runs.
    """
    ledger = read(ledger) if isinstance(ledger, (str, Path)) else ledger
    require(isinstance(ledger, dict) and ledger.get('schema_version') == SCHEMA and ledger.get('phase') == 'B', 'Invalid phase B ledger')
    audit_dir = Path(ledger.get('audit_directory', '')).resolve()
    package, snapshot = verify_package(audit_dir)
    a_ledger, a_result, a_hash = frozen_a(audit_dir, package, snapshot)
    require(ledger.get('package_sha256') == value_digest(package), 'Phase B package hash mismatch')
    require(ledger.get('phase_a_sha256') == a_hash, 'Phase B frozen adjudication hash mismatch')
    packet = read(audit_dir / 'phase_b.packet.json')
    require(value_digest(packet) == ledger.get('phase_b_packet_sha256') and packet.get('phase_a_sha256') == a_hash
            and packet.get('frozen_adjudication') == a_ledger and packet.get('routes') == snapshot['routes']
            and packet.get('final_targets') == snapshot['final_targets'] and packet.get('manuscript') == snapshot['manuscript']
            and packet.get('page_images') == snapshot['page_images']
            and packet.get('comparison_groups') == comparison_groups(snapshot, a_result['components']),
            'Phase B comparison packet changed')
    reviewer = review_provenance(ledger.get('reviewer'), 'B')
    require(ledger.get('report') == packet.get('report'), 'Phase B report binding changed')
    bound = ledger.get('report')
    if report_path is not None:
        require(bound is not None and Path(bound['path']).resolve() == Path(report_path).resolve(), 'Report must be bound before phase B review')
    report_text = None
    if bound:
        path = Path(bound['path'])
        require(path.is_file() and digest(path) == bound.get('sha256'), 'Report changed after phase B preparation')
        report_text = path.read_text(encoding='utf-8-sig')
        require(packet.get('report_text') == report_text, 'Phase B report text changed')
    reviewed, components = ledger.get('components', []), a_result['components']
    require(isinstance(reviewed, list) and len(reviewed) == len(components)
            and {r.get('component_id') for r in reviewed} == set(components), 'Phase B duplicate/missing component accounting')
    blockers, optional_missing, visible_unknown = [], [], []
    remaining_unknown = [cid for cid, (_, c) in components.items() if c['assessment'] == 'unknown']
    row_map = {r['component_id']: r for r in reviewed}
    for cid, row in row_map.items():
        sid, original = components[cid]
        status = row.get('status')
        require(status in {'pending', 'kept', 'missing', 'not_required', 'unresolved'}, 'Invalid phase B status')
        require(isinstance(row.get('target_quotes'), list) and isinstance(row.get('report_quotes'), list), 'Phase B target/report excerpts must be lists')
        if status == 'pending':
            blockers.append({'component_id': cid, 'reason': 'comparison pending'})
            continue
        require(substantial(row.get('reason')), 'Phase B component-specific reason required')
        assessment = original['assessment']
        if assessment == 'required':
            require(status in {'kept', 'missing', 'unresolved'}, 'Supported required component cannot be discarded')
        elif assessment == 'unknown':
            require(status == 'unresolved', 'Unknown necessity cannot be marked resolved')
        elif assessment in {'unsupported', 'already_answered', 'duplicate'}:
            require(status == 'not_required', 'Evidence-supported withdrawal/duplicate must remain not_required')
        if status == 'kept':
            require(row['target_quotes'], 'Kept obligation needs target excerpts')
            for target_quote in row['target_quotes']:
                require(isinstance(target_quote, dict), 'Target excerpt must be an object')
                target_id, field, quote = target_quote.get('target_id'), target_quote.get('field'), target_quote.get('quote')
                require(target_id in snapshot['routes'][sid]['final_ids'], 'Target ID outside original source lineage')
                target = snapshot['final_targets'][target_id]
                require(field in target and isinstance(target[field], str), 'Unknown target excerpt field')
                require(substantial(quote) and quote in target[field], 'Exact target excerpt missing/non-substantive')
            if report_text is not None:
                require(row['report_quotes'], 'Kept obligation needs actual report excerpts')
                for quote in row['report_quotes']:
                    require(substantial(quote) and quote in report_text, 'Exact report excerpt missing/non-substantive')
        elif assessment == 'unknown' and status == 'unresolved':
            require(not row['target_quotes'], 'Unknown unresolved obligation cannot claim retained target coverage')
            for quote in row['report_quotes']:
                require(report_text is not None and substantial(quote) and quote in report_text,
                        'Exact uncertainty report excerpt missing/non-substantive or report not bound')
            visibility = row.get('uncertainty_visibility_review', {})
            visible = (report_text is not None and bool(row['report_quotes'])
                       and visibility.get('status') == 'completed'
                       and visibility.get('presented_as') == 'unknown_or_author_confirmation'
                       and substantial(visibility.get('reason')))
            if visible:
                visible_unknown.append(cid)
        else:
            require(not row['target_quotes'] and not row['report_quotes'], 'Non-kept obligation cannot claim target coverage')
        if status in {'missing', 'unresolved'}:
            if status == 'missing' and assessment == 'optional':
                optional_missing.append(cid)
            elif assessment == 'unknown' and cid in visible_unknown:
                pass  # Disclosed uncertainty is deliverable, never resolved/certified.
            else:
                blockers.append({'component_id': cid, 'reason': status + ': ' + row['reason']})
        if assessment == 'duplicate':
            canonical = original['duplicate_of']
            if components[canonical][1]['assessment'] == 'required' and row_map[canonical]['status'] != 'kept':
                blockers.append({'component_id': cid, 'reason': 'canonical required component not kept: ' + canonical})
    result = {'status': 'records_validated', 'delivery_ready': not blockers, 'blockers': blockers,
              'optional_missing': optional_missing, 'visible_unknown': visible_unknown, 'remaining_unknown': remaining_unknown,
              'report_bound': bool(bound), 'semantic_correctness_verified': False,
              'selection_scope': package['selection'], 'audited_source_ids': package['selected_source_ids'],
              'reviewer_provenance': {'phase_a': a_result['reviewer'], 'phase_b': reviewer},
              'limit': 'Hashes, IDs and excerpt presence validate records; judgments require substantive review.'}
    if require_ready:
        require(result['delivery_ready'], 'Obligation audit not delivery ready: ' + json.dumps(blockers, ensure_ascii=False))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare')
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--max-batch-bytes', type=int)
    p = sub.add_parser('adjudicate')
    p.add_argument('--audit', type=Path, required=True)
    p.add_argument('--ledger', type=Path, required=True)
    p = sub.add_parser('compare')
    p.add_argument('--audit', type=Path, required=True)
    p.add_argument('--report', type=Path)
    p = sub.add_parser('check')
    p.add_argument('--ledger', type=Path, required=True)
    p.add_argument('--report', type=Path)
    p.add_argument('--allow-incomplete', action='store_true')
    args = parser.parse_args()
    try:
        if args.command == 'prepare':
            result = prepare(args.run, args.output, args.max_batch_bytes)
        elif args.command == 'adjudicate':
            result = adjudicate(args.audit, args.ledger)
        elif args.command == 'compare':
            result = compare(args.audit, args.report)
        else:
            result = validate(args.ledger, args.report, not args.allow_incomplete)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    main()
