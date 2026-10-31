"""Manuscript-derived obligations and scope closure. No inferred scientific verdicts."""
import copy

PLAN = '''COVERAGE BASIS v1: In this existing planning call return coverage_basis:[
{id,lane:"reader|technical",question,trigger,anchors:[],object_ids:[],relation:boolean}].
Derive independently answerable obligations from actual claims, methodological steps,
reported results/comparisons, citation attributions and paragraph dependencies. Reuse
object IDs; do not repeat their descriptions. Group only questions with the same answer
and conditions. Cross-object relations name both actual endpoints in anchors/object_ids;
do not generate all pairs or a paragraph-by-dimension matrix. A defensible intended
interpretation does not answer whether the printed claim or attribution is supported.
Return coverage_exclusions:[{page,reason}] only for pages with no applicable obligation.
This is a manuscript-derived basis, not a known-defect list or a completeness certificate.
'''
REVIEW = '''COVERAGE ANSWERS v1: For each supplied coverage_basis item for your lane,
return coverage_answers:[{basis_id,check_ids:[],status:"answered|partial|unknown|not_applicable|unfinished",
remaining_question,reason}]. Link actual checks rather than repeat evidence or prose.
Answered means the WHOLE stated question within its conditions was checked; a sufficient
subcase cannot close the whole question. Partial/unknown/unfinished names the exact
remaining question. Unknowns remain questions, not invented defects. Check citation
attribution separately from a plausible mathematical or editorial interpretation.
Add manuscript-grounded missed obligations as new_coverage_basis in the same schema
and answer them. No new call or defect quota; Advisor uses its own independent inventory.
'''
AUDIT = '''COVERAGE AUDIT v1 (Reader/Expert stage_scope only): FIRST inspect the manuscript
for relevant claims and relationships not represented by the basis; THEN compare each
basis question with actual checks/coverage_answers. Return coverage_audit:[{basis_id,
status:"adequate|narrowed|unattempted|unknown",reason,issue_id?}]. Non-adequate rows link
issues:[{id,question,anchors:[],reason}]. New omissions outside the basis are issues too.
A registered ID or a model's answered label is not proof of semantic coverage. Do not
recheck every successful calculation: inspect scope/evidence sufficiency and cross-object
endpoints. Missing review is an execution issue, not automatically an author error.
'''
VERIFY = '''Resolve each supplied coverage_execution_issue once in execution_resolutions:
[{issue_id,status:"resolved|author_confirmation|not_applicable",reason,evidence:[],output_ids:[]}].
Inspect the original question and evidence; retain meaningful author unknowns explicitly.
Resolved/not_applicable require evidence. Author_confirmation links an actual finding
with request_type author_confirmation or a candidate author_confirmation output. Do not
repeat initial review of unaffected objects. These follow-ups are not independent discovery.
'''


def require(ok, message):
    if not ok:
        raise ValueError(message)


def validate_basis(rows, objects, pages, anchor):
    require(isinstance(rows, list), 'Coverage basis must be a list')
    ids = [r.get('id') for r in rows]
    require(all(isinstance(i, str) and i for i in ids) and len(ids) == len(set(ids)), 'Duplicate/invalid coverage ID')
    known = {o['id'] for o in objects}
    for row in rows:
        require(row.get('lane') in {'reader', 'technical'}, 'Invalid coverage lane')
        require(all(isinstance(row.get(k), str) and row[k].strip() for k in ['question', 'trigger']), 'Coverage question/trigger missing')
        require(row.get('object_ids') and set(row['object_ids']) <= known, 'Coverage object absent')
        require(type(row.get('relation')) is bool and row.get('anchors'), 'Coverage endpoints missing')
        require(not row['relation'] or len(row['anchors']) >= 2, 'Relation needs both anchored endpoints')
        for a in row['anchors']:
            anchor(a, pages)


