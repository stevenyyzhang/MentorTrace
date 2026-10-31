"""Versioned scope contracts. Structural checks do not certify scientific truth."""
TECH_AXES = ('symbols_operations', 'dimensions', 'conditions', 'inference', 'formula_prose')
EDITORIAL_AXES = ('selection', 'emphasis_space', 'transitions', 'standalone_readability')
WITHDRAWAL_BASES = {'source_contradiction', 'meaning_or_dependency_loss',
    'incompatible_selected_alternative', 'unsupported_attribution',
    'outside_requested_scope', 'specific_cost_outweighs_stated_goal'}
UNCERTAINTY_BASES = {'missing_source_evidence', 'unknown_author_fact',
    'unresolved_applicability', 'unresolved_compatibility'}

TECH_INSTRUCTIONS = '''SCOPED TECHNICAL REVIEW v1:
Inspect printed expressions and adjacent explanations, independently of whether the intended
argument is reasonable. Include unnumbered expressions, bounds and approximations; the object
plan is a starting point, not an exhaustive formula inventory. Add missed technical objects.
Return technical_scope:[{object_id,aspects:[{aspect,status,scope,reason,evidence:[],finding_ids:[]}]}]
for every technical object, including additions. Exactly cover aspects symbols_operations,
dimensions, conditions, inference, formula_prose. Status is pass|gap|unknown|not_checked|not_applicable.
Scope names the actual expressions/assertions tested, not the whole paragraph by implication.
Inspect original page glyphs before alleging a symbol error. Pass requires evidence and a
specific account; gap links ordinary findings; unknown/not_checked explicitly identifies the
remaining task. Valid applicability does not certify printed algebra or prose. Do not silently
repair an expression while reading it. No defect quota and no claim of exhaustive proof.
For each actual experiment, displayed result and reported statistic, follow the local chain:
input/parameter scale and reference -> processing -> displayed quantity -> calculation or
sampling basis -> claim. A general noise/model explanation does not establish every scene's
parameter values; a display normalization does not explain how a plot was generated. Resolve
applicable questions in existing checks/technical_scope, with exact scope and evidence. For
empirical results inspect fixed versus resampled quantities and relevant variability; analytical
results need their assumptions and calculation, not an invented repeated-trial experiment.
Use manuscript-grounded questions, not a fixed list of expected defects or a required comment count.
'''
READER_INSTRUCTIONS = '''EDITORIAL COVERAGE v1:
Being understandable does not establish that information selection or presentation is optimal.
In each reading_review.sections row add editorial_axes:[{aspect,status,scope,reason,evidence:[],
finding_ids:[],suggestion_ids:[]}], exactly covering selection, emphasis_space, transitions,
standalone_readability. Use status keep|change|unknown|not_checked|not_applicable. State actual
reader effects, including independent reading of abstracts/captions/conclusions where relevant.
Look for supported optional gains without demanding technical necessity or a suggestion quota.
Use the supplied task-matched published cases for editorial questions as well as missing
explanations: information selection, emphasis, sentence/paragraph roles, handoffs and standalone
summaries/captions where relevant. Relate these to the actual target through existing case_usage
and writing_transfers; do not create a second parallel case checklist. Source ordering is not
mandatory and a case need not produce a suggestion. The four axes organize target coverage;
they do not replace case-based reading or become an Advisor inventory.
Check the actual semantic relationship in literature summaries as well as their fluency:
coordinated contributions, dependency and claimed scope. If cited evidence is unavailable and
the relationship matters to the wording, preserve the specific question and sentence anchor;
a generic literature-not-verified note does not carry that question. Do not invent cited results.
'''
SELECTION_INSTRUCTIONS = '''EDITORIAL ALTERNATIVES v1:
Each editorial_selection group adds comparison:{original_excerpt,alternative,reader_effect,
preserved_requirements,decision_basis}. original_excerpt is exact manuscript text. alternative
is a concrete local wording/order plan sufficient to compare, not just "compress" or "move".
Judge gain, transition/repetition/reference costs and preservation together. "Already readable"
or "small gain" alone is not a comparison. Do not manufacture unknown author facts. A new keep
group without an incoming proposal may use alternative:null with a concrete no_candidate_reason.
Incoming proposals must be compared even when rejected. Optional benefit need not repair an error.
For each group also record purpose:"reader_comprehension|information_selection|mentor_style|other_editorial"
and benefit_status:"supported|plausible|uncertain|not_claimed". These distinguish supporting evidence
from estimated benefit. Source/manuscript support, applicable conditions, meaning preservation and
compatibility are the retention criteria. Unmeasured or uncertain comparative benefit alone is
not a withdrawal reason, including for optional organization changes beyond mentor style.
Keep a supported compatible suggestion as optional, with its conditions and uncertain benefit;
do not manufacture a defect or claim it is superior. Preserve one compatible path for genuinely
competing alternatives; do not retain contradictory rewrites simply to increase the count.
Each withdrawn organization_disposition needs withdrawal_basis from source_contradiction,
meaning_or_dependency_loss, incompatible_selected_alternative, unsupported_attribution,
outside_requested_scope, specific_cost_outweighs_stated_goal, with concrete reason and manuscript
evidence. A generic cost label is insufficient. Duplicates normally merge into the actual surviving
recommendation with their sources intact. 'Already readable', 'no demonstrated gain', 'small gain'
or 'not necessary' alone cannot support withdrawal. Unresolved dispositions need uncertainty_basis
from missing_source_evidence|unknown_author_fact|unresolved_applicability|unresolved_compatibility
and pending_fact naming what must be resolved; uncertain comparative benefit is not such a blocker.
Verify receives excluded_organization_candidates with complete original proposals and frozen Merge
dispositions. Return withdrawn_candidate_reviews:[{input_id,decision:"withdraw|restore|unresolved",
output_ids:[],reason,evidence:[],withdrawal_basis?,uncertainty_basis?,pending_fact?}] covering each
exactly once. Reassess against the manuscript, not Merge's authority. Restore links to actual
verify organization_suggestions marked new_in_stage:true, with ordinary editorial selection;
withdraw needs the same concrete grounds; unresolved names a genuine missing fact. This is in the
existing Verify call. Never change the frozen initial proposals or claim restoration is new discovery.
'''
LINEAGE_INSTRUCTIONS = '''CROSS-CATEGORY LINEAGE v1:
Content dispositions may use status incorporated with output_ids pointing only to actual
organization_suggestions. Explain the supported category change with manuscript evidence.
Keep independent technical requirements in content findings; never relabel them as optional
to bypass review. Ordinary retained/merged/narrowed targets remain findings. Withdrawn and
unresolved have no targets. A delivered rewrite is tracked through the existing delivery_map
and revision_actions, not falsely called a withdrawal. Changed categories remain audit-eligible.
Conversely, a proposal independently confirmed as a definite local language error may be
incorporated into an actual surface finding. Use an incorporated organization disposition,
explicit manuscript evidence, and an editorial selected_output_ids link to that finding.
Apply ordinary surface-error validation. Do not retain a conflicting optional duplicate,
silently drop the source, or promote uncertain style to a definite error.
'''
CLARITY_INSTRUCTIONS = '''AUTHOR CLARITY v1:
Use titles that identify a concrete manuscript problem. Each comment should let its author
locate the passage, understand the reason, and perform the requested action. Explain terms in
context; avoid internal audit shorthand. Write each language naturally, preserving all scope,
negation and uncertainty. Distinguish the clarity of review comments from the style of manuscript
replacement prose. Expression may realize a mentor-style goal without demonstrably improving
the original. Record style alignment versus an evidenced improvement as distinct adoption reasons;
do not invent a readability gain or call acceptable original wording defective. Source-supported
style transfer with preserved meaning, target fit and understandable prose is acceptable even
when comparative quality is unknown. Attribution alone does not prove superiority or mentor approval.
Keep conditions that change validity or the selected action; remove anticipatory rebuttals that
only list work not requested. Keep rejected-repair rationale in private dispositions. The comment
states the defect or missing fact; the action states the adequate repair positively. Uncertainty
about author implementation calls for a precise question, not a long defensive tail. Avoid noun
stacks and sentences carrying diagnosis, alternatives and exceptions at once. Check English and
Chinese independently for natural phrasing, then compare meaning. Optional style proposals need
no repeated disclaimer about superiority or the author's right to keep the original.
Review these properties in the existing final-text pass, not an extra
full-manuscript call. Return global_scope.author_clarity:{status:"pass|fail",reason,
issues:[{target_id,problem,required_change}]}. Inspect all delivered comments and replacement
passages, not only a sample. Any unresolved readability or meaning issue fails this check.
'''

