"""Private source-bound Expression snapshots and independent Advisor retrieval.

Recorded matches are candidates, never defects or certified mentor preferences.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

SCOPES = {'sentence', 'paragraph', 'argument_unit', 'section', 'cross_section', 'whole_paper'}
FIELDS = ['title', 'section_task', 'before_account', 'observed_change', 'changed_relationship',
          'after_account', 'transfer_conditions', 'do_not_transfer', 'facts_and_qualifications', 'source_review_status']
LIST_OR_TEXT_FIELDS = {'transfer_conditions', 'do_not_transfer', 'facts_and_qualifications'}
TASK_SCHEMA = '''Independently map the supplied manuscript's editorial tasks for Advisor retrieval.
No Reader/Expert plan, findings or historical answers are supplied. Return JSON
{tasks:[{id:"AT1",anchors:[{page,quote} or {page,kind:"image",description}],section_task,scope:"sentence|paragraph|argument_unit|section|cross_section|whole_paper",
rhetorical_relation,retrieval_terms:[]}],page_coverage:[{page,status:"mapped|unreadable|unfinished",reason}],limits:[]}.
Cover actual paragraph/section tasks, information selection, emphasis and handoffs, including
model, method, proof and experiments. Anchor each task to existing text/images. Describe current
roles and neutral relations to inspect, not defects or preferred rewrites. No task-count quota.
Text quotes must be continuous exact supplied extraction. Use an image anchor for visually
read spans that are interleaved or absent in extraction; never invent a matching text quote.
Unreadable/unmapped scope stays explicit. No judgment, gap, findings or suggestions in this map.
'''
TRANSFER_SCHEMA = '''EXPRESSION: Supplied expression_sources contain actual attributed mentor
proposals and original context. These are not accepted revised paragraphs, scientific facts or
universal preferences. Read complete supplied context. Test conditions against the target.
When supplied, language_choices.proposal_source_match records literal matching only. An analysis_not_verbatim
representation must not be quoted as mentor wording. Even a verbatim_mentor_excerpt may be
discussion, an outline or a fragment rather than proposed or accepted manuscript prose.
Only the supplied Expression records are admitted transfer candidates. Extra annotations in
their full original-page context are contextual evidence; do not promote them into new writing
guidance, use a held proposal, or invent a source ID from that context.
For every supplied Expression record return at least one writing_transfer with
source_kind="mentor_expression", source_id=its ID, and source_excerpt an exact excerpt from
mentor_texts.text or, for an explicit deletion with no annotation wording, marked_texts.text.
The latter is original manuscript text marked by the mentor, never mentor-authored wording.
Include concrete sentence/paragraph operations, the observed distinction,
target support, preserved facts/conditions and reasons to keep/not apply. Every assigned
expression_task needs expression_task_dispositions:[{task_id,status:"checked|unfinished",
transfer_ids:[],reason}]. Checked tasks link at least one source-based or manuscript-only
transfer anchored to that task's actual target page; no-match tasks still receive manuscript inspection.
Each linked editorial Concern also needs its own source_kind="advisor_concern" transfer.
A related mentor_expression transfer preserves a different source and does not replace that
Concern record. Keep exact attributed wording and the Concern abstraction separately traceable.
When records contain language_features, inspect their concrete lexical/syntactic choices and
source genre. Unclassified excerpts require contextual judgment, not promotion by literal match.
Preserve actual feature IDs and conditions when describing a transfer; detailed final-sentence
realization is checked in post-freeze drafting, not a reason to invent a manuscript defect.
Do not invent applied after text,
mentor acceptance or target facts. Mandatory repairs and optional improvements stay distinct.
When a record contains held_operations, those remain archived unresolved actions,
not admitted writing guidance. Transfer only its admitted operations under the stated
target conditions. Version-response reviews may extend the original learning context;
their unknown-writer body text and later annotation context do not establish mentor
authorship, acceptance or independently admitted additional guidance.
'''


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def check_records(records, episodes, concern_ids=None):
    by_episode = {e['id']: e for e in episodes}
    require(len(by_episode) == len(episodes), 'Duplicate Expression episode')
    require(len({r['id'] for r in records}) == len(records), 'Duplicate Expression ID')
    by_record={r['id']:r for r in records}
    for record in records:
        linked = record.get('episode_ids', [])
        require(linked and len(linked) == len(set(linked)) and set(linked) <= by_episode.keys(), 'Unknown Expression episode')
        context_ids = record.get('context_episode_ids', [])
        require(isinstance(context_ids,list) and len(context_ids)==len(set(context_ids)) and
                set(context_ids)<=by_episode.keys() and not set(context_ids)&set(linked), 'Unknown Expression context episode')
        require(record.get('authority') in {'mentor_wording', 'explicit_editorial_action'}, 'Unattributed Expression authority')
        require(record.get('preference_status') in {'local_requirement', 'provisional_preference', 'unresolved'}, 'Unsupported Expression preference')
        require(record.get('scope') in SCOPES, 'Invalid Expression scope')
        for field in FIELDS:
            value = record.get(field)
            valid = isinstance(value, str) and bool(value.strip())
            if field in LIST_OR_TEXT_FIELDS and isinstance(value, list):
                valid = bool(value) and all(isinstance(item, str) and item.strip() for item in value)
            require(valid, 'Incomplete Expression: '+field)
        for field in ['operations', 'retrieval_terms', 'concern_ids', 'mentor_texts', 'evidence_refs']:
            require(isinstance(record.get(field), list), 'Missing Expression list: '+field)
        require(record['operations'] and record['retrieval_terms'], 'Expression lacks concrete operations/retrieval')
        if concern_ids is not None:
            require(set(record['concern_ids']) <= set(concern_ids), 'Expression links an unknown Concern')
        evidence = {f['ref']: f for eid in linked for f in by_episode[eid]['feedback']}
        quoted={t['ref'] for t in record['mentor_texts']}
        marked = record.get('marked_texts', [])
        require(isinstance(marked, list), 'Invalid marked Expression text')
        marked_by_ref = {t.get('ref'): t for t in marked}
        require(len(marked_by_ref) == len(marked), 'Duplicate marked Expression text')
        for item in marked:
            source = evidence.get(item.get('ref'))
            require(source and source.get('author') == 'mentor_confirmed' and
                    source.get('subtype') == '/StrikeOut' and item.get('action') == 'delete' and
                    item.get('text') and item['text'] == source.get('marked_text'),
                    'Expression deletion lacks exact attributed source span')
        require(set(marked_by_ref) <= quoted, 'Expression action lacks annotation attribution')
        cited=set(record['evidence_refs'])
        require(record['mentor_texts'] and quoted <= cited <= (evidence.keys() | set(linked) | set(context_ids)), 'Expression evidence/text mismatch')
        for text in record['mentor_texts']:
            source = evidence.get(text.get('ref'))
            require(source and source.get('author') == 'mentor_confirmed', 'Expression text has no confirmed mentor')
            exact = text.get('text') == source['mentor_text']
            action_only = text.get('ref') in marked_by_ref
            require(exact, 'Expression changed actual mentor text')
            require(bool(text.get('text')) or action_only,
                    'Empty markup supplies no mentor wording or verified deletion action')
        require(record['authority'] != 'mentor_wording' or any(t['text'] for t in record['mentor_texts']),
                'Mentor wording authority lacks actual wording')
        require(all(any(t['ref'] in {f['ref'] for f in by_episode[eid]['feedback']} for t in record['mentor_texts']) for eid in linked), 'Expression episode has no quoted evidence')
        bindings=record.get('local_reference_bindings',[])
        require(isinstance(bindings,list),'Invalid Expression companion bindings')
        for binding in bindings:
            require(binding.get('source_local_id') and binding.get('status') in {'admitted','held'},'Invalid Expression companion state')
            if binding['status']=='held':
                require(binding.get('expression_id') is None,'Held companion cannot supply admitted guidance')
            else:
                require(binding.get('expression_id') in by_record and binding['expression_id']!=record['id'],'Unknown Expression companion')


def build(records, episodes, destination, concern_ids):
    """Create a private immutable snapshot; caller performs semantic admission."""
    dest = Path(destination).resolve()
    require('private' in dest.parts, 'Raw Expression snapshots must stay in private storage')
    require(not dest.exists(), 'Expression snapshot exists; preserve prior version')
    check_records(records, episodes, concern_ids)
    require(all(r['preference_status']!='unresolved' for r in records), 'Unresolved Expression cannot enter a runtime snapshot')
    for e in episodes:
        require(sha(e['source_path']) == e['source_sha256'], 'Expression original source changed')
        require(sha(e['image_path']) == e['image_sha256'], 'Expression source image changed')
    dest.mkdir(parents=True)
    def save(name, value):
        (dest/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    save('records.json', records)
    save('episodes.json', episodes)
    save('index.json', [{'id':r['id'], 'section_task':r['section_task'], 'scope':r['scope'],
                        'retrieval_terms':r['retrieval_terms'], 'concern_ids':r['concern_ids'],
                        'authority':r['authority'], 'preference_status':r['preference_status']} for r in records])
    save('manifest.json', {'role':'private_advisor_expression', 'version':1, 'count':len(records),
        'families':sorted({e['family_id'] for e in episodes}), 'private_raw_text':True,
        'source_scope':'Attributed mentor proposals with original context; applied versions/acceptance not presumed',
        'training_exposure':'Historical Concern development families; no held-out claim'})
    save('FREEZE.json', {'files':{name:sha(dest/name) for name in ['records.json','episodes.json','index.json','manifest.json']}})
    return dest


def validate_tasks(result, manuscript, anchor):
    pages = {p['page']:p['text'] for p in manuscript}
    require(isinstance(result.get('tasks'), list), 'Missing independent Advisor tasks')
    require(not any(k in result for k in ['findings','organization_suggestions','judgment','gap']), 'Advisor task map must not contain verdicts')
    require(len({t['id'] for t in result['tasks']}) == len(result['tasks']), 'Duplicate Advisor task')
    for task in result['tasks']:
        require(task['id'].startswith('AT') and task.get('scope') in SCOPES, 'Invalid Advisor task')
        require(not any(k in task for k in ['judgment','gap','finding_ids','proposed_action']), 'Advisor tasks must not pre-judge')
        require(task.get('anchors') and task.get('section_task') and task.get('rhetorical_relation') and task.get('retrieval_terms'), 'Incomplete Advisor task')
        for item in task['anchors']:
            anchor(item, pages)
    rows = result.get('page_coverage', [])
    require(len(rows) == len(pages) and {r['page'] for r in rows} == pages.keys(), 'Advisor map page coverage')
    for row in rows:
        require(row.get('status') in {'mapped','unreadable','unfinished'} and row.get('reason'), 'Advisor map coverage state')
        if row['status'] == 'mapped':
            require(any(a['page'] == row['page'] for t in result['tasks'] for a in t['anchors']), 'Mapped page lacks task')


def tokens(text):
    stop = {'the','and','for','with','from','this','that','into','each','given','paper','task','method'}
    return set(re.findall(r'[a-z][a-z0-9_]{2,}', text.lower()))-stop


def route(library, tasks, batches, top_k=3):
    records = read(Path(library)/'records.json')
    require(batches and top_k > 0, 'Expression route requires Advisor batches and capacity')
    assignments = {stage:{'task_ids':[], 'record_ids':[], 'candidates':[]} for stage in batches}
    stages = list(batches)
    for i, task in enumerate(tasks):
        stage = stages[i % len(stages)]
        assignments[stage]['task_ids'].append(task['id'])
        query = tokens(' '.join([task['section_task'],task['rhetorical_relation']]+task['retrieval_terms']))
        ranked = []
        for record in records:
            terms = tokens(' '.join([record['section_task'],record['changed_relationship']]+record['retrieval_terms']))
            overlap = sorted(query & terms)
            if overlap:
                ranked.append({'record_id':record['id'], 'task_id':task['id'], 'score':len(overlap),
                               'matched_terms':overlap, 'basis':'independent_target_task'})
        ranked.sort(key=lambda r:(-r['score'],r['record_id']))
        for n, item in enumerate(ranked):
            item['selected'] = n < top_k
            assignments[stage]['candidates'].append(item)
            if item['selected']:
                assignments[stage]['record_ids'].append(item['record_id'])
    for stage, card_ids in batches.items():
        for record in records:
            links = sorted(set(record['concern_ids']) & set(card_ids))
            if links:
                assignments[stage]['record_ids'].append(record['id'])
                assignments[stage]['candidates'].append({'record_id':record['id'], 'concern_ids':links,
                                                        'selected':True,'basis':'linked_concern'})
        assignments[stage]['record_ids'] = sorted(set(assignments[stage]['record_ids']))
        by_id={r['id']:r for r in records}
        supplied=set(assignments[stage]['record_ids'])
        pending=sorted(supplied,reverse=True)
        while pending:
            current=by_id[pending.pop()]
            for binding in current.get('local_reference_bindings',[]):
                if binding['status']!='admitted':continue
                dependency=binding['expression_id']
                require(dependency in by_id,'Missing admitted Expression companion')
                if dependency not in supplied:
                    supplied.add(dependency);pending.append(dependency)
                    assignments[stage]['candidates'].append({'record_id':dependency,'selected':True,
                        'basis':'explicit_source_learning_companion','requested_by':current['id']})
        assignments[stage]['record_ids']=sorted(supplied)
    return {'version':1,'top_k':top_k,'assignments':assignments,
            'limit':'Transparent lexical candidate retrieval plus linked Concern union; semantic suitability is judged by Advisor. No match is not no manuscript issue.'}


def admitted_closure(by_id, wanted):
    """Keep explicit admitted source companions, including transitive prerequisites."""
    supplied=set(wanted)
    require(supplied<=set(by_id),'Unknown routed Expression')
    pending=sorted(supplied,reverse=True)
    while pending:
        current=by_id[pending.pop()]
        for binding in current.get('local_reference_bindings',[]):
            if binding['status']!='admitted':continue
            dependency=binding['expression_id']
            require(dependency in by_id,'Missing admitted Expression companion')
            if dependency not in supplied:
                supplied.add(dependency);pending.append(dependency)
    return supplied


def frozen_active_links(library, records):
    """Apply only the new run's frozen overlay to derived views, never original files."""
    library=Path(library); overlay=library.parent/'expression_concern_links.json'
    if not overlay.exists():return records
    table=read(overlay)
    require(sha(library/'records.json')==table['corpus_sha256']['corpus/advisor-expression-v1/records.json'],
            'Frozen relation overlay differs from Expression source')
    historical={(r['expression_id'],r['concern_id']) for r in table['links'] if r['kind']=='historical'}
    return [{**r,'concern_ids':[c for c in r['concern_ids'] if (r['id'],c) not in historical]} for r in records]


