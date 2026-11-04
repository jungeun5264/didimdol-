"""디딤돌 계정별 마이페이지. 저장된 실제 결과만 표시합니다.

디자인은 여기에서만 관리하므로 친구 원본 HTML/CSS나 test.py를 건드리지 않습니다.
"""
from __future__ import annotations

from html import escape
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

import auth
import store
from missions import MISSIONS
from scoring import ABILITY_META, ABILITY_ORDER

CSS_FILE = Path(__file__).with_name('mypage.css')


def _radar(profile: dict, before: dict | None = None):
    labels = [ABILITY_META[k]['label'] for k in ABILITY_ORDER]
    theta = labels + [labels[0]]
    figure = go.Figure()
    if before:
        old = [int(before.get(key, 0)) for key in ABILITY_ORDER]
        figure.add_trace(go.Scatterpolar(
            r=old + [old[0]], theta=theta, name='사전진단',
            fill='toself', line=dict(color='#9AABA1', width=2),
            fillcolor='rgba(154,171,161,.12)'
        ))
    now = [int(profile.get(key, 0)) for key in ABILITY_ORDER]
    figure.add_trace(go.Scatterpolar(
        r=now + [now[0]], theta=theta, name='현재 프로필',
        fill='toself', line=dict(color='#25975A', width=3),
        fillcolor='rgba(37,151,90,.16)'
    ))
    figure.update_layout(
        height=365, margin=dict(l=45, r=45, b=20, t=40),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#3F5D4C', size=11),
        polar=dict(bgcolor='rgba(0,0,0,0)',
                   radialaxis=dict(visible=True, range=[0, 100], tickvals=[20,40,60,80,100],
                                   tickfont=dict(size=9), gridcolor='#E0EDE3'),
                   angularaxis=dict(gridcolor='#E0EDE3')),
        legend=dict(orientation='h', y=1.17, x=.02),
        showlegend=True,
    )
    return figure


def render(navigate):
    user = auth.current_user()
    if not user:
        navigate('login')
        return
    st.html('<style>' + CSS_FILE.read_text(encoding='utf-8') + '</style>')

    diagnosis = store.load_diagnosis(user['user_id'])
    trainings = store.load_trainings(user['user_id'])
    total_attempts = sum(len(attempts) for attempts in trainings.values())
    unique_missions = sum(bool(attempts) for attempts in trainings.values())
    score = sum(float(x) for x in diagnosis['scores'].values()) if diagnosis else None
    name = escape(user['display_name'])
    username = escape(user['username'])
    initial = escape(user['display_name'][:1] or '?')

    st.markdown('''<div class="di-my-eyebrow">MY LEARNING SPACE</div>''', unsafe_allow_html=True)
    st.markdown(f'''
      <section class="di-my-hero">
        <div class="di-my-hero-left">
          <div class="di-my-hi">나의 마이페이지</div>
          <h1>{name}님, 오늘도 한 걸음 성장해요.</h1>
          <p>AI 활용 역량을 확인하고, 나의 진단과 훈련 기록을 한곳에서 관리해보세요.</p>
        </div>
        <div class="di-my-profile"><div class="di-my-avatar">{initial}</div>
          <b>{name}</b><span>@{username}</span></div>
      </section>
    ''', unsafe_allow_html=True)

    tab_type, tab_growth = st.tabs(['나의 AI 활용 유형', '나의 역량 성장'])
    with tab_type:
        _render_type_tab(navigate, user)
    with tab_growth:
        _render_growth_section(navigate, user, diagnosis, trainings,
                               total_attempts, unique_missions, score)


