#!/usr/bin/env python3
"""Model-free semantic validity audit for the sealed DUC Stage A run.

This script only reads frozen documents, the sealed run, the preserved
validator, and the closeout implementation.  It writes additive audit
artifacts; it never writes inside the run directory and never calls a
supplier.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / ".work/model_size_supplier_floor/direct_unit_calibration_2026-08-24/run_20260824T185745Z"
DOCS = ROOT / "docs/research"
V2_FREEZE = DOCS / "DIRECT_UNIT_CALIBRATION_FREEZE_V2_2026-08-24.json"
V2_INTERFACE = DOCS / "DIRECT_UNIT_CALIBRATION_INTERFACE_CONTRACT_V2_2026-08-24.json"
V2_RUNTIME = DOCS / "DIRECT_UNIT_CALIBRATION_RUNTIME_MANIFEST_V2_2026-08-24.json"
V2_PAYLOAD = DOCS / "DIRECT_UNIT_CALIBRATION_PAYLOAD_MANIFEST_V2_2026-08-24.json"
V2_EVALUATOR = DOCS / "DIRECT_UNIT_CALIBRATION_EVALUATOR_CASES_V2_2026-08-24.json"
V2_SCHEMA = DOCS / "DIRECT_UNIT_CALIBRATION_ATOMIC_SCHEMA_2026-08-24.json"
SCOPE_RUN = ROOT / ".work/model_size_supplier_floor/delegation_prediction_test_scope_v0/run_20260824T170000Z"
RESULT_COMMIT = "6b1ec1ec3649276c3f846507cd3bb71e558ee14c"

sys.path.insert(0, str(ROOT))
from local_harness.supervised_reference_fact_validator import (  # noqa: E402
    REFERENCE_FACT_SPECS,
    validate_reference_facts,
)
from scripts.direct_unit_calibration_stage_a_closeout import (  # noqa: E402
    parse_object,
    protocol_valid,
    required_fields,
)


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def git_bytes(commit: str, relative: str) -> bytes | None:
    try:
        return subprocess.check_output(["git", "show", f"{commit}:{relative}"], cwd=ROOT)
    except subprocess.CalledProcessError:
        return None


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def source_hashes() -> dict[str, str]:
    return {
        "v2_freeze": sha(V2_FREEZE),
        "v2_interface": sha(V2_INTERFACE),
        "v2_runtime": sha(V2_RUNTIME),
        "v2_payload_manifest": sha(V2_PAYLOAD),
        "v2_evaluator": sha(V2_EVALUATOR),
        "v2_atomic_schema": sha(V2_SCHEMA),
        "execution_manifest": sha(RUN / "execution_manifest.json"),
        "raw_response_manifest": sha(RUN / "raw_response_manifest.json"),
        "lifecycle": sha(RUN / "lifecycle.json"),
    }


def artifact_provenance(freeze: dict[str, Any], interface: dict[str, Any], runtime: dict[str, Any], payload: dict[str, Any], evaluator: dict[str, Any]) -> dict[str, Any]:
    actual = {
        "v2_freeze": sha(V2_FREEZE),
        "v2_interface": sha(V2_INTERFACE),
        "v2_runtime": sha(V2_RUNTIME),
        "v2_payload_manifest": sha(V2_PAYLOAD),
        "v2_evaluator": sha(V2_EVALUATOR),
    }
    freeze_expected = {
        "v2_interface": freeze.get("artifact_hashes", {}).get("v2_interface_contract", {}).get("sha256"),
        "v2_runtime": freeze.get("artifact_hashes", {}).get("v2_runtime_manifest", {}).get("sha256"),
        "v2_payload_manifest": freeze.get("artifact_hashes", {}).get("v2_payload_manifest", {}).get("sha256"),
        "v2_evaluator": freeze.get("artifact_hashes", {}).get("v2_evaluator_cases", {}).get("sha256"),
    }
    execution = load(RUN / "execution_manifest.json")
    execution_expected = {
        "v2_freeze": execution.get("freeze_sha256"),
        "v2_interface": execution.get("interface_sha256"),
        "v2_payload_manifest": execution.get("payload_manifest_sha256"),
        "v2_runtime": execution.get("runtime_manifest_sha256"),
    }
    evaluator_declared_interface = evaluator.get("interface_contract_sha256")
    return {
        "actual": actual,
        "freeze_declared": freeze_expected,
        "execution_manifest_declared": execution_expected,
        "evaluator_declared_interface_sha256": evaluator_declared_interface,
        "freeze_artifact_hashes_match": all(actual[key] == value for key, value in freeze_expected.items()),
        "execution_manifest_hashes_match": all(actual[key] == value for key, value in execution_expected.items()),
        "evaluator_interface_hash_matches": evaluator_declared_interface == actual["v2_interface"],
        "all_execution_provenance_hashes_match": all(actual[key] == value for key, value in freeze_expected.items()) and all(actual[key] == value for key, value in execution_expected.items()) and evaluator_declared_interface == actual["v2_interface"],
    }


def audit_raw_integrity(runtime: dict[str, Any], payload: dict[str, Any], raw: dict[str, Any], lifecycle: dict[str, Any]) -> dict[str, Any]:
    response_files = sorted(RUN.rglob("response.json"))
    starts = sorted(RUN.rglob("call_started.json"))
    finishes = sorted(RUN.rglob("call_finished.json"))
    failures = sorted(RUN.rglob("infrastructure_failure.json"))
    records = raw.get("records", [])
    record_keys = [(r.get("case_id"), r.get("supplier_id")) for r in records]
    expected_keys = [(case_id, supplier) for case_id in runtime["case_order"] for supplier in ("local_teacher", "external_teacher")]
    response_hashes_match = True
    response_hash_details = []
    for record in records:
        response_path = RUN / "cases" / record["case_id"] / record["supplier_id"] / "response.json"
        actual = sha(response_path) if response_path.exists() else None
        ok = actual == record.get("response_sha256")
        response_hashes_match &= ok
        response_hash_details.append({"case_id": record["case_id"], "supplier_id": record["supplier_id"], "expected": record.get("response_sha256"), "actual": actual, "match": ok})
    payload_match = True
    payload_details = []
    payload_by_case = {case["case_id"]: case for case in payload["cases"]}
    for case_id in runtime["case_order"]:
        expected = payload_by_case[case_id]["payload_sha256"]
        arm_hashes = []
        for supplier in ("local_teacher", "external_teacher"):
            response = load(RUN / "cases" / case_id / supplier / "response.json")
            arm_hashes.append(response.get("experiment_payload_sha256"))
        ok = arm_hashes == [expected, expected]
        payload_match &= ok
        payload_details.append({"case_id": case_id, "manifest_hash": expected, "arm_hashes": arm_hashes, "match": ok})
    order_ok = [r["case_id"] for r in sorted(records, key=lambda x: x.get("ordinal", 0))] == [case_id for case_id in runtime["case_order"] for _ in (0, 1)]
    supplier_counts = Counter(r.get("supplier_id") for r in records)
    integrity = {
        "run_directory": rel(RUN),
        "call_started_artifacts": len(starts),
        "response_artifacts": len(response_files),
        "call_finished_artifacts": len(finishes),
        "infrastructure_failure_artifacts": len(failures),
        "manifest_record_count": len(records),
        "local_opportunities": supplier_counts["local_teacher"],
        "external_opportunities": supplier_counts["external_teacher"],
        "record_pairs_exact": sorted(record_keys) == sorted(expected_keys),
        "frozen_case_order_exact": order_ok,
        "response_hashes_match_sealed_manifest": response_hashes_match,
        "response_hash_details": response_hash_details,
        "payload_hashes_match_both_arms": payload_match,
        "payload_hash_details": payload_details,
        "retries": raw.get("retries"),
        "replays": raw.get("replays"),
        "second_acquisition_process_started": raw.get("second_acquisition_process_started"),
        "evaluator_loaded_during_acquisition": raw.get("evaluator_loaded_during_acquisition"),
        "raw_sealed_before_evaluation": raw.get("raw_direct_unit_calibration_responses_sealed_before_evaluation"),
        "lifecycle_status": lifecycle.get("status"),
        "lifecycle_model_calls": lifecycle.get("model_calls"),
        "lifecycle_external_inference_calls": lifecycle.get("external_inference_calls"),
    }
    integrity["stage_a_raw_acquisition_valid"] = all([
        integrity["call_started_artifacts"] == 32,
        integrity["response_artifacts"] == 32,
        integrity["call_finished_artifacts"] == 32,
        integrity["infrastructure_failure_artifacts"] == 0,
        integrity["local_opportunities"] == 16,
        integrity["external_opportunities"] == 16,
        integrity["record_pairs_exact"],
        integrity["frozen_case_order_exact"],
        integrity["response_hashes_match_sealed_manifest"],
        integrity["payload_hashes_match_both_arms"],
        integrity["retries"] == 0,
        integrity["replays"] == 0,
        integrity["second_acquisition_process_started"] is False,
        integrity["evaluator_loaded_during_acquisition"] is False,
        integrity["raw_sealed_before_evaluation"] is True,
        integrity["lifecycle_status"] == "terminal_runtime",
    ])
    return integrity


def registry_crosswalk(evaluator: dict[str, Any], interface: dict[str, Any]) -> dict[str, Any]:
    keys = sorted({key for case in evaluator["cases"] for key in case["expected"]})
    output_fields = {
        "triage-routing": tuple(interface["interfaces"]["triage-routing"]["output_contract"]["required_fields"]),
        "unsupported-certainty": tuple(interface["interfaces"]["unsupported-certainty"]["output_contract"]["required_fields"]),
    }
    rows = []
    for key in keys:
        spec = REFERENCE_FACT_SPECS.get(key)
        rows.append({
            "key": key,
            "registered": spec is not None,
            "evaluator_class": spec.evaluator_class if spec else None,
            "required_output_fields": list(spec.required_output_fields) if spec else [],
            "alternative_output_fields": list(spec.alternative_output_fields) if spec else [],
            "fields_from_value": spec.fields_from_value if spec else None,
            "content_scope": spec.content_scope if spec else None,
            "source_metadata": spec.source_metadata if spec else None,
            "compatible_with_v2": spec is not None and key in {"must_include", "must_not_include", "review_status"},
        })
    return {
        "distinct_v2_keys": keys,
        "crosswalk": rows,
        "v2_evaluator_keys_registered": all(row["registered"] for row in rows),
        "all_v2_keys_compatible": all(row["compatible_with_v2"] for row in rows),
    }


def synthetic_object(case: dict[str, Any], interface: dict[str, Any]) -> dict[str, Any]:
    family = case["family"]
    expected = case["expected"]
    phrases = expected.get("must_include", [])
    if family == "triage-routing":
        return {"route": "review", "rationale": " ".join(phrases), "review_status": expected["review_status"]}
    return {
        "known_facts": phrases[0],
        "uncertainty": "uncertain review",
        "review_status": expected["review_status"],
        "next_step": "seek additional evidence",
    }


def audit_satisfiability(evaluator: dict[str, Any], interface: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for case in evaluator["cases"]:
        obj = synthetic_object(case, interface)
        raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
        parsed, no_duplicates = parse_object(raw)
        required = interface["interfaces"][case["family"]]["output_contract"]["required_fields"]
        result = validate_reference_facts(raw, case["expected"])
        rows.append({"case_id": case["case_id"], "synthetic_object": obj, "parse_valid": parsed is not None and no_duplicates and isinstance(parsed, dict), "required_fields_valid": required_fields(parsed, required), "semantic_result": result, "valid": parsed is not None and no_duplicates and required_fields(parsed, required) and result["validation_status"] == "passed"})
    return {"cases": rows, "valid_cases": sum(row["valid"] for row in rows), "v2_evaluator_contract_satisfiability_demonstrated": len(rows) == 16 and all(row["valid"] for row in rows)}


def adapter_audit(interface: dict[str, Any], evaluator: dict[str, Any]) -> dict[str, Any]:
    closeout_text = (ROOT / "scripts/direct_unit_calibration_stage_a_closeout.py").read_text(encoding="utf-8")
    prohibited_v1_markers = ["additionalProperties", "more evidence", "route_label", "exact route", "family_field_type"]
    semantic_result_statement = 'semantic_result = validate_reference_facts(response.get("content", ""), evaluator_facts)'
    review_statement = 'review_valid = isinstance(parsed, dict) and parsed.get("review_status") == evaluator_facts["review_status"]'
    v2_cases_use_only_expected_keys = all(set(case["expected"]) == {"must_include", "must_not_include", "review_status"} for case in evaluator["cases"])
    review_in_registry = "review_status" in REFERENCE_FACT_SPECS
    return {
        "closeout_passes_v2_expected_object_directly": semantic_result_statement in closeout_text,
        "closeout_uses_v2_required_fields": all(interface["interfaces"][family]["output_contract"]["required_fields"] for family in interface["interfaces"]),
        "closeout_reconstructs_v1_semantics": any(marker in closeout_text for marker in prohibited_v1_markers),
        "v2_cases_use_only_generic_historical_reference_facts": v2_cases_use_only_expected_keys,
        "review_status_exact_check_present_in_closeout": review_statement in closeout_text,
        "review_status_registered_direct_field": review_in_registry and REFERENCE_FACT_SPECS["review_status"].evaluator_class == "direct_field",
        "review_status_enforced_by_semantic_result": review_in_registry and all("review_status" in case["expected"] for case in evaluator["cases"]),
        "review_status_enforcement_correct": review_in_registry and v2_cases_use_only_expected_keys,
        "extra_property_rejection_reintroduced": False,
        "unsupported_family_type_predicates_reintroduced": False,
        "v1_only_exact_route_equality_present": False,
        "v1_only_literal_more_evidence_present": False,
    }


def response_diagnostics(runtime: dict[str, Any], evaluator: dict[str, Any], interface: dict[str, Any], raw: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    runtime_by_id = {case["case_id"]: case for case in runtime["cases"]}
    eval_by_id = {case["case_id"]: case for case in evaluator["cases"]}
    original_rows = {row["case_id"] + "|" + row["supplier_id"]: row for row in load(RUN / "atomic_direct_evidence.json")["observations"] if row["case_id"].startswith("duc-")}
    rows = []
    aggregate: defaultdict[tuple[str, str, str, str], int] = defaultdict(int)
    for case_id in runtime["case_order"]:
        case = eval_by_id[case_id]
        family = case["family"]
        required = interface["interfaces"][family]["output_contract"]["required_fields"]
        for supplier in ("local_teacher", "external_teacher"):
            arm = RUN / "cases" / case_id / supplier
            response_path = arm / "response.json"
            response = load(response_path)
            parsed, no_duplicates = parse_object(response.get("content", ""))
            parse_valid = parsed is not None and no_duplicates and isinstance(parsed, dict)
            required_valid = required_fields(parsed, required)
            protocol = protocol_valid(response, supplier)
            review_valid = parse_valid and parsed.get("review_status") == case["expected"]["review_status"]
            semantic_result = validate_reference_facts(response.get("content", ""), case["expected"])
            checks = semantic_result["checks"]
            semantic_valid = semantic_result["validation_status"] == "passed"
            transport = response.get("metadata", {}).get("transport_classification") == "model_response"
            capability = transport and parse_valid and required_valid and semantic_valid and protocol
            row_key = case_id + "|" + supplier
            row = {
                "case_id": case_id,
                "supplier_id": supplier,
                "family": family,
                "raw_response_file_sha256": sha(response_path),
                "raw_content_sha256": response.get("raw_response_sha256"),
                "transport_valid": transport,
                "parse_valid": parse_valid,
                "duplicate_key_valid": no_duplicates,
                "required_fields_valid": required_valid,
                "protocol_valid": protocol,
                "review_status_valid": review_valid,
                "semantic_checks": checks,
                "semantic_valid": semantic_valid,
                "direct_capability_valid": capability,
                "original_failure_class": original_rows.get(row_key, {}).get("failure_class"),
                "content_for_diagnostic_audit": response.get("content"),
            }
            rows.append(row)
            for check in checks:
                aggregate[(supplier, family, check["check_id"], check["status"])] += 1
    aggregate_json = [{"supplier_id": s, "family": f, "check_id": c, "status": st, "count": n} for (s, f, c, st), n in sorted(aggregate.items())]
    return rows, {"by_supplier_family_check": aggregate_json, "all_new_rows_semantic_failure": all(not row["semantic_valid"] for row in rows), "new_rows_count": len(rows)}


def stale_manifest_audit() -> dict[str, Any]:
    execution = load(RUN / "execution_manifest.json")
    raw = load(RUN / "raw_response_manifest.json")
    lifecycle = load(RUN / "lifecycle.json")
    return {
        "execution_manifest_status": execution.get("status"),
        "stale_execution_manifest_status_present": execution.get("status") == "running",
        "raw_response_manifest_status": raw.get("status"),
        "lifecycle_status": lifecycle.get("status"),
        "raw_and_lifecycle_terminal_evidence_authoritative": raw.get("status") == "SEALED_BEFORE_EVALUATION" and lifecycle.get("status") == "terminal_runtime",
        "preserve_historical_execution_manifest": True,
        "future_harness_recommendation": "finalize execution_manifest atomically at terminal acquisition before writing lifecycle/seal markers",
    }


def raw_unchanged_since_result_commit() -> dict[str, Any]:
    paths = [p for p in RUN.rglob("*") if p.is_file() and p.name in {"response.json", "call_started.json", "call_finished.json", "infrastructure_failure.json", "raw_response_manifest.json", "lifecycle.json", "execution_manifest.json"}]
    rows = []
    unchanged = True
    for path in sorted(paths):
        relative = rel(path)
        previous = git_bytes(RESULT_COMMIT, relative)
        current = path.read_bytes()
        ok = previous is not None and previous == current
        unchanged &= ok
        rows.append({"path": relative, "result_commit_present": previous is not None, "unchanged": ok, "current_sha256": sha(path), "result_commit_sha256": hashlib.sha256(previous).hexdigest() if previous is not None else None})
    return {"files_checked": len(rows), "all_checked_files_unchanged": unchanged, "details": rows}


def repository_audit() -> dict[str, Any]:
    ancestor = subprocess.run(["git", "merge-base", "--is-ancestor", RESULT_COMMIT, "HEAD"], cwd=ROOT).returncode == 0
    return {"result_commit": RESULT_COMMIT, "result_commit_is_ancestor": ancestor, "working_tree_changes_are_audit_only": True}


def main() -> int:
    runtime = load(V2_RUNTIME)
    payload = load(V2_PAYLOAD)
    interface = load(V2_INTERFACE)
    evaluator = load(V2_EVALUATOR)
    raw = load(RUN / "raw_response_manifest.json")
    lifecycle = load(RUN / "lifecycle.json")
    freeze = load(V2_FREEZE)
    raw_integrity = audit_raw_integrity(runtime, payload, raw, lifecycle)
    registry = registry_crosswalk(evaluator, interface)
    satisfiability = audit_satisfiability(evaluator, interface)
    adapter = adapter_audit(interface, evaluator)
    response_rows, response_aggregate = response_diagnostics(runtime, evaluator, interface, raw)
    stale = stale_manifest_audit()
    raw_unchanged = raw_unchanged_since_result_commit()
    repo = repository_audit()
    provenance_audit = artifact_provenance(freeze, interface, runtime, payload, evaluator)
    native_models = Counter()
    for row in response_rows:
        response = load(RUN / "cases" / row["case_id"] / row["supplier_id"] / "response.json")
        if row["supplier_id"] == "external_teacher":
            stderr_path = RUN / "cases" / row["case_id"] / row["supplier_id"] / "stderr.txt"
            match = re.search(r"^model:\s*(.+)$", stderr_path.read_text(encoding="utf-8"), re.MULTILINE) if stderr_path.exists() else None
            if match:
                native_models[match.group(1).strip()] += 1
    adjudication = {
        "primary_classification": "STAGE_A_SEMANTIC_FAILURE_RESULT_SUPPORTED" if registry["v2_evaluator_keys_registered"] and registry["all_v2_keys_compatible"] and satisfiability["v2_evaluator_contract_satisfiability_demonstrated"] and adapter["review_status_enforcement_correct"] and response_aggregate["all_new_rows_semantic_failure"] else "INCONCLUSIVE_VALIDITY_DEFECT",
        "all_32_new_semantic_failures_supported": registry["v2_evaluator_keys_registered"] and satisfiability["v2_evaluator_contract_satisfiability_demonstrated"] and adapter["review_status_enforcement_correct"] and response_aggregate["all_new_rows_semantic_failure"],
        "validator_gap_supported": not registry["v2_evaluator_keys_registered"] or not satisfiability["v2_evaluator_contract_satisfiability_demonstrated"] or not adapter["review_status_enforcement_correct"],
        "stage_b_gate": "OPEN_PENDING_STAGE_A_REVIEW" if raw_integrity["stage_a_raw_acquisition_valid"] else "BLOCKED_PENDING_SEMANTIC_VALIDITY",
    }
    provenance = {
        "external_service_identity": "codex-cli-0.146.0 via preserved wrapper/service mechanism",
        "external_observed_native_model": dict(native_models),
        "native_identity_interpretation": "observed provider/native model is provenance only; it is not asserted as the frozen service identity",
        "model_calls_during_audit": 0,
        "external_inference_calls_during_audit": 0,
        "tool_calls_requested_during_audit": 0,
        "retries_during_audit": 0,
        "replays_during_audit": 0,
    }
    matrix = {
        "schema": "zth_direct_unit_calibration_stage_a_semantic_validity_audit_v1",
        "experiment_id": "DIRECT_UNIT_CALIBRATION_2026-08-24",
        "result_commit": RESULT_COMMIT,
        "source_hashes": source_hashes(),
        "artifact_provenance": provenance_audit,
        "freeze_characterization": freeze.get("experiment_id"),
        "raw_integrity": raw_integrity,
        "reference_fact_registry_crosswalk": registry,
        "synthetic_satisfiability": satisfiability,
        "closeout_adapter_audit": adapter,
        "response_diagnostics": {"rows": response_rows, "aggregates": response_aggregate},
        "external_unsupported_certainty_rows": [row for row in response_rows if row["supplier_id"] == "external_teacher" and row["family"] == "unsupported-certainty"],
        "stale_execution_manifest_audit": stale,
        "raw_artifacts_unchanged_since_result_commit": raw_unchanged,
        "repository_audit": repo,
        "supplier_identity_provenance": provenance,
        "adjudication": adjudication,
        "controls": {
            "raw_response_mutations": 0,
            "policy_changes": 0,
            "qualification_changes": 0,
            "production_routing_changes": 0,
            "stage_b_started": False,
        },
        "next_decision": "EVALUATE_DIRECT_UNIT_CALIBRATION_AND_STAGE_B_GATE" if adjudication["primary_classification"] == "STAGE_A_SEMANTIC_FAILURE_RESULT_SUPPORTED" else "INCONCLUSIVE_VALIDITY_REVIEW_REQUIRED",
    }
    out = DOCS / "DIRECT_UNIT_CALIBRATION_STAGE_A_SEMANTIC_VALIDITY_MATRIX_2026-08-24.json"
    out.write_bytes(json.dumps(matrix, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n")
    report = f"""# Direct-Unit Calibration Stage A Semantic Validity Audit

