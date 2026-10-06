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


def complete_target_actions(ledger):
    """Complete synthetic heading/instruction records; tests add facts explicitly."""
    ledger['target_review'] = {
        'reviewer': 'synthetic final-text review',
        'assertion_completeness': 'All blocks and draft constituents inspected; factual cases are recorded separately.',
        'semantic_review': 'Synthetic actions and headings retain their meaning and local draft conditions.'}
    for row in ledger['target_units']:
        row['review'] = {
            'reviewed_sha256': row['sha256'],
            'reason': 'Synthetic heading, label or editorial instruction; no implemented result asserted.',
            'meaning_check': 'The instruction and its stated scope are unchanged.',
            'style_check': 'The synthetic wording is direct and readable.'}
        if row['kind'] == 'suggested_wording':
            row['review']['assertion_completeness'] = 'All constituent blocks have their own factual/action review.'
        else:
            row['review'].update(classification='action', assertions=[])


def factual_assertion(ledger, quote, status='supported', **details):
    row = next(row for row in ledger['target_units'] if row['kind'] == 'block' and quote in row['text'])
    row['review'].update(classification='factual', reason='Review the exact factual assertion rather than its verb tense.',
                         assertions=[{'quote': quote, 'status': status, 'reason': 'Exact assertion and its stated scope inspected.', **details}])
    return row


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
        complete_target_actions(self.ledger)

    def test_v2_is_default_and_frozen_v1_is_readable(self):
        self.assertEqual(self.ledger['version'], 2)
        legacy = copy.deepcopy(self.ledger)
        legacy['version'] = 1
        legacy.pop('target_units')
        legacy.pop('target_review')
        result = audit.validate(legacy, self.report)
        self.assertEqual(result['status'], 'records_validated')
        self.assertIn('without a target factual inventory', result['limitation'])
        with self.assertRaisesRegex(ValueError, 'requires a version 2'):
            audit.validate(legacy, self.report, require_v2=True)

    def test_separator_cannot_locate_an_obligation_in_either_version(self):
        self.report.write_text(self.report.read_text(encoding='utf-8') + '\n\n---', encoding='utf-8')
        self.ledger['report_sha256'] = audit.digest(self.report)
        self.ledger['units'][0]['components'][0]['target_quotes'] = ['---']
        for version in (1, 2):
            with self.subTest(version=version):
                ledger = copy.deepcopy(self.ledger)
                ledger['version'] = version
                with self.assertRaisesRegex(ValueError, 'Separator-only'):
                    audit.validate(ledger, self.report)

    def test_frozen_v1_mixed_excerpts_pass_but_v2_rejects_separator_extras(self):
        self.report.write_text(self.report.read_text(encoding='utf-8') + '\n\n---', encoding='utf-8')
        self.ledger['report_sha256'] = audit.digest(self.report)
        self.ledger['units'][0]['components'][0]['target_quotes'].append('---')
        legacy = copy.deepcopy(self.ledger)
        legacy['version'] = 1
        result = audit.validate(legacy, self.report)
        self.assertEqual(result['status'], 'records_validated')
        self.assertFalse(result['semantic_correctness_verified'])
        with self.assertRaisesRegex(ValueError, 'Separator-only'):
            audit.validate(self.ledger, self.report)

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


