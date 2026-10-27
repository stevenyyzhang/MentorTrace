"""Source-to-editorial-decision accounting. No model calls or corpus promotion.

These checks establish links and recorded scope, not semantic correctness,
mentor acceptance, reader benefit, or causal contribution.
"""
import argparse
import hashlib
import json
from pathlib import Path


SCHEMA = '''Return writing_transfers:[] alongside ordinary checks/findings. Each record is
{id:"STAGE:W1",source_kind:"published_case|advisor_concern|manuscript",source_id,
source_excerpt,learned_distinction,scope:"sentence|paragraph|argument_unit|section|cross_section|whole_paper",
target_anchors:[],reader_task,current_handling,decision:"keep|required_repair|optional_improvement|unknown|not_applicable|unfinished",
proposed_action,preserved_dependencies,check_ids:[],finding_ids:[],suggestion_ids:[],limits}.
source_excerpt is a short exact excerpt from the supplied source relation/sentence-role account
or a concern's six decision fields; it is an excerpt of an ANALYST SUMMARY, not a mentor quotation.
Manuscript-only records use source_id="manuscript", source_excerpt="". Explain the distinction
learned, its task/conditions in this manuscript, what the existing passage already does, and the
specific action or reason to keep it. Use concise evidence accounts, not hidden deliberation.
Account for every selected Reader case (including keep/nonmatch), and link every organization
suggestion to at least one transfer record; a manuscript-only proposal is legitimate. Several
targets may use one source, and several sources may support one proposal; preserve these links.
Advisor: add writing_scope:"editorial|content_only|undetermined" to each existing card_disposition.
Editorial includes selection, emphasis, compression, paragraph roles, explanations and handoffs,
not just moves. For each linked editorial card provide a transfer; content-only checks need none.
Use unknown/unfinished when evidence/inspection is missing, never content_only as a fallback.
For required/optional decisions link the actual finding/suggestion and its supporting checks.
Other decisions have no output IDs. A kept/nonmatching example is useful learning, not a defect.
Do not add a finding per case, mimic wording, assume mentor acceptance, or turn readability into
technical invalidity. A published case illustrates a source arrangement; it proves no mentor preference.
'''

SCOPES = {'sentence', 'paragraph', 'argument_unit', 'section', 'cross_section', 'whole_paper'}
DECISIONS = {'keep', 'required_repair', 'optional_improvement', 'unknown', 'not_applicable', 'unfinished'}
FIELDS = ['core_question', 'new_manuscript_check', 'relationship_to_check',
          'historically_insufficient_response', 'potentially_sufficient_response', 'applicability_boundary']


def require(condition, message):
    if not condition:
        raise ValueError(message)


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def source_texts(kind, record, excerpt_basis=None):
    if kind == 'mentor_expression':
        import public_expression as public
        if public.is_public(record):return public.excerpt_texts(record,excerpt_basis)
        return [t['text'] for t in record['mentor_texts']] + [t['text'] for t in record.get('marked_texts', [])]
    if kind == 'advisor_concern':
        return [record[field]['text'] for field in FIELDS]
    summary = record['full_case']
    summary_texts=list(strings({key: summary.get(key) for key in
                         ['reader_task', 'context_notes', 'sentence_roles', 'full_relation_chain', 'reader_after']}))
    original_texts=[p['text'] for p in record.get('source_passages',{}).get('pages',[])]
    if excerpt_basis=='analyst_summary':return summary_texts
    if excerpt_basis=='original_page_text':return original_texts
    return summary_texts+original_texts


def sources(context):
    result = {('advisor_concern', c['id']): c for c in context.get('cards', [])}
    result.update({('published_case', c['case_id']): c for c in
                   context.get('goodpaper_cases', {}).get('complete_cases', []) if 'full_case' in c})
    result.update({('mentor_expression', r['id']):r for r in context.get('expression_sources',{}).get('records',[])})
    return result


