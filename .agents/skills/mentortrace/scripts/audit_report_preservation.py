"""Account for source blocks and their semantic obligations before report delivery.

This validates records, hashes and quoted evidence, not semantic equivalence.
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


def initialize(report, source_paths):
    sources = [{'path': str(Path(p).resolve()), 'sha256': digest(p)} for p in source_paths]
    units = inventory(sources)
    return {'version': 1, 'report': str(Path(report).resolve()), 'report_sha256': digest(report),
            'sources': sources, 'scope_review': {'reviewer': '', 'source_completeness': '', 'semantic_review': ''},
            'units': [{**u, 'components': [], 'non_substantive_reason': ''} for u in units]}


def validate(ledger, report):
    def require(value, message):
        if not value:
            raise ValueError(message)
    report = Path(report).resolve()
    require(ledger.get('version') == 1, 'Unsupported preservation ledger')
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
            require(isinstance(quotes, list) and all(q and q in target for q in quotes), 'Target excerpt missing')
            if status != 'rejected':
                require(quotes, 'Retained/revised/unresolved obligation must be visible')
            if status in {'revised', 'rejected'}:
                evidence = c.get('evidence', [])
                require(evidence, 'Changed obligation needs evidence')
                for e in evidence:
                    path = Path(e['path'])
                    require(digest(path) == e['sha256'], 'Disposition evidence changed')
                    require(e.get('quote') and e['quote'] in path.read_text(encoding='utf-8-sig'), 'Disposition evidence excerpt absent')
    return {'status': 'records_validated', 'source_blocks': len(rows),
            'limitation': 'Semantic coverage depends on the recorded review; this is not a proof of equivalence.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['init', 'check'])
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--ledger', type=Path, required=True)
    parser.add_argument('--source', type=Path, action='append', default=[])
    args = parser.parse_args()
    if args.command == 'init':
        if args.ledger.exists():
            raise FileExistsError('Preserve the existing ledger; choose a new filename')
        if not args.source:
            parser.error('init requires --source')
        args.ledger.write_text(json.dumps(initialize(args.report, args.source), ensure_ascii=False, indent=2), encoding='utf-8')
    else:
        print(json.dumps(validate(read(args.ledger), args.report), ensure_ascii=False))


if __name__ == '__main__':
    main()
