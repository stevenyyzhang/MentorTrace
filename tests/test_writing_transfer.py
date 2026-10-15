"""Source attribution and backward-compatibility tests; no writing quality claims."""
import copy
import importlib.util
import unittest
import writing_transfer as w
import test_pipeline as fixture
from test_pipeline import m, A, answer


def transfer(stage='reader', **changes):
    row = {'id': stage + ':W1', 'source_kind': 'manuscript', 'source_id': 'manuscript',
           'source_excerpt': '', 'learned_distinction': 'Explain a named observation before use.',
           'scope': 'paragraph', 'target_anchors': [A], 'reader_task': 'Locate the detector input.',
           'current_handling': 'Observation is named; access is not explained.', 'decision': 'required_repair',
           'proposed_action': 'Explain access beside the first observation.', 'preserved_dependencies': 'Retain the observation definition.',
           'check_ids': [stage + ':C1'], 'finding_ids': [stage + ':F1'], 'suggestion_ids': [],
           'limits': 'Synthetic evidence, not a mentor preference.'}
    row.update(changes)
    return row


class WritingTransfer(unittest.TestCase):
    setUp = fixture.Pipeline.setUp
    tearDown = fixture.Pipeline.tearDown
    advance = fixture.Pipeline.advance

    def enable(self):
        p = m.read(self.run / 'inputs/protocol.json'); p['writing_transfer'] = 1
        m.save(self.run / 'inputs/protocol.json', p); m.freeze(self.run / 'inputs')

    def test_draft_view_keeps_complete_sources_and_selected_retrieval(self):
        evidence={'raw_to_final':[],'writing_transfers':[],
            'expression_sources':{'records':[{'id':'EXP-1','mentor_texts':[{'text':'Exact mentor wording.'}],
                'transfer_conditions':['Preserve the stated prerequisite.']}],
                'episodes':[{'id':'EP-1','page_text':'Complete original source context.','after':{'status':'unavailable'}}]},
            'draft_expression_links':[{'verified_id':'verify:G1','expression_ids':['EXP-1'],
                'scope':'Post-freeze drafting retrieval.',
                'retrieval':{'version':1,'top_k':3,'assignments':{'draft':{'record_ids':['EXP-1'],
                    'candidates':[{'record_id':'EXP-1','selected':True,'score':7},
                                  {'record_id':'EXP-2','selected':False,'score':2}]}}}}]}
        before=copy.deepcopy(evidence)
        projected=w.draft_view(evidence)
        self.assertEqual(evidence,before)
        self.assertEqual(projected['expression_sources'],before['expression_sources'])
        assignment=projected['draft_expression_links'][0]['retrieval']['assignments']['draft']
        self.assertEqual(assignment['record_ids'],['EXP-1'])
        self.assertEqual(assignment['candidates'],[{'record_id':'EXP-1','selected':True,'score':7}])

    def test_new_default_and_frozen_legacy_contracts(self):
        new = self.root / 'new'
        m.create_run(self.root / 'paper', self.root / 'knowledge', new, goodpaper_cases=False)
        self.assertEqual(m.read(new / 'inputs/protocol.json')['writing_transfer'], 1)
        self.advance()
        legacy = m.prepare_stage_request(self.run, 'reader')
        self.assertNotIn('writing-transfer.md', legacy['module_hashes'])
        self.assertNotIn('writing_transfer', m.context_for(self.run, 'reader'))

    def test_new_reader_requires_records_and_accepts_target_grounded_repair(self):
        self.enable(); self.advance()
        ctx = m.context_for(self.run, 'reader'); x = answer('reader', ctx)
        x.pop('writing_transfers')
        with self.assertRaisesRegex(ValueError, 'Missing writing transfer'): m.validate('reader', x, ctx)
        x['writing_transfers'] = [transfer()]
        m.validate('reader', x, ctx)

    def test_advisor_remains_isolated_and_editorial_card_requires_transfer(self):
        self.enable()
        req = m.prepare_stage_request(self.run, 'supplement_1')
        self.assertIn('writing-transfer.md', req['module_hashes'])
        ctx = m.context_for(self.run, 'supplement_1')
        self.assertNotIn('objects', ctx); self.assertNotIn('goodpaper_cases', ctx)
        x = answer('supplement_1', ctx); x['card_dispositions'][0]['writing_scope'] = 'editorial'
        with self.assertRaisesRegex(ValueError, 'no transfer record'): m.validate('supplement_1', x, ctx)
        x['writing_transfers'] = [transfer('supplement_1', source_kind='advisor_concern', source_id='T0', source_excerpt='fixture')]
        m.validate('supplement_1', x, ctx)
        x['writing_transfers'][0]['source_excerpt'] = 'Invented mentor quotation'
        with self.assertRaisesRegex(ValueError, 'excerpt absent'): m.validate('supplement_1', x, ctx)

    def test_selected_case_disposition_and_keep_without_findings(self):
        self.enable(); self.advance()
        ctx = m.context_for(self.run, 'reader')
        ctx['goodpaper_cases'] = {'complete_cases': [{'case_id': 'P1', 'full_case': {'full_relation_chain': 'Structure explains the saving.'}}], 'same_task_companions': []}
        x = answer('reader', ctx)
        x['case_usage'] = [{'case_id': 'P1', 'effect': 'sufficiency_recognition', 'object_ids': ['O1'], 'reason': 'Source example inspected.'}]
        x['writing_transfers'] = []
        with self.assertRaisesRegex(ValueError, 'no transfer disposition'): m.validate('reader', x, ctx)
        x['writing_transfers'] = [transfer(source_kind='published_case', source_id='P1', source_excerpt='Structure explains', decision='keep', finding_ids=[])]
        m.validate('reader', x, ctx)

    def test_concern_transfer_allows_independent_context_checks_but_needs_source_use(self):
        self.enable();ctx=m.context_for(self.run,'supplement_1')
        x=answer('supplement_1',ctx);stage='supplement_1'
        contextual=copy.deepcopy(x['checks'][0])
        contextual.update(id=stage+':C2',card_ids=[],finding_ids=[],judgment='sufficient')
        x['checks'].append(contextual)
        row=transfer(stage,source_kind='advisor_concern',source_id='T0',source_excerpt='fixture',
                     check_ids=[stage+':C1',stage+':C2'])
        x['writing_transfers']=[row]
        pages={p['page']:p['text'] for p in ctx['manuscript']}
        w.validate(stage,x,ctx,pages,m.anchor)
        row.update(check_ids=[stage+':C2'],decision='keep',finding_ids=[])
        with self.assertRaisesRegex(ValueError,'not used by its linked checks'):
            w.validate(stage,x,ctx,pages,m.anchor)

    def test_supplied_reader_after_is_analysis_not_original_prose_or_recipe(self):
        self.enable(); self.advance(); ctx=m.context_for(self.run,'reader')
        ctx['goodpaper_cases']={'complete_cases':[{'case_id':'P1',
            'full_case':{'full_relation_chain':'Stage input leads to its output.',
                         'reader_after':'The reader knows each stage input.',
                         'writing_pattern':'Withheld writing recipe.'},
            'source_passages':{'pages':[{'text':'Actual published source wording.'}]}}],
            'same_task_companions':[]}
        x=answer('reader',ctx)
        x['case_usage']=[{'case_id':'P1','effect':'sharpened_check','object_ids':['O1'],
                         'reason':'The supplied analyst account distinguishes the inputs.'}]
        row=transfer(source_kind='published_case',source_id='P1',
                     source_excerpt='The reader knows each stage input.',excerpt_basis='analyst_summary')
        x['writing_transfers']=[row]
        m.validate('reader',x,ctx)
        row['excerpt_basis']='original_page_text'
        with self.assertRaisesRegex(ValueError,'excerpt absent'):m.validate('reader',x,ctx)
        row['excerpt_basis']='analyst_summary';row['source_excerpt']='Withheld writing recipe.'
        with self.assertRaisesRegex(ValueError,'excerpt absent'):m.validate('reader',x,ctx)

    def test_unloaded_source_and_disconnected_output_rejected(self):
        self.enable(); self.advance(); ctx = m.context_for(self.run, 'reader'); x = answer('reader', ctx)
        x['writing_transfers'] = [transfer(source_kind='advisor_concern', source_id='T0', source_excerpt='fixture')]
        with self.assertRaisesRegex(ValueError, 'unsupplied source'): m.validate('reader', x, ctx)
        x['writing_transfers'] = [transfer(check_ids=[])]
        with self.assertRaisesRegex(ValueError, 'anchored checks'): m.validate('reader', x, ctx)

    def test_anchored_explicit_nonmatch_needs_no_fabricated_check(self):
        self.enable();ctx=m.context_for(self.run,'supplement_1');stage='supplement_1'
        row=transfer(stage,source_kind='advisor_concern',source_id='T0',source_excerpt='fixture',
                     decision='not_applicable',check_ids=[],finding_ids=[])
        x={'checks':[],'findings':[],'organization_suggestions':[],'writing_transfers':[row],
           'card_dispositions':[{'card_id':'T0','state':'not_applicable','writing_scope':'editorial','reason':'The required source condition is absent in the anchored target.'}]}
        pages={p['page']:p['text'] for p in ctx['manuscript']}
        w.validate(stage,x,ctx,pages,m.anchor)
        x['card_dispositions'][0]['state']='applicable'
        with self.assertRaisesRegex(ValueError,'not used by its linked checks'):w.validate(stage,x,ctx,pages,m.anchor)
        x['card_dispositions'][0]['state']='not_applicable';row['target_anchors']=[]
        with self.assertRaisesRegex(ValueError,'not used by its linked checks'):w.validate(stage,x,ctx,pages,m.anchor)

    def test_optional_incorporation_follows_to_final_content(self):
        merge = {'organization_dispositions': [{'input_id': 'reader:G1', 'output_ids': ['merge:F1']}], 'dispositions': []}
        final = {'dispositions': [{'input_id': 'merge:F1', 'output_ids': ['verify:F1']}], 'organization_dispositions': []}
        self.assertEqual(w.follow('reader:G1', merge, final), ['verify:F1'])
        final['dispositions'][0]['output_ids'] = []
        self.assertEqual(w.follow('reader:G1', merge, final), [])

    def test_export_and_draft_keep_connected_concerns_and_source_records(self):
        self.enable()
        while m.next_request(self.run): self.advance()
        m.export_report(self.run)
        packet = m.read(self.run / 'writing_transfer.json')
        self.assertEqual({c['id'] for c in packet['advisor_sources']}, {'T0', 'T1', 'T2', 'T3'})
        self.assertTrue(all(c['core_question']['text'] == 'fixture' for c in packet['advisor_sources']))
        spec = importlib.util.spec_from_file_location('draft_test', m.ROOT / 'scripts/prepare_revision_proposals.py')
        draft = importlib.util.module_from_spec(spec); spec.loader.exec_module(draft)
        before = m.sha(self.run / 'calls/verify/response.json')
        request = draft.prepare(self.run, self.root / 'delivery')
        prompt = m.read(request)['prompt']
        self.assertIn('revision_attribution', prompt); self.assertIn('WRITING EVIDENCE', prompt)
        self.assertEqual(before, m.sha(self.run / 'calls/verify/response.json'))
        m.verify_frozen(self.root / 'delivery/inputs')

    def test_draft_source_attribution_cannot_cross_final_items(self):
        evidence = {'writing_transfers': [], 'raw_to_final': [{'final_ids': ['verify:F1'], 'writing_transfer_ids': [],
                    'advisor_card_ids': ['T0'], 'associated_case_ids': []}]}
        final = {'findings': [{'id': 'verify:F1'}, {'id': 'verify:F2'}]}
        rows = [{'verified_id': fid, 'report_excerpt': 'Explain the input.', 'basis': 'target_analysis',
                 'case_ids': [], 'card_ids': [], 'transfer_ids': [], 'use_explanation': 'Target evidence.', 'target_support': [A]}
                for fid in ['verify:F1', 'verify:F2']]
        response = {'report_markdown': 'Explain the input.', 'revision_attribution': rows}
        manuscript = [{'page': 1, 'text': A['quote']}]
        w.validate_proposals(response, evidence, final, manuscript, m.anchor)
        rows[1].update(basis='advisor_concern', card_ids=['T0'])
        with self.assertRaisesRegex(ValueError, 'unrelated source'): w.validate_proposals(response, evidence, final, manuscript, m.anchor)
        rows[1].update(basis='target_analysis', card_ids=[], report_excerpt='Missing text')
        with self.assertRaisesRegex(ValueError, 'actual report excerpt'): w.validate_proposals(response, evidence, final, manuscript, m.anchor)


if __name__ == '__main__': unittest.main()
