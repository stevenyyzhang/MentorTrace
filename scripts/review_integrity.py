"""Explicit subquestions, withdrawal observations and conditional-claim accounting.

These validators enforce records and source bindings, never decide scientific truth.
"""
import copy
import hashlib
import json
import re

TECH_INSTRUCTIONS = '''TECHNICAL SUBQUESTIONS v1:
For each actual technical_configuration add dimensions:[{id,question,condition,anchors:[]}].
Select independently answerable questions triggered by the actual setting, not a fixed defect
list or a Cartesian product. Inspect parameter dependence as well as formula existence at
singleton/zero settings, exact special axes as well as neighborhoods, exact versus estimated
inputs, covariance versus randomness, function domains, and analytical evaluation/crossing
accuracy separately from empirical sampling precision when relevant. No added experiment,
decoder or tracker is implied. Expert returns configuration_review.items[].dimension_reviews:
[{dimension_id,status:"sufficient|gap|unknown|not_applicable|unfinished",reason,evidence:[],
check_ids:[],finding_ids:[]}]. Every declared question is explicit; sufficient on one does not
answer another. Gap links an actual ordinary finding preserving the condition/action.
Additional configurations carry their own dimensions. This is in the existing Expert call.
'''
WITHDRAWAL_INSTRUCTIONS = '''WITHDRAWAL OBSERVATIONS v1:
For every organization proposal that THIS Verify newly withdraws, add withdrawal_observations:
[{input_id,observed_feature,anchor,observation,evidence:[],geometry?}]. Account for retained-at-Merge
proposals too, not only already-excluded candidates. An alleged existing paragraph/indent/float
needs the actual local page observation; indentation/paragraph_boundary withdrawals require
geometry.line_ref and column_ref from frozen source_layout_facts. If those facts are unavailable
do not claim a definite existing paragraph. If supplying geometry use numeric line_x,column_x,
indent_tolerance and claimed_indented. Programs compare these values; do not invent coordinates.
Uncertain layout cannot support a definite source_contradiction. Preserve an applicable optional
proposal or state the actual uncertainty; unmeasured style benefit is not a missing author fact.
'''
CLAIM_INSTRUCTIONS = '''CONDITION-PRESERVING DRAFT v1:
For each frozen source_requirement_resolution with required/optional/unknown assessment,
return requirement_delivery:[{component_id,status:"delivered|author_confirmation|optional",
report_quotes:[],condition_check:{status:"preserved|not_applicable|unknown",reason}}].
Use exact report excerpts; include each condition, independent branch, normalization and
occurrence, not a topic match. Unknown stays a concrete author question. This accounting does
not prove semantic equivalence; the independent delivery review still checks every component.
Keep Original/source_quote/source_excerpt immutable. New summaries retain theorem assumptions,
power versus amplitude references, dimensional constants and scope. Report section codes are
exactly content|organization|language, not full heading strings. Return stable draft fragments
as report_fragments:[{section,group_id,text,verified_ids:[],candidate_ids:[]}], each an entire
coordinated group. Only part 1 supplies report_preamble; assemble fragments by section without
duplicating prose. Shared replacements have one owning group; other groups give actions/links.
'''


def require(ok, message):
    if not ok: raise ValueError(message)


def validate_dimensions(configurations, review=None, pages=None, anchor=None):
    expected = {}
    for config in configurations:
        dimensions = config.get('dimensions')
        require(isinstance(dimensions, list) and dimensions, 'Actual configuration needs explicit subquestions')
        ids = [r.get('id') for r in dimensions]
        require(len(set(ids)) == len(ids) and all(isinstance(i,str) and i for i in ids), 'Duplicate/invalid dimension')
        expected[config['id']] = set(ids)
        for row in dimensions:
            require(all(isinstance(row.get(k),str) and row[k].strip() for k in ['question','condition']), 'Subquestion scope/condition missing')
            require(row.get('anchors'), 'Subquestion needs actual source anchors')
            if anchor:
                for a in row['anchors']: anchor(a, pages)
    if review is None: return expected
    for item in review:
        rows = item.get('dimension_reviews', []); ids = [r.get('dimension_id') for r in rows]
        require(len(ids)==len(set(ids)) and set(ids)==expected[item['configuration_id']], 'Technical subquestion accounting mismatch')
        for row in rows:
            require(row.get('status') in {'sufficient','gap','unknown','not_applicable','unfinished'} and row.get('reason'), 'Missing subquestion judgment')
            require(isinstance(row.get('check_ids'),list) and row['check_ids'] and set(row['check_ids'])<=set(item['check_ids']), 'Subquestion lost actual check links')
            require(isinstance(row.get('finding_ids'),list) and set(row['finding_ids'])<=set(item['finding_ids']), 'Subquestion finding outside actual configuration')
            require(row['status']!='gap' or row['finding_ids'], 'Subquestion gap lost its reportable requirement')
            require(row['status']!='sufficient' or row.get('evidence'), 'Subquestion sufficient needs evidence')
            if anchor:
                for a in row.get('evidence',[]): anchor(a, pages)
        require(item.get('outcome')!='sufficient' or all(r['status']=='sufficient' for r in rows), 'Aggregate sufficient conceals unfinished subquestion')
    return expected


