
import random
import re
import streamlit as st

st.set_page_config(
    page_title="AI 활용 사전진단",
    page_icon="🤖",
    layout="centered",
)

# =========================================================
# 0. 디자인
# =========================================================
st.markdown(
    """
    <style>
    .block-container {
        max-width: 900px;
        padding-top: 1.2rem;
        padding-bottom: 3rem;
    }

    .hero {
        border: 1px solid rgba(128,128,128,.18);
        border-radius: 18px;
        padding: 18px 20px;
        margin-bottom: 12px;
        background: rgba(128,128,128,.035);
    }

    .hero-kicker {
        font-size: .80rem;
        font-weight: 700;
        color: #6b7280;
        margin-bottom: 3px;
        letter-spacing: .04em;
    }

    .app-title {
        font-size: 1.9rem;
        font-weight: 800;
        letter-spacing: -0.04em;
        margin-bottom: 3px;
    }

    .app-subtitle {
        color: #6b7280;
        margin: 0;
    }

    .progress-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin: 2px 0 5px 0;
        color: #6b7280;
        font-size: .88rem;
    }

    .question-card {
        border: 1px solid rgba(128,128,128,.19);
        border-radius: 16px;
        padding: 14px 16px;
        margin: 8px 0 12px 0;
        background: rgba(128,128,128,.015);
    }

    .score-card {
        border: 1px solid rgba(128,128,128,.19);
        border-radius: 18px;
        padding: 18px;
        margin: 10px 0 16px 0;
        background: rgba(128,128,128,.02);
    }

    .result-title {
        font-size: 1.6rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        margin-bottom: .25rem;
    }

    .score-number {
        font-size: 1.55rem;
        font-weight: 800;
        margin-bottom: 2px;
    }

    .score-label {
        color: #6b7280;
        font-size: .84rem;
        margin-bottom: 7px;
    }

    div.stButton > button {
        width: 100%;
        height: auto !important;
        min-height: 52px;
        text-align: left;
        border-radius: 13px;
        padding: 11px 15px;
        white-space: normal !important;
        overflow: visible !important;
        margin-bottom: 5px;
    }

    div.stButton > button div[data-testid="stMarkdownContainer"] p {
        margin: 0;
        white-space: normal !important;
        overflow: visible !important;
        text-overflow: clip !important;
        display: block !important;
        -webkit-line-clamp: unset !important;
        word-break: keep-all;
        overflow-wrap: break-word;
        line-height: 1.45;
        text-align: left;
    }

    div[data-testid="stExpander"] {
        border-radius: 13px;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 14px;
    }

    textarea {
        border-radius: 12px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# 1. 평가 영역 / 공식 루브릭
# =========================================================
DOMAINS = {
    "agency": "인간의 주도권",
    "responsibility": "인간의 책임",
    "ethics": "윤리적 관점",
    "safety": "안전하고 책임 있는 사용",
    "ai_basics": "AI의 기초",
    "utilization": "활용 능력",
}

DOMAIN_TIPS = {
    "agency": "AI에게 결정을 넘기기보다, 내가 먼저 목적과 범위를 정한 뒤 필요한 부분에 AI를 활용해보세요.",
    "responsibility": "AI가 제시한 정보는 원자료·공식 출처를 확인하고, 중요한 최종 판단은 직접 내려보세요.",
    "ethics": "정확도뿐 아니라 편향, 차별, 포용성, 타인의 권리에 미치는 영향도 함께 살펴보세요.",
    "safety": "AI에 자료를 넣기 전에 개인을 식별할 수 있는 정보를 가리고, 작업에 꼭 필요한 정보만 남겨보세요.",
    "ai_basics": "AI가 자연스럽고 자신 있게 말하더라도 사실과 다른 내용을 만들 수 있다는 점을 기억하세요.",
    "utilization": "목적·맥락·조건·출력 형태를 제시하고, 첫 답변이 부족하면 부족한 점을 구체적으로 수정 요청해보세요.",
}

RUBRIC_SUMMARY = {
    "agency": "0점: 결정 위임 · 1점: AI가 탐색을 주도하고 사람은 선택 · 2점: 사람이 목적·범위를 먼저 정하고 AI를 보조적으로 활용",
    "responsibility": "선택 최대 1점 + 검증 이유 최대 1점. 원자료·공식 출처와 수치/맥락을 직접 확인할수록 높은 점수",
    "ethics": "선택 최대 1점 + 이유 최대 1점. 데이터·평가기준과 편향·차별의 연결을 구체적으로 볼수록 높은 점수",
    "safety": "개인 식별정보를 적절히 제거하고, 분석에 필요한 내용은 남길수록 높은 점수",
    "ai_basics": "오류 가능성 인식 최대 1점 + 실제 오류/검증 지점 발견 최대 1점",
    "utilization": "첫 프롬프트 최대 1점(목적·맥락·조건·출력형태 각 0.25) + 수정 요청 최대 1점",
}

# =========================================================
# 2. 상태
# =========================================================
def init_state():
    defaults = {
        "stage": 0,
        "answers": {},
        "option_orders": {},
        "editing_mode": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_state()

# =========================================================
# 3. 공통 유틸
# =========================================================
def normalize(text):
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def shuffled_once(key, items):
    if key not in st.session_state.option_orders:
        copied = list(items)
        random.shuffle(copied)
        st.session_state.option_orders[key] = copied
    return st.session_state.option_orders[key]


def set_stage(stage):
    st.session_state.stage = stage
    st.rerun()


def scenario_number(stage):
    if stage <= 1:
        return 1
    if stage in (2, 3):
        return 2
    if stage in (4, 5):
        return 3
    if stage == 6:
        return 4
    if stage in (7, 8):
        return 5
    if stage == 9:
        return 6
    if stage in (10, 11):
        return 7
    return 7


def diagnosis_complete():
    a = st.session_state.answers
    required = [
        "agency_choice",
        "responsibility_choice",
        "responsibility_reason",
        "ethics_choice",
        "ethics_reason",
        "safety_selected",
        "ai_basics_choice",
        "ai_basics_reason",
        "initial_prompt",
        "revision_decision",
    ]
    if not all(k in a and a[k] not in (None, "", []) for k in required):
        return False
    if a.get("revision_decision") == "revise":
        return bool(a.get("revision_prompt", "").strip())
    return True


def previous_stage(stage):
    mapping = {
        1: 0,
        2: 1,
        3: 2,
        4: 3,
        5: 4,
        6: 5,
        7: 6,
        8: 7,
        9: 8,
        10: 9,
        11: 10,
        12: 11 if st.session_state.answers.get("revision_decision") == "revise" else 10,
    }
    return mapping.get(stage)


def render_navigation():
    stage = st.session_state.stage
    if stage == 0 or stage == 13:
        return

    left, right = st.columns([1, 1])

    with left:
        prev = previous_stage(stage)
        if prev is not None and st.button("← 이전 단계", key=f"back_{stage}", use_container_width=True):
            set_stage(prev)

    with right:
        if st.session_state.editing_mode and diagnosis_complete():
            if st.button("수정 완료 · 결과로 돌아가기", key=f"return_result_{stage}", use_container_width=True):
                st.session_state.editing_mode = False
                set_stage(13)


def free_text_form(form_key, answer_key, placeholder, button_label="답변 저장하고 다음", height=95):
    current = st.session_state.answers.get(answer_key, "")
    with st.form(form_key, clear_on_submit=False):
        value = st.text_area(
            "답변",
            value=current,
            placeholder=placeholder,
            height=height,
            label_visibility="collapsed",
            key=f"{form_key}_widget",
        )
        submitted = st.form_submit_button(button_label, use_container_width=True)

    if submitted:
        cleaned = value.strip()
        if not cleaned:
            st.warning("답변을 입력해주세요.")
            return None
        return cleaned
    return None


# =========================================================
# 4. 채점 함수 - Scoring Rubric v2
# =========================================================
def score_responsibility_reason(text):
    """
    최대 1점
    0   : 검증 관점 없음
    0.5 : 출처/사실 확인 필요성을 일반적으로 인식
    1.0 : 원자료·공식 출처 + 실제 수치/조사 맥락 등을 직접 검증하려는 행동
    """
    t = normalize(text)
    if not t or t in {"없음", "없다", "모르겠다"}:
        return 0.0

    source = any(k in t for k in ["원자료", "원문", "공식", "보고서", "논문", "출처", "링크"])
    fact = any(k in t for k in ["수치", "통계", "조사", "표본", "연도", "맥락", "방법", "실제"])
    action = any(k in t for k in ["직접", "검색", "찾아", "들어가", "확인", "검증"])

    if sum([source, fact, action]) >= 2:
        return 1.0
    if source or fact or action:
        return 0.5
    return 0.0


def score_ethics_reason(text):
    """
    최대 1점
    0   : 효율/정확도만 언급
    0.5 : 공정성·편향 가능성을 일반적으로 인식
    1.0 : 데이터/기준이 특정 집단에 유리·불리한 결과를 낳을 수 있음을 구체적으로 연결
    """
    t = normalize(text)
    if not t:
        return 0.0

    fairness = any(k in t for k in ["편향", "차별", "공정", "불공정", "불리", "유리", "권리", "다양성", "포용"])
    mechanism = any(k in t for k in ["데이터", "학습", "기준", "과거", "출신", "학교", "성별", "연령", "배경", "집단"])

    if fairness and mechanism:
        return 1.0
    if fairness or mechanism:
        return 0.5
    return 0.0


def score_safety(selected):
    """
    최대 2점
    핵심 식별정보: 이름/전화번호/이메일
    0   : 수정 없이 사용
    0.5 : 핵심 식별정보는 못 가렸지만 위험 요소를 일부 인식
    1.0 : 핵심 식별정보 1개 제거
    1.5 : 핵심 식별정보 2개 제거
    2.0 : 핵심 식별정보 3개 제거
    인터뷰 내용까지 제거하면 분석 목적에 필요한 정보까지 없애므로 0.5 감점
    """
    if not selected:
        return 0.0
    selected = set(selected)

    if "수정 없이 사용" in selected:
        return 0.0

    pii = {"이름", "전화번호", "이메일"}
    removed = len(pii.intersection(selected))

    if removed == 0:
        score = 0.5 if selected else 0.0
    elif removed == 1:
        score = 1.0
    elif removed == 2:
        score = 1.5
    else:
        score = 2.0

    if "인터뷰 내용" in selected:
        score -= 0.5

    return max(0.0, min(2.0, score))


def score_ai_basics_reason(text):
    """
    최대 1점
    0    : 오류/검증 지점 없음
    0.5  : 일반적으로 사실 확인 필요성을 언급
    0.75 : '분야' 등 구체적 지점을 의심
    1.0  : 수학 노벨상 오류를 직접 발견
    """
    t = normalize(text)
    if not t or t in {"없음", "없다"}:
        return 0.0

    explicit_math = (
        ("수학" in t and ("노벨" in t or "상" in t or "분야" in t))
        or "수학상" in t
    )
    specific_field = any(k in t for k in ["분야", "6개", "수여 분야", "1901"])
    verify = any(k in t for k in ["확인", "검증", "출처", "사실", "틀", "오류", "의심"])

    if explicit_math:
        return 1.0
    if specific_field and verify:
        return 0.75
    if verify:
        return 0.5
    return 0.0


def score_initial_prompt(text):
    """
    최대 1점: 4요소 x 0.25
    목적 / 맥락·대상 / 조건 / 출력형태
    """
    t = normalize(text)
    score = 0.0

    if any(k in t for k in ["발표", "5분", "과제", "준비", "설명", "정리"]):
        score += 0.25

    if any(k in t for k in ["대학", "수업", "학생", "비전공", "청중", "교수", "초보"]):
        score += 0.25

    if any(k in t for k in ["장점", "단점", "한계", "사례", "각각", "분량", "시간", "근거"]):
        score += 0.25

    if any(k in t for k in ["슬라이드", "목차", "표", "대본", "구성", "항목", "bullet", "불릿"]):
        score += 0.25

    return min(1.0, score)


def score_revision_prompt(text):
    """
    최대 1점
    0    : 수정 없음
    0.25 : '더 자세히', '다시' 등 모호한 수정
    0.5  : 구체적 문제 또는 새 조건 중 하나 제시
    0.75 : 문제점 + 새 조건/형식 제시
    1.0  : 문제점을 명확히 짚고 2개 이상의 구체 조건으로 재설계
    """
    t = normalize(text)
    if not t:
        return 0.0

    vague = any(k in t for k in ["더 자세", "다시 해", "더 잘", "더 좋", "길게"])

    problem = any(
        k in t
        for k in ["일반적", "뻔", "추상", "부족", "중복", "어렵", "너무 짧", "구체적이지", "사례가 없"]
    )

    dimensions = 0
    if any(k in t for k in ["대학생", "비전공", "청중", "초보", "대상"]):
        dimensions += 1
    if any(k in t for k in ["사례", "장점", "한계", "각각", "근거", "비교"]):
        dimensions += 1
    if any(k in t for k in ["슬라이드", "대본", "표", "목차", "구성", "형식"]):
        dimensions += 1
    if any(k in t for k in ["5분", "5장", "3개", "분량", "시간"]):
        dimensions += 1

    if problem and dimensions >= 2:
        return 1.0
    if problem and dimensions >= 1:
        return 0.75
    if dimensions >= 1 or problem:
        return 0.5
    if vague:
        return 0.25
    return 0.0


def calculate_scores():
    a = st.session_state.answers

    # 1. 인간의 주도권: 선택 자체가 0~2점
    agency_map = {
        "내가 관심 있는 분야를 먼저 정하고, 그 안에서 발표 주제를 같이 찾아본다.": 2.0,
        "요즘 발표하기 좋은 주제를 몇 개 추천해달라고 한다.": 1.0,
        "다른 학생들이 많이 선택하는 발표 주제가 무엇인지 물어본다.": 1.0,
        "과제 조건을 알려주고 가장 높은 점수를 받을 만한 주제를 하나 골라달라고 한다.": 0.5,
    }

    # 2. 인간의 책임: 선택 최대 1 + 꼬리질문 최대 1
    responsibility_choice_map = {
        "발표자료에 우선 넣고, 시간이 되면 나중에 확인한다.": 0.0,
        "다른 AI에게 같은 내용을 물어보고 답이 같은지 비교한다.": 0.25,
        "AI에게 해당 조사의 링크나 출처를 요청한다.": 0.5,
        "UNESCO 사이트나 원자료를 직접 찾아 조사와 수치를 확인한다.": 1.0,
    }

    # 3. 윤리적 관점: 선택 최대 1 + 꼬리질문 최대 1
    ethics_choice_map = {
        "사람이 직접 평가했을 때보다 시간이 얼마나 단축됐는지 확인한다.": 0.0,
        "AI 평가를 도입한 뒤 최종 합격률이 얼마나 변했는지 확인한다.": 0.25,
        "AI의 평가 정확도가 몇 %인지 확인한다.": 0.5,
        "AI가 어떤 데이터와 기준을 바탕으로 지원자를 평가했는지 확인한다.": 1.0,
    }

    # 5. AI의 기초: 선택 최대 1 + 꼬리질문 최대 1
    basics_choice_map = {
        "구체적인 연도와 분야까지 제시했으므로 신뢰할 수 있다고 생각한다.": 0.0,
        "유명한 주제이므로 AI도 정확히 알고 있을 가능성이 높다고 생각한다.": 0.25,
        "표현을 조금 더 자세하게 만들어달라고 요청한다.": 0.25,
        "자연스럽게 설명했지만 사실관계는 따로 확인할 수 있다고 생각한다.": 1.0,
    }

    scores = {
        "agency": agency_map.get(a.get("agency_choice"), 0.0),
        "responsibility": min(
            2.0,
            responsibility_choice_map.get(a.get("responsibility_choice"), 0.0)
            + score_responsibility_reason(a.get("responsibility_reason", "")),
        ),
        "ethics": min(
            2.0,
            ethics_choice_map.get(a.get("ethics_choice"), 0.0)
            + score_ethics_reason(a.get("ethics_reason", "")),
        ),
        "safety": score_safety(a.get("safety_selected", [])),
        "ai_basics": min(
            2.0,
            basics_choice_map.get(a.get("ai_basics_choice"), 0.0)
            + score_ai_basics_reason(a.get("ai_basics_reason", "")),
        ),
        "utilization": min(
            2.0,
            score_initial_prompt(a.get("initial_prompt", ""))
            + (
                score_revision_prompt(a.get("revision_prompt", ""))
                if a.get("revision_decision") == "revise"
                else 0.0
            ),
        ),
    }
    return scores


def get_level(scores):
    total = round(sum(scores.values()), 2)
    minimum = min(scores.values())

    if total >= 9.5 and minimum >= 1.0:
        return 4, "주도적 활용", total
    if total >= 6.5:
        return 3, "적용", total
    if total >= 3.5:
        return 2, "이해", total
    return 1, "탐색", total


# =========================================================
# 5. 이전 대화 / 현재 질문 표시
# =========================================================
def previous_response_sections():
    a = st.session_state.answers
    return [
        ("상황 1 · 발표 주제 정하기", [
            ("내 선택", a.get("agency_choice")),
        ]),
        ("상황 2 · AI가 제시한 통계 확인하기", [
            ("내 선택", a.get("responsibility_choice")),
            ("내가 확인하고 싶었던 점", a.get("responsibility_reason")),
        ]),
        ("상황 3 · AI 채용 평가 살펴보기", [
            ("내 선택", a.get("ethics_choice")),
            ("내가 확인하고 싶었던 문제", a.get("ethics_reason")),
        ]),
        ("상황 4 · 개인정보가 포함된 자료 다루기", [
            (
                "내가 제거하거나 가리기로 한 항목",
                ", ".join(a.get("safety_selected", []))
                if isinstance(a.get("safety_selected"), list)
                else a.get("safety_selected"),
            ),
        ]),
        ("상황 5 · AI 답변의 오류 가능성 판단하기", [
            ("내 선택", a.get("ai_basics_choice")),
            ("내가 확인하고 싶었던 부분", a.get("ai_basics_reason")),
        ]),
        ("상황 6 · 실제 프롬프트 작성하기", [
            ("내가 처음 작성한 프롬프트", a.get("initial_prompt")),
        ]),
        ("상황 7 · AI 답변을 그대로 쓸지 수정할지 결정하기", [
            (
                "내 선택",
                "이대로 사용하기"
                if a.get("revision_decision") == "use_as_is"
                else "한 번 더 요청하기"
                if a.get("revision_decision") == "revise"
                else None,
            ),
            ("내가 작성한 수정 요청", a.get("revision_prompt")),
        ]),
    ]


def render_previous_conversation(current_scenario):
    sections = previous_response_sections()
    previous = sections[: max(0, current_scenario - 1)]

    visible = []
    for title, items in previous:
        items = [(label, value) for label, value in items if value not in (None, "", [])]
        if items:
            visible.append((title, items))

    if not visible:
        return

    with st.expander("이전 대화 보기", expanded=False):
        for title, items in visible:
            st.markdown(f"#### {title}")
            for label, value in items:
                st.markdown(f"**{label}**")
                st.write(value)
            st.divider()


def question_card(markdown_text):
    with st.container(border=True):
        st.markdown(markdown_text)


def context_box(markdown_text, answer=None):
    st.caption("질문 맥락")
    with st.container(height=185, border=True):
        st.markdown(markdown_text)
        if answer:
            st.markdown("**내가 선택한 답변**")
            st.write(answer)


# =========================================================
# 6. 상단
# =========================================================
stage = st.session_state.stage

if stage == 0:
    progress = 0.0
    status_left = "시작 전"
    status_right = "약 5~8분"
elif stage in range(1, 12):
    n = scenario_number(stage)
    progress = n / 7
    status_left = f"상황 {n} / 7"
    status_right = f"{int(progress * 100)}% 진행"
else:
    progress = 1.0
    status_left = "진단 완료"
    status_right = "100%"

st.markdown(
    """
    <div class="hero">
        <div class="hero-kicker">AI LITERACY CHECK</div>
        <div class="app-title">AI 활용 사전진단</div>
        <div class="app-subtitle">짧은 상황을 해결하며 나의 AI 활용 방식을 확인해보세요.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f'<div class="progress-row"><span>{status_left}</span><span>{status_right}</span></div>',
    unsafe_allow_html=True,
)
st.progress(progress)

