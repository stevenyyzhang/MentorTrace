"""Synthetic record-contract tests; these do not certify review quality."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import audit_merge_obligations as audit

ROOT = Path(__file__).resolve().parents[1]
PAGE = 'Receiver observes y. Input access is unstated. Joint independence is unstated. Sampling is already stated. Normalization is unstated. Only a single-stream observation model is claimed. Abstract headline is 12% gain.'
INTRO = 'Introduction headline is 12% gain. The reference-method comparator appears in the experiment.'


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(audit.encoded(value))


def anchor(quote='Receiver observes y.', page=1):
    return {'kind': 'text', 'page': page, 'quote': quote}


def finding(fid, goal, check_id=None):
    row = {'id': fid, 'anchor': anchor(), 'relation': 'Observation and input conditions',
           'gap': 'An input relation is unclear.', 'impact': 'Interpretation cannot be reconstructed.', 'closure_goal': goal}
    if check_id:
        row['check_ids'] = [check_id]
    return row


def organization(sid, quote, page, check_id):
    return {'id': sid, 'anchor': anchor(quote, page), 'current_order': quote,
            'proposed_order': 'At this headline occurrence, identify the reference-method comparator.',
            'reason': 'Identify what this local range comparison measures.', 'affected_links': 'Headline to experiment',
            'conditions': 'Use only the existing comparator.', 'check_ids': [check_id]}


def disposition(sid, target_ids, status='merged'):
    return {'input_id': sid, 'status': status, 'output_ids': target_ids,
            'reason': 'CHANGED_REASON_DO_NOT_REVEAL_IN_A', 'evidence': [anchor()]}


def reviewer(phase='A', kind='synthetic_test', seen=False):
    return {'name': 'Synthetic fixture reviewer', 'kind': kind, 'prior_outputs_seen': seen,
            'context_scope': 'originals_and_full_manuscript' if phase == 'A' else 'frozen_a_and_final_outputs',
            'limits': 'Synthetic declared judgments; no scientific or model review.'}


class MergeObligationAudit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run = self.root / 'run'
        self.out = self.root / 'side-audit'
        self.report = self.root / 'report.md'
        self.report.write_text('State input source and declare the independence premise.\nState normalization.\nAt the abstract headline, identify the reference-method comparator.\n---', encoding='utf-8')
        write(self.run / 'inputs/paper/body.json', [{'page': 1, 'text': PAGE}, {'page': 2, 'text': INTRO}])
        image_entries = []
        for page in (1, 2):
            image = self.run / f'inputs/paper/images/page-{page:04d}.png'
            image.parent.mkdir(parents=True, exist_ok=True)
            image.write_bytes(b'synthetic-image-' + str(page).encode())
            image_entries.append({'page': page, 'path': f'images/page-{page:04d}.png', 'sha256': audit.digest(image)})
        write(self.run / 'inputs/paper/manifest.json', {'pages': 2, 'images': image_entries, 'role': 'review_manuscript'})
        self.f1 = finding('reader:F1', 'State input source.', 'reader:C1')
        self.f2 = finding('technical:F1', 'Declare the independence premise.', 'technical:C1')
        self.f3 = finding('reader:F2', 'State sampling and state normalization.', 'reader:C2')
        self.f4 = finding('technical:F2', 'Require antenna combination details.', 'technical:C2')
        self.f5 = finding('reader:F3', 'Explain an unchanged one-to-one item.', 'reader:C3')
        self.g1 = organization('reader:G1', 'Abstract headline is 12% gain.', 1, 'reader:C1')
        self.g2 = organization('supplement_1:G2', 'Introduction headline is 12% gain.', 2, 'supplement_1:C1')
        for stage, findings, suggestions in (
                ('reader', [self.f1, self.f3, self.f5], [self.g1]),
                ('technical', [self.f2, self.f4], []),
                ('supplement_1', [], [self.g2])):
            check_ids = sorted({cid for row in findings + suggestions for cid in row['check_ids']})
            checks = [{'id': cid, 'anchor': anchor(), 'required_relation': 'Synthetic original input relation',
                       'reason': 'SOURCE_OPINION_NOT_AUTHORITY', 'judgment': 'gap'} for cid in check_ids]
            write(self.run / f'calls/{stage}/response.json', {'findings': findings, 'checks': checks, 'organization_suggestions': suggestions})
        raw = [self.f1, self.f2, self.f3, self.f4, self.f5]
        write(self.run / 'findings_raw.json', raw)
        merged = {'findings': [finding('merge:F1', 'State input source and declare the independence premise.'),
                               finding('merge:F2', 'State normalization.'), finding('merge:F3', 'Explain an unchanged one-to-one item.')],
                  'organization_suggestions': [{**self.g1, 'id': 'merge:G1'}],
                  'dispositions': [disposition(self.f1['id'], ['merge:F1']), disposition(self.f2['id'], ['merge:F1']),
                                   disposition(self.f3['id'], ['merge:F2'], 'narrowed'), disposition(self.f4['id'], [], 'withdrawn'),
                                   disposition(self.f5['id'], ['merge:F3'], 'retained')],
                  'organization_dispositions': [disposition(self.g1['id'], ['merge:G1']), disposition(self.g2['id'], ['merge:G1'])]}
        final = {'findings': [finding('verify:F1', 'State input source and declare the independence premise.'),
                              finding('verify:F2', 'State normalization.'), finding('verify:F3', 'Explain an unchanged one-to-one item.')],
                 'organization_suggestions': [{**self.g1, 'id': 'verify:G1',
                                              'proposed_order': 'At the abstract headline, identify the reference-method comparator.'}],
                 'dispositions': [disposition('merge:F1', ['verify:F1'], 'retained'), disposition('merge:F2', ['verify:F2'], 'retained'),
                                  disposition('merge:F3', ['verify:F3'], 'retained')],
                 'organization_dispositions': [disposition('merge:G1', ['verify:G1'], 'retained')]}
        write(self.run / 'calls/merge/response.json', merged)
        write(self.run / 'calls/verify/response.json', final)
        write(self.run / 'final.json', final)
        write(self.run / 'RAW_FREEZE.json', {'sha256': audit.digest(self.run / 'findings_raw.json')})
        write(self.run / 'RESULT_FREEZE.json', {'raw': audit.digest(self.run / 'findings_raw.json'), 'final': audit.digest(self.run / 'final.json')})

    def prepare(self):
        return audit.prepare(self.run, self.out)

    def complete_a(self):
        ledger = audit.read(self.out / 'phase_a.template.json')
        ledger['reviewer'] = reviewer()
        originals = {s['source_id']: s['original'] for s in audit.read(self.out / 'phase_a.packet.json')['sources']}
        for unit in ledger['units']:
            sid = unit['source_id']
            source = originals[sid]
            field = 'proposed_order' if ':G' in sid else 'closure_goal'
            evidence = [anchor()]
            assessment = 'optional' if ':G' in sid else 'required'
            if sid == 'technical:F2':
                assessment, evidence = 'unsupported', [anchor('Only a single-stream observation model is claimed.')]
            unit['coverage_review'] = {'status': 'completed', 'reason': 'Synthetic scope decomposition includes every stated requirement and occurrence.'}
            unit['components'] = [{'id': sid + ':c1', 'source_field': field, 'source_quote': source[field],
                                   'requirement': source[field], 'assessment': assessment,
                                   'reason': 'Synthetic requirement decision grounded in the supplied manuscript.',
                                   'evidence': evidence, 'occurrences': [source['anchor']]}]
            if sid == 'reader:F2':
                unit['components'][0].update(source_quote='State sampling', requirement='State sampling.',
                                              assessment='already_answered', evidence=[anchor('Sampling is already stated.')])
                unit['components'].append({'id': sid + ':c2', 'source_field': field, 'source_quote': 'state normalization',
                                           'requirement': 'State normalization.', 'assessment': 'required',
                                           'reason': 'Synthetic formation requirement remains unanswered.',
                                           'evidence': [anchor('Normalization is unstated.')], 'occurrences': [anchor()]})
        return ledger

    def ready_b(self, a=None):
        if not self.out.exists():
            self.prepare()
        audit.adjudicate(self.out, a or self.complete_a())
        audit.compare(self.out, self.report)
        ledger = audit.read(self.out / 'phase_b.template.json')
        ledger['reviewer'] = reviewer('B', seen=True)
        for row in ledger['components']:
            cid = row['component_id']
            if cid in {'reader:F2:c1', 'technical:F2:c1'}:
                row.update(status='not_required', reason='Frozen A supports this sound withdrawal.', target_quotes=[], report_quotes=[])
            elif cid == 'supplement_1:G2:c1':
                row.update(status='missing', reason='Additional introduction occurrence is omitted; frozen A assessed it optional.')
            else:
                if cid == 'reader:F2:c2':
                    tid, field, quote = 'verify:F2', 'closure_goal', 'State normalization.'
                elif cid == 'reader:G1:c1':
                    tid, field, quote = 'verify:G1', 'proposed_order', 'At the abstract headline, identify the reference-method comparator.'
                else:
                    tid, field, quote = 'verify:F1', 'closure_goal', 'State input source and declare the independence premise.'
                row.update(status='kept', reason='Synthetic focused excerpt covers this component at its required occurrence.',
                           target_quotes=[{'target_id': tid, 'field': field, 'quote': quote}], report_quotes=[quote])
        return ledger

    def test_selection_and_phase_a_blinding(self):
        before = {p.relative_to(self.run).as_posix(): audit.digest(p) for p in self.run.rglob('*') if p.is_file()}
        result = self.prepare()
        self.assertEqual(result['selected_sources'], 6)
        packet = audit.read(self.out / 'phase_a.packet.json')
        sids = {s['source_id'] for s in packet['sources']}
        self.assertNotIn('reader:F3', sids)
        self.assertIn('technical:F2', sids)
        self.assertIn('supplement_1:G2', sids)
        self.assertTrue(any(set(g['source_ids']) == {'reader:F1', 'technical:F1'} for g in packet['groups']))
        self.assertTrue(any(set(g['source_ids']) == {'reader:G1', 'supplement_1:G2'} for g in packet['groups']))
        text = json.dumps(packet)
        self.assertNotIn('CHANGED_REASON_DO_NOT_REVEAL_IN_A', text)
        self.assertNotIn('verify:F', text)
        self.assertNotIn('merge:F', text)
        self.assertEqual([p['page'] for p in packet['manuscript']], [1, 2])
        self.assertEqual(before, {p.relative_to(self.run).as_posix(): audit.digest(p) for p in self.run.rglob('*') if p.is_file()})
        self.assertFalse((self.out / 'phase_b.packet.json').exists())

    def sync_final(self, final):
        write(self.run / 'calls/verify/response.json', final)
        write(self.run / 'final.json', final)
        write(self.run / 'RESULT_FREEZE.json', {'raw': audit.digest(self.run / 'findings_raw.json'), 'final': audit.digest(self.run / 'final.json')})

    def test_verify_only_fan_in_and_verify_changed_one_to_one_selection(self):
        merged = audit.read(self.run / 'calls/merge/response.json')
        merged['findings'].append(finding('merge:F4', 'Declare the independence premise.'))
        next(d for d in merged['dispositions'] if d['input_id'] == 'technical:F1').update(status='retained', output_ids=['merge:F4'])
        next(d for d in merged['dispositions'] if d['input_id'] == 'reader:F1')['status'] = 'retained'
        write(self.run / 'calls/merge/response.json', merged)
        final = audit.read(self.run / 'final.json')
        final['dispositions'].append(disposition('merge:F4', ['verify:F1']))
        self.sync_final(final)
        snapshot = audit.load_run(self.run)
        self.assertTrue(any(set(g['source_ids']) == {'reader:F1', 'technical:F1'} for g in snapshot['groups']))
        self.assertNotIn('reader:F3', [s['source_id'] for s in snapshot['sources']])
        for status in ('narrowed', 'withdrawn'):
            changed = copy.deepcopy(final)
            d = next(d for d in changed['dispositions'] if d['input_id'] == 'merge:F3')
            d['status'] = status
            if status == 'withdrawn':
                d['output_ids'] = []
                changed['findings'] = [f for f in changed['findings'] if f['id'] != 'verify:F3']
            self.sync_final(changed)
            with self.subTest(status=status):
                self.assertIn('reader:F3', [s['source_id'] for s in audit.load_run(self.run)['sources']])

    def test_surface_withdrawal_is_excluded_and_source_accounting_is_strict(self):
        surface = finding('language:F1', 'Replace a surface typo.')
        surface['finding_type'] = 'surface'
        write(self.run / 'calls/language/response.json', {'findings': [surface], 'checks': []})
        raw = audit.read(self.run / 'findings_raw.json') + [surface]
        write(self.run / 'findings_raw.json', raw)
        write(self.run / 'RAW_FREEZE.json', {'sha256': audit.digest(self.run / 'findings_raw.json')})
        merged = audit.read(self.run / 'calls/merge/response.json')
        merged['dispositions'].append(disposition('language:F1', [], 'withdrawn'))
        write(self.run / 'calls/merge/response.json', merged)
        self.sync_final(audit.read(self.run / 'final.json'))
        self.assertNotIn('language:F1', [s['source_id'] for s in audit.load_run(self.run)['sources']])
        merged['dispositions'].pop()
        write(self.run / 'calls/merge/response.json', merged)
        with self.assertRaisesRegex(ValueError, 'duplicate/missing source dispositions'):
            self.prepare()
        self.assertFalse(self.out.exists())

    def test_missing_source_check_reference_is_rejected(self):
        path = self.run / 'calls/reader/response.json'
        source = audit.read(path)
        source['checks'].pop()
        write(path, source)
        with self.assertRaisesRegex(ValueError, 'Missing/duplicate source check'):
            self.prepare()
        self.assertFalse(self.out.exists())

    def test_branch_acceptance_records_and_raw_hashes_are_bound(self):
        response = self.run / 'calls/reader/response.json'
        raw = self.run / 'calls/reader/raw_response.json'
        raw.write_bytes(response.read_bytes())
        record = self.run / 'calls/reader/record.json'
        write(record, {'response_sha256': audit.digest(response), 'raw_response_sha256': audit.digest(raw)})
        ledger = self.ready_b()
        package = audit.read(self.out / 'package.json')
        self.assertIn('calls/reader/raw_response.json', package['source_files'])
        raw.write_bytes(raw.read_bytes() + b' ')
        with self.assertRaisesRegex(ValueError, 'raw_response.json source hash mismatch'):
            audit.validate(ledger, self.report)

    def test_merge_and_verify_raw_response_hashes_are_bound(self):
        raw_paths = []
        for stage in ('merge', 'verify'):
            response = self.run / f'calls/{stage}/response.json'
            raw = self.run / f'calls/{stage}/raw_response.json'
            raw.write_bytes(response.read_bytes())
            write(self.run / f'calls/{stage}/record.json', {'response_sha256': audit.digest(response),
                                                          'raw_response_sha256': audit.digest(raw)})
            raw_paths.append(raw)
        ledger = self.ready_b()
        package = audit.read(self.out / 'package.json')
        for stage in ('merge', 'verify'):
            self.assertIn(f'calls/{stage}/raw_response.json', package['source_files'])
        for raw in raw_paths:
            old = raw.read_bytes()
            raw.write_bytes(old + b' ')
            try:
                with self.subTest(stage=raw.parent.name), self.assertRaisesRegex(ValueError, 'raw_response.json source hash mismatch'):
                    audit.validate(ledger, self.report)
            finally:
                raw.write_bytes(old)

    def test_actual_phase_a_batches_and_support_files_are_bound(self):
        self.prepare()
        paths = [self.out / 'phase_a.batches/batch_0001.json', self.out / 'schema.json', self.out / 'instructions.md']
        for path in paths:
            old = path.read_bytes()
            path.write_bytes(old + b' ')
            try:
                with self.subTest(path=path.name), self.assertRaisesRegex(ValueError, 'batch changed|support file changed'):
                    audit.adjudicate(self.out, self.complete_a())
            finally:
                path.write_bytes(old)
        missing = paths[0]
        backup = missing.with_suffix('.backup')
        missing.rename(backup)
        try:
            with self.assertRaisesRegex(ValueError, 'duplicate/missing batch files'):
                audit.adjudicate(self.out, self.complete_a())
        finally:
            backup.rename(missing)
        ledger = self.ready_b()
        packet = audit.read(paths[0])
        packet.update(manuscript=[], sources=[])
        write(paths[0], packet)
        with self.assertRaisesRegex(ValueError, 'batch changed'):
            audit.validate(ledger, self.report)

    def test_sound_withdrawal_optional_occurrence_and_no_certification(self):
        ledger = self.ready_b()
        result = audit.validate(ledger, self.report)
        self.assertTrue(result['delivery_ready'])
        self.assertEqual(result['optional_missing'], ['supplement_1:G2:c1'])
        self.assertFalse(result['semantic_correctness_verified'])
        self.assertEqual(result['status'], 'records_validated')

    def test_phase_b_cannot_open_before_a_is_frozen(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, 'not frozen'):
            audit.compare(self.out, self.report)
        self.assertFalse((self.out / 'phase_b.packet.json').exists())

    def test_a_missing_source_duplicate_source_and_component_ids(self):
        self.prepare()
        for change in ('missing_source', 'duplicate_source', 'duplicate_component'):
            a = self.complete_a()
            if change == 'missing_source':
                a['units'].pop()
            elif change == 'duplicate_source':
                a['units'][-1] = copy.deepcopy(a['units'][0])
            else:
                a['units'][1]['components'][0]['id'] = a['units'][0]['components'][0]['id']
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'duplicate/missing|Duplicate/missing'):
                audit.adjudicate(self.out, a)

    def test_a_pending_scope_and_empty_components_do_not_freeze(self):
        self.prepare()
        for change in ('pending', 'empty'):
            a = self.complete_a()
            if change == 'pending':
                a['units'][0]['coverage_review']['status'] = 'pending'
            else:
                a['units'][0]['components'] = []
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'pending|needs obligation'):
                audit.adjudicate(self.out, a)
        self.assertFalse((self.out / 'phase_a.freeze.json').exists())

    def test_a_invented_text_page_image_and_original_excerpt(self):
        self.prepare()
        for bad in (anchor('Text never supplied'), anchor(page=9),
                    {'kind': 'image', 'page': 1, 'image_sha256': 'bad', 'description': 'Synthetic image description'}):
            a = self.complete_a()
            a['units'][0]['components'][0]['evidence'] = [bad]
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, 'Invented|hash mismatch'):
                audit.adjudicate(self.out, a)
        a = self.complete_a()
        a['units'][0]['components'][0]['source_quote'] = 'invented original requirement'
        with self.assertRaisesRegex(ValueError, 'Source excerpt missing'):
            audit.adjudicate(self.out, a)

    def test_withdrawal_needs_manuscript_evidence(self):
        self.prepare()
        a = self.complete_a()
        row = next(u for u in a['units'] if u['source_id'] == 'technical:F2')
        row['components'][0]['evidence'] = []
        with self.assertRaisesRegex(ValueError, 'withdrawal needs manuscript evidence'):
            audit.adjudicate(self.out, a)

    def test_exposed_a_reviewer_is_truthfully_self_review(self):
        self.prepare()
        a = self.complete_a()
        a['reviewer'] = reviewer(kind='human', seen=True)
        with self.assertRaisesRegex(ValueError, 'self_review'):
            audit.adjudicate(self.out, a)
        a['reviewer']['kind'] = 'self_review'
        result = audit.validate(self.ready_b(a), self.report)
        self.assertEqual(result['reviewer_provenance']['phase_a']['kind'], 'self_review')

    def test_required_missing_blocks_and_cannot_be_discarded(self):
        ledger = self.ready_b()
        row = next(r for r in ledger['components'] if r['component_id'] == 'technical:F1:c1')
        row.update(status='missing', reason='The final instruction omits the independently required premise.', target_quotes=[], report_quotes=[])
        result = audit.validate(ledger, self.report, require_ready=False)
        self.assertFalse(result['delivery_ready'])
        self.assertEqual(result['blockers'][0]['component_id'], 'technical:F1:c1')
        with self.assertRaisesRegex(ValueError, 'not delivery ready'):
            audit.validate(ledger, self.report)
        row['status'] = 'not_required'
        with self.assertRaisesRegex(ValueError, 'cannot be discarded'):
            audit.validate(ledger, self.report)

    def test_b_missing_or_duplicate_component_accounting(self):
        ledger = self.ready_b()
        for duplicate in (False, True):
            b = copy.deepcopy(ledger)
            if duplicate:
                b['components'][-1] = copy.deepcopy(b['components'][0])
            else:
                b['components'].pop()
            with self.subTest(duplicate=duplicate), self.assertRaisesRegex(ValueError, 'duplicate/missing component'):
                audit.validate(b, self.report)

    def test_pending_and_unknown_are_visible_blockers(self):
        self.prepare()
        a = self.complete_a()
        row = next(u for u in a['units'] if u['source_id'] == 'technical:F1')
        row['components'][0]['assessment'] = 'unknown'
        ledger = self.ready_b(a)
        b_row = next(r for r in ledger['components'] if r['component_id'] == 'technical:F1:c1')
        b_row.update(status='unresolved', reason='Necessity remains unknown.', target_quotes=[], report_quotes=[])
        result = audit.validate(ledger, self.report, False)
        self.assertFalse(result['delivery_ready'])
        self.assertIn('unresolved', result['blockers'][0]['reason'])
        b_row['status'] = 'pending'
        result = audit.validate(ledger, self.report, False)
        self.assertEqual(result['blockers'][0]['reason'], 'comparison pending')
        b_row['status'] = 'not_required'
        with self.assertRaisesRegex(ValueError, 'Unknown necessity'):
            audit.validate(ledger, self.report)

    def test_unknown_can_be_delivered_only_as_explicit_report_uncertainty(self):
        self.prepare()
        a = self.complete_a()
        a_row = next(u for u in a['units'] if u['source_id'] == 'technical:F1')
        a_row['components'][0]['assessment'] = 'unknown'
        uncertainty = 'Please confirm whether the independence premise holds; this remains unknown from the supplied manuscript.'
        self.report.write_text(self.report.read_text(encoding='utf-8') + '\n' + uncertainty, encoding='utf-8')
        ledger = self.ready_b(a)
        row = next(r for r in ledger['components'] if r['component_id'] == 'technical:F1:c1')
        row.update(status='unresolved', target_quotes=[], report_quotes=[uncertainty],
                   reason='This is still unknown and explicitly requests author confirmation.',
                   uncertainty_visibility_review={'status': 'completed', 'presented_as': 'unknown_or_author_confirmation',
                                                  'reason': 'The focused report excerpt explicitly says unknown and asks the author to confirm it.'})
        result = audit.validate(ledger, self.report)
        self.assertTrue(result['delivery_ready'])
        self.assertEqual(result['visible_unknown'], ['technical:F1:c1'])
        self.assertEqual(result['remaining_unknown'], ['technical:F1:c1'])
        self.assertEqual(row['status'], 'unresolved')
        self.assertFalse(result['semantic_correctness_verified'])
        row['uncertainty_visibility_review']['presented_as'] = 'confirmed_error'
        self.assertFalse(audit.validate(ledger, self.report, False)['delivery_ready'])
        row['uncertainty_visibility_review']['presented_as'] = 'unknown_or_author_confirmation'
        row['report_quotes'] = []
        self.assertFalse(audit.validate(ledger, self.report, False)['delivery_ready'])
        row['report_quotes'] = ['---']
        with self.assertRaisesRegex(ValueError, 'uncertainty report excerpt'):
            audit.validate(ledger, self.report)

    def test_required_unresolved_stays_blocking_even_with_uncertainty_note(self):
        ledger = self.ready_b()
        row = next(r for r in ledger['components'] if r['component_id'] == 'technical:F1:c1')
        row.update(status='unresolved', target_quotes=[], report_quotes=[], reason='The supported required premise has not been preserved.',
                   uncertainty_visibility_review={'status': 'completed', 'presented_as': 'unknown_or_author_confirmation',
                                                  'reason': 'A visibility note does not remove an already supported requirement.'})
        result = audit.validate(ledger, self.report, False)
        self.assertFalse(result['delivery_ready'])
        self.assertIn('technical:F1:c1', [r['component_id'] for r in result['blockers']])

    def test_stale_manuscript_initial_checks_final_and_frozen_a(self):
        ledger = self.ready_b()
        for relative in ('inputs/paper/body.json', 'calls/reader/response.json', 'final.json', 'phase_a.adjudicated.json'):
            path = (self.out if relative.startswith('phase_a') else self.run) / relative
            old = path.read_bytes()
            path.write_bytes(old + b' ')
            try:
                with self.subTest(relative=relative), self.assertRaisesRegex(ValueError, 'changed|stale|freeze mismatch'):
                    audit.validate(ledger, self.report)
            finally:
                path.write_bytes(old)

    def test_source_file_manifest_cannot_omit_bound_source(self):
        ledger = self.ready_b()
        package_path = self.out / 'package.json'
        package = audit.read(package_path)
        package['source_files'].pop('calls/reader/response.json')
        write(package_path, package)
        with self.assertRaisesRegex(ValueError, 'source file accounting stale'):
            audit.validate(ledger, self.report)

    def test_report_hash_and_exact_substantive_excerpts(self):
        ledger = self.ready_b()
        old = self.report.read_text(encoding='utf-8')
        self.report.write_text(old + ' Changed final report.', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Report changed'):
            audit.validate(ledger, self.report)
        self.report.write_text(old, encoding='utf-8')
        row = next(r for r in ledger['components'] if r['status'] == 'kept')
        for quote in ('---', 'Invented report sentence'):
            row['report_quotes'] = [quote]
            with self.subTest(quote=quote), self.assertRaisesRegex(ValueError, 'report excerpt missing/non-substantive'):
                audit.validate(ledger, self.report)

    def test_target_excerpt_and_lineage(self):
        ledger = self.ready_b()
        row = next(r for r in ledger['components'] if r['status'] == 'kept')
        quote = row['target_quotes'][0]
        quote['quote'] = 'Invented target requirement'
        with self.assertRaisesRegex(ValueError, 'target excerpt missing'):
            audit.validate(ledger, self.report)
        quote.update(target_id='verify:F3', quote='Explain an unchanged one-to-one item.')
        with self.assertRaisesRegex(ValueError, 'outside original source lineage'):
            audit.validate(ledger, self.report)

    def test_duplicates_require_canonical_and_same_occurrence(self):
        self.prepare()
        a = self.complete_a()
        first = next(u for u in a['units'] if u['source_id'] == 'reader:G1')['components'][0]
        extra = next(u for u in a['units'] if u['source_id'] == 'supplement_1:G2')['components'][0]
        extra.update(assessment='duplicate', duplicate_of=first['id'])
        with self.assertRaisesRegex(ValueError, 'Different occurrence'):
            audit.adjudicate(self.out, a)
        extra['duplicate_of'] = 'invented:component'
        with self.assertRaisesRegex(ValueError, 'existing canonical'):
            audit.adjudicate(self.out, a)

    def test_accepted_duplicate_tracks_canonical_missing_requirement(self):
        self.prepare()
        a = self.complete_a()
        first = next(u for u in a['units'] if u['source_id'] == 'reader:F1')['components'][0]
        second = next(u for u in a['units'] if u['source_id'] == 'technical:F1')['components'][0]
        second.update(assessment='duplicate', duplicate_of=first['id'], requirement=first['requirement'], occurrences=first['occurrences'])
        ledger = self.ready_b(a)
        duplicate = next(r for r in ledger['components'] if r['component_id'] == second['id'])
        duplicate.update(status='not_required', reason='Synthetic canonical formulation is retained.', target_quotes=[], report_quotes=[])
        self.assertTrue(audit.validate(ledger, self.report)['delivery_ready'])
        canonical = next(r for r in ledger['components'] if r['component_id'] == first['id'])
        canonical.update(status='missing', reason='The canonical requirement is missing.', target_quotes=[], report_quotes=[])
        self.assertFalse(audit.validate(ledger, self.report, False)['delivery_ready'])

    def test_byte_preflight_preserves_whole_groups_and_full_manuscript(self):
        snapshot = audit.load_run(self.run)
        packet = audit.make_a_packet(snapshot)
        base = {k: v for k, v in packet.items() if k not in {'groups', 'sources'}}
        sources = {s['source_id']: s for s in packet['sources']}
        max_one = max(len(audit.encoded({**base, 'groups': [g], 'sources': [sources[sid] for sid in sorted(g['source_ids'])]})) for g in packet['groups'])
        batches = audit.batch_packets(packet, max_one)
        self.assertGreater(len(batches), 1)
        self.assertEqual({g['group_id'] for b in batches for g in b['groups']}, {g['group_id'] for g in packet['groups']})
        self.assertTrue(all(b['manuscript'] == packet['manuscript'] for b in batches))
        with self.assertRaisesRegex(ValueError, 'never truncate'):
            audit.prepare(self.run, self.out, 100)
        self.assertFalse(self.out.exists())

    def test_no_overwrite_or_original_run_output(self):
        with self.assertRaisesRegex(ValueError, 'separate from immutable'):
            audit.prepare(self.run, self.run / 'audit-side-records')
        self.prepare()
        with self.assertRaisesRegex(ValueError, 'already exists'):
            audit.prepare(self.run, self.out)
        a = self.complete_a()
        audit.adjudicate(self.out, a)
        with self.assertRaisesRegex(ValueError, 'already frozen'):
            audit.adjudicate(self.out, a)

    def test_cli_check_valid_ledger_and_pending_nonzero(self):
        ledger = self.ready_b()
        path = self.root / 'completed-b.json'
        write(path, ledger)
        command = [sys.executable, '-B', str(ROOT / 'scripts/audit_merge_obligations.py'), 'check', '--ledger', str(path), '--report', str(self.report)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)['semantic_correctness_verified'])
        ledger['components'][0].update(status='pending', target_quotes=[], report_quotes=[])
        write(path, ledger)
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('not delivery ready', result.stderr)
        result = subprocess.run(command + ['--allow-incomplete'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)['delivery_ready'])


if __name__ == '__main__':
    unittest.main()
