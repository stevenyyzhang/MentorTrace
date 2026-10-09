"""Portable execution invariants with synthetic data and fake senders only."""
import contextlib
import copy
import io
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import codex_adapter
import execution_policy
import prepare_delivery_delta as delta
import run_authorized_stage as stages
import prepare_revision_proposals as proposals
import test_pipeline as fixtures
from test_preservation import complete_target_actions


def authorization(effort='xhigh', tier='default'):
    return {'authorized_by': 'user', 'user_statement':
            f'Synthetic explicit choice: synthetic-model, {effort}, {tier}; accept additional usage if Fast.',
            'model': 'synthetic-model', 'reasoning_effort': effort, 'service_tier': tier}


class SettingsAuthorization(unittest.TestCase):
    def test_urgency_or_deadline_is_not_structured_permission(self):
        for statement in ('Please hurry.', 'Finish in 30 minutes.', '加快速度'):
            with self.subTest(statement=statement), self.assertRaisesRegex(ValueError, 'does not match'):
                execution_policy.validate_authorization(
                    {'authorized_by': 'user', 'user_statement': statement}, 'synthetic-model', 'xhigh', 'fast')

    def test_fast_requires_exact_tier_and_additional_usage(self):
        record = authorization(tier='fast')
        with self.assertRaisesRegex(ValueError, 'additional usage'):
            execution_policy.validate_authorization(record, 'synthetic-model', 'xhigh', 'fast')
        record['accepts_additional_usage'] = True
        execution_policy.validate_authorization(record, 'synthetic-model', 'xhigh', 'fast')
        with self.assertRaisesRegex(ValueError, 'service_tier'):
            execution_policy.validate_authorization(authorization(), 'synthetic-model', 'xhigh', 'fast')

    def test_reasoning_changes_in_both_directions_are_rejected(self):
        for authorized, requested in [('xhigh', 'high'), ('high', 'xhigh')]:
            with self.subTest(authorized=authorized), self.assertRaisesRegex(ValueError, 'reasoning_effort'):
                execution_policy.validate_authorization(authorization(authorized), 'synthetic-model', requested)
        execution_policy.validate_authorization(authorization('high'), 'synthetic-model', 'high')

    def test_unauthorized_cli_stops_before_process_or_directory_creation(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(codex_adapter.subprocess, 'Popen') as popen:
            out = Path(folder) / 'not-created'
            with self.assertRaisesRegex(ValueError, 'authorization'):
                codex_adapter.invoke(out, 'Synthetic data')
            self.assertFalse(out.exists())
            popen.assert_not_called()

    def test_cli_pins_standard_and_preserves_effort_and_output_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            calls = []
            class FakeProcess:
                pid = 1
                returncode = 0
                def __init__(self, cmd, **kwargs):
                    calls.append(cmd)
                    self.cmd, self.out = cmd, kwargs['stdout']
                def communicate(self, prompt, timeout):
                    Path(self.cmd[self.cmd.index('-o') + 1]).write_text('{}', encoding='utf-8')
                    self.out.write(json.dumps({'type': 'turn.completed', 'usage': {'input_tokens': 1, 'output_tokens': 1}}) + '\n')
            with patch.object(codex_adapter.shutil, 'which', return_value='fake-codex'), \
                 patch.object(codex_adapter.subprocess, 'Popen', FakeProcess):
                output, _ = codex_adapter.invoke(folder, 'Synthetic', model='synthetic-model',
                                                settings_authorization=authorization())
            self.assertIn('service_tier="default"', calls[0])
            self.assertIn('model_reasoning_effort="xhigh"', calls[0])
            record = json.loads((Path(folder) / 'audit.json').read_text())
            self.assertEqual(record['output_sha256'], stages.mentortrace.sha(output))


class ReuseAndConcurrency(unittest.TestCase):
    def test_real_requests_prefetch_then_accept_without_another_submission(self):
        fixture = fixtures.Pipeline(); fixture.setUp(); self.addCleanup(fixture.tearDown)
        fixture.advance()  # objects frozen; initial lanes remain independent
        auth = fixture.root / 'auth.json'; auth.write_text(json.dumps(authorization()))
        argv = ['runner', '--run', str(fixture.run), '--model', 'synthetic-model',
                '--settings-authorization', str(auth), '--context-window', '1000000',
                '--output-reserve', '10000', '--image-token-reserve', '1000']
        def fake_invoke(folder, prompt, images, **settings):
            folder = Path(folder); stage = folder.parent.name
            output = folder / 'final_text.json'
            output.write_text(json.dumps(fixtures.answer(stage, fixtures.m.context_for(fixture.run, stage))))
            record = {'model': settings['model'], 'reasoning_effort': settings['reasoning_effort'],
                      'requested_service_tier': settings['service_tier'], 'images': [], 'returncode': 0,
                      'fresh_ephemeral_context': True, 'usage': [{'input_tokens': 1, 'output_tokens': 1}],
                      'prompt_sha256': delta.audit.text_digest(prompt), 'output_sha256': delta.audit.digest(output)}
            (folder / 'audit.json').write_text(json.dumps(record))
            return output, record['usage']
        with patch.object(sys, 'argv', argv + ['--prefetch-advisor', '--workers', '2']), \
             patch.object(stages.codex_adapter, 'invoke', side_effect=fake_invoke) as invoke, \
             contextlib.redirect_stdout(io.StringIO()):
            stages.main()
        self.assertEqual(invoke.call_count, 4)
        self.assertEqual(fixtures.m.read(fixture.run / 'state.json')['completed'], ['objects'])
        fixture.advance(); fixture.advance()  # Reader and Technical accepted sequentially
        with patch.object(sys, 'argv', argv), patch.object(stages.codex_adapter, 'invoke') as invoke, \
             contextlib.redirect_stdout(io.StringIO()):
            stages.main()
        invoke.assert_not_called()
        self.assertEqual(fixtures.m.read(fixture.run / 'state.json')['completed'][-1], 'supplement_1')

    def test_completed_cached_stage_does_not_invoke_model_again(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Path(folder); attempt = run / 'calls/supplement_1/first'; attempt.mkdir(parents=True)
            output = attempt / 'final_text.json'; output.write_text('{}')
            request = {'stage': 'supplement_1', 'prompt': 'Synthetic', 'images': []}
            record = {'model': 'synthetic-model', 'reasoning_effort': 'xhigh', 'requested_service_tier': 'default',
                      'prompt_sha256': delta.audit.text_digest('Synthetic'), 'images': [], 'returncode': 0,
                      'fresh_ephemeral_context': True, 'usage': [{'output_tokens': 1}],
                      'output_sha256': delta.audit.digest(output)}
            (attempt / 'audit.json').write_text(json.dumps(record))
            from types import SimpleNamespace
            args = SimpleNamespace(model='synthetic-model', effort='xhigh', service_tier='default',
                                   context_window=10000, output_reserve=100, image_token_reserve=100,
                                   safety_margin=100, attempt_name='new-name')
            with patch.object(stages.codex_adapter, 'invoke') as invoke, \
                 patch.object(stages.normalize_stage_response, 'normalize', return_value=(output, 0, [])), \
                 patch.object(stages.mentortrace, 'validate'), \
                 patch.object(stages.mentortrace, 'context_for', return_value={}):
                result = stages.execute_request(run, request, args, authorization())
            invoke.assert_not_called()
            self.assertTrue(result['reused'])
            self.assertFalse((attempt.parent / 'new-name').exists())

    def test_matching_completed_output_is_found_across_attempt_names(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); attempt = root / 'first'; attempt.mkdir()
            output = attempt / 'final_text.json'; output.write_text('{}')
            request = {'prompt': 'Synthetic', 'images': []}
            record = {'model': 'synthetic-model', 'reasoning_effort': 'xhigh', 'requested_service_tier': 'default',
                      'prompt_sha256': delta.audit.text_digest('Synthetic'), 'images': [],
                      'returncode': 0, 'fresh_ephemeral_context': True, 'usage': [{'output_tokens': 1}],
                      'output_sha256': delta.audit.digest(output)}
            (attempt / 'audit.json').write_text(json.dumps(record))
            found = stages.find_cached(root, request, 'synthetic-model', 'xhigh')
            self.assertEqual(found[0], output)
            output.write_text('{"modified":true}')
            with self.assertRaisesRegex(ValueError, 'modified'):
                stages.find_cached(root, request, 'synthetic-model', 'xhigh')

    def test_legacy_pinned_settings_preserve_standard_and_reject_effort_change(self):
        with tempfile.TemporaryDirectory() as folder:
            stages.pin_settings(folder, {'model': 'synthetic', 'reasoning_effort': 'xhigh'})
            stages.pin_settings(folder, {'model': 'synthetic', 'reasoning_effort': 'xhigh', 'service_tier': 'default'})
            with self.assertRaisesRegex(ValueError, 'settings changed'):
                stages.pin_settings(folder, {'model': 'synthetic', 'reasoning_effort': 'high'})

    def test_prefetch_is_bounded_and_does_not_accept_shared_state(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Path(folder); (run / 'inputs').mkdir()
            names = [f'supplement_{number}' for number in range(1, 5)]
            (run / 'inputs/protocol.json').write_text(json.dumps({'stages': ['objects', 'reader'] + names}))
            (run / 'state.json').write_text(json.dumps({'completed': ['objects']}))
            auth = run / 'auth.json'; auth.write_text(json.dumps(authorization()))
            lock = threading.Lock(); barrier = threading.Barrier(2); active = 0; maximum = 0; completed = []
            def execute(run, request, args, auth):
                nonlocal active, maximum
                with lock:
                    active += 1; maximum = max(maximum, active)
                barrier.wait(timeout=5)
                with lock:
                    active -= 1; completed.append(request['stage'])
                return {'stage': request['stage']}
            argv = ['runner', '--run', str(run), '--model', 'synthetic-model', '--settings-authorization', str(auth),
                    '--context-window', '10000', '--output-reserve', '100', '--image-token-reserve', '100',
                    '--safety-margin', '100', '--prefetch-advisor', '--workers', '2']
            with patch.object(sys, 'argv', argv), \
                 patch.object(stages.mentortrace, 'next_request', return_value={'stage': 'reader'}), \
                 patch.object(stages.mentortrace, 'prepare_stage_request', side_effect=lambda run, name:
                              {'stage': name, 'prompt': 'Synthetic', 'images': []}), \
                 patch.object(stages, 'execute_request', side_effect=execute), \
                 patch.object(stages.mentortrace, 'accept_response') as accept, contextlib.redirect_stdout(io.StringIO()):
                stages.main()
            self.assertEqual(maximum, 2)
            self.assertEqual(set(completed), set(names))
            accept.assert_not_called()
            self.assertEqual(json.loads((run / 'state.json').read_text()), {'completed': ['objects']})


class DeliveryDelta(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / 'source.md'
        self.source.write_text('Explain the input.\n\nDescribe the experiment.', encoding='utf-8')
        self.previous_report = self.root / 'previous.md'
        self.previous_report.write_text('# First\n\nExplain the input.\n\n# Second\n\nDescribe the experiment.', encoding='utf-8')
        self.report = self.root / 'current.md'
        self.report.write_text(self.previous_report.read_text().replace('Describe the experiment.', 'Describe the experiment and its settings.'), encoding='utf-8')
        ledger = delta.audit.initialize(self.previous_report, [self.source])
        ledger['scope_review'] = {'reviewer': 'synthetic', 'source_completeness': 'all fixture blocks', 'semantic_review': 'fixture only'}
        for row in ledger['units']:
            row['components'] = [{'source_quote': row['text'], 'obligation': row['text'], 'status': 'retained',
                                  'target_quotes': [row['text']], 'reason': 'Synthetic exact mapping.'}]
        complete_target_actions(ledger)
        self.previous_ledger = self.root / 'previous.json'
        self.previous_ledger.write_text(json.dumps(ledger), encoding='utf-8')

    def assessment(self, **changes):
        return {'previous_ledger_sha256': delta.audit.digest(self.previous_ledger),
                'report_sha256': delta.audit.digest(self.report), 'reviewer': 'synthetic scope reviewer',
                'reason': 'Only the second fixture paragraph changed.',
                'cross_context_review': 'The two synthetic instructions have no shared conditions.',
                'affected_source_ids': ['S1:B2'], 'affected_target_ids': ['T:B4'], **changes}

    def test_candidates_do_not_automatically_become_reviewed(self):
        ledger, plan = delta.prepare(self.previous_ledger, self.previous_report, self.report)
        self.assertEqual(plan['candidate_source_ids'], ['S1:B1'])
        self.assertEqual(plan['candidate_target_ids'], ['T:B1', 'T:B2'])
        self.assertEqual(plan['carried_target_ids'], [])
        self.assertTrue(all(not row['review'] for row in ledger['target_units']))

    def test_valid_scope_carries_only_unchanged_context_and_preserves_provenance(self):
        ledger, plan = delta.prepare(self.previous_ledger, self.previous_report, self.report, assessment=self.assessment())
        self.assertEqual(plan['carried_source_ids'], ['S1:B1'])
        self.assertEqual(plan['pending_target_ids'], ['T:B3', 'T:B4'])
        self.assertEqual(ledger['carryover']['target_reviewer_provenance'],
                         delta.audit.read(self.previous_ledger)['target_review'])
        with self.assertRaisesRegex(ValueError, 'Missing source/semantic review'):
            delta.audit.validate(ledger, self.report, require_v2=True)

    def test_changed_context_invalidates_unchanged_sentence(self):
        self.report.write_text(self.previous_report.read_text().replace('# First', '# First: conditional use'))
        _, plan = delta.prepare(self.previous_ledger, self.previous_report, self.report)
        self.assertNotIn('T:B2', plan['candidate_target_ids'])

    def test_cross_context_assessment_invalidates_linked_source(self):
        _, plan = delta.prepare(self.previous_ledger, self.previous_report, self.report,
                                assessment=self.assessment(affected_target_ids=['T:B2', 'T:B4']))
        self.assertEqual(plan['carried_source_ids'], [])
        self.assertEqual(plan['carried_target_ids'], [])

    def test_stale_assessment_and_source_changes_cannot_certify_reuse(self):
        with self.assertRaisesRegex(ValueError, 'stale'):
            delta.prepare(self.previous_ledger, self.previous_report, self.report,
                          assessment=self.assessment(report_sha256='wrong'))
        self.source.write_text('Different source')
        _, plan = delta.prepare(self.previous_ledger, self.previous_report, self.report)
        self.assertFalse(plan['previous_valid'])
        self.assertEqual(plan['candidate_target_ids'], [])


class DraftInputPreservation(unittest.TestCase):
    def test_compact_drafting_preserves_all_verified_findings_and_pending_items(self):
        fixture = fixtures.Pipeline(); fixture.setUp(); self.addCleanup(fixture.tearDown)
        while fixtures.m.next_request(fixture.run):
            fixture.advance()
        final_path = fixture.run / 'calls/verify/response.json'
        before_hash = fixtures.m.sha(final_path)
        request_path = proposals.prepare(fixture.run, fixture.root / 'draft')
        prompt = fixtures.m.read(request_path)['prompt']
        supplied, _ = json.JSONDecoder().raw_decode(prompt.split('\nVERIFIED REVIEW\n', 1)[1])
        verified = fixtures.m.read(final_path)
        original_fields = {key: value for key, value in supplied.items() if key != 'source_fidelity_checks'}
        self.assertEqual(original_fields, {key: value for key, value in verified.items()
                                          if key not in {'dispositions', 'source_fidelity_checks'}})
        if 'source_fidelity_checks' in verified:
            self.assertEqual([{key: value for key, value in row.items() if key != 'finding_ids'}
                              for row in supplied['source_fidelity_checks']], verified['source_fidelity_checks'])
        coverage, _ = json.JSONDecoder().raw_decode(prompt.split('\nCOVERAGE AND PENDING ITEMS\n', 1)[1])
        self.assertEqual(coverage['unresolved_dispositions'],
                         [row for row in verified['dispositions'] if row['status'] == 'unresolved'])
        self.assertEqual(before_hash, fixtures.m.sha(final_path))
        self.assertEqual(fixtures.m.read(request_path)['images'],
                         [{**row, 'path': 'inputs/paper/' + row['path']}
                          for row in fixtures.m.read(fixture.run / 'inputs/paper/manifest.json')['images']])


if __name__ == '__main__':
    unittest.main()
