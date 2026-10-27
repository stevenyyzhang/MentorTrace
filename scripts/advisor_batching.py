"""Fixed source provenance with lossless cross-group capacity packing before review."""
import argparse
import copy
import json
import math
from collections import Counter
from pathlib import Path
from advisor_capacity import check_capacity, estimate

ROLE_INSTRUCTIONS = '''
ADVISOR SOURCE RESPONSIBILITIES (version 1, one combined review call):
Concern: test whether a manuscript requirement/relationship is adequately supported,
using its complete six fields, manuscript evidence, alternatives and boundaries.
Expression: compare the source's actual wording, syntax, qualification, transition,
sentence order or paragraph operation with the target; name its specific added
realization beyond any Concern requirement. An operation account is not mentor prose.
Do not turn a generic requirement already covered by Concern into another defect.
Do not count source matches/links as independent problems. Share a target check or
recommendation when the requirement is the same; retain all distinct source links.
Expressions can realize an evidenced necessary repair, independently offer a useful
expression improvement, or identify a local expression error with target evidence.
No Concern match is required for an Expression-only improvement/error. Do not use
a source sentence to establish a missing scientific fact or technical invalidity.
Use the original as baseline: a sufficient Concern can coexist with a useful optional
expression improvement; equivalent style, unsuitable conditions or no demonstrable
gain call for keep/not_applicable. Every source is inspected, no rewrite quota.
For EVERY mentor_expression writing_transfer add
expression_contribution:{role:"repair_realization|expression_improvement|expression_repair|no_change|unresolved",
feature_ids:[],supporting_concern_ids:[]}.
repair_realization means required_repair implementing an evidenced Concern check;
expression_repair means required_repair for a target-evidenced local expression error;
expression_improvement means optional_improvement; no_change means keep/not_applicable;
unresolved means unknown/unfinished. List actual adopted language_features IDs for
repairs/improvements when the source has features. Use only this record's IDs.
supporting_concern_ids cites supplied cards actually used by this transfer's linked
checks, not all historical associations. repair_realization needs at least one.
Use existing learned_distinction to identify the exact additional expression operation,
current_handling to compare the actual target, proposed_action for gain or reason to
keep, and limits/preserved_dependencies for conditions and facts. Do not repeat those
explanations in another new field. Keep source_use_dispositions for every active link;
reason_ref can share only an explanation that genuinely covers that particular use.
These records account for declared contributions; IDs and labels do not certify fit,
quality, mentor preference, adoption in final prose, or the truth of the target claim.
'''

INSTRUCTIONS = '''ADVISOR PACKET CONTRACT (overrides only batch accounting):
Only primary_card_ids require card_dispositions and primary Concern inspection.
Other supplied cards are complete context for Expression uses, not extra primary assignments.
Concern uses carry relation_kind: direct is an implementation candidate, conditional
is a partial/conditional association. Neither proves applicability in this manuscript.
Fresh rechecks can also mark uncertain: retain this active link and its complete Concern
context, examine the stated unresolved point, and never convert uncertainty into a defect.
Check conditional applicability and restrictions explicitly; do not force a matching defect.
relation_condition states a matched prerequisite or unresolved point from the library
comparison. Verify it against the manuscript and full source boundaries; it is not a finding.
Individually rechecked historical-only links remain in local provenance, not required uses.
Their Expressions are still fully supplied and require independent writing-transfer inspection.
Every supplied Expression still needs its complete writing_transfer disposition.
Only expression_tasks require expression_task_dispositions; context_only_tasks retain complete use context.
INPUT may use exact_shared_values_v1: definitions holds full values; data is the context.
Every {"$same":"D..."} stands for that exact value in definitions within THIS request.
{"$rows":{"columns":[...],"values":[...]}} is a list of full records: pair each row's
values with the column names in order. No fields or rows are skipped. Values may use $same.
Resolve references and same-record projections as complete evidence, not as external retrieval.
Only publication_permission and transport capacity bookkeeping are stored locally; evidence,
source status, acceptance uncertainty, conditions, restrictions and all manuscript text remain here.
This is ONE review pass over EVERY assigned source, never an applicability screening pass.
For EACH source_uses entry return source_use_dispositions:[{expression_id,target_kind,target_id,
status:"checked|unfinished",transfer_ids:[],reason OR reason_ref}]. reason_ref may be a linked
writing_transfer ID when its reader_task/current_handling/proposed_action/limits explicitly
cover this particular use. Write that
explanation once in the transfer; retain a separate reason for distinct use-specific reasoning.
Do not reuse a reason merely because source IDs match. Keep every distinct use, even if one source
has several Concern/task links. Checked uses link this Expression's writing_transfers; an unfinished
transfer cannot establish checked use. Do not infer a defect from a historical association.
For task uses, checked transfers must include an anchor on that task's actual target page.
public_language_features.$projection_of references complete fields of language_features in the
SAME record by zero-based index and keys. Resolve these exact references before judging.
No source, condition, quotation or manuscript passage is summarized or omitted. Mark unfinished
work explicitly; never shorten evidence or silently skip uses to fit the budget.
Expressions without Concern/task links are mandatory independent source inspections: locate
possible applications in the full manuscript and record applicability or non-applicability in
their writing_transfers. Lack of a retrieval match is not permission to skip them.'''


