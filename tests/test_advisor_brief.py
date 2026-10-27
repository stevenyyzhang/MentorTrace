import copy
import unittest
import advisor_output as output
import advisor_brief as brief
import writing_transfer as writing
import advisor_batching as batching


class BriefAssessment(unittest.TestCase):
    def setUp(self):
        self.ctx = {'advisor_output_contract':1,'advisor_expression_brief':1,
                    'advisor_direct_fulltext':1,'advisor_role_division':1,'expression_version':1,
                    'cards':[],'primary_card_ids':[],
                    'manuscript':[{'page':1,'text':'Terms are defined.'}],
                    'expression_sources':{'records':[{'id':'E1'}]},'source_uses':[]}
        self.row = {'id':'supplement_1:W1','source_id':'E1','assessment':'brief',
                    'decision':'keep','reason':'The plural subject already agrees with are.',
                    'target_anchors':[{'page':1,'quote':'Terms are defined.'}]}

    def response(self, row=None, ctx=None):
        return output.expand({'advisor_output_version':1,'definitions':{},'response':{
            'writing_transfers':[copy.deepcopy(row or self.row)],'findings':[],
            'checks':[],'card_dispositions':[],'source_use_dispositions':[],
            'organization_suggestions':[]}}, ctx or self.ctx)

    def validate(self, response):
        def anchor(a, pages):
            if a.get('quote') not in pages.get(a.get('page'), ''): raise ValueError('Bad anchor')
        writing.validate('supplement_1',response,self.ctx,{1:'Terms are defined.'},anchor)
        batching.validate_uses(response,self.ctx)

    def test_brief_without_duplicate_check_and_exact_roundtrip(self):
        r=self.response(); self.validate(r)
        self.assertEqual([],output.preflight(r,self.ctx)['issues'])
        self.assertEqual(r,output.expand(output.encode(r,self.ctx),self.ctx))
        self.assertNotIn('source_excerpt',r['writing_transfers'][0])

    def test_old_protocol_rejects_brief(self):
        ctx={**self.ctx};ctx.pop('advisor_expression_brief')
        with self.assertRaisesRegex(ValueError,'frozen protocol'): self.response(ctx=ctx)

    def test_cannot_hide_actions_or_adoption(self):
        for decision in ['required_repair','optional_improvement']:
            r=self.response({**self.row,'decision':decision})
            with self.assertRaisesRegex(ValueError,'complete evidence'): self.validate(r)
        r=self.response();r['writing_transfers'][0]['finding_ids']=['F1']
        with self.assertRaisesRegex(ValueError,'cannot claim'): self.validate(r)

    def test_evidence_and_explicit_reason_required(self):
        for change in [{'target_anchors':[]},{'reason':''},{'target_anchors':[{'page':1,'quote':'Invented'}]}]:
            with self.assertRaises(ValueError): self.validate(self.response({**self.row,**change}))

    def test_coverage_and_unknown_not_completed_use(self):
        r=self.response();r['writing_transfers']=[]
        with self.assertRaisesRegex(ValueError,'no transfer'):self.validate(r)
        r=self.response({**self.row,'decision':'unfinished','target_anchors':[]})
        self.validate(r)
        self.ctx['source_uses']=[{'expression_id':'E1','target_kind':'concern','target_id':'C1'}]
        r['source_use_dispositions']=[{**self.ctx['source_uses'][0],'status':'checked',
            'transfer_ids':['supplement_1:W1'],'reason_ref':'supplement_1:W1'}]
        with self.assertRaisesRegex(ValueError,'Unchecked'):self.validate(r)

if __name__ == '__main__': unittest.main()
