#!/usr/bin/env python3
"""Durable, preregistration-bound Run 4A calibration driver.

This driver is the execution wrapper for the already frozen Run 4A protocol.
It is intentionally not a router and never updates capability evidence.  The
``--dry-run`` mode performs binding checks only; model calls require an
explicit non-dry invocation after operator review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from local_harness.icm_spec import WorkerResponse, resolve_worker_spec
from local_harness.resource_telemetry import load_approved_resource_weights
from local_harness.run4a_fixture_pack import (
    TARGET_BLOCKS,
    select_included_candidates,
    verify_manifest,
)
from local_harness.run4a_intervention_harness import (
    EXTERNAL_TIMEOUT_SECONDS,
    _default_external_teacher,
    _default_local_teacher,
    _default_worker,
    _response_payload,
    _utc_now,
    _validator_result,
    _write_infrastructure_failure,
    run_isolated_intervention_arm,
)
from local_harness.supervised_capability_loop import load_task_fixture


ARM_NAMES = ("deterministic_patch_retry", "local_teacher", "external_teacher")
TERMINAL_BASELINE_DISPOSITIONS = {"baseline_pass", "baseline_failed_eligible", "infrastructure_error"}
TERMINAL_EXPERIMENT_STATES = {"experiment_completed", "experiment_incomplete"}


class Run4ADriverError(RuntimeError):
    """A frozen binding or durable state cannot be trusted."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: Any) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(data).hexdigest()


def _json_write(path: Path, payload: Any) -> str:
    data = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")
    return hashlib.sha256(data.encode()).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Run4ADriverError(f"invalid JSON artifact: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise Run4ADriverError(f"JSON artifact must be an object: {path}")
    return value


def _append_transition(path: Path, transition: str, **fields: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"transition": transition, "timestamp": _utc_now(), **fields}, sort_keys=True) + "\n")


