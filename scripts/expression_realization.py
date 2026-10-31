"""Source-bound language features and their realization in actual replacement prose.

No model calls. Mechanical checks bind evidence and text, not linguistic truth.
Existing frozen libraries and proposals remain readable without this protocol.
"""
import hashlib
import json
from pathlib import Path
import re
import shutil

KINDS = {'lexical','syntax','qualification','transition','sentence_order','paragraph','unclassified'}
EVIDENCE_KINDS = {'mentor_prose','mentor_fragment','editorial_instruction','analytical_operation','deletion','mentor_excerpt_unclassified'}
SCHEMA = '''LANGUAGE REALIZATION v1: Return language_realizations, one record per revision_actions
group with the identical draft_label and verified_ids. Each is {draft_label,verified_ids:[],
scope:"prose|action_only|no_rewrite",passages:[{id,text}],source_disposition:"used|no_match|no_rewrite",
reason,feature_decisions:[{expression_id,feature_id,decision:"use|adapt|not_applicable",
realization_type:"language_form|language_edit|editorial_operation",
evidence_kind:"mentor_prose|mentor_fragment|editorial_instruction|analytical_operation|deletion",source_ref,source_quote,
requested_feature,target_quote,realization_explanation,preserved_meaning,adaptations,reason}]}.
Every passage.text is the COMPLETE actual English manuscript replacement, copied exactly from
report_markdown; never the review explanation or an instruction to the author. Supply distinct
passages for noncontiguous replacements. action_only/no_rewrite has no replacement passages.
Before drafting, use the linked language feature plus its COMPLETE supplied context to decide
whether it fits this target task. Preserve concrete subject/verb/complement forms, collocations,
qualification or transition choices when they work here. Distinguish source-proposed prose,
isolated words, instructions to an author and deleted author text. Unclassified historical
features require an explicit contextual evidence_kind judgment; literal quotation alone is
not genre classification. Never turn an instruction (e.g. 'you should') into manuscript prose.
Only a source's body_form_allowed=true insertion/replacement candidate can support language_form,
and contextual judgment must confirm mentor_prose/mentor_fragment. Ordinary comments, including
fluent English sentences inside numbered instructions, NEVER supply manuscript wording or syntax.
They may support editorial_operation only. A deletion supports language_edit, not mentor-authored
positive wording. Annotation metadata establishes a candidate, not automatic semantic admission.
Actual mentor title/heading examples marked body_form_allowed=false likewise support
editorial_operation only, with no body-drafting frame or body-sentence attribution.
Public v2 analytical_operation features quote a supplied analytical account, not mentor text.
They support editorial_operation only and never positive manuscript wording or language_edit.
Held features/operations are ineligible. Source frames are analyst abstractions, not quotations.
For use/adapt, target_quote must be an exact substantive span of a supplied replacement passage,
and explain the specific realized language feature, preserved target meaning and any adaptation.
For action_only, cite the exact delivered editing action in target_quote and explain its operation;
do not claim that an unwritten paragraph realizes a sentence pattern. A paragraph-order instruction
is not evidence of a copied mentor sentence. No generic 'clarity' attribution or source-ID-only claim.
For not_applicable, target_quote is empty and reason states the target-specific conflict.
Use only features from the linked supplied records, including admitted companions; each selected
feature ID is unique within its group. A valid source need not be used, but do not claim realized
style when no compatible feature reached the text. no_match records why the supplied evidence
does not justify a concrete language operation. Do not force changes to already retained prose.
Facts, formulae, roles, sequence, citations and claim strength come only from this manuscript.
Never transplant source-specific facts, universalize a local correction or guarantee mentor approval.
The review comment's wording does not count as realization in the manuscript replacement.
For public_minimized_expression_v1 records, private original pages are unavailable. Read all
supplied minimized examples, analytical accounts, conditions and limits; do not reconstruct
omitted context. source_ref binds a public example ID, not an original annotation locator.
No new findings, extra replacement scope, or competing drafts may be introduced by style retrieval.
'''

