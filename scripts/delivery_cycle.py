"""Bounded delivery closure: actual checkpoints -> pending corrections -> both gates.

Record recovery never edits reports; native v2 transactions renew affected reviews.
"""
import copy
import datetime
import json
import time
from pathlib import Path


def require(ok, message):
    if not ok:
        raise ValueError(message)


def actual_language_blockers(bundle, responses):
    """Explicit negative semantic verdicts require report work, not approval retries."""
    import review_workflow as w
    tasks = {t['id']: t for t in w.m.read(Path(bundle) / 'inventory.json')}
    result = []
    for path in responses:
        raw = w.m.read(path)
        for row in raw.get('results', []):
            ids = row.get('task_ids', [])
            if not any(tasks.get(t, {}).get('kind') == 'language' for t in ids):
                continue
            value = w.expand_judgments(row['value'], raw.get('judgments', {}))
            if not isinstance(value,dict):
                continue  # Canonical record inspection owns type failures; never invent a verdict.
            if any(value.get(k, {}).get('status') == 'fail' for k in ['meaning', 'naturalness']) or any(
                    r.get('status') == 'rejected' for r in value.get('feature_results', [])):
                result.append({'task_ids': ids, 'actual_language_verdict': value,
                               'reason': 'Actual meaning/style/realization failure requires a report correction.'})
    return result


def checkpoint(bundle, responses, out):
    import review_workflow as w
    out = Path(out)
    if (out / 'checkpoint.json').is_file():
        return out / 'checkpoint.json'
    try:
        w.assemble_delivery(bundle, responses, out)
    except (ValueError, KeyError, TypeError) as error:
        require((out / 'checkpoint.json').is_file(), 'No trustworthy partial checkpoint: ' + str(error))
        w.m.save(out / 'assembly_failure.json', {'error': str(error), 'not_deliverable': True})
    return out / 'checkpoint.json'