render_navigation()

# =========================================================
# 7. 진단 단계
# =========================================================

# Stage 0: 시작
if stage == 0:
    question_card(
        """
        **진단 방식**

        - 실제 AI 사용 상황이 차례로 제시됩니다.
        - 일부는 선택형, 일부는 짧은 자유응답입니다.
        - 중간에는 점수나 정답을 보여주지 않습니다.
        - 답변을 잘못 입력했다면 언제든 **이전 단계**로 돌아가 수정할 수 있습니다.
        """
    )

    if st.button("진단 시작하기 →", use_container_width=True):
        set_stage(1)


# Stage 1: 인간의 주도권
elif stage == 1:
    render_previous_conversation(1)

    question_card(
        """
        ### 상황 1
        교수님이 **자유주제로 5분 발표**를 준비하라고 했습니다. 아직 주제를 정하지 못했습니다.

        **AI를 사용한다면 가장 먼저 무엇을 하시겠어요?**
        """
    )

    options = [
        "요즘 발표하기 좋은 주제를 몇 개 추천해달라고 한다.",
        "내가 관심 있는 분야를 먼저 정하고, 그 안에서 발표 주제를 같이 찾아본다.",
        "과제 조건을 알려주고 가장 높은 점수를 받을 만한 주제를 하나 골라달라고 한다.",
        "다른 학생들이 많이 선택하는 발표 주제가 무엇인지 물어본다.",
    ]

    for idx, label in enumerate(shuffled_once("agency", options)):
        if st.button(label, key=f"agency_{idx}", use_container_width=True):
            st.session_state.answers["agency_choice"] = label
            set_stage(2)


