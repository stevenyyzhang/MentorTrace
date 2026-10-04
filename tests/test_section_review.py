"""Coverage and backward-compatibility checks; not editorial-quality scoring."""
import copy
import importlib.util
import sys
import unittest
import test_pipeline as fixture
from test_pipeline import m, answer, A

class SectionReview(unittest.TestCase):
 setUp=fixture.Pipeline.setUp
 tearDown=fixture.Pipeline.tearDown
 advance=fixture.Pipeline.advance

 def test_missing_review_or_unsupported_summary_anchor_rejected(self):
  self.advance();ctx=m.context_for(self.run,'reader');x=answer('reader',ctx)
  missing=copy.deepcopy(x);missing.pop('reading_review')
  with self.assertRaisesRegex(ValueError,'Missing section/whole-paper'):m.validate('reader',missing,ctx)
  x['reading_review']['whole_paper']['summary_links'][0]['support']=[{'page':1,'quote':'invented body evidence'}]
  with self.assertRaisesRegex(ValueError,'Quote absent'):m.validate('reader',x,ctx)

 def test_sufficient_section_account_survives_export_without_new_finding(self):
  self.advance();m.next_request(self.run);ctx=m.context_for(self.run,'reader');x=answer('reader',ctx)
  x['checks'][0].update(judgment='sufficient',finding_ids=[]);x['findings']=[]
  x['reading_review']['multiscale']['tasks'][0].update(outcome='sufficient',finding_ids=[],missing_information='')
  x['reading_review']['editorial'][0].update(decision='keep',action='Retain the current order.',
      reason='The single sentence has no useful alternative order.',finding_ids=[])
  m.accept_response(self.run,x)
  while m.next_request(self.run):self.advance()
  m.export_report(self.run)
  self.assertEqual(m.read(self.run/'reading_review.json')['reader'],x['reading_review'])
  self.assertEqual(len(m.read(self.run/'findings_raw.json')),5)

 def test_reader_coverage_never_enters_independent_advisor(self):
  self.advance();req=m.prepare_stage_request(self.run,'supplement_1')
  self.assertIn('section-argument.md',req['module_hashes'])
  ctx=m.context_for(self.run,'supplement_1')
  self.assertNotIn('objects',ctx);self.assertNotIn('reading_review',ctx)
  self.assertNotIn('section_review',ctx)

 def test_legacy_snapshot_not_upgraded(self):
  protocol=m.read(self.run/'inputs/protocol.json');protocol.pop('section_review')
  m.save(self.run/'inputs/protocol.json',protocol)
  (self.run/'inputs/skill/references/section-argument.md').unlink()
  m.freeze(self.run/'inputs')
  self.advance();req=m.next_request(self.run)
  self.assertNotIn('section-argument.md',req['module_hashes'])
  self.assertNotIn(m.READING_SCHEMA,req['prompt'])
  ctx=m.context_for(self.run,'reader');x=answer('reader',ctx)
  self.assertNotIn('reading_review',x);m.validate('reader',x,ctx)

 def test_post_freeze_proposals_are_separate_and_reject_incomplete_run(self):
  spec=importlib.util.spec_from_file_location('proposal',m.ROOT/'scripts/prepare_revision_proposals.py')
  module=importlib.util.module_from_spec(spec)
  prior=sys.modules.get('mentortrace_v1');sys.modules['mentortrace_v1']=m
  try:spec.loader.exec_module(module)
  finally:
   if prior is None:sys.modules.pop('mentortrace_v1')
   else:sys.modules['mentortrace_v1']=prior
  out=self.root/'proposals'
  with self.assertRaisesRegex(ValueError,'Diagnosis must be complete'):module.prepare(self.run,out)
  self.assertFalse(out.exists())
  while m.next_request(self.run):self.advance()
  before=m.sha(self.run/'calls/verify/response.json')
  request=module.prepare(self.run,out);m.verify_frozen(out/'inputs')
  self.assertEqual(before,m.sha(self.run/'calls/verify/response.json'))
  self.assertEqual(m.read(out/'inputs/verified.json'),m.read(self.run/'calls/verify/response.json'))
  self.assertIn('revision_actions',m.read(request)['prompt'])
  self.assertIn('reader-checklist.md',m.read(request)['prompt'])
  self.assertIn('affected_links',m.read(request)['prompt'])
  self.assertFalse(m.read(request)['tools_allowed'])
  self.assertFalse(m.read(request)['model_context_fit_verified'])
  with self.assertRaisesRegex(ValueError,'Output already exists'):module.prepare(self.run,out)

if __name__=='__main__':unittest.main()
