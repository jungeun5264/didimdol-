"""Streamlit 사용자 인증: PBKDF2-HMAC SHA256, 계정별 DB 연동."""
from __future__ import annotations

import base64
import hashlib
import hmac
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
                 'baseline', 'diagnosis_baseline_is_real', 'saved_diagnosis_digest'):
        st.session_state.pop(name, None)
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


def _login_submit(username, password):
    if not _allowed_login_attempt():
        st.error('로그인 시도가 너무 많습니다. 잠시 후 다시 시도해주세요.')
        return False
    record = store.find_account(username.strip().lower())
    # 없는 계정도 동일한 KDF를 실행하여 계정 존재 여부의 타이밍 유출을 줄입니다.
    if record is None:
        verify_password(password, _DUMMY_HASH)
        valid = False
    else:
        valid = verify_password(password, record['password_hash'])
    if not valid:
        st.session_state.setdefault('login_fail_times', []).append(time.monotonic())
        st.error('아이디 또는 비밀번호가 올바르지 않습니다.')
        return False
    user = {k: record[k] for k in ('user_id', 'username', 'display_name')}
    load_user_data(user)
    st.session_state['auth_user'] = user
    st.session_state['login_fail_times'] = []
    return True


# 고정 더미 계정을 조회하지 않더라도 해시 검증 시간을 비슷하게 맞춥니다.
_DUMMY_HASH = hash_password('not-a-real-account')


def render_auth(view, navigate):
    st.html('''<style>
      [data-testid="stMainBlockContainer"]{max-width:1060px!important;padding-top:38px!important;}
      .auth-intro{text-align:center;padding:18px 0 24px;}
      .auth-eyebrow{font-size:12px;font-weight:800;letter-spacing:.12em;color:#238954;}
      .auth-title{font-size:36px;font-weight:850;color:#1c3128;margin:6px 0;}
      .auth-subtitle{font-size:15px;color:#64736a;}
      .st-key-auth_card{max-width:460px;margin:0 auto;background:#fff;border:1px solid #e1ece3;
        border-radius:24px;padding:28px 32px;box-shadow:0 8px 25px rgba(22,83,48,.06);}
      .st-key-auth_card .stButton>button[kind="primary"]{background:#238954;border-color:#238954;color:white;}
      .st-key-auth_card input{background:#fff!important;color:#203528!important;}
      </style><div class="auth-intro"><div class="auth-eyebrow">DIDIMDOL · ACCOUNT</div>
      <div class="auth-title">디딤돌</div><div class="auth-subtitle">나의 AI 역량 성장 기록을 안전하게 관리하세요.</div></div>''')
    if current_user():
        navigate('mypage')
        return
    with st.container(key='auth_card'):
        t1,t2 = st.columns(2)
        if t1.button('로그인', key='auth_tab_login', type='primary' if view == 'login' else 'secondary',use_container_width=True):
            navigate('login')
        if t2.button('회원가입', key='auth_tab_signup', type='primary' if view == 'signup' else 'secondary',use_container_width=True):
            navigate('signup')
        st.write('')
        if view == 'login':
            st.markdown('### 다시 만나서 반가워요!')
            with st.form('login_form', clear_on_submit=False):
                username = st.text_input('아이디', placeholder='아이디를 입력하세요', max_chars=24)
                password = st.text_input('비밀번호', type='password', placeholder='비밀번호를 입력하세요')
                submit = st.form_submit_button('로그인', type='primary', use_container_width=True)
            if submit and _login_submit(username, password):
                dest = st.session_state.pop('post_login_view', 'mypage')
                navigate(dest)
            st.caption('비밀번호 찾기·이메일 인증은 아직 지원하지 않습니다. 계정을 잊어버리지 않도록 보관해주세요.')
        else:
            st.markdown('### 디딤돌 시작하기')
            with st.form('signup_form', clear_on_submit=False):
                display_name = st.text_input('이름 또는 닉네임',max_chars=40,placeholder='표시할 이름을 입력하세요')
                username = st.text_input('아이디',max_chars=24,placeholder='영문·숫자·_·- (3~24자)')
                password = st.text_input('비밀번호',type='password',placeholder='8자 이상',max_chars=128)
                confirm = st.text_input('비밀번호 확인',type='password',max_chars=128)
                submit = st.form_submit_button('회원가입 완료',type='primary',use_container_width=True)
            if submit:
                if not display_name.strip() or len(display_name.strip()) > 40:
                    st.error('이름 또는 닉네임을 입력해주세요.')
                elif not _USER_RX.fullmatch(username):
                    st.error('아이디는 영문·숫자·밑줄·하이픈 3~24자로 입력해주세요.')
                elif len(password) < 8:
                    st.error('비밀번호는 8자 이상 입력해주세요.')
                elif password != confirm:
                    st.error('비밀번호 확인이 일치하지 않습니다.')
                else:
                    record = store.create_account(username.lower(), display_name.strip(), hash_password(password))
                    if record is None:
                        st.error('이미 사용 중인 아이디입니다.')
                    else:
                        load_user_data(record)
                        st.session_state['auth_user'] = record
                        dest = st.session_state.pop('post_login_view', 'mypage')
                        navigate(dest)
        if not store.is_hosted_database():
            st.caption('현재 로컬 SQLite 저장소를 사용합니다. Streamlit Cloud 배포 전 DATABASE_URL 설정이 필요합니다.')