def project(context):
    import advisor_output
    result = advisor_output.project(context)
    for rec in result.get('expression_sources', {}).get('records', []):
        values, features = rec.get('public_language_features'), rec.get('language_features')
        if not isinstance(values, list) or not values or not isinstance(features, list):
            continue
        refs = []
        for value in values:
            matches = [i for i, f in enumerate(features) if all(f.get(k) == v and k in f for k, v in value.items())]
            if not matches:
                break
            refs.append(dict(index=matches[0], keys=list(value)))
        else:
            ref = {'$projection_of': 'language_features', 'items': refs}
            if len(json.dumps(ref)) < len(json.dumps(values)):
                rec['public_language_features'] = ref
    if inflate(result) != context:
        raise ValueError('Lossless projection failed')
    return result


def inflate(context):
    import advisor_output
    result = advisor_output.inflate(context)
    for rec in result.get('expression_sources', {}).get('records', []):
        value = rec.get('public_language_features')
        if isinstance(value, dict) and value.get('$projection_of') == 'language_features':
            rec['public_language_features'] = [{k: rec['language_features'][r['index']][k] for k in r['keys']} for r in value['items']]
    return result


def instructions(context):
    if not context.get('advisor_direct_fulltext'):
        return INSTRUCTIONS
    text = INSTRUCTIONS.replace('Only expression_tasks require expression_task_dispositions; context_only_tasks retain complete use context.\n', '')
    text = text.replace("For task uses, checked transfers must include an anchor on that task's actual target page.\n", '')
    text += '''
DIRECT FULL-MANUSCRIPT REVIEW: No preliminary task map, Reader/Expert object plan,
or earlier lane findings are supplied. Independently identify manuscript relations
from the complete Concern distinctions and Expression operations and boundaries.
Every Expression searches the full manuscript, including sentence, paragraph,
section and cross-section uses; Concern associations are additional prompts, never
the limit of its applications. A nonmatch needs an operation/condition-based reason,
not merely absence of matching words. Inspect source uses without forcing a defect.
Keep sufficient text, distinguish optional improvements, and explicitly mark work
that remains unknown or unfinished. Do not return expression_task_dispositions.
'''
    return text + (ROLE_INSTRUCTIONS if context.get('advisor_role_division') else '')


def validate_contributions(response, context):
    """Bind role/feature declarations to actual supplied sources and target checks."""
    from mentortrace_v1 import require
    records = {r['id']:r for r in context['expression_sources']['records']}
    cards = {c['id'] for c in context['cards']}
    checks = {c['id']:c for c in response.get('checks', [])}
    allowed = {'required_repair':{'repair_realization','expression_repair'},
               'optional_improvement':{'expression_improvement'},
               'keep':{'no_change'}, 'not_applicable':{'no_change'},
               'unknown':{'unresolved'}, 'unfinished':{'unresolved'}}
    for row in response.get('writing_transfers', []):
        if row['source_kind'] != 'mentor_expression': continue
        import advisor_brief
        if advisor_brief.validate(row, context): continue
        require(row['source_id'] in records, 'Expression contribution cites an unsupplied source')
        contribution = row.get('expression_contribution')
        require(isinstance(contribution,dict), 'Missing Expression contribution')
        require(contribution.get('role') in allowed.get(row.get('decision'),set()), 'Expression role/decision mismatch')
        feature_ids = contribution.get('feature_ids')
        supporting = contribution.get('supporting_concern_ids')
        require(isinstance(feature_ids,list) and all(isinstance(v,str) for v in feature_ids)
                and len(feature_ids)==len(set(feature_ids)), 'Invalid Expression feature IDs')
        require(isinstance(supporting,list) and all(isinstance(v,str) for v in supporting)
                and len(supporting)==len(set(supporting)) and set(supporting)<=cards, 'Invalid supporting Concern IDs')
        available = {f['id'] for f in records[row['source_id']].get('language_features', [])}
        require(set(feature_ids)<=available, 'Expression feature belongs to another or missing source')
        if row['decision'] in {'required_repair','optional_improvement'}:
            require(not available or feature_ids, 'Adopted Expression feature not identified')
        linked_cards = {cid for ident in row.get('check_ids', []) if ident in checks for cid in checks[ident]['card_ids']}
        require(set(supporting)<=linked_cards, 'Expression contribution lacks its supporting Concern check')
        if contribution['role']=='repair_realization':
            require(supporting, 'Repair realization needs an evidenced Concern')