# Stage 2: 인간의 책임 - 선택
elif stage == 2:
    render_previous_conversation(2)

    question_card(
        """
        ### 상황 2
        발표를 준비하던 중 AI가 이런 정보를 알려줬습니다.

        > **“2025년 조사에 따르면 대학생의 82.4%가 생성형 AI를 매일 사용합니다. 이 조사는 UNESCO가 실시했습니다.”**

        발표 내용에 잘 맞아 보입니다. **다음으로 무엇을 하시겠어요?**
        """
    )

    options = [
        "발표자료에 우선 넣고, 시간이 되면 나중에 확인한다.",
        "AI에게 해당 조사의 링크나 출처를 요청한다.",
        "UNESCO 사이트나 원자료를 직접 찾아 조사와 수치를 확인한다.",
        "다른 AI에게 같은 내용을 물어보고 답이 같은지 비교한다.",
    ]

    for idx, label in enumerate(shuffled_once("responsibility", options)):
        if st.button(label, key=f"responsibility_{idx}", use_container_width=True):
            st.session_state.answers["responsibility_choice"] = label
            set_stage(3)


# Stage 3: 인간의 책임 - 꼬리질문
elif stage == 3:
    render_previous_conversation(2)

    context_box(
        """
        **상황 2**

        AI가 “2025년 대학생의 82.4%가 생성형 AI를 매일 사용하며 UNESCO 조사 결과”라고 알려줬습니다.
        """,
        st.session_state.answers.get("responsibility_choice"),
    )

    st.markdown("#### 확인한다면 어떤 점을 가장 확인하고 싶은가요?")

    text = free_text_form(
        "responsibility_reason_form",
        "responsibility_reason",
        "예: 실제 조사인지, 수치가 맞는지, 원출처가 무엇인지...",
    )
    if text is not None:
        st.session_state.answers["responsibility_reason"] = text
        set_stage(4)


