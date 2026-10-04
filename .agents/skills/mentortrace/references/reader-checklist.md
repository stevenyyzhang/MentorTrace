# General Reader: Multiscale Understanding and Exposition Checks

This catalog guides planning and actual Reader checks. It does not require a standard paper outline or a target number of issues. Reader checks whether the author establishes the relationships needed for understanding; Technical independently checks whether relationships, assumptions, equations, and methods are valid. Advisor independently reads the entire manuscript and uses concerns, without being restricted by general planning or this catalog's coverage records.

## Execution

1. Inventory the manuscript's actual important section tasks, argument units, and cross-section dependencies, and establish a neutral `reader_scope_plan`. A section task may be embedded in another section; a unit may span paragraphs and headings. Do not select only a few easy objects, or require every sentence to become an object.
2. Check local understanding in reading order, then integrated understanding at the end of argument units, subsections, and sections, and finally the whole-paper summary. Cover every substantive section and important dependency; add tasks absent from this catalog when needed.
3. For each applicable task, identify both ends of the relationship, summarize the understanding reconstructable from the manuscript, and identify support and information still needed from the author. Paragraph functions, symbol definitions, or a statement that the logic is clear do not complete an understanding check. Record concise evidence conclusions, not internal reasoning traces.
4. Judge separately whether the whole paper provides the information, whether it is available when first needed, and whether organization has concrete room for improvement. A later explanation does not automatically resolve reading-order problems, and explicit signposting does not automatically constitute a defect.
5. Cases help formulate checks, recognize sufficient explanations, and develop faithful revisions. Identify a task before selecting cases; identifying an existing defect is not a prerequisite. Complete general checks even without matching cases. Reader may add omissions through `new_objects` and `additional_units` without changing frozen case routing.
6. Distinguish sufficient, necessary repair, optional improvement, pending confirmation, and incomplete for each task. Necessary repairs enter findings; optional improvements enter organization_suggestions. Do not label unread scope inapplicable or manufacture comments to fill a coverage table.
7. **Perform a separate editorial check.** Reconstructable relationships do not establish that information order and allocation of space are suitable. During planning, formulate concrete neutral questions about actual first appearances of figures/tables, first uses of important definitions, subsection entrances and exits, neighboring-paragraph transitions, potentially excessive background, and information selection in the abstract, contributions, and conclusion. Explain why units with no applicable question lack one. For each question, specify an executable alternative: what to delete, compress, move, add, merge, or rewrite; its source and destination; and what may be lost. In particular, test whether figures/tables should follow their defining equations and whether a boundary paragraph belongs in the subsection responsible for its task. These are alternatives to test, not predetermined revisions. Top-of-page floating figures in two-column layouts may precede explanatory prose visually; this is normal typesetting. Judge comprehension order through the first textual reference, caption, and argument unit, rather than requiring relocation or every condition in the caption solely because of physical page position. Reader must compare first-reading benefits and costs using this **actual alternative**. Do not substitute an obviously unsuitable distant location and then declare the original reasonable, or replace editorial judgment with mere comprehensibility. Necessary repairs enter content comments; beneficial but nonessential adjustments enter optional organization suggestions. Executable alternatives must not remain only in a section's `selection` field. There is no minimum revision count, and comprehensible arrangements must not be forced into defect labels.

## Full Checklist (User-Confirmed Version)

The complete user-provided requirements are retained below without replacing them with a compressed summary. Determine applicability from the manuscript; do not mechanically enumerate every combination or impose an issue-count target.

<!-- FULL_CHECKLIST_BEGIN -->
Three intersecting dimensions organize the checks: structural scale, section task, and relationship type. Judgment and output requirements then apply consistently.

Relationships such as scenario-to-equation and assumption-to-later-use belong to the relationship dimension. The same relationship can appear in different sections or span different scales. For example, assumption-to-use can concern an explanation within one paragraph or connect the System Model with a theorem several pages later.