def _render_type_tab(navigate, user):
    """2025 Q26 LPA 6유형: 기존 5점 설문과 구분하여 표시."""
    from user_types import TYPES, AREAS
    profile = store.load_lpa_profile(user['user_id'])
    if st.session_state.pop('type_survey_just_completed', False):
        st.success('12문항 자기평가가 저장되었습니다. 새 LPA 유형 분석 결과를 확인해보세요.')
    if not profile:
        legacy = store.load_type_profile(user['user_id'])
        if legacy:
            from legacy_user_types import TYPES as LEGACY_TYPES
            old = LEGACY_TYPES.get(legacy['primary_type'])
            st.warning('이전 버전의 5점 척도 설문 결과가 있습니다. 새 4점 Q26-LPA 분류와 비교하거나 자동 변환하지 않습니다.')
            if old:
                st.markdown(f'이전 설문 결과: **{old.name}**')
        else:
            st.markdown('### 아직 Q26 기반 AI 활용 유형 설문을 완료하지 않았어요')
            st.caption('기존 회원의 진단·훈련 기록에는 영향을 주지 않습니다.')
        if st.button('새 12문항 설문 시작하기', key='my_start_lpa', type='primary'):
            navigate('onboarding')
        return

    primary = TYPES.get(profile['primary_type'])
    if not primary:
        st.error('저장된 유형을 해석할 수 없습니다. 데이터 관리자에게 문의해주세요.')
        return

    st.markdown('### 나의 AI 활용 유형')
    st.caption('2025 디지털정보격차 실태조사 Q26의 4개 자기평가 영역에 기반한 LPA 모형의 사후확률 추론 결과입니다. 객관적 AI 수행 점수나 정답 확률이 아닙니다.')
    with st.container(border=True):
        st.markdown(f'#### {primary.name} ({profile["primary_type"]})')
        st.write(primary.description)
        st.info(primary.tip)
        st.metric('추천 유형의 사후확률', f'{profile["primary_probability"] * 100:.1f}%')
        runner_info = TYPES[profile['runner_up_type']]
        st.caption(f'두 번째로 가능성이 높은 유형: {runner_info.name} · {profile["runner_up_probability"] * 100:.1f}%')
        if profile['is_close']:
            st.warning('상위 두 유형의 사후확률 차이가 10%p 미만입니다. 두 유형의 설명을 함께 참고하세요. 이 기준은 화면 안내용 임시 정책입니다.')

    st.markdown('#### 네 가지 자기평가 영역')
    for name, mean in zip(AREAS, profile['four_means']):
        st.progress(min(1.0, max(0., mean / 4)), text=f'{name}: {mean:.2f} / 4.00')
    st.caption('각 영역은 세 문항 평균이며, 분류에는 반올림하지 않은 1~4점 원점수를 사용했습니다.')

    st.markdown('#### 여섯 유형의 사후확률')
    for code, info in TYPES.items():
        prob = profile['posterior_probabilities'].get(code, 0.0)
        st.progress(min(1.0, max(0.0, prob)), text=f'{info.name}: {prob * 100:.1f}%')
    st.caption('사후확률 합계는 100%입니다. 기존 조사에서 추정된 혼합비율(pi)이나 실제 수행능력의 정확도와 동일한 값이 아닙니다.')
    st.caption(f'모형: {profile["model_id"]} · 설문: {profile["survey_version"]} · 최근 완료: {profile["updated_at"]}')
    if st.button('12문항 설문 다시 하기', key='my_retake_survey'):
        navigate('onboarding')


