"""Versioned delivery contracts. Locators/accounting are not semantic verdicts."""
import copy
import hashlib
import json


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def candidates(stage, response, plan=None):
    """Register explicit proposals and anchored unknowns, without diagnosing them."""
    rows = []
    def add(path, value, kind, text, anchors):
        if not isinstance(text, str) or not text.strip() or not anchors:
            return
        ident = stage + ':candidate:' + path.replace('/', ':')
        rows.append({'id': ident, 'kind': kind, 'origin_stage': stage,
                     'origin_path': path, 'source_sha256': digest(value),
                     'source': copy.deepcopy(value), 'text': text, 'anchors': anchors})
    for field, kind in [('optional_suggestions', 'optional'), ('uncertain_items', 'unknown'),
                        ('author_questions', 'unknown')]:
        for i, row in enumerate(response.get(field, [])):
            if not isinstance(row, dict):
                continue
            text = row.get('question') or row.get('reason') or row.get('description')
            add(f'{field}/{i}', row, kind, text, [row['anchor']] if row.get('anchor') else [])
    # Historical evidence_requests control source retrieval and remain on that path.
    # Register concrete manuscript questions, never convert a generic limit into a defect.
    tasks = response.get('reading_review', {}).get('multiscale', {}).get('tasks', [])
    for i, row in enumerate(tasks):
        if row.get('outcome') in {'unknown', 'unfinished'} and row.get('missing_information'):
            anchors = [e['anchor'] for e in row.get('endpoints', []) if e.get('anchor')]
            add(f'reading_review/multiscale/tasks/{i}', row, 'unknown', row['missing_information'], anchors)
    for i, row in enumerate(response.get('checks', [])):
        if row.get('judgment') == 'unknown' or row.get('execution') == 'unfinished':
            add(f'checks/{i}', row, 'unknown', row.get('required_relation'),
                [row['anchor']] if row.get('anchor') else [])
    if plan is not None:
        objects = {o['id']: o for o in plan.get('objects', []) + response.get('new_objects', [])}
        checks = response.get('checks', [])
        def locations(object_id, value, linked=()):
            found = value.get('anchors', []) or value.get('evidence', [])
            if not found:
                found = [c['anchor'] for c in checks if c.get('anchor') and
                         (c.get('object_id') == object_id or c.get('id') in linked)]
            if not found and objects.get(object_id, {}).get('anchor'):
                found = [objects[object_id]['anchor']]
            require(found, 'Concrete unresolved scope lacks an anchor; fix the record before integration')
            return found
        for item in response.get('technical_scope', []):
            for aspect in item.get('aspects', []):
                if aspect.get('status') in {'unknown', 'not_checked'}:
                    add('technical_scope/' + item['object_id'] + '/' + aspect['aspect'], aspect, 'unknown',
                        aspect['scope'] + ': ' + aspect['reason'], locations(item['object_id'], aspect))
        configs = plan.get('technical_configurations', []) + response.get('configuration_review', {}).get('additional_configurations', [])
        dimensions = {(c['id'], d['id']): d for c in configs for d in c.get('dimensions', [])}
        for item in response.get('configuration_review', {}).get('items', []):
            for row in item.get('dimension_reviews', []):
                if row.get('status') in {'unknown', 'unfinished'}:
                    d = dimensions.get((item['configuration_id'], row['dimension_id']), {})
                    add('configuration_review/' + item['configuration_id'] + '/' + row['dimension_id'], row, 'unknown',
                        (d.get('question') or 'Unresolved configuration question') + ': ' + row['reason'],
                        locations(None, d, row.get('check_ids', [])))
        basis = {r['id']: r for r in plan.get('coverage_basis', []) + response.get('new_coverage_basis', [])}
        for row in response.get('coverage_answers', []):
            if row.get('status') in {'partial', 'unknown', 'unfinished'}:
                require(row['basis_id'] in basis and row.get('remaining_question'), 'Unknown coverage basis/question')
                add('coverage_answers/' + row['basis_id'], row, 'unknown', row['remaining_question'], basis[row['basis_id']]['anchors'])
        # Same topic is NOT a duplicate. Keep distinct origins; Merge/Verify explicitly
        # consolidate equivalent requests through their existing candidate dispositions.
    return rows