| Dimension | Question answered | Examples |
| --- | --- | --- |
| Structural scale | At what scope should the check operate? | Current position, neighboring paragraphs, argument unit, subsection, section, cross-section, whole paper |
| Section task | What should this part help the reader accomplish? | Understand the scenario, identify the gap, understand the method, assess evidence |
| Relationship type | Which contents should be connected? | Scenario -> equation, difficulty -> method, condition -> conclusion, result -> contribution |
| Check conclusion | Does the current writing complete the task? | Sufficient, necessary repair, optional improvement, pending confirmation, incomplete |
| Revision action | How should an established issue be addressed? | Retain, add, delete, compress, move, merge, split, rewrite |

The first three dimensions organize checks; the last two record outcomes. Do not check every possible combination mechanically or require a comment from each combination. Important relationships actually present in the manuscript require explicit checking grounds and disposition records.

The detailed checklist below records the requirements established through the preceding discussion.

### I. Structural Scales: From Understanding Here to Understanding the Entire Paper

#### 1. Current Reading Position: Is Earlier Information Sufficient for Understanding Here?

The object may be a sentence, definition, figure, equation, or operation.

- Object identification: What specifically do this method, this result, or the preceding conditions refer to? Are multiple interpretations possible?
- Understandable terminology: Have new terms, abbreviations, and symbols been introduced? Are standard background knowledge and paper-specific definitions distinguished?
- Available information: Which inputs, parameters, symbol values, or priors does this operation require? Does the reader know their sources?
- Stated conditions: Has a condition appeared when a derivation, explanation, or operation first depends on it?
- Equation introduction: Does the reader know what the equation describes, why it appears here, and what its term groups represent?
- Purpose of an operation: Why perform this transformation, define this intermediate quantity, or introduce this auxiliary problem now?
- Supported conclusion: Does a judgment following therefore, clearly, or this shows follow from the preceding material?
- Comparison reference: Better, lower, significant, or negligible compared with what, and under which conditions?
- Appropriate forward references: Later details may be signposted, but is information essential for current understanding also postponed?
- Necessary reading burden: Do currently unnecessary symbols, details, or qualifications hide the main point?

Do not ask only whether an explanation exists elsewhere. Ask whether readers can use the information when they first need it.

#### 2. Neighboring Paragraphs: Why Does the Next Paragraph Follow This One?

- What question, conclusion, or expectation does the preceding paragraph establish at its end?
- Does the next paragraph answer, develop, support, qualify, or begin another task?
- Is the actual logical link explicit rather than supplied only by Moreover or Therefore?
- Is there an unexplained change in object, scenario, assumption, metric, or level of discussion?
- Does the next paragraph use premises not established by the preceding one?
- Is a bridge needed to explain why the preceding paragraph leads to the next?
- Do both paragraphs repeat one task and warrant compression or merging?
- Does one paragraph combine two unrelated tasks and warrant splitting?
- Does order create difficulties by giving results before the problem or using objects before defining them?
- After moving or merging, do pronouns, figure/table references, equation references, and transitions remain valid?

#### 3. Complete Argument Unit: Does the Explanation Around One Question Close Its Argument?

An argument unit is defined by its task, not its heading. It may comprise two paragraphs or span multiple subsections. For example:

Why this model is needed -> what the model retains -> how those choices affect the method.

Or:

Difficulty in the original scheme -> introduced transformation -> what it solves -> remaining difficulty.

Check each item:

- Task: Which question does this unit answer?
- Starting point: Are the problem, background conditions, and existing capabilities sufficiently clear?
- Main claim: What does the author want the reader to accept?
- Intermediate links: Which explanations or reasoning steps between the starting point and claim cannot be omitted?
- Support: Do equations, proofs, figures, tables, or examples support this claim rather than a neighboring question?
- Qualification: Are the conclusion's conditions and scope retained?
- Closure: At the unit's end, does the reader know what is and is not solved?
- Downstream interface: Why is the result sufficient to enter the next step?
- Internal selection: Is some material relevant but unhelpful for this unit's task?
- Coordinated repair: If several links are missing, does the entire unit need coordinated adjustment rather than scattered added sentences?

