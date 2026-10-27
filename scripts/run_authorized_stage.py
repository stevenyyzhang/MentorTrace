"""Submit one frozen MentorTrace request through an isolated Codex context.

Run only after the manuscript owner authorizes sending the request and page
images to the Codex model service. The original response is preserved before
the MentorTrace validator accepts it. A failed call is never retried here.
"""

import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import codex_adapter
import mentortrace_v1 as mentortrace
import normalize_stage_response
from execution_policy import validate_authorization


def capacity_preflight(request, context_window, output_reserve, image_token_reserve, safety_margin):
    """Conservative byte bound; caller supplies verified model/image limits."""
    mentortrace.require(all(isinstance(v, int) and v > 0 for v in
                            [context_window, output_reserve, image_token_reserve, safety_margin]),
                        "Positive verified context and image/output reserves are required")
    text_bound = len(request['prompt'].encode('utf-8'))
    total = text_bound + len(request['images']) * image_token_reserve + output_reserve + safety_margin
    mentortrace.require(total <= context_window, "Conservative capacity bound exceeded; no call sent. Never truncate the request")
    return {'method': 'UTF-8 byte upper bound for text plus caller-verified image reserve',
            'context_window': context_window, 'text_token_upper_bound': text_bound,
            'image_token_reserve_each': image_token_reserve, 'output_reserve': output_reserve,
            'safety_margin': safety_margin, 'total_reserved': total,
            'limits_verified_by_operator': True, 'exact_provider_token_count': False}


def matching_prompt(audit, request, output_path=None):
    expected = request['prompt'].encode('utf-8')
    if audit.get('prompt_sha256') == hashlib.sha256(expected).hexdigest():
        return True
    if output_path is None:
        return False
    path = Path(output_path).parent / 'prompt.txt'
    if not path.is_file():
        return False
    original = path.read_bytes()
    return (hashlib.sha256(original).hexdigest() == audit.get('prompt_sha256') and
            original.replace(b'\r\n', b'\n') == expected)


def validate_cached(audit, request, model, effort, service_tier='default', output_path=None):
    mentortrace.require(audit.get('model') == model and audit.get('reasoning_effort') == effort,
                        'Cached response settings differ; do not relabel or silently rerun')
    mentortrace.require(matching_prompt(audit, request, output_path),
                        'Cached prompt changed')
    mentortrace.require([i['sha256'] for i in audit.get('images', [])] ==
                        [i['sha256'] for i in request['images']], 'Cached images changed')
    mentortrace.require(audit.get('requested_service_tier', 'default') == service_tier,
                        'Cached service tier differs; preserve original settings')
    if output_path is not None:
        mentortrace.require(Path(output_path).is_file() and
                            audit.get('output_sha256') == mentortrace.sha(output_path),
                            'Cached output modified or legacy hash missing; inspect before reuse')


def find_cached(stage_dir, request, model, effort, service_tier='default'):
    matches = []
    image_shas = [i['sha256'] for i in request['images']]
    for audit_path in sorted(Path(stage_dir).glob('*/audit.json')):
        audit = mentortrace.read(audit_path)
        if (audit.get('model'), audit.get('reasoning_effort'), audit.get('requested_service_tier', 'default'),
            [i['sha256'] for i in audit.get('images', [])]) != (
                model, effort, service_tier, image_shas):
            continue
        output = audit_path.parent / 'final_text.json'
        if not matching_prompt(audit, request, output):
            continue
        validate_cached(audit, request, model, effort, service_tier, output)
        mentortrace.require(audit.get('returncode') == 0 and audit.get('usage') and
                            audit.get('fresh_ephemeral_context') is True,
                            'Cached completion/provenance missing; inspect before reuse')
        matches.append((output, audit))
    mentortrace.require(len({audit['output_sha256'] for _, audit in matches}) <= 1,
                        'Matching completed attempts disagree; inspect before reuse')
    return matches[0] if matches else None


