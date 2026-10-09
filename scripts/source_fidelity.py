"""Source-fidelity accounting for new reviews; no OCR, model call or text repair.

Text candidates are inspection targets, not confirmed manuscript errors.
Validators check records and source hashes, not the truth of visual judgments.
"""
import re


INLINE_SPLIT = re.compile(r'\b[A-Za-z]{2,}[-\u2010\u00ad][ \t]+[A-Za-z]{2,}\b')


def surface_candidates(pages):
    result = []
    for page in pages:
        for number, match in enumerate(INLINE_SPLIT.finditer(page['text']), 1):
            result.append({
                'id': f"source:p{page['page']}:s{number}",
                'page': page['page'], 'kind': 'inline_hyphen_space',
                'quote': match.group(), 'start': match.start(), 'end': match.end(),
                'context': page['text'][max(0, match.start()-100):match.end()+100],
                'observation': 'Hyphen and whitespace within one extracted text line; verify physical placement on the page.',
            })
    return result


SURFACE_SCHEMA = '''SOURCE FIDELITY: Return source_candidate_dispositions:[{candidate_id,status:"definite_error|valid_source|extraction_artifact|unresolved",image_anchor:{page,kind:"image",description},image_sha256,reason,finding_ids:[],uncertain_ids:[]} for every INPUT.source_candidates exactly once, including [] when none. Inspect the original page before classifying a split. A same-line split is not automatically an author error; a line-end split is not automatically an artifact. Definite errors must link to anchored Language findings; unresolved candidates must link to uncertain_items with stable IDs. Valid source/artifact rows explain the observed layout and have no error links. Preserve raw spelling in observed excerpts; never silently join a candidate while checking the prose. A whole-page checked record does not dispose of these candidates.'''

VERIFY_SCHEMA = '''SOURCE FIDELITY: Return source_fidelity_checks covering every INPUT.input_findings ID and every new_in_stage finding ID exactly once. For an item whose allegation does not depend on a formula, use {input_id,status:"not_formula_dependent",reason}. For a formula-dependent item use {input_id,status:"confirmed|contradicted|unreadable",anchor:{page,kind:"image",description},image_sha256,decisive_expression,decisive_symbols:[{symbol,role}],extraction_difference,reason}. Transcribe the decisive original expression from the page image, with its equation number in the anchor, before adjudicating the allegation. Record the observed operators/delimiters, including their scope, that control this judgment; do not copy an earlier finding as source evidence. confirmed means the page supports the alleged formula premise, not that the entire criticism is correct. contradicted requires withdrawing the false allegation, or narrowing it with an explicit reason about the independently supported remainder. unreadable requires an unresolved disposition without confirmed output; never supply a guessed expression. For a readable formula, expression/symbol records and the matching frozen image hash are mandatory. Compare the raw extraction with the page, and report any difference in extraction_difference (or "none observed"). Repeated agreement across lanes does not resolve shared extraction corruption.'''


def _require(test, message):
    if not test:
        raise ValueError(message)


def _image(row, context, pages, anchor, unreadable=False):
    ref = row.get('image_anchor', row.get('anchor'))
    _require(isinstance(ref, dict) and ref.get('kind') == 'image', 'Source fidelity needs a page-image anchor')
    anchor(ref, pages)
    expected = {x['page']: x['sha256'] for x in context['source_page_images']}.get(ref['page'])
    if unreadable and expected is None:
        _require(row.get('image_sha256') is None, 'Missing image cannot have a claimed hash')
    else:
        _require(expected and row.get('image_sha256') == expected, 'Source fidelity image hash mismatch')
    return ref


def validate_candidates(response, context, pages, anchor):
    expected = {c['id']: c for c in context['source_candidates']}
    rows = response.get('source_candidate_dispositions')
    _require(isinstance(rows, list) and len(rows) == len(expected)
             and {r.get('candidate_id') for r in rows} == set(expected), 'Source candidate coverage missing or duplicated')
    findings = {f['id']: f for f in response['findings']}
    uncertain = {u['id']: u for u in response['uncertain_items'] if 'id' in u}
    for row in rows:
        _require(row.get('status') in {'definite_error', 'valid_source', 'extraction_artifact', 'unresolved'}
                 and row.get('reason'), 'Incomplete source candidate judgment')
        ref = _image(row, context, pages, anchor, unreadable=row['status'] == 'unresolved')
        _require(ref['page'] == expected[row['candidate_id']]['page'], 'Candidate inspection uses a different page')
        fids, uids = row.get('finding_ids'), row.get('uncertain_ids')
        _require(isinstance(fids, list) and isinstance(uids, list), 'Candidate disposition needs explicit links')
        _require(set(fids) <= set(findings) and set(uids) <= set(uncertain), 'Unknown source candidate output')
        if row['status'] == 'definite_error':
            _require(fids and not uids, 'Definite source error must become a Language finding')
            _require(all(findings[f]['anchor']['page'] == ref['page'] for f in fids), 'Candidate finding has a different page')
        elif row['status'] == 'unresolved':
            _require(uids and not fids, 'Unresolved source candidate needs a visible uncertainty record')
            for uid in uids:
                anchor(uncertain[uid].get('anchor', {}), pages)
                _require(uncertain[uid]['anchor']['page'] == ref['page'], 'Candidate uncertainty has a different page')
        else:
            _require(not fids and not uids, 'Valid source/artifact cannot assert a candidate error')


def validate_formula_checks(response, context, pages, anchor):
    inputs = {f['id'] for f in context['input_findings']}
    new = {f['id'] for f in response['findings'] if f.get('new_in_stage')}
    expected = inputs | new
    rows = response.get('source_fidelity_checks')
    _require(isinstance(rows, list) and len(rows) == len(expected)
             and {r.get('input_id') for r in rows} == expected, 'Source fidelity coverage missing or duplicated')
    dispositions = {d['input_id']: d for d in response['dispositions']}
    for row in rows:
        status = row.get('status')
        _require(status in {'confirmed', 'contradicted', 'unreadable', 'not_formula_dependent'}
                 and row.get('reason'), 'Incomplete source fidelity judgment')
        if status == 'not_formula_dependent':
            continue
        _image(row, context, pages, anchor, unreadable=status == 'unreadable')
        if status != 'unreadable':
            _require(isinstance(row.get('decisive_expression'), str) and row['decisive_expression'].strip(),
                     'Readable formula lacks original expression')
            symbols = row.get('decisive_symbols')
            _require(isinstance(symbols, list) and symbols
                     and all(s.get('symbol') and s.get('role') for s in symbols), 'Formula lacks decisive symbol inspection')
            _require(isinstance(row.get('extraction_difference'), str) and row['extraction_difference'].strip(),
                     'Formula extraction comparison missing')
        if status in {'contradicted', 'unreadable'}:
            disposition = dispositions.get(row['input_id'])
            _require(disposition is not None, 'Contradicted/unreadable new finding cannot be a confirmed output')
            if status == 'contradicted':
                _require(disposition['status'] in {'withdrawn', 'narrowed'}, 'Contradicted formula premise was retained')
            else:
                _require(disposition['status'] == 'unresolved' and not disposition['output_ids'],
                         'Unreadable formula cannot support a confirmed finding')