def validate_uses(response, context):
    from mentortrace_v1 import require
    if context.get('advisor_role_division'): validate_contributions(response,context)
    if context.get('advisor_shared_results'):
        import advisor_results
        advisor_results.validate_uses(response,context)
        return
    expected = {(r['expression_id'], r['target_kind'], r['target_id']) for r in context['source_uses']}
    rows = response.get('source_use_dispositions', [])
    actual = [(r.get('expression_id'), r.get('target_kind'), r.get('target_id')) for r in rows]
    require(len(actual) == len(set(actual)) and set(actual) == expected, 'Expression use coverage missing/duplicated')
    transfers = {r['id']: r for r in response.get('writing_transfers', [])}
    tasks = {t['id']: t for t in context.get('expression_tasks', []) + context.get('context_only_tasks', [])}
    for row in rows:
        require(row.get('status') in {'checked', 'unfinished'}, 'Invalid use disposition')
        links = row.get('transfer_ids', [])
        require(isinstance(links, list) and len(links) == len(set(links)), 'Invalid use transfer links')
        require(all(t in transfers and transfers[t]['source_kind'] == 'mentor_expression' and
                    transfers[t]['source_id'] == row['expression_id'] for t in links), 'Use cites another Expression')
        require(isinstance(row.get('reason'), str) and row['reason'].strip() or
                row.get('reason_ref') in links, 'Use disposition lacks a reason or linked reason reference')
        if row['status'] == 'checked':
            require(links and all(transfers[t]['decision'] != 'unfinished' for t in links), 'Unchecked Expression use')
            if row['target_kind'] == 'task':
                pages = {a['page'] for a in tasks[row['target_id']]['anchors']}
                require(any(a['page'] in pages for t in links for a in transfers[t]['target_anchors']), 'Task use lacks target anchor')


def fixed_groups(root, cards, records):
    import mentortrace_v1 as m
    table = m.read(Path(root) / 'config/advisor-groups.json')
    for file, expected in table['corpus_sha256'].items():
        m.require(m.sha(Path(root) / file) == expected, 'Fixed group corpus changed')
    groups = table['groups']
    for field, available in [('concern_ids', cards), ('expression_ids', records)]:
        assigned = [i for g in groups for i in g[field]]
        m.require(len(assigned) == len(set(assigned)) and set(assigned) == set(available), 'Fixed group coverage differs from run corpus')
    return groups


def relation_index(root, records):
    import mentortrace_v1 as m
    table = m.read(Path(root) / 'config/expression-concern-links.json')
    for file, expected in table['corpus_sha256'].items():
        m.require(m.sha(Path(root) / file) == expected, 'Relation corpus changed')
    m.require(set(table['expression_ids']) == set(records), 'Relation record coverage differs')
    expected = {(eid, cid) for eid, r in records.items() for cid in r['concern_ids']}
    actual = [(r['expression_id'], r['concern_id']) for r in table['links']]
    m.require(len(actual) == len(set(actual)) and set(actual) == expected, 'Relation coverage differs')
    m.require(all(r['kind'] in {'direct','conditional','historical','uncertain'} for r in table['links']), 'Unknown relation kind')
    m.require(all(r.get('reason') and r.get('basis') in {'retained_feature_rechecked','fresh_retained_content_review'}
                  for r in table['links'] if r['kind'] == 'historical'), 'Historical link lacks recheck')
    if table.get('fresh_full_review'):
        m.require(all(r.get('basis') == 'fresh_retained_content_review' and r.get('reason') and
                      r.get('expression_evidence') and r.get('concern_evidence') and r.get('audit_id')
                      for r in table['links']), 'Incomplete fresh relation review provenance')
    return table


def split_group(units, build, render, policy, image_count, start_index):
    """Binary-fit indivisible source units against complete rendered prompts."""
    packets = []
    while units:
        stage = 'supplement_' + str(start_index + len(packets))
        lo, hi, best = 1, len(units), None
        while lo <= hi:
            count = (lo + hi) // 2
            context = build(units[:count])
            request = render(stage, context)
            budget = request.get('advisor_capacity') or estimate(request['prompt'], image_count, policy)
            if budget['fits']:
                best = (count, context, budget); lo = count + 1
            else:
                hi = count - 1
        if best is None:
            raise ValueError('One complete source and its dependencies/full manuscript exceed capacity. No material removed; no review submitted.')
        count, context, budget = best
        packets.append((stage, context, budget))
        units = units[count:]
    return packets


