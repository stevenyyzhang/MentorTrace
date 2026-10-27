"""Versioned limited-depth Expression assessment; never infer omitted judgments."""

INSTRUCTIONS = '''BRIEF EXPRESSION ASSESSMENT v1 overrides verbose non-action Expression accounting.
Keep full Concern review. Consider every supplied Expression and active use against
the full paper, prioritizing clear useful improvements over exhaustive stylistic
alternatives. This limited-depth review does not certify every possible application.
Do not select a correct example merely to discharge a source; carry observed errors
into findings. For mentor_expression keep/not_applicable/unknown/unfinished, return
a brief writing_transfer: {id,source_id,assessment:"brief",decision,reason,target_anchors:[]}.
Reason is normally one short sentence comparing the operation/conditions with this
manuscript. KEEP needs an actual anchor; nonmatch needs an operation-based reason.
Mark uncertainty/unexamined scope unknown/unfinished. Never infer a verdict from
silence. Omit excerpts, six explanatory fields and duplicate formal checks for these
brief records. Only empty output lists and no-change/unresolved metadata are added
by the program. Retain explicit source_use_dispositions for every use; reason_ref
may reference a brief record only when its reason actually answers that use.
Checked means assessed at this declared limited depth, not an exhaustive audit.
Repairs/improvements still require COMPLETE ordinary transfers, source features,
checks and findings/suggestions with target evidence. No finding quota, truncated
sources, lower capacity reserves or model/effort changes. Keep explanations concise.'''

def validate(row, context, anchor=None, pages=None):
    if 'assessment' not in row:
        return False
    def require(ok, message):
        if not ok: raise ValueError(message)
    require(context.get('advisor_expression_brief') == 1 and context.get('advisor_direct_fulltext'),
            'Brief Expression assessment not enabled in frozen protocol')
    require(row['assessment'] == 'brief' and row.get('source_kind') == 'mentor_expression',
            'Brief assessment is only for Expression')
    require(row.get('source_id') in {r['id'] for r in context.get('expression_sources', {}).get('records', [])},
            'Brief assessment cites unsupplied Expression')
    require(row.get('decision') in {'keep','not_applicable','unknown','unfinished'},
            'Actionable Expression requires complete evidence')
    require(isinstance(row.get('reason'), str) and bool(row['reason'].strip()), 'Brief assessment needs explicit reason')
    require(isinstance(row.get('target_anchors'), list), 'Brief assessment needs anchor list')
    require(context.get('advisor_shared_results') or row['decision'] != 'keep' or bool(row['target_anchors']), 'Brief KEEP needs target evidence')
    for key in ('check_ids','finding_ids','suggestion_ids'):
        require(row.get(key) == [], 'Brief non-action record cannot claim checks or outputs')
    role = 'unresolved' if row['decision'] in {'unknown','unfinished'} else 'no_change'
    require(row.get('expression_contribution') == {'role':role,'feature_ids':[],'supporting_concern_ids':[]},
            'Brief non-action contribution must not claim adoption')
    if anchor:
        for item in row['target_anchors']: anchor(item, pages)
    return True

def expand_metadata(row, context):
    if row.get('assessment') != 'brief': return
    if context.get('advisor_expression_brief') != 1:
        raise ValueError('Brief Expression assessment not enabled in frozen protocol')
    for key in ('check_ids','finding_ids','suggestion_ids'): row.setdefault(key, [])
    role = 'unresolved' if row.get('decision') in {'unknown','unfinished'} else 'no_change'
    row.setdefault('expression_contribution', {'role':role,'feature_ids':[],'supporting_concern_ids':[]})
