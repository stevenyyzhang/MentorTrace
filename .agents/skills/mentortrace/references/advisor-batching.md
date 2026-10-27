# Advisor direct full-manuscript review, capacity and workload

For ordinary v1.2 public-corpus reviews, use `config/advisor-groups.json`: 12 fixed
base groups own all 493 Concerns and all 1,581 Expressions exactly once. These
are source ownership groups, not a guarantee of 12 model calls. Do not reuse a
previous paper's request packets or capacity result for a new paper.
New direct runs also pin [output contract v1](advisor-output.md). Shared analyses,
exact source references, passage IDs and compact use IDs reduce repeated writing;
every Concern and Expression still requires an explicit result and validation.
Candidate associations need explanations only when actually adopted or an exception
is encountered; unlisted associations remain not_assessed, never implicitly reviewed.
The fixed groups provide source provenance, not runtime packing boundaries. New
plans cluster Expressions sharing active Concern context and pack across groups.
Each Concern has exactly one primary inspection, placed near its related
Expression packets when available; unlinked Concerns still receive full inspection.
This changes placement only, never source content or association judgments.

## Required order

1. Import the complete readable manuscript and page images; create the run with
   the ordinary `mentortrace_v1.py create` command. Confirm the actual user-selected
   model and effort, and keep Standard unless explicitly authorized otherwise.
2. Generate no `advisor_tasks` map. Use the complete frozen Concern and Expression
   inventories and reviewed source associations directly; no task-based retrieval
   selects or excludes initial Advisor sources. This preparation is local only.
3. On the first `run_authorized_stage.py` invocation, automatic capacity discovery
   and `advisor_batching.plan_run` finalize every Advisor packet before objects,
   Reader, Expert, Advisor or Editor review. No manual capacity numbers are needed.
   Omit the legacy `--context-window`, `--output-reserve`, `--image-token-reserve`
   flags. Keep the usual `--model`, `--effort`, `--settings-authorization` arguments.
4. The planner validates `inputs/advisor_plan.json`: complete source/use coverage,
   fixed-group ownership, packet count, full prompt size, capacity and workload reservations.
   Only after all packets fit both limits may the ordinary review sequence continue.
   Each submission repeats both checks and pins the detected context window.
   This is an automatic check, not a user inspection or approval step. Do not ask
   ordinary users to select profiles, enter capacity or approve individual packets.
   Read model metadata locally without a separate planning confirmation; host
   permissions and authorization for the actual model calls still apply.

`advisor_batching.py --run RUN --model MODEL --effort EFFORT` can prepare the same
plan without submitting a model request, before any review stage is prepared.
Existing frozen v1.1 runs keep their original behavior; never rewrite completed
or uncertain calls to migrate them. Use a new run for the new protocol.

## Coverage and splitting rules

Each assigned Concern independently prompts full-manuscript relationship checks.
Each Expression independently searches the full manuscript for its concrete
operations, conditions and limits, including uses beyond its Concern links.
No-match, keep, optional improvement, necessary repair, unknown and unfinished
outcomes remain distinct. No preliminary AI-selected task list restricts scope.
Reader/Expert retain object extraction and their original review inputs; their
plans, selected-case inventory and conclusions are not supplied to Advisor.

### Source responsibilities

New runs freeze `advisor_role_division: 1`. In the same combined review call:

| Source | Main responsibility | Legitimate contribution |
|---|---|---|
| Concern | Test the requirement, relationship, evidence and boundaries | Sufficient/gap/not-applicable/unknown/unfinished judgments |
| Expression | Compare actual source wording, syntax and bounded sentence/paragraph operations with the target | Repair realization, optional improvement, local expression repair, keep/nonmatch or unresolved inspection |

An Expression's generic instruction to define before use is not another requirement
if Concern already covers it. Identify the additional concrete realization, such
as a source-supported defining construction, modifier placement or anchored order
change. Concern sufficiency does not preclude a worthwhile optional improvement.
No Concern match is required for an independently supported expression improvement
or local expression error. Source prose alone cannot prove scientific invalidity.
Keep an already suitable target; source matching is not a rewrite obligation.

Every Expression transfer includes compact `expression_contribution` accounting:
role, actual adopted feature IDs, and supplied Concern IDs genuinely supporting its
linked checks. Existing transfer prose carries the additional operation, target
comparison, gain/keep reason and preserved conditions, without duplicate narration.
Reuse an existing target check/recommendation for the same requirement where
appropriate; retain all source links and independently answerable requirements.
Each candidate association retains a local disposition. Under the shared-result
contract, the model explains only adopted associations and encountered exceptions;
all others remain not_assessed. IDs/roles do not certify semantic fit.
Carry linked contributions into post-verification drafting; distinguish declared
discovery contributions from features actually realized in the delivered prose.
Previously frozen protocols without this flag retain their original schema.

