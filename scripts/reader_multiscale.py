"""Versioned Reader coverage accounting; validates evidence links, not editorial quality."""
SCALES = ['reading_point', 'adjacent_paragraphs', 'argument_unit', 'subsection',
          'section', 'cross_section', 'whole_paper']
PLAN_SCHEMA = '''MULTISCALE READER PLAN v1: Also return reader_scope_plan:[{id,anchors:[],chapter_tasks:[],scales:[],task,object_ids:[]}]. Use the seven scale keys reading_point, adjacent_paragraphs, argument_unit, subsection, section, cross_section, whole_paper. Inventory actual substantive sections and argument units, including implicit related-work/contribution tasks and important cross-section dependencies. Each unit has manuscript anchors, a concrete comprehension task and existing Reader object IDs. Every Reader object belongs to a unit. One unit may span headings or scales; avoid one object per sentence or a Cartesian-product quota. Plan neutral relationships, not friction, sufficiency verdicts or repairs. Identify locally needed information and section-wide tasks before case routing. Reader must revisit the inventory and can add missed units/objects; the plan is not a discovery ceiling.'''
READER_SCHEMA = '''MULTISCALE READER AUDIT v1: Keep the ordinary checks/findings/organization_suggestions and reading_review. Additionally return reading_review.multiscale:{additional_units:[],tasks:[{id,unit_ids:[],scales:[],relation_type,endpoints:[{anchor,role}],reader_task,reconstruction,support:[],missing_information,outcome:"sufficient|required_repair|optional_improvement|unknown|unfinished",check_ids:[],finding_ids:[],suggestion_ids:[]}],units:[{unit_id,status:"checked|unfinished",task_ids:[],reason}],scales:[{scale,status:"checked|not_applicable|unfinished",task_ids:[],reason}]}. additional_units use the planner's reader_scope_plan schema, anchored to new or existing Reader objects. Account for every planned/additional unit and all seven scales exactly once. A checked unit must have tasks covering every scale declared for it; a checked scale must cover every relevant unit. A scale with no applicable unit can be not_applicable with a manuscript-specific reason; an unread scope is unfinished, not not_applicable. Every Reader check must be linked to a task; task checks must belong to the cited units. Each task names at least two anchored relationship endpoints and briefly reconstructs the understanding supported by the manuscript; do not return private reasoning. Separate manuscript evidence, routine inference and missing author facts. This is more than naming paragraph roles. Support is a list of manuscript anchors. required_repair must link a reported finding; optional_improvement must link an organization suggestion; sufficient needs evidence and cannot link a finding; unknown/unfinished must explain the limit. Only concise evidence-based accounts are needed, not duplicated full comments. Additional tasks without a routed case still receive ordinary checks; do not change the frozen case route. No issue/rewrite quota. Validate semantic adequacy against the manuscript, not field presence.'''
EDITORIAL_FOCI = {'first_use', 'paragraph_handoff', 'information_selection',
                   'display_placement', 'section_arrangement', 'summary_alignment'}