def validate_withdrawals(response, pages, anchor, context=None):
    withdrawn = {r['input_id'] for r in response.get('organization_dispositions',[]) if r['status']=='withdrawn'}
    rows = response.get('withdrawal_observations',[])
    require(len(rows)==len(withdrawn) and {r.get('input_id') for r in rows}==withdrawn, 'Every Verify withdrawal needs its own actual observation')
    for row in rows:
        require(all(row.get(k) for k in ['observed_feature','observation','evidence','anchor']), 'Withdrawal observation incomplete')
        anchor(row['anchor'],pages)
        for e in row['evidence']: anchor(e,pages)
        g = row.get('geometry')
        if row['observed_feature'] in {'indentation','paragraph_boundary'} and context is not None:
            require(g and context.get('source_layout_facts'),'Definitive paragraph withdrawal needs frozen layout evidence')
            require(g.get('line_ref') and g.get('column_ref'),'Layout withdrawal needs actual line/column references')
            import layout_evidence
            g=layout_evidence.indentation(g,context['source_layout_facts'])
        if g:
            require(all(isinstance(g.get(k),(int,float)) and not isinstance(g[k],bool) for k in ['line_x','column_x','indent_tolerance']), 'Withdrawal geometry must be numeric')
            require(g['indent_tolerance']>=0 and isinstance(g.get('claimed_indented'),bool), 'Invalid geometry claim')
            require(g['claimed_indented']==(g['line_x']-g['column_x']>g['indent_tolerance']), 'Withdrawal indentation contradicts supplied geometry')


def draft_requirements(final, response):
    expected = {r['component_id']:r for r in final.get('source_requirement_resolutions',[]) if r['assessment'] in {'required','optional','unknown'}}
    rows = response.get('requirement_delivery',[])
    require(len(rows)==len(expected) and {r.get('component_id') for r in rows}==set(expected), 'Draft requirement/condition coverage mismatch')
    for row in rows:
        source=expected[row['component_id']];check=row.get('condition_check',{})
        require(row.get('status') in {'delivered','author_confirmation','optional'}, 'Invalid requirement delivery')
        require(source['assessment']!='unknown' or row['status']=='author_confirmation', 'Unknown obligation became resolved')
        require(source['assessment']!='required' or row['status']=='delivered', 'Required obligation downgraded')
        require(check.get('status') in {'preserved','not_applicable','unknown'} and check.get('reason'), 'Missing explicit condition check')
        require(row.get('report_quotes') and all(isinstance(q,str) and q in response['report_markdown'] for q in row['report_quotes']), 'Requirement delivery needs actual report excerpts')


def normalize_section(value):
    aliases={'content and technical comments':'content','organization and flow comments':'organization','language and presentation comments':'language'}
    return aliases.get(value.lower(),value) if isinstance(value,str) else value


def safe_patch(response, edits):
    """Apply field/path scoped edits, preserving all source fields and Original spans."""
    require(not response.get('canonical_draft'), 'Use canonical_draft.replace_groups for an atomic authored-group update')
    result=copy.deepcopy(response);before=response['report_markdown']
    originals=lambda text:[text[m.end():n.start() if n else len(text)] for m,n in _original_ranges(text)]
    for edit in edits:
        path=edit['path'];require(path and not any(str(p) in {'source_quote','source_excerpt','original_references','source_ref','source_sha256'} for p in path), 'Source quotation field is immutable')
        current=result
        for key in path[:-1]:current=current[key]
        key=path[-1];text=current[key]
        require(isinstance(text,str) and hashlib.sha256(text.encode()).hexdigest()==edit['old_sha256'], 'Patch target changed')
        require(edit['old'] and text.count(edit['old'])==edit['expected_count'], 'Patch occurrence mismatch')
        current[key]=text.replace(edit['old'],edit['new'])
    require(originals(before)==originals(result['report_markdown']), 'Patch changed an Original field')
    require(not re.search(r'\\mathcal\s+\\mathcal',result['report_markdown']), 'Patch introduced duplicate calligraphic macro')
    return result


def _original_ranges(text):
    starts=list(re.finditer(r'^\*\*Original:\*\*[ \t]*',text,re.M))
    boundary=re.compile(r'^(?:#{1,6}\s|\*\*[^\n*]+[:：]\*\*|---\s*$)',re.M)
    return [(s,boundary.search(text,s.end())) for s in starts]


def assemble_fragments(parts, partial=False):
    preambles=[p['report_preamble'] for p in parts if p.get('report_preamble')]
    require(len(preambles)==1 or (partial and not preambles),'Exactly one report preamble required')
    fragments=[f for p in parts for f in p.get('report_fragments',[])];seen=set();groups=[]
    for f in fragments:
        require(f.get('section') in {'content','organization','language'} and f.get('group_id') and f.get('text'),'Invalid report fragment')
        require(not re.search(r'^## ',f['text'],re.M),'Section headings belong to assembly, not report fragments')
        require(f['group_id'] not in seen,'Duplicate coordinated report group');seen.add(f['group_id']);groups.append(f)
    require(groups,'Missing structured report fragments')
    headings={'content':'Content and technical comments / 内容与技术意见','organization':'Organization and flow comments / 篇章与行文意见','language':'Language and presentation comments / 语言与格式意见'}
    text=[preambles[0]] if preambles else []
    for section in headings:
        selected=[g['text'] for g in groups if g['section']==section]
        if selected:text+=['## '+headings[section],*selected]
    return '\n\n'.join(text),groups
