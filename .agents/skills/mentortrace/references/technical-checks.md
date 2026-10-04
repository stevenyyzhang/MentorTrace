# Manuscript-driven technical checks

Trace the actual objective, observations, unknowns, assumptions, operations and claimed outputs. For applicable objects check who knows a quantity, when it becomes available, what is identifiable, and what the algorithm consumes. Check distinctions between distributions and realizations, training and deployment, detection events and update events, and stated versus demonstrated guarantees when the manuscript raises them.

For a design choice, check its reason independently of formula correctness. For experiments, distinguish reported parameters, internally consistent settings, physical plausibility, fair comparison, uncertainty, and supported scope. No universal demand for new experiments, fixed tests or proof styles.

Original pages govern formulas; extraction corruption is not an author error. Mathematical assertions require readable premises and an actual derivation or cited support. Mark technical validity unknown when only a reporting omission is established. Use tools or external primary evidence only within the run's declared permissions, never silently expand the evidence boundary.

## Choose a relationship before a verdict

| Manuscript object | Relationship to reconstruct | Sufficient evidence may include |
|---|---|---|
| Receiver or estimator | observations → identifiable quantities → quantities actually consumed | Explicit observation model, information timing and detector input; an identifiable aggregate can suffice even if components are unknown |
| Learned/discrete component | objective terms → differentiation or assignment rule → updated parameters | An explicit gradient, straight-through, separate codebook or moving-average update; a claim of joint training alone does not select one |
| Changing deployment configuration | trained parameters → new inputs → generated outputs → retraining conditions | Defined parameter sharing and dimension handling; architectural compatibility alone does not guarantee performance |
| Assumption change | old assumptions → dependent operation → new validity conditions | A derivation, changed algorithm or bounded scope; repeating an old formula need not be wrong if its actual dependencies remain available |
| Baseline or method choice | task requirements → baseline limitations under those requirements → proposed capability | A specific comparison in the paper's setting; do not demand every known alternative |
| Experiment and claim | tested configuration → comparison → supported inference → scope | Evidence matching the claim; missing reporting, unrealistic settings and unsupported generalization are different issues |

Select applicable relationships from actual objects, not from topic-keyword matches. For each, seek the strongest passage that could already close the concern, including appendices. Then distinguish: sufficient; an evidenced gap; not applicable; or unknown because implementation/premises are missing. A missing specification supports a request for clarification, not an invented proof of failure.

These are general technical inspection routes, not evidence that the advisor asked each question. Historical cards provide more conditional examples through the separate advisor module.

For new protocols, perform the actual-setting applicability subpass in technical-applicability.md. Generic relationship coverage does not demonstrate that baseline parameter values satisfy the formula prerequisites.