# Stage 4: 윤리적 관점 - 선택
elif stage == 4:
    render_previous_conversation(3)

    question_card(
        """
        ### 상황 3
        한 회사가 AI로 신입사원 지원서를 자동 평가했습니다.

        결과를 확인해보니 **특정 대학 출신 지원자들이 계속 높은 점수**를 받고 있었습니다.
        담당자는 “AI가 일관된 기준으로 평가하기 때문에 사람보다 공정하다”고 말합니다.

        **이 상황에서 가장 먼저 확인하고 싶은 것은 무엇인가요?**
        """
    )

    options = [
        "AI의 평가 정확도가 몇 %인지 확인한다.",
        "사람이 직접 평가했을 때보다 시간이 얼마나 단축됐는지 확인한다.",
        "AI가 어떤 데이터와 기준을 바탕으로 지원자를 평가했는지 확인한다.",
        "AI 평가를 도입한 뒤 최종 합격률이 얼마나 변했는지 확인한다.",
    ]

    for idx, label in enumerate(shuffled_once("ethics", options)):
        if st.button(label, key=f"ethics_{idx}", use_container_width=True):
            st.session_state.answers["ethics_choice"] = label
            set_stage(5)


# Stage 5: 윤리적 관점 - 꼬리질문
elif stage == 5:
    render_previous_conversation(3)

    context_box(
        """
        **상황 3**

        AI 채용 평가에서 특정 대학 출신 지원자들이 계속 높은 점수를 받고 있습니다.
        """,
        st.session_state.answers.get("ethics_choice"),
    )

    st.markdown("#### 그 자료나 기준을 확인해서 어떤 문제가 있는지 보고 싶은가요?")

    text = free_text_form(
        "ethics_reason_form",
        "ethics_reason",
        "예: 특정 집단에 유리하거나 불리한 기준이 들어갔는지...",
    )
    if text is not None:
        st.session_state.answers["ethics_reason"] = text
        set_stage(6)


