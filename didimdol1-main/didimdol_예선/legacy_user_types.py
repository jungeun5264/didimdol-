"""디딤돌 AI 활용 *성향* 설문: 12개 문항, 6유형의 탐색적 분류.

이 점수는 기존 사전진단의 여섯 '역량' 점수와 별개입니다.
검증된 심리검사가 아니므로 성격/능력을 확정적으로 판정하지 않습니다.
"""
from __future__ import annotations

from dataclasses import dataclass

SURVEY_VERSION = 'type-survey-v1'

@dataclass(frozen=True)
class TypeInfo:
    name: str
    description: str
    tip: str


TYPES = {
    'planner': TypeInfo('목표설계형', 'AI를 사용하기 전에 목표와 조건을 구조화하는 경향', '요구사항을 간단한 체크리스트로 작성한 뒤 AI에 요청해보세요.'),
    'explorer': TypeInfo('탐색확장형', '가능한 선택지와 아이디어를 폭넓게 살피는 경향', '많은 아이디어 중 근거와 실행 가능성을 기준으로 추려보세요.'),
    'verifier': TypeInfo('검증중심형', 'AI 답변의 출처와 정확성을 확인하는 경향', '검증에 사용할 기준과 신뢰할 자료를 미리 정해보세요.'),
    'improver': TypeInfo('반복개선형', '초안을 비교하고 여러 번 다듬는 경향', '수정 전후 차이를 기록하며 개선 효과를 확인해보세요.'),
    'executor': TypeInfo('실행중심형', 'AI의 제안을 실제 행동 계획으로 연결하는 경향', '실행 단계별 완료 조건과 점검 시점을 정해보세요.'),
    'guardian': TypeInfo('위험관리형', '개인정보, 편향, 윤리와 부작용을 먼저 고려하는 경향', '위험 점검과 함께 문제 해결에 필요한 대안을 찾아보세요.'),
}

# 사용자가 문항의 취지에 동의하는 정도를 1~5로 답합니다.
# 2개 문항의 합(2~10)을 사용하며, 동일한 가중치를 부여합니다.
QUESTIONS = [
    ('p1', 'planner', 'AI에게 질문하기 전에 달성하려는 목표를 먼저 정리한다.'),
    ('e1', 'explorer', '한 가지 답보다 다양한 아이디어나 대안을 먼저 찾아본다.'),
    ('v1', 'verifier', 'AI가 제공한 사실을 다른 자료와 대조하여 확인한다.'),
    ('i1', 'improver', '처음 받은 AI 답변을 수정 요청하며 여러 번 다듬는다.'),
    ('x1', 'executor', 'AI가 제안한 내용을 실행 가능한 작업 순서로 바꾼다.'),
    ('g1', 'guardian', 'AI에 자료를 입력하기 전에 개인정보가 포함되어 있는지 확인한다.'),
    ('p2', 'planner', 'AI에 요청할 때 필요한 조건과 제약을 구체적으로 알려준다.'),
    ('e2', 'explorer', 'AI의 답변을 바탕으로 기존에 생각하지 못한 방향을 더 탐색한다.'),
    ('v2', 'verifier', '수치·인용·출처가 제시되면 근거가 실제로 있는지 점검한다.'),
    ('i2', 'improver', '여러 버전의 결과를 비교하고 더 나은 표현을 선택한다.'),
    ('x2', 'executor', 'AI를 활용한 뒤 실제로 해야 할 다음 행동을 정한다.'),
    ('g2', 'guardian', 'AI 결과가 누군가에게 불공정하거나 위험하지 않을지 생각한다.'),
]

ANSWER_LABELS = {
    1: '전혀 그렇지 않다',
    2: '그렇지 않은 편이다',
    3: '보통이다',
    4: '그런 편이다',
    5: '매우 그렇다',
}


def classify(answers: dict[str, int]) -> dict:
    """모든 응답이 완료된 경우에만 분류. 통점 시 결과는 탐색적 안내."""
    ids = {question_id for question_id, _, _ in QUESTIONS}
    if not isinstance(answers, dict) or set(answers) != ids:
        raise ValueError('12개 설문 문항에 모두 응답해야 합니다.')
    for question_id, _, _ in QUESTIONS:
        score = answers[question_id]
        if type(score) is not int or not 1 <= score <= 5:
            raise ValueError(f'{question_id}의 응답은 1~5 정수여야 합니다.')

    scores = {type_id: 0 for type_id in TYPES}
    second_question = {}
    for question_id, type_id, _ in QUESTIONS:
        scores[type_id] += answers[question_id]
        if question_id.endswith('2'):
            second_question[type_id] = answers[question_id]

    top_score = max(scores.values())
    tied = [type_id for type_id in TYPES if scores[type_id] == top_score]
    # 통점 때 두 번째 행동 문항 점수를 우선 비교하고, 완전 동점은 사전 정의된 유형 순서로 선택.
    primary = sorted(tied, key=lambda type_id: (-second_question[type_id], list(TYPES).index(type_id)))[0]
    ordered_scores = sorted(scores.values(), reverse=True)
    margin = ordered_scores[0] - ordered_scores[1]
    return {
        'survey_version': SURVEY_VERSION,
        'primary_type': primary,
        'scores': scores,
        'tied_types': tied,
        'margin': margin,
        'is_close': margin <= 1,
    }