def validate(stage, response, context, pages, anchor):
    rows = response.get('writing_transfers')
    require(isinstance(rows, list), 'Missing writing transfer records')
    require(len({r['id'] for r in rows}) == len(rows), 'Duplicate writing transfer ID')
    available = sources(context)
    checks = {c['id']: c for c in response.get('checks', [])}
    findings = {f['id']: f for f in response['findings']}
    suggestions = {s['id']: s for s in response.get('organization_suggestions', [])}
    seen, covered = set(), set()
    for row in rows:
        require(row['id'].startswith(stage + ':W'), 'Writing transfer namespace')
        key = (row.get('source_kind'), row.get('source_id'))
        import advisor_brief
        if advisor_brief.validate(row, context, anchor, pages):
            seen.add(key)
            continue
        if key == ('manuscript', 'manuscript'):
            require(row.get('source_excerpt') == '', 'Manuscript transfer cannot invent a historical excerpt')
        else:
            require(key in available, 'Writing transfer cites an unsupplied source')
            excerpt = row.get('source_excerpt')
            excerpt_basis=None
            if key[0]=='published_case' and available[key].get('source_passages'):
                excerpt_basis=row.get('excerpt_basis')
                require(excerpt_basis in {'analyst_summary','original_page_text'}, 'Case transfer must identify excerpt origin')
            if key[0]=='mentor_expression':
                import public_expression as public
                if context.get('advisor_guidance')==1:
                    import advisor_guidance
                    basis=row.get('expression_excerpt_basis',{})
                    require(not (basis.get('kind')=='analytical_account' and basis.get('field')=='operations')
                            or advisor_guidance.operation_excerpt_visible(available[key],excerpt),
                            'Canonical guidance cannot be quoted as original operations')
                if context.get('advisor_efficiency') == 1:
                    import advisor_efficiency
                    basis=row.get('expression_excerpt_basis',{})
                    require(not (basis.get('kind')=='analytical_account' and basis.get('field') in advisor_efficiency.LOCAL_FIELDS),
                            'Transfer cites a narrative field not supplied in economical view')
                if public.is_public(available[key]):
                    public.validate_excerpt(available[key],row)
                    excerpt_basis=row['expression_excerpt_basis']
            require(isinstance(excerpt, str) and excerpt.strip() and
                    any(excerpt in text for text in source_texts(key[0], available[key],excerpt_basis)),
                    'Writing transfer excerpt absent from supplied source account')
            seen.add(key)
        import advisor_results
        valid_scope=advisor_results.nonempty_text(row.get('scope')) if context.get('advisor_shared_results') else row.get('scope') in SCOPES
        require(valid_scope and row.get('decision') in DECISIONS, 'Invalid writing transfer scope/decision')
        for field in ['learned_distinction', 'reader_task', 'current_handling', 'proposed_action', 'preserved_dependencies', 'limits']:
            if context.get('advisor_shared_results') and field=='preserved_dependencies':
                require(advisor_results.dependencies_valid(row.get(field)), 'Incomplete writing transfer: ' + field)
            else:require(isinstance(row.get(field), str) and row[field].strip(), 'Incomplete writing transfer: ' + field)
        for field in ['target_anchors', 'check_ids', 'finding_ids', 'suggestion_ids']:
            require(isinstance(row.get(field), list), 'Missing writing transfer list: ' + field)
        for item in row['target_anchors']:
            anchor(item, pages)
        cids, fids, sids = (set(row[k]) for k in ['check_ids', 'finding_ids', 'suggestion_ids'])
        require(cids <= checks.keys() and fids <= findings.keys() and sids <= suggestions.keys(), 'Unknown writing transfer output/check')
        if row['decision'] not in {'not_applicable', 'unfinished'}:
            require(row['target_anchors'] and cids, 'Applied writing transfer needs anchored checks')
        if key[0] == 'advisor_concern':
            linked=any(key[1] in checks[c]['card_ids'] for c in cids)
            explicit_nonmatch=(row['decision']=='not_applicable' and not cids and bool(row['target_anchors'])
                and any(d.get('card_id')==key[1] and d.get('state')=='not_applicable'
                        and isinstance(d.get('reason'),str) and d['reason'].strip()
                        for d in response.get('card_dispositions',[])))
            require(linked or explicit_nonmatch, 'Concern transfer not used by its linked checks or explicit anchored nonmatch')
        for output in [findings[f] for f in fids] + [suggestions[s] for s in sids]:
            require(cids & set(output['check_ids']), 'Writing transfer disconnected from output evidence')
        if row['decision'] == 'required_repair':
            require(fids and not sids, 'Required writing repair needs finding IDs only')
        elif row['decision'] == 'optional_improvement':
            require(sids and not fids, 'Optional writing improvement needs suggestion IDs only')
        else:
            require(not fids and not sids, 'Non-repair transfer cannot assert outputs')
        covered.update(sids)
    require(covered == suggestions.keys(), 'Organization suggestion missing writing transfer')
    if context.get('expression_version'):
        import expression_runtime as expression
        require({k for k in available if k[0]=='mentor_expression'} <= seen, 'Selected Expression has no transfer disposition')
        expression.validate_dispositions(response,context)
    if stage == 'reader':
        required = {key for key in available if key[0] == 'published_case'}
        require(required <= seen, 'Selected Reader case has no transfer disposition')
    else:
        for item in response.get('card_dispositions', []):
            require(item.get('writing_scope') in ({'editorial', 'content_only', 'undetermined','shared_analysis'} if context.get('advisor_shared_results') else {'editorial', 'content_only', 'undetermined'}), 'Missing Advisor writing scope')
            if item['state'] == 'linked' and item['writing_scope'] == 'editorial':
                require(('advisor_concern', item['card_id']) in seen, 'Linked editorial concern has no transfer record')