# Stage 6: 안전한 사용
elif stage == 6:
    render_previous_conversation(4)

    question_card(
        """
        ### 상황 4
        팀원 인터뷰 내용을 AI로 요약하려고 합니다.

        ```text
        김민수 / 경제학과 / 010-1234-5678
        “AI를 과제를 정리할 때 자주 사용한다.”

        박지영 / 컴퓨터공학과 / jihyeong@email.com
        “코딩할 때 주로 사용한다.”
        ```

        **AI에게 전달하기 전에 제거하거나 가리고 싶은 항목을 모두 선택해주세요.**
        """
    )

    options = ["이름", "학과", "전화번호", "이메일", "인터뷰 내용", "수정 없이 사용"]
    default = st.session_state.answers.get("safety_selected", [])

    selected = st.multiselect(
        "제거하거나 가릴 항목",
        options,
        default=default,
        placeholder="여러 개 선택할 수 있어요.",
        key="safety_multiselect",
    )

    if st.button("이 선택으로 저장하고 다음 →", use_container_width=True):
        if not selected:
            st.warning("최소 한 가지를 선택해주세요.")
        elif "수정 없이 사용" in selected and len(selected) > 1:
            st.warning("'수정 없이 사용'은 다른 항목과 함께 선택할 수 없어요.")
        else:
            st.session_state.answers["safety_selected"] = selected
            set_stage(7)


