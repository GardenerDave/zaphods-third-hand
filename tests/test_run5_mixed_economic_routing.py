from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from local_harness.icm_spec import WorkerResponse
from local_harness.run5_mixed_economic_policy import FAMILY_MATRIX, load_policy_freeze
from local_harness.run5_mixed_fixture_pack import PACKS, verify_manifest
from local_harness.supervised_capability_loop import load_task_fixture
from scripts import zth_run5_mixed_economic_routing as driver
from scripts.zth_run4a_intervention_calibration import Run4ADriverError


ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "docs/research/RUN_5_MIXED_ECONOMIC_ROUTING_PREREGISTRATION_2026-08-20.json"


def _response(content: str, *, model: str = "fixture-model") -> WorkerResponse:
    return WorkerResponse("ok", content, "http://fixture.invalid/v1", model, model, "stop", {}, {}, None)


def _output(task: dict, *, valid: bool) -> str:
    if valid:
        if task["task_family"] == "triage-routing":
            facts = task["validator"]["reference_facts"]
            phrase = " ".join(facts["must_include"])
            return json.dumps({"route": phrase, "rationale": phrase, "review_status": facts["review_status"]})
        facts = task["validator"]["reference_facts"]
        return json.dumps({"allowed_targets": facts["required_allowed_targets"], "held_targets": facts["required_held_targets"], "scope_expansion_required": facts["requires_scope_expansion_flag"], "review_status": facts["review_status"]})
    if task["task_family"] == "triage-routing":
        return json.dumps({"route": "", "rationale": "", "review_status": "pending"})
    return json.dumps({"allowed_targets": [], "held_targets": [], "scope_expansion_required": True, "review_status": "ready_for_review"})


def _context() -> dict:
    context = driver._load_context(PREREG, ROOT, require_runtime=False)
    context["preregistration_path"] = PREREG
    context["git_head"] = "synthetic-run5-head"
    return context


def _execution_manifest(context: dict, *, status: str, completed_at: str | None = None) -> dict:
    value = {
        "schema": "zth_run5_mixed_execution_manifest_v1",
        "status": status,
        "git_head": context["git_head"],
        "preregistration_sha256": hashlib.sha256(PREREG.read_bytes()).hexdigest(),
        "driver_sha256": context["preregistration"]["driver"]["sha256"],
        "policy_freeze_sha256": context["preregistration"]["policy_freeze"]["canonical_sha256"],
        "fixture_pack_sha256": {family: context["manifests"][family]["pack_sha256"] for family in ("triage", "scope")},
        "models": context["preregistration"]["models"],
        "timeouts_seconds": context["preregistration"]["timeouts_seconds"],
        "pair_order_seed": 20260824,
    }
    if completed_at is not None:
        value["completed_at"] = completed_at
    return value


def _callbacks(context: dict, calls: dict[str, int]):
    tasks = context["tasks"]

    def worker(prompt: str) -> WorkerResponse:
        calls["worker"] += 1
        for task in tasks.values():
            if prompt == task["prompt"]:
                return _response(_output(task, valid=False))
            if task["prompt"] in prompt:
                return _response(_output(task, valid=True))
        return _response("{}")

    def local(_: str) -> WorkerResponse:
        calls["local_teacher"] += 1
        return _response('{"diagnosis":"bounded review"}', model="local-teacher")

    def external(_: str):
        calls["external_teacher"] += 1
        return "codex-fixture", '{"diagnosis":"bounded review"}'

    return worker, local, external


def test_run5_policy_matrix_differs_only_on_scope():
    assert FAMILY_MATRIX["triage-routing"] == {"external_everywhere": "external_teacher", "evidence_qualified_economic": "external_teacher"}
    assert FAMILY_MATRIX["scope-authority-boundary"] == {"external_everywhere": "external_teacher", "evidence_qualified_economic": "local_teacher"}
    assert sum(FAMILY_MATRIX[f]["external_everywhere"] != FAMILY_MATRIX[f]["evidence_qualified_economic"] for f in FAMILY_MATRIX) == 1


def test_run5_selection_and_planning_budget_are_frozen():
    order = [f"candidate-{n:02d}" for n in range(1, 16)]
    summaries = {task_id: {"eligible": task_id in {order[0], order[3], order[5], order[12]}} for task_id in order}
    selected = driver._selection(order, summaries)
    assert selected["included_task_ids"] == [order[0], order[3], order[5], order[12]]
    assert selected["reserve_task_ids"] == [task_id for task_id in order if task_id not in selected["included_task_ids"]]
    prereg = json.loads(PREREG.read_text())
    budget = prereg["planning_budget"]
    assert budget["maximum_physical_calls"] == 102
    assert budget["maximum_worker_calls"] == 66
    assert budget["maximum_external_teacher_calls"] == 24
    assert budget["maximum_local_teacher_calls"] == 12
    assert budget["expected_physical_experiment_cost_ms"] == 1231797.198
    assert budget["expected_control_policy_post_baseline_cost_ms"] == 815533.896
    assert budget["expected_treatment_policy_post_baseline_cost_ms"] == 665733.240
    assert budget["expected_policy_savings_ms"] == 149800.656


