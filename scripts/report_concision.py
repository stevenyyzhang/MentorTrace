"""Mechanical placeholder candidates plus an explicit model economy judgment."""
import re


DRAFT_INSTRUCTIONS='''CONCISE REPORT CONTRACT:
Keep every supported independent requirement, condition, uncertainty and exact edit location.
Comment explains the problem and consequence once; Suggested revision gives the concrete action.
Lead with the specific problem or missing fact. Use concrete verbs and explicit subjects; split
sentences that mix diagnosis, repair options and scope. Do not repeat the entire derivation in
the comment when only its decisive step is needed. Do not add unsupported claims of harm.
Keep decision-changing conditions, such as "if this is an empirical average". Remove anticipatory
rebuttals about algorithms, experiments or work that the comment does not request. Keep rationale
for rejecting excessive repairs in the private disposition. State the selected adequate action
positively. A generic "not necessarily", "does not require" or "the author may decide" tail is
not a substitute for defining that action. Do not ban negation: retain it when it states the
actual defect, mathematical scope, a live author choice or a necessary use condition.
Original contains manuscript text only, not a summary or connecting narration such as
"the paragraph subsequently prints". Put locations in Location and interpretation in Comment.
Use separate exact source excerpts for noncontiguous passages. Preserve the source's wording,
errors and inline/display math roles; checked LaTeX transcription and line-wrap repair are
allowed, silent correction or paraphrase is not. Do not copy an earlier report as source evidence.
Do not repeat the diagnosis in actions, shared plans and draft instructions. Preserve a local
condition wherever the draft would otherwise be unsafe or unclear. Shared plans carry common
actions once. Print a complete selected replacement once; do not repeat overlapping local drafts.
Keep both languages and the required identical English corrections in both language tracks.
Simple grammar comments need an exact correction and a brief reason, not a grammar lesson.
If necessary facts are absent, request the exact facts and insertion point in revision actions;
do not fabricate them or write a paragraph filled with [METHOD], [DATA], [VALUE] or similar holes.
Still provide complete, usable wording where evidence supports it, with concrete use conditions.
Preserve technical derivations and material distinctions even if they need more space. No target
page/comment count; do not silently discard small errors or reduce a substantive repair to a slogan.
'''

# A separately pinned extension keeps already frozen report-concision v1 requests valid.
SOURCE_QUOTE_INSTRUCTIONS = '''EXACT ORIGINAL FIELDS v1:
The supplied original_fields inventory locates complete Original fields by text_span offsets
in report_text, including continuation paragraphs and formulas. Only when assigned global_scope,
in global_scope.report_economy also return original_results:
[{original_id,status:"verbatim|not_verbatim|unresolved",reason,evidence:[]}]. Account for each
exactly once. Compare the WHOLE field with the actual manuscript, not just the words inside
quotation marks. Reviewer introductions, summaries, source tags and invented connecting prose
inside this field fail. Location belongs outside Original. Multiple exact excerpts may be
separated by paragraph breaks without invented connecting language. Outer quotation marks,
line-wrap repair and faithful math typesetting are allowed; changed claims, repaired source
errors and stitched fragments presented as one source sentence are not. Inspect decisive math
glyphs on the page. Use ordinary manuscript evidence; for image transcriptions return an actual
evidence_record bound to the inspected source_pages. A checked transcript supports reproduction,
not the scientific truth of the quoted sentence. Unresolved or not_verbatim blocks delivery;
correct only affected fields and dependent judgments. This check shares the existing delivery
call. The local validator checks complete records and evidence bindings, not visual truth.
'''


def original_fields(report):
    """Inventory literal Original fields, retaining continuation prose and display math."""
    starts = list(re.finditer(r'^\*\*Original:\*\*[ \t]*', report, re.M))
    boundary = re.compile(r'^(?:#{1,6}\s|\*\*[^\n*]+[:：]\*\*|---\s*$)', re.M)
    result = []
    for start in starts:
        end = boundary.search(report, start.end())
        stop = end.start() if end else len(report)
        result.append({'id': f'O{len(result)+1}', 'text_span': [start.end(), stop]})
    return result


def validate_originals(review, items, evidence_validator, allowed_paths):
    rows = review.get('original_results') if isinstance(review, dict) else None
    if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
        raise ValueError('Original fields need explicit individual source comparisons')
    if len(rows) != len(items) or {r.get('original_id') for r in rows} != {i['id'] for i in items}:
        raise ValueError('Original field source comparisons are missing or duplicated')
    for row in rows:
        if row.get('status') != 'verbatim' or not isinstance(row.get('reason'), str) or not row['reason'].strip():
            raise ValueError('Original field is paraphrased, unresolved or unchecked')
        evidence_validator(row.get('evidence'), 'Original needs actual manuscript evidence', factual=True)
        if any(e.get('path') not in allowed_paths or e.get('basis') != 'manuscript' for e in row['evidence']):
            raise ValueError('Original must use bound manuscript text or page transcription')
