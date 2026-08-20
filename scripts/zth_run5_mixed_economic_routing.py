#!/usr/bin/env python3
"""Execute the frozen, experiment-only mixed-portfolio Run 5 protocol."""

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

from local_harness.run4a_intervention_harness import run_isolated_intervention_arm
from scripts.zth_run4a_intervention_calibration import (
    Run4ADriverError,
    _append_transition,
    _json_write,
    _read_json,
    _transitions,
    _write_arm_artifact_index,
    run_baseline,
)
from scripts.zth_run4_economic_routing import _arm_terminal, _baseline_payload
from local_harness.run5_mixed_economic_policy import (
    ACTION_COSTS_MS,
    FAMILY_MATRIX,
    POLICY_NAMES,
    RESOURCE_PRIORS_MS,
    canonical_sha256,
    load_policy_freeze,
    verify_matrix,
)
from local_harness.run5_mixed_fixture_pack import PACKS, verify_manifest
from local_harness.supervised_capability_loop import load_task_fixture


TERMINAL_STATUSES = {"experiment_completed", "experiment_incomplete"}
VALID_DISPOSITIONS = {"ready_for_review", "unresolved"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_head(repo_root: Path) -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True, capture_output=True, check=True).stdout.strip()


def _assert_no_ambiguous(path: Path) -> None:
    rows = _transitions(path)
    completed = {row.get("call_id") for row in rows if row.get("transition") in {"response_captured", "infrastructure_failed"}}
    ambiguous = [row for row in rows if row.get("transition") == "call_started" and row.get("call_id") not in completed]
    if ambiguous:
        raise Run4ADriverError(f"ambiguous started call in {path}")


def _terminal_execution(value: Mapping[str, Any]) -> bool:
    return value.get("status") == "experiment_completed" or (value.get("status") == "experiment_incomplete" and bool(value.get("completed_at")))


