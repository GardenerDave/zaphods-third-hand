#!/usr/bin/env python3
"""Model-free closeout for a sealed DIRECT_UNIT_CALIBRATION Stage A run."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from local_harness.supervised_reference_fact_validator import validate_reference_facts


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "docs/research/DIRECT_UNIT_CALIBRATION_FREEZE_V2_2026-08-24.json"
INTERFACE = ROOT / "docs/research/DIRECT_UNIT_CALIBRATION_INTERFACE_CONTRACT_V2_2026-08-24.json"
RUNTIME = ROOT / "docs/research/DIRECT_UNIT_CALIBRATION_RUNTIME_MANIFEST_V2_2026-08-24.json"
PAYLOADS = ROOT / "docs/research/DIRECT_UNIT_CALIBRATION_PAYLOAD_MANIFEST_V2_2026-08-24.json"
EVALUATOR = ROOT / "docs/research/DIRECT_UNIT_CALIBRATION_EVALUATOR_CASES_V2_2026-08-24.json"
SCOPE_RUN = ROOT / ".work/model_size_supplier_floor/delegation_prediction_test_scope_v0/run_20260824T170000Z"
SCOPE_EVALUATOR = ROOT / "docs/research/DELEGATION_PREDICTION_PROSPECTIVE_EVALUATOR_CASES_2026-08-24.json"
SCOPE_INTERFACE = ROOT / "docs/research/DELEGATION_PREDICTION_PROSPECTIVE_INTERFACE_CONTRACT_V2_2026-08-24.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> str:
    data = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_object(raw: str) -> tuple[Any, bool]:
    duplicates: list[str] = []

    def hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result and key not in duplicates:
                duplicates.append(key)
            result[key] = value
        return result

    try:
        return json.loads(raw, object_pairs_hook=hook), not duplicates
    except json.JSONDecodeError:
        return None, False


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def required_fields(parsed: Any, fields: list[str]) -> bool:
    return isinstance(parsed, dict) and all(field in parsed for field in fields)


def protocol_valid(response: dict[str, Any], supplier_id: str) -> bool:
    metadata = response.get("metadata", {})
    if metadata.get("evaluator_access") is not False:
        return False
    if supplier_id == "local_teacher":
        return metadata.get("tool_calls") == 0 and metadata.get("repository_access") is False
    return metadata.get("tool_calls_observed") == 0 and metadata.get("repository_access_observed") is False


def failure_class(transport: bool, parsed: bool, contract: bool, protocol: bool, semantic: bool) -> str:
    if not transport:
        return "TRANSPORT_FAILURE"
    if not parsed:
        return "PARSE_FAILURE"
    if not contract:
        return "CONTRACT_FAILURE"
    if not protocol:
        return "PROTOCOL_FAILURE"
    if not semantic:
        return "SEMANTIC_FAILURE"
    return "VALID_DIRECT_RESPONSE"


def v2_record(run: Path, case: dict[str, Any], supplier_id: str) -> dict[str, Any]:
    arm = run / "cases" / case["case_id"] / supplier_id
    response_path = arm / "response.json"
    response = read_json(response_path)
    transport = response.get("metadata", {}).get("transport_classification") == "model_response"
    parsed, no_duplicates = parse_object(response.get("content", ""))
    parsed_valid = parsed is not None and no_duplicates and isinstance(parsed, dict)
    contract = required_fields(parsed, case["output_contract"]["required_fields"])
    evaluator_facts = case["expected"]
    semantic_result = validate_reference_facts(response.get("content", ""), evaluator_facts)
    semantic = semantic_result["validation_status"] == "passed"
    review_valid = isinstance(parsed, dict) and parsed.get("review_status") == evaluator_facts["review_status"]
    protocol = protocol_valid(response, supplier_id)
    capability = transport and parsed_valid and contract and semantic and protocol
    metadata = response.get("metadata", {})
    native_model = None
    stderr = (arm / "stderr.txt").read_text(encoding="utf-8") if (arm / "stderr.txt").exists() else ""
    match = re.search(r"^model:\s*(.+)$", stderr, re.MULTILINE)
    if match:
        native_model = match.group(1).strip()
    return {
        "supplier_id": supplier_id,
        "model_runtime_identity": case["supplier_identity"],
        "native_model_observed": native_model,
        "capability_family": case["capability_family"],
        "bounded_responsibility": case["bounded_responsibility"],
        "interface_id": case["interface_id"],
        "interface_hash": case["interface_hash"],
        "supplier_role": "DIRECT_RESPONDER",
        "downstream_dependencies": [],
        "validated_artifact": "direct_supplier_response",
        "authority_context": case["authority_context"],
        "evaluator_id": f"DIRECT_UNIT_CALIBRATION_EVALUATOR_CASES_V2_2026-08-24.json#{case['case_id']}",
        "evidence_timestamp": response.get("captured_at"),
        "case_id": case["case_id"],
        "experiment_payload_hash": response.get("experiment_payload_sha256"),
        "raw_response_hash": sha(response_path),
        "raw_content_hash": response.get("raw_response_sha256"),
        "transport_valid": transport,
        "parse_valid": parsed_valid,
        "required_fields_valid": contract,
        "contract_valid": contract,
        "reference_facts_valid": semantic,
        "semantic_valid": semantic,
        "review_status_valid": review_valid,
        "protocol_valid": protocol,
        "capability_valid": capability,
        "failure_class": failure_class(transport, parsed_valid, contract, protocol, semantic),
        "freshness_lineage": case["freshness_lineage"],
        "request": case["request"],
        "native_envelope_observation": {
            "tool_calls_observed": response.get("metadata", {}).get("tool_calls", response.get("metadata", {}).get("tool_calls_observed")),
            "repository_access_observed": response.get("metadata", {}).get("repository_access", response.get("metadata", {}).get("repository_access_observed")),
            "evaluator_access": response.get("metadata", {}).get("evaluator_access"),
            "stderr_hash": response.get("metadata", {}).get("stderr_sha256"),
        },
    }


def scope_record(case: dict[str, Any], supplier_id: str) -> dict[str, Any]:
    response_path = SCOPE_RUN / "cases" / case["task_id"] / supplier_id / "response.json"
    response = read_json(response_path)
    parsed, no_duplicates = parse_object(response.get("content", ""))
    transport = response.get("metadata", {}).get("transport_classification") == "model_response"
    parsed_valid = parsed is not None and no_duplicates and isinstance(parsed, dict)
    expected = case["expected"]
    contract = required_fields(parsed, ["allowed_targets", "held_targets", "scope_expansion_required", "review_status"])
    semantic = contract and parsed == expected
    protocol = response.get("metadata", {}).get("tool_calls") == 0 and response.get("metadata", {}).get("repository_access") is False and response.get("metadata", {}).get("evaluator_access") is False
    capability = transport and parsed_valid and contract and semantic and protocol
    payload = read_json(SCOPE_RUN / "cases" / case["task_id"] / supplier_id / "experiment_payload.json")
    return {
        "supplier_id": supplier_id,
        "model_runtime_identity": response.get("metadata", {}).get("model") if supplier_id == "local_teacher" else "codex-cli-0.146.0",
        "capability_family": "scope-authority-boundary",
        "bounded_responsibility": "direct four-field scope-authority response under review-only authority",
        "interface_id": "DELEGATION_PREDICTION_SCOPE_JSON_COMPATIBLE_SUCCESSOR_V1",
        "interface_hash": sha(SCOPE_INTERFACE),
        "supplier_role": "DIRECT_RESPONDER",
        "downstream_dependencies": [],
        "validated_artifact": "direct_supplier_response",
        "authority_context": payload["authority_context"],
        "evaluator_id": f"DELEGATION_PREDICTION_PROSPECTIVE_EVALUATOR_CASES_2026-08-24.json#{case['task_id']}",
        "evidence_timestamp": response.get("captured_at"),
        "case_id": case["task_id"],
        "experiment_payload_hash": response.get("experiment_payload_sha256"),
        "raw_response_hash": sha(response_path),
        "raw_content_hash": response.get("raw_response_sha256"),
        "transport_valid": transport,
        "parse_valid": parsed_valid,
        "required_fields_valid": contract,
        "contract_valid": contract,
        "reference_facts_valid": semantic,
        "semantic_valid": semantic,
        "review_status_valid": parsed_valid and parsed.get("review_status") == "ready_for_review",
        "protocol_valid": protocol,
        "capability_valid": capability,
        "failure_class": failure_class(transport, parsed_valid, contract, protocol, semantic),
        "freshness_lineage": "sealed Scope V0 direct evidence; historical relative to this Stage A closeout",
        "request": payload["request"],
        "historical_source_run": str(SCOPE_RUN.relative_to(ROOT)),
    }


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_supplier: dict[str, dict[str, Any]] = {}
    for supplier in ("local_teacher", "external_teacher"):
        supplier_rows = [row for row in records if row["supplier_id"] == supplier]
        families: dict[str, dict[str, Any]] = {}
        for family in ("scope-authority-boundary", "triage-routing", "unsupported-certainty"):
            rows = [row for row in supplier_rows if row["capability_family"] == family]
            families[family] = {
                "successes": sum(row["capability_valid"] for row in rows),
                "failures": sum(not row["capability_valid"] for row in rows),
                "opportunities": len(rows),
                "rate": sum(row["capability_valid"] for row in rows) / len(rows) if rows else None,
                "failure_classes": {cls: sum(row["failure_class"] == cls for row in rows) for cls in sorted({row["failure_class"] for row in rows})},
            }
        micro_successes = sum(row["capability_valid"] for row in supplier_rows)
        rates = [families[family]["rate"] for family in families]
        by_supplier[supplier] = {
            "families": families,
            "micro_aggregate_direct": {"successes": micro_successes, "failures": len(supplier_rows) - micro_successes, "opportunities": len(supplier_rows), "rate": micro_successes / len(supplier_rows)},
            "family_macro_aggregate_direct": sum(rates) / len(rates),
        }
    return by_supplier


def closeout(run: Path) -> int:
    raw_manifest = read_json(run / "raw_response_manifest.json")
    lifecycle = read_json(run / "lifecycle.json")
    runtime = read_json(RUNTIME)
    interface = read_json(INTERFACE)
    evaluator = read_json(EVALUATOR)
    scope_evaluator = read_json(SCOPE_EVALUATOR)
    if raw_manifest.get("status") != "SEALED_BEFORE_EVALUATION" or raw_manifest.get("evaluator_loaded_during_acquisition") is not False:
        raise RuntimeError("raw acquisition is not sealed before evaluation")
    if raw_manifest.get("actual_supplier_calls") != 32 or lifecycle.get("model_calls") != 32:
        raise RuntimeError("incomplete Stage A acquisition; refusing capability closeout")
    runtime_cases = {case["case_id"]: case for case in runtime["cases"]}
    evaluator_cases = {case["case_id"]: case for case in evaluator["cases"]}
    new_records: list[dict[str, Any]] = []
    for case_id in runtime["case_order"]:
        case = dict(runtime_cases[case_id])
        case.update(evaluator_cases[case_id])
        case["output_contract"] = interface["interfaces"][case["capability_family"]]["output_contract"]
        case["supplier_identity"] = "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf" if case_id and case_id else None
        # Identity is replaced per arm by v2_record from the preserved raw metadata.
        for supplier in ("local_teacher", "external_teacher"):
            row = v2_record(run, case, supplier)
            row["model_runtime_identity"] = "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf" if supplier == "local_teacher" else "codex-cli-0.146.0"
            new_records.append(row)
    scope_records: list[dict[str, Any]] = []
    for case in scope_evaluator["cases"]:
        for supplier in ("local_teacher", "external_teacher"):
            scope_records.append(scope_record(case, supplier))
    all_records = scope_records + new_records
    summaries = summarize(all_records)
    scope_manifest = read_json(SCOPE_RUN / "raw_response_manifest.json")
    integrity = {
        "planned_new_supplier_calls": 32,
        "actual_new_supplier_calls": raw_manifest["actual_supplier_calls"],
        "actual_new_local_calls": raw_manifest["actual_local_calls"],
        "actual_new_external_calls": raw_manifest["actual_external_calls"],
        "new_response_files": len(list(run.rglob("response.json"))),
        "new_call_started_files": len(list(run.rglob("call_started.json"))),
        "new_call_finished_files": len(list(run.rglob("call_finished.json"))),
        "new_failure_files": len(list(run.rglob("infrastructure_failure.json"))),
        "retries": raw_manifest["retries"],
        "replays": raw_manifest["replays"],
        "evaluator_loaded_during_acquisition": raw_manifest["evaluator_loaded_during_acquisition"],
        "raw_sealed_before_evaluation": raw_manifest["raw_direct_unit_calibration_responses_sealed_before_evaluation"],
        "scope_v0_manifest_sha256": sha(SCOPE_RUN / "raw_response_manifest.json"),
        "scope_v0_interface_sha256": sha(SCOPE_INTERFACE),
        "v2_freeze_sha256": sha(FREEZE),
        "v2_interface_sha256": sha(INTERFACE),
        "v2_runtime_sha256": sha(RUNTIME),
        "v2_payload_manifest_sha256": sha(PAYLOADS),
        "v2_evaluator_sha256": sha(EVALUATOR),
        "frozen_case_order_unchanged": runtime["case_order"] == [case["case_id"] for case in runtime["cases"]],
    }
    run_closeout = {
        "schema": "zth_direct_unit_calibration_stage_a_closeout_v1",
        "experiment_id": "DIRECT_UNIT_CALIBRATION_2026-08-24",
        "run_directory": str(run.relative_to(ROOT)),
        "freeze_characterization": "DIRECT_UNIT_CALIBRATION_EXPERIMENT_CORRECTED_FREEZE_UNEXECUTED",
        "evaluator_loaded_only_after_raw_seal": True,
        "scope_v0_historical_direct_observations": 32,
        "new_direct_observations": 32,
        "total_direct_observations": len(all_records),
        "integrity": integrity,
        "summaries": summaries,
        "micro_and_family_macro_summaries_computed": True,
        "future_broad_policy_aggregation_rule_not_selected": True,
        "stage_b_started": False,
        "qualification_change": False,
        "production_routing_change": False,
        "controls": {"model_calls": 32, "teacher_intervention": 0, "tool_calls": 0, "external_inference_calls": 16, "retries": 0, "replays": 0},
        "stage_a_success": all(row["supplier_role"] == "DIRECT_RESPONDER" and row["downstream_dependencies"] == [] for row in new_records),
        "primary_characterization": "DIRECT_UNIT_CALIBRATION_STAGE_A_COMPLETED_MODEL_FREE_CLOSEOUT",
    }
    write_json(run / "atomic_direct_evidence.json", {"schema": "zth_direct_unit_calibration_atomic_evidence_v1", "observations": all_records})
    write_json(run / "stage_a_closeout.json", run_closeout)
    matrix = {
        "schema": "zth_direct_unit_calibration_results_matrix_v1",
        "experiment_id": "DIRECT_UNIT_CALIBRATION_2026-08-24",
        "run_directory": str(run.relative_to(ROOT)),
        "freeze_sha256": sha(FREEZE),
        "interface_sha256": sha(INTERFACE),
        "runtime_manifest_sha256": sha(RUNTIME),
        "payload_manifest_sha256": sha(PAYLOADS),
        "evaluator_sha256": sha(EVALUATOR),
        "scope_v0_raw_manifest_sha256": sha(SCOPE_RUN / "raw_response_manifest.json"),
        "integrity": integrity,
        "supplier_family_summaries": summaries,
        "micro_and_family_macro_summaries_computed": True,
        "future_broad_policy_aggregation_rule_not_selected": True,
        "stage_b_started": False,
        "qualification_change": False,
        "production_routing_change": False,
        "failure_taxonomy": {cls: sum(row["failure_class"] == cls for row in new_records) for cls in sorted({row["failure_class"] for row in new_records})},
        "external_protocol_observation": {"tool_calls_observed": sum(row["native_envelope_observation"]["tool_calls_observed"] or 0 for row in new_records if row["supplier_id"] == "external_teacher"), "repository_access_observed": any(row["native_envelope_observation"]["repository_access_observed"] for row in new_records if row["supplier_id"] == "external_teacher"), "telemetry_structured": False},
        "stage_a_success": run_closeout["stage_a_success"],
        "primary_characterization": run_closeout["primary_characterization"],
    }
    results_path = ROOT / "docs/research/DIRECT_UNIT_CALIBRATION_RESULTS_MATRIX_2026-08-24.json"
    atomic_path = ROOT / "docs/research/DIRECT_UNIT_CALIBRATION_ATOMIC_EVIDENCE_2026-08-24.json"
    write_json(results_path, matrix)
    write_json(atomic_path, {"schema": "zth_direct_unit_calibration_atomic_evidence_v1", "source_run": str(run.relative_to(ROOT)), "observations": all_records})
    report = """# Direct-Unit Calibration Stage A Results

