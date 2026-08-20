from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from local_harness.icm_spec import WorkerResponse
from local_harness.run7_escalation_policy import (
    EXTERNAL_ACTION_MS,
    LOCAL_ACTION_MS,
    break_even_escalation_count,
    choose_intervention,
    should_escalate,
    verify_policy,
)
from local_harness.run7_scope_fixture_pack import verify_manifest
from local_harness.supervised_capability_loop import _parse_teacher
from scripts import zth_run7_scope_escalation as driver
from scripts.zth_run4a_intervention_calibration import Run4ADriverError

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "docs/research/RUN_7_VALIDATION_GATED_ESCALATION_PREREGISTRATION_2026-08-20.json"
PACK = ROOT / "local_harness/fixtures/capability_loop/run7_scope"
FAMILY = "scope-authority-boundary"


def _response(content: str, model: str = "fixture-model") -> WorkerResponse:
    return WorkerResponse("ok", content, "http://fixture.invalid/v1", model, model, "stop", {}, {}, None)


def _context() -> dict:
    context = driver._load_context(PREREG, ROOT, require_runtime=False)
    context["preregistration_path"] = PREREG
    context["git_head"] = "synthetic-run7-head"
    return context


def _valid(task: dict) -> str:
    facts = task["validator"]["reference_facts"]
    return json.dumps({"allowed_targets": facts["required_allowed_targets"], "held_targets": facts["required_held_targets"], "scope_expansion_required": facts["requires_scope_expansion_flag"], "review_status": facts["review_status"]})


def _invalid(task: dict) -> str:
    return json.dumps({"allowed_targets": [], "held_targets": [], "scope_expansion_required": False, "review_status": "ready_for_review"})


def _callbacks(context: dict, calls: dict[str, int], *, local_pass: bool = False):
    tasks = context["tasks"]

    def worker(prompt: str) -> WorkerResponse:
        calls["worker"] += 1
        for task in tasks.values():
            if prompt == task["prompt"]:
                return _response(_invalid(task))
            if task["prompt"] in prompt:
                if "local_first_validation_failure" in prompt or (local_pass and "intervention" in prompt):
                    return _response(_valid(task))
                if "local_marker" in prompt:
                    return _response(_invalid(task))
        return _response("{}")

    def local(_: str) -> WorkerResponse:
        calls["local_teacher"] += 1
        return _response('{"local_marker":"local","bounded_guidance":"hold unauthorized targets"}', model="local-teacher")

    def external(_: str):
        calls["external_teacher"] += 1
        return "codex-fixture", '{"external_marker":"external","bounded_guidance":"apply recorded authority"}'

    return worker, local, external


def test_run7_policy_and_break_even_are_frozen():
    verify_policy()
    assert choose_intervention("external_everywhere") == "external_teacher"
    assert choose_intervention("validation_gated_economic_escalation") == "local_teacher"
    assert should_escalate({"validation_status": "failed"})
    assert not should_escalate({"validation_status": "passed"})
    assert not should_escalate({"validation_status": "infrastructure_error"})
    assert break_even_escalation_count() == 7
    assert 20 * LOCAL_ACTION_MS + 7 * EXTERNAL_ACTION_MS < 20 * EXTERNAL_ACTION_MS
    assert 20 * LOCAL_ACTION_MS + 8 * EXTERNAL_ACTION_MS >= 20 * EXTERNAL_ACTION_MS


def test_run7_fixture_pack_is_intervention_blind_and_bound():
    manifest = verify_manifest(PACK, ROOT)
    assert len(manifest["fixtures"]) == 24
    assert manifest["target_included_count"] == 20
    assert manifest["target_evidence_resolution"] == "failure_class"
    assert manifest["pair_order"]["seed"] == 20260826
    audit = json.loads((PACK / "novelty_audit.json").read_text())
    assert audit["model_outputs_consulted"] is False
    assert not audit["task_id_collisions"]
    assert not audit["exact_prompt_duplicates"]
    assert not audit["normalized_prompt_duplicates"]
    assert not audit["high_similarity_pairs"]
    assert audit["counts"]["new_source"] == 24


def test_run7_dry_run_makes_zero_model_calls():
    result = subprocess.run(["python3", "scripts/zth_run7_scope_escalation.py", "--preregistration", str(PREREG), "--output-dir", "/tmp/run7-scope-dry"], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"control": "external_direct", "model_calls": 0, "pair_order_seed": 20260826, "status": "dry_run_valid", "treatment": "validation_gated_economic_escalation"}


