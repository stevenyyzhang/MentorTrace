import copy
import unittest
import test_pipeline as fixture
from test_pipeline import m, answer

class Surface(unittest.TestCase):
 setUp=fixture.Pipeline.setUp
 tearDown=fixture.Pipeline.tearDown
 advance=fixture.Pipeline.advance
 def test_surface_isolation_coverage_and_delivery(self):
  self.advance()
  ctx=m.context_for(self.run,'language')
  self.assertNotIn('objects',ctx);self.assertNotIn('cards',ctx)
  x=answer('language',ctx)
  bad=copy.deepcopy(x);bad['coverage']=[]
  with self.assertRaisesRegex(ValueError,'coverage'):m.validate('language',bad,ctx)
  f={'id':'language:F1','finding_type':'surface','category':'formatting','unit_ids':[ctx['text_units'][0]['id']],
     'anchor':{'page':1,'quote':'The receiver observes y.'},'relation':'synthetic punctuation check','gap':'synthetic correction',
     'impact':'minor readability','closure_goal':'synthetic fix','suggested_text':'The receiver observes y.'}
  x['findings']=[f];x['coverage'][0]['finding_ids']=[f['id']]
  m.validate('language',x,ctx)
  while m.next_request(self.run)['stage']!='language':self.advance()
  m.accept_response(self.run,x)
  for stage in ['merge','verify']:
   context=m.context_for(self.run,stage);response=answer(stage,context)
   with self.assertRaisesRegex(ValueError,'Surface finding lost'):m.validate(stage,response,context)
   # Separate technical and surface output paths, including the correction payload.
   surface=copy.deepcopy(f);surface['id']=stage+':F2';surface['new_in_stage']=False
   response['findings'].append(surface)
   for d in response['dispositions']:
    original=next(i for i in context['input_findings'] if i['id']==d['input_id'])
    if original.get('finding_type')=='surface':d['output_ids']=[surface['id']]
   m.accept_response(self.run,response)
  m.export_report(self.run)
  self.assertEqual(len(m.read(self.run/'surface_qa.json')['final_findings']),1)
  self.assertIn('language:F1',[r['raw_id'] for r in m.read(self.run/'trace.json')['raw_to_final']])

if __name__=='__main__':unittest.main()
