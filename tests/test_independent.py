"""Offline request-boundary and provenance regression; no model/network calls."""
import copy
import json
import unittest
import test_pipeline as fixture
from test_pipeline import m, answer

class Independent(unittest.TestCase):
 setUp=fixture.Pipeline.setUp
 tearDown=fixture.Pipeline.tearDown
 advance=fixture.Pipeline.advance

 def test_advisor_before_planning_and_no_prior_findings(self):
  req=m.prepare_stage_request(self.run,'supplement_1')
  ctx=json.loads(req['prompt'].split('\nINPUT\n')[1])
  self.assertEqual(set(ctx),{'manuscript','cards'})
  self.assertEqual(req['object_ids'],[])
  self.advance();self.advance();self.advance()
  self.assertEqual(req,m.next_request(self.run))

 def test_unknown_or_rewritten_or_unanswered_relation_rejected(self):
  ctx=m.context_for(self.run,'supplement_1');base=answer('supplement_1',ctx)
  for change in ['unknown','rewrite','unanswered']:
   x=copy.deepcopy(base)
   if change=='unknown':x['checks'][0]['relation_id']='O1'
   if change=='rewrite':x['checks'][0]['required_relation']='weaker claim'
   if change=='unanswered':x['checks']=[]
   with self.assertRaises(ValueError):m.validate('supplement_1',x,ctx)

 def test_separate_relations_and_unfinished_state_survive(self):
  for _ in range(3):self.advance()
  ctx=m.context_for(self.run,'supplement_1');x=answer('supplement_1',ctx)
  relation=copy.deepcopy(x['relations'][0]);relation.update(id='supplement_1:R2',relation='distinct unanswered relation');x['relations'].append(relation)
  check=copy.deepcopy(x['checks'][0]);check.update(id='supplement_1:C2',relation_id=relation['id'],execution='unfinished',judgment=None,finding_ids=[]);x['checks'].append(check)
  m.accept_response(self.run,x)
  folder=self.run/'calls/supplement_1'
  self.assertEqual(m.read(folder/'raw_response.json'),x)
  accepted=m.read(folder/'response.json')
  self.assertEqual(accepted['checks'][1]['required_relation'],relation['relation'])
  self.assertIsNone(accepted['checks'][1]['judgment'])
  self.assertTrue((folder/'adapter_map.json').exists())
  m.save(folder/'raw_response.json',{})
  with self.assertRaisesRegex(ValueError,'Original response changed'):m.next_request(self.run)

 def test_semantic_mismatch_is_not_certified_by_schema(self):
  ctx=m.context_for(self.run,'supplement_1');x=answer('supplement_1',ctx)
  x['findings']=[];x['checks'][0].update(judgment='sufficient',finding_ids=[],reason='Answers an unrelated question')
  m.validate('supplement_1',x,ctx)  # Deliberate limitation: no semantic truth oracle.

 def test_legacy_protocol_stays_planner_fed(self):
  p=self.run/'inputs/protocol.json';protocol=m.read(p);protocol.pop('workflow_version');m.save(p,protocol);m.freeze(self.run/'inputs')
  self.advance()
  ctx=m.context_for(self.run,'supplement_1')
  self.assertIn('objects',ctx)
  req=m.prepare_stage_request(self.run,'supplement_1')
  self.assertEqual(req['object_ids'],['O1'])

 def test_manifest_batches_not_fixed_four(self):
  cards=m.read(self.root/'source.json')
  cards += [{**copy.deepcopy(cards[0]),'id':'T4'}]
  m.save(self.root/'five.json',cards)
  m.import_knowledge(self.root/'five.json',self.root/'five',batch_size=2)
  run=self.root/'five-run';m.create_run(self.root/'paper',self.root/'five',run,goodpaper_cases=False)
  p=m.read(run/'inputs/protocol.json')
  self.assertEqual(p['concern_count'],5)
  self.assertEqual(sum(s.startswith('supplement_') for s in p['stages']),3)
  seen=[]
  for n in range(1,4):seen+=m.prepare_stage_request(run,f'supplement_{n}')['card_ids']
  self.assertEqual(seen,[c['id'] for c in cards])

 def test_manifest_corruption_rejected_before_run_creation(self):
  k=self.root/'knowledge';manifest=m.read(k/'manifest.json');manifest['batches'].pop();m.save(k/'manifest.json',manifest);m.freeze(k)
  dest=self.root/'bad'
  with self.assertRaisesRegex(ValueError,'coverage'):m.create_run(self.root/'paper',k,dest)
  self.assertFalse(dest.exists())

 def test_evidence_ceiling_preserves_pending(self):
  p=self.run/'inputs/protocol.json';v=m.read(p);v['max_evidence_calls']=0;m.save(p,v);m.freeze(self.run/'inputs')
  for _ in range(3):self.advance()
  x=answer('supplement_1',m.context_for(self.run,'supplement_1'));x['evidence_requests']=[{'card_id':'T0','reason':'missing history'}]
  m.accept_response(self.run,x)
  with self.assertRaisesRegex(ValueError,'budget exhausted'):m.next_request(self.run)
  self.assertEqual(len(m.read(self.run/'state.json')['pending_evidence']),1)

if __name__=='__main__':unittest.main()