# Stage 7: AI의 기초 - 선택
elif stage == 7:
    render_previous_conversation(5)

    question_card(
        """
        ### 상황 5
        AI가 다음과 같이 답했습니다.

        > **“노벨상은 1901년부터 수학·물리학·화학·생리의학·문학·평화의 6개 분야에서 수여되었습니다.”**

        이 설명을 받은 뒤 **가장 가까운 생각**은 무엇인가요?
        """
    )

    options = [
        "구체적인 연도와 분야까지 제시했으므로 신뢰할 수 있다고 생각한다.",
        "자연스럽게 설명했지만 사실관계는 따로 확인할 수 있다고 생각한다.",
        "유명한 주제이므로 AI도 정확히 알고 있을 가능성이 높다고 생각한다.",
        "표현을 조금 더 자세하게 만들어달라고 요청한다.",
    ]

    for idx, label in enumerate(shuffled_once("ai_basics", options)):
        if st.button(label, key=f"basics_{idx}", use_container_width=True):
            st.session_state.answers["ai_basics_choice"] = label
            set_stage(8)


# Stage 8: AI의 기초 - 꼬리질문
elif stage == 8:
    render_previous_conversation(5)

    context_box(
        """
        **상황 5**

        AI가 “노벨상은 1901년부터 수학·물리학·화학·생리의학·문학·평화의 6개 분야에서 수여되었다”고 답했습니다.
        """,
        st.session_state.answers.get("ai_basics_choice"),
    )

    st.markdown("#### 이 답변에서 확인하고 싶은 부분이나 이상하다고 느껴지는 부분이 있나요?")

    text = free_text_form(
        "basics_reason_form",
        "ai_basics_reason",
        "없다면 '없음'이라고 입력해도 괜찮아요.",
    )
    if text is not None:
        st.session_state.answers["ai_basics_reason"] = text
        set_stage(9)


