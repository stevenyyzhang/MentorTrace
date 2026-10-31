"""Prepare conservative final-text carryover and pending IDs; no model calls."""
import argparse
import copy
import importlib.util
import json
import validation_cache
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


@validation_cache.scoped
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
    partial=previous.get('partial_review_version')==1
    local_sources=set();local_targets=set();local_errors=[]
    if partial and not previous_valid:
        # Establish immutable inventories/report/evidence before testing individual judgments.
        audit.require(str(previous_report.resolve())==previous['report'] and audit.digest(previous_report)==previous['report_sha256'],'Partial report binding changed')
        expected=audit.inventory(previous['sources'])
        audit.require([(x['id'],x['text']) for x in expected]==[(x['id'],x['text']) for x in previous['units']],'Partial source inventory changed')
        for row in previous['units']:
            try:audit.validate_source_row(row,previous_report.read_text(encoding='utf-8-sig'));local_sources.add(row['id'])
            except (ValueError,KeyError,TypeError,OSError) as error:local_errors.append({'id':row['id'],'error':str(error)})
        prepared=audit.prepare_target_validation(previous,previous_report)
        for row in previous['target_units']:
            try:audit.validate_target_review(previous,previous_report,{row['id']},prepared);local_targets.add(row['id'])
            except (ValueError,KeyError,TypeError,OSError) as error:local_errors.append({'id':row['id'],'error':str(error)})
    old_contexts = contexts(previous.get('target_units', []))
    new_contexts = contexts(fresh['target_units'])
    exact_sources = previous.get('sources') == fresh['sources']
    old_bindings=previous.get('sources',[])
    source_extension=bool(assessment and assessment.get('allow_append_only_sources') and old_bindings and
                          len(fresh['sources'])>len(old_bindings) and fresh['sources'][:len(old_bindings)]==old_bindings)
    # Appending history never changes the old source units; all new source units
    # remain pending. Existing context/evidence/affected-scope predicates still apply.
    same_sources = exact_sources or source_extension
    if (previous_valid or partial) and same_sources and previous.get('verified_review_reuse'):
        fresh['verified_review_reuse']=copy.deepcopy(previous['verified_review_reuse'])
    old_targets = {row['id']: row for row in previous.get('target_units', [])}
    if same_sources:
        for key in ['review_provenance_index','task_provenance','delivery_hardening','delivery_compact','history_binding']:
            if key in previous:fresh[key]=copy.deepcopy(previous[key])
    old_sources = {row['id']: row for row in previous.get('units', [])}
    safe_contexts = {key for key in new_contexts if new_contexts[key] == old_contexts.get(key)}
    candidate_targets = set()
    candidate_sources = set()
    if (previous_valid or partial) and same_sources:
        for row in fresh['target_units']:
            old = old_targets.get(row['id'])
            if old and (previous_valid or row['id'] in local_targets) and row['context_id'] in safe_contexts and unchanged_evidence(old.get('review')):
                candidate_targets.add(row['id'])
        for row in fresh['units']:
            old = old_sources.get(row['id'])
            if not old or (not previous_valid and row['id'] not in local_sources) or row['text'] != old['text'] or not unchanged_evidence(old):
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
    # Invalid records do not change identical report text or invalidate an
    # independent positive meaning/style judgment. Exclude those records alone.
    excluded=set((assessment or {}).get('invalid_record_task_ids',[]))
    candidate_targets-={i.split(':',1)[1] for i in excluded if i.startswith('target:')}
    candidate_sources-={i.split(':',1)[1] for i in excluded if i.startswith('source_field:')}
    carried_targets = candidate_targets if assessment is not None else set()
    carried_sources = candidate_sources if assessment is not None else set()
    language_pending=[]
    if previous.get('language_realization_required') or 'language_realization' in previous:
        fresh['language_realization_required']=True
        binding=copy.deepcopy(previous.get('language_realization',{}))
        old_review=binding.get('review',{});carried_groups=[]
        if binding.get('response') and Path(binding['response']['path']).is_file():
            audit.require(audit.digest(binding['response']['path'])==binding['response']['sha256'],'Previous language response binding changed')
            audit.require(audit.digest(binding['evidence']['path'])==binding['evidence']['sha256'],'Language evidence binding changed')
            response=audit.read(binding['response']['path'])
            old_response=response
            new_ref=(assessment or {}).get('language_response')
            if new_ref:
                audit.require(audit.digest(new_ref['path'])==new_ref['sha256'],'Changed language response binding')
                response=audit.read(new_ref['path'])
                audit.require(response['report_markdown']==Path(report).read_text(encoding='utf-8-sig'),'New language response does not match report')
                binding['response']=copy.deepcopy(new_ref)
            import expression_realization as realization
            evidence=audit.read(binding['evidence']['path'])
            realization.validate_draft(old_response,evidence);realization.validate_draft(response,evidence)
            old_drafts={r['draft_label']:r for r in old_response['language_realizations']}
            old_actions={r['draft_label']:r for r in old_response['revision_actions']}
            actions={r['draft_label']:r for r in response['revision_actions']}
            from delivery_runtime import language_contexts
            for draft in response.get('language_realizations',[]):
                texts=[p['text'] for p in draft.get('passages',[])]
                contexts_for_draft=language_contexts(draft,old_response,previous['target_units'])
                old_group=next((g for g in old_review.get('groups',[]) if g['draft_label']==draft['draft_label']),None)
                local_language_valid=False
                if old_group and old_drafts.get(draft['draft_label'])==draft and old_actions.get(draft['draft_label'])==actions.get(draft['draft_label']):
                    try:realization.validate_group(draft,old_group,Path(previous_report).read_text(encoding='utf-8-sig'));local_language_valid=True
                    except (ValueError,KeyError,TypeError):pass
                safe=(local_language_valid and 'language:'+draft['draft_label'] not in excluded and (previous_valid or partial) and assessment is not None and same_sources and
                    contexts_for_draft and contexts_for_draft<=safe_contexts and
                    not any(row['context_id'] in contexts_for_draft and row['id'] in affected_targets
                            for row in fresh['target_units']) and unchanged_evidence(binding['evidence']))
                old_group=next((g for g in old_review.get('groups',[]) if g['draft_label']==draft['draft_label']),None)
                if safe and old_group:carried_groups.append(old_group)
                else:language_pending.append(draft['draft_label'])
        binding['review']={'reviewer':'','groups':carried_groups,
            'carried_reviewer':old_review.get('reviewer'),'pending_draft_labels':language_pending}
        fresh['language_realization']=binding
    for row in fresh['target_units']:
        if row['id'] in carried_targets:
            row['review'] = copy.deepcopy(old_targets[row['id']]['review'])
    for index, row in enumerate(fresh['units']):
        if row['id'] in carried_sources:
            fresh['units'][index] = copy.deepcopy(old_sources[row['id']])
    coverage=None
    old_b_ref=(assessment or {}).get('previous_phase_b')
    if old_b_ref and same_sources:
        audit.require(audit.digest(old_b_ref['path'])==old_b_ref['sha256'],'Previous B binding changed')
        from delivery_runtime import coverage_carryover
        texts=['\n\n'.join(r['text'] for r in members if r['kind']=='block') for c,members in new_contexts.items() if c in safe_contexts and c not in {r['context_id'] for r in fresh['target_units'] if r['id'] in affected_targets}]
        coverage=coverage_carryover(old_b_ref['path'],previous_report,report,texts,(assessment or {}).get('affected_component_ids',[]))
    if coverage:fresh['coverage_carryover']=coverage
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
        'partial_review_eligible':partial,'local_errors':local_errors,
        'same_source_bindings': same_sources, 'report_sha256': fresh['report_sha256'],
        'previous_ledger_sha256': audit.digest(previous_ledger),
        'changed_context_ids': sorted(set(new_contexts) - safe_contexts),
        'candidate_source_ids': sorted(candidate_sources), 'candidate_target_ids': sorted(candidate_targets),
        'carried_source_ids': sorted(carried_sources), 'carried_target_ids': sorted(carried_targets),
        'pending_source_ids': [row['id'] for row in fresh['units'] if row['id'] not in carried_sources],
        'pending_target_ids': [row['id'] for row in fresh['target_units'] if row['id'] not in carried_targets],
        'global_scope_review_pending': True, 'report_bound_B_review_required': True,
        'pending_language_draft_labels':language_pending,
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