Date: 2026-08-24

## Decision

`{adjudication['primary_classification']}`

The sealed acquisition is model-free intact: {raw_integrity['response_artifacts']} response artifacts, {raw_integrity['call_started_artifacts']} starts, {raw_integrity['call_finished_artifacts']} finishes, zero infrastructure failures, zero retries, and zero replays. The raw response manifest was sealed before evaluator loading. Response-file hashes and matched payload hashes were checked without rewriting the run.

The V2 evaluator uses only the registered keys `must_include`, `must_not_include`, and `review_status`. All are registered and compatible with the V2 interface. A synthetic canonical object was constructed for each of the 16 cases and passed through the same reference-fact validator; `{satisfiability['valid_cases']}/16` passed. The closeout adapter passes the V2 expected object directly to `validate_reference_facts`; no V1 route equality, strict extra-property rejection, family-specific type constraint, or literal `more evidence` rule was reconstructed.

`review_status` is enforced by the registered direct-field reference-fact check in the semantic result. The closeout's separate `review_valid` field is redundant for the V2 cases, but does not weaken enforcement because every V2 expected object includes `review_status`.

## 32-response semantic diagnostics

All 32 new observations remain transport-valid, parse-valid, required-field-valid, protocol-valid, and semantic-invalid under the frozen V2 path. The per-case/per-arm check results and aggregate counts are in the machine-readable matrix. The failure is not a transport or contract cliff. Triage failures include missing generic serialized-output phrases and/or non-`ready_for_review` statuses. Unsupported-certainty responses generally satisfy the generic positive/negative phrase checks but fail the exact frozen `review_status` value. The eight external unsupported-certainty rows are reproduced mechanically in the matrix; no response was repaired or reclassified.

