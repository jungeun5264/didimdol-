from __future__ import annotations

import os
import html
from textwrap import dedent
from copy import deepcopy
from typing import Any, Dict, List

import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from luna_service import chat_reply, create_training_plan, evaluate
import store
from missions import CATEGORIES, MISSIONS
from scoring import (
    ABILITY_META, ABILITY_ORDER, all_ability_scores, biggest_growth,
    overall_score, strongest_assessed, update_profile, weakest_assessed,
)

load_dotenv()
# Streamlit 페이지 설정은 통합 웹의 app.py에서 한 번만 수행합니다.

PRIMARY = "#6258E8"
TEAL = "#735BDE"
INK = "#172033"
MUTED = "#6B7280"
SURFACE = "#F6FAF7"
BASELINE = {
    "ai_basic": 62, "ai_usage": 58, "human_agency": 55,
    "human_responsibility": 52, "ethical_view": 68, "safe_use": 72,
}

# CSS는 매 rerun마다 render_training()에서 주입합니다.


def init_state():
    defaults = {
        "page": "library", "selected_id": None, "category": "전체",
        "messages": [], "training_plan": None, "revealed_events": [], "event_index": 0,
        "outputs": {}, "attempts": {}, "attempt_no": 1,
        "baseline": deepcopy(BASELINE), "draft_message": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def get_api_key() -> str:
    try:
        secret = st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        secret = ""
    return secret or os.getenv("OPENAI_API_KEY", "")


def get_model() -> str:
    try:
        secret = st.secrets.get("OPENAI_MODEL", "")
    except Exception:
        secret = ""
    return secret or os.getenv("OPENAI_MODEL", "gpt-6-luna")


def selected_mission() -> Dict[str, Any]:
    return MISSIONS[st.session_state.selected_id]


def histories(mid: str) -> List[Dict[str, Any]]:
    return st.session_state.attempts.setdefault(mid, [])


def render_brand(back: bool = False):
    c1, c2 = st.columns([5,1])
    with c1:
        st.markdown('<div class="brand"><div class="brand-mark">◈</div><div class="brand-name">디딤돌 · AI 실전 훈련</div></div>', unsafe_allow_html=True)
    if back and c2.button("← 목록으로", use_container_width=True):
        st.session_state.page = "library"
        st.rerun()



def library_page():
    st.markdown(dedent('''
    <section class="practice-hero">
      <span class="practice-eyebrow">AI PRACTICE · 실전형 역량 훈련</span>
      <h1 class="practice-hero-title">AI를 잘 쓰는 힘,<br>실제 상황에서 길러보세요.</h1>
      <p class="practice-hero-copy">일상과 학업, 취업 상황에서 AI와 함께 문제를 해결해요. 조건이 바뀌면 계획을 고치고,
      마지막에는 내가 내린 판단을 되돌아봅니다.</p>
    </section>
    ''').strip(), unsafe_allow_html=True)
    st.markdown('<div class="practice-heading">어떤 상황을 연습해볼까요?</div>', unsafe_allow_html=True)
    st.caption("관심 있는 상황을 선택해 시작하세요. 각 미션에는 새로운 조건이 3차례 추가됩니다.")
    cols = st.columns(len(CATEGORIES), gap="small")
    for i, cat in enumerate(CATEGORIES):
        if cols[i].button(cat, use_container_width=True,
                          type="primary" if st.session_state.category == cat else "secondary",
                          key=f"cat_{cat}"):
            st.session_state.category = cat
            st.rerun()
    st.write("")
    missions = [m for m in MISSIONS.values() if st.session_state.category == "전체" or m["eyebrow"].startswith(st.session_state.category)]
    if not missions:
        st.info("이 카테고리의 훈련이 준비되지 않았어요.")
        return
    for start in range(0, len(missions), 3):
        cols = st.columns(3, gap="large")
        for col, m in zip(cols, missions[start:start+3]):
            with col:
                with st.container(border=True, key=f"training_mission_{m['id']}"):
                    st.markdown(dedent(f"""
                    <div class="mission-content">
                      <div class="mission-topline"><span class="mission-number">{html.escape(m['accent'])}</span>
                      <span class="mission-category">{html.escape(m['eyebrow'])}</span></div>
                      <h3 class="mission-title">{html.escape(m['title'])}</h3>
                      <p class="mission-summary">{html.escape(m['summary'])}</p>
                      <div class="mission-meta"><span>{html.escape(m['difficulty'])}</span><span>약 {int(m['minutes'])}분</span><span>변수 3개</span></div>
                    </div>
                    """).strip(), unsafe_allow_html=True)
                    if st.button("이 상황 연습하기  →", key=f"open_{m['id']}", use_container_width=True, type="primary"):
                        st.session_state.selected_id = m["id"]
                        st.session_state.attempt_no = len(histories(m["id"])) + 1
                        st.session_state.page = "detail"
                        st.rerun()
        st.write("")


def detail_page():
    m = selected_mission()
    render_brand(back=True)
    left, right = st.columns([1.15, .85], gap="large")
    with left:
        st.markdown(f'<div class="detail-title">{m["title"]}</div><div class="detail-summary">{m["summary"]}</div>', unsafe_allow_html=True)
        st.write("")
        st.markdown("#### 지금 놓인 상황")
        st.markdown(f'<div class="info-panel">{m["situation"]}</div>', unsafe_allow_html=True)
        st.write("")
        st.markdown("#### 이번 연습에서 완성할 것")
        for i, goal in enumerate(m["goals"], 1):
            st.markdown(f'<div class="goal-row"><div class="goal-no">{i}</div><div>{goal}</div></div>', unsafe_allow_html=True)
    with right:
        st.markdown("#### 기본 조건")
        for x in m["constraints"]:
            st.markdown(f"- {x}")
        st.markdown("---")
        st.markdown("#### 진행 방식")
        st.markdown("AI와 자유롭게 대화합니다. 대화 중 **3개의 새로운 상황**이 순서대로 열립니다. 마지막에는 AI 답변을 복사하는 대신, 오른쪽 결과 영역에서 직접 최종안을 정리합니다.")
        st.markdown("---")
        if not get_api_key():
            st.warning("실제 훈련을 시작하려면 서버의 OPENAI_API_KEY 설정이 필요합니다.")
        if st.button("훈련 시작", type="primary", use_container_width=True, disabled=not bool(get_api_key())):
            start_training(m)


def start_training(m: Dict[str, Any]):
    st.session_state.messages = []
    st.session_state.revealed_events = []
    st.session_state.event_index = 0
    st.session_state.outputs = {}
    st.session_state.draft_message = ""
    with st.spinner("이번 도전의 상황을 구성하고 있어요..."):
        try:
            plan = create_training_plan(get_api_key(), get_model(), m, st.session_state.attempt_no)
        except Exception as exc:
            st.error(f"Luna에서 훈련 상황을 만드는 중 오류가 발생했습니다: {exc}")
            return
    st.session_state.training_plan = plan
    st.session_state.messages = [{"role": "assistant", "content": plan["opening_message"]}]
    st.session_state.page = "workspace"
    st.rerun()


def reveal_next_event():
    plan = st.session_state.training_plan or {}
    events = plan.get("events", [])
    idx = st.session_state.event_index
    if idx < len(events):
        event = events[idx]
        st.session_state.revealed_events.append(event)
        st.session_state.event_index += 1
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"**새로운 상황 — {event['title']}**\n\n{event['situation']}\n\n**지금 해결할 것:** {event['task']}"
        })
        st.rerun()


