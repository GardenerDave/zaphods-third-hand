import json
from pathlib import Path

from scripts.zth_qwen3_1_7b_minimal_action_object_atom import validate_model_free


ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "docs/research/MINIMAL_ACTION_OBJECT_ATOM_TASKS_2026-08-22.json"


def test_minimal_atom_is_balanced_and_model_free():
    binding = validate_model_free()
    assert len(binding["tasks"]) == 8
    assert sum(t["semantic_regime"] == "DIRECT_ENTITY_OBJECT" for t in binding["tasks"]) == 4
    assert sum(t["semantic_regime"] == "SUBOBJECT_WITH_REFERENCE" for t in binding["tasks"]) == 4
    assert binding["payload"]["model_outputs_consulted"] is False


def test_each_action_occurs_in_both_regimes():
    tasks = json.loads(TASKS.read_text())["tasks"]
    for action in {t["action_verb"] for t in tasks}:
        assert {t["semantic_regime"] for t in tasks if t["action_verb"] == action} == {"DIRECT_ENTITY_OBJECT", "SUBOBJECT_WITH_REFERENCE"}
