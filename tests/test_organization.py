"""Organization-suggestion transport tests; not a test of editorial judgment."""
import copy
import unittest

import test_pipeline as fixture
from test_pipeline import m, answer, A


def suggestion(stage):
 return {'id':stage+':G1','anchor':A,'current_order':'The definition follows its first use.',
         'proposed_order':'Move the existing definition immediately before the first use.',
         'reason':'Avoid a backward search while preserving the complete explanation.',
         'affected_links':'Update the following reference to the definition.',
         'conditions':'Use only the existing definition.','check_ids':[stage+':C1']}


class Organization(unittest.TestCase):
 setUp=fixture.Pipeline.setUp
 tearDown=fixture.Pipeline.tearDown
 advance=fixture.Pipeline.advance

 def test_sufficient_check_suggestion_survives_to_delivery(self):
  self.advance()
  req=m.next_request(self.run)
  self.assertIn('organization_suggestions',req['prompt'])
  x=answer('reader',m.context_for(self.run,'reader'))
  x['checks'][0].update(judgment='sufficient',finding_ids=[])
  x['findings']=[];x['organization_suggestions']=[suggestion('reader')]
  x['reading_review']['multiscale']['tasks'][0].update(outcome='optional_improvement',finding_ids=[],suggestion_ids=['reader:G1'],missing_information='')
  x['reading_review']['editorial'][0].update(decision='optional_improvement',
      action='Move the definition before its first use.',finding_ids=[],suggestion_ids=['reader:G1'])
  m.accept_response(self.run,x)
  while m.next_request(self.run)['stage']!='merge':self.advance()
  for stage in ['merge','verify']:
   ctx=m.context_for(self.run,stage);x=answer(stage,ctx)
   self.assertEqual(len(ctx['input_organization_suggestions']),1)
   with self.assertRaisesRegex(ValueError,'Organization disposition coverage'):
    m.validate(stage,x,ctx)
   item=copy.deepcopy(ctx['input_organization_suggestions'][0]);item['id']=stage+':G1'
   x['organization_suggestions']=[item]
   x['organization_dispositions']=[{'input_id':ctx['input_organization_suggestions'][0]['id'],
     'status':'retained','output_ids':[item['id']],'reason':'Concrete optional improvement remains useful.','evidence':[]}]
   m.accept_response(self.run,x)
  m.export_report(self.run)
  record=m.read(self.run/'organization_review.json')
  self.assertEqual(len(record['raw']),1)
  self.assertEqual(record['final_suggestions'][0]['proposed_order'],suggestion('reader')['proposed_order'])
  self.assertIn('Optional organization and flow suggestions',(self.run/'report.md').read_text(encoding='utf-8'))
  self.assertEqual(len(m.read(self.run/'final.json')['findings']),1)

 def test_withdrawal_and_incorporation_are_explicit(self):
  ctx={'manuscript':[{'page':1,'text':A['quote']}], 'input_organization_suggestions':[suggestion('reader')]}
  x={'findings':[{'id':'merge:F1'}], 'organization_dispositions':[{
   'input_id':'reader:G1','status':'withdrawn','output_ids':[],'reason':'Existing order is adequate.','evidence':[]}]}
  pages={1:A['quote']}
  with self.assertRaisesRegex(ValueError,'withdrawal lacks evidence'):m.validate_organization('merge',x,ctx,pages)
  x['organization_dispositions'][0]['evidence']=[A]
  m.validate_organization('merge',x,ctx,pages)
  x['organization_dispositions'][0].update(status='incorporated',output_ids=['merge:F1'])
  m.validate_organization('merge',x,ctx,pages)
  x['findings'][0]['finding_type']='surface'
  with self.assertRaisesRegex(ValueError,'content finding'):m.validate_organization('merge',x,ctx,pages)

 def test_independent_advisor_preserves_suggestion_and_isolation(self):
  self.advance()
  ctx=m.context_for(self.run,'supplement_1');x=answer('supplement_1',ctx)
  x['organization_suggestions']=[suggestion('supplement_1')]
  m.validate('supplement_1',x,ctx)
  normalized=m.adapt_independent('supplement_1',x,ctx)
  self.assertEqual(normalized['organization_suggestions'],x['organization_suggestions'])
  self.assertNotIn('input_organization_suggestions',ctx)
  self.assertNotIn('objects',ctx)

 def test_legacy_protocol_does_not_gain_new_prompt_fields(self):
  protocol=m.read(self.run/'inputs/protocol.json');protocol.pop('organization_review')
  m.save(self.run/'inputs/protocol.json',protocol);m.freeze(self.run/'inputs')
  self.advance()
  self.assertNotIn(m.ORGANIZATION_SCHEMA.splitlines()[0],m.next_request(self.run)['prompt'])


if __name__=='__main__':unittest.main()
