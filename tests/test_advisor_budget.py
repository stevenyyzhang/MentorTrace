"""Automatic choice, atomic request limits and dispatch failure; fake senders only."""
import copy
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import advisor_budget as budget
import run_authorized_stage as runner


def config():
    # Frozen v2 runs must retain their old selection and retry limits.
    return dict(version=2,name='balanced',target_batches=15,max_batches=24,
        standalone_expression_target=110,limits=dict(concerns=50,operations=150,uses=180,complexity=700),
        alternatives=[dict(name='combined',standalone_expression_target=160,
            limits=dict(concerns=70,operations=220,uses=260,complexity=1000))])


def current_config():
    return json.loads((Path(__file__).resolve().parents[1]/'config/advisor-workload.json').read_text())


class AutomaticChoice(unittest.TestCase):
    def test_current_policy_prefers_twelve_without_forcing_count_or_stopping_overflow(self):
        current=current_config()
        self.assertEqual(current['preferred_max_batches'],12)
        self.assertNotIn('max_batches',current)
        self.assertNotIn('target_batches',current)
        self.assertNotIn('uses',current['limits'])
        self.assertEqual(current['association_weight'],.25)
        self.assertEqual(current['limits']['complexity'],2000)
        for n in (1,4,5,6,10,12,13,20):
            packets,choice,execution,trials=budget.select(current,lambda c:(list(range(n)),''))
            self.assertEqual(len(packets),n)
            self.assertFalse(execution['user_confirmation_required'])
            self.assertEqual(execution['max_batches'],max(12,n))
            self.assertEqual(execution['automatic_overflow'],n>12)

    def test_current_policy_compares_fewer_packets_even_if_first_is_below_cap(self):
        current=current_config();current['alternatives']=[dict(name='alternative')]
        packets,choice,execution,trials=budget.select(current,lambda c:(list(range(10 if c['name']=='compact' else 6)),''))
        self.assertEqual(len(packets),6);self.assertEqual(len(trials),2)

    def test_real_packer_adapts_capacity_and_automatically_exceeds_twelve(self):
        import advisor_batching as batching
        units=[('E',[f'E{i}']) for i in range(20)]
        def build(es,cs):
            return dict(primary_card_ids=[],cards=[],source_uses=[],
                        expression_sources=dict(records=[dict(id=e) for e in es]))
        for packet_capacity,expected in ((4,5),(1,20)):
            def render(stage,ctx):
                return dict(advisor_capacity=dict(fits=len(ctx['expression_sources']['records'])<=packet_capacity))
            packets,choice,execution,trials=budget.select(current_config(),
                lambda policy:batching._pack_direct_units(units,[],build,render,policy,backfill=True))
            self.assertEqual(len(packets),expected)
            ids=[r['id'] for _,ctx,_,_ in packets for r in ctx['expression_sources']['records']]
            self.assertEqual(sorted(ids),sorted(e for _,members in units for e in members))
            self.assertEqual(len(ids),len(set(ids)))
            self.assertEqual(execution['automatic_overflow'],expected>12)
            self.assertFalse(execution['user_confirmation_required'])

    def choose(self,counts):
        called=[]
        def evaluate(choice):
            called.append(choice['name']);n=counts[choice['name']]
            return (list(range(n)),'') if n<=24 else (None,f'{n} exceeds budget')
        result=budget.select(config(),evaluate)
        return result,called

    def test_lighter_plan_meeting_goal_skips_broader_profile_without_forcing_count(self):
        (packets,choice,limits,trials),called=self.choose(dict(balanced=9,combined=7))
        self.assertEqual(called,['balanced'])
        self.assertEqual(len(packets),9)
        self.assertTrue(limits['target_met'])
        self.assertFalse(limits['user_confirmation_required'])

    def test_broader_profile_is_compared_automatically_and_tie_prefers_lighter(self):
        for first,second,expected in [(17,12,'combined'),(20,20,'balanced'),(25,24,'combined')]:
            with self.subTest(first=first,second=second):
                (packets,choice,limits,trials),called=self.choose(dict(balanced=first,combined=second))
                self.assertEqual(called,['balanced','combined'])
                self.assertEqual(choice['name'],expected)
                self.assertEqual(limits['planned_batches'],min(first,second))
                self.assertEqual(limits['max_batches'],24)
                self.assertFalse(limits['user_confirmation_required'])

    def test_impossible_plan_never_silently_extends_budget_or_load_limits(self):
        with self.assertRaises(budget.PlanningBudgetError) as error:
            self.choose(dict(balanced=28,combined=25))
        self.assertEqual(len(error.exception.trials),2)
        self.assertEqual(len(budget.candidates(config())),2)
        invalid=copy.deepcopy(config());invalid['alternatives'][0]['max_batches']=25
        with self.assertRaisesRegex(ValueError,'preserve'):budget.candidates(invalid)