#### 4. Subsection: Do Its Paragraphs Complete One Clear Task Together?

- Does the subsection heading match its actual contents?
- Does the opening explain why the subsection exists?
- Do the paragraphs have identifiable roles?
- Does their order follow information dependencies rather than the author's research chronology?
- Is the task promised by the heading completed?
- Are necessary steps missing, such as a method without inputs or results without their meaning?
- Does a switch to another task interrupt the main line?
- Are explanations repeated, background excessive, or details movable elsewhere?
- Does the ending explain the subsection's output and subsequent use?
- Should a long subsection split by subtasks, or fragmented subsections merge to restore a complete argument?

#### 5. Section: Do Its Subsections Jointly Fulfill Its Responsibility?

- Are the section objective and subsection roles clear?
- Are responsibilities duplicated, absent, or reversed in order?
- Do subsections jointly support a conclusion or merely list material side by side?
- Are important content's space and position proportional to its importance?
- Is a common framework needed before special cases?
- Are methods, scenarios, or experiments organized along comparable dimensions?
- Does a local detail occupy excessive space and hide the section's emphasis?
- Does the section ending answer the reader's entry question?
- Is coordinated relocation, merging, or rewriting needed beyond changing subsection headings?

#### 6. Cross-Section Relationships: Do Later Sections Correctly Continue Earlier Promises, Conditions, and Outputs?

- Do introductory difficulties match the difficulties actually solved by the method?
- Does the System Model provide the algorithm's required inputs?
- Are problem-definition objectives and constraints retained in the solution method?
- Do method assumptions agree with the model and theory?
- Does theoretical analysis concern the implemented method?
- Do experimental settings satisfy method and theory conditions?
- Can experimental metrics test the claimed capabilities?
- Are appendix conditions or key results available when needed in the main text?
- Does later text silently change symbols, objects, objectives, baselines, or scope?
- Do abstract, contributions, experimental discussion, and conclusion describe the same result consistently?
- Is material explained in one section appropriately recalled elsewhere, or duplicated at unnecessary length?

#### 7. Whole-Paper Summary: Can Readers State What Was Done, Why, and How Far the Evidence Goes?

- Is the core question stable and clear?
- Do the principal difficulties correspond to method design choices?
- Are the components alternatives, complements, stages, or solutions for different conditions?
- Are the most important contributions emphasized, or do minor details receive excessive attention?
- Do abstract and contribution summaries cover the work without exceeding evidence?
- Does the conclusion summarize proved or demonstrated results rather than introduce stronger claims?
- Can every paragraph be understandable while the combined main contribution remains unclear?
- Are essential limitations lost in the summary?
- Can readers form an accurate overall account without supplying multiple missing links themselves?

### II. Section Tasks: What Different Parts Need to Accomplish

These are writing tasks, not required headings. Related work, contributions, and objectives may all appear in the Introduction and still need separate identification and checks.

| Section task | Core responsibility |
| --- | --- |
| Abstract | Compress the problem, method, main results, and contribution accurately |
| Introduction | Establish the need and introduce the solution route |
| Related work | Explain existing capabilities, conditions, and the remaining problem |
| Contributions | Summarize new work and its value |
| System Model | Establish usable scenarios, interactions, observations, and conditions |
| Problem definition | Convert the scenario's task into a definite solution object |
| Method | Explain how to solve it and why key designs help |
| Theory | State results, conditions, and supporting reasoning |
| Experiments | Answer performance, mechanism, and applicability questions with suitable evidence |
| Conclusion | Summarize achievements, significance, and boundaries at the supported level |

#### 1. Abstract

