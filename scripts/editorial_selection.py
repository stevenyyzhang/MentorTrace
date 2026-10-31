"""Account for editorial decisions and chosen outputs, not measured prose quality."""

BRANCH_SCHEMA = '''EDITORIAL SELECTION v1: Keeping the original is the baseline. A Concern, Expression or good-paper example is a source of questions and feasible wording, not an obligation to diagnose or rewrite. Distinguish a necessary dependency repair, a useful optional change, equivalent style, and an unknown author fact. For optional improvement claims, assess concrete reader benefit against transition, repetition, emphasis and space costs. A mentor-style writing goal can instead justify a compatible expression choice without demonstrated superiority. State this distinct purpose in reason/gain; do not invent a reading benefit or a defect. For the same reader task, compare alternatives and prefer a compatible path rather than issuing one suggestion for every possible placement. Preserve independent content requirements even when a rearrangement is rejected. Coverage records may conclude keep; no issue quota and no assumption that a final draft is error-free.'''

MERGE_SCHEMA = '''EDITORIAL DECISION GROUPS v1: Also return editorial_selection:[{id,input_ids:[],reader_task,current_arrangement,evidence:[],preferred_action:"keep|change|defer",selected_output_ids:[],reason,gain,cost,compatibility}]. Group optional source proposals by the underlying reader task/decision, not merely by location or shared vocabulary. Every input_organization_suggestions ID occurs exactly once across groups. Compare keeping the original with viable alternatives and select one preferred path per group, possibly consisting of several jointly necessary operations. selected_output_ids contains the exact optional suggestion IDs and/or incorporated content finding IDs delivered for that path; cover every delivered organization suggestion. Rejected alternatives must have explicit withdrawn/unresolved organization_dispositions, with manuscript evidence for withdrawal; don't silently omit them or mark them merged into a different proposal. A keep/defer group selects no outputs. New proposals also need a group (input_ids may be empty only when selected outputs are genuinely new). Give the evidenced gain or the mentor-style alignment goal (comparative quality may be unestablished), cost and compatibility with other chosen groups; coexisting independent requirements must not be lost. Select no mutually exclusive placement, duplicated rewrite or incompatible full-paragraph replacements. Verify rechecks the chosen set against the original and supplied prior group record; it may change a choice with evidence. Fields establish traceability, not semantic correctness or mentor endorsement.'''


def require(test, message):
    if not test:
        raise ValueError(message)


def validate(x, context, pages, anchor):
    groups=x.get('editorial_selection')
    require(isinstance(groups,list), 'Missing editorial selection groups')
    incoming={s['id'] for s in context.get('input_organization_suggestions',[])}
    suggestions={s['id'] for s in x.get('organization_suggestions',[])}
    content={f['id'] for f in x['findings'] if f.get('finding_type')!='surface' or context.get('review_quality')}
    dispositions={d['input_id']:d for d in x.get('organization_dispositions',[])}
    seen_inputs=set();seen_outputs=set();seen_groups=set()
    for group in groups:
        gid=group.get('id')
        require(isinstance(gid,str) and gid and gid not in seen_groups, 'Invalid editorial group ID')
        seen_groups.add(gid)
        for key in ['reader_task','current_arrangement','reason','gain','cost','compatibility']:
            require(isinstance(group.get(key),str) and group[key].strip(), 'Incomplete editorial selection '+key)
        inputs=group.get('input_ids');outputs=group.get('selected_output_ids')
        require(isinstance(inputs,list) and len(inputs)==len(set(inputs)) and set(inputs)<=incoming,
                'Invalid editorial group inputs')
        require(not seen_inputs & set(inputs), 'Editorial input belongs to multiple decisions')
        seen_inputs.update(inputs)
        require(isinstance(outputs,list) and len(outputs)==len(set(outputs)) and set(outputs)<=suggestions|content,
                'Invalid editorial selected outputs')
        # Optional proposals may have only one preferred decision; a distinct
        # content requirement can also support another group as context.
        require(not (seen_outputs & set(outputs) & suggestions), 'Editorial output selected by multiple decisions')
        seen_outputs.update(outputs)
        action=group.get('preferred_action')
        require(action in {'keep','change','defer'}, 'Invalid editorial preferred action')
        require(bool(outputs)==(action=='change'), 'Editorial preferred action/output mismatch')
        require(inputs or outputs, 'Empty editorial decision')
        require(isinstance(group.get('evidence'),list) and group['evidence'], 'Editorial selection lacks evidence')
        for evidence in group['evidence']:anchor(evidence,pages)
        mapped={oid for iid in inputs for oid in dispositions[iid]['output_ids']+dispositions[iid].get('content_output_ids',[])}
        require(mapped<=set(outputs), 'Editorial selected path contradicts source dispositions')
        extra=set(outputs)-mapped
        new={s['id'] for s in x.get('organization_suggestions',[]) if s.get('new_in_stage') is True}
        if context.get('review_quality'):
            new.update(t for d in x.get('dispositions',[]) if d['status']=='incorporated' for t in d['output_ids'])
        require(extra<=new, 'Editorial selected output has no source in this decision')
    require(seen_inputs==incoming, 'Editorial selection input coverage mismatch')
    require(suggestions<=seen_outputs, 'Delivered editorial suggestion missing preferred decision')