def send_message(m: Dict[str, Any]):
    prompt = st.session_state.get("draft_message", "").strip()
    if not prompt:
        return
    st.session_state.messages.append({"role": "user", "content": prompt})
    # draft_message는 이미 이 실행에서 text_area 위젯으로 생성된 상태이므로
    # 여기서 직접 값을 바꾸면 StreamlitWidgetAlreadyInstantiatedError가 발생한다.
    # 다음 rerun에서 위젯이 만들어지기 전에 비우도록 플래그만 남긴다.
    st.session_state["_clear_draft_message"] = True
    with st.spinner("Luna가 생각하고 있어요..."):
        try:
            answer = chat_reply(get_api_key(), get_model(), m, st.session_state.revealed_events, st.session_state.messages)
            st.session_state.messages.append({"role": "assistant", "content": answer})
        except Exception as exc:
            st.session_state.messages.append({"role": "assistant", "content": f"응답을 불러오지 못했어요: {exc}"})
    st.rerun()


def workspace_page():
    m = selected_mission()
    if not st.session_state.training_plan:
        st.session_state.page = "detail"
        st.rerun()
    render_brand()
    user_turns = sum(1 for x in st.session_state.messages if x["role"] == "user")
    unlocked = st.session_state.event_index
    phase_index = min(unlocked, 3)
    phases = ["기본 상황", "변수 1", "변수 2", "변수 3", "최종 정리"]
    st.markdown(f'<div class="workspace-head"><div><div class="workspace-title">{m["title"]}</div><div class="phase-wrap">' + ''.join(f'<span class="phase {"phase-on" if i <= phase_index else ""}">{p}</span>' for i,p in enumerate(phases)) + '</div></div></div>', unsafe_allow_html=True)

    left, right = st.columns([1.12, .88], gap="large")
    with left:
        st.markdown('<div class="panel-title">AI와 협업하기</div>', unsafe_allow_html=True)
        # send_message()에서 남긴 플래그를 다음 실행에서 처리한다.
        # 반드시 text_area가 생성되기 전에 session_state 값을 변경해야 한다.
        if st.session_state.get("_clear_draft_message", False):
            st.session_state["draft_message"] = ""
            st.session_state["_clear_draft_message"] = False
        with st.container(height=520, border=False):
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
        st.text_area("메시지", key="draft_message", placeholder="Luna에게 요청하거나, 답변을 검토하고 다음 지시를 내려보세요.", height=92, label_visibility="collapsed")
        send_col, event_col = st.columns([1.3,1])
        if send_col.button("Luna에게 보내기", type="primary", use_container_width=True):
            send_message(m)
        plan_events = (st.session_state.training_plan or {}).get("events", [])
        can_open = user_turns >= max(1, st.session_state.event_index + 1) and st.session_state.event_index < len(plan_events)
        if event_col.button(
            f"새 상황 열기 ({st.session_state.event_index+1}/3)" if st.session_state.event_index < 3 else "새 상황 모두 확인",
            use_container_width=True,
            disabled=not can_open,
        ):
            reveal_next_event()
        if st.session_state.revealed_events:
            e = st.session_state.revealed_events[-1]
            st.markdown(f'<div class="branch-card"><div class="branch-kicker">CURRENT CHALLENGE</div><div class="branch-title">{e["title"]}</div><div class="branch-copy">{e["situation"]}<br><b>{e["task"]}</b></div></div>', unsafe_allow_html=True)
        else:
            st.caption("AI와 한 번 이상 대화하면 첫 번째 새로운 상황을 열 수 있어요.")

    with right:
        st.markdown('<div class="panel-title">나의 최종안</div>', unsafe_allow_html=True)
        with st.expander("현재 과제 조건 다시 보기"):
            st.write(m["situation"])
            for x in m["constraints"]:
                st.write(f"• {x}")
        for key, label, placeholder in m["deliverable"]:
            widget_key = f"out_{m['id']}_{st.session_state.attempt_no}_{key}"
            value = st.text_area(label, value=st.session_state.outputs.get(key, ""), placeholder=placeholder, height=112, key=widget_key)
            st.session_state.outputs[key] = value

    st.write("")
    filled = sum(bool(v.strip()) for v in st.session_state.outputs.values())
    st.markdown(f'<div class="progress-row"><span class="progress-pill">대화 {user_turns}회</span><span class="progress-pill">새 상황 {len(st.session_state.revealed_events)}/3</span><span class="progress-pill">최종안 {filled}/{len(m["deliverable"])}</span></div>', unsafe_allow_html=True)
    a,b,c = st.columns([1,1,1.2])
    if a.button("← 과제 설명", use_container_width=True):
        st.session_state.page = "detail"
        st.rerun()
    if b.button("처음부터 다시", use_container_width=True):
        start_training(m)
    submit_ready = user_turns >= 1 and filled >= 1
    if c.button("분석하고 결과 보기", type="primary", use_container_width=True, disabled=not submit_ready):
        submit_training(m)


