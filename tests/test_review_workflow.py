"""No network: actual runtime branches, fake senders and strict review accounting."""
import copy
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import mentortrace_v1 as m
import review_workflow as w
import run_authorized_stage as runner
import run_review_packet as packet_runner
import test_pipeline as fixture
from test_execution_efficiency import authorization

POLICY=dict(model='synthetic-model',effort='xhigh',effective_context=10000000,context_window=10000000,
            output_reserve=64000,image_reserve_each=6000,system_reserve=8000,text_multiplier=1.1,
            token_method='utf8_upper_bound',max_prompt_chars=1048576)


class ParallelInitial(unittest.TestCase):
    def setUp(self):
        self.f=fixture.Pipeline();self.f.setUp();self.addCleanup(self.f.tearDown);self.f.advance()
        self.args=SimpleNamespace(model='synthetic-model',effort='xhigh',service_tier='default',attempt_name='fake',
             auto_capacity=POLICY,workers=3)

    def test_reader_expert_advisor_overlap_without_cross_lane_inputs(self):
        barrier=threading.Barrier(3);seen=[];guard=threading.Lock()
        def invoke(folder,prompt,images,**settings):
            folder=Path(folder);stage=folder.parent.name
            with guard:
                first=len(seen)<3;seen.append(stage)
            if first:barrier.wait(timeout=10)
            self.assertNotIn('SYNTHETIC_GAP_SENTINEL',prompt)
            if stage.startswith('supplement_'):
                ctx=m.context_for(self.f.run,stage)
                self.assertNotIn('objects',ctx);self.assertNotIn('reader_scope_plan',ctx)
            output=folder/'final_text.json';m.save(output,fixture.answer(stage,m.context_for(self.f.run,stage)))
            return output,[{'input_tokens':1,'output_tokens':1}]
        with patch.object(runner.codex_adapter,'invoke',side_effect=invoke) as send:
            result=runner.parallel_initial(self.f.run,self.args,authorization(),'synthetic-sha')
        self.assertEqual(result['failures'],[])
        self.assertEqual(set(seen),{'reader','technical','language',*[f'supplement_{n}' for n in range(1,5)]})
        done=m.read(self.f.run/'state.json')['completed']
        self.assertEqual(done,m.read(self.f.run/'inputs/protocol.json')['stages'][:-2])
        self.assertEqual(send.call_count,7)
        self.assertEqual(m.next_request(self.f.run)['stage'],'merge')

    def test_failed_reader_does_not_skip_or_retry_and_other_results_survive(self):
        def execute(run,req,args,auth):
            if req['stage']=='reader':raise ValueError('synthetic failure')
            return {'stage':req['stage'],'saved':True}
        with patch.object(runner,'execute_request',side_effect=execute) as send:
            result=runner.parallel_initial(self.f.run,self.args,authorization(),'sha')
        self.assertEqual(send.call_count,7)
        self.assertEqual(m.read(self.f.run/'state.json')['completed'],['objects'])
        self.assertEqual(len(result['deferred']),6)
        self.assertEqual(result['failures'][0]['stage'],'reader')
        self.assertFalse((self.f.run/'parallel_initial.lock').exists())

    def test_all_requests_capacity_checked_before_sender(self):
        self.args.auto_capacity={**POLICY,'effective_context':1}
        with patch.object(runner.codex_adapter,'invoke') as send,self.assertRaisesRegex(ValueError,'capacity'):
            runner.parallel_initial(self.f.run,self.args,authorization(),'sha')
        send.assert_not_called()