def _render_growth_section(navigate, user, diagnosis, trainings,
                           total_attempts, unique_missions, score):
    c1,c2,c3,c4 = st.columns(4, gap='medium')
    data = [
        ('사전진단', '완료' if diagnosis else '미완료', '7개 상황 · 6개 역량'),
        ('진단 총점', f'{score:.2f} / 12' if score is not None else '—', '역량별 2점 만점'),
        ('완료한 훈련', f'{total_attempts}회', '누적 문제 풀이'),
        ('도전한 미션', f'{unique_missions}개', f'전체 {len(MISSIONS)}개 미션'),
    ]
    for col,(label,value,description) in zip((c1,c2,c3,c4),data):
        with col:
            st.markdown(f'''<div class="di-my-metric"><span>{escape(label)}</span>
                        <strong>{escape(value)}</strong><small>{escape(description)}</small></div>''',
                        unsafe_allow_html=True)

    st.write('')
    st.markdown('### 나의 AI 역량')
    st.caption('사전진단에서 확인한 6개 역량을 100점 기준으로 표시해요. 훈련 기록이 있다면 선택한 미션의 수행 결과와 비교할 수 있어요.')
    left,right = st.columns([1.2, .8], gap='large')
    before = auth.baseline_from_scores(diagnosis['scores']) if diagnosis else None

    with left:
        with st.container(border=True):
            if before:
                selected = None
                if total_attempts:
                    mission_ids = [mid for mid, attempts in trainings.items() if attempts]
                    selected = st.selectbox(
                        '비교할 훈련 미션', mission_ids,
                        format_func=lambda mid: MISSIONS.get(mid, {}).get('title',mid),
                        key='mypage_compare_mission',
                    )
                profile = trainings[selected][-1].get('profile',before) if selected else before
                st.plotly_chart(_radar(profile, before if selected else None),
                                use_container_width=True, config={'displayModeBar':False})
                if selected:
                    st.caption('초록색은 선택한 미션의 최종 역량 프로필, 회색은 사전진단 결과예요.')
                else:
                    st.caption('사전진단 결과예요. 훈련을 완료하면 이전·이후 역량을 비교할 수 있어요.')
            else:
                st.info('아직 사전진단을 완료하지 않았어요. 먼저 진단을 진행하면 역량 그래프가 표시돼요.')
                if st.button('사전진단 시작하기 →',type='primary',key='my_start_diagnosis'):
                    navigate('diagnosis-live')
    with right:
        with st.container(border=True):
            st.markdown('#### 영역별 진단 점수')
            if diagnosis:
                labels = {
                    'agency':'인간의 주도권', 'responsibility':'인간의 책임',
                    'ethics':'윤리적 관점', 'safety':'안전하고 책임 있는 사용',
                    'ai_basics':'AI의 기초 이해', 'utilization':'AI 활용 능력',
                }
                for key,label in labels.items():
                    v = float(diagnosis['scores'].get(key,0))
                    st.progress(min(1.,max(0.,v/2)),text=f'{label}   {v:g} / 2점')
                if st.button('내 진단 결과·답변 확인 →', key='my_view_diagnosis', use_container_width=True):
                    st.session_state['stage'] = 13
                    navigate('diagnosis-live')
            else:
                st.markdown('진단 완료 후 강점과 보완할 역량을 확인할 수 있어요.')
            st.write('')
            if st.button('맞춤형 심화 교육으로 이동 →', key='my_go_training',use_container_width=True):
                navigate('training')

    st.write('')
    st.markdown('### 내 문제 훈련 기록')
    if not trainings or not total_attempts:
        with st.container(border=True):
            st.markdown('#### 아직 훈련 기록이 없어요')
            st.caption('처음 문제를 풀고 분석을 완료하면 여기에 나의 도전 기록이 쌓여요.')
            if st.button('첫 번째 훈련 시작하기 →', key='my_first_training', type='primary'):
                navigate('training')
    else:
        for mission_id, attempts in trainings.items():
            if not attempts:
                continue
            latest = attempts[-1]
            mission = MISSIONS.get(mission_id,{})
            title = mission.get('title',mission_id)
            with st.container(border=True):
                a,b,c=st.columns([3.5,1,1],vertical_alignment='center')
                with a:
                    st.markdown(f'**{title}**')
                    st.caption(f"{mission.get('eyebrow','실전 훈련')} · 누적 {len(attempts)}회 도전")
                with b:
                    st.metric('마지막 수행',f'{latest.get("overall",0)}점')
                with c:
                    if st.button('결과 보기 →',key=f'my_result_{mission_id}',use_container_width=True):
                        st.session_state['selected_id']=mission_id
                        st.session_state['page']='result'
                        navigate('training')

    st.write('')
    with st.expander('계정 정보 및 안내'):
        st.write(f'계정: @{user["username"]}')
        st.caption('진단 및 훈련 결과는 로그인한 계정에 연결돼요. 이메일 인증과 비밀번호 재설정은 아직 제공되지 않아요.')
        if not store.is_hosted_database():
            st.warning('로컬 SQLite로 저장 중입니다. Streamlit Cloud에서 여러 사용자 기록을 유지하려면 DATABASE_URL을 설정해야 해요.')
        if st.button('로그아웃',key='my_logout'):
            auth.sign_out()
            navigate('home')