INSTRUCTIONS=DRAFT_INSTRUCTIONS+'''In the existing global_scope result return report_economy:{status:"pass|fail",reason,
placeholder_results:[{candidate_id,decision:"literal_notation|author_placeholder",reason,evidence:[]}]}.
Exactly cover supplied placeholder candidates. Their detection is mechanical, not a finding:
literal scientific notation needs actual manuscript evidence containing that token. An unresolved
author placeholder in delivered replacement prose fails this gate. Independently inspect other
placeholder forms and redundant prose; the candidate list does not exhaust them. Record concrete
remaining problems in global_scope.issues; do not approve them merely to shorten the workflow.
'''
PATTERN=re.compile(r'\[(?:METHOD|DATA|VALUE|PARAMETERS?|FILL IN[^\]\n]*|TODO[^\]\n]*|待补充[^\]\n]*|填写[^\]\n]*)\]|\{\{(?:METHOD|DATA|VALUE|PARAMETERS?)\}\}',re.I)


def candidates(response,target_units=None):
    result=[]
    documents=[{'draft_label':u['context_id'],'id':u['id'],'text':u['text']}
               for u in (target_units or []) if u['kind']=='suggested_wording']
    if not documents:
        documents=[{**p,'draft_label':g['draft_label']} for g in response.get('language_realizations',[]) for p in g.get('passages',[])]
    for passage in documents:
        for match in PATTERN.finditer(passage['text']):
            result.append({'id':f'P{len(result)+1}','draft_label':passage['draft_label'],
                'passage_id':passage['id'],'token':match.group(),
                'context':passage['text'][max(0,match.start()-90):match.end()+90]})
    return result


def validate(review,items,evidence_validator,allowed_paths=None):
    if not isinstance(review,dict) or review.get('status')!='pass' or not isinstance(review.get('reason'),str) or not review['reason'].strip():
        raise ValueError('Explicit report concision/placeholder review remains incomplete or failed')
    rows=review.get('placeholder_results',[])
    if not isinstance(rows,list) or len(rows)!=len(items) or {r.get('candidate_id') for r in rows}!={p['id'] for p in items}:
        raise ValueError('Placeholder candidates need explicit individual dispositions')
    by_id={p['id']:p for p in items}
    for row in rows:
        if row.get('decision')!='literal_notation' or not row.get('reason'):
            raise ValueError('Unresolved author placeholder in delivered replacement prose')
        evidence_validator(row.get('evidence'),'Literal notation needs actual manuscript evidence',factual=True)
        if allowed_paths is not None and any(e['path'] not in allowed_paths for e in row['evidence']):
            raise ValueError('Literal notation must use actual manuscript text/image evidence')
        if not any(e.get('basis')=='manuscript' and by_id[row['candidate_id']]['token'] in e['quote'] for e in row['evidence']):
            raise ValueError('Literal-notation evidence does not contain the candidate token')


META_PATTERN=re.compile(r'\b(?:present|current|this) rewrite\b|(?:cannot|prevent\w*|no)\b[^.\n]{0,120}\b(?:draft(?:ed|ing)?|setup rewrite)\b|does not (?:necessarily )?require[^.\n]{0,80}(?:new|additional) (?:experiment|algorithm)|当前改写|尚不能完整改写|此处不提供|未代写|没有起草|不需要新增.{0,12}(?:实验|算法)',re.I)


def meta_candidates(target_units):
    """Heuristic candidates, never automatic deletion or a semantic verdict."""
    rows=[]
    for unit in target_units:
        if unit['kind']!='block' or unit['text'].startswith(('**Original:**','**Location:**')):continue
        for match in META_PATTERN.finditer(unit['text']):
            rows.append({'id':'M'+str(len(rows)+1),'target_id':unit['id'],'token':match.group(),
                'span':[match.start(),match.end()],'text':unit['text']})
    return rows


def validate_meta(review,candidates):
    rows=review.get('meta_results',[])
    if len(rows)!=len(candidates) or {r.get('candidate_id') for r in rows}!={c['id'] for c in candidates}:
        raise ValueError('Every private-narration candidate needs an actual disposition')
    for row in rows:
        if row.get('decision')!='keep_validity_condition' or not row.get('reason'):
            raise ValueError('Private report-writing narration remains in delivered text')


META_INSTRUCTIONS='''For every report_meta_candidate return report_economy.meta_results:
[{candidate_id,decision:"keep_validity_condition|remove_private_narration",reason}]. These are
heuristic candidates, not prohibited words. Keep a real mathematical condition, author choice
or action-changing uncertainty; remove explanations of what the reviewer did not draft or
why a replacement was withheld. Evaluate each full context in both languages. A remaining
remove_private_narration item blocks delivery. Do not delete technical negation or factual scope.
'''