def test_run7_all_escalate_clean_counts_and_branch_metrics(tmp_path: Path):
    context = _context(); calls = {"worker": 0, "local_teacher": 0, "external_teacher": 0}
    worker, local, external = _callbacks(context, calls)
    result = driver.run_experiment(context, tmp_path / "all-escalate", worker=worker, local_teacher=local, external_teacher=external)
    assert result["status"] == "experiment_completed"
    assert calls == {"worker": 84, "local_teacher": 20, "external_teacher": 40}
    aggregate = json.loads((tmp_path / "all-escalate" / "aggregate.json").read_text())
    assert aggregate["selected_tasks"] == 20
    assert aggregate["local_first_passes"] == 0
    assert aggregate["local_first_failures"] == 20
    assert aggregate["escalations"] == 20
    assert aggregate["escalation_rescues"] == 20
    assert aggregate["comparable_tasks"] == 20


def test_run7_local_pass_has_no_escalations(tmp_path: Path):
    context = _context(); calls = {"worker": 0, "local_teacher": 0, "external_teacher": 0}
    worker, local, external = _callbacks(context, calls, local_pass=True)
    driver.run_experiment(context, tmp_path / "all-pass", worker=worker, local_teacher=local, external_teacher=external)
    assert calls == {"worker": 64, "local_teacher": 20, "external_teacher": 20}
    aggregate = json.loads((tmp_path / "all-pass" / "aggregate.json").read_text())
    assert aggregate["local_first_passes"] == 20
    assert aggregate["escalations"] == 0


def test_run7_escalation_durable_before_treatment_closeout_resume_has_no_duplicates(tmp_path: Path, monkeypatch):
    context = _context(); calls = {"worker": 0, "local_teacher": 0, "external_teacher": 0}; worker, local, external = _callbacks(context, calls); output = tmp_path / "partial"
    original = driver._treatment_summary; interrupted = {"value": False}

    def interrupt_once(*args, **kwargs):
        if not interrupted["value"]:
            interrupted["value"] = True
            raise RuntimeError("clean interruption before escalation closeout")
        return original(*args, **kwargs)

    monkeypatch.setattr(driver, "_treatment_summary", interrupt_once)
    with pytest.raises(RuntimeError, match="before escalation closeout"):
        driver.run_experiment(context, output, worker=worker, local_teacher=local, external_teacher=external)
    manifest = json.loads((output / "execution_manifest.json").read_text())
    assert manifest["status"] == "experiment_running" and "active_call" not in manifest
    monkeypatch.setattr(driver, "_treatment_summary", original)
    resumed = driver.run_experiment(context, output, worker=worker, local_teacher=local, external_teacher=external)
    assert resumed["status"] == "experiment_completed"
    assert calls == {"worker": 84, "local_teacher": 20, "external_teacher": 40}


def test_run7_local_failure_before_escalation_resume_has_no_duplicates(tmp_path: Path, monkeypatch):
    context = _context(); calls = {"worker": 0, "local_teacher": 0, "external_teacher": 0}; worker, local, external = _callbacks(context, calls); output = tmp_path / "pre-escalation"
    original_valid = driver._valid; interrupted = {"value": False}

    def interrupt_after_local(summary):
        if not interrupted["value"] and summary.get("intervention") == "local_teacher":
            interrupted["value"] = True
            raise RuntimeError("clean interruption before escalation active call")
        return original_valid(summary)

    monkeypatch.setattr(driver, "_valid", interrupt_after_local)
    with pytest.raises(RuntimeError, match="before escalation active call"):
        driver.run_experiment(context, output, worker=worker, local_teacher=local, external_teacher=external)
    manifest = json.loads((output / "execution_manifest.json").read_text())
    assert manifest["status"] == "experiment_running"
    assert "active_call" not in manifest
    selected = json.loads((output / "selections" / "scope.json").read_text())["included_task_ids"]
    task_id = selected[0]
    local_dir = output / "tasks" / "scope" / task_id / "local_first"
    assert (local_dir / "arm_summary.json").exists()
    assert (local_dir / "arm_artifacts.json").exists()
    assert not (output / "tasks" / "scope" / task_id / "escalation").exists()
    trajectory = (local_dir / "trajectory.jsonl").read_text()
    assert '"role": "local_teacher"' in trajectory
    assert '"call_id": "worker:worker-retry"' in trajectory
    assert calls["local_teacher"] == 1
    assert calls["external_teacher"] in {0, 1}
    before_resume = dict(calls)
    monkeypatch.setattr(driver, "_valid", original_valid)
    resumed = driver.run_experiment(context, output, worker=worker, local_teacher=local, external_teacher=external)
    assert resumed["status"] == "experiment_completed"
    assert calls == {"worker": 84, "local_teacher": 20, "external_teacher": 40}
    assert calls["local_teacher"] == before_resume["local_teacher"] + 19
    escalation_prompt = next((output / "tasks" / "scope").glob("*/escalation/external_teacher.prompt.txt"))
    prompt_payload = json.loads(escalation_prompt.read_text())
    assert prompt_payload["failed_transitions"][1]["intervention_id"] == "local_first"


