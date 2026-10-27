"""Versioned economical review view and explicit grouped non-action decisions."""
import copy

LOCAL_FIELDS=('before_account','observed_change','changed_relationship','after_account','retrieval_terms')
INSTRUCTIONS='''ADVISOR ECONOMICAL REVIEW v1:
Concern remains a full independent requirement review. Expression prioritizes clear
errors, useful realization of repairs and worthwhile improvements, not exhaustive
style alternatives. Review operation families together in this SAME call; these
families are routing hints, never evidence that cases or conditions are equivalent.
Read each member's operations, examples, provenance, conditions and boundaries.
Narrative history/retrieval fields stay local; the review receives core guidance.
This is a deliberately narrower review view, not lossless semantic compression.
For non-action Expressions sharing an ACTUAL decision/reason and target comparison,
return expression_assessment_groups:[{id:"STAGE:WG1",source_ids:[...],decision,
reason,target_anchors:[...]}]. Decisions: keep/not_applicable/unknown/unfinished.
Each member is an explicit model decision, never inferred from absence. KEEP groups
need a real common target anchor. If conditions, reason or target differ, split the
group or return ordinary individual brief records. The program expands members to
transfer IDs group.id+"."+source_id, e.g. STAGE:WG1.EX00001; use those exact IDs in
explicit source_use_dispositions. Every source/use remains accounted for. Do not
claim an uninspected association is checked. Group uncertainty separately.
Actionable cases retain complete source, check and finding/suggestion evidence.
Use supplied $anchor passage IDs, never retype or abbreviate extraction quotations.
For formula/glyph/layout evidence use {$image_anchor:{page:2,description:"Equation
(5), right column: ..."}}. A locator copies no invented text and certifies no visual
judgment; inspect the supplied image. No second screening/review call is added.'''

def families(records):
    """Coarse routing only: never merge evidence, drop cases or assign decisions."""
    groups={}
    for record in records:
        kinds=sorted({f['kind'] for f in record.get('language_features',[])})
        family=' / '.join(kinds) or 'conditional_operation'
        groups.setdefault(family,[]).append(record['id'])
    return [{'family':k,'source_ids':v} for k,v in sorted(groups.items())]

def expand_groups(response, context):
    if 'expression_assessment_groups' not in response:return
    if context.get('advisor_efficiency')!=1:raise ValueError('Unpinned grouped assessment')
    groups=response.pop('expression_assessment_groups')
    if not isinstance(groups,list):raise ValueError('Invalid assessment groups')
    available={r['id'] for r in context['expression_sources']['records']}
    rows=response.setdefault('writing_transfers',[])
    seen={r.get('source_id') for r in rows if r.get('source_kind')=='mentor_expression' or r.get('source_id') in available}
    gids=set()
    for g in groups:
        if set(g)!={'id','source_ids','decision','reason','target_anchors'}:raise ValueError('Invalid group fields')
        if not isinstance(g['id'],str) or ':W' not in g['id'] or g['id'] in gids:raise ValueError('Invalid/duplicate group ID')
        gids.add(g['id']);members=g['source_ids']
        if not isinstance(members,list) or not members or any(not isinstance(s,str) for s in members):raise ValueError('Invalid group membership')
        if len(members)!=len(set(members)) or not set(members)<=available or set(members)&seen:raise ValueError('Duplicate or unsupplied grouped source')
        if g['decision'] not in {'keep','not_applicable','unknown','unfinished'}:raise ValueError('Group cannot replace actionable evidence')
        seen.update(members)
        for source in members:
            rows.append({'id':g['id']+'.'+source,'source_id':source,'source_kind':'mentor_expression',
                'assessment':'brief','decision':g['decision'],'reason':g['reason'],
                'target_anchors':copy.deepcopy(g['target_anchors']),'assessment_group':g['id']})
