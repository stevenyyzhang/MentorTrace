"""Account for retained obligations and facts in the actual final report.

Version 2 binds a separate target-to-evidence review to report blocks and draft
passages. Frozen version 1 records remain readable. This validates accounting,
hashes and quotations, not semantic truth or complete assertion splitting.
Run init, complete the ledger in a separate review, then run check.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def require(value, message):
    if not value:
        raise ValueError(message)


def has_text(value):
    return isinstance(value, str) and bool(value.strip())


def substantive_quote(value):
    # A separator cannot locate an obligation. Text presence still cannot prove
    # that a substantive excerpt preserves its meaning.
    return has_text(value) and any(char.isalnum() for char in value)


def text_digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def blocks(path):
    text = Path(path).read_text(encoding='utf-8-sig')
    if Path(path).suffix.lower() != '.json':
        return [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    data = json.loads(text)
    result = []
    # Preserve each evidence/requirement field separately, not just finding IDs.
    fields = ('anchor', 'relation', 'gap', 'impact', 'closure_goal', 'suggested_text',
              'current_order', 'proposed_order', 'reason', 'affected_links', 'conditions')
    for kind in ('findings', 'organization_suggestions'):
        for item in data.get(kind, []):
            for field in fields:
                if field in item:
                    result.append(json.dumps({'id': item['id'], 'field': field, 'value': item[field]}, ensure_ascii=False, sort_keys=True))
    if not result:
        raise ValueError('JSON source needs findings or organization_suggestions: ' + str(path))
    return result


def inventory(sources):
    units = []
    for index, source in enumerate(sources):
        path = Path(source['path'])
        if digest(path) != source['sha256']:
            raise ValueError('Source changed: ' + str(path))
        for number, text in enumerate(blocks(path), 1):
            units.append({'id': f'S{index + 1}:B{number}', 'text': text})
    return units


def target_inventory(report):
    """Inventory Markdown blocks and explicit Suggested wording passages.

    Heading and label blocks are included because their changes can alter a
    draft's stated readiness. Blank lines and horizontal separators are not
    assertions. This parser identifies format boundaries, never factual verbs.
    """
    units = []
    context = 'C0'
    heading_count = 0
    pending = []

    def add(text, kind='block'):
        if substantive_quote(text):
            units.append({'id': f'T:B{len(units) + 1}', 'kind': kind,
                          'text': text, 'sha256': text_digest(text),
                          'context_id': context})

    def flush():
        if pending:
            add('\n'.join(pending).strip())
            pending.clear()

    for line in Path(report).read_text(encoding='utf-8-sig').splitlines():
        if not line.strip():
            flush()
        elif re.match(r'^\s{0,3}#{1,6}\s+\S', line):
            flush()
            heading_count += 1
            context = f'C{heading_count}'
            add(line.strip())
        elif re.fullmatch(r'\s*(?:-{3,}|\*{3,}|_{3,})\s*', line):
            flush()
        else:
            pending.append(line)
    flush()

    drafts = []
    active = None
    marker = re.compile(r'^\*\*Suggested wording\s*/\s*建议文本:\*\*$', re.I)

    def finish():
        nonlocal active
        if active and active['member_ids']:
            text = '\n\n'.join(active.pop('parts'))
            drafts.append({**active, 'text': text, 'sha256': text_digest(text)})
        active = None

    for unit in units:
        is_marker = bool(marker.fullmatch(unit['text']))
        if active and (unit['context_id'] != active['context_id'] or is_marker):
            finish()
        if is_marker:
            active = {'id': f'T:D{len(drafts) + 1}', 'kind': 'suggested_wording',
                      'context_id': unit['context_id'], 'marker_id': unit['id'],
                      'member_ids': [], 'parts': []}
        elif active:
            active['member_ids'].append(unit['id'])
            active['parts'].append(unit['text'])
    finish()
    return units + drafts


def initialize(report, source_paths):
    sources = [{'path': str(Path(p).resolve()), 'sha256': digest(p)} for p in source_paths]
    units = inventory(sources)
    return {'version': 2, 'report': str(Path(report).resolve()), 'report_sha256': digest(report),
            'sources': sources, 'scope_review': {'reviewer': '', 'source_completeness': '', 'semantic_review': ''},
            'units': [{**u, 'components': [], 'non_substantive_reason': ''} for u in units],
            'target_review': {'reviewer': '', 'assertion_completeness': '', 'semantic_review': ''},
            'target_units': [{**u, 'review': {}} for u in target_inventory(report)]}


def validate_evidence(entries, message, factual=False):
    require(isinstance(entries, list) and bool(entries), message)
    for entry in entries:
        require(isinstance(entry, dict) and has_text(entry.get('path')), 'Evidence source missing')
        path = Path(entry['path'])
        require(path.is_file(), 'Evidence source missing: ' + str(path))
        require(digest(path) == entry.get('sha256'), 'Evidence source changed: ' + str(path))
        try:
            text = path.read_text(encoding='utf-8-sig')
        except (OSError, UnicodeError) as error:
            raise ValueError('Evidence needs a readable textual inspection/derivation record: ' + str(path)) from error
        require(substantive_quote(entry.get('quote')) and entry['quote'] in text,
                'Evidence excerpt absent: ' + str(path))
        if factual:
            require(entry.get('basis') in {'manuscript', 'direct_derivation'},
                    'Factual assertion needs manuscript or direct-derivation evidence')


def validate_target_review(ledger, report):
    expected = target_inventory(report)
    rows = ledger.get('target_units')
    require(isinstance(rows, list) and bool(expected), 'Missing final target inventory')
    fields = ('id', 'kind', 'text', 'sha256', 'context_id', 'marker_id', 'member_ids')
    signature = lambda row: [row.get(key) for key in fields]
    require(all(isinstance(row, dict) for row in rows) and
            [signature(row) for row in rows] == [signature(row) for row in expected],
            'Final target block missing or changed; re-review required')
    scope = ledger.get('target_review', {})
    require(isinstance(scope, dict) and all(has_text(scope.get(key)) for key in
            ('reviewer', 'assertion_completeness', 'semantic_review')),
            'Missing final target assertion-completeness/semantic review')
    blocks_by_id = {row['id']: row for row in expected if row['kind'] == 'block'}
    positions = {unit_id: index for index, unit_id in enumerate(blocks_by_id)}
    draft_by_member = {member: row for row in expected if row['kind'] == 'suggested_wording'
                       for member in row['member_ids']}

    def local_notice(notice, row, label):
        require(isinstance(notice, dict) and has_text(notice.get('reason')),
                label + ' needs a locally visible explanation')
        other = blocks_by_id.get(notice.get('target_unit_id'))
        require(other and substantive_quote(notice.get('quote')) and notice['quote'] in other['text'],
                label + ' excerpt absent from its referenced target block')
        if other['id'] == row['id']:
            return
        draft = draft_by_member.get(row['id'])
        if draft:
            local = (other['context_id'] == draft['context_id'] and
                     positions[other['id']] < positions[draft['marker_id']])
        else:
            local = (other['context_id'] == row['context_id'] and
                     positions[other['id']] + 1 == positions[row['id']])
        require(local, label + ' must be attached locally before the assertion/draft')

    for row in rows:
        review = row.get('review', {})
        require(isinstance(review, dict) and review.get('reviewed_sha256') == row['sha256'],
                'Target review missing or stale for ' + row['id'])
        require(all(has_text(review.get(key)) for key in ('reason', 'meaning_check', 'style_check')),
                'Target needs factual/meaning/style review: ' + row['id'])
        if row['kind'] == 'suggested_wording':
            require(has_text(review.get('assertion_completeness')),
                    'Suggested wording needs constituent assertion review: ' + row['id'])
            continue
        classification = review.get('classification')
        require(classification in {'factual', 'non_factual', 'action', 'explanatory'},
                'Target block needs a factual/non-factual classification: ' + row['id'])
        assertions = review.get('assertions', [])
        require(isinstance(assertions, list), 'Target assertions must be a list')
        if classification == 'factual':
            require(assertions, 'Factual target block needs reviewed assertions: ' + row['id'])
        for assertion in assertions:
            require(isinstance(assertion, dict) and substantive_quote(assertion.get('quote')) and
                    assertion['quote'] in row['text'], 'Target assertion excerpt absent: ' + row['id'])
            require(has_text(assertion.get('reason')), 'Target assertion needs a review rationale')
            status = assertion.get('status')
            require(status in {'supported', 'conditional', 'unresolved'}, 'Unprocessed target assertion')
            if status == 'supported':
                validate_evidence(assertion.get('evidence'),
                                  'Supported target assertion needs evidence', factual=True)
            elif status == 'conditional':
                local_notice(assertion.get('condition'), row, 'Author condition')
            else:
                local_notice(assertion.get('unresolved_notice'), row, 'Unresolved fact/action')
    return {'target_blocks': len(blocks_by_id),
            'suggested_wording_passages': sum(row['kind'] == 'suggested_wording' for row in expected)}


def validate(ledger, report, require_v2=False):
    report = Path(report).resolve()
    version = ledger.get('version')
    require(version in {1, 2}, 'Unsupported preservation ledger')
    require(not require_v2 or version == 2, 'New delivery requires a version 2 preservation ledger')
    require(str(report) == ledger['report'] and digest(report) == ledger['report_sha256'], 'Report changed; re-review required')
    require(ledger.get('sources'), 'No authoritative sources')
    expected = inventory(ledger['sources'])
    rows = ledger['units']
    require([(r['id'], r['text']) for r in rows] == [(r['id'], r['text']) for r in expected], 'Source block missing or changed')
    scope = ledger.get('scope_review', {})
    require(all(isinstance(scope.get(k), str) and scope[k].strip() for k in ('reviewer', 'source_completeness', 'semantic_review')), 'Missing source/semantic review')
    target = report.read_text(encoding='utf-8-sig')
    for row in rows:
        components = row.get('components', [])
        require(bool(components) != bool(row.get('non_substantive_reason')), 'Each source block needs obligations or a non-substantive rationale: ' + row['id'])
        for c in components:
            require(c.get('source_quote') and c['source_quote'] in row['text'], 'Obligation lacks exact source quote')
            require(c.get('obligation') and c.get('reason'), 'Missing obligation or disposition rationale')
            status = c.get('status')
            require(status in {'retained', 'revised', 'rejected', 'unresolved'}, 'Unprocessed obligation')
            quotes = c.get('target_quotes', [])
            require(isinstance(quotes, list) and all(has_text(q) and q in target for q in quotes), 'Target excerpt missing')
            if version == 2:
                require(all(substantive_quote(q) for q in quotes), 'Separator-only target excerpt cannot locate an obligation')
            elif quotes:
                # Preserve frozen mixed v1 excerpts, while closing the all-rule
                # mapping loophole. New v2 reviews do not retain those extras.
                require(any(substantive_quote(q) for q in quotes),
                        'Separator-only target excerpts cannot locate an obligation')
            if status != 'rejected':
                require(quotes, 'Retained/revised/unresolved obligation must be visible')
            if status in {'revised', 'rejected'}:
                validate_evidence(c.get('evidence', []), 'Changed obligation needs evidence')
    counts = validate_target_review(ledger, report) if version == 2 else {}
    return {'status': 'records_validated', 'version': version, 'source_blocks': len(rows), **counts,
            'semantic_correctness_verified': False,
            'limitation': ('Semantic coverage, factual support and assertion splitting depend on the recorded review; '
                           'this is not a proof of equivalence or truth.' if version == 2 else
                           'Frozen version 1 validates source-to-target records only, without a target factual inventory. '
                           'Semantic coverage depends on the recorded review; this is not a proof of equivalence.')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['init', 'check'])
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--ledger', type=Path, required=True)
    parser.add_argument('--source', type=Path, action='append', default=[])
    parser.add_argument('--require-v2', action='store_true', help='Reject legacy ledgers for new report delivery')
    args = parser.parse_args()
    if args.command == 'init':
        if args.ledger.exists():
            raise FileExistsError('Preserve the existing ledger; choose a new filename')
        if not args.source:
            parser.error('init requires --source')
        args.ledger.write_text(json.dumps(initialize(args.report, args.source), ensure_ascii=False, indent=2), encoding='utf-8')
    else:
        print(json.dumps(validate(read(args.ledger), args.report, require_v2=args.require_v2), ensure_ascii=False))


if __name__ == '__main__':
    main()
