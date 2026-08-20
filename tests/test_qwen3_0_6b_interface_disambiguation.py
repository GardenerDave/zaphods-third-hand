from __future__ import annotations

import json

from scripts.zth_qwen3_0_6b_interface_disambiguation import (
    EXPLICIT_INTERFACE_SUFFIX,
    prompt_for,
    raw_quality,
)


def test_prompt_uses_explicit_typed_object_and_not_field_name_array() -> None:
    task = {
        "prompt": "Bounded task.",
        "output_contract": {"required_fields": ["allowed_targets", "held_targets", "scope_expansion_required", "review_status"]},
    }
    prompt = prompt_for(task)
    assert "Return ONLY a bare JSON object." in prompt
    assert '"allowed_targets": ["string"]' in prompt
    assert '"scope_expansion_required": true' in prompt
    assert "Do not use markdown or code fences." in prompt
    assert '["allowed_targets","held_targets","scope_expansion_required","review_status"]' not in prompt
    assert prompt.endswith("/no_think")
    assert EXPLICIT_INTERFACE_SUFFIX in prompt


def test_raw_quality_treats_not_applicable_authority_as_neutral() -> None:
    validation = {
        "validation_status": "passed",
        "checks": [{"check_id": "parse_json", "status": "passed"}],
        "structural_checks": [
            {"check_id": "parse_json", "status": "passed"},
            {"check_id": "target_authority", "status": "not_applicable"},
        ],
        "semantic_checks": [{"check_id": "reference", "status": "passed"}],
    }
    assert raw_quality(validation) == {
        "parse_valid": True,
        "contract_valid": True,
        "reference_valid": True,
        "fully_validated": True,
    }


def test_raw_quality_does_not_repair_failed_validation() -> None:
    validation = {
        "validation_status": "failed",
        "checks": [{"check_id": "parse_json", "status": "passed"}],
        "structural_checks": [{"check_id": "parse_json", "status": "passed"}],
        "semantic_checks": [{"check_id": "reference", "status": "failed"}],
    }
    result = raw_quality(validation)
    assert result["parse_valid"] is True
    assert result["contract_valid"] is True
    assert result["reference_valid"] is False
    assert result["fully_validated"] is False