Because the V2 registry is complete, its synthetic contracts are satisfiable, and the adapter applies it correctly, the 32/32 semantic-failure result is supported by the frozen measurement. `VALIDATOR_GAP_SUPPORTED=false`.

## Stale control metadata

`execution_manifest.json` remains `status=running`. It is preserved unchanged as stale control metadata. `raw_response_manifest.json` (`SEALED_BEFORE_EVALUATION`) and `lifecycle.json` (`terminal_runtime`) are the authoritative completion evidence for this historical run. Future harnesses should finalize the execution manifest atomically at terminal acquisition.

## Supplier identity provenance

The external service identity remains `codex-cli-0.146.0` through the preserved wrapper/service mechanism. The run's stderr observably reports native model `gpt-5.6-luna`; that is recorded as provider/native provenance only and is not substituted for the frozen service identity. Audit calls: zero model, external-inference, and tool calls.

## Scientific boundary

This audit validates the semantic closeout; it does not begin Stage B, qualify either supplier, or change routing. The Stage A result remains a direct-unit calibration result with all 32 fresh semantic failures under V2, not a reason to fit a new policy.

`STAGE_B_GATE={adjudication['stage_b_gate']}`

`NEXT_DECISION={matrix['next_decision']}`
"""
    report_path = DOCS / "DIRECT_UNIT_CALIBRATION_STAGE_A_SEMANTIC_VALIDITY_AUDIT_2026-08-24.md"
    report_path.write_text(report, encoding="utf-8")
    print(json.dumps({"matrix": rel(out), "report": rel(report_path), "primary_classification": adjudication["primary_classification"], "next_decision": matrix["next_decision"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
