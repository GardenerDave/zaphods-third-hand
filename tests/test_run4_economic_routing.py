from __future__ import annotations

import json
import hashlib
import os
import subprocess
from pathlib import Path

import pytest

from local_harness.icm_spec import WorkerResponse
from local_harness.run4_economic_fixture_pack import pair_orders, verify_manifest
from local_harness.run4_economic_policy import choose_intervention, verify_policy_freeze
from local_harness.supervised_capability_loop import load_task_fixture
from local_harness.run4a_intervention_harness import run_isolated_intervention_arm
from scripts.zth_run4_economic_routing import (
    Run4ADriverError,
    _baseline_payload,
    _json_write,
    _write_arm_artifact_index,
    aggregate_results,
    canonical_sha256,
    run_baseline,
    run_experiment,
    validate_preregistration,
)


ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "docs/research/RUN_4_ECONOMIC_ROUTING_PREREGISTRATION_2026-08-19.json"
PACK = ROOT / "local_harness/fixtures/capability_loop/reviewed_run4_economic_triage"
POLICY = ROOT / "docs/research/RUN_4_ECONOMIC_ROUTING_POLICY_FREEZE_2026-08-19.json"
COMPARATIVE = ROOT / "docs/research/RUN_4A_COMPARATIVE_EVIDENCE_FREEZE_2026-08-19.json"


def _response(content: str, *, model: str = "fixture-model") -> WorkerResponse:
    return WorkerResponse("ok", content, "http://fixture.invalid/v1", model, model, "stop", {}, {}, None)


def _valid_output(task: dict) -> str:
    facts = task["validator"]["reference_facts"]
    phrase = " ".join(facts["must_include"])
    return json.dumps({"route": phrase, "rationale": phrase, "review_status": facts["review_status"]})


def test_policy_matrix_exactly_matches_frozen_run4a_evidence():
    evidence = json.loads(COMPARATIVE.read_text())
    expected = {
        "contradiction-handling": ("deterministic_patch_retry", "deterministic_patch_retry"),
        "triage-routing": ("external_teacher", "deterministic_patch_retry"),
        "scope-authority-boundary": ("local_teacher", "local_teacher"),
        "unsupported-certainty": ("deterministic_patch_retry", "deterministic_patch_retry"),
    }
    for key, (control, treatment) in expected.items():
        assert choose_intervention(evidence, key, "capability_first")["recommended_intervention"] == control
        assert choose_intervention(evidence, key, "cheapest_supported_positive")["recommended_intervention"] == treatment
    assert sum(control != treatment for control, treatment in expected.values()) == 1


def test_negative_and_missing_positive_evidence_cannot_be_selected():
    evidence = {"blocks": {"triage-routing": {
        "deterministic_patch_retry": {"evidence_status": "supported_negative", "rescue_rate": 0.0, "expected_immediate_action_cost_ms": 5276.567},
        "local_teacher": {"evidence_status": "observed", "rescue_rate": 1.0, "expected_immediate_action_cost_ms": 21497.191},
        "external_teacher": {"evidence_status": "insufficient", "rescue_rate": 1.0, "expected_immediate_action_cost_ms": 33980.579},
    }}}
    assert choose_intervention(evidence, "triage-routing", "capability_first")["routing_disposition"] == "abstain"


def test_fixture_manifest_has_fifteen_candidates_and_pair_order_is_reproducible():
    manifest = verify_manifest(PACK, ROOT)
    assert manifest["candidate_count"] == 15
    assert manifest["target_included_count"] == 12
    assert manifest["candidate_order"] == sorted(manifest["candidate_order"])
    assert manifest["pair_order"]["orders"] == pair_orders(manifest["candidate_order"])
    assert len(manifest["pair_order"]["orders"]) == 15


def test_policy_freeze_is_self_verifying():
    freeze = verify_policy_freeze(POLICY, COMPARATIVE, ROOT / "local_harness/run4_economic_policy.py")
    assert freeze["authority"] == "experiment_only_advisory_policy"