def ordered_expression_units(records, cards, uses):
    """Cluster shared full-card context; the 80-source locality window is not a batch size.

    Admitted companion components form indivisible units. No relevance decisions,
    records, links or capacity allowances are changed by this ordering heuristic.
    """
    import mentortrace_v1 as m
    parent = {eid: eid for eid in records}
    def find(eid):
        while parent[eid] != eid:
            parent[eid] = parent[parent[eid]]
            eid = parent[eid]
        return eid
    for eid, record in records.items():
        for link in record.get('local_reference_bindings', []):
            if link['status'] == 'admitted':
                other = link['expression_id']
                m.require(other in records, 'Missing admitted Expression companion')
                left, right = sorted((find(eid), find(other)))
                parent[right] = left
    components = {}
    for eid in sorted(records):
        components.setdefault(find(eid), []).append(eid)
    members = {key: tuple(value) for key, value in components.items()}
    links = {key: set() for key in members}
    for eid, kind, target in uses:
        if kind == 'concern':
            links[find(eid)].add(target)
    weights = {cid: len(json.dumps(card)) for cid, card in cards.items()}
    source_weights = {key: sum(len(json.dumps(records[e])) for e in es) for key, es in members.items()}
    remaining, ordered = set(members), []
    while remaining:
        seed = max(remaining, key=lambda e: (sum(weights[c] for c in links[e]), e))
        shared, count = set(), 0
        while remaining and count < 80:
            eid = seed if not count else max(remaining, key=lambda e: (
                sum(weights[c] for c in links[e] & shared) /
                (source_weights[e] + sum(weights[c] for c in links[e] - shared)),
                -sum(weights[c] for c in links[e] - shared), e))
            remaining.remove(eid)
            ordered.append(('E', members[eid]))
            count += len(members[eid]); shared.update(links[eid])
    return ordered


def workload(context, policy=None):
    """Transparent structural proxy; does not certify semantic review quality."""
    records = context['expression_sources']['records']
    features = sum(max(1, len(r.get('language_features', [])), len(r.get('operations', []))) for r in records)
    boundaries = 0
    for record in records:
        values = []
        for key in ['transfer_conditions', 'do_not_transfer', 'facts_and_qualifications', 'limits']:
            value = record.get(key, [])
            values.extend(value if isinstance(value, list) else [value])
        for feature in record.get('language_features', []):
            for key in ['conditions', 'do_not_transfer']:
                value = feature.get(key, [])
                values.extend(value if isinstance(value, list) else [value])
        boundaries += len({json.dumps(v, sort_keys=True, ensure_ascii=False) for v in values if v})
    primary = len(context['primary_card_ids'])
    extra = len(context['cards']) - primary
    uses = context['source_uses']
    kinds = Counter(u['relation_kind'] for u in uses)
    weight = (policy or {}).get('association_weight', 1)
    if not isinstance(weight, (int, float)) or isinstance(weight, bool) or not 0 <= weight <= 1:
        raise ValueError('Invalid candidate-association workload weight')
    score = 3*primary + features + .25*boundaries + weight*(len(uses) + .5*kinds['conditional'] + kinds['uncertain']) + .5*extra
    return dict(concerns=primary, context_concerns=extra, expressions=len(records), operations=features,
                boundaries=boundaries, uses=len(uses), conditional_uses=kinds['conditional'],
                uncertain_uses=kinds['uncertain'], complexity=score)


def check_workload(context, policy):
    result = workload(context, policy)
    if not all(result[key] <= value for key, value in policy['limits'].items()):
        raise ValueError('Complete Advisor packet exceeds frozen review workload limits; replan, never skip sources')
    return result


def plan_run(run, policy):
    import mentortrace_v1 as m
    protocol = m.read(Path(run) / 'inputs/protocol.json')
    if protocol.get('advisor_batching') or not protocol.get('advisor_direct_fulltext'):
        return _legacy_plan_run(run, policy)
    return _plan_direct(run, policy)


def _legacy_workload():
    # Preserve the policy used by direct runs created before automatic budgeting.
    return dict(version=1,name='balanced',limits=dict(concerns=50,expressions=110,
        operations=150,uses=180,complexity=700),
        formula='3*C + F + 0.25*B + U + 0.5*conditional_U + uncertain_U + 0.5*context_C',
        basis='Original balanced structural proxy; not model-measured difficulty or a quality guarantee.')