- Is the research task clear rather than only a broad field?
- Is the existing difficulty's significance explained?
- Is the method's core role explained beyond technique names?
- If several algorithms are proposed, is their multiplicity explained along with tasks and conditions?
- If the method has multiple components, are their functional relationships explained?
- Are theoretical analysis, algorithm design, and experimental contributions distinguished?
- Do numerical gains include needed references, metrics, and conditions?
- Is performing a calculation promoted to achieving a more complete system capability?
- Are excessive details, repeated explanations, or irrelevant information included?
- Is the result most representative of the actual work omitted?
- Can every principal claim be traced to main-text evidence?
- If rewriting is needed, can it produce a coherent abstract rather than separate sentence patches?

#### 2. Introduction

- Does motivation arise from a concrete task or need?
- Is the difficulty a real obstacle in that task or a generic field challenge?
- Does background serve the later research question?
- Is the remaining problem clear after related work?
- Is the link from the remaining problem to the chosen method explained?
- Is the effectiveness of key design choices against the difficulty explained?
- Are relationships among multiple methods or scenarios stated?
- Are motivation, method overview, contributions, and article organization mixed together?
- Is historical background too long, discussion peripheral, or algorithm detail premature?
- After compression, are necessary motivation information and citations retained?
- Does the introduction's end prepare readers for what will be proved and demonstrated?
- Do contribution summaries match completed work?

#### 3. Related Work

- Is organization based on relevant capabilities, conditions, or approaches rather than a paper-by-paper list?
- Is each literature group's relation to the current paper explicit?
- Are prior capabilities represented fairly?
- Do alleged limitations specify scenarios and conditions?
- Is a different setting mistaken for a defect in prior methods?
- Is the reasoning from comparison to gap sufficient?
- Are methods compared on common dimensions?
- Do citations support the nearby specific claims?
- Are irrelevant details repeatedly introduced?
- When full texts are unavailable, are external factual judgments left for verification rather than asserted?

#### 4. Contribution Statements

- Is each item a new model, method, theory, explanation, or evidence?
- Does it state what is added and why it matters?
- Is using a standard tool called a contribution without its new role?
- Do several items repeat the same work?
- Should method and analysis be separate, or jointly constitute one contribution?
- Are multiple algorithms' values and relationships summarized accurately?
- Is the contribution list merely a section schedule?
- Is the most important finding omitted?
- Are broad performance or system-capability claims unsupported in the main text?
- Can each item be tied to a clear method, theorem, result, or experiment?

#### 5. System Model

This task requires particularly detailed checks.

- Scenario and participants: Who transmits, receives, and processes? What are targets, environment, and system boundaries?
- Geometry and physical quantities: Relative to what are distances, angles, and speeds defined? Do these definitions explain phase, attenuation, and delay?
- Interaction and timing: What happens at each stage? Which information is obtained before which operations?
- Processing and observations: How do physical signals become current observations? Are sampling, transformation, combining, and preprocessing explained?
- Prose and equations: Which objects or mechanisms generate principal terms, indices, and summations?
- Information availability: Which quantities are known, unknown, estimated, or supplied by other modules? When are they available?
- Assumptions and uses: Why adopt a condition, and where does it first matter?
- Simplification and consequences: Which effects are omitted or retained, and how does this affect scope or methods?
- Multiple cases: Is a common model established before necessary differences? Is case-by-case repetition excessive?
- Definitions and task: After defining variables, can readers state what is to be obtained from which observations?
- Model and problem definition: Is there a natural transition to unknowns, objective, and constraints?
- Information selection: Do long motivation, solver detail, or result discussions displace model explanation?
- Dependencies after relocation: When moving material out, does the model retain conditions needed later?
- Overall organization: Is reorganization as scenario -> process -> observation -> information conditions -> task needed instead of isolated additions?

The requirement is to explain equations' sources and purposes sufficiently, not to derive every standard model fully from first principles.

#### 6. Problem Definition

