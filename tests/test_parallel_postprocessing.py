"""No-network tests of isolated, bounded post-processing waves and their barrier."""
import hashlib
import json
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import test_review_workflow as fixture
from test_execution_efficiency import authorization
import advisor_wire

m=fixture.m;w=fixture.w;runner=fixture.packet_runner


class ParallelPackets(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.bundle=self.root/'bundle';self.calls=self.root/'calls'
        self.source=self.root/'source.txt';self.source.write_text('complete unchanged source',encoding='utf-8')
        self.tasks=[w.task('target',str(i),{'text':'Complete source '+str(i)}) for i in range(5)]
        # Synthetic per-task output estimate forces five complete packets without lowering reserves.
        with patch.dict(w.OUTPUT_ESTIMATES,{'target':40000}):
            w.prepare_bundle(self.bundle,'delivery',{'page_images':[]},self.tasks,{str(self.source):m.sha(self.source)},fixture.POLICY)
        self.args=SimpleNamespace(model='synthetic-model',effort='xhigh',service_tier='default',attempt_name='fake')

    def answer(self,folder,prompt,images,**settings):
        self.assertEqual(settings['model'],self.args.model);self.assertEqual(settings['reasoning_effort'],self.args.effort)
        self.assertEqual(settings['service_tier'],'default');self.assertNotIn('UNIQUE_RETURNED_JUDGMENT',prompt)
        payload=advisor_wire.unpack(json.loads(prompt.rsplit('\nINPUT\n',1)[1]))
        source='original_stage_context' in payload
        response={'reviewer':{'name':'synthetic','kind':'synthetic_test','context_scope':'originals_and_full_manuscript' if source else 'frozen_a_and_final_outputs',
             'prior_outputs_seen':not source,'limits':'No model called'},'judgments':{},
             'results':[{'task_ids':[t['id']],'value':{'status':'unknown','reason':'UNIQUE_RETURNED_JUDGMENT'}} for t in payload['tasks']]}
        folder=Path(folder);folder.mkdir(parents=True,exist_ok=True);raw=folder/'final_text.json';m.save(raw,response)
        m.save(folder/'audit.json',{'model':settings['model'],'reasoning_effort':settings['reasoning_effort'],
             'requested_service_tier':settings['service_tier'],'images':[],'returncode':0,'fresh_ephemeral_context':True,
             'usage':[{'input_tokens':1,'output_tokens':1}],'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'output_sha256':m.sha(raw)})
        return raw,[{'input_tokens':1,'output_tokens':1}]

    def test_default_three_workers_all_tasks_exactly_once_and_cached_resume(self):
        barrier=threading.Barrier(3);guard=threading.Lock();active=0;maximum=0;seen=[]
        def sender(folder,*a,**kw):
            nonlocal active,maximum
            with guard:
                active+=1;maximum=max(maximum,active);seen.append(str(folder));first=len(seen)<=3
            try:
                if first:barrier.wait(timeout=10)
                return self.answer(folder,*a,**kw)
            finally:
                with guard:active-=1
        with patch.object(runner.codex_adapter,'invoke',side_effect=sender) as send:
            result=runner.execute_bundle(self.bundle,self.calls,self.args,authorization())
        self.assertEqual(maximum,3);self.assertEqual(send.call_count,5);self.assertEqual(len(set(seen)),5)
        self.assertTrue(result['ready_for_assembly']);self.assertEqual(result['complete_task_count'],5)
        self.assertFalse(result['downstream_started']);self.assertEqual(w.verify_bundle(self.bundle)['policy'],fixture.POLICY)
        values,_=w.collect(self.bundle,result['responses']);self.assertEqual(set(values),{t['id'] for t in self.tasks})
        with patch.object(runner.codex_adapter,'invoke',side_effect=AssertionError('Unexpected repeat')) as send:
            resumed=runner.execute_bundle(self.bundle,self.calls,self.args,authorization())
        send.assert_not_called();self.assertTrue(resumed['ready_for_assembly'])
        self.assertNotEqual(result['receipt'],resumed['receipt'])

    def test_failed_packet_keeps_others_no_retry_no_downstream(self):
        def sender(folder,*a,**kw):
            if Path(folder).parent.name=='delivery-002':raise ValueError('Synthetic uncertain attempt')
            return self.answer(folder,*a,**kw)
        with patch.object(runner.codex_adapter,'invoke',side_effect=sender) as send,patch.object(w,'assemble_delivery') as assemble:
            result=runner.execute_bundle(self.bundle,self.calls,self.args,authorization())
        self.assertEqual(send.call_count,5);assemble.assert_not_called()
        self.assertFalse(result['ready_for_assembly']);self.assertFalse(result['automatic_retry'])
        self.assertEqual(len(result['responses']),4);self.assertEqual(result['failed'][0]['packet_id'],'delivery-002')
        self.assertTrue(all(Path(p).exists() for p in result['responses']))
        self.assertFalse((self.calls/'bundle-execution.lock').exists())

    def test_all_inputs_checked_before_any_call(self):
        self.source.write_text('changed',encoding='utf-8')
        with patch.object(runner.codex_adapter,'invoke') as send,self.assertRaisesRegex(ValueError,'source changed'):
            runner.execute_bundle(self.bundle,self.calls,self.args,authorization())
        send.assert_not_called()

    def test_explicit_missing_judgment_cannot_release_barrier(self):
        def sender(folder,*a,**kw):
            raw,usage=self.answer(folder,*a,**kw)
            if Path(folder).parent.name=='delivery-003':
                data=m.read(raw);data['results']=[];m.save(raw,data)
            return raw,usage
        with patch.object(runner.codex_adapter,'invoke',side_effect=sender):
            result=runner.execute_bundle(self.bundle,self.calls,self.args,authorization())
        self.assertFalse(result['ready_for_assembly']);self.assertEqual(result['complete_task_count'],0)
        self.assertEqual(result['failed'][0]['phase'],'complete_result_collection')

    def test_duplicate_coordinator_does_not_submit(self):
        self.calls.mkdir();(self.calls/'bundle-execution.lock').write_text('existing coordinator')
        with patch.object(runner.codex_adapter,'invoke') as send,self.assertRaises(FileExistsError):
            runner.execute_bundle(self.bundle,self.calls,self.args,authorization())
        send.assert_not_called();self.assertTrue((self.calls/'bundle-execution.lock').exists())

    def test_source_wave_preserves_source_only_context(self):
        self.bundle=self.root/'source-bundle'
        tasks=[w.task('source','reader:F'+str(i),{'stage':'reader','original':'Complete original'}) for i in range(3)]
        with patch.dict(w.OUTPUT_ESTIMATES,{'source':40000}):
            w.prepare_bundle(self.bundle,'source',{'page_images':[],
                 'original_stage_context':[{'stage':'reader','original':'Frozen original checks only'}]},tasks,
                 {str(self.source):m.sha(self.source)},fixture.POLICY)
        def sender(folder,prompt,*a,**kw):
            payload=advisor_wire.unpack(json.loads(prompt.rsplit('\nINPUT\n',1)[1]))
            self.assertNotIn('frozen_a',payload);self.assertNotIn('final_targets',payload)
            return self.answer(folder,prompt,*a,**kw)
        with patch.object(runner.codex_adapter,'invoke',side_effect=sender) as send:
            result=runner.execute_bundle(self.bundle,self.calls,self.args,authorization())
        self.assertTrue(result['ready_for_assembly'],result['failed']);self.assertEqual(send.call_count,3)
        self.assertEqual(result['complete_task_count'],3)


if __name__=='__main__':unittest.main()
