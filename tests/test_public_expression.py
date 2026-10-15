"""Minimized-source integration/genre checks; synthetic data, no model calls."""
import copy
import unittest

import public_expression as public
import expression_runtime as expression
import expression_realization as realization
import writing_transfer as writing
import test_pipeline as fixture
from test_pipeline import m, A


def card(number=1, kind='verbatim_mentor_prose', text='Define the observation as the receiver input.', body=True, feature_kind='syntax'):
    rid = 'EX' + str(number).zfill(5)
    eid = rid + ':E1'
    record = {'id': rid, 'title': 'Observation definition', 'scope': 'paragraph',
              'section_task': 'receiver observation detector input',
              'before_account': 'A named input needs a clear role.',
              'observed_change': 'Define the observation before detector use.',
              'changed_relationship': 'observation before detector input',
              'after_account': 'Proposed change only; adoption is not established.',
              'operations': ['State the observation role.'],
              'transfer_conditions': ['The target establishes the input role.'],
              'do_not_transfer': ['Do not invent a receiver observation.'],
              'facts_and_qualifications': ['Preserve target facts and sequence.'],
              'retrieval_terms': ['receiver', 'observation', 'detector'],
              'examples': [{'id': eid, 'kind': kind, 'text': text,
                            'function': 'Synthetic source-role fixture.',
                            'body_form_allowed': body, 'pair_id': None}],
              'language_features': [{'id': rid + ':L1', 'kind': feature_kind,
                                     'evidence_example_ids': [eid],
                                     'function': 'State the observation role.',
                                     'frame': 'Define [quantity] as [role].',
                                     'operation': 'Define the observation role before use.',
                                     'conditions': ['Target quantity and role established.'],
                                     'do_not_transfer': ['Do not copy source facts.'],
                                     'evidence_status': 'Synthetic test fixture only.'}],
              'limits': ['Synthetic fixture; not real mentor evidence.'],
              'publication_permission': 'unconfirmed',
              'content_status': 'minimized_local_candidate_permission_unconfirmed',
              'preference_status': 'local_example_not_verified_general_preference',
              'concern_ids': []}
    return record