def view(library, wanted):
    available=read(Path(library)/'records.json')
    supplied=admitted_closure({r['id']:r for r in available},wanted)
    records = [r for r in available if r['id'] in supplied]
    import public_expression as public
    if read(Path(library)/'manifest.json').get('role') in public.ROLES:
        public.check_records(records)
        return {'records':frozen_active_links(library,[public.project(r) for r in records]), 'episodes':[],
                'source_format':public.FORMAT,
                'limits':'Minimized examples and conditional analysis only; private original pages and mapping are not available.'}
    episode_ids = {eid for r in records for eid in r['episode_ids']+r.get('context_episode_ids',[])}
    episodes = [{k:v for k,v in e.items() if k not in {'source_path','image_path'}}
                for e in read(Path(library)/'episodes.json') if e['id'] in episode_ids]
    if read(Path(library)/'manifest.json').get('expression_episode_projection') == 2:
        # Derived labels leave the frozen records and their actual quotations intact.
        labeled=[]
        for record in records:
            choices=[]
            for choice in record.get('language_choices',[]):
                proposal=choice.get('mentor_proposal','')
                refs=[t['ref'] for t in record['mentor_texts'] if proposal and proposal in t['text']]
                kind='verbatim_mentor_excerpt' if refs else 'analysis_not_verbatim' if proposal else 'not_supplied'
                choices.append({**choice,'proposal_source_match':{'kind':kind,'refs':refs}})
            labeled.append({**record,'language_choices':choices})
        records=labeled
        # Keep complete original/neighbor prose and literal annotation context;
        # geometric locators and duplicate analytical cards stay in the archive.
        allowed = {'id','family_id','group_id','source_sha256','page','page_text',
                   'neighboring_page_text','image_sha256','chronology','after',
                   'training_exposure','version_response_review','context_image_refs'}
        feedback_fields = {'ref','mentor_text','marked_text','subtype','author','author_raw',
                           'annotation_index','reply_to_object_id'}
        projected=[]
        for episode in episodes:
            result={k:v for k,v in episode.items() if k in allowed}
            result['feedback']=[{k:v for k,v in f.items() if k in feedback_fields} for f in episode['feedback']]
            if episode.get('context_annotations'):
                result['context_annotations']=[{k:v for k,v in f.items() if k in
                    {'page','annotation_index','author_raw','contents','subtype','reply_to_object_id'}}
                    for f in episode['context_annotations']]
            projected.append(result)
        episodes=projected
    return {'records':records,'episodes':episodes}


