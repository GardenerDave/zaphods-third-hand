from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from scripts.zth_qwen3_1_7b_crossed_scope_factorial_probe import (
    EXPECTED_EFFECTIVE_CTX,
    MAX_OUTPUT_TOKENS,
    TASK_MANIFEST,
    task_prompt,
    validate_factorial_manifest,
)


def load_tasks() -> dict:
    return json.loads(TASK_MANIFEST.read_text(encoding="utf-8"))


def test_factorial_manifest_is_balanced_and_leakage_free() -> None:
    payload = load_tasks()
    audit = validate_factorial_manifest(payload)
    tasks = payload["tasks"]
    assert audit["task_count"] == 16
    assert audit["true_count"] == 8
    assert audit["false_count"] == 8
    assert audit["answer_leakage_findings"] == 0
    assert Counter(task["operation_factor"] for task in tasks) == {"READ": 8, "MUTATE": 8}
    assert Counter(task["authority_factor"] for task in tasks) == {
        "INSIDE_AUTHORITY": 8,
        "OUTSIDE_AUTHORITY": 8,
    }
    assert Counter(task["distractor_factor"] for task in tasks) == {
        "HELD_DISTRACTOR_PRESENT": 8,
        "HELD_DISTRACTOR_ABSENT": 8,
    }


def test_each_crossed_cell_has_two_tasks() -> None:
    tasks = load_tasks()["tasks"]
    cells = Counter(
        (task["operation_factor"], task["authority_factor"], task["distractor_factor"])
        for task in tasks
    )
    assert len(cells) == 8
    assert set(cells.values()) == {2}
    operation_authority = Counter(
        (task["operation_factor"], task["authority_factor"]) for task in tasks
    )
    assert set(operation_authority.values()) == {4}


def test_prompt_bound_is_below_effective_context() -> None:
    tasks = load_tasks()["tasks"]
    max_prompt = max(len(task_prompt(task)) for task in tasks)
    assert max_prompt + MAX_OUTPUT_TOKENS < EXPECTED_EFFECTIVE_CTX


def test_expected_boolean_is_authority_derived_only() -> None:
    for task in load_tasks()["tasks"]:
        assert task["expected_scope_expansion_required"] == (
            task["authority_factor"] == "OUTSIDE_AUTHORITY"
        )
