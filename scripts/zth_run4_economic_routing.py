#!/usr/bin/env python3
"""Durable paired execution driver for the targeted economic Run 4 experiment."""

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

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from local_harness.icm_spec import WorkerResponse
from local_harness.resource_telemetry import load_approved_resource_weights
from local_harness.run4_economic_fixture_pack import verify_manifest
from local_harness.run4_economic_policy import choose_intervention, verify_policy_freeze
from local_harness.run4a_intervention_harness import run_isolated_intervention_arm
from local_harness.supervised_capability_loop import load_task_fixture
from scripts.zth_run4a_intervention_calibration import (
    Run4ADriverError,
    _append_transition,
    _default_external_teacher,
    _default_local_teacher,
    _default_worker,
    _json_write,
    _read_json,
    _response_payload,
    _validator_result,
    _write_arm_artifact_index,
    canonical_sha256,
    run_baseline,
    sha256_file,
)


ARM_NAMES = ("control", "treatment")
TARGET_FAMILY = "triage-routing"
TERMINAL_STATUSES = {"experiment_completed", "experiment_incomplete"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _no_ambiguous_started(path: Path) -> None:
    if not path.exists():
        return
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    captured = {row.get("call_id") for row in rows if row.get("transition") in {"response_captured", "infrastructure_failed"}}
    if any(row.get("call_id") not in captured for row in rows if row.get("transition") == "call_started"):
        raise Run4ADriverError(f"ambiguous started call in {path}")


def _git_head(repo_root: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True).strip()


def _runtime_identities(preregistration: Mapping[str, Any], *, require: bool) -> dict[str, str]:
    models = preregistration["models"]
    configured = {
        "worker": os.environ.get("ZTH_CAPABILITY_WORKER_MODEL"),
        "local_teacher": os.environ.get("ZTH_CAPABILITY_TEACHER_MODEL"),
        "external_teacher": os.environ.get("ZTH_EXTERNAL_TEACHER_IDENTITY", models["external_teacher"]),
    }
    if require:
        for role in ("worker", "local_teacher"):
            if not configured[role]:
                raise Run4ADriverError(f"missing runtime identity: {role}")
        for role, expected in models.items():
            key = "external_teacher" if role == "external_teacher" else role
            if configured[key] != expected:
                raise Run4ADriverError(f"runtime identity mismatch for {key}")
    return {role: configured[role] or models[role] for role in ("worker", "local_teacher", "external_teacher")}


def validate_preregistration(prereg_path: Path, repo_root: Path, *, require_runtime_identities: bool = False) -> dict[str, Any]:
    prereg = _read_json(prereg_path)
    if prereg.get("model_calls_made") is not False:
        raise Run4ADriverError("Run 4 preregistration must remain model-call-free before execution")
    pack = prereg["fixture_pack"]
    pack_dir = repo_root / pack["path"]
    manifest = verify_manifest(pack_dir, repo_root)
    for key in ("manifest_sha256", "pack_sha256"):
        if pack[key] != manifest[key]:
            raise Run4ADriverError(f"fixture {key} mismatch")
    if pack["candidate_ids"] != manifest["candidate_order"]:
        raise Run4ADriverError("candidate order drift")
    if len(manifest["fixtures"]) != 15 or manifest["target_included_count"] != 12:
        raise Run4ADriverError("candidate/target count drift")
    novelty_path = repo_root / pack["novelty_audit_path"]
    if sha256_file(novelty_path) != pack["novelty_audit_file_sha256"]:
        raise Run4ADriverError("novelty audit mismatch")

    frozen = prereg["frozen_inputs"]
    comparative = repo_root / frozen["comparative_evidence_path"]
    comparative_artifact = _read_json(comparative)
    if comparative_artifact["freeze_sha256"] != frozen["comparative_evidence_freeze_sha256"]:
        raise Run4ADriverError("comparative evidence digest mismatch")
    policy_path = repo_root / frozen["policy_freeze_path"]
    policy = verify_policy_freeze(policy_path, comparative, repo_root / frozen["router_source_path"])
    if sha256_file(policy_path) != frozen["policy_freeze_file_sha256"]:
        raise Run4ADriverError("policy freeze file hash mismatch")
    if sha256_file(repo_root / frozen["router_source_path"]) != frozen["router_source_sha256"]:
        raise Run4ADriverError("router source hash mismatch")
    resource = load_approved_resource_weights(repo_root / frozen["resource_weight_manifest_path"])
    if resource.get("manifest_sha256") != frozen["resource_weight_manifest_sha256"]:
        raise Run4ADriverError("resource manifest digest mismatch")
    if resource.get("weights", {}).get("worker_time_ms") != 5276.567 or resource["weights"].get("external_teacher_time_ms") != 28704.012:
        raise Run4ADriverError("resource priors drift")
    patch_path = repo_root / frozen["deterministic_patch_path"]
    if sha256_file(patch_path) != frozen["deterministic_patch_sha256"]:
        raise Run4ADriverError("patch hash mismatch")
    for item in prereg["validators"]:
        if sha256_file(repo_root / item["path"]) != item["sha256"]:
            raise Run4ADriverError(f"validator hash mismatch: {item['path']}")
    for key, value in prereg["timeouts_seconds"].items():
        env_key = {"worker": "ZTH_CAPABILITY_WORKER_TIMEOUT", "local_teacher": "ZTH_CAPABILITY_TEACHER_TIMEOUT", "external_teacher": None}[key]
        actual = 120 if key == "external_teacher" else int(os.environ.get(env_key, value))
        if actual != value:
            raise Run4ADriverError(f"timeout binding mismatch: {key}")
    identities = _runtime_identities(prereg, require=require_runtime_identities)
    driver = prereg["driver"]
    if sha256_file(repo_root / driver["path"]) != driver["sha256"]:
        raise Run4ADriverError("paired driver hash mismatch")
    if prereg["target"]["family"] != TARGET_FAMILY or prereg["target"]["resolution"] != "task_family" or prereg["target"]["evidence_key"] != TARGET_FAMILY:
        raise Run4ADriverError("target evidence binding mismatch")
    return {"preregistration": prereg, "manifest": manifest, "pack_dir": pack_dir, "comparative": comparative_artifact, "policy": policy, "identities": identities}


def _baseline_payload(candidate_dir: Path, summary: Mapping[str, Any]) -> dict[str, Any]:
    raw_ref = summary.get("raw_response")
    if not raw_ref or not summary.get("validation"):
        raise Run4ADriverError(f"baseline lacks valid failure artifacts: {candidate_dir}")
    return {
        "task_id": summary["task_id"],
        "transport_valid": summary["transport_valid"],
        "transport_classification": summary["transport_classification"],
        "validation": summary["validation"],
        "raw": _read_json(candidate_dir / raw_ref),
    }


def _arm_terminal(arm_dir: Path, binding: Mapping[str, Any]) -> dict[str, Any] | None:
    summary_path = arm_dir / "arm_summary.json"
    if not summary_path.exists() and not arm_dir.exists():
        return None
    if not summary_path.exists() or not (arm_dir / "arm_binding.json").exists() or not (arm_dir / "arm_artifacts.json").exists():
        raise Run4ADriverError(f"incomplete paired arm: {arm_dir}")
    if _read_json(arm_dir / "arm_binding.json") != dict(binding):
        raise Run4ADriverError(f"paired arm binding drift: {arm_dir}")
    _no_ambiguous_started(arm_dir / "trajectory.jsonl")
    return _read_json(summary_path)


def _write_pair_summary(task_dir: Path, task_id: str, policy_outputs: Mapping[str, Any], arm_summaries: Mapping[str, Any]) -> dict[str, Any]:
    control = arm_summaries["control"]
    treatment = arm_summaries["treatment"]
    if not all(summary.get("transport_valid") is True and summary.get("transport_classification") == "model_response" for summary in arm_summaries.values()):
        disposition = "infrastructure_excluded"
    else:
        disposition = "terminal"
    pair = {
        "schema": "zth_run4_economic_pair_summary_v1",
        "task_id": task_id,
        "disposition": disposition,
        "policy_outputs": dict(policy_outputs),
        "control": {"intervention": control.get("intervention"), "rescue": bool(control.get("deterministically_validated_rescue")), "elapsed_ms": control.get("realized_elapsed_ms")},
        "treatment": {"intervention": treatment.get("intervention"), "rescue": bool(treatment.get("deterministically_validated_rescue")), "elapsed_ms": treatment.get("realized_elapsed_ms")},
        "paired_outcome": "both_solve" if control.get("deterministically_validated_rescue") and treatment.get("deterministically_validated_rescue") else "control_only" if control.get("deterministically_validated_rescue") else "treatment_only" if treatment.get("deterministically_validated_rescue") else "neither",
        "authority": "review_required_no_router_mutation",
    }
    _json_write(task_dir / "pair_summary.json", pair)
    return pair


def aggregate_results(execution: Mapping[str, Any], output_dir: Path) -> dict[str, Any]:
    pairs = [_read_json(path) for path in sorted(output_dir.glob("tasks/*/pair_summary.json"))]
    control_solve = sum(item["control"]["rescue"] for item in pairs)
    treatment_solve = sum(item["treatment"]["rescue"] for item in pairs)
    control_elapsed = sum(float(item["control"]["elapsed_ms"] or 0) for item in pairs)
    treatment_elapsed = sum(float(item["treatment"]["elapsed_ms"] or 0) for item in pairs)
    outcome_counts = {name: sum(item["paired_outcome"] == name for item in pairs) for name in ("both_solve", "control_only", "treatment_only", "neither")}
    result = {
        "schema": "zth_run4_economic_aggregate_v1",
        "status": "review_required",
        "candidate_baselines": 15,
        "included_pairs": len(pairs),
        "control": {"validated_passes": control_solve, "solve_rate": control_solve / len(pairs) if pairs else 0.0, "post_baseline_elapsed_ms": control_elapsed, "worker_retry_calls": len(pairs), "external_teacher_calls": len(pairs), "local_teacher_calls": 0, "expected_decision_cost_ms": 33980.579 * len(pairs)},
        "treatment": {"validated_passes": treatment_solve, "solve_rate": treatment_solve / len(pairs) if pairs else 0.0, "post_baseline_elapsed_ms": treatment_elapsed, "worker_retry_calls": len(pairs), "external_teacher_calls": 0, "local_teacher_calls": 0, "expected_decision_cost_ms": 5276.567 * len(pairs)},
        "paired_outcomes": outcome_counts,
        "quality_preserved": treatment_solve >= control_solve,
        "resource_reduced": treatment_elapsed < control_elapsed,
        "economic_routing_success": treatment_solve >= control_solve and treatment_elapsed < control_elapsed,
        "infrastructure_exclusions": 0,
        "execution_manifest_sha256": sha256_file(output_dir / "execution_manifest.json"),
        "authority": "review_required_no_evidence_merge",
    }
    _json_write(output_dir / "aggregate.json", result)
    return result


def run_experiment(context: Mapping[str, Any], output_dir: Path, *, worker: Callable[[str], WorkerResponse] = _default_worker, local_teacher: Callable[[str], WorkerResponse] = _default_local_teacher, external_teacher: Callable[..., Any] = _default_external_teacher, deterministic_patch: Mapping[str, Any] | None = None) -> dict[str, Any]:
    prereg = context["preregistration"]
    manifest = context["manifest"]
    existing = output_dir / "execution_manifest.json"
    if existing.exists():
        execution = _read_json(existing)
        if execution.get("status") in TERMINAL_STATUSES and execution.get("completed_at"):
            return execution
        if execution.get("active_call"):
            raise Run4ADriverError("ambiguous active call; refusing to resume")
    else:
        output_dir.mkdir(parents=True, exist_ok=False)
        execution = {"schema": "zth_run4_economic_execution_manifest_v1", "status": "experiment_running", "started_at": utc_now(), "git_head": context.get("git_head"), "preregistration_sha256": sha256_file(context["preregistration_path"]), "fixture_pack_sha256": manifest["pack_sha256"], "candidate_states": {}, "arm_orders": manifest["pair_order"]["orders"], "model_calls_started": True}
        _json_write(existing, execution)
    tasks = {row["task_id"]: load_task_fixture(context["pack_dir"] / Path(row["path"]).name) for row in manifest["fixtures"]}
    baseline_summaries: dict[str, Any] = {}
    for task_id in manifest["candidate_order"]:
        candidate_dir = output_dir / "candidates" / task_id
        execution["active_call"] = {"kind": "baseline", "task_id": task_id, "role": "worker"}
        _json_write(existing, execution)
        baseline_summaries[task_id] = run_baseline(tasks[task_id], candidate_dir, worker=worker)
        execution.pop("active_call", None)
        execution["candidate_states"][task_id] = "baseline_terminal"
        _json_write(existing, execution)
    eligible = [task_id for task_id in manifest["candidate_order"] if baseline_summaries[task_id].get("eligible") is True]
    selected = eligible[: manifest["target_included_count"]]
    selection = {"candidate_order": manifest["candidate_order"], "eligible": eligible, "included_task_ids": selected, "reserve_task_ids": [task_id for task_id in manifest["candidate_order"] if task_id not in selected], "selected_count": len(selected), "complete": len(selected) == manifest["target_included_count"]}
    _json_write(output_dir / "selection.json", selection)
    if not selection["complete"]:
        execution["status"] = "experiment_incomplete"
        execution["completed_at"] = utc_now()
        execution["selection"] = selection
        _json_write(existing, execution)
        return execution
    policy_evidence = context["comparative"]
    policy_outputs = {"control": choose_intervention(policy_evidence, TARGET_FAMILY, "capability_first"), "treatment": choose_intervention(policy_evidence, TARGET_FAMILY, "cheapest_supported_positive")}
    for task_id in selected:
        task_dir = output_dir / "tasks" / task_id
        baseline = _baseline_payload(output_dir / "candidates" / task_id, baseline_summaries[task_id])
        for arm in manifest["pair_order"]["orders"][task_id]:
            actual = policy_outputs[arm]["recommended_intervention"]
            arm_dir = task_dir / "arms" / arm
            binding = {"schema": "zth_run4_economic_arm_binding_v1", "task_id": task_id, "arm": arm, "actual_intervention": actual, "policy_sha256": prereg["frozen_inputs"]["policy_freeze_sha256"], "comparative_freeze_sha256": prereg["frozen_inputs"]["comparative_evidence_freeze_sha256"], "baseline_summary_sha256": canonical_sha256(baseline)}
            terminal = _arm_terminal(arm_dir, binding)
            if terminal is None:
                _json_write(arm_dir / "arm_binding.json", binding)
                execution["active_call"] = {"kind": "paired_arm", "task_id": task_id, "arm": arm, "intervention": actual}
                _json_write(existing, execution)
                run_isolated_intervention_arm(tasks[task_id], baseline, intervention=actual, out_dir=arm_dir, worker=worker, local_teacher=local_teacher, external_teacher=external_teacher, deterministic_patch=deterministic_patch if actual == "deterministic_patch_retry" else None)
                _write_arm_artifact_index(arm_dir)
                terminal = _read_json(arm_dir / "arm_summary.json")
                execution.pop("active_call", None)
            execution["candidate_states"][task_id] = "arm_terminal"
            _json_write(existing, execution)
            task_dir.mkdir(parents=True, exist_ok=True)
        _write_pair_summary(task_dir, task_id, policy_outputs, {arm: _read_json(task_dir / "arms" / arm / "arm_summary.json") for arm in ARM_NAMES})
    execution["status"] = "experiment_completed"
    execution["completed_at"] = utc_now()
    execution["selection"] = selection
    execution["aggregate_path"] = "aggregate.json"
    _json_write(existing, execution)
    aggregate_results(execution, output_dir)
    return execution


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    root = Path.cwd()
    context = validate_preregistration(args.preregistration, root, require_runtime_identities=args.execute)
    context["preregistration_path"] = args.preregistration
    context["git_head"] = _git_head(root)
    if not args.execute:
        print(json.dumps({"status": "dry_run_valid", "model_calls": 0, "policy_matrix": context["policy"]["expected_policy_matrix"]}, sort_keys=True))
        return 0
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise Run4ADriverError("output directory is not new")
    frozen = context["preregistration"]["frozen_inputs"]
    patch = {"patch_id": frozen["deterministic_patch_id"], "patch_path": str(root / frozen["deterministic_patch_path"]), "patch_sha256": frozen["deterministic_patch_sha256"]}
    result = run_experiment(context, args.output_dir, deterministic_patch=patch)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
