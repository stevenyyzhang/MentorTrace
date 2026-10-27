import copy,unittest
import advisor_output as out
import advisor_wire as wire
import advisor_brief as brief
import advisor_efficiency as efficient

class EconomicalReview(unittest.TestCase):
 def setUp(self):
  self.ctx={'advisor_output_contract':1,'advisor_expression_brief':1,'advisor_efficiency':1,
    'advisor_direct_fulltext':1,'advisor_batching':{'policy':'unchanged'},'cards':[],
    'manuscript':[{'page':1,'text':'Terms are defined.\nA second statement.\n'}],
    'expression_sources':{'records':[{'id':s,'operations':['Check agreement'],
       'before_account':'Local historical narrative.','retrieval_terms':['index only'],
       'transfer_conditions':['Plural subject'],'do_not_transfer':['Do not pluralize a singular subject'],
       'examples':[{'text':'are','kind':'verbatim_mentor_fragment'}],
       'language_features':[{'kind':'syntax','operation':'Check agreement'}],
       'publication_permission':'authorized','concern_ids':[]} for s in ['E1','E2']]},'source_uses':[]}
  self.group={'id':'supplement_1:WG1','source_ids':['E1','E2'],'decision':'keep',
     'reason':'The actual plural subject already has a matching verb.',
     'target_anchors':[{'$anchor':'P1.1'}]}
 def expand(self,g=None,ctx=None):
  return out.expand({'advisor_output_version':1,'definitions':{},'response':{
     'expression_assessment_groups':[copy.deepcopy(g or self.group)],'writing_transfers':[]}},ctx or self.ctx)
 def test_all_explicit_members_expand_without_fabricated_others(self):
  r=self.expand();self.assertEqual([x['source_id'] for x in r['writing_transfers']],['E1','E2'])
  for x in r['writing_transfers']:self.assertTrue(brief.validate(x,self.ctx))
  one=self.expand({**self.group,'source_ids':['E1']})
  self.assertEqual(len(one['writing_transfers']),1)
 def test_invalid_groups_and_legacy_rejected(self):
  for change in [{'source_ids':['E1','E1']},{'source_ids':['E3']},{'decision':'required_repair'}]:
   with self.assertRaises(ValueError):self.expand({**self.group,**change})
  ctx=copy.deepcopy(self.ctx);ctx.pop('advisor_efficiency')
  with self.assertRaises(ValueError):self.expand(ctx=ctx)
 def test_runtime_view_keeps_boundaries_and_roundtrips_local_history(self):
  packed,admin=wire.prepare(self.ctx);review=wire.unpack(packed)
  record=review['expression_sources']['records'][0]
  self.assertNotIn('before_account',record);self.assertNotIn('retrieval_terms',record)
  for k in ['operations','transfer_conditions','do_not_transfer','examples','language_features']:
   self.assertEqual(record[k],self.ctx['expression_sources']['records'][0][k])
  self.assertEqual(wire.restore(review,admin),self.ctx)
  self.assertEqual(review['expression_operation_families'][0]['source_ids'],['E1','E2'])
 def test_duplicate_sources_across_groups_or_individual_rows_rejected(self):
  for rows,groups in [([], [self.group,{**self.group,'id':'supplement_1:WG2'}]),
    ([{'source_kind':'mentor_expression','source_id':'E1'}],[self.group])]:
   response={'writing_transfers':copy.deepcopy(rows),'expression_assessment_groups':copy.deepcopy(groups)}
   with self.assertRaisesRegex(ValueError,'Duplicate or unsupplied'):
    efficient.expand_groups(response,self.ctx)
 def test_grouped_keep_needs_evidence_and_unknown_stays_unknown(self):
  r=self.expand({**self.group,'target_anchors':[]})
  for row in r['writing_transfers']:
   with self.assertRaisesRegex(ValueError,'KEEP needs target evidence'):brief.validate(row,self.ctx)
  r=self.expand({**self.group,'decision':'unknown','target_anchors':[]})
  for row in r['writing_transfers']:
   self.assertTrue(brief.validate(row,self.ctx))
   self.assertEqual(row['expression_contribution']['role'],'unresolved')
 def test_group_expansion_preserves_exact_member_ids_and_independent_anchors(self):
  r=self.expand();a,b=r['writing_transfers']
  self.assertEqual(a['id'],'supplement_1:WG1.E1')
  self.assertEqual(b['id'],'supplement_1:WG1.E2')
  a['target_anchors'][0]['quote']='Changed only in first member'
  self.assertEqual(b['target_anchors'][0]['quote'],'Terms are defined.\n')
 def test_hidden_narrative_cannot_be_cited_via_input_reference(self):
  with self.assertRaisesRegex(ValueError,'withheld'):
   out.expand({'advisor_output_version':1,'definitions':{},'response':{'x':{'$input':['expression_sources','records',0,'before_account']}}},self.ctx)
 def test_exact_passages_and_explicit_image_locators(self):
  r=self.expand();self.assertEqual(r['writing_transfers'][0]['target_anchors'][0],{'page':1,'quote':'Terms are defined.\n'})
  g={**self.group,'target_anchors':[{'$image_anchor':{'page':1,'description':'First line on original page.'}}]}
  self.assertEqual(self.expand(g)['writing_transfers'][0]['target_anchors'][0]['kind'],'image')
  g['target_anchors'][0]['$image_anchor']['page']=99
  with self.assertRaises(ValueError):self.expand(g)

if __name__=='__main__':unittest.main()
