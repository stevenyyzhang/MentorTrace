import copy
import unittest
import advisor_wire as w
import advisor_batching as b
import expression_runtime as expression
import tempfile
from pathlib import Path
import hashlib
import json


class Wire(unittest.TestCase):
    def test_frozen_view_filters_only_historical_links_and_keeps_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            parent=Path(directory);library=parent/'expression';library.mkdir()
            records=[dict(id='E1',concern_ids=['C1','C2','C3'],operations=['Complete retained evidence'])]
            path=library/'records.json';path.write_text(json.dumps(records),encoding='utf-8')
            table=dict(corpus_sha256={'corpus/advisor-expression-v1/records.json':hashlib.sha256(path.read_bytes()).hexdigest()},
                links=[dict(expression_id='E1',concern_id='C1',kind='historical'),
                       dict(expression_id='E1',concern_id='C2',kind='uncertain'),
                       dict(expression_id='E1',concern_id='C3',kind='conditional')])
            (parent/'expression_concern_links.json').write_text(json.dumps(table),encoding='utf-8')
            derived=expression.frozen_active_links(library,records)
            self.assertEqual(derived[0]['concern_ids'],['C2','C3'])
            self.assertEqual(derived[0]['operations'],records[0]['operations'])
            self.assertEqual(records[0]['concern_ids'],['C1','C2','C3'])
            path.write_text('[]',encoding='utf-8')
            with self.assertRaises(ValueError):expression.frozen_active_links(library,records)

    def test_full_reconstruction_including_local_administration(self):
        evidence = 'Exact evidence, condition and uncertainty. ' * 12
        original = dict(advisor_batching={'model': 'test', 'effective_context': 123},
            manuscript=[{'page': 1, 'text': evidence}],
            expression_sources={'records': [dict(id='E'+str(i), publication_permission='authorized',
                source_context_limit=evidence, content_status='unconfirmed',
                conditions=[evidence], examples=[{'text': evidence}]) for i in range(10)]})
        frozen = copy.deepcopy(original)
        wire, admin = w.prepare(original)
        self.assertEqual(original, frozen)
        self.assertEqual(w.restore(w.unpack(wire), admin), original)
        self.assertLess(len(w.dump(wire)), len(w.dump(original)))
        review=w.unpack(wire)
        self.assertTrue(all(r['content_status']=='unconfirmed' for r in review['expression_sources']['records']))
        self.assertNotIn('publication_permission', review['expression_sources']['records'][0])
        self.assertEqual(review['manuscript'], original['manuscript'])

    def test_null_false_empty_and_heterogeneous_records_survive(self):
        value={'items':[{'a': None}, {'a': False, 'b': ''}, {'a': [], 'b': {}}]}
        self.assertEqual(w.unpack(w.pack(value)),value)
        for key in ['$same','$rows']:
            with self.assertRaises(ValueError): w.pack({'source':{key:'literal'}})

    def test_reason_reference_must_belong_to_same_source_and_use(self):
        use=dict(expression_id='E1',target_kind='concern',target_id='C1')
        ctx=dict(source_uses=[use],expression_tasks=[],context_only_tasks=[])
        transfer=dict(id='W1',source_kind='mentor_expression',source_id='E1',decision='keep')
        row=dict(**use,status='checked',transfer_ids=['W1'],reason_ref='W1')
        b.validate_uses(dict(source_use_dispositions=[row],writing_transfers=[transfer]),ctx)
        row['reason_ref']='W2'
        with self.assertRaises(ValueError):
            b.validate_uses(dict(source_use_dispositions=[row],writing_transfers=[transfer]),ctx)
        row['reason_ref']='W1';transfer['source_id']='E2'
        with self.assertRaises(ValueError):
            b.validate_uses(dict(source_use_dispositions=[row],writing_transfers=[transfer]),ctx)

if __name__=='__main__': unittest.main()
