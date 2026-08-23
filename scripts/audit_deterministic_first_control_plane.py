#!/usr/bin/env python3
"""Model-free audit of the preserved deterministic-first run."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts import zth_deterministic_first_semantic_fallback as probe

ROOT = probe.ROOT
RUN = ROOT / ".work/model_size_supplier_floor/deterministic_first_semantic_fallback/run_20260823T120100Z"
MATRIX = ROOT / "docs/research/DETERMINISTIC_FIRST_SEMANTIC_FALLBACK_MATRIX_2026-08-23.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def audit_rows() -> list[dict[str, Any]]:
    historical = read(MATRIX)
    rows = []
    for source in historical["aggregate"]["rows"]:
        task_dir = RUN / "tasks" / source["task_id"]
        operation = read(task_dir / "operation_derivation_1.json") if (task_dir / "operation_derivation_1.json").exists() else read(task_dir / "operation_derivation_0.json")
        plan = read(task_dir / "capability_plan_0.json")
        result = read(task_dir / "runtime_result.json")
        tool_observation = read(task_dir / "tool_observation.json") if (task_dir / "tool_observation.json").exists() else None
        operation_resolved = operation["status"] == "RESOLVED"
        operation_authorized = bool(operation_resolved and operation.get("canonical_operation") in read(task_dir / "runtime_task.json")["environment_facts"]["authority_record"].get("allowed_observation_operations", []))
        operation_executed = bool(tool_observation and tool_observation.get("status") == "VALID_OBSERVATION")
        non_observation = operation.get("canonical_operation") in {"inspect", "amend", "index", "dispatch"}
        required_execution_supplier_present = operation_executed or not non_observation
        routing_success = bool(plan["overall_coverage"] == "COMPLETE" and (operation_resolved or source["regime"] == "SEMANTIC_FALLBACK_REQUIRED"))
        task_terminal_success = operation_executed
        rows.append({
            "task_id": source["task_id"],
            "regime": source["regime"],
            "frozen_evaluator_correct": source["task_correct"],
            "routing_decision_correct": routing_success,
            "required_execution_supplier_present": required_execution_supplier_present,
            "operation_resolved": operation_resolved,
            "operation_authorized": operation_authorized,
            "operation_actually_executed": operation_executed,
            "task_success_contract_satisfied": result["terminal_state"] == "terminal_success",
            "task_terminal_success": task_terminal_success,
            "historical_terminal_state": result["terminal_state"],
            "historical_tool_calls": result.get("tool_calls", 0),
            "historical_model_calls": result.get("model_calls", 0),
            "completion_interpretation": "observation produced and validated" if operation_executed else ("routing-only terminal; no actuator executed" if non_observation else "fail-closed or semantic evidence incomplete"),
        })
    return rows


def audit() -> dict[str, Any]:
    old_manifest = read(RUN / "router_manifest.json")
    old_runtime_factory = probe.runtime_task
    runtime_example = old_runtime_factory(probe.tasks()[0])
    evaluator_corruption = {"expected_requested_target":"corrupted/path.md","expected_authority_operations":["delete"]}
    corrupted_runtime = old_runtime_factory({**probe.tasks()[0], **evaluator_corruption})
    rows = audit_rows()
    return {
        "schema":"zth_deterministic_first_control_plane_audit_v0",
        "source_closeout_commit":"1d68d672158e40c29f5eaa3bc48b726815238154",
        "historical_raw_evidence_modified":False,
        "preserved_markers":{
            "DETERMINISTIC_FIRST_CAPABILITY_ROUTING_DEMONSTRATED":True,
            "MODEL_CALL_AVOIDANCE_FROM_CAPABILITY_DECOMPOSITION_DEMONSTRATED":True,
            "SEMANTIC_MODEL_FALLBACK_DEMONSTRATED":"bounded partial routing/normalization sense",
            "DYNAMIC_INTELLIGENCE_SURFACE_MINIMIZATION_DEMONSTRATED":"bounded routing-decision sense",
        },
        "runtime_expected_field_direct_reads":0,
        "evaluator_derived_runtime_authority":runtime_example["environment_facts"]["authority_record"] != corrupted_runtime["environment_facts"]["authority_record"],
        "oracle_free_runtime_authority_demonstrated":False,
        "authority_value_correctness_not_disputed":True,
        "runtime_authority_source":"evaluator expected_requested_target/expected_authority_operations via runtime_task()",
        "authority_provenance_graph":["evaluator task expectations","runtime_task(task)","environment_facts.authority_record","tool authorization"],
        "runtime_evaluator_dependency_graph":["evaluator fields -> runtime authority (historical defect)","runtime authority -> capability/authorization","only closeout scoring should consume evaluator fields"],
        "evaluator_corruption_changes_historical_runtime_authority":runtime_example["environment_facts"]["authority_record"] != corrupted_runtime["environment_facts"]["authority_record"],
        "routing_success_task_success_separation":True,
        "non_observation_operations_terminated_without_actuation":any(r["historical_terminal_state"] == "terminal_success" and not r["operation_actually_executed"] for r in rows),
        "end_to_end_task_completion_demonstrated":False,
        "success_contract_confused_routing_success_with_task_success":True,
        "rows":rows,
        "summary":{
            "frozen_evaluator_terminal_match":sum(r["frozen_evaluator_correct"] for r in rows),
            "routing_success":sum(r["routing_decision_correct"] for r in rows),
            "operation_actually_executed":sum(r["operation_actually_executed"] for r in rows),
            "task_terminal_success":sum(r["task_terminal_success"] for r in rows),
            "fallback_planned":sum(r["regime"] == "SEMANTIC_FALLBACK_REQUIRED" for r in rows),
            "fallback_model_calls":sum(r["historical_model_calls"] for r in rows if r["regime"] == "SEMANTIC_FALLBACK_REQUIRED"),
            "fallback_canonical_resolved":sum(r["regime"] == "SEMANTIC_FALLBACK_REQUIRED" and r["operation_resolved"] for r in rows),
            "fallback_fail_closed":sum(r["regime"] == "SEMANTIC_FALLBACK_REQUIRED" and not r["operation_resolved"] for r in rows),
            "model_calls":sum(r["historical_model_calls"] for r in rows),
            "tool_calls":sum(r["historical_tool_calls"] for r in rows),
            "no_call_audit_model_calls":0,
            "no_call_audit_tool_calls":0,
        },
        "historical_manifest_sha256":digest(RUN / "router_manifest.json"),
        "historical_matrix_sha256":digest(MATRIX),
        "qualification_change":False,
    }


def main() -> None:
    result = audit()
    out = ROOT / "docs/research/DETERMINISTIC_FIRST_SEMANTIC_FALLBACK_CONTROL_PLANE_AUDIT_MATRIX_2026-08-23.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