PLAN_SCHEMA_V2 = PLAN_SCHEMA + '''\nEDITORIAL READER PLAN v2: Also return reader_editorial_plan:[{id,unit_ids:[],focus,anchors:[],question}]. Build neutral, manuscript-specific questions about information order and selection, independently of whether the argument is eventually understandable. Focus is one of first_use, paragraph_handoff, information_selection, display_placement, section_arrangement, summary_alignment. Inspect actual first appearances of figures/tables and their setup, subsection entrances and exits, adjacent paragraph handoffs, potentially expendable background, and abstract/contribution/conclusion selection. Name the concrete passages or displays in each question; do not merely ask if the section flows well. Each scope unit must have a relevant editorial question or a reader_editorial_exclusions item {unit_id,reason} explaining why order/selection has no meaningful alternative in that unit. Do not pre-judge or prescribe a move. Do not force one criticism per unit.'''
READER_SCHEMA_V2 = READER_SCHEMA + '''\nEDITORIAL READER AUDIT v2: Also return reading_review.editorial:[{plan_id,decision:"keep|required_repair|optional_improvement|unknown|unfinished",evidence:[],current_arrangement,reader_effect,action,reason,finding_ids:[],suggestion_ids:[]}], exactly once per reader_editorial_plan item. For every target, compare the current arrangement with a proposed alternative whose feasibility is still to be checked; explain in reader_effect whether the current order helps, impedes, or merely could improve the reader's task. For keep, say why moving/deleting/adding would not help; action may be "retain". For required_repair link an ordinary finding whose closure_goal identifies the insertion, deletion, move or rewrite and affected dependency. For optional_improvement link an organization_suggestion with concrete source/destination and affected links. Unknown/unfinished states need the precise missing evidence. A comprehension relation may be sufficient while its editorial judgment is optional_improvement: do not let the first judgment suppress the second. Do not silently leave a candidate only in section selection prose. If a substantial arrangement was discovered outside the plan, add an editorial target to reading_review.editorial_additions with the same plan fields and audit it here. No suggestion quota; a supported keep is a valid result.'''
PLAN_SCHEMA_V3 = PLAN_SCHEMA_V2 + '''\nEDITORIAL COUNTERFACTUAL PLAN v3: For each reader_editorial_plan target also give candidate_alternative:{operation,source,destination,expected_reader_gain,possible_cost}. The candidate must be a concrete, plausible delete/compress/move/add/merge/rewrite alternative tied to named manuscript passages, not a generic "reorder for clarity" or the current arrangement. If the figure's logical source/callout order places it before a defining equation, test whether moving the source placement after that equation or adding a genuinely needed prerequisite to the caption would help. Do not infer such an order defect merely from a normal top-of-page float in a multi-column layout: assess the first textual callout, caption purpose, and surrounding argument instead of physical page position alone. For a task/objective paragraph at a section boundary, test placing it under the section that executes the task. These are questions, not presumed fixes. Name the source and destination even if the operation is compression or deletion (destination may say "remove from section"). Do not derive alternatives from prior reviews.'''
READER_SCHEMA_V3 = READER_SCHEMA_V2 + '''\nEDITORIAL COUNTERFACTUAL AUDIT v3: For every reading_review.editorial row also give alternative_evaluation:{tested_change,reader_gain,reader_cost,verdict_reason}. Test the *planned* candidate at its named source and destination, not an easier or more remote alternative. State whether the gain survives necessary transitions, definitions, citations, and page/float constraints. A keep verdict must explain specifically why this candidate adds no worthwhile benefit; merely saying current text is understandable is insufficient. If a different alternative is better, add a new editorial target and assess it. A necessary content repair at the same location may remain linked to a keep-on-placement verdict. No minimum suggestion count.'''


def require(test, message):
    if not test:
        raise ValueError(message)


def unique(items, key, label):
    require(isinstance(items, list), 'Missing '+label)
    values=[x.get(key) for x in items]
    require(all(isinstance(v,str) and v for v in values) and len(values)==len(set(values)), 'Invalid/duplicate '+label)
    return set(values)


def validate_units(units, objects, pages, anchor):
    names=unique(units,'id','Reader scope units')
    allowed={o['id'] for o in objects if 'reader' in o['lanes']}
    for unit in units:
        require(not any(k in unit for k in ['judgment','outcome','gap','repair_goal','status']), 'Reader plan must not pre-judge')
        require(isinstance(unit.get('task'),str) and unit['task'].strip(), 'Missing unit task')
        require(isinstance(unit.get('chapter_tasks'),list) and unit['chapter_tasks'] and all(isinstance(v,str) and v.strip() for v in unit['chapter_tasks']), 'Missing chapter tasks')
        require(unit.get('scales') and set(unit['scales'])<=set(SCALES), 'Invalid unit scales')
        require(unit.get('object_ids') and set(unit['object_ids'])<=allowed, 'Scope must reference Reader objects')
        require(unit.get('anchors'), 'Missing unit anchors')
        for a in unit['anchors']:anchor(a,pages)
    return names


def validate_plan(x,pages,anchor,version=1):
    units=x.get('reader_scope_plan')
    validate_units(units,x['objects'],pages,anchor)
    covered={oid for u in units for oid in u['object_ids']}
    require(covered=={o['id'] for o in x['objects'] if 'reader' in o['lanes']}, 'Reader object missing scope unit')
    if version>=2:validate_editorial_plan(x,units,pages,anchor,version)


def validate_editorial_plan(x,units,pages,anchor,version=2):
    targets=x.get('reader_editorial_plan')
    target_ids=unique(targets,'id','Reader editorial targets')
    unit_ids={u['id'] for u in units}
    for item in targets:
        require(item.get('unit_ids') and set(item['unit_ids'])<=unit_ids,'Editorial target has unknown units')
        require(item.get('focus') in EDITORIAL_FOCI,'Invalid editorial focus')
        require(isinstance(item.get('question'),str) and item['question'].strip(),'Missing editorial question')
        require(item.get('anchors'),'Editorial target lacks anchors')
        if version>=3:
            alt=item.get('candidate_alternative')
            require(isinstance(alt,dict) and all(isinstance(alt.get(k),str) and alt[k].strip()
                for k in ['operation','source','destination','expected_reader_gain','possible_cost']),
                'Missing editorial counterfactual')
            require(alt['operation'] in {'delete','compress','move','add','merge','rewrite'},
                'Invalid editorial counterfactual operation')
        require(not any(k in item for k in ['decision','judgment','gap','action','suggestion']),
                'Editorial plan must not pre-judge')
        for a in item['anchors']:anchor(a,pages)
    exclusions=x.get('reader_editorial_exclusions')
    require(isinstance(exclusions,list),'Missing editorial exclusions')
    excluded=set()
    for item in exclusions:
        uid=item.get('unit_id')
        require(uid in unit_ids and uid not in excluded and bool(item.get('reason')),
                'Invalid editorial exclusion')
        excluded.add(uid)
    covered={uid for item in targets for uid in item['unit_ids']}
    require(not covered&excluded and covered|excluded==unit_ids,
            'Editorial plan omitted or contradicted a scope unit')
    return target_ids


