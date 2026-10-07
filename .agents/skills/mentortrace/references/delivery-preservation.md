# Delivery preservation review

Apply source-fidelity.md to Original quotations and formula-related assertions in addition to Phase A/B and the version 2 final-text ledger. Reuse the checked source transcription, compare the rendered decisive glyphs against the bound original page, and keep repeated quotations consistent. A preserved earlier requirement does not certify its source accuracy. If a quotation correction contradicts a finding's premise, readjudicate the finding and affected shared actions before delivering the corrected report.

Run after frozen initial discovery and fresh verification, before author-facing Markdown delivery or HTML/PDF export. Preserve original responses and earlier reports. Do not feed an earlier report into the initial lanes. Structural record validation is separate from the reviewer's substantive judgment.

## Review the source requirements before their delivery

Use `scripts/audit_merge_obligations.py prepare --run RUN --output AUDIT` after the internal diagnostic export has created `final.json`. AUDIT must be outside the immutable source run. The tool selects narrowed, withdrawn, unresolved and many-to-one content/organization lineages, including intermediate merges. This is a targeted consolidation audit; it does not certify all initial sufficiency judgments or completeness of initial discovery.

Phase A supplies complete original selected requirements, their source checks, manuscript text and page-image hashes. Changed outputs and disposition reasons are withheld. Read the manuscript and split each source into independently answerable components, including actual conditions, alternatives and explicitly affected occurrences. Assess each component as required, optional, already_answered, unsupported, unknown or duplicate, with typed manuscript evidence and a component-specific reason. Review whether the split covers the source; a component count is not proof of completeness. Fill a copy of `phase_a.template.json` using `schema.json`. Record the actual reviewer and whether later outputs had already been seen; self-review is not independent verification.

Freeze the submitted A record with `adjudicate --audit AUDIT --ledger A.json`. Only then run `compare --audit AUDIT --report REPORT.md` and fill a copy of `phase_b.template.json`. B compares the adjudicated requirements with final review fields and the actual report, using exact focused excerpts and source lineage. A required missing requirement or an unfinished comparison blocks delivery. An optional omission is recorded without becoming a technical defect. An unknown requirement may remain explicitly unknown or awaiting author confirmation in the report; the ledger must document that visible treatment and must not call it resolved. Check using `check --ledger B.json --report REPORT.md`.

These commands prepare and validate records; they make no model calls. A pending template never certifies preservation. `--max-batch-bytes` groups complete source packets without truncation; it measures UTF-8 bytes, so model token/image capacity still needs separate preflight. Do not automatically launch extra paid calls.

If a supported requirement is missing from the frozen final review, return the correction to merge/verification in a separate run or version; do not rewrite the original raw, final or accepted response files. Reusing initial responses requires identical factual inputs and initial request content, a recorded source hash and disclosure that they were replayed rather than newly discovered. Changes to manuscript or initial rules require a fresh appropriate review. Recheck the corrected output before delivery.

For report-only edits, create a new audit directory and comparison record. Unchanged frozen A may be reused with its original provenance when all bound sources still match. Review B against the new report hash and excerpts; changing a hash alone does not redo the review.

Apply the [execution efficiency rules](execution-efficiency.md) for incremental review, complete evidence packets, combined checks and batching within verified capacity: prepare a local change inventory and renew affected source mappings, final facts, both-language meaning and style together. `scripts/prepare_delivery_delta.py` creates a fresh final-text ledger, conservative carryover candidates and pending IDs; approved carryover requires a recorded affected-scope assessment and exact source/context/evidence checks. New global completeness statements and the report-bound B record remain required. Do not re-submit valid unchanged units or create separate polishing audit stages.

## Source-to-report obligations

Initialize the version 2 ledger from the complete final report:

```text
python .agents/skills/mentortrace/scripts/audit_report_preservation.py init --report REPORT.md --ledger DELIVERY.json --source final.json
```

Repeat `--source` for earlier delivered reports and unresolved inherited revision details on re-review. A first report needs the current verified final review; comparing only the last rewrite hides earlier omissions. The tool inventories substantive source blocks and all current Markdown blocks, plus explicit Suggested wording groups.

