"""Offline complete-input capacity and partition contracts; no model quality claim."""
import copy
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import test_pipeline as fixture
from test_review_workflow import POLICY
from test_execution_efficiency import authorization
import request_capacity as cap
import stage_capacity as split
import run_authorized_stage as runner
import draft_capacity
import run_prepared_draft
import tempfile

m=fixture.m


class CompleteCapacity(unittest.TestCase):
    def setUp(self):
        self.f=fixture.Pipeline();self.f.setUp();self.addCleanup(self.f.tearDown)
        p=m.read(self.f.run/'inputs/protocol.json');p['request_capacity']=1;p['max_prompt_bytes']=1
        m.save(self.f.run/'inputs/protocol.json',p);m.freeze(self.f.run/'inputs')
        m.save(self.f.run/'automatic_capacity.json',POLICY)

    def test_all_stages_ignore_legacy_bytes_and_roundtrip_whole_context(self):
        seen=[]
        while m.next_request(self.f.run):
            req=m.next_request(self.f.run);stage=req['stage'];seen.append(stage)
            self.assertGreater(req['utf8_bytes'],1)
            wire=json.loads(req['prompt'].rsplit('\nINPUT\n',1)[1])
            decoded=cap.advisor_wire.unpack(wire)
            self.assertEqual(decoded['context'],m.context_for(self.f.run,stage))
            self.assertTrue(cap.preflight(req,POLICY)['fits'])
            self.f.advance()
        self.assertIn('reader',seen);self.assertIn('verify',seen)

    def test_above_950000_bytes_is_not_a_capacity_failure(self):
        request={'stage':'reader','prompt':'汉'*330000,'images':[]}
        policy={**POLICY,'effective_context':2000000,'context_window':2000000}
        result=cap.preflight(request,policy)
        self.assertGreater(result['utf8_bytes'],950000)
        self.assertLess(result['prompt_chars'],1048576)
        self.assertFalse(result['legacy_byte_limit_applied'])

    def test_true_token_and_transport_overflow_still_rejected(self):
        req={'prompt':'hello','images':[]}
        for policy in [{**POLICY,'effective_context':1},{**POLICY,'max_prompt_chars':4}]:
            with self.assertRaisesRegex(ValueError,'actual capacity'):cap.preflight(req,policy)
        with self.assertRaisesRegex(ValueError,'detected'):cap.preflight(req,None)

    def test_all_images_and_reserves_count(self):
        req={'prompt':'hello','images':[{'sha256':str(n)} for n in range(6)]}
        result=cap.preflight(req,POLICY)
        self.assertEqual(result['total_reserved'],6+6*6000+8000+64000)
        self.assertEqual(result['policy'],POLICY)

    def test_lossless_shared_modules_and_context(self):
        phrase='Exact condition with exceptions. '*300
        value={'modules':{'rule':phrase},'context':{'manuscript':[phrase], 'sources':[phrase]*4}}
        wire=cap.encode(value)
        self.assertEqual(cap.advisor_wire.unpack(json.loads(wire)),value)
        self.assertLess(len(wire),len(json.dumps(value)))