def validate_review(x,context,pages,anchor):
    audit=x['reading_review'].get('multiscale')
    require(isinstance(audit,dict),'Missing multiscale Reader audit')
    extra=audit.get('additional_units')
    require(isinstance(extra,list),'Missing additional units')
    units=context['reader_scope_plan']+extra
    objects=context['objects']+x.get('new_objects',[])
    uids=validate_units(units,objects,pages,anchor)
    require({o['id'] for o in objects if 'reader' in o['lanes']}<={oid for u in units for oid in u['object_ids']}, 'New Reader object missing scope unit')
    ub={u['id']:u for u in units}
    tasks=audit.get('tasks');tids=unique(tasks,'id','Reader tasks');tb={t['id']:t for t in tasks}
    checks={c['id']:c for c in x['checks']};finds={f['id']:f for f in x['findings']}
    suggestions={s['id']:s for s in x.get('organization_suggestions',[])}
    for t in tasks:
        require(t.get('unit_ids') and set(t['unit_ids'])<=uids,'Task has unknown units')
        require(t.get('scales') and set(t['scales'])<=set(SCALES),'Invalid task scales')
        require(set(t['scales'])<={s for uid in t['unit_ids'] for s in ub[uid]['scales']},'Task scale absent from units')
        require(all(isinstance(t.get(k),str) and t[k].strip() for k in ['relation_type','reader_task','reconstruction']), 'Missing task reconstruction')
        require(isinstance(t.get('missing_information'),str),'Missing explicit information limit')
        require(isinstance(t.get('endpoints'),list) and len(t['endpoints'])>=2,'Relationship needs two anchored endpoints')
        for end in t['endpoints']:
            anchor(end['anchor'],pages);require(bool(end.get('role')),'Endpoint role missing')
        require(isinstance(t.get('support'),list),'Missing task support')
        for a in t['support']:anchor(a,pages)
        require(t.get('check_ids') and set(t['check_ids'])<=set(checks),'Task has unknown checks')
        allowed={oid for uid in t['unit_ids'] for oid in ub[uid]['object_ids']}
        require(all(checks[c]['object_id'] in allowed for c in t['check_ids']),'Task check outside cited units')
        for field,known in [('finding_ids',finds),('suggestion_ids',suggestions)]:
            require(isinstance(t.get(field),list) and set(t[field])<=set(known),'Unknown task '+field)
            for ref in t[field]:require(set(known[ref]['check_ids'])&set(t['check_ids']),'Task output has no supporting check')
        outcome=t.get('outcome');cs=[checks[c] for c in t['check_ids']]
        require(outcome in ['sufficient','required_repair','optional_improvement','unknown','unfinished'],'Invalid task outcome')
        if outcome=='required_repair':require(bool(t['finding_ids']),'Required repair lost finding')
        else:require(not t['finding_ids'],'Non-repair task asserts finding')
        if outcome=='optional_improvement':require(bool(t['suggestion_ids']),'Optional improvement lost suggestion')
        if outcome in ['sufficient','optional_improvement']:
            require(t['support'] and all(c['execution']=='completed' and c['judgment']=='sufficient' for c in cs),'Sufficient task lacks supported sufficient checks')
        if outcome=='unknown':require(t['missing_information'] and any(c['judgment']=='unknown' for c in cs),'Unknown task lacks unknown check/limit')
        if outcome=='unfinished':require(t['missing_information'] and any(c['execution']=='unfinished' for c in cs),'Unfinished task lacks unfinished check/limit')
    require({c for t in tasks for c in t['check_ids']}==set(checks),'Reader check omitted from task audit')
    rows=audit.get('units');require(unique(rows,'unit_id','unit coverage')==uids,'Unit coverage mismatch')
    for row in rows:
        require(row.get('status') in ['checked','unfinished'] and row.get('reason'),'Invalid unit disposition')
        require(isinstance(row.get('task_ids'),list) and set(row['task_ids'])<=tids,'Invalid unit task IDs')
        expected={t['id'] for t in tasks if row['unit_id'] in t['unit_ids']}
        require(set(row['task_ids'])==expected,'Unit/task reverse link mismatch')
        if row['status']=='checked':
            require(set(ub[row['unit_id']]['scales'])<={s for tid in expected for s in tb[tid]['scales']},'Checked unit omitted scale')
            require(all(tb[tid]['outcome']!='unfinished' for tid in expected),'Unfinished task marked checked')
    unfinished_units={r['unit_id'] for r in rows if r['status']=='unfinished'}
    rows=audit.get('scales');require(unique(rows,'scale','scale coverage')==set(SCALES),'Seven-scale accounting mismatch')
    for row in rows:
        require(row.get('status') in ['checked','not_applicable','unfinished'] and row.get('reason'),'Invalid scale disposition')
        require(isinstance(row.get('task_ids'),list) and set(row['task_ids'])<=tids,'Invalid scale task IDs')
        expected={t['id'] for t in tasks if row['scale'] in t['scales']}
        require(set(row['task_ids'])==expected,'Scale/task reverse link mismatch')
        relevant={u['id'] for u in units if row['scale'] in u['scales']}
        if row['status']=='not_applicable':require(not relevant and not expected,'Applicable scale cannot be skipped')
        if row['status']=='checked':
            require(not relevant & unfinished_units,'Unfinished unit in checked scale')
            require(expected and relevant<={uid for tid in expected for uid in tb[tid]['unit_ids']},'Checked scale has uncovered units')
            require(all(tb[tid]['outcome']!='unfinished' for tid in expected),'Unfinished scale marked checked')
    if context.get('reader_multiscale',1)>=2:
        validate_editorial_review(x,context,pages,anchor,checks,finds,suggestions,uids)


