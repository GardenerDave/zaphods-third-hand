#!/usr/bin/env python3
"""Model-free closeout using the frozen Explicit-Interface V3 evaluator."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "research"
RUN = ROOT / ".work/model_size_supplier_floor/explicit_interface_direct_unit_calibration_v3/run_20260824T225000Z"
EVALUATOR = ROOT / "scripts/evaluate_explicit_interface_direct_unit_calibration_v3.py"
CASES = DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_EVALUATOR_CASES_V3_2026-08-24.json"
FREEZE = DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_FREEZE_V3_2026-08-24.json"
EXPECTED_EVALUATOR_SHA256 = "3922879d7c740531d65c0af06b1d9fb0a667357867736783d0ccd6ccd20d5eda"
EXPECTED_CASES_SHA256 = "91454cc877dcb27805fdc6288d1b7753bd079273babc7663cb334a79fe114698"
EXPECTED_SCHEDULE_SHA256 = "25d5107fdf23948a7419336e50386233be824a8d47574254c428699b5d2bbe61"
DIMENSIONS = ("TRANSPORT_VALID", "PARSE_VALID", "REQUIRED_FIELDS_VALID", "REQUIRED_FIELD_TYPES_VALID", "EXPLICIT_INTERFACE_VALID", "TASK_SEMANTICS_VALID", "REVIEW_STATUS_VALID", "PROHIBITED_ACTIONS_NOT_OBSERVED", "PROTOCOL_VALID", "DIRECT_CAPABILITY_VALID")


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_raw_integrity() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    execution = load(RUN / "execution_manifest.json")
    lifecycle = load(RUN / "lifecycle.json")
    raw = load(RUN / "raw_response_manifest.json")
    if lifecycle["status"] != "TERMINAL_COMPLETE" or execution["status"] != "TERMINAL_COMPLETE":
        raise RuntimeError("V3 acquisition is not terminally complete")
    if len(list(RUN.glob("cases/*/*/call_started.json"))) != 32 or len(list(RUN.glob("cases/*/*/call_finished.json"))) != 32:
        raise RuntimeError("V3 call artifact count mismatch")
    if len(list(RUN.glob("cases/*/*/response.json"))) != 32:
        raise RuntimeError("V3 response count mismatch")
    if list(RUN.glob("cases/*/*/infrastructure_failure.json")) or list(RUN.glob("cases/*/*/terminal_recording_failure.json")):
        raise RuntimeError("V3 contains infrastructure or recording failures")
    if raw["raw_explicit_v3_responses_sealed_before_evaluation"] is not True or raw["terminal_arm_artifact_count"] != 32:
        raise RuntimeError("V3 raw seal is not complete")
    if raw["retries"] != 0 or raw["replays"] != 0 or lifecycle["processes_started"] != 1 or execution["second_acquisition_process_started"] is not False:
        raise RuntimeError("V3 lifecycle controls mismatch")
    if execution["schedule_sha256"] != EXPECTED_SCHEDULE_SHA256 or hashlib.sha256(canonical(execution["schedule"])).hexdigest() != EXPECTED_SCHEDULE_SHA256:
        raise RuntimeError("V3 schedule hash mismatch")
    for arm in raw["terminal_arm_artifacts"]:
        for relative, expected in arm["artifact_hashes"].items():
            path = RUN / relative
            if not path.is_file() or sha_file(path) != expected:
                raise RuntimeError(f"terminal artifact hash mismatch: {relative}")
    freeze = load(FREEZE)
    for case_id in freeze["case_order"]:
        local = (RUN / "cases" / case_id / "local_teacher" / "supplier_message.txt").read_bytes()
        external = (RUN / "cases" / case_id / "external_teacher" / "supplier_message.txt").read_bytes()
        if local != external:
            raise RuntimeError(f"matched supplier message bytes differ: {case_id}")
    return execution, lifecycle, raw


def evaluate() -> dict[str, Any]:
    execution, lifecycle, raw = verify_raw_integrity()
    if sha_file(EVALUATOR) != EXPECTED_EVALUATOR_SHA256 or sha_file(CASES) != EXPECTED_CASES_SHA256:
        raise RuntimeError("frozen evaluator hash mismatch")
    # Scoring semantics are imported only after raw integrity and frozen hashes
    # have passed.
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.evaluate_explicit_interface_direct_unit_calibration_v3 import evaluate as frozen_evaluate
    cases = {case["case_id"]: case for case in load(CASES)["cases"]}
    rows: list[dict[str, Any]] = []
    for record in sorted(raw["records"], key=lambda item: item["ordinal"]):
        response_path = RUN / "cases" / record["case_id"] / record["supplier_id"] / "response.json"
        response = load(response_path)
        case = cases[record["case_id"]]
        result = frozen_evaluate(response["raw_supplier_content"], case, response["metadata"])
        dimensions = dict(result["dimensions"])
        dimensions["DIRECT_CAPABILITY_VALID"] = result["DIRECT_CAPABILITY_VALID"]
        rows.append({"ordinal": record["ordinal"], "case_id": record["case_id"], "supplier_id": record["supplier_id"], "family": case["family"], "raw_supplier_content_sha256": response["raw_supplier_content_sha256"], "dimensions": dimensions, "direct_capability_valid": result["DIRECT_CAPABILITY_VALID"], "failure_dimensions": result["failure_dimensions"]})

    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    supplier_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["family"], row["supplier_id"])].append(row)
        supplier_groups[row["supplier_id"]].append(row)

    def summary(items: list[dict[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {"n": len(items)}
        for dimension in DIMENSIONS:
            values = [item["dimensions"][dimension] for item in items]
            result[dimension] = {"valid": sum(values), "total": len(values), "rate": sum(values) / len(values) if values else None}
        return result

    group_summaries = {f"{family}|{supplier}": summary(items) for (family, supplier), items in sorted(groups.items())}
    supplier_summaries = {supplier: summary(items) for supplier, items in sorted(supplier_groups.items())}
    micro = {supplier: supplier_summaries[supplier]["DIRECT_CAPABILITY_VALID"] for supplier in supplier_summaries}
    family_macro = {}
    for supplier in supplier_groups:
        rates = [group_summaries[f"{family}|{supplier}"]["DIRECT_CAPABILITY_VALID"]["rate"] for family in ("triage-routing", "unsupported-certainty")]
        family_macro[supplier] = {"family_rates": dict(zip(("triage-routing", "unsupported-certainty"), rates)), "equal_weight_rate": mean(rates)}

    by_case: dict[str, dict[str, bool]] = defaultdict(dict)
    for row in rows:
        by_case[row["case_id"]][row["supplier_id"]] = row["direct_capability_valid"]
    pair_counts = Counter()
    pair_by_family = Counter()
    for case_id, values in by_case.items():
        state = ("both_pass" if values["local_teacher"] and values["external_teacher"] else "local_only" if values["local_teacher"] else "external_only" if values["external_teacher"] else "both_fail")
        family = next(row["family"] for row in rows if row["case_id"] == case_id)
        pair_counts[state] += 1
        pair_by_family[(family, state)] += 1

    failure_counts: dict[str, Any] = {"overall": Counter(), "by_supplier": defaultdict(Counter), "by_family": defaultdict(Counter), "by_supplier_family": defaultdict(Counter)}
    for row in rows:
        for dimension in row["failure_dimensions"]:
            failure_counts["overall"][dimension] += 1
            failure_counts["by_supplier"][row["supplier_id"]][dimension] += 1
            failure_counts["by_family"][row["family"]][dimension] += 1
            failure_counts["by_supplier_family"][(row["supplier_id"], row["family"])][dimension] += 1

    def counter_json(value: Any) -> dict[str, int]:
        return dict(sorted(value.items()))

    matrix = {"schema": "zth.explicit_interface_direct_unit_calibration.v3.results.matrix", "status": "closed_model_free", "provenance": {"execution_boundary_commit": "442ff0a875bc09135aeaf57193fa97f753c68115", "run": str(RUN.relative_to(ROOT)), "schedule_sha256": EXPECTED_SCHEDULE_SHA256, "execution_harness_sha256": "b51bb6458f2a1708928a3f9e657213ed622ed2e8332a652a5db54ea74e36299d", "evaluator_sha256": EXPECTED_EVALUATOR_SHA256, "evaluator_cases_sha256": EXPECTED_CASES_SHA256, "raw_seal": True, "response_count": 32, "transport_failures": 0, "retries": 0, "replays": 0}, "dimensions": list(DIMENSIONS), "rows": rows, "group_summaries": group_summaries, "supplier_summaries": supplier_summaries, "micro_aggregate_direct_explicit_v3": micro, "family_macro_aggregate_direct_explicit_v3": family_macro, "matched_pair_counts": dict(sorted(pair_counts.items())), "matched_pair_counts_by_family": {f"{family}|{state}": count for (family, state), count in sorted(pair_by_family.items())}, "failure_dimensions": {"overall": counter_json(failure_counts["overall"]), "by_supplier": {k: counter_json(v) for k, v in sorted(failure_counts["by_supplier"].items())}, "by_family": {k: counter_json(v) for k, v in sorted(failure_counts["by_family"].items())}, "by_supplier_family": {f"{k[0]}|{k[1]}": counter_json(v) for k, v in sorted(failure_counts["by_supplier_family"].items())}}, "interpretation_boundary": "V3 calibration cohort only; semantic capability was observable because all 32 transports produced captured responses; no population, general capability, routing superiority, or supplier qualification claim.", "evaluation_supplier_calls": 0, "evaluation_model_calls": 0, "evaluation_external_inference_calls": 0}
    return matrix


def main() -> int:
    # Explicit pre-evaluation integrity gate; evaluator import occurs inside evaluate().
    verify_raw_integrity()
    matrix = evaluate()
    out = DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_V3_RESULTS_MATRIX_2026-08-24.json"
    out.write_text(json.dumps(matrix, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "closeout_pass", "evaluation_supplier_calls": 0, "evaluation_model_calls": 0, "evaluation_external_inference_calls": 0, "micro": matrix["micro_aggregate_direct_explicit_v3"], "family_macro": matrix["family_macro_aggregate_direct_explicit_v3"], "matched_pairs": matrix["matched_pair_counts"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
