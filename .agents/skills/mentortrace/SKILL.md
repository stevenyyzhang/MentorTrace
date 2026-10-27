---
name: mentortrace
description: Diagnose academic manuscripts with independent Reader, Expert, Advisor and Editor reviews; retrieve task-matched exemplary-paper cases for evidence-grounded findings and revision proposals. Also extract conditional Concern records and preserve actual mentor Expression examples from explicitly supplied historical feedback and revisions. Automatic manuscript editing is not integrated.
---

# MentorTrace 1.2.0

The four review modules are **Reader, Expert, Advisor and Editor**. Expert performs technical review; Editor handles language and surface checks. Their serialized stage IDs remain `technical` and `language` for compatibility with frozen runs. **Concern** records describe what the mentor asks authors to explain or justify. **Expression** records preserve concrete mentor-proposed wording and paragraph actions. Normal CLI runs load the bundled 1,581-record `corpus/advisor-expression-v1` for independent Advisor review and related drafting; read [Expression](references/expression.md) for its source and transfer boundaries.

Before admitting or transferring an Expression, identify the concrete wording or
paragraph operation it adds and compare it with applicable Concerns using the
[admission boundary](references/expression.md#expression-admission-and-concern-overlap).
An attributable edit alone does not establish a reusable expression feature.

Within the same independent Advisor call, Concern tests whether requirements and
relationships are sufficiently supported; Expression contributes specific wording,
syntax, qualification, transitions or sentence/paragraph operations. Name what
Expression adds beyond any Concern requirement, compare the actual target, and
keep equivalent or unsuitable prose unchanged. An Expression may implement a
necessary repair, independently support an optional improvement or identify a
target-evidenced local expression error. Do not duplicate a generic requirement
as another problem. Follow the versioned contribution accounting in
[Advisor responsibilities](references/advisor-batching.md#source-responsibilities).

New direct Advisor runs use [compact output records](references/advisor-output.md):
write each actual target analysis once, retain explicit dispositions for every
source/use, and let the program expand exact source/anchor references and mechanical
links. All substantive evidence and ordinary validators remain required. Preserve
frozen older protocols; offline replay is not a new review or measured speedup.

New runs additionally pin `advisor_expression_brief: 1` to prioritize elapsed time.
For non-action Expressions, this overrides the verbose per-case transfer/check
requirement: record an explicit decision, one concise operation-based reason, and
an actual anchor for KEEP. All sources and uses remain accounted for, but these
are limited-depth assessments, not exhaustive application audits. Clear repairs
and worthwhile optional improvements retain full source and manuscript evidence.
Concern review and Reader/Expert remain unchanged. Follow the brief protocol in
[Advisor output](references/advisor-output.md#brief-expression-assessment).
Disclose this reduced depth in report coverage. Do not claim a two-hour completion
guarantee or convert omitted judgments into no-change decisions.

New runs also pin `advisor_efficiency: 1`. Read related expression-operation
families together in the same Advisor call. These are routing hints, never merged
evidence or automatic judgments. Keep each case's conditions and exceptions.
Return explicit shared non-action groups only when the actual decision, reason
and target support every named member. Detail actionable cases normally. The
runtime view keeps operations, examples, feature/provenance information, conditions,
facts and boundaries; five narrative/retrieval fields remain local. This narrower
view can miss subtle contextual applications and must be disclosed in coverage.
Use exact passage identifiers or explicit image-page locators rather than retyped
quotations. See [shared guidance and object locators](references/advisor-output.md#shared-guidance-and-object-locators).

When pinned, use the source-bound shared guidance catalogue prepared with the
library: related-operation groups organize inspection, while every case retains
its own conditions, exceptions, examples and explicit verdict. Do not regenerate
this corpus comparison for each manuscript or quote canonical analyst guidance as
mentor wording. Use supplied text/object IDs for evidence locations; equation and
caption candidates still require page-image inspection, and ambiguous labels must
not be treated as certified object identification. Frozen older runs keep their
original protocol.

For mentor-guided English drafting with an `expression_realization: 1` snapshot,
apply [concrete language realization](references/expression-realization.md) after
the revision scope is fixed. Retrieve by passage job and language function, retain
appropriate mentor lexical/syntactic features in the actual replacement passages,
and verify their realization within the existing final-text review. Source matches
do not require extra findings or edits to retained passages.

Use the four-lane diagnosis workflow below. This repository-scoped skill is discovered from .agents/skills. Keep the full repository and resolve runtime paths from its root. Reading it does not constitute running the workflow. The default CLI creates independent-Advisor runs; frozen older runs retain their original protocol. Read the [execution guide](references/execution.md) for commands and transport boundaries. Project paths below resolve against the MentorTrace root.

## Start from the user's task

For ordinary review, use the bundled Expression library without extra setup. Verify its
freeze and declared format when creating the run. `--expression PATH` selects another
explicitly supplied snapshot; `--no-expression` creates an explicit baseline. A missing or
changed default snapshot must be reported, not silently replaced with a Concern-only run.
Read `private/config/editorial_sources.json` only when the user explicitly selects private
historical sources; its existence alone does not override the public default or authorize
cloud transmission. Public examples do not supply omitted pages, private annotations or
an accepted final mentor revision. Preserve existing frozen runs when changing defaults.

For autonomous diagnosis, use the fixed manuscript without its target comments, scoring answers or future versions. For an explanation of supplied comments, disclose that it is assisted interpretation and not autonomous discovery. For drafting or applied edits, explain the current implementation boundary and use [repair boundary](references/repair-contract.md) to formulate a supported revision plan; the V1 runner does not apply edits.

For explicitly requested learning from historical annotated papers or LaTeX revisions, read [historical training intake](references/historical-training-intake.md). This mode produces source-linked conditional concerns and version histories; keep its private annotations and later drafts separate from autonomous target diagnosis.

When using local published-paper originals, select the private source-passage snapshot with `--case-passages`. Reader and Expert receive only passages for their frozen selected cases. Actual source prose, analyst reconstructions and generated target revisions remain distinct; source facts and a source sentence order cannot establish a target defect. Full connected Reader passages continue into post-freeze drafting.

Confirm the available manuscript version and scope from supplied files. Ask only for essential missing input: which version when ambiguous, or unreadable/missing manuscript content. Do not invent the author's implementation or results. Do not require target advisor comments for autonomous diagnosis.

## Execution efficiency

For normal public-corpus reviews, follow [Advisor grouping, capacity and workload](references/advisor-batching.md) before any review lane. Read the selected Codex model capacity automatically, without asking users for capacity numbers or batch approval. Minimize complete packets within the pinned capacity/workload bounds, preferring at most 12 packets. Automatically allow necessary extra packets when complete packing requires them; record the count/reason without asking the user. Never fill a smaller plan to 12. Do not hard-code Sol 6 or Astra 10: these are offline examples for one paper. Preserve all 493 Concerns, 1,581 Expressions, candidate associations and conditions, including unlinked cases. Each source requires an explicit result; missing results never imply review. Candidate associations are references with discounted selection cost, not mandatory separate judgments. Keep fixed groups as provenance, assign each primary Concern once, and preserve full context where needed. No Advisor task map or Reader/Expert plans constrain its full-manuscript review. Finalize and validate all packets before review, then repeat capacity/workload checks at submission. Exceeding 12 is not an error. Missing metadata or an indivisible source that cannot fit remains a genuine execution failure; preserve materials and report it without asking for routine parameter choices. Never truncate, lower reserves or change model/effort. Cached valid responses use no new submission slot. Host permissions remain in force. Reader/Expert and existing frozen runs retain their workflows.

Apply [execution efficiency](references/execution-efficiency.md) when submitting, resuming or postprocessing reviews. Reuse valid stage outputs with their original settings/provenance; renew only reviews affected by changed text, context, evidence or applicable rules. Submit complete task-relevant evidence, group related final-text checks, and use concise evidence-focused records. Batch complete packets to verified capacity and run independent batches with bounded concurrency. Keep initial lanes and Phase A/B isolated, preserve their full required coverage, and use local programs for mechanical checks. Inspect failed/uncertain attempts before retrying; stop after required delivery checks pass.

New adaptive runs pin `review_efficiency: 1` and follow the
[combined review workflow](references/review-workflow.md): after the existing
Reader/Expert object plan and case selection, run Reader/Expert, independent
Advisor and Editor concurrently in separate contexts, defaulting to three workers.
Combine source-only execution/requirement review; then combine report coverage,
final facts, bilingual meaning/style and Expression realization. Programs expand
only actual explicit judgments into the existing ledgers. Both delivery gates,
complete source decisions, original provenance and capacity reserves remain
mandatory. Offline replay is not a new review or a measured speedup.

Use Standard by default. Fast requires explicit user authorization naming the tier and accepting its additional usage; urgency, acceleration requests and deadlines are not authorization. Any reasoning-effort change, upward or downward, also requires explicit user authorization naming the new effort. Preserve the authorized model/effort across stages; never lower effort automatically to save time or usage. These rules travel with this skill and apply to isolated CLI and alternative transports without changing users' global settings.

## Route the diagnosis

Apply [source fidelity](references/source-fidelity.md): extracted text locates evidence; original page images govern decisive glyphs and physical word placement. New runs freeze a neutral surface-candidate inventory for Editor and require formula-dependent verification records. Inspect the decisive original expression before alleging a mathematical defect, and carry checked transcriptions into report quotations. These runtime gates establish record coverage and hash binding, not visual truth or complete error recall.

1. **Freeze inputs.** Register one readable manuscript version, page text/images, knowledge snapshot, hashes, model/effort, capacity plan and family policy. Keep target comments, scoring answers and future target versions out of review requests. A directory scan does not prove the model saw a file.
2. **Plan general checks without verdicts.** Preserve both ends of each relationship, the actual conclusion and its conditions. Planning serves Reader and Expert; it is not a mandatory inventory for Advisor. In case-enhanced mode, freeze a separate task-to-case route from this plan before either lane runs.
3. **Run four isolated lanes**, following the table below. Reader and Expert may add targets. Advisor independently creates and judges its own relation inventory; it does not attach cards to the general plan. Every Advisor batch reads the same full manuscript. Complete the frozen coverage plan without requiring a problem per card.
4. **Respect evidence availability.** Public cards contain analytical abstractions, not private histories. Request historical follow-up only when a separately supplied package explicitly declares those fields available. Otherwise preserve unknown/unfinished outcomes. Follow-ups are not independent initial discovery.
5. **Freeze raw findings.** Preserve original lane responses, additional targets, evidence findings, language uncertainty and coverage. A relation, a check and a reportable finding are different records. In new `review_efficiency: 1` runs, combine execution and source-requirement review in an isolated source-only pass, which may overlap merge and must finish before Verify. Earlier protocols retain their pre-integration execution review. Distinguish unattempted task scope from completed-but-unknown judgment; source-ID coverage alone does not prove each relation was answered.
6. **Organize and independently verify.** Apply [merge and verify](references/merge-verify.md). Deduplicate the same requirement; retain independently answerable gaps and concrete closure goals. Verify against the manuscript in a fresh context, retaining source links and evidence for withdrawals. Fewer findings is not a quality target.
7. **Audit delivery and freeze.** Complete the two-phase source-requirement comparison and version 2 final-text review in [delivery preservation](references/delivery-preservation.md). Judge original changed requirements before viewing the changed output, then bind coverage to the actual final report. Review its facts, both-language meaning and direct wording after the last edit. Check that supported specific requirements survived into the author-facing output. If re-reviewing the same manuscript, compare the newly frozen findings with the prior report only after independent discovery; give every prior item an evidence-based retained, covered, rejected or unresolved disposition before replacing its report. A changed model output alone does not justify silently losing a language correction. If reorganization is needed, preserve the prior version and create a source-traceable new version without target-directed questions. Deliver the three author-facing comment categories under report-language.md, with unresolved items and coverage limits.
8. **Score only when requested, after delivery freeze.** Use a separate context for target advisor comments/problem chains. Fix applicability and counting rules before comparing scores; multiple findings matching one chain count once. Report full, partial and miss separately. Reorganization or grading changes are not new autonomous discoveries.

| Lane | Review input | Responsibility |
|---|---|---|
| [Reader / Structure](references/reader-structure.md) | Full manuscript/images + general plan; selected [Reader cases](references/goodpaper-reader.md) only in case-enhanced mode; no other initial lane findings | Attempt key reader tasks; locate support, reading friction and necessary missing connections for the intended audience |
| [Expert](references/expert-checks.md) | Full manuscript/images + general plan; selected [Expert cases](references/goodpaper-expert.md) only in case-enhanced mode; no other initial lane findings | Information availability, mechanisms, assumptions, operations and supported claims |
| [Advisor](references/advisor-evidence.md) | Full manuscript/images + assigned complete Concerns and Expressions; **no preliminary task map, general plan or earlier findings** | Source distinctions and concrete operations → independently located manuscript relations → evidence-based judgments and optional improvements |
| [Editor / Surface](references/editor-surface.md) | Full manuscript/images and text blocks; no plan or cards | Definite language, notation, reference and formatting errors; uncertainty and optional style separate |

The [diagnosis contract](references/diagnosis-contract.md) governs content-lane evidence and judgments; it is not another review lane. Editor uses its own coverage contract and records definite small errors regardless of importance. Full coverage does not guarantee zero missed errors. Input isolation matters whether calls run sequentially or concurrently.

## Runtime completeness and delivery preservation

After findings are frozen, apply the revision scope and completeness check in [repair boundary](references/repair-contract.md) to every retained content/technical and organization comment or coordinated group. Select and deliver the supported repair at sentence, paragraph or action-only scope, or identify missing author facts; verify that the report actually contains that deliverable before its preservation audit.

New runs enable [actual-setting applicability](references/technical-applicability.md) for planning and Expert. Inspect actual baseline/ablation/experiment configurations against operation prerequisites, not merely general relationship coverage. Advisor remains independent of that inventory. Older frozen runs retain their protocol.

Before author-facing Markdown/HTML/PDF delivery, use [source-to-report preservation](references/delivery-preservation.md), including earlier delivered reports for re-reviews. This records conditions, decisive evidence and repair actions separately; a topic-level match is insufficient. The executable check validates accounting records, while semantic fidelity still needs review.

## Public knowledge boundaries

Load the manifest-defined public concern package at `corpus/advisor-concerns-v4/`. It preserves the original 437 cards and adds 56 conditional historical abstractions, including twelve additions restored or extracted during the joint-context and admission reviews. Earlier snapshots are retained in historical releases or local archives, not bundled with v1.1.0. Its six English decision fields preserve conditional analytical distinctions. Anonymous source IDs support internal links, not public identification of the private source manuscripts. These cards contain no original annotations, marked manuscript text, neighboring passages or private revision histories. They are analyst abstractions, not mentor-certified rules. Treat withheld history as unavailable; do not invent it or infer advisor acceptance. The added training collection is exposed; it cannot establish unseen-family review performance.

The published-case summaries at `corpus/published-cases-v1/` are enabled by default for new runs. Select task-matched Reader and Expert cases after the neutral plan; freeze the selection before either lane. Zero matches still require complete generic checks. The manifest states actual case counts. These English records provide original analytical summaries and verified public citations, not source PDFs, full-page transcriptions or private-feedback companions. Read their complete summary, candidate sufficiency questions, evidence classes and boundaries. Case IDs are provenance, not defect evidence or Advisor card IDs. See [Reader routing](references/goodpaper-reader.md) and [Expert routing](references/goodpaper-expert.md).

Public analytical abstractions do not establish diagnostic accuracy or better recall. Private source-family identities are not distributed; held-out eligibility must be established using an independently maintained private registry, not inferred from anonymous IDs. Do not include target comments, future versions or scoring answers in autonomous review requests.

## Section and whole-paper reading

New dev.4 runs freeze `writing_transfer: 1`. Apply [writing transfer](references/writing-transfer.md) in Reader, independent Advisor and drafting. Learn sentence/paragraph roles, information selection, emphasis and argument dependencies from complete supplied source accounts; test each against the target's own facts and existing arrangement. Advisor records editorial versus content-only scope in its existing concern dispositions. Preserve source-to-action records through raw freeze and link them to the final report's actual revision wording. The runner validates links and scope, not improved writing or established mentor preference. For historical learning, use [editorial episode learning](references/editorial-learning.md); preserve before/context/feedback/after/follow-up and uncertainty before admitting a reusable distinction. Do not count added checks or cases as learned preferences.

Use [section argument and information selection](references/section-argument.md) alongside Reader and independent Advisor checks. Reader records section syntheses and a whole-paper summary-to-evidence map; Advisor applies related concerns independently at their natural scope. Preserve necessary and optional section-level revisions through merge/verification. Draft supported replacement passages only after diagnosis freeze when requested.

Reader coverage separates passage job from structural scope and includes system models, problem formulations, methods, theory and experiments, not only abstracts/introduction/contributions. Advisor independently uses historical concerns at their relevant scope; the Reader coverage framework does not become its prescribed inventory. Keep Expert's validity and evidence remit unchanged.

## Deliverable

Apply the concise revision-request rules in [report language](references/report-language.md): missing author facts and insertion locations belong in Suggested revision / 建议修改, never a separate author-information field. Coordinate overlapping drafts and all affected claim occurrences under [repair boundary](references/repair-contract.md). Keep routine language explanations brief while preserving exact corrections and locations. Final review checks these decisions through the existing delivery audits.

Check sentence/paragraph order through Reader and independent Advisor evidence: distinguish information present somewhere from information available where needed. Preserve concrete optional rearrangements through merge and verification and deliver them separately from confirmed content problems, following the Reader and merge references.

For each finding show its location, what the manuscript already supplies, the missing or conflicting relation, consequence, counterevidence/uncertainty and closure goal. Prefer separate finding IDs for independently answerable supported gaps, even under a shared heading; merge duplicate requirements, not different questions about one topic. Keep technical invalidity distinct from missing explanation. Report unfinished checks and missing evidence separately. A limited interactive review must disclose its actual coverage and must not claim the full frozen batch workflow ran.

Identify anchored objects before judging them. Readers may know standard graduate-level domain concepts but not manuscript-specific assumptions or notation. Separate earlier-text accessibility from whole-paper support. Sufficient text and reasonable previews pass; unreadable evidence stays unknown.

For new adaptive runs, follow the [combined workflow](references/review-workflow.md): retain independent initial review and Verify; after freeze, explicitly reuse unchanged verified diagnostic claims while grounding new or changed claims. Keep reports concise without losing requirements or bilingual content, and replace unsupported fill-in drafts with exact author actions. Never infer that a missing review result passed.

Apply [complete-request capacity](references/request-capacity.md) to every stage in new adaptive runs. Use detected model and transport limits with unchanged reserves instead of the legacy byte cutoff. Automatically execute prepared complete-task partitions without asking users to confirm batching; preserve full evidence, source coverage and original outputs. Send prepared drafts with `run_prepared_draft.py`, including when a draft names a capacity plan. Both complete-report delivery gates still apply.

For each prepared source-check or combined-delivery bundle, run `run_review_packet.py` without `--packet` to default to three isolated workers. Use its complete response list for phase assembly; do not proceed on failures or missing judgments. Keep dependent phases sequential as specified in [review workflow](references/review-workflow.md). Parallelism never grants permission for a new model setting or paid retry.

Historical feedback is conditional evidence, not a required answer. Reference provenance and issue type are separate: an advisor-derived concern may be technical, explanatory, organizational, or stylistic. Revisions need actual task authorization; autonomous discovery and supplied-comment repair are distinct modes.

Keep raw findings, later-added objects and verification discoveries separately traceable. Do not merge different relations simply because their topic or location is shared. Freeze supported review findings before drafting revisions, but do not turn these two processing stages into separate report parts. Present supported wording beside its numbered comment or after its group's shared revision plan. Where the manuscript lacks facts, identify the exact author-supplied condition, method step or evidence needed. After diagnosis freeze, use selected source relation reconstructions and verified target facts to develop revisions, following [repair boundary](references/repair-contract.md). Unvalidated editing recipes are excluded from execution inputs; see [case evidence](references/case-evidence.md). The runner does not automatically edit the manuscript.

When the user requests a bilingual HTML/PDF manuscript report, use the [saved report print format](references/report-pdf.md) after the author-facing findings are frozen. It governs presentation and export, not diagnosis or scoring. Its default pagination is continuous: fitting comment cards stay together, short cards may share a page, and no rule assigns one page to each comment. Shared plans present complete English actions before complete Chinese actions without a shaded plan frame; each local draft is one independent bordered block with two language/wording separators and one copy of its suggested passage.

For every author-facing bilingual report, use the [bilingual report language rules](references/report-language.md) as the authoritative presentation contract. Prominently title it MentorTrace; put bilingual manuscript metadata above the usage heading, then content and technical comments, organization and flow comments, language and presentation comments, and coverage/remaining checks. Group the opening English usage paragraphs first, then their Chinese counterparts, without report-navigation prose. Group related content problems by revision object, keeping individual numbering and explanations, followed by shared revision actions and any useful local drafts; state which part of the actions each draft implements and what remains to be supplied. Sort a cross-section issue by the passage where the author first verifies or edits the underlying fact, not automatically by the earliest formula it affects; put that passage first in its Location and Original, then identify definitions and summaries to synchronize. Recheck numbering after relocation. Within each problem, present the complete English account first: priority, Location, Original, Comment and any Suggested revision. Then give only Chinese 审阅意见 and 建议修改. Do not repeat priority, location or Original in the Chinese part; keep the separate Chinese priority explanation in the opening 使用说明. Put each English source passage on its own line and any section tag before its quotation; use sufficiently distinctive surrounding source sentences for easy location, and for formula-centered issues include the relevant formula with precise page/column/section/equation anchors, preserving display versus inline math. Repeat any actionable English replacement wording in the corresponding Chinese action rather than referring to wording elsewhere. For cross-section issues, tell the author where to establish the missing fact before synchronizing earlier definitions or later claims. Use self-contained explanations without numbered dependencies and same-line label/value fields in separate paragraphs. Language comments use Location → Original → Comment → Suggested revision in English and 审阅意见 → 建议修改 in Chinese, repeating the same corrected English wording under both suggested-revision labels. Do not treat normal page-top figure floats in multi-column layouts as reading-order defects or preserve unsupported comments to maintain a count. Preserve actual uncertainty and priority; keep detailed review provenance private. Export PDF only when requested, using the saved print format.

### Generic Reader multiscale coverage

New runs use `reader_multiscale: 4` and `editorial_selection: 1`. Planning and Reader load [reader-checklist.md](references/reader-checklist.md), inventory actual chapter tasks, structural scales and relationships, and reconstruct understanding with evidence, including sufficient and unfinished outcomes. Inspect first use, display placement, paragraph handoffs, section arrangement and information selection separately from comprehension. Keeping the current arrangement is the baseline; an editorial question need not produce an edit. Freeze a grounded candidate when one is worth testing, otherwise an explicit null candidate with a manuscript-specific reason. Compare actual reader gain with transition, repetition, emphasis and space costs. Reader and Advisor distinguish necessary repairs, useful optional changes and equivalent style. Concern, Expression and good-paper examples guide questions and phrasing without obligating revisions. Merge and verify record decision groups, choose one compatible path per task, and explicitly dispose of competing proposals; independent content requirements survive. Preserve these groups in `organization_review.json`. Coverage is not a comment-count target. Frozen older runs retain their original protocol.

For stage-specific Expression content, follow [Review and drafting views](references/advisor-output.md#review-and-drafting-views): diagnose with the pinned review view and reload full selected frozen sources for post-merge drafting.

For new Advisor runs, follow [Shared analyses and explicit source results](references/advisor-output.md#shared-analyses-and-explicit-source-results): one analysis per actual problem, explicit result for every source, and no assumed review of unused associations.