# Stage 9: 활용 능력 - 첫 프롬프트
elif stage == 9:
    render_previous_conversation(6)

    question_card(
        """
        ### 상황 6 · 실제로 AI에게 요청해보기
        대학 수업에서 **‘생성형 AI의 장점과 한계’를 주제로 5분 발표**를 해야 합니다.

        AI에게 도움을 요청한다면, **평소처럼 실제로 입력할 문장**을 작성해주세요.
        """
    )

    text = free_text_form(
        "initial_prompt_form",
        "initial_prompt",
        "AI에게 실제로 요청하듯 작성해주세요.",
        "프롬프트 저장하고 다음 →",
        height=120,
    )
    if text is not None:
        st.session_state.answers["initial_prompt"] = text
        set_stage(10)


# Stage 10: 활용 능력 - 수정 여부
elif stage == 10:
    render_previous_conversation(7)

    question_card(
        """
        ### 상황 7
        AI가 방금 이렇게 답했다고 가정해볼게요.

        > 생성형 AI의 장점은 **업무 효율 향상, 정보 접근성 향상, 창의적인 아이디어 제공**입니다.  
        > 반면 한계로는 **잘못된 정보 생성, 개인정보 문제, 지나친 의존**이 있습니다.  
        > 발표에서는 이러한 장점과 한계를 균형 있게 설명하면 좋습니다.

        이 답변을 실제 발표 준비에 사용한다고 생각해보세요.

        **이대로 사용하시겠어요, 아니면 AI에게 한 번 더 요청하시겠어요?**
        """
    )

    if st.button("이대로 사용하기", use_container_width=True):
        st.session_state.answers["revision_decision"] = "use_as_is"
        st.session_state.answers.pop("revision_prompt", None)
        set_stage(12)

    if st.button("한 번 더 요청하기", use_container_width=True):
        st.session_state.answers["revision_decision"] = "revise"
        set_stage(11)


# Stage 11: 활용 능력 - 수정 프롬프트
elif stage == 11:
    render_previous_conversation(7)

    context_box(
        """
        **상황 7**

        AI의 답변은 장점과 한계를 나열했지만, 발표에 바로 쓰기에는 다소 일반적인 내용입니다.
        """,
        "한 번 더 요청하기",
    )

    st.markdown("#### 어떤 점을 바꾸고 싶은지 AI에게 직접 수정 요청을 해보세요.")

    text = free_text_form(
        "revision_prompt_form",
        "revision_prompt",
        "예: 부족했던 점과 원하는 조건을 함께 적어보세요.",
        "수정 요청 저장 →",
        height=110,
    )
    if text is not None:
        st.session_state.answers["revision_prompt"] = text
        set_stage(12)


