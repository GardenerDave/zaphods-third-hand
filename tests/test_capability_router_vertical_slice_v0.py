from __future__ import annotations

import json
from pathlib import Path

from scripts.zth_capability_router_vertical_slice_v0 import (
    deterministic_policy,
    load_registry,
    load_tasks,
    parse_model_output,
    validate_model_free,
)


def test_frozen_fixture_and_registry_audit():
    binding = validate_model_free()
    assert len(binding["tasks"]) == 8
    assert len(binding["registry"]["entries"]) == 5
    assert sum(t["expected_supplier_type"] == "DETERMINISTIC_CODE" for t in binding["tasks"]) == 2
    assert sum(t["expected_supplier_type"] == "MODEL" for t in binding["tasks"]) == 4
    assert sum(t["expected_supplier_type"] == "REVIEW_OR_ESCALATION" for t in binding["tasks"]) == 2
    assert all(deterministic_policy(t) == t["expected_policy_result"] for t in binding["tasks"] if t["expected_supplier_type"] == "DETERMINISTIC_CODE")


def test_model_contract_and_fail_closed_registry():
    parsed, parse_valid, contract_valid, diagnostics = parse_model_output('{"action":"inspect","object_expression":"amber-ledger.json"}')
    assert parsed == {"action": "inspect", "object_expression": "amber-ledger.json"}
    assert parse_valid and contract_valid and diagnostics == []
    parsed, parse_valid, contract_valid, diagnostics = parse_model_output('{"action":"inspect","object_expression":"x","extra":"no"}')
    assert parsed is None and parse_valid and not contract_valid
    assert load_tasks() and load_registry()["automatic_promotion"] is False