def prepare(bundle, responses, out, rule_compatibility=None):
    """Offline, resumable preparation from unchanged actual output; no model call."""
    import review_workflow as w
    import prepare_delivery_delta as delta
    import review_contract
    bundle = Path(bundle).resolve(); out = Path(out).resolve()
    manifest = w.verify_bundle(bundle); ctx = w.m.read(bundle / 'context.json')
    require(ctx.get('delivery_compact') and ctx.get('delivery_reliability'), 'Bounded cycle requires v2 and recoverable checkpoints')
    identity = {'bundle': str(bundle), 'manifest_sha256': w.m.sha(bundle / 'manifest.json'),
                'responses': {str(Path(p).resolve()): w.m.sha(p) for p in responses}}
    plan_path = out / 'correction_plan.json'
    if plan_path.exists():
        result = w.m.read(plan_path)
        require(result['identity'] == identity, 'Correction folder belongs to different actual outputs')
        w.verify_bundle(result['bundle'])
        return result
    out.mkdir(parents=True, exist_ok=True)
    cp = checkpoint(bundle, responses, out / 'checkpoint')
    previous = w.m.read(cp); report = Path(previous['report'])
    values,_=w.collect(bundle,responses,allow_partial=True)
    all_tasks=w.m.read(bundle/'inventory.json');byid={t['id']:t for t in all_tasks}
    all_issues=review_contract.inspect(all_tasks,values,ctx)+w.delivery_efficiency.inspect_values(all_tasks,values)
    for p in responses:
        raw=w.m.read(p);request=w.m.read(bundle/next(e['file'] for e in manifest['packets'] if e['id']==raw['packet_id']))
        assigned=[byid[k] for k in request['task_ids']]
        all_issues+=w.recovery.inspect(assigned,values,ctx,raw.get('evidence_records',[]))
        all_issues += [{**issue,'task_id':t['id']} for issue in review_contract.inspect_records(raw,manifest['bindings'],ctx.get('page_images',[])) for t in assigned]
    invalid={i['task_id'] for i in all_issues if i.get('task_id') in byid}
    # The report, context and sources are exactly unchanged. This is not a semantic
    # affected-scope guess for an edited report. Every positive local record is
    # independently revalidated by delta; the global judgment is always fresh.
    assessment = {'previous_ledger_sha256': w.m.sha(cp), 'report_sha256': w.m.sha(report),
                  'reviewer': 'Deterministic unchanged-report recovery',
                  'reason': 'Identical full report and frozen sources; revalidate actual local records.',
                  'cross_context_review': 'No text/context was edited. Reuse only validated actual records; global dependencies remain a fresh task.',
                  'affected_source_ids': [], 'affected_target_ids': [],
                  'invalid_record_task_ids': sorted(invalid),
                  'affected_component_ids': sorted(byid[i]['key'] for i in invalid if byid[i]['kind']=='coverage'),
                  'previous_phase_b': {'path': str((out / 'checkpoint/checkpoint_phase_b.json').resolve()),
                                       'sha256': w.m.sha(out / 'checkpoint/checkpoint_phase_b.json')}}
    if rule_compatibility is not None:assessment['local_rule_compatibility']=copy.deepcopy(rule_compatibility)
    fresh, pending = delta.prepare(cp, report, report, assessment=assessment)
    ledger_path = out / 'delta.json'; w.m.save(ledger_path, fresh)
    corrected = out / 'bundle'
    contract = ctx.get('delivery_contract', {})
    w.prepare_delivery(ctx['audit_directory'], ledger_path, corrected, manifest['policy'],
                       fidelity=contract.get('verified_delivery_fidelity', False),
                       concise=contract.get('report_concision', False), recoverable=True)
    # Supply all known defects together, and only to the tasks that must correct them.
    values, _ = w.collect(bundle, responses, allow_partial=True)
    tasks = w.m.read(bundle / 'inventory.json')
    issues = all_issues
    original_values = {}
    for p in responses:
        raw = w.m.read(p)
        issues.extend({'task_id':e['task_id'],'problem':e['error'],'kind':'format'} for e in raw.get('protocol_errors',[]) if e.get('task_id'))
        for row in raw.get('results', []):
            for tid in row.get('task_ids', []):
                original_values[tid] = copy.deepcopy(row['value'])
    next_ctx = w.m.read(corrected / 'context.json')
    next_tasks = w.m.read(corrected / 'inventory.json')
    feedback = {}
    for task in next_tasks:
        if task['kind'] == 'global_scope':
            continue
        feedback[task['id']] = {'actual_prior_value': original_values.get(task['id']),
                               'known_defects': [i for i in issues if i.get('task_id') == task['id']],
                               'local_validation': [e for e in pending.get('local_errors', []) if e.get('id') == task['key']]}
    # Requests are still unsubmitted. Rebuild with feedback using the SAME canonical
    # preparer; do not edit hashes or relabel a repair output as an old response.
    if feedback:
        next_ctx['correction_feedback'] = feedback
        enriched = out / 'ready'
        prepared = w.prepare_bundle(enriched, 'delivery', next_ctx, next_tasks,
                                    w.m.read(corrected / 'manifest.json')['bindings'], manifest['policy'])
        corrected = enriched
    else:
        prepared = w.m.read(corrected / 'manifest.json')
    result = {'identity': identity, 'bundle': str(corrected), 'checkpoint': str(cp),
              'pending_task_ids': prepared['task_ids'], 'pending': pending,
              'carried_coverage': len(next_ctx.get('delivery_carryover', {}).get('coverage', [])),
              'new_model_calls': 0, 'report_edited': False,
              'origin': 'Actual prior judgments retained with their native evidence/provenance; failed records are not passed.'}
    w.m.save(plan_path, result)
    return result


def assemble_or_resume(bundle,responses,out):
    """An interruption after assembly must not turn success into a new model task."""
    import review_workflow as w
    out=Path(out);ctx=w.m.read(Path(bundle)/'context.json')
    if (out/'preservation.json').is_file() and (out/'phase_b.json').is_file():
        w.collect(bundle,responses)
        report=ctx['report_correspondence_evidence']['path']
        preservation=w.preservation.validate(w.m.read(out/'preservation.json'),report,require_v2=True)
        consolidation=w.audit.validate(w.m.read(out/'phase_b.json'),report,require_ready=True)
        return out,{'preservation':preservation,'consolidation':consolidation,'semantic_correctness_verified':False}
    # Preserve incomplete assembly debris. Rebuild only local files from completed
    # provider outputs; do not confuse interrupted persistence with a report defect.
    fresh=out;number=0
    while fresh.exists():
        number+=1;fresh=out.with_name(out.name+'-recovered-'+str(number))
    return fresh,w.assemble_delivery(bundle,responses,fresh)


