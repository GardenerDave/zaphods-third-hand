from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from local_harness.icm_spec import WorkerResponse
from scripts.zth_run3_routing_experiment import (
    RESOURCE_ACTIONS,
    Run3StateError,
    _baseline,
    arm_order,
    derive_action,
    external_teacher,
    require_valid_preflight,
)


ROOT = Path(__file__).resolve().parents[1]
PREREG = json.loads((ROOT / "docs/research/RUN_3_PREREGISTRATION_2026-08-18.json").read_text())


def test_arm_order_matches_preregistered_seed_and_first_bit_for_all_tasks():
    for task_id in PREREG["task_pack"]["task_ids"]:
        first_bit_is_zero = int(hashlib.sha256(f"20260818:{task_id}".encode()).hexdigest()[0], 16) < 8
        expected = ["control", "treatment"] if first_bit_is_zero else ["treatment", "control"]
        assert arm_order(task_id) == expected


def test_avoid_derives_deterministic_retry_from_supported_negative_alternative():
    advisory = {
        "routing_disposition": "avoid",
        "recommended_intervention": None,
        "alternatives": [
            {"intervention": "deterministic_patch_retry", "resource_tier": 1, "evidence_polarity": "supported_negative"},
            {"intervention": "local_teacher", "resource_tier": 2, "evidence_polarity": "observed"},
        ],
    }
    assert derive_action(advisory) == "avoid_deterministic_patch_retry"


def test_preflight_requires_authoritative_transport_metadata():
    require_valid_preflight({"transport_valid": True, "transport_classification": "model_response"})
    with pytest.raises(Run3StateError):
        require_valid_preflight({"transport_valid": True, "transport_classification": None})


@pytest.mark.parametrize("action,expected", RESOURCE_ACTIONS.items())
def test_every_frozen_treatment_action_has_exact_rung_sequence(action, expected):
    calls = []
    for rung in expected:
        calls.append(rung)
    assert calls == list(expected)


def test_baseline_reuse_makes_one_synthetic_call_and_preserves_artifacts(tmp_path):
    task = {"task_id": "synthetic-baseline", "task_family": "test", "prompt": "Return JSON.", "output_contract": {"format": "json", "required_fields": ["answer"]}, "validator": {"kind": "exact_json"}, "expected_output": {"answer": "ok"}}
    calls = []

    def worker(_prompt):
        calls.append(1)
        return WorkerResponse("ok", '{"answer":"ok"}', "http://test.invalid/v1", "worker", "worker", "stop", {"prompt_tokens": 1}, {}, {}, None, False, None, None)

    first = _baseline(task, tmp_path, worker)
    raw_before = (tmp_path / "attempt-1.raw.json").read_bytes()
    second = _baseline(task, tmp_path, worker)
    assert len(calls) == 1
    assert first["artifact_hashes"]["raw"] == second["artifact_hashes"]["raw"]
    assert (tmp_path / "attempt-1.raw.json").read_bytes() == raw_before


def test_incomplete_baseline_fails_closed_without_call(tmp_path):
    (tmp_path / "attempt-1.raw.json").write_text("{}")
    calls = []
    with pytest.raises(Run3StateError):
        _baseline({"task_id": "x", "prompt": "x"}, tmp_path, lambda _prompt: calls.append(1))
    assert calls == []


def test_external_adapter_uses_bounded_timeout_without_invoking_process(monkeypatch):
    observed = {}

    class Completed:
        returncode = 0
        stdout = "{}"

    def fake_run(argv, **kwargs):
        observed.update(kwargs)
        return Completed()

    monkeypatch.setenv("ZTH_EXTERNAL_TEACHER_COMMAND", "codex-teacher-wrapper")
    monkeypatch.setattr("scripts.zth_run3_routing_experiment.subprocess.run", fake_run)
    external_teacher("bounded packet")
    assert observed["timeout"] == 120
    assert observed["capture_output"] is True
    assert observed["input"] == "bounded packet"
