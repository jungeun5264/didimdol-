"""추가 설치 없이 Q26-LPA 모델, 가상 사례, 저장/마이그레이션 테스트.

실행: python verify_lpa.py
실제 계정 DB를 사용하지 않습니다.
"""
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

if 'streamlit' not in sys.modules:
    st = types.ModuleType('streamlit')
    st.secrets = {}
    sys.modules['streamlit'] = st

import store
from user_types import QUESTIONS, TYPES, AREAS, SURVEY_VERSION, classify
from legacy_user_types import QUESTIONS as LEGACY_QUESTIONS, classify as legacy_classify

ROOT = Path(__file__).resolve().parent


def answer_map(values):
    return {f'Q26_{i}': value for i, value in enumerate(values, 1)}


class LpaTests(unittest.TestCase):
    def test_structure_and_labels(self):
        self.assertEqual(len(QUESTIONS), 12)
        self.assertEqual(len(AREAS), 4)
        self.assertEqual(len(TYPES), 6)
        self.assertEqual([v[0] for v in QUESTIONS], [f'Q26_{i}' for i in range(1, 13)])

    def test_input_validation(self):
        answers = answer_map([2] * 12)
        for bad, value in [('Q26_1', 0), ('Q26_2', 5), ('Q26_3', '3'), ('Q26_4', 3.0), ('Q26_5', True)]:
            changed = dict(answers, **{bad: value})
            with self.assertRaises(ValueError):
                classify(changed)
        with self.assertRaises(ValueError):
            classify({})
        with self.assertRaises(ValueError):
            classify({**answers, 'unknown': 4})

    def test_team_supplied_smoke_cases(self):
        smoke = json.loads((ROOT / 'classification_smoke_tests.json').read_text(encoding='utf-8'))
        self.assertEqual(smoke['model_id'], 'LPA_full_equal_K6')
        for case in smoke['cases']:
            with self.subTest(case=case['name']):
                actual = classify(answer_map(case['q26_1_to_12']))
                self.assertEqual(actual['primary_type'], f'C{case["expected_type"]}')
                for a, b in zip(actual['four_means'], case['four_means']):
                    self.assertAlmostEqual(a, b, places=10)
                for i, expected in enumerate(case['expected_posterior_type_1_to_6'], 1):
                    self.assertLess(abs(actual['posterior_probabilities'][f'C{i}'] - expected),
                                    smoke['probability_tolerance'])
                self.assertAlmostEqual(sum(actual['posterior_probabilities'].values()), 1.0)

    def test_all_three_is_boundary(self):
        x = classify(answer_map([3] * 12))
        self.assertTrue(x['is_close'])
        self.assertEqual(x['primary_type'], 'C5')
        self.assertEqual(x['runner_up_type'], 'C6')


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_path = store.LOCAL_DB
        self.old_url = store._database_url
        store.LOCAL_DB = Path(self.temp.name) / 'example.sqlite3'
        store._database_url = lambda: ''
        store.initialize()

    def tearDown(self):
        store.LOCAL_DB = self.old_path
        store._database_url = self.old_url
        self.temp.cleanup()

    def test_onboarding_preserves_previous_versions_and_training(self):
        user = store.create_account('example', '예시 사용자', 'dummy-hash')
        uid = user['user_id']
        self.assertTrue(store.needs_onboarding(uid))
        store.save_diagnosis(uid, {'utilization': 1.5}, {'sample': '과거 응답'})
        store.save_training(uid, 'mission-old', {'attempt_no': 1, 'overall': 76})
        old_answers = {q[0]: 3 for q in LEGACY_QUESTIONS}
        old_result = legacy_classify(old_answers)
        store.save_type_profile(uid, old_answers, old_result)
        old_profile = store.load_type_profile(uid)
        self.assertIsNone(store.load_lpa_profile(uid))

        new_answers = answer_map([1] * 12)
        new_result = store.save_lpa_profile(uid, new_answers)
        self.assertEqual(new_result['primary_type'], 'C1')
        self.assertFalse(store.needs_onboarding(uid))
        stored = store.load_lpa_profile(uid)
        self.assertEqual(stored['survey_version'], SURVEY_VERSION)
        self.assertEqual(stored['answers'], new_answers)
        self.assertEqual(stored['model_id'], 'LPA_full_equal_K6')
        self.assertAlmostEqual(sum(stored['posterior_probabilities'].values()), 1)
        self.assertEqual(store.load_type_profile(uid), old_profile)
        self.assertEqual(store.load_diagnosis(uid)['answers'], {'sample': '과거 응답'})
        self.assertEqual(store.load_trainings(uid)['mission-old'][0]['overall'], 76)

        new_again = answer_map([4] * 12)
        store.save_lpa_profile(uid, new_again)
        self.assertEqual(store.load_lpa_profile(uid)['primary_type'], 'C6')
        self.assertEqual(store.load_type_profile(uid), old_profile)

    def test_incomplete_survey_does_not_clear_pending(self):
        user = store.create_account('incomplete', '미완료', 'dummy-hash')
        with self.assertRaises(ValueError):
            store.save_lpa_profile(user['user_id'], answer_map([2] * 11))
        self.assertTrue(store.needs_onboarding(user['user_id']))


if __name__ == '__main__':
    unittest.main(verbosity=2)
