"""Offline output/reference and coverage regressions; no model/network calls."""
import copy
import unittest

import advisor_output as output
import advisor_batching as batching


class Output(unittest.TestCase):
    def setUp(self):
        self.context = {'advisor_output_contract': 1,
            'manuscript': [{'page': 1, 'text': 'First line.\nSecond line.\n'},
                           {'page': 2, 'text': 'Formula α ≠ β.\n'}],
            'cards': [], 'expression_sources': {'records': [{'id': 'E1'}, {'id': 'E2'}]},
            'source_uses': [{'expression_id': 'E1', 'target_kind': 'concern', 'target_id': 'C1'},
                            {'expression_id': 'E1', 'target_kind': 'concern', 'target_id': 'C2'}]}
        self.text = 'A source-specific target comparison, including its actual conditions and limitations. '

    def envelope(self, response, definitions=None):
        return {'advisor_output_version': 1, 'definitions': definitions or {}, 'response': response}

    def test_all_analysis_and_distinct_uses_round_trip(self):
        rows = []
        for i in range(1, 15):
            rows.append({'id': 's:W' + str(i), 'source_kind': 'mentor_expression', 'source_id': 'E1',
                'decision': 'keep', 'learned_distinction': self.text,
                'current_handling': self.text, 'limits': self.text + str(i),
                'check_ids': ['s:C1'], 'target_anchors': [{'page': 1, 'quote': 'First line.'}],
                'finding_ids': [], 'suggestion_ids': [],
                'expression_contribution': {'role': 'no_change', 'feature_ids': [], 'supporting_concern_ids': []}})
        response = {'writing_transfers': rows, 'checks': [{'id': 's:C1', 'finding_ids': []}], 'findings': [],
            'source_use_dispositions': [dict(**u, status='checked', transfer_ids=['s:W1'], reason=self.text + str(i))
                                        for i, u in enumerate(self.context['source_uses'])]}
        wire = output.encode(response, self.context)
        self.assertEqual(output.expand(wire, self.context), response)
        self.assertLess(len(output.dump(wire)), len(output.dump(response)) * .65)
        batching.validate_uses(output.expand(wire, self.context), self.context)
        broken = copy.deepcopy(response); broken['source_use_dispositions'].pop()
        with self.assertRaisesRegex(ValueError, 'coverage'):
            batching.validate_uses(output.expand(output.encode(broken, self.context), self.context), self.context)

    def test_projection_preserves_every_character_and_page(self):
        projected = batching.project(self.context)
        self.assertNotEqual(projected['manuscript'], self.context['manuscript'])
        self.assertEqual(batching.inflate(projected), self.context)
        wire = self.envelope({'anchor': {'$anchor': ['P1.1', 'P1.2']}})
        self.assertEqual(output.expand(wire, self.context)['anchor'],
                         {'page': 1, 'quote': self.context['manuscript'][0]['text']})
        for bad in [['P1.1', 'P2.1'], ['P1.2', 'P1.1'], 'P1.99']:
            with self.assertRaises(ValueError):
                output.expand(self.envelope({'a': {'$anchor': bad}}), self.context)

    def test_exact_input_reference_and_invalid_paths(self):
        self.context['expression_sources']['records'][0]['text'] = self.text
        ref = ['expression_sources', 'records', 0, 'text']
        expanded = output.expand(self.envelope({'t': {'$input': ref}}), self.context)
        self.assertEqual(expanded['t'], self.text)
        for path in [['external', 'answer'], ['expression_sources', 'records', -1, 'text'],
                     ['expression_sources', 'records', True, 'text']]:
            with self.assertRaises(ValueError):
                output.expand(self.envelope({'t': {'$input': path}}), self.context)

    def test_no_generated_judgments_checks_or_positive_links(self):
        raw = {'writing_transfers': [{'source_id': 'E1', 'decision': 'keep'}],
               'source_use_dispositions': [{'use_id': 1}]}
        expanded = output.expand(self.envelope(raw), self.context)
        self.assertNotIn('status', expanded['source_use_dispositions'][0])
        self.assertNotIn('check_ids', expanded['writing_transfers'][0])
        self.assertNotIn('limits', expanded['writing_transfers'][0])
        with self.assertRaises(ValueError): batching.validate_uses(expanded, self.context)
        raw['writing_transfers'][0]['decision'] = 'required_repair'
        self.assertNotIn('finding_ids', output.expand(self.envelope(raw), self.context)['writing_transfers'][0])

    def test_inverse_links_only_use_explicit_forward_links(self):
        raw = {'checks': [{'id': 'K1'}, {'id': 'K2', 'finding_ids': ['wrong']}],
               'findings': [{'id': 'F1', 'check_ids': ['K1']}]}
        expanded = output.expand(self.envelope(raw), self.context)
        self.assertEqual(expanded['checks'][0]['finding_ids'], ['F1'])
        self.assertEqual(expanded['checks'][1]['finding_ids'], ['wrong'])

    def test_dangling_cycles_tables_and_conflicts_fail(self):
        bad = [self.envelope({'a': {'$same': 'missing'}}),
               self.envelope({'a': {'$same': 'A'}}, {'A': {'$same': 'B'}, 'B': {'$same': 'A'}}),
               self.envelope({'x': {'$rows': {'columns': ['a'], 'values': [[1, 2]]}}}),
               self.envelope({'x': {'$rows': {'columns': ['a', 'a'], 'values': [[1, 2]]}}}),
               self.envelope({'source_use_dispositions': [{'use_id': 1, 'target_id': 'wrong'}]})]
        for item in bad:
            with self.assertRaises(ValueError): output.expand(item, self.context)

    def test_legacy_is_unchanged_and_new_format_cannot_enter_old_run(self):
        raw = {'writing_transfers': [{'id': 'old', 'decision': 'unknown'}]}
        self.assertEqual(output.expand(raw, {}), raw)
        with self.assertRaisesRegex(ValueError, 'Unpinned'):
            output.expand(self.envelope(raw), {})

    def test_preflight_collects_missing_sources_checks_and_uses_without_filling(self):
        context={**self.context,'primary_card_ids':['C1']}
        raw={'card_dispositions':[], 'writing_transfers':[{'source_kind':'mentor_expression',
            'source_id':'E1','decision':'keep'}], 'checks':[],'findings':[],'source_use_dispositions':[]}
        original=copy.deepcopy(raw)
        inventory=output.preflight(raw,context)
        paths={i['path'] for i in inventory['issues']}
        self.assertTrue({'card_dispositions','writing_transfers','source_use_dispositions'} <= paths)
        self.assertIn('writing_transfers[0].check_ids',paths)
        self.assertIn('writing_transfers[0].limits',paths)
        self.assertEqual(raw,original)


if __name__ == '__main__':
    unittest.main()
