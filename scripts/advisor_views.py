"""Stage-specific Expression view; full frozen records remain drafting sources."""
import copy

INSTRUCTIONS='''EXPRESSION REVIEW VIEW v1:
This call diagnoses and proposes modification directions; it does not draft the
final replacement prose. Complete canonical operations, every individual condition,
exception, factual qualification and source example remain review evidence.
Reusable sentence frames and drafting permission/pair metadata remain local and
are retrieved from the frozen full source for post-merge drafting. Do not invent
or cite those hidden fields. Examples here illustrate evidence, not permission to
copy wording. Analyst abstractions are never mentor quotations. Cite visible
source examples/conditions and target locators for actionable suggestions; retain
all existing explicit source/use decisions and full Concern review. No extra
screening pass or implicit completion is introduced.'''

def separate(review, administration):
    administration['draft_view_fields']={}
    for record in review.get('expression_sources',{}).get('records',[]):
        saved={k:copy.deepcopy(record[k]) for k in ['language_features','public_language_features','examples'] if k in record}
        administration['draft_view_fields'][record['id']]=saved
        for key in ['language_features','public_language_features']:
            features=record.get(key,[])
            if isinstance(features,list):
                for feature in features:feature.pop('frame',None)
            elif isinstance(features,dict):
                for row in features.get('items',[]):row['keys']=[k for k in row['keys'] if k!='frame']
        for example in record.get('examples',[]):
            for key in ['body_form_allowed','pair_id']:example.pop(key,None)

def restore(result,administration):
    for record in result.get('expression_sources',{}).get('records',[]):
        record.update(copy.deepcopy(administration['draft_view_fields'][record['id']]))

def withheld_path(path):
    return bool(path and path[0]=='expression_sources' and
      (('frame' in path and any(k in path for k in ['language_features','public_language_features'])) or
       ('examples' in path and any(k in path for k in ['body_form_allowed','pair_id']))))
