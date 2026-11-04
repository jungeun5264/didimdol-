"""디딤돌: 친구 Figma HTML 원본 + 계정 로그인 + test.py + GPT Luna 훈련."""
from __future__ import annotations

from pathlib import Path
import streamlit as st
import store
import auth
from friend_pages import original_fragment

st.set_page_config(page_title='디딤돌 | AI 활용 역량 진단·훈련',
                   layout='wide', initial_sidebar_state='collapsed')
BASE = Path(__file__).resolve().parent

try:
    store.initialize()
except Exception as exc:
    st.error('사용자 데이터베이스에 연결할 수 없습니다. DATABASE_URL 설정과 DB 연결 상태를 확인해주세요.')
    st.caption(type(exc).__name__)
    st.stop()


def go(view: str) -> None:
    st.session_state['current_view'] = view
    st.query_params['view'] = view
    st.rerun()


def _is_active(current_view: str, route: str) -> bool:
    if route == 'diagnosis':
        return current_view in ('diagnosis', 'diagnosis-live')
    return current_view == route


def _nav_button(label: str, route: str, key: str, current_view: str) -> None:
    button_type = 'primary' if _is_active(current_view, route) else 'secondary'
    if st.button(label, key=key, use_container_width=True, type=button_type):
        if route == 'logout':
            auth.sign_out()
            go('home')
        else:
            go(route)


def header(current_view: str):
    with st.container(key='topbar_shell'):
        left, right = st.columns([8.3, 2.7], gap='medium', vertical_alignment='center')
        with left:
            cols = st.columns([1.45, .85, 1.10, 1.85, 1.05], gap='small', vertical_alignment='center')
            items = [
                ('디딤돌', 'home', 'brand_home'),
                ('홈', 'home', 'menu_home'),
                ('사전진단', 'diagnosis', 'menu_diagnosis'),
                ('맞춤형 심화 교육', 'training', 'menu_training'),
                ('커뮤니티', 'community', 'menu_community'),
            ]
            for col, (label, route, key) in zip(cols, items):
                with col:
                    if key == 'brand_home':
                        if st.button(label, key=key, use_container_width=True):
                            go(route)
                    else:
                        _nav_button(label, route, key, current_view)

        with right:
            action_cols = st.columns([1.15, 1.0], gap='small', vertical_alignment='center')
            action_items = [
                ('마이페이지', 'mypage', 'action_mypage'),
                ('로그아웃' if auth.current_user() else '로그인',
                 'logout' if auth.current_user() else 'login',
                 'action_auth'),
            ]
            for col, (label, route, key) in zip(action_cols, action_items):
                with col:
                    _nav_button(label, route, key, current_view)

    st.divider()


def hidden_route_buttons():
    st.html('''<style>.st-key-didimdol_router_controls{position:absolute!important;
         width:0!important;height:0!important;overflow:hidden!important;opacity:0!important;
         pointer-events:none!important;}</style>''')
    with st.container(key='didimdol_router_controls'):
        for view in ('home', 'diagnosis', 'diagnosis-live', 'training',
                     'mypage', 'login', 'signup', 'onboarding', 'community'):
            if st.button('route', key='route_' + view):
                go(view)


def mypage():
    import mypage as mypage_module
    mypage_module.render(go)


view = st.query_params.get('view') or st.session_state.get('current_view', 'home')
allowed = {'home', 'diagnosis', 'diagnosis-live', 'training', 'mypage', 'login', 'signup', 'onboarding', 'community'}
if view not in allowed:
    view = 'home'
st.session_state['current_view'] = view

if view in ('diagnosis-live', 'training', 'mypage', 'onboarding', 'community') and not auth.current_user():
    st.session_state['post_login_view'] = view
    go('login')

user = auth.current_user()
if user and view != 'onboarding' and store.needs_onboarding(user['user_id']):
    go('onboarding')

if view in ('home', 'diagnosis'):
    hidden_route_buttons()
    name = 'index.html' if view == 'home' else 'diagnosis.html'
    st.html(original_fragment(name), unsafe_allow_javascript=True)
else:
    st.markdown('<style>' + (BASE/'ui.css').read_text(encoding='utf-8') + '\n' +
                (BASE/'training.css').read_text(encoding='utf-8') + '</style>', unsafe_allow_html=True)
    header(view)
    if view in ('login', 'signup'):
        auth.render_auth(view, go)
    elif view == 'mypage':
        mypage()
    elif view == 'onboarding':
        import onboarding
        onboarding.render(go)
    elif view == 'diagnosis-live':
        import test
        test.render()
        auth.persist_diagnosis_if_complete()
    elif view == 'community':
        import community
        community.render(go)
    elif view == 'training':
        import training
        training.render_training()
