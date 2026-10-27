import copy,unittest
import advisor_views as v
import advisor_wire as wire
import advisor_output as output
import test_advisor_guidance as fixtures

class Views(unittest.TestCase):
 def fixture(self):
  fixture=fixtures.Guidance();fixture.setUp();ctx=fixture.ctx
  for r in ctx['expression_sources']['records']:
   r['language_features'][0]['frame']='[plural subject] are [property]'
   r['examples'][0].update(body_form_allowed=False,pair_id='P1')
  ctx['advisor_review_view']=1
  return ctx
 def test_stage_separation_roundtrip_and_bounds(self):
  ctx=self.fixture();original=copy.deepcopy(ctx)
  packed,admin=wire.prepare(ctx);view=wire.unpack(packed)
  for a,b in zip(ctx['expression_sources']['records'],view['expression_sources']['records']):
   self.assertNotIn('frame',b['language_features'][0])
   self.assertEqual(a['language_features'][0]['conditions'],b['language_features'][0]['conditions'])
   self.assertEqual(a['examples'][0]['text'],b['examples'][0]['text'])
   self.assertEqual(a['examples'][0]['kind'],b['examples'][0]['kind'])
  self.assertEqual(wire.restore(view,admin),original)
  self.assertEqual(ctx,original)
 def test_hidden_draft_field_cannot_be_cited(self):
  ctx=self.fixture()
  with self.assertRaisesRegex(ValueError,'Draft-only'):
   output.expand({'advisor_output_version':1,'definitions':{},'response':{'x':{'$input':['expression_sources','records',0,'language_features',0,'frame']}}},ctx)
 def test_legacy_retains_draft_fields(self):
  ctx=self.fixture();ctx.pop('advisor_review_view')
  packed,_=wire.prepare(ctx)
  self.assertIn('frame',wire.unpack(packed)['expression_sources']['records'][0]['language_features'][0])

 def test_encoder_does_not_reference_hidden_frame(self):
  ctx=self.fixture();frame='A long drafting frame that is stored locally and must not become an input reference. '*4
  ctx['expression_sources']['records'][0]['language_features'][0]['frame']=frame
  response={'findings':[],'checks':[],'writing_transfers':[],'source_use_dispositions':[],'note':frame}
  encoded=output.encode(response,ctx)
  self.assertEqual(output.expand(encoded,ctx),response)
