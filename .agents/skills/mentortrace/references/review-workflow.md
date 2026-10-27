# Combined review workflow

New adaptive runs pin `review_efficiency: 1`. Earlier frozen runs retain their
protocols. This changes scheduling and record production, not source coverage,
Advisor independence, capacity allowances, model, effort or service tier.

## Independent initial lanes

Complete the existing object plan and freeze task-to-case selection for
Reader/Expert. The authorized runner then defaults to parallel initial execution:
Reader, Expert, Advisor batches and Editor use separate frozen requests and fresh
contexts. Advisor receives the full paper and its assigned libraries, without
object plans, Reader/Expert cases, initial opinions or reports. Every primary
Concern/Expression, including unlinked cases, still needs an explicit decision.
Unlisted associations remain not_assessed.

`run_authorized_stage.py --parallel-initial` also selects this scheduler explicitly.
It defaults to three workers; `--workers 2` or `1` supports constrained transports.
This is ordinary concurrency, not Fast authorization. Workers never accept shared
runtime state; the coordinator accepts results in the existing stage order.
Check all complete requests against unchanged capacity limits before sending.
Merge waits for all initial lanes and pending evidence. A failed attempt is not
automatically retried; completed other lanes remain saved/reusable while the
failure is inspected. A stale coordinator lock requires checking saved status.

## Source-only check and diagnosis freeze

After initial freeze, combine initial-execution and original-requirement review:

```text
python scripts/review_workflow.py prepare-source --run RUN --policy RUN/automatic_capacity.json --out SOURCE
```

The inventory includes every actual check, every stage's assigned/declared scope,
and every nonsurface finding/organization requirement. Complete original
same-stage records and analysis-ID mappings are supplied. Later decisions and
reports are withheld. The reviewer assesses execution and original requirements
together, retaining separate supported, optional, unsupported and unknown
judgments. Do not add another initial-execution call or repeat this decomposition
in a separate later A pass. An unattempted check is not an author error.

For actual authorized submission, `run_review_packet.py --bundle SOURCE --calls CALLS
--model MODEL --effort EFFORT --service-tier default --settings-authorization AUTH`
defaults to three isolated workers for all packets in this frozen source bundle.
Use `--workers 1` or `2` for constrained transports; `--packet source-001` retains
explicit single-packet execution. Use the same pinned settings and reserves.
The program binds request IDs/hashes
to untouched model output; models supply judgments, not transport metadata.

```text
python scripts/review_workflow.py assemble-source --bundle SOURCE --responses RESULTS... --out RUN/initial_review.json
```

Verify consumes these bound source assessments/execution issues as hypotheses.
Resolve supported omissions and contradictions before diagnosis freeze and
drafting. The source reviewer has not seen Verify or the report. Keep all original
provenance; completed unknowns remain unknown.

After ordinary audit preparation, reuse matching source-only A records:

```text
python scripts/review_workflow.py seed-a --source-review RUN/initial_review.json --audit AUDIT --out A.json
```

Reuse requires identical originals, checks, manuscript and page images. New merge
sources or duplicate canonical components outside selection remain pending. Use
`prepare-a-delta --audit AUDIT --seed A.json --policy RUN/automatic_capacity.json
--out A_DELTA`, then `complete-a --audit AUDIT --seed A.json --bundle A_DELTA
--responses RESULTS... --out A_COMPLETE.json`. The delta still sees originals
only. Freeze complete A with existing `adjudicate`; pending is never a pass.

## One combined delivery check

New adaptive runs enable `verified_delivery_fidelity: 1` and `report_concision: 1`.
Independent initial review and formal Verify remain mandatory. After diagnosis
freeze, explicitly compare each delivered assertion with its complete accepted
diagnostic statement. An unchanged claim may use `reused_verified` only with a
bound verification chain and an explicit same-claim, preserved-conditions and
uncertainty, no-new-fact comparison. This reuses a judgment; it is not fresh paper
evidence. Only accepted `relation`, `gap`, and `impact` fields qualify. Requested
future actions do not prove what the authors have done. New facts, broader claims,
changed conditions, contradictions or uncertain equivalence still need ordinary
grounding or an explicit conditional/unresolved disposition. Missing chain means
ordinary checks, never automatic approval. Every task still needs a result.

