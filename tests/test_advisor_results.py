import copy,unittest
import advisor_results as r,advisor_output as output,mentortrace_v1 as m

class Results(unittest.TestCase):
 def setUp(self):
  self.ctx={'advisor_shared_results':1,'advisor_output_contract':1,'advisor_expression_brief':1,'advisor_direct_fulltext':1,'advisor_batching':True,'advisor_role_division':1,'writing_transfer':1,'expression_version':1,
   'primary_card_ids':['C1','C2'],'cards':[{'id':'C1'},{'id':'C2'}],
   'manuscript':[{'page':1,'text':'A definition follows its first use.'}],
   'expression_sources':{'records':[{'id':i,'mentor_texts':[{'text':'Define before use.'}],'language_features':[]} for i in ['E1','E2']]},
   'source_uses':[{'expression_id':'E1','target_kind':'concern','target_id':'C1'},{'expression_id':'E2','target_kind':'concern','target_id':'C2'}]}
  self.raw={'stage':'supplement_1','analyses':[],
   'concern_results':[{'source_ids':['C1','C2'],'state':'not_applicable','reason':'The triggering construction is absent.','analysis_ids':[]}],
   'expression_results':[{'source_ids':['E1','E2'],'decision':'keep','reason':'Definitions already precede use throughout the applicable passages.','target_anchors':[]}],
   'adopted_uses':[],'association_exceptions':[]}
 def expand(self):return output.expand({'advisor_output_version':1,'definitions':{},'response':self.raw},self.ctx)
 def action(self):
  self.raw['analyses']=[{'id':'supplement_1:A1','anchor':{'$anchor':'P1.1'},'relation':'Definition before use','passage_job':'Explain the named quantity.','execution':'completed','judgment':'gap','author_explanation':'Definition follows use.','counterevidence':'No earlier definition.','reason':'Reader needs meaning first.','local_support':[],'later_support':[], 'finding':{'gap':'Late definition.','impact':'Cannot interpret use.','closure_goal':'Move the definition before use.'},'suggestion':None}]
  self.raw['concern_results']=[{'source_ids':['C1'],'state':'linked','reason':'Late definition.','analysis_ids':['supplement_1:A1']},{'source_ids':['C2'],'state':'not_applicable','reason':'Trigger absent.','analysis_ids':[]}]
  self.raw['expression_results']=[{'source_ids':['E1'],'decision':'required_repair','analysis_ids':['supplement_1:A1'],'contribution':'Move the definition, retaining its conditions.','source_excerpt':'Define before use.','expression_excerpt_basis':{},'scope':'sentence','preserved_dependencies':'Retain all qualifiers.','limits':'Do not alter meaning.','feature_ids':[],'supporting_concern_ids':['C1'],'role':'repair_realization'}, {'source_ids':['E2'],'decision':'not_applicable','reason':'Different construction.','target_anchors':[]}]
 def test_nonaction_explicit_coverage_and_unassessed_associations(self):
  expanded=self.expand();m.validate('supplement_1',expanded,self.ctx)
  self.assertEqual({u['status'] for u in expanded['source_use_dispositions']},{'not_assessed'})
  self.assertFalse(output.preflight(expanded,self.ctx)['issues'])
 def test_missing_and_duplicate_source_fail(self):
  for label in ['concern_results','expression_results']:
   before=copy.deepcopy(self.raw)
   self.raw[label][0]['source_ids'].pop()
   with self.assertRaisesRegex(ValueError,'coverage'):self.expand()
   self.raw=copy.deepcopy(before);self.raw[label][0]['source_ids'].append(self.raw[label][0]['source_ids'][0])
   with self.assertRaisesRegex(ValueError,'coverage'):self.expand()
   self.raw=before
 def test_one_analysis_generates_links_without_rewriting_evidence(self):
  self.action();self.raw['adopted_uses']=[{'use_id':1,'expression_id':'E1','reason':'This operation supplies the definition-order repair.'}]
  expanded=self.expand();m.validate('supplement_1',expanded,self.ctx)
  self.assertEqual(len(expanded['checks']),1);self.assertEqual(len(expanded['findings']),1)
  self.assertEqual(expanded['writing_transfers'][0]['current_handling'],'Definition follows use.')
  self.assertEqual([u['status'] for u in expanded['source_use_dispositions']],['adopted','not_assessed'])
 def test_invalid_adoption_and_reference_fail(self):
  self.raw['adopted_uses']=[{'use_id':1,'expression_id':'E1','reason':'Claimed.'}]
  with self.assertRaisesRegex(ValueError,'supported action'):self.expand()
  self.action();self.raw['adopted_uses']=[];self.raw['expression_results'][0]['analysis_ids']=['supplement_1:A404']
  with self.assertRaisesRegex(ValueError,'Unknown'):self.expand()
 def test_unknown_and_unfinished_remain_visible(self):
  self.raw['expression_results'][0]['decision']='unfinished'
  self.raw['concern_results'][0]['state']='unknown'
  result=self.expand();m.validate('supplement_1',result,self.ctx)
  self.assertEqual(result['source_review_summary']['expression_states'],{'unfinished':2})
  self.assertEqual(result['source_review_summary']['concern_states'],{'unknown':2})
 def test_old_protocol_cannot_accept_new_rows(self):
  self.ctx.pop('advisor_shared_results')
  with self.assertRaisesRegex(ValueError,'not enabled'):self.expand()
 def test_independent_manuscript_suggestion(self):
  self.action();a=self.raw['analyses'][0];a['judgment']='sufficient';a['finding']=None
  a['suggestion']={'scope':'paragraph','current_order':'Definition is explained later.','proposed_order':'Move the explanation beside the name.','reason':'Reduce reading distance.','affected_links':'Keep references valid.','conditions':'Only if this improves the local flow.'}
  self.raw['expression_results']=[{'source_ids':['E1','E2'],'decision':'not_applicable','reason':'These particular constructions do not apply.','target_anchors':[]}]
  result=self.expand();m.validate('supplement_1',result,self.ctx)
  self.assertEqual(result['writing_transfers'][-1]['source_kind'],'manuscript')
 def test_one_source_can_have_distinct_required_and_optional_actions(self):
  self.action();a=copy.deepcopy(self.raw['analyses'][0]);a['id']='supplement_1:A2';a['judgment']='sufficient';a['finding']=None
  a['suggestion']={'scope':'paragraph','current_order':'Supported but distant explanation.','proposed_order':'Place nearby.','reason':'Reduce reading distance.','affected_links':'Keep definitions valid.','conditions':'Only if useful.'}
  self.raw['analyses'].append(a);self.raw['concern_results'][0]['analysis_ids'].append(a['id'])
  action=self.raw['expression_results'][0];first={k:v for k,v in action.items() if k!='source_ids'}
  second={**first,'decision':'optional_improvement','analysis_ids':[a['id']],'role':'expression_improvement'}
  self.raw['expression_results'][0]={'source_ids':['E1'],'actions':[first,second]}
  result=self.expand();m.validate('supplement_1',result,self.ctx)
  self.assertEqual(len(result['expression_result_manifest'][0]['transfer_ids']),2)
  self.assertEqual(result['source_review_summary']['expression_states']['optional_improvement/required_repair'],1)
 def test_context_results_are_preserved_but_do_not_replace_primary(self):
  self.ctx['cards'].append({'id':'C3'})
  self.raw['concern_results'].append({'source_ids':['C3'],'state':'sufficient','reason':'Explicit optional context judgment.','analysis_ids':[]})
  expanded=self.expand();m.validate('supplement_1',expanded,self.ctx)
  self.assertEqual(expanded['context_card_dispositions'][0]['reason'],'Explicit optional context judgment.')
  self.assertEqual(len(expanded['card_dispositions']),2)
  self.raw['concern_results'][0]['source_ids'].remove('C1')
  with self.assertRaisesRegex(ValueError,'coverage'):self.expand()
 def test_omitted_optional_anchor_is_not_a_generated_judgment(self):
  self.raw['expression_results'][0].pop('target_anchors')
  expanded=self.expand();m.validate('supplement_1',expanded,self.ctx)
  self.assertEqual(expanded['writing_transfers'][0]['target_anchors'],[])
  self.assertEqual(expanded['writing_transfers'][0]['reason'],self.raw['expression_results'][0]['reason'])
  self.raw['expression_results'][0]['target_anchors']=None
  with self.assertRaisesRegex(ValueError,'anchor list'):m.validate('supplement_1',self.expand(),self.ctx)
 def test_description_scope_and_dependencies_list_preserved(self):
  self.action();action=self.raw['expression_results'][0]
  action['scope']='The definition in the opening paragraph.';action['preserved_dependencies']=['Qualifier one.','Qualifier two.']
  expanded=self.expand();m.validate('supplement_1',expanded,self.ctx)
  for key in ['scope','preserved_dependencies']:self.assertEqual(expanded['writing_transfers'][0][key],action[key])
  action['preserved_dependencies']=['']
  with self.assertRaisesRegex(ValueError,'dependencies'):m.validate('supplement_1',self.expand(),self.ctx)
 def test_page_locator_alias_requires_supplied_consistent_id(self):
  self.ctx['advisor_efficiency']=1;self.action()
  self.raw['analyses'][0]['anchor']={'$image_anchor':{'page_locator':'IMG:P1','description':'Original description.'}}
  expanded=self.expand();m.validate('supplement_1',expanded,self.ctx)
  self.assertEqual(expanded['findings'][0]['anchor'],{'page':1,'kind':'image','description':'Original description.'})
  self.raw['analyses'][0]['anchor']['$image_anchor']['page']=2
  with self.assertRaisesRegex(ValueError,'Contradictory'):self.expand()
  self.raw['analyses'][0]['anchor']['$image_anchor']={'page_locator':'IMG:P99','description':'Unknown page.'}
  with self.assertRaisesRegex(ValueError,'Unknown'):self.expand()
