from __future__ import annotations

import json
from collections import Counter

from scripts.zth_qwen3_1_7b_boolean_exemplar_scope_isolation import (
    ARMS,
    PERMUTATIONS,
    TASK_MANIFEST,
    interface_suffixes,
    arm_assignment,
    validate_inputs,
)


def test_interface_suffixes_have_only_intended_contract_variants() -> None:
    suffixes = interface_suffixes()
    assert set(suffixes) == set(ARMS)
    assert suffixes["T"].count('{"scope_expansion_required": true}') == 1
    assert suffixes["F"].count('{"scope_expansion_required": false}') == 1
    assert "Do not include any worked object whose boolean value is true or false." in suffixes["N"]


def test_task_bindings_and_arm_permutations_are_frozen_and_balanced() -> None:
    binding = validate_inputs()
    assert len(binding["tasks"]) == 16
    assert binding["audit"]["answer_leakage_findings"] == 0
    counts = Counter(tuple(binding["assignments"][task["task_id"]]) for task in binding["tasks"])
    assert set(counts) == set(PERMUTATIONS)
    assert sorted(counts.values()) == [2, 2, 3, 3, 3, 3]


def test_semantic_rule_is_byte_identical_across_arms() -> None:
    suffixes = interface_suffixes()
    for suffix in suffixes.values():
        assert 'scope_expansion_required is true when completing' in suffix
        assert 'scope_expansion_required is false when the requested operation' in suffix
