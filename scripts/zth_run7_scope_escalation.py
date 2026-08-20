#!/usr/bin/env python3
"""Execute the frozen, scope-only Run 7 validation-gated escalation protocol."""

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
)
from local_harness.run6_sequential_fixture_pack import verify_manifest as verify_run6_manifest  # noqa: E402
from local_harness.run7_escalation_policy import verify_policy  # noqa: E402
from local_harness.run7_scope_fixture_pack import verify_manifest  # noqa: E402
from local_harness.supervised_capability_loop import load_task_fixture  # noqa: E402
from scripts.zth_run4_economic_routing import _arm_terminal, _baseline_payload  # noqa: E402
from scripts.zth_run4a_intervention_calibration import (  # noqa: E402
    Run4ADriverError,
    _append_transition,
    _read_json,
    _write_arm_artifact_index,
    run_baseline,
)
from scripts.zth_run6_sequential_economic_routing import (  # noqa: E402
    _assert_action_reusable,
    _resource_history,
    _run_single_action,
    _treatment_summary,
    _valid,
    _write_scorecard,
)


TARGET_COUNT = 20
FAMILY = "scope-authority-boundary"
TERMINAL_STATUSES = {"experiment_completed", "experiment_incomplete"}


def _run_external_escalation(
    context: Mapping[str, Any],
    output_dir: Path,
    task_id: str,
    baseline: Mapping[str, Any],
    local_summary: Mapping[str, Any],
    *,
    worker: Callable[..., Any],
    external_teacher: Callable[..., Any],
) -> dict[str, Any]:
    """Run the repaired Run 7 escalation action.

    Escalation uses the same diagnostic/review-only teacher contract as the
    proven direct intervention path.  The local validation failure is carried
    as an additional failed transition; it is evidence for diagnosis, never
    authoritative task guidance.
    """

    action_dir = output_dir / "tasks" / "scope" / task_id / "escalation"
    prereg = context["preregistration"]
    baseline_digest = hashlib.sha256(
        json.dumps(baseline, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    binding = {
        "schema": "zth_run7_escalation_action_binding_v1",
        "family": "scope-authority-boundary",
        "task_id": task_id,
        "stage": "escalation",
        "intervention": "external_teacher",
        "preregistration_sha256": sha256_file(context["preregistration_path"]),
        "fixture_pack_sha256": context["manifests"]["scope"]["pack_sha256"],
        "baseline_summary_sha256": baseline_digest,
        "policy_freeze_sha256": prereg["policy_freeze"]["canonical_sha256"],
        "models": prereg["models"],
        "timeouts_seconds": prereg["timeouts_seconds"],
    }
    terminal = _arm_terminal(action_dir, binding)
    if terminal is not None:
        return terminal
    if action_dir.exists():
        _assert_action_reusable(action_dir)
        if any(action_dir.iterdir()):
            raise Run4ADriverError(f"incomplete Run 7 escalation artifacts in {action_dir}")
    action_dir.mkdir(parents=True, exist_ok=True)
    _json_write(action_dir / "arm_binding.json", binding)

    baseline_copy = dict(baseline)
    baseline_copy["raw"] = dict(baseline.get("raw", {}))
    _json_write(action_dir / "baseline_reference.json", baseline_copy)

    trajectory = action_dir / "trajectory.jsonl"
    task = context["tasks"][task_id]
    failed_transitions = [
        {"validation": baseline["validation"], "intervention_id": "none:1"},
        {
            "validation": {
                "validation_status": local_summary.get("validation_status"),
                "failed_checks": local_summary.get("failed_checks", []),
                "diagnostics": local_summary.get("failed_checks", []),
            },
            "intervention_id": "local_first",
        },
    ]
    escalation_prompt = _teacher_prompt(
        task,
        role="external_teacher",
        failed_transitions=failed_transitions,
        patch_records=[],
    )
    teacher_payload, infrastructure = _call_teacher(
        action_dir,
        trajectory,
        task,
        escalation_prompt,
        role="external_teacher",
        local_teacher=lambda _: (_ for _ in ()).throw(Run4ADriverError("local teacher forbidden in escalation")),
        external_teacher=external_teacher,
    )
    worker_result = None
    if teacher_payload is not None:
        retry_prompt = json.dumps(
            {
                "task_prompt": task["prompt"],
                "output_contract": task["output_contract"],
                "reference_facts": task["validator"].get("reference_facts", {}),
                "baseline_diagnostics": baseline["validation"].get("diagnostics", []),
                "local_first_validation_failure": local_summary.get("failed_checks", []),
                "intervention": teacher_payload.get("parsed", {}),
                "authority": REQUIRED_AUTHORITY,
            },
            indent=2,
            sort_keys=True,
        )
        worker_result, infrastructure = _call_worker(
            action_dir,
            trajectory,
            task,
            retry_prompt,
            worker=worker,
            attempt_id="worker-retry",
        )
    if infrastructure is not None:
        summary = {
            "schema": "zth_run7_stage_summary_v1",
            "task_id": task_id,
            "task_family": task["task_family"],
            "stage": "escalation",
            "intervention": "external_teacher",
            "capability_verdict_available": False,
            "deterministically_validated_rescue": False,
            "transport_valid": False,
            "disposition": "infrastructure_error",
            "infrastructure_artifact": infrastructure.get("artifact_ref"),
            "trigger": "deterministic validation failure",
            "authority": "review_required_no_evidence_merge",
        }
    else:
        validation = worker_result["validation"]
        summary = {
            "schema": "zth_run7_stage_summary_v1",
            "task_id": task_id,
            "task_family": task["task_family"],
            "stage": "escalation",
            "intervention": "external_teacher",
            "capability_verdict_available": True,
            "transport_valid": True,
            "transport_classification": "model_response",
            "deterministically_validated_rescue": validation["validation_status"] == "passed",
            "validation_status": validation["validation_status"],
            "failed_checks": [c["check_id"] for c in validation.get("checks", []) if c.get("status") == "failed"],
            "realized_elapsed_ms": worker_result["telemetry"]["elapsed_ms"] + teacher_payload["resource_telemetry"]["elapsed_ms"],
            "resource_telemetry": {"worker": worker_result["telemetry"], "external_teacher": teacher_payload["resource_telemetry"]},
            "disposition": "ready_for_review" if validation["validation_status"] == "passed" else "unresolved",
            "trigger": "deterministic validation failure",
            "authority": "review_required_no_evidence_merge",
        }
    _append_transition(trajectory, summary["disposition"], task_id=task_id, stage="escalation", capability_verdict_available=summary["capability_verdict_available"])
    _json_write(action_dir / "arm_summary.json", summary)
    _write_arm_artifact_index(action_dir)
    return summary


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_head(repo_root: Path) -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True, capture_output=True, check=True).stdout.strip()


def _policy_digest(policy: Mapping[str, Any]) -> str:
    basis = dict(policy)
    basis["canonical_digest"] = None
    return hashlib.sha256(json.dumps(basis, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _load_context(prereg_path: Path, repo_root: Path, *, require_runtime: bool) -> dict[str, Any]:
    prereg = _read_json(prereg_path)
    if prereg.get("model_calls_made") is not False:
        raise Run4ADriverError("Run 7 preregistration is not model-free")
    policy_binding = prereg["policy_freeze"]
    policy_path = repo_root / policy_binding["path"]
    policy = _read_json(policy_path)
    if sha256_file(policy_path) != policy_binding["file_sha256"] or _policy_digest(policy) != policy_binding["canonical_sha256"]:
        raise Run4ADriverError("Run 7 policy binding mismatch")
    verify_policy()
    source = prereg["policy_source"]
    if sha256_file(repo_root / source["path"]) != source["sha256"]:
        raise Run4ADriverError("Run 7 policy source binding mismatch")
    criteria_path = repo_root / prereg["difficulty_criteria"]["path"]
    if sha256_file(criteria_path) != prereg["difficulty_criteria"]["sha256"]:
        raise Run4ADriverError("Run 7 difficulty criteria binding mismatch")
    provenance_path = repo_root / prereg["fixture_provenance"]["path"]
    if sha256_file(provenance_path) != prereg["fixture_provenance"]["sha256"]:
        raise Run4ADriverError("Run 7 provenance binding mismatch")
    pack_binding = prereg["fixture_pack"]
    pack_dir = repo_root / pack_binding["path"]
    manifest = verify_manifest(pack_dir, repo_root)
    if sha256_file(pack_dir / "manifest.json") != pack_binding["manifest_file_sha256"] or manifest["manifest_sha256"] != pack_binding["manifest_sha256"] or manifest["pack_sha256"] != pack_binding["pack_sha256"]:
        raise Run4ADriverError("Run 7 fixture pack binding mismatch")
    if sha256_file(pack_dir / "novelty_audit.json") != pack_binding["novelty_audit_file_sha256"]:
        raise Run4ADriverError("Run 7 novelty audit binding mismatch")
    resource_binding = prereg["resource_manifest"]
    resource_path = repo_root / resource_binding["path"]
    if sha256_file(resource_path) != resource_binding["sha256"]:
        raise Run4ADriverError("Run 7 resource manifest mismatch")
    resource = _read_json(resource_path)
    if resource.get("manifest_sha256") != resource_binding["canonical_sha256"]:
        raise Run4ADriverError("Run 7 resource canonical digest mismatch")
    for item in prereg["validators"]:
        if sha256_file(repo_root / item["path"]) != item["sha256"]:
            raise Run4ADriverError(f"Run 7 validator binding mismatch: {item['path']}")
    if sha256_file(repo_root / prereg["driver"]["path"]) != prereg["driver"]["sha256"]:
        raise Run4ADriverError("Run 7 driver binding mismatch")
    timeouts = prereg["timeouts_seconds"]
    effective = {"worker": int(os.environ.get("ZTH_CAPABILITY_WORKER_TIMEOUT", timeouts["worker"])), "local_teacher": int(os.environ.get("ZTH_CAPABILITY_TEACHER_TIMEOUT", timeouts["local_teacher"])), "external_teacher": int(timeouts["external_teacher"])}
    if effective != timeouts:
        raise Run4ADriverError("Run 7 timeout binding mismatch")
    configured = {"worker": os.environ.get("ZTH_CAPABILITY_WORKER_MODEL"), "local_teacher": os.environ.get("ZTH_CAPABILITY_TEACHER_MODEL"), "external_teacher": os.environ.get("ZTH_EXTERNAL_TEACHER_IDENTITY")}
    if require_runtime and any(configured[k] != prereg["models"][k] for k in configured):
        raise Run4ADriverError("Run 7 runtime identity mismatch")
    if prereg["pair_order"]["seed"] != 20260826 or manifest["candidate_count"] != 24 or manifest["target_included_count"] != TARGET_COUNT:
        raise Run4ADriverError("Run 7 selection binding mismatch")
    tasks = {row["task_id"]: load_task_fixture(repo_root / row["path"]) for row in manifest["fixtures"]}
    return {"preregistration": prereg, "preregistration_path": prereg_path, "policy": policy, "manifests": {"scope": manifest}, "tasks": tasks, "effective_timeouts": effective}


def _selection(order: list[str], summaries: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    eligible = [task_id for task_id in order if summaries[task_id].get("eligible") is True]
    selected = eligible[:TARGET_COUNT]
    return {"schema": "zth_run7_scope_selection_v1", "family": FAMILY, "candidate_order": order, "eligible_task_ids": eligible, "included_task_ids": selected, "reserve_task_ids": [task_id for task_id in order if task_id not in selected], "selected_count": len(selected), "family_complete": len(selected) == TARGET_COUNT, "selection_uses_intervention_outputs": False}


def _validate_execution_bindings(context: Mapping[str, Any], execution: Mapping[str, Any]) -> None:
    prereg = context["preregistration"]
    expected = {"preregistration_sha256": sha256_file(context["preregistration_path"]), "driver_sha256": prereg["driver"]["sha256"], "policy_freeze_sha256": prereg["policy_freeze"]["canonical_sha256"], "fixture_pack_sha256": prereg["fixture_pack"]["pack_sha256"], "models": prereg["models"], "timeouts_seconds": prereg["timeouts_seconds"], "pair_order_seed": prereg["pair_order"]["seed"]}
    for field, value in expected.items():
        if execution.get(field) != value:
            raise Run4ADriverError(f"Run 7 execution binding drift: {field}")
    if context.get("git_head") is not None and execution.get("git_head") != context["git_head"]:
        raise Run4ADriverError("Run 7 execution binding drift: git_head")


def _aggregate(output_dir: Path) -> dict[str, Any]:
    rows = [_read_json(path) for path in sorted((output_dir / "tasks" / FAMILY).glob("*/scorecard.json"))]
    comparable = [row for row in rows if row["disposition"] == "comparable"]
    details = [row.get("treatment_detail") for row in comparable if row.get("treatment_detail")]
    control_solves = sum(row["control"]["rescue"] for row in comparable)
    treatment_solves = sum(row["treatment"]["rescue"] for row in comparable)
    local_passes = sum(bool(d and d["local_first"].get("deterministically_validated_rescue")) for d in details)
    escalations = sum(bool(d and d.get("escalated")) for d in details)
    escalation_rescues = sum(bool(d and d.get("escalated") and d["final"].get("deterministically_validated_rescue")) for d in details)
    history = _resource_history(output_dir)
    n = len(comparable)
    control_elapsed = sum(float(row["control"].get("elapsed_ms") or 0) for row in comparable)
    treatment_elapsed = sum(float(row["treatment"].get("elapsed_ms") or 0) for row in comparable)
    result = {"schema": "zth_run7_scope_aggregate_v1", "status": "review_required", "family": FAMILY, "selected_tasks": len(rows), "comparable_tasks": n, "infrastructure_excluded_tasks": len(rows) - n, "control_validated_solves": control_solves, "treatment_final_validated_solves": treatment_solves, "control_solve_rate": control_solves / n if n else None, "treatment_final_solve_rate": treatment_solves / n if n else None, "quality_preserved": treatment_solves >= control_solves if n else None, "control_post_baseline_elapsed_ms": control_elapsed if n else None, "treatment_post_baseline_elapsed_ms": treatment_elapsed if n else None, "resource_reduced": treatment_elapsed < control_elapsed if n else None, "economic_routing_success": (treatment_solves >= control_solves and treatment_elapsed < control_elapsed) if n else None, "local_first_passes": local_passes, "local_first_failures": sum(bool(d and not d["local_first"].get("deterministically_validated_rescue")) for d in details), "escalations": escalations, "escalation_rescues": escalation_rescues, "escalation_failures": escalations - escalation_rescues, "escalation_rate": escalations / len(details) if details else None, "paired_outcomes": {name: sum(row["paired_outcome"] == name for row in comparable) for name in ("both_solve", "control_only", "treatment_only", "neither")}, "physical_execution_resource_history": history, "authority": "review_required_no_evidence_merge"}
    _json_write(output_dir / "aggregate.json", result)
    return result


def run_experiment(context: Mapping[str, Any], output_dir: Path, *, worker: Callable[..., Any], local_teacher: Callable[..., Any], external_teacher: Callable[..., Any], checkpoint_hook: Callable[[str, Mapping[str, Any]], None] | None = None) -> dict[str, Any]:
    manifest_path = output_dir / "execution_manifest.json"
    if manifest_path.exists():
        execution = _read_json(manifest_path)
        _validate_execution_bindings(context, execution)
        if execution.get("status") in TERMINAL_STATUSES and (execution.get("status") == "experiment_completed" or execution.get("completed_at")):
            return execution
        if execution.get("active_call"):
            raise Run4ADriverError("ambiguous active Run 7 call; refusing resume")
    elif output_dir.exists() and any(output_dir.iterdir()):
        raise Run4ADriverError("existing nonempty output directory lacks a bound Run 7 execution manifest")
    else:
        output_dir.mkdir(parents=True, exist_ok=True)
        execution = {"schema": "zth_run7_scope_execution_manifest_v1", "status": "experiment_running", "started_at": utc_now(), "git_head": context.get("git_head") or git_head(Path.cwd()), "preregistration_sha256": sha256_file(context["preregistration_path"]), "driver_sha256": context["preregistration"]["driver"]["sha256"], "policy_freeze_sha256": context["preregistration"]["policy_freeze"]["canonical_sha256"], "fixture_pack_sha256": context["preregistration"]["fixture_pack"]["pack_sha256"], "models": context["preregistration"]["models"], "timeouts_seconds": context["preregistration"]["timeouts_seconds"], "pair_order_seed": context["preregistration"]["pair_order"]["seed"], "candidate_states": {}, "model_calls_started": False}
        _json_write(manifest_path, execution)
    order = context["manifests"]["scope"]["candidate_order"]
    summaries: dict[str, Any] = {}
    for task_id in order:
        candidate_dir = output_dir / "candidates" / task_id
        execution["active_call"] = {"kind": "baseline", "task_id": task_id, "role": "worker"}; _json_write(manifest_path, execution)
        summaries[task_id] = run_baseline(context["tasks"][task_id], candidate_dir, worker=worker)
        execution.pop("active_call", None); execution["candidate_states"][task_id] = "baseline_terminal"; _json_write(manifest_path, execution)
        if checkpoint_hook: checkpoint_hook(f"baseline_terminal:{task_id}", execution)
    selection = _selection(order, summaries)
    (output_dir / "selections").mkdir(parents=True, exist_ok=True); _json_write(output_dir / "selections" / "scope.json", selection)
    execution["selection"] = selection; _json_write(manifest_path, execution)
    if not selection["family_complete"]:
        execution.update({"status": "experiment_incomplete", "completed_at": utc_now()}); _json_write(manifest_path, execution); return execution
    for task_id in selection["included_task_ids"]:
        task_dir = output_dir / "tasks" / FAMILY / task_id
        summary_path = output_dir / "candidates" / task_id / "baseline_summary.json"
        baseline_summary = _read_json(summary_path)
        baseline = _baseline_payload(output_dir / "candidates" / task_id, baseline_summary)
        stages: dict[str, Any] = {}
        for arm in context["manifests"]["scope"]["pair_order"]["orders"][task_id]:
            if arm == "control":
                execution["active_call"] = {"kind": "control_arm", "task_id": task_id, "intervention": "external_teacher"}; _json_write(manifest_path, execution)
                stages["control"] = _run_single_action(context, output_dir, "scope", task_id, "control", "external_teacher", baseline, worker=worker, local_teacher=local_teacher, external_teacher=external_teacher)
                execution.pop("active_call", None); _json_write(manifest_path, execution)
            else:
                execution["active_call"] = {"kind": "local_first", "task_id": task_id, "intervention": "local_teacher"}; _json_write(manifest_path, execution)
                local_summary = _run_single_action(context, output_dir, "scope", task_id, "local_first", "local_teacher", baseline, worker=worker, local_teacher=local_teacher, external_teacher=external_teacher)
                execution.pop("active_call", None); _json_write(manifest_path, execution)
                escalation = None
                if _valid(local_summary) and local_summary.get("validation_status") == "failed":
                    execution["active_call"] = {"kind": "external_escalation", "task_id": task_id, "intervention": "external_teacher"}; _json_write(manifest_path, execution)
                    escalation = _run_external_escalation(context, output_dir, task_id, baseline, local_summary, worker=worker, external_teacher=external_teacher)
                    execution.pop("active_call", None); _json_write(manifest_path, execution)
                treatment = _treatment_summary(task_id, local_summary, escalation)
                _json_write(task_dir / "treatment_summary.json", treatment)
                stages["treatment"] = treatment["final"]; stages["treatment_detail"] = treatment
            if checkpoint_hook: checkpoint_hook(f"stage_terminal:{task_id}:{arm}", execution)
        _write_scorecard(task_dir / "scorecard.json", family=FAMILY, task_id=task_id, control=stages["control"], treatment=stages["treatment"], treatment_detail=stages["treatment_detail"])
        execution["candidate_states"][task_id] = "terminal"; _json_write(manifest_path, execution)
    execution.update({"status": "experiment_completed", "completed_at": utc_now(), "aggregate_path": "aggregate.json"}); _json_write(manifest_path, execution); _aggregate(output_dir); return execution


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
        print(json.dumps({"status": "dry_run_valid", "model_calls": 0, "control": "external_direct", "treatment": "validation_gated_economic_escalation", "pair_order_seed": context["preregistration"]["pair_order"]["seed"]}, sort_keys=True))
        return 0
    context["preregistration_path"] = args.preregistration
    result = run_experiment(context, args.output_dir, worker=_default_worker, local_teacher=_default_local_teacher, external_teacher=_default_external_teacher)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