def execute_records(bundle, calls, args, authorization):
    """CLI v2 default: at most one correction wave after known completed results."""
    import review_workflow as w
    import run_review_packet as runner
    import execution_policy
    bundle = Path(bundle).resolve(); calls = Path(calls).resolve()
    w.verify_bundle(bundle)
    execution_policy.validate_authorization(authorization, args.model, args.effort, args.service_tier)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat(); timer = time.monotonic()
    calls.mkdir(parents=True, exist_ok=True)
    lock = calls / 'delivery-cycle.lock'
    from native_delivery import locked
    guard=locked(lock);guard.__enter__()
    try:
        binding = {'bundle': str(bundle), 'manifest_sha256': w.m.sha(bundle / 'manifest.json'),
                   'model': args.model, 'effort': args.effort, 'service_tier': args.service_tier}
        pinned = calls / 'cycle_binding.json'
        if pinned.exists():
            require(w.m.read(pinned) == binding, 'Cycle settings or frozen inputs changed')
        else:
            w.m.save(pinned, binding)
        complete = calls / 'delivery_result.json'
        if complete.exists():
            old = w.m.read(complete)
            # Bind actual old raw outputs and actual execution audits on resume too.
            for wave in old['waves']:
                w.collect(wave['bundle'],wave['responses'],allow_partial=True)
            # Revalidate both native gates even when no provider submission is needed.
            w.preservation.validate(w.m.read(old['preservation']), old['report'], require_v2=True)
            w.audit.validate(w.m.read(old['phase_b']), old['report'], require_ready=True)
            return old
        waves = []; active = bundle
        for wave in range(2):
            receipt = runner.execute_bundle(active, calls / ('initial' if wave == 0 else 'correction'), args, authorization)
            waves.append(receipt)
            failures = receipt.get('failed', [])
            actual_bundle = Path(receipt['bundle'])
            actual_responses = receipt['responses']
            language_blockers = actual_language_blockers(actual_bundle, actual_responses)
            if not failures:
                assembled = calls / ('accepted-initial' if wave == 0 else 'accepted-correction')
                try:
                    assembled, validation = assemble_or_resume(actual_bundle, actual_responses, assembled)
                    result = {'ready_for_assembly': True, 'delivery_ready': True, 'report': w.m.read(actual_bundle / 'context.json')['report_correspondence_evidence']['path'],
                              'preservation': str(assembled / 'preservation.json'), 'phase_b': str(assembled / 'phase_b.json'),
                              'validation': validation, 'correction_waves': wave, 'waves': waves,
                              'started_utc': started, 'wall_seconds': time.monotonic() - timer,
                              'report_edited': False, 'automatic_transport_retry': False}
                    w.m.save(complete, result)
                    return result
                except (ValueError, KeyError, TypeError) as error:
                    # Actual semantic/report blockers are not fixed by repeatedly
                    # asking the reviewer to approve the same manuscript/report.
                    failures = [{'phase': 'native_delivery_gates', 'error': str(error)}]
            if wave == 1 or language_blockers or any(f.get('phase') not in {'local_result_check'} for f in failures):
                result = {'ready_for_assembly': False, 'delivery_ready': False, 'waves': waves,
                          'failed': failures, 'correction_waves': wave, 'automatic_transport_retry': False,
                          'reason': 'Stopped: correction limit, uncertain transport, or genuine report/global/native-gate issue. Preserve actual results; no approval-seeking retry.',
                          'wall_seconds': time.monotonic() - timer}
                if language_blockers:
                    result['language_blockers'] = language_blockers
                    result['checkpoint'] = str(checkpoint(actual_bundle, actual_responses, calls / 'blocked-language'))
                semantic=bool(language_blockers) or any(f.get('phase') in {'global_result_check','native_delivery_gates'} for f in failures)
                result['continuation_required']=True
                result['next_action']='revise_report_and_recheck_affected' if semantic else 'inspect_saved_execution_and_repair_pending'
                result['user_input_required']=False
                result['continuation_note']='This stops the current reviewer wave, not the authorized task. The skill coordinator must inspect saved actual defects, fix execution or create a separate report revision, preserve valid judgments, and renew affected locals plus global and both gates. Never resubmit an unchanged negative report for a pass.'
                w.m.save(calls / 'continuation.json',result)
                w.m.save(calls / 'needs_attention.json', result)
                return result
            plan = prepare(actual_bundle, actual_responses, calls / 'correction-plan')
            active = Path(plan['bundle'])
        raise AssertionError('Unreachable correction loop')
    finally:
        guard.__exit__(None,None,None)


def execute(bundle,calls,args,authorization):
    import review_workflow as w
    if w.m.read(Path(bundle)/"context.json").get("native_report_repair"):
        return __import__("native_delivery").execute(bundle,calls,args,authorization)
    return execute_records(bundle,calls,args,authorization)


def main():
    import argparse
    import review_workflow as w
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--responses', nargs='+', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(prepare(args.bundle, args.responses, args.out)))


if __name__ == '__main__':
    main()