def require(value, message):
    if not value:
        raise ValueError(message)

def disposition_basis(row, decision, pages, anchor):
    if decision=='withdraw':
        require(row.get('withdrawal_basis') in WITHDRAWAL_BASES,
                'Withdrawal needs concrete grounds; uncertain benefit alone is insufficient')
        require(isinstance(row.get('evidence'),list) and row['evidence'], 'Withdrawal needs evidence')
        for evidence in row['evidence']:anchor(evidence,pages)
    if decision=='unresolved':
        require(row.get('uncertainty_basis') in UNCERTAINTY_BASES,
                'Uncertain benefit alone cannot make a supported proposal unresolved')
        require(isinstance(row.get('pending_fact'),str) and row['pending_fact'].strip(), 'Missing actual pending fact')

def aspects(rows, expected, statuses, pages, anchor, findings, suggestions=()):
    require(isinstance(rows,list) and len(rows)==len(expected) and
            {r.get('aspect') for r in rows}==set(expected), 'Incomplete scoped aspects')
    for row in rows:
        require(row.get('status') in statuses, 'Invalid scoped status')
        require(all(isinstance(row.get(k),str) and row[k].strip() for k in ('scope','reason')), 'Missing precise scope/reason')
        require(isinstance(row.get('evidence'),list), 'Missing scope evidence')
        for e in row['evidence']: anchor(e,pages)
        fids=row.get('finding_ids',[]); sids=row.get('suggestion_ids',[])
        require(isinstance(fids,list) and set(fids)<=set(findings), 'Unknown scoped finding')
        require(isinstance(sids,list) and set(sids)<=set(suggestions), 'Unknown scoped suggestion')
        if row['status'] in ('pass','gap','keep','change'):
            require(row['evidence'], 'Checked scope needs evidence')
        if row['status']=='gap': require(fids, 'Scoped gap needs finding')
        if row['status']=='change': require(fids or sids, 'Scoped change needs delivered proposal')
        if row['status'] not in ('gap','change'):
            require(not fids and not sids, 'Non-gap scope cannot claim an issue')

