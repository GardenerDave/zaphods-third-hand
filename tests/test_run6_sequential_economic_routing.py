from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from local_harness.icm_spec import WorkerResponse
from local_harness.run6_sequential_policy import FAMILY_MATRIX, choose_initial_intervention, should_escalate, verify_policy
from local_harness.run6_sequential_fixture_pack import PACKS, verify_manifest
from scripts import zth_run6_sequential_economic_routing as driver
from scripts.zth_run4a_intervention_calibration import Run4ADriverError


ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "docs/research/RUN_6_VALIDATION_GATED_ECONOMIC_ESCALATION_PREREGISTRATION_2026-08-20.json"


def _response(content: str, *, model: str = "fixture-model") -> WorkerResponse:
    return WorkerResponse("ok", content, "http://fixture.invalid/v1", model, model, "stop", {}, {}, None)


def _context() -> dict:
    context = driver._load_context(PREREG, ROOT, require_runtime=False)
    context["preregistration_path"] = PREREG
    context["git_head"] = "synthetic-run6-head"
    return context


def _valid_output(task: dict) -> str:
    facts = task["validator"]["reference_facts"]
    if task["task_family"] == "triage-routing":
        phrase = " ".join(facts["must_include"])
        return json.dumps({"route": phrase, "rationale": phrase, "review_status": facts["review_status"]})
    return json.dumps({"allowed_targets": facts["required_allowed_targets"], "held_targets": facts["required_held_targets"], "scope_expansion_required": facts["requires_scope_expansion_flag"], "review_status": facts["review_status"]})


def _invalid_output(task: dict) -> str:
    if task["task_family"] == "triage-routing":
        return json.dumps({"route": "", "rationale": "", "review_status": "pending"})
    return json.dumps({"allowed_targets": [], "held_targets": [], "scope_expansion_required": True, "review_status": "ready_for_review"})


def _callbacks(context: dict, calls: dict[str, int], *, local_pass: bool = False):
    tasks = context["tasks"]

    def worker(prompt: str) -> WorkerResponse:
        calls["worker"] += 1
        for task in tasks.values():
            if prompt == task["prompt"]:
                return _response(_invalid_output(task))
            if task["prompt"] in prompt:
                if "local_first_validation_failure" in prompt or local_pass or "external_marker" in prompt:
                    return _response(_valid_output(task))
        return _response("{}")

    def local(_: str) -> WorkerResponse:
        calls["local_teacher"] += 1
        return _response('{"local_marker":"local","bounded_guidance":"retain approved targets and hold the rest"}', model="local-teacher")

    def external(_: str):
        calls["external_teacher"] += 1
        return "codex-fixture", '{"external_marker":"external","bounded_guidance":"apply only recorded authority"}'

    return worker, local, external


def test_run6_policy_matrix_and_validation_gate():
    verify_policy()
    assert choose_initial_intervention("triage-routing", "external_everywhere") == "external_teacher"
    assert choose_initial_intervention("scope-authority-boundary", "external_everywhere") == "external_teacher"
    assert choose_initial_intervention("triage-routing", "validation_gated_economic_escalation") == "external_teacher"
    assert choose_initial_intervention("scope-authority-boundary", "validation_gated_economic_escalation") == "local_teacher"
    assert should_escalate({"validation_status": "failed"}) is True
    assert should_escalate({"validation_status": "passed"}) is False
    assert should_escalate({"validation_status": "infrastructure_error"}) is False
    assert sum(FAMILY_MATRIX[f]["external_everywhere"] != FAMILY_MATRIX[f]["validation_gated_economic_escalation"] for f in FAMILY_MATRIX) == 1


def test_run6_planning_budget_is_mechanically_frozen():
    prereg = json.loads(PREREG.read_text())
    budget = prereg["planning_budget"]
    assert budget["maximum_calls"] == {"worker": 78, "external_teacher": 36, "local_teacher": 12, "total": 126}
    assert budget["maximum_physical_expected_elapsed_ms"] == 1639564.146
    assert budget["control_expected_post_baseline_ms"] == 815533.896
    assert budget["treatment_expected_post_baseline_max_ms"] == 1073500.188


