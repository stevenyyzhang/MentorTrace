# Reading across passages, sections and the whole manuscript

This module adds reading tasks, not an outline template or a quota of criticisms. Keep three judgments distinct: understanding available at the current reading point; the argument formed by a complete section; and the fidelity of summaries to the whole paper. A later explanation may establish completeness without repairing premature use. A clear preview may be sufficient without repeating a proof.

## Reader: complete the section, then revisit its parts

Use three intersecting dimensions: the passage's job (model, problem formulation, method, proof, experiment, summary, or another actual task), its scope (reading point, adjacent paragraphs, argument unit, subsection, section, cross-section dependency or whole paper), and the relationship being reconstructed (for example scenario-to-equation, assumption-to-use or claim-to-evidence). A short subsection can have a structural gap; length is not the trigger. Cover substantive body sections as well as the opening and closing summaries. An argument unit may cross headings when several parts jointly establish one result.

For each section account, make the job and relevant scope explicit in `section_job` and `synthesis`; use anchored `paragraph_roles` to show the connections. In `selection`, distinguish necessary retained material, any missing connection, and justified compression/movement. Record a successful reconstruction when the text is sufficient. Record unread/unreadable scopes in `limits`. These are concise coverage records, not a finding quota or a requirement for one comment per paragraph.

| Passage job | Relationships to reconstruct when applicable |
|---|---|
| Abstract and contribution account | Actual task, methods' distinct roles, supported results and scope; summary-to-body fidelity; adopted tools versus new contributions |
| Motivation and related work | Situation, relevant prior capability, remaining limitation and the proposed direction; relevance-based space allocation and paragraph handoffs |
| System model | Participants and roles, interaction/timing, observation generation, known/unknown quantities and assumptions, then the task enabled by the model; connections between prose and equations |
| Problem formulation | Available model information, desired output, objective/constraints and their meaning; transition from describing a system to posing the research problem |
| Method or algorithm | Difficulty, core idea, module roles, inputs/outputs and dependencies, executable steps and the connection to the claimed capability |
| Theory and proof | Question, conditions, result, the role of proof components and the result's scope; distinguish a needed explanation from a legitimately deferred proof |
| Experiments and discussion | Claim to test, design/comparator, observation, explanation and supported inference; whether experiments collectively address the stated questions |
| Conclusion | Main supported outcomes, qualifications and implications; consistency with the actual body rather than repetition of aspirations |

These are relationship prompts, not mandatory section headings or fixed writing orders. Reader judges whether the intended audience can reconstruct the account from the manuscript. Technical separately judges validity and evidential support; do not make Reader prove every theorem again. A formula can be correct while its place in the argument remains unexplained. Conversely, a difficult technical result is not automatically an exposition defect.

Review the abstract and each substantive section at its natural boundary. Identify the section's actual task and briefly map its paragraphs to roles and connections. For a long section, group paragraphs only when they serve the same task, preserving locations. Explain what the section establishes as a whole. Check whether consecutive paragraphs genuinely develop that account, rather than merely sharing a topic. Mark unreadable or unreviewed sections explicitly; do not silently select only problematic sections.

Assess information selection as well as presence: what must be retained to establish the task, what important link is missing or underemphasized, and what could be compressed, moved or omitted without losing evidence or necessary qualification? A correct sentence may still distract from this section's job. Conversely, repetition in overview and implementation may serve different tasks. Do not impose a universal paragraph count, compulsory contribution bullets, fixed abstract order, or arbitrary word limit.

After reconstructing the section, make a distinct editorial pass. Test concrete first-use and display positions, paragraph handoffs, section boundaries and space allocation even when comprehension checks passed. For each candidate, name a plausible alternative with an exact source and destination, then compare its reader benefit, lost context, transition/citation cost and layout constraints with the existing arrangement. Do not dismiss a candidate by testing an unrelated or obviously worse move. Record why the existing order should stay or what anchored change would improve a reader's task. A section-level `selection` summary alone does not discharge an actionable editorial candidate; route necessary changes to findings and justified optional changes to organization suggestions. Account for planned candidates individually without imposing a finding count.

For an abstract, ask whether the reader can identify the actual task, distinctive approach, supported outcome and material scope without implementation detail crowding out the contribution. For an introduction, attempt to explain how the reviewed prior capabilities and remaining difficulty motivate this paper's approach. Separate evidence of an actual missing connection from a preference for a different exposition. External novelty claims remain unverified when the cited literature has not been read.

## Whole-paper return: summaries and contributions

After reading the body, revisit the abstract, contribution passage (whether or not headed Contributions), and conclusion. Map each substantive summary claim to the method, analysis or result supporting it. Check conditions and strength, distinguish adopted tools from added work, and ask whether the summary collectively captures the main supported contributions without duplication or omission of an essential result. Explain why a proposed addition is central to the paper's own argument; do not promote every equation or experiment into a contribution.

Do not declare a whole section sufficient merely because each local relation is individually plausible. Conversely, do not require a rewrite when the section already performs its task. Record a concise section account and evidence for the judgment. These records are coverage and reasoning summaries, not private chain-of-thought.

## Advisor: independent scope and historical evidence

The job-by-scope framework is Reader's coverage responsibility, not a required Advisor inventory. Advisor remains independently manuscript- and concern-driven. Historical source auditing is knowledge maintenance, not another review lane and not something every new manuscript review must repeat.

Apply relevant cards at their natural scope, including relationships among paragraphs and between summaries and body evidence. A cue about contribution organization need not become a single-sentence check. Preserve the card's conditional boundary: a source involving two algorithms does not require every new paper to have two. Retain independent manuscript-driven discovery. Do not receive Reader's section map or a predetermined list of defects. Use full archived evidence via the existing follow-up path when the runtime card cannot establish why a historical rewrite was requested. A student's subsequent revision is not proof of mentor approval; unexplained deletion does not establish its motive.

## From diagnosis to a revision proposal

During diagnosis, use existing findings for necessary repairs and `organization_suggestions` for concrete optional editorial improvements. These can span a whole section and include retain, delete, compress, move, add, merge or rewrite actions, not only reordering. In the existing `current_order` and `proposed_order` fields record the current passage arrangement and the proposed content/structure plan, with exact locations. For necessary repairs put the same detail in `closure_goal`. Explain the benefit, preserve required evidence, note changed transitions/references and distinguish missing author facts. Do not leave a proposal solely inside a sufficient check's reason.

Merge and verification must preserve the section-level purpose and all independently justified actions. Shared locations do not make a global argument repair a duplicate of grammar edits. Recheck deletion against dependencies and summary wording against body evidence.

After findings are verified and frozen, an authorized revision-proposal pass may draft a complete paragraph or section using the manuscript and retained requirements. Link the draft to those requirements, list retained/removed/moved content, and make author-dependent conditions explicit. Do not fabricate a novelty comparison, implementation, hypothesis or result. If several findings motivate one replacement passage, place one coordinated draft after their group's shared revision plan and explain its purpose and conditions directly; do not require numbered cross-references to understand it. Keep this pass separate from discovery; it does not apply edits to the manuscript or retroactively create discoveries. Follow report-language.md for bilingual comments; replacement English passages need no duplicate Chinese translation when the bilingual revision instructions already explain the changes.

## Generic Reader integration

Reader additionally follows [reader-checklist.md](reader-checklist.md): chapter task, structural scale and relationship type are intersecting dimensions. Inventory actual argument units and dependencies, attempt reconstruction, and account for all applicable scales. Advisor remains independent; Reader scope plans and audit records are not Advisor inputs. Preserve coordinated repairs across local checks during merge and verification.