def test_dry_run_validation_requires_no_model_calls():
    context = validate_preregistration(PREREG, ROOT)
    assert context["preregistration"]["model_calls_made"] is False


def test_paired_driver_with_stubs_runs_two_arms_and_no_local_teacher(tmp_path: Path):
    context = validate_preregistration(PREREG, ROOT)
    context["preregistration_path"] = PREREG
    context["git_head"] = "synthetic"
    tasks = {row["task_id"]: load_task_fixture(PACK / Path(row["path"]).name) for row in context["manifest"]["fixtures"]}
    calls = {"worker": 0, "local": 0, "external": 0}

    def worker(prompt: str) -> WorkerResponse:
        calls["worker"] += 1
        for task in tasks.values():
            if prompt == task["prompt"]:
                return _response("{}")
            if task["prompt"] in prompt:
                return _response(_valid_output(task))
        return _response("{}")

    def local(_: str) -> WorkerResponse:
        calls["local"] += 1
        return _response("{}", model="local")

    def external(_: str):
        calls["external"] += 1
        return "codex-fixture", json.dumps({"failure_classification": "synthetic", "teacher_diagnosis": "review", "retry_guidance": "Return the bounded JSON."})

    frozen = context["preregistration"]["frozen_inputs"]
    patch = {"patch_id": frozen["deterministic_patch_id"], "patch_path": str(ROOT / frozen["deterministic_patch_path"]), "patch_sha256": frozen["deterministic_patch_sha256"]}
    result = run_experiment(context, tmp_path / "run", worker=worker, local_teacher=local, external_teacher=external, deterministic_patch=patch)
    assert result["status"] == "experiment_completed"
    assert calls == {"worker": 39, "local": 0, "external": 12}
    aggregate = json.loads((tmp_path / "run" / "aggregate.json").read_text())
    assert aggregate["selected_pairs"] == 12
    assert aggregate["control"]["validated_passes"] == 12
    assert aggregate["treatment"]["validated_passes"] == 12
    assert aggregate["control"]["external_teacher_calls"] == 12
    assert aggregate["treatment"]["external_teacher_calls"] == 0
    env = os.environ.copy()
    env.update({
        "ZTH_CAPABILITY_WORKER_MODEL": "Qwen_Qwen3-1.7B-Q4_K_M.gguf",
        "ZTH_CAPABILITY_TEACHER_MODEL": "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf",
        "ZTH_EXTERNAL_TEACHER_IDENTITY": "codex-cli-0.146.0",
    })
    resumed = subprocess.run(
        ["python3", "scripts/zth_run4_economic_routing.py", "--preregistration", str(PREREG), "--output-dir", str(tmp_path / "run"), "--execute"],
        cwd=ROOT, env=env, capture_output=True, text=True,
    )
    assert resumed.returncode == 0, resumed.stderr


def test_active_call_fails_closed_before_any_resume_call(tmp_path: Path):
    context = validate_preregistration(PREREG, ROOT)
    context["preregistration_path"] = PREREG
    context["git_head"] = "synthetic"
    output = tmp_path / "run"
    output.mkdir()
    (output / "execution_manifest.json").write_text(json.dumps({
        "schema": "zth_run4_economic_execution_manifest_v1",
        "status": "experiment_running",
        "preregistration_sha256": hashlib.sha256(PREREG.read_bytes()).hexdigest(),
        "fixture_pack_sha256": context["manifest"]["pack_sha256"],
        "arm_orders": context["manifest"]["pair_order"]["orders"],
        "active_call": {"task_id": "x", "arm": "control"},
    }))
    with pytest.raises(Run4ADriverError, match="ambiguous active call"):
        run_experiment(context, output, worker=lambda _: (_ for _ in ()).throw(AssertionError("call")), local_teacher=lambda _: _response("{}"), external_teacher=lambda _: ("x", "{}"), deterministic_patch={})