class ReviewAccounting(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.bound=self.root/'source.txt';self.bound.write_text('complete source',encoding='utf-8')
        self.bundle=self.root/'bundle'
        self.tasks=[w.task('target','a',{'text':'One.'},'same'),w.task('target','b',{'text':'Two.'},'same')]
        w.prepare_bundle(self.bundle,'delivery',{'page_images':[]},self.tasks,{str(self.bound):m.sha(self.bound)},POLICY)
        req=m.read(self.bundle/'requests/delivery-001.json')
        self.result={'packet_id':'delivery-001','request_sha256':req['request_sha256'],
                     'reviewer':{'name':'synthetic fixture','kind':'synthetic_test','context_scope':'frozen_a_and_final_outputs','prior_outputs_seen':True,'limits':'No model called'},
                     'judgments':{'J1':{'reason':'Explicit shared actual reason','status':'unknown'}},
                     'results':[{'task_ids':['target:a','target:b'],'value':{'$judgment':'J1'}}]}

    def save(self):
        p=self.root/'actual.json';m.save(p,self.result);return p

    def test_explicit_shared_verdict_expands_only_named_ids(self):
        values,_=w.collect(self.bundle,[self.save()])
        self.assertEqual(set(values),{'target:a','target:b'})
        self.assertEqual(values['target:a'],{'reason':'Explicit shared actual reason','status':'unknown'})

    def test_omission_duplicate_and_unknown_reference_never_default_pass(self):
        for rows in [[{'task_ids':['target:a'],'value':{'status':'keep'}}],
                     [{'task_ids':['target:a','target:a'],'value':{'status':'keep'}}],
                     [{'task_ids':['target:a','target:b'],'value':{'$judgment':'absent'}}]]:
            with self.subTest(rows=rows):
                self.result['results']=rows
                with self.assertRaises(ValueError):w.collect(self.bundle,[self.save()])

    def test_tampered_context_or_evidence_rejects_reuse(self):
        self.bound.write_text('changed',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'source changed'):w.collect(self.bundle,[self.save()])

    def test_capacities_and_output_reserves_unchanged(self):
        manifest=w.verify_bundle(self.bundle)
        self.assertEqual(manifest['policy'],POLICY)
        self.assertEqual(manifest['policy']['output_reserve'],64000)
        self.assertEqual(manifest['policy']['image_reserve_each'],6000)

    def test_oversized_scheduling_group_splits_complete_tasks_without_lowering_policy(self):
        policy={**POLICY,'output_reserve':200}
        folder=self.root/'small-output'
        manifest=w.prepare_bundle(folder,'delivery',{'page_images':[],'complete_source':'Full unchanged shared context'},self.tasks,{},policy)
        self.assertEqual(len(manifest['packets']),2)
        self.assertEqual(manifest['policy'],policy)
        assigned=[]
        import advisor_wire
        for entry in manifest['packets']:
            req=m.read(folder/entry['file']);assigned+=req['task_ids']
            payload=advisor_wire.unpack(json.loads(req['prompt'].split('\nINPUT\n')[-1]))
            self.assertEqual(payload['complete_source'],'Full unchanged shared context')
            self.assertEqual(payload['tasks'][0]['data'],next(t['data'] for t in self.tasks if t['id']==req['task_ids'][0]))
        self.assertEqual(set(assigned),{'target:a','target:b'})

    def test_typed_source_paths_do_not_evaluate_arbitrary_expressions(self):
        s={'original':{'closure_goal':'Actual goal.'},'checks':[{'reason':'Actual reason.','local_support':['Actual source.']}]}
        self.assertEqual(w.audit.source_text(s,'original.closure_goal'),'Actual goal.')
        self.assertEqual(w.audit.source_text(s,'checks[0].reason'),'Actual reason.')
        self.assertEqual(w.audit.source_text(s,'checks[0].local_support[0]'),'Actual source.')
        for key in ['checks[-1].reason','checks[9].reason','__class__','checks[0].reason.upper()']:
            self.assertIsNone(w.audit.source_text(s,key))


class SourceIsolation(unittest.TestCase):
    def setUp(self):
        self.f=fixture.Pipeline();self.f.setUp();self.addCleanup(self.f.tearDown)
        protocol=m.read(self.f.run/'inputs/protocol.json');protocol['review_efficiency']=1
        m.save(self.f.run/'inputs/protocol.json',protocol);m.freeze(self.f.run/'inputs')
        while m.next_request(self.f.run)['stage']!='merge':self.f.advance()

    def test_source_preparation_excludes_later_outputs_and_all_checks_are_assigned(self):
        m.save(self.f.run/'calls/merge/response.json',{'secret':'LATER_OUTCOME_MUST_STAY_HIDDEN'})
        m.save(self.f.run/'final.json',{'secret':'LATER_OUTCOME_MUST_STAY_HIDDEN'})
        out=self.f.root/'source'
        plan=w.prepare_source(self.f.run,out,POLICY)
        tasks=m.read(out/'inventory.json')
        expected={c['id'] for s in m.branch_stages(self.f.run) for c in m.read(self.f.run/f'calls/{s}/response.json').get('checks',[])}
        self.assertEqual({t['key'] for t in tasks if t['kind']=='execution'},expected)
        assigned={tid:p['id'] for p in plan['packets'] for tid in m.read(out/p['file'])['task_ids']}
        for t in tasks:
            if t['kind']=='source':
                for c in t['data']['checks']:
                    self.assertEqual(assigned[t['id']],assigned['execution:'+c['id']])
        for entry in plan['packets']:
            self.assertNotIn('LATER_OUTCOME_MUST_STAY_HIDDEN',m.read(out/entry['file'])['prompt'])

    def test_verified_source_assembly_cannot_be_edited_or_omit_units(self):
        out=self.f.root/'source';plan=w.prepare_source(self.f.run,out,POLICY)
        inventory={t['id']:t for t in m.read(out/'inventory.json')};responses=[]
        for entry in plan['packets']:
            req=m.read(out/entry['file']);rows=[]
            for ident in req['task_ids']:
                t=inventory[ident]
                if t['kind']=='source':
                    field='closure_goal' if 'closure_goal' in t['data']['original'] else 'proposed_order'
                    quote=t['data']['original'][field]
                    value={'coverage_review':{'status':'completed','reason':'Synthetic complete original task reviewed'},
                           'components':[{'id':t['key']+':A1','source_field':field,'source_quote':quote,'requirement':quote,
                             'assessment':'required','reason':'Synthetic fixture judgment only',
                             'evidence':[{'kind':'text','page':1,'quote':fixture.A['quote']}],'occurrences':[]}]}
                elif t['kind']=='execution':value={'status':'completed','reason':'Explicit synthetic check outcome','issues':[]}
                else:value={'status':'completed','reason':'Explicit synthetic stage scope outcome','issues':[],'unresolved_ids':[]}
                rows.append({'task_ids':[ident],'value':value})
            path=self.f.root/(entry['id']+'.json');m.save(path,{'packet_id':entry['id'],'request_sha256':req['request_sha256'],
                'reviewer':{'name':'synthetic fixture','kind':'synthetic_test','context_scope':'originals_and_full_manuscript','prior_outputs_seen':False,'limits':'No model call'},'results':rows})
            responses.append(path)
        target=self.f.run/'initial_review.json';w.assemble_source(out,responses,target)
        w.validated_source_review(target)
        altered=m.read(target);altered['units'].pop();m.save(target,altered)
        with self.assertRaisesRegex(ValueError,'inventory omitted'):w.validated_source_review(target)

    def test_new_verify_protocol_requires_completed_bound_source_review(self):
        protocol=m.read(self.f.run/'inputs/protocol.json');protocol['review_efficiency']=1
        m.save(self.f.run/'inputs/protocol.json',protocol);m.freeze(self.f.run/'inputs')
        self.f.advance()  # merge still independent of source-only reviewer
        with self.assertRaisesRegex(ValueError,'combined source/execution review'):m.next_request(self.f.run)


class PreparedPacketTransport(unittest.TestCase):
    setUp=ReviewAccounting.setUp
    def test_exact_prepared_request_is_reused_without_another_submission(self):
        args=SimpleNamespace(model='synthetic-model',effort='xhigh',service_tier='default',attempt_name='first')
        calls=self.root/'calls'
        def invoke(folder,prompt,images,**settings):
            folder=Path(folder);folder.mkdir(parents=True)
            self.assertEqual(settings['model'],'synthetic-model');self.assertEqual(settings['reasoning_effort'],'xhigh')
            self.assertEqual(settings['service_tier'],'default')
            raw=folder/'final_text.json';m.save(raw,{k:v for k,v in self.result.items() if k not in {'packet_id','request_sha256'}})
            m.save(folder/'audit.json',{'model':settings['model'],'reasoning_effort':settings['reasoning_effort'],
                'requested_service_tier':settings['service_tier'],'images':[],'returncode':0,'fresh_ephemeral_context':True,
                'usage':[{'input_tokens':1,'output_tokens':1}],'prompt_sha256':__import__('hashlib').sha256(prompt.encode()).hexdigest(),
                'output_sha256':m.sha(raw)})
            return raw,[{'input_tokens':1,'output_tokens':1}]
        with patch.object(packet_runner.codex_adapter,'invoke',side_effect=invoke) as send:
            output=packet_runner.execute(self.bundle,'delivery-001',calls,args,authorization())
            before=output.read_bytes()
            self.assertEqual(packet_runner.execute(self.bundle,'delivery-001',calls,args,authorization()),output)
            self.assertEqual(send.call_count,1);self.assertEqual(output.read_bytes(),before)
        w.collect(self.bundle,[output])


class CombinedDeliveryGates(unittest.TestCase):
    def setUp(self):
        from test_delivery_integration import DeliveryIntegration
        self.f=DeliveryIntegration();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.root=self.f.fixture.root;self.bundle=self.root/'combined'
        self.plan=w.prepare_delivery(self.f.fixture.out,self.f.ledger_path,self.bundle,POLICY)
        self.responses=[];sources={u['id']:u for u in self.f.ledger['units']}
        targets={u['id']:u for u in self.f.ledger['target_units']};bs={r['component_id']:r for r in self.f.upstream['components']}
        inventory={t['id']:t for t in m.read(self.bundle/'inventory.json')}
        for entry in self.plan['packets']:
            req=m.read(self.bundle/entry['file']);rows=[]
            for ident in req['task_ids']:
                t=inventory[ident]
                if t['kind']=='coverage':value={k:v for k,v in bs[t['key']].items() if k!='component_id'}
                elif t['kind']=='source_field':value={k:v for k,v in sources[t['key']].items() if k in {'components','non_substantive_reason'}}
                elif t['kind']=='target':value=targets[t['key']]['review']
                else:value={'source_completeness':'Synthetic complete source scope','assertion_completeness':'Synthetic full target scope','semantic_review':'Synthetic actual scope review','issues':[]}
                rows.append({'task_ids':[ident],'value':value})
            path=self.root/(entry['id']+'.json');m.save(path,{'packet_id':entry['id'],'request_sha256':req['request_sha256'],'reviewer':self.f.upstream['reviewer'],'results':rows})
            self.responses.append(path)

    def test_one_combined_result_produces_both_validated_ledgers(self):
        result=w.assemble_delivery(self.bundle,self.responses,self.root/'checked')
        self.assertTrue(result['consolidation']['delivery_ready'])
        self.assertEqual(result['preservation']['status'],'records_validated')
        self.assertFalse(result['semantic_correctness_verified'])

    def test_missing_required_coverage_is_not_hidden_by_final_text_pass(self):
        required={c['id'] for u in m.read(self.f.fixture.out/'phase_a.adjudicated.json')['units'] for c in u['components'] if c['assessment']=='required'}
        for path in self.responses:
            data=m.read(path)
            for row in data['results']:
                if any(ident[len('coverage:'):] in required for ident in row['task_ids'] if ident.startswith('coverage:')):
                    row['value']={'status':'missing','reason':'Synthetic explicit required omission','target_quotes':[],'report_quotes':[]}
                    m.save(path,data)
                    with self.assertRaises(ValueError):w.assemble_delivery(self.bundle,self.responses,self.root/'blocked')
                    return
        self.fail('Fixture has no required coverage task')

    def test_supported_assertion_still_requires_evidence(self):
        for path in self.responses:
            data=m.read(path)
            row=next((r for r in data['results'] if r['task_ids'][0].startswith('target:') and r['value'].get('classification')),None)
            if row:
                quote=next(u['text'] for u in self.f.ledger['target_units'] if 'target:'+u['id']==row['task_ids'][0])
                row['value'].update(classification='factual',assertions=[{'quote':quote,'status':'supported','reason':'Synthetic unsupported assertion','evidence':[]}])
                m.save(path,data)
                with self.assertRaisesRegex(ValueError,'evidence'):w.assemble_delivery(self.bundle,self.responses,self.root/'blocked')
                return
        self.fail('Fixture has no target block')

    def test_other_final_source_cannot_borrow_a_valid_b_record(self):
        changed=copy.deepcopy(self.f.ledger);other=self.root/'other-final.json'
        m.save(other,m.read(self.f.fixture.run/'final.json'))
        changed['sources'][0]['path']=str(other);changed['sources'][0]['sha256']=m.sha(other)
        path=self.root/'other-ledger.json';m.save(path,changed)
        with self.assertRaisesRegex(ValueError,'same final review'):
            w.prepare_delivery(self.f.fixture.out,path,self.root/'other-combined',POLICY)


class SourceReuse(unittest.TestCase):
    def test_identical_source_only_judgments_seed_selected_a_without_another_review(self):
        from test_merge_obligations import MergeObligationAudit,reviewer
        f=MergeObligationAudit();f.setUp();self.addCleanup(f.doCleanups)
        f.ready_b();package,snapshot=w.audit.verify_package(f.out)
        bundle=f.root/'source-reuse';base={'manuscript':snapshot['manuscript'],'page_images':snapshot['page_images'],'original_stage_context':[]}
        plan=w.prepare_bundle(bundle,'source',base,[w.task('source',s['source_id'],s) for s in snapshot['sources']],{},POLICY)
        original=m.read(f.out/'phase_a.adjudicated.json');by_id={u['source_id']:u for u in original['units']};responses=[]
        for entry in plan['packets']:
            req=m.read(bundle/entry['file']);rows=[]
            for ident in req['task_ids']:
                unit=by_id[ident[len('source:'):]]
                rows.append({'task_ids':[ident],'value':{k:v for k,v in unit.items() if k not in {'source_id','source_sha256'}}})
            path=f.root/(entry['id']+'.json');m.save(path,{'packet_id':entry['id'],'request_sha256':req['request_sha256'],'reviewer':reviewer(),'results':rows});responses.append(path)
        result=f.root/'source-review.json';w.assemble_source(bundle,responses,result)
        seeded=w.seed_a(result,f.out,f.root/'seeded.json')
        self.assertEqual(seeded['pending_source_ids'],[])
        self.assertEqual(seeded['units'],original['units'])


class EfficientDraft(unittest.TestCase):
    def test_full_draft_inputs_and_real_pending_observations_survive_lossless_encoding(self):
        import prepare_revision_proposals as proposals
        import advisor_wire
        f=fixture.Pipeline();f.setUp();self.addCleanup(f.tearDown)
        while m.next_request(f.run):f.advance()
        before=m.sha(f.run/'final.json');protocol=m.read(f.run/'inputs/protocol.json')
        protocol['review_efficiency']=1;m.save(f.run/'inputs/protocol.json',protocol);m.freeze(f.run/'inputs')
        actual={'execution_reviews':[{'check_id':'synthetic:C1','status':'unknown','reason':'Synthetic unresolved execution observation','issues':[]}],'stage_scope_reviews':[]}
        m.save(f.run/'initial_review.json',actual)
        with patch.object(w,'validated_source_review',return_value=actual),patch.object(proposals.m,'next_request',return_value=None):
            path=proposals.prepare(f.run,f.root/'draft-efficient')
        payload=advisor_wire.unpack(json.loads(m.read(path)['prompt'].split('\nINPUT\n')[-1]))
        self.assertEqual(payload['manuscript'],m.read(f.run/'inputs/paper/body.json'))
        self.assertEqual(payload['coverage_and_pending']['initial_execution_observations']['checks'],actual['execution_reviews'])
        self.assertEqual(payload['verified_review']['findings'],m.read(f.run/'final.json')['findings'])
        self.assertEqual(m.sha(f.run/'final.json'),before)
        self.assertTrue(m.read(path.parent/'lossless_input_receipt.json')['complete_roundtrip'])


if __name__=='__main__':unittest.main()