# Stage 12: 완료 확인
elif stage == 12:
    render_previous_conversation(8)

    question_card(
        """
        ### 진단 응답이 모두 저장되었습니다
        마지막 답변까지 반영했어요.

        결과를 보기 전에 답변을 다시 확인하거나, **이전 단계**로 돌아가 수정할 수 있습니다.
        """
    )

    if diagnosis_complete():
        if st.button("진단 결과 보기 →", use_container_width=True):
            st.session_state.editing_mode = False
            set_stage(13)
    else:
        st.warning("아직 저장되지 않은 답변이 있어요. 이전 단계로 돌아가 확인해주세요.")


# Stage 13: 결과
elif stage == 13:
    scores = calculate_scores()
    level_num, level_name, total = get_level(scores)

    level_desc = {
        1: "AI 활용에 필요한 기본 개념과 사용 원칙을 익혀가는 단계입니다.",
        2: "AI의 역할과 한계를 이해하고, 책임 있는 사용 원칙을 인식하고 있는 단계입니다.",
        3: "이해한 원칙을 실제 AI 사용 상황에 비교적 잘 적용할 수 있는 단계입니다.",
        4: "목적·책임·윤리·안전·AI 이해·활용을 전반적으로 고려하며 주도적으로 AI를 활용하는 단계입니다.",
    }

    st.markdown(
        f"""
        <div class="score-card">
            <div class="result-title">Level {level_num} · {level_name}</div>
            <div>{level_desc[level_num]}</div>
            <br>
            <b>총 역량 점수: {total:.2f} / 12</b>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### 한눈에 보는 6개 역량")
    domain_items = list(DOMAINS.items())

    for row_start in range(0, 6, 3):
        cols = st.columns(3)
        for offset, (key, label) in enumerate(domain_items[row_start:row_start + 3]):
            score = scores[key]
            with cols[offset]:
                with st.container(border=True):
                    st.markdown(f"**{label}**")
                    st.markdown(f'<div class="score-number">{score:.2f}</div>', unsafe_allow_html=True)
                    st.markdown('<div class="score-label">2점 만점</div>', unsafe_allow_html=True)
                    st.progress(score / 2)

    sorted_scores = sorted(scores.items(), key=lambda x: x[1])
    weakest = sorted_scores[:2]
    strongest = sorted_scores[-2:][::-1]

    left, right = st.columns(2)
    with left:
        st.markdown("### 강점")
        for key, score in strongest:
            st.success(f"**{DOMAINS[key]}**\n\n현재 진단에서 상대적으로 강하게 나타났어요.")

    with right:
        st.markdown("### 우선 연습")
        for key, score in weakest:
            st.info(f"**{DOMAINS[key]}**\n\n{DOMAIN_TIPS[key]}")

    with st.expander("채점 기준 보기", expanded=False):
        st.caption("각 영역은 0~2점이며, 복합 문항은 하위 행동 점수를 합산합니다.")
        for key, label in DOMAINS.items():
            st.markdown(f"**{label}**")
            st.write(RUBRIC_SUMMARY[key])

    with st.expander("내 응답 다시 보기", expanded=False):
        for title, items in previous_response_sections():
            visible_items = [(label, value) for label, value in items if value not in (None, "", [])]
            if not visible_items:
                continue

            with st.container(border=True):
                st.markdown(f"#### {title}")
                for label, value in visible_items:
                    st.markdown(f"**{label}**")
                    if isinstance(value, str) and len(value) > 70:
                        st.markdown(f"> {value}")
                    else:
                        st.write(value)

    st.markdown("### 답변 수정")
    st.caption("수정하고 싶은 상황을 선택하면 해당 문항으로 돌아갑니다. 기존 답변은 그대로 남아 있어 수정해서 다시 저장할 수 있어요.")

    edit_options = {
        "상황 1 · 발표 주제 정하기": 1,
        "상황 2 · AI 통계 확인하기": 2,
        "상황 3 · AI 채용 평가": 4,
        "상황 4 · 개인정보 자료 다루기": 6,
        "상황 5 · AI 오류 판단": 7,
        "상황 6 · 실제 프롬프트 작성": 9,
        "상황 7 · AI 답변 수정 여부": 10,
    }

    selected_edit = st.selectbox(
        "수정할 상황",
        list(edit_options.keys()),
        label_visibility="collapsed",
    )

    if st.button("선택한 답변 수정하기 ←", use_container_width=True):
        st.session_state.editing_mode = True
        set_stage(edit_options[selected_edit])

    if st.button("처음부터 다시 진단하기", use_container_width=True):
        for key in ["stage", "answers", "option_orders", "editing_mode"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
