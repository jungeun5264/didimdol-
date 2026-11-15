"""Streamlit 사용자 인증: PBKDF2-HMAC SHA256, 계정별 DB 연동."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
from copy import deepcopy
import streamlit as st

import store

_ITERATIONS = 600_000
_USER_RX = re.compile(r'^[a-zA-Z0-9_-]{3,24}$')


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    raw = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, _ITERATIONS)
    return f'pbkdf2_sha256${_ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(raw).decode()}'


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, digest = encoded.split('$')
        if algorithm != 'pbkdf2_sha256':
            return False
        expected = base64.b64decode(digest, validate=True)
        check = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'),
                                    base64.b64decode(salt, validate=True), int(iterations))
        return hmac.compare_digest(expected, check)
    except (ValueError, TypeError):
        return False


def current_user():
    return st.session_state.get('auth_user')


def load_user_data(user):
    """새 로그인 시 타인의 이전 세션 캐시를 제거하고 자신의 데이터를 읽습니다."""
    from training import BASELINE
    saved = store.load_diagnosis(user['user_id'])
    for name in ('stage', 'answers', 'option_orders', 'editing_mode',
                 'page', 'selected_id', 'category', 'messages', 'training_plan',
                 'revealed_events', 'event_index', 'outputs', 'attempts',
                 'attempt_no', 'draft_message', '_clear_draft_message',
                 'baseline', 'diagnosis_baseline_is_real', 'saved_diagnosis_digest',
                 'onboarding_owner', 'onboarding_answers', 'onboarding_step',
                 'type_survey_just_completed'):
        st.session_state.pop(name, None)
    for key in list(st.session_state):
        if key.startswith('survey_q_'):
            st.session_state.pop(key, None)
    if saved:
        st.session_state['stage'] = 13
        st.session_state['answers'] = saved['answers']
        scores = saved['scores']
        st.session_state['baseline'] = baseline_from_scores(scores)
        st.session_state['diagnosis_baseline_is_real'] = True
        st.session_state['saved_diagnosis_digest'] = digest_answers(saved['answers'])
    else:
        st.session_state['baseline'] = deepcopy(BASELINE)
        st.session_state['diagnosis_baseline_is_real'] = False
    st.session_state['attempts'] = store.load_trainings(user['user_id'])
    st.session_state['page'] = 'library'


def baseline_from_scores(scores):
    from training import BASELINE
    mapping = {
        'agency': 'human_agency', 'responsibility': 'human_responsibility',
        'ethics': 'ethical_view', 'safety': 'safe_use',
        'ai_basics': 'ai_basic', 'utilization': 'ai_usage',
    }
    result = deepcopy(BASELINE)
    for source, target in mapping.items():
        if source in scores:
            result[target] = round(min(2.0, max(0.0, float(scores[source]))) / 2 * 100)
    return result


def digest_answers(answers):
    import json
    return hashlib.sha256(json.dumps(answers, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def persist_diagnosis_if_complete():
    user = current_user()
    if not user or st.session_state.get('stage') != 13:
        return
    import test
    answers = st.session_state.get('answers', {})
    if not test.diagnosis_complete():
        return
    digest = digest_answers(answers)
    if st.session_state.get('saved_diagnosis_digest') == digest:
        return
    scores = test.calculate_scores()
    store.save_diagnosis(user['user_id'], scores, answers)
    st.session_state['saved_diagnosis_digest'] = digest
    st.session_state['baseline'] = baseline_from_scores(scores)
    st.session_state['diagnosis_baseline_is_real'] = True


def sign_out():
    # 사용자 전환 시 위젯/진단/훈련 캐시를 포함한 모든 세션 상태를 제거합니다.
    st.session_state.clear()


def _allowed_login_attempt():
    log = [t for t in st.session_state.get('login_fail_times', []) if time.monotonic() - t < 60]
    st.session_state['login_fail_times'] = log
    return len(log) < 5


def _login_attempt(username, password):
    """Authenticate using the existing account store. Return an error or None."""
    if not _allowed_login_attempt():
        return '로그인 시도가 너무 많습니다. 잠시 후 다시 시도해주세요.'
    record = store.find_account(username.strip().lower())
    # Constant-work dummy hash also for unknown usernames.
    valid = verify_password(password, record['password_hash']) if record else verify_password(password, _DUMMY_HASH)
    if not valid:
        st.session_state.setdefault('login_fail_times', []).append(time.monotonic())
        return '아이디 또는 비밀번호가 올바르지 않습니다.'
    user = {k: record[k] for k in ('user_id', 'username', 'display_name')}
    load_user_data(user)
    st.session_state['auth_user'] = user
    st.session_state['login_fail_times'] = []
    return None


def _signup_attempt(display_name, username, password, confirm):
    """Register with existing onboarding_pending mechanism. Return (error, field)."""
    if not display_name.strip() or len(display_name.strip()) > 40:
        return '이름 또는 닉네임을 입력해주세요.', 'nickname'
    if not _USER_RX.fullmatch(username):
        return '아이디는 영문·숫자·밑줄·하이픈 3~24자로 입력해주세요.', 'userId'
    if len(password) < 8 or len(password) > 128:
        return '비밀번호는 8~128자로 입력해주세요.', 'password'
    if password != confirm:
        return '비밀번호 확인이 일치하지 않습니다.', 'passwordConfirm'
    record = store.create_account(username.lower(), display_name.strip(), hash_password(password))
    if record is None:
        return '이미 사용 중인 아이디입니다.', 'userId'
    load_user_data(record)
    st.session_state['auth_user'] = record
    return None


# 고정 더미 계정을 조회하지 않더라도 해시 검증 시간을 비슷하게 맞춥니다.
_DUMMY_HASH = hash_password('not-a-real-account')


def render_auth(view, navigate):
    """Show friend's unchanged login.html UI; bind it to existing account + LPA logic."""
    from friend_pages import auth_fragment
    user = current_user()
    if user:
        navigate('onboarding' if store.needs_onboarding(user['user_id']) else 'mypage')
        return

    # The HTML submits its values to a hidden *server-side* Streamlit form.
    # Sensitive values are not written into HTML by this module.
    st.html("""<style>
      .st-key-auth_bridge {position:absolute!important;width:0!important;height:0!important;
        overflow:hidden!important;opacity:0!important;pointer-events:none!important;}
    </style>""")
    with st.container(key='auth_bridge'):
        with st.form('auth_bridge_form', clear_on_submit=True, border=False):
            raw_payload = st.text_input('payload', key='auth_payload', max_chars=1000,
                                        label_visibility='collapsed')
            sent = st.form_submit_button('submit', key='auth_bridge_submit')

    flash = None
    if sent:
        st.session_state['auth_render_no'] = st.session_state.get('auth_render_no', 0) + 1
        try:
            payload = json.loads(raw_payload or '{}')
        except (ValueError, TypeError):
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        mode = payload.get('mode') if payload.get('mode') in ('login','signup') else view
        data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
        value = lambda k: str(data.get(k) or '')[:200]
        username = value('userId').strip().lower()
        if mode == 'login':
            error = _login_attempt(username, value('password'))
            if error is None:
                destination = st.session_state.pop('post_login_view', 'mypage')
                user = current_user()
                navigate('onboarding' if store.needs_onboarding(user['user_id']) else destination)
                return
            flash = {'msg':error,'userId':username,'field':'password'}
        else:
            name = value('nickname')
            issue = _signup_attempt(name, username, value('password'), value('passwordConfirm'))
            if issue is None:
                st.session_state.pop('post_login_view', None)
                navigate('onboarding')  # preserve mandatory Q26 12-item LPA survey
                return
            flash = {'msg':issue[0],'field':issue[1],'userId':username,'nickname':name}
        view = mode

    st.html(auth_fragment(view, flash, st.session_state.get('auth_render_no', 0)),
            unsafe_allow_javascript=True)