class ConsolidationPartitions(unittest.TestCase):
    def setUp(self):
        self.f=fixture.Pipeline();self.f.setUp();self.addCleanup(self.f.tearDown)
        p=m.read(self.f.run/'inputs/protocol.json');p['request_capacity']=1
        m.save(self.f.run/'inputs/protocol.json',p);m.freeze(self.f.run/'inputs')
        while m.next_request(self.f.run)['stage']!='merge':self.f.advance()
        self.ctx=m.context_for(self.f.run,'merge')
        # Unique large complete source requirements force actual partitioning.
        for n,item in enumerate(self.ctx['input_findings']):
            item['gap']=' '.join(f'{n}-{i}' for i in range(1800))
        self.policy={**POLICY,'max_prompt_chars':70000}

    def plan(self):
        req=m.prepare_stage_request(self.f.run,'merge',_context_override=self.ctx,_planning=True)
        path=split.prepare(self.f.run,'merge',self.ctx,req,self.policy)
        return m.read(self.f.run/path)

    def test_complete_inputs_partitioned_once_full_evidence_repeated(self):
        plan=self.plan();self.assertGreater(len(plan['parts']),1)
        self.assertFalse(plan['user_confirmation_required'])
        found=[]
        for part in plan['parts']:
            c=part['context'];found+=c['input_findings']
            self.assertEqual(c['manuscript'],self.ctx['manuscript'])
            self.assertEqual(c['checks'],self.ctx['checks'])
            cap.preflight(part['request'],self.policy)
        self.assertEqual(found,self.ctx['input_findings'])
        result=split.combine('merge',[(fixture.answer('merge',p['context']),p['context']) for p in plan['parts']],self.ctx)
        self.assertEqual(len(result['dispositions']),len(found))
        self.assertEqual(len(result['findings']),len(plan['parts']))

    def test_missing_part_not_implicitly_reviewed(self):
        plan=self.plan()
        with self.assertRaisesRegex(ValueError,'disposition'):
            split.combine('merge',[(fixture.answer('merge',p['context']),p['context']) for p in plan['parts'][:-1]],self.ctx)

    def test_normal_preparation_automatically_routes_overflow_and_resumes(self):
        # No submission occurred in this synthetic fixture. Start at first preparation.
        (self.f.run/'calls/merge/request.json').unlink()
        m.save(self.f.run/'automatic_capacity.json',self.policy)
        with patch.object(m,'context_for',return_value=self.ctx):
            request=m.prepare_stage_request(self.f.run,'merge')
            self.assertEqual(request,m.prepare_stage_request(self.f.run,'merge'))
        self.assertEqual(request['capacity_plan'],'capacity_plans/merge/plan.json')

    def test_no_truncation_when_complete_shared_evidence_cannot_fit(self):
        self.policy={**self.policy,'max_prompt_chars':10}
        with self.assertRaisesRegex(ValueError,'no evidence removed'):self.plan()
        self.assertEqual(m.read(self.f.run/'capacity_checks/merge.obstacle.json')['status'],'infeasible')

    def test_automatic_execution_preserves_raw_and_composite_provenance(self):
        plan=self.plan();req={**plan['canonical_request'],'capacity_plan':'capacity_plans/merge/plan.json'}
        args=SimpleNamespace(auto_capacity=self.policy,model='synthetic-model',effort='xhigh',service_tier='default',attempt_name='fake')
        def invoke(folder,prompt,images,**kwargs):
            c=cap.advisor_wire.unpack(json.loads(prompt.rsplit('\nINPUT\n',1)[1]))['context']
            out=Path(folder)/'final_text.json';m.save(out,fixture.answer('merge',c))
            return out,[{'input_tokens':1,'output_tokens':1}]
        with patch.object(split.m,'context_for',return_value=self.ctx),patch.object(runner.codex_adapter,'invoke',side_effect=invoke) as send:
            result=runner.execute_request(self.f.run,req,args,authorization())
        self.assertEqual(send.call_count,len(plan['parts']))
        self.assertEqual(len(result['capacity_parts']),send.call_count)
        for row in result['capacity_parts']:self.assertEqual(m.sha(row['raw_path']),row['raw_sha256'])
        self.assertTrue(m.read(Path(result['model_output']).parent/'audit.json')['not_a_single_model_output'])


