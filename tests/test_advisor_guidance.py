import copy,unittest
import advisor_guidance as g
import advisor_wire as wire
import advisor_output as output

class Guidance(unittest.TestCase):
 def setUp(self):
  self.records=[{'id':s,'operations':['Original operation.'],'language_features':[{'id':s+':L1','kind':'syntax','operation':'Original feature operation.','conditions':['Only with a plural subject.'],'do_not_transfer':['Not singular.']}],
    'examples':[{'id':s+':E1','text':'are','kind':'verbatim_mentor_fragment'}],
    'transfer_conditions':['Retain source facts.'],'do_not_transfer':['No inferred facts.'],'before_account':'Local history.'} for s in ['E1','E2']]
  self.reg={'version':1,'guidance':{'G1':{'operation':'Consolidated analyst instruction.','topic':'subject verb agreement'}},
    'records':{r['id']:{'source_fields_sha256':g.signature(r),'units':[{'id':r['id']+':U1','guidance_id':'G1','paths':['operations/0','language_features/0/operation']}]} for r in self.records}}
  self.ctx={'advisor_batching':{'policy':'unchanged'},'advisor_efficiency':1,'advisor_guidance':1,'advisor_output_contract':1,'manuscript':[{'page':1,'text':'The units are valid.\n'}],
    'expression_sources':{'records':self.records},'expression_guidance':self.reg}
 def test_shared_operation_and_complete_boundaries_roundtrip(self):
  packed,admin=wire.prepare(self.ctx);visible=wire.unpack(packed)
  self.assertNotIn('expression_guidance',visible)
  for record in visible['expression_sources']['records']:
   self.assertEqual(record['operations'],['Consolidated analyst instruction.'])
   self.assertNotIn('operation',record['language_features'][0])
   self.assertNotIn('operation_index',record['language_features'][0])
   self.assertEqual(record['language_features'][0]['conditions'],['Only with a plural subject.'])
   self.assertEqual(record['examples'][0]['text'],'are')
  self.assertEqual(wire.restore(visible,admin),self.ctx)
 def test_no_cross_record_applicability_inference(self):
  self.ctx['expression_sources']['records'][1]['transfer_conditions']=['A different trigger.']
  packed,admin=wire.prepare(self.ctx);rs=wire.unpack(packed)['expression_sources']['records']
  self.assertNotEqual(rs[0]['transfer_conditions'],rs[1]['transfer_conditions'])
 def test_stale_or_missing_source_mapping_rejected(self):
  self.records[0]['operations'][0]='Changed instruction.'
  with self.assertRaisesRegex(ValueError,'Stale'):g.validate(self.reg,self.records)
  self.reg['records']['E1']['source_fields_sha256']=g.signature(self.records[0])
  self.reg['records']['E1']['units'][0]['paths'].pop()
  with self.assertRaisesRegex(ValueError,'loss or duplication'):g.validate(self.reg,self.records)
 def test_original_hidden_operation_not_available_as_input_quote(self):
  for path in [['expression_sources','records',0,'operations',0],['expression_sources','records',0,'language_features',0,'operation']]:
   with self.assertRaisesRegex(ValueError,'replaced by analyst'):
    output.expand({'advisor_output_version':1,'definitions':{},'response':{'quote':{'$input':path}}},self.ctx)
 def test_subset_contains_every_required_guidance_and_no_other_records(self):
  sub=g.subset(self.reg,['E2']);self.assertEqual(set(sub['records']),{'E2'});self.assertEqual(set(sub['guidance']),{'G1'})
  self.assertTrue(g.validate(sub,[self.records[1]]))
 def test_legacy_keeps_original_operations(self):
  self.ctx.pop('advisor_guidance');self.ctx.pop('expression_guidance')
  packed,_=wire.prepare(self.ctx)
  self.assertEqual(wire.unpack(packed)['expression_sources']['records'][0]['operations'],['Original operation.'])
 def test_withheld_realization_feature_retains_analytical_guidance(self):
  r=self.records[0]
  r['public_language_features']=copy.deepcopy(r['language_features'])
  r['language_features']=[]
  packed,admin=wire.prepare(self.ctx);visible=wire.unpack(packed)['expression_sources']['records'][0]
  self.assertEqual(visible['language_features'],[])
  self.assertNotIn('operation',visible['public_language_features'][0])
  self.assertNotIn('operation_index',visible['public_language_features'][0])
  self.assertEqual(wire.restore(wire.unpack(packed),admin),self.ctx)
 def test_retained_analytical_quote_is_not_rewritten_guidance(self):
  r=copy.deepcopy(self.records[0]);f=r['language_features'][0]
  f.update(evidence_kind='analytical_operation',evidence_account={'field':'operations'},source_quote='Actual retained account.')
  self.assertTrue(g.operation_excerpt_visible(r,'retained account'))
  self.assertFalse(g.operation_excerpt_visible(r,'New canonical instruction.'))
  self.assertFalse(g.operation_excerpt_visible(r,''))
  f['evidence_kind']='mentor_fragment'
  self.assertFalse(g.operation_excerpt_visible(r,'retained account'))
 def test_multiple_actions_keep_explicit_feature_binding(self):
  self.reg['guidance']['G2']={'operation':'A distinct feature action.','topic':'different action'}
  self.reg['records']['E1']['units']=[
    {'id':'E1:U1','guidance_id':'G1','paths':['operations/0']},
    {'id':'E1:U2','guidance_id':'G2','paths':['language_features/0/operation']}]
  packed,admin=wire.prepare(self.ctx);record=wire.unpack(packed)['expression_sources']['records'][0]
  self.assertEqual(record['language_features'][0]['operation_index'],1)
  self.assertEqual(record['operations'][1],'A distinct feature action.')
  self.assertEqual(wire.restore(wire.unpack(packed),admin),self.ctx)

if __name__=='__main__':unittest.main()
