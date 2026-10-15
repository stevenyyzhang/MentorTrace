"""Selection transport regressions; these do not measure editorial quality."""
import copy
import unittest
import test_pipeline as fixture
from test_pipeline import m, answer, A
from test_organization import suggestion


class EditorialSelection(unittest.TestCase):
 setUp=fixture.Pipeline.setUp
 tearDown=fixture.Pipeline.tearDown
 advance=fixture.Pipeline.advance

 def enable(self):
  protocol=m.read(self.run/'inputs/protocol.json')
  protocol.update(reader_multiscale=4,editorial_selection=1)
  m.save(self.run/'inputs/protocol.json',protocol);m.freeze(self.run/'inputs')

 def test_null_candidate_is_explicit_reasoned_and_versioned(self):
  self.enable();ctx=m.context_for(self.run,'objects');plan=answer('objects',ctx)
  target=plan['reader_editorial_plan'][0];target['candidate_alternative']=None
  with self.assertRaisesRegex(ValueError,'Null editorial candidate'):m.validate('objects',plan,ctx)
  target['no_candidate_reason']='The sentence gives the observation before the detector uses it.'
  m.validate('objects',plan,ctx)
  old=copy.deepcopy(ctx);old['reader_multiscale']=3
  with self.assertRaisesRegex(ValueError,'Missing editorial counterfactual'):m.validate('objects',plan,old)
  m.accept_response(self.run,plan)
  ctx=m.context_for(self.run,'reader');result=answer('reader',ctx)
  result['checks'][0].update(judgment='sufficient',finding_ids=[]);result['findings']=[]
  result['reading_review']['multiscale']['tasks'][0].update(outcome='sufficient',finding_ids=[],missing_information='')
  row=result['reading_review']['editorial'][0]
  row.update(decision='keep',finding_ids=[],action='retain',reason='The observation already precedes its use.')
  row['alternative_evaluation'].update(tested_change='No alternative proposed.',reader_gain='No supported extra benefit.',reader_cost='An extra sentence would repeat the same observation.',verdict_reason='Retain the adequate current sequence.')
  m.validate('reader',result,ctx)

 def group(self,inputs,outputs,action='change'):
  return {'id':'D1','input_ids':inputs,'reader_task':'Locate the detector input.',
   'current_arrangement':'Observation precedes use.','evidence':[A],
   'preferred_action':action,'selected_output_ids':outputs,
   'reason':'One optional path is preferred; the competing placement repeats it.',
   'gain':'A shorter reference at the use point.','cost':'One local transition.',
   'compatibility':'The second placement is excluded; no overlapping replacement.'}

 def test_chosen_path_survives_merge_verify_and_export(self):
  self.enable();self.advance()
  ctx=m.context_for(self.run,'reader');result=answer('reader',ctx)
  first=suggestion('reader');second=copy.deepcopy(first);second['id']='reader:G2'
  second['proposed_order']='Repeat the definition after its first use.'
  result['organization_suggestions']=[first,second];m.accept_response(self.run,result)
  while m.next_request(self.run)['stage']!='merge':self.advance()
  for stage in ['merge','verify']:
   ctx=m.context_for(self.run,stage);result=answer(stage,ctx)
   if stage=='verify':self.assertEqual(ctx['prior_editorial_selection'][0]['selected_output_ids'],['merge:G1'])
   chosen=suggestion(stage);result['organization_suggestions']=[chosen]
   incoming=ctx['input_organization_suggestions']
   result['organization_dispositions']=[{'input_id':item['id'],'status':'retained' if i==0 else 'withdrawn',
    'output_ids':[chosen['id']] if i==0 else [],'reason':'Select the first path; the alternative repeats it.','evidence':[A]} for i,item in enumerate(incoming)]
   result['editorial_selection']=[self.group([s['id'] for s in incoming],[chosen['id']])]
   m.accept_response(self.run,result)
  m.export_report(self.run)
  audit=m.read(self.run/'organization_review.json')
  self.assertEqual(len(audit['raw']),2)
  self.assertEqual(audit['merge_selection'][0]['input_ids'],['reader:G1','reader:G2'])
  self.assertEqual(audit['verified_selection'][0]['selected_output_ids'],['verify:G1'])

 def test_unselected_output_cannot_remain_retained_or_be_published(self):
  ctx={'editorial_selection':1,'input_organization_suggestions':[suggestion('reader')]}
  result={'findings':[],'organization_suggestions':[suggestion('merge')],
   'organization_dispositions':[{'input_id':'reader:G1','status':'retained','output_ids':['merge:G1'],'reason':'Retained.'}],
   'editorial_selection':[self.group(['reader:G1'],[],'keep')]}
  with self.assertRaisesRegex(ValueError,'contradicts source dispositions'):m.validate_organization('merge',result,ctx,{1:A['quote']})
  result['organization_dispositions'][0].update(status='withdrawn',output_ids=[],evidence=[A])
  result['organization_suggestions'][0]['new_in_stage']=True
  with self.assertRaisesRegex(ValueError,'missing preferred decision'):m.validate_organization('merge',result,ctx,{1:A['quote']})
  result['organization_suggestions']=[];m.validate_organization('merge',result,ctx,{1:A['quote']})

 def test_independent_content_requirement_survives_rejected_move(self):
  ctx={'editorial_selection':1,'input_organization_suggestions':[suggestion('reader')]}
  result={'findings':[{'id':'merge:F1'}],'organization_suggestions':[],
   'organization_dispositions':[{'input_id':'reader:G1','status':'withdrawn','output_ids':[],'reason':'Placement is already adequate.','evidence':[A]}],
   'editorial_selection':[self.group(['reader:G1'],[],'keep')]}
  m.validate_organization('merge',result,ctx,{1:A['quote']})
  result['organization_dispositions'][0].update(status='incorporated',output_ids=['merge:F1'])
  result['editorial_selection']=[self.group(['reader:G1'],['merge:F1'])]
  m.validate_organization('merge',result,ctx,{1:A['quote']})

 def test_duplicate_membership_and_untraced_output_rejected(self):
  ctx={'editorial_selection':1,'input_organization_suggestions':[suggestion('reader')]}
  result={'findings':[],'organization_suggestions':[],
   'organization_dispositions':[{'input_id':'reader:G1','status':'withdrawn','output_ids':[],'reason':'Equivalent style.','evidence':[A]}],
   'editorial_selection':[self.group(['reader:G1'],[],'keep')]}
  duplicate=copy.deepcopy(result['editorial_selection'][0]);duplicate['id']='D2'
  result['editorial_selection'].append(duplicate)
  with self.assertRaisesRegex(ValueError,'multiple decisions'):m.validate_organization('merge',result,ctx,{1:A['quote']})
  result['editorial_selection']=[]
  with self.assertRaisesRegex(ValueError,'input coverage mismatch'):m.validate_organization('merge',result,ctx,{1:A['quote']})
  ctx.pop('editorial_selection');result.pop('editorial_selection')
  m.validate_organization('merge',result,ctx,{1:A['quote']})

 def test_new_prompts_are_gated_and_advisor_stays_independent(self):
  self.assertNotIn('editorial_selection',m.read(self.run/'inputs/protocol.json'))
  self.enable();self.assertIn(m.multiscale.PLAN_SCHEMA_V4,m.next_request(self.run)['prompt'])
  self.advance()
  for stage in ['reader','supplement_1']:
   req=m.prepare_stage_request(self.run,stage)
   self.assertIn(m.editorial_selection.BRANCH_SCHEMA,req['prompt'])
  ctx=m.context_for(self.run,'supplement_1')
  self.assertNotIn('input_organization_suggestions',ctx)
  self.assertNotIn('reader_editorial_plan',ctx)


if __name__=='__main__':unittest.main()