def pin_settings(run, settings):
    pinned = Path(run) / 'codex_transport_settings.json'
    if pinned.exists():
        previous = mentortrace.read(pinned)
        previous.setdefault('service_tier', 'default')
        current = dict(settings)
        current.setdefault('service_tier', 'default')
        mentortrace.require(previous == current,
                            'Codex transport settings changed during this frozen run; create a new run')
    else:
        mentortrace.save(pinned, settings)


def execute_request(run, request, args, authorization):
    if request.get('capacity_plan'):
        return execute_capacity_plan(run,request,args,authorization)
    stage = request['stage']
    stage_dir = run / 'calls' / stage
    images = [mentortrace.safe_path(run, item['path']) for item in request['images']]
    for path, item in zip(images, request['images']):
        mentortrace.require(mentortrace.sha(path) == item['sha256'], 'Page image changed')
    automatic = getattr(args, 'auto_capacity', None)
    if automatic:
        from request_capacity import preflight as check_request
        preflight = check_request(request, automatic, run/'capacity_checks'/(stage+'.json'))
        if request.get('advisor_capacity'):
            mentortrace.require(request['advisor_capacity']['policy'] == automatic, 'Frozen packet capacity differs from transport')
    else:
        preflight = capacity_preflight(request, args.context_window, args.output_reserve,
                                       args.image_token_reserve, args.safety_margin)
    cached = find_cached(stage_dir, request, args.model, args.effort, args.service_tier)
    if cached:
        model_output_path, audit = cached
        usage = audit['usage']
    else:
        call_dir = stage_dir / args.attempt_name
        call_dir.mkdir(parents=True, exist_ok=True)
        mentortrace.save(call_dir / 'capacity_preflight.json', preflight)
        from advisor_budget import reserve_request
        reserve_request(run,request,args.attempt_name)
        capacity_options = {'context_window': automatic['context_window']} if automatic else {}
        model_output_path, usage = codex_adapter.invoke(
            call_dir, request['prompt'], images, model=args.model, reasoning_effort=args.effort,
            service_tier=args.service_tier, settings_authorization=authorization, **capacity_options)
    output_path, _, unresolved = normalize_stage_response.normalize(run, stage, model_output_path)
    mentortrace.require(not unresolved, f'Unresolved source anchors in {stage}; inspect normalization log')
    mentortrace.validate(stage, mentortrace.read(output_path), mentortrace.context_for(run, stage))
    return {'stage': stage, 'module_name': mentortrace.naming.display_name(stage), 'output': str(output_path), 'model_output': str(model_output_path),
            'usage': usage, 'reused': cached is not None}


def accept_result(run, result, args, authorization_sha):
    """Only the coordinator writes the ordered runtime state."""
    model_output = Path(result['model_output'])
    mentortrace.accept_response(run, Path(result['output']), {
        'kind': 'capacity_partitioned' if result.get('capacity_parts') else 'isolated_codex_cli', 'model': args.model,
        'reasoning_effort': args.effort, 'requested_service_tier': args.service_tier,
        'settings_authorization_sha256': authorization_sha,
        'reused_completed_response': result['reused'], 'usage': result['usage'],
        'audit': str((model_output.parent / 'audit.json').relative_to(run)),
        'model_output': str(model_output.relative_to(run)),
        'normalization_log': None if result.get('capacity_parts') else str((model_output.parent / 'anchor_normalization.json').relative_to(run)),
        'fresh_context': not bool(result.get('capacity_parts')), 'user_authorized_manuscript_disclosure': True,
        **({'actual_model_calls':result['capacity_parts'],'not_a_single_model_output':True} if result.get('capacity_parts') else {})})