def validate(stage, response, context, pages, anchor):
    if not context.get('coverage_basis_v1'):
        return
    if stage == 'objects':
        rows = response.get('coverage_basis')
        validate_basis(rows, response['objects'], pages, anchor)
        covered = {a['page'] for r in rows for a in r['anchors']}
        excluded = response.get('coverage_exclusions', [])
        require(all(r.get('page') in pages and r.get('reason') for r in excluded), 'Invalid coverage exclusion')
        require(len(excluded) == len({r['page'] for r in excluded}) and not covered & {r['page'] for r in excluded}, 'Duplicate/contradictory page accounting')
        require(covered | {r['page'] for r in excluded} == set(pages), 'Coverage basis silently omits a page')
    if stage in {'reader', 'technical'}:
        added = response.get('new_coverage_basis', [])
        validate_basis(added, context['objects'] + response.get('new_objects', []), pages, anchor)
        require(all(r['lane'] == stage for r in added), 'Cross-lane coverage addition')
        basis = context['coverage_basis'] + added
        require(len(basis) == len({r['id'] for r in basis}), 'Coverage addition duplicates ID')
        expected = {r['id'] for r in basis if r['lane'] == stage}
        answers = response.get('coverage_answers', [])
        require(len(answers) == len(expected) and {r.get('basis_id') for r in answers} == expected, 'Coverage answer missing/duplicate')
        checks = {c['id']: c for c in response.get('checks', [])}
        for row in answers:
            status = row.get('status')
            require(status in {'answered', 'partial', 'unknown', 'not_applicable', 'unfinished'} and row.get('reason'), 'Invalid scope closure')
            require(isinstance(row.get('check_ids'), list) and set(row['check_ids']) <= set(checks), 'Unknown coverage check')
            require(status == 'unfinished' or row['check_ids'], 'Scope closure needs actual check')
            remaining = row.get('remaining_question')
            require(isinstance(remaining, str), 'Explicit remaining question required')
            require(bool(remaining.strip()) == (status in {'partial', 'unknown', 'unfinished'}), 'Whole-question pass conceals remaining scope')
            if status == 'answered':
                require(all(checks[c].get('judgment') != 'unknown' and checks[c].get('execution') != 'unfinished' for c in row['check_ids']), 'Unknown check cannot close whole question')
    if stage == 'verify':
        issues = context.get('coverage_execution_issues', [])
        rows = response.get('execution_resolutions', [])
        require(len(rows) == len(issues) and {r.get('issue_id') for r in rows} == {i['id'] for i in issues}, 'Execution issues not closed')
        targets = {f['id'] for key in ['findings', 'organization_suggestions'] for f in response.get(key, [])}
        confirmations = {f['id'] for f in response.get('findings', []) if f.get('request_type') == 'author_confirmation'}
        confirmations |= {c['candidate_id'] for c in response.get('candidate_reviews', []) if c['status'] == 'author_confirmation'}
        for row in rows:
            require(row.get('status') in {'resolved', 'author_confirmation', 'not_applicable'} and row.get('reason'), 'Invalid execution resolution')
            require(isinstance(row.get('output_ids'), list) and set(row['output_ids']) <= targets | confirmations, 'Unknown execution output')
            if row['status'] == 'author_confirmation':
                require(set(row['output_ids']) & confirmations, 'Execution unknown has no explicit author question')
            else:
                require(row.get('evidence'), 'Resolved execution issue needs evidence')
            for e in row.get('evidence', []):
                anchor(e, pages)


def validate_audit(value, scope, pages, anchor):
    if scope['stage'] not in {'reader', 'technical'}:
        return
    basis = scope['assigned_plan'].get('coverage_basis', []) + scope['actual_initial_records'].get('new_coverage_basis', [])
    expected = {r['id'] for r in basis if r['lane'] == scope['stage']}
    rows = value.get('coverage_audit', [])
    require(len(rows) == len(expected) and {r.get('basis_id') for r in rows} == expected, 'Source audit omits coverage basis')
    issues = value.get('issues', [])
    ids = [r.get('id') for r in issues]
    require(len(ids) == len(set(ids)) and all(isinstance(i, str) and i for i in ids), 'Scope issues need stable IDs')
    for r in issues:
        require(r.get('question') and r.get('reason') and r.get('anchors'), 'Execution issue lacks concrete question/evidence location')
        for a in r['anchors']:
            anchor(a, pages)
    for r in rows:
        require(r.get('status') in {'adequate', 'narrowed', 'unattempted', 'unknown'} and r.get('reason'), 'Invalid coverage audit')
        require(r['status'] == 'adequate' or r.get('issue_id') in ids, 'Scope shortfall lacks issue route')


def execution_issues(source_review):
    """Namespace actual source-auditor issues; never create judgments from statuses."""
    return [{**copy.deepcopy(i), 'id': r['stage'] + ':' + i['id'], 'origin_id': i['id'], 'origin_stage': r['stage']}
            for r in source_review['stage_scope_reviews'] if r['stage'] in {'reader', 'technical'}
            for i in r.get('issues', [])]
