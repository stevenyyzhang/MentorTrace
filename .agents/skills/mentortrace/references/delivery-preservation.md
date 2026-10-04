# Delivery preservation review

Run after independent discovery/verification, before replacing or exporting an author-facing report. Never feed prior reports into independent review lanes. Preserve prior reports and frozen responses.

## Sources and obligations

Use current verified findings and organization suggestions, supporting checks where needed, and prior delivered findings/revision details without an evidence-backed disposition. Comparing only with the immediately preceding rewrite hides inherited omissions. A first report needs current verified findings; a re-review also needs earlier delivered reports. Restoration is not new autonomous discovery.

Run `scripts/audit_report_preservation.py init --report NEW.md --ledger AUDIT.json --source final.json --source EARLIER.md`. Repeat `--source` as needed. It inventories every Markdown paragraph or relevant JSON finding field. Complete the ledger in a separate source-to-target review, then run `check` with the same report and ledger. The renderer requires `--preservation-audit AUDIT.json` before writing output. Markdown delivery requires the same check. Internal diagnostic exports are not delivery certification.

Split substantive source blocks into independently meaningful `components`. Each component has `source_quote`, `obligation`, `status`, `target_quotes`, `reason`, and, when revised/rejected, `evidence` entries `{path,sha256,quote}` pointing to supporting textual manuscript/evidence records. For visual evidence use an anchored inspection record tied to the original image hash, not a filename alone. Status is retained, revised, rejected or unresolved. Unresolved obligations must be visible in the report. Revised/rejected obligations need evidence, not just a different model answer. Headings/usage boilerplate may instead have `non_substantive_reason`; technical conditions and repair details may not.

Account separately for:

- Exact defect, actual setting, prerequisites, exceptions and uncertainty.
- Decisive quantitative/logical evidence and its conditions. Shorten calculations only if the important comparison remains understandable.
- What changes, where, and conditional downstream actions, such as recomputing results if their scale changes.
- Alternative valid repairs: do not turn analytic-or-empirical evaluation into a simulation-only requirement without evidence.
- Necessary/optional status, localization and bilingual meaning. A shared plan must retain all distinct actions.

Fill `scope_review.reviewer`, `source_completeness` and `semantic_review` with the actual review performed, historical sources checked and compound obligations split. Do not describe self-attestation as independent model verification.

## Limits

The checker rejects stale sources/reports, missing source blocks, unprocessed obligations, absent target excerpts, changed/rejected obligations without evidence, and invisible unresolved items. It cannot prove that all clauses were split or that a broad target excerpt preserves a specific condition. The reviewer must check that explicitly. Passing validates accounting records, not semantic equivalence or recall. Never mark substantive paragraphs boilerplate to bypass review.

Re-run after every report edit and re-review changed mappings. When reviewing the same manuscript again, compare its earlier report only after independent discovery. That comparison never dictates manuscript judgments or requires an unchanged finding count.