def test_terminal_incomplete_is_reused_without_calls_and_unbound_directory_fails(tmp_path: Path):
    context = validate_preregistration(PREREG, ROOT)
    context["preregistration_path"] = PREREG
    context["git_head"] = "synthetic"
    base = {
        "schema": "zth_run4_economic_execution_manifest_v1",
        "status": "experiment_incomplete",
        "completed_at": "synthetic-closeout",
        "preregistration_sha256": hashlib.sha256(PREREG.read_bytes()).hexdigest(),
        "fixture_pack_sha256": context["manifest"]["pack_sha256"],
        "arm_orders": context["manifest"]["pair_order"]["orders"],
    }
    terminal = tmp_path / "terminal"
    terminal.mkdir()
    (terminal / "execution_manifest.json").write_text(json.dumps(base))
    result = run_experiment(context, terminal, worker=lambda _: (_ for _ in ()).throw(AssertionError("duplicate")), local_teacher=lambda _: _response("{}"), external_teacher=lambda _: ("x", "{}"), deterministic_patch={})
    assert result["status"] == "experiment_incomplete"
    unbound = tmp_path / "unbound"
    unbound.mkdir()
    (unbound / "unrelated.txt").write_text("do not overwrite")
    with pytest.raises(Run4ADriverError, match="lacks a bound execution manifest"):
        run_experiment(context, unbound, worker=lambda _: _response("{}"), local_teacher=lambda _: _response("{}"), external_teacher=lambda _: ("x", "{}"), deterministic_patch={})


def test_infrastructure_excluded_pair_is_outside_quality_and_cost_denominators(tmp_path: Path):
    output = tmp_path / "run"
    (output / "tasks" / "one").mkdir(parents=True)
    (output / "execution_manifest.json").write_text("{}")
    pair = {
        "task_id": "one", "disposition": "infrastructure_excluded",
        "valid_arms": {"control": True, "treatment": False},
        "infrastructure_failures": [{"arm": "treatment", "intervention": "deterministic_patch_retry", "role": "worker", "artifact": "worker.infrastructure.json"}],
        "control": {"rescue": True, "elapsed_ms": 100}, "treatment": {"rescue": False, "elapsed_ms": None},
        "paired_outcome": "control_only",
    }
    (output / "tasks" / "one" / "pair_summary.json").write_text(json.dumps(pair))
    result = aggregate_results({}, output)
    assert result["selected_pairs"] == 1
    assert result["comparable_pairs"] == 0
    assert result["infrastructure_excluded_pairs"] == 1
    assert result["control"]["valid_responses"] == 1
    assert result["control"]["validated_passes"] == 0
    assert result["control"]["solve_rate"] is None
    assert result["quality_preserved"] is None
    assert result["economic_routing_success"] is None
    assert result["infrastructure_exclusions"]["by_role"] == {"worker": 1}


def test_corrupted_terminal_arm_index_cannot_be_reused(tmp_path: Path):
    context = validate_preregistration(PREREG, ROOT)
    context["preregistration_path"] = PREREG
    context["git_head"] = "synthetic"
    tasks = {row["task_id"]: load_task_fixture(PACK / Path(row["path"]).name) for row in context["manifest"]["fixtures"]}
    def worker(prompt: str) -> WorkerResponse:
        for task in tasks.values():
            if prompt == task["prompt"]:
                return _response("{}")
            if task["prompt"] in prompt:
                return _response(_valid_output(task))
        return _response("{}")
    teacher = lambda _: ("codex-fixture", json.dumps({"failure_classification": "synthetic", "teacher_diagnosis": "review", "retry_guidance": "Return JSON."}))
    frozen = context["preregistration"]["frozen_inputs"]
    patch = {"patch_id": frozen["deterministic_patch_id"], "patch_path": str(ROOT / frozen["deterministic_patch_path"]), "patch_sha256": frozen["deterministic_patch_sha256"]}
    run_experiment(context, tmp_path / "run", worker=worker, local_teacher=lambda _: _response("{}"), external_teacher=teacher, deterministic_patch=patch)
    arm = next((tmp_path / "run" / "tasks").glob("*/arms/*"))
    index = json.loads((arm / "arm_artifacts.json").read_text())
    summary = json.loads((arm / "arm_binding.json").read_text())
    artifact_name = next(name for name in index["files"] if name.endswith(".raw.json"))
    (arm / artifact_name).write_text((arm / artifact_name).read_text() + "\ncorruption")
    from scripts.zth_run4_economic_routing import _arm_terminal
    with pytest.raises(Run4ADriverError, match="artifact hash mismatch"):
        _arm_terminal(arm, summary)


