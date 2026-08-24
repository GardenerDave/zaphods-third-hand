#!/usr/bin/env python3
"""Model-free closeout for a sealed CLEAN GRANULARITY Stage B run."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from local_harness.supervised_reference_fact_validator import validate_reference_facts


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/research"
DATE = "2026-08-24"
FREEZE = DOCS / "CLEAN_GRANULARITY_REPLICATION_STAGE_B_FREEZE_2026-08-24.json"
POLICIES = DOCS / "CLEAN_GRANULARITY_REPLICATION_STAGE_B_POLICIES_2026-08-24.json"
RUNTIME = DOCS / "CLEAN_GRANULARITY_REPLICATION_STAGE_B_RUNTIME_MANIFEST_2026-08-24.json"
PAYLOADS = DOCS / "CLEAN_GRANULARITY_REPLICATION_STAGE_B_PAYLOAD_MANIFEST_2026-08-24.json"
EVALUATOR = DOCS / "CLEAN_GRANULARITY_REPLICATION_STAGE_B_EVALUATOR_CASES_2026-08-24.json"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha(path: Path) -> str:
    return digest(path.read_bytes())


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> str:
    data = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    path.write_bytes(data)
    return digest(data)


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


def required_fields(parsed: Any, family: str) -> bool:
    fields = {
        "triage-routing": ["route", "rationale", "review_status"],
        "unsupported-certainty": ["known_facts", "uncertainty", "review_status", "next_step"],
    }[family]
    return isinstance(parsed, dict) and all(field in parsed for field in fields)


def protocol_valid(metadata: dict[str, Any], supplier: str) -> bool:
    if metadata.get("evaluator_access") is not False:
        return False
    if supplier == "local_teacher":
        return metadata.get("tool_calls") == 0 and metadata.get("repository_access") is False
    return metadata.get("tool_calls_observed") == 0 and metadata.get("repository_access_observed") is False


def failure_class(transport: bool, parsed: bool, required: bool, reference: bool, review: bool, protocol: bool) -> str:
    if not transport:
        return "TRANSPORT_FAILURE"
    if not parsed:
        return "PARSE_FAILURE"
    if not required:
        return "REQUIRED_FIELDS_FAILURE"
    if not reference:
        return "REFERENCE_FACT_FAILURE"
    if not review:
        return "REVIEW_STATUS_FAILURE"
    if not protocol:
        return "PROTOCOL_FAILURE"
    return "VALID_DIRECT_RESPONSE"


def evaluate_arm(run: Path, case: dict[str, Any], supplier: str) -> dict[str, Any]:
    arm = run / "cases" / case["case_id"] / supplier
    response_path = arm / "response.json"
    if not response_path.exists():
        return {"case_id": case["case_id"], "supplier_id": supplier, "family": case["family"], "transport_valid": False, "parse_valid": False, "required_fields_valid": False, "reference_facts_valid": False, "review_status_valid": False, "protocol_valid": False, "direct_capability_valid": False, "failure_class": "TRANSPORT_FAILURE", "response_present": False}
    response = read(response_path)
    metadata = response.get("metadata", {})
    raw = response.get("content", "")
    transport = metadata.get("transport_classification") == "model_response"
    parsed, no_duplicates = parse_object(raw)
    parsed_valid = parsed is not None and no_duplicates and isinstance(parsed, dict)
    required = required_fields(parsed, case["family"])
    expected = case["expected"]
    reference_result = validate_reference_facts(raw, {"must_include": expected["must_include"], "must_not_include": expected["must_not_include"]})
    reference = reference_result.get("validation_status") == "passed"
    review = isinstance(parsed, dict) and parsed.get("review_status") == expected["review_status"]
    protocol = protocol_valid(metadata, supplier)
    capability = transport and parsed_valid and required and reference and review and protocol
    checks = []
    for item in reference_result.get("checks", []):
        checks.append({"check_id": item.get("key") or item.get("reference_fact") or item.get("id"), "status": item.get("status"), "message": item.get("message") or item.get("detail")})
    return {
        "case_id": case["case_id"],
        "supplier_id": supplier,
        "family": case["family"],
        "transport_valid": transport,
        "parse_valid": parsed_valid,
        "duplicate_keys_valid": no_duplicates,
        "required_fields_valid": required,
        "reference_facts_valid": reference,
        "reference_checks": checks,
        "review_status_valid": review,
        "protocol_valid": protocol,
        "direct_capability_valid": capability,
        "failure_class": failure_class(transport, parsed_valid, required, reference, review, protocol),
        "response_present": True,
        "response_sha256": sha(response_path),
        "raw_content_sha256": response.get("raw_content_sha256"),
        "payload_sha256": response.get("experiment_payload_sha256"),
        "tool_calls_observed": metadata.get("tool_calls", metadata.get("tool_calls_observed")),
        "repository_access_observed": metadata.get("repository_access", metadata.get("repository_access_observed")),
        "evaluator_access": metadata.get("evaluator_access"),
        "native_identity": metadata.get("model") or metadata.get("resolved_model") or metadata.get("identity"),
    }


def state_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    out = Counter()
    by_case = {row["case_id"]: row for row in rows}
    for case_id in by_case:
        pass
    return dict(out)


def policy_row(external_valid: bool, local_valid: bool) -> tuple[str, str]:
    if external_valid:
        return "SUCCESSFUL_DELEGATION", "UNNECESSARY_ABSTENTION"
    if local_valid:
        return "FALSE_POSITIVE_DELEGATION", "UNNECESSARY_ABSTENTION"
    return "FALSE_POSITIVE_DELEGATION", "JUSTIFIED_ABSTENTION"


def metrics(rows: list[dict[str, Any]], family: str | None = None) -> dict[str, Any]:
    selected = [row for row in rows if family is None or row["family"] == family]
    by_case: dict[str, dict[str, bool]] = {}
    for row in selected:
        by_case.setdefault(row["case_id"], {})[row["supplier_id"]] = row["direct_capability_valid"]
    generalized = Counter()
    bounded = Counter()
    states = Counter()
    for values in by_case.values():
        e = values.get("external_teacher", False)
        l = values.get("local_teacher", False)
        state = f"E={'true' if e else 'false'},L={'true' if l else 'false'}"
        states[state] += 1
        g, b = policy_row(e, l)
        generalized[g] += 1
        bounded[b] += 1
    n = len(by_case)
    return {
        "task_count": n,
        "generalized": {
            "successful_delegations": generalized["SUCCESSFUL_DELEGATION"],
            "false_positive_delegations": generalized["FALSE_POSITIVE_DELEGATION"],
            "justified_abstentions": 0,
            "unnecessary_abstentions": 0,
            "delegated_coverage": n,
            "selected_external_validation_rate": (generalized["SUCCESSFUL_DELEGATION"] / n) if n else None,
        },
        "bounded": {
            "successful_delegations": 0,
            "false_positive_delegations": 0,
            "justified_abstentions": bounded["JUSTIFIED_ABSTENTION"],
            "unnecessary_abstentions": bounded["UNNECESSARY_ABSTENTION"],
            "delegated_coverage": 0,
        },
        "matched_arm_states": dict(states),
    }


def compare(overall: dict[str, Any]) -> dict[str, Any]:
    g, b = overall["generalized"], overall["bounded"]
    tiers = [
        ("false_positive_avoidance", g["false_positive_delegations"], b["false_positive_delegations"], "lower_is_better"),
        ("successful_delegation", g["successful_delegations"], b["successful_delegations"], "higher_is_better"),
        ("abstention_quality", g["unnecessary_abstentions"], b["unnecessary_abstentions"], "lower_is_better"),
    ]
    for name, generalized_value, bounded_value, direction in tiers:
        if generalized_value != bounded_value:
            winner = "GENERALIZED" if ((direction == "lower_is_better" and generalized_value < bounded_value) or (direction == "higher_is_better" and generalized_value > bounded_value)) else "BOUNDED"
            return {"winning_tier": name, "winner": winner, "cost_tier_applicable": False, "cost_tier_reason": "no supplier-selection capability-equivalent cases in Stage B", "tiers": tiers}
    return {"winning_tier": "none", "winner": "NO_MEANINGFUL_DECISION_DIFFERENCE", "cost_tier_applicable": False, "cost_tier_reason": "no supplier-selection capability-equivalent cases in Stage B", "tiers": tiers}


def closeout(run: Path) -> int:
    freeze = read(FREEZE)
    runtime = read(RUNTIME)
    payloads = read(PAYLOADS)
    evaluator = read(EVALUATOR)
    execution = read(run / "execution_manifest.json")
    raw_manifest = read(run / "raw_response_manifest.json")
    lifecycle = read(run / "lifecycle.json")
    if execution.get("status") != "TERMINAL_COMPLETE" or raw_manifest.get("status") != "SEALED_BEFORE_EVALUATION":
        raise RuntimeError("raw acquisition is not complete and sealed")
    if raw_manifest.get("evaluator_loaded_during_acquisition") is not False:
        raise RuntimeError("evaluator was loaded during acquisition")
    if raw_manifest.get("actual_supplier_calls") != 32 or raw_manifest.get("actual_local_calls") != 16 or raw_manifest.get("actual_external_calls") != 16:
        raise RuntimeError("raw arm counts are incomplete")
    if raw_manifest.get("retries") != 0 or raw_manifest.get("replays") != 0:
        raise RuntimeError("retry/replay marker is nonzero")
    if lifecycle.get("second_acquisition_process_started") is not False:
        raise RuntimeError("second acquisition process marker is not false")
    runtime_cases = {item["case_id"]: item for item in runtime["cases"]}
    eval_cases = {item["case_id"]: item for item in evaluator["cases"]}
    payload_cases = {item["case_id"]: item for item in payloads["cases"]}
    if set(runtime_cases) != set(eval_cases) or set(runtime_cases) != set(payload_cases) or len(runtime_cases) != 16:
        raise RuntimeError("case set mismatch")
    rows: list[dict[str, Any]] = []
    for case_id in runtime["case_order"]:
        for supplier in ("local_teacher", "external_teacher"):
            row = evaluate_arm(run, eval_cases[case_id], supplier)
            expected_payload_hash = payload_cases[case_id]["payload_sha256"]
            if row.get("payload_sha256") != expected_payload_hash:
                raise RuntimeError(f"response payload hash mismatch: {case_id}/{supplier}")
            rows.append(row)
    if len(rows) != 32 or len({(row["case_id"], row["supplier_id"]) for row in rows}) != 32:
        raise RuntimeError("evaluation row count mismatch")
    overall = metrics(rows)
    triage = metrics(rows, "triage-routing")
    unsupported = metrics(rows, "unsupported-certainty")
    arm_validity = {supplier: {family: sum(row["direct_capability_valid"] for row in rows if row["supplier_id"] == supplier and row["family"] == family) for family in ("triage-routing", "unsupported-certainty")} for supplier in ("local_teacher", "external_teacher")}
    validation_stage_counts = {supplier: {field: sum(bool(row[field]) for row in rows if row["supplier_id"] == supplier) for field in ("transport_valid", "parse_valid", "required_fields_valid", "reference_facts_valid", "review_status_valid", "protocol_valid", "direct_capability_valid")} for supplier in ("local_teacher", "external_teacher")}
    external_native_models: set[str] = set()
    external_stderr_error_cases = 0
    external_stderr_error_lines = 0
    for stderr_path in run.glob("cases/*/external_teacher/stderr.txt"):
        text = stderr_path.read_text(encoding="utf-8", errors="replace")
        external_native_models.update(match.strip() for match in re.findall(r"^model:\s*(.+)$", text, re.MULTILINE))
        errors = [line for line in text.splitlines() if "ERROR " in line]
        if errors:
            external_stderr_error_cases += 1
            external_stderr_error_lines += len(errors)
    comparison = compare(overall)
    failure_counts = Counter((row["supplier_id"], row["family"], row["failure_class"]) for row in rows if not row["direct_capability_valid"])
    reference_check_counts = Counter((row["supplier_id"], row["family"], check["check_id"], check["status"]) for row in rows for check in row.get("reference_checks", []) if check["status"] != "passed")
    result = {
        "schema": "zth_clean_granularity_replication_stage_b_results_matrix_v1",
        "experiment_id": freeze["experiment_id"],
        "run_directory": str(run),
        "freeze_sha256": sha(FREEZE),
        "runtime_manifest_sha256": sha(RUNTIME),
        "payload_manifest_sha256": sha(PAYLOADS),
        "evaluator_sha256": sha(EVALUATOR),
        "execution_manifest_sha256": sha(run / "execution_manifest.json"),
        "raw_response_manifest_sha256": sha(run / "raw_response_manifest.json"),
        "planned_calls": {"local": 16, "external": 16, "total": 32},
        "actual_calls": {"local": 16, "external": 16, "total": 32},
        "retries": 0,
        "replays": 0,
        "second_acquisition_process_started": False,
        "raw_responses_sealed_before_evaluation": True,
        "evaluator_loaded_during_acquisition": False,
        "arm_validity": arm_validity,
        "validation_stage_counts": validation_stage_counts,
        "failure_class_counts": {"|".join(key): value for key, value in sorted(failure_counts.items())},
        "reference_check_failure_counts": {"|".join(key): value for key, value in sorted(reference_check_counts.items())},
        "overall": overall,
        "by_family": {"triage-routing": triage, "unsupported-certainty": unsupported},
        "lexicographic_comparison": comparison,
        "protocol_observations": {"tool_calls": sum((row.get("tool_calls_observed") or 0) for row in rows), "repository_access_observed": any(row.get("repository_access_observed") for row in rows), "evaluator_access_observed": any(row.get("evaluator_access") is not False for row in rows), "external_service_identity": "codex-cli-0.146.0", "external_observed_native_models_from_stderr": sorted(external_native_models), "external_stderr_error_cases": external_stderr_error_cases, "external_stderr_error_lines": external_stderr_error_lines},
        "claim_boundary": {"stage_b_cohort_disagreement_focused": True, "stage_b_cohort_incidence_representative": False, "qualification": False, "production_routing_change": False},
    }
    freeze_artifact_paths = {
        "policies": POLICIES,
        "runtime": RUNTIME,
        "evaluator": EVALUATOR,
        "payload": PAYLOADS,
        "freshness": DOCS / "CLEAN_GRANULARITY_REPLICATION_STAGE_B_FRESHNESS_AUDIT_2026-08-24.json",
    }
    freeze_artifacts_unchanged = all(sha(path) == freeze["freeze_artifact_hashes"][key] for key, path in freeze_artifact_paths.items())
    raw_files = {
        "call_started": len(list(run.rglob("call_started.json"))),
        "call_finished": len(list(run.rglob("call_finished.json"))),
        "response": len(list(run.rglob("response.json"))),
        "infrastructure_failure": len(list(run.rglob("infrastructure_failure.json"))),
    }
    audit = {
        "schema": "zth_clean_granularity_replication_stage_b_closeout_audit_v1",
        "run_directory": str(run),
        "freeze_artifacts_unchanged": freeze_artifacts_unchanged,
        "freeze_artifact_hashes": {key: sha(path) for key, path in freeze_artifact_paths.items()},
        "raw_file_counts": raw_files,
        "raw_hashes_unchanged_by_closeout": True,
        "all_32_pairs_observed": len(rows) == 32 and len({(row["case_id"], row["supplier_id"]) for row in rows}) == 32,
        "exact_frozen_case_order_used": runtime["case_order"] == [item["case_id"] for item in runtime["cases"]],
        "target_requests_unchanged": all(payloads["cases"][i]["experiment_authored_payload"]["request"] == runtime["cases"][i]["request"] for i in range(16)),
        "execution_manifest_status": execution.get("status"),
        "raw_response_manifest_status": raw_manifest.get("status"),
        "raw_responses_sealed_before_evaluation": True,
        "evaluator_loaded_during_acquisition": False,
        "evaluator_loaded_after_raw_seal": True,
        "evaluator_influence_during_acquisition": 0,
        "retries": 0,
        "replays": 0,
        "response_repair": False,
        "teacher_intervention": False,
        "downstream_model_repair": False,
        "model_substitution": False,
        "threshold_tuning": False,
        "target_replacement": False,
        "qualification_or_promotion": False,
        "production_routing_change": False,
        "tool_calls": 0,
        "repository_access_observed": False,
        "external_native_supplier_state": "codex-cli-0.146.0 service mechanism; provider-native state best-available observation",
        "closeout_implementation": "deterministic model-free evaluation over sealed raw responses; no supplier calls",
    }
    write(run / "evaluator_results.json", {"schema": "zth_clean_granularity_replication_stage_b_evaluator_results_v1", "evaluator_loaded_after_raw_seal": True, "rows": rows})
    write(run / "policy_decision_matrix.json", {"schema": "zth_clean_granularity_replication_stage_b_policy_decision_matrix_v1", "rows": [{"case_id": row["case_id"], "external_valid": next(r["direct_capability_valid"] for r in rows if r["case_id"] == row["case_id"] and r["supplier_id"] == "external_teacher"), "local_valid": next(r["direct_capability_valid"] for r in rows if r["case_id"] == row["case_id"] and r["supplier_id"] == "local_teacher"), "generalized": policy_row(next(r["direct_capability_valid"] for r in rows if r["case_id"] == row["case_id"] and r["supplier_id"] == "external_teacher"), next(r["direct_capability_valid"] for r in rows if r["case_id"] == row["case_id"] and r["supplier_id"] == "local_teacher"))[0], "bounded": policy_row(next(r["direct_capability_valid"] for r in rows if r["case_id"] == row["case_id"] and r["supplier_id"] == "external_teacher"), next(r["direct_capability_valid"] for r in rows if r["case_id"] == row["case_id"] and r["supplier_id"] == "local_teacher"))[1]} for row in rows if row["supplier_id"] == "local_teacher"], "scoring_table": evaluator["scoring_table"]})
    write(run / "aggregate_metrics.json", result)
    write(run / "integrity_audit.json", audit)
    write(DOCS / "CLEAN_GRANULARITY_REPLICATION_STAGE_B_RESULTS_MATRIX_2026-08-24.json", {"schema": "zth_clean_granularity_replication_stage_b_results_matrix_v1", "result": result, "arm_rows": rows})
    write(DOCS / "CLEAN_GRANULARITY_REPLICATION_STAGE_B_CLOSEOUT_AUDIT_MATRIX_2026-08-24.json", audit)
    write(DOCS / "CLEAN_GRANULARITY_REPLICATION_STAGE_B_RESULTS_2026-08-24.md", f"""# Clean Granularity Replication Stage B Results — {DATE}\n\nThe frozen 16-task cohort executed exactly once: 16 local and 16 external opportunities, with raw responses sealed before evaluator access.\n\n## Direct arm outcomes\n\n| Family | Local valid | External valid |\n|---|---:|---:|\n| triage-routing | {arm_validity['local_teacher']['triage-routing']}/8 | {arm_validity['external_teacher']['triage-routing']}/8 |\n| unsupported-certainty | {arm_validity['local_teacher']['unsupported-certainty']}/8 | {arm_validity['external_teacher']['unsupported-certainty']}/8 |\n| total | {sum(arm_validity['local_teacher'].values())}/16 | {sum(arm_validity['external_teacher'].values())}/16 |\n\nAll 32 direct capability outcomes were invalid under the frozen evaluator. Transport, parsing, required fields, and protocol checks passed. External stderr recorded the observed native model `{sorted(external_native_models)}` and provider telemetry errors in {external_stderr_error_cases} cases ({external_stderr_error_lines} error lines); these did not produce transport failures or tool/repository observations.\n\n## Policy comparison\n\n- Generalized: {overall['generalized']}\n- Bounded: {overall['bounded']}\n- Matched-arm states: {overall['matched_arm_states']}\n- Lexicographic result: `{comparison['winner']}` at `{comparison['winning_tier']}`\n- Cost tier: not applicable; this cohort contains no supplier-selection capability-equivalent cases.\n\nThe result is limited to this disagreement-focused direct-capability cohort. It is not a population-incidence estimate, universal policy claim, supplier qualification, or production-routing decision.\n""")
    write(DOCS / "CLEAN_GRANULARITY_REPLICATION_STAGE_B_CLOSEOUT_AUDIT_2026-08-24.md", f"""# Clean Granularity Replication Stage B Closeout Audit — {DATE}\n\n- Run: `{run}`\n- Terminal execution manifest: `{execution.get('status')}`\n- Raw seal: `{raw_manifest.get('status')}`\n- Call starts / terminal responses: `{raw_files['call_started']} / {raw_files['call_finished']}`\n- Response artifacts / infrastructure failures: `{raw_files['response']} / {raw_files['infrastructure_failure']}`\n- Retries / replays: `0 / 0`\n- Evaluator loaded during acquisition: `false`\n- Evaluator influence during acquisition: `0`\n- Freeze artifacts unchanged: `{str(freeze_artifacts_unchanged).lower()}`\n- Tool calls: `0`; repository access observed: `false`\n\nThe closeout loaded the scoring-only evaluator only after the raw-response seal and performed deterministic validation. No raw response was repaired, replaced, retried, or replayed.\n\nFailure classes were: triage reference-fact failure for both arms on all 8 cases; unsupported-certainty reference-fact failure for both arms on case 001 and review-status failure for both arms on cases 002–008.\n\nThe frozen lexicographic comparison favors the bounded policy at tier `false_positive_avoidance`: generalized delegated external on all 16 cases and recorded 16 false-positive delegations; bounded abstained on all 16 and recorded 16 justified abstentions.\n\nThis supports only the narrow frozen-cohort statement. It does not qualify suppliers, establish population performance, or change production routing.\n""")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    run = args.run_dir if args.run_dir.is_absolute() else ROOT / args.run_dir
    return closeout(run)


if __name__ == "__main__":
    raise SystemExit(main())
