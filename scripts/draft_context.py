"""Select complete linked writing sources after diagnosis; never summarize evidence.

The frozen full inputs remain the audit/validation authority. Only known lineage
permits pruning. Unknown layouts or incomplete links retain the whole input.
"""
import copy
import hashlib
import json
import expression_runtime


INSTRUCTIONS = '''DRAFT INPUT SCOPE: All assigned verified requests remain complete.
Related verified targets supply dependency context, not extra assigned prose.
Writing sources are complete records selected by frozen target/transfer links,
including admitted transitive companions and private source episodes. Missing or
ambiguous lineage retains the full source view. This is not another source-ranking
or diagnosis pass. Full manuscript, page images, coverage and unresolved items stay.
Initial Advisor ID-remapping tables stay in the frozen audit, not this drafting input.
'''


def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode()).hexdigest()


def strings(value):
    if isinstance(value,str):yield value
    elif isinstance(value,list):
        for item in value:yield from strings(item)
    elif isinstance(value,dict):
        for item in value.values():yield from strings(item)


def targets(final):
    rows=final.get('findings',[])+final.get('organization_suggestions',[])
    rows += [r for r in final.get('candidate_reviews',[]) if r.get('status') in {'optional','author_confirmation'}]
    return {r.get('id',r.get('candidate_id')):r for r in rows}


