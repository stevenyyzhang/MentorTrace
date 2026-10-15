# Source-based editorial learning intake

For the language layer, retain source-bound subject/verb/complement forms,
collocations, qualification, transitions and cross-sentence progression in
Expression `language_features`. Preserve exact quotations and identify source genre;
frames with variable slots are analyst abstractions. Reuse existing verified
language choices without labeling them newly learned. Unknown authorship, held
operations and unmatched analytical proposals cannot supply mentor replacement
wording. Use `expression_realization.build_snapshot` to create a separate versioned
snapshot and per-record coverage; its checks do not replace contextual admission.

Use only when the user asks to learn from historical feedback or source examples.
The private source reading and the public abstraction are separate artifacts.

## Preserve the actual edit episode

Start from the requested sources and related existing intake records. Locate the
complete affected argument unit, not just inserted/deleted words. Create an episode
with stable ID, source-family/version IDs and byte-bound source locators. Retain:

1. Before passage and neighboring context, including its intended section task.
2. Literal feedback or mentor-authored edit, its location and attribution evidence.
3. After passage and actual modifier status; explicitly record when absent.
4. Subsequent feedback or correction; explicitly record when none is available.
5. Material changes in facts/claims as distinct from presentation-only changes.

Expression intake also needs its own source selection. A list selected while
extracting Concerns does not cover all mentor writing examples. Within the agreed
source scope, inspect attributed paragraph/section proposals and their available
replies or later versions even when they link no Concern. Preserve the complete
long annotation, including discussion and unfinished placeholders; distinguish
proposed prose from instructions and outline text. Record selected and deferred
sources and the coverage limit before learning. Do not describe a Concern-seeded
subset as complete Expression training.

Register every attributed annotation in the agreed scope, including empty
StrikeOut/Caret/Highlight objects. Each needs an explicit reuse, learned,
no-Expression, duplicate or held disposition. A duplicate needs the same
attributed event and unchanged source context; repeated versions are not
independent preference evidence. Preserve marked original text separately from
literal mentor wording. Complete coverage means no unprocessed candidates,
not admitting every mark into the runtime library.

Bind candidate later passages within a supported version series, with source and
page hashes. Record observed wording separately from its actual writer and mentor
acceptance. Unknown authorship permits a version-response observation, not a
mentor-authored after paragraph. Matching words alone do not certify chronology,
acceptance or recurrence. Preserve frozen earlier intakes and add a new intake.

Preserve compound edits jointly when they change the same reader task, and retain
independently answerable requirements separately. Never manufacture a before/after
contrast from unrelated versions. Unexplained deletion alone does not prove a
preference for concise writing. Read an accepted local wording change in its
paragraph context before deriving a wider prose preference.

## Derive an editorial lesson

For each episode write a concise, source-linked lesson with these fields:

| Field | Required content |
|---|---|
| `source_episode_ids` | Actual private source episodes; preserve family dependence |
| `authority` | Explicit mentor requirement, observed edit, student response, or analyst hypothesis |
| `reader_task` and `scope` | What the passage needs to accomplish and at what structural scale |
| `before_account` | Sentence/paragraph roles, existing support, and the precise difficulty |
| `observed_change` | Actual retain/delete/compress/move/split/merge/add/rewrite operations; unknown when absent |
| `changed_relationship` | The particular emphasis, dependency, handoff or evidence distinction affected |
| `after_account` | What changed and what remains unsupported; no inferred acceptance |
| `transfer_conditions` | Conditions under which the same reader task exists in another paper |
| `do_not_transfer` | Exceptions, conflicting evidence, alternatives and facts that cannot be copied |
| `preference_status` | Local requirement, provisional preference, corroborated conditional preference, or unresolved |
| `support_and_conflict` | Exact evidence for attribution, recurrence, later corrections and exceptions |
| `source_review_status` | Which original pages/source spans were read and which were not |

Use `scripts/editorial_learning.py prepare` with an explicit episode JSON file to
freeze the evidence and a learning request; it sends no model call. Then use its
`check` command on the returned lessons to verify IDs, evidence quotes, chronology
status and conditions. Semantic reading is still required. The resulting private
lessons are candidate learning records, not automatically admitted runtime cards.

## Turn a lesson into usable knowledge

Apply the [Expression admission and Concern-overlap review](expression.md#expression-admission-and-concern-overlap)
before admitting a lesson. Preserve the edit for traceability even when no reusable
wording or concrete paragraph operation can be established; source coverage is
not an instruction to populate Expression with every substantive request.

Keep actual mentor wording and concrete paragraph actions in the private Expression
view of the same source episode, even when no complete Concern can be derived.
Expression may link zero or several Concerns; a Concern need not have replacement
text. `expression_runtime.py` validates attributed original text and source hashes
before building a separate frozen private snapshot. Use [Expression](expression.md)
for runtime retrieval and transfer. Missing applied after text stays unavailable;
neither an anonymous Concern abstraction nor a model reconstruction replaces it.

Compare it with existing concerns in all six fields. Preserve an additional
presentation distinction even when the technical topic is already covered. The new
manuscript check names the reader task and dependency, not the old paper's vocabulary.
The potentially sufficient response describes a bounded operation and its conditions;
the historical-response field records only what actually happened. Reuse or refine
an existing concern for the same requirement; add only a distinct requirement.

For published examples, retain the documented source roles/context and boundaries
under case-evidence.md. Their role is to show a possible execution of a reader task;
they do not establish mentor preference. A private lesson may link a relevant case
and concern, but this association does not feed Advisor the Reader inventory.

After source review, derive an anonymous English abstraction and promote it through
the existing frozen-snapshot and training-promotion process. Keep the raw episode,
identity evidence, exact comments, revisions and source-family registry private.
Do not update the 493-card dev.3 snapshot in place. Record the lesson-to-card link,
admission decision and unresolved evidence; a checked JSON record alone is not
admission or evidence of successful transfer. Then assess a new target with the
writing-transfer protocol, retaining keeps and failed transfers to revise the lesson.
