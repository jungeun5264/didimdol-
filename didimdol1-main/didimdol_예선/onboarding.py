"""회원가입 직후 진행하는 AI 활용 성향 설문.

기존 7개 상황의 AI 역량 사전진단과 별도로 관리합니다.
"""
from __future__ import annotations

import streamlit as st

import auth
import store
from user_types import ANSWER_LABELS, QUESTIONS, SURVEY_VERSION, classify


def render(navigate):
    user = auth.current_user()
    if not user:
        navigate('login')
        return

    prior = store.load_type_profile(user['user_id'])
    if st.session_state.get('onboarding_owner') != user['user_id']:
        st.session_state['onboarding_owner'] = user['user_id']
        st.session_state['onboarding_answers'] = dict(prior['answers']) if prior else {}
        st.session_state['onboarding_step'] = 0

    answers = st.session_state['onboarding_answers']
    step = st.session_state['onboarding_step']
    st.markdown('### 나의 AI 활용 성향 알아보기')
    st.caption('12문항 · 6가지 활용 유형 · 약 3분')
    st.info('이 설문은 AI를 사용하는 경향을 탐색하기 위한 것으로, 기존 사전진단의 6개 역량 점수나 검증된 심리검사 결과가 아닙니다.')
    st.progress(step / 3, text=f'{step + 1}/3단계 · {step * 4 + 1}~{step * 4 + 4}번 문항')

    questions = QUESTIONS[step * 4:(step + 1) * 4]
    with st.form(key=f'type_survey_step_{step}'):
        page_answers = {}
        for index, (question_id, _, question) in enumerate(questions, start=step * 4 + 1):
            previous = answers.get(question_id)
            page_answers[question_id] = st.radio(
                f'{index}. {question}', options=list(ANSWER_LABELS),
                format_func=lambda n: ANSWER_LABELS[n],
                index=previous - 1 if previous is not None else None,
                horizontal=True, key=f'survey_q_{question_id}',
            )
            st.write('')

        left, right = st.columns(2)
        with left:
            back = st.form_submit_button('이전 단계', use_container_width=True, disabled=step == 0)
        with right:
            proceed = st.form_submit_button('결과 확인' if step == 2 else '다음 단계',
                                            type='primary', use_container_width=True)

    if not (back or proceed):
        return
    # 단계 이동 시 해당 페이지 응답을 보관해 돌아와도 다시 입력할 필요가 없습니다.
    answers.update({k: v for k, v in page_answers.items() if v is not None})
    if back:
        st.session_state['onboarding_step'] = step - 1
        st.rerun()
    if any(value is None for value in page_answers.values()):
        st.error('현재 페이지의 네 문항에 모두 답변해주세요.')
        return
    if step < 2:
        st.session_state['onboarding_step'] = step + 1
        st.rerun()

    result = classify(answers)
    try:
        store.save_type_profile(user['user_id'], answers, result)
    except Exception:
        st.error('설문 결과를 저장하지 못했습니다. DB 연결 상태를 확인한 뒤 다시 제출해주세요.')
        return
    for key in list(st.session_state):
        if key.startswith('survey_q_'):
            st.session_state.pop(key, None)
    st.session_state.pop('onboarding_owner', None)
    st.session_state.pop('onboarding_answers', None)
    st.session_state.pop('onboarding_step', None)
    st.session_state['type_survey_just_completed'] = True
    navigate('mypage')

