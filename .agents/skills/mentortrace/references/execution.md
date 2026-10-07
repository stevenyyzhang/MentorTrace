# Execution guide

Resolve paths from the full repository root. Python 3.10+, prepared manuscript pages, both frozen public corpora, and an explicitly authorized model transport are needed. The runner creates requests and validates responses; it does not automatically send manuscripts or modify their files.

For transport, resumption and postprocessing, apply [execution efficiency](execution-efficiency.md). Keep model/effort fixed unless the user explicitly authorizes the new settings. Standard is the default; Fast requires explicit tier and additional-usage authorization, never an inference from urgency.

## Prepare and freeze

Use scripts/prepare_paper.py to extract an annotation-free manuscript into consecutive page/text records and matching PNG images. Inspect the images for burned-in comments and confirm text-image correspondence. Extraction alone does not establish that annotations were removed or every equation was readable. Private inputs and runs belong in ignored workspaces/ and runs/.

Create a new run with scripts/mentortrace_v1.py create --paper PACKAGE --run RUN. It validates frozen hashes, copies the English concern package and public case summaries, and freezes the skill and protocol. Missing or modified corpus files fail explicitly. Never migrate an existing frozen run in place. Select and record the actual model, reasoning effort, input capacity and output budget; user-interface selection does not configure a script.

## Review stages and isolation

New protocols enable source_fidelity: 1 and freeze inputs/source_fidelity.json from raw page text and image hashes. This adds deterministic inline split-word candidates to Language only, plus formula-source records in Verify; source-fidelity.md also guides Technical, Advisor, consolidation and drafting. Candidate dispositions and formula records are validated on acceptance. The program does not rewrite extraction, perform OCR or certify the reviewer's visual judgment. Frozen older protocols retain their existing request/response contracts.

Use next --run RUN to prepare one request, then accept --run RUN --response RESPONSE.json. Preserve the original response before any normalization. Each initial lane uses a fresh context: Reader and Technical receive the target plan and only their selected cases; each Advisor batch receives the full manuscript and its complete card batch without the plan or prior opinions; Language receives manuscript text units and images without cards or plan. Complete the manifest-defined Advisor batch coverage, not a fixed number of defects.

After accepting objects, use route-input --run RUN, read case_route_input.json and write a selection with source_plan_sha256, reader, technical and skipped_entries. Each route names target object_ids, task, entry_ids, case_ids, reason and sufficiency_question. Freeze it with route-cases --run RUN --route SELECTION.json. Empty routes are valid when unused entries have reasons. IDs and links are executable checks; semantic task matching still requires review. Source examples prompt a target question; no alternative answer is required.

The public concern package cannot supply private historical evidence. Cards declare that limitation. Do not request unavailable histories or count them as checked; retain affected uncertainty. An explicitly supplied private package may support bounded follow-ups, which are logged separately from initial discovery. The target manuscript remains the evidence for every reported defect.

The four lanes are followed by raw freeze, a source-execution review, merge, fresh verification, requirement comparison, final-text review and author-facing report freeze. After raw freeze, inspect whether the planned and independently created relations were actually answered: compare the original target with the evidence/reason, including compound tasks, current claim scope and conditional proof versus premise declaration. Record the inspected source IDs, evidence, unresolved or unattempted parts and review limits in a private initial_execution_review record. Completed accounting does not establish substantive completeness; completed plus unknown is valid. A sampling review must disclose its coverage. A missing review task is not an author error. Carry justified later additions into the merge/verify trace without rewriting frozen initial outputs or expanding every unknown into a finding. Technical checks actual configurations and operation prerequisites; Reader records multiscale comprehension and editorial alternatives. Advisor remains independent. Do not truncate evidence to fit a request: preflight actual text, images, model context and output reserve. Failure and uncertain transport attempts require inspection; retry is explicit and archives the prior attempt.

## Optional transport

scripts/run_authorized_stage.py submits one request through an ephemeral isolated Codex CLI context. Use it only after the manuscript owner authorizes that submission. Its model and effort are explicit parameters. CLI compatibility was checked against 0.159.2; account access, server context capacity and diagnosis quality are not established by that check. The core file transport also works with another authorized service that preserves fresh contexts, all pages, original responses and actual model settings.

Provide `--settings-authorization AUTH.json` recording the actual explicit human choice, as specified in execution-efficiency.md. The runner pins those settings, verifies cached output hashes before reuse, and defaults to `--service-tier default`. `--prefetch-advisor --workers 2` submits only pending independent Advisor batches; no results are accepted concurrently and no failed call is automatically retried. Accept prefetched results through subsequent ordinary stage invocations. The optional Responses adapter enforces the same settings authorization.

The optional Responses adapter is disabled in config/provider.json and config/project.json. Configure a verified context limit and explicit authorization before enabling; token preflight also transmits material. Keep credentials only in the local environment. Never redistribute saved requests, responses, usage logs or manuscript page images.

## Delivery

After completion, export --run RUN writes internal English review records. prepare_revision_proposals.py --run RUN --out OUTPUT prepares a separate post-freeze request for a bilingual author report and supported local revision proposals; it calls no model and applies no edits. The final report must follow report-language.md, repair-contract.md and delivery-preservation.md. Retained findings and optional organization actions need traceable delivery locations. Preserve conditions and author-supplied facts; missing facts are questions, not invented prose.

Complete the separate A/B consolidation review and version 2 final-text preservation ledger under delivery-preservation.md before render_bilingual_report.py. New narrowed/withdrawn dispositions identify excluded_requirements with exact source_quote and reason plus typed manuscript evidence; unresolved dispositions retain no asserted output IDs. The final report and final review hashes must match both audits. Recheck affected records after every parent or subtask edit. Deliver report_bilingual.md and derive its PDF from the same Markdown with the saved CSS. Inspect every rendered PDF page, equations, Chinese glyphs, finding coverage and long draft boundaries. Report unfinished checks separately. Optional grading uses another context only after delivery freeze.

## Public release limitations

Public cards are conditional analytical abstractions. Source histories are withheld, and all original Reader/Technical case identities and paired companion summaries are retained as English analytical records, without source passages. Schema tests verify accounting and boundaries, not technical truth or equivalence to the private release. Anonymous IDs cannot establish unseen-source-family eligibility. The repository contains no source manuscript PDFs or private historical mapping.
