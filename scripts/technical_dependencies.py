"""Link existing technical scope records; do not create another review inventory."""

PLAN = '''TECHNICAL DEPENDENCIES: Derive questions from each actually used method/result chain:
what a step consumes, where that input/condition is established, what is produced, and which
later calculation, implementation choice or displayed claim relies on it. Seek the strongest
existing explanation, including appendices, before proposing a gap. Record independent
questions in the existing coverage_basis or configuration dimensions, not another checklist.
Retain decision-changing conditions, branches and downstream uses in the question. A named
topic is not its independently answerable requirements. No fixed parameter list, mandatory
new experiment, all-pairs matrix or historical expected answer. Reuse existing object IDs.
'''
REVIEW = '''TECHNICAL DEPENDENCY CLOSURE: In each technical coverage_answer add dimension_refs:
[{configuration_id,dimension_id}] for actual configuration dimension judgments answering that
question, or [] when no configuration dimension applies. Reuse checks/evidence rather than
repeat them. An answered label cannot cover an unknown/unfinished referenced dimension.
Trace the actual producer/consumer conditions and reported scope within this existing call;
add overlooked, independently answerable questions through new_coverage_basis. Partial
coverage names the residual question and its condition; do not replace it with a broad topic.
Do not promote missing implementation facts to proof of failure. The existing source reviewer
audits these scope links and routes concrete residuals; no extra independent review phase.
'''


def validate(response, context):
    if not context.get('technical_dependency_v1'):
        return
    dimensions={(r['configuration_id'],d['dimension_id']):d
                for r in response.get('configuration_review',{}).get('items',[])
                for d in r.get('dimension_reviews',[])}
    for answer in response.get('coverage_answers',[]):
        refs=answer.get('dimension_refs')
        if not isinstance(refs,list):raise ValueError('Technical coverage needs explicit dimension_refs (empty allowed)')
        keys=[]
        for ref in refs:
            if not isinstance(ref,dict) or set(ref)!={'configuration_id','dimension_id'}:
                raise ValueError('Invalid technical dimension reference')
            key=(ref['configuration_id'],ref['dimension_id'])
            if key not in dimensions or key in keys:raise ValueError('Unknown/duplicate technical dimension reference')
            keys.append(key)
            dim=dimensions[key]
            if not set(dim['check_ids'])<=set(answer['check_ids']):
                raise ValueError('Coverage omitted referenced dimension checks')
            if answer['status']=='answered' and dim['status'] in {'unknown','unfinished'}:
                raise ValueError('Whole-question closure conceals unresolved technical dimension')