def test_run7_terminal_action_corruption_fails_closed(tmp_path: Path):
    context = _context(); calls = {"worker": 0, "local_teacher": 0, "external_teacher": 0}; worker, local, external = _callbacks(context, calls); output = tmp_path / "corrupt"
    driver.run_experiment(context, output, worker=worker, local_teacher=local, external_teacher=external)
    action = next((output / "tasks" / "scope").glob("*/local_first"))
    indexed = [p for p in action.iterdir() if p.name not in {"arm_artifacts.json", "arm_binding.json", "arm_summary.json", "trajectory.jsonl"}]
    indexed[0].write_text(indexed[0].read_text() + "\ncorrupt\n")
    manifest = json.loads((output / "execution_manifest.json").read_text()); manifest.pop("completed_at"); manifest["status"] = "experiment_running"; (output / "execution_manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(Run4ADriverError, match="artifact hash mismatch"):
        driver.run_experiment(context, output, worker=lambda _: (_ for _ in ()).throw(AssertionError("duplicate")), local_teacher=lambda _: (_ for _ in ()).throw(AssertionError("duplicate")), external_teacher=lambda _: (_ for _ in ()).throw(AssertionError("duplicate")))
    assert calls == {"worker": 84, "local_teacher": 20, "external_teacher": 40}


def test_run7_escalation_action_corruption_fails_closed(tmp_path: Path):
    context = _context(); calls = {"worker": 0, "local_teacher": 0, "external_teacher": 0}; worker, local, external = _callbacks(context, calls); output = tmp_path / "escalation-corrupt"
    driver.run_experiment(context, output, worker=worker, local_teacher=local, external_teacher=external)
    action = next((output / "tasks" / "scope").glob("*/escalation"))
    indexed = [p for p in action.iterdir() if p.name not in {"arm_artifacts.json", "arm_binding.json", "arm_summary.json", "trajectory.jsonl"}]
    assert indexed
    indexed[0].write_text(indexed[0].read_text() + "\ncorrupt\n")
    manifest = json.loads((output / "execution_manifest.json").read_text()); manifest.pop("completed_at"); manifest["status"] = "experiment_running"; (output / "execution_manifest.json").write_text(json.dumps(manifest))
    before = dict(calls)
    with pytest.raises(Run4ADriverError, match="artifact hash mismatch"):
        driver.run_experiment(context, output, worker=lambda _: (_ for _ in ()).throw(AssertionError("duplicate worker")), local_teacher=lambda _: (_ for _ in ()).throw(AssertionError("duplicate local")), external_teacher=lambda _: (_ for _ in ()).throw(AssertionError("duplicate external")))
    assert calls == before


def test_run7_escalation_uses_diagnostic_contract_and_preserves_baseline_reference(tmp_path: Path):
    context = _context()
    calls = {"worker": 0, "local_teacher": 0, "external_teacher": 0}
    captured_worker_prompts: list[str] = []

    def worker(prompt: str) -> WorkerResponse:
        calls["worker"] += 1
        captured_worker_prompts.append(prompt)
        for task in context["tasks"].values():
            if prompt == task["prompt"]:
                return _response(_invalid(task))
            if task["prompt"] in prompt and "local_first_validation_failure" in prompt:
                return _response(_valid(task))
        return _response("{}")

    def local(_: str) -> WorkerResponse:
        calls["local_teacher"] += 1
        return _response('{"teacher_diagnosis":"local miss"}', model="local-teacher")

    def external(_: str):
        calls["external_teacher"] += 1
        return "codex-fixture", json.dumps(
            {
                "failure_classification": "scope_boundary",
                "teacher_diagnosis": "recover from local validation failure",
                "retry_guidance": "preserve allowed targets and hold unauthorized targets",
                "corrected_reference_output": {
                    "allowed_targets": ["target-a"],
                    "held_targets": ["target-b"],
                    "scope_expansion_required": False,
                    "review_status": "review_only",
                },
            }
        )

    output = tmp_path / "semantic-contract"
    driver.run_experiment(context, output, worker=worker, local_teacher=local, external_teacher=external)
    escalation = next((output / "tasks" / "scope").glob("*/escalation"))
    teacher_prompt = json.loads((escalation / "external_teacher.prompt.txt").read_text())
    retry_prompt = json.loads((escalation / "worker-retry.prompt.txt").read_text())
    intervention = retry_prompt["intervention"]
    control = next((output / "tasks" / "scope").glob("*/control"))
    control_retry_prompt = json.loads((control / "worker-retry.prompt.txt").read_text())

    assert teacher_prompt["allowed_fields"] == [
        "failure_classification",
        "teacher_diagnosis",
        "candidate_prompt_patch",
        "retry_guidance",
        "corrected_reference_output",
    ]
    assert len(teacher_prompt["failed_transitions"]) == 2
    assert teacher_prompt["failed_transitions"][1]["intervention_id"] == "local_first"
    assert intervention["teacher_parse_status"] == "passed"
    assert intervention["teacher_diagnosis"] == "recover from local validation failure"
    assert intervention["retry_guidance"]
    corrected = intervention["corrected_reference_output"]
    assert isinstance(corrected["allowed_targets"], list)
    assert isinstance(corrected["held_targets"], list)
    assert isinstance(corrected["scope_expansion_required"], bool)
    assert isinstance(corrected["review_status"], str)
    assert set(intervention) != {"teacher_parse_status"}
    for field in ("teacher_diagnosis", "retry_guidance", "corrected_reference_output", "teacher_parse_status"):
        assert field in control_retry_prompt["intervention"]
        assert field in intervention
    assert (escalation / "baseline_reference.json").exists()
    index = json.loads((escalation / "arm_artifacts.json").read_text())
    assert "baseline_reference.json" in index["files"]
    assert captured_worker_prompts


def test_run7_observed_escalation_response_shapes_are_not_lossy_when_guidance_is_diagnostic():
    parsed = _parse_teacher(
        json.dumps(
            {
                "failure_classification": "scope_boundary",
                "teacher_diagnosis": "the local answer omitted held targets",
                "retry_guidance": "emit the bounded review-only result",
                "corrected_reference_output": {
                    "allowed_targets": ["a", "b"],
                    "held_targets": ["c"],
                    "scope_expansion_required": True,
                    "review_status": "review_only",
                },
            }
        )
    )
    assert parsed["teacher_parse_status"] == "passed"
    assert parsed["failure_classification"] == "scope_boundary"
    assert parsed["teacher_diagnosis"]
    assert parsed["retry_guidance"]
    assert isinstance(parsed["corrected_reference_output"]["allowed_targets"], list)
    assert isinstance(parsed["corrected_reference_output"]["held_targets"], list)
    assert isinstance(parsed["corrected_reference_output"]["scope_expansion_required"], bool)
    assert isinstance(parsed["corrected_reference_output"]["review_status"], str)
    assert set(parsed) != {"teacher_parse_status"}


def test_run7_local_infrastructure_does_not_escalate(tmp_path: Path):
    context = _context(); calls = {"worker": 0, "local_teacher": 0, "external_teacher": 0}; worker, _, external = _callbacks(context, calls)
    def local(_: str) -> WorkerResponse:
        calls["local_teacher"] += 1
        raise OSError("synthetic local transport failure")
    driver.run_experiment(context, tmp_path / "infra", worker=worker, local_teacher=local, external_teacher=external)
    aggregate = json.loads((tmp_path / "infra" / "aggregate.json").read_text())
    assert aggregate["comparable_tasks"] == 0
    assert aggregate["quality_preserved"] is None
    assert aggregate["resource_reduced"] is None
    assert aggregate["escalations"] == 0


@pytest.mark.parametrize("field", ["preregistration_sha256", "driver_sha256", "policy_freeze_sha256", "fixture_pack_sha256", "models", "timeouts_seconds", "pair_order_seed", "git_head"])
def test_run7_resume_binding_drift_rejected(tmp_path: Path, field: str):
    context = _context(); calls = {"worker": 0, "local_teacher": 0, "external_teacher": 0}; worker, local, external = _callbacks(context, calls); output = tmp_path / field
    driver.run_experiment(context, output, worker=worker, local_teacher=local, external_teacher=external)
    manifest = json.loads((output / "execution_manifest.json").read_text()); manifest.pop("completed_at"); manifest["status"] = "experiment_running"; manifest[field] = "drift" if field != "fixture_pack_sha256" else "drift"; (output / "execution_manifest.json").write_text(json.dumps(manifest))
    before = dict(calls)
    with pytest.raises(Run4ADriverError, match="binding drift"):
        driver.run_experiment(context, output, worker=lambda _: (_ for _ in ()).throw(AssertionError("no call")), local_teacher=lambda _: (_ for _ in ()).throw(AssertionError("no call")), external_teacher=lambda _: (_ for _ in ()).throw(AssertionError("no call")))
    assert calls == before
