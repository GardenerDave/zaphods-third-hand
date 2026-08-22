import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "docs/research/TARGET_BOUND_ACTION_EXTRACTION_ISOLATION_TASKS_2026-08-22.json"


def test_role_reversal_and_shortcut_audits():
    payload = json.loads(TASKS.read_text())
    tasks = payload["tasks"]
    assert len(tasks) == 8
    assert len({task["pair_id"] for task in tasks}) == 4
    for pair_id in {task["pair_id"] for task in tasks}:
        pair = [task for task in tasks if task["pair_id"] == pair_id]
        assert len(pair) == 2
        assert pair[0]["requested_target"] == pair[1]["requested_target"]
        assert {pair[0]["expected_target_bound_operation"], pair[1]["expected_target_bound_operation"]} == {pair[0]["verb_a"], pair[0]["verb_b"]}
        assert {pair[0]["secondary_action"], pair[1]["secondary_action"]} == {pair[0]["verb_a"], pair[0]["verb_b"]}
    for verb in {task["verb_a"] for task in tasks} | {task["verb_b"] for task in tasks}:
        roles = [task["expected_target_bound_operation"] == verb for task in tasks if verb in (task["verb_a"], task["verb_b"])]
        assert roles.count(True) == roles.count(False) == 1
    answers = [task["expected_target_bound_operation"] for task in tasks]
    first = [task["first_action"] for task in tasks]
    last = [task["second_action"] for task in tasks]
    assert not all(answer == token for answer, token in zip(answers, first))
    assert not all(answer == token for answer, token in zip(answers, last))
    assert {task["expected_answer_position"] for task in tasks} == {"first", "second"}


def test_prompt_source_has_no_forbidden_semantic_terms():
    payload = json.loads(TASKS.read_text())
    text = " ".join(task["sentence"] for task in payload["tasks"]).casefold()
    for forbidden in ("authorization", "scope", "membership", "policy", "allowed", "review"):
        assert forbidden not in text