def execute_capacity_plan(run,request,args,authorization):
    """Automatic exact-target partition execution; no confirmation or blind retry."""
    import stage_capacity, request_capacity
    plan=stage_capacity.validate_plan(run,request)
    mentortrace.require(plan['policy']==args.auto_capacity,'Capacity plan settings changed')
    stage=request['stage'];folder=run/'calls'/stage/'capacity_parts'
    # Validate every packet before paid work, keeping all shared evidence and images.
    for part in plan['parts']:
        request_capacity.preflight(part['request'],args.auto_capacity)
    parts=[];provenance=[];usage=[];all_cached=True
    for part in plan['parts']:
        req=part['request'];part_dir=folder/part['id']
        cached=find_cached(part_dir,req,args.model,args.effort,args.service_tier)
        if cached:raw,audit=cached;used=audit['usage']
        else:
            all_cached=False
            images=[mentortrace.safe_path(run,i['path']) for i in req['images']]
            for path,item in zip(images,req['images']):mentortrace.require(mentortrace.sha(path)==item['sha256'],'Page image changed')
            attempt=part_dir/args.attempt_name
            request_capacity.preflight(req,args.auto_capacity,attempt/'capacity_preflight.json')
            raw,used=codex_adapter.invoke(attempt,req['prompt'],images,model=args.model,reasoning_effort=args.effort,
                 service_tier=args.service_tier,settings_authorization=authorization,context_window=args.auto_capacity['context_window'])
        normalized,_,unresolved=normalize_stage_response.normalize(run,stage,raw)
        mentortrace.require(not unresolved,'Unresolved partition anchors; preserve original output')
        value=mentortrace.read(normalized);mentortrace.validate(stage,value,part['context'])
        parts.append((value,part['context']));usage.extend(used)
        provenance.append({'part':part['id'],'raw_path':str(raw),'raw_sha256':mentortrace.sha(raw),
                           'normalized_path':str(normalized),'normalized_sha256':mentortrace.sha(normalized),
                           'normalization_log':str(raw.parent/'anchor_normalization.json'),'reused':bool(cached)})
    combined=stage_capacity.combine(stage,parts,plan['source_context'])
    output=folder/'combined.json'
    if output.exists():mentortrace.require(mentortrace.read(output)==combined,'Combined partition output changed')
    else:mentortrace.save(output,combined)
    mentortrace.save(folder/'audit.json',{'not_a_single_model_output':True,'actual_model_calls':provenance,
         'assembly':'Exact returned-record union with deterministic output ID namespaces','output_sha256':mentortrace.sha(output)})
    return {'stage':stage,'module_name':mentortrace.naming.display_name(stage),'output':str(output),
            'model_output':str(output),'usage':usage,'reused':all_cached,'capacity_parts':provenance}


