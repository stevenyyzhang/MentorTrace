"""Synthetic evidence/independence tests; these do not certify mentor fit."""
import copy
import json
import os
import subprocess
import sys
import unittest

import expression_runtime as e
import writing_transfer as w
import prepare_revision_proposals as draft
import goodpaper_runtime as goodpaper
import test_pipeline as fixture
from test_pipeline import m, A, answer
from test_writing_transfer import transfer


class Expression(unittest.TestCase):
    setUp = fixture.Pipeline.setUp
    tearDown = fixture.Pipeline.tearDown

    def library(self, links=None):
        original=self.root/'original.txt';original.write_text('Synthetic original evidence.',encoding='utf-8')
        pixels=self.root/'image.txt';pixels.write_text('Synthetic image placeholder; no visual claim.',encoding='utf-8')
        episode={'id':'E1','family_id':'synthetic','source_path':str(original),'source_sha256':m.sha(original),
                 'image_path':str(pixels),'image_sha256':m.sha(pixels),'page':1,'page_text':A['quote'],
                 'feedback':[{'ref':'a1','author':'mentor_confirmed','mentor_text':'Explain the observation before detector use.'}]}
        record={'id':'EXP1','episode_ids':['E1'],'evidence_refs':['a1'],
                'title':'Observation handoff','section_task':'receiver detector input','scope':'paragraph',
                'authority':'mentor_wording','preference_status':'local_requirement',
                'mentor_texts':[{'ref':'a1','text':episode['feedback'][0]['mentor_text']}],
                'before_account':'Observation named.', 'observed_change':'Proposed explanation before use.',
                'changed_relationship':'receiver observation detector input', 'after_account':'Applied version unavailable.',
                'transfer_conditions':'A detector needs an observation.', 'do_not_transfer':'No invented access facts.',
                'facts_and_qualifications':'Preserve observed y.', 'source_review_status':'Synthetic fixture only.',
                'operations':['add'],'retrieval_terms':['receiver','observation','detector','input'],
                'concern_ids':links if links is not None else ['T0']}
        self.episodes=[episode];self.records=[record]
        self.lib=e.build(self.records,self.episodes,self.root/'private/expression',['T0','T1','T2','T3'])
        return self.lib

    def new_run(self,mode='advisor_and_draft',links=None):
        self.library(links)
        self.run=self.root/'expression-run'
        m.create_run(self.root/'paper',self.root/'knowledge',self.run,goodpaper_cases=False,
                     expression_library=self.lib,expression_mode=mode)

    def task_map(self):
        return {'tasks':[{'id':'AT1','anchors':[A],'scope':'paragraph','section_task':'receiver input',
                          'rhetorical_relation':'observation before detector input',
                          'retrieval_terms':['observation','detector']}],
                'page_coverage':[{'page':1,'status':'mapped','reason':'Synthetic observation task.'}], 'limits':[]}

    def advance(self):
        request=m.next_request(self.run);stage=request['stage'];ctx=m.context_for(self.run,stage)
        result=self.task_map() if stage=='advisor_tasks' else answer(stage,ctx)
        if ctx.get('expression_version'):
            for n,record in enumerate(ctx['expression_sources']['records'],1):
                result['writing_transfers'].append(transfer(stage,id=stage+':W'+str(n),
                    source_kind='mentor_expression',source_id=record['id'],source_excerpt=record['mentor_texts'][0]['text']))
            result['expression_task_dispositions']=[{'task_id':t['id'],'status':'checked',
                 'transfer_ids':[r['id'] for r in result['writing_transfers']],'reason':'Synthetic task inspected.'}
                 for t in ctx['expression_tasks']]
        m.accept_response(self.run,result,{'kind':'synthetic_fixture','model_called':False})
        return request,result

    def test_mentor_text_and_identity_are_bound(self):
        self.library();altered=copy.deepcopy(self.records)
        altered[0]['evidence_refs'].append('E1')
        e.check_records(altered,self.episodes,['T0'])
        altered[0]['mentor_texts'][0]['text']='Invented mentor paragraph.'
        with self.assertRaisesRegex(ValueError,'changed actual mentor'):e.check_records(altered,self.episodes,['T0'])
        self.episodes[0]['feedback'][0]['author']='student'
        with self.assertRaisesRegex(ValueError,'confirmed mentor'):e.check_records(self.records,self.episodes,['T0'])

    def test_expression_only_task_retrieves_without_concern_link(self):
        self.new_run(links=[])
        request,_=self.advance()
        self.assertEqual(request['module_name'],'Advisor')
        self.assertNotIn('cards',m.context_for(self.run,'advisor_tasks'))
        ctx=m.context_for(self.run,'supplement_1')
        self.assertEqual([r['id'] for r in ctx['expression_sources']['records']],['EXP1'])
        self.assertNotIn('objects',ctx);self.assertNotIn('goodpaper_cases',ctx)
        self.assertEqual([c['id'] for c in ctx['cards']],['T0'])

    def test_conditional_companion_is_preserved_without_promoting_held_actions(self):
        self.library(links=[])
        first=copy.deepcopy(self.records[0])
        second=copy.deepcopy(first)
        second.update(id='EXP2',section_task='Distinct prerequisite',
                      changed_relationship='Distinct prerequisite',retrieval_terms=['prerequisite'])
        first['local_reference_bindings']=[
            {'source_local_id':'E02','expression_id':'EXP2','status':'admitted'},
            {'source_local_id':'E03','expression_id':None,'status':'held'}]
        second['local_reference_bindings']=[{'source_local_id':'E01','expression_id':'EXP1','status':'admitted'}]
        library=e.build([first,second],self.episodes,self.root/'private/dependencies',[])
        route=e.route(library,self.task_map()['tasks'],{'supplement_1':[]},top_k=1)
        assigned=route['assignments']['supplement_1']
        self.assertEqual(assigned['record_ids'],['EXP1','EXP2'])
        companions=[r for r in assigned['candidates'] if r['basis']=='explicit_source_learning_companion']
        self.assertEqual([r['record_id'] for r in companions],['EXP2'])
        source_view=e.view(library,['EXP1'])
        self.assertEqual([r['id'] for r in source_view['records']],['EXP1','EXP2'])
        self.assertEqual(source_view['records'][1]['mentor_texts'],second['mentor_texts'])
        self.assertEqual([r['id'] for r in source_view['episodes']],['E1'])
        self.assertEqual(e.admitted_closure({r['id']:r for r in [first,second]},['EXP1']),{'EXP1','EXP2'})
        with self.assertRaisesRegex(ValueError,'Missing admitted Expression companion'):
            e.admitted_closure({'EXP1':first},['EXP1'])

    def test_companion_route_can_resume_across_process_hash_seeds(self):
        self.library(links=[])
        first=copy.deepcopy(self.records[0]);second=copy.deepcopy(first);third=copy.deepcopy(first)
        second['id']='EXP2'
        third.update(id='EXP3',section_task='Distinct prerequisite',
                     changed_relationship='Distinct prerequisite',retrieval_terms=['prerequisite'])
        for record in [first,second]:
            record['local_reference_bindings']=[{'source_local_id':'E03','expression_id':'EXP3','status':'admitted'}]
        library=e.build([first,second,third],self.episodes,self.root/'private/resumable',[])
        code='import sys,json;sys.path.insert(0,sys.argv[1]);import expression_runtime as e;print(json.dumps(e.route(sys.argv[2],json.loads(sys.argv[3]),{"supplement_1":[]},top_k=2),sort_keys=True))'
        args=[sys.executable,'-c',code,str(m.ROOT/'scripts'),str(library),json.dumps(self.task_map()['tasks'])]
        outputs=[subprocess.check_output(args,env={**os.environ,'PYTHONHASHSEED':seed},text=True) for seed in ['1','9']]
        self.assertEqual(outputs[0],outputs[1])

    def test_blank_deletion_preserves_action_without_inventing_mentor_words(self):
        self.library()
        record=copy.deepcopy(self.records[0]);episode=copy.deepcopy(self.episodes[0])
        episode['feedback'][0].update(mentor_text='',subtype='/StrikeOut',marked_text='redundant explanation')
        record.update(authority='explicit_editorial_action',mentor_texts=[{'ref':'a1','text':''}],
                      marked_texts=[{'ref':'a1','text':'redundant explanation','action':'delete'}])
        e.check_records([record],[episode],['T0'])
        self.assertEqual(w.source_texts('mentor_expression',record),['','redundant explanation'])
        record['marked_texts'][0]['text']='invented deletion'
        with self.assertRaisesRegex(ValueError,'exact attributed source span'):
            e.check_records([record],[episode],['T0'])

    def test_blank_highlight_cannot_be_certified_as_a_deletion(self):
        self.library()
        record=copy.deepcopy(self.records[0]);episode=copy.deepcopy(self.episodes[0])
        episode['feedback'][0].update(mentor_text='',subtype='/Highlight',marked_text='highlighted phrase')
        record.update(authority='explicit_editorial_action',mentor_texts=[{'ref':'a1','text':''}],
                      marked_texts=[{'ref':'a1','text':'highlighted phrase','action':'delete'}])
        with self.assertRaisesRegex(ValueError,'exact attributed source span'):
            e.check_records([record],[episode],['T0'])

    def test_mixed_replacement_keeps_blank_deletion_and_literal_insertion_separate(self):
        self.library()
        record=copy.deepcopy(self.records[0]);episode=copy.deepcopy(self.episodes[0])
        episode['feedback'].append({'ref':'a2','author':'mentor_confirmed','mentor_text':'',
                                    'subtype':'/StrikeOut','marked_text':'Thus,'})
        record['mentor_texts'].append({'ref':'a2','text':''});record['evidence_refs'].append('a2')
        record['marked_texts']=[{'ref':'a2','text':'Thus,','action':'delete'}]
        e.check_records([record],[episode],['T0'])
        record['mentor_texts'][0]['text']='';episode['feedback'][0]['mentor_text']=''
        episode['feedback'][0].update(subtype='/StrikeOut',marked_text='old lead')
        record['marked_texts'].append({'ref':'a1','text':'old lead','action':'delete'})
        with self.assertRaisesRegex(ValueError,'lacks actual wording'):
            e.check_records([record],[episode],['T0'])

    def test_full_library_projection_keeps_context_and_legacy_views(self):
        self.library()
        records=m.read(self.lib/'records.json')
        records[0]['language_choices']=[{'mentor_proposal':'Explain the observation'},
            {'mentor_proposal':'Explain ... detector use.'},{'mentor_proposal':''}]
        m.save(self.lib/'records.json',records)
        records_hash=m.sha(self.lib/'records.json')
        self.assertEqual(e.view(self.lib,['EXP1'])['records'],records)
        episodes=m.read(self.lib/'episodes.json')
        episodes[0].update(neighboring_page_text=[{'page':2,'text':'Complete neighboring paragraph.'}],
                           related_concerns=[{'id':'duplicate analytical card'}])
        episodes[0]['feedback'][0]['quad_points']=[1,2,3,4]
        m.save(self.lib/'episodes.json',episodes)
        self.assertIn('quad_points',e.view(self.lib,['EXP1'])['episodes'][0]['feedback'][0])
        manifest=m.read(self.lib/'manifest.json');manifest['expression_episode_projection']=2
        m.save(self.lib/'manifest.json',manifest)
        selected=e.view(self.lib,['EXP1'])
        view=selected['episodes'][0]
        self.assertEqual(view['neighboring_page_text'],episodes[0]['neighboring_page_text'])
        self.assertEqual(view['feedback'][0]['mentor_text'],episodes[0]['feedback'][0]['mentor_text'])
        self.assertNotIn('quad_points',view['feedback'][0]);self.assertNotIn('related_concerns',view)
        choices=selected['records'][0]['language_choices']
        self.assertEqual([c['proposal_source_match']['kind'] for c in choices],
            ['verbatim_mentor_excerpt','analysis_not_verbatim','not_supplied'])
        self.assertEqual(choices[0]['proposal_source_match']['refs'],['a1'])
        self.assertEqual(choices[1]['mentor_proposal'],'Explain ... detector use.')
        self.assertEqual(selected['records'][0]['mentor_texts'],records[0]['mentor_texts'])
        self.assertEqual(m.sha(self.lib/'records.json'),records_hash)

    def test_conditional_lists_preserve_source_learning_output(self):
        self.library()
        record=copy.deepcopy(self.records[0])
        for field in e.LIST_OR_TEXT_FIELDS:
            record[field]=[record[field]]
        e.check_records([record],self.episodes,['T0'])
        record['transfer_conditions']=['']
        with self.assertRaisesRegex(ValueError,'transfer_conditions'):
            e.check_records([record],self.episodes,['T0'])

    def test_neighbor_page_context_does_not_become_mentor_wording(self):
        self.library()
        record=copy.deepcopy(self.records[0]);context=copy.deepcopy(self.episodes[0])
        context.update(id='E2',feedback=[])
        record['context_episode_ids']=['E2'];record['evidence_refs'].append('E2')
        e.check_records([record],self.episodes+[context],['T0'])
        library=e.build([record],self.episodes+[context],self.root/'private/neighbors',['T0'])
        self.assertEqual({r['id'] for r in e.view(library,['EXP1'])['episodes']},{'E1','E2'})
        record['mentor_texts'].append({'ref':'E2','text':'Invented neighbor quotation.'})
        with self.assertRaisesRegex(ValueError,'confirmed mentor'):
            e.check_records([record],self.episodes+[context],['T0'])

    def test_no_match_still_requires_task_inspection(self):
        self.library(links=[])
        task=self.task_map()['tasks'][0]
        task.update(section_task='zebra',rhetorical_relation='quartz',retrieval_terms=['zenith'])
        route=e.route(self.lib,[task],{'supplement_1':[]})
        self.assertEqual(route['assignments']['supplement_1']['record_ids'],[])
        ctx={'expression_tasks':[task]}
        with self.assertRaisesRegex(ValueError,'coverage'):e.validate_dispositions({'writing_transfers':[]},ctx)
        with self.assertRaisesRegex(ValueError,'inspection record'):
            e.validate_dispositions({'writing_transfers':[],'expression_task_dispositions':[{'task_id':'AT1','status':'checked','reason':'Checked','transfer_ids':[]}]},ctx)

    def test_frozen_route_rejects_mutation(self):
        self.new_run();self.advance();m.context_for(self.run,'supplement_1')
        route=m.read(self.run/'expression_route.json');route['top_k']=99;m.save(self.run/'expression_route.json',route)
        with self.assertRaisesRegex(ValueError,'route changed'):m.context_for(self.run,'supplement_1')

    def test_advisor_task_map_cannot_use_verdict_or_drop_page(self):
        result=self.task_map();result['tasks'][0]['gap']='Pre-judged'
        with self.assertRaisesRegex(ValueError,'pre-judge'):e.validate_tasks(result,[{'page':1,'text':A['quote']}],m.anchor)
        result=self.task_map();result['page_coverage']=[]
        with self.assertRaisesRegex(ValueError,'coverage'):e.validate_tasks(result,[{'page':1,'text':A['quote']}],m.anchor)

    def test_retained_expression_reaches_actual_drafting_packet(self):
        self.new_run()
        while m.next_request(self.run):self.advance()
        packet=w.packet(self.run,m)
        self.assertEqual([r['id'] for r in packet['expression_sources']['records']],['EXP1'])
        request=draft.prepare(self.run,self.root/'draft')
        prompt=m.read(request)['prompt']
        self.assertIn(self.records[0]['mentor_texts'][0]['text'],prompt)
        self.assertIn('expression_uses',prompt)
        m.verify_frozen(self.root/'draft/inputs')

    def test_draft_only_adds_no_discovery_stage_or_advisor_source(self):
        self.new_run(mode='draft_only')
        self.assertNotIn('advisor_tasks',m.read(self.run/'inputs/protocol.json')['stages'])
        self.assertNotIn('expression_sources',m.context_for(self.run,'supplement_1'))
        while m.next_request(self.run):self.advance()
        packet=w.packet(self.run,m)
        self.assertTrue(packet['draft_expression_links'])
        self.assertTrue(packet['expression_sources']['records'])

    def test_snapshot_rejects_public_raw_text_and_changed_sources(self):
        self.library()
        with self.assertRaisesRegex(ValueError,'private storage'):
            e.build(self.records,self.episodes,self.root/'public',['T0'])
        unresolved=copy.deepcopy(self.records)
        unresolved[0]['preference_status']='unresolved'
        with self.assertRaisesRegex(ValueError,'Unresolved Expression'):
            e.build(unresolved,self.episodes,self.root/'private/unresolved',['T0'])
        Path=__import__('pathlib').Path
        Path(self.episodes[0]['source_path']).write_text('Changed',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'source changed'):
            e.build(self.records,self.episodes,self.root/'private/changed',['T0'])

    def test_original_case_passages_keep_actual_text_and_paper_identity(self):
        library=self.root/'private/passages';library.mkdir(parents=True)
        m.save(library/'manifest.json',{'role':'private_published_case_passages'})
        m.save(library/'case_links.json',{'C1':{'paper_id':'P1','anchor_pages':[2]}})
        m.save(library/'sources.json',{'P1':{'paper_id':'P1','source_path':'private original',
                 'source_sha256':'synthetic','page_count':4,
                 'pages':[{'page':n,'text':'Actual source page '+str(n)} for n in range(1,5)]}})
        case={'case_id':'C1','paper_id':'P1','full_case':{'reader_task':'Task'}}
        selection=goodpaper.with_passages({'complete_cases':[case],'same_task_companions':[]},library)
        passage=selection['complete_cases'][0]['source_passages']
        self.assertEqual([p['page'] for p in passage['pages']],[1,2,3])
        self.assertNotIn('source_path',passage)
        self.assertIn('Actual source page 2',w.source_texts('published_case',case))
        case['paper_id']='different'
        with self.assertRaisesRegex(ValueError,'different paper'):
            goodpaper.with_passages({'complete_cases':[case],'same_task_companions':[]},library)

    def test_original_case_excerpt_cannot_be_mislabelled_as_analyst_summary(self):
        self.advance();ctx=m.context_for(self.run,'reader');result=answer('reader',ctx)
        ctx['goodpaper_cases']={'complete_cases':[{'case_id':'P1',
            'full_case':{'full_relation_chain':'Analyst summary wording.'},
            'source_passages':{'pages':[{'page':1,'text':'Actual source wording.'}]}}]}
        row=transfer(source_kind='published_case',source_id='P1',source_excerpt='Actual source wording.',
                     excerpt_basis='original_page_text',decision='keep',finding_ids=[])
        result['writing_transfers']=[row];pages={p['page']:p['text'] for p in ctx['manuscript']}
        w.validate('reader',result,ctx,pages,m.anchor)
        self.assertIn('excerpt_basis',w.review_schema(ctx))
        row['excerpt_basis']='analyst_summary'
        with self.assertRaisesRegex(ValueError,'excerpt absent'):w.validate('reader',result,ctx,pages,m.anchor)
        row.pop('excerpt_basis')
        with self.assertRaisesRegex(ValueError,'identify excerpt origin'):w.validate('reader',result,ctx,pages,m.anchor)

    def test_draft_attribution_requires_an_actual_related_expression_use(self):
        self.library()
        evidence={'expression_version':1,'expression_sources':{'records':self.records},
                  'writing_transfers':[], 'raw_to_final':[],
                  'draft_expression_links':[{'verified_id':'verify:F1','expression_ids':['EXP1']}]}
        final={'findings':[{'id':'verify:F1'},{'id':'verify:F2'}]}
        row={'verified_id':'verify:F1','report_excerpt':'Explain input.','basis':'mentor_expression',
             'case_ids':[],'card_ids':[],'transfer_ids':[],'expression_ids':['EXP1'],
             'expression_uses':[{'expression_id':'EXP1','source_excerpt':self.records[0]['mentor_texts'][0]['text'],
                'borrowed_operation':'Explain before use.','target_application':'Name the observation source.',
                'do_not_transfer':'Do not invent access conditions.'}],
             'use_explanation':'Apply the observed handoff.','target_support':[A]}
        other={**row,'verified_id':'verify:F2','basis':'target_analysis','expression_ids':[],'expression_uses':[]}
        response={'report_markdown':'Explain input.','revision_attribution':[row,other]}
        w.validate_proposals(response,evidence,final,[{'page':1,'text':A['quote']}],m.anchor)
        other.update(basis='mentor_expression',expression_ids=['EXP1'],expression_uses=row['expression_uses'])
        with self.assertRaisesRegex(ValueError,'unrelated Expression'):
            w.validate_proposals(response,evidence,final,[{'page':1,'text':A['quote']}],m.anchor)

    def test_draft_companion_attribution_stays_bound_to_its_linked_item(self):
        self.library()
        first=copy.deepcopy(self.records[0]);second=copy.deepcopy(first);second['id']='EXP2'
        first['local_reference_bindings']=[{'source_local_id':'E02','expression_id':'EXP2','status':'admitted'},
            {'source_local_id':'E03','expression_id':None,'status':'held'}]
        evidence={'expression_version':1,'expression_sources':{'records':[first,second]},
            'writing_transfers':[],'raw_to_final':[],
            'draft_expression_links':[{'verified_id':'verify:F1','expression_ids':['EXP1']}]}
        final={'findings':[{'id':'verify:F1'},{'id':'verify:F2'}]}
        row={'verified_id':'verify:F1','report_excerpt':'Explain input.','basis':'mentor_expression',
            'case_ids':[],'card_ids':[],'transfer_ids':[],'expression_ids':['EXP2'],
            'expression_uses':[{'expression_id':'EXP2','source_excerpt':second['mentor_texts'][0]['text'],
                'borrowed_operation':'Retain the explicit companion prerequisite.',
                'target_application':'Explain the observation before use.',
                'do_not_transfer':'Do not invent target access facts.'}],
            'use_explanation':'Use the admitted companion of this item’s actual linked source.','target_support':[A]}
        other={**row,'verified_id':'verify:F2','basis':'target_analysis','expression_ids':[],'expression_uses':[]}
        response={'report_markdown':'Explain input.','revision_attribution':[row,other]}
        w.validate_proposals(response,evidence,final,[{'page':1,'text':A['quote']}],m.anchor)
        other.update(basis='mentor_expression',expression_ids=['EXP2'],expression_uses=row['expression_uses'])
        with self.assertRaisesRegex(ValueError,'unrelated Expression'):
            w.validate_proposals(response,evidence,final,[{'page':1,'text':A['quote']}],m.anchor)


if __name__=='__main__':unittest.main()