def _transitions(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _assert_no_ambiguous_started(trajectory: Path) -> None:
    rows = _transitions(trajectory)
    completed = {row.get("call_id") for row in rows if row.get("transition") in {"response_captured", "infrastructure_failed"}}
    ambiguous = [row for row in rows if row.get("transition") == "call_started" and row.get("call_id") not in completed]
    if ambiguous:
        raise Run4ADriverError(f"ambiguous started call in {trajectory}; refusing to rerun")


def _expected_runtime_identities(preregistration: Mapping[str, Any]) -> dict[str, str]:
    models = preregistration["models"]
    return {
        "worker": str(models["worker"]),
        "local_teacher": str(models["local_teacher"]),
        "external_teacher": str(models["external_teacher"]),
    }


def validate_runtime_identities(preregistration: Mapping[str, Any], *, require: bool) -> dict[str, str]:
    expected = _expected_runtime_identities(preregistration)
    configured = {
        "worker": os.environ.get("ZTH_CAPABILITY_WORKER_MODEL"),
        "local_teacher": os.environ.get("ZTH_CAPABILITY_TEACHER_MODEL"),
        "external_teacher": os.environ.get("ZTH_EXTERNAL_TEACHER_IDENTITY", expected["external_teacher"]),
    }
    if require:
        missing = [role for role in ("worker", "local_teacher") if not configured[role]]
        if missing:
            raise Run4ADriverError(f"runtime model identity is not configured for: {', '.join(missing)}")
        for role, expected_value in expected.items():
            if configured[role] != expected_value:
                raise Run4ADriverError(f"{role} identity mismatch: expected {expected_value!r}, got {configured[role]!r}")
    return {role: configured[role] or expected[role] for role in expected}


def validate_preregistration(prereg_path: Path, repo_root: Path, *, require_runtime_identities: bool = False) -> dict[str, Any]:
    prereg = _read_json(prereg_path)
    if prereg.get("model_calls_made") is not False:
        raise Run4ADriverError("Run 4A preregistration is not model-call-free")
    fixture_pack = prereg["fixture_pack"]
    pack_dir = repo_root / fixture_pack["path"]
    manifest = verify_manifest(pack_dir, repo_root)
    for key in ("manifest_sha256", "pack_sha256"):
        if fixture_pack[key] != manifest[key]:
            raise Run4ADriverError(f"fixture {key} binding mismatch")
    novelty_path = repo_root / fixture_pack["novelty_audit_path"]
    if sha256_file(novelty_path) != fixture_pack["novelty_audit_sha256"]:
        raise Run4ADriverError("novelty audit hash mismatch")
    if fixture_pack["task_ids"] != [row["task_id"] for row in manifest["fixtures"]]:
        raise Run4ADriverError("preregistered task list drift")
    if fixture_pack["candidate_order_by_block"] != manifest["candidate_order_by_block"]:
        raise Run4ADriverError("candidate order drift")
    if fixture_pack["included_candidates_by_block"] != manifest["included_candidates_by_block"] or fixture_pack["reserve_candidates_by_block"] != manifest["reserve_candidates_by_block"]:
        raise Run4ADriverError("included/reserve freeze drift")
    if fixture_pack.get("target_included_count_by_block") != manifest.get("target_included_count_by_block"):
        raise Run4ADriverError("target included counts drift")
    if fixture_pack.get("selection_rule") != manifest.get("selection_rule") or fixture_pack.get("reserve_rule") != manifest.get("reserve_rule"):
        raise Run4ADriverError("baseline selection semantics drift")
    frozen = prereg["frozen_inputs"]
    for path_key, hash_key in (
        ("routing_policy_path", "routing_policy_sha256"),
        ("capability_bundle_path", "capability_bundle_sha256"),
        ("deterministic_patch_path", "deterministic_patch_sha256"),
    ):
        path = repo_root / frozen[path_key]
        if sha256_file(path) != frozen[hash_key]:
            raise Run4ADriverError(f"frozen input hash mismatch: {path_key}")
    resource_path = repo_root / frozen["resource_weight_manifest_path"]
    resource = load_approved_resource_weights(resource_path)
    if resource.get("manifest_sha256") != frozen["resource_weight_manifest_sha256"]:
        raise Run4ADriverError("resource manifest digest mismatch")
    if resource.get("weights") != {**resource["weights"], **prereg["frozen_inputs"]["resource_priors_ms"]}:
        raise Run4ADriverError("resource priors drift")
    patch = _read_json(repo_root / frozen["deterministic_patch_path"])
    if patch.get("candidate_patch_id", patch.get("patch_id")) != frozen["deterministic_patch_id"]:
        raise Run4ADriverError("deterministic patch ID drift")
    harness = prereg["harness"]
    if sha256_file(repo_root / harness["path"]) != harness["sha256"]:
        raise Run4ADriverError("isolated harness hash mismatch")
    for validator in prereg["validators"]:
        if sha256_file(repo_root / validator["path"]) != validator["sha256"]:
            raise Run4ADriverError(f"validator hash mismatch: {validator['path']}")
    for key in ("seed", "permutations", "orders"):
        if prereg["arm_order"].get(key) != manifest["arm_order"].get(key):
            raise Run4ADriverError(f"arm order drift: {key}")
    timeout_values = prereg["timeouts_seconds"]
    effective_timeouts = {
        "worker": int(os.environ.get("ZTH_CAPABILITY_WORKER_TIMEOUT", timeout_values["worker"])),
        "local_teacher": int(os.environ.get("ZTH_CAPABILITY_TEACHER_TIMEOUT", timeout_values["local_teacher"])),
        "external_teacher": EXTERNAL_TIMEOUT_SECONDS,
    }
    if effective_timeouts != timeout_values:
        raise Run4ADriverError("runtime timeout binding mismatch")
    identities = validate_runtime_identities(prereg, require=require_runtime_identities)
    driver_binding = prereg.get("driver")
    if not driver_binding:
        raise Run4ADriverError("preregistration does not bind the execution driver")
    driver_path = repo_root / driver_binding["path"]
    if sha256_file(driver_path) != driver_binding["sha256"]:
        raise Run4ADriverError("execution driver hash mismatch")
    return {"preregistration": prereg, "manifest": manifest, "pack_dir": pack_dir, "identities": identities, "effective_timeouts": effective_timeouts}


def _baseline_summary_path(candidate_dir: Path) -> Path:
    return candidate_dir / "baseline_summary.json"


def run_baseline(task: Mapping[str, Any], candidate_dir: Path, *, worker: Callable[[str], WorkerResponse]) -> dict[str, Any]:
    """Make exactly one durable canonical baseline attempt."""
    candidate_dir.mkdir(parents=True, exist_ok=True)
    summary_path = _baseline_summary_path(candidate_dir)
    if summary_path.exists():
        summary = _read_json(summary_path)
        if summary.get("disposition") in TERMINAL_BASELINE_DISPOSITIONS:
            _assert_no_ambiguous_started(candidate_dir / "trajectory.jsonl")
            return summary
    state_path = candidate_dir / "state.json"
    state = _read_json(state_path) if state_path.exists() else {"state": "baseline_not_started"}
    if state.get("state") == "baseline_started":
        raise Run4ADriverError(f"baseline interrupted in {candidate_dir}; refusing duplicate")
    if state.get("state") == "baseline_terminal" and not summary_path.exists():
        raise Run4ADriverError(f"baseline terminal state lacks summary: {candidate_dir}")
    trajectory = candidate_dir / "trajectory.jsonl"
    _assert_no_ambiguous_started(trajectory)
    prompt = str(task["prompt"])
    prompt_path = candidate_dir / "baseline.prompt.txt"
    prompt_path.write_text(prompt, encoding="utf-8")
    _json_write(state_path, {"state": "baseline_started", "task_id": task["task_id"], "attempt": 1})
    started_at = _utc_now()
    started = time.monotonic()
    call_id = "worker:baseline"
    _append_transition(trajectory, "call_started", call_id=call_id, role="worker", prompt_ref=prompt_path.name, prompt_sha256=sha256_file(prompt_path), started_at=started_at)
    try:
        response = worker(prompt)
        raw = _response_payload(response, role="worker", started=started, captured=time.monotonic(), timeout_seconds=int(os.environ.get("ZTH_CAPABILITY_WORKER_TIMEOUT", "900")))
    except Exception as exc:
        artifact = _write_infrastructure_failure(candidate_dir, trajectory, call_id=call_id, role="worker", started_at=started_at, started=started, exc=exc, timeout_seconds=int(os.environ.get("ZTH_CAPABILITY_WORKER_TIMEOUT", "900")))
        summary = {"schema": "zth_run4a_baseline_summary_v1", "task_id": task["task_id"], "task_family": task["task_family"], "prompt": prompt, "raw_response": None, "response_metadata": None, "resource_telemetry": artifact.get("resource_telemetry"), "validation": None, "transport_valid": False, "transport_classification": artifact["classification"], "eligible": False, "eligibility_reason": "infrastructure failure", "disposition": "infrastructure_error", "infrastructure_artifact": artifact["artifact_ref"]}
        _json_write(summary_path, summary)
        _json_write(state_path, {"state": "baseline_terminal", "disposition": summary["disposition"]})
        return summary
    raw_digest = _json_write(candidate_dir / "baseline.raw.json", raw)
    classification = raw["metadata"].get("transport_classification")
    if classification != "model_response":
        artifact = _write_infrastructure_failure(candidate_dir, trajectory, call_id=call_id, role="worker", started_at=started_at, started=started, exc=RuntimeError(raw["metadata"].get("error") or classification), timeout_seconds=int(os.environ.get("ZTH_CAPABILITY_WORKER_TIMEOUT", "900")), response_present=True, response_artifact="baseline.raw.json")
        summary = {"schema": "zth_run4a_baseline_summary_v1", "task_id": task["task_id"], "task_family": task["task_family"], "prompt": prompt, "raw_response": "baseline.raw.json", "response_metadata": raw["metadata"], "resource_telemetry": raw["metadata"].get("resource_telemetry"), "validation": None, "transport_valid": False, "transport_classification": classification, "eligible": False, "eligibility_reason": "infrastructure failure", "disposition": "infrastructure_error", "infrastructure_artifact": artifact["artifact_ref"], "raw_sha256": raw_digest}
    else:
        validation = _validator_result(raw["content"], task, attempt_id="baseline")
        validation_digest = _json_write(candidate_dir / "baseline.validation.json", validation)
        _append_transition(trajectory, "response_captured", call_id=call_id, role="worker", artifact_ref="baseline.raw.json", artifact_sha256=raw_digest, validation_ref="baseline.validation.json", validation_sha256=validation_digest, transport_valid=True)
        failed = validation.get("validation_status") == "failed"
        summary = {"schema": "zth_run4a_baseline_summary_v1", "task_id": task["task_id"], "task_family": task["task_family"], "prompt": prompt, "raw_response": "baseline.raw.json", "response_metadata": raw["metadata"], "resource_telemetry": raw["metadata"].get("resource_telemetry"), "validation": validation, "transport_valid": True, "transport_classification": "model_response", "eligible": failed, "eligibility_reason": "valid model response with deterministic baseline failure" if failed else "valid model response passed deterministic baseline validation", "disposition": "baseline_failed_eligible" if failed else "baseline_pass", "raw_sha256": raw_digest, "validation_sha256": validation_digest}
    _json_write(summary_path, summary)
    _json_write(state_path, {"state": "baseline_terminal", "disposition": summary["disposition"]})
    _append_transition(trajectory, "baseline_terminal", disposition=summary["disposition"], eligible=summary["eligible"])
    return summary


def write_block_selection(block: str, candidate_order: list[str], summaries: Mapping[str, Mapping[str, Any]], block_dir: Path) -> dict[str, Any]:
    eligible = [task_id for task_id in candidate_order if summaries[task_id].get("eligible") is True]
    selected, reserve = select_included_candidates(candidate_order, set(eligible), 4)
    result = {"schema": "zth_run4a_block_selection_v1", "block": block, "candidate_order": candidate_order, "eligibility": {task_id: bool(summaries[task_id].get("eligible")) for task_id in candidate_order}, "eligibility_reasons": {task_id: summaries[task_id].get("eligibility_reason") for task_id in candidate_order}, "included_task_ids": selected, "reserve_task_ids": reserve, "selected_count": len(selected), "block_complete": len(selected) == 4}
    _json_write(block_dir / "selection.json", result)
    return result


def _arm_binding(preregistration: Mapping[str, Any], manifest: Mapping[str, Any], task_id: str, intervention: str, baseline_summary: Mapping[str, Any], repo_root: Path) -> dict[str, Any]:
    frozen = preregistration["frozen_inputs"]
    return {"schema": "zth_run4a_arm_binding_v1", "task_id": task_id, "intervention": intervention, "preregistration_sha256": canonical_sha256(preregistration), "fixture_pack_sha256": manifest["pack_sha256"], "baseline_summary_sha256": canonical_sha256(baseline_summary), "harness_sha256": preregistration["harness"]["sha256"], "patch_id": frozen["deterministic_patch_id"], "patch_sha256": frozen["deterministic_patch_sha256"], "models": preregistration["models"], "timeouts_seconds": preregistration["timeouts_seconds"]}


def _arm_terminal(arm_dir: Path, binding: Mapping[str, Any]) -> dict[str, Any] | None:
    summary_path = arm_dir / "arm_summary.json"
    binding_path = arm_dir / "arm_binding.json"
    if not summary_path.exists() and not binding_path.exists():
        return None
    index_path = arm_dir / "arm_artifacts.json"
    if not summary_path.exists() or not binding_path.exists() or not index_path.exists():
        raise Run4ADriverError(f"incomplete arm artifacts in {arm_dir}")
    if _read_json(binding_path) != dict(binding):
        raise Run4ADriverError(f"arm binding mismatch in {arm_dir}")
    summary = _read_json(summary_path)
    if summary.get("disposition") not in {"ready_for_review", "unresolved", "infrastructure_error"}:
        raise Run4ADriverError(f"nonterminal arm summary in {arm_dir}")
    _assert_no_ambiguous_started(arm_dir / "trajectory.jsonl")
    index = _read_json(index_path)
    current = {path.name: sha256_file(path) for path in sorted(arm_dir.iterdir()) if path.is_file() and path.name != "arm_artifacts.json"}
    if index.get("files") != current:
        raise Run4ADriverError(f"terminal arm artifact hash mismatch in {arm_dir}")
    return summary


def _write_arm_artifact_index(arm_dir: Path) -> None:
    files = {path.name: sha256_file(path) for path in sorted(arm_dir.iterdir()) if path.is_file() and path.name != "arm_artifacts.json"}
    _json_write(arm_dir / "arm_artifacts.json", {"schema": "zth_run4a_arm_artifact_index_v1", "files": files})


def aggregate_results(preregistration: Mapping[str, Any], manifest: Mapping[str, Any], output_dir: Path, selections: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    thresholds = preregistration["metrics"]["support_threshold"]
    blocks: dict[str, Any] = {}
    supported_blocks = 0
    for block, selection in selections.items():
        rows: dict[str, Any] = {}
        for intervention in ARM_NAMES:
            if not selection["block_complete"]:
                rows[intervention] = {"block_complete": False, "comparable_opportunities": 0, "valid_model_responses": 0, "infrastructure_exclusions": 0, "validated_rescues": 0, "rescue_rate": 0.0, "evidence_status": "insufficient", "expected_decision_cost_ms": [], "realized_elapsed_ms": [], "worker_retry_calls": 0, "intervention_calls": 0}
                continue
            observations = []
            infra = 0
            for task_id in selection["included_task_ids"]:
                summary = _read_json(output_dir / "tasks" / task_id / "arms" / intervention / "arm_summary.json")
                if summary.get("capability_verdict_available") and summary.get("transport_valid") is True:
                    observations.append(summary)
                else:
                    infra += 1
            valid = len(observations)
            rescues = sum(bool(row.get("deterministically_validated_rescue")) for row in observations)
            rate = rescues / valid if valid else 0.0
            if valid >= thresholds["minimum_comparable_opportunities"]:
                status = "supported_positive" if rate >= thresholds["minimum_rescue_rate"] else "supported_negative"
            else:
                status = "observed" if valid else "insufficient"
            rows[intervention] = {"comparable_opportunities": len(selection["included_task_ids"]), "valid_model_responses": valid, "infrastructure_exclusions": infra, "validated_rescues": rescues, "rescue_rate": rate, "evidence_status": status, "expected_decision_cost_ms": [row.get("expected_action_cost_ms") for row in observations], "realized_elapsed_ms": [row.get("realized_elapsed_ms") for row in observations], "worker_retry_calls": sum((output_dir / "tasks" / task_id / "arms" / intervention / "worker-retry.raw.json").exists() for task_id in selection["included_task_ids"]), "intervention_calls": sum((output_dir / "tasks" / task_id / "arms" / intervention / (intervention + ".raw.json")).exists() for task_id in selection["included_task_ids"])}
            if status == "supported_positive":
                rows.setdefault("_supported_count", 0)
                rows["_supported_count"] += 1
        supported_blocks += rows.get("_supported_count", 0) >= 2
        rows.pop("_supported_count", None)
        blocks[block] = rows
    result = {"schema": "zth_run4a_aggregate_v1", "status": "review_required", "blocks": blocks, "blocks_with_at_least_two_supported_positive_interventions": sum(1 for block in blocks.values() if sum(row["evidence_status"] == "supported_positive" for row in block.values()) >= 2), "evidence_formation_criterion_met": supported_blocks >= 2, "capability_bundle_modified": False, "routing_policy_modified": False}
    _json_write(output_dir / "aggregate.json", result)
    return result


def run_experiment(context: Mapping[str, Any], output_dir: Path, *, worker: Callable[[str], WorkerResponse], local_teacher: Callable[[str], WorkerResponse], external_teacher: Callable[[str], tuple[str, str]], deterministic_patch: Mapping[str, Any]) -> dict[str, Any]:
    """Execute the frozen protocol; callers must explicitly opt into this."""
    prereg = context["preregistration"]
    manifest = context["manifest"]
    output_dir.mkdir(parents=True, exist_ok=True)
    execution_manifest_path = output_dir / "execution_manifest.json"
    existing_execution = None
    if execution_manifest_path.exists():
        execution = _read_json(execution_manifest_path)
        if execution.get("status") in TERMINAL_EXPERIMENT_STATES:
            return execution
        active_call = execution.get("active_call")
        if active_call:
            raise Run4ADriverError(f"execution has an unresolved active call: {active_call}")
        existing_execution = execution
    execution = existing_execution or {"schema": "zth_run4a_execution_manifest_v1", "status": "experiment_incomplete", "started_at": _utc_now(), "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), "preregistration_sha256": canonical_sha256(prereg), "fixture_pack_sha256": manifest["pack_sha256"], "candidate_states": {task_id: "baseline_not_started" for task_id in prereg["fixture_pack"]["task_ids"]}, "arm_orders_executed": {}, "model_calls_started": False}
    if execution.get("preregistration_sha256") != canonical_sha256(prereg) or execution.get("fixture_pack_sha256") != manifest["pack_sha256"]:
        raise Run4ADriverError("existing execution binding mismatch")
    _json_write(execution_manifest_path, execution)
    selections: dict[str, dict[str, Any]] = {}
    tasks_by_id = {row["task_id"]: load_task_fixture(context["pack_dir"] / Path(row["path"]).name) for row in manifest["fixtures"]}
    for block in TARGET_BLOCKS:
        block_dir = output_dir / "blocks" / block
        candidate_order = manifest["candidate_order_by_block"][block]
        summaries = {}
        for task_id in candidate_order:
            candidate_dir = output_dir / "candidates" / task_id
            execution["active_call"] = {"kind": "baseline", "task_id": task_id}
            execution["model_calls_started"] = True
            _json_write(execution_manifest_path, execution)
            summary = run_baseline(tasks_by_id[task_id], candidate_dir, worker=worker)
            execution.pop("active_call", None)
            summaries[task_id] = summary
            execution["candidate_states"][task_id] = "baseline_terminal"
            _json_write(execution_manifest_path, execution)
        selection = write_block_selection(block, candidate_order, summaries, block_dir)
        selections[block] = selection
        execution.setdefault("selections", {})[block] = selection
        _json_write(execution_manifest_path, execution)
        if len(selection["included_task_ids"]) < 4:
            continue
        for task_id in selection["included_task_ids"]:
            task_dir = output_dir / "tasks" / task_id
            baseline_summary = summaries[task_id]
            baseline = {"task_id": task_id, "transport_valid": baseline_summary["transport_valid"], "transport_classification": baseline_summary["transport_classification"], "validation": baseline_summary["validation"], "raw": _read_json(output_dir / "candidates" / task_id / "baseline.raw.json") if baseline_summary.get("raw_response") else {}}
            for intervention in prereg["arm_order"]["orders"][task_id]:
                arm_dir = task_dir / "arms" / intervention
                binding = _arm_binding(prereg, manifest, task_id, intervention, baseline_summary, Path("."))
                terminal = _arm_terminal(arm_dir, binding)
                if terminal is None:
                    _json_write(arm_dir / "arm_binding.json", binding)
                    execution["candidate_states"][task_id] = "arm_started"
                    execution["model_calls_started"] = True
                    execution["active_call"] = {"kind": "arm", "task_id": task_id, "intervention": intervention}
                    execution.setdefault("arm_orders_executed", {}).setdefault(task_id, []).append(intervention)
                    _json_write(execution_manifest_path, execution)
                    terminal = run_isolated_intervention_arm(tasks_by_id[task_id], baseline, intervention=intervention, out_dir=arm_dir, worker=worker, local_teacher=local_teacher, external_teacher=external_teacher, deterministic_patch=deterministic_patch)
                    _write_arm_artifact_index(arm_dir)
                    execution.pop("active_call", None)
                execution["candidate_states"][task_id] = "arm_terminal"
                _json_write(execution_manifest_path, execution)
    aggregate = aggregate_results(prereg, manifest, output_dir, selections)
    execution["status"] = "experiment_completed" if all(selection["block_complete"] for selection in selections.values()) else "experiment_incomplete"
    execution["completed_at"] = _utc_now()
    execution["aggregate_path"] = "aggregate.json"
    _json_write(execution_manifest_path, execution)
    return execution


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true", help="validate all frozen bindings without making calls")
    parser.add_argument("--execute", action="store_true", help="explicitly authorize execution of the frozen protocol")
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    context = validate_preregistration(repo_root / args.preregistration if not args.preregistration.is_absolute() else args.preregistration, repo_root, require_runtime_identities=not args.dry_run)
    if args.dry_run or not args.execute:
        print(json.dumps({"status": "validated", "model_calls_made": False, "fixture_pack_sha256": context["manifest"]["pack_sha256"]}, sort_keys=True))
        return 0
    frozen = context["preregistration"]["frozen_inputs"]
    patch = {"patch_id": frozen["deterministic_patch_id"], "patch_path": str(repo_root / frozen["deterministic_patch_path"]), "patch_sha256": frozen["deterministic_patch_sha256"]}
    result = run_experiment(context, args.output_dir if args.output_dir.is_absolute() else repo_root / args.output_dir, worker=_default_worker, local_teacher=_default_local_teacher, external_teacher=_default_external_teacher, deterministic_patch=patch)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
