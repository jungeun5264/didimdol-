"""회원가입 직후 Q26 12문항(1~4점) 및 기존 LPA 모형을 이용한 유형 분류 화면."""
from __future__ import annotations

import streamlit as st

import auth
import store
from user_types import AREAS, ANSWER_LABELS, QUESTIONS, classify


def render(navigate):
    user = auth.current_user()
    if not user:
        navigate('login')
        return

    previous = store.load_lpa_profile(user['user_id'])
    if st.session_state.get('onboarding_owner') != user['user_id']:
        st.session_state['onboarding_owner'] = user['user_id']
        st.session_state['onboarding_answers'] = dict(previous['answers']) if previous else {}
        st.session_state['onboarding_step'] = 0

    answers = st.session_state['onboarding_answers']
    step = st.session_state['onboarding_step']
    st.markdown('### 나의 AI 활용 수준과 유형 알아보기')
    st.caption('AI 활용 자기평가 · 총 12문항 · 4점 척도')
    st.info('이 설문은 AI 활용에 대한 자기평가 응답을 바탕으로 기존 LPA 통계 모형의 6개 유형 중 가장 가까운 유형을 제안합니다. 실제 수행능력 시험이나 성격검사는 아닙니다.')
    st.progress(step / 4, text=f'{step + 1}/4단계 · {AREAS[step]} ({step*3+1}~{step*3+3}번 문항)')

    questions = QUESTIONS[step * 3:(step + 1) * 3]
    with st.form(key=f'q26_lpa_step_{step}'):
        page_answers = {}
        for index, (question_id, _, question) in enumerate(questions, start=step * 3 + 1):
            previous_choice = answers.get(question_id)
            page_answers[question_id] = st.radio(
                f'{index}. {question}', options=list(ANSWER_LABELS),
                format_func=lambda n: f'{n}점 · {ANSWER_LABELS[n]}',
                index=(previous_choice - 1) if previous_choice is not None else None,
                horizontal=False, key=f'survey_q_{question_id}',
            )
            st.write('')
        left, right = st.columns(2)
        with left:
            back = st.form_submit_button('이전 단계', disabled=step == 0, use_container_width=True)
        with right:
            proceed = st.form_submit_button('유형 분석 결과 확인' if step == 3 else '다음 단계',
                                            type='primary', use_container_width=True)

    if not (back or proceed):
        return
    answers.update({k: v for k, v in page_answers.items() if v is not None})
    if back:
        st.session_state['onboarding_step'] = step - 1
        st.rerun()
    if any(value is None for value in page_answers.values()):
        st.error('현재 영역의 세 문항에 모두 응답해주세요.')
        return
    if step < 3:
        st.session_state['onboarding_step'] = step + 1
        st.rerun()

    try:
        # 실제 분류는 서버에서 실행하고 결과를 사용자 계정에 저장합니다.
        classify(answers)
        store.save_lpa_profile(user['user_id'], answers)
    except ValueError as exc:
        st.error(str(exc))
        return
    except Exception:
        st.error('설문 결과 저장에 실패했습니다. 데이터베이스 연결 상태를 확인한 뒤 다시 제출해주세요.')
        return

    for key in list(st.session_state):
        if key.startswith('survey_q_'):
            st.session_state.pop(key, None)
    for key in ('onboarding_owner', 'onboarding_answers', 'onboarding_step'):
        st.session_state.pop(key, None)
    st.session_state['type_survey_just_completed'] = True
    navigate('mypage')