def project(payload, full_payload=None):
    """Return a model view and local receipt. Never mutate or replace audit inputs."""
    original=full_payload or payload
    result=copy.deepcopy(payload)
    receipt={'version':1,'source_sha256':digest(original),'mode':'full',
             'removed_administration':[],'assigned_ids':[], 'dependency_ids':[]}
    if not payload.get('draft_context_v1'):
        receipt['reason']='Frozen legacy protocol'
        return result,receipt
    try:
        final=original['verified_review'];all_targets=targets(final)
        assigned=set(payload.get('draft_partition',{}).get('assigned_ids',targets(payload['verified_review'])))
        if not assigned<=set(all_targets):raise ValueError('Assigned target absent from full verified inventory')
        evidence=original['writing_evidence_linked_sources_not_target_facts']
        raw=evidence['raw_to_final'];transfers=evidence['writing_transfers']
        transfer_map={r['id']:r for r in transfers}
        if len(transfer_map)!=len(transfers):raise ValueError('Ambiguous transfer IDs')
        active=set(assigned)
        # Preserve explicit cross-target and shared-requirement dependencies. Do
        # not guess relevance from words, headings, pages or a top-k score.
        while True:
            before=set(active)
            for ident in list(active):
                active.update(set(strings(all_targets[ident])) & set(all_targets))
            for row in final.get('source_requirement_resolutions',[]):
                linked=set(row.get('output_ids',[])) & set(all_targets)
                if linked & active:active.update(linked)
            for row in final.get('editorial_selection',[]):
                linked=set(strings(row)) & set(all_targets)
                if linked & active:active.update(linked)
            linked_raw=[r for r in raw if set(r['final_ids']) & active]
            tids={i for r in linked_raw for i in r['writing_transfer_ids']}
            if not tids<=set(transfer_map):raise ValueError('Linked transfer missing')
            for r in linked_raw:active.update(set(r['final_ids']) & set(all_targets))
            # One transfer may support several original requirements that later
            # received separate verified IDs; preserve that coordinated context.
            for row in raw:
                if tids & set(row['writing_transfer_ids']):active.update(set(row['final_ids']) & set(all_targets))
            if active==before:break
        linked_raw=[r for r in raw if set(r['final_ids']) & active]
        tids={i for r in linked_raw for i in r['writing_transfer_ids']}
        selected_transfers=[r for r in transfers if r['id'] in tids]
        pids={i for r in linked_raw for i in r['associated_case_ids']}
        cids={i for r in linked_raw for i in r['advisor_card_ids']}
        eids=set()
        for row in selected_transfers:
            kind=row['source_kind'];sid=row['source_id']
            if kind=='published_case':pids.add(sid)
            elif kind=='advisor_concern':cids.add(sid)
            elif kind=='mentor_expression':eids.add(sid)
            elif kind=='manuscript':pass
            else:raise ValueError('Unknown transfer source kind')
        links=[r for r in evidence.get('draft_expression_links',[]) if r['verified_id'] in active]
        for row in links:eids.update(row['expression_ids'])
        view=copy.deepcopy(evidence)
        def select(field,wanted,id_field):
            records=evidence.get(field,[]);known={r[id_field] for r in records}
            if len(known)!=len(records) or not wanted<=known:raise ValueError('Incomplete/ambiguous '+field)
            return [copy.deepcopy(r) for r in records if r[id_field] in wanted]
        view['raw_to_final']=copy.deepcopy(linked_raw)
        view['writing_transfers']=copy.deepcopy(selected_transfers)
        view['reader_sources']=select('reader_sources',pids,'case_id')
        view['advisor_sources']=select('advisor_sources',cids,'id')
        if 'draft_expression_links' in evidence:view['draft_expression_links']=copy.deepcopy(links)
        if 'expression_sources' in evidence:
            source=evidence['expression_sources'];records=source['records'];by_id={r['id']:r for r in records}
            if len(by_id)!=len(records):raise ValueError('Ambiguous Expression IDs')
            eids=expression_runtime.admitted_closure(by_id,eids)
            chosen=[r for r in records if r['id'] in eids]
            episodes=source.get('episodes',[])
            if episodes or any(r.get('episode_ids') or r.get('context_episode_ids') for r in chosen):
                if any('episode_ids' not in r for r in chosen):raise ValueError('Private episode linkage unavailable')
                episode_ids={i for r in chosen for i in r['episode_ids']+r.get('context_episode_ids',[])}
                if not episode_ids<={r['id'] for r in episodes}:raise ValueError('Private episode missing')
                episodes=[r for r in episodes if r['id'] in episode_ids]
            view['expression_sources']={**copy.deepcopy(source),'records':copy.deepcopy(chosen),'episodes':copy.deepcopy(episodes)}
        elif eids:raise ValueError('Expression sources unavailable')
        # Remapping is already realized in raw_to_final/verified IDs. Keep actual
        # source judgments, summaries, limits and all uncertainty unchanged.
        removed=view.pop('advisor_analysis_id_maps',None)
        result['writing_evidence_linked_sources_not_target_facts']=view
        if full_payload is not None:
            related=active-assigned
            previous={r.get('id',r.get('candidate_id')):r for r in result.get('related_verified_targets',[])}
            previous.update({i:all_targets[i] for i in related})
            result['related_verified_targets']=[copy.deepcopy(previous[i]) for i in sorted(previous)]
        receipt.update(mode='linked_complete_sources',assigned_ids=sorted(assigned),dependency_ids=sorted(active-assigned),
                       retained_source_ids={'reader':sorted(pids),'concern':sorted(cids),'expression':sorted(eids)},
                       retained_raw_ids=[r['raw_id'] for r in linked_raw],retained_transfer_ids=sorted(tids),
                       preserved=['manuscript','coverage_and_pending','verified_review'])
        if removed is not None:receipt['removed_administration']=[{'field':'advisor_analysis_id_maps','sha256':digest(removed)}]
        # Part 1 owns preamble/usage metadata. Pending manuscript questions and
        # review judgments remain complete in every part.
        if payload.get('draft_partition',{}).get('part',1)>1:
            coverage=result.get('coverage_and_pending',{})
            for field in ['actual_call_settings','settings_status','knowledge_count','advisor_batches']:
                if field in coverage:
                    value=coverage.pop(field)
                    receipt['removed_administration'].append({'field':'coverage_and_pending.'+field,'sha256':digest(value),'owner':'draft part 1'})
            receipt['preserved']=['manuscript','verified_review','coverage questions, judgments and limits']
    except (KeyError,TypeError,ValueError) as exc:
        result=copy.deepcopy(payload)
        # A malformed or unfamiliar link never triggers guessed pruning or a
        # corrective model call. Retain the original full evidence for this part.
        result['writing_evidence_linked_sources_not_target_facts']=copy.deepcopy(original.get('writing_evidence_linked_sources_not_target_facts',{}))
        receipt.update(mode='full_fallback',reason=str(exc))
    receipt['projected_sha256']=digest(result)
    return result,receipt
