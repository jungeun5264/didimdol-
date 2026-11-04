"""추가 패키지 없이 실행하는 유형 설문/DB 회귀 테스트.

실행: python verify_onboarding.py
실제 계정 DB가 아닌 임시 SQLite 파일만 사용합니다.
"""
import os
import sqlite3
import sys
import tempfile
import types
import unittest
from pathlib import Path

# store._database_url()의 st.secrets 조회를 위한 최소 스텁. DB 자체는 sqlite로 테스트.
if 'streamlit' not in sys.modules:
    fake_st = types.ModuleType('streamlit')
    fake_st.secrets = {}
    sys.modules['streamlit'] = fake_st

import store
from user_types import QUESTIONS, TYPES, classify


class OnboardingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.previous = store.LOCAL_DB
        self.previous_url = store._database_url
        store.LOCAL_DB = Path(self.tmp.name) / 'test.sqlite3'
        store._database_url = lambda: ''

    def tearDown(self):
        store.LOCAL_DB = self.previous
        store._database_url = self.previous_url
        self.tmp.cleanup()

    def test_12_questions_and_6_types(self):
        self.assertEqual(len(QUESTIONS), 12)
        self.assertEqual(len(TYPES), 6)
        self.assertEqual(len({q[0] for q in QUESTIONS}), 12)
        for type_id in TYPES:
            self.assertEqual(sum(1 for question in QUESTIONS if question[1] == type_id), 2)

    def test_validation_and_ties(self):
        answers = {q[0]: 3 for q in QUESTIONS}
        result = classify(answers)
        self.assertTrue(result['is_close'])
        self.assertEqual(len(result['tied_types']), 6)
        with self.assertRaises(ValueError):
            classify({})
        answers['p1'] = 0
        with self.assertRaises(ValueError):
            classify(answers)

    def test_new_account_requires_survey_and_preserves_existing_data(self):
        store.initialize()
        # 기존 계정 모의 생성: 마이그레이션해도 필수 설문 대상으로 바뀌지 않아야 함.
        with store.connect() as conn:
            store._execute(conn, 'INSERT INTO users (user_id,username,display_name,password_hash) VALUES (?,?,?,?)',
                           ('old-id', 'old', '기존', 'dummy-hash'))
        self.assertFalse(store.needs_onboarding('old-id'))
        store.save_diagnosis('old-id', {'utilization':1.5}, {'a':'기존답변'})
        store.save_training('old-id', 'm1', {'attempt_no':1, 'overall':70})

        new = store.create_account('new', '신규', 'dummy-hash')
        self.assertTrue(store.needs_onboarding(new['user_id']))
        self.assertIsNone(store.load_type_profile(new['user_id']))
        with self.assertRaises(ValueError):
            store.save_type_profile(new['user_id'], {}, {})
        self.assertTrue(store.needs_onboarding(new['user_id']))
        answers = {q[0]: (5 if q[1] == 'verifier' else 2) for q in QUESTIONS}
        result = classify(answers)
        self.assertEqual(result['primary_type'], 'verifier')
        store.save_type_profile(new['user_id'], answers, result)
        self.assertFalse(store.needs_onboarding(new['user_id']))
        profile = store.load_type_profile(new['user_id'])
        self.assertEqual(profile['primary_type'], 'verifier')
        self.assertEqual(profile['answers'], answers)

        # 설문 재응시 시 최근 결과로 덮어쓰되 기존 진단·훈련은 그대로여야 함.
        revised = {q[0]: (5 if q[1] == 'explorer' else 2) for q in QUESTIONS}
        store.save_type_profile(new['user_id'], revised, classify(revised))
        self.assertEqual(store.load_type_profile(new['user_id'])['primary_type'], 'explorer')
        self.assertEqual(store.load_diagnosis('old-id')['scores']['utilization'], 1.5)
        self.assertEqual(store.load_trainings('old-id')['m1'][0]['overall'], 70)
        self.assertTrue(store.find_account('old'))

    def test_migration_from_existing_tables_preserves_records(self):
        # 기존 DB가 users/diagnoses/training_attempts 3개 테이블만 가진 경우.
        with sqlite3.connect(store.LOCAL_DB) as conn:
            conn.execute("""CREATE TABLE users (
                user_id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL, password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            conn.execute("""CREATE TABLE diagnoses (
                user_id TEXT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
                scores_json TEXT NOT NULL, answers_json TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            conn.execute("""CREATE TABLE training_attempts (
                user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                mission_id TEXT NOT NULL,attempt_no INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id,mission_id,attempt_no))""")
            conn.execute("INSERT INTO users(user_id,username,display_name,password_hash) VALUES (?,?,?,?)",
                         ('legacy', 'legacy', '기존 회원', 'old-hash'))
            conn.execute("INSERT INTO diagnoses(user_id,scores_json,answers_json) VALUES(?,?,?)",
                         ('legacy', '{"agency": 1.5}', '{"q": "answer"}'))
            conn.execute("INSERT INTO training_attempts(user_id,mission_id,attempt_no,payload_json) VALUES(?,?,?,?)",
                         ('legacy', 'case01', 1, '{"attempt_no":1, "overall": 70}'))
        store.initialize()
        self.assertFalse(store.needs_onboarding('legacy'))
        self.assertEqual(store.load_diagnosis('legacy')['scores']['agency'], 1.5)
        self.assertEqual(store.load_trainings('legacy')['case01'][0]['overall'], 70)
        self.assertIsNone(store.load_type_profile('legacy'))

    def test_idempotent_initialization(self):
        store.initialize()
        store.initialize()
        self.assertTrue(store.create_account('example', '테스트', 'hashed'))
        self.assertIsNone(store.create_account('example', '테스트', 'hashed'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