def follow(raw_id, merged, final):
    """Includes optional-to-required incorporation at either consolidation stage."""
    def outputs(document, item_id):
        rows = document.get('dispositions', []) + document.get('organization_dispositions', [])
        match = [row for row in rows if row['input_id'] == item_id]
        require(len(match) == 1, 'Missing/duplicate writing lineage disposition: ' + item_id)
        return match[0]['output_ids']
    return sorted({out for middle in outputs(merged, raw_id) for out in outputs(final, middle)})


def packet(run, workflow=None):
    """Reconstruct actual lineage. Never relabel legacy output as dev.4 learning."""
    if workflow is None:
        import mentortrace_v1 as workflow
    run = Path(run)
    read = workflow.read
    merged = read(run / 'calls/merge/response.json')
    final = read(run / 'calls/verify/response.json')
    cases = {}
    if workflow.goodpaper_enabled(run):
        workflow.verify_case_route(run)
        cases = {c['case_id']: c for c in workflow.goodpaper.selected_for_lane(
            run / 'inputs/goodpaper', read(run / 'case_route.json'), 'reader')['complete_cases']}
        if read(run/'inputs/protocol.json').get('case_passages_version'):
            selection=workflow.goodpaper.with_passages({'complete_cases':list(cases.values()),'same_task_companions':[]},run/'inputs/case_passages')
            cases={c['case_id']:c for c in selection['complete_cases']}
    cards = {c['id']: c for c in workflow.all_runtime_cards(run)}
    raw_sources, records = [], []
    used_cases, used_cards, used_expressions = set(), set(), set()
    protocol=read(run/'inputs/protocol.json')
    for stage in workflow.branch_stages(run):
        response = read(run / f'calls/{stage}/response.json')
        checks = {c['id']: c for c in response.get('checks', [])}
        transfers = response.get('writing_transfers', [])
        records.extend({'stage': stage, **r} for r in transfers)
        for item in response['findings'] + response.get('organization_suggestions', []):
            final_ids = follow(item['id'], merged, final)
            if not final_ids:
                continue
            linked_checks = [checks[cid] for cid in item.get('check_ids', [])]
            concern_ids = sorted({cid for check in linked_checks for cid in check.get('card_ids', [])})
            object_ids = {c.get('object_id', c.get('relation_id')) for c in linked_checks}
            # Legacy case_usage is object-level association, never precise action attribution.
            associated_cases = sorted({u['case_id'] for u in response.get('case_usage', [])
                                       if set(u.get('object_ids', [])) & object_ids and u['case_id'] in cases})
            linked_transfers = [r for r in transfers if item['id'] in r['finding_ids'] + r['suggestion_ids']]
            transfer_cases = {r['source_id'] for r in linked_transfers if r['source_kind'] == 'published_case'}
            used_expressions.update(r['source_id'] for r in linked_transfers if r['source_kind']=='mentor_expression')
            used_cards.update(concern_ids)
            used_cases.update(associated_cases)
            used_cases.update(transfer_cases)
            raw_sources.append({'raw_id': item['id'], 'stage': stage, 'final_ids': final_ids,
                                'raw_requirement': item, 'source_checks': linked_checks,
                                'advisor_card_ids': concern_ids, 'associated_case_ids': associated_cases,
                                'writing_transfer_ids': [r['id'] for r in linked_transfers],
                                'attribution_status': 'recorded_transfer_not_causal_proof' if linked_transfers else
                                'check_or_object_association_only; specific_writing_influence_unrecorded'})
    result = {'version': 1, 'source_protocol': protocol.get('writing_transfer', 0),
            'verified_sha256': workflow.sha(run / 'calls/verify/response.json'),
            'raw_to_final': raw_sources, 'writing_transfers': records,
            'reader_sources': [cases[cid] for cid in sorted(used_cases)],
            'advisor_sources': [cards[cid] for cid in sorted(used_cards)],
            'limits': 'Source associations and model-recorded transfers are not causal effects or mentor endorsement. '
                      'Legacy runs lack dev.4 transfer records. Source facts cannot supply missing target facts.'}
    if protocol.get('advisor_role_division'):result['advisor_role_division']=protocol['advisor_role_division']
    if protocol.get('advisor_expression_brief'):
        result['advisor_expression_brief']=1
        result['limits'] += ' Non-action Expressions received limited-depth brief assessment, not exhaustive per-case application audits.'
    if protocol.get('advisor_shared_results'):
        result['advisor_shared_results']=1
        result['advisor_analysis_id_maps']={stage:read(run/f'calls/{stage}/response.json').get('analysis_id_map',[]) for stage in workflow.branch_stages(run) if stage.startswith('supplement_')}
        result['context_concern_results']={stage:read(run/f'calls/{stage}/response.json').get('context_card_dispositions',[]) for stage in workflow.branch_stages(run) if stage.startswith('supplement_')}
        result['source_review_summaries']={stage:read(run/f'calls/{stage}/response.json').get('source_review_summary') for stage in workflow.branch_stages(run) if stage.startswith('supplement_')}
        result['limits'] += ' Shared manuscript analyses support explicit per-source decisions. Unknown/unfinished are unresolved; candidate associations not adopted are not certified as inspected.'
    if protocol.get('advisor_review_view'):
        result['advisor_review_view']=1
        result['limits'] += ' Review withheld drafting frames and permission metadata; drafting sources below are reloaded in full from frozen inputs, not reconstructed from the slim review view.'
    if protocol.get('advisor_efficiency'):
        result['advisor_efficiency']=1
        result['limits'] += ' Expression history narratives were withheld from review; explicit shared non-action judgments may cover several cases. Full local records are not proof all fields were reviewed.'
    if protocol.get('expression_version'):
        import expression_runtime as expression
        result['expression_version']=1
        draft_links=[]
        if protocol['expression_mode']=='draft_only':
            for item in final['findings']+final.get('organization_suggestions',[]):
                if item.get('finding_type')=='surface':continue
                linked=[r for r in raw_sources if item['id'] in r['final_ids']]
                cids=sorted({c for r in linked for c in r['advisor_card_ids']})
                task={'id':item['id'],'section_task':'verified passage repair',
                      'rhetorical_relation':' '.join(str(item.get(k,'')) for k in ['relation','gap','closure_goal','current_order','proposed_order']),
                      'retrieval_terms':[]}
                retrieval=expression.route(run/'inputs/expression',[task],{'draft':cids})
                eids=retrieval['assignments']['draft']['record_ids']
                used_expressions.update(eids)
                draft_links.append({'verified_id':item['id'],'expression_ids':eids,'retrieval':retrieval,
                                    'scope':'post-freeze drafting retrieval; not original discovery'})
        result['draft_expression_links']=draft_links
        result['expression_sources']=expression.view(run/'inputs/expression',used_expressions)
        if read(run/'inputs/expression/manifest.json').get('expression_realization'):
            import expression_realization as realization
            language_links=realization.route(run/'inputs/expression',
                final['findings']+final.get('organization_suggestions',[]))
            result['draft_expression_links']+=language_links
            used_expressions.update(eid for link in language_links for eid in link['expression_ids'])
            result['expression_sources']=expression.view(run/'inputs/expression',used_expressions)
            result['expression_realization']=1
    return result