def stage_context(run, stage):
    run = Path(run)
    route_path = run/'expression_route.json'
    task_path = run/'calls/advisor_tasks/response.json'
    protocol = read(run/'inputs/protocol.json')
    if stage.startswith('evidence_') and protocol.get('advisor_batching'):
        # Adaptive packets have their own frozen ownership; deferred evidence remains
        # Concern-specific and must not rebuild the original preparation route.
        return {'expression_version':1,'expression_tasks':[], 'expression_sources':{'records':[],'episodes':[]}}
    require(task_path.exists(), 'Complete independent Advisor tasks before Expression retrieval')
    stages = [s for s in protocol['stages'] if s.startswith('supplement_')]
    batches = {s:[c['id'] for c in read(run/f'inputs/batches/batch_{s.rsplit("_",1)[1]}.json')] for s in stages}
    tasks = read(task_path)['tasks']
    expected = {**route(run/'inputs/expression',tasks,batches),
                'task_map_sha256':sha(task_path),
                'library_freeze_sha256':sha(run/'inputs/expression/FREEZE.json')}
    if route_path.exists():
        require(read(route_path) == expected, 'Frozen Expression route changed')
    else:
        route_path.write_text(json.dumps(expected,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if stage.startswith('evidence_'):
        # Deferred evidence is Concern-specific; do not silently introduce unrelated task scope.
        return {'expression_version':1,'expression_tasks':[], 'expression_sources':{'records':[],'episodes':[]}}
    assigned = expected['assignments'][stage]
    return {'expression_version':1,
            'expression_tasks':[t for t in tasks if t['id'] in assigned['task_ids']],
            'expression_sources':view(run/'inputs/expression',assigned['record_ids'])}


def transfer_schema(context):
    import public_expression as public
    schema = TRANSFER_SCHEMA
    if context.get('advisor_direct_fulltext'):
        start = schema.index('Every assigned\nexpression_task')
        end = schema.index('Each linked editorial Concern', start)
        schema = schema[:start] + schema[end:]
    if any(public.is_public(r) for r in context.get('expression_sources',{}).get('records',[])):
        return schema+'\nFor public-format records, the following labeled-example/account contract replaces the raw mentor_texts, marked_texts and full original-page source requirements. No raw episodes are available.\n'+public.SCHEMA
    return schema


def validate_dispositions(response, context):
    if context.get('advisor_direct_fulltext'):
        require(not context.get('expression_tasks') and not response.get('expression_task_dispositions'), 'Direct Advisor has no preliminary task assignments')
        return
    expected = {t['id'] for t in context.get('expression_tasks', [])}
    rows = response.get('expression_task_dispositions')
    require(isinstance(rows,list) and len(rows) == len(expected) and {r['task_id'] for r in rows} == expected, 'Expression task coverage mismatch')
    transfers = {r['id']:r for r in response.get('writing_transfers', [])}
    tasks = {t['id']:t for t in context.get('expression_tasks',[])}
    for row in rows:
        require(row.get('status') in {'checked','unfinished'} and row.get('reason'), 'Expression task state')
        require(set(row.get('transfer_ids',[])) <= transfers.keys(), 'Unknown Expression task transfer')
        if row['status'] == 'checked':
            require(row.get('transfer_ids'), 'Checked Expression task lacks inspection record')
            task_pages={a['page'] for a in tasks[row['task_id']]['anchors']}
            require(any(task_pages & {a['page'] for a in transfers[tid]['target_anchors']}
                        for tid in row['transfer_ids']), 'Checked Expression task has no target-linked inspection')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--records',type=Path,required=True)
    p.add_argument('--episodes',type=Path,required=True)
    p.add_argument('--concerns',type=Path,required=True)
    p.add_argument('--destination',type=Path,required=True)
    a = p.parse_args()
    print(build(read(a.records),read(a.episodes),a.destination,[c['id'] for c in read(a.concerns)]))