class RequestReservations(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.run=Path(temporary.name);(self.run/'inputs').mkdir()
        limits=dict(target_batches=15,max_batches=24,planned_batches=1)
        self.save('inputs/protocol.json',dict(advisor_batch_budget=1,advisor_request_budget=limits))
        self.save('inputs/advisor_plan.json',dict(groups=[dict(stage='supplement_1')],execution_budget=limits))
        self.save('inputs/advisor_planning_policy.json',config())
        self.request=dict(stage='supplement_1',prompt='Synthetic',images=[])

    def save(self,path,value):
        (self.run/path).write_text(json.dumps(value),encoding='utf-8')

    def test_current_twelve_limit_counts_explicit_attempts_without_hidden_extension(self):
        limits=dict(target_batches=12,max_batches=12,planned_batches=1)
        self.save('inputs/protocol.json',dict(advisor_batch_budget=1,advisor_request_budget=limits))
        self.save('inputs/advisor_plan.json',dict(groups=[dict(stage='supplement_1')],execution_budget=limits))
        self.save('inputs/advisor_planning_policy.json',current_config())
        for i in range(12):self.assertIsNotNone(self.reserve(f'current-{i}'))
        self.assertIsNone(self.reserve('over-limit'))

    def test_overflow_plan_has_enough_slots_without_confirmation(self):
        packets,choice,limits,trials=budget.select(current_config(),lambda c:(list(range(17)),''))
        self.save('inputs/protocol.json',dict(advisor_batch_budget=1,advisor_request_budget=limits))
        self.save('inputs/advisor_plan.json',dict(groups=[dict(stage=f'supplement_{i+1}') for i in packets],execution_budget=limits))
        self.save('inputs/advisor_planning_policy.json',current_config())
        self.assertTrue(budget.check_plan(self.run)['automatic_overflow'])
        for i in range(17):self.assertIsNotNone(self.reserve(f'overflow-{i}'))
        self.assertIsNone(self.reserve('over-limit'))

    def reserve(self,name):
        try:return budget.reserve_request(self.run,self.request,name)
        except ValueError:return None

    def test_concurrent_unique_attempts_never_exceed_hard_limit(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            results=list(pool.map(self.reserve,[f'try-{n}' for n in range(32)]))
        self.assertEqual(sum(x is not None for x in results),24)
        self.assertEqual(len(list((self.run/'advisor_request_slots').glob('*.json'))),24)

    def test_same_attempt_concurrency_reserves_only_once(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(self.reserve,['same']*8))
        self.assertEqual(sum(x is not None for x in results),1)
        self.assertEqual(len(list((self.run/'advisor_request_slots').glob('*.json'))),1)

    def test_exhausted_budget_stops_dispatch_and_cache_does_not_take_a_slot(self):
        for n in range(24):budget.reserve_request(self.run,self.request,f'try-{n}')
        args=SimpleNamespace(model='fixture',effort='high',service_tier='default',
            context_window=10000,output_reserve=100,image_token_reserve=100,
            safety_margin=100,attempt_name='next')
        with patch.object(runner.codex_adapter,'invoke') as invoke:
            with self.assertRaisesRegex(ValueError,'budget exhausted'):
                runner.execute_request(self.run,self.request,args,{})
        invoke.assert_not_called()
        output=self.run/'cached.json';output.write_text('{}')
        with patch.object(runner,'find_cached',return_value=(output,dict(usage=[]))), \
             patch.object(runner.normalize_stage_response,'normalize',return_value=(output,0,[])), \
             patch.object(runner.mentortrace,'validate'), \
             patch.object(runner.mentortrace,'context_for',return_value={}), \
             patch.object(runner.codex_adapter,'invoke') as invoke, \
             patch.object(budget,'reserve_request') as reserve:
            self.assertTrue(runner.execute_request(self.run,self.request,args,{})['reused'])
        invoke.assert_not_called();reserve.assert_not_called()

    def test_plan_and_stage_must_match_pinned_budget_and_legacy_is_unchanged(self):
        with self.assertRaisesRegex(ValueError,'absent'):budget.check_plan(self.run,'supplement_99')
        policy=config();policy['max_batches']=23;self.save('inputs/advisor_planning_policy.json',policy)
        with self.assertRaisesRegex(ValueError,'differs'):budget.check_plan(self.run)
        self.save('inputs/protocol.json',{})
        self.assertIsNone(budget.reserve_request(self.run,self.request,'legacy'))


if __name__=='__main__':unittest.main()