Split each substantive source block into meaningful `components`: `source_quote`, `obligation`, `status`, `target_quotes`, `reason`, and evidence `{path,sha256,quote}` when revised or rejected. Status is retained, revised, rejected or unresolved. Target excerpts must be substantive and exact, with an explanation of how each fulfills this obligation; separators are not coverage. For visual claims use a focused inspection record bound to the original image hash. Unresolved obligations must remain visibly unresolved. Headings or usage boilerplate may have `non_substantive_reason`; substantive conditions and actions may not.

Preserve the actual defect, applicable setting, negation, necessary/sufficient conditions, uncertainty, decisive calculation, action location and conditional downstream work. Keep valid alternative repairs and optional status. A shared revision plan must retain each independent requirement. Fill `scope_review.reviewer`, `source_completeness` and `semantic_review` with the work actually performed.

## Final-text facts, meaning and wording

Every `target_units` block has its exact text and hash. Its `review` records `reviewed_sha256`, `classification` (factual, non_factual, action or explanatory), `reason`, `assertions`, `meaning_check` and `style_check`. Classify by meaning, not by the presence of a verb, pronoun or tense. Each factual assertion needs its exact local `quote`, a reason and one of:

- `supported`: textual evidence `{path,sha256,quote,basis}`; basis is manuscript or direct_derivation. A requested future action is not evidence of its implementation. A derivation may support a mathematical assertion; it cannot establish author implementation history or a measured experimental outcome.
- `conditional`: a specific local author-confirmation condition `{target_unit_id,quote,reason}` attached to this passage.
- `unresolved`: an explicit local uncertainty notice in the same form, with no unconditional paste-ready claim.

Suggested wording groups bind their constituent block IDs and the whole passage hash. Their review includes `reviewed_sha256`, `reason`, `assertion_completeness`, `meaning_check` and `style_check`; the constituent blocks carry fact evidence. Complete global `target_review.reviewer`, `assertion_completeness` and `semantic_review`. Inspect English and Chinese against the same checked meaning, and write each naturally. Direct feedback still preserves qualifications and valid alternatives.

A change to a passage, formula, readiness condition or its evidence invalidates the affected review. Reinitialize the current inventory and re-review changed units and mappings; carry over unchanged reviews only when their exact text, context, evidence and local conditions remain valid. Updating only the report hash cannot restore a stale passage review. Check with `check --report REPORT.md --ledger DELIVERY.json --require-v2`.

New author delivery requires both the report-bound B consolidation record and the version 2 final-text ledger. The renderer accepts `--requirements-audit B.json --preservation-audit DELIVERY.json` and validates both before writing HTML/PDF. For Markdown-only delivery, run the same `validate_delivery` function from the renderer module, or both check commands with the exact report and confirm the final-review source hash is the one bound by B. Internal diagnostic exports are not author-delivery certification.

## Coordinated action and concision review

Use the existing component comparisons and final-text meaning/style reviews for these checks; do not add a new audit stage or author-facing checklist. Verify that a shortened or alternative request still answers every supported independent question, with evidence for any relaxation. Check claim corrections across all affected manuscript occurrences against one supported conclusion, preserving legitimate differences in meaning. Check that plans and overlapping replacements can be applied together, or are explicitly separate alternatives. Put missing author facts and insertion locations in Suggested revision / 建议修改 or shared revision actions, with no separate author-information field. Review concise language comments for exact corrections and all occurrence anchors. Remove redundant explanations, repeated checklists and duplicate drafts while retaining locally necessary use conditions. Any resulting text change still requires the affected bound review to be renewed.

## Limits

Version 1 ledgers remain readable as legacy accounting records; they have no final-text fact inventory and cannot satisfy new export requirements. Both checkers reject stale sources, missing accounting, invented excerpts and pending reviews. They cannot prove all clauses/assertions were identified, evidence establishes the conclusion, or the wording is natural. Passing returns records_validated with semantic_correctness_verified=false, never scientific truth, diagnostic recall or model independence. Record these limits honestly and disclose remaining checks.
