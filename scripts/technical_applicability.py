"""Versioned accounting for actual manuscript configurations, not proof of validity."""

PLAN_SCHEMA = '''TECHNICAL APPLICABILITY v1: Also return technical_configurations:[{id,object_ids:[],anchors:[],configuration,operation,question}] and technical_configuration_exclusions:[{object_id,reason}]. Inventory actual method, baseline, ablation and experiment settings that must be checked against formula/algorithm prerequisites. Include actual singleton/zero/limiting settings, dimensions, normalization, information/noise assumptions and order of statistical operations when relevant; do not manufacture extreme cases absent from the manuscript's claims. Name the setting and operation at their respective source anchors, with a neutral applicability question, not a verdict. Every Technical object must belong to a configuration or have a specific exclusion explaining why this applicability pass is not relevant (the ordinary Technical check still runs). One configuration can cover several objects; no Cartesian product or defect quota.'''

REVIEW_SCHEMA = '''TECHNICAL APPLICABILITY v1: Also return configuration_review:{additional_configurations:[],items:[{configuration_id,case_values,required_condition,evaluation,evidence:[],outcome:"sufficient|gap|unknown|not_applicable|unfinished",check_ids:[],finding_ids:[]}],limits:[]}. Account for every planned and additional configuration exactly once. Additional configurations use the plan schema and may link new Technical objects; add any missed actual settings without changing frozen case routes. State the actual parameter values/assumptions, the operation's required condition, and a short substitution/calculation or evidence-based explanation. Merely repeating the formula or saying a baseline is named does not test applicability. Separate a formula that is undefined under the stated setting from an unknown implementation that may use a special convention. Missing implementation facts cannot be filled by assumption. Link to ordinary checks/findings; gap requires a finding; unknown/unfinished records the precise limit. Sufficiency applies only to the tested setting. Concise public evidence accounts only, no hidden reasoning. Preserve the condition and required action in the finding's gap/closure_goal.'''


def require(value, message):
    if not value:
        raise ValueError(message)


def unique(rows, key, label):
    require(isinstance(rows, list), 'Missing ' + label)
    values = [r.get(key) for r in rows]
    require(all(isinstance(v, str) and v.strip() for v in values)
            and len(values) == len(set(values)), 'Duplicate/invalid ' + label)
    return set(values)


def configurations(rows, objects, pages, anchor):
    names = unique(rows, 'id', 'technical configurations')
    covered = set()
    allowed = {o['id'] for o in objects if 'technical' in o['lanes']}
    for row in rows:
        require(not any(k in row for k in ('judgment', 'outcome', 'gap', 'repair')),
                'Configuration plan must not pre-judge')
        require(row.get('object_ids') and set(row['object_ids']) <= allowed,
                'Configuration references non-Technical object')
        require(row.get('anchors'), 'Configuration needs setting/operation anchors')
        for a in row['anchors']:
            anchor(a, pages)
        for field in ('configuration', 'operation', 'question'):
            require(isinstance(row.get(field), str) and row[field].strip(),
                    'Missing configuration ' + field)
        covered.update(row['object_ids'])
    return names, covered


def validate_plan(x, pages, anchor):
    _, covered = configurations(x.get('technical_configurations'), x['objects'], pages, anchor)
    exclusions = x.get('technical_configuration_exclusions')
    excluded = unique(exclusions, 'object_id', 'technical configuration exclusions')
    allowed = {o['id'] for o in x['objects'] if 'technical' in o['lanes']}
    require(excluded <= allowed and not excluded & covered,
            'Configuration exclusions conflict with coverage')
    require(covered | excluded == allowed, 'Technical applicability inventory omits object')
    require(all(isinstance(r.get('reason'), str) and r['reason'].strip() for r in exclusions),
            'Configuration exclusion needs a reason')


def validate_review(x, context, pages, anchor):
    review = x.get('configuration_review')
    require(isinstance(review, dict), 'Missing Technical configuration review')
    planned = context['technical_configurations']
    additions = review.get('additional_configurations')
    names, _ = configurations(additions, context['objects'] + x.get('new_objects', []), pages, anchor)
    require(not names & {r['id'] for r in planned}, 'Configuration rewrites frozen plan')
    require(all(n.startswith('technical:') for n in names), 'New configuration namespace')
    configs = {r['id']: r for r in planned + additions}
    rows = review.get('items')
    require(unique(rows, 'configuration_id', 'configuration review items') == set(configs),
            'Configuration review coverage mismatch')
    require(isinstance(review.get('limits'), list), 'Missing configuration review limits')
    checks = {c['id']: c for c in x['checks']}
    findings = {f['id']: f for f in x['findings']}
    for row in rows:
        for field in ('case_values', 'required_condition', 'evaluation'):
            require(isinstance(row.get(field), str) and row[field].strip(),
                    'Missing configuration ' + field)
        require(isinstance(row.get('evidence'), list), 'Missing configuration evidence')
        for a in row['evidence']:
            anchor(a, pages)
        cids = row.get('check_ids')
        fids = row.get('finding_ids')
        require(isinstance(cids, list) and cids and set(cids) <= set(checks),
                'Configuration has no valid check links')
        require(isinstance(fids, list) and set(fids) <= set(findings),
                'Invalid configuration finding links')
        # A check can legitimately connect the planned setting to an additional
        # dependency, such as noise normalization used by an SNR calculation.
        # All IDs are already validated against this Technical response above.
        outcome = row.get('outcome')
        require(outcome in {'sufficient', 'gap', 'unknown', 'not_applicable', 'unfinished'},
                'Invalid configuration outcome')
        if outcome == 'gap':
            linked = {f for c in cids for f in checks[c]['finding_ids']}
            require(bool(fids) and set(fids) <= linked, 'Configuration gap lost its finding')
        else:
            require(not fids, 'Non-gap configuration asserts a finding')
        if outcome in {'sufficient', 'not_applicable'}:
            require(all(checks[c]['execution'] == 'completed' and checks[c]['judgment'] == outcome for c in cids),
                    'Configuration outcome contradicts checks')
            if outcome == 'sufficient':
                require(row['evidence'], 'Configuration sufficiency needs evidence')
        if outcome == 'unknown':
            require(any(checks[c]['judgment'] == 'unknown' for c in cids),
                    'Unknown configuration lacks an unknown check')
        if outcome == 'unfinished':
            require(any(checks[c]['execution'] == 'unfinished' for c in cids),
                    'Unfinished configuration lacks an unfinished check')
