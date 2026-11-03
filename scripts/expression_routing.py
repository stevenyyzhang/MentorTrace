"""Bounded post-freeze candidates for every revision target; no adoption judgments."""
from pathlib import Path
import expression_runtime as expression

# Task matching should not be driven by shared grammatical glue. Only this routing
# layer changes; original mentor examples, admitted features and checks remain intact.
GENERIC={'its','than','within','have','has','are','was','were','will','can','may','should','would',
         'use','used','using','state','stated','include','included','provide','given','actual',
         'describe','description','text','sentence','paragraph','word','wording','change','changes',
         'before','after','also','only','other','these','those','such','which','where','when'}


def task_terms(text):
    return expression.tokens(text)-GENERIC


def eligible(feature):
    # These are already admitted features, not raw comments or held choices.
    return bool(feature.get('body_evidence', {}).get('body_form_allowed')) or feature.get('evidence_kind') in {
        'deletion', 'editorial_instruction', 'analytical_operation', 'mentor_prose', 'mentor_fragment'}


def route(library, items, *, concern_links=None, top_k=2):
    if type(top_k) is not int or top_k < 1:
        raise ValueError('Positive bounded retrieval size required')
    library = Path(library)
    raw = expression.read(library/'records.json')
    # view applies the frozen active-link overlay and supplies full admitted features.
    records = expression.view(library, [r['id'] for r in raw])['records']
    index = []
    for r in records:
        features = [f for f in r.get('language_features', []) if eligible(f)]
        if not features:
            continue
        functions = task_terms(' '.join(str(f.get(k, '')) for f in features
                                               for k in ['kind', 'function', 'operation']))
        tasks = task_terms(' '.join(str(r.get(k, '')) for k in
                                           ['title', 'section_task', 'changed_relationship', 'retrieval_terms']))
        modes = sorted({'wording' if f.get('body_evidence', {}).get('body_form_allowed')
                        or f.get('evidence_kind') == 'deletion' else 'editorial_operation' for f in features})
        index.append((r, functions, tasks, modes))
    links = []
    if len({item['id'] for item in items}) != len(items):
        raise ValueError('Duplicate revision target ID')
    for item in items:
        # Surface and action-only targets participate; no mandatory paragraph rewrite.
        query = task_terms(' '.join(str(item.get(k, '')) for k in
            ['title', 'reader_task', 'relation', 'gap', 'closure_goal', 'current_order',
             'proposed_order', 'action', 'suggestion', 'correction', 'suggested_text',
             'category', 'reason', 'delivery_action', 'question']))
        cids = set((concern_links or {}).get(item['id'], []))
        candidates = []
        for r, functions, tasks, modes in index:
            fm, tm = sorted(query & functions), sorted(query & tasks)
            linked = sorted(cids & set(r.get('concern_ids', [])))
            if not (linked or fm or len(tm)>=2):
                continue
            candidates.append({'record_id': r['id'], 'score': 3*len(fm)+len(tm),
                'function_matches': fm, 'task_matches': tm, 'concern_ids': linked,
                'modes': modes, 'basis': 'linked_concern_and_task' if linked else 'post_freeze_language_task'})
        candidates.sort(key=lambda r: (not bool(r['concern_ids']), -r['score'], r['record_id']))
        chosen = []
        # Rank task relevance first. Do not spend a slot on a weak different mode
        # merely to obtain one wording and one organization example.
        for r in candidates:
            if len(chosen) >= top_k:
                break
            if r['record_id'] not in chosen:
                chosen.append(r['record_id'])
        for r in candidates:
            r['selected'] = r['record_id'] in chosen
        links.append({'verified_id': item['id'], 'expression_ids': chosen,
            'scope': 'post-freeze wording/action retrieval; not original discovery',
            'retrieval': {'version': 3, 'top_k': top_k,
                'status': 'candidates_available' if chosen else 'no_candidate',
                'limit': 'Bounded lexical and frozen-association retrieval; no semantic adoption or exhaustive-match claim.',
                'assignments': {'draft': {'record_ids': chosen, 'candidates': candidates}}}})
    return links
