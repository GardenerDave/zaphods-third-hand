from __future__ import annotations

import hashlib

from scripts.zth_qwen3_5_0_8b_atomic_audition import PROMPT_SUFFIX, aggregate_rows


def _row(task_id: str, expansion: bool, semantic_fields: int, passed: bool = False) -> dict:
    return {
        "task_id": task_id,
        "reference_facts": {"requires_scope_expansion_flag": expansion},
        "transport_valid": True,
        "raw_parse_valid": True,
        "contract_valid": True,
        "reference_fact_valid": passed,
        "full_validator_pass": passed,
        "validator_contract_valid": False,
        "atomic": {
            "semantic_fields_correct": semantic_fields,
            "allowed_targets": {"exact_set_match": True, "precision": 1.0, "recall": 1.0},
            "held_targets": {"exact_set_match": True, "precision": 1.0, "recall": 1.0},
            "authority_separation": {"observability": "OBSERVED_AND_CORRECT", "overlap_targets": []},
            "scope_expansion": {"correct": expansion, "false_positive": False, "false_negative": False},
            "review_status": {"exact_match": passed, "confusion_pair": None if passed else "ready_for_review -> other"},
            "semantic_field_vector": {"allowed_targets": True, "held_targets": True, "scope_expansion_required": expansion, "review_status": passed},
            "object_observable": True,
            "structural_contract_valid": True,
        },
        "wall_elapsed_ms": 10.0,
        "power_summary": {"gross_energy_joules": 2.0},
    }


def test_prompt_suffix_is_explicit_typed_json_and_no_think():
    assert "Return ONLY a bare JSON object." in PROMPT_SUFFIX
    assert '"allowed_targets": ["string"]' in PROMPT_SUFFIX
    assert '"scope_expansion_required": true' in PROMPT_SUFFIX
    assert PROMPT_SUFFIX.endswith("/no_think")
    assert hashlib.sha256(PROMPT_SUFFIX.encode()).hexdigest() == "3a1003f506379b1fd21eae3103cc683bf86a12f5667bdcc07a76828a58b0b9c8"


def test_aggregate_preserves_true_false_scope_branches_and_profiles():
    rows = [
        _row("false-1", False, 4, True),
        _row("false-2", False, 3, False),
        _row("true-1", True, 4, True),
        _row("true-2", True, 2, False),
    ]
    result = aggregate_rows(rows, {"mean_power_watts": 1.0})
    assert result["tasks"] == 4
    assert result["branch_results"]["false"]["tasks"] == 2
    assert result["branch_results"]["true"]["tasks"] == 2
    assert result["semantic_fields_correct_distribution"] == {"0": 0, "1": 0, "2": 1, "3": 1, "4": 2}
    assert result["execution"] == {"supplier_model_calls": 16, "teacher_calls": 0, "retry_count": 0, "escalation_count": 0}
