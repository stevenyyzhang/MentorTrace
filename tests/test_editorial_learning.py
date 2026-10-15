import copy
import tempfile
import unittest
from pathlib import Path
import editorial_learning as learning


class Learning(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.source = self.root / 'source.txt'; self.source.write_text('Explain the mechanism before the steps.', encoding='utf-8')
        available = {'status': 'available', 'text': self.source.read_text(), 'locator': 'line 1', 'source_path': str(self.source),
                     'source_sha256': learning.digest(self.source), 'review_status': 'source_read', 'actor': 'mentor_confirmed'}
        unavailable = {'status': 'unavailable', 'reason': 'No later version supplied.'}
        self.data = {'version': 1, 'episodes': [{'id': 'E1', 'family_id': 'F1', 'section_task': 'Explain method design.',
                     'attribution': 'mentor_confirmed', 'attribution_evidence': 'Synthetic attributed feedback.',
                     'chronology': 'established', 'conflict_status': 'none_observed', 'before': available, 'context': available,
                     'feedback': available, 'after': unavailable, 'followup': unavailable}]}
        lesson = {'id': 'L1', 'source_episode_ids': ['E1'], 'authority': 'explicit_mentor_requirement', 'reader_task': 'Explain design.',
                  'scope': 'paragraph', 'before_account': 'Mechanism implicit.', 'observed_change': 'No revision available.',
                  'changed_relationship': 'Design rationale to steps.', 'after_account': 'Unknown.', 'transfer_conditions': 'Steps need a rationale.',
                  'do_not_transfer': 'Already explained rationale.', 'preference_status': 'local_requirement',
                  'support': [{'episode_id': 'E1', 'field': 'feedback', 'quote': 'Explain the mechanism'}],
                  'support_and_conflict': 'One attributed synthetic comment.', 'source_review_status': 'Synthetic source read.'}
        self.result = {'lessons': [lesson], 'episode_dispositions': [{'episode_id': 'E1', 'status': 'learned', 'lesson_ids': ['L1'], 'reason': 'Local distinction.'}], 'limits': []}

    def tearDown(self): self.temp.cleanup()

    def test_preparation_freezes_without_promoting_or_overwriting(self):
        learning.save(self.root / 'episodes.json', self.data)
        req = learning.prepare(self.root / 'episodes.json', self.root / 'packet')
        self.assertFalse(learning.read(req)['model_called'])
        self.assertFalse(learning.check(self.data, self.result)['admitted_to_runtime'])
        with self.assertRaisesRegex(ValueError, 'preserve prior'): learning.prepare(self.root / 'episodes.json', self.root / 'packet')

    def test_student_revision_is_not_mentor_endorsement(self):
        self.data['episodes'][0]['feedback'] = {'status': 'unavailable', 'reason': 'No mentor feedback.'}
        after = copy.deepcopy(self.data['episodes'][0]['before']); after['actor'] = 'student'
        self.data['episodes'][0]['after'] = after
        self.result['lessons'][0]['support'][0]['field'] = 'after'
        with self.assertRaisesRegex(ValueError, 'attributed evidence'): learning.check(self.data, self.result)

    def test_versions_of_one_family_do_not_corroborate_preference(self):
        second = copy.deepcopy(self.data['episodes'][0]); second['id'] = 'E2'
        self.data['episodes'].append(second)
        lesson = self.result['lessons'][0]; lesson['source_episode_ids'].append('E2')
        lesson['support'].append({'episode_id': 'E2', 'field': 'feedback', 'quote': 'Explain the mechanism'})
        lesson['preference_status'] = 'corroborated_conditional_preference'
        self.result['episode_dispositions'].append({'episode_id': 'E2', 'status': 'learned', 'lesson_ids': ['L1'], 'reason': 'Same family.'})
        with self.assertRaisesRegex(ValueError, 'independent source families'): learning.check(self.data, self.result)
        second['family_id'] = 'F2'; second['conflict_status'] = 'unresolved'
        with self.assertRaisesRegex(ValueError, 'remains unresolved'): learning.check(self.data, self.result)

    def test_changed_source_or_invented_quote_rejected(self):
        self.result['lessons'][0]['support'][0]['quote'] = 'The mentor accepted this paragraph.'
        with self.assertRaisesRegex(ValueError, 'quote absent'): learning.check(self.data, self.result)
        self.source.write_text('Changed.', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Changed learning source'): learning.validate_episodes(self.data)


if __name__ == '__main__': unittest.main()
