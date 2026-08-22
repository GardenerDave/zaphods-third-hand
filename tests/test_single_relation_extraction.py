import json
from pathlib import Path

from scripts.zth_qwen3_1_7b_single_relation_extraction import validate_model_free


ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "docs/research/SINGLE_RELATION_EXTRACTION_TASKS_2026-08-22.json"


def test_single_relation_manifest_is_balanced_and_model_free():
    binding = validate_model_free()
    assert len(binding["tasks"]) == 8
    assert sum(t["semantic_regime"] == "DIRECT_ENTITY_OBJECT" for t in binding["tasks"]) == 4
    assert sum(t["semantic_regime"] == "SUBOBJECT_WITH_REFERENCE" for t in binding["tasks"]) == 4
    assert len({t["action_verb"] for t in binding["tasks"]}) == 4
    assert binding["payload"]["model_outputs_consulted"] is False


def test_each_action_appears_in_both_semantic_regimes():
    tasks = json.loads(TASKS.read_text())["tasks"]
    for action in {task["action_verb"] for task in tasks}:
        assert {task["semantic_regime"] for task in tasks if task["action_verb"] == action} == {"DIRECT_ENTITY_OBJECT", "SUBOBJECT_WITH_REFERENCE"}