New runs freeze `config/advisor-workload.json` as `inputs/advisor_planning_policy.json`
at creation, then freeze the selected profile as `inputs/advisor_workload.json`.
New policy v4 minimizes packets within the detected effective capacity and prefers
at most 12 packets. When complete packing needs more, automatically allow the
necessary extra packets without user confirmation and record the reason.
There is no fixed model-specific packet count. Use this approved workload profile:

| Profile | Primary Concerns | Operation units | Candidate associations | Complexity |
|---|---:|---:|---:|---:|
| compact | 120 | 400 | No independent count cap | 2000 |

Pack whole source units, including capacity-checked merging of light packets.
Minimize calls within the approved bounds; the heuristic does not prove a global
minimum. Do not automatically raise workload limits again. Expression count has
no independent hard cap: operations, boundaries and complete capacity constrain it.
Candidate associations retain a quarter of the old complexity charge, not a
quarter of their content or coverage. Six Sol packets and ten Astra packets were
offline examples for one paper, not defaults to hard-code or quality guarantees.
The profile's standalone-expression target only spreads unlinked Concerns; it
does not exclude Expressions or impose a separate source count.

Every complete valid plan proceeds without a planning confirmation, even above
12. Never stop merely because 12 is exceeded, pad a smaller plan to 12, or weaken
coverage/reserves/workload limits to meet it. Record actual count and overflow
reason in the plan. Recompute for each new manuscript and machine/model context.
If even one indivisible source cannot fit, or capacity metadata is unavailable,
no valid plan can be promised; retain materials and report the actual failure,
without requesting a routine profile or capacity choice.

Freeze max(12, actual planned packets) submission slots, so every planned packet
can run. This is a finite attempt budget, not a cap on automatic initial packing.
The transport atomically reserves a slot for each new Advisor adapter
invocation, including explicit retries and follow-ups; completed cached responses
use no additional slot. Failed or uncertain invocations retain their slots.
Inspect saved outcomes before any explicit retry; there is no automatic paid
retry policy. This counts workflow submissions, not unobservable internal
provider/client retries, and excludes other review lanes. It does not override
the host application's own permissions. Old frozen runs keep their old contracts.

Let C=primary Concerns, context_C=additional
Concern cards, F=sum(max(1, feature count, operation count)) per Expression,
B=exact-distinct conditions/restrictions/qualifications/limits per Expression,
and U=active Concern uses. Complexity is
`3*C + F + 0.25*B + 0.25*(U + 0.5*conditional_U + uncertain_U) + 0.5*context_C`.
These are structural planning proxies, not measured semantic difficulty or a
quality guarantee. Related context still consumes attention. Keep the pinned
capacity allowances. Frozen v2 policies retain their original weights and budgets.
Spread standalone Concerns through the Expression stream;
never front-load all of them solely because bytes fit. An indivisible source
that cannot meet either limit stops planning without dropping material.

New public runs also freeze `config/expression-concern-links.json` as a typed overlay.
The original corpus stays unchanged. `direct` identifies an implementation
candidate, not proof of present applicability. `conditional`
preserves partial associations and their full Concern context. Both remain in the
candidate manifest. Only individually rechecked `historical` links unsupported by the retained content are removed
from required use accounting and moved to local administration; the full
Expression still receives independent review. All original links can be restored.
The legacy label `historical` archives an unsupported link; it does not certify
that a particular historical edit or co-occurrence took place. Never weaken a
supported link merely to reduce request size.
The overlay declares its review scope and provenance. A `fresh_full_review` overlay
must cover every original edge with a new retained-content judgment, exact Expression
and Concern evidence, and an audited model-call identifier. Old judgments must not be
relabeled as new calls. `uncertain` edges remain active with full Concern context;
their unresolved conditions must be supplied to the reviewer. A semantic recheck is
not evidence that a particular manuscript has a defect or that quality has improved.
Pass `relation_condition` for conditional and uncertain links alongside the complete
source records. These notes bound applicability; they do not replace evidence or
establish a manuscript finding. Keep direct/conditional/uncertain cases in the same
single full review pass as all other Expressions.

