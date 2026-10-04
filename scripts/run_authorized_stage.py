"""Submit one frozen MentorTrace request through an isolated Codex context.

Run only after the manuscript owner authorizes sending the request and page
images to the Codex model service. The original response is preserved before
the MentorTrace validator accepts it. A failed call is never retried here.
"""

import argparse
import hashlib
import json
from pathlib import Path

import codex_adapter
import mentortrace_v1 as mentortrace
import normalize_stage_response


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


def validate_cached(audit, request, model, effort):
    mentortrace.require(audit.get('model') == model and audit.get('reasoning_effort') == effort,
                        'Cached response settings differ; do not relabel or silently rerun')
    mentortrace.require(audit.get('prompt_sha256') == hashlib.sha256(request['prompt'].encode('utf-8')).hexdigest(),
                        'Cached prompt changed')
    mentortrace.require([i['sha256'] for i in audit.get('images', [])] ==
                        [i['sha256'] for i in request['images']], 'Cached images changed')


def pin_settings(run, settings):
    pinned = Path(run) / 'codex_transport_settings.json'
    if pinned.exists():
        mentortrace.require(mentortrace.read(pinned) == settings,
                            'Codex transport settings changed during this frozen run; create a new run')
    else:
        mentortrace.save(pinned, settings)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--stage", help="Prefetch an independent Advisor batch before its turn")
    parser.add_argument("--attempt-name", default="codex-authorized",
                        help="New transport folder for a reconciled failed network attempt")
    parser.add_argument("--model", default="gpt-6-sol")
    parser.add_argument("--effort", default="xhigh")
    parser.add_argument('--context-window', type=int, required=True,
                        help='Verified token capacity of the selected model')
    parser.add_argument('--output-reserve', type=int, required=True,
                        help='Reserve for reasoning and output; this does not set a CLI generation limit')
    parser.add_argument('--image-token-reserve', type=int, required=True,
                        help='Verified conservative upper bound per supplied page image')
    parser.add_argument('--safety-margin', type=int, default=4096)
    args = parser.parse_args()

    run = args.run.resolve()
    next_request = mentortrace.next_request(run)
    mentortrace.require(next_request is not None, "Run is complete")
    request = (mentortrace.prepare_stage_request(run, args.stage)
               if args.stage else next_request)
    stage = request["stage"]
    stage_dir = run / "calls" / stage
    images = [mentortrace.safe_path(run, item["path"]) for item in request["images"]]
    for path, item in zip(images, request["images"]):
        mentortrace.require(mentortrace.sha(path) == item["sha256"], "Page image changed")

    # The previous failed transport is retained in calls/objects. This new,
    # explicitly authorized attempt gets its own folder and audit trail.
    call_dir = stage_dir / args.attempt_name
    preflight = capacity_preflight(request, args.context_window, args.output_reserve,
                                   args.image_token_reserve, args.safety_margin)
    pin_settings(run, {'model': args.model, 'reasoning_effort': args.effort,
                       'context_window': args.context_window, 'output_reserve': args.output_reserve,
                       'image_token_reserve': args.image_token_reserve, 'safety_margin': args.safety_margin})
    if (call_dir / "audit.json").exists():
        output_path = call_dir / "final_text.json"
        cached = mentortrace.read(call_dir / 'audit.json')
        validate_cached(cached, request, args.model, args.effort)
        usage = cached['usage']
    else:
        call_dir.mkdir(parents=True, exist_ok=True)
        mentortrace.save(call_dir / 'capacity_preflight.json', preflight)
        output_path, usage = codex_adapter.invoke(
            call_dir, request["prompt"], images, model=args.model,
            reasoning_effort=args.effort,
        )
    model_output_path = output_path
    output_path, _, unresolved = normalize_stage_response.normalize(run, stage, model_output_path)
    mentortrace.require(not unresolved, f"Unresolved source anchors in {stage}; inspect normalization log")
    mentortrace.validate(stage, mentortrace.read(output_path), mentortrace.context_for(run, stage))
    if stage != next_request["stage"]:
        print(json.dumps({"prefetched": stage, "output": str(output_path)}))
        return
    mentortrace.accept_response(run, output_path, {
        "kind": "isolated_codex_cli",
        "model": args.model,
        "reasoning_effort": args.effort,
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