- Are solution objects, inputs, and outputs clear?
- Which unknowns require estimation, optimization, detection, or decisions?
- Why does the objective represent the real task?
- Do constraints arise from physics, resources, design choices, or analytical convenience?
- Are each variable's range and role understandable?
- Are data, parameters, decisions, and auxiliaries distinguished?
- Are existence detection and parameter estimation conflated?
- Is the problem's difficulty explained?
- Are later solution problems equivalent, approximate, relaxed, or replacements?
- Are necessary conditions hidden in an appendix or later text?
- At the subsection's end, is the method's next task clear?

#### 7. Methods and Algorithms

- Are inputs, outputs, and overall flow introduced first?
- How does each stage continue the preceding output?
- Why do key operations address the stated difficulties?
- Are purposes of intermediates, transformations, and auxiliary problems explained?
- After transformation, what is solved and what remains difficult?
- Why do multiple algorithms coexist, how are they chosen, and what costs do they incur?
- Are initialization, stopping, branches, and exceptions explained sufficiently for understanding and reproduction?
- Is required information actually provided earlier?
- How do theoretical formulas correspond to computational steps?
- Are generic methods and specific implementations clearly separated?
- Do premature details obscure the overall method?
- What is produced at completion and how do later modules or experiments use it?

#### 8. Theory and Proofs

- Before derivation, is the desired result and its need stated?
- Does the proposition concern the same object as the method?
- Are conditions, quantifiers, scope, and statistical meaning clear?
- Do important conditions precede first use?
- Are exact equalities, approximations, bounds, and asymptotic orders distinguished?
- What roles do lemmas, intermediates, and case splits serve?
- Is a connection missing between intermediates and the final conclusion?
- Does clearly replace nontrivial reasoning at a critical step?
- Are special-case results enlarged to general results?
- Does the main text provide needed understanding while leaving suitable detail to appendices?
- After the theorem, are design implications and limits explained?
- Are mathematical validity and engineering significance conflated?

Reader checks whether these relationships are established clearly. Technical must check equivalence, derivation validity, and sufficiency of conditions.

#### 9. Experiments and Discussion

- Which question does each experiment answer?
- Does that question correspond to an earlier claim?
- Are scenario, inputs, parameters, and baselines clear when the text first relies on the figure? A two-column top-of-page float is not defective merely because it precedes later explanatory prose visually. Independently check caption and text identification, and whether reproduction information is actually supplied.
- Why are these baselines or ablations chosen?
- Are comparison conditions clear enough to explain where differences arise?
- Are metrics, axes, normalization, and statistical conventions explained?
- Are single examples, averages, probability results, and theory distinguished?
- Does result description only repeat curves instead of answering the experiment's question?
- Is a mechanism explanation supported or inferred speculatively from one plot?
- Is qualitative demonstration promoted to reliability, universal superiority, or real-system guarantees?
- Do experiments form a coherent capability -> cause -> boundary evidence chain?
- Is the same information repeated while critical validation is missing?
- Do positive, negative, or unusual results need explanation?
- At the section's end, do readers know supported and untested claims?

#### 10. Conclusion

- Does it summarize completed work rather than repeat motivation?
- Does it accurately represent methods and results?
- Does it omit a result emphasized in the abstract?
- Do numerical results retain needed comparison conditions?
- Are new unsupported conclusions introduced?
- Are local examples promoted to general capabilities?
- Is it consistent with title, abstract, and contributions?
- Are important interpretive limits retained?
- Does future work match unresolved problems?
- Is whole-paragraph rewriting needed to avoid method-name lists and repetitive promotion?

### III. General Relationship Types: The Objects Reader Actually Tests

Use this layer as a common index so checks go beyond section completeness.