def test_clean_partial_resume_reuses_terminal_baseline_and_arm(tmp_path: Path):
    context = validate_preregistration(PREREG, ROOT)
    context["preregistration_path"] = PREREG
    context["git_head"] = "synthetic"
    tasks = {row["task_id"]: load_task_fixture(PACK / Path(row["path"]).name) for row in context["manifest"]["fixtures"]}
    calls = {"worker": 0, "external": 0}
    def worker(prompt: str) -> WorkerResponse:
        calls["worker"] += 1
        for task in tasks.values():
            if prompt == task["prompt"]:
                return _response("{}")
            if task["prompt"] in prompt:
                return _response(_valid_output(task))
        return _response("{}")
    def external(_: str):
        calls["external"] += 1
        return "codex-fixture", json.dumps({"failure_classification": "synthetic", "teacher_diagnosis": "review", "retry_guidance": "Return JSON."})
    execution_dir = tmp_path / "partial"
    first_ids = context["manifest"]["candidate_order"][:3]
    baseline_summaries = {}
    for task_id in first_ids:
        baseline_summaries[task_id] = run_baseline(tasks[task_id], execution_dir / "candidates" / task_id, worker=worker)
    first = first_ids[0]
    baseline = _baseline_payload(execution_dir / "candidates" / first, baseline_summaries[first])
    actual = context["manifest"]["pair_order"]["orders"][first][0]
    actual_intervention = "external_teacher" if actual == "control" else "deterministic_patch_retry"
    arm_dir = execution_dir / "tasks" / first / "arms" / actual
    binding = {"schema": "zth_run4_economic_arm_binding_v1", "task_id": first, "arm": actual, "actual_intervention": actual_intervention, "policy_sha256": context["preregistration"]["frozen_inputs"]["policy_freeze_sha256"], "comparative_freeze_sha256": context["preregistration"]["frozen_inputs"]["comparative_evidence_freeze_sha256"], "baseline_summary_sha256": canonical_sha256(baseline)}
    _json_write(arm_dir / "arm_binding.json", binding)
    frozen = context["preregistration"]["frozen_inputs"]
    patch = {"patch_id": frozen["deterministic_patch_id"], "patch_path": str(ROOT / frozen["deterministic_patch_path"]), "patch_sha256": frozen["deterministic_patch_sha256"]}
    run_isolated_intervention_arm(tasks[first], baseline, intervention=actual_intervention, out_dir=arm_dir, worker=worker, local_teacher=lambda _: _response("{}"), external_teacher=external, deterministic_patch=patch if actual_intervention == "deterministic_patch_retry" else None)
    _write_arm_artifact_index(arm_dir)
    manifest = context["manifest"]
    execution = {"schema": "zth_run4_economic_execution_manifest_v1", "status": "experiment_running", "started_at": "synthetic", "git_head": "synthetic", "preregistration_sha256": hashlib.sha256(PREREG.read_bytes()).hexdigest(), "fixture_pack_sha256": manifest["pack_sha256"], "candidate_states": {task_id: "baseline_terminal" if task_id in first_ids else "baseline_not_started" for task_id in manifest["candidate_order"]}, "arm_orders": manifest["pair_order"]["orders"], "model_calls_started": True}
    _json_write(execution_dir / "execution_manifest.json", execution)
    before = dict(calls)
    result = run_experiment(context, execution_dir, worker=worker, local_teacher=lambda _: _response("{}"), external_teacher=external, deterministic_patch=patch)
    assert result["status"] == "experiment_completed"
    assert calls["worker"] == 39
    assert calls["external"] == 12
    assert before["worker"] < calls["worker"] and before["external"] <= calls["external"]
    assert json.loads((execution_dir / "selection.json").read_text())["included_task_ids"] == manifest["candidate_order"][:12]