def candidate_source(row):
    result = {'source_id': row['id'], 'source_type': 'candidate', 'checks': [],
            'original': {'id': row['id'], 'relation': row['text'],
                         'gap': row['text'], 'closure_goal': row['text'],
                         'anchor': row['anchors'][0], 'candidate_kind': row['kind'],
                         'source_record': row['source']},
            'source_sha256': digest(row)}
    result['source_sha256'] = hashlib.sha256(json.dumps(result['original'],ensure_ascii=False,indent=2).encode()).hexdigest()
    return result


def request_targets(response):
    """Lossless view of actual optional/question judgments; not invented findings."""
    return {r['candidate_id']: {'id': r['candidate_id'], 'anchor': r['anchor'],
            'closure_goal': r['author_action'], 'author_action': r['author_action'], 'conditions': r.get('conditions', ''),
            'request_type': r['status']}
            for r in response.get('candidate_reviews', [])
            if r['status'] in {'optional', 'author_confirmation'}}


INSTRUCTIONS = '''DELIVERY RELIABILITY v1:
Account for every delivery_candidate in candidate_reviews:[{candidate_id,
status:"incorporated|optional|author_confirmation|excluded",output_ids:[],reason,
evidence:[],anchor,author_action,conditions}]. These are candidates, not established defects.
Incorporated links to actual finding/organization IDs and preserves each concrete question.
Optional and author_confirmation need a specific anchored author_action, with conditions,
and no output_ids. Excluded needs manuscript evidence and a decisive reason. Duplicate
questions should incorporate into one actual surviving output, not disappear. Generic
limitations need no new author demand; explain exclusion. Do not treat unknown benefit as
unknown applicability. Style similarity is not evidence for a factual or grammatical error.
Verify independently adjudicates the original candidates; prior candidate decisions are
proposals, not authority. Preserve acceptable alternatives and every affected occurrence.
For source_requirement_resolutions return one row per supplied source component:
{component_id,assessment,reason,evidence:[],output_ids:[],delivery_action}.
assessment is required|optional|already_answered|unsupported|unknown|duplicate.
Use the same stable component ID; do not combine distinct questions under a topic label.
Required/optional need concrete delivery_action and actual output IDs. Unknown needs an
anchored author-confirmation output, not a generic unverified disclaimer. Rejections and
changed assessments need manuscript evidence. These explicit resolutions settle conflicts
before drafting; they never rewrite the original source review. If unresolved, preserve
the precise question rather than pretending it was verified. An implementation request
is not evidence that the implementation exists.
'''


SCOPE_INSTRUCTIONS = '''Check each actual object at its relevant level: definitions and physical
references; operation prerequisites; data generation; statistic/aggregation; displayed
quantity and interpretation. An algebraic pass cannot answer acquisition or calibration;
shared random inputs do not specify whether a plot is one trial or a summary. Mark actual
unknowns and unattempted relations distinctly. These are dimensions to consider, not a
fixed defect list or a requirement to request unnecessary experiments. Preserve adequate
existing explanations. Advisor does not receive this inventory.'''