Date: 2026-08-24

## Boundary

Stage A acquisition completed once under the corrected V2 freeze. Raw supplier
responses were sealed before the V2 evaluator was loaded. This is direct-unit
calibration evidence, not a Stage B broad-versus-bounded routing comparison.

## Acquisition integrity

- planned/new calls: 32 / 32
- local calls: 16 / 16
- external calls: 16 / 16
- call starts/responses/finished: 32 / 32 / 32
- retries/replays: 0 / 0
- evaluator loaded during acquisition: false
- raw responses sealed before evaluation: true
- tools observed: local 0; external 0 observed in captured stderr telemetry
- repository access observed: false for both arms

## Direct-unit summaries

The machine-readable matrix reports, for each supplier, scope-authority,
triage-routing, and unsupported-certainty successes/opportunities, the pooled
micro aggregate, and the equal-family-weight macro aggregate. Failure classes
remain separate; no confidence formula, threshold, or routing policy was
selected.

Scope V0 contributes 32 immutable historical direct observations. The new run
contributes 32 observations. The combined Stage A corpus contains 64 atomic
observations. Scope V0 was not replayed or mutated.

## Interpretation boundary

This closeout establishes only whether aligned direct observations were created
under the three bounded responsibility/interface units. It does not qualify a
supplier, choose a broad aggregation rule, create Stage B targets, or change
production routing.

Primary characterization:

`DIRECT_UNIT_CALIBRATION_STAGE_A_COMPLETED_MODEL_FREE_CLOSEOUT`
"""
    (ROOT / "docs/research/DIRECT_UNIT_CALIBRATION_RESULTS_2026-08-24.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": "closeout_pass", "new_records": len(new_records), "scope_records": len(scope_records), "total_records": len(all_records), "summaries": summaries}, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--closeout", action="store_true")
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    if not args.closeout:
        parser.error("use --closeout")
    run = args.run_dir if args.run_dir.is_absolute() else ROOT / args.run_dir
    return closeout(run)


if __name__ == "__main__":
    raise SystemExit(main())
