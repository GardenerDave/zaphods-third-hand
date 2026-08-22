import json
from pathlib import Path

from scripts.zth_qwen3_1_7b_action_object_relation_extraction import score, select_target_relation


ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "docs/research/ACTION_OBJECT_RELATION_EXTRACTION_TASKS_2026-08-22.json"


def test_relation_pairs_reverse_target_binding():
    payload = json.loads(TASKS.read_text())
    tasks = payload["tasks"]
    assert len(tasks) == 8
    pairs = {}
    for task in tasks:
        pairs.setdefault(task["pair_id"], []).append(task)
    assert len(pairs) == 4
    for rows in pairs.values():
        assert len(rows) == 2
        assert rows[0]["requested_target"] == rows[1]["requested_target"]
        verbs = {rows[0]["action_1"], rows[0]["action_2"]}
        assert verbs == {rows[1]["action_1"], rows[1]["action_2"]}
        assert {rows[0]["expected_selected_operation"], rows[1]["expected_selected_operation"]} == verbs
        assert all(sum(task["object_1"] == task["requested_target"] for task in rows) + sum(task["object_2"] == task["requested_target"] for task in rows) == 2 for task in rows)
        assert {task["expected_selected_position"] for task in rows} == {"first", "second"}


def test_no_policy_or_shortcut_terms_in_sentences():
    payload = json.loads(TASKS.read_text())
    text = " ".join(task["sentence"] for task in payload["tasks"]).casefold()
    for forbidden in ("authorization", "scope", "membership", "policy", "allowed", "review", "boolean"):
        assert forbidden not in text


def test_no_surface_shortcut_perfectly_predicts_selected_operation():
    payload = json.loads(TASKS.read_text())
    tasks = payload["tasks"]
    assert sum(task["expected_selected_position"] == "first" for task in tasks) == 4
    assert sum(task["expected_selected_position"] == "second" for task in tasks) == 4
    assert sum(task["expected_selected_operation"] == task["action_1"] for task in tasks) == 4
    assert sum(task["expected_selected_operation"] == task["action_2"] for task in tasks) == 4
    for action_key in ("action_1", "action_2"):
        actions = [task[action_key] for task in tasks]
        for action in sorted(set(actions)):
            rows = [task for task in tasks if task[action_key] == action]
            assert any(task["expected_selected_operation"] == action for task in rows)
            assert any(task["expected_selected_operation"] != action for task in rows)


def test_deterministic_target_selection_and_fault_containment():
    inside = {
        "action_1": "inspect",
        "object_1": "beacon-record.json",
        "action_2": "document",
        "object_2": "expiration detail",
    }
    task = {
        "requested_target": "beacon-record.json",
        "action_1": "inspect",
        "object_1": "beacon-record.json",
        "action_2": "document",
        "object_2": "expiration detail",
        "expected_selected_operation": "inspect",
    }
    selection = select_target_relation(inside, task["requested_target"])
    assert selection["selected_operation"] == "inspect"
    assert score(inside, True, True, task)["selected_correct"] is True

    outside = dict(inside)
    outside["object_1"] = "not-the-requested-target.json"
    outside_task = dict(task)
    outside_task["expected_selected_operation"] = "document"
    selection = select_target_relation(outside, task["requested_target"])
    assert selection["selected_operation"] is None
    assert selection["evaluable"] is False
    assert score(outside, True, True, outside_task)["failure_class"] == "RELATION_EXTRACTION_ERROR_SELECTION_UNEVALUABLE"


def test_ambiguous_target_binding_is_not_resolved_by_code():
    parsed = {
        "action_1": "inspect",
        "object_1": "beacon-record.json",
        "action_2": "document",
        "object_2": "beacon-record.json",
    }
    result = select_target_relation(parsed, "beacon-record.json")
    assert result["ambiguous"] is True
    assert result["selected_operation"] is None