def validate(stage, response, context, anchor):
    if not context.get('delivery_reliability'):
        return
    pages = {p['page']: p['text'] for p in context['manuscript']}
    targets = {f['id'] for key in ('findings', 'organization_suggestions') for f in response.get(key, [])}
    expected = {c['id'] for c in context.get('delivery_candidates', [])}
    rows = response.get('candidate_reviews', [])
    require(len(rows) == len(expected) and {r.get('candidate_id') for r in rows} == expected,
            'Missing/duplicate candidate disposition')
    for row in rows:
        status = row.get('status'); links = row.get('output_ids', [])
        require(status in {'incorporated', 'optional', 'author_confirmation', 'excluded'} and row.get('reason'), 'Invalid candidate disposition')
        require(set(links) <= targets, 'Candidate has unknown target')
        if status == 'incorporated':
            require(row.get('evidence'), 'Candidate incorporation needs evidence, not style analogy')
            require(bool(links), 'Incorporated candidate needs an actual target')
        else:
            require(not links, 'Non-incorporated candidate cannot claim target coverage')
        if status in {'optional', 'author_confirmation'}:
            require(isinstance(row.get('author_action'), str) and row['author_action'].strip(), 'Concrete author action missing')
            anchor(row.get('anchor', {}), pages)
        if status == 'excluded':
            require(row.get('evidence'), 'Candidate exclusion needs evidence')
        for e in row.get('evidence', []):
            anchor(e, pages)
    if stage != 'verify':
        return
    targets |= set(request_targets(response))
    components = {c['id']: c for u in context.get('initial_source_review', {}).get('source_requirements', []) for c in u['components']}
    decisions = response.get('source_requirement_resolutions', [])
    require(len(decisions) == len(components) and {d.get('component_id') for d in decisions} == set(components), 'Unresolved source-requirement accounting before drafting')
    for d in decisions:
        require(d.get('assessment') in {'required', 'optional', 'already_answered', 'unsupported', 'unknown', 'duplicate'} and d.get('reason'), 'Invalid source resolution')
        if d['assessment'] in {'required', 'optional', 'unknown'}:
            require(d.get('output_ids') and set(d['output_ids']) <= targets and d.get('delivery_action'), 'Source requirement lacks concrete delivery route')
            if d['assessment']=='unknown':
                confirmations={x['candidate_id'] for x in rows if x['status']=='author_confirmation'}
                confirmations.update(f['id'] for f in response.get('findings',[]) if f.get('request_type')=='author_confirmation')
                require(set(d['output_ids']) & confirmations, 'Unknown requirement needs an explicit author-confirmation route')
        else:
            require(not d.get('output_ids'), 'Excluded source requirement cannot claim coverage')
        # Explicit evidence is mandatory for all resolved scientific decisions, and
        # for a duplicate reference. Unknown remains a question with actual location.
        if d['assessment'] != 'unknown':
            require(d.get('evidence'), 'Source resolution needs manuscript evidence')
        for e in d.get('evidence', []):
            anchor(e, pages)


def apply_resolutions(ledger, final, provenance):
    decisions = {d['component_id']: d for d in final.get('source_requirement_resolutions', [])}
    for unit in ledger['units']:
        for c in unit.get('components', []):
            if c['id'] not in decisions:
                continue
            d = decisions[c['id']]
            # Duplicate elimination remains the source-only canonical decision;
            # Verify cannot invent a canonical link by changing a nonduplicate.
            require(d['assessment'] != 'duplicate' or c['assessment'] == 'duplicate', 'New duplicate requires source-only adjudication')
            c['original_assessment'] = c['assessment']
            c['assessment'] = d['assessment']; c['reason'] = d['reason']
            if d['assessment'] != 'duplicate':
                old_duplicate = c.pop('duplicate_of', None)
                if old_duplicate: c['original_duplicate_of'] = old_duplicate
            if d.get('evidence'): c['evidence'] = copy.deepcopy(d['evidence'])
            c['resolution_provenance'] = provenance
    ledger['resolution_note'] = 'Source-first review retained; explicit Verify resolutions applied before delivery, not a fresh independent A judgment.'
    return ledger


def original_text(pages, reference):
    """Only an exact frozen text span; no OCR repair or formula reconstruction."""
    page = next((p for p in pages if p['page'] == reference.get('page')), None)
    require(page is not None, 'Unknown Original page')
    require(reference.get('page_sha256') == hashlib.sha256(page['text'].encode()).hexdigest(), 'Original page changed')
    start, end = reference.get('span', (None, None))
    require(type(start) is int and type(end) is int and 0 <= start < end <= len(page['text']), 'Invalid Original span')
    return page['text'][start:end]