| Relationship | Core question |
| --- | --- |
| Object -> definition | Is the current object clearly identified? |
| Scenario -> representation | Does the scenario explain mathematical or visual representation? |
| Interaction -> observation | How does the system process produce the algorithm's data? |
| Information source -> operation | Has required information been obtained before execution? |
| Assumption -> use | Why is the condition needed, and is it stated before dependency? |
| Problem -> objective | Does the solution objective match the actual task? |
| Difficulty -> design | How does the design address the earlier difficulty? |
| Transformation -> effect | What does it solve, retain, and leave unresolved? |
| Step -> step | Does the preceding output support the next step? |
| Definition -> task | What does the new variable or intermediate accomplish? |
| Claim -> evidence | Does evidence answer the actual claim? |
| Result -> explanation | Do observations support the proposed reason? |
| Local -> overall | How broadly can a local result support conclusions? |
| Method -> method | Are methods alternatives, complements, stages, or condition-specific? |
| Paragraph -> section task | Does the paragraph serve its section? |
| Detail -> importance | Are space and position proportional to argumentative value? |
| Main text -> appendix | Is essential understanding postponed improperly? |
| Summary -> actual work | Do abstract, contributions, and conclusion faithfully compress the paper? |

### IV. Records Required for Each Check

To prevent coverage records that do not identify what was checked, every important check must record at least:

| Field | Required record |
| --- | --- |
| Location and scope | Involved sentences, paragraphs, subsections, or sections |
| Section task | What these contents should help the reader accomplish |
| Structural scale | Current point, paragraph transition, unit, subsection, section, cross-section, or whole paper |
| Relationship to check | Which two contents require what connection |
| Existing manuscript support | Specific prose, equations, figures/tables, and locations |
| Actual understanding test | Whether the information reconstructs the process, explains the choice, or supports the conclusion |
| Judgment | Sufficient, necessary repair, optional improvement, pending confirmation, or incomplete |
| Revision requirements | What to retain, add, delete, compress, move, or rewrite and where |
| Impact scope | Definitions, transitions, references, and summaries requiring synchronized changes |
| Rewrite delivery | Directly usable text, a conditional draft, or explicit missing information |

The actual understanding test is the most important record. For example:

Do not record only that the model gives an observation equation. Check whether the earlier scenario and process let readers explain who obtains the observation, what each term group represents, and which known quantities subsequent processing requires.
<!-- FULL_CHECKLIST_END -->

## Run Records and Staged Delivery

The new `reader_multiscale: 3` protocol freezes `reader_editorial_plan` and each concrete alternative in addition to scope planning and multiscale audits. `reading_review.editorial` must record each alternative's first-reading benefits, costs, and selection reasons. Additional candidates use `editorial_additions`. Each of the seven scales still records checked, inapplicable, or incomplete status and links actual tasks and original checks. Pending confirmation means checked with insufficient evidence, not unperformed. Anchor, field, and reference validation detects missing or contradictory records but cannot establish semantic quality; review must read the manuscript to verify judgments. Frozen version-1 and version-2 runs retain their original protocols.

Freeze original comments first, consolidate and review second, and generate revision advice last. One overall argument problem may span local checks; merging must retain the common repair objective, scope, and action dependencies rather than split or delete based on similar wording. When facts suffice, provide directly usable sentence/paragraph rewrites and specify what to retain, delete, compress, move, merge, add, or rewrite, with transitions and references adjusted. When facts are insufficient, identify missing material or give explicitly conditional drafts; do not invent results, assumptions, or author intent.

For retained whole-paragraph or whole-section repairs in the abstract, introduction, contributions, or other sections, the revision stage must explicitly deliver a draft, conditional draft, request for author information, or a reason that a complete rewrite is unnecessary. Do not silently skip these items. Present necessary repairs separately from optional improvements; rewrite counts and length do not measure effectiveness.

The full checklist's revision requirements, impact scope, and rewrite delivery are completed in stages. Original diagnosis retains the necessary repair objective and affected scope before freezing. After review, each retained issue or coordinated repair group receives specific actions, synchronized adjustments, and delivery status. Sufficient checks require no invented revisions. Unknown author facts remain missing information and must not be assumed before appearing in a draft.
