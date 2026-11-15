"""디딤돌 통합 Streamlit 앱: 친구 디자인 + Q26-LPA + 진단 + Luna + 커뮤니티."""
from __future__ import annotations

from pathlib import Path
import streamlit as st
import store
import auth
from friend_pages import original_fragment, header_fragment

st.set_page_config(page_title='디딤돌 | AI 활용 역량 진단·훈련',
                   page_icon='🌱', layout='wide', initial_sidebar_state='collapsed')
BASE = Path(__file__).resolve().parent

try:
    store.initialize()  # retain onboarding_pending, LPA, diagnoses, training_attempts
except Exception as exc:
    st.error('사용자 데이터베이스에 연결할 수 없습니다. DATABASE_URL 설정과 DB 연결 상태를 확인해주세요.')
    st.caption(type(exc).__name__)
    st.stop()

ROUTES = ('home', 'diagnosis', 'diagnosis-live', 'training', 'community',
          'mypage', 'login', 'signup', 'onboarding')


def go(view: str) -> None:
    st.session_state['current_view'] = view
    st.query_params['view'] = view
    st.rerun()


def hidden_route_buttons():
    # Friend HTML links are clicked through hidden native Streamlit buttons
    # so auth/diagnosis/assessment session_state is preserved.
    st.html('''<style>.st-key-didimdol_router_controls{position:absolute!important;
         width:0!important;height:0!important;overflow:hidden!important;opacity:0!important;
         pointer-events:none!important;}</style>''')
    with st.container(key='didimdol_router_controls'):
        for route in ROUTES:
            if st.button('route', key='route_' + route):
                if route == 'community':
                    st.session_state['community_mode'] = 'list'
                go(route)


def header(view: str):
    css = ((BASE / 'ui.css').read_text(encoding='utf-8') + '\n' +
           (BASE / 'training.css').read_text(encoding='utf-8'))
    st.html(header_fragment(view, css), unsafe_allow_javascript=True)
    hidden_route_buttons()


view = st.query_params.get('view') or st.session_state.get('current_view', 'home')
if view not in ROUTES:
    view = 'home'
st.session_state['current_view'] = view

# Do not weaken mandatory Q26 onboarding, original diagnosis auth or current
# authenticated community: those are existing app behaviors.
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
elif view in ('login', 'signup'):
    hidden_route_buttons()
    auth.render_auth(view, go)
else:
    header(view)
    if view == 'mypage':
        import mypage
        mypage.render(go)
    elif view == 'onboarding':
        import onboarding
        onboarding.render(go)
    elif view == 'diagnosis-live':
        import test
        test.render()
        auth.persist_diagnosis_if_complete()
    elif view == 'training':
        import training
        training.render_training()
    elif view == 'community':
        import community
        community.render(go)