def test_run5_packs_are_fresh_satisfiable_and_fifteen_each():
    for family, spec in PACKS.items():
        manifest = verify_manifest(ROOT / "local_harness/fixtures/capability_loop" / spec["directory"], ROOT)
        assert manifest["candidate_count"] == 15
        assert manifest["target_included_count"] == 12
        assert manifest["task_family"] == spec["family"]
        audit = json.loads((ROOT / manifest["novelty_audit_path"]).read_text())
        assert audit["model_outputs_consulted"] is False
        assert audit["task_id_collisions"] == []
        assert audit["exact_prompt_duplicates"] == []
        assert audit["normalized_prompt_duplicates"] == []
        assert audit["high_similarity_pairs"] == []
        assert all(row["novelty"] == "new_source" for row in manifest["fixtures"])


def test_run5_dry_run_is_zero_call_and_binds_seed():
    result = subprocess.run(["python3", "scripts/zth_run5_mixed_economic_routing.py", "--preregistration", str(PREREG), "--output-dir", "/tmp/run5-dry-check"], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {"control": "external_everywhere", "model_calls": 0, "pair_order_seed": 20260824, "status": "dry_run_valid", "treatment": "evidence_qualified_economic"}


def test_run5_stub_has_common_triage_action_and_exact_physical_totals(tmp_path: Path):
    context = _context()
    calls = {"worker": 0, "local_teacher": 0, "external_teacher": 0}
    worker, local, external = _callbacks(context, calls)
    result = driver.run_experiment(context, tmp_path / "run", worker=worker, local_teacher=local, external_teacher=external)
    assert result["status"] == "experiment_completed"
    assert calls == {"worker": 66, "local_teacher": 12, "external_teacher": 24}
    aggregate = json.loads((tmp_path / "run" / "aggregate.json").read_text())
    assert aggregate["physical_execution_resource_history"]["total_model_call_attempts"] == 102
    assert aggregate["physical_execution_resource_history"]["attempts_by_role"] == {"worker": 66, "external_teacher": 24, "local_teacher": 12}
    triage_scores = list((tmp_path / "run" / "tasks" / "triage").glob("*/scorecard.json"))
    assert len(triage_scores) == 12
    for path in triage_scores:
        score = json.loads(path.read_text())
        assert score["common_action_reused"] is True
        assert score["control"] == score["treatment"]
    assert aggregate["family_results"]["triage"]["comparable_tasks"] == 12
    assert aggregate["family_results"]["scope"]["comparable_tasks"] == 12


def test_run5_terminal_reuse_and_common_artifact_corruption_fail_closed(tmp_path: Path):
    context = _context()
    calls = {"worker": 0, "local_teacher": 0, "external_teacher": 0}
    callbacks = _callbacks(context, calls)
    output = tmp_path / "run"
    driver.run_experiment(context, output, worker=callbacks[0], local_teacher=callbacks[1], external_teacher=callbacks[2])
    before = dict(calls)
    reused = driver.run_experiment(context, output, worker=lambda _: (_ for _ in ()).throw(AssertionError("duplicate")), local_teacher=lambda _: (_ for _ in ()).throw(AssertionError("duplicate")), external_teacher=lambda _: (_ for _ in ()).throw(AssertionError("duplicate")))
    assert reused["status"] == "experiment_completed"
    assert calls == before
    common = next((output / "tasks" / "triage").glob("*/common_external"))
    index = json.loads((common / "arm_artifacts.json").read_text())
    artifact = next(name for name in index["files"] if name.endswith(".raw.json"))
    (common / artifact).write_text((common / artifact).read_text() + "\ncorrupt")
    manifest = json.loads((output / "execution_manifest.json").read_text())
    manifest["status"] = "experiment_running"
    manifest.pop("completed_at", None)
    (output / "execution_manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(Run4ADriverError, match="artifact hash mismatch"):
        driver.run_experiment(context, output, worker=lambda _: (_ for _ in ()).throw(AssertionError("duplicate")), local_teacher=lambda _: _response("{}"), external_teacher=lambda _: ("x", "{}"))


def test_run5_clean_partial_resume_reuses_all_terminal_work_without_duplicates(tmp_path: Path):
    context = _context()
    calls = {"worker": 0, "local_teacher": 0, "external_teacher": 0}
    callbacks = _callbacks(context, calls)
    interrupted = {"value": False}

    def checkpoint(event: str, _execution: dict):
        if event.startswith("arm_terminal:scope:") and not interrupted["value"]:
            interrupted["value"] = True
            raise RuntimeError("synthetic clean Run 5 interruption")

    output = tmp_path / "partial"
    with pytest.raises(RuntimeError, match="clean Run 5 interruption"):
        driver.run_experiment(context, output, worker=callbacks[0], local_teacher=callbacks[1], external_teacher=callbacks[2], checkpoint_hook=checkpoint)
    manifest = json.loads((output / "execution_manifest.json").read_text())
    assert manifest["status"] == "experiment_running"
    assert "active_call" not in manifest
    calls_after_interrupt = dict(calls)
    resumed = driver.run_experiment(context, output, worker=callbacks[0], local_teacher=callbacks[1], external_teacher=callbacks[2])
    assert resumed["status"] == "experiment_completed"
    assert calls == {"worker": 66, "local_teacher": 12, "external_teacher": 24}
    assert sum(calls[role] - calls_after_interrupt[role] for role in calls) > 0
    assert json.loads((output / "selections" / "triage.json").read_text())["included_task_ids"] == context["manifests"]["triage"]["candidate_order"][:12]
    assert json.loads((output / "selections" / "scope.json").read_text())["included_task_ids"] == context["manifests"]["scope"]["candidate_order"][:12]
    triage_score = json.loads(next((output / "tasks" / "triage").glob("*/scorecard.json")).read_text())
    assert triage_score["common_action_reused"] is True
    assert triage_score["control"] == triage_score["treatment"]
    aggregate = json.loads((output / "aggregate.json").read_text())
    assert aggregate["physical_execution_resource_history"]["total_model_call_attempts"] == 102


@pytest.mark.parametrize("field", ["preregistration_sha256", "driver_sha256", "policy_freeze_sha256", "fixture_pack_sha256", "models", "timeouts_seconds", "pair_order_seed", "git_head"])
def test_run5_resume_rejects_recorded_binding_drift(tmp_path: Path, field: str):
    context = _context()
    payload = _execution_manifest(context, status="experiment_running")
    if field == "fixture_pack_sha256":
        payload[field] = {"triage": "drift", "scope": context["manifests"]["scope"]["pack_sha256"]}
    elif field in {"models", "timeouts_seconds"}:
        payload[field] = dict(payload[field]); payload[field][next(iter(payload[field]))] = "drift"
    elif field == "pair_order_seed":
        payload[field] = 99
    else:
        payload[field] = "drift"
    output = tmp_path / "drift"
    output.mkdir()
    (output / "execution_manifest.json").write_text(json.dumps(payload))
    with pytest.raises(Run4ADriverError, match="binding drift"):
        driver.run_experiment(context, output, worker=lambda _: (_ for _ in ()).throw(AssertionError("no model call")), local_teacher=lambda _: _response("{}"), external_teacher=lambda _: ("x", "{}"))


def test_run5_terminal_and_active_call_lifecycle_is_explicit(tmp_path: Path):
    context = _context()
    for status in ("experiment_completed", "experiment_incomplete"):
        output = tmp_path / status
        output.mkdir()
        (output / "execution_manifest.json").write_text(json.dumps(_execution_manifest(context, status=status, completed_at="synthetic-closeout")))
        result = driver.run_experiment(context, output, worker=lambda _: (_ for _ in ()).throw(AssertionError("duplicate")), local_teacher=lambda _: _response("{}"), external_teacher=lambda _: ("x", "{}"))
        assert result["status"] == status
    active = _execution_manifest(context, status="experiment_running")
    active["active_call"] = {"kind": "common_action", "family": "triage", "task_id": "run5-triage-001"}
    output = tmp_path / "active"
    output.mkdir(); (output / "execution_manifest.json").write_text(json.dumps(active))
    with pytest.raises(Run4ADriverError, match="ambiguous active"):
        driver.run_experiment(context, output, worker=lambda _: (_ for _ in ()).throw(AssertionError("duplicate")), local_teacher=lambda _: _response("{}"), external_teacher=lambda _: ("x", "{}"))
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir(); (unrelated / "unrelated.txt").write_text("not Run 5")
    with pytest.raises(Run4ADriverError, match="lacks a bound Run 5"):
        driver.run_experiment(context, unrelated, worker=lambda _: _response("{}"), local_teacher=lambda _: _response("{}"), external_teacher=lambda _: ("x", "{}"))


def test_run5_common_infrastructure_is_excluded_from_both_policy_scorecards(tmp_path: Path):
    context = _context()
    calls = {"worker": 0, "local_teacher": 0, "external_teacher": 0}
    worker, local, external = _callbacks(context, calls)
    def failing_external(_: str):
        calls["external_teacher"] += 1
        raise OSError("synthetic transport denial")
    result = driver.run_experiment(context, tmp_path / "run", worker=worker, local_teacher=local, external_teacher=failing_external)
    # All triage common actions are excluded, while scope remains comparable.
    assert result["status"] == "experiment_completed"
    aggregate = json.loads((tmp_path / "run" / "aggregate.json").read_text())
    triage = aggregate["family_results"]["triage"]
    assert triage["comparable_tasks"] == 0
    assert triage["infrastructure_excluded_tasks"] == 12
    assert aggregate["portfolio"]["comparable_policy_tasks"] == 0
    assert aggregate["portfolio"]["control_solve_rate"] is None
    assert aggregate["portfolio"]["treatment_solve_rate"] is None
    assert aggregate["portfolio"]["quality_preserved"] is None
    assert aggregate["portfolio"]["resource_reduced"] is None
    assert aggregate["portfolio"]["economic_routing_success"] is None
    assert aggregate["physical_execution_resource_history"]["infrastructure_failures_by_role"]["external_teacher"] == 24


def test_run5_triage_only_infrastructure_exclusion_preserves_other_family(tmp_path: Path):
    context = _context(); calls = {"worker": 0, "local_teacher": 0, "external_teacher": 0}; callbacks = _callbacks(context, calls)
    target = "run5-triage-001"
    def external(prompt: str):
        if context["tasks"][target]["prompt"] in prompt:
            calls["external_teacher"] += 1
            raise OSError("one common triage transport failure")
        return callbacks[2](prompt)
    driver.run_experiment(context, tmp_path / "triage-infra", worker=callbacks[0], local_teacher=callbacks[1], external_teacher=external)
    aggregate = json.loads((tmp_path / "triage-infra" / "aggregate.json").read_text())
    assert aggregate["family_results"]["triage"]["comparable_tasks"] == 11
    assert aggregate["family_results"]["scope"]["comparable_tasks"] == 12
    assert aggregate["portfolio"]["comparable_policy_tasks"] == 23
    assert aggregate["physical_execution_resource_history"]["infrastructure_failures_by_role"]["external_teacher"] == 1


def test_run5_scope_only_infrastructure_exclusion_preserves_triage_and_other_scope(tmp_path: Path):
    context = _context(); calls = {"worker": 0, "local_teacher": 0, "external_teacher": 0}; callbacks = _callbacks(context, calls)
    target = "run5-scope-001"
    def local(prompt: str):
        if context["tasks"][target]["prompt"] in prompt:
            calls["local_teacher"] += 1
            raise OSError("one local scope transport failure")
        return callbacks[1](prompt)
    driver.run_experiment(context, tmp_path / "scope-infra", worker=callbacks[0], local_teacher=local, external_teacher=callbacks[2])
    aggregate = json.loads((tmp_path / "scope-infra" / "aggregate.json").read_text())
    assert aggregate["family_results"]["triage"]["comparable_tasks"] == 12
    assert aggregate["family_results"]["scope"]["comparable_tasks"] == 11
    assert aggregate["portfolio"]["comparable_policy_tasks"] == 23
    assert aggregate["physical_execution_resource_history"]["infrastructure_failures_by_role"]["local_teacher"] == 1
    excluded = [row for row in aggregate["family_results"]["scope"]["infrastructure"] if row["task_id"] == target]
    assert excluded


def test_run5_scope_arm_artifact_corruption_fails_closed(tmp_path: Path):
    context = _context(); calls = {"worker": 0, "local_teacher": 0, "external_teacher": 0}; callbacks = _callbacks(context, calls); output = tmp_path / "scope-corrupt"
    driver.run_experiment(context, output, worker=callbacks[0], local_teacher=callbacks[1], external_teacher=callbacks[2])
    arm = next(output.glob("tasks/scope/*/arms/*"))
    index = json.loads((arm / "arm_artifacts.json").read_text())
    artifact = next(name for name in index["files"] if name.endswith(".raw.json"))
    (arm / artifact).write_text((arm / artifact).read_text() + "\ncorrupt")
    manifest = json.loads((output / "execution_manifest.json").read_text()); manifest["status"] = "experiment_running"; manifest.pop("completed_at", None); (output / "execution_manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(Run4ADriverError, match="artifact hash mismatch"):
        driver.run_experiment(context, output, worker=lambda _: (_ for _ in ()).throw(AssertionError("duplicate")), local_teacher=lambda _: _response("{}"), external_teacher=lambda _: ("x", "{}"))
