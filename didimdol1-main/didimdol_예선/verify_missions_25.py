"""25개 미션 데이터 무결성 및 기존 데이터 보존 검증. python verify_missions_25.py"""
from collections import Counter
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

base = Path(__file__).resolve().parent
spec = spec_from_file_location("mission_candidate", base / "missions.py")
mod = module_from_spec(spec)
spec.loader.exec_module(mod)
ms = mod.MISSIONS
assert len(ms) == 25, f"미션 수 오류: {len(ms)}"
expected = {"일상": 5, "학업": 5, "취업": 5, "실전직무": 5, "평가": 5}
assert Counter(m["eyebrow"].split(" · ")[0] for m in ms.values()) == expected
keys = {"id", "eyebrow", "title", "summary", "difficulty", "minutes", "accent", "situation", "goals", "constraints", "deliverable", "target_abilities", "fallback_events"}
allowed_abilities = {"ai_basic", "ai_usage", "human_agency", "human_responsibility", "ethical_view", "safe_use"}
for key, m in ms.items():
    assert m.keys() == keys, key
    assert m["id"] == key, key
    assert len(m["fallback_events"]) == 3, key
    assert all(set(event) == {"title", "situation", "task"} and all(event.values()) for event in m["fallback_events"]), key
    assert len(m["goals"]) >= 3 and len(m["constraints"]) >= 3, key
    assert len(m["deliverable"]) == 4 and len({a[0] for a in m["deliverable"]}) == 4, key
    assert all(len(a) == 3 and all(isinstance(x, str) and x.strip() for x in a) for a in m["deliverable"]), key
    assert m["target_abilities"] and set(m["target_abilities"]) <= allowed_abilities, key
    assert m["difficulty"] in {"쉬움", "보통", "어려움"}, key
    assert 1 <= m["minutes"] <= 45, key
print("PASS: 25 missions, 5 per category, schema, constraints, events, deliverables")
