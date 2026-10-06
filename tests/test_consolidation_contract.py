"""Post-discovery contract tests; no scientific sufficiency or model-quality claim."""
import copy
import unittest
import test_pipeline as pipeline
A, answer, m = pipeline.A, pipeline.answer, pipeline.m


class ConsolidationContract(unittest.TestCase):
    def context_and_response(self, modern=True):
        source = {'id': 'reader:F1', 'relation': 'Input access and calibration',
                  'gap': 'Input origin and decision calibration are unstated.',
                  'closure_goal': 'State input origin and calibrate the decision.'}
        context = {'manuscript': [{'page': 1, 'text': A['quote']}],
                   'objects': [], 'input_findings': [source]}
        if modern:
            context['consolidation_review'] = 1
        response = {'findings': [{'id': 'merge:F1', 'anchor': A, 'relation': 'Input access',
                                 'gap': 'Input origin is unstated.', 'impact': 'Execution unknown.',
                                 'closure_goal': 'State input origin.'}],
                    'dispositions': [{'input_id': source['id'], 'status': 'narrowed',
                                      'output_ids': ['merge:F1'], 'reason': 'Synthetic evidence-backed exclusion.',
                                      'evidence': [A], 'excluded_requirements': [
                                          {'source_quote': 'calibrate the decision', 'reason': 'Synthetic calibration scope already answered.'}]}]}
        return context, response

    def test_modern_narrow_requires_evidence_and_real_excluded_clause(self):
        context, response = self.context_and_response()
        m.validate('merge', response, context)
        for field in ['evidence', 'excluded_requirements']:
            with self.subTest(field=field):
                changed = copy.deepcopy(response)
                changed['dispositions'][0].pop(field)
                with self.assertRaises(ValueError):
                    m.validate('merge', changed, context)
        changed = copy.deepcopy(response)
        changed['dispositions'][0]['excluded_requirements'][0]['source_quote'] = 'invented requirement'
        with self.assertRaisesRegex(ValueError, 'exact source requirement'):
            m.validate('merge', changed, context)
        changed['dispositions'][0]['excluded_requirements'][0]['source_quote'] = ''
        with self.assertRaises(ValueError):
            m.validate('merge', changed, context)

    def test_legacy_narrow_protocol_remains_readable(self):
        context, response = self.context_and_response(modern=False)
        response['dispositions'][0].pop('excluded_requirements')
        response['dispositions'][0].pop('evidence')
        m.validate('merge', response, context)

    def test_unresolved_cannot_claim_retained_output_in_new_protocol(self):
        context, response = self.context_and_response()
        response['dispositions'][0]['status'] = 'unresolved'
        with self.assertRaisesRegex(ValueError, 'Unresolved disposition'):
            m.validate('merge', response, context)
        response['findings'] = []
        response['dispositions'][0]['output_ids'] = []
        m.validate('merge', response, context)

    def test_initial_requests_unchanged_by_consolidation_flag(self):
        fixture = pipeline.Pipeline()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        m.accept_response(fixture.run, answer('objects', m.context_for(fixture.run, 'objects')),
                          {'kind': 'synthetic_fixture', 'model_called': False})
        protocol_path = fixture.run/'inputs/protocol.json'
        modern = m.read(protocol_path)
        stages = ['objects', 'reader', 'technical', 'supplement_1', 'language']
        before = {stage: m.prepare_stage_request(fixture.run, stage) for stage in stages}
        legacy = copy.deepcopy(modern)
        legacy.pop('consolidation_review')
        m.save(protocol_path, legacy)
        m.freeze(fixture.run/'inputs')
        after = {stage: m.prepare_stage_request(fixture.run, stage) for stage in stages}
        self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