class PublicExpression(unittest.TestCase):
    setUp = fixture.Pipeline.setUp
    tearDown = fixture.Pipeline.tearDown

    def library(self, records=None):
        self.records = records or [card()]
        self.lib = self.root / 'minimized-expression'
        m.save(self.lib / 'records.json', self.records)
        m.save(self.lib / 'index.json', [{k: r[k] for k in ['id', 'scope', 'section_task', 'retrieval_terms', 'concern_ids']} for r in self.records])
        m.save(self.lib / 'manifest.json', {'role': 'public_expression_candidate', 'schema_version': 1,
                                          'count': len(self.records), 'private_raw_pages': False,
                                          'private_original_mapping': False, 'private_images': False,
                                          'publication_permission': 'unconfirmed',
                                          'status': 'local_preparation_complete_permission_unconfirmed',
                                          'expression_realization': 1})
        m.freeze(self.lib)
        return self.lib

    def test_view_binds_public_examples_without_fake_private_context(self):
        self.library()
        before = copy.deepcopy(self.records)
        public.check_library(self.lib)
        view = expression.view(self.lib, ['EX00001'])
        self.assertEqual(view['episodes'], [])
        record = view['records'][0]
        self.assertNotIn('mentor_texts', record)
        self.assertNotIn('episode_ids', record)
        feature = record['language_features'][0]
        self.assertEqual(feature['source_ref'], 'EX00001:E1')
        realization.check_feature(feature, record)
        self.assertEqual(m.read(self.lib / 'records.json'), before)

    def test_instruction_and_generated_sentence_cannot_supply_body_syntax(self):
        comment = card(2, 'verbatim_editorial_instruction', 'Explain the observation before detector use.', False)
        public.check_records([comment])
        projected = public.project(comment)
        self.assertEqual(projected['language_features'], [])
        comment['language_features'][0]['kind'] = 'paragraph'
        projected = public.project(comment)
        feature = projected['language_features'][0]
        self.assertEqual(feature['evidence_kind'], 'editorial_instruction')
        self.assertFalse(feature['body_evidence']['body_form_allowed'])
        feature['body_evidence']['body_form_allowed'] = True
        with self.assertRaisesRegex(ValueError, 'comment cannot'):realization.check_feature(feature, projected)
        generated = card(3, 'synthetic_example', body=False)
        self.assertEqual(public.project(generated)['language_features'], [])

    def test_deletion_remains_author_evidence(self):
        record = public.project(card(3, 'verbatim_author_deletion', 'in order to', False))
        feature = record['language_features'][0]
        self.assertEqual(feature['evidence_kind'], 'deletion')
        self.assertFalse(feature['body_evidence']['body_form_allowed'])
        realization.check_feature(feature, record)
        feature['evidence_kind'] = 'mentor_fragment'
        with self.assertRaisesRegex(ValueError, 'changed evidence genre'):realization.check_feature(feature, record)

    def test_actual_title_fragment_supports_operation_without_becoming_body_prose(self):
        record = card(13, 'verbatim_mentor_fragment', 'Exploiting', False)
        record['section_task'] = 'Open a title with the contribution action.'
        record['language_features'][0]['frame'] = 'Exploiting [resource]'
        public.check_records([record])
        projected = public.project(record)
        feature = projected['language_features'][0]
        self.assertEqual(feature['evidence_kind'], 'mentor_fragment')
        self.assertEqual(feature['source_quote'], 'Exploiting')
        self.assertEqual(feature['frame'], '')
        self.assertFalse(feature['body_evidence']['body_form_allowed'])
        realization.check_feature(feature, projected)
        feature['body_evidence']['body_form_allowed'] = True
        with self.assertRaisesRegex(ValueError, 'comment cannot'):
            realization.check_feature(feature, projected)

    def test_title_fragment_is_usable_as_action_but_rejected_as_body_language(self):
        record = card(13, 'verbatim_mentor_fragment', 'Exploiting', False)
        response, evidence = self.realization_fixture(record)
        with self.assertRaisesRegex(ValueError, 'Comment cannot'):
            realization.validate_draft(response, evidence)
        action = 'Open the title with the contribution action and make the resource its object.'
        response['report_markdown'] = action
        row = response['language_realizations'][0]
        row.update(scope='action_only', passages=[])
        row['feature_decisions'][0].update(realization_type='editorial_operation', target_quote=action)
        self.assertEqual(realization.validate_draft(response, evidence)['used_features'], 1)

    def test_excerpt_origin_prevents_comment_or_analysis_as_mentor_quote(self):
        record = public.project(card(2, 'verbatim_editorial_instruction', body=False, feature_kind='paragraph'))
        use = {'source_excerpt': record['examples'][0]['text'],
               'expression_excerpt_basis': {'kind': 'editorial_instruction', 'example_id': 'EX00002:E1'}}
        public.validate_excerpt(record, use)
        use['expression_excerpt_basis']['kind'] = 'mentor_wording'
        with self.assertRaisesRegex(ValueError, 'changed evidence genre'):public.validate_excerpt(record, use)
        use = {'source_excerpt': record['observed_change'],
               'expression_excerpt_basis': {'kind': 'analytical_account', 'field': 'observed_change'}}
        public.validate_excerpt(record, use)
        use.pop('expression_excerpt_basis')
        with self.assertRaisesRegex(ValueError, 'evidence origin'):public.validate_excerpt(record, use)

    def test_operation_only_record_has_usable_analytical_transfer(self):
        record = card(4);record['examples'] = [];record['language_features'] = []
        public.check_records([record]);record = public.project(record)
        use = {'source_excerpt': 'Define the observation before detector use.',
               'expression_excerpt_basis': {'kind': 'analytical_account', 'field': 'observed_change'}}
        public.validate_excerpt(record, use)
        self.assertIn(use['source_excerpt'], writing.source_texts('mentor_expression', record, use['expression_excerpt_basis']))

    def test_comment_free_structure_binds_an_analytical_operation(self):
        record = card(10, feature_kind='paragraph')
        record['examples'] = []
        feature = record['language_features'][0]
        feature['evidence_example_ids'] = []
        feature['evidence_account'] = {'field': 'operations', 'quote': record['operations'][0]}
        public.check_records([record])
        projected = public.project(record)
        feature = projected['language_features'][0]
        self.assertEqual(feature['evidence_kind'], 'analytical_operation')
        self.assertFalse(feature['body_evidence']['body_form_allowed'])
        self.assertNotIn('mentor_texts', projected)
        self.assertEqual(feature['source_quote'], record['operations'][0])
        realization.check_feature(feature, projected)
        public.validate_excerpt(projected, {'source_excerpt': feature['source_quote'],
                                            'expression_excerpt_basis': {'kind': 'analytical_account', 'field': 'operations'}})
        feature['body_evidence']['body_form_allowed'] = True
        with self.assertRaisesRegex(ValueError, 'cannot supply manuscript'):realization.check_feature(feature, projected)

    def test_analytical_operation_rejects_changed_binding_and_body_syntax(self):
        record = card(11, feature_kind='paragraph')
        record['examples'] = []
        feature = record['language_features'][0]
        feature['evidence_example_ids'] = []
        feature['evidence_account'] = {'field': 'operations', 'quote': record['operations'][0]}
        projected = public.project(record)
        projected['operations'] = ['A different operation.']
        with self.assertRaisesRegex(ValueError, 'changed account binding'):
            realization.check_feature(projected['language_features'][0], projected)
        feature['kind'] = 'syntax'
        with self.assertRaisesRegex(ValueError, 'cannot establish manuscript wording'):public.check_records([record])
        feature['kind'] = 'paragraph'
        feature['evidence_account']['source_path'] = 'private.pdf'
        with self.assertRaisesRegex(ValueError, 'account origin'):public.check_records([record])

    def test_v2_package_admits_operations_and_rejects_literal_comments(self):
        record = card(12, feature_kind='paragraph')
        record['examples'] = []
        feature = record['language_features'][0]
        feature['evidence_example_ids'] = []
        feature['evidence_account'] = {'field': 'operations', 'quote': record['operations'][0]}
        self.library([record])
        manifest = m.read(self.lib / 'manifest.json')
        manifest.update(schema_version=2, editorial_comment_policy='analytical_operations_only')
        m.save(self.lib / 'manifest.json', manifest);m.freeze(self.lib)
        public.check_library(self.lib)
        record['examples'] = card(12, 'verbatim_editorial_instruction', body=False)['examples']
        m.save(self.lib / 'records.json', [record]);m.freeze(self.lib)
        with self.assertRaisesRegex(ValueError, 'Literal editorial comment'):public.check_library(self.lib)

    def test_structured_operation_preserves_its_own_condition(self):
        record = card(4)
        record['operations'] = [{'action': 'Omit the redundant display.', 'condition': 'Its claim remains supported.'}]
        public.check_records([record]);projected = public.project(record)
        self.assertEqual(projected['operations'], record['operations'])
        public.validate_excerpt(projected, {'source_excerpt': 'Its claim remains supported.',
                                            'expression_excerpt_basis': {'kind': 'analytical_account', 'field': 'operations'}})
        record['operations'][0]['source_path'] = 'private.pdf'
        with self.assertRaisesRegex(ValueError, 'operations'):public.check_records([record])

    def test_structured_operation_keeps_target_and_multiple_conditions(self):
        record = card(4)
        operation = {'action': 'Introduce the measurement before its first use.',
                     'target': 'The comparison lead-in.',
                     'conditions': ['The target defines this measurement.', 'The comparison uses the same measurement.']}
        record['operations'] = [operation]
        public.check_records([record]);projected = public.project(record)
        self.assertEqual(projected['operations'][0], operation)
        for quote in [operation['action'], operation['target']] + operation['conditions']:
            public.validate_excerpt(projected, {'source_excerpt': quote,
                                                'expression_excerpt_basis': {'kind': 'analytical_account', 'field': 'operations'}})
        record['operations'][0]['conditions'] = 'Wrong list type'
        with self.assertRaisesRegex(ValueError, 'operations'):public.check_records([record])

    def test_public_package_rejects_private_extras_and_changed_hash(self):
        self.library();public.check_library(self.lib)
        extra = self.lib / 'PRIVATE_MAP.json';extra.write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'package files'):public.check_library(self.lib)
        extra.unlink()
        m.save(self.lib / 'records.json', [])
        with self.assertRaisesRegex(ValueError, 'frozen file changed'):public.check_library(self.lib)

    def test_public_library_reaches_independent_advisor_context(self):
        self.library()
        run = self.root / 'public-expression-run'
        m.create_run(self.root / 'paper', self.root / 'knowledge', run, goodpaper_cases=False, expression_library=self.lib)
        request = m.next_request(run)
        self.assertEqual(request['stage'], 'advisor_tasks')
        task = {'id': 'AT1', 'anchors': [A], 'section_task': 'receiver observation detector input',
                'scope': 'paragraph', 'rhetorical_relation': 'observation before detector input',
                'retrieval_terms': ['receiver', 'observation', 'detector']}
        m.accept_response(run, {'tasks': [task], 'page_coverage': [{'page': 1, 'status': 'mapped', 'reason': 'Synthetic task.'}], 'limits': []}, {'kind': 'synthetic_fixture', 'model_called': False})
        context = m.context_for(run, 'supplement_1')
        self.assertNotIn('objects', context)
        self.assertEqual(context['expression_sources']['episodes'], [])
        self.assertEqual(context['expression_sources']['records'][0]['id'], 'EX00001')
        self.assertIn(public.SCHEMA, expression.transfer_schema(context))
        self.assertIn(public.SCHEMA, writing.review_schema(context))

    def test_post_freeze_route_uses_body_or_deletion_not_instruction_form(self):
        self.library([card(), card(2, 'verbatim_editorial_instruction', body=False, feature_kind='paragraph'), card(3, 'synthetic_example', body=False)])
        links = realization.route(self.lib, [{'id': 'G1', 'title': 'State the observation role.', 'reader_task': 'Find the receiver observation.'}])
        self.assertEqual(links[0]['expression_ids'], ['EX00001'])

    def realization_fixture(self, record, realization_type='language_form'):
        record = public.project(record)
        source = record['language_features'][0]
        text = 'Define the signal as the detector input.'
        decision = {'expression_id': record['id'], 'feature_id': source['id'],
                    'decision': 'adapt', 'realization_type': realization_type,
                    'evidence_kind': source['evidence_kind'], 'source_ref': source['source_ref'],
                    'source_quote': source['source_quote'], 'requested_feature': 'Definition construction.',
                    'target_quote': text, 'realization_explanation': 'Synthetic actual-text binding.',
                    'preserved_meaning': 'Target signal role retained.', 'adaptations': 'Target noun substituted.',
                    'reason': 'Synthetic compatible task.'}
        evidence = {'expression_realization': 1, 'expression_sources': {'records': [record], 'episodes': []},
                    'raw_to_final': [], 'writing_transfers': [],
                    'draft_expression_links': [{'verified_id': 'G1', 'expression_ids': [record['id']]}]}
        response = {'report_markdown': text, 'revision_actions': [{'draft_label': 'D1', 'verified_ids': ['G1']}],
                    'language_realizations': [{'draft_label': 'D1', 'verified_ids': ['G1'], 'scope': 'prose',
                                              'passages': [{'id': 'P1', 'text': text}], 'source_disposition': 'used',
                                              'reason': 'Synthetic supported realization.', 'feature_decisions': [decision]}]}
        return response, evidence

    def test_public_realization_binds_actual_replacement_and_exact_public_quote(self):
        response, evidence = self.realization_fixture(card())
        self.assertEqual(realization.validate_draft(response, evidence)['used_features'], 1)
        response['language_realizations'][0]['feature_decisions'][0]['source_quote'] = 'Invented source sentence.'
        with self.assertRaisesRegex(ValueError, 'changed source feature evidence'):realization.validate_draft(response, evidence)

    def test_public_instruction_cannot_be_realized_as_manuscript_language(self):
        response, evidence = self.realization_fixture(card(2, 'verbatim_editorial_instruction', body=False, feature_kind='paragraph'))
        with self.assertRaisesRegex(ValueError, 'Comment cannot'):realization.validate_draft(response, evidence)


if __name__ == '__main__':
    unittest.main()
