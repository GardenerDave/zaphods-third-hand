#!/usr/bin/env python3
"""Execute the frozen Run 6 validation-gated sequential economic protocol."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from local_harness.run4a_intervention_harness import (  # noqa: E402
    REQUIRED_AUTHORITY,
    _call_teacher,
    _call_worker,
    _default_external_teacher,
    _default_local_teacher,
    _default_worker,
    _json_write,
    _teacher_prompt,
    run_isolated_intervention_arm,
)
from local_harness.run6_sequential_fixture_pack import PACKS, verify_manifest  # noqa: E402
from local_harness.run6_sequential_policy import (  # noqa: E402
    FAMILY_MATRIX,
    RESOURCE_PRIORS_MS,
    choose_initial_intervention,
    should_escalate,
    verify_policy,
)
from local_harness.supervised_capability_loop import load_task_fixture  # noqa: E402
from scripts.zth_run4_economic_routing import _arm_terminal, _baseline_payload  # noqa: E402
from scripts.zth_run4a_intervention_calibration import (  # noqa: E402
    Run4ADriverError,
    _append_transition,
    _read_json,
    _transitions,
    _write_arm_artifact_index,
    run_baseline,
)


TERMINAL_STATUSES = {"experiment_completed", "experiment_incomplete"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_head(repo_root: Path) -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True, capture_output=True, check=True).stdout.strip()


def _valid(summary: Mapping[str, Any] | None) -> bool:
    return bool(summary and summary.get("capability_verdict_available") is True and summary.get("transport_valid") is True and summary.get("transport_classification") == "model_response")


def _terminal_summary(path: Path) -> dict[str, Any] | None:
    summary_path = path / "arm_summary.json"
    if not summary_path.exists():
        return None
    summary = _read_json(summary_path)
    if summary.get("disposition") in {"ready_for_review", "unresolved", "infrastructure_error"}:
        return summary
    raise Run4ADriverError(f"invalid nonterminal Run 6 action summary: {summary_path}")


def _assert_action_reusable(path: Path) -> None:
    trajectory = path / "trajectory.jsonl"
    rows = _transitions(trajectory) if trajectory.exists() else []
    completed = {row.get("call_id") for row in rows if row.get("transition") in {"response_captured", "infrastructure_failed"}}
    ambiguous = [row for row in rows if row.get("transition") == "call_started" and row.get("call_id") not in completed]
    if ambiguous:
        raise Run4ADriverError(f"ambiguous started Run 6 action in {trajectory}")


def _load_context(prereg_path: Path, repo_root: Path, *, require_runtime: bool) -> dict[str, Any]:
    prereg = _read_json(prereg_path)
    if prereg.get("model_calls_made") is not False:
        raise Run4ADriverError("Run 6 preregistration must remain model-call-free before execution")
    policy_binding = prereg["policy_freeze"]
    policy_path = repo_root / policy_binding["path"]
    if sha256_file(policy_path) != policy_binding["file_sha256"]:
        raise Run4ADriverError("Run 6 policy freeze file hash mismatch")
    policy = _read_json(policy_path)
    policy_basis = dict(policy); recorded = policy_basis.get("freeze_sha256"); policy_basis["freeze_sha256"] = None
    if recorded != hashlib.sha256(json.dumps(policy_basis, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest():
        raise Run4ADriverError("Run 6 policy freeze digest mismatch")
    if policy.get("family_action_matrix") != FAMILY_MATRIX:
        raise Run4ADriverError("Run 6 policy matrix mismatch")
    verify_policy()
    source = policy["policy_source"]
    if sha256_file(repo_root / source["path"]) != source["sha256"]:
        raise Run4ADriverError("Run 6 policy source hash mismatch")
    manifests: dict[str, dict[str, Any]] = {}
    for family in ("triage", "scope"):
        binding = prereg["fixture_packs"][family]
        pack_dir = repo_root / binding["path"]
        manifest = verify_manifest(pack_dir, repo_root)
        if manifest["manifest_sha256"] != binding["manifest_sha256"] or manifest["pack_sha256"] != binding["pack_sha256"]:
            raise Run4ADriverError(f"Run 6 {family} fixture binding mismatch")
        if sha256_file(pack_dir / "novelty_audit.json") != binding["novelty_audit_sha256"]:
            raise Run4ADriverError(f"Run 6 {family} novelty audit binding mismatch")
        manifests[family] = manifest
    for item in prereg["research_basis"]:
        if sha256_file(repo_root / item["path"]) != item["sha256"]:
            raise Run4ADriverError(f"Run 6 evidence input hash mismatch: {item['path']}")
    resource_binding = prereg["resource_manifest"]
    resource_path = repo_root / resource_binding["path"]
    if sha256_file(resource_path) != resource_binding["sha256"]:
        raise Run4ADriverError("Run 6 resource manifest hash mismatch")
    resource = _read_json(resource_path)
    recorded_weights = resource.get("weights", {})
    if resource.get("manifest_sha256") != resource_binding["canonical_sha256"] or any(recorded_weights.get(key) != value for key, value in RESOURCE_PRIORS_MS.items()):
        raise Run4ADriverError("Run 6 resource priors drift")
    for item in prereg["validators"]:
        if sha256_file(repo_root / item["path"]) != item["sha256"]:
            raise Run4ADriverError(f"Run 6 validator binding mismatch: {item['path']}")
    driver_binding = prereg["driver"]
    if sha256_file(repo_root / driver_binding["path"]) != driver_binding["sha256"]:
        raise Run4ADriverError("Run 6 driver hash mismatch")
    timeouts = prereg["timeouts_seconds"]
    effective = {"worker": int(os.environ.get("ZTH_CAPABILITY_WORKER_TIMEOUT", timeouts["worker"])), "local_teacher": int(os.environ.get("ZTH_CAPABILITY_TEACHER_TIMEOUT", timeouts["local_teacher"])), "external_teacher": 120}
    if effective != timeouts:
        raise Run4ADriverError("Run 6 timeout binding mismatch")
    configured = {"worker": os.environ.get("ZTH_CAPABILITY_WORKER_MODEL"), "local_teacher": os.environ.get("ZTH_CAPABILITY_TEACHER_MODEL"), "external_teacher": os.environ.get("ZTH_EXTERNAL_TEACHER_IDENTITY")}
    if require_runtime and any(configured[role] != prereg["models"][role] for role in configured):
        raise Run4ADriverError("Run 6 runtime model identity mismatch")
    if prereg["pair_order"]["seed"] != 20260825:
        raise Run4ADriverError("Run 6 pair-order seed drift")
    tasks = {}
    for manifest in manifests.values():
        for row in manifest["fixtures"]:
            task = load_task_fixture(repo_root / row["path"])
            tasks[task["task_id"]] = task
    return {"preregistration": prereg, "preregistration_path": prereg_path, "policy": policy, "manifests": manifests, "tasks": tasks, "effective_timeouts": effective}


def _selection(candidate_order: list[str], summaries: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    eligible = [task_id for task_id in candidate_order if summaries[task_id].get("eligible") is True]
    selected = eligible[:12]
    return {"candidate_order": candidate_order, "eligible_task_ids": eligible, "included_task_ids": selected, "reserve_task_ids": [task_id for task_id in candidate_order if task_id not in selected], "selected_count": len(selected), "family_complete": len(selected) == 12}


def _binding(context: Mapping[str, Any], family: str, task_id: str, stage: str, intervention: str, baseline: Mapping[str, Any]) -> dict[str, Any]:
    return {"schema": "zth_run6_action_binding_v1", "family": family, "task_id": task_id, "stage": stage, "intervention": intervention, "preregistration_sha256": sha256_file(context["preregistration_path"]), "fixture_pack_sha256": context["manifests"][family]["pack_sha256"], "baseline_summary_sha256": hashlib.sha256(json.dumps(baseline, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest(), "policy_freeze_sha256": context["preregistration"]["policy_freeze"]["canonical_sha256"], "models": context["preregistration"]["models"], "timeouts_seconds": context["preregistration"]["timeouts_seconds"]}


def _run_single_action(context: Mapping[str, Any], output_dir: Path, family: str, task_id: str, stage: str, intervention: str, baseline: Mapping[str, Any], *, worker: Callable[..., Any], local_teacher: Callable[..., Any], external_teacher: Callable[..., Any]) -> dict[str, Any]:
    action_dir = output_dir / "tasks" / family / task_id / stage
    binding = _binding(context, family, task_id, stage, intervention, baseline)
    terminal = _arm_terminal(action_dir, binding)
    if terminal is not None:
        return terminal
    if action_dir.exists():
        _assert_action_reusable(action_dir)
        if any(action_dir.iterdir()):
            raise Run4ADriverError(f"incomplete Run 6 action artifacts in {action_dir}")
    action_dir.mkdir(parents=True, exist_ok=True)
    _json_write(action_dir / "arm_binding.json", binding)
    summary = run_isolated_intervention_arm(context["tasks"][task_id], baseline, intervention=intervention, out_dir=action_dir, worker=worker, local_teacher=local_teacher, external_teacher=external_teacher)
    _write_arm_artifact_index(action_dir)
    return summary


def _run_external_escalation(context: Mapping[str, Any], output_dir: Path, task_id: str, baseline: Mapping[str, Any], local_summary: Mapping[str, Any], *, worker: Callable[..., Any], external_teacher: Callable[..., Any]) -> dict[str, Any]:
    action_dir = output_dir / "tasks" / "scope" / task_id / "escalation"
    binding = _binding(context, "scope", task_id, "escalation", "external_teacher", baseline)
    terminal = _arm_terminal(action_dir, binding)
    if terminal is not None:
        return terminal
    if action_dir.exists():
        _assert_action_reusable(action_dir)
        if any(action_dir.iterdir()):
            raise Run4ADriverError(f"incomplete Run 6 escalation artifacts in {action_dir}")
    action_dir.mkdir(parents=True, exist_ok=True)
    _json_write(action_dir / "arm_binding.json", binding)
    trajectory = action_dir / "trajectory.jsonl"
    task = context["tasks"][task_id]
    escalation_prompt = json.dumps({"task_prompt": task["prompt"], "output_contract": task["output_contract"], "reference_facts": task["validator"].get("reference_facts", {}), "baseline_diagnostics": baseline["validation"].get("diagnostics", []), "local_first_attempt": {"validation": local_summary.get("validation_status"), "failed_checks": local_summary.get("failed_checks", []), "realized_elapsed_ms": local_summary.get("realized_elapsed_ms")}, "escalation_trigger": "deterministic validation failure", "authority": REQUIRED_AUTHORITY}, indent=2, sort_keys=True)
    teacher_payload, infrastructure = _call_teacher(action_dir, trajectory, task, escalation_prompt, role="external_teacher", local_teacher=lambda _: (_ for _ in ()).throw(Run4ADriverError("local teacher forbidden in escalation")), external_teacher=external_teacher)
    worker_result = None
    if teacher_payload is not None:
        retry_prompt = json.dumps({"task_prompt": task["prompt"], "output_contract": task["output_contract"], "reference_facts": task["validator"].get("reference_facts", {}), "baseline_diagnostics": baseline["validation"].get("diagnostics", []), "local_first_validation_failure": local_summary.get("failed_checks", []), "intervention": teacher_payload.get("parsed", {}), "authority": REQUIRED_AUTHORITY}, indent=2, sort_keys=True)
        worker_result, infrastructure = _call_worker(action_dir, trajectory, task, retry_prompt, worker=worker, attempt_id="worker-retry")
    if infrastructure is not None:
        summary = {"schema": "zth_run6_stage_summary_v1", "task_id": task_id, "task_family": task["task_family"], "stage": "escalation", "intervention": "external_teacher", "capability_verdict_available": False, "deterministically_validated_rescue": False, "transport_valid": False, "disposition": "infrastructure_error", "infrastructure_artifact": infrastructure.get("artifact_ref"), "trigger": "deterministic validation failure", "authority": "review_required_no_evidence_merge"}
    else:
        validation = worker_result["validation"]
        summary = {"schema": "zth_run6_stage_summary_v1", "task_id": task_id, "task_family": task["task_family"], "stage": "escalation", "intervention": "external_teacher", "capability_verdict_available": True, "transport_valid": True, "transport_classification": "model_response", "deterministically_validated_rescue": validation["validation_status"] == "passed", "validation_status": validation["validation_status"], "failed_checks": [c["check_id"] for c in validation.get("checks", []) if c.get("status") == "failed"], "realized_elapsed_ms": worker_result["telemetry"]["elapsed_ms"] + teacher_payload["resource_telemetry"]["elapsed_ms"], "resource_telemetry": {"worker": worker_result["telemetry"], "external_teacher": teacher_payload["resource_telemetry"]}, "disposition": "ready_for_review" if validation["validation_status"] == "passed" else "unresolved", "trigger": "deterministic validation failure", "authority": "review_required_no_evidence_merge"}
    _append_transition(trajectory, summary["disposition"], task_id=task_id, stage="escalation", capability_verdict_available=summary["capability_verdict_available"])
    _json_write(action_dir / "arm_summary.json", summary)
    _write_arm_artifact_index(action_dir)
    return summary


def _treatment_summary(task_id: str, local_summary: Mapping[str, Any], escalation: Mapping[str, Any] | None) -> dict[str, Any]:
    if not _valid(local_summary):
        return {"schema": "zth_run6_treatment_summary_v1", "task_id": task_id, "initial_intervention": "local_teacher", "local_first": local_summary, "escalated": False, "escalation": None, "final": local_summary, "disposition": "infrastructure_excluded", "infrastructure_artifact": local_summary.get("infrastructure_artifact")}
    if should_escalate({"validation_status": local_summary.get("validation_status")}):
        final = escalation or {"capability_verdict_available": False, "disposition": "infrastructure_error", "infrastructure_artifact": None}
        return {"schema": "zth_run6_treatment_summary_v1", "task_id": task_id, "initial_intervention": "local_teacher", "local_first": local_summary, "escalated": True, "escalation": final, "final": final, "disposition": "ready_for_review" if _valid(final) else "infrastructure_excluded", "infrastructure_artifact": final.get("infrastructure_artifact")}
    return {"schema": "zth_run6_treatment_summary_v1", "task_id": task_id, "initial_intervention": "local_teacher", "local_first": local_summary, "escalated": False, "escalation": None, "final": local_summary, "disposition": "comparable", "infrastructure_artifact": None}


def _write_scorecard(path: Path, *, family: str, task_id: str, common: Mapping[str, Any] | None = None, control: Mapping[str, Any] | None = None, treatment: Mapping[str, Any] | None = None, treatment_detail: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if common is not None: control = treatment = common
    assert control is not None and treatment is not None
    comparable = _valid(control) and _valid(treatment)
    pair_outcome = "both_solve" if control.get("deterministically_validated_rescue") and treatment.get("deterministically_validated_rescue") else "control_only" if control.get("deterministically_validated_rescue") else "treatment_only" if treatment.get("deterministically_validated_rescue") else "neither"
    value = {"schema": "zth_run6_policy_scorecard_v1", "family": family, "task_id": task_id, "common_action_reused": common is not None, "disposition": "comparable" if comparable else "infrastructure_excluded", "control": {"intervention": control.get("intervention"), "rescue": bool(control.get("deterministically_validated_rescue")), "elapsed_ms": control.get("realized_elapsed_ms")}, "treatment": {"intervention": treatment.get("intervention"), "rescue": bool(treatment.get("deterministically_validated_rescue")), "elapsed_ms": treatment.get("realized_elapsed_ms")}, "paired_outcome": pair_outcome, "infrastructure": [] if comparable else [{"policy_arm": "control", "intervention": control.get("intervention"), "artifact": control.get("infrastructure_artifact")}, {"policy_arm": "treatment", "intervention": treatment.get("intervention"), "artifact": treatment.get("infrastructure_artifact")}], "treatment_detail": treatment_detail, "authority": "review_required_no_evidence_merge"}
    _json_write(path, value)
    return value


def _resource_history(output_dir: Path) -> dict[str, Any]:
    attempts: dict[str, int] = {}; valid: dict[str, int] = {}; infra: dict[str, int] = {}; elapsed: dict[str, float] = {}; seen: set[tuple[str, str]] = set()
    for path in sorted(output_dir.rglob("trajectory.jsonl")):
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        completed = {row.get("call_id"): row for row in rows if row.get("transition") in {"response_captured", "infrastructure_failed"}}
        for row in rows:
            if row.get("transition") != "call_started": continue
            key = (str(path), str(row.get("call_id")))
            if key in seen: continue
            seen.add(key); role = row.get("role", "unknown"); attempts[role] = attempts.get(role, 0) + 1
            done = completed.get(row.get("call_id"))
            if not done: continue
            ref = done.get("artifact_ref"); artifact = _read_json(path.parent / ref) if ref else {}
            if done.get("transition") == "infrastructure_failed": infra[role] = infra.get(role, 0) + 1
            else:
                meta = artifact.get("metadata", {}) if isinstance(artifact, dict) else {}
                if (meta.get("transport_valid", artifact.get("transport_valid")) is True and meta.get("transport_classification", artifact.get("transport_classification")) == "model_response"): valid[role] = valid.get(role, 0) + 1
            telemetry = (artifact.get("metadata", {}) or {}).get("resource_telemetry") or artifact.get("resource_telemetry")
            if isinstance(telemetry, dict) and isinstance(telemetry.get("elapsed_ms"), (int, float)): elapsed[role] = elapsed.get(role, 0.0) + float(telemetry["elapsed_ms"])
    return {"schema": "zth_run6_execution_resource_history_v1", "attempts_by_role": attempts, "valid_responses_by_role": valid, "infrastructure_failures_by_role": infra, "realized_elapsed_ms_by_role": elapsed, "total_model_call_attempts": sum(attempts.values()), "total_worker_attempts": attempts.get("worker", 0), "total_teacher_attempts": attempts.get("local_teacher", 0) + attempts.get("external_teacher", 0), "accounting_scope": "all physical durable attempts; common triage action counted once"}


def aggregate_results(output_dir: Path) -> dict[str, Any]:
    scorecards = [_read_json(p) for p in sorted(output_dir.glob("tasks/*/*/scorecard.json"))]
    family_results = {}
    for family in ("triage", "scope"):
        rows = [r for r in scorecards if r["family"] == family]; comparable = [r for r in rows if r["disposition"] == "comparable"]
        treatment_details = [r.get("treatment_detail") for r in comparable if r.get("treatment_detail")]
        family_results[family] = {"selected_tasks": len(rows), "comparable_tasks": len(comparable), "infrastructure_excluded_tasks": len(rows)-len(comparable), "control_validated_solves": sum(r["control"]["rescue"] for r in comparable), "treatment_validated_solves": sum(r["treatment"]["rescue"] for r in comparable), "control_post_baseline_elapsed_ms": sum(float(r["control"]["elapsed_ms"] or 0) for r in comparable), "treatment_post_baseline_elapsed_ms": sum(float(r["treatment"]["elapsed_ms"] or 0) for r in comparable), "paired_outcomes": {n: sum(r["paired_outcome"] == n for r in comparable) for n in ("both_solve", "control_only", "treatment_only", "neither")}, "treatment_first_stage_local_solves": sum(bool(d and d["local_first"].get("deterministically_validated_rescue")) for d in treatment_details), "treatment_escalations": sum(bool(d and d.get("escalated")) for d in treatment_details), "treatment_escalation_rescues": sum(bool(d and d.get("escalated") and d["final"].get("deterministically_validated_rescue")) for d in treatment_details), "treatment_escalation_failures": sum(bool(d and d.get("escalated") and not d["final"].get("deterministically_validated_rescue")) for d in treatment_details), "infrastructure": [r for r in rows if r["disposition"] != "comparable"]}
    comparable_total = family_results["triage"]["comparable_tasks"] + family_results["scope"]["comparable_tasks"]
    control_solves = family_results["triage"]["control_validated_solves"] + family_results["scope"]["control_validated_solves"]
    treatment_solves = family_results["triage"]["treatment_validated_solves"] + family_results["scope"]["treatment_validated_solves"]
    control_elapsed = family_results["triage"]["control_post_baseline_elapsed_ms"] + family_results["scope"]["control_post_baseline_elapsed_ms"]
    treatment_elapsed = family_results["triage"]["treatment_post_baseline_elapsed_ms"] + family_results["scope"]["treatment_post_baseline_elapsed_ms"]
    history = _resource_history(output_dir)
    return {"schema": "zth_run6_sequential_aggregate_v1", "status": "review_required", "family_results": family_results, "portfolio": {"comparable_policy_tasks": comparable_total, "control_validated_solves": control_solves, "treatment_validated_solves": treatment_solves, "control_solve_rate": control_solves / comparable_total if comparable_total else None, "treatment_solve_rate": treatment_solves / comparable_total if comparable_total else None, "control_post_baseline_policy_elapsed_ms": control_elapsed if comparable_total else None, "treatment_post_baseline_policy_elapsed_ms": treatment_elapsed if comparable_total else None, "quality_preserved": treatment_solves >= control_solves if comparable_total else None, "resource_reduced": treatment_elapsed < control_elapsed if comparable_total else None, "economic_routing_success": treatment_solves >= control_solves and treatment_elapsed < control_elapsed if comparable_total else None}, "physical_execution_resource_history": history, "authority": "review_required_no_evidence_merge"}


def _validate_execution_bindings(context: Mapping[str, Any], execution: Mapping[str, Any]) -> None:
    expected = {"preregistration_sha256": sha256_file(context["preregistration_path"]), "driver_sha256": context["preregistration"]["driver"]["sha256"], "policy_freeze_sha256": context["preregistration"]["policy_freeze"]["canonical_sha256"], "fixture_pack_sha256": {f: context["manifests"][f]["pack_sha256"] for f in ("triage", "scope")}, "models": context["preregistration"]["models"], "timeouts_seconds": context["preregistration"]["timeouts_seconds"], "pair_order_seed": context["preregistration"]["pair_order"]["seed"]}
    for field, value in expected.items():
        if execution.get(field) != value: raise Run4ADriverError(f"Run 6 execution binding drift: {field}")
    if context.get("git_head") is not None and execution.get("git_head") != context["git_head"]: raise Run4ADriverError("Run 6 execution binding drift: git_head")


def run_experiment(context: Mapping[str, Any], output_dir: Path, *, worker: Callable[..., Any], local_teacher: Callable[..., Any], external_teacher: Callable[..., Any], checkpoint_hook: Callable[[str, Mapping[str, Any]], None] | None = None) -> dict[str, Any]:
    manifest_path = output_dir / "execution_manifest.json"
    if manifest_path.exists():
        execution = _read_json(manifest_path); _validate_execution_bindings(context, execution)
        if execution.get("status") == "experiment_completed" or (execution.get("status") == "experiment_incomplete" and execution.get("completed_at")): return execution
        if execution.get("active_call"): raise Run4ADriverError("ambiguous active Run 6 call; refusing resume")
    elif output_dir.exists() and any(output_dir.iterdir()):
        raise Run4ADriverError("existing nonempty output directory lacks a bound Run 6 execution manifest")
    else:
        output_dir.mkdir(parents=True, exist_ok=True)
        execution = {"schema": "zth_run6_sequential_execution_manifest_v1", "status": "experiment_running", "started_at": utc_now(), "git_head": context.get("git_head") or git_head(Path.cwd()), "preregistration_sha256": sha256_file(context["preregistration_path"]), "driver_sha256": context["preregistration"]["driver"]["sha256"], "policy_freeze_sha256": context["preregistration"]["policy_freeze"]["canonical_sha256"], "fixture_pack_sha256": {f: context["manifests"][f]["pack_sha256"] for f in ("triage", "scope")}, "models": context["preregistration"]["models"], "timeouts_seconds": context["preregistration"]["timeouts_seconds"], "pair_order_seed": context["preregistration"]["pair_order"]["seed"], "candidate_states": {}, "model_calls_started": True}
        _json_write(manifest_path, execution)
    for family in ("triage", "scope"):
        summaries = {}; order = context["manifests"][family]["candidate_order"]
        for task_id in order:
            candidate_dir = output_dir / "candidates" / family / task_id
            execution["active_call"] = {"kind": "baseline", "family": family, "task_id": task_id, "role": "worker"}; _json_write(manifest_path, execution)
            summaries[task_id] = run_baseline(context["tasks"][task_id], candidate_dir, worker=worker)
            execution.pop("active_call", None); execution["candidate_states"][f"{family}:{task_id}"] = "baseline_terminal"; _json_write(manifest_path, execution)
            if checkpoint_hook: checkpoint_hook(f"baseline_terminal:{family}:{task_id}", execution)
        selection = _selection(order, summaries); (output_dir / "selections").mkdir(parents=True, exist_ok=True); _json_write(output_dir / "selections" / f"{family}.json", selection); execution.setdefault("selections", {})[family] = selection; _json_write(manifest_path, execution)
    if not all(execution["selections"][f]["family_complete"] for f in ("triage", "scope")):
        execution.update({"status": "experiment_incomplete", "completed_at": utc_now()}); _json_write(manifest_path, execution); return execution
    for family in ("triage", "scope"):
        for task_id in execution["selections"][family]["included_task_ids"]:
            baseline = _baseline_payload(output_dir / "candidates" / family / task_id, _read_json(output_dir / "candidates" / family / task_id / "baseline_summary.json"))
            if family == "triage":
                execution["active_call"] = {"kind": "common_action", "family": family, "task_id": task_id, "intervention": "external_teacher"}; _json_write(manifest_path, execution)
                common = _run_single_action(context, output_dir, family, task_id, "common_external", "external_teacher", baseline, worker=worker, local_teacher=local_teacher, external_teacher=external_teacher)
                execution.pop("active_call", None); _json_write(manifest_path, execution); _write_scorecard(output_dir / "tasks" / family / task_id / "scorecard.json", family=family, task_id=task_id, common=common)
                if checkpoint_hook: checkpoint_hook(f"common_terminal:{family}:{task_id}", execution)
            else:
                order = context["manifests"][family]["pair_order"]["orders"][task_id]; stages: dict[str, Any] = {}
                for arm in order:
                    if arm == "control":
                        execution["active_call"] = {"kind": "control_arm", "family": family, "task_id": task_id, "intervention": "external_teacher"}; _json_write(manifest_path, execution)
                        stages["control"] = _run_single_action(context, output_dir, family, task_id, "control", "external_teacher", baseline, worker=worker, local_teacher=local_teacher, external_teacher=external_teacher)
                        execution.pop("active_call", None); _json_write(manifest_path, execution)
                    else:
                        execution["active_call"] = {"kind": "local_first", "family": family, "task_id": task_id, "intervention": "local_teacher"}; _json_write(manifest_path, execution)
                        local_summary = _run_single_action(context, output_dir, family, task_id, "local_first", "local_teacher", baseline, worker=worker, local_teacher=local_teacher, external_teacher=external_teacher)
                        execution.pop("active_call", None); _json_write(manifest_path, execution)
                        escalation = None
                        if _valid(local_summary) and should_escalate({"validation_status": local_summary.get("validation_status")}):
                            execution["active_call"] = {"kind": "external_escalation", "family": family, "task_id": task_id, "intervention": "external_teacher"}; _json_write(manifest_path, execution)
                            escalation = _run_external_escalation(context, output_dir, task_id, baseline, local_summary, worker=worker, external_teacher=external_teacher)
                            execution.pop("active_call", None); _json_write(manifest_path, execution)
                        treatment = _treatment_summary(task_id, local_summary, escalation); _json_write(output_dir / "tasks" / family / task_id / "treatment_summary.json", treatment); stages["treatment"] = treatment["final"]; stages["treatment_detail"] = treatment
                    if checkpoint_hook: checkpoint_hook(f"stage_terminal:{family}:{task_id}:{arm}", execution)
                _write_scorecard(output_dir / "tasks" / family / task_id / "scorecard.json", family=family, task_id=task_id, control=stages["control"], treatment=stages["treatment"], treatment_detail=stages["treatment_detail"])
            execution["candidate_states"][f"{family}:{task_id}"] = "terminal"; _json_write(manifest_path, execution)
    execution.update({"status": "experiment_completed", "completed_at": utc_now(), "aggregate_path": "aggregate.json"}); _json_write(manifest_path, execution); _json_write(output_dir / "aggregate.json", aggregate_results(output_dir)); return execution


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--preregistration", type=Path, required=True); parser.add_argument("--output-dir", type=Path, required=True); parser.add_argument("--execute", action="store_true"); args = parser.parse_args()
    repo_root = Path.cwd(); context = _load_context(args.preregistration, repo_root, require_runtime=args.execute); context["git_head"] = git_head(repo_root)
    if not args.execute:
        print(json.dumps({"status": "dry_run_valid", "model_calls": 0, "control": "external_everywhere", "treatment": "validation_gated_economic_escalation", "pair_order_seed": context["preregistration"]["pair_order"]["seed"]}, sort_keys=True)); return 0
    context["preregistration_path"] = args.preregistration
    result = run_experiment(context, args.output_dir, worker=_default_worker, local_teacher=_default_local_teacher, external_teacher=_default_external_teacher); print(json.dumps(result, sort_keys=True)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
