# Reader and section-function checks

Before comments, locate the manuscript's actual claims, design choices, condition comparisons, key quantities, multi-step processes, and repeated explanations. Record the local passage's job and the relationship it needs, without predicting whether it fails. Assign objects to downstream checks; an object without a consumer remains unfinished.

General planning supplies Reader and Technical, not the independent Advisor lane. Preserve both ends of a relationship and what their connection establishes. For comparisons retain the alternatives, dimension, conditions and actual claim strength, with the complete source statement and necessary qualifications. Put the conclusion in the relation itself, not only in a quote. Do not upgrade motivation into universal superiority or weaken a comparison into merely describing different mechanisms. Unclear scope stays unclear. Separate independently answerable tasks without making every paragraph a task. Planning makes no sufficient/gap verdict.

For each relevant object distinguish design rationale, validity conditions, execution, capability comparison, definition, and organization. Checking one relation does not discharge another.

Use the full manuscript, while separately citing earlier/local support and later support. This is a sequential-reader perspective, not an experiment that hides future text. Ask what the intended reader must understand here, and what can legitimately wait. Do not require tutorials for domain common knowledge or copy a later proof into a clear preview.

For redundancy compare passage functions and dependencies, not text similarity alone. For displays inspect original images where spatial arrangement matters. Record the actual obstruction, its consequence, counterevidence, and minimum change; never manufacture one issue per section.

## Complete the reader's task

Inventory and attempt all substantive comprehension tasks warranted by this manuscript's actual claims and intended audience, using the scales, chapter tasks and relationship checks in [reader-checklist.md](reader-checklist.md). Do not sample only a small set of central tasks. Group related checks without creating a sentence-by-sentence quota. Examples are explaining a method choice, explaining how a design produces a claimed capability, following one algorithm execution from available inputs to outputs, or distinguishing prior capability from the contribution and its evidence. These are task examples, not obligations for every paper or paragraph. Use the stated audience; otherwise assume graduate-level domain knowledge without knowledge of manuscript-specific assumptions or notation.

Attempt each selected task using the manuscript. Give a concise account of the essential connections and cite their support, rather than merely declaring the explanation clear or unclear. Distinguish manuscript statements, routine background or direct derivations, and additional manuscript-specific assumptions, implementations or arguments that you would have to supply. Do not invent the latter to complete the task. A mechanism does not by itself justify its selection; a performance number does not explain its cause; listing contributions does not establish the research gap.

Use existing check fields: `author_explanation` describes what the paper supplies; `reason` briefly records the task outcome and any necessary unsupported connection; evidence, `local_support` and `later_support` locate the support. This is a short evidence-based account, not hidden reasoning or a new report per paragraph. When a task succeeds, record why it is sufficient. When it cannot be completed, identify the exact obstruction, why resolving it is the paper's responsibility for this audience, and the minimum connection needed. Routine definitions, simple derivations and legitimate forward references do not automatically require expansion. Missing or unreadable evidence remains unknown rather than an asserted omission.

Tasks may span planned objects. Preserve the existing coverage of assigned objects; task selection does not excuse unperformed checks. Add a newly encountered necessary dependency through `new_objects` and its own check when the plan omitted it. Two passages on the same subject can serve different reader tasks. Do not force new findings or require an author-written tutorial when the task is already achievable.


| Situation | Judgment boundary |
|---|---|
| A short preview names a method and explicitly points to a later derivation | Pass if the current task needs only the preview; do not demand the derivation twice |
| A decision depends on a manuscript-specific quantity defined later | Check whether its meaning is needed now; cite both locations before diagnosing a local obstacle |
| An overall explanation exists but omits one local operation | Identify the local gap without claiming the entire method is unexplained |
| Similar descriptions occur in overview and implementation | Compare their responsibilities; retain both if they serve distinct needs |
| A paragraph's intended job cannot be established | Mark the interpretation uncertain; do not impose an invented outline |

These are constructed calibration cases, not newly learned advisor evidence. A proposed reordering must identify which dependency it restores and which forward references it affects.

## Sentence and paragraph order

Assess whole-paper completeness separately from information available at the point of reading. For a relevant passage, identify what its sentences do, what the reader needs first, and whether the current order causes a concrete misunderstanding, avoidable backtracking, or interrupted argument. Later support can establish completeness without resolving a local ordering obstacle. A clear preview or legitimate forward reference can still be sufficient. Do not demand a reordering for every paragraph or impose one standard outline.

If the order obstructs a necessary reader task, record a content finding with the source and destination of the proposed move in its closure goal. If the text is understandable but a specific rearrangement would improve the flow, preserve an optional organization suggestion even when the underlying content check is sufficient. Do not leave that actionable proposal only in a check's reason.

For each proposal identify the anchored current arrangement, the proposed sentence/paragraph order or exact insertion point, the expected reader benefit, affected pronouns/transitions/cross-references, and any author confirmation needed. Moving an assumption forward must not invent or authorize that assumption. Use the runner's `organization_suggestions` extension when supplied; otherwise retain these details in a separate internal organization-suggestion record. Keep optional suggestions outside confirmed finding counts. In the author-facing report, use “Organization and flow comments / 篇章与行文意见” without an optional category prefix, following report-language.md; preserve the underlying judgment and conditions.

For section-level argument, information selection and whole-paper summary checks, also follow [section-argument.md](section-argument.md). Its runtime module is enabled for new section-review protocols; frozen older requests are unchanged.