Draft the diagnosis/consequence once in its Comment, then concrete repair actions.
Share common actions without removing local conditions or bilingual content. Keep
complete supported rewrites; when facts are unavailable, specify what to supply
and where, rather than a replacement paragraph filled with placeholders. The
same combined delivery review explicitly checks concision and placeholder
candidates in `global_scope.report_economy`; it adds no separate model call.
Mechanical detection is not a semantic verdict, and scientific notation requires
manuscript evidence before dismissing a candidate. Do not shorten by deleting
independent requirements, small errors, useful derivations or source coverage.

Keep one draft step. Programs generate IDs, locations, hashes, exact excerpts and
HTML, and validate numbered presentation. Models supply diagnoses, repair choices,
bilingual wording and actual language-feature judgments. An ID does not establish
semantic review, and no program fabricates a missing judgment.

Prepare the existing report-bound B packet and version-2 final-text ledger,
attaching the actual language response/evidence where applicable, then:

```text
python scripts/review_workflow.py prepare-delivery --audit AUDIT --ledger DELIVERY_TEMPLATE.json --policy RUN/automatic_capacity.json --out COMBINED
python scripts/review_workflow.py assemble-delivery --bundle COMBINED --responses RESULTS... --out CHECKED
```

Each request combines coverage, final-source fields, report blocks and applicable
Expression realization, with the common context supplied once through lossless
shared-value encoding. Complete local contexts stay together. Every task requires
an explicit result. Models may explicitly group equivalent decisions or reference
one exact shared judgment; the program expands only named IDs and returned values.
Different judgments retain separate records and substantive evidence.

Assembly produces ordinary B and preservation/language ledgers and runs **both
existing validators**. Missing records, unsupported assertions, mandatory omissions
or rejected language realizations block delivery. Do not add separate B,
translation, style or Expression calls for this same unchanged material.

## Default post-processing concurrency and dependency barrier

After preparing each source or combined-delivery bundle, invoke
`run_review_packet.py` without `--packet`; it executes that bundle with at most
three isolated workers. Each worker reads its frozen request only, never another
worker's output. All packet capacities and sources are checked before submission.
The coordinator stores a separate receipt with ordered response paths and
`ready_for_assembly`; this means complete explicit task accounting, not semantic
approval or author-delivery readiness. Assembly still runs the normal validators.

The normal phase order is initial-review freeze -> source bundle -> source assembly
-> merge -> Verify -> draft -> prepare/freeze delivery inputs -> delivery bundle
-> delivery assembly and both gates -> export. Never submit a downstream stage
using partial upstream results. This default does not overlap merge with source
review or modify the existing within-stage consolidation/draft partition runners.
If an A-delta bundle is necessary, its independent packets use the same scheduler
after their frozen prerequisites; complete/adjudicate A before delivery preparation.

A failed packet leaves the phase incomplete. Preserve successful other outputs,
never default missing judgments to pass, and do not retry paid calls automatically.
Matching cached responses are reused with original provenance. Coordinator locks
prevent duplicate concurrent waves; receipts are retained separately on resume.
No user batching confirmation is required; existing model/effort/Standard
authorization still applies. Concurrency changes waiting time, not packet counts,
coverage, capacity reserves or model quality guarantees.

Batch count follows complete input capacity and estimated output workload, not a
fixed 2/3-call target. Output estimates are planning heuristics; the full reserve,
including reasoning, remains unchanged. Check pinned token/image/system/headroom
and character limits; never truncate evidence or silently change settings.

For actual corrections, use the existing delivery-delta helper and reviewer
assessment of affected scope, including bilingual counterparts, shared actions
and cross-section dependencies. Combine coverage/facts/meaning/language renewal
in one pass; retain valid unaffected judgments with original provenance. Format
reconciliation stays local and preserves raw output. Stop after required checks
pass. Runtime targets do not permit waiving required checks.