def parallel_initial(run, args, authorization, authorization_sha):
    """Submit isolated initial lanes; preserve serial acceptance and inspect-first failures.

    Object planning and case selection remain prerequisites for Reader/Expert.
    No worker accepts results or sees any other lane's output.
    """
    protocol = mentortrace.read(run / 'inputs/protocol.json')
    completed = mentortrace.read(run / 'state.json')['completed']
    mentortrace.require('objects' in completed, 'Complete object planning before parallel initial lanes')
    if mentortrace.goodpaper_enabled(run):
        mentortrace.verify_case_route(run)
    mentortrace.require(not mentortrace.read(run / 'state.json')['pending_evidence'],
                        'Resolve the recorded pending evidence request before starting another wave')
    initial = [s for s in protocol['stages'] if s in {'reader', 'technical', 'language'} or
               s.startswith('supplement_')]
    requests = [mentortrace.prepare_stage_request(run, s) for s in initial if s not in completed]
    # Check every complete prompt with the unchanged policy BEFORE any submission.
    for request in requests:
        if args.auto_capacity:
            from advisor_capacity import check_capacity
            check_capacity(request['prompt'], len(request['images']), args.auto_capacity)
        else:
            capacity_preflight(request, args.context_window, args.output_reserve,
                               args.image_token_reserve, args.safety_margin)
    lock = run / 'parallel_initial.lock'
    with lock.open('x', encoding='utf-8') as f:
        json.dump({'stages': [r['stage'] for r in requests], 'workers': args.workers}, f)
    results, failures, accepted, acceptance_blocked = {}, [], [], False
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            jobs = {pool.submit(execute_request, run, r, args, authorization): r['stage'] for r in requests}
            for future in as_completed(jobs):
                try:
                    result = future.result()
                    results[result['stage']] = result
                except Exception as error:
                    failures.append({'stage': jobs[future], 'error': str(error)})
                # Do not prepare merge, skip failed lanes or bypass pending evidence.
                while not acceptance_blocked and not mentortrace.read(run / 'state.json')['pending_evidence']:
                    done = mentortrace.read(run / 'state.json')['completed']
                    pending = next((s for s in protocol['stages'] if s not in done), None)
                    if pending not in results or pending not in initial:
                        break
                    try:
                        accept_result(run, results[pending], args, authorization_sha)
                        accepted.append(pending)
                    except Exception as error:
                        failures.append({'stage':pending,'error':str(error),'phase':'acceptance'})
                        acceptance_blocked = True
    finally:
        lock.unlink()
    receipt = {'accepted': accepted, 'completed': list(results.values()), 'failures': failures,
               'deferred': sorted(set(results) - set(accepted)), 'workers': args.workers,
               'independent_contexts': True, 'accepted_concurrently': False,
               'automatic_retry': False}
    mentortrace.save(run / 'parallel_initial_result.json', receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--stage", help="Stage ID (expert/editor aliases supported); independent Advisor batches may be prefetched")
    parser.add_argument("--attempt-name", default="codex-authorized",
                        help="New transport folder for a reconciled failed network attempt")
    parser.add_argument("--model", default="gpt-6-sol")
    parser.add_argument("--effort", default="xhigh")
    parser.add_argument('--service-tier', choices=['default', 'fast', 'priority'], default='default')
    parser.add_argument('--settings-authorization', type=Path, required=True,
                        help='Recorded explicit human model/effort/tier choice; Fast additionally acknowledges usage')
    parser.add_argument('--prefetch-advisor', action='store_true', help='Prefetch only independent pending Advisor batches')
    parser.add_argument('--parallel-initial', action='store_true', help='Run Reader/Expert/Advisor/Editor in isolated concurrent requests after planning/routing')
    parser.add_argument('--workers', type=int, choices=range(1, 5), help='Defaults to 3 for new parallel initial runs, otherwise 2; set 2 or 1 for constrained accounts')
    parser.add_argument('--context-window', type=int,
                        help='Verified token capacity of the selected model')
    parser.add_argument('--output-reserve', type=int,
                        help='Reserve for reasoning and output; this does not set a CLI generation limit')
    parser.add_argument('--image-token-reserve', type=int,
                        help='Verified conservative upper bound per supplied page image')
    parser.add_argument('--safety-margin', type=int, default=4096)
    args = parser.parse_args()

    mentortrace.require(Path(args.attempt_name).name == args.attempt_name and
                        args.attempt_name not in {'.', '..', ''}, 'Attempt name must be a single directory name')
    authorization = mentortrace.read(args.settings_authorization)
    authorization_sha = validate_authorization(authorization, args.model, args.effort, args.service_tier)
    mentortrace.require(sum(bool(v) for v in [args.prefetch_advisor, args.parallel_initial, args.stage]) <= 1,
                        'Choose --stage, --parallel-initial or --prefetch-advisor')

    run = args.run.resolve()
    protocol = mentortrace.read(run / 'inputs/protocol.json')
    args.auto_capacity = None
    manual = [args.context_window, args.output_reserve, args.image_token_reserve]
    mentortrace.require(all(v is None for v in manual) or all(v is not None for v in manual), 'Supply all legacy reserves or omit all for automatic detection')
    if protocol.get('advisor_batching_pending') or protocol.get('advisor_batching'):
        mentortrace.require(all(v is None for v in manual), 'Fixed-group v1.2 runs use detected capacity; remove manual reserve flags')
    if protocol.get('request_capacity')==1:
        mentortrace.require(all(v is None for v in manual), 'New complete-request capacity runs use automatic model metadata and unchanged reserves')
    if all(v is None for v in manual):
        from advisor_capacity import discover
        from advisor_batching import plan_run
        pinned = run / 'automatic_capacity.json'
        if pinned.exists():
            args.auto_capacity = mentortrace.read(pinned)
            mentortrace.require((args.auto_capacity['model'], args.auto_capacity['effort']) == (args.model, args.effort), 'Detected model/effort changed')
        else:
            args.auto_capacity = discover(args.model, args.effort)
            mentortrace.save(pinned, args.auto_capacity)
        if protocol.get('advisor_batching'):
            mentortrace.require(protocol['advisor_capacity'] == args.auto_capacity, 'Frozen automatic capacity differs')
        elif protocol.get('advisor_batching_pending') and (protocol.get('advisor_direct_fulltext') or 'advisor_tasks' in mentortrace.read(run / 'state.json')['completed']):
            plan_run(run, args.auto_capacity)
    next_request = mentortrace.next_request(run)
    mentortrace.require(next_request is not None, "Run is complete")
    settings = {'model': args.model, 'reasoning_effort': args.effort, 'service_tier': args.service_tier,
                'context_window': args.context_window, 'output_reserve': args.output_reserve,
                'image_token_reserve': args.image_token_reserve, 'safety_margin': args.safety_margin}
    if args.auto_capacity: settings['automatic_capacity'] = args.auto_capacity
    pin_settings(run, settings)
    initial_stage = next_request['stage'] in {'reader', 'technical', 'language'} or next_request['stage'].startswith('supplement_')
    use_parallel = args.parallel_initial or (protocol.get('review_efficiency') == 1 and initial_stage and
                                            not args.stage and not args.prefetch_advisor)
    args.workers = args.workers or (3 if use_parallel else 2)
    if use_parallel:
        result = parallel_initial(run, args, authorization, authorization_sha)
        print(json.dumps(result))
        if result['failures']:
            raise SystemExit(1)
        return
    if args.prefetch_advisor:
        completed = mentortrace.read(run / 'state.json')['completed']
        requests = [mentortrace.prepare_stage_request(run, stage)
                    for stage in mentortrace.read(run / 'inputs/protocol.json')['stages']
                    if stage.startswith('supplement_') and stage not in completed]
        # Fail capacity preflight for the whole set before starting any paid work.
        for request in requests:
            if args.auto_capacity:
                from advisor_capacity import check_capacity
                check_capacity(request['prompt'], len(request['images']), args.auto_capacity)
            else:
                capacity_preflight(request, args.context_window, args.output_reserve,
                                   args.image_token_reserve, args.safety_margin)
        results, failures = [], []
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            jobs = {pool.submit(execute_request, run, request, args, authorization): request['stage']
                    for request in requests}
            for future in as_completed(jobs):
                try:
                    results.append(future.result())
                except Exception as error:
                    failures.append({'stage': jobs[future], 'error': str(error)})
        print(json.dumps({'prefetched': results, 'failures': failures, 'accepted_concurrently': False}))
        if failures:
            raise SystemExit(1)
        return
    request = mentortrace.prepare_stage_request(run, args.stage) if args.stage else next_request
    stage = request["stage"]
    stage_dir = run / "calls" / stage
    result = execute_request(run, request, args, authorization)
    output_path, model_output_path = Path(result['output']), Path(result['model_output'])
    call_dir = model_output_path.parent
    usage = result['usage']
    if stage != next_request["stage"]:
        print(json.dumps({"prefetched": stage, "module_name": mentortrace.naming.display_name(stage), "output": str(output_path)}))
        return
    accept_result(run, result, args, authorization_sha)
    response = mentortrace.read(stage_dir / "response.json")
    print(json.dumps({"accepted": stage, "module_name": mentortrace.naming.display_name(stage), "findings": len(response.get("findings", []))}))


if __name__ == "__main__":
    main()
