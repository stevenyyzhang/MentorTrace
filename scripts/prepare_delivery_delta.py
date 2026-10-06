"""Prepare conservative final-text carryover and pending IDs; no model calls."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    'mentortrace_preservation_delta', ROOT / '.agents/skills/mentortrace/scripts/audit_report_preservation.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def contexts(rows):
    result = {}
    for row in rows:
        result.setdefault(row['context_id'], []).append({
            key: row.get(key) for key in ('id', 'kind', 'text', 'sha256', 'marker_id', 'member_ids')})
    return result


def unchanged_evidence(value):
    if isinstance(value, list):
        return all(unchanged_evidence(item) for item in value)
    if not isinstance(value, dict):
        return True
    if 'path' in value and 'sha256' in value:
        path = Path(value['path'])
        if not path.is_file() or audit.digest(path) != value['sha256']:
            return False
        if 'quote' in value:
            try:
                if value['quote'] not in path.read_text(encoding='utf-8-sig'):
                    return False
            except (UnicodeError, OSError):
                return False
    return all(unchanged_evidence(item) for item in value.values())


def prepare(previous_ledger, previous_report, report, source_paths=None, assessment=None):
    previous_ledger, previous_report, report = map(Path, (previous_ledger, previous_report, report))
    previous = audit.read(previous_ledger)
    fresh = audit.initialize(report, source_paths or [source['path'] for source in previous['sources']])
    # A stale previous report/source/evidence cannot establish valid carryover.
    try:
        audit.validate(previous, previous_report, require_v2=True)
        previous_valid = True
        previous_error = None
    except (ValueError, OSError, KeyError) as error:
        previous_valid = False
        previous_error = str(error)
    old_contexts = contexts(previous.get('target_units', []))
    new_contexts = contexts(fresh['target_units'])
    same_sources = previous.get('sources') == fresh['sources']
    old_targets = {row['id']: row for row in previous.get('target_units', [])}
    old_sources = {row['id']: row for row in previous.get('units', [])}
    safe_contexts = {key for key in new_contexts if new_contexts[key] == old_contexts.get(key)}
    candidate_targets = set()
    candidate_sources = set()
    if previous_valid and same_sources:
        for row in fresh['target_units']:
            old = old_targets.get(row['id'])
            if old and row['context_id'] in safe_contexts and unchanged_evidence(old.get('review')):
                candidate_targets.add(row['id'])
        for row in fresh['units']:
            old = old_sources.get(row['id'])
            if not old or row['text'] != old['text'] or not unchanged_evidence(old):
                continue
            quotes = [quote for component in old.get('components', [])
                      for quote in component.get('target_quotes', [])]
            complete = True
            for quote in quotes:
                located = [context for context, members in old_contexts.items()
                           if quote in '\n\n'.join(member['text'] for member in members
                                                  if member['kind'] == 'block')]
                if not located or any(context not in safe_contexts for context in located):
                    complete = False
                    break
            if complete:
                candidate_sources.add(row['id'])
    affected_targets, affected_sources = set(), set()
    if assessment is not None:
        audit.require(isinstance(assessment, dict), 'Affected-scope assessment must be an object')
        audit.require(assessment.get('previous_ledger_sha256') == audit.digest(previous_ledger) and
                      assessment.get('report_sha256') == fresh['report_sha256'], 'Affected-scope assessment is stale')
        for field in ('reviewer', 'reason', 'cross_context_review'):
            audit.require(audit.has_text(assessment.get(field)), 'Affected-scope assessment missing ' + field)
        for key, rows in [('affected_target_ids', fresh['target_units']), ('affected_source_ids', fresh['units'])]:
            values = assessment.get(key)
            audit.require(isinstance(values, list) and all(isinstance(value, str) for value in values) and
                          len(values) == len(set(values)) and set(values) <= {row['id'] for row in rows},
                          'Affected-scope assessment contains invalid IDs: ' + key)
        affected_targets = set(assessment['affected_target_ids'])
        affected_sources = set(assessment['affected_source_ids'])
        affected_contexts = {row['context_id'] for row in fresh['target_units'] if row['id'] in affected_targets}
        candidate_targets -= {row['id'] for row in fresh['target_units']
                              if row['context_id'] in affected_contexts}
        # A cross-context affected target also invalidates source mappings to it.
        for source_id in list(candidate_sources):
            quotes = [quote for component in old_sources[source_id].get('components', [])
                      for quote in component.get('target_quotes', [])]
            if any(quote in '\n\n'.join(member['text'] for member in old_contexts[context]
                                         if member['kind'] == 'block')
                   for quote in quotes for context in affected_contexts if context in old_contexts):
                candidate_sources.remove(source_id)
        candidate_sources -= affected_sources
    carried_targets = candidate_targets if assessment is not None else set()
    carried_sources = candidate_sources if assessment is not None else set()
    for row in fresh['target_units']:
        if row['id'] in carried_targets:
            row['review'] = copy.deepcopy(old_targets[row['id']]['review'])
    for index, row in enumerate(fresh['units']):
        if row['id'] in carried_sources:
            fresh['units'][index] = copy.deepcopy(old_sources[row['id']])
    fresh['carryover'] = {
        'previous_ledger': str(previous_ledger.resolve()), 'previous_ledger_sha256': audit.digest(previous_ledger),
        'previous_report_sha256': previous.get('report_sha256'),
        'source_reviewer_provenance': previous.get('scope_review'),
        'target_reviewer_provenance': previous.get('target_review'),
        'affected_scope_assessment': copy.deepcopy(assessment),
        'carried_source_ids': sorted(carried_sources), 'carried_target_ids': sorted(carried_targets),
        'limit': 'Exact local context/evidence checks plus recorded scope judgment; no semantic certification.'}
    plan = {
        'previous_valid': previous_valid, 'previous_validation_error': previous_error,
        'same_source_bindings': same_sources, 'report_sha256': fresh['report_sha256'],
        'previous_ledger_sha256': audit.digest(previous_ledger),
        'changed_context_ids': sorted(set(new_contexts) - safe_contexts),
        'candidate_source_ids': sorted(candidate_sources), 'candidate_target_ids': sorted(candidate_targets),
        'carried_source_ids': sorted(carried_sources), 'carried_target_ids': sorted(carried_targets),
        'pending_source_ids': [row['id'] for row in fresh['units'] if row['id'] not in carried_sources],
        'pending_target_ids': [row['id'] for row in fresh['target_units'] if row['id'] not in carried_targets],
        'global_scope_review_pending': True, 'report_bound_B_review_required': True,
        'semantic_correctness_verified': False}
    return fresh, plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous-ledger', type=Path, required=True)
    parser.add_argument('--previous-report', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--source', type=Path, action='append')
    parser.add_argument('--assessment', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    audit.require(not args.out.exists(), 'Refuse to overwrite an existing delta package')
    ledger, plan = prepare(args.previous_ledger, args.previous_report, args.report, args.source,
                           audit.read(args.assessment) if args.assessment else None)
    args.out.mkdir(parents=True)
    assessment_template = {
        'previous_ledger_sha256': plan['previous_ledger_sha256'], 'report_sha256': plan['report_sha256'],
        'reviewer': '', 'reason': '', 'cross_context_review': '',
        'affected_source_ids': [row['id'] for row in ledger['units']
                                if row['id'] not in plan['candidate_source_ids']],
        'affected_target_ids': [row['id'] for row in ledger['target_units']
                                if row['id'] not in plan['candidate_target_ids']]}
    for name, value in [('delivery.template.json', ledger), ('pending.json', plan),
                        ('assessment.template.json', assessment_template)]:
        (args.out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'pending_sources': len(plan['pending_source_ids']),
                      'pending_targets': len(plan['pending_target_ids']), 'model_calls': 0}))


if __name__ == '__main__':
    main()
