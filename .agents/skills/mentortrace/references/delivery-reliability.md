# Delivery reliability v1

New adaptive runs pin `delivery_reliability: 1`. Frozen older protocols keep their
original rules. This extends the existing source review, Verify and delivery pass;
it creates no additional whole-manuscript review lane. Advisor discovery inputs,
case records, independent judgments and settings remain unchanged.

## Discovery and registration

Reader and Expert distinguish an object's definitions/references, operation
prerequisites, data generation, statistic/aggregation and displayed interpretation
where applicable. Use their existing checks and scope records. A mathematical pass
cannot answer an acquisition question. These dimensions are not defect quotas,
mandatory experiments or an Advisor task map. Unknown and unattempted are distinct.

The runtime registers anchored optional suggestions, uncertain items, explicit
author questions, Reader missing-information tasks and unknown/unfinished checks.
It preserves the literal source record and location. Generic limits do not become
automatic author demands. Historical `evidence_requests` remain source-retrieval
requests; their completed unknown checks can enter author-question accounting.

Merge and Verify return one `candidate_reviews` disposition for every registered
candidate. An optional proposal remains optional; an unknown remains a precise
author-confirmation request unless manuscript evidence resolves it. Incorporation
must name a surviving finding or organization suggestion. Exclusion needs evidence
and a decisive reason. Verify sees the originals as well as Merge's proposals.
Unknown comparative benefit alone is not evidence against a style suggestion.

## Requirements and decisions before drafting

The existing source-only pass decomposes independently answerable questions, not
sentences or topics. Preserve object, occurrence, condition, action and real author
choices. Reuse an explicit shared judgment where it actually applies; do not ask
the model to reproduce the same evidence for every audit view.

Verify returns `source_requirement_resolutions` for every source component, with
its stable ID, assessment, manuscript evidence, actual final output IDs and concrete
delivery action. Supported and unknown requirements need a route. Changing a source
assessment requires an explicit decision, not a silent omission. Original source
assessments remain saved. `seed-a` applies the actual recorded Verify decisions to a
new ledger and labels this reconciliation truthfully; it is not fresh independent A.
New duplicate judgments need source-only adjudication, never guessed canonical IDs.

All original content/organization sources and registered candidates participate in
the new protocol's stable preservation inventory. Adding a lineage edge must not
silently change which original sources were subject to review. Derived routes come
from actual source-component decisions; topic similarity cannot create an edge.

Before drafting, validate the actual final decisions against the bound sources.
Unresolved scientific meaning is presented as an anchored question; unsupported
claims cannot be repaired by hiding uncertainty. Do not let a later drafting pass
choose between conflicting requirement sets. Corrections to accepted/frozen records
require a separate derived version with the actual changed decision and provenance.

## Author-facing output

State the problem and the action directly. Include the reason and conditions only
when they help the author judge or perform the repair. Preserve meaningful choices
in concise positive form; remove private explanations defending against unrequested
extra work. Do not delete a real condition merely because it starts with “if”.

Expression can implement mentor-style alignment with unmeasured or equivalent
quality. Record that purpose without claiming superiority. Grammar, number and
referents still depend on the target meaning, not the example's syntax. If the
referent is uncertain, ask what is meant or offer the corresponding conditional
wording. The author's discretion does not justify unsupported definitive criticism.

`candidate_delivery_map` binds each optional/question action to an exact report
excerpt; the final preservation inventory includes those actions. A generic
remaining-checks disclaimer does not deliver a specific question. Incorporated
candidates use their actual finding/organization routes.

Use exact frozen text for Original. Drafts can reference immutable page spans with
`[[ORIGINAL:ref_id]]` and `original_references:{ref_id:{page,page_sha256,span:[start,end]}}`.
The runner performs literal substitution, not summarization. In partitioned drafts
prefix reference IDs with the part ID. Formula glyphs that differ from extraction
still need the ordinary independent page-image check; never silently repair text.

## Local validity, recovery and delivery validity

A failed complete report can contain valid local judgments. `assemble-delivery`
saves a `checkpoint.json` with actual review provenance before final gates. It is
explicitly not a delivery pass. `prepare_delivery_delta.py` can carry valid local
source/target judgments from that checkpoint after current context, evidence,
rules and dependency checks. Unknown applicability or changed shared premises
invalidate dependent judgments even when text is identical. Expression groups
remain conservative: no reuse from an incomplete full-group review.

Recover completed raw results without a new call:

```
python scripts/delivery_recovery.py --bundle BUNDLE --responses RESULTS... --out NEW_RECOVERY.json
```

Missing tasks stay pending; duplicate/foreign tasks are errors. Never turn a
checkpoint, recovered record, hash match or synthetic replay into semantic approval.
Both ordinary report-bound delivery gates remain mandatory. After a failed call,
inspect stored results first; retry only the failed or affected work. Repeated
failure of the same unresolved condition stops automatic retries and remains visible.

## Bounded incremental packets

The repair's existing affected-scope assessment may include `packet_scopes`, keyed
by the scheduling groups in `context.json/task_groups`. Each group records
`status: complete|unbounded`, reviewer, reason, context_ids, source_ids, final_ids and
pages. These name complete local passages and cross-section prerequisites, not
keyword snippets. Current report/source hashes bind the assessment.

Alternatively supply `prepare-delivery --scope-plan FILE`, containing
`report_sha256`, `source_bindings` (the ledger source path/hash mapping), and `groups`.
Bounded local packets receive all declared dependencies; the global packet retains
the full report and inventories. Missing or unbounded assessments safely retain full
context. Do not invent a complete dependency assessment to meet a size target.

Local tools collect ID, field, quote, hash and reference failures together. Optional
exact evidence-span references expand only actual supplied or returned evidence.
Evidence sufficiency, bilingual meaning, requirement completeness and readability
still require semantic review. Performance measurements distinguish task count,
packet bytes/tokens, wall time, repeated calls and changed scope. Synthetic byte
reduction is not measured model speedup or improved technical recall.


For new `delivery_hardening: 1` runs, the additional [delivery hardening contract](delivery-hardening.md) governs source/component retention, actual-result barriers and scoped recovery. Older frozen protocols retain their existing rules.