def _task_map(repo_root: Path, manifests: Mapping[str, Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    result = {}
    for family, manifest in manifests.items():
        for row in manifest["fixtures"]:
            task = load_task_fixture(repo_root / row["path"])
            result[task["task_id"]] = task
    return result


def _load_context(prereg_path: Path, repo_root: Path, *, require_runtime: bool) -> dict[str, Any]:
    prereg = _read_json(prereg_path)
    if prereg.get("model_calls_made") is not False:
        raise Run4ADriverError("Run 5 preregistration must remain model-call-free before execution")
    policy_binding = prereg["policy_freeze"]
    policy_path = repo_root / policy_binding["path"]
    if sha256_file(policy_path) != policy_binding["file_sha256"]:
        raise Run4ADriverError("Run 5 policy freeze file hash mismatch")
    policy = load_policy_freeze(policy_path)
    if policy.get("policy_sha256") != policy_binding["canonical_sha256"]:
        raise Run4ADriverError("Run 5 policy canonical digest mismatch")
    policy_source = policy["policy_source"]
    if sha256_file(repo_root / policy_source["path"]) != policy_source["sha256"]:
        raise Run4ADriverError("Run 5 policy source hash mismatch")
    verify_matrix()
    manifests = {}
    for family in ("triage", "scope"):
        binding = prereg["fixture_packs"][family]
        pack_dir = repo_root / binding["path"]
        manifest = verify_manifest(pack_dir, repo_root)
        if manifest["manifest_sha256"] != binding["manifest_sha256"] or manifest["pack_sha256"] != binding["pack_sha256"]:
            raise Run4ADriverError(f"{family} fixture binding mismatch")
        if sha256_file(pack_dir / "novelty_audit.json") != binding["novelty_audit_sha256"]:
            raise Run4ADriverError(f"{family} novelty audit binding mismatch")
        if manifest["candidate_order"] != binding["candidate_order"] or manifest["target_included_count"] != 12:
            raise Run4ADriverError(f"{family} candidate order/count drift")
        manifests[family] = manifest
    for item in prereg["evidence_inputs"]:
        if sha256_file(repo_root / item["path"]) != item["sha256"]:
            raise Run4ADriverError(f"evidence input hash mismatch: {item['path']}")
    resource = prereg["resource_manifest"]
    if sha256_file(repo_root / resource["path"]) != resource["sha256"]:
        raise Run4ADriverError("resource manifest hash mismatch")
    loaded_resource = _read_json(repo_root / resource["path"])
    if loaded_resource.get("manifest_sha256") != resource["canonical_sha256"] or loaded_resource.get("weights", {}).get("worker_time_ms") != RESOURCE_PRIORS_MS["worker_time_ms"] or loaded_resource.get("weights", {}).get("local_teacher_time_ms") != RESOURCE_PRIORS_MS["local_teacher_time_ms"] or loaded_resource.get("weights", {}).get("external_teacher_time_ms") != RESOURCE_PRIORS_MS["external_teacher_time_ms"]:
        raise Run4ADriverError("resource priors drift")
    patch = prereg["deterministic_patch"]
    if sha256_file(repo_root / patch["path"]) != patch["sha256"]:
        raise Run4ADriverError("deterministic patch binding mismatch")
    for item in prereg["validators"]:
        if sha256_file(repo_root / item["path"]) != item["sha256"]:
            raise Run4ADriverError(f"validator hash mismatch: {item['path']}")
    driver = prereg["driver"]
    driver_path = repo_root / driver["path"]
    if sha256_file(driver_path) != driver["sha256"]:
        raise Run4ADriverError("Run 5 driver hash mismatch")
    timeouts = prereg["timeouts_seconds"]
    effective = {"worker": int(os.environ.get("ZTH_CAPABILITY_WORKER_TIMEOUT", timeouts["worker"])), "local_teacher": int(os.environ.get("ZTH_CAPABILITY_TEACHER_TIMEOUT", timeouts["local_teacher"])), "external_teacher": 120}
    if effective != timeouts:
        raise Run4ADriverError("Run 5 timeout binding mismatch")
    models = prereg["models"]
    configured = {"worker": os.environ.get("ZTH_CAPABILITY_WORKER_MODEL"), "local_teacher": os.environ.get("ZTH_CAPABILITY_TEACHER_MODEL"), "external_teacher": os.environ.get("ZTH_EXTERNAL_TEACHER_IDENTITY")}
    if require_runtime and any(configured[role] != models[role] for role in configured):
        raise Run4ADriverError("Run 5 runtime model identity mismatch")
    if prereg["pair_order"]["seed"] != 20260824:
        raise Run4ADriverError("Run 5 pair-order seed drift")
    return {"preregistration": prereg, "preregistration_path": prereg_path, "policy": policy, "manifests": manifests, "tasks": _task_map(repo_root, manifests), "effective_timeouts": effective}


def _selection(candidate_order: list[str], summaries: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    eligible = [task_id for task_id in candidate_order if summaries[task_id].get("eligible") is True]
    selected = eligible[:12]
    return {"candidate_order": candidate_order, "eligible_task_ids": eligible, "included_task_ids": selected, "reserve_task_ids": [task_id for task_id in candidate_order if task_id not in selected], "selected_count": len(selected), "family_complete": len(selected) == 12}


def _binding(context: Mapping[str, Any], family: str, task_id: str, arm: str, intervention: str, baseline: Mapping[str, Any], *, common: bool = False) -> dict[str, Any]:
    return {"schema": "zth_run5_action_binding_v1", "family": family, "task_id": task_id, "arm": arm, "intervention": intervention, "common_action": common, "preregistration_sha256": sha256_file(context["preregistration_path"]), "fixture_pack_sha256": context["manifests"][family]["pack_sha256"], "baseline_summary_sha256": canonical_sha256(baseline), "policy_freeze_sha256": context["preregistration"]["policy_freeze"]["canonical_sha256"], "models": context["preregistration"]["models"], "timeouts_seconds": context["preregistration"]["timeouts_seconds"]}


def _run_action(context: Mapping[str, Any], output_dir: Path, family: str, task_id: str, arm: str, intervention: str, baseline: Mapping[str, Any], *, worker: Callable[..., Any], local_teacher: Callable[..., Any], external_teacher: Callable[..., Any], common: bool = False) -> dict[str, Any]:
    arm_dir = output_dir / "tasks" / family / task_id / (Path("common_external") if common else Path("arms") / arm)
    binding = _binding(context, family, task_id, arm, intervention, baseline, common=common)
    terminal = _arm_terminal(arm_dir, binding)
    if terminal is not None:
        return terminal
    if (arm_dir / "arm_summary.json").exists() or (arm_dir / "arm_binding.json").exists():
        raise Run4ADriverError(f"incomplete Run 5 action artifacts in {arm_dir}")
    arm_dir.mkdir(parents=True, exist_ok=True)
    _json_write(arm_dir / "arm_binding.json", binding)
    summary = run_isolated_intervention_arm(context["tasks"][task_id], baseline, intervention=intervention, out_dir=arm_dir, worker=worker, local_teacher=local_teacher, external_teacher=external_teacher, deterministic_patch=None)
    _write_arm_artifact_index(arm_dir)
    return summary


def _valid(summary: Mapping[str, Any]) -> bool:
    return summary.get("capability_verdict_available") is True and summary.get("transport_valid") is True and summary.get("transport_classification") == "model_response"


def _write_scorecard(path: Path, *, family: str, task_id: str, common: Mapping[str, Any] | None = None, control: Mapping[str, Any] | None = None, treatment: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if common is not None:
        control = treatment = common
    assert control is not None and treatment is not None
    comparable = _valid(control) and _valid(treatment)
    pair_outcome = "both_solve" if control.get("deterministically_validated_rescue") and treatment.get("deterministically_validated_rescue") else "control_only" if control.get("deterministically_validated_rescue") else "treatment_only" if treatment.get("deterministically_validated_rescue") else "neither"
    value = {"schema": "zth_run5_policy_scorecard_v1", "family": family, "task_id": task_id, "common_action_reused": common is not None, "disposition": "comparable" if comparable else "infrastructure_excluded", "control": {"intervention": control.get("intervention"), "rescue": bool(control.get("deterministically_validated_rescue")), "elapsed_ms": control.get("realized_elapsed_ms")}, "treatment": {"intervention": treatment.get("intervention"), "rescue": bool(treatment.get("deterministically_validated_rescue")), "elapsed_ms": treatment.get("realized_elapsed_ms")}, "paired_outcome": pair_outcome, "infrastructure": [] if comparable else [{"policy_arm": "control", "intervention": control.get("intervention"), "artifact": control.get("infrastructure_artifact")}, {"policy_arm": "treatment", "intervention": treatment.get("intervention"), "artifact": treatment.get("infrastructure_artifact")}], "authority": "review_required_no_evidence_merge"}
    _json_write(path, value)
    return value


def _resource_history(output_dir: Path) -> dict[str, Any]:
    attempts: dict[str, int] = {}; valid: dict[str, int] = {}; infra: dict[str, int] = {}; elapsed: dict[str, float] = {}; paths = list(output_dir.rglob("trajectory.jsonl"))
    seen: set[tuple[str, str]] = set()
    for path in sorted(set(paths)):
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        done = {row.get("call_id"): row for row in rows if row.get("transition") in {"response_captured", "infrastructure_failed"}}
        for row in rows:
            if row.get("transition") != "call_started": continue
            role = row.get("role", "unknown"); key = (str(path), str(row.get("call_id")))
            if key in seen: continue
            seen.add(key); attempts[role] = attempts.get(role, 0) + 1
            completion = done.get(row.get("call_id"));
            if completion is None: continue
            ref = completion.get("artifact_ref"); artifact = _read_json(path.parent / ref) if ref else {}
            if completion.get("transition") == "infrastructure_failed": infra[role] = infra.get(role, 0) + 1
            else:
                meta = artifact.get("metadata", {}) if isinstance(artifact, dict) else {}
                if (meta.get("transport_valid", artifact.get("transport_valid")) is True and meta.get("transport_classification", artifact.get("transport_classification")) == "model_response"):
                    valid[role] = valid.get(role, 0) + 1
            telemetry = (artifact.get("metadata", {}) or {}).get("resource_telemetry") or artifact.get("resource_telemetry")
            if isinstance(telemetry, dict) and isinstance(telemetry.get("elapsed_ms"), (int, float)): elapsed[role] = elapsed.get(role, 0.0) + float(telemetry["elapsed_ms"])
    return {"schema": "zth_run5_execution_resource_history_v1", "attempts_by_role": attempts, "valid_responses_by_role": valid, "infrastructure_failures_by_role": infra, "realized_elapsed_ms_by_role": elapsed, "total_model_call_attempts": sum(attempts.values()), "total_worker_attempts": attempts.get("worker", 0), "total_teacher_attempts": attempts.get("local_teacher", 0) + attempts.get("external_teacher", 0), "accounting_scope": "all physical durable call attempts; common triage action counted once"}


def aggregate_results(context: Mapping[str, Any], output_dir: Path, execution: Mapping[str, Any]) -> dict[str, Any]:
    scorecards = [ _read_json(path) for path in sorted(output_dir.glob("tasks/*/*/scorecard.json")) ]
    family_results: dict[str, Any] = {}
    for family in ("triage", "scope"):
        rows = [row for row in scorecards if row["family"] == family]
        comparable = [row for row in rows if row["disposition"] == "comparable"]
        family_results[family] = {"selected_tasks": len(rows), "comparable_tasks": len(comparable), "infrastructure_excluded_tasks": len(rows)-len(comparable), "control_validated_solves": sum(row["control"]["rescue"] for row in comparable), "treatment_validated_solves": sum(row["treatment"]["rescue"] for row in comparable), "control_post_baseline_elapsed_ms": sum(float(row["control"]["elapsed_ms"] or 0) for row in comparable), "treatment_post_baseline_elapsed_ms": sum(float(row["treatment"]["elapsed_ms"] or 0) for row in comparable), "paired_outcomes": {name: sum(row["paired_outcome"] == name for row in comparable) for name in ("both_solve", "control_only", "treatment_only", "neither")}, "infrastructure": [row for row in rows if row["disposition"] != "comparable"]}
    portfolio_comparable = family_results["triage"]["comparable_tasks"] + family_results["scope"]["comparable_tasks"]
    control_solves = family_results["triage"]["control_validated_solves"] + family_results["scope"]["control_validated_solves"]
    treatment_solves = family_results["triage"]["treatment_validated_solves"] + family_results["scope"]["treatment_validated_solves"]
    control_elapsed = family_results["triage"]["control_post_baseline_elapsed_ms"] + family_results["scope"]["control_post_baseline_elapsed_ms"]
    treatment_elapsed = family_results["triage"]["treatment_post_baseline_elapsed_ms"] + family_results["scope"]["treatment_post_baseline_elapsed_ms"]
    history = _resource_history(output_dir)
    result = {"schema": "zth_run5_mixed_aggregate_v1", "status": "review_required", "family_results": family_results, "portfolio": {"comparable_policy_tasks": portfolio_comparable, "control_validated_solves": control_solves, "treatment_validated_solves": treatment_solves, "control_solve_rate": control_solves / portfolio_comparable if portfolio_comparable else None, "treatment_solve_rate": treatment_solves / portfolio_comparable if portfolio_comparable else None, "control_post_baseline_policy_elapsed_ms": control_elapsed if portfolio_comparable else None, "treatment_post_baseline_policy_elapsed_ms": treatment_elapsed if portfolio_comparable else None, "quality_preserved": treatment_solves >= control_solves if portfolio_comparable else None, "resource_reduced": treatment_elapsed < control_elapsed if portfolio_comparable else None, "economic_routing_success": treatment_solves >= control_solves and treatment_elapsed < control_elapsed if portfolio_comparable else None}, "physical_execution_resource_history": history, "physical_expected_cost_ms": 1231797.198, "control_expected_policy_cost_ms": 815533.896, "treatment_expected_policy_cost_ms": 665733.240, "authority": "review_required_no_evidence_merge"}
    _json_write(output_dir / "aggregate.json", result)
    return result


def run_experiment(context: Mapping[str, Any], output_dir: Path, *, worker: Callable[..., Any], local_teacher: Callable[..., Any], external_teacher: Callable[..., Any]) -> dict[str, Any]:
    manifest_path = output_dir / "execution_manifest.json"
    if manifest_path.exists():
        execution = _read_json(manifest_path)
        if execution.get("schema") != "zth_run5_mixed_execution_manifest_v1" or execution.get("preregistration_sha256") != sha256_file(context["preregistration_path"]):
            raise Run4ADriverError("Run 5 execution binding mismatch")
        if _terminal_execution(execution): return execution
        if execution.get("active_call"): raise Run4ADriverError("ambiguous active Run 5 call; refusing resume")
    elif output_dir.exists() and any(output_dir.iterdir()):
        raise Run4ADriverError("existing nonempty output directory lacks a bound Run 5 execution manifest")
    else:
        output_dir.mkdir(parents=True, exist_ok=True)
        execution = {"schema": "zth_run5_mixed_execution_manifest_v1", "status": "experiment_running", "started_at": utc_now(), "git_head": git_head(Path.cwd()), "preregistration_sha256": sha256_file(context["preregistration_path"]), "driver_sha256": context["preregistration"]["driver"]["sha256"], "policy_freeze_sha256": context["preregistration"]["policy_freeze"]["canonical_sha256"], "fixture_pack_sha256": {family: context["manifests"][family]["pack_sha256"] for family in context["manifests"]}, "models": context["preregistration"]["models"], "timeouts_seconds": context["preregistration"]["timeouts_seconds"], "pair_order_seed": context["preregistration"]["pair_order"]["seed"], "candidate_states": {}, "model_calls_started": True}
        _json_write(manifest_path, execution)
    for family in ("triage", "scope"):
        summaries = {}
        candidate_order = context["manifests"][family]["candidate_order"]
        for task_id in candidate_order:
            candidate_dir = output_dir / "candidates" / family / task_id
            execution["active_call"] = {"kind": "baseline", "family": family, "task_id": task_id, "role": "worker"}; _json_write(manifest_path, execution)
            summaries[task_id] = run_baseline(context["tasks"][task_id], candidate_dir, worker=worker)
            execution.pop("active_call", None); execution["candidate_states"][f"{family}:{task_id}"] = "baseline_terminal"; _json_write(manifest_path, execution)
        selection = _selection(candidate_order, summaries)
        _json_write(output_dir / "selections" / f"{family}.json", selection)
        execution.setdefault("selections", {})[family] = selection; _json_write(manifest_path, execution)
    if not all(execution["selections"][family]["family_complete"] for family in ("triage", "scope")):
        execution.update({"status": "experiment_incomplete", "completed_at": utc_now()}); _json_write(manifest_path, execution); return execution
    for family in ("triage", "scope"):
        for task_id in execution["selections"][family]["included_task_ids"]:
            baseline = _baseline_payload(output_dir / "candidates" / family / task_id, _read_json(output_dir / "candidates" / family / task_id / "baseline_summary.json"))
            if family == "triage":
                execution["active_call"] = {"kind": "common_action", "family": family, "task_id": task_id, "intervention": "external_teacher"}; _json_write(manifest_path, execution)
                common = _run_action(context, output_dir, family, task_id, "common", "external_teacher", baseline, worker=worker, local_teacher=local_teacher, external_teacher=external_teacher, common=True)
                execution.pop("active_call", None); _json_write(manifest_path, execution)
                _write_scorecard(output_dir / "tasks" / family / task_id / "scorecard.json", family=family, task_id=task_id, common=common)
            else:
                order = context["manifests"][family]["pair_order"]["orders"][task_id]
                summaries = {}
                for arm in order:
                    intervention = FAMILY_MATRIX["scope-authority-boundary"]["external_everywhere" if arm == "control" else "evidence_qualified_economic"]
                    execution["active_call"] = {"kind": "paired_arm", "family": family, "task_id": task_id, "arm": arm, "intervention": intervention}; _json_write(manifest_path, execution)
                    summaries[arm] = _run_action(context, output_dir, family, task_id, arm, intervention, baseline, worker=worker, local_teacher=local_teacher, external_teacher=external_teacher)
                    execution.pop("active_call", None); _json_write(manifest_path, execution)
                _write_scorecard(output_dir / "tasks" / family / task_id / "scorecard.json", family=family, task_id=task_id, control=summaries["control"], treatment=summaries["treatment"])
            execution["candidate_states"][f"{family}:{task_id}"] = "terminal"; _json_write(manifest_path, execution)
    execution.update({"status": "experiment_completed", "completed_at": utc_now(), "aggregate_path": "aggregate.json"}); _json_write(manifest_path, execution); aggregate_results(context, output_dir, execution); return execution


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    repo_root = Path.cwd()
    context = _load_context(args.preregistration, repo_root, require_runtime=args.execute)
    context["git_head"] = git_head(repo_root)
    if not args.execute:
        print(json.dumps({"status": "dry_run_valid", "model_calls": 0, "control": "external_everywhere", "treatment": "evidence_qualified_economic", "pair_order_seed": context["preregistration"]["pair_order"]["seed"]}, sort_keys=True))
        return 0
    context["preregistration_path"] = args.preregistration
    result = run_experiment(context, args.output_dir, worker=_default_worker, local_teacher=_default_local_teacher, external_teacher=_default_external_teacher)
    print(json.dumps(result, sort_keys=True))
    return 0


def _default_worker(prompt: str) -> Any:
    from local_harness.run4a_intervention_harness import _default_worker as call
    return call(prompt)


def _default_local_teacher(prompt: str) -> Any:
    from local_harness.run4a_intervention_harness import _default_local_teacher as call
    return call(prompt)


def _default_external_teacher(prompt: str) -> Any:
    from local_harness.run4a_intervention_harness import _default_external_teacher as call
    return call(prompt)


if __name__ == "__main__":
    raise SystemExit(main())
