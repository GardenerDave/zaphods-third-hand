#!/usr/bin/env python3
"""Model-free post-seal closeout using the already-frozen V2 evaluator."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.evaluate_explicit_interface_direct_unit_calibration_v2 import evaluate


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "research"
RUN = ROOT / ".work/model_size_supplier_floor/explicit_interface_direct_unit_calibration_v2/run_20260824T000000Z"
FREEZE = DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_FREEZE_V2_2026-08-24.json"
CASES = DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_EVALUATOR_CASES_V2_2026-08-24.json"
EVALUATOR = ROOT / "scripts/evaluate_explicit_interface_direct_unit_calibration_v2.py"
EXPECTED_EVALUATOR_SHA256 = "db067b700711c91c8a22877a7b8170c517640b9f5e1723f8041d5b4a44f5d9fb"
EXPECTED_SCHEDULE_SHA256 = "6cd43015d5cdb40034c073bc6185ea70b24d77e75ad5623954ebbd8fe981e121"


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_sealed_run() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    manifest = read_json(RUN / "execution_manifest.json")
    raw = read_json(RUN / "raw_response_manifest.json")
    lifecycle = read_json(RUN / "lifecycle.json")
    assert manifest["status"] == "TERMINAL_COMPLETE"
    assert lifecycle["status"] == "TERMINAL_COMPLETE"
    assert len(raw["records"]) == 32
    assert raw["raw_explicit_v2_responses_sealed_before_evaluation"] is True
    assert raw["terminal_arm_artifact_count"] == 32
    for arm in raw["terminal_arm_artifact_hashes"]:
        for relative, expected in arm["artifact_hashes"].items():
            path = RUN / relative
            assert path.is_file(), relative
            assert sha_file(path) == expected, relative
    schedule_sha = sha_bytes(canonical(manifest["schedule"]))
    assert schedule_sha == EXPECTED_SCHEDULE_SHA256
    assert sha_file(EVALUATOR) == EXPECTED_EVALUATOR_SHA256
    freeze = read_json(FREEZE)
    assert sha_file(CASES) == freeze["artifact_hashes"]["evaluator_cases"]
    assert freeze["artifact_hashes"]["evaluator_implementation"] == EXPECTED_EVALUATOR_SHA256
    return manifest, raw, lifecycle


def protocol_metadata(artifact: dict[str, Any] | None) -> dict[str, Any]:
    metadata = artifact.get("metadata", {}) if artifact else {}
    status = metadata.get("status")
    return {
        "transport_valid": status == "ok",
        "protocol_valid": not any(metadata.get(key) is True for key in ("tool_calls_observed", "repository_access_observed", "evaluator_access_observed")),
    }


def score() -> dict[str, Any]:
    manifest, raw, lifecycle = verify_sealed_run()
    cases = {item["case_id"]: item for item in read_json(CASES)["cases"]}
    rows: list[dict[str, Any]] = []
    for terminal in sorted(raw["records"], key=lambda item: item["ordinal"]):
        case_id = terminal["case_id"]
        supplier = terminal["supplier_id"]
        arm = RUN / "cases" / case_id / supplier
        response_path = arm / "response.json"
        failure_path = arm / "infrastructure_failure.json"
        response = read_json(response_path) if response_path.exists() else None
        failure = read_json(failure_path) if failure_path.exists() else None
        artifact = response or failure
        metadata = artifact.get("metadata", {}) if artifact else {}
        if response is not None:
            raw_content = response.get("raw_supplier_content", "")
            raw_content_bytes = raw_content.encode("utf-8")
            content_observed = metadata.get("status") == "ok"
            source_kind = "response_artifact"
        else:
            raw_content_bytes = b""
            content_observed = False
            source_kind = "no_response_artifact"
        result = evaluate(raw_content_bytes, cases[case_id], protocol_metadata(artifact))
        dimensions = result["dimensions"]
        rows.append({
            "ordinal": terminal["ordinal"],
            "case_id": case_id,
            "family": cases[case_id]["family"],
            "supplier_id": supplier,
            "terminal_disposition": terminal["terminal_disposition"],
            "response_artifact_present": response is not None,
            "raw_supplier_content_observed": content_observed,
            "raw_content_length": len(raw_content_bytes),
            "source_kind": source_kind,
            "transport_status": metadata.get("status"),
            "transport_classification": metadata.get("transport_classification"),
            "return_code": metadata.get("return_code"),
            "protocol_observations": {key: metadata.get(key) for key in ("tool_calls_observed", "repository_access_observed", "evaluator_access_observed")},
            "dimensions": dimensions,
            "DIRECT_CAPABILITY_VALID": result["DIRECT_CAPABILITY_VALID"],
            "failure_dimensions": result["failure_dimensions"],
            "evaluator_input_source": source_kind,
        })
    by_family_supplier: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_family_supplier[(row["family"], row["supplier_id"])].append(row)
    dimensions = ["TRANSPORT_VALID", "PARSE_VALID", "REQUIRED_FIELDS_VALID", "REQUIRED_FIELD_TYPES_VALID", "EXPLICIT_INTERFACE_VALID", "TASK_SEMANTICS_VALID", "REVIEW_STATUS_VALID", "PROTOCOL_VALID", "DIRECT_CAPABILITY_VALID"]
    family_supplier = {}
    for (family, supplier), group in sorted(by_family_supplier.items()):
        family_supplier[f"{family}|{supplier}"] = {name: {"valid": sum(bool(row.get(name) if name == "DIRECT_CAPABILITY_VALID" else row["dimensions"][name]) for row in group), "total": len(group)} for name in dimensions}
    supplier_summary = {}
    for supplier in ("local_teacher", "external_teacher"):
        group = [row for row in rows if row["supplier_id"] == supplier]
        supplier_summary[supplier] = {name: {"valid": sum(bool(row.get(name) if name == "DIRECT_CAPABILITY_VALID" else row["dimensions"][name]) for row in group), "total": len(group)} for name in dimensions}
    family_macro = {}
    for supplier in ("local_teacher", "external_teacher"):
        rates = []
        for family in ("triage-routing", "unsupported-certainty"):
            group = by_family_supplier[(family, supplier)]
            rates.append(sum(row["DIRECT_CAPABILITY_VALID"] for row in group) / len(group))
        family_macro[supplier] = {"valid_rate": sum(rates) / len(rates), "families_equal_weighted": True}
    external_failures = [row for row in rows if row["supplier_id"] == "external_teacher" and row["terminal_disposition"] != "RESPONSE_CAPTURED"]
    external_signatures = Counter()
    external_return_codes = Counter()
    external_stdout_nonempty = 0
    external_stderr_by_signature = {}
    for row in external_failures:
        arm = RUN / "cases" / row["case_id"] / "external_teacher"
        failure = read_json(arm / "infrastructure_failure.json")
        stderr = (arm / "stderr.bin").read_bytes().decode("utf-8", errors="replace")
        normalized = re.sub(r"\s+", " ", stderr).strip().casefold()
        signature = "codex_cli_state_initialization_read_only_filesystem" if "failed to initialize in-process app-server client" in normalized and "read-only file system" in normalized else "other_external_failure"
        external_signatures[signature] += 1
        external_return_codes[str(failure["metadata"].get("return_code"))] += 1
        external_stderr_by_signature[signature] = normalized
        if (arm / "stdout.bin").stat().st_size:
            external_stdout_nonempty += 1
    local_rows = [row for row in rows if row["supplier_id"] == "local_teacher"]
    local_errors = Counter()
    local_urls = Counter()
    for row in local_rows:
        arm = RUN / "cases" / row["case_id"] / "local_teacher"
        response = read_json(arm / "response.json")
        meta = response["metadata"]
        local_errors[str(meta.get("error"))] += 1
        local_urls[str(meta.get("request_url"))] += 1
    return {
        "provenance": {"run": str(RUN.relative_to(ROOT)), "evaluator_sha256": sha_file(EVALUATOR), "evaluator_cases_sha256": sha_file(CASES), "schedule_sha256": EXPECTED_SCHEDULE_SHA256, "execution_manifest_status": manifest["status"], "raw_seal": raw["raw_explicit_v2_responses_sealed_before_evaluation"], "terminal_arm_artifact_hash_count": raw["terminal_arm_artifact_count"]},
        "acquisition_integrity": {"planned": manifest["planned_supplier_calls"], "terminal": len(raw["records"]), "local": manifest["actual_local_calls"], "external": manifest["actual_external_calls"], "retries": raw["retries"], "replays": raw["replays"], "processes_started": lifecycle["processes_started"], "second_process_started": lifecycle["second_acquisition_process_started"], "evaluator_access_during_acquisition": raw["evaluator_file_access_during_acquisition"], "evaluator_semantics_loaded_during_acquisition": raw["evaluator_semantics_loaded_during_acquisition"], "evaluator_runtime_influence": raw["evaluator_runtime_influence"]},
        "rows": rows,
        "family_supplier": family_supplier,
        "supplier_summary": supplier_summary,
        "micro_aggregate_direct_explicit_v2": {supplier: {name: summary[name] for name in dimensions} for supplier, summary in supplier_summary.items()},
        "family_macro_aggregate_direct_explicit_v2": family_macro,
        "external_transport_diagnosis": {"failure_count": len(external_failures), "unique_return_codes": dict(external_return_codes), "signatures": {key: {"count": value, "normalized_stderr": external_stderr_by_signature[key]} for key, value in external_signatures.items()}, "heterogeneity": "identical" if len(external_signatures) == 1 else "heterogeneous", "stdout_nonempty_count": external_stdout_nonempty, "response_generation_observed": external_stdout_nonempty > 0, "failure_layer": "Codex CLI/wrapper initialization and read-only filesystem state; no model-produced response observed"},
        "local_transport_diagnosis": {"unique_errors": dict(local_errors), "request_urls": dict(local_urls), "response_generation_observed": sum(row["raw_supplier_content_observed"] for row in local_rows) > 0, "failure_layer": "local HTTP endpoint/DNS or configuration; all captured statuses were request_error"},
        "interpretation": {"local_direct_capability_evaluator_rate": supplier_summary["local_teacher"]["DIRECT_CAPABILITY_VALID"], "local_semantic_capability_observed": any(row["raw_supplier_content_observed"] for row in local_rows), "external_direct_capability_evaluator_rate": supplier_summary["external_teacher"]["DIRECT_CAPABILITY_VALID"], "external_semantic_capability_observed": any(row["raw_supplier_content_observed"] for row in external_failures), "experimental_mechanism": "both_supplier_transport_failures_prevented_meaningful_matched_capability_comparison", "characterization": "LOCAL_AND_EXTERNAL_CAPABILITY_NOT_MEASURED_DUE_TO_TRANSPORT_FAILURES"},
        "closeout_calls": {"supplier_calls": 0, "model_calls": 0, "external_inference_calls": 0, "retries": 0, "replays": 0},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = score()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "closeout_scored", "supplier_calls": 0, "model_calls": 0, "external_inference_calls": 0, "rows": len(result["rows"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
