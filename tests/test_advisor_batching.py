"""Offline batching/capacity regressions. No model generation or network calls."""
import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import advisor_batching as b
import advisor_capacity as capacity
import run_authorized_stage as runner
import test_expression as expression_fixture
from test_pipeline import m, answer
from test_writing_transfer import transfer


def policy(window=500000):
    return dict(version=1, model='fixture-model', effort='high', context_window=window,
                effective_context=window, output_reserve=10000, image_reserve_each=1000,
                system_reserve=1000, text_multiplier=1.25, token_method='utf8_upper_bound')


class Batching(unittest.TestCase):
    setUp = expression_fixture.Expression.setUp
    tearDown = expression_fixture.Expression.tearDown
    library = expression_fixture.Expression.library
    task_map = expression_fixture.Expression.task_map

    def prepared(self):
        self.library()
        # A source with no Concern link AND no lexical task match must still be sent.
        unlinked = copy.deepcopy(self.records[0]); unlinked['id'] = 'EXP2'
        unlinked.update(concern_ids=[], section_task='zebra', changed_relationship='zebra', retrieval_terms=['zebra'])
        m.save(self.lib / 'records.json', self.records + [unlinked]); m.freeze(self.lib)
        self.run = self.root / 'adaptive'
        m.create_run(self.root / 'paper', self.root / 'knowledge', self.run,
                     goodpaper_cases=False, expression_library=self.lib, adaptive_advisor=True)
        self.assertNotIn('advisor_tasks', m.read(self.run/'inputs/protocol.json')['stages'])

    def groups(self, *args):
        return [dict(id='G01', concern_ids=['T0', 'T1'], expression_ids=['EXP1']),
                dict(id='G02', concern_ids=['T2', 'T3'], expression_ids=['EXP2'])]

    def plan(self, budget=None):
        with patch.object(b, 'fixed_groups', self.groups), patch.object(b, 'relation_index', self.relations):
            return b.plan_run(self.run, budget or policy())

    def relations(self, root, records):
        return {'links': [dict(expression_id=e, concern_id=c, kind='direct') for e,r in records.items() for c in r['concern_ids']]}

    def test_all_sources_and_uses_survive_and_can_enter_pipeline(self):
        self.prepared()
        with self.assertRaisesRegex(ValueError, 'Plan full Advisor'):
            m.next_request(self.run)
        plan = self.plan()
        self.assertEqual(plan['coverage'], dict(concerns=4, expressions=2, tasks=0, uses=1))
        self.assertEqual(len(plan['groups']), 1)
        self.assertEqual(plan['groups'][0]['fixed_groups'], ['G01', 'G02'])
        self.assertFalse((self.run / 'calls/advisor_tasks').exists())
        self.assertEqual(self.plan(), plan)
        for stage in ['objects', 'reader', 'technical']:
            req = m.next_request(self.run); self.assertEqual(req['stage'], stage)
            m.accept_response(self.run, answer(stage, m.context_for(self.run, stage)))
        seen = []
        for group in plan['groups']:
            req = m.next_request(self.run); ctx = m.context_for(self.run, req['stage'])
            self.assertLessEqual(req['advisor_capacity']['total_reserved'], policy()['effective_context'])
            result = answer(req['stage'], ctx)
            result['card_dispositions'] = [d for d in result['card_dispositions'] if d['card_id'] in ctx['primary_card_ids']]
            for n, record in enumerate(ctx['expression_sources']['records']):
                seen.append(record['id'])
                result['writing_transfers'].append(transfer(req['stage'], id=req['stage'] + ':W' + str(n),
                    source_kind='mentor_expression', source_id=record['id'], source_excerpt=record['mentor_texts'][0]['text'],
                    decision='unfinished',check_ids=[],finding_ids=[],
                    expression_contribution=dict(role='unresolved',feature_ids=[],supporting_concern_ids=[])))
            result['source_use_dispositions'] = [dict(**u, status='not_assessed', transfer_ids=[], reason='Synthetic candidate association; no judgment supplied') for u in ctx['source_uses']]
            import advisor_results
            result['expression_result_manifest']=[{'source_id':r['id'],'transfer_ids':[t['id'] for t in result['writing_transfers'] if t['source_kind']=='mentor_expression' and t['source_id']==r['id']]} for r in ctx['expression_sources']['records']]
            result['source_review_summary'] = advisor_results.summary(result)
            import advisor_output
            native = advisor_output.encode(result, ctx)
            import normalize_stage_response
            native_path = self.run/f"calls/{req['stage']}/fixture/final_text.json"
            m.save(native_path, native)
            normalized, _, unresolved = normalize_stage_response.normalize(self.run, req['stage'], native_path)
            self.assertEqual(unresolved, [])
            self.assertEqual(m.read(normalized), result)
            m.accept_response(self.run, native, {'kind': 'synthetic_fixture', 'model_called': False})
            self.assertEqual(m.read(self.run/f"calls/{req['stage']}/raw_response.json"), native)
            self.assertEqual(m.read(self.run/f"calls/{req['stage']}/expanded_response.json"), result)
        self.assertEqual(sorted(seen), ['EXP1', 'EXP2'])
        self.assertFalse((self.run / 'calls/advisor_tasks').exists())
        self.assertEqual(m.next_request(self.run)['stage'], 'language')

    def test_tiny_capacity_leaves_inputs_unchanged(self):
        self.prepared(); frozen = m.sha(self.run / 'inputs/FREEZE.json')
        with self.assertRaisesRegex(ValueError, 'One complete source'):
            self.plan(policy(1000))
        self.assertEqual(m.sha(self.run / 'inputs/FREEZE.json'), frozen)
        self.assertFalse((self.run / 'inputs/advisor_plan.json').exists())

    def test_native_shared_results_enter_pipeline_without_inferred_review(self):
        self.prepared(); self.plan()
        for stage in ['objects','reader','technical']:
            m.next_request(self.run)
            m.accept_response(self.run,answer(stage,m.context_for(self.run,stage)))
        req=m.next_request(self.run);stage=req['stage'];ctx=m.context_for(self.run,stage)
        self.assertIn('ADVISOR SHARED ANALYSIS CONTRACT',req['prompt'])
        raw={'advisor_output_version':1,'definitions':{},'response':{
          'stage':stage,'analyses':[],
          'concern_results':[{'source_ids':ctx['primary_card_ids'],'state':'unknown','analysis_ids':[],'reason':'Synthetic fixture has not determined applicability.'}],
          'expression_results':[{'source_ids':[r['id'] for r in ctx['expression_sources']['records']],
            'decision':'unfinished','reason':'Synthetic fixture intentionally leaves inspection unfinished.','target_anchors':[]}],
          'adopted_uses':[],'association_exceptions':[]}}
        m.accept_response(self.run,raw,{'kind':'synthetic_fixture','model_called':False})
        saved=m.read(self.run/f'calls/{stage}/response.json')
        self.assertEqual(saved['source_review_summary']['expression_states'],{'unfinished':2})
        self.assertEqual(saved['source_review_summary']['association_states'],{'not_assessed':1})
        self.assertEqual(m.read(self.run/f'calls/{stage}/raw_response.json'),raw)

    def test_workload_splits_even_with_abundant_capacity_and_is_checked_at_submission(self):
        self.prepared()
        limit = m.read(self.run/'inputs/advisor_planning_policy.json')
        limit['limits'].update(concerns=2, expressions=1)
        for choice in limit['alternatives']: choice['limits'].update(concerns=2,expressions=1)
        m.save(self.run/'inputs/advisor_planning_policy.json',limit);m.freeze(self.run/'inputs')
        plan=self.plan(policy(5000000))
        self.assertGreater(len(plan['groups']),1)
        self.assertEqual(plan['coverage'],dict(concerns=4,expressions=2,tasks=0,uses=1))
        for g in plan['groups']:
            ctx=m.context_for(self.run,g['stage'])
            self.assertLessEqual(b.check_workload(ctx,limit)['expressions'],1)
            m.prepare_stage_request(self.run,g['stage'])
        ctx=m.context_for(self.run,plan['groups'][0]['stage'])
        ctx['primary_card_ids']=['T0','T1','T2'];ctx['cards']=m.all_runtime_cards(self.run)
        with self.assertRaisesRegex(ValueError,'workload'):
            m.prepare_stage_request(self.run,plan['groups'][0]['stage'],_context_override=ctx)

    def test_direct_packets_do_not_depend_on_reader_expert_or_task_outputs(self):
        self.prepared(); plan=self.plan()
        stage=plan['groups'][0]['stage']
        before=m.prepare_stage_request(self.run,stage)
        for lane in ['objects','reader','technical','advisor_tasks']:
            m.save(self.run/f'calls/{lane}/response.json',{'untrusted_plan_or_verdict':'LEAK_SENTINEL_'+lane})
        after=m.prepare_stage_request(self.run,stage)
        self.assertEqual(before['prompt'],after['prompt'])
        ctx=m.context_for(self.run,stage)
        self.assertNotIn('objects',ctx)
        self.assertNotIn('expression_tasks',ctx)
        self.assertNotIn('context_only_tasks',ctx)
        self.assertNotIn('LEAK_SENTINEL',after['prompt'])
        self.assertEqual(ctx['manuscript'],m.read(self.run/'inputs/paper/body.json'))

    def test_legacy_pending_and_frozen_task_map_runs_keep_their_original_contract(self):
        self.prepared()
        protocol=m.read(self.run/'inputs/protocol.json');protocol.pop('advisor_direct_fulltext')
        protocol.pop('advisor_role_division')
        protocol.pop('advisor_batch_budget')
        protocol['stages'].insert(0,'advisor_tasks')
        m.save(self.run/'inputs/protocol.json',protocol);m.freeze(self.run/'inputs')
        m.next_request(self.run)
        m.accept_response(self.run,self.task_map(),{'kind':'synthetic_fixture','model_called':False})
        plan=self.plan()
        original=m.sha(self.run/'inputs/FREEZE.json')
        self.assertEqual(plan['coverage']['tasks'],1)
        self.assertEqual(self.plan(),plan)
        self.assertEqual(m.sha(self.run/'inputs/FREEZE.json'),original)

    def test_budget_failure_precedes_review_and_does_not_mutate_frozen_inputs(self):
        self.prepared()
        config=m.read(self.run/'inputs/advisor_planning_policy.json')
        config.update(version=3,target_batches=1,max_batches=1)
        for choice in [config]+config['alternatives']:
            choice['limits'].update(concerns=2,expressions=1)
        m.save(self.run/'inputs/advisor_planning_policy.json',config);m.freeze(self.run/'inputs')
        before=m.sha(self.run/'inputs/FREEZE.json')
        with patch.object(runner.codex_adapter,'invoke') as invoke:
            with self.assertRaisesRegex(ValueError,'1-request budget'):self.plan(policy(5000000))
        invoke.assert_not_called()
        self.assertEqual(m.sha(self.run/'inputs/FREEZE.json'),before)
        self.assertFalse((self.run/'inputs/advisor_plan.json').exists())
        failure=m.read(self.run/'advisor_planning_failure.json')
        self.assertEqual(failure['model_calls'],0)
        self.assertFalse(failure['user_confirmation_required'])

    def test_policy_is_pinned_at_creation_and_older_pending_run_keeps_old_limits(self):
        self.prepared()
        config=m.read(self.run/'inputs/advisor_planning_policy.json')
        self.assertEqual(config['preferred_max_batches'],12)
        self.assertNotIn('max_batches',config)
        self.assertNotIn('target_batches',config)
        protocol=m.read(self.run/'inputs/protocol.json');protocol.pop('advisor_batch_budget')
        m.save(self.run/'inputs/protocol.json',protocol);m.freeze(self.run/'inputs')
        plan=self.plan()
        self.assertEqual(plan['workload_policy']['limits']['expressions'],110)
        self.assertNotIn('execution_budget',plan)

    def contribution_context(self):
        return dict(advisor_role_division=1,cards=[{'id':'C1'},{'id':'C2'}],
            expression_sources={'records':[{'id':'E1','language_features':[{'id':'E1:L1'}]},
                                           {'id':'E2','language_features':[{'id':'E2:L1'}]}]})

    def contribution_response(self):
        return dict(checks=[dict(id='Ck1',card_ids=['C1'])],writing_transfers=[
            dict(source_kind='mentor_expression',source_id='E1',decision='required_repair',check_ids=['Ck1'],
                 expression_contribution=dict(role='repair_realization',feature_ids=['E1:L1'],supporting_concern_ids=['C1']))])

    def test_expression_contribution_references_its_own_feature_and_actual_concern_check(self):
        ctx=self.contribution_context();response=self.contribution_response()
        b.validate_contributions(response,ctx)
        for changes in [dict(feature_ids=['E2:L1']),dict(feature_ids=[]),
                        dict(supporting_concern_ids=['C2']),dict(supporting_concern_ids=[]),
                        dict(role='expression_improvement')]:
            invalid=copy.deepcopy(response)
            invalid['writing_transfers'][0]['expression_contribution'].update(changes)
            with self.assertRaises(ValueError): b.validate_contributions(invalid,ctx)
        del response['writing_transfers'][0]['expression_contribution']
        with self.assertRaisesRegex(ValueError,'Missing Expression contribution'):b.validate_contributions(response,ctx)

    def test_unlinked_expression_can_offer_optional_improvement_or_local_error_without_concern(self):
        ctx=self.contribution_context();response=self.contribution_response()
        row=response['writing_transfers'][0];row['source_id']='E2'
        row['expression_contribution'].update(feature_ids=['E2:L1'],supporting_concern_ids=[])
        row['decision']='optional_improvement';row['expression_contribution']['role']='expression_improvement'
        b.validate_contributions(response,ctx)
        row['decision']='required_repair';row['expression_contribution']['role']='expression_repair'
        b.validate_contributions(response,ctx)
        for decision,role in [('keep','no_change'),('not_applicable','no_change'),
                              ('unknown','unresolved'),('unfinished','unresolved')]:
            row['decision']=decision
            row['expression_contribution'].update(role=role,feature_ids=[])
            b.validate_contributions(response,ctx)

    def test_earlier_direct_protocol_has_no_new_contribution_contract(self):
        old=dict(advisor_direct_fulltext=1,source_uses=[])
        b.validate_uses(dict(writing_transfers=[dict(id='legacy:W1',source_kind='mentor_expression')]),old)
        self.assertNotIn('expression_contribution',b.instructions(old))

    def test_cross_group_packing_responds_to_capacity_without_lowering_reserves(self):
        import shutil
        self.prepared()
        smaller_run = self.root / 'smaller'
        shutil.copytree(self.run, smaller_run)
        large = self.plan(policy(500000))
        small_policy = policy(large['groups'][0]['capacity']['total_reserved'] - 500)
        original = copy.deepcopy(small_policy)
        self.run = smaller_run
        small = self.plan(small_policy)
        self.assertEqual(small_policy, original)
        self.assertEqual(m.read(self.run/'inputs/protocol.json')['advisor_capacity'], original)
        self.assertGreater(len(small['groups']), len(large['groups']))
        self.assertEqual(small['coverage'], large['coverage'])
        for group in small['groups']:
            self.assertEqual(group['capacity']['policy'], original)
            self.assertTrue(group['capacity']['fits'])

    def test_companion_components_stay_indivisible_and_order_is_deterministic(self):
        records = {'E1': {'local_reference_bindings':[{'status':'admitted','expression_id':'E2'}]},
                   'E2': {}, 'E3': {}, 'E4': {}}
        cards = {'C1': {'text':'complete requirement'}, 'C2': {'text':'another complete requirement'}}
        uses = {('E1','concern','C1'), ('E2','concern','C2'), ('E3','concern','C1')}
        units = b.ordered_expression_units(records, cards, uses)
        self.assertIn(('E',('E1','E2')), units)
        self.assertEqual(sorted(e for _,es in units for e in es), sorted(records))
        self.assertEqual(units,b.ordered_expression_units(dict(reversed(list(records.items()))),cards,uses))
        del records['E2']
        with self.assertRaisesRegex(ValueError,'Missing admitted'):
            b.ordered_expression_units(records,cards,uses)

    def test_historical_links_do_not_remove_sources_or_conditions(self):
        self.prepared()
        def historical(root, records):
            table = self.relations(root, records)
            table['links'][0]['kind'] = 'historical'
            return table
        import advisor_wire as wire
        with patch.object(b, 'fixed_groups', self.groups), patch.object(b, 'relation_index', historical):
            plan = b.plan_run(self.run, policy())
        self.assertEqual(plan['coverage']['expressions'], 2)
        self.assertEqual(plan['coverage']['concerns'], 4)
        self.assertEqual(plan['coverage']['uses'], 0)
        ctx = m.context_for(self.run, plan['groups'][0]['stage'])
        req = m.prepare_stage_request(self.run, plan['groups'][0]['stage'])
        sent = json.loads(req['prompt'].rsplit('\nINPUT\n', 1)[1])
        review = wire.unpack(sent)
        self.assertEqual(next(r for r in review['expression_sources']['records'] if r['id']=='EXP1')['concern_ids'], [])
        self.assertEqual(b.inflate(wire.restore(review, req['local_administration'])), ctx)
        self.assertTrue(next(r for r in ctx['expression_sources']['records'] if r['id']=='EXP1')['concern_ids'])
        self.assertFalse(any(u['target_kind']=='concern' for u in ctx['source_uses']))

    def test_public_relation_index_covers_every_original_edge(self):
        records={r['id']:r for r in m.read(m.ROOT/'corpus/advisor-expression-v1/records.json')}
        table=b.relation_index(m.ROOT,records)
        self.assertEqual(len(table['links']),2585)
        self.assertEqual(set(table['expression_ids']),set(records))
        links={(r['expression_id'],r['concern_id']):r for r in table['links']}
        # Different final retained operations must not inherit an adjacent scope edit.
        self.assertEqual(links[('EX00193','C0044')]['kind'],'historical')
        self.assertEqual(links[('EX00187','C0044')]['kind'],'direct')
        if table.get('fresh_full_review'):
            self.assertTrue(all(r['basis']=='fresh_retained_content_review' and r['audit_id']
                                for r in table['links']))

    def test_adaptive_deferred_evidence_does_not_rebuild_preparation_batches(self):
        self.prepared();self.plan()
        protocol=m.read(self.run/'inputs/protocol.json')
        protocol['stages'].append('supplement_999')
        m.save(self.run/'inputs/protocol.json',protocol);m.freeze(self.run/'inputs')
        self.assertFalse((self.run/'expression_route.json').exists())
        result=m.expression.stage_context(self.run,'evidence_1')
        self.assertEqual(result['expression_sources'],{'records':[],'episodes':[]})
        self.assertEqual(result['expression_tasks'],[])
        self.assertFalse((self.run/'expression_route.json').exists())

    def test_conditional_link_boundaries_are_supplied_without_changing_source(self):
        self.prepared()
        before=m.sha(self.run/'inputs/expression/records.json')
        note='Apply only when the retained source and current manuscript share the stated prerequisite.'
        def conditional(root,records):
            table=self.relations(root,records)
            table['links'][0].update(kind='conditional',condition=note)
            return table
        with patch.object(b,'fixed_groups',self.groups),patch.object(b,'relation_index',conditional):
            plan=b.plan_run(self.run,policy())
        contexts=[m.context_for(self.run,g['stage']) for g in plan['groups']]
        uses=[u for c in contexts for u in c['source_uses'] if u['relation_kind']=='conditional']
        self.assertEqual(len(uses),1)
        self.assertEqual(uses[0]['relation_condition'],note)
        self.assertEqual(m.sha(self.run/'inputs/expression/records.json'),before)

    def test_splits_one_concern_many_expressions_without_truncation(self):
        units = [('E', str(i)) for i in range(8)]
        def build(items):
            return dict(cards=[{'id': 'C1', 'full': 'complete concern'}], items=items, text='x' * (500 * len(items)))
        def render(stage, ctx): return {'prompt': json.dumps(ctx)}
        p = policy(15000)
        packets = b.split_group(units, build, render, p, 0, 1)
        self.assertGreater(len(packets), 1)
        self.assertEqual([x for _, c, _ in packets for x in c['items']], units)
        self.assertTrue(all(c['cards'][0]['full'] == 'complete concern' for _, c, _ in packets))
        self.assertTrue(all(v['fits'] for _, _, v in packets))

    def test_missing_duplicate_or_wrong_expression_uses_fail(self):
        ctx = dict(source_uses=[dict(expression_id='E1', target_kind='concern', target_id='C1')], expression_tasks=[], context_only_tasks=[])
        row = dict(**ctx['source_uses'][0], status='unfinished', transfer_ids=[], reason='pending')
        b.validate_uses(dict(source_use_dispositions=[row]), ctx)
        for rows in [[], [row, row], [{**row, 'expression_id': 'E2'}], [{**row, 'status': 'checked'}]]:
            with self.assertRaises(ValueError): b.validate_uses(dict(source_use_dispositions=rows), ctx)

    def test_projection_restores_every_value(self):
        feature = {'text': 'full source quote ' * 40, 'conditions': 'full conditions ' * 40}
        ctx = {'expression_sources': {'records': [{'language_features': [feature], 'public_language_features': [feature]}]}}
        compact = b.project(ctx)
        self.assertLess(len(json.dumps(compact)), len(json.dumps(ctx)))
        self.assertEqual(b.inflate(compact), ctx)

    def test_public_fixed_groups_cover_entire_corpus_once(self):
        cards = {r['id']: r for r in m.read(m.DEFAULT_KNOWLEDGE / 'archive.json')}
        records = {r['id']: r for r in m.read(m.DEFAULT_EXPRESSION / 'records.json')}
        groups = b.fixed_groups(m.ROOT, cards, records)
        self.assertEqual(len(groups), 12)
        self.assertEqual(sum(len(g['concern_ids']) for g in groups), 493)
        self.assertEqual(sum(len(g['expression_ids']) for g in groups), 1581)
        self.assertEqual(sum(not r['concern_ids'] for r in records.values()), 271)

    def test_model_catalog_not_maximum_or_bundled_and_effort_preserved(self):
        catalog = {'models': [dict(slug='fixture-model', context_window=500000, max_context_window=900000,
                   effective_context_window_percent=95, supported_reasoning_levels=[{'effort': 'high'}])]}
        result = type('Result', (), dict(returncode=0, stdout=json.dumps(catalog)))()
        with patch.object(capacity.shutil, 'which', return_value='codex'), patch.object(capacity.subprocess, 'run', return_value=result) as call, patch.object(capacity, 'tokenizer', return_value=()):
            p = capacity.discover('fixture-model', 'high')
            self.assertEqual(p['context_window'], 500000); self.assertEqual(p['effective_context'], 475000)
            self.assertEqual((p['output_reserve'],p['image_reserve_each'],p['system_reserve'],p['text_multiplier']),
                             (64000,6000,8000,1.10))
            self.assertEqual(p['max_prompt_chars'],1048576)
            self.assertNotIn('--bundled', call.call_args.args[0])
            with self.assertRaises(ValueError): capacity.discover('missing', 'high')
            with self.assertRaises(ValueError): capacity.discover('fixture-model', 'xhigh')

    def test_association_discount_preserves_counts_and_legacy_score(self):
        self.prepared();plan=self.plan()
        ctx=m.context_for(self.run,plan['groups'][0]['stage'])
        legacy=b.workload(ctx)
        current=b.workload(ctx,{'association_weight':.25})
        for key in legacy:
            if key!='complexity':self.assertEqual(legacy[key],current[key])
        self.assertEqual(legacy['complexity']-current['complexity'],
                         .75*(legacy['uses']+.5*legacy['conditional_uses']+legacy['uncertain_uses']))
        with self.assertRaisesRegex(ValueError,'weight'):b.workload(ctx,{'association_weight':-1})

    def test_image_and_output_reserves_participate(self):
        p = policy(13000)
        self.assertTrue(capacity.estimate('x' * 100, 0, p)['fits'])
        self.assertFalse(capacity.estimate('x' * 100, 3, p)['fits'])

    def test_transport_characters_can_exceed_limit_even_when_tokens_fit(self):
        p=policy(5000000);p['max_prompt_chars']=10
        self.assertTrue(capacity.check_capacity('x'*10,0,p)['fits'])
        result=capacity.estimate('x'*11,0,p)
        self.assertLess(result['total_reserved'],p['effective_context'])
        self.assertFalse(result['transport_character_fit'])
        with self.assertRaisesRegex(ValueError,'character limit'):capacity.check_capacity('x'*11,0,p)
        self.assertFalse(capacity.estimate('\U0001f600'*6,0,p)['fits'])
        p.pop('max_prompt_chars')
        self.assertTrue(capacity.estimate('x'*11,0,p)['fits']) # Frozen old runs unchanged.

    def test_runner_automatically_plans_before_any_review_submission(self):
        self.prepared()
        auth = self.root / 'authorization.json'
        m.save(auth, dict(authorized_by='user', user_statement='Synthetic authorization fixture only.',
                         model='fixture-model', reasoning_effort='high', service_tier='default'))
        args = ['run_authorized_stage.py', '--run', str(self.run), '--model', 'fixture-model',
                '--effort', 'high', '--settings-authorization', str(auth)]
        def stop_before_model(run, request, arguments, authorization):
            self.assertTrue((run / 'inputs/advisor_plan.json').exists())
            self.assertEqual(request['stage'], 'objects')
            self.assertEqual(arguments.auto_capacity, policy())
            self.assertEqual(authorization['model'], 'fixture-model')
            raise RuntimeError('TEST STOP: no model generation')
        with patch.object(sys, 'argv', args), patch.object(capacity, 'discover', return_value=policy()), \
             patch.object(b, 'fixed_groups', self.groups), patch.object(b, 'relation_index', self.relations), patch.object(runner, 'execute_request', side_effect=stop_before_model):
            with self.assertRaisesRegex(RuntimeError, 'TEST STOP'):
                runner.main()
        self.assertEqual(m.read(self.run / 'state.json')['completed'], [])


if __name__ == '__main__':
    unittest.main()
