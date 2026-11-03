from __future__ import annotations
from copy import deepcopy
from typing import Any, Dict, List, Tuple

ABILITY_META = {
    "ai_basic": {"label": "AI의 기초 이해", "criteria": ["limitations_awareness", "uncertainty_awareness", "appropriate_use"]},
    "ai_usage": {"label": "AI 활용 능력", "criteria": ["goal_definition", "context_constraints", "iterative_refinement"]},
    "human_agency": {"label": "인간의 주도권", "criteria": ["criteria_setting", "critical_selection", "decision_ownership"]},
    "human_responsibility": {"label": "인간의 책임", "criteria": ["verification", "uncertainty_handling", "final_review"]},
    "ethical_view": {"label": "윤리적 관점", "criteria": ["bias_fairness", "stakeholder_impact", "honest_use"]},
    "safe_use": {"label": "안전하고 책임 있는 사용", "criteria": ["privacy", "confidentiality", "risk_management"]},
}
ABILITY_ORDER = list(ABILITY_META.keys())


def ability_score(result: Dict[str, Any], key: str) -> int | None:
    block = result.get(key, {})
    if not block.get("evaluated", False):
        return None
    vals = [max(0, min(4, int(block.get(c, 0)))) for c in ABILITY_META[key]["criteria"]]
    return round(sum(vals) / (len(vals) * 4) * 100)


def all_ability_scores(result: Dict[str, Any]) -> Dict[str, int | None]:
    return {k: ability_score(result, k) for k in ABILITY_ORDER}


def overall_score(result: Dict[str, Any]) -> int:
    vals = [v for v in all_ability_scores(result).values() if v is not None]
    return round(sum(vals) / len(vals)) if vals else 0


def update_profile(baseline: Dict[str, int], result: Dict[str, Any]) -> Dict[str, int]:
    profile = deepcopy(baseline)
    for key, score in all_ability_scores(result).items():
        if score is not None:
            profile[key] = score
    return profile


def strongest_assessed(result: Dict[str, Any]) -> Tuple[str, int] | None:
    rows = [(k, v) for k, v in all_ability_scores(result).items() if v is not None]
    if not rows:
        return None
    key, score = max(rows, key=lambda x: x[1])
    return ABILITY_META[key]["label"], score


def weakest_assessed(result: Dict[str, Any]) -> Tuple[str, int] | None:
    rows = [(k, v) for k, v in all_ability_scores(result).items() if v is not None]
    if not rows:
        return None
    key, score = min(rows, key=lambda x: x[1])
    return ABILITY_META[key]["label"], score


def biggest_growth(prev: Dict[str, Any], curr: Dict[str, Any]) -> Tuple[str, int, int, int] | None:
    p, c = all_ability_scores(prev), all_ability_scores(curr)
    rows: List[Tuple[str, int, int, int]] = []
    for key in ABILITY_ORDER:
        if p[key] is not None and c[key] is not None:
            rows.append((key, p[key], c[key], c[key] - p[key]))
    if not rows:
        return None
    key, pv, cv, delta = max(rows, key=lambda x: x[3])
    return ABILITY_META[key]["label"], pv, cv, delta
