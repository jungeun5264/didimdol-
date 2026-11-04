"""2025 디지털정보격차 실태조사 Q26을 이용한 LPA 6유형 *추론*.

- 새 사용자의 Q26_1..Q26_12에 대한 1~4점 정수 자기평가 응답만 받습니다.
- 네 개 영역의 산술평균을 원점수 그대로 사용합니다(표준화/역코딩 없음).
- 사용자별 가장 높은 사후확률의 유형을 추천합니다.
- 저장된 모형의 추론만 수행합니다. 재학습하거나 객관적 역량을 판정하지 않습니다.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

SURVEY_VERSION = 'Q26-LPA-2025-v1'
MODEL_FILE = Path(__file__).with_name('LPA_inference_only.json')
AREAS = ('AI 이해', 'AI 활용', 'AI 평가·선택', '책임·안전 인식')

# 응답 척도의 정확한 원조사 앵커 문구는 원본 조사표와 대조할 것.
ANSWER_LABELS = {
    1: '전혀 그렇지 않다',
    2: '그렇지 않은 편이다',
    3: '그런 편이다',
    4: '매우 그렇다',
}

# Q26 순서는 통계 모형과 직접 연결됩니다. 임의 변경 금지.
QUESTIONS = [
    ('Q26_1', 'AI 이해', 'AI가 적용된 기기와 아닌 기기를 구별할 수 있다'),
    ('Q26_2', 'AI 이해', 'AI 기술로 내가 어떤 도움을 받을 수 있는지 알고 있다'),
    ('Q26_3', 'AI 이해', '내가 사용하는 애플리케이션과 제품에 적용된 AI기술을 식별해낼 수 있다'),
    ('Q26_4', 'AI 활용', 'AI 애플리케이션이나 제품을 일상 업무에 능숙하게 활용할 수 있다'),
    ('Q26_5', 'AI 활용', '새로운 AI 애플리케이션이나 제품을 배우는 것이 어렵지 않다'),
    ('Q26_6', 'AI 활용', 'AI 애플리케이션이나 제품을 사용하여 업무 효율성을 향상시킬 수 있다'),
    ('Q26_7', 'AI 평가·선택', 'AI 애플리케이션이나 제품을 일정 기간 사용한 후에 그 기능과 한계를 평가할 수 있다'),
    ('Q26_8', 'AI 평가·선택', '스마트 에이전트(AI 추천 시스템, 챗봇 등)가 제공하는 다양한 솔루션 중에서 적절한 것을 선택할 수 있다'),
    ('Q26_9', 'AI 평가·선택', '다양한 선택지 중 특정 작업에 가장 적합한 AI 애플리케이션이나 제품을 선택할 수 있다'),
    ('Q26_10', '책임·안전 인식', 'AI 애플리케이션이나 제품을 사용할 때 법률을 위반하지 않거나 다른 사람의 권리를 침해하지 않도록 노력한다'),
    ('Q26_11', '책임·안전 인식', 'AI 애플리케이션이나 제품을 사용할 때 개인정보 보호나 정보 보안 문제를 의식하는 편이다'),
    ('Q26_12', '책임·안전 인식', 'AI 기술의 잘못된 사용에 대해 경계한다'),
]

@dataclass(frozen=True)
class TypeInfo:
    name: str
    description: str
    tip: str

# 유형명은 사용자가 제공한 분석팀 전달안내와 일치하도록 매핑합니다.
TYPES = {
    'C1': TypeInfo('AI 첫걸음형', '네 가지 AI 자기평가 영역에서 모두 낮은 응답 경향', 'AI 사용 예제부터 부담 없이 시작해보세요.'),
    'C2': TypeInfo('안전 인식 우세 입문형', '일반 활용 자기평가에 비해 책임·안전 인식이 높은 경향', '기초 AI 활용 연습과 안전한 사용 습관을 함께 발전시켜보세요.'),
    'C3': TypeInfo('기초 활용형', '네 가지 영역에서 전반적으로 기초 수준의 자기평가 경향', '일상·학업 과제에서 AI를 적용해보고 결과를 검토해보세요.'),
    'C4': TypeInfo('안전 인식 우세 확장형', '책임·안전 인식이 상대적으로 높은 중간 수준 자기평가 경향', '안전한 사용 습관을 유지하며 복합적인 문제 해결에 도전해보세요.'),
    'C5': TypeInfo('실용 활용형', '대부분의 AI 자기평가 영역에서 비교적 높은 응답 경향', '실전 과제를 반복 수행하며 검증과 개선 과정을 기록해보세요.'),
    'C6': TypeInfo('숙련 활용형', '네 가지 영역에서 모두 높은 자기평가 경향', '복잡한 과제와 AI 결과의 비판적 검증을 연습해보세요.'),
}


def _cholesky(matrix):
    """4x4 양의 정부호 공분산을 위한 순수 Python 촐레스키 분해."""
    size = len(matrix)
    lower = [[0.0] * size for _ in range(size)]
    for i in range(size):
        for j in range(i + 1):
            v = matrix[i][j] - sum(lower[i][k] * lower[j][k] for k in range(j))
            if i == j:
                if v <= 0 or not math.isfinite(v):
                    raise ValueError('LPA 공분산이 양의 정부호가 아닙니다.')
                lower[i][j] = math.sqrt(v)
            else:
                lower[i][j] = v / lower[j][j]
    return lower


@lru_cache(maxsize=1)
def _load_model():
    data = json.loads(MODEL_FILE.read_text(encoding='utf-8'))
    pi, means, cov = data['pi'], data['means'], data['covariance']
    if (len(pi) != 6 or len(means) != 6 or any(len(row) != 4 for row in means)
            or len(cov) != 4 or any(len(row) != 4 for row in cov)):
        raise ValueError('LPA 모형 차원이 6유형 × 4영역과 일치하지 않습니다.')
    if any(not math.isfinite(float(p)) or float(p) <= 0 for p in pi) or abs(sum(pi) - 1) > 1e-6:
        raise ValueError('LPA 혼합비율이 올바르지 않습니다.')
    if any(not math.isfinite(float(v)) for row in [*means, *cov] for v in row):
        raise ValueError('LPA 평균/공분산에 유한하지 않은 값이 있습니다.')
    if any(abs(cov[i][j] - cov[j][i]) > 1e-9 for i in range(4) for j in range(4)):
        raise ValueError('LPA 공분산 행렬이 대칭이 아닙니다.')
    lower = _cholesky(cov)
    return data['model_id'], pi, means, lower


def _quadratic_distance(x, mean, lower):
    """(x-mu)^T Sigma^(-1) (x-mu), 역행렬 없이 계산."""
    residual = [v - m for v, m in zip(x, mean)]
    solved = []
    for i in range(4):
        solved.append((residual[i] - sum(lower[i][j] * solved[j] for j in range(i))) / lower[i][i])
    return sum(v*v for v in solved)


def classify(answers: dict[str, int]) -> dict:
    expected_keys = {item[0] for item in QUESTIONS}
    if not isinstance(answers, dict) or set(answers) != expected_keys:
        raise ValueError('Q26 12문항에 빠짐없이 응답해주세요.')
    for key in expected_keys:
        if type(answers[key]) is not int or not 1 <= answers[key] <= 4:
            raise ValueError(f'{key} 응답은 1~4 정수여야 합니다.')

    # 3문항 평균 x 4영역; 기존 학습 모형의 순서와 척도를 그대로 사용.
    x = [sum(answers[f'Q26_{i}'] for i in range(start, start + 3)) / 3
         for start in (1, 4, 7, 10)]
    model_id, pi, means, lower = _load_model()

    # 공통 공분산인 동일 차원의 다변량 정규분포이므로 정규화 상수는 유형 간 상쇄.
    log_weights = [math.log(pi[k]) - .5 * _quadratic_distance(x, means[k], lower)
                   for k in range(6)]
    pivot = max(log_weights)
    normalizers = [math.exp(z - pivot) for z in log_weights]
    total = sum(normalizers)
    posterior = [v / total for v in normalizers]
    ordering = sorted(range(6), key=lambda i: (-posterior[i], i))
    primary = f'C{ordering[0] + 1}'
    runner_up = f'C{ordering[1] + 1}'
    gap = posterior[ordering[0]] - posterior[ordering[1]]
    return {
        'survey_version': SURVEY_VERSION,
        'model_id': model_id,
        'four_means': x,
        'posterior_probabilities': {f'C{k+1}': posterior[k] for k in range(6)},
        'primary_type': primary,
        'primary_probability': posterior[ordering[0]],
        'runner_up_type': runner_up,
        'runner_up_probability': posterior[ordering[1]],
        'margin': gap,
        # 0.10은 경계 사례를 쉽게 안내하기 위한 UI 정책일 뿐 통계적으로 검증된 기준이 아님.
        'is_close': gap < 0.10,
    }