def submit_training(m: Dict[str, Any]):
    with st.spinner("대화 방식과 최종안을 분석하고 있어요..."):
        try:
            result = evaluate(get_api_key(), get_model(), m, st.session_state.revealed_events, st.session_state.messages, st.session_state.outputs)
        except Exception as exc:
            st.error(f"평가 중 오류가 발생했습니다: {exc}")
            return
    hist = histories(m["id"])
    base_profile = hist[-1]["profile"] if hist else st.session_state.baseline
    profile = update_profile(base_profile, result)
    hist.append({
        "attempt_no": st.session_state.attempt_no,
        "result": result,
        "overall": overall_score(result),
        "profile": profile,
        "messages": deepcopy(st.session_state.messages),
        "events": deepcopy(st.session_state.revealed_events),
        "outputs": deepcopy(st.session_state.outputs),
    })
    # 유저별 영구 기록: 현재 미션의 마지막 수행만 저장합니다.
    account = st.session_state.get('auth_user')
    if account:
        store.save_training(account['user_id'], m['id'], hist[-1])
    st.session_state.page = "result"
    st.rerun()


def radar(
    profile: Dict[str, int],
    comparison: Dict[str, int] | None = None,
    current_label: str = "이번 수행 반영 후",
    comparison_label: str = "사전진단 프로필",
) -> go.Figure:
    labels = [ABILITY_META[k]["label"] for k in ABILITY_ORDER]
    theta = labels + [labels[0]]
    fig = go.Figure()
    if comparison:
        vals = [comparison[k] for k in ABILITY_ORDER]
        fig.add_trace(go.Scatterpolar(
            r=vals+[vals[0]], theta=theta, fill="toself", name=comparison_label,
            line=dict(color="#A6A9B6", width=2), fillcolor="rgba(166,169,182,.08)",
            hovertemplate="%{theta}: %{r}점<extra>"+comparison_label+"</extra>",
        ))
    vals = [profile[k] for k in ABILITY_ORDER]
    fig.add_trace(go.Scatterpolar(
        r=vals+[vals[0]], theta=theta, fill="toself", name=current_label,
        line=dict(color=PRIMARY, width=3), fillcolor="rgba(35,137,84,.16)",
        hovertemplate="%{theta}: %{r}점<extra>"+current_label+"</extra>",
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="white",
            radialaxis=dict(visible=True, range=[0,100], tickvals=[20,40,60,80,100], tickfont=dict(size=9, color="#9B9EAA"), gridcolor="#ECEEF4"),
            angularaxis=dict(gridcolor="#E6E8EF", tickfont=dict(size=12, color="#404657")),
        ),
        paper_bgcolor="white", plot_bgcolor="white", showlegend=True, height=500,
        margin=dict(l=80,r=80,t=60,b=40),
        legend=dict(orientation="h", y=1.11, x=.02, font=dict(size=12, color="#4B5262")),
    )
    return fig