def test_run6_fixture_packs_are_fresh_and_bound():
    context = _context()
    for family, spec in PACKS.items():
        manifest = verify_manifest(ROOT / "local_harness/fixtures/capability_loop" / spec["directory"], ROOT)
        assert len(manifest["fixtures"]) == 15
        assert manifest["target_included_count"] == 12
        assert manifest["pair_order"]["seed"] == 20260825
        assert manifest["task_family"] == context["manifests"][family]["task_family"]
        audit = json.loads((ROOT / "local_harness/fixtures/capability_loop" / spec["directory"] / "novelty_audit.json").read_text())
        assert audit["model_outputs_consulted"] is False
        assert not audit["task_id_collisions"]
        assert not audit["exact_prompt_duplicates"]
        assert not audit["normalized_prompt_duplicates"]
        assert not audit["high_similarity_pairs"]
        assert audit["counts"]["new_source"] == 15


def test_run6_dry_run_makes_zero_model_calls():
    result = subprocess.run(["python3", "scripts/zth_run6_sequential_economic_routing.py", "--preregistration", str(PREREG), "--output-dir", "/tmp/run6-sequential-dry"], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {"control": "external_everywhere", "model_calls": 0, "pair_order_seed": 20260825, "status": "dry_run_valid", "treatment": "validation_gated_economic_escalation"}


def test_run6_full_stub_escalates_only_after_local_validation_failure(tmp_path: Path):
    context = _context(); calls = {"worker": 0, "local_teacher": 0, "external_teacher": 0}
    worker, local, external = _callbacks(context, calls)
    result = driver.run_experiment(context, tmp_path / "execution", worker=worker, local_teacher=local, external_teacher=external)
    assert result["status"] == "experiment_completed"
    assert calls == {"worker": 78, "local_teacher": 12, "external_teacher": 36}
    aggregate = json.loads((tmp_path / "execution" / "aggregate.json").read_text())
    assert aggregate["portfolio"]["comparable_policy_tasks"] == 24
    assert aggregate["family_results"]["scope"]["treatment_escalations"] == 12
    assert aggregate["family_results"]["scope"]["treatment_escalation_rescues"] == 12
    assert aggregate["family_results"]["scope"]["treatment_first_stage_local_solves"] == 0
    assert aggregate["physical_execution_resource_history"]["attempts_by_role"] == {"external_teacher": 36, "local_teacher": 12, "worker": 78}
    escalation_prompt = next((tmp_path / "execution" / "tasks" / "scope").glob("*/escalation/external_teacher.prompt.txt"))
    assert "local_first_attempt" in escalation_prompt.read_text()
    for path in (tmp_path / "execution" / "tasks" / "scope").glob("*/treatment_summary.json"):
        assert json.loads(path.read_text())["escalated"] is True


def test_run6_local_pass_does_not_escalate(tmp_path: Path):
    context = _context(); calls = {"worker": 0, "local_teacher": 0, "external_teacher": 0}
    worker, local, external = _callbacks(context, calls, local_pass=True)
    driver.run_experiment(context, tmp_path / "pass", worker=worker, local_teacher=local, external_teacher=external)
    assert calls == {"worker": 66, "local_teacher": 12, "external_teacher": 24}
    assert not list((tmp_path / "pass" / "tasks" / "scope").glob("*/escalation/arm_summary.json"))
    for path in (tmp_path / "pass" / "tasks" / "scope").glob("*/treatment_summary.json"):
        value = json.loads(path.read_text()); assert value["escalated"] is False; assert value["final"]["deterministically_validated_rescue"] is True


def test_run6_local_infrastructure_failure_does_not_trigger_escalation(tmp_path: Path):
    context = _context(); calls = {"worker": 0, "local_teacher": 0, "external_teacher": 0}; worker, _, external = _callbacks(context, calls)
    def local(_: str) -> WorkerResponse:
        calls["local_teacher"] += 1
        raise OSError("synthetic local transport failure")
    driver.run_experiment(context, tmp_path / "infra", worker=worker, local_teacher=local, external_teacher=external)
    aggregate = json.loads((tmp_path / "infra" / "aggregate.json").read_text())
    assert aggregate["family_results"]["scope"]["infrastructure_excluded_tasks"] == 12
    assert aggregate["family_results"]["scope"]["treatment_escalations"] == 0
    assert not list((tmp_path / "infra" / "tasks" / "scope").glob("*/escalation/arm_summary.json"))


def test_run6_clean_partial_resume_reuses_local_and_escalation_without_duplicates(tmp_path: Path):
    context = _context(); calls = {"worker": 0, "local_teacher": 0, "external_teacher": 0}; worker, local, external = _callbacks(context, calls); output = tmp_path / "partial"; interrupted = {"value": False}
    def checkpoint(label, execution):
        if label.startswith("stage_terminal:scope:") and label.endswith(":treatment") and not interrupted["value"]:
            interrupted["value"] = True
            raise RuntimeError("clean interruption after terminal sequential treatment")
    with pytest.raises(RuntimeError, match="clean interruption"):
        driver.run_experiment(context, output, worker=worker, local_teacher=local, external_teacher=external, checkpoint_hook=checkpoint)
    manifest = json.loads((output / "execution_manifest.json").read_text())
    assert manifest["status"] == "experiment_running"
    assert "active_call" not in manifest
    resumed = driver.run_experiment(context, output, worker=worker, local_teacher=local, external_teacher=external)
    assert resumed["status"] == "experiment_completed"
    assert calls == {"worker": 78, "local_teacher": 12, "external_teacher": 36}


def test_run6_local_pass_before_treatment_closeout_resumes_without_escalation(tmp_path: Path, monkeypatch):
    context = _context(); calls = {"worker": 0, "local_teacher": 0, "external_teacher": 0}; worker, local, external = _callbacks(context, calls, local_pass=True); output = tmp_path / "local-pass"
    original = driver._treatment_summary
    interrupted = {"value": False}

    def interrupt_once(*args, **kwargs):
        if not interrupted["value"]:
            interrupted["value"] = True
            raise RuntimeError("interrupt after durable local pass")
        return original(*args, **kwargs)

    monkeypatch.setattr(driver, "_treatment_summary", interrupt_once)
    with pytest.raises(RuntimeError, match="durable local pass"):
        driver.run_experiment(context, output, worker=worker, local_teacher=local, external_teacher=external)
    monkeypatch.setattr(driver, "_treatment_summary", original)
    resumed = driver.run_experiment(context, output, worker=worker, local_teacher=local, external_teacher=external)
    assert resumed["status"] == "experiment_completed"
    assert calls == {"worker": 66, "local_teacher": 12, "external_teacher": 24}
    assert not list((output / "tasks" / "scope").glob("*/escalation/arm_summary.json"))
    scorecards = list((output / "tasks" / "scope").glob("*/scorecard.json"))
    assert all(json.loads(path.read_text())["treatment"]["rescue"] for path in scorecards)


def test_run6_local_failure_before_escalation_resumes_with_one_escalation(tmp_path: Path, monkeypatch):
    context = _context(); calls = {"worker": 0, "local_teacher": 0, "external_teacher": 0}; worker, local, external = _callbacks(context, calls); output = tmp_path / "local-fail-before-escalation"
    original_gate = driver.should_escalate
    original_summary = driver._treatment_summary
    interrupted = {"value": False}

    def interrupt_once(*args, **kwargs):
        if not interrupted["value"]:
            interrupted["value"] = True
            raise RuntimeError("interrupt before escalation active call")
        return original_summary(*args, **kwargs)

    monkeypatch.setattr(driver, "should_escalate", lambda _: False)
    monkeypatch.setattr(driver, "_treatment_summary", interrupt_once)
    with pytest.raises(RuntimeError, match="before escalation"):
        driver.run_experiment(context, output, worker=worker, local_teacher=local, external_teacher=external)
    assert not list((output / "tasks" / "scope").glob("*/escalation/arm_summary.json"))
    monkeypatch.setattr(driver, "should_escalate", original_gate)
    monkeypatch.setattr(driver, "_treatment_summary", original_summary)
    resumed = driver.run_experiment(context, output, worker=worker, local_teacher=local, external_teacher=external)
    assert resumed["status"] == "experiment_completed"
    assert calls == {"worker": 78, "local_teacher": 12, "external_teacher": 36}
    escalation_prompt = next((output / "tasks" / "scope").glob("*/escalation/external_teacher.prompt.txt"))
    assert "local_first_attempt" in escalation_prompt.read_text()
    assert all(json.loads(path.read_text())["treatment"]["rescue"] for path in (output / "tasks" / "scope").glob("*/scorecard.json"))


def test_run6_escalation_before_treatment_closeout_resumes_without_duplicate_stages(tmp_path: Path, monkeypatch):
    context = _context(); calls = {"worker": 0, "local_teacher": 0, "external_teacher": 0}; worker, local, external = _callbacks(context, calls); output = tmp_path / "escalation-closeout"
    original = driver._treatment_summary
    interrupted = {"value": False}

    def interrupt_once(*args, **kwargs):
        if not interrupted["value"]:
            interrupted["value"] = True
            raise RuntimeError("interrupt after durable escalation")
        return original(*args, **kwargs)

    monkeypatch.setattr(driver, "_treatment_summary", interrupt_once)
    with pytest.raises(RuntimeError, match="durable escalation"):
        driver.run_experiment(context, output, worker=worker, local_teacher=local, external_teacher=external)
    monkeypatch.setattr(driver, "_treatment_summary", original)
    assert list((output / "tasks" / "scope").glob("*/escalation/arm_summary.json"))
    resumed = driver.run_experiment(context, output, worker=worker, local_teacher=local, external_teacher=external)
    assert resumed["status"] == "experiment_completed"
    assert calls == {"worker": 78, "local_teacher": 12, "external_teacher": 36}
    assert all(json.loads(path.read_text())["treatment"]["rescue"] for path in (output / "tasks" / "scope").glob("*/scorecard.json"))


@pytest.mark.parametrize("stage", ["local_first", "escalation"])
def test_run6_sequential_terminal_artifact_corruption_fails_closed(tmp_path: Path, stage: str):
    context = _context(); calls = {"worker": 0, "local_teacher": 0, "external_teacher": 0}; worker, local, external = _callbacks(context, calls); output = tmp_path / stage
    driver.run_experiment(context, output, worker=worker, local_teacher=local, external_teacher=external)
    action = next((output / "tasks" / "scope").glob(f"*/{stage}"))
    indexed = [p for p in action.iterdir() if p.name not in {"arm_artifacts.json", "arm_binding.json", "arm_summary.json", "trajectory.jsonl"} and p.is_file()]
    assert indexed
    indexed[0].write_text(indexed[0].read_text() + "\ncorrupt\n")
    manifest = json.loads((output / "execution_manifest.json").read_text()); manifest.pop("completed_at"); manifest["status"] = "experiment_running"; (output / "execution_manifest.json").write_text(json.dumps(manifest))
    before = dict(calls)
    with pytest.raises(Run4ADriverError, match="artifact hash mismatch"):
        driver.run_experiment(context, output, worker=lambda _: (_ for _ in ()).throw(AssertionError("no duplicate")), local_teacher=lambda _: (_ for _ in ()).throw(AssertionError("no duplicate")), external_teacher=lambda _: (_ for _ in ()).throw(AssertionError("no duplicate")))
    assert calls == before


@pytest.mark.parametrize("field", ["preregistration_sha256", "driver_sha256", "policy_freeze_sha256", "fixture_pack_sha256", "models", "timeouts_seconds", "pair_order_seed", "git_head"])
def test_run6_resume_rejects_every_recorded_binding_drift(tmp_path: Path, field: str):
    context = _context()
    payload = {"schema": "zth_run6_sequential_execution_manifest_v1", "status": "experiment_running", "git_head": context["git_head"], "preregistration_sha256": hashlib.sha256(PREREG.read_bytes()).hexdigest(), "driver_sha256": context["preregistration"]["driver"]["sha256"], "policy_freeze_sha256": context["preregistration"]["policy_freeze"]["canonical_sha256"], "fixture_pack_sha256": {f: context["manifests"][f]["pack_sha256"] for f in ("triage", "scope")}, "models": context["preregistration"]["models"], "timeouts_seconds": context["preregistration"]["timeouts_seconds"], "pair_order_seed": 20260825}
    if field == "fixture_pack_sha256": payload[field] = {"triage": "drift", "scope": payload[field]["scope"]}
    elif field in {"models", "timeouts_seconds"}: payload[field] = dict(payload[field]); payload[field][next(iter(payload[field]))] = "drift"
    else: payload[field] = "drift"
    output = tmp_path / field; output.mkdir(); (output / "execution_manifest.json").write_text(json.dumps(payload))
    with pytest.raises(Run4ADriverError, match="binding drift"):
        driver.run_experiment(context, output, worker=lambda _: (_ for _ in ()).throw(AssertionError("no model call")), local_teacher=lambda _: (_ for _ in ()).throw(AssertionError("no model call")), external_teacher=lambda _: (_ for _ in ()).throw(AssertionError("no model call")))


def test_run6_active_call_and_terminal_states_fail_closed_or_reuse(tmp_path: Path):
    context = _context()
    base = {"schema": "zth_run6_sequential_execution_manifest_v1", "git_head": context["git_head"], "preregistration_sha256": hashlib.sha256(PREREG.read_bytes()).hexdigest(), "driver_sha256": context["preregistration"]["driver"]["sha256"], "policy_freeze_sha256": context["preregistration"]["policy_freeze"]["canonical_sha256"], "fixture_pack_sha256": {f: context["manifests"][f]["pack_sha256"] for f in ("triage", "scope")}, "models": context["preregistration"]["models"], "timeouts_seconds": context["preregistration"]["timeouts_seconds"], "pair_order_seed": 20260825}
    for status in ("experiment_completed", "experiment_incomplete"):
        out = tmp_path / status; out.mkdir(); (out / "execution_manifest.json").write_text(json.dumps({**base, "status": status, "completed_at": "synthetic-closeout"}))
        assert driver.run_experiment(context, out, worker=lambda _: (_ for _ in ()).throw(AssertionError("duplicate")), local_teacher=lambda _: _response("{}"), external_teacher=lambda _: ("x", "{}"))["status"] == status
    active = tmp_path / "active"; active.mkdir(); (active / "execution_manifest.json").write_text(json.dumps({**base, "status": "experiment_running", "active_call": {"kind": "local_first"}}))
    with pytest.raises(Run4ADriverError, match="ambiguous active"):
        driver.run_experiment(context, active, worker=lambda _: (_ for _ in ()).throw(AssertionError("duplicate")), local_teacher=lambda _: _response("{}"), external_teacher=lambda _: ("x", "{}"))
    unrelated = tmp_path / "unrelated"; unrelated.mkdir(); (unrelated / "file.txt").write_text("unbound")
    with pytest.raises(Run4ADriverError, match="lacks a bound Run 6"):
        driver.run_experiment(context, unrelated, worker=lambda _: _response("{}"), local_teacher=lambda _: _response("{}"), external_teacher=lambda _: ("x", "{}"))
