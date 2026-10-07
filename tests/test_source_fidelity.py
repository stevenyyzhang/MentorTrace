"""Local source-fidelity contract tests; no model calls or recall claim."""
import unittest
import test_pipeline as fixture
from test_pipeline import m, answer


class SourceFidelity(unittest.TestCase):
    def surface_context(self):
        pages = [{'page': 1, 'text': 'Range resolu- tion is limited.'}]
        return {'manuscript': pages, 'text_units': m.surface_units(pages),
                'source_fidelity': 1, 'source_candidates': m.fidelity.surface_candidates(pages),
                'source_page_images': [{'page': 1, 'sha256': 'image-hash'}]}

    def surface_answer(self, status='valid_source'):
        ctx = self.surface_context()
        result = answer('language', ctx)
        result['source_candidate_dispositions'] = [{
            'candidate_id': ctx['source_candidates'][0]['id'], 'status': status,
            'image_anchor': {'page': 1, 'kind': 'image', 'description': 'Observed split-word placement.'},
            'image_sha256': 'image-hash', 'reason': 'Synthetic visual inspection record.',
            'finding_ids': [], 'uncertain_ids': []}]
        return ctx, result

    def formula_case(self):
        ref = {'page': 1, 'kind': 'image', 'description': 'Equation (1), magnitude-weighted kernel.'}
        ctx = {'manuscript': [{'page': 1, 'text': 'J=sum f exp(-d^2).'}],
               'input_findings': [{'id': 'merge:F1', 'anchor': ref,
                                   'gap': 'The map is complex because the coefficient has no magnitude.'}],
               'source_fidelity': 1, 'source_page_images': [{'page': 1, 'sha256': 'image-hash'}]}
        result = {'findings': [], 'dispositions': [{
            'input_id': 'merge:F1', 'status': 'withdrawn', 'output_ids': [],
            'reason': 'The original page takes coefficient magnitude.', 'evidence': [ref]}],
            'source_fidelity_checks': [{
                'input_id': 'merge:F1', 'status': 'contradicted', 'anchor': ref,
                'image_sha256': 'image-hash', 'decisive_expression': r'J=\sum |f|\exp(-d^2)',
                'decisive_symbols': [{'symbol': '|f|', 'role': 'Nonnegative magnitude weight.'}],
                'extraction_difference': 'The text layer omitted the magnitude delimiters.',
                'reason': 'Magnitude weighting contradicts the complex-map premise.'}], 'limits': []}
        return ctx, result

    def test_candidates_preserve_inline_split_and_leave_normal_line_wrap(self):
        text = 'Range resolu- tion. Normal resolu-\ntion. A state-of-the-art method. x- y.'
        result = m.fidelity.surface_candidates([{'page': 2, 'text': text}])
        self.assertEqual([r['quote'] for r in result], ['resolu- tion'])
        self.assertEqual(text[result[0]['start']:result[0]['end']], result[0]['quote'])
        self.assertEqual(result, m.fidelity.surface_candidates([{'page': 2, 'text': text}]))

    def test_page_checked_does_not_dispose_of_candidate(self):
        ctx = self.surface_context()
        with self.assertRaisesRegex(ValueError, 'candidate coverage'):
            m.validate('language', answer('language', ctx), ctx)

    def test_candidates_need_correct_image_hash_and_page(self):
        ctx, result = self.surface_answer()
        m.validate('language', result, ctx)
        result['source_candidate_dispositions'][0]['image_sha256'] = 'stale'
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            m.validate('language', result, ctx)

    def test_definite_candidate_becomes_anchored_surface_finding(self):
        ctx, result = self.surface_answer('definite_error')
        with self.assertRaisesRegex(ValueError, 'must become a Language finding'):
            m.validate('language', result, ctx)
        result['findings'] = [{'id': 'language:F1', 'finding_type': 'surface', 'category': 'spelling',
                               'unit_ids': ['p1:u1'], 'anchor': {'page': 1, 'quote': 'resolu- tion'},
                               'relation': 'Spelling must form one word.', 'gap': 'Unintended inline split.',
                               'impact': 'Visible typo.', 'closure_goal': 'Remove hyphen and space.',
                               'suggested_text': 'resolution'}]
        result['coverage'][0]['finding_ids'] = ['language:F1']
        result['source_candidate_dispositions'][0]['finding_ids'] = ['language:F1']
        m.validate('language', result, ctx)

    def test_unresolved_candidate_needs_uncertainty_record(self):
        ctx, result = self.surface_answer('unresolved')
        with self.assertRaisesRegex(ValueError, 'uncertainty record'):
            m.validate('language', result, ctx)
        result['uncertain_items'] = [{'id': 'language:U1', 'anchor': {'page': 1, 'kind': 'image',
                                      'description': 'Unclear intended compound.'},
                                      'check_request': 'Confirm the intended term.'}]
        result['source_candidate_dispositions'][0]['uncertain_ids'] = ['language:U1']
        m.validate('language', result, ctx)

    def test_page_magnitude_can_dispose_of_corrupted_text_allegation(self):
        ctx, result = self.formula_case()
        m.validate('verify', result, ctx)
        result['source_fidelity_checks'] = []
        with self.assertRaisesRegex(ValueError, 'fidelity coverage'):
            m.validate('verify', result, ctx)

    def test_contradicted_formula_premise_cannot_be_retained(self):
        ctx, result = self.formula_case()
        final = {'id': 'verify:F1', 'anchor': ctx['input_findings'][0]['anchor'],
                 'relation': 'Voting must be real.', 'gap': 'Voting is complex.',
                 'impact': 'Ordering undefined.', 'closure_goal': 'Change weighting.'}
        result['findings'] = [final]
        result['dispositions'][0].update(status='retained', output_ids=['verify:F1'])
        with self.assertRaisesRegex(ValueError, 'Contradicted formula premise was retained'):
            m.validate('verify', result, ctx)

    def test_formula_inspection_cannot_omit_expression_or_symbols(self):
        ctx, result = self.formula_case()
        result['source_fidelity_checks'][0]['decisive_expression'] = ''
        with self.assertRaisesRegex(ValueError, 'original expression'):
            m.validate('verify', result, ctx)
        result['source_fidelity_checks'][0]['decisive_expression'] = '|f|'
        result['source_fidelity_checks'][0]['decisive_symbols'] = []
        with self.assertRaisesRegex(ValueError, 'symbol inspection'):
            m.validate('verify', result, ctx)

    def test_unreadable_formula_stays_unresolved_without_confirmed_output(self):
        ctx, result = self.formula_case()
        result['source_fidelity_checks'][0]['status'] = 'unreadable'
        result['dispositions'][0].update(status='unresolved', evidence=[])
        m.validate('verify', result, ctx)
        result['dispositions'][0]['status'] = 'withdrawn'
        result['dispositions'][0]['evidence'] = [ctx['input_findings'][0]['anchor']]
        with self.assertRaisesRegex(ValueError, 'Unreadable formula'):
            m.validate('verify', result, ctx)

    def test_new_verification_findings_also_need_source_record(self):
        ctx, result = self.formula_case()
        result['findings'] = [{'id': 'verify:F2', 'anchor': ctx['input_findings'][0]['anchor'],
                              'relation': 'Threshold reporting.', 'gap': 'Threshold unspecified.',
                              'impact': 'Cannot reproduce.', 'closure_goal': 'Supply threshold.',
                              'new_in_stage': True}]
        with self.assertRaisesRegex(ValueError, 'fidelity coverage'):
            m.validate('verify', result, ctx)
        result['source_fidelity_checks'].append({'input_id': 'verify:F2',
                                               'status': 'not_formula_dependent',
                                               'reason': 'Reporting requirement, not a claim about formula glyphs.'})
        m.validate('verify', result, ctx)


