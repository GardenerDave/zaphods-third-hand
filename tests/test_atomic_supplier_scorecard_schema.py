import json
from pathlib import Path

import pytest
from jsonschema import ValidationError, validate


SCHEMA = json.loads(Path("docs/research/ATOMIC_SUPPLIER_SCORECARD_SCHEMA_V1.json").read_text())


def scorecard(*, analysis_calls: int = 0, supplier_calls: int = 12) -> dict:
    return {
        "provenance": {
            "evidence_resolution": "screening",
            "source_paths": ["fixture.json"],
            "source_hashes": ["abc"],
            "analysis_model_calls_made": analysis_calls,
        },
        "supplier": {
            "model_identity": "candidate",
            "runtime_identity": "runtime",
        },
        "task_family": "scope-authority-boundary",
        "attempts": {
            "supplier_model_calls_made": supplier_calls,
            "tasks": 12,
            "transport_valid": 12,
            "raw_parse_valid": 12,
            "contract_valid": 8,
            "full_validator_passes": 4,
        },
        "atomic_profile": {
            "structured_output": {},
            "field_types": {},
            "allowed_targets": {},
            "held_targets": {},
            "authority_separation": {},
            "scope_expansion": {},
            "review_status": {},
            "semantic_fields_correct_distribution": {"0": 1, "4": 3},
            "full_task": {},
        },
        "resource_profile": {},
        "escalation_profile": {"escalation_count": 0, "rescue_count": 0, "repair_deltas": []},
    }


def test_model_free_analysis_scorecard_is_valid() -> None:
    validate(scorecard(analysis_calls=0, supplier_calls=0), SCHEMA)


def test_future_supplier_execution_calls_are_not_const_zero() -> None:
    validate(scorecard(analysis_calls=0, supplier_calls=12), SCHEMA)


def test_negative_call_counts_are_rejected() -> None:
    with pytest.raises(ValidationError):
        validate(scorecard(analysis_calls=-1), SCHEMA)
    with pytest.raises(ValidationError):
        validate(scorecard(supplier_calls=-1), SCHEMA)


def test_provenance_and_atomic_vectors_remain_required() -> None:
    missing_provenance_count = scorecard()
    del missing_provenance_count["provenance"]["analysis_model_calls_made"]
    with pytest.raises(ValidationError):
        validate(missing_provenance_count, SCHEMA)
    missing_vector = scorecard()
    del missing_vector["atomic_profile"]["review_status"]
    with pytest.raises(ValidationError):
        validate(missing_vector, SCHEMA)
