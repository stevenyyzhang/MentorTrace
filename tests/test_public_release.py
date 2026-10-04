import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import audit_public_release as audit
import goodpaper_runtime as cases
import normalize_stage_response as normalize
import run_authorized_stage as transport
import mentortrace_v1 as workflow
import test_pipeline as fixtures


class PublicRelease(unittest.TestCase):
    def test_route_input_cli_works_with_full_distributed_case_indexes(self):
        fixture = fixtures.Pipeline()
        fixture.setUp()
        try:
            run = fixture.root / 'case-cli-run'
            workflow.create_run(fixture.root / 'paper', fixture.root / 'knowledge', run)
            workflow.next_request(run)
            workflow.accept_response(run, fixtures.answer('objects', workflow.context_for(run, 'objects')))
            result = subprocess.run([sys.executable, str(workflow.ROOT / 'scripts/mentortrace_v1.py'),
                                     'route-input', '--run', str(run)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads(result.stdout)
            manifest = workflow.read(workflow.DEFAULT_GOODPAPER / 'manifest.json')
            self.assertEqual(summary['reader_cases'], manifest['reader_cases'])
            self.assertEqual(summary['technical_cases'], manifest['technical_F_cases'])
        finally:
            fixture.tearDown()
    def test_case_recipes_do_not_enter_model_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            record = {'case_id': 'R1', 'full_case': {'full_relation_chain': 'source relation',
                      'writing_pattern': {'action': 'unvalidated edit'},
                      'plausible_alternative': 'unverified comparison', 'rewrite_boundary': 'preserve prerequisites'}}
            (root / 'reader_cases.json').write_text(json.dumps({'R1': record}), encoding='utf-8')
            supplied = cases.selected_for_lane(root, {'reader': [{'case_ids': ['R1']}]}, 'reader')['complete_cases'][0]['full_case']
            self.assertEqual(supplied['full_relation_chain'], 'source relation')
            self.assertEqual(supplied['rewrite_boundary'], 'preserve prerequisites')
            self.assertNotIn('writing_pattern', supplied)
            self.assertNotIn('plausible_alternative', supplied)

    def test_transport_settings_cannot_change_between_stages(self):
        with tempfile.TemporaryDirectory() as folder:
            transport.pin_settings(folder, {'model': 'same', 'effort': 'high'})
            transport.pin_settings(folder, {'model': 'same', 'effort': 'high'})
            with self.assertRaisesRegex(ValueError, 'settings changed'):
                transport.pin_settings(folder, {'model': 'changed', 'effort': 'high'})

    def test_technical_and_companion_source_views_preserve_limits_without_critique(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            summary = {'source_description': 'The source states a conditional result.',
                       'anchor_pages': [2], 'source_review_limits': {'formula_check': 'not performed'},
                       'analyst_critical_note': 'unverified critique',
                       'transfer_hypothesis': 'unvalidated edit', 'chain': ['unverified criticism']}
            record = {'case_id': 'F1', 'full_source_record': summary}
            companion = {'case_id': 'L1', 'paired_from': 'F1', 'full_source_record': summary}
            (root / 'technical_cases.json').write_text(json.dumps({'F1': record}), encoding='utf-8')
            (root / 'technical_companions.json').write_text(json.dumps({'L1': companion}), encoding='utf-8')
            supplied = cases.selected_for_lane(root, {'technical': [{'case_ids': ['F1'], 'companion_ids': ['L1']}]}, 'technical')
            for row in supplied['complete_cases'] + supplied['same_task_companions']:
                self.assertEqual(row['full_source_record'], {
                    'source_description': summary['source_description'], 'anchor_pages': [2],
                    'source_review_limits': {'formula_check': 'not performed'}})

    def test_context_overflow_stops_without_truncation(self):
        request = {'prompt': 'Complete input', 'images': [{'sha256': 'image'}]}
        with self.assertRaisesRegex(ValueError, 'Never truncate'):
            transport.capacity_preflight(request, 100, 50, 80, 10)
        record = transport.capacity_preflight(request, 1000, 50, 80, 10)
        self.assertEqual(record['text_token_upper_bound'], len(request['prompt'].encode('utf-8')))

    def test_cached_output_cannot_be_relabelled_or_rebound(self):
        request = {'prompt': 'A', 'images': [{'sha256': 'original-image'}]}
        record = {'model': 'model-a', 'reasoning_effort': 'high',
                  'prompt_sha256': hashlib.sha256(b'A').hexdigest(),
                  'images': [{'sha256': 'original-image'}]}
        transport.validate_cached(record, request, 'model-a', 'high')
        for changed_request, model, effort in [
            (request, 'model-b', 'high'), (request, 'model-a', 'low'),
            ({**request, 'prompt': 'B'}, 'model-a', 'high'),
            ({**request, 'images': [{'sha256': 'changed'}]}, 'model-a', 'high')
        ]:
            with self.assertRaises(ValueError):
                transport.validate_cached(record, changed_request, model, effort)

    def test_only_complete_unique_anchor_normalization_is_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'inputs/paper').mkdir(parents=True)
            page = 'An obser\u00advation with a uniquely defined input supports the next step.'
            (root / 'inputs/paper/body.json').write_text(json.dumps([{'page': 1, 'text': page}]), encoding='utf-8')
            raw = root / 'raw.json'
            raw.write_text(json.dumps({'anchor': {'page': 1, 'quote': page.replace('\u00ad', '').replace(' ', '\n')}}), encoding='utf-8')
            result, count, unresolved = normalize.normalize(root, 'reader', raw)
            self.assertEqual(count, 1)
            self.assertFalse(unresolved)
            self.assertEqual(json.loads(result.read_text())['anchor']['quote'], page)
            raw.write_text(json.dumps({'anchor': {'page': 1, 'quote': page + ' An unsupported assertion.'}}), encoding='utf-8')
            _, count, unresolved = normalize.normalize(root, 'reader', raw)
            self.assertEqual(count, 0)
            self.assertEqual(len(unresolved), 1)

    def test_private_and_non_english_corpus_fields_fail_public_audit(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'corpus').mkdir()
            (root / 'corpus/example.json').write_text(json.dumps({'original_comments': 'private evidence', 'label': '\u4e2d\u6587'}, ensure_ascii=False), encoding='utf-8')
            rules = {item['rule'] for item in audit.audit(root)['findings']}
            self.assertIn('private_or_source_excerpt_field', rules)
            self.assertIn('non_english_corpus', rules)


if __name__ == '__main__':
    unittest.main()
