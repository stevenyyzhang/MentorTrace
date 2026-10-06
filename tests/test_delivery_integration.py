"""Both audit layers must bind the actual report and the same final review."""
import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path
import test_merge_obligations as obligation_tests
write = obligation_tests.write
from test_preservation import audit as preservation, complete_target_actions

ROOT = Path(__file__).resolve().parents[1]
SKILL_SCRIPTS = ROOT/'.agents/skills/mentortrace/scripts'
sys.path.insert(0, str(SKILL_SCRIPTS))
spec = importlib.util.spec_from_file_location('delivery_renderer', SKILL_SCRIPTS/'render_bilingual_report.py')
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)


class DeliveryIntegration(unittest.TestCase):
    def setUp(self):
        self.fixture = obligation_tests.MergeObligationAudit()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.report = self.fixture.report
        final = self.fixture.run/'final.json'
        extra = '\n\n'.join(preservation.blocks(final))
        self.report.write_text(self.report.read_text('utf-8')+'\n\n'+extra, encoding='utf-8')
        self.upstream = self.fixture.ready_b()
        self.upstream_path = self.fixture.root/'B.json'
        write(self.upstream_path, self.upstream)
        self.ledger = preservation.initialize(self.report, [final])
        self.ledger['scope_review'] = {'reviewer': 'synthetic fixture',
                                     'source_completeness': 'Every synthetic JSON block copied.',
                                     'semantic_review': 'Synthetic instruction and required scope retained.'}
        for row in self.ledger['units']:
            row['components'] = [{'source_quote': row['text'], 'obligation': row['text'],
                                  'status': 'retained', 'target_quotes': [row['text']],
                                  'reason': 'Exact synthetic source block copied.'}]
        complete_target_actions(self.ledger)
        self.ledger_path = self.fixture.root/'delivery.json'
        write(self.ledger_path, self.ledger)

    def validate(self):
        return renderer.validate_delivery(self.report, self.ledger_path, self.upstream_path)

    def test_completed_two_layer_synthetic_review_passes(self):
        result = self.validate()
        self.assertTrue(result['consolidation']['delivery_ready'])
        self.assertFalse(result['semantic_correctness_verified'])

    def test_missing_consolidation_cannot_export(self):
        with self.assertRaisesRegex(ValueError, 'requirements-audit'):
            renderer.validate_delivery(self.report, self.ledger_path)

    def test_old_final_text_audit_cannot_export(self):
        self.ledger['version'] = 1
        write(self.ledger_path, self.ledger)
        with self.assertRaisesRegex(ValueError, 'version 2'):
            self.validate()

    def test_unrelated_final_source_cannot_reuse_consolidation(self):
        other = self.fixture.root/'other-final.json'
        data = json.loads((self.fixture.run/'final.json').read_text('utf-8'))
        data['review_origin'] = 'different synthetic final'
        write(other, data)
        self.ledger['sources'][0] = {'path': str(other), 'sha256': preservation.digest(other)}
        write(self.ledger_path, self.ledger)
        with self.assertRaisesRegex(ValueError, 'final review bound'):
            self.validate()

    def test_changed_report_cannot_reuse_old_comparison(self):
        self.report.write_text(self.report.read_text('utf-8')+'\n\nExtra editorial action.', encoding='utf-8')
        fresh = preservation.initialize(self.report, [self.fixture.run/'final.json'])
        fresh['scope_review'] = self.ledger['scope_review']
        fresh['units'] = self.ledger['units']
        complete_target_actions(fresh)
        write(self.ledger_path, fresh)
        with self.assertRaisesRegex(ValueError, 'Report changed'):
            self.validate()


if __name__ == '__main__':
    unittest.main()
