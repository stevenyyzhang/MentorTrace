"""Mechanical placeholder candidates plus an explicit model economy judgment."""
import re


DRAFT_INSTRUCTIONS='''CONCISE REPORT CONTRACT:
Keep every supported independent requirement, condition, uncertainty and exact edit location.
Comment explains the problem and consequence once; Suggested revision gives the concrete action.
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
