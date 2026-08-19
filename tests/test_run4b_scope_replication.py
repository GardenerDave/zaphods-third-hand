from __future__ import annotations

import json
import subprocess
import hashlib
from pathlib import Path

import pytest

from local_harness.icm_spec import WorkerResponse
from local_harness.run4b_scope_fixture_pack import (
    failure_classes,
    representative_output,
    select_included_candidates,
    verify_manifest,
)
from local_harness.supervised_capability_loop import load_task_fixture
from scripts.zth_run4a_intervention_calibration import Run4ADriverError
import scripts.zth_run4b_scope_replication as run4b_driver
from scripts.zth_run4b_scope_replication import aggregate_results, execution_resource_history, run_baseline, run_experiment, validate_preregistration


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "local_harness/fixtures/capability_loop/reviewed_run4b_scope"
PREREG = ROOT / "docs/research/RUN_4B_SCOPE_INTERVENTION_REPLICATION_PREREGISTRATION_2026-08-19.json"


def _response(content: str, *, model: str = "fixture-model") -> WorkerResponse:
    return WorkerResponse("ok", content, "http://fixture.invalid/v1", model, model, "stop", {}, {}, None)


def test_run4b_pack_is_fresh_self_verifying_and_failure_class_bound():
    manifest = verify_manifest(PACK, ROOT)
    assert manifest["candidate_count"] == 15
    assert manifest["target_included_count"] == 12
    assert manifest["task_family"] == "scope-authority-boundary"
    assert manifest["target_evidence_resolution"] == "failure_class"
    assert manifest["model_outputs_consulted"] is False
    audit = json.loads((PACK / "novelty_audit.json").read_text())
    assert audit["task_id_collisions"] == []
    assert audit["exact_prompt_duplicates"] == []
    assert audit["normalized_prompt_duplicates"] == []
    assert audit["high_similarity_pairs"] == []
    assert audit["source_document_collisions"] == []
    assert audit["source_anchor_collisions"] == []
    assert audit["counts"] == {"candidates": 15, "new_source": 15, "new_scenario_same_family": 0, "source_document_reuse": 0, "source_anchor_reuse": 0}
    for row in manifest["fixtures"]:
        task = load_task_fixture(ROOT / row["path"])
        assert task["calibration"]["target_evidence_resolution"] == "failure_class"
        assert task["calibration"]["target_evidence_key"] == "scope-authority-boundary"
        assert task["calibration"]["target_failure_classes"] == ["authority_boundary", "reference_fact_application", "unsupported_inference"]


def test_run4b_selection_is_first_twelve_eligible_and_reserves_rest():
    order = [f"run4b-scope-{n:03d}" for n in range(1, 16)]
    selected, reserve = select_included_candidates(order, set(order[:4]) | {order[4], order[5], order[6], order[7], order[8], order[9], order[10], order[11], order[12]})
    assert selected == order[:12]
    assert reserve == order[12:]
    selected, reserve = select_included_candidates(order, set(order[0:2]) | set(order[4:14]))
    assert selected == [order[0], order[1], *order[4:14]][:12]
    assert order[14] in reserve


def test_run4b_pair_orders_match_preregistration_and_only_two_frozen_arms():
    manifest = verify_manifest(PACK, ROOT)
    prereg = json.loads(PREREG.read_text())
    assert manifest["pair_order"]["seed"] == 20260823
    assert manifest["pair_order"]["orders"] == prereg["pair_order"]["orders"]
    assert set(prereg["pair_order"]["orders"]["run4b-scope-001"]) == {"control", "treatment"}
    assert prereg["interventions"] == {"control": "external_teacher", "treatment": "local_teacher", "deterministic_patch": False, "fallback_escalation": False, "semantics": prereg["interventions"]["semantics"]}


