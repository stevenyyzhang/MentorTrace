"""Evidence/actual-text invariants; these tests do not grade mentor style."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import expression_realization as r
import test_expression
import test_pipeline
import writing_transfer
import prepare_revision_proposals


def fixture():
    record={'id':'EXP1','mentor_texts':[{'ref':'a1','text':'The task is to estimate the range.'}],
        'marked_texts':[],'local_reference_bindings':[], 'section_task':'state a task',
        'observed_change':'Use a task-centered subject.','transfer_conditions':'An established task.',
        'do_not_transfer':'Source ranging facts.', 'language_choices':[{
            'role':'task subject','original':'We estimate.',
            'mentor_proposal':'The task is to estimate the range.',
            'operation':'Use task as subject with is to.','conditions':'Target task established.'}]}
    record['language_features']=r.derive(record)[0]
    record['language_features'][0]['body_evidence']={'body_form_allowed':True,'basis':'synthetic explicit insertion'}
    evidence={'expression_realization':1,'expression_sources':{'records':[record]},
        'raw_to_final':[],'writing_transfers':[],
        'draft_expression_links':[{'verified_id':'G1','expression_ids':['EXP1']}]}
    text='The task is to estimate the target position.'
    f={'expression_id':'EXP1','feature_id':'EXP1:L1','decision':'adapt',
       'realization_type':'language_form',
       'evidence_kind':'mentor_prose','source_ref':'a1','source_quote':record['mentor_texts'][0]['text'],
       'requested_feature':'Task subject and is-to complement.','target_quote':text,
       'realization_explanation':'Task subject retained in target sentence.',
       'preserved_meaning':'Target position task only.','adaptations':'Range replaced by target position.',
       'reason':'Same rhetorical task.'}
    response={'report_markdown':'Explanation.\n\n'+text,
        'revision_actions':[{'draft_label':'D1','verified_ids':['G1']}],
        'language_realizations':[{'draft_label':'D1','verified_ids':['G1'],'scope':'prose',
            'passages':[{'id':'P1','text':text}],'source_disposition':'used','reason':'Supported task sentence.',
            'feature_decisions':[f]}]}
    review={'reviewer':'synthetic independent reviewer','groups':[{'draft_label':'D1',
        'meaning':{'status':'pass','reason':'Target task unchanged.'},
        'naturalness':{'status':'pass','reason':'Complete task statement.'},
        'feature_results':[{'expression_id':'EXP1','feature_id':'EXP1:L1',
            'status':'confirmed','reason':'Actual task subject and is-to clause.'}]}]}
    return record,evidence,response,review


class Realization(unittest.TestCase):
    def test_reuse_preserves_genre_uncertainty_and_holds_analytical_wording(self):
        record,_,_,_=fixture()
        record['language_choices'].append({**record['language_choices'][0],
            'mentor_proposal':'Invented fluent replacement.'})
        features,held=r.derive(record)
        self.assertEqual(len(features),1);self.assertEqual(len(held),1)
        self.assertEqual(features[0]['evidence_kind'],'mentor_excerpt_unclassified')
        self.assertEqual(features[0]['frame'],'')
        record['mentor_texts'].append({'ref':'a2','text':','})
        record['language_choices'].append({**record['language_choices'][0],'mentor_proposal':','})
        self.assertEqual(len(r.derive(record)[1]),2)
        record['language_choices'][0]['operation']='Held scientific dependency'
        self.assertEqual(r.derive(record)[0],[])

    def test_comment_cannot_substitute_for_actual_replacement(self):
        _,e,x,_=fixture();r.validate_draft(x,e)
        x['language_realizations'][0]['feature_decisions'][0]['target_quote']='Explanation.'
        with self.assertRaisesRegex(ValueError,'actual replacement'):r.validate_draft(x,e)

    def test_unsupplied_and_wrong_task_sources_are_rejected(self):
        _,e,x,_=fixture()
        e['draft_expression_links'][0]['verified_id']='different-task'
        with self.assertRaisesRegex(ValueError,'unrelated'):r.validate_draft(x,e)
        e['draft_expression_links'][0]['verified_id']='G1'
        x['language_realizations'][0]['feature_decisions'][0]['feature_id']='EXP1:L2'
        with self.assertRaisesRegex(ValueError,'unknown/held'):r.validate_draft(x,e)

    def test_exact_evidence_and_contextual_genre_required(self):
        _,e,x,_=fixture();f=x['language_realizations'][0]['feature_decisions'][0]
        f['evidence_kind']='mentor_excerpt_unclassified'
        with self.assertRaisesRegex(ValueError,'contextual'):r.validate_draft(x,e)
        f['evidence_kind']='mentor_prose';f['source_quote']='The goal is to estimate the range.'
        with self.assertRaisesRegex(ValueError,'changed source'):r.validate_draft(x,e)

    def test_fluent_comment_cannot_be_learned_as_manuscript_syntax(self):
        record,e,x,_=fixture()
        record['language_features'][0]['body_evidence']['body_form_allowed']=False
        with self.assertRaisesRegex(ValueError,'Comment cannot'):r.validate_draft(x,e)
        x['language_realizations'][0]['feature_decisions'][0]['realization_type']='editorial_operation'
        r.validate_draft(x,e)
        episode={'id':'EP1','feedback':[{'ref':'a1','subtype':'/Text','object_id':1,
            'marked_text':'unrelated equation','mentor_text':record['mentor_texts'][0]['text']}]}
        record['episode_ids']=['EP1']
        admission=r.body_evidence(record['language_features'][0],record,{'EP1':episode})
        self.assertFalse(admission['body_form_allowed'])

    def test_all_groups_and_features_accounted_without_forcing_use(self):
        _,e,x,_=fixture();row=x['language_realizations'][0]
        row.update(scope='no_rewrite',passages=[],source_disposition='no_rewrite')
        row['feature_decisions'][0].update(decision='not_applicable',target_quote='',reason='Existing wording already supplies this role.')
        self.assertEqual(r.validate_draft(x,e)['used_features'],0)
        row['source_disposition']='used'
        with self.assertRaisesRegex(ValueError,'False'):r.validate_draft(x,e)
        x['language_realizations']=[]
        with self.assertRaisesRegex(ValueError,'coverage'):r.validate_draft(x,e)

    def test_action_only_does_not_claim_unwritten_sentence(self):
        _,e,x,_=fixture();row=x['language_realizations'][0]
        row.update(scope='action_only',passages=[])
        row['feature_decisions'][0]['realization_type']='editorial_operation'
        row['feature_decisions'][0]['target_quote']='Explanation.'
        r.validate_draft(x,e)
        row['passages']=[{'id':'P1','text':'Explanation.'}]
        with self.assertRaisesRegex(ValueError,'Action-only'):r.validate_draft(x,e)

    def test_semantic_rejection_and_changed_final_text_block_review(self):
        _,e,x,review=fixture();r.validate_review(x,e,review,x['report_markdown'])
        review['groups'][0]['feature_results'][0].update(status='rejected',reason='Instruction was used as body prose.')
        with self.assertRaisesRegex(ValueError,'rejected'):r.validate_review(x,e,review)
        review['groups'][0]['feature_results'][0]['status']='confirmed'
        with self.assertRaisesRegex(ValueError,'passage changed'):r.validate_review(x,e,review,'Changed paragraph.')
        review['groups'][0]['meaning']['status']='fail'
        with self.assertRaisesRegex(ValueError,'meaning'):r.validate_review(x,e,review)

    def test_hash_bound_final_review_cannot_be_reused_after_evidence_edit(self):
        _,e,x,review=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);r.write(tmp/'response.json',x);r.write(tmp/'evidence.json',e)
            binding={k:{'path':str(tmp/(k+'.json')),'sha256':r.sha(tmp/(k+'.json'))} for k in ['response','evidence']}
            binding['review']=review;r.validate_delivery_binding(binding,x['report_markdown'])
            e['expression_sources']['records'][0]['mentor_texts'][0]['text']='Changed'
            r.write(tmp/'evidence.json',e)
            with self.assertRaisesRegex(ValueError,'Stale'):r.validate_delivery_binding(binding,x['report_markdown'])

    def test_legacy_proposals_unchanged(self):
        self.assertEqual(r.validate_draft({},{}),{'status':'legacy_contract'})

    def test_full_inventory_reuses_sources_without_mutating_old_snapshot(self):
        record,_,_,_=fixture();record.pop('language_features')
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)/'private'/'base';base.mkdir(parents=True)
            r.write(base/'records.json',[record]);r.write(base/'episodes.json',[])
            r.write(base/'manifest.json',{'count':1,'role':'private_advisor_expression'})
            r.write(base/'FREEZE.json',{'files':{n:r.sha(base/n) for n in ['records.json','episodes.json','manifest.json']}})
            before=r.sha(base/'records.json');dest=base.parent/'enhanced'
            counts=r.build_snapshot(base,dest)
            self.assertEqual(counts['records'],1);self.assertEqual(counts['features'],1)
            self.assertEqual(r.sha(base/'records.json'),before)
            self.assertEqual(r.read(dest/'records.json')[0]['mentor_texts'],record['mentor_texts'])
            with self.assertRaisesRegex(ValueError,'New private'):r.build_snapshot(base,dest)


class RealizationIntegration(unittest.TestCase):
    setUp=test_pipeline.Pipeline.setUp
    tearDown=test_pipeline.Pipeline.tearDown
    library=test_expression.Expression.library
    task_map=test_expression.Expression.task_map
    advance=test_expression.Expression.advance

    def test_enhanced_snapshot_reaches_actual_proposal_prompt(self):
        self.library()
        enhanced=self.root/'private'/'enhanced'
        r.build_snapshot(self.lib,enhanced)
        self.run=self.root/'enhanced-run'
        m=test_pipeline.m
        m.create_run(self.root/'paper',self.root/'knowledge',self.run,
            goodpaper_cases=False,expression_library=enhanced)
        for _ in range(30):
            if m.next_request(self.run) is None:break
            self.advance()
        self.assertIsNone(m.next_request(self.run))
        evidence=writing_transfer.packet(self.run,m)
        self.assertEqual(evidence['expression_realization'],1)
        path=prepare_revision_proposals.prepare(self.run,self.root/'draft')
        request=m.read(path)
        self.assertIn('LANGUAGE REALIZATION v1',request['prompt'])
        self.assertTrue((path.parent/'realization_review_contract.json').exists())
        self.assertIn('expression-realization.md',m.read(path.parent/'inputs/FREEZE.json')['files'])
        with self.assertRaisesRegex(ValueError,'group coverage'):
            r.validate_draft({'revision_actions':[{'draft_label':'D1','verified_ids':['G1']}]},evidence)


if __name__=='__main__':unittest.main()