class DraftPartitions(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.out=Path(self.tmp.name)
        m.save(self.out/'inputs/verified.json',{});m.freeze(self.out/'inputs')
        self.payload={'manuscript':[{'page':n,'text':'The receiver observes y.'} for n in range(1,5)],
            'writing_evidence_linked_sources_not_target_facts':{'writing_transfers':[],'raw_to_final':[]},
            'verified_review':{'findings':[{'id':f'verify:F{n}','anchor':{'page':n,'quote':'The receiver observes y.'},
                'gap':' '.join(f'{n}-{i}' for i in range(1000))} for n in range(1,5)]},'coverage_and_pending':{'all':'complete'}}
        self.policy={**POLICY,'max_prompt_chars':10000}
        self.request={'stage':'revision_proposals','prompt':'synthetic full request','images':[]}
        m.save(self.out/'automatic_capacity.json',self.policy)

    def plan(self):
        path=draft_capacity.prepare(self.out,'Synthetic rules',self.payload,[],self.policy,self.request)
        m.save(self.out/'request.json',{**self.request,'capacity_plan':path})
        return m.read(self.out/path)

    def response(self,part):
        ids=part['assigned_ids'];num=part['payload']['draft_partition']['part'];text='Synthetic complete repair '+', '.join(ids)
        return {'report_markdown':text,'delivery_map':[{'verified_id':i} for i in ids],
            'revision_actions':[{'draft_label':f'P{num}_D','verified_ids':ids}],
            'revision_attribution':[{'verified_id':i,'basis':'target_analysis','case_ids':[],'card_ids':[],
                'transfer_ids':[],'report_excerpt':text,'use_explanation':'Synthetic target analysis',
                'target_support':[{'page':1,'quote':'The receiver observes y.'}]} for i in ids], 'limits':[]}

    def test_partition_preserves_complete_shared_sources_and_all_targets(self):
        plan=self.plan();self.assertEqual(len(plan['parts']),4)
        for part in plan['parts']:
            self.assertEqual(part['payload']['manuscript'],self.payload['manuscript'])
            self.assertEqual(part['payload']['writing_evidence_linked_sources_not_target_facts'],self.payload['writing_evidence_linked_sources_not_target_facts'])
            cap.preflight(part['request'],self.policy)
        result=draft_capacity.combine([self.response(p) for p in plan['parts']],plan)
        self.assertEqual(len(result['delivery_map']),4)
        for part in plan['parts']:self.assertIn(self.response(part)['report_markdown'],result['report_markdown'])
        with self.assertRaisesRegex(ValueError,'Missing draft'):draft_capacity.combine([],plan)

    def test_same_page_changes_are_not_separated_to_force_fit(self):
        for row in self.payload['verified_review']['findings']:row['anchor']['page']=1
        with self.assertRaisesRegex(ValueError,'no content removed'):self.plan()
        self.assertFalse(m.read(self.out/'capacity_obstacle.json')['user_confirmation_required'])

    def test_missing_target_not_passed_and_runner_uses_no_confirmation(self):
        plan=self.plan();results=[self.response(p) for p in plan['parts']]
        bad=copy.deepcopy(results);bad[0]['delivery_map']=[]
        with self.assertRaisesRegex(ValueError,'coverage'):draft_capacity.combine(bad,plan)
        def invoke(folder,prompt,images,**kwargs):
            data=cap.advisor_wire.unpack(json.loads(prompt.rsplit('\nINPUT\n',1)[1]))
            part=plan['parts'][data['draft_partition']['part']-1]
            out=Path(folder)/'final_text.json';m.save(out,self.response(part));return out,[{}]
        args=SimpleNamespace(model='synthetic-model',effort='xhigh',service_tier='default',attempt_name='fake')
        with patch.object(run_prepared_draft.codex_adapter,'invoke',side_effect=invoke) as sender:
            output=run_prepared_draft.execute(self.out,args,authorization())
        self.assertEqual(sender.call_count,4)
        self.assertEqual(m.read(output),draft_capacity.combine(results,plan))
        self.assertTrue(m.read(self.out/'submission_receipt.json')['complete_delivery_audits_required'])

    def test_single_draft_runner_still_validates_source_coverage(self):
        m.save(self.out/'request.json',self.request)
        m.save(self.out/'inputs/verified.json',self.payload['verified_review'])
        m.save(self.out/'inputs/writing_evidence.json',self.payload['writing_evidence_linked_sources_not_target_facts'])
        m.save(self.out/'inputs/paper/body.json',self.payload['manuscript']);m.freeze(self.out/'inputs')
        part={'assigned_ids':[f['id'] for f in self.payload['verified_review']['findings']],
              'payload':{'draft_partition':{'part':1}}}
        def invoke(folder,*unused,**kwargs):
            out=Path(folder)/'final_text.json';m.save(out,self.response(part));return out,[{}]
        args=SimpleNamespace(model='synthetic-model',effort='xhigh',service_tier='default',attempt_name='fake')
        with patch.object(run_prepared_draft.codex_adapter,'invoke',side_effect=invoke) as sender:
            result=run_prepared_draft.execute(self.out,args,authorization())
        self.assertEqual(sender.call_count,1);self.assertEqual(len(m.read(result)['delivery_map']),4)


if __name__=='__main__':unittest.main()