def test_run4b_preregistration_dry_run_makes_zero_model_calls():
    result = subprocess.run(["python3", "scripts/zth_run4b_scope_replication.py", "--preregistration", str(PREREG), "--output-dir", "/tmp/run4b-scope-test-dry"], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "dry_run_valid"
    assert payload["model_calls"] == 0
    assert payload["control"] == "external_teacher"
    assert payload["treatment"] == "local_teacher"


def test_run4b_stub_execution_has_exactly_two_teacher_arms_and_no_patch(tmp_path: Path):
    context = validate_preregistration(PREREG, ROOT)
    tasks = {row["task_id"]: load_task_fixture(ROOT / row["path"]) for row in context["manifest"]["fixtures"]}
    calls = {"worker": 0, "local_teacher": 0, "external_teacher": 0}

    def worker(prompt: str) -> WorkerResponse:
        calls["worker"] += 1
        for task in tasks.values():
            if prompt == task["prompt"]:
                return _response("{}")
            if task["prompt"] in prompt:
                return _response(json.dumps(representative_output(task), sort_keys=True))
        return _response("{}")

    teacher = lambda _: (calls.__setitem__("local_teacher", calls["local_teacher"] + 1) or _response(json.dumps({"failure_classification": "synthetic", "teacher_diagnosis": "review", "retry_guidance": "Return the bounded JSON."}), model="local-teacher"))
    external = lambda _: (calls.__setitem__("external_teacher", calls["external_teacher"] + 1) or ("codex-fixture", json.dumps({"failure_classification": "synthetic", "teacher_diagnosis": "review", "retry_guidance": "Return the bounded JSON."})))
    result = run_experiment(context, tmp_path / "execution", worker=worker, local_teacher=teacher, external_teacher=external)
    assert result["status"] == "experiment_completed"
    assert calls == {"worker": 39, "local_teacher": 12, "external_teacher": 12}
    selected = json.loads((tmp_path / "execution" / "selection.json").read_text())["included_task_ids"]
    assert selected == context["manifest"]["candidate_order"][:12]
    summaries = list((tmp_path / "execution" / "tasks").glob("*/arms/*/arm_summary.json"))
    assert len(summaries) == 24
    for path in summaries:
        summary = json.loads(path.read_text())
        assert summary["intervention"] in {"local_teacher", "external_teacher"}
        assert summary["intervention"] != "deterministic_patch_retry"
    aggregate = json.loads((tmp_path / "execution" / "aggregate.json").read_text())
    assert aggregate["comparable_pairs"] == 12
    assert aggregate["infrastructure_excluded_pairs"] == 0
    history = aggregate["execution_resource_history"]
    assert history["attempts_by_role"] == {"external_teacher": 12, "local_teacher": 12, "worker": 39}
    assert history["total_model_call_attempts"] == 63


def _stub_callbacks(tasks, calls):
    def worker(prompt: str) -> WorkerResponse:
        calls["worker"] += 1
        for task in tasks.values():
            if prompt == task["prompt"]:
                return _response("{}")
            if task["prompt"] in prompt:
                return _response(json.dumps(representative_output(task), sort_keys=True))
        return _response("{}")

    def local(prompt: str) -> WorkerResponse:
        calls["local_teacher"] += 1
        return _response(json.dumps({"failure_classification": "synthetic", "teacher_diagnosis": "review", "retry_guidance": "Return bounded JSON."}), model="local-teacher")

    def external(prompt: str):
        calls["external_teacher"] += 1
        return "codex-fixture", json.dumps({"failure_classification": "synthetic", "teacher_diagnosis": "review", "retry_guidance": "Return bounded JSON."})

    return worker, local, external


def test_run4b_partial_resume_reuses_terminal_work_without_duplicates(tmp_path: Path, monkeypatch):
    context = validate_preregistration(PREREG, ROOT)
    tasks = {row["task_id"]: load_task_fixture(ROOT / row["path"]) for row in context["manifest"]["fixtures"]}
    calls = {"worker": 0, "local_teacher": 0, "external_teacher": 0}
    worker, local, external = _stub_callbacks(tasks, calls)
    output = tmp_path / "partial"
    real_arm = run4b_driver.run_isolated_intervention_arm
    interrupted = {"value": False}

    def stop_after_first_terminal_arm(*args, **kwargs):
        result = real_arm(*args, **kwargs)
        if not interrupted["value"]:
            interrupted["value"] = True
            raise RuntimeError("synthetic clean interruption after terminal arm")
        return result

    monkeypatch.setattr(run4b_driver, "run_isolated_intervention_arm", stop_after_first_terminal_arm)
    with pytest.raises(RuntimeError, match="clean interruption"):
        run_experiment(context, output, worker=worker, local_teacher=local, external_teacher=external)
    first_task = context["manifest"]["candidate_order"][0]
    first_arm = context["manifest"]["pair_order"]["orders"][first_task][0]
    run4b_driver._write_arm_artifact_index(output / "tasks" / first_task / "arms" / first_arm)
    manifest_path = output / "execution_manifest.json"
    execution = json.loads(manifest_path.read_text())
    assert execution["active_call"]["kind"] == "paired_arm"
    execution.pop("active_call")
    manifest_path.write_text(json.dumps(execution))
    monkeypatch.setattr(run4b_driver, "run_isolated_intervention_arm", real_arm)
    resumed = run_experiment(context, output, worker=worker, local_teacher=local, external_teacher=external)
    assert resumed["status"] == "experiment_completed"
    assert calls == {"worker": 39, "local_teacher": 12, "external_teacher": 12}
    assert json.loads((output / "selection.json").read_text())["included_task_ids"] == context["manifest"]["candidate_order"][:12]


def test_run4b_terminal_states_and_unbound_directory_fail_closed(tmp_path: Path):
    context = validate_preregistration(PREREG, ROOT)
    base = {"schema": "zth_run4b_scope_execution_manifest_v1", "preregistration_sha256": hashlib.sha256(context["preregistration_path"].read_bytes()).hexdigest(), "fixture_pack_sha256": context["manifest"]["pack_sha256"], "pair_orders": context["manifest"]["pair_order"]["orders"]}
    for status in ("experiment_completed", "experiment_incomplete"):
        out = tmp_path / status
        out.mkdir()
        payload = {**base, "status": status, "completed_at": "2026-08-19T00:00:00+00:00"}
        (out / "execution_manifest.json").write_text(json.dumps(payload))
        result = run_experiment(context, out, worker=lambda _: (_ for _ in ()).throw(AssertionError("duplicate worker")))
        assert result["status"] == status
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    (unrelated / "unbound.txt").write_text("not a Run 4B execution")
    with pytest.raises(Run4ADriverError, match="lacks a bound execution manifest"):
        run_experiment(context, unrelated, worker=lambda _: (_ for _ in ()).throw(AssertionError("no call")))


def test_run4b_baseline_terminal_reuse_and_started_state_fail_closed(tmp_path: Path):
    context = validate_preregistration(PREREG, ROOT)
    row = context["manifest"]["fixtures"][0]
    task = load_task_fixture(ROOT / row["path"])
    calls = {"worker": 0}

    def worker(prompt: str) -> WorkerResponse:
        calls["worker"] += 1
        return _response("{}")

    candidate = tmp_path / "candidate"
    first = run_baseline(task, candidate, worker=worker)
    second = run_baseline(task, candidate, worker=lambda _: (_ for _ in ()).throw(AssertionError("duplicate baseline")))
    assert first == second
    assert calls["worker"] == 1
    interrupted = tmp_path / "interrupted"
    (interrupted / "state.json").parent.mkdir(parents=True)
    (interrupted / "state.json").write_text(json.dumps({"state": "baseline_started", "task_id": task["task_id"], "attempt": 1}))
    with pytest.raises(Run4ADriverError, match="baseline interrupted"):
        run_baseline(task, interrupted, worker=lambda _: (_ for _ in ()).throw(AssertionError("no retry")))


def test_run4b_infrastructure_excluded_pair_preserves_attempted_resource_history(tmp_path: Path):
    output = tmp_path / "infra"
    (output / "tasks" / "one" / "arms" / "control").mkdir(parents=True)
    (output / "tasks" / "one" / "arms" / "treatment").mkdir(parents=True)
    (output / "execution_manifest.json").write_text("{}")
    control = output / "tasks/one/arms/control"
    treatment = output / "tasks/one/arms/treatment"
    (control / "trajectory.jsonl").write_text(json.dumps({"transition": "call_started", "call_id": "external_teacher:1", "role": "external_teacher"}) + "\n" + json.dumps({"transition": "response_captured", "call_id": "external_teacher:1", "artifact_ref": "external_teacher.raw.json"}) + "\n")
    (control / "external_teacher.raw.json").write_text(json.dumps({"transport_valid": True, "transport_classification": "model_response", "resource_telemetry": {"elapsed_ms": 5}}))
    (treatment / "trajectory.jsonl").write_text(json.dumps({"transition": "call_started", "call_id": "local_teacher:1", "role": "local_teacher"}) + "\n" + json.dumps({"transition": "infrastructure_failed", "call_id": "local_teacher:1", "role": "local_teacher", "artifact_ref": "local_teacher.infrastructure.json"}) + "\n")
    (treatment / "local_teacher.infrastructure.json").write_text(json.dumps({"classification": "transport_request_error", "capability_verdict_available": False, "resource_telemetry": {"elapsed_ms": 7}}))
    pair = {"disposition": "infrastructure_excluded", "valid_arms": {"control": True, "treatment": False}, "infrastructure_failures": [{"arm": "treatment", "role": "local_teacher", "artifact": "local_teacher.infrastructure.json"}], "control": {"rescue": True, "elapsed_ms": 5}, "treatment": {"rescue": False, "elapsed_ms": None}, "paired_outcome": "control_only"}
    (output / "tasks/one/pair_summary.json").write_text(json.dumps(pair))
    result = aggregate_results({}, output)
    assert result["selected_pairs"] == 1
    assert result["comparable_pairs"] == 0
    assert result["infrastructure_excluded_pairs"] == 1
    assert result["result_available"] is False
    assert result["quality_preserved"] is None
    assert result["resource_reduced"] is None
    assert result["infrastructure_exclusions"]["by_arm"] == {"treatment": 1}
    history = execution_resource_history(output)
    assert history["attempts_by_role"] == {"external_teacher": 1, "local_teacher": 1}
    assert history["infrastructure_failures_by_role"] == {"local_teacher": 1}
    assert history["total_model_call_attempts"] == 2


def test_run4b_corrupted_terminal_arm_is_rejected(tmp_path: Path):
    context = validate_preregistration(PREREG, ROOT)
    tasks = {row["task_id"]: load_task_fixture(ROOT / row["path"]) for row in context["manifest"]["fixtures"]}
    calls = {"worker": 0, "local_teacher": 0, "external_teacher": 0}
    worker, local, external = _stub_callbacks(tasks, calls)
    output = tmp_path / "corrupt"
    run_experiment(context, output, worker=worker, local_teacher=local, external_teacher=external)
    first = context["manifest"]["candidate_order"][0]
    arm = output / "tasks" / first / "arms" / context["manifest"]["pair_order"]["orders"][first][0]
    artifact = next(path for path in arm.iterdir() if path.name not in {"arm_artifacts.json", "arm_binding.json", "arm_summary.json", "trajectory.jsonl"} and path.is_file())
    artifact.write_text(artifact.read_text() + "\ncorrupt\n")
    execution = json.loads((output / "execution_manifest.json").read_text())
    execution.pop("completed_at")
    execution["status"] = "experiment_running"
    (output / "execution_manifest.json").write_text(json.dumps(execution))
    with pytest.raises(Run4ADriverError, match="artifact hash mismatch"):
        run_experiment(context, output, worker=lambda _: (_ for _ in ()).throw(AssertionError("no duplicate")), local_teacher=lambda _: (_ for _ in ()).throw(AssertionError("no duplicate")), external_teacher=lambda _: (_ for _ in ()).throw(AssertionError("no duplicate")))


def test_run4b_active_call_fails_closed(tmp_path: Path):
    context = validate_preregistration(PREREG, ROOT)
    manifest = context["manifest"]
    execution = {"schema": "zth_run4b_scope_execution_manifest_v1", "status": "experiment_running", "preregistration_sha256": context["preregistration_path"].read_bytes() and __import__("hashlib").sha256(context["preregistration_path"].read_bytes()).hexdigest(), "fixture_pack_sha256": manifest["pack_sha256"], "pair_orders": manifest["pair_order"]["orders"], "active_call": {"kind": "baseline", "task_id": manifest["candidate_order"][0]}}
    out = tmp_path / "active"; out.mkdir(); (out / "execution_manifest.json").write_text(json.dumps(execution))
    with pytest.raises(Run4ADriverError):
        run_experiment(context, out, worker=lambda _: (_ for _ in ()).throw(AssertionError("no call")))
