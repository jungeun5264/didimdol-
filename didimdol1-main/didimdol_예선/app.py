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


def header():
    cols = st.columns([1.55, .60, .90, 1.34, .93, .83, .82], gap='small', vertical_alignment='center')
    items = [('디딤돌','home'), ('홈','home'), ('사전진단','diagnosis'),
             ('맞춤형 심화 교육','training'), ('Prompt Coach','prompt-info'),
             ('마이페이지','mypage'), ('로그아웃' if auth.current_user() else '로그인',
                                     'logout' if auth.current_user() else 'login')]
    for i, (c, (label, route)) in enumerate(zip(cols, items)):
        with c:
            if st.button(label, key=f'nav_{i}_{route}', use_container_width=True):
                if route == 'logout':
                    auth.sign_out()
                    go('home')
                else:
                    go(route)
    st.divider()


def hidden_route_buttons():
    # 원본 HTML의 a 링크를 클릭하면 JS가 이 Streamlit 버튼을 클릭합니다.
    # 브라우저 URL을 다시 로딩하지 않으므로 로그인/진단/훈련 세션이 유지됩니다.
    st.html('''<style>.st-key-didimdol_router_controls{position:absolute!important;
         width:0!important;height:0!important;overflow:hidden!important;opacity:0!important;
         pointer-events:none!important;}</style>''')
    with st.container(key='didimdol_router_controls'):
        for view in ('home', 'diagnosis', 'diagnosis-live', 'training', 'prompt-info',
                     'mypage', 'login', 'signup'):
            if st.button('route', key='route_' + view):
                go(view)


def mypage():
    # 마이페이지 UI는 별도 모듈: 친구 HTML/CSS 원본은 변경하지 않습니다.
    import mypage as mypage_module
    mypage_module.render(go)


def pending(title, body):
    st.title(title)
    st.info(body)
    if st.button('홈으로 돌아가기', use_container_width=True):
        go('home')


view = st.query_params.get('view') or st.session_state.get('current_view', 'home')
allowed = {'home', 'diagnosis', 'diagnosis-live', 'training', 'prompt-info', 'mypage', 'login', 'signup'}
if view not in allowed:
    view = 'home'
st.session_state['current_view'] = view

if view in ('diagnosis-live', 'training', 'mypage') and not auth.current_user():
    st.session_state['post_login_view'] = view
    go('login')

if view in ('home', 'diagnosis'):
    hidden_route_buttons()
    name = 'index.html' if view == 'home' else 'diagnosis.html'
    st.html(original_fragment(name), unsafe_allow_javascript=True)
else:
    st.markdown('<style>' + (BASE/'ui.css').read_text(encoding='utf-8') + '\n' +
                (BASE/'training.css').read_text(encoding='utf-8') + '</style>', unsafe_allow_html=True)
    header()
    if view in ('login','signup'):
        auth.render_auth(view, go)
    elif view == 'mypage':
        mypage()
    elif view == 'diagnosis-live':
        import test
        test.render()
        auth.persist_diagnosis_if_complete()
    elif view == 'training':
        import training
        training.render_training()
    elif view == 'prompt-info':
        pending('Prompt Coach', 'Prompt Coach의 별도 기능 코드는 아직 연결 전입니다.')
