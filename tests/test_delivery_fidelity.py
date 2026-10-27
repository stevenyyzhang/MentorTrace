"""Explicit reuse and report economy; no model calls or generated judgments."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import mentortrace_v1 as m
import review_workflow as w
import verification_basis as basis
import report_concision as economy
import test_pipeline as fixtures
from test_preservation import complete_target_actions


class FrozenVerificationReuse(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.Pipeline();self.f.setUp();self.addCleanup(self.f.tearDown)
        while m.next_request(self.f.run):self.f.advance()
        self.binding=basis.build(self.f.run);self.assertTrue(self.binding['available'])
        self.finding=m.read(self.f.run/'final.json')['findings'][0]
        self.report=self.f.root/'report.md';self.report.write_text(self.finding['gap'],encoding='utf-8')
        self.ledger=w.preservation.initialize(self.report,[self.f.run/'final.json'])
        complete_target_actions(self.ledger)
        self.ledger['verified_review_reuse']=self.binding
        self.assertion={'quote':self.finding['gap'],'status':'reused_verified','reason':'Synthetic actual comparison to unchanged frozen statement',
            'reuse_reference':{'finding_id':self.finding['id'],'field':'gap','comparison':{
                'same_claim':True,'conditions_and_uncertainty_preserved':True,'no_new_fact':True,
                'reason':'Synthetic exact gap statement; no new author action or condition asserted'}}}
        self.ledger['target_units'][0]['review'].update(classification='factual',assertions=[self.assertion])

    def test_explicit_same_claim_reuses_verification_without_new_manuscript_evidence(self):
        result=w.preservation.validate_target_review(self.ledger,self.report)
        self.assertEqual(result['target_blocks'],1)
        self.assertNotIn('evidence',self.assertion)

    def test_hashes_alone_do_not_approve_semantic_reuse(self):
        self.assertion['reuse_reference'].pop('comparison')
        with self.assertRaisesRegex(ValueError,'Explicit unchanged-claim comparison'):
            w.preservation.validate_target_review(self.ledger,self.report)

    def test_new_or_broader_claim_cannot_reuse_prior_judgment(self):
        for key in ['same_claim','conditions_and_uncertainty_preserved','no_new_fact']:
            self.assertion['reuse_reference']['comparison'][key]=False
            with self.subTest(key=key),self.assertRaises(ValueError):
                w.preservation.validate_target_review(self.ledger,self.report)
            self.assertion['reuse_reference']['comparison'][key]=True

    def test_future_author_action_is_not_a_verified_fact(self):
        self.assertion['reuse_reference']['field']='closure_goal'
        with self.assertRaisesRegex(ValueError,'future action'):
            w.preservation.validate_target_review(self.ledger,self.report)

    def test_changed_manuscript_invalidates_reuse(self):
        path=self.f.run/'inputs/paper/body.json';body=m.read(path);body[0]['text']+=' New evidence.';m.save(path,body)
        with self.assertRaisesRegex(ValueError,'reuse source changed'):
            w.preservation.validate_target_review(self.ledger,self.report)

    def test_new_supported_fact_still_requires_direct_evidence(self):
        self.assertion['status']='supported';self.assertion['evidence']=[]
        with self.assertRaisesRegex(ValueError,'needs evidence'):
            w.preservation.validate_target_review(self.ledger,self.report)

    def test_reuse_without_accepted_chain_is_not_available(self):
        self.ledger.pop('verified_review_reuse')
        with self.assertRaisesRegex(ValueError,'bound verified review'):
            w.preservation.validate_target_review(self.ledger,self.report)
        (self.f.run/'calls/verify/record.json').unlink()
        self.assertFalse(basis.build(self.f.run)['available'])


class ReportEconomy(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.response={'language_realizations':[{'draft_label':'noise','passages':[{'id':'p1','text':'We estimate noise using [METHOD] from [DATA].'}]}]}

    def test_real_math_intervals_and_original_quotes_are_not_placeholder_findings(self):
        units=[{'id':'T:B1','kind':'block','context_id':'C1','text':'Original: [DATA]'},
               {'id':'T:D1','kind':'suggested_wording','context_id':'C2','text':'Let x belong to [0, 2π].'}]
        self.assertEqual(economy.candidates({},units),[])

    def test_missing_candidate_dispositions_never_default_pass(self):
        items=economy.candidates(self.response);self.assertEqual(len(items),2)
        with self.assertRaisesRegex(ValueError,'explicit individual'):
            economy.validate({'status':'pass','reason':'Synthetic check','placeholder_results':[]},items,w.preservation.validate_evidence)

    def test_author_placeholders_block_even_if_overall_label_says_pass(self):
        items=economy.candidates(self.response)
        review={'status':'pass','reason':'Synthetic scope','placeholder_results':[{
            'candidate_id':p['id'],'decision':'author_placeholder','reason':'Required facts are absent'} for p in items]}
        with self.assertRaisesRegex(ValueError,'author placeholder'):
            economy.validate(review,items,w.preservation.validate_evidence)

    def test_literal_notation_requires_manuscript_support_not_report_self_citation(self):
        response={'language_realizations':[{'draft_label':'literal','passages':[{'id':'p1','text':'The matrix [DATA] is defined above.'}]}]}
        items=economy.candidates(response);paper=self.root/'paper.txt';paper.write_text('The matrix [DATA] is defined above.',encoding='utf-8')
        evidence={'path':str(paper),'sha256':m.sha(paper),'quote':'The matrix [DATA]','basis':'manuscript'}
        review={'status':'pass','reason':'Synthetic literal notation comparison','placeholder_results':[{
            'candidate_id':'P1','decision':'literal_notation','reason':'The original uses this notation','evidence':[evidence]}]}
        economy.validate(review,items,w.preservation.validate_evidence,{str(paper)})
        with self.assertRaisesRegex(ValueError,'actual manuscript'):
            economy.validate(review,items,w.preservation.validate_evidence,set())

    def test_draft_instruction_preserves_substance_and_rejects_fill_in_paragraphs(self):
        self.assertIn('do not fabricate',economy.DRAFT_INSTRUCTIONS)
        self.assertIn('No target',economy.DRAFT_INSTRUCTIONS)
        self.assertIn('both languages',economy.DRAFT_INSTRUCTIONS)


class CombinedFidelityIntegration(unittest.TestCase):
    def test_fidelity_and_concision_use_same_delivery_pass_and_both_gates(self):
        from test_merge_obligations import MergeObligationAudit
        from test_review_workflow import POLICY
        f=MergeObligationAudit();f.setUp();self.addCleanup(f.doCleanups)
        # Synthetic accepted verification, explicitly no model invocation.
        m.save(f.run/'inputs/protocol.json',{'verified_delivery_fidelity':1,'report_concision':1})
        m.freeze(f.run/'inputs')
        folder=f.run/'calls/verify';m.save(folder/'request.json',{'stage':'verify','prompt':'Synthetic verification; no model called'})
        m.save(folder/'raw_response.json',m.read(folder/'response.json'))
        m.save(folder/'record.json',{'schema_validated':True,**{key:m.sha(folder/name) for key,name in [
            ('request_sha256','request.json'),('response_sha256','response.json'),('raw_response_sha256','raw_response.json')]}})
        f.report.write_text(f.report.read_text(encoding='utf-8')+'\n\n'+'\n\n'.join(w.preservation.blocks(f.run/'final.json')),encoding='utf-8')
        old_b=f.ready_b();ledger=w.preservation.initialize(f.report,[f.run/'final.json'])
        ledger['scope_review']={'reviewer':'synthetic','source_completeness':'Complete source scope','semantic_review':'Synthetic unchanged scope'}
        for row in ledger['units']:row['components']=[{'source_quote':row['text'],'obligation':row['text'],'status':'retained','target_quotes':[row['text']],'reason':'Synthetic unchanged source field'}]
        complete_target_actions(ledger);path=f.root/'template.json';m.save(path,ledger)
        bundle=f.root/'new-delivery';plan=w.prepare_delivery(f.out,path,bundle,POLICY)
        ctx=m.read(bundle/'context.json');self.assertEqual(ctx['verified_delivery_fidelity'],1);self.assertEqual(ctx['report_concision'],1)
        by_b={r['component_id']:r for r in old_b['components']};sources={u['id']:u for u in ledger['units']};targets={u['id']:u for u in ledger['target_units']}
        finding=m.read(f.run/'final.json')['findings'][0];changed=False;responses=[]
        inventory={t['id']:t for t in m.read(bundle/'inventory.json')}
        for entry in plan['packets']:
            request=m.read(bundle/entry['file']);rows=[]
            self.assertIn('POST-FREEZE FIDELITY MODE',request['prompt']);self.assertIn('CONCISE REPORT CONTRACT',request['prompt'])
            for tid in request['task_ids']:
                t=inventory[tid]
                if t['kind']=='coverage':value={k:v for k,v in by_b[t['key']].items() if k!='component_id'}
                elif t['kind']=='source_field':value={k:v for k,v in sources[t['key']].items() if k in {'components','non_substantive_reason'}}
                elif t['kind']=='target':
                    value=copy.deepcopy(targets[t['key']]['review'])
                    if not changed and targets[t['key']]['kind']=='block' and finding['gap'] in targets[t['key']]['text']:
                        value.update(classification='factual',assertions=[{'quote':finding['gap'],'status':'reused_verified','reason':'Synthetic exact frozen statement comparison',
                            'reuse_reference':{'finding_id':finding['id'],'field':'gap','comparison':{'same_claim':True,'conditions_and_uncertainty_preserved':True,'no_new_fact':True,'reason':'No new condition or fact'}}}]);changed=True
                else:value={'source_completeness':'All original requirements present','assertion_completeness':'Every assigned block examined','semantic_review':'Synthetic actual meaning comparison','issues':[],
                    'report_economy':{'status':'pass','reason':'Synthetic concise actions and no unresolved placeholder','placeholder_results':[]}}
                rows.append({'task_ids':[tid],'value':value})
            response=f.root/(entry['id']+'.json');m.save(response,{'packet_id':entry['id'],'request_sha256':request['request_sha256'],'reviewer':old_b['reviewer'],'results':rows});responses.append(response)
        self.assertTrue(changed)
        result=w.assemble_delivery(bundle,responses,f.root/'checked')
        self.assertEqual(result['preservation']['reused_verified_assertions'],1)
        self.assertTrue(result['consolidation']['delivery_ready'])


if __name__=='__main__':unittest.main()
