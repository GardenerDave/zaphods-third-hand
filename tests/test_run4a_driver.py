from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from local_harness.icm_spec import WorkerResponse
from local_harness.run4a_fixture_pack import representative_output, verify_manifest
from local_harness.supervised_capability_loop import load_task_fixture
from scripts.zth_run4a_intervention_calibration import (
    Run4ADriverError,
    _arm_terminal,
    run_baseline,
    run_experiment,
    validate_preregistration,
    write_block_selection,
)


ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "docs/research/RUN_4A_PREREGISTRATION_2026-08-19.json"
PACK = ROOT / "local_harness/fixtures/capability_loop/reviewed_v4a"


def _response(content: str, *, model: str = "fixture-model") -> WorkerResponse:
    return WorkerResponse("ok", content, "http://fixture.invalid/v1", model, model, "stop", {}, {}, None)


def _task(name: str = "scope-001") -> dict:
    return load_task_fixture(PACK / f"{name}.json")


def _failed_worker(_: str) -> WorkerResponse:
    return _response("{}")


def test_selection_artifact_uses_all_five_eligibility_results(tmp_path: Path):
    order = ["001", "002", "003", "004", "005"]
    summaries = {
        task_id: {"eligible": task_id != "002", "eligibility_reason": "synthetic"}
        for task_id in order
    }
    result = write_block_selection("synthetic", order, summaries, tmp_path)
    assert result["included_task_ids"] == ["001", "003", "004", "005"]
    assert result["reserve_task_ids"] == ["002"]
    assert result["block_complete"] is True


def test_selection_marks_block_incomplete_without_replacement(tmp_path: Path):
    order = ["001", "002", "003", "004", "005"]
    summaries = {task_id: {"eligible": task_id in {"001", "003"}, "eligibility_reason": "synthetic"} for task_id in order}
    result = write_block_selection("synthetic", order, summaries, tmp_path)
    assert result["included_task_ids"] == ["001", "003"]
    assert result["reserve_task_ids"] == ["002", "004", "005"]
    assert result["block_complete"] is False


def test_baseline_pass_and_infrastructure_are_terminal_and_not_eligible(tmp_path: Path):
    task = _task()
    passed = run_baseline(task, tmp_path / "pass", worker=lambda _: _response(json.dumps(representative_output(task))))
    assert passed["disposition"] == "baseline_pass"
    assert passed["eligible"] is False

    failed = run_baseline(task, tmp_path / "infra", worker=lambda _: WorkerResponse("request_error", "", "fixture", "fixture", "fixture", None, None, None, None, "transport"))
    assert failed["disposition"] == "infrastructure_error"
    assert failed["eligible"] is False
    assert failed["infrastructure_artifact"] == "worker.infrastructure.json"


def test_interrupted_baseline_fails_closed(tmp_path: Path):
    task = _task()
    state_dir = tmp_path / "candidate"
    state_dir.mkdir()
    (state_dir / "state.json").write_text(json.dumps({"state": "baseline_started"}))
    with pytest.raises(Run4ADriverError):
        run_baseline(task, state_dir, worker=_failed_worker)


def test_terminal_arm_requires_binding_and_artifact_hash_index(tmp_path: Path):
    arm = tmp_path / "arm"
    arm.mkdir()
    binding = {"task_id": "x", "intervention": "deterministic_patch_retry"}
    (arm / "arm_binding.json").write_text(json.dumps(binding, sort_keys=True))
    (arm / "arm_summary.json").write_text(json.dumps({"disposition": "ready_for_review"}))
    (arm / "trajectory.jsonl").write_text("")
    with pytest.raises(Run4ADriverError):
        _arm_terminal(arm, binding)


def test_frozen_driver_run_with_stubs_makes_no_real_model_calls(tmp_path: Path):
    context = validate_preregistration(PREREG, ROOT)
    tasks = {row["task_id"]: load_task_fixture(ROOT / row["path"]) for row in context["manifest"]["fixtures"]}
    calls = {"worker": 0, "local_teacher": 0, "external_teacher": 0}
    baseline_pass_task = tasks["run4a-candidate-contradiction-001"]

    def worker(prompt: str) -> WorkerResponse:
        calls["worker"] += 1
        for task in tasks.values():
            if prompt == baseline_pass_task["prompt"]:
                return _response(json.dumps(representative_output(baseline_pass_task)))
            if task["prompt"] in prompt and prompt != task["prompt"]:
                return _response(json.dumps(representative_output(task)))
        return _failed_worker(prompt)

    teacher = json.dumps({"failure_classification": "synthetic", "teacher_diagnosis": "review", "retry_guidance": "Return the contract."})

    def local(_: str) -> WorkerResponse:
        calls["local_teacher"] += 1
        return _response(teacher, model="local-teacher")

    def external(_: str) -> tuple[str, str]:
        calls["external_teacher"] += 1
        return "codex-fixture", teacher

    frozen = context["preregistration"]["frozen_inputs"]
    patch = {"patch_id": frozen["deterministic_patch_id"], "patch_path": str(ROOT / frozen["deterministic_patch_path"]), "patch_sha256": frozen["deterministic_patch_sha256"]}
    capability_bundle = ROOT / ".work/capability_cards/capability_cards.json"
    resource_manifest = ROOT / "docs/research/RUN_4_RESOURCE_WEIGHTS_FREEZE_2026-08-19.json"
    before = (hashlib.sha256(capability_bundle.read_bytes()).hexdigest(), hashlib.sha256(resource_manifest.read_bytes()).hexdigest())
    result = run_experiment(context, tmp_path / "execution", worker=worker, local_teacher=local, external_teacher=external, deterministic_patch=patch)
    assert result["status"] == "experiment_completed"
    assert calls == {"worker": 68, "local_teacher": 16, "external_teacher": 16}
    assert len(list((tmp_path / "execution" / "tasks").glob("*/arms/*/arm_summary.json"))) == 48
    selected_ids = [task_id for selection in result["selections"].values() for task_id in selection["included_task_ids"]]
    assert len(selected_ids) == 16
    assert "run4a-candidate-contradiction-001" not in selected_ids
    assert "run4a-candidate-contradiction-005" in result["selections"]["contradiction-handling"]["included_task_ids"]
    assert not (tmp_path / "execution" / "tasks" / "run4a-candidate-contradiction-001").exists()
    assert all((tmp_path / "execution" / "tasks" / task_id / "arms" / intervention / "arm_artifacts.json").exists() for task_id in selected_ids for intervention in ("deterministic_patch_retry", "local_teacher", "external_teacher"))
    execution_manifest = json.loads((tmp_path / "execution" / "execution_manifest.json").read_text())
    for task_id in selected_ids:
        assert execution_manifest["arm_orders_executed"][task_id] == context["preregistration"]["arm_order"]["orders"][task_id]
    after = (hashlib.sha256(capability_bundle.read_bytes()).hexdigest(), hashlib.sha256(resource_manifest.read_bytes()).hexdigest())
    assert before == after
    calls_before_resume = dict(calls)
    resumed = run_experiment(context, tmp_path / "execution", worker=lambda _: (_ for _ in ()).throw(AssertionError("duplicate model call")), local_teacher=lambda _: (_ for _ in ()).throw(AssertionError("duplicate teacher call")), external_teacher=lambda _: (_ for _ in ()).throw(AssertionError("duplicate external call")), deterministic_patch=patch)
    assert resumed["status"] == "experiment_completed"
    assert calls == calls_before_resume
