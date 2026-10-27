import copy,unittest
import advisor_locators as loc
import advisor_output as out

class Locators(unittest.TestCase):
 def setUp(self):
  self.ctx={'advisor_output_contract':1,'advisor_locators':1,'manuscript':[
   {'page':1,'text':'See equation (5)\nx = y (5)\nFig. 2. A caption\nTABLE IV\n'},
   {'page':2,'text':'(5)\nAn unnumbered formula follows\n'}]}
 def test_candidates_preserve_ambiguity_and_exclude_prose_reference(self):
  rows=loc.catalogue(self.ctx)
  equations=[x for x in rows if x['kind']=='equation']
  self.assertEqual([x['id'] for x in equations],['EQUATION:P1:L2','EQUATION:P2:L1'])
  self.assertTrue(all(x['ambiguous_label'] for x in equations))
  self.assertEqual([x['label'] for x in rows if x['kind']=='table'],['IV'])
 def test_roundtrip_and_catalogue_tampering(self):
  wire=out.project(self.ctx);self.assertEqual(out.inflate(wire),self.ctx)
  wire['manuscript_locators'][0]['page']=99
  with self.assertRaises(ValueError):out.inflate(wire)
 def test_expands_to_image_not_transcribed_formula(self):
  value=out.expand({'advisor_output_version':1,'definitions':{},'response':{'location':{'$object_anchor':'EQUATION:P1:L2'}}},self.ctx)['location']
  self.assertEqual(value['page'],1);self.assertEqual(value['kind'],'image');self.assertNotIn('quote',value)
  with self.assertRaises(ValueError):loc.expand('EQUATION:P9:L2',self.ctx)
 def test_legacy_not_silently_upgraded(self):
  old=copy.deepcopy(self.ctx);old.pop('advisor_locators')
  self.assertNotIn('manuscript_locators',out.project(old))
  with self.assertRaises(ValueError):loc.expand('IMG:P1',old)
 def test_two_column_suffix_and_sub_equations_are_only_candidates(self):
  ctx={'manuscript':[{'page':3,'text':'(11a) Opposite-column fragment\nx ∈ V, (18) where another column begins\n(24) can be rewritten\n'}]}
  rows=[x for x in loc.catalogue(ctx) if x['kind']=='equation']
  self.assertEqual([x['label'] for x in rows],['11a','18'])
  self.assertTrue(all(x['status']=='unverified_label_candidate' for x in rows))

if __name__=='__main__':unittest.main()
