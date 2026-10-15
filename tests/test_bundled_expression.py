"""Downloaded-package defaults and explicit overrides; no model calls."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import mentortrace_v1 as workflow
import public_expression as public
from test_public_expression import card


class BundledExpression(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.paper = self.root / 'paper'
        workflow.save(self.paper / 'body.json', [{'page': 1, 'text': 'The receiver observes y.'}])
        workflow.save(self.paper / 'manifest.json', {'role': 'review_manuscript', 'images': []})
        workflow.freeze(self.paper)

    def tearDown(self):
        self.temporary.cleanup()

    def create(self, *options):
        run = self.root / 'new-run'
        command = [sys.executable, str(workflow.ROOT / 'scripts/mentortrace_v1.py'),
                   'create', '--paper', str(self.paper), '--run', str(run), *options]
        result = subprocess.run(command, cwd=self.root, capture_output=True, text=True)
        return run, result

    def test_default_cli_freezes_bundled_library_and_prepares_advisor_request(self):
        run, result = self.create()
        self.assertEqual(result.returncode, 0, result.stderr)
        protocol = workflow.read(run / 'inputs/protocol.json')
        self.assertEqual(protocol['stages'][0], 'advisor_tasks')
        self.assertEqual(protocol['expression_mode'], 'advisor_and_draft')
        self.assertEqual(workflow.read(run / 'inputs/expression/manifest.json')['count'], 1581)
        self.assertEqual(workflow.sha(run / 'inputs/expression/FREEZE.json'),
                         workflow.sha(workflow.DEFAULT_EXPRESSION / 'FREEZE.json'))
        self.assertFalse((run / 'inputs/expression/episodes.json').exists())
        request = workflow.next_request(run)
        self.assertEqual(request['stage'], 'advisor_tasks')
        self.assertLessEqual(request['utf8_bytes'], protocol['max_prompt_bytes'])

    def test_no_expression_creates_explicit_baseline(self):
        run, result = self.create('--no-expression')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('expression_version', workflow.read(run / 'inputs/protocol.json'))
        self.assertFalse((run / 'inputs/expression').exists())
        self.assertEqual(workflow.next_request(run)['stage'], 'objects')

    def test_explicit_snapshot_replaces_default(self):
        library = self.root / 'override'
        records = [card()]
        workflow.save(library / 'records.json', records)
        workflow.save(library / 'index.json', [{k: records[0][k] for k in
                       ['id', 'scope', 'section_task', 'retrieval_terms', 'concern_ids']}])
        workflow.save(library / 'manifest.json', {'role': 'public_expression_candidate',
                      'schema_version': 1, 'count': 1, 'private_raw_pages': False,
                      'private_original_mapping': False, 'private_images': False,
                      'status': 'local_preparation_complete_permission_unconfirmed'})
        workflow.freeze(library)
        run, result = self.create('--expression', str(library))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(public.check_library(run / 'inputs/expression')['count'], 1)

    def test_conflicting_switches_do_not_create_run(self):
        run, result = self.create('--expression', str(workflow.DEFAULT_EXPRESSION), '--no-expression')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(run.exists())

    def test_missing_default_does_not_silently_disable_expression(self):
        run = self.root / 'missing-default-run'
        arguments = ['mentortrace_v1.py', 'create', '--paper', str(self.paper), '--run', str(run)]
        with patch.object(workflow, 'DEFAULT_EXPRESSION', self.root / 'missing'), patch.object(sys, 'argv', arguments):
            with self.assertRaises((ValueError, FileNotFoundError)):
                workflow.main()
        self.assertFalse((run / 'state.json').exists())


if __name__ == '__main__':
    unittest.main()
