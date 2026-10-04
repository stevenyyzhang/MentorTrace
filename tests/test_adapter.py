"""Provider behavior with synthetic payloads and a local fake sender; no network."""
import importlib.util
import json
import sys
from pathlib import Path
import unittest
import test_pipeline as t

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import model_adapter as a

class Adapter(unittest.TestCase):
 def setUp(self):
  self.fixture=t.Pipeline();self.fixture.setUp();self.run=self.fixture.run
  self.settings={'enabled':True,'model':'synthetic-model','context_window':10000,'max_output_tokens':1000,'safety_margin_tokens':100}
  self.project={'model_calls_enabled':True};self.calls=[]
 def tearDown(self):self.fixture.tearDown()
 def fake(self,path,payload):
  self.calls.append((path,payload))
  if path.endswith('input_tokens'):return {'input_tokens':100}
  return {'status':'completed','id':'synthetic-response','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(t.answer('objects',{}))}]}],'usage':{'input_tokens':100,'output_tokens':50}}
 def test_disabled_makes_no_requests(self):
  with self.assertRaisesRegex(ValueError,'disabled'):a.run_one(self.run,self.settings,project={'model_calls_enabled':False},sender=self.fake)
  self.assertEqual(self.calls,[])
 def test_paused_run_makes_no_requests(self):
  self.project['paused_run_paths']=[str(self.run)]
  with self.assertRaisesRegex(ValueError,'paused'):a.run_one(self.run,self.settings,project=self.project,sender=self.fake)
  self.assertEqual(self.calls,[])
 def test_preflight_fresh_context_and_usage(self):
  a.run_one(self.run,self.settings,project=self.project,sender=self.fake)
  self.assertEqual([c[0] for c in self.calls],['/responses/input_tokens','/responses'])
  payload=self.calls[-1][1]
  self.assertNotIn('previous_response_id',payload);self.assertNotIn('conversation',payload)
  self.assertEqual(payload['tools'],[]);self.assertEqual(payload['truncation'],'disabled')
  self.assertEqual(t.m.read(self.run/'calls/objects/transport.json')['usage']['output_tokens'],50)
 def test_overflow_never_generates(self):
  self.settings['context_window']=1150
  with self.assertRaisesRegex(ValueError,'Context budget'):a.run_one(self.run,self.settings,project=self.project,sender=self.fake)
  self.assertEqual(len(self.calls),1)
 def test_network_uncertainty_not_retried(self):
  def failing(path,payload):raise TimeoutError()
  with self.assertRaises(TimeoutError):a.run_one(self.run,self.settings,project=self.project,sender=failing)
  with self.assertRaisesRegex(ValueError,'Previous provider'):a.run_one(self.run,self.settings,project=self.project,sender=self.fake)
  self.assertEqual(self.calls,[])
 def test_incomplete_provider_not_accepted(self):
  def incomplete(path,payload):return {'input_tokens':100} if path.endswith('input_tokens') else {'status':'incomplete','output':[]}
  with self.assertRaisesRegex(ValueError,'incomplete'):a.run_one(self.run,self.settings,project=self.project,sender=incomplete)
  self.assertEqual(t.m.read(self.run/'state.json')['completed'],[])

if __name__=='__main__':unittest.main(verbosity=2)
