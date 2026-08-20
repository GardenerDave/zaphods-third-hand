from __future__ import annotations

import json
from pathlib import Path

import pytest

from local_harness.sequential_cost import treatment_sequential_elapsed_ms
from scripts import zth_run8_scope_aggregation as run8_aggregation


def _detail(local_ms: float, escalation_ms: float | None = None) -> dict:
    return {
        "local_first": {
            "realized_elapsed_ms": local_ms,
            "deterministically_validated_rescue": escalation_ms is None,
        },
        "escalated": escalation_ms is not None,
        "escalation": None if escalation_ms is None else {
            "realized_elapsed_ms": escalation_ms,
            "deterministically_validated_rescue": True,
        },
        "final": {"deterministically_validated_rescue": True},
    }


def _scorecard(task_id: str, detail: dict, *, control_ms: float = 100.0) -> dict:
    treatment_ms = detail["local_first"]["realized_elapsed_ms"] if not detail["escalated"] else detail["escalation"]["realized_elapsed_ms"]
    return {
        "family": "scope-authority-boundary",
        "task_id": task_id,
        "disposition": "comparable",
        "control": {"rescue": True, "elapsed_ms": control_ms},
        "treatment": {"rescue": True, "elapsed_ms": treatment_ms},
        "treatment_detail": detail,
        "paired_outcome": "both_solve",
    }


def _write_run7_scorecards(root: Path, details: list[dict]) -> Path:
    family = root / "tasks" / "scope-authority-boundary"
    for index, detail in enumerate(details):
        task_dir = family / f"task-{index}"
        task_dir.mkdir(parents=True)
        (task_dir / "scorecard.json").write_text(json.dumps(_scorecard(f"task-{index}", detail)))
    return root


def test_sequential_helper_counts_each_stage_once():
    assert treatment_sequential_elapsed_ms(_detail(10.0)) == 10.0
    assert treatment_sequential_elapsed_ms(_detail(10.0, 30.0)) == 40.0


def test_run7_aggregate_mixed_and_physical_cost_separate(tmp_path, monkeypatch):
    output = _write_run7_scorecards(tmp_path, [_detail(10.0), _detail(10.0, 30.0)])
    aggregate_path = output / "aggregate.json"
    aggregate_path.write_text(json.dumps({"control_validated_solves": 2, "treatment_final_validated_solves": 2, "treatment_post_baseline_elapsed_ms": 23.0, "resource_reduced": True, "economic_routing_success": True, "physical_execution_resource_history": {"total_model_call_attempts": 6, "realized_elapsed_ms_by_role": {"worker": 60.0}}}))
    aggregate = run8_aggregation.aggregate_future_run8(output)
    assert aggregate["treatment_post_baseline_elapsed_ms"] == 50.0
    assert aggregate["resource_reduced"] is True
    assert aggregate["physical_execution_resource_history"]["total_model_call_attempts"] == 6


def test_run7_aggregate_all_local_pass_and_all_escalate(tmp_path):
    all_pass = _write_run7_scorecards(tmp_path / "pass", [_detail(10.0), _detail(20.0)])
    (all_pass / "aggregate.json").write_text(json.dumps({"control_validated_solves": 2, "treatment_final_validated_solves": 2}))
    pass_aggregate = run8_aggregation.aggregate_future_run8(all_pass)
    assert pass_aggregate["treatment_post_baseline_elapsed_ms"] == 30.0

    all_escalate = _write_run7_scorecards(tmp_path / "escalate", [_detail(10.0, 30.0), _detail(20.0, 40.0)])
    (all_escalate / "aggregate.json").write_text(json.dumps({"control_validated_solves": 2, "treatment_final_validated_solves": 2}))
    escalate_aggregate = run8_aggregation.aggregate_future_run8(all_escalate)
    assert escalate_aggregate["treatment_post_baseline_elapsed_ms"] == 100.0


def test_old_final_stage_only_calculation_is_the_run8_undercount(tmp_path):
    output = _write_run7_scorecards(tmp_path, [_detail(13176.262, 41075.11), _detail(11419.967, 42628.641)])
    (output / "aggregate.json").write_text(json.dumps({"control_validated_solves": 2, "treatment_final_validated_solves": 2}))
    corrected = run8_aggregation.aggregate_future_run8(output)
    old_final_only = 41075.11 + 42628.641
    assert old_final_only == 83703.751
    assert corrected["treatment_post_baseline_elapsed_ms"] == pytest.approx(108299.98)
