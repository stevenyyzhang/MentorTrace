import copy
import importlib.util
import tempfile
import json
import subprocess
import sys
import unittest
from pathlib import Path
import technical_applicability as technical

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('preservation', ROOT/'.agents/skills/mentortrace/scripts/audit_report_preservation.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class DeliveryAudit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root/'old.md'
        self.report = self.root/'new.md'
        self.source.write_text('For M=1, specify the window convention.\n\nState whether averaging precedes dB conversion.', encoding='utf-8')
        self.report.write_text(self.source.read_text(encoding='utf-8'), encoding='utf-8')
        self.ledger = audit.initialize(self.report, [self.source])
        self.ledger['scope_review'] = {'reviewer':'synthetic test', 'source_completeness':'Both obligations supplied.', 'semantic_review':'Both copied unchanged.'}
        for row in self.ledger['units']:
            row['components'] = [{'source_quote':row['text'], 'obligation':row['text'], 'status':'retained', 'target_quotes':[row['text']], 'reason':'Unchanged obligation.'}]

    def test_valid_then_dropped_parameter_detail(self):
        audit.validate(self.ledger, self.report)
        self.ledger['units'].pop(0)
        with self.assertRaisesRegex(ValueError, 'block missing'):
            audit.validate(self.ledger, self.report)

    def test_lost_target_and_stale_hash(self):
        self.report.write_text('Explain the experiment protocol.', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Report changed'):
            audit.validate(self.ledger, self.report)
        self.ledger['report_sha256'] = audit.digest(self.report)
        with self.assertRaisesRegex(ValueError, 'excerpt missing'):
            audit.validate(self.ledger, self.report)

    def test_source_changed(self):
        self.source.write_text('Changed source', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Source changed'):
            audit.validate(self.ledger, self.report)

    def test_rejection_requires_real_evidence(self):
        c = self.ledger['units'][0]['components'][0]
        c.update(status='rejected', target_quotes=[])
        with self.assertRaisesRegex(ValueError, 'needs evidence'):
            audit.validate(self.ledger, self.report)

    def test_unresolved_must_be_visible(self):
        c = self.ledger['units'][0]['components'][0]
        c.update(status='unresolved', target_quotes=[])
        with self.assertRaisesRegex(ValueError, 'must be visible'):
            audit.validate(self.ledger, self.report)

    def test_pending_components_rejected(self):
        self.ledger['units'][0]['components'] = []
        with self.assertRaisesRegex(ValueError, 'needs obligations'):
            audit.validate(self.ledger, self.report)

    def test_renderer_blocks_before_writing_outputs(self):
        self.ledger['units'][0]['components'] = []
        ledger_path = self.root/'audit.json'
        ledger_path.write_text(json.dumps(self.ledger), encoding='utf-8')
        output = self.root/'rendered'
        result = subprocess.run([sys.executable, str(ROOT/'.agents/skills/mentortrace/scripts/render_bilingual_report.py'),
                                 '--markdown', str(self.report), '--preservation-audit', str(ledger_path),
                                 '--output-dir', str(output), '--html-only'], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('needs obligations', result.stderr)
        self.assertFalse(output.exists())


class ApplicabilityAudit(unittest.TestCase):
    def setUp(self):
        self.anchor = {'page':1, 'quote':'M=1'}
        self.obj = {'id':'O1', 'lanes':['technical']}
        self.config = {'id':'K1', 'object_ids':['O1'], 'anchors':[self.anchor], 'configuration':'M=1', 'operation':'divide by M-1', 'question':'Is the convention defined?'}
        self.context = {'technical_configurations':[self.config], 'objects':[self.obj]}
        self.result = {'checks':[{'id':'technical:C1', 'object_id':'O1', 'judgment':'gap', 'execution':'completed', 'finding_ids':['technical:F1']}],
                       'findings':[{'id':'technical:F1'}], 'configuration_review':{'additional_configurations':[], 'limits':[], 'items':[{
                           'configuration_id':'K1', 'case_values':'M=1', 'required_condition':'nonzero denominator', 'evaluation':'M-1=0; implementation convention unspecified',
                           'evidence':[self.anchor], 'outcome':'gap', 'check_ids':['technical:C1'], 'finding_ids':['technical:F1']}]}}

    def anchor_check(self, anchor, pages):
        if anchor['quote'] not in pages[anchor['page']]:
            raise ValueError('Bad source')

    def validate(self):
        technical.validate_review(self.result, self.context, {1:'M=1'}, self.anchor_check)

    def test_missing_configuration_fails(self):
        self.validate()
        self.result['configuration_review']['items'] = []
        with self.assertRaisesRegex(ValueError, 'coverage mismatch'):
            self.validate()

    def test_gap_cannot_hide_without_finding(self):
        self.result['configuration_review']['items'][0]['finding_ids'] = []
        with self.assertRaisesRegex(ValueError, 'lost its finding'):
            self.validate()

    def test_sufficiency_cannot_override_gap(self):
        self.result['configuration_review']['items'][0].update(outcome='sufficient', finding_ids=[])
        with self.assertRaisesRegex(ValueError, 'contradicts'):
            self.validate()

    def test_plan_omission_and_explicit_exclusion(self):
        plan = {'objects':[self.obj], 'technical_configurations':[], 'technical_configuration_exclusions':[]}
        with self.assertRaisesRegex(ValueError, 'omits object'):
            technical.validate_plan(plan, {1:'M=1'}, self.anchor_check)
        plan['technical_configuration_exclusions'] = [{'object_id':'O1', 'reason':'Synthetic exclusion example; ordinary review still required'}]
        technical.validate_plan(plan, {1:'M=1'}, self.anchor_check)

    def test_configuration_can_use_relevant_subset_of_context_objects(self):
        self.context['technical_configurations'][0]['object_ids']=['O1','O2']
        self.context['objects'].append({'id':'O2','lanes':['technical']})
        self.validate()


class RuntimeIntegration(unittest.TestCase):
    def test_default_isolation_and_legacy_protocol(self):
        from test_pipeline import Pipeline, m
        fixture = Pipeline()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        request, _ = fixture.advance()
        self.assertIn('TECHNICAL APPLICABILITY v1', request['prompt'])
        advisor = m.prepare_stage_request(fixture.run, 'supplement_1')
        self.assertNotIn('technical_configurations', advisor['prompt'])
        reader = m.prepare_stage_request(fixture.run, 'reader')
        self.assertNotIn('TECHNICAL APPLICABILITY v1', reader['prompt'])
        request = m.prepare_stage_request(fixture.run, 'technical')
        self.assertIn('configuration_review', request['prompt'])
        while m.next_request(fixture.run):
            fixture.advance()
        ctx = m.context_for(fixture.run, 'verify')
        self.assertTrue(all('source_explanation' in c for c in ctx['source_evidence']))
        legacy_run = fixture.root/'legacy'
        m.create_run(fixture.root/'paper', fixture.root/'knowledge', legacy_run, goodpaper_cases=False)
        protocol = m.read(legacy_run/'inputs/protocol.json')
        protocol.pop('technical_applicability')
        m.save(legacy_run/'inputs/protocol.json', protocol)
        m.freeze(legacy_run/'inputs')
        m.save(legacy_run/'calls/objects/response.json', m.read(fixture.run/'calls/objects/response.json'))
        legacy = m.prepare_stage_request(legacy_run, 'technical')
        self.assertNotIn('TECHNICAL APPLICABILITY v1', legacy['prompt'])
        self.assertNotIn('technical_configurations', m.context_for(legacy_run, 'technical'))