def result_page():
    m = selected_mission()
    hist = histories(m["id"])
    cur = hist[-1]
    prev = hist[-2] if len(hist) >= 2 else None
    render_brand()

    st.markdown(
        f'<div class="section-title">{m["title"]} · 수행 분석</div>'
        '<div class="section-copy">여행 계획 자체의 완성도보다, AI를 어떤 방식으로 활용했는지를 평가합니다.</div>',
        unsafe_allow_html=True,
    )

    scores = all_ability_scores(cur["result"])
    assessed_keys = [k for k in ABILITY_ORDER if scores[k] is not None]
    assessed_labels = [ABILITY_META[k]["label"] for k in assessed_keys]

    # 첫 도전에서는 실제 사전진단을 아직 연결하지 않았으므로 현재 프로토타입의 샘플 프로필과 비교한다.
    if prev:
        comparison_profile = prev["profile"]
        comparison_label = "이전 도전"
        current_label = "이번 도전 반영 후"
    else:
        comparison_profile = st.session_state.baseline
        comparison_label = "사전진단 프로필" if st.session_state.get("diagnosis_baseline_is_real") else "사전진단 프로필 (현재 샘플)"
        current_label = "이번 수행 반영 후"

    top_left, top_right = st.columns([.72, 1.28], gap="large")
    with top_left:
        st.markdown("### 이번 수행 점수")
        st.markdown(
            f'<div class="result-score">{cur["overall"]}<span style="font-size:20px;letter-spacing:0">점</span></div>',
            unsafe_allow_html=True,
        )
        if prev:
            delta = cur["overall"] - prev["overall"]
            st.markdown(f'<div class="result-sub">이전 도전의 수행 점수보다 <b>{delta:+d}점</b></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="result-sub">첫 번째 도전입니다.</div>', unsafe_allow_html=True)

        st.info(
            f"이번 점수는 **{len(assessed_keys)}개 평가 역량의 평균**입니다. "
            "이번 미션에서 관찰하지 않은 역량은 0점으로 처리하지 않고 계산에서 제외합니다."
        )
        if assessed_labels:
            st.caption("이번 미션 평가 역량 · " + " · ".join(assessed_labels))

        st.write("")
        for key in ABILITY_ORDER:
            label = ABILITY_META[key]["label"]
            if scores[key] is None:
                retained = cur["profile"][key]
                st.markdown(
                    f'<div style="margin:12px 0 2px;color:#9AA0AE;font-size:14px;">'
                    f'{label} · <b>미평가</b> <span style="font-size:12px;">(프로필 {retained}점 유지)</span></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.progress(scores[key] / 100, text=f"{label}  {scores[key]}점")

        with st.expander("점수는 어떻게 계산되나요?"):
            st.markdown(
                "각 역량은 **3개의 세부 행동**을 0~4점으로 평가합니다. "
                "세부 점수의 합을 100점 척도로 환산하고, 이번 미션에서 실제 평가된 역량만 평균해 수행 점수를 계산합니다."
            )
            st.code("역량 점수 = (세부점수 합 ÷ 12) × 100\n수행 점수 = 평가된 역량 점수들의 평균", language="text")

    with top_right:
        st.markdown("### 현재 AI 역량 프로필")
        st.caption(
            "육각형은 6개 역량의 전체 프로필입니다. 이번 미션에서 평가되지 않은 축은 이전 프로필 값을 그대로 유지합니다."
        )
        st.plotly_chart(
            radar(
                cur["profile"],
                comparison_profile,
                current_label=current_label,
                comparison_label=comparison_label,
            ),
            use_container_width=True,
            config={"displayModeBar":False},
        )
        if not prev and not st.session_state.get("diagnosis_baseline_is_real"):
            st.caption("※ 회색 기준 점수는 샘플입니다. 사전진단(test.py)을 완료하면 6개 실제 역량 점수로 대체됩니다.")

    strongest = strongest_assessed(cur["result"])
    weakest = weakest_assessed(cur["result"])
    f1,f2,f3 = st.columns(3, gap="medium")
    with f1:
        st.markdown(f'<div class="feedback-card"><div class="feedback-label">STRENGTH</div><div class="feedback-title">{strongest[0] if strongest else "잘한 행동"}{" · "+str(strongest[1])+"점" if strongest else ""}</div><div class="small-muted">{cur["result"].get("strength_feedback","")}</div></div>', unsafe_allow_html=True)
    with f2:
        st.markdown(f'<div class="feedback-card"><div class="feedback-label">NEXT FOCUS</div><div class="feedback-title">{weakest[0] if weakest else "다음 보완점"}{" · "+str(weakest[1])+"점" if weakest else ""}</div><div class="small-muted">{cur["result"].get("improvement_feedback","")}</div></div>', unsafe_allow_html=True)
    with f3:
        st.markdown(f'<div class="feedback-card"><div class="feedback-label">NEXT ACTION</div><div class="feedback-title">다음 도전에서 한 가지</div><div class="small-muted">{cur["result"].get("next_action","")}</div></div>', unsafe_allow_html=True)

    if prev:
        growth = biggest_growth(prev["result"], cur["result"])
        if growth:
            st.success(f"가장 크게 달라진 영역: **{growth[0]} {growth[1]} → {growth[2]} ({growth[3]:+d})**")

    with st.expander("왜 이런 평가가 나왔는지 보기"):
        for key in ABILITY_ORDER:
            block = cur["result"].get(key, {})
            st.markdown(f"**{ABILITY_META[key]['label']}**")
            if not block.get("evaluated", False):
                st.caption("이번 미션의 평가 대상이 아니므로 점수를 새로 만들지 않았고, 프로필에서는 이전 값을 유지했습니다.")
                continue
            for ev in block.get("evidence", []):
                st.write(f"- {ev}")
            st.caption(block.get("feedback", ""))
        st.markdown("---")
        st.write("**파생 상황 대응**", cur["result"].get("event_feedback", ""))
        st.write("**최종안**", cur["result"].get("deliverable_feedback", ""))

    c1,c2,c3 = st.columns(3)
    if c1.button("다른 조건으로 다시 도전", type="primary", use_container_width=True):
        st.session_state.attempt_no = len(hist) + 1
        start_training(m)
    if c2.button("수행 기록 보기", use_container_width=True):
        st.session_state.page = "review"
        st.rerun()
    if c3.button("다른 상황 선택", use_container_width=True):
        st.session_state.page = "library"
        st.rerun()

def review_page():
    m = selected_mission()
    cur = histories(m["id"])[-1]
    render_brand(back=True)
    st.markdown(f"## {m['title']} · 수행 기록")
    l,r = st.columns(2, gap="large")
    with l:
        st.markdown("### AI와 나눈 대화")
        for msg in cur["messages"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
    with r:
        st.markdown("### 내가 작성한 최종안")
        for key,label,_ in m["deliverable"]:
            st.markdown(f"**{label}**")
            st.write(cur["outputs"].get(key, "") or "—")


def render_training():
    init_state()
    if not get_api_key():
        st.warning("GPT Luna API 키가 설정되지 않았습니다. `.streamlit/secrets.toml` 또는 Streamlit Cloud Secrets에 `OPENAI_API_KEY`를 등록하면 바로 사용할 수 있습니다.")
    if st.session_state.get("diagnosis_baseline_is_real"):
        st.caption("✓ 사전진단에서 받은 실제 6개 역량 점수가 훈련 결과 비교에 반영됩니다.")
    else:
        st.caption("진단을 아직 완료하지 않았어요. 현재 비교 그래프는 예시 점수이며, 사전진단 완료 후 실제 점수로 바뀝니다.")

    page = st.session_state.page
    if page == "library": library_page()
    elif page == "detail": detail_page()
    elif page == "workspace": workspace_page()
    elif page == "result": result_page()
    else: review_page()