class SourceProtocol(unittest.TestCase):
    setUp = fixture.Pipeline.setUp
    tearDown = fixture.Pipeline.tearDown

    def test_new_protocol_freezes_inventory_and_loads_stage_specific_contract(self):
        self.assertEqual(m.read(self.run/'inputs/protocol.json')['source_fidelity'], 1)
        m.verify_frozen(self.run/'inputs')
        ctx = m.context_for(self.run, 'language')
        self.assertEqual(ctx['source_candidates'], [])
        self.assertNotIn('objects', ctx)
        self.assertNotIn('cards', ctx)
        req = m.prepare_stage_request(self.run, 'language')
        self.assertIn('source-fidelity.md', req['module_hashes'])
        self.assertIn('source_candidate_dispositions', req['prompt'])

    def test_legacy_protocol_does_not_acquire_new_schema(self):
        protocol = m.read(self.run/'inputs/protocol.json')
        protocol.pop('source_fidelity')
        m.save(self.run/'inputs/protocol.json', protocol)
        m.freeze(self.run/'inputs')
        ctx = m.context_for(self.run, 'language')
        self.assertNotIn('source_fidelity', ctx)
        result = answer('language', ctx)
        self.assertNotIn('source_candidate_dispositions', result)
        m.validate('language', result, ctx)
        req = m.prepare_stage_request(self.run, 'language')
        self.assertNotIn('source-fidelity.md', req['module_hashes'])

    def test_generic_protocol_freezes_inventory_without_advisor_inputs(self):
        run = self.root/'generic'
        m.create_generic_run(self.root/'paper', run, 1)
        m.verify_frozen(run/'inputs')
        self.assertEqual(m.read(run/'inputs/protocol.json')['source_fidelity'], 1)
        ctx = m.context_for(run, 'language')
        self.assertEqual(ctx['source_candidates'], [])
        self.assertNotIn('cards', ctx)
        req = m.prepare_stage_request(run, 'language')
        self.assertIn('source-fidelity.md', req['module_hashes'])
        self.assertIn('source_candidate_dispositions', req['prompt'])

    def test_postfreeze_proposal_receives_source_transcriptions_and_contract(self):
        import prepare_revision_proposals
        while m.next_request(self.run):
            stage = m.next_request(self.run)['stage']
            m.accept_response(self.run, answer(stage, m.context_for(self.run, stage)))
        out = self.root/'proposals'
        prepare_revision_proposals.prepare(self.run, out)
        self.assertEqual(m.read(out/'inputs/verified.json')['source_fidelity_checks'],
                         m.read(self.run/'final.json')['source_fidelity_checks'])
        request = m.read(out/'request.json')
        self.assertIn('source-fidelity.md', request['prompt'])
        self.assertIn('reuse the checked expressions', request['prompt'])
        supplied = __import__('json').loads(request['prompt'].split('\nVERIFIED REVIEW\n', 1)[1].split('\nMANUSCRIPT\n', 1)[0])
        verified = m.read(out/'inputs/verified.json')
        links = {row['input_id']: row['output_ids'] for row in verified['dispositions']}
        self.assertNotIn('dispositions', supplied)
        for row in supplied['source_fidelity_checks']:
            self.assertEqual(row['finding_ids'], links[row['input_id']])
        m.verify_frozen(out/'inputs')


if __name__ == '__main__':
    unittest.main()