DRAFT_SCHEMA = '''Also return revision_attribution:[{verified_id,report_excerpt,
basis:"target_analysis|published_case|advisor_concern|combined",case_ids:[],card_ids:[],
transfer_ids:[],use_explanation,target_support:[]}]. Account for every retained content/organization
item once (surface items may also be included). report_excerpt must be an exact substantive passage
of the actual report. Attribute a case/concern only if the supplied writing_evidence packet links it
to that final item; document the actual distinction used, not just the source ID. target_analysis
with empty source IDs is valid. target_support gives original manuscript anchors supporting the
action, not evidence borrowed from the source paper. Legacy check/object associations may guide
this NEW drafting pass but must not be called original discovery or established mentor preference.
Each target_support entry is an anchor object: {page:1,kind:"text",quote:"exact target text"}
or {page:1,kind:"image",description:"specific visible target location"}; do not use strings.
Set basis from the nonempty source-ID types actually used: no type means target_analysis,
one type means that source type, and two or more types means combined. Target manuscript
analysis is required for every action and does not count as an additional source type.
Do not expose private attribution fields in the author-facing report. Complete this accounting
alongside generation, then audit-proposals locally; subsequent report changes invalidate its hash.
'''

EXPRESSION_DRAFT_SCHEMA = DRAFT_SCHEMA.replace(
    'basis:"target_analysis|published_case|advisor_concern|combined",case_ids:[],card_ids:[],',
    'basis:"target_analysis|published_case|advisor_concern|mentor_expression|combined",case_ids:[],card_ids:[],expression_ids:[],expression_uses:[],')+'''
For each used Expression include expression_uses:[{expression_id,source_excerpt,borrowed_operation,
target_application,do_not_transfer}]. source_excerpt must quote the supplied actual mentor_texts
or marked_texts. Marked text is original manuscript wording deleted by the mentor, not mentor prose;
explain the specific selection/order/syntax/wording choice adopted and preserved target conditions.
The replacement itself is new model drafting, never a mentor quotation or mentor-approved text.
Use only Expression sources linked to this retained item through recorded transfers or the explicitly
marked post-freeze draft_expression_links. No extra discovery requirement may be added in drafting.
An explicitly admitted local_reference_bindings companion of a linked Expression may contribute
its complete source context; record its actual source ID and borrowing operation. Held bindings
never supply guidance. A companion connection is source context, not a new diagnosis or proof
that the mentor accepted a revision.
Target-only drafting remains valid; a supplied example is not a mandatory template.
'''
import public_expression as public_expression
EXPRESSION_DRAFT_SCHEMA += '\n'+public_expression.SCHEMA