def _pack_direct_units(source_units,standalone,build,render,load_policy,*,backfill=False):
    """Whole source packing; no model, user selection or frozen-input mutations."""
    units=list(source_units);pending_c=list(standalone);packets=[]
    limits=load_policy['limits']
    target=load_policy.get('standalone_expression_target',limits.get('expressions',110))
    def fits(ctx):return all(workload(ctx,load_policy)[k]<=v for k,v in limits.items())
    while units or pending_c:
        remaining_e=sum(len(es) for _,es in units)
        share=min(limits['concerns']//2,math.ceil(len(pending_c)*target/max(1,remaining_e))) if units else limits['concerns']
        cs=pending_c[:max(1,share)] if pending_c else []
        stage='supplement_'+str(len(packets)+1)
        max_take=0;es=[]
        for _,members in units:
            trial=es+list(members)
            if not fits(build(trial,cs)):break
            es=trial;max_take+=1
        while True:
            es=[e for _,members in units[:max_take] for e in members]
            ctx=build(es,cs);budget=render(stage,ctx)['advisor_capacity']
            best=(max_take,es,ctx,budget) if budget['fits'] and fits(ctx) else None
            if best is None:
                lo,hi=0,max_take-1
                while lo<=hi:
                    take=(lo+hi)//2;trial=[e for _,members in units[:take] for e in members]
                    ctx=build(trial,cs);budget=render(stage,ctx)['advisor_capacity']
                    if budget['fits'] and fits(ctx):best=(take,trial,ctx,budget);lo=take+1
                    else:hi=take-1
            if best is not None and (best[0] or cs):break
            if cs:
                cs=cs[:len(cs)//2]
                if not max_take and units:max_take=1
            else:return None,'One complete source and its dependencies/full manuscript exceed capacity or workload'
        take,es,ctx,budget=best
        packets.append(dict(es=es,cs=cs,context=ctx,budget=budget))
        units=units[take:];pending_c=pending_c[len(cs):]
    if backfill:
        while len(packets)>1:
            light=min(range(len(packets)),key=lambda i:workload(packets[i]['context'],load_policy)['complexity'])
            options=[]
            for i,p in enumerate(packets):
                if i==light:continue
                q=packets[light];es=p['es']+q['es'];cs=p['cs']+q['cs'];ctx=build(es,cs)
                if fits(ctx):options.append((workload(ctx,load_policy)['complexity'],i,es,cs,ctx))
            combined=False
            for _,i,es,cs,ctx in sorted(options,key=lambda x:(x[0],x[1])):
                budget=render('supplement_'+str(i+1),ctx)['advisor_capacity']
                if budget['fits']:
                    packets[i]=dict(es=es,cs=cs,context=ctx,budget=budget)
                    del packets[light];combined=True;break
            if not combined:break
    result=[]
    for index,p in enumerate(packets,1):
        stage='supplement_'+str(index);ctx=p['context']
        budget=render(stage,ctx)['advisor_capacity']
        if not budget['fits']:return None,'Complete final packet exceeds capacity after stage renumbering'
        result.append((stage,ctx,budget,check_workload(ctx,load_policy)))
    if load_policy.get('max_batches') and len(result)>load_policy['max_batches']:
        return None,f"Constructed {len(result)} packets, above the {load_policy['max_batches']}-request budget"
    return result,''


def _plan_direct(run, policy):
    """Plan from complete frozen corpora, before any model call or object plan."""
    import mentortrace_v1 as m
    run = Path(run).resolve(); m.verify_frozen(run / 'inputs')
    protocol = m.read(run / 'inputs/protocol.json'); state = m.read(run / 'state.json')
    m.require(protocol.get('advisor_batching_pending'), 'New direct review requires pending planning')
    m.require(not state['completed'] and not state['pending_evidence'], 'Plan direct Advisor before any review lane')
    m.require(not (run / 'calls').exists() or not any((run / 'calls').iterdir()), 'Other stage already prepared; preserve this run')
    if protocol.get('advisor_batch_budget'):
        import advisor_budget
        load_config=m.read(run/'inputs/advisor_planning_policy.json')
        advisor_budget.candidates(load_config)
    else:load_config=_legacy_workload()
    cards = {r['id']: r for r in m.all_runtime_cards(run)}
    records = {r['id']: r for r in m.read(run / 'inputs/expression/records.json')}
    groups = fixed_groups(m.ROOT, cards, records)
    relations = relation_index(m.ROOT, records)
    historical = {(r['expression_id'], r['concern_id']) for r in relations['links'] if r['kind'] == 'historical'}
    active = [r for r in relations['links'] if r['kind'] != 'historical']
    selected_view = m.expression.view(run / 'inputs/expression', records)
    selected = {r['id']: r for r in selected_view['records']}
    m.require(set(selected) == set(records), 'Every public Expression must enter the complete run')
    uses = {(r['expression_id'], 'concern', r['concern_id']) for r in active}
    by_expression = {eid: [] for eid in selected}
    for row in sorted(active, key=lambda r:(r['expression_id'], r['concern_id'])):
        by_expression[row['expression_id']].append(dict(expression_id=row['expression_id'], target_kind='concern',
            target_id=row['concern_id'], relation_kind=row['kind'],
            relation_condition=row.get('condition', '') if row['kind'] in {'conditional','uncertain'} else ''))
    units = ordered_expression_units(selected, cards, uses)
    first_c = {}
    for _, members in units:
        for eid in members:
            for row in by_expression[eid]: first_c.setdefault(row['target_id'], eid)
    pending_c = sorted(set(cards) - set(first_c))
    stage = next(s for s in protocol['stages'] if s.startswith('supplement_'))
    common = m.context_for(run, stage)
    m.require('objects' not in common, 'Independent Advisor must not receive planning objects')
    common.pop('cards')
    source_meta = {k:copy.deepcopy(v) for k,v in selected_view.items() if k != 'records'}
    guidance_registry=None
    if protocol.get('advisor_guidance'):
        import advisor_guidance
        guidance_registry=m.read(run/'inputs/expression_guidance.json')
        advisor_guidance.validate(guidance_registry,list(selected.values()))
    def build(es, cs):
        chosen = set(es)
        primary = list(cs) + [c for c,e in first_c.items() if e in chosen]
        edges = [r for eid in es for r in by_expression[eid]]
        needed = set(primary) | {r['target_id'] for r in edges}
        context={**copy.deepcopy(common), 'advisor_batching':policy, 'primary_card_ids':primary,
                'cards':[cards[c] for c in sorted(needed)],
                'expression_sources':{**source_meta, 'records':[selected[e] for e in es]},
                'historical_concern_links':[list(p) for p in sorted(historical) if p[0] in chosen],
                'source_uses':edges}
        if guidance_registry is not None:context['expression_guidance']=advisor_guidance.subset(guidance_registry,es)
        return context
    def render(stage,ctx):return m.prepare_stage_request(run,stage,_context_override=ctx,_planning=True)
    if protocol.get('advisor_batch_budget'):
        def evaluate(choice):return _pack_direct_units(units,pending_c,build,render,choice,backfill=True)
        try:packets,load_policy,execution_budget,trials=advisor_budget.select(load_config,evaluate)
        except advisor_budget.PlanningBudgetError as error:
            m.save(run/'advisor_planning_failure.json',dict(status='unavailable_before_review',
                reason=str(error),candidates=error.trials,target_batches=load_config.get('preferred_max_batches',load_config.get('target_batches',load_config.get('max_batches'))),
                max_batches=load_config.get('max_batches'),model_calls=0,no_sources_removed=True,
                user_confirmation_required=False))
            raise
    else:
        load_policy=load_config
        packets,reason=_pack_direct_units(units,pending_c,build,render,load_policy)
        m.require(packets is not None,reason+'. No material removed; no review submitted.')
    def once(actual, expected, label):
        m.require(len(actual)==len(set(actual)) and set(actual)==set(expected), label+' loss/duplication')
    once([c for _,ctx,_,_ in packets for c in ctx['primary_card_ids']], cards, 'Concern')
    once([r['id'] for _,ctx,_,_ in packets for r in ctx['expression_sources']['records']], selected, 'Expression')
    once([(u['expression_id'],u['target_kind'],u['target_id']) for _,ctx,_,_ in packets for u in ctx['source_uses']], uses, 'Use')
    c_owner = {c:g['id'] for g in groups for c in g['concern_ids']}
    e_owner = {e:g['id'] for g in groups for e in g['expression_ids']}
    manifest = [dict(stage=s, primary_card_ids=ctx['primary_card_ids'],
        expression_ids=[r['id'] for r in ctx['expression_sources']['records']],
        fixed_groups=sorted({c_owner[c] for c in ctx['primary_card_ids']} | {e_owner[r['id']] for r in ctx['expression_sources']['records']}),
        capacity=budget, workload=load) for s,ctx,budget,load in packets]
    plan = dict(version=3, packing='direct_fulltext_capacity_workload_v1', groups=manifest,
        coverage=dict(concerns=len(cards),expressions=len(selected),tasks=0,uses=len(uses)),
        workload_policy=load_policy, model_calls=0, semantic_quality_verified=False,
        fixed_groups_sha256=m.sha(m.ROOT/'config/advisor-groups.json'), original_concern_links=len(relations['links']),
        relation_counts=dict(Counter(r['kind'] for r in relations['links'])))
    if protocol.get('advisor_role_division'):plan['role_division_version']=protocol['advisor_role_division']
    if protocol.get('advisor_output_contract'):plan['output_contract_version']=protocol['advisor_output_contract']
    if protocol.get('advisor_batch_budget'):
        plan.update(version=4,packing='direct_fulltext_adaptive_budget_v1',
                    execution_budget=execution_budget,planning_candidates=trials)
    # All validation precedes writes to frozen inputs. Existing frozen plans never migrate.
    m.save(run/'advisor_preparation_freeze.json',m.read(run/'inputs/FREEZE.json'))
    m.save(run/'inputs/expression_concern_links.json',relations)
    m.save(run/'inputs/advisor_workload.json',load_policy)
    m.save(run/'inputs/advisor_plan.json',plan)
    for stage,ctx,_,_ in packets: m.save(run/f'inputs/advisor_packets/{stage}.json',project(ctx))
    protocol['stages'] = ['objects','reader','technical'] + [s for s,_,_,_ in packets] + ['language','merge','verify']
    protocol.pop('advisor_batching_pending'); protocol['advisor_batching']=1
    protocol['advisor_capacity']=policy; protocol['advisor_workload']=load_policy
    if protocol.get('advisor_batch_budget'):protocol['advisor_request_budget']=execution_budget
    m.save(run/'inputs/protocol.json',protocol); m.freeze(run/'inputs')
    return plan


def _legacy_plan_run(run, policy):
    import mentortrace_v1 as m
    run = Path(run).resolve(); m.verify_frozen(run / 'inputs')
    protocol = m.read(run / 'inputs/protocol.json'); state = m.read(run / 'state.json')
    if protocol.get('advisor_batching'):
        m.require(protocol['advisor_capacity'] == policy, 'Frozen capacity changed; use a new run')
        return m.read(run / 'inputs/advisor_plan.json')
    m.require(protocol.get('advisor_batching_pending'), 'Legacy run preserved; create a v1.2 run for fixed-group batching')
    m.require(state['completed'] == ['advisor_tasks'] and not state['pending_evidence'],
              'Finish neutral Advisor task mapping, then plan before any review lane')
    for folder in (run / 'calls').iterdir():
        m.require(folder.name == 'advisor_tasks', 'Other stage already prepared; do not mutate this run')
    accepted = m.read(run / 'calls/advisor_tasks/record.json')
    for name in ['request', 'response', 'raw_response']:
        m.require(m.sha(run / f'calls/advisor_tasks/{name}.json') == accepted[name + '_sha256'], 'Accepted task map changed')
    cards = {r['id']: r for r in m.all_runtime_cards(run)}
    records = {r['id']: r for r in m.read(run / 'inputs/expression/records.json')}
    groups = fixed_groups(m.ROOT, cards, records)
    relations = relation_index(m.ROOT, records)
    relation_notes = {(r['expression_id'], r['concern_id']): r.get('condition','') for r in relations['links']}
    kinds = {(r['expression_id'], r['concern_id']): r['kind'] for r in relations['links']}
    historical = {pair for pair, kind in kinds.items() if kind == 'historical'}
    # Preserve original task retrieval and links, and include ALL unlinked Expressions too.
    old_stages = [s for s in protocol['stages'] if s.startswith('supplement_')]
    contexts = [m.context_for(run, s) for s in old_stages]
    tasks = {r['id']: r for c in contexts for r in c['expression_tasks']}
    selected = {r['id']: r for c in contexts for r in c['expression_sources']['records']}
    unlinked = {eid for eid, record in records.items() if not record['concern_ids']}
    selected.update({r['id']: r for r in m.expression.view(run / 'inputs/expression', unlinked)['records']})
    m.require(set(selected) == set(records), 'Every public Expression must enter the complete run')
    route = m.read(run / 'expression_route.json')
    uses = set()
    for assignment in route['assignments'].values():
        for row in assignment['candidates']:
            if row.get('selected'):
                for cid in row.get('concern_ids', []):
                    if (row['record_id'], cid) not in historical:
                        uses.add((row['record_id'], 'concern', cid))
                if row.get('task_id'): uses.add((row['record_id'], 'task', row['task_id']))
    m.require({(e,t) for e,k,t in uses if k == 'concern'} == set(kinds) - historical,
              'Active Expression-Concern use coverage differs from reviewed links')
    owner = {eid: g['id'] for g in groups for eid in g['expression_ids']}
    concern_owner = {cid: g['id'] for g in groups for cid in g['concern_ids']}
    expression_units = ordered_expression_units(selected, cards, uses)
    uses_by_expression = {eid: [] for eid in selected}
    for edge in sorted(uses): uses_by_expression[edge[0]].append(edge)
    first_c, first_t = {}, {}
    for _, members in expression_units:
        for eid in members:
            for _, kind, target in uses_by_expression[eid]:
                (first_c if kind == 'concern' else first_t).setdefault(target, eid)
    common = {k: copy.deepcopy(v) for k, v in contexts[0].items() if k not in {'cards', 'expression_sources', 'expression_tasks'}}
    source_meta = {k: copy.deepcopy(v) for k, v in contexts[0]['expression_sources'].items() if k != 'records'}
    def build(units):
        primary_e = [eid for kind, members in units if kind == 'E' for eid in members]
        primary_set = set(primary_e)
        primary_c = [ident for kind, ident in units if kind == 'C'] + [c for c,e in first_c.items() if e in primary_set]
        primary_t = [ident for kind, ident in units if kind == 'T'] + [t for t,e in first_t.items() if e in primary_set]
        edges = sorted(u for eid in primary_e for u in uses_by_expression[eid])
        needed_c = set(primary_c) | {t for _, kind, t in edges if kind == 'concern'}
        needed_t = {t for _, kind, t in edges if kind == 'task'} - set(primary_t)
        return {**copy.deepcopy(common), 'advisor_batching': policy, 'primary_card_ids': primary_c,
                'cards': [cards[c] for c in sorted(needed_c)],
                'expression_sources': {**source_meta, 'records': [selected[e] for e in primary_e]},
                'expression_tasks': [tasks[t] for t in primary_t],
                'context_only_tasks': [tasks[t] for t in sorted(needed_t)],
                'historical_concern_links': [list(pair) for pair in sorted(historical) if pair[0] in primary_e],
                'source_uses': [dict(expression_id=e, target_kind=k, target_id=t,
                                     relation_kind=kinds[(e,t)] if k == 'concern' else 'task',
                                     relation_condition=relation_notes[(e,t)] if k == 'concern' and kinds[(e,t)] in {'conditional','uncertain'} else '') for e, k, t in edges]}
    def render(stage, context):
        return m.prepare_stage_request(run, stage, _context_override=context, _planning=True)
    image_count = len(m.read(run / 'inputs/paper/manifest.json')['images'])
    units = [('C', c) for c in sorted(cards) if c not in first_c]
    units += [('T', t) for t in sorted(tasks) if t not in first_t]
    units += expression_units
    packets = split_group(units, build, render, policy, image_count, 1)
    manifest = []
    for stage, ctx, budget in packets:
        eids = [r['id'] for r in ctx['expression_sources']['records']]
        provenance = sorted({owner[e] for e in eids} | {concern_owner[c] for c in ctx['primary_card_ids']})
        manifest.append(dict(stage=stage, fixed_groups=provenance, primary_card_ids=ctx['primary_card_ids'],
                             expression_ids=eids, task_ids=[t['id'] for t in ctx['expression_tasks']], capacity=budget))
    def complete_once(actual, expected, label):
        m.require(len(actual) == len(set(actual)) and set(actual) == set(expected), label + ' loss/duplication')
    complete_once([c for _,ctx,_ in packets for c in ctx['primary_card_ids']], cards, 'Concern')
    complete_once([r['id'] for _,ctx,_ in packets for r in ctx['expression_sources']['records']], selected, 'Expression')
    complete_once([t['id'] for _,ctx,_ in packets for t in ctx['expression_tasks']], tasks, 'Task')
    complete_once([(u['expression_id'],u['target_kind'],u['target_id']) for _,ctx,_ in packets for u in ctx['source_uses']], uses, 'Use')
    # No writes to frozen inputs until every full packet fits. Preserve preparation provenance.
    m.save(run / 'advisor_preparation_freeze.json', m.read(run / 'inputs/FREEZE.json'))
    plan = dict(version=2, packing='cross_group_shared_concern_v1', groups=manifest, coverage=dict(concerns=len(cards), expressions=len(selected),
                tasks=len(tasks), uses=len(uses)), model_calls=0, semantic_quality_verified=False,
                original_route_sha256=m.sha(run / 'expression_route.json'),
                fixed_groups_sha256=m.sha(m.ROOT / 'config/advisor-groups.json'))
    plan['relation_counts'] = {kind: sum(v == kind for v in kinds.values()) for kind in ['direct','conditional','historical','uncertain']}
    plan['original_concern_links'] = len(kinds)
    m.save(run / 'inputs/expression_concern_links.json', relations)
    m.save(run / 'inputs/advisor_plan.json', plan)
    for stage, ctx, _ in packets: m.save(run / f'inputs/advisor_packets/{stage}.json', project(ctx))
    protocol['stages'] = ['advisor_tasks', 'objects', 'reader', 'technical'] + [s for s, _, _ in packets] + ['language', 'merge', 'verify']
    protocol.pop('advisor_batching_pending'); protocol['advisor_batching'] = 1; protocol['advisor_capacity'] = policy
    m.save(run / 'inputs/protocol.json', protocol); m.freeze(run / 'inputs')
    return plan


if __name__ == '__main__':
    from advisor_capacity import discover
    import mentortrace_v1 as m
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--model', required=True); parser.add_argument('--effort', required=True)
    args = parser.parse_args()
    pinned = args.run / 'automatic_capacity.json'
    policy = m.read(pinned) if pinned.exists() else discover(args.model, args.effort)
    m.require((policy['model'], policy['effort']) == (args.model, args.effort), 'Frozen model/effort differs')
    if not pinned.exists(): m.save(pinned, policy)
    print(json.dumps(plan_run(args.run, policy), ensure_ascii=False))
