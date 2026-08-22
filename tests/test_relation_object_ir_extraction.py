import json
from pathlib import Path

from scripts.zth_qwen3_1_7b_relation_object_ir_extraction import validate_model_free
from scripts.zth_relation_object_ir import select_direct_target


ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "docs/research/RELATION_OBJECT_IR_EXTRACTION_TASKS_2026-08-22.json"


def test_fresh_relation_ir_manifest_is_balanced_and_model_free():
    binding = validate_model_free()
    assert len(binding["tasks"]) == 8
    assert len(binding["pairs"]) == 4
    assert binding["task_sha256"] == __import__("hashlib").sha256(TASKS.read_bytes()).hexdigest()
    assert all(binding["tasks"][index]["expected_selected_relation_position"] in {"first", "second"} for index in range(8))


def test_model_free_selector_reproduces_all_expected_operations():
    payload = json.loads(TASKS.read_text())
    for task in payload["tasks"]:
        relations = [
            {"action": task["action_1"], "direct_object": task["direct_object_1"], "reference_entity": task["reference_entity_1"]},
            {"action": task["action_2"], "direct_object": task["direct_object_2"], "reference_entity": task["reference_entity_2"]},
        ]
        selected = select_direct_target(relations, task["requested_target"])
        assert selected["selected_operation"] == task["expected_selected_operation"]


def test_reference_entity_does_not_bind_and_failures_are_explicit():
    relation = {"action": "inspect", "direct_object": "checksum note", "reference_entity": "harbor-index.json"}
    assert select_direct_target([relation], "harbor-index.json")["classification"] == "NO_DIRECT_TARGET_BINDING"
    ambiguous = [
        {"action": "inspect", "direct_object": "harbor-index.json", "reference_entity": ""},
        {"action": "record", "direct_object": "harbor-index.json", "reference_entity": ""},
    ]
    assert select_direct_target(ambiguous, "harbor-index.json")["classification"] == "AMBIGUOUS_DIRECT_TARGET_BINDING"