def draft_schema(evidence):
    result = EXPRESSION_DRAFT_SCHEMA if evidence.get('expression_version') else DRAFT_SCHEMA
    if evidence.get('advisor_role_division'):
        result += '''\nConcern records justify requirements; Expression contributions identify concrete
realization choices. For linked transfers carrying expression_contribution, read their
actual adopted feature IDs and target comparison. Carry the useful supported operation
into the coordinated report/replacement where appropriate, rather than restating a
generic Concern as an additional problem. Source-count is not problem-count. Use only
features actually supported for that target and source genre; no forced phrase copying.
A transfer's declared contribution is not proof of actual realization in final prose:
record the actual operation used and verify it in the delivered passage. Preserve each
independently justified requirement when coordinating actions. Target-only drafting
remains valid where no source expression is suitable.\n'''
    return result


def review_schema(context):
    schema=SCHEMA
    if context.get('expression_version'):
        schema=SCHEMA.replace('published_case|advisor_concern|manuscript',
                              'published_case|advisor_concern|mentor_expression|manuscript').replace(
            'it is an excerpt of an ANALYST SUMMARY, not a mentor quotation.',
            'case/Concern excerpts quote analytical summaries; mentor_expression excerpts quote actual supplied mentor_texts or explicit marked_texts (original manuscript wording deleted by the mentor, not mentor prose).').replace(
            'Do not add a finding per case, mimic wording, assume mentor acceptance,',
            'Do not add a finding per case, copy source facts, assume mentor acceptance,')
    if any(c.get('source_passages') for c in context.get('goodpaper_cases',{}).get('complete_cases',[])):
        schema=schema.replace('it is an excerpt of an ANALYST SUMMARY, not a mentor quotation.',
            'case excerpts identify analyst_summary or original_page_text; Concern excerpts remain analyst abstractions. Neither is mentor wording.')
        schema+='\nPublished cases with source_passages require excerpt_basis:"analyst_summary|original_page_text" on their writing transfer. Quote exactly from that chosen layer and state the concrete source operation; do not mislabel an analyst reconstruction as original prose.'
    if any(public_expression.is_public(r) for r in context.get('expression_sources',{}).get('records',[])):
        schema+='\n'+public_expression.SCHEMA
    return schema