def validate_editorial_review(x,context,pages,anchor,checks,finds,suggestions,unit_ids):
    additions=x['reading_review'].get('editorial_additions')
    require(isinstance(additions,list),'Missing editorial additions')
    version=context.get('reader_multiscale',2)
    source={'reader_editorial_plan':context['reader_editorial_plan']+additions,
            'reader_editorial_exclusions':[]}
    all_targets=source['reader_editorial_plan']
    if version>=3:
        for item in all_targets:
            alt=item.get('candidate_alternative')
            require(isinstance(alt,dict) and all(isinstance(alt.get(k),str) and alt[k].strip()
                for k in ['operation','source','destination','expected_reader_gain','possible_cost']),
                'Missing editorial counterfactual')
            require(alt['operation'] in {'delete','compress','move','add','merge','rewrite'},
                'Invalid editorial counterfactual operation')
    target_ids=unique(all_targets,'id','Reader editorial targets')
    original={t['id'] for t in context['reader_editorial_plan']}
    for item in additions:
        require(item['id'] not in original and item.get('unit_ids') and set(item['unit_ids'])<=unit_ids,
                'Invalid editorial addition')
        require(item.get('focus') in EDITORIAL_FOCI and bool(item.get('question')) and item.get('anchors'),
                'Incomplete editorial addition')
        for a in item['anchors']:anchor(a,pages)
    rows=x['reading_review'].get('editorial')
    require(unique(rows,'plan_id','Reader editorial audit')==target_ids,
            'Editorial audit target mismatch')
    for row in rows:
        require(row.get('decision') in {'keep','required_repair','optional_improvement','unknown','unfinished'},
                'Invalid editorial decision')
        require(all(isinstance(row.get(k),str) and row[k].strip() for k in
                    ['current_arrangement','reader_effect','action','reason']),
                'Incomplete editorial judgment')
        require(isinstance(row.get('evidence'),list) and row['evidence'],
                'Editorial judgment lacks evidence')
        if version>=3:
            assessment=row.get('alternative_evaluation')
            require(isinstance(assessment,dict) and all(isinstance(assessment.get(k),str) and assessment[k].strip()
                for k in ['tested_change','reader_gain','reader_cost','verdict_reason']),
                'Missing editorial alternative evaluation')
        for a in row['evidence']:anchor(a,pages)
        for field,known in [('finding_ids',finds),('suggestion_ids',suggestions)]:
            require(isinstance(row.get(field),list) and set(row[field])<=set(known),
                    'Unknown editorial '+field)
        decision=row['decision']
        # A sound placement can coexist with a required content repair at that
        # location.  "keep" judges the arrangement, not whether the passage is
        # otherwise complete; related findings may remain linked for context.
        require(decision!='required_repair' or bool(row['finding_ids']),
                'Editorial repair/finding mismatch')
        require(bool(row['suggestion_ids'])==(decision=='optional_improvement'),
                'Editorial improvement/suggestion mismatch')

# Expected gains and feasible orderings are hypotheses, not planner verdicts.
READER_SCHEMA_V3 += "\nAn alternative is a proposal, not a known reasonable ordering. Check whether it preserves necessary information, dependencies and supported author meaning before preferring it. Reject an infeasible proposal without treating its failure as proof that the current order is uniquely correct. Do not create a worse order merely to validate the current passage. Unknown feasibility stays unknown; no revision quota."
