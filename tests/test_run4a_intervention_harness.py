from __future__ import annotations

import json
from pathlib import Path

import pytest

from local_harness.icm_spec import WorkerResponse
from local_harness.run4a_fixture_pack import representative_output
from local_harness.run4a_intervention_harness import Run4AIncompleteError, run_isolated_intervention_arm
from local_harness.supervised_capability_loop import _validator_result, load_task_fixture


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "local_harness/fixtures/capability_loop/reviewed_v4a/scope-001.json"


def _response(content: str, *, model: str = "fixture-model") -> WorkerResponse:
    return WorkerResponse("ok", content, "http://fixture.invalid/v1", model, model, "stop", {}, {}, None)


def _task_and_baseline() -> tuple[dict, dict]:
    task = load_task_fixture(FIXTURE)
    failed = {"allowed_targets": [], "held_targets": [], "scope_expansion_required": False, "review_status": "ready_for_review"}
    validation = _validator_result(json.dumps(failed), task, attempt_id="baseline")
    assert validation["validation_status"] == "failed"
    return task, {"task_id": task["task_id"], "transport_valid": True, "transport_classification": "model_response", "validation": validation, "raw": {"status": "ok", "content": json.dumps(failed)}}


def _patch(tmp_path: Path) -> dict:
    path = tmp_path / "patch.json"
    payload = {"candidate_patch_id": "fixture-patch", "prompt_delta": "Use the declared contract and return JSON only."}
    path.write_text(json.dumps(payload))
    import hashlib
    return {"patch_id": "fixture-patch", "patch_path": str(path), "patch_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


@pytest.mark.parametrize("intervention", ["deterministic_patch_retry", "local_teacher", "external_teacher"])
def test_isolated_arm_makes_exactly_one_intervention_and_worker_retry(tmp_path: Path, intervention: str):
    task, baseline = _task_and_baseline()
    calls = {"worker": 0, "local_teacher": 0, "external_teacher": 0}
    output = json.dumps(representative_output(task))
    teacher = json.dumps({"failure_classification": "fixture", "teacher_diagnosis": "review", "retry_guidance": "Return the declared JSON contract."})

    def worker(_prompt: str):
        calls["worker"] += 1
        return _response(output)

    def local(_prompt: str):
        calls["local_teacher"] += 1
        return _response(teacher, model="local-teacher")

    def external(_prompt: str):
        calls["external_teacher"] += 1
        return "codex-fixture", teacher

    summary = run_isolated_intervention_arm(
        task, baseline, intervention=intervention, out_dir=tmp_path / intervention,
        worker=worker, local_teacher=local, external_teacher=external,
        deterministic_patch=_patch(tmp_path) if intervention == "deterministic_patch_retry" else None,
    )
    assert summary["disposition"] == "ready_for_review"
    assert summary["deterministically_validated_rescue"] is True
    assert calls["worker"] == 1
    assert calls["local_teacher"] == (1 if intervention == "local_teacher" else 0)
    assert calls["external_teacher"] == (1 if intervention == "external_teacher" else 0)
    assert (tmp_path / intervention / "arm_summary.json").is_file()


def test_baseline_success_cannot_start_an_intervention_arm(tmp_path: Path):
    task = load_task_fixture(FIXTURE)
    baseline = {"task_id": task["task_id"], "transport_valid": True, "transport_classification": "model_response", "validation": {"validation_status": "passed"}}
    with pytest.raises(ValueError, match="baseline failure"):
        run_isolated_intervention_arm(task, baseline, intervention="local_teacher", out_dir=tmp_path / "arm", local_teacher=lambda _: _response("{}"))
    assert not (tmp_path / "arm").exists()


def test_transport_failure_is_infrastructure_only(tmp_path: Path):
    task, baseline = _task_and_baseline()
    def worker(_prompt: str):
        return WorkerResponse("request_error", "", "fixture", "fixture-model", "fixture-model", None, None, None, None, "Operation not permitted")
    summary = run_isolated_intervention_arm(task, baseline, intervention="deterministic_patch_retry", out_dir=tmp_path / "arm", worker=worker, deterministic_patch=_patch(tmp_path))
    assert summary["disposition"] == "infrastructure_error"
    assert summary["capability_verdict_available"] is False
    assert not (tmp_path / "arm" / "worker-retry.validation.json").exists()
    assert (tmp_path / "arm" / "worker.infrastructure.json").is_file()


def test_ambiguous_started_call_fails_closed_without_duplicate(tmp_path: Path):
    task, baseline = _task_and_baseline()
    arm = tmp_path / "arm"
    arm.mkdir()
    (arm / "trajectory.jsonl").write_text(json.dumps({"transition": "call_started", "call_id": "worker:worker-retry"}) + "\n")
    with pytest.raises(Run4AIncompleteError):
        run_isolated_intervention_arm(task, baseline, intervention="deterministic_patch_retry", out_dir=arm, worker=lambda _: _response("{}"), deterministic_patch=_patch(tmp_path))