REVIEW_SCHEMA = '''Within the existing final-text review, review the language_realizations against
the actual complete replacement passages and all supplied source context. Return realization_review:
{reviewer,groups:[{draft_label,meaning:{status:"pass|fail",reason},
naturalness:{status:"pass|fail",reason},feature_results:[{expression_id,feature_id,
status:"confirmed|rejected",reason}]}]}. Exactly cover every draft group and every use/adapt
feature, including action-only operations. Independently check source genre, target applicability,
actual linguistic realization, adaptations and preservation of meaning. A source ID, shared words,
or the drafter's explanation is not evidence of success. Reject instruction-as-prose, transferred
source facts, unsupported sequence/roles, unsupported certainty and purely nominal attributions.
Do not require literal copying of a whole sentence or count nonuse as successful mentor imitation.
Check explicit body insertion/replacement evidence before confirming any language_form. Reject
comment-to-prose style learning even when the comment contains grammatically complete sentences.
language_form needs a concrete lexical choice or grammatical construction retained/adapted in
the target. Shared topic, information role or numeric scope alone is editorial reasoning, not
evidence that the mentor's wording/syntax reached the sentence. Report retained versus newly
changed forms separately; source attribution cannot establish a causal improvement.
A mentor-style writing goal does not require the replacement to outperform the original.
Confirm actual compatible feature realization and preserved meaning even when comparative
quality is uncertain or equivalent; state style alignment separately from quality improvement.
This is source-conditioned semantic review, not mentor approval or scientific certification.
Public-format source context is explicitly minimized; do not claim inspection of omitted
private pages or infer their content. Apply the same evidence-genre and actual-text checks.
'''