def draft_view(evidence):
    """Retain full connected knowledge once; raw audit duplicates stay on disk.

    The verified requirements and manuscript are already separate prompt inputs.
    Do not repeat every duplicate initial diagnosis/check under each final item.
    """
    fields = ['raw_id', 'stage', 'final_ids', 'advisor_card_ids', 'associated_case_ids',
              'writing_transfer_ids', 'attribution_status']
    linked_transfers = {tid for row in evidence['raw_to_final'] for tid in row['writing_transfer_ids']}
    result={**evidence, 'raw_to_final': [{k: row[k] for k in fields} for row in evidence['raw_to_final']],
            'writing_transfers': [r for r in evidence['writing_transfers'] if r['id'] in linked_transfers]}
    if 'draft_expression_links' in evidence:
        result['draft_expression_links']=[{**link,'retrieval':{**link['retrieval'],
            'assignments':{stage:{**assignment,'candidates':[r for r in assignment['candidates'] if r.get('selected')]}
                           for stage,assignment in link['retrieval']['assignments'].items()},
            'audit_projection':'Unselected candidate ranking rows remain in the frozen evidence file; complete selected sources and their actual selection records are supplied.'}}
            for link in evidence['draft_expression_links']]
    return result


def validate_proposals(response, evidence, final, manuscript, anchor):
    pages = {p['page']: p['text'] for p in manuscript}
    required = {f['id'] for f in final['findings'] if f.get('finding_type') != 'surface'}
    required.update(s['id'] for s in final.get('organization_suggestions', []))
    allowed = required | {f['id'] for f in final['findings']}
    rows = response.get('revision_attribution')
    require(isinstance(rows, list), 'Missing revision attribution')
    ids = [r['verified_id'] for r in rows]
    require(len(ids) == len(set(ids)) and required <= set(ids) <= allowed, 'Revision attribution coverage mismatch')
    transfer_by_id = {r['id']: r for r in evidence['writing_transfers']}
    for row in rows:
        linked = [r for r in evidence['raw_to_final'] if row['verified_id'] in r['final_ids']]
        tids = {tid for r in linked for tid in r['writing_transfer_ids']}
        cids = {cid for r in linked for cid in r['advisor_card_ids']}
        pids = {cid for r in linked for cid in r['associated_case_ids']}
        pids.update(transfer_by_id[t]['source_id'] for t in tids if transfer_by_id[t]['source_kind'] == 'published_case')
        eids={transfer_by_id[t]['source_id'] for t in tids if transfer_by_id[t]['source_kind']=='mentor_expression'}
        for link in evidence.get('draft_expression_links',[]):
            if link['verified_id']==row['verified_id']:eids.update(link['expression_ids'])
        if evidence.get('expression_version'):
            import expression_runtime as expression
            available={r['id']:r for r in evidence['expression_sources']['records']}
            eids=expression.admitted_closure(available,eids)
        require(set(row.get('expression_ids',[])) <= eids,'Revision attribution claims an unrelated Expression')
        require(set(row.get('case_ids', [])) <= pids and set(row.get('card_ids', [])) <= cids and
                set(row.get('transfer_ids', [])) <= tids, 'Revision attribution claims an unrelated source')
        basis = row.get('basis')
        if evidence.get('expression_version'):
            used=set(row.get('expression_ids',[]))
            require(used <= eids,'Revision attribution claims an unrelated Expression')
            uses=row.get('expression_uses')
            require(isinstance(uses,list) and len(uses)==len(used) and {u['expression_id'] for u in uses}==used,'Expression drafting use coverage')
            available={r['id']:r for r in evidence['expression_sources']['records']}
            for use in uses:
                if public_expression.is_public(available[use['expression_id']]):public_expression.validate_excerpt(available[use['expression_id']],use)
                require(any(use.get('source_excerpt') and use['source_excerpt'] in text for text in source_texts('mentor_expression', available[use['expression_id']])), 'Draft Expression excerpt absent')
                require(all(use.get(k) for k in ['borrowed_operation','target_application','do_not_transfer']), 'Draft Expression operation missing')
        active=[name for name,key in [('published_case','case_ids'),('advisor_concern','card_ids'),('mentor_expression','expression_ids')] if row.get(key)]
        require(basis==('combined' if len(active)>1 else active[0] if active else 'target_analysis'), 'Revision attribution basis mismatch')
        quote = row.get('report_excerpt', '')
        require(isinstance(quote, str) and any(c.isalnum() for c in quote) and quote in response['report_markdown'], 'Revision attribution lacks actual report excerpt')
        require(row.get('use_explanation') and row.get('target_support'), 'Revision attribution lacks use/support')
        for item in row['target_support']:
            anchor(item, pages)
    if evidence.get('expression_realization'):
        import expression_realization as realization
        realization.validate_draft(response,evidence)
    return {'status': 'passed_record_links_only', 'items': len(rows),
            'report_sha256': hashlib.sha256(response['report_markdown'].encode('utf-8')).hexdigest(),
            'limits': 'Separate semantic/factual and final-text preservation reviews remain required.'}


def main():
    import mentortrace_v1 as workflow
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('trace'); p.add_argument('--run', required=True, type=Path); p.add_argument('--out', required=True, type=Path)
    p = sub.add_parser('audit-proposals'); p.add_argument('--delivery', required=True, type=Path); p.add_argument('--response', required=True, type=Path)
    args = parser.parse_args()
    if args.command == 'trace':
        require(not args.out.exists(), 'Trace output already exists')
        require(workflow.next_request(args.run) is None, 'Diagnosis incomplete')
        workflow.save(args.out, packet(args.run, workflow))
        print(args.out)
    else:
        folder = args.delivery / 'inputs'
        workflow.verify_frozen(folder)
        result = validate_proposals(workflow.read(args.response), workflow.read(folder / 'writing_evidence.json'),
                                    workflow.read(folder / 'verified.json'), workflow.read(folder / 'paper/body.json'), workflow.anchor)
        result['response_sha256'] = workflow.sha(args.response)
        result['evidence_sha256'] = workflow.sha(folder / 'writing_evidence.json')
        print(workflow.dump(result))


if __name__ == '__main__':
    main()
