"""Synthetic contract tests. These do not measure manuscript review quality."""
import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location('mt',Path(__file__).resolve().parents[1]/'scripts/mentortrace_v1.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
A={'page':1,'quote':'The receiver observes y.'}
O={'id':'O1','anchor':A,'relation':'observation -> detector input','passage_job':'state information conditions','lanes':['reader','technical','supplement']}

def answer(stage,ctx):
 if stage=='language':return {'coverage':[{'unit_id':u['id'],'status':'checked','reason':'synthetic clean text','finding_ids':[]} for u in ctx['text_units']],'findings':[],'uncertain_items':[],'optional_suggestions':[],'limits':[]}
 if stage=='objects':return {'technical_configurations':[{'id':'K1','object_ids':['O1'],'anchors':[A],'configuration':'receiver observation','operation':'detector input','question':'Is observation accessible?'}],'technical_configuration_exclusions':[],'objects':[copy.deepcopy(O)],'section_jobs':[{'pages':[1],'job':'model','object_ids':['O1']}],'reader_scope_plan':[{'id':'U1','anchors':[A],'chapter_tasks':['system_model'],'scales':['reading_point'],'task':'Reconstruct receiver input','object_ids':['O1']}], 'reader_editorial_plan':[{'id':'E1','unit_ids':['U1'],'focus':'first_use','anchors':[A],'question':'Is the observation available before the detector uses it?','candidate_alternative':{'operation':'add','source':'receiver observation sentence','destination':'immediately before detector use','expected_reader_gain':'supply input availability','possible_cost':'one explanatory clause'}}], 'reader_editorial_exclusions':[],'limits':[]}
 if stage in ['merge','verify']:
  f={'id':stage+':F1','anchor':A,'relation':'observation -> detector input','gap':'SYNTHETIC_GAP_SENTINEL','impact':'execution unknown','closure_goal':'identify input','new_in_stage':False}
  return {'findings':[f],'dispositions':[{'input_id':i['id'],'status':'merged' if stage=='merge' else 'retained','output_ids':[f['id']],'reason':'same synthetic relation','evidence':[]} for i in ctx['input_findings']],'limits':[]}
 cards=ctx.get('cards',[]);cid=stage+':C1';fid=stage+':F1'
 result={'new_objects':[],'checks':[{'id':cid,'object_id':'O1','anchor':A,'execution':'completed','judgment':'gap','author_explanation':'observes y','required_relation':'observation -> detector input','counterevidence':[],'reason':'fixture gap','card_ids':[c['id'] for c in cards],'finding_ids':[fid],'local_support':[],'later_support':[]}],
  'findings':[{'id':fid,'object_id':'O1','anchor':A,'relation':'observation -> detector input','gap':'SYNTHETIC_GAP_SENTINEL','impact':'execution unknown','closure_goal':'identify input','check_ids':[cid]}],
  'card_dispositions':[{'card_id':c['id'],'state':'linked','object_ids':['O1'],'reason':'fixture relation'} for c in cards], 'evidence_requests':[],'limits':[]}
 if stage=='technical' and ctx.get('technical_applicability'):
  result['configuration_review']={'additional_configurations':[],'items':[{'configuration_id':'K1','case_values':'receiver observes y','required_condition':'input access','evaluation':'Input access is unspecified.','evidence':[A],'outcome':'gap','check_ids':[cid],'finding_ids':[fid]}],'limits':[]}
 if stage=='reader' and ctx.get('section_review'):
  result['reading_review']={'sections':[{'anchor':A,'section_job':'model','paragraph_roles':[{'anchor':A,'role':'observation','connection':'supplies detector input'}],'synthesis':'Defines the observation.','selection':'Retain required observation.','check_ids':[cid]}], 'whole_paper':{'account':'Observation feeds detector.','summary_links':[{'anchor':A,'support':[A],'assessment':'Same scope.'}],'check_ids':[cid]},'limits':[]}
 if stage=='reader' and ctx.get('reader_multiscale'):
  result['reading_review']['multiscale']={'additional_units':[],
   'tasks':[{'id':'RT1','unit_ids':['U1'],'scales':['reading_point'],'relation_type':'observation -> input','endpoints':[{'anchor':A,'role':'observation'},{'anchor':A,'role':'input'}],'reader_task':'Reconstruct input','reconstruction':'Observation named; input access unresolved.','support':[A],'missing_information':'input access','outcome':'required_repair','check_ids':[cid],'finding_ids':[fid],'suggestion_ids':[]}],
   'units':[{'unit_id':'U1','status':'checked','task_ids':['RT1'],'reason':'Synthetic input relation inspected'}],
   'scales':[{'scale':scale,'status':'checked' if scale=='reading_point' else 'not_applicable','task_ids':['RT1'] if scale=='reading_point' else [],'reason':'One-sentence synthetic fixture; no larger textual structure'} for scale in m.multiscale.SCALES]}
  if ctx['reader_multiscale']>=2:
   result['reading_review']['editorial_additions']=[]
   result['reading_review']['editorial']=[{'plan_id':'E1','decision':'required_repair','evidence':[A],
    'current_arrangement':'The observation is named before its use.','reader_effect':'The source remains unknown at first use.',
    'action':'Explain the input source at first use.','reason':'The detector needs an available input.',
    'finding_ids':[fid],'suggestion_ids':[]}]
   if ctx['reader_multiscale']>=3:
    result['reading_review']['editorial'][0]['alternative_evaluation']={'tested_change':'Add the input source before detector use.',
      'reader_gain':'Clarifies the detector input.','reader_cost':'Adds one clause.',
      'verdict_reason':'The gain is necessary for interpreting the observation.'}
 if stage.startswith('supplement_') and 'objects' not in ctx:
  rid=stage+':R1';result.pop('new_objects')
  result['relations']=[{'id':rid,'anchor':A,'relation':'observation -> detector input','passage_job':'information conditions'}]
  for c in result['checks']:
   c.pop('object_id');c.pop('required_relation');c['relation_id']=rid
  for f in result['findings']:f.pop('object_id');f['relation_id']=rid
  for d in result['card_dispositions']:d.pop('object_ids');d['relation_ids']=[rid]
 elif stage.startswith('evidence_'):
  for o in ctx['objects']:
   if o['id']=='O1':continue
   c=copy.deepcopy(result['checks'][0]);c['id']=stage+':C'+str(len(result['checks'])+1);c['object_id']=o['id']
   result['checks'].append(c);result['findings'][0]['check_ids'].append(c['id'])
 return result

class Pipeline(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  cards=[{'id':f'T{i}',**{k:{'text':'fixture','basis':'synthetic','source_ids':[]} for k in m.FIELDS},'evidence_status':{'original_comments':[],'version_evidence':['long fixture'],'transitions':[]}} for i in range(4)]
  m.save(self.root/'source.json',cards);m.import_knowledge(self.root/'source.json',self.root/'knowledge',expected=4,batch_size=1)
  paper=self.root/'paper';m.save(paper/'body.json',[{'page':1,'text':A['quote']}])
  m.save(paper/'manifest.json',{'role':'review_manuscript','images':[]});m.freeze(paper)
  self.run=self.root/'run';m.create_run(paper,self.root/'knowledge',self.run,goodpaper_cases=False)
 def tearDown(self):self.tmp.cleanup()
 def advance(self):
  r=m.next_request(self.run);x=answer(r['stage'],m.context_for(self.run,r['stage']))
  m.accept_response(self.run,x,{'kind':'synthetic_fixture','model_called':False});return r,x
 def test_all_nine_stages_and_isolation(self):
  for stage in m.STAGES:
   r=m.next_request(self.run);self.assertEqual(r,m.next_request(self.run))
   self.assertEqual(r['stage'],stage)
   if stage in m.STAGES[1:7]:self.assertNotIn('SYNTHETIC_GAP_SENTINEL',r['prompt'])
   if stage.startswith('supplement'):self.assertEqual(len(r['card_ids']),1)
   if stage=='merge':self.assertTrue((self.run/'RAW_FREEZE.json').exists())
   if stage=='verify':self.assertNotIn('"judgment":',r['prompt'])
   self.advance()
  self.assertIsNone(m.next_request(self.run));self.assertEqual(len(m.read(self.run/'findings_raw.json')),6)
  self.assertEqual(m.read(self.run/'state.json')['status'],'complete')
 def test_variable_batch_count_preserves_coverage(self):
  run=self.root/'adaptive';m.create_run(self.root/'paper',self.root/'knowledge',run,[['T0','T1','T2'],['T3']],goodpaper_cases=False);self.run=run
  seen=[]
  while m.next_request(run):
   req,_=self.advance()
   if req['stage'].startswith('supplement_'):seen+=req['card_ids']
  self.assertEqual(seen,['T0','T1','T2','T3'])
  self.assertEqual(len(m.read(run/'state.json')['completed']),8)
  m.export_report(run)
 def test_independent_prefetch_request_unchanged_after_other_branches(self):
  self.advance();prefetched=m.prepare_stage_request(self.run,'supplement_1')
  self.advance();self.advance()
  self.assertEqual(prefetched,m.next_request(self.run))
  self.assertNotIn('SYNTHETIC_GAP_SENTINEL',prefetched['prompt'])
 def test_generic_arm_has_no_advisor_package(self):
  run=self.root/'generic';m.create_generic_run(self.root/'paper',run,2);self.run=run
  self.assertFalse((run/'inputs/knowledge/archive.json').exists())
  self.assertFalse((run/'inputs/skill/references/advisor-evidence.md').exists())
  while m.next_request(run):
   req,_=self.advance();self.assertEqual(req['card_ids'],[])
   self.assertNotIn('long fixture',req['prompt'])
  m.export_report(run)
 def test_input_tamper_rejected(self):
  m.save(self.run/'inputs/paper/body.json',[])
  with self.assertRaisesRegex(ValueError,'Frozen input changed'):m.next_request(self.run)
 def test_completed_response_tamper_rejected(self):
  self.advance();m.save(self.run/'calls/objects/response.json',{})
  with self.assertRaisesRegex(ValueError,'Completed response changed'):m.next_request(self.run)
 def test_planner_judgment_rejected(self):
  x=answer('objects',{});x['objects'][0]['judgment']='gap'
  with self.assertRaisesRegex(ValueError,'pre-judge'):m.accept_response(self.run,x)
  self.assertTrue((self.run/'calls/objects/rejected.json').exists())
 def test_omitted_object_rejected(self):
  self.advance();ctx=m.context_for(self.run,'reader');x=answer('reader',ctx);x['checks']=[]
  with self.assertRaisesRegex(ValueError,'silently omitted'):m.validate('reader',x,ctx)
 def test_card_omission_rejected(self):
  self.advance();ctx=m.context_for(self.run,'supplement_1');x=answer('supplement_1',ctx);x['card_dispositions']=[]
  with self.assertRaisesRegex(ValueError,'card accounting'):m.validate('supplement_1',x,ctx)
 def test_wrong_quote_rejected(self):
  x=answer('objects',{});x['objects'][0]['anchor']={'page':1,'quote':'Not in paper'}
  with self.assertRaisesRegex(ValueError,'Quote absent'):m.validate('objects',x,m.context_for(self.run,'objects'))
 def test_pdf_quote_normalization_preserves_operators(self):
  m.anchor({'page':1,'quote':'the parameter'}, {1:'the para-\nmeter'})
  with self.assertRaises(ValueError):m.anchor({'page':1,'quote':'x+y'}, {1:'x-y'})
 def test_disposition_omission_rejected(self):
  ctx={'manuscript':[{'page':1,'text':A['quote']}],'input_findings':[{'id':'reader:F1'}]};x=answer('merge',ctx);x['dispositions']=[]
  with self.assertRaisesRegex(ValueError,'disposition'):m.validate('merge',x,ctx)
 def test_withdrawal_requires_real_anchor(self):
  ctx={'manuscript':[{'page':1,'text':A['quote']}],'input_findings':[{'id':'reader:F1'}]}
  x={'findings':[],'dispositions':[{'input_id':'reader:F1','status':'withdrawn','output_ids':[],'reason':'answered','evidence':[{'page':1,'quote':'invented answer'}]}]}
  with self.assertRaisesRegex(ValueError,'Quote absent'):m.validate('merge',x,ctx)
  x['dispositions'][0]['evidence']=[A];m.validate('merge',x,ctx)
 def test_deferred_evidence_loaded_and_completed(self):
  for _ in range(3):self.advance()
  ctx=m.context_for(self.run,'supplement_1');x=answer('supplement_1',ctx)
  x['evidence_requests']=[{'card_id':'T0','reason':'need longitudinal evidence'}]
  m.accept_response(self.run,x)
  request=m.next_request(self.run)
  self.assertEqual(request['stage'],'evidence_1');self.assertEqual(request['card_ids'],['T0'])
  self.assertIn('long fixture',request['prompt']);self.advance()
  while m.next_request(self.run):self.advance()
  self.assertEqual(len(m.read(self.run/'findings_raw.json')),7)
  m.export_report(self.run);self.assertEqual(len(m.read(self.run/'trace.json')['raw_to_final']),7)
 def test_retry_preserves_failed_response(self):
  x=answer('objects',{});x['objects'][0]['judgment']='gap'
  with self.assertRaises(ValueError):m.accept_response(self.run,x)
  m.retry_failed(self.run)
  archived=self.run/'calls/objects/attempts/1'
  self.assertEqual(m.read(archived/'raw_response.json'),x);m.verify_frozen(archived)
  self.advance();self.assertEqual(m.next_request(self.run)['stage'],'reader')
 def test_invalid_json_preserved_and_retryable(self):
  p=self.root/'bad.json';p.write_text('{bad',encoding='utf-8')
  with self.assertRaises(ValueError):m.accept_response(self.run,p)
  m.retry_failed(self.run);self.advance()
 def test_target_provenance_rejected(self):
  cards=m.read(self.root/'source.json');cards[0]['evidence_status']['training_exposed_group']='SYNTHETIC_GROUP_A'
  m.save(self.root/'source.json',cards)
  with self.assertRaisesRegex(ValueError,'Training-exposure'):m.import_knowledge(self.root/'source.json',self.root/'bad',expected=4)
 def test_byte_capacity_preserves_complete_cards_and_order(self):
  cards=m.read(self.root/'source.json');limit=len(m.dump([m.runtime_card(c) for c in cards[:2]]).encode('utf-8'))
  dest=self.root/'bounded';m.import_knowledge(self.root/'source.json',dest,batch_size=4,max_batch_bytes=limit)
  manifest=m.read(dest/'manifest.json');loaded=[c for b in manifest['batches'] for c in m.read(dest/b['file'])]
  self.assertEqual(loaded,[m.runtime_card(c) for c in cards])
  self.assertTrue(all(b['utf8_bytes']<=limit for b in manifest['batches']))
  with self.assertRaisesRegex(ValueError,'never truncate'):m.import_knowledge(self.root/'source.json',self.root/'tiny',max_batch_bytes=1)
  self.assertFalse((self.root/'tiny').exists())
 def test_explicit_promotion_is_bound_to_card_and_records_exposure(self):
  cards=m.read(self.root/'source.json');cards[0]['evidence_status']['training_exposed_group']='SYNTHETIC_GROUP_A'
  m.save(self.root/'source.json',cards)
  registry={'authorization':{'user_request':'promote synthetic fixture'},'promoted_cards':{'T0':{'source_group':'SYNTHETIC_GROUP_A','card_sha256':m.hashlib.sha256(m.dump(cards[0]).encode('utf-8')).hexdigest()}}}
  m.save(self.root/'promotion.json',registry)
  m.import_knowledge(self.root/'source.json',self.root/'promoted',expected=4,promotion_registry=self.root/'promotion.json')
  self.assertEqual(m.read(self.root/'promoted/training_promotion.json'),registry)
  m.verify_frozen(self.root/'promoted')
  cards[0]['core_question']['text']='changed after authorization';m.save(self.root/'source.json',cards)
  with self.assertRaisesRegex(ValueError,'Training-exposure'):
   m.import_knowledge(self.root/'source.json',self.root/'tampered',promotion_registry=self.root/'promotion.json')
 def test_diagnosis_cannot_edit(self):
  x=answer('objects',{});x['edits']=[]
  with self.assertRaisesRegex(ValueError,'must not apply edits'):m.validate('objects',x,m.context_for(self.run,'objects'))
 def test_non_gap_cannot_link_finding(self):
  self.advance();ctx=m.context_for(self.run,'reader');x=answer('reader',ctx);x['checks'][0]['judgment']='sufficient'
  with self.assertRaises(ValueError):m.validate('reader',x,ctx)
 def test_cross_object_support_preserves_primary_and_reciprocal_links(self):
  self.advance();ctx=m.context_for(self.run,'reader');o=copy.deepcopy(O);o['id']='O2';ctx['objects'].append(o)
  x=answer('reader',ctx);c=copy.deepcopy(x['checks'][0]);c.update(id='reader:C2',object_id='O2');x['checks'].append(c)
  ctx['reader_scope_plan'][0]['object_ids'].append('O2')
  x['reading_review']['multiscale']['tasks'][0]['check_ids'].append(c['id'])
  x['findings'][0]['check_ids'].append(c['id']);m.validate('reader',x,ctx)
  x['findings'][0]['check_ids']=[c['id']]
  with self.assertRaisesRegex(ValueError,'primary object'):m.validate('reader',x,ctx)

if __name__=='__main__':unittest.main(verbosity=2)
