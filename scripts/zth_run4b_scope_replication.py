#!/usr/bin/env python3
"""Durable paired Run 4B scope intervention replication driver."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from local_harness.resource_telemetry import load_approved_resource_weights
from local_harness.run4b_scope_fixture_pack import verify_manifest
from local_harness.run4a_intervention_harness import run_isolated_intervention_arm
from local_harness.supervised_capability_loop import load_task_fixture
from scripts.zth_run4_economic_routing import (
    _arm_terminal,
    _baseline_payload,
    _default_external_teacher,
    _default_local_teacher,
    _default_worker,
    _json_write,
    _read_json,
    _write_arm_artifact_index,
    canonical_sha256,
    run_baseline,
    sha256_file,
)
from scripts.zth_run4a_intervention_calibration import Run4ADriverError


ARM_NAMES = ("control", "treatment")
ARM_INTERVENTIONS = {"control": "external_teacher", "treatment": "local_teacher"}
TARGET_FAMILY = "scope-authority-boundary"
TARGET_RESOLUTION = "failure_class"
TERMINAL_STATUSES = {"experiment_completed", "experiment_incomplete"}
WEIGHTS = {"worker_time_ms": 5276.567, "local_teacher_time_ms": 16220.624, "external_teacher_time_ms": 28704.012}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git_head(root: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def _runtime_identities(preregistration: Mapping[str, Any], *, require: bool) -> dict[str, str]:
    models = preregistration["models"]
    configured = {
        "worker": os.environ.get("ZTH_CAPABILITY_WORKER_MODEL"),
        "local_teacher": os.environ.get("ZTH_CAPABILITY_TEACHER_MODEL"),
        "external_teacher": os.environ.get("ZTH_EXTERNAL_TEACHER_IDENTITY", models["external_teacher"]),
    }
    if require:
        for role in ("worker", "local_teacher", "external_teacher"):
            if configured[role] != models[role]:
                raise Run4ADriverError(f"runtime identity mismatch for {role}")
    return {role: configured[role] or models[role] for role in configured}


def validate_preregistration(prereg_path: Path, repo_root: Path, *, require_runtime_identities: bool = False) -> dict[str, Any]:
    prereg = _read_json(prereg_path)
    if prereg.get("model_calls_made") is not False:
        raise Run4ADriverError("Run 4B preregistration must remain model-call-free before execution")
    for bound in (prereg["interpretation_freeze"], prereg["run4_closeout"]):
        if sha256_file(repo_root / bound["path"]) != bound["sha256"]:
            raise Run4ADriverError(f"bound research artifact hash mismatch: {bound['path']}")

    pack_spec = prereg["fixture_pack"]
    pack_dir = repo_root / pack_spec["path"]
    manifest = verify_manifest(pack_dir, repo_root)
    for key in ("manifest_sha256", "pack_sha256"):
        if manifest[key] != pack_spec[key]:
            raise Run4ADriverError(f"fixture {key} mismatch")
    novelty_path = repo_root / pack_spec["novelty_audit_path"]
    if sha256_file(novelty_path) != pack_spec["novelty_audit_file_sha256"]:
        raise Run4ADriverError("novelty audit hash mismatch")
    if manifest["candidate_order"] != pack_spec["candidate_order"] or len(manifest["fixtures"]) != 15:
        raise Run4ADriverError("candidate order/count drift")
    if manifest["target_included_count"] != 12 or manifest["task_family"] != TARGET_FAMILY:
        raise Run4ADriverError("target count/family drift")

    frozen = prereg["frozen_inputs"]
    comparative_path = repo_root / frozen["comparative_evidence_path"]
    comparative = _read_json(comparative_path)
    if sha256_file(comparative_path) != frozen["comparative_evidence_file_sha256"] or comparative.get("freeze_sha256") != frozen["comparative_evidence_freeze_sha256"]:
        raise Run4ADriverError("Run 4A comparative evidence binding mismatch")
    resource = load_approved_resource_weights(repo_root / frozen["resource_weight_manifest_path"])
    if resource.get("manifest_sha256") != frozen["resource_weight_manifest_sha256"]:
        raise Run4ADriverError("resource manifest binding mismatch")
    if resource.get("weights") != {**resource.get("weights", {}), **WEIGHTS}:
        raise Run4ADriverError("resource priors drift")
    for item in prereg["validators"]:
        if sha256_file(repo_root / item["path"]) != item["sha256"]:
            raise Run4ADriverError(f"validator hash mismatch: {item['path']}")
    for key, expected in prereg["timeouts_seconds"].items():
        env_key = {"worker": "ZTH_CAPABILITY_WORKER_TIMEOUT", "local_teacher": "ZTH_CAPABILITY_TEACHER_TIMEOUT", "external_teacher": None}[key]
        actual = 120 if key == "external_teacher" else int(os.environ.get(env_key, expected))
        if actual != expected:
            raise Run4ADriverError(f"timeout binding mismatch: {key}")
    identities = _runtime_identities(prereg, require=require_runtime_identities)
    driver = prereg["driver"]
    if sha256_file(repo_root / driver["path"]) != driver["sha256"]:
        raise Run4ADriverError("Run 4B driver hash mismatch")
    if prereg["target"] != {"family": TARGET_FAMILY, "resolution": TARGET_RESOLUTION, "evidence_key": TARGET_FAMILY, "included_count": 12}:
        raise Run4ADriverError("target evidence binding mismatch")
    interventions = prereg["interventions"]
    if any((interventions.get(key) != value) for key, value in {"control": "external_teacher", "treatment": "local_teacher", "deterministic_patch": False, "fallback_escalation": False}.items()):
        raise Run4ADriverError("intervention semantics mismatch")
    return {"preregistration": prereg, "manifest": manifest, "pack_dir": pack_dir, "comparative": comparative, "identities": identities, "preregistration_path": prereg_path}


def _write_pair_summary(task_dir: Path, task_id: str, arm_summaries: Mapping[str, Any]) -> dict[str, Any]:
    valid = {
        arm: summary.get("capability_verdict_available") is True and summary.get("transport_valid") is True and summary.get("transport_classification") == "model_response"
        for arm, summary in arm_summaries.items()
    }
    excluded = not all(valid.values())
    control, treatment = arm_summaries["control"], arm_summaries["treatment"]
    outcome = "both_solve" if control.get("deterministically_validated_rescue") and treatment.get("deterministically_validated_rescue") else "external_only" if control.get("deterministically_validated_rescue") else "local_only" if treatment.get("deterministically_validated_rescue") else "neither"
    failures = []
    for arm, summary in arm_summaries.items():
        if not valid[arm]:
            artifact = summary.get("infrastructure_artifact")
            failures.append({"arm": arm, "intervention": summary.get("intervention"), "role": (artifact or summary.get("intervention", "unknown")).split(".", 1)[0], "artifact": artifact})
    pair = {
        "schema": "zth_run4b_scope_pair_summary_v1", "task_id": task_id,
        "disposition": "infrastructure_excluded" if excluded else "terminal", "valid_arms": valid,
        "infrastructure_failures": failures,
        "control": {"intervention": control.get("intervention"), "rescue": bool(control.get("deterministically_validated_rescue")), "elapsed_ms": control.get("realized_elapsed_ms")},
        "treatment": {"intervention": treatment.get("intervention"), "rescue": bool(treatment.get("deterministically_validated_rescue")), "elapsed_ms": treatment.get("realized_elapsed_ms")},
        "paired_outcome": outcome, "authority": "review_required_no_evidence_merge",
    }
    _json_write(task_dir / "pair_summary.json", pair)
    return pair


def _telemetry_from_artifact(artifact: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """Return only explicitly recorded call telemetry; never infer timing."""
    metadata = artifact.get("metadata")
    if isinstance(metadata, Mapping) and isinstance(metadata.get("resource_telemetry"), Mapping):
        return metadata["resource_telemetry"]
    telemetry = artifact.get("resource_telemetry")
    return telemetry if isinstance(telemetry, Mapping) else None


def execution_resource_history(output_dir: Path) -> dict[str, Any]:
    """Account for every durable call attempt, including excluded pairs.

    This is intentionally separate from the comparable-pair capability and
    cost denominators.  A call is counted from a durable ``call_started``
    transition, while validity and timing come only from its captured durable
    response or infrastructure artifact.
    """
    attempts_by_role: dict[str, int] = {}
    valid_by_role: dict[str, int] = {}
    infrastructure_by_role: dict[str, int] = {}
    elapsed_by_role: dict[str, float] = {}
    elapsed_coverage_by_role: dict[str, int] = {}
    attempts_by_phase: dict[str, int] = {}
    infrastructure_by_arm: dict[str, int] = {}
    seen: set[tuple[str, str]] = set()

    trajectory_paths = sorted(output_dir.glob("candidates/*/trajectory.jsonl")) + sorted(output_dir.glob("tasks/*/arms/*/trajectory.jsonl"))
    for trajectory_path in trajectory_paths:
        rows = [_read_json_line(line) for line in trajectory_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        completions = {
            row.get("call_id"): row
            for row in rows
            if row.get("transition") in {"response_captured", "infrastructure_failed"}
        }
        relative = trajectory_path.relative_to(output_dir).parts
        phase = "baseline" if relative[0] == "candidates" else relative[3]
        arm_label = None if phase == "baseline" else phase
        for started in (row for row in rows if row.get("transition") == "call_started"):
            call_id = str(started.get("call_id"))
            key = (str(trajectory_path), call_id)
            if key in seen:
                continue
            seen.add(key)
            role = str(started.get("role") or "unknown")
            attempts_by_role[role] = attempts_by_role.get(role, 0) + 1
            attempts_by_phase[phase] = attempts_by_phase.get(phase, 0) + 1
            completion = completions.get(started.get("call_id"))
            if completion is None:
                continue
            artifact_ref = completion.get("artifact_ref")
            artifact = _read_json(trajectory_path.parent / artifact_ref) if artifact_ref else {}
            if completion.get("transition") == "infrastructure_failed":
                infrastructure_by_role[role] = infrastructure_by_role.get(role, 0) + 1
                if arm_label is not None:
                    infrastructure_by_arm[arm_label] = infrastructure_by_arm.get(arm_label, 0) + 1
            else:
                artifact_metadata = artifact.get("metadata", {}) if isinstance(artifact, Mapping) else {}
                classification = artifact_metadata.get("transport_classification", artifact.get("transport_classification")) if isinstance(artifact, Mapping) else None
                transport_valid = artifact_metadata.get("transport_valid", artifact.get("transport_valid")) if isinstance(artifact, Mapping) else None
                if transport_valid is True and classification == "model_response":
                    valid_by_role[role] = valid_by_role.get(role, 0) + 1
            telemetry = _telemetry_from_artifact(artifact)
            elapsed = telemetry.get("elapsed_ms") if telemetry else None
            if isinstance(elapsed, (int, float)):
                elapsed_by_role[role] = elapsed_by_role.get(role, 0.0) + float(elapsed)
                elapsed_coverage_by_role[role] = elapsed_coverage_by_role.get(role, 0) + 1

    return {
        "schema": "zth_run4b_execution_resource_history_v1",
        "total_model_call_attempts": sum(attempts_by_role.values()),
        "total_worker_attempts": attempts_by_role.get("worker", 0),
        "total_teacher_attempts": attempts_by_role.get("local_teacher", 0) + attempts_by_role.get("external_teacher", 0),
        "attempts_by_role": attempts_by_role,
        "attempts_by_phase": attempts_by_phase,
        "valid_responses_by_role": valid_by_role,
        "infrastructure_failures_by_role": infrastructure_by_role,
        "infrastructure_failures_by_arm": infrastructure_by_arm,
        "realized_elapsed_ms_by_role": elapsed_by_role,
        "elapsed_telemetry_coverage_by_role": elapsed_coverage_by_role,
        "accounting_scope": "all durable call attempts, including infrastructure-excluded pairs",
    }


def _read_json_line(line: str) -> dict[str, Any]:
    try:
        value = json.loads(line)
    except json.JSONDecodeError as exc:
        raise Run4ADriverError(f"invalid trajectory transition: {exc}") from exc
    if not isinstance(value, dict):
        raise Run4ADriverError("trajectory transition must be an object")
    return value


def aggregate_results(execution: Mapping[str, Any], output_dir: Path) -> dict[str, Any]:
    pairs = [_read_json(path) for path in sorted(output_dir.glob("tasks/*/pair_summary.json"))]
    comparable = [pair for pair in pairs if pair.get("disposition") == "terminal" and all(pair.get("valid_arms", {}).values())]
    excluded = [pair for pair in pairs if pair not in comparable]
    control_solve = sum(pair["control"]["rescue"] for pair in comparable)
    treatment_solve = sum(pair["treatment"]["rescue"] for pair in comparable)
    control_elapsed = sum(float(pair["control"]["elapsed_ms"] or 0) for pair in comparable)
    treatment_elapsed = sum(float(pair["treatment"]["elapsed_ms"] or 0) for pair in comparable)
    by_arm: dict[str, int] = {}; by_role: dict[str, int] = {}
    for pair in excluded:
        for failure in pair.get("infrastructure_failures", []):
            by_arm[failure["arm"]] = by_arm.get(failure["arm"], 0) + 1
            by_role[failure.get("role") or "unknown"] = by_role.get(failure.get("role") or "unknown", 0) + 1
    available = bool(comparable)
    resource_history = execution_resource_history(output_dir)
    result = {
        "schema": "zth_run4b_scope_aggregate_v1", "status": "review_required",
        "selected_pairs": len(pairs), "comparable_pairs": len(comparable), "infrastructure_excluded_pairs": len(excluded),
        "control": {"intervention": "external_teacher", "valid_responses": len(comparable), "validated_passes": control_solve, "solve_rate": control_solve / len(comparable) if available else None, "post_baseline_elapsed_ms": control_elapsed if available else None, "worker_retry_calls": len(comparable), "external_teacher_calls": len(comparable), "local_teacher_calls": 0, "expected_decision_cost_ms": 33980.579 * len(comparable)},
        "treatment": {"intervention": "local_teacher", "valid_responses": len(comparable), "validated_passes": treatment_solve, "solve_rate": treatment_solve / len(comparable) if available else None, "post_baseline_elapsed_ms": treatment_elapsed if available else None, "worker_retry_calls": len(comparable), "external_teacher_calls": 0, "local_teacher_calls": len(comparable), "expected_decision_cost_ms": 21497.191 * len(comparable)},
        "paired_outcomes": {name: sum(pair["paired_outcome"] == name for pair in comparable) for name in ("both_solve", "external_only", "local_only", "neither")},
        "quality_preserved": treatment_solve >= control_solve if available else None,
        "resource_reduced": treatment_elapsed < control_elapsed if available else None,
        "scope_efficiency_replication": treatment_solve >= control_solve and treatment_elapsed < control_elapsed if available else None,
        "result_available": available,
        "infrastructure_exclusions": {"by_arm": by_arm, "by_role": by_role},
        "scientific_comparable_resource": {
            "scope": "comparable pairs only",
            "control_post_baseline_elapsed_ms": control_elapsed if available else None,
            "treatment_post_baseline_elapsed_ms": treatment_elapsed if available else None,
        },
        "execution_resource_history": resource_history,
        "execution_manifest_sha256": sha256_file(output_dir / "execution_manifest.json"),
        "authority": "review_required_no_evidence_merge",
    }
    _json_write(output_dir / "aggregate.json", result)
    return result


def run_experiment(context: Mapping[str, Any], output_dir: Path, *, worker: Callable[[str], Any] = _default_worker, local_teacher: Callable[[str], Any] = _default_local_teacher, external_teacher: Callable[..., Any] = _default_external_teacher) -> dict[str, Any]:
    prereg = context["preregistration"]; manifest = context["manifest"]
    manifest_path = output_dir / "execution_manifest.json"
    if manifest_path.exists():
        execution = _read_json(manifest_path)
        if execution.get("schema") != "zth_run4b_scope_execution_manifest_v1" or execution.get("preregistration_sha256") != sha256_file(context["preregistration_path"]) or execution.get("fixture_pack_sha256") != manifest["pack_sha256"] or execution.get("pair_orders") != manifest["pair_order"]["orders"]:
            raise Run4ADriverError("Run 4B execution binding mismatch")
        if execution.get("status") in TERMINAL_STATUSES and execution.get("completed_at"):
            return execution
        if execution.get("active_call"):
            raise Run4ADriverError("ambiguous active call; refusing to resume")
    elif output_dir.exists() and any(output_dir.iterdir()):
        raise Run4ADriverError("existing output directory lacks a bound execution manifest")
    else:
        output_dir.mkdir(parents=True, exist_ok=True)
        execution = {"schema": "zth_run4b_scope_execution_manifest_v1", "status": "experiment_running", "started_at": utc_now(), "git_head": context.get("git_head"), "preregistration_sha256": sha256_file(context["preregistration_path"]), "fixture_pack_sha256": manifest["pack_sha256"], "candidate_states": {}, "pair_orders": manifest["pair_order"]["orders"], "model_calls_started": True}
        _json_write(manifest_path, execution)
    tasks = {row["task_id"]: load_task_fixture(context["pack_dir"] / Path(row["path"]).name) for row in manifest["fixtures"]}
    summaries: dict[str, Any] = {}
    for task_id in manifest["candidate_order"]:
        candidate_dir = output_dir / "candidates" / task_id
        execution["active_call"] = {"kind": "baseline", "task_id": task_id, "role": "worker"}; _json_write(manifest_path, execution)
        summaries[task_id] = run_baseline(tasks[task_id], candidate_dir, worker=worker)
        execution.pop("active_call", None); execution["candidate_states"][task_id] = "baseline_terminal"; _json_write(manifest_path, execution)
    eligible = [task_id for task_id in manifest["candidate_order"] if summaries[task_id].get("eligible") is True]
    selected = eligible[:manifest["target_included_count"]]
    selection = {"candidate_order": manifest["candidate_order"], "eligible": eligible, "included_task_ids": selected, "reserve_task_ids": [task_id for task_id in manifest["candidate_order"] if task_id not in selected], "selected_count": len(selected), "complete": len(selected) == manifest["target_included_count"]}
    _json_write(output_dir / "selection.json", selection)
    if not selection["complete"]:
        execution.update({"status": "experiment_incomplete", "completed_at": utc_now(), "selection": selection}); _json_write(manifest_path, execution); return execution
    for task_id in selected:
        task_dir = output_dir / "tasks" / task_id
        baseline = _baseline_payload(output_dir / "candidates" / task_id, summaries[task_id])
        for arm in manifest["pair_order"]["orders"][task_id]:
            intervention = ARM_INTERVENTIONS[arm]
            arm_dir = task_dir / "arms" / arm
            binding = {"schema": "zth_run4b_scope_arm_binding_v1", "task_id": task_id, "arm": arm, "actual_intervention": intervention, "comparative_freeze_sha256": prereg["frozen_inputs"]["comparative_evidence_freeze_sha256"], "baseline_summary_sha256": canonical_sha256(baseline)}
            terminal = _arm_terminal(arm_dir, binding)
            if terminal is None:
                _json_write(arm_dir / "arm_binding.json", binding)
                execution["active_call"] = {"kind": "paired_arm", "task_id": task_id, "arm": arm, "intervention": intervention}; _json_write(manifest_path, execution)
                run_isolated_intervention_arm(tasks[task_id], baseline, intervention=intervention, out_dir=arm_dir, worker=worker, local_teacher=local_teacher, external_teacher=external_teacher, deterministic_patch=None)
                _write_arm_artifact_index(arm_dir)
                execution.pop("active_call", None)
            execution["candidate_states"][task_id] = "arm_terminal"; _json_write(manifest_path, execution)
        _write_pair_summary(task_dir, task_id, {arm: _read_json(task_dir / "arms" / arm / "arm_summary.json") for arm in ARM_NAMES})
    execution.update({"status": "experiment_completed", "completed_at": utc_now(), "selection": selection, "aggregate_path": "aggregate.json"}); _json_write(manifest_path, execution); aggregate_results(execution, output_dir); return execution


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    root = Path.cwd()
    context = validate_preregistration(args.preregistration, root, require_runtime_identities=args.execute)
    context["git_head"] = _git_head(root)
    if not args.execute:
        print(json.dumps({"status": "dry_run_valid", "model_calls": 0, "control": "external_teacher", "treatment": "local_teacher", "pair_order_seed": context["manifest"]["pair_order"]["seed"]}, sort_keys=True)); return 0
    context["preregistration_path"] = args.preregistration
    result = run_experiment(context, args.output_dir)
    print(json.dumps(result, sort_keys=True)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