- Inspect every Concern and every Expression. All 271 originally unlinked
  Expressions are included without task keyword retrieval or a preliminary map.
- A linked Concern helps locate the manuscript relationship; it does not prove
  an Expression is applicable. A sufficient Concern result does not automatically
  exclude a useful wording improvement. Unlinked Expressions independently seek
  corresponding passage jobs. Record applicability/non-applicability/unfinished
  work; neither a finding nor a rewrite is required for every source.
- Pack across fixed-group boundaries, using the final serialized request with
  full manuscript, rules, source records and unchanged images/output,
  system and text reserves. The deterministic ordering heuristic groups shared
  Concern context in locality windows; these are not model batches or a count cap.
  Actual packet boundaries satisfy complete-request capacity, the selected workload
  profile and the execution budget. Never fill toward 12, omit sources or
  reduce reserves to reach a target count.
  A Concern's many Expression uses may span subpackets: repeat the complete
  Concern as context where needed, but assign its primary inspection only once.
  Keep admitted companion components together as indivisible packing units.
  Plans list each packet's contributing `fixed_groups` for provenance; version 4
  also records candidate plans and the automatically selected execution budget.
- `primary_card_ids` alone require Concern dispositions. Other complete cards are
  use context; they may support checks but must not be counted as repeated primary
  coverage. Every supplied Expression requires an explicit source result; the
  program expands the transfer records without inventing judgments. It also
  preserves every candidate association, marking unjudged ones not_assessed.
  There are no preliminary
  task assignments or task-disposition requirements in the direct protocol.
- Use compact JSON and exact same-record feature references. Restore projections
  and compare full values locally; do not replace source fields with summaries,
  titles or shortened quotations. Each subpacket reads the same full manuscript;
  no other batch's judgments are provided. Merge/verify retain their v1.1 behavior.
- Use the reversible `exact_shared_values_v1` wire format: repeated values are
  defined in the same request, and homogeneous record lists may share column names.
  Resolve `$same` and `$rows` before judging; every evidence value remains available.
  Keep only publication-authorization and capacity bookkeeping in local request
  administration. Preserve source status, uncertainty, conditions, restrictions and
  all substantive evidence in the model input. The local reconstruction check must
  restore the complete original context, including the administration fields.
- Follow the shared-result contract for adopted associations and exceptions; do
  not reinstate exhaustive candidate-by-candidate prose. No source ID may be
  omitted from explicit results. This remains one review pass, not a preliminary
  applicability filter. Keep the pinned capacity reserves during execution.

## Capacity evidence and limits

`codex debug models` supplies the selected model's current catalog entry. Use its
`context_window` and `effective_context_window_percent`, not `max_context_window`
or a hard-coded 950,000-byte threshold. The isolated transport pins that detected
window for the run. Desktop model selection alone does not configure a script.
Unsupported CLI versions or missing metadata stop before review; update/login
and recheck rather than guessing capacity or silently changing models.

Text uses the larger cl100k/o200k token count with 10% headroom when tiktoken is
available; otherwise UTF-8 bytes provide a conservative text bound. The planner
reserves 64,000 tokens for output INCLUDING reasoning, 6,000 per paper-page image
and 8,000 for system overhead. These allowances were calibrated against saved Sol
trials on the same six-page manuscript, not all image sizes or other models.
Use the selected model's catalog context_window and effective percentage (currently
95%), not max_context_window or an API-advertised maximum. These are explicit
planning allowances, not measured provider limits or an output-length command.
The automatic catalog read may use the CLI's current cache; it is not a server
acceptance probe. Unknown output size, image processing and server limits remain
uncertain. If one complete source/dependency packet cannot fit, stop with the
scope retained; never truncate it or claim it was reviewed. Generation failures
remain inspect-first, with no new automatic paid retry policy.
New Codex capacity policies also enforce the observed turn/start ceiling of
1,048,576 input characters (conservative UTF-16 code-unit count), separately from
tokens. A token-fitting packet can still exceed this transport limit. Repack
whole sources losslessly before submission; never truncate. Preserve completed
or running packets whose exact prompts remain valid when recovering rejected ones.
Missing metadata, a long manuscript, indivisible dependencies or workload limits
can also block a 12-packet plan; do not describe every failure as a small model.
Other AI hosts need a reliable capacity adapter; no universal silent discovery
is promised, and Codex metadata must not be substituted for another host's capacity.

Offline coverage, capacity and lossless reconstruction checks do not establish
model comprehension, complete reasoning or improved review quality.
