"""Dependency diagnostics must not report success without the tokenizer package."""
import contextlib
import importlib.metadata
import io
import json
from pathlib import Path
import runpy
import unittest
from unittest.mock import patch


class Doctor(unittest.TestCase):
    def inspect(self, missing=None):
        def version(name):
            if name == missing:
                raise importlib.metadata.PackageNotFoundError(name)
            return 'installed-fixture'
        output = io.StringIO()
        with patch('importlib.metadata.version', side_effect=version), \
             patch('shutil.which', return_value=None), contextlib.redirect_stdout(output):
            with self.assertRaises(SystemExit) as stopped:
                runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/doctor.py'), run_name='__main__')
        return stopped.exception.code, json.loads(output.getvalue())

    def test_missing_tokenizer_fails_python_dependency_check(self):
        code, report = self.inspect('tiktoken')
        self.assertEqual(code, 1)
        self.assertIsNone(report['packages']['tiktoken'])

    def test_installed_python_dependencies_and_missing_external_tools_are_reported(self):
        code, report = self.inspect()
        self.assertEqual(code, 0)
        self.assertEqual(set(report['packages']), {'lxml', 'pypdf', 'tiktoken'})
        self.assertFalse(report['tools']['pdftotext'])
        self.assertFalse(report['tools']['codex'])
