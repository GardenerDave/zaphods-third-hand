from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.zth_qwen3_0_6b_clean_scope_logic_probe import (
    EXPECTED_GPU_UUID,
    PROMPT_SUFFIX,
    SEMANTIC_RULE,
    build_aggregate,
    parse_atomic,
    prompt_for,
    validate_fixture_manifest,
)
from local_harness.stage_a_power_telemetry import PowerSample, integrate_energy_joules


ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_0_6B_CLEAN_SCOPE_LOGIC_PROBE_TASKS_2026-08-21.json"


def load_tasks() -> dict:
    return json.loads(TASKS.read_text(encoding="utf-8"))


def test_frozen_probe_is_balanced_and_has_no_task_answer_leakage():
    result = validate_fixture_manifest(load_tasks())
    assert result["task_count"] == 16
    assert result["true_count"] == 8
    assert result["false_count"] == 8
    assert result["answer_leakage_findings"] == 0


def test_task_prompt_excludes_hidden_expected_and_derivation():
    task = load_tasks()["tasks"][0]
    prompt = prompt_for(task)
    assert str(task["expected_scope_expansion_required"]) not in prompt
    assert task["derivation_note"] not in prompt
    assert PROMPT_SUFFIX in prompt
    assert SEMANTIC_RULE in prompt
    assert "scope_expansion_required" not in prompt.split("\n\nReturn ONLY", 1)[0]


@pytest.mark.parametrize(
    ("raw", "parse_valid", "contract_valid", "observed", "failure"),
    [
        ('{"scope_expansion_required":true}', True, True, True, None),
        ('{"scope_expansion_required":false}', True, True, False, None),
        ('{"scope_expansion_required":"true"}', True, False, "true", "INVALID_CONTRACT"),
        ('{"other":true}', True, False, None, "INVALID_CONTRACT"),
        ('```json\n{"scope_expansion_required":true}\n```', False, False, None, "SERIALIZATION_FAILURE"),
    ],
)
def test_atomic_raw_contract_is_strict(raw, parse_valid, contract_valid, observed, failure):
    assert parse_atomic(raw) == {
        "raw_parse_valid": parse_valid,
        "contract_valid": contract_valid,
        "observed": observed,
        "failure": failure,
    } | ({"parse_error": "Expecting value"} if raw.startswith("```") else {})


def test_energy_integration_uses_gpu_device_samples_only():
    samples = [
        PowerSample("2026-08-21T00:00:00+00:00", 1.0, EXPECTED_GPU_UUID, 20.0, 1),
        PowerSample("2026-08-21T00:00:01+00:00", 1.25, EXPECTED_GPU_UUID, 24.0, 2),
    ]
    assert integrate_energy_joules(samples, sample_interval_seconds=0.25, expected_gpu_uuid=EXPECTED_GPU_UUID) == 11.0


def test_aggregate_reports_separate_branch_counts_and_failure_classes():
    rows = []
    for index in range(8):
        expected = index >= 4
        observed = expected if index != 1 else not expected
        rows.append(
            {
                "expected_scope_expansion_required": expected,
                "observed_scope_expansion_required": observed,
                "correct": expected == observed,
                "failure_class": None if expected == observed else "SCOPE_DECISION_FAILURE",
                "wall_elapsed_ms": 10.0 + index,
                "power_summary": {"gross_energy_joules": 2.0 + index},
            }
        )
    result = build_aggregate(rows, {"mean_power_watts": 10.0})
    assert result["branch_results"]["true"]["tasks"] == 4
    assert result["branch_results"]["false"]["tasks"] == 4
    assert result["scope_decision_failures"] == 1
    assert result["serialization_failures"] == 0