class FinalTargetEvidence(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root/'manuscript.txt'
        self.report = self.root/'report.md'

    def make_ledger(self, source, report=None, target_quote=None):
        self.source.write_text(source, encoding='utf-8')
        self.report.write_text(source if report is None else report, encoding='utf-8')
        ledger = audit.initialize(self.report, [self.source])
        ledger['scope_review'] = {'reviewer': 'synthetic test', 'source_completeness': 'All supplied source blocks inspected.',
                                  'semantic_review': 'Source requirements retained in the indicated synthetic passages.'}
        for row in ledger['units']:
            row['components'] = [{'source_quote': row['text'], 'obligation': row['text'], 'status': 'retained',
                                  'target_quotes': [target_quote or row['text']], 'reason': 'The cited passage retains the source requirement.'}]
        complete_target_actions(ledger)
        return ledger

    def evidence(self, quote, basis='manuscript', path=None):
        path = self.source if path is None else path
        return {'path': str(path), 'sha256': audit.digest(path), 'quote': quote, 'basis': basis}

    def conditional_ledger(self):
        action = 'Evaluate the procedure with the full model.'
        condition = 'Use this sentence only after the author confirms the procedure was evaluated with the full model.'
        assertion = 'For the extended setting, we evaluate the procedure with the full model.'
        report = (action + '\n\n##### Conditional assessment draft\n\n**Use:** ' + condition +
                  '\n\n**Suggested wording / 建议文本:**\n\n' + assertion)
        ledger = self.make_ledger(action, report, action)
        condition_row = next(row for row in ledger['target_units'] if row['text'] == '**Use:** ' + condition)
        row = factual_assertion(ledger, assertion, status='conditional',
                                condition={'target_unit_id': condition_row['id'], 'quote': condition,
                                           'reason': 'This exact procedure sentence depends on the named author confirmation.'})
        return ledger, row

    def test_source_backed_present_tense_passes(self):
        statement = 'We apply the stated linear filter.'
        ledger = self.make_ledger(statement, '# Supported draft\n\n' + statement)
        factual_assertion(ledger, statement, evidence=[self.evidence(statement)])
        result = audit.validate(ledger, self.report, require_v2=True)
        self.assertEqual(result['status'], 'records_validated')
        self.assertIn('not a proof', result['limitation'])

    def test_direct_derivation_present_tense_passes(self):
        statement = 'For x=0, the product xy is zero.'
        ledger = self.make_ledger(statement)
        derivation = self.root/'derivation.txt'
        derivation.write_text('Substituting x=0 into the supplied product xy gives zero.', encoding='utf-8')
        factual_assertion(ledger, statement, evidence=[self.evidence(
            'Substituting x=0 into the supplied product xy gives zero.', basis='direct_derivation', path=derivation)])
        audit.validate(ledger, self.report)

    def test_factual_assertion_requires_evidence(self):
        statement = 'We evaluate the procedure with the full model.'
        ledger = self.make_ledger(statement)
        factual_assertion(ledger, statement, evidence=[])
        with self.assertRaisesRegex(ValueError, 'needs evidence'):
            audit.validate(ledger, self.report)

    def test_missing_or_invented_source_cannot_support_assertion(self):
        statement = 'We apply the stated linear filter.'
        ledger = self.make_ledger(statement)
        row = factual_assertion(ledger, statement, evidence=[self.evidence(statement)])
        row['review']['assertions'][0]['evidence'][0]['path'] = str(self.root/'missing.txt')
        with self.assertRaisesRegex(ValueError, 'Evidence source missing'):
            audit.validate(ledger, self.report)
        row['review']['assertions'][0]['evidence'] = [self.evidence('All extended-setting evaluations were completed.')]
        with self.assertRaisesRegex(ValueError, 'Evidence excerpt absent'):
            audit.validate(ledger, self.report)

    def test_supporting_source_change_invalidates_review(self):
        statement = 'We apply the stated linear filter.'
        ledger = self.make_ledger(statement)
        support = self.root/'support.txt'
        support.write_text(statement, encoding='utf-8')
        factual_assertion(ledger, statement, evidence=[self.evidence(statement, path=support)])
        support.write_text('The chosen filter is not identified.', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Evidence source changed'):
            audit.validate(ledger, self.report)

    def test_conditional_present_tense_draft_passes(self):
        ledger, _ = self.conditional_ledger()
        result = audit.validate(ledger, self.report)
        self.assertEqual(result['suggested_wording_passages'], 1)

    def test_condition_must_be_visible_and_local(self):
        ledger, row = self.conditional_ledger()
        row['review']['assertions'][0]['condition']['quote'] = 'The author confirmed all experiments were completed.'
        with self.assertRaisesRegex(ValueError, 'Author condition excerpt absent'):
            audit.validate(ledger, self.report)
        ledger, row = self.conditional_ledger()
        row['review']['assertions'][0]['condition'] = {
            'target_unit_id': ledger['target_units'][0]['id'],
            'quote': ledger['target_units'][0]['text'], 'reason': 'Claimed generic condition elsewhere.'}
        with self.assertRaisesRegex(ValueError, 'attached locally'):
            audit.validate(ledger, self.report)

    def test_unresolved_fact_requires_visible_notice(self):
        ledger, row = self.conditional_ledger()
        assertion = row['review']['assertions'][0]
        assertion['status'] = 'unresolved'
        with self.assertRaisesRegex(ValueError, 'Unresolved fact/action needs'):
            audit.validate(ledger, self.report)
        assertion['unresolved_notice'] = assertion.pop('condition')
        audit.validate(ledger, self.report)

    def test_must_to_we_edit_fails_even_after_report_hash_update(self):
        action = 'Evaluate the procedure with the full model.'
        draft = 'For the extended setting, the procedure must be evaluated with the full model.'
        report = action + '\n\n##### Assessment repair\n\n**Suggested wording / 建议文本:**\n\n' + draft
        ledger = self.make_ledger(action, report, action)
        audit.validate(ledger, self.report)
        self.report.write_text(report.replace('the procedure must be evaluated',
                                              'we evaluate the procedure'), encoding='utf-8')
        ledger['report_sha256'] = audit.digest(self.report)
        with self.assertRaisesRegex(ValueError, 'Final target block missing or changed'):
            audit.validate(ledger, self.report)

    def test_copying_new_inventory_does_not_refresh_old_reviews(self):
        ledger, _ = self.conditional_ledger()
        old_reviews = {row['id']: row['review'] for row in ledger['target_units']}
        self.report.write_text(self.report.read_text(encoding='utf-8').replace('we evaluate', 'we validate'), encoding='utf-8')
        ledger['report_sha256'] = audit.digest(self.report)
        ledger['target_units'] = [{**row, 'review': old_reviews[row['id']]} for row in audit.target_inventory(self.report)]
        with self.assertRaisesRegex(ValueError, 'Target review missing or stale'):
            audit.validate(ledger, self.report)

    def test_new_fact_and_missing_block_require_target_review(self):
        action = 'Specify the window convention.'
        ledger = self.make_ledger(action)
        self.report.write_text(action + '\n\nAll assessments have been completed.', encoding='utf-8')
        ledger['report_sha256'] = audit.digest(self.report)
        with self.assertRaisesRegex(ValueError, 'Final target block missing or changed'):
            audit.validate(ledger, self.report)
        ledger = self.make_ledger(action)
        ledger['target_units'].pop()
        with self.assertRaisesRegex(ValueError, 'Final target block missing or changed'):
            audit.validate(ledger, self.report)

    def test_blank_target_review_cannot_be_delivered(self):
        action = 'Specify the window convention.'
        ledger = self.make_ledger(action)
        ledger['target_units'][0]['review'] = {}
        with self.assertRaisesRegex(ValueError, 'Target review missing or stale'):
            audit.validate(ledger, self.report)

    def test_grouped_draft_covers_each_paragraph_and_formula(self):
        action = 'State the exact normalization ratio.'
        report = (action + '\n\n##### Ratio draft\n\n**Suggested wording / 建议文本:**\n\n'
                  'Specify the normalization factor.\n\n$$q=a/b.$$\n\nState its normalization.\n\n'
                  '##### Next comment\n\nRetain the next definition.')
        ledger = self.make_ledger(action, report, action)
        draft = next(row for row in ledger['target_units'] if row['kind'] == 'suggested_wording')
        self.assertEqual(len(draft['member_ids']), 3)
        factual_assertion(ledger, '$$q=a/b.$$', status='conditional', condition={
            'target_unit_id': draft['member_ids'][0], 'quote': 'Specify the normalization factor.',
            'reason': 'Synthetic draft intentionally lacks a local author confirmation.'})
        with self.assertRaisesRegex(ValueError, 'attached locally'):
            audit.validate(ledger, self.report)


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
