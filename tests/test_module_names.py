"""Reviewer display names must not change serialized evidence or manuscript text."""
import json
import unittest
from pathlib import Path

import test_pipeline as fixture

m = fixture.m


class ModuleNames(unittest.TestCase):
    setUp = fixture.Pipeline.setUp
    tearDown = fixture.Pipeline.tearDown

    def test_new_protocol_and_aliases_preserve_ids(self):
        protocol = m.read(self.run/'inputs/protocol.json')
        self.assertEqual(protocol['module_naming_version'], 1)
        self.assertEqual(protocol['module_names'], m.naming.NAMES)
        config = m.read(Path(__file__).resolve().parents[1]/'config/project.json')
        self.assertEqual(config['module_names'], m.naming.NAMES)
        fixture.Pipeline.advance(self)
        for alias, stage, display, reference in [
            ('expert', 'technical', 'Expert', 'expert-checks.md'),
            ('editor', 'language', 'Editor', 'editor-surface.md'),
        ]:
            request = m.prepare_stage_request(self.run, alias)
            self.assertEqual(request, m.prepare_stage_request(self.run, stage))
            self.assertEqual(request['stage'], stage)
            self.assertEqual(request['module_name'], display)
            self.assertIn('REVIEW MODULE: '+display, request['prompt'])
            self.assertIn(reference, request['module_hashes'])
            self.assertEqual(m.context_for(self.run, alias), m.context_for(self.run, stage))
            result = fixture.answer(stage, m.context_for(self.run, stage))
            m.validate(alias, result, m.context_for(self.run, alias))

    def test_input_payload_is_not_renamed(self):
        paper = self.run/'inputs/paper/body.json'
        body = m.read(paper)
        body[0]['text'] = 'Technical and Language are literal manuscript words.'
        m.save(paper, body)
        m.freeze(self.run/'inputs/paper')
        m.freeze(self.run/'inputs')
        request = m.prepare_stage_request(self.run, 'editor')
        payload = json.loads(request['prompt'].split('\nINPUT\n', 1)[1])
        self.assertEqual(payload, m.context_for(self.run, 'editor'))
        self.assertIn(body[0]['text'], request['prompt'])
        self.assertIn('anchored Editor findings', request['prompt'])
        self.assertNotIn('anchored Language findings', request['prompt'])

    def test_generic_run_resolves_current_references_through_completion(self):
        run = self.root/'generic'
        m.create_generic_run(self.root/'paper', run, 1)
        seen = set()
        while request := m.next_request(run):
            stage = request['stage']
            seen.add(request['module_name'])
            m.accept_response(run, fixture.answer(stage, m.context_for(run, stage)))
        self.assertTrue({'Reader', 'Expert', 'Advisor', 'Editor'} <= seen)
        self.assertEqual(m.read(run/'state.json')['status'], 'complete')

    def test_expert_case_reference_loads_with_frozen_route(self):
        self.run = self.root/'with_cases'
        m.create_run(self.root/'paper', self.root/'knowledge', self.run)
        fixture.Pipeline.advance(self)
        routing = m.case_route_input(self.run)
        route = {'source_plan_sha256': routing['source_plan_sha256'], 'reader': [], 'technical': [],
                 'skipped_entries': [{'lane': lane, 'entry_id': entry['id'],
                                      'reason': 'No matching task in the synthetic fixture.'}
                                     for lane in ['reader', 'technical']
                                     for entry in routing[lane+'_index']['entries']]}
        m.freeze_case_route(self.run, route)
        request = m.prepare_stage_request(self.run, 'expert')
        self.assertIn('goodpaper-expert.md', request['module_hashes'])
        self.assertNotIn('goodpaper-technical.md', request['module_hashes'])

    def test_instruction_adapter_preserves_subject_terms_and_legacy_filenames(self):
        old = 'Technical validity remains the separate Technical lane remit. Language findings. Language and presentation comments.'
        self.assertEqual(m.naming.current_instructions(old),
                         'Technical validity remains the separate Expert lane remit. Editor findings. Language and presentation comments.')
        for legacy, current in m.naming.REFERENCES.items():
            self.assertEqual(m.naming.reference_name(current, False), legacy)
            self.assertEqual(m.naming.reference_name(legacy, True), current)


if __name__ == '__main__':
    unittest.main()
