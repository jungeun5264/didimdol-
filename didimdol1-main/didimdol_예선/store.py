"""디딤돌 사용자/진단/훈련 기록 저장소.

로컬: SQLite, 공유 서비스: DATABASE_URL 지정 시 PostgreSQL.
비밀번호는 별도 auth.py에서 PBKDF2로 해시됩니다.
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path

BASE = Path(__file__).resolve().parent
LOCAL_DB = BASE / 'didimdol_users.sqlite3'


def _database_url():
    try:
        import streamlit as st
        value = st.secrets.get('DATABASE_URL', '')
    except Exception:
        value = ''
    return value or os.getenv('DATABASE_URL', '')


def is_hosted_database():
    return bool(_database_url())


@contextmanager
def connect():
    url = _database_url()
    if url:
        import psycopg
        from psycopg.rows import dict_row
        conn = psycopg.connect(url, row_factory=dict_row, sslmode='require', connect_timeout=8)
    else:
        conn = sqlite3.connect(LOCAL_DB, timeout=20)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        conn.execute('PRAGMA busy_timeout = 20000')
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _execute(conn, sql, params=()):
    # SQL 문장들은 모두 상수 문자열이고 사용자 입력은 매개변수로만 전달합니다.
    sql = sql.replace('?', '%s') if _database_url() else sql
    return conn.execute(sql, params)


def initialize():
    with connect() as conn:
        _execute(conn, '''CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )''')
        _execute(conn, '''CREATE TABLE IF NOT EXISTS diagnoses (
            user_id TEXT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
            scores_json TEXT NOT NULL,
            answers_json TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )''')
        _execute(conn, '''CREATE TABLE IF NOT EXISTS onboarding_pending (
            user_id TEXT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE
        )''')
        _execute(conn, '''CREATE TABLE IF NOT EXISTS user_type_profiles (
            user_id TEXT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
            survey_version TEXT NOT NULL,
            primary_type TEXT NOT NULL,
            answers_json TEXT NOT NULL,
            scores_json TEXT NOT NULL,
            tied_types_json TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )''')
        _execute(conn, '''CREATE TABLE IF NOT EXISTS training_attempts (
            user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            mission_id TEXT NOT NULL,
            attempt_no INTEGER NOT NULL,
            payload_json TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, mission_id, attempt_no)
        )''')


def create_account(username, display_name, password_hash):
    user_id = uuid.uuid4().hex
    try:
        with connect() as conn:
            _execute(conn, 'INSERT INTO users (user_id,username,display_name,password_hash) VALUES (?,?,?,?)',
                     (user_id, username.lower(), display_name, password_hash))
            # 기존 가입자는 유지하고 새 가입자에게만 설문 완료를 필수로 표시합니다.
            _execute(conn, 'INSERT INTO onboarding_pending (user_id) VALUES (?)', (user_id,))
    except Exception as exc:
        # 트랜잭션은 contextmanager가 먼저 rollback한 상태여야 합니다.
        if (_database_url() and type(exc).__name__ == 'UniqueViolation') or (
            not _database_url() and isinstance(exc, sqlite3.IntegrityError)):
            return None
        raise
    return {'user_id': user_id, 'username': username.lower(), 'display_name': display_name}


def find_account(username):
    with connect() as conn:
        row = _execute(conn, 'SELECT user_id,username,display_name,password_hash FROM users WHERE username=?',
                       (username.lower(),)).fetchone()
    return dict(row) if row else None


def get_profile(user_id):
    with connect() as conn:
        row = _execute(conn, 'SELECT user_id,username,display_name FROM users WHERE user_id=?', (user_id,)).fetchone()
    return dict(row) if row else None


def save_diagnosis(user_id, scores, answers):
    with connect() as conn:
        _execute(conn, '''INSERT INTO diagnoses (user_id,scores_json,answers_json) VALUES (?,?,?)
              ON CONFLICT(user_id) DO UPDATE SET scores_json=excluded.scores_json,
              answers_json=excluded.answers_json, updated_at=CURRENT_TIMESTAMP''',
                 (user_id, json.dumps(scores, ensure_ascii=False), json.dumps(answers, ensure_ascii=False)))


def load_diagnosis(user_id):
    with connect() as conn:
        row = _execute(conn, 'SELECT scores_json,answers_json,updated_at FROM diagnoses WHERE user_id=?',
                       (user_id,)).fetchone()
    if row is None:
        return None
    return {'scores': json.loads(row['scores_json']), 'answers': json.loads(row['answers_json']),
            'updated_at': str(row['updated_at'])}


def save_training(user_id, mission_id, item):
    with connect() as conn:
        _execute(conn, '''INSERT INTO training_attempts (user_id,mission_id,attempt_no,payload_json) VALUES (?,?,?,?)
                 ON CONFLICT (user_id,mission_id,attempt_no) DO UPDATE SET
                 payload_json=excluded.payload_json, updated_at=CURRENT_TIMESTAMP''',
                 (user_id, mission_id, int(item['attempt_no']), json.dumps(item, ensure_ascii=False)))


def load_trainings(user_id):
    with connect() as conn:
        rows = _execute(conn, 'SELECT mission_id,payload_json FROM training_attempts WHERE user_id=? ORDER BY mission_id,attempt_no',
                        (user_id,)).fetchall()
    out = {}
    for row in rows:
        out.setdefault(row['mission_id'], []).append(json.loads(row['payload_json']))
    return out


def needs_onboarding(user_id):
    """신규 가입 후 아직 설문을 끝내지 않은 계정만 True."""
    with connect() as conn:
        row = _execute(conn, 'SELECT user_id FROM onboarding_pending WHERE user_id=?', (user_id,)).fetchone()
    return row is not None


def save_type_profile(user_id, answers, result):
    """설문 결과 저장과 필수 설문 해제를 원자적으로 처리합니다."""
    from user_types import classify
    verified = classify(answers)
    if result != verified:
        raise ValueError('응답과 분류 결과가 일치하지 않습니다.')
    with connect() as conn:
        _execute(conn, '''INSERT INTO user_type_profiles
            (user_id,survey_version,primary_type,answers_json,scores_json,tied_types_json)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET
            survey_version=excluded.survey_version,
            primary_type=excluded.primary_type,
            answers_json=excluded.answers_json,
            scores_json=excluded.scores_json,
            tied_types_json=excluded.tied_types_json,
            updated_at=CURRENT_TIMESTAMP''',
                 (user_id, verified['survey_version'], verified['primary_type'],
                  json.dumps(answers, ensure_ascii=False),
                  json.dumps(verified['scores'], ensure_ascii=False),
                  json.dumps(verified['tied_types'], ensure_ascii=False)))
        _execute(conn, 'DELETE FROM onboarding_pending WHERE user_id=?', (user_id,))


def load_type_profile(user_id):
    with connect() as conn:
        row = _execute(conn, '''SELECT survey_version, primary_type, answers_json, scores_json,
                               tied_types_json, updated_at FROM user_type_profiles WHERE user_id=?''',
                       (user_id,)).fetchone()
    if row is None:
        return None
    scores = json.loads(row['scores_json'])
    ordered = sorted(scores.values(), reverse=True)
    return {
        'survey_version': row['survey_version'],
        'primary_type': row['primary_type'],
        'answers': json.loads(row['answers_json']),
        'scores': scores,
        'tied_types': json.loads(row['tied_types_json']),
        'margin': ordered[0] - ordered[1],
        'is_close': ordered[0] - ordered[1] <= 1,
        'updated_at': str(row['updated_at']),
    }

    