def require(ok, message):
    if not ok: raise ValueError(message)

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def write(path,value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def text_sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def meaningful(value):
    return isinstance(value,str) and bool(value.strip()) and any(c.isalnum() for c in value)

def account(value):
    return meaningful(value) or (isinstance(value,list) and bool(value) and all(meaningful(v) for v in value))

def check_feature(feature, record):
    require(feature.get('id','').startswith(record['id']+':L'),'Feature namespace mismatch')
    require(feature.get('kind') in KINDS,'Unknown language feature kind')
    require(feature.get('evidence_kind') in EVIDENCE_KINDS,'Unknown language evidence kind')
    import public_expression as public
    if public.is_public(record):
        public.check_feature(feature,record)
    else:
        require(feature['evidence_kind'] != 'analytical_operation', 'Analytical operation requires explicit public account binding')
        source=record.get('marked_texts',[]) if feature['evidence_kind']=='deletion' else record['mentor_texts']
        quote=feature.get('source_quote')
        require(meaningful(quote) and any(t['ref']==feature.get('source_ref') and quote in t['text'] for t in source),
                'Language feature quote/ref absent from attributed source')
    for key in ['function','operation','conditions','do_not_transfer']:
        require(bool(feature.get(key)),'Missing language feature '+key)
    require(isinstance(feature.get('frame',''),str),'Invalid analytical frame')

def derive(record):
    """Reuse existing learned choices without pretending regex performs semantic admission."""
    features=[];held=[]
    for n,choice in enumerate(record.get('language_choices',[]),1):
        proposal=choice.get('mentor_proposal','')
        matches=[t for t in record['mentor_texts'] if proposal and proposal in t['text']]
        deleted=not proposal and [t for t in record.get('marked_texts',[]) if
            choice.get('original') and choice['original'] in t['text']]
        if not matches and not deleted:
            held.append({'choice_index':n,'reason':'No exact proposal or attributed deletion span; analytical wording is not mentor prose.'})
            continue
        if re.search(r'\bheld\b',str(choice.get('operation','')),re.I):
            held.append({'choice_index':n,'reason':'Existing learned operation explicitly held.'});continue
        selected=(matches or deleted)[0]
        quote=proposal if matches else choice['original']
        if not meaningful(quote):
            held.append({'choice_index':n,'reason':'Punctuation-only edit retained in original evidence; no standalone lexical/syntactic feature.'})
            continue
        feature={'id':record['id']+':L'+str(n),'kind':'unclassified',
            'evidence_kind':'mentor_excerpt_unclassified' if matches else 'deletion',
            'source_ref':selected['ref'],'source_quote':quote,
            'function':choice.get('role') or record['section_task'],'frame':'',
            'operation':choice.get('operation') or record['observed_change'],
            'conditions':choice.get('conditions') or record['transfer_conditions'],
            'do_not_transfer':record['do_not_transfer'],
            'provenance':'reused_existing_language_choice; genre and applicability require contextual drafting review',
            'choice_index':n}
        check_feature(feature,record);features.append(feature)
    return features,held


def body_evidence(feature,record,episodes):
    """Conservative source-role admission; ordinary comments cannot supply body syntax."""
    feedback=[f for eid in record['episode_ids'] for f in episodes[eid]['feedback']]
    source=next((f for f in feedback if f['ref']==feature['source_ref']),None)
    require(source is not None,'Feature lacks original annotation metadata')
    subtype=source.get('subtype','unknown');basis='comment_or_ambiguous_annotation'
    allowed=False
    if subtype=='/Caret':
        allowed=True;basis='explicit_insertion_marker; context still distinguishes body proposal from instruction'
    else:
        obj=source.get('object_id');parent=source.get('reply_to_object_id')
        linked=[f for f in feedback if (parent is not None and f.get('object_id')==parent) or
                (obj is not None and f.get('reply_to_object_id')==obj)]
        if any(f.get('subtype')=='/StrikeOut' for f in linked):
            allowed=True;basis='explicit_reply_linked_replacement; contextual body judgment required'
        norm=lambda s:' '.join(str(s).split())
        marked=norm(source.get('marked_text',''))
        if subtype=='/Highlight' and any(len(norm(c.get('original','')))>20 and
            norm(c['original']) in marked and feature['source_quote'] in c.get('mentor_proposal','')
            for c in record.get('language_choices',[])):
            allowed=True;basis='highlighted_before_span_paired_with_direct_replacement_proposal; context required'
    if feature['evidence_kind'] in {'editorial_instruction','deletion'}:allowed=False
    return {'annotation_subtype':subtype,'annotation_index':source.get('annotation_index'),
        'object_id':source.get('object_id'),'body_form_allowed':allowed,'basis':basis,
        'source_role_limit':'Insertion/replacement candidate, not author adoption; ordinary comments support actions only.'}

def build_snapshot(source,destination,pilot=None,provenance=None):
    source=Path(source).resolve();dest=Path(destination).resolve()
    require('private' in dest.parts and not dest.exists(),'New private snapshot required')
    for name,digest in read(source/'FREEZE.json')['files'].items():
        require(sha(source/name)==digest,'Source snapshot changed')
    records=read(source/'records.json');by_id={r['id']:r for r in records}
    episodes={e['id']:e for e in read(source/'episodes.json')}
    pilot=pilot or []
    require(len({r['expression_id'] for r in pilot})==len(pilot),'Duplicate pilot record')
    overrides={r['expression_id']:r for r in pilot}
    require(overrides.keys()<=by_id.keys(),'Pilot cites unknown source')
    coverage=[];enhanced=[]
    for record in records:
        features,held=derive(record)
        disposition='reused_language_choices' if features else 'operation_only_existing_record'
        if record['id'] in overrides:
            row=overrides[record['id']]
            require(row.get('status') in {'language_features','operation_only','held'} and row.get('reason'),'Incomplete pilot decision')
            features=row.get('features',[])
            if row['status']=='held':require(not features,'Held pilot features cannot enter runtime')
            disposition='pilot_'+row['status']
        require(len({f['id'] for f in features})==len(features),'Duplicate feature ID')
        admitted=[]
        for f in features:
            check_feature(f,record)
            if episodes:
                admission=body_evidence(f,record,episodes);f={**f,'body_evidence':admission}
                if not admission['body_form_allowed'] and f['evidence_kind']!='deletion':
                    if f['kind'] in {'lexical','syntax','qualification','transition','unclassified'}:
                        held.append({'feature_id':f['id'],'reason':'No explicit body insertion/replacement evidence; comment wording cannot supply manuscript language.'})
                        continue
                    f['evidence_kind']='editorial_instruction'
                    f['frame']=''
            admitted.append(f)
        features=admitted
        if record['id'] in overrides and not any(
                f.get('body_evidence',{}).get('body_form_allowed') or f['evidence_kind']=='deletion' for f in features):
            disposition='pilot_operation_only_source_role_corrected'
        elif not features:
            disposition='operation_only_existing_record'
        enhanced.append({**record,'language_features':features,'language_feature_status':disposition})
        coverage.append({'expression_id':record['id'],'status':disposition,'feature_ids':[f['id'] for f in features],
            'held_choices':held,'reason':overrides.get(record['id'],{}).get('reason',
            'Reuse frozen learned roles, operations and exact attributed spans; no new semantic or mentor-preference certification.')})
    shutil.copytree(source,dest)
    write(dest/'records.json',enhanced)
    write(dest/'language_features_coverage.json',coverage)
    manifest=read(dest/'manifest.json')
    manifest.update(expression_realization=1,language_feature_count=sum(len(r['language_features']) for r in enhanced),
        language_feature_parent_sha256=sha(source/'FREEZE.json'),language_feature_provenance=provenance or {},
        language_feature_limit='Full inventory coverage; reused choices require contextual genre/fit review. Pilot enrichment is separately identified. No global mentor-style certification.')
    write(dest/'manifest.json',manifest)
    freeze=read(source/'FREEZE.json');names=set(freeze['files'])|{'language_features_coverage.json'}
    write(dest/'FREEZE.json',{'files':{n:sha(dest/n) for n in sorted(names)}})
    return {'records':len(records),'features':manifest['language_feature_count'],
            'pilot':len(pilot),'held_choices':sum(len(r['held_choices']) for r in coverage)}

def route(library,items,top_k=2):
    """Language-task/function retrieval, followed by mandatory contextual model judgment."""
    import expression_runtime as expression
    records=read(Path(library)/'records.json');links=[]
    import public_expression as public
    if read(Path(library)/'manifest.json').get('role') in public.ROLES:
        records=expression.view(library,[r['id'] for r in records])['records']
    for item in items:
        if item.get('finding_type')=='surface':continue
        task=' '.join(str(item.get(k,'')) for k in ['title','reader_task','relation','gap','closure_goal','current_order','proposed_order','action'])
        query=expression.tokens(task);candidates=[]
        for r in records:
            features=[f for f in r.get('language_features',[]) if
                f.get('body_evidence',{}).get('body_form_allowed') or f.get('evidence_kind')=='deletion']
            if not features:continue
            functions=expression.tokens(' '.join(str(f.get(k,'')) for f in features for k in ['function','operation']))
            tasks=expression.tokens(str(r['section_task'])+' '+str(r['changed_relationship']))
            fmatch=sorted(query & functions);tmatch=sorted(query & tasks)
            if not fmatch:continue
            candidates.append({'record_id':r['id'],'score':3*len(fmatch)+len(tmatch),
                'function_matches':fmatch,'task_matches':tmatch,'basis':'post_freeze_language_task'})
        candidates.sort(key=lambda x:(-x['score'],x['record_id']))
        for n,r in enumerate(candidates):r['selected']=n<top_k
        chosen=[r['record_id'] for r in candidates if r['selected']]
        links.append({'verified_id':item['id'],'expression_ids':chosen,
            'scope':'post-freeze wording retrieval, not original discovery',
            'retrieval':{'version':1,'top_k':top_k,'assignments':{'draft':{'record_ids':chosen,'candidates':candidates}}}})
    return links

def allowed_sources(evidence,verified_ids):
    used=set();transfers={r['id']:r for r in evidence.get('writing_transfers',[])}
    for row in evidence.get('raw_to_final',[]):
        if set(row['final_ids']) & set(verified_ids):
            used.update(transfers[t]['source_id'] for t in row.get('writing_transfer_ids',[])
                        if t in transfers and transfers[t]['source_kind']=='mentor_expression')
    for row in evidence.get('draft_expression_links',[]):
        if row['verified_id'] in verified_ids:used.update(row['expression_ids'])
    import expression_runtime as expression
    available={r['id']:r for r in evidence.get('expression_sources',{}).get('records',[])}
    return expression.admitted_closure(available,used)

def validate_draft(response,evidence):
    if not evidence.get('expression_realization'):return {'status':'legacy_contract'}
    actions=response.get('revision_actions',[]);rows=response.get('language_realizations')
    labels=[a.get('draft_label') for a in actions]
    require(actions and all(meaningful(x) for x in labels) and len(labels)==len(set(labels)),'Unique draft labels required')
    require(isinstance(rows,list) and len(rows)==len(labels) and {r.get('draft_label') for r in rows}==set(labels),
        'Language realization group coverage mismatch')
    action_map={a['draft_label']:a for a in actions}
    records={r['id']:r for r in evidence['expression_sources']['records']}
    report=response['report_markdown'];used_count=0
    for row in rows:
        action=action_map[row['draft_label']]
        require(set(row.get('verified_ids',[]))==set(action['verified_ids']),'Language realization requirement mismatch')
        require(row.get('scope') in {'prose','action_only','no_rewrite'} and meaningful(row.get('reason')),'Language realization scope/reason')
        passages=row.get('passages');require(isinstance(passages,list),'Missing replacement passages')
        require(len({p.get('id') for p in passages})==len(passages),'Duplicate passage IDs')
        if row['scope']=='prose':require(passages,'Prose realization without actual prose')
        else:require(not passages,'Action-only realization invents a replacement passage')
        for p in passages:
            require(meaningful(p.get('id')) and meaningful(p.get('text')) and p['text'] in report,
                'Realization passage absent from actual report')
        decisions=row.get('feature_decisions');require(isinstance(decisions,list),'Missing feature decisions')
        require(len({(f.get('expression_id'),f.get('feature_id')) for f in decisions})==len(decisions),'Duplicate feature decision')
        allowed=allowed_sources(evidence,row['verified_ids']);used=0
        for f in decisions:
            require(f.get('expression_id') in allowed,'Realization cites unrelated Expression')
            record=records[f['expression_id']]
            features={v['id']:v for v in record.get('language_features',[])}
            require(f.get('feature_id') in features,'Realization cites unknown/held feature')
            source=features[f['feature_id']]
            import public_expression as public
            if public.is_public(record):check_feature(source,record)
            require(f.get('evidence_kind') in EVIDENCE_KINDS-{'mentor_excerpt_unclassified'},'Source genre needs contextual judgment')
            require(f.get('source_ref')==source['source_ref'] and f.get('source_quote')==source['source_quote'],
                'Realization changed source feature evidence')
            if source['evidence_kind']!='mentor_excerpt_unclassified':
                require(f['evidence_kind']==source['evidence_kind'],'Realization changed established source genre')
            if f['evidence_kind']=='deletion':
                require(source['evidence_kind']=='deletion','Positive mentor annotation cannot be relabeled deleted author text')
            require(f.get('decision') in {'use','adapt','not_applicable'},'Invalid feature decision')
            require(f.get('realization_type') in {'language_form','language_edit','editorial_operation'},'Missing language realization type')
            if f['evidence_kind']=='analytical_operation':
                require(f['realization_type']=='editorial_operation','Analytical account is an editorial operation, not mentor wording or deletion text')
            if f['decision']!='not_applicable':
                if f['realization_type']=='language_form':
                    require(source.get('body_evidence',{}).get('body_form_allowed') and
                            f['evidence_kind'] in {'mentor_prose','mentor_fragment'},
                            'Comment cannot supply manuscript wording/syntax')
                if f['realization_type']=='language_edit':
                    require(f['evidence_kind']=='deletion','Positive comment wording is not a deletion edit')
            keys=['requested_feature','reason']
            if f['decision']!='not_applicable':
                keys+=['realization_explanation','preserved_meaning','adaptations']
            for k in keys:
                require(account(f.get(k)),'Missing feature realization '+k)
            if f.get('claim_extent','full')=='partial':
                require(f['decision']=='adapt' and meaningful(f.get('claimed_operation')) and
                    meaningful(f.get('source_operation_quote')) and f['source_operation_quote'] in source['operation'],
                    'Partial adoption needs a source-bound operation subset')
            quote=f.get('target_quote','')
            if f['decision']=='not_applicable':require(quote=='','Unused feature claims target realization')
            else:
                require(row['scope']!='no_rewrite','No-rewrite group claims applied style')
                target=[p['text'] for p in passages] if row['scope']=='prose' else [report]
                require(meaningful(quote) and any(quote in t for t in target),
                    'Feature not realized in actual replacement prose/action')
                used+=1
        expected='used' if used else 'no_rewrite' if row['scope']=='no_rewrite' else 'no_match'
        require(row.get('source_disposition')==expected,'False language use disposition')
        used_count+=used
    return {'status':'record_links_validated','groups':len(rows),'used_features':used_count,
        'semantic_correctness_verified':False}

def validate_review(response,evidence,review,report_text=None):
    validate_draft(response,evidence)
    require(meaningful(review.get('reviewer')),'Missing realization reviewer')
    groups=review.get('groups',[]);drafts=response['language_realizations']
    require(len(groups)==len(drafts) and {r.get('draft_label') for r in groups}=={d['draft_label'] for d in drafts},
        'Final realization review coverage mismatch')
    by_label={g['draft_label']:g for g in groups}
    for draft in drafts:
        validate_group(draft,by_label[draft['draft_label']],report_text)
    return {'status':'records_validated','semantic_correctness_verified':False}


def validate_group(draft,group,report_text=None):
    if report_text is not None:
        for p in draft['passages']:require(p['text'] in report_text,'Final realized passage changed')
    for key in ['meaning','naturalness']:
        require(group.get(key,{}).get('status')=='pass' and meaningful(group[key].get('reason')),
            'Final language '+key+' review failed or unfinished')
    used={(f['expression_id'],f['feature_id']) for f in draft['feature_decisions'] if f['decision']!='not_applicable'}
    results=group.get('feature_results',[])
    require(len(results)==len(used) and {(r.get('expression_id'),r.get('feature_id')) for r in results}==used,
        'Final feature review coverage mismatch')
    decisions={(f['expression_id'],f['feature_id']):f for f in draft['feature_decisions']}
    for result in results:
        decision=decisions[(result['expression_id'],result['feature_id'])]
        if decision.get('claim_extent','full')=='partial':
            require(result.get('status')=='partial' and result.get('covered_operation')==decision['claimed_operation'] and meaningful(result.get('reason')),'Partial feature claim lacks actual subset review')
        else:
            require(result.get('status')=='confirmed' and meaningful(result.get('reason')),'Final feature realization rejected or unfinished')
    nonuse={(f['expression_id'],f['feature_id']) for f in draft['feature_decisions'] if f['decision']=='not_applicable'}
    for result in group.get('nonuse_results',[]):
        require((result.get('expression_id'),result.get('feature_id')) in nonuse and result.get('reason'),'Nonuse result mislabels a claimed realization')
    return {'status':'records_validated','semantic_correctness_verified':False}

def validate_delivery_binding(binding,report_text):
    """Called by existing final-text ledger; hashes bind the reviewed draft and sources."""
    for key in ['response','evidence']:
        ref=binding.get(key,{})
        require(ref.get('path') and ref.get('sha256')==sha(ref['path']),'Stale realization '+key+' binding')
    return validate_review(read(binding['response']['path']),read(binding['evidence']['path']),
                           binding.get('review',{}),report_text)


PARTIAL_INSTRUCTIONS = "Partial adaptation is optional: claim_extent=partial, claimed_operation and a literal source_operation_quote bind only the adopted operation. Its final result is status=partial with covered_operation matching that claim; do not call a whole compound source feature confirmed. Explicit nonuse results stay separate in nonuse_results. Equivalent style or uncertain quality benefit does not prevent a supported optional adaptation."
