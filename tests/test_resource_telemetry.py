import json
from pathlib import Path

import pytest

from local_harness.resource_telemetry import (
    RESOURCE_TELEMETRY_SCHEMA,
    build_resource_telemetry,
    load_approved_resource_weights,
    validate_resource_telemetry,
)
from local_harness.icm_spec import WorkerResponse
from local_harness.supervised_capability_loop import run_capability_loop


def _response(content: str, model: str) -> WorkerResponse:
    return WorkerResponse("ok", content, "http://fixture.invalid/v1", model, model, "stop", None, None, None)


def _task() -> dict:
    return {
        "task_id": "telemetry-task",
        "task_family": "telemetry",
        "prompt": "Return JSON.",
        "output_contract": {"format": "json"},
        "expected_output": {"answer": "ok"},
    }


def test_common_contract_is_structurally_complete_for_all_roles():
    for role in ("worker", "local_teacher", "external_teacher"):
        record = build_resource_telemetry(
            role=role,
            request_start_monotonic=10.0,
            response_capture_monotonic=10.25,
            response_metadata={"transport_classification": "model_response"},
            model_identity="example-model",
            adapter_server_identity="JARVIS_LOCAL" if role != "external_teacher" else "codex-cli",
            timeout_seconds=120,
        )
        validate_resource_telemetry(record)
        assert record["schema"] == RESOURCE_TELEMETRY_SCHEMA
        assert record["elapsed_ms"] == 250.0
        assert record["hardware_device_identity"] is None


def test_missing_external_usage_is_null_not_zero():
    record = build_resource_telemetry(
        role="external_teacher",
        request_start_monotonic=1.0,
        response_capture_monotonic=2.0,
        response_metadata={"transport_classification": "model_response"},
    )
    assert record["prompt_tokens"] is None
    assert record["completion_tokens"] is None
    assert record["total_tokens"] is None
    assert record["server_prompt_ms"] is None
    assert record["server_generation_ms"] is None


def test_server_usage_and_monotonic_elapsed_are_preserved():
    record = build_resource_telemetry(
        role="worker",
        request_start_monotonic=4.0,
        response_capture_monotonic=4.125,
        response_metadata={
            "model": "worker-model",
            "endpoint_alias": "JARVIS_LOCAL",
            "transport_classification": "model_response",
            "usage": {"prompt_tokens": 4, "completion_tokens": 5, "total_tokens": 9, "prompt_tokens_details": {"cached_tokens": 2}},
            "timings": {"prompt_ms": 3.5, "predicted_ms": 8.5},
        },
    )
    assert record["elapsed_ms"] == 125.0
    assert record["prompt_tokens"] == 4
    assert record["cached_tokens"] == 2
    assert record["server_generation_ms"] == 8.5


def test_resource_weights_require_frozen_approval(tmp_path: Path):
    draft = {
        "schema": "zth_resource_weight_manifest_v1",
        "frozen": False,
        "review_status": "draft",
        "weights": {"worker_call": 1},
    }
    path = tmp_path / "weights.json"
    path.write_text(json.dumps(draft))
    with pytest.raises(ValueError, match="frozen approved"):
        load_approved_resource_weights(path)


def test_historical_artifacts_do_not_require_new_telemetry_fields():
    raw = Path(".work/capability_batch_reviewed_v3c/run3c_execution_2026-08-20/control").glob("*/*.raw.json")
    path = next(raw, None)
    if path is None:
        pytest.skip("historical Run 3C artifacts unavailable")
    payload = json.loads(path.read_text())
    assert payload["metadata"]["transport_classification"] == "model_response"
    # The old artifact remains valid even if it predates resource_telemetry.
    assert "resource_telemetry" not in payload["metadata"] or isinstance(payload["metadata"]["resource_telemetry"], dict)


def test_loop_writes_common_worker_local_and_external_records(tmp_path: Path):
    worker_outputs = iter(['{"answer":"wrong"}', '{"answer":"ok"}'])
    teacher = json.dumps({"failure_classification": "wrong", "teacher_diagnosis": "retry", "retry_guidance": "JSON only"})
    run_capability_loop(
        _task(),
        out_dir=tmp_path / "local",
        worker=lambda _prompt: _response(next(worker_outputs), "worker"),
        local_teacher=lambda _prompt: _response(teacher, "local-teacher"),
        max_worker_attempts=1,
        max_teacher_passes=1,
    )
    local_payload = json.loads((tmp_path / "local" / "local-teacher-1.json").read_text())
    assert local_payload["raw"]["metadata"]["resource_telemetry"]["role"] == "local_teacher"
    worker_payload = json.loads((tmp_path / "local" / "attempt-1.raw.json").read_text())
    assert worker_payload["metadata"]["resource_telemetry"]["role"] == "worker"

    worker_outputs = iter(['{"answer":"wrong"}', '{"answer":"ok"}'])
    run_capability_loop(
        _task(),
        out_dir=tmp_path / "external",
        worker=lambda _prompt: _response(next(worker_outputs), "worker"),
        max_worker_attempts=1,
        max_teacher_passes=0,
        external_teacher=lambda _prompt: ("external-adapter", teacher),
    )
    external_payload = json.loads((tmp_path / "external" / "external-teacher.json").read_text())
    telemetry = external_payload["resource_telemetry"]
    assert telemetry["role"] == "external_teacher"
    assert telemetry["total_tokens"] is None