def validate(stage, response, context, pages, anchor):
    if not context.get('review_quality'): return
    findings={f['id'] for f in response.get('findings',[])}
    if stage=='technical':
        objects=context['objects']+response.get('new_objects',[])
        expected={o['id'] for o in objects if 'technical' in o['lanes']}
        rows=response.get('technical_scope')
        require(isinstance(rows,list) and len(rows)==len(expected) and
                {r.get('object_id') for r in rows}==expected, 'Technical scope omits/duplicates object')
        for row in rows: aspects(row.get('aspects'),TECH_AXES,
            {'pass','gap','unknown','not_checked','not_applicable'},pages,anchor,findings)
    if stage=='reader':
        for section in response.get('reading_review',{}).get('sections',[]):
            aspects(section.get('editorial_axes'),EDITORIAL_AXES,
                {'keep','change','unknown','not_checked','not_applicable'},pages,anchor,findings,
                {s['id'] for s in response.get('organization_suggestions',[])})
    if stage in ('merge','verify'):
        for row in response.get('organization_dispositions',[]):
            disposition_basis(row, 'withdraw' if row.get('status')=='withdrawn' else row.get('status'),pages,anchor)
        for group in response.get('editorial_selection',[]):
            c=group.get('comparison',{})
            require(all(isinstance(c.get(k),str) and c[k].strip() for k in
                ('original_excerpt','reader_effect','preserved_requirements','decision_basis')), 'Incomplete editorial comparison')
            require(any(c['original_excerpt'] in text for text in pages.values()), 'Comparison excerpt absent')
            require(isinstance(c.get('alternative'),str) and c['alternative'].strip() or
                (not group.get('input_ids') and group['preferred_action']=='keep' and c.get('alternative') is None
                 and isinstance(c.get('no_candidate_reason'),str) and c['no_candidate_reason'].strip()),
                'Concrete editorial alternative required')
            require(group.get('purpose') in {'reader_comprehension','information_selection','mentor_style','other_editorial'},
                    'Editorial purpose missing')
            require(group.get('benefit_status') in {'supported','plausible','uncertain','not_claimed'},
                    'Editorial benefit status missing')
        if stage=='verify':
            candidates=context.get('excluded_organization_candidates',[])
            expected={c['suggestion']['id'] for c in candidates}
            rows=response.get('withdrawn_candidate_reviews',[])
            require(isinstance(rows,list) and len(rows)==len(expected) and
                    {r.get('input_id') for r in rows}==expected, 'Excluded proposal reconsideration incomplete')
            suggestions={s['id']:s for s in response.get('organization_suggestions',[])}
            for row in rows:
                decision=row.get('decision')
                require(decision in {'withdraw','restore','unresolved'}, 'Invalid reconsideration decision')
                require(isinstance(row.get('reason'),str) and row['reason'].strip(), 'Reconsideration needs reason')
                outputs=row.get('output_ids')
                require(isinstance(outputs,list) and len(outputs)==len(set(outputs)) and set(outputs)<=set(suggestions),
                        'Invalid reconsideration target')
                require(bool(outputs)==(decision=='restore'), 'Restoration needs actual suggestion targets')
                if decision=='restore':
                    require(all(suggestions[i].get('new_in_stage') is True for i in outputs), 'Restored proposal must identify Verify addition')
                    require(isinstance(row.get('evidence'),list) and row['evidence'], 'Restoration needs evidence')
                    for e in row['evidence']:anchor(e,pages)
                disposition_basis(row,decision,pages,anchor)

def validate_clarity(value):
    require(isinstance(value,dict) and value.get('status')=='pass' and
            isinstance(value.get('reason'),str) and value['reason'].strip() and value.get('issues')==[],
            'Author clarity review missing or failed')
