# Diagnosis contract

Object: stable ID, source anchor, source excerpt, passage responsibility, relation to check, assigned check lane. Planning carries no gap/sufficient verdict. Later objects retain their creation stage.

The independent Advisor interface declares its own anchored `relations` with local IDs before judgments. Checks reference `relation_id` and do not generate a replacement `required_relation`; the compatibility adapter obtains that text from the declared relation map. Advisor receives no general planning objects. Post-freeze correspondence to a general object is a sidecar mapping, not a prerequisite for accepting a new relation. ID consistency protects task handoff, not semantic correctness of the relation or judgment.

Execution state: pending, completed, unfinished. Judgment for completed checks: sufficient, gap, unknown, not_applicable. An unselected or unloaded item cannot be labeled sufficient or not applicable.

Check: object ID; actual evidence references; knowledge IDs if used; applicability conditions; what the author already supplied; required relationship; counterevidence; judgment and concise evidential explanation; uncertainty; finding IDs. Separate reporting clarity from technical validity when their conclusions differ. Do not request hidden chain-of-thought.

Reader checks include local accessibility and whole-paper support as separate fields. New findings require location, specific missing/conflicting relationship, consequence, and closure goal. No quota of criticisms. A schema validator checks references and completeness, not semantic correctness.

Inputs are supplied manuscript artifacts and explicit allowed references. Target comments, scoring inventories, later target versions, design documents containing target answers, and other runs' diagnoses are excluded during generation. Record actual transmitted text/images, not merely filenames. Provider/tool capability and execution logs must be audited before claiming isolation.

## Evidence and completion

### Judge sufficiency against the required relation

Before assigning `sufficient`, use the existing `reason` field to identify which supplied evidence answers `required_relation`, and explain the connection briefly. A relevant mention or a statement compatible with the manuscript is enough only when it actually answers that relation. An explicit assumption can establish the scope of a conditional result; it does not by itself establish how the assumed information is acquired or whether a broader claim holds. Require those additional relations only when the manuscript's claim or task depends on them.


Keep `required_relation` faithful to the planned relationship and the passage's responsibility. Do not silently narrow it to the part that is easy to support. If distinct relations need different judgments, use separate checks under the same object with unique check IDs; a sufficient subrelation does not close the remaining applicable relation. Briefly explain a justified scope adjustment in `reason`.

When the evidence does not answer the relation, distinguish a demonstrated explanatory or technical `gap` from `unknown` due to missing or unreadable evidence; use `not_applicable` for a relation the current claim does not require. Use unfinished execution when the check was not completed. Do not turn every unresolved relation into a finding. Preserve sufficient text and reasonable previews when their required support is supplied elsewhere in the manuscript, recording that support in the existing fields.

This is a judgment criterion, not a request for hidden reasoning or a new output field. During object planning, retain the existing prohibition on verdicts. During merge and verification, apply the same criterion to the supplied relations without inventing new check records or changing the stage schema. Structural validation cannot certify that evidence semantically answers a relation.

### Carry supported requirements into findings

Write each independently answerable gap as its own finding where it has distinct support and a distinct closure goal. State the actual missing explanation or conflicting relation, not just “clarify the method” or “report the settings.” Keep a necessary justification request explicit: “state the parameter” and “justify why this parameter may be shared or known” are different requirements when both are relevant. Do not generate either requirement when current manuscript evidence already closes it.

For an apparent explanatory gap, check the whole manuscript for an explicit answer or an adequate equivalent explanation. A correct inference the reviewer can supply is not automatically an explanation the author has supplied; identify why the missing connection matters to this manuscript's claim or intended reader. Conversely, a standard background fact or a reasonable forward reference need not be expanded without a concrete comprehension or validity obstacle. Preserve the existing sufficient/gap/unknown/not_applicable distinction; uncertainty alone does not justify criticism.

When a gap check supports a finding, preserve each distinct supported requirement from that check in the finding's existing `gap` and `closure_goal` fields: the concrete object, missing or conflicting relation, and what the author needs to answer. A broad heading may group requirements, but generic wording must not replace them. Use this test: could the author fully comply with the finding while still leaving the supported specific question unanswered? If so, make that requirement explicit or separate the finding.

Do not export every question from a check as a criticism. Exclude unsupported, answered or inapplicable subquestions with a brief basis in the check's `reason`; retain unresolved uncertainty explicitly. At generation time ensure the check judgment, explanation and linked finding agree. This is part of the initial output, not permission to rewrite frozen findings later. Existing check and finding IDs provide the trace; no new schema fields are needed.

Use exact page quotes or page-image descriptions for anchors. Record author explanation separately from the required relation and your judgment. Do not describe an inference as a quotation. Empty counterevidence means none was found in the supplied scope, not proof none exists.

Completed checks may be sufficient, gap, unknown or not_applicable. Unfinished checks have no judgment. A gap must link to a concrete finding and the finding back to its checks. Incomplete output is a recorded failure, not permission to skip an object or card. A syntactically valid response can still be substantively wrong.

Machine-readable stage schemas are injected by the runner and take precedence for field names. Additional semantic requirements here must appear inside their corresponding explanation fields. Evidence follow-ups use their own stage IDs; they never overwrite the first diagnosis.
