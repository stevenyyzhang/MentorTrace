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


def validate_cached(audit, request, model, effort, service_tier='default', output_path=None):
    mentortrace.require(audit.get('model') == model and audit.get('reasoning_effort') == effort,
                        'Cached response settings differ; do not relabel or silently rerun')
    mentortrace.require(audit.get('prompt_sha256') == hashlib.sha256(request['prompt'].encode('utf-8')).hexdigest(),
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
    prompt_sha = hashlib.sha256(request['prompt'].encode('utf-8')).hexdigest()
    image_shas = [i['sha256'] for i in request['images']]
    for audit_path in sorted(Path(stage_dir).glob('*/audit.json')):
        audit = mentortrace.read(audit_path)
        if (audit.get('model'), audit.get('reasoning_effort'), audit.get('requested_service_tier', 'default'),
            audit.get('prompt_sha256'), [i['sha256'] for i in audit.get('images', [])]) != (
                model, effort, service_tier, prompt_sha, image_shas):
            continue
        output = audit_path.parent / 'final_text.json'
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
    stage = request['stage']
    stage_dir = run / 'calls' / stage
    images = [mentortrace.safe_path(run, item['path']) for item in request['images']]
    for path, item in zip(images, request['images']):
        mentortrace.require(mentortrace.sha(path) == item['sha256'], 'Page image changed')
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
        model_output_path, usage = codex_adapter.invoke(
            call_dir, request['prompt'], images, model=args.model, reasoning_effort=args.effort,
            service_tier=args.service_tier, settings_authorization=authorization)
    output_path, _, unresolved = normalize_stage_response.normalize(run, stage, model_output_path)
    mentortrace.require(not unresolved, f'Unresolved source anchors in {stage}; inspect normalization log')
    mentortrace.validate(stage, mentortrace.read(output_path), mentortrace.context_for(run, stage))
    return {'stage': stage, 'output': str(output_path), 'model_output': str(model_output_path),
            'usage': usage, 'reused': cached is not None}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--stage", help="Prefetch an independent Advisor batch before its turn")
    parser.add_argument("--attempt-name", default="codex-authorized",
                        help="New transport folder for a reconciled failed network attempt")
    parser.add_argument("--model", default="gpt-6-sol")
    parser.add_argument("--effort", default="xhigh")
    parser.add_argument('--service-tier', choices=['default', 'fast', 'priority'], default='default')
    parser.add_argument('--settings-authorization', type=Path, required=True,
                        help='Recorded explicit human model/effort/tier choice; Fast additionally acknowledges usage')
    parser.add_argument('--prefetch-advisor', action='store_true', help='Prefetch only independent pending Advisor batches')
    parser.add_argument('--workers', type=int, choices=range(1, 5), default=2)
    parser.add_argument('--context-window', type=int, required=True,
                        help='Verified token capacity of the selected model')
    parser.add_argument('--output-reserve', type=int, required=True,
                        help='Reserve for reasoning and output; this does not set a CLI generation limit')
    parser.add_argument('--image-token-reserve', type=int, required=True,
                        help='Verified conservative upper bound per supplied page image')
    parser.add_argument('--safety-margin', type=int, default=4096)
    args = parser.parse_args()

    mentortrace.require(Path(args.attempt_name).name == args.attempt_name and
                        args.attempt_name not in {'.', '..', ''}, 'Attempt name must be a single directory name')
    authorization = mentortrace.read(args.settings_authorization)
    authorization_sha = validate_authorization(authorization, args.model, args.effort, args.service_tier)
    mentortrace.require(not (args.prefetch_advisor and args.stage), 'Choose --stage or --prefetch-advisor')

    run = args.run.resolve()
    next_request = mentortrace.next_request(run)
    mentortrace.require(next_request is not None, "Run is complete")
    settings = {'model': args.model, 'reasoning_effort': args.effort, 'service_tier': args.service_tier,
                'context_window': args.context_window, 'output_reserve': args.output_reserve,
                'image_token_reserve': args.image_token_reserve, 'safety_margin': args.safety_margin}
    pin_settings(run, settings)
    if args.prefetch_advisor:
        completed = mentortrace.read(run / 'state.json')['completed']
        requests = [mentortrace.prepare_stage_request(run, stage)
                    for stage in mentortrace.read(run / 'inputs/protocol.json')['stages']
                    if stage.startswith('supplement_') and stage not in completed]
        # Fail capacity preflight for the whole set before starting any paid work.
        for request in requests:
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
        print(json.dumps({"prefetched": stage, "output": str(output_path)}))
        return
    mentortrace.accept_response(run, output_path, {
        "kind": "isolated_codex_cli",
        "model": args.model,
        "reasoning_effort": args.effort,
        "requested_service_tier": args.service_tier,
        "settings_authorization_sha256": authorization_sha,
        "reused_completed_response": result['reused'],
        "usage": usage,
        "audit": str((call_dir / "audit.json").relative_to(run)),
        "model_output": str(model_output_path.relative_to(run)),
        "normalization_log": str((call_dir / "anchor_normalization.json").relative_to(run)),
        "fresh_context": True,
        "user_authorized_manuscript_disclosure": True,
    })
    response = mentortrace.read(stage_dir / "response.json")
    print(json.dumps({"accepted": stage, "findings": len(response.get("findings", []))}))


if __name__ == "__main__":
    main()
