"""Contract regressions, not a claim of improved editorial judgment."""
import copy
import unittest
import test_pipeline as fixture
from test_pipeline import m, answer, A


class Multiscale(unittest.TestCase):
 setUp=fixture.Pipeline.setUp
 tearDown=fixture.Pipeline.tearDown
 advance=fixture.Pipeline.advance

 def review(self):
  self.advance()
  ctx=m.context_for(self.run,'reader')
  return ctx,answer('reader',ctx)

 def test_runtime_loads_checklist_only_for_planning_and_reader(self):
  self.assertIn('reader-checklist.md',m.next_request(self.run)['module_hashes'])
  self.advance()
  req=m.next_request(self.run)
  self.assertIn(m.multiscale.READER_SCHEMA,req['prompt'])
  checklist=(self.run/'inputs/skill/references/reader-checklist.md').read_text(encoding='utf-8')
  self.assertIn(m.dump(checklist),req['prompt'])
  for detail in ['Geometry and physical quantities','quantifiers','normalization','Object -> definition','Impact scope','Rewrite delivery']:
   self.assertIn(detail,checklist)
  for lane in ['technical','supplement_1','language']:
   req=m.prepare_stage_request(self.run,lane)
   self.assertNotIn('reader-checklist.md',req['module_hashes'])
   ctx=m.context_for(self.run,lane)
   self.assertNotIn('reader_scope_plan',ctx)
   self.assertNotIn('reader_multiscale',ctx)

 def test_plan_cannot_omit_or_prediagnose_reader_units(self):
  ctx=m.context_for(self.run,'objects');x=answer('objects',ctx)
  x['reader_scope_plan']=[]
  with self.assertRaisesRegex(ValueError,'missing scope unit'):m.validate('objects',x,ctx)
  x=answer('objects',ctx);x['reader_scope_plan'][0]['outcome']='gap'
  with self.assertRaisesRegex(ValueError,'pre-judge'):m.validate('objects',x,ctx)

 def test_missing_scale_and_unread_unit_cannot_claim_coverage(self):
  ctx,x=self.review();audit=x['reading_review']['multiscale']
  audit['units'][0]['status']='unfinished'
  with self.assertRaisesRegex(ValueError,'Unfinished unit'):m.validate('reader',x,ctx)
  audit['scales'][0]['status']='unfinished'
  m.validate('reader',x,ctx)
  audit['scales'].pop()
  with self.assertRaisesRegex(ValueError,'Seven-scale'):m.validate('reader',x,ctx)

 def test_sufficiency_requires_supported_checks_and_real_anchors(self):
  ctx,x=self.review();task=x['reading_review']['multiscale']['tasks'][0]
  task.update(outcome='sufficient',finding_ids=[])
  with self.assertRaisesRegex(ValueError,'supported sufficient checks'):m.validate('reader',x,ctx)
  x['findings']=[];x['checks'][0].update(judgment='sufficient',finding_ids=[])
  x['reading_review']['editorial'][0].update(decision='keep',action='Retain the current order.',
      reason='No alternative placement helps this synthetic sentence.',finding_ids=[])
  m.validate('reader',x,ctx)
  task['support']=[{'page':1,'quote':'Invented explanation'}]
  with self.assertRaisesRegex(ValueError,'Quote absent'):m.validate('reader',x,ctx)

 def test_editorial_plan_and_delivery_are_accounted_separately(self):
  ctx=m.context_for(self.run,'objects');plan=answer('objects',ctx)
  plan['reader_editorial_plan']=[]
  with self.assertRaisesRegex(ValueError,'Editorial plan omitted'):m.validate('objects',plan,ctx)
  ctx,x=self.review();x['reading_review']['editorial']=[]
  with self.assertRaisesRegex(ValueError,'Editorial audit target mismatch'):m.validate('reader',x,ctx)

 def test_v3_requires_a_specific_counterfactual_and_its_evaluation(self):
  ctx=m.context_for(self.run,'objects');plan=answer('objects',ctx)
  plan['reader_editorial_plan'][0].pop('candidate_alternative')
  with self.assertRaisesRegex(ValueError,'Missing editorial counterfactual'):m.validate('objects',plan,ctx)
  ctx,x=self.review();x['reading_review']['editorial'][0].pop('alternative_evaluation')
  with self.assertRaisesRegex(ValueError,'Missing editorial alternative evaluation'):m.validate('reader',x,ctx)

 def test_optional_editorial_judgment_needs_a_delivered_suggestion(self):
  ctx,x=self.review();row=x['reading_review']['editorial'][0]
  row.update(decision='optional_improvement',finding_ids=[],suggestion_ids=[])
  with self.assertRaisesRegex(ValueError,'Editorial improvement/suggestion mismatch'):
   m.multiscale.validate_editorial_review(x,ctx,{1:A['quote']},m.anchor,
       {c['id']:c for c in x['checks']},{f['id']:f for f in x['findings']},{}, {'U1'})

 def test_keep_arrangement_can_link_distinct_content_repair(self):
  ctx,x=self.review();row=x['reading_review']['editorial'][0]
  row.update(decision='keep',action='Retain this placement and complete the missing explanation here.',
      reason='Moving the passage would not supply the missing information.',finding_ids=[x['findings'][0]['id']])
  m.validate('reader',x,ctx)

 def test_discovered_unit_is_allowed_but_must_be_accounted(self):
  ctx,x=self.review()
  o=copy.deepcopy(fixture.O);o['id']='reader:O2';x['new_objects']=[o]
  c=copy.deepcopy(x['checks'][0]);c.update(id='reader:C2',object_id='reader:O2')
  x['checks'].append(c);x['findings'][0]['check_ids'].append(c['id'])
  audit=x['reading_review']['multiscale']
  unit=copy.deepcopy(ctx['reader_scope_plan'][0]);unit.update(id='U2',object_ids=['reader:O2'])
  audit['additional_units']=[unit]
  task=audit['tasks'][0];task['unit_ids'].append('U2');task['check_ids'].append(c['id'])
  with self.assertRaisesRegex(ValueError,'Unit coverage mismatch'):m.validate('reader',x,ctx)
  audit['units'].append({'unit_id':'U2','status':'checked','task_ids':['RT1'],'reason':'New dependency checked'})
  m.validate('reader',x,ctx)

 def test_default_cases_zero_match_retains_generic_scope_and_isolation(self):
  run=self.root/'with_cases'
  m.create_run(self.root/'paper',self.root/'knowledge',run)
  self.run=run;self.advance()
  routing=m.case_route_input(run)
  self.assertEqual(routing['reader_scope_plan'],m.read(run/'calls/objects/response.json')['reader_scope_plan'])
  self.assertEqual(routing['reader_editorial_plan'],m.read(run/'calls/objects/response.json')['reader_editorial_plan'])
  route={'source_plan_sha256':routing['source_plan_sha256'],'reader':[],'technical':[],
   'skipped_entries':[{'lane':lane,'entry_id':entry['id'],'reason':'Synthetic one-sentence fixture has no matching case task'} for lane in ['reader','technical'] for entry in routing[lane+'_index']['entries']]}
  m.freeze_case_route(run,route)
  ctx=m.context_for(run,'reader');x=answer('reader',ctx);x['case_usage']=[]
  self.assertEqual(ctx['goodpaper_cases']['complete_cases'],[])
  m.validate('reader',x,ctx)
  self.assertIn(m.multiscale.READER_SCHEMA,m.next_request(run)['prompt'])
  self.assertNotIn('reader_scope_plan',m.context_for(run,'supplement_1'))

 def test_old_section_protocol_does_not_acquire_new_contract(self):
  protocol=m.read(self.run/'inputs/protocol.json');protocol.pop('reader_multiscale')
  m.save(self.run/'inputs/protocol.json',protocol);m.freeze(self.run/'inputs')
  self.advance();req=m.next_request(self.run)
  self.assertNotIn('reader-checklist.md',req['module_hashes'])
  self.assertNotIn(m.multiscale.READER_SCHEMA,req['prompt'])
  ctx=m.context_for(self.run,'reader');x=answer('reader',ctx)
  self.assertNotIn('multiscale',x['reading_review']);m.validate('reader',x,ctx)


if __name__=='__main__':unittest.main()
