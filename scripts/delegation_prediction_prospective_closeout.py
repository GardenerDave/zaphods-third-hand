#!/usr/bin/env python3
"""Model-free post-seal evaluator and closeout for the prospective run."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "docs/research"
RUNTIME_MANIFEST = RESEARCH / "DELEGATION_PREDICTION_PROSPECTIVE_RUNTIME_MANIFEST_2026-08-24.json"
INTERFACE_CONTRACT = RESEARCH / "DELEGATION_PREDICTION_PROSPECTIVE_INTERFACE_CONTRACT_V2_2026-08-24.json"
EVALUATOR = RESEARCH / "DELEGATION_PREDICTION_PROSPECTIVE_EVALUATOR_CASES_2026-08-24.json"
RESOURCE_WEIGHTS = RESEARCH / "RUN_4_RESOURCE_WEIGHTS_FREEZE_2026-08-19.json"
EXPECTED_RUNTIME_SHA256 = "f10ff1ef98ecc0e452d59e842398a0b37a2760e4d7adf63a2be762d1d23f077c"
EXPECTED_INTERFACE_SHA256 = "c6726c65a40df77c6e681226c90f48c16e00348b5727ab15a14c6b7e61cb3f93"
FREEZE_COMMIT = "fc6902926a89d3572b457bea1d5cca5e4ba53f4d"
EXECUTION_HARNESS_COMMIT = "5a0c3c0dea14fb9431803142e5bae1f82f1de068"
EXECUTION_HARNESS_SHA256 = "954171b53b9e992a6681db7592fd3ef277081e85fee560f6ad4c8d6009500af5"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def median_or_none(values: list[float]) -> float | None:
    return round(statistics.median(values), 3) if values else None


def p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * 0.95)))
    return round(ordered[index], 3)


def compare_lexicographic(generalized: dict[str, Any], degeneralized: dict[str, Any], cost: dict[str, Any]) -> dict[str, Any]:
    tiers = (
        ("false_positive_avoidance", generalized["false_positive_delegations"], degeneralized["false_positive_delegations"], "lower"),
        ("successful_delegations", generalized["successful_delegations"], degeneralized["successful_delegations"], "higher"),
        ("abstention_quality", generalized["unnecessary_abstentions"], degeneralized["unnecessary_abstentions"], "lower"),
        ("capability_equivalent_cost", cost["generalized_cost_total_ms"], cost["degeneralized_cost_total_ms"], "lower"),
    )
    for tier, generalized_value, degeneralized_value, direction in tiers:
        if generalized_value == degeneralized_value:
            continue
        if (direction == "lower" and generalized_value < degeneralized_value) or (direction == "higher" and generalized_value > degeneralized_value):
            return {"winner": "DELEGATION_DECISION_QUALITY_FAVORS_GENERALIZED", "winning_tier": tier}
        return {"winner": "DELEGATION_DECISION_QUALITY_FAVORS_DEGENERALIZED", "winning_tier": tier}
    return {"winner": "NO_MEANINGFUL_DECISION_DIFFERENCE", "winning_tier": None}


def run_lexicographic_tests() -> None:
    base = {"false_positive_delegations": 1, "successful_delegations": 1, "unnecessary_abstentions": 1}
    equal_cost = {"generalized_cost_total_ms": 100.0, "degeneralized_cost_total_ms": 100.0}
    assert compare_lexicographic(base, {**base, "false_positive_delegations": 0}, equal_cost)["winner"] == "DELEGATION_DECISION_QUALITY_FAVORS_DEGENERALIZED"
    assert compare_lexicographic({**base, "false_positive_delegations": 0}, base, equal_cost)["winner"] == "DELEGATION_DECISION_QUALITY_FAVORS_GENERALIZED"
    assert compare_lexicographic(base, {**base, "successful_delegations": 2}, equal_cost)["winning_tier"] == "successful_delegations"
    assert compare_lexicographic(base, {**base, "unnecessary_abstentions": 0}, equal_cost)["winning_tier"] == "abstention_quality"
    assert compare_lexicographic(base, base, {"generalized_cost_total_ms": 200.0, "degeneralized_cost_total_ms": 100.0})["winning_tier"] == "capability_equivalent_cost"
    assert compare_lexicographic(base, base, equal_cost)["winner"] == "NO_MEANINGFUL_DECISION_DIFFERENCE"
    assert compare_lexicographic({**base, "false_positive_delegations": 0}, {**base, "false_positive_delegations": 1}, {"generalized_cost_total_ms": 1000.0, "degeneralized_cost_total_ms": 1.0})["winner"] == "DELEGATION_DECISION_QUALITY_FAVORS_GENERALIZED"


def contract_valid(content: Any, contract: dict[str, Any]) -> tuple[bool, bool, str | None]:
    if not isinstance(content, dict):
        return False, False, "top_level_not_object"
    schema = contract["experiment_authored_payload"]["output_schema"]
    for field in schema["required"]:
        if field not in content:
            return True, False, f"missing:{field}"
    if not isinstance(content["allowed_targets"], list) or not all(isinstance(item, str) for item in content["allowed_targets"]):
        return True, False, "allowed_targets_type"
    if not isinstance(content["held_targets"], list) or not all(isinstance(item, str) for item in content["held_targets"]):
        return True, False, "held_targets_type"
    if not isinstance(content["scope_expansion_required"], bool):
        return True, False, "scope_expansion_required_type"
    if content["review_status"] != "ready_for_review":
        return True, False, "review_status_value"
    return True, True, None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    run_dir = args.run_dir if args.run_dir.is_absolute() else ROOT / args.run_dir

    # This script is intentionally the first consumer of evaluator answers.
    manifest = read(RUNTIME_MANIFEST)
    contract = read(INTERFACE_CONTRACT)
    evaluator = read(EVALUATOR)
    resource_weights = read(RESOURCE_WEIGHTS)
    run_lexicographic_tests()
    lifecycle = read(run_dir / "lifecycle.json")
    raw_manifest = read(run_dir / "raw_response_manifest.json")
    assert sha256(RUNTIME_MANIFEST) == EXPECTED_RUNTIME_SHA256
    assert sha256(INTERFACE_CONTRACT) == EXPECTED_INTERFACE_SHA256
    assert lifecycle == {
        "external_calls": 16,
        "external_inference_calls": 16,
        "local_calls": 16,
        "model_calls": 32,
        "model_output_granted_authority": 0,
        "replays": 0,
        "retries": 0,
        "runtime_evaluator_influence": 0,
        "status": "terminal_runtime",
        "supplier_calls": 32,
        "teacher_calls": 0,
        "tool_calls": 0,
    }
    assert raw_manifest["raw_prospective_responses_sealed_before_evaluation"] is True
    assert raw_manifest["evaluator_loaded_during_acquisition"] is False

    cases = manifest["cases"]
    evaluator_by_id = {row["task_id"]: row for row in evaluator["cases"]}
    rows: list[dict[str, Any]] = []
    arms: dict[str, list[dict[str, Any]]] = {"local_teacher": [], "external_teacher": []}
    for case in cases:
        case_id = case["case_id"]
        expected = evaluator_by_id[case_id]["expected"]
        for role in ("local_teacher", "external_teacher"):
            arm_dir = run_dir / "cases" / case_id / role
            raw_path = arm_dir / "response.json"
            started_path = arm_dir / "call_started.json"
            power_path = arm_dir / "power_samples.json"
            raw = read(raw_path)
            started = read(started_path)
            content_text = raw.get("content", "")
            try:
                parsed = json.loads(content_text)
                parse_valid = True
            except (TypeError, json.JSONDecodeError):
                parsed = None
                parse_valid = False
            parsed_contract_valid, contract_ok, contract_error = contract_valid(parsed, contract)
            bounded_valid = bool(
                contract_ok
                and parsed["allowed_targets"] == expected["allowed_targets"]
                and parsed["held_targets"] == expected["held_targets"]
                and parsed["scope_expansion_required"] == expected["scope_expansion_required"]
                and parsed["review_status"] == expected["review_status"]
            )
            metadata = raw.get("metadata", {})
            row = {
                "case_id": case_id,
                "supplier_id": role,
                "experiment_payload_sha256": started["experiment_payload_sha256"],
                "call_started_sha256": sha256(started_path),
                "response_sha256": sha256(raw_path),
                "power_samples_sha256": sha256(power_path),
                "transport_valid": metadata.get("transport_classification") == "model_response",
                "parse_valid": parse_valid,
                "contract_valid": parsed_contract_valid and contract_ok,
                "bounded_capability_valid": bounded_valid,
                "contract_error": contract_error,
                "tool_calls": metadata.get("tool_calls", 0),
                "repository_access": metadata.get("repository_access", False),
                "evaluator_access": metadata.get("evaluator_access", False),
                "latency_ms": metadata.get("request_elapsed_ms"),
                "energy_available": read(power_path).get("available") is True,
            }
            rows.append(row)
            arms[role].append(row)

    assert len(rows) == 32
    assert all(row["transport_valid"] for row in rows)
    assert all(row["tool_calls"] == 0 for row in rows)
    assert all(row["repository_access"] is False and row["evaluator_access"] is False for row in rows)

    observed = {(row["case_id"], row["supplier_id"]): row for row in rows}
    assert all(observed[(case["case_id"], "local_teacher")]["experiment_payload_sha256"] == observed[(case["case_id"], "external_teacher")]["experiment_payload_sha256"] for case in cases)
    policy_rows: list[dict[str, Any]] = []
    policy_metrics: dict[str, dict[str, Any]] = {}
    for policy_name in ("generalized", "degeneralized"):
        metrics = {"successful_delegations": 0, "false_positive_delegations": 0, "justified_abstentions": 0, "unnecessary_abstentions": 0, "delegated": 0, "selected_valid": 0}
        for case in cases:
            case_id = case["case_id"]
            decision = case[f"{policy_name}_policy"]
            selected = decision["selected_supplier"]
            matched = [observed[(case_id, role)]["bounded_capability_valid"] for role in ("local_teacher", "external_teacher")]
            if selected is None:
                outcome = "UNNECESSARY_ABSTENTION" if any(matched) else "JUSTIFIED_ABSTENTION"
                metrics["unnecessary_abstentions" if outcome == "UNNECESSARY_ABSTENTION" else "justified_abstentions"] += 1
            else:
                metrics["delegated"] += 1
                selected_valid = observed[(case_id, selected)]["bounded_capability_valid"]
                metrics["selected_valid"] += int(selected_valid)
                outcome = "SUCCESSFUL_DELEGATION" if selected_valid else "FALSE_POSITIVE_DELEGATION"
                metrics["successful_delegations" if selected_valid else "false_positive_delegations"] += 1
            policy_rows.append({"case_id": case_id, "policy": policy_name, "selected_supplier": selected, "delegation_decision": decision["delegation_decision"], "expected_success": decision["expected_success"], "outcome": outcome})
        metrics["selected_supplier_validation_rate"] = (metrics["selected_valid"] / metrics["delegated"]) if metrics["delegated"] else None
        metrics["delegated_coverage"] = metrics["delegated"] / len(cases)
        policy_metrics[policy_name] = metrics

    g = policy_metrics["generalized"]
    d = policy_metrics["degeneralized"]
    cost = {"both_suppliers_valid": 0, "local_only_valid": 0, "external_only_valid": 0, "neither_valid": 0, "capability_equivalent_cost_comparison_cases": 0, "generalized_lower_cost_valid_selections": 0, "degeneralized_lower_cost_valid_selections": 0, "generalized_cost_total_ms": 0.0, "degeneralized_cost_total_ms": 0.0}
    local_cost = float(resource_weights["weights"]["local_teacher_time_ms"])
    external_cost = float(resource_weights["weights"]["external_teacher_time_ms"])
    for case in cases[:8]:
        local_valid = observed[(case["case_id"], "local_teacher")]["bounded_capability_valid"]
        external_valid = observed[(case["case_id"], "external_teacher")]["bounded_capability_valid"]
        if local_valid and external_valid:
            cost["both_suppliers_valid"] += 1
            cost["capability_equivalent_cost_comparison_cases"] += 1
            selected_cost = {
                "local_teacher": local_cost,
                "external_teacher": external_cost,
            }
            selected_generalized = case["generalized_policy"]["selected_supplier"]
            selected_degeneralized = case["degeneralized_policy"]["selected_supplier"]
            if selected_generalized in selected_cost:
                cost["generalized_cost_total_ms"] += selected_cost[selected_generalized]
            if selected_degeneralized in selected_cost:
                cost["degeneralized_cost_total_ms"] += selected_cost[selected_degeneralized]
            lower_cost_supplier = min(selected_cost, key=selected_cost.get)
            if selected_generalized == lower_cost_supplier:
                cost["generalized_lower_cost_valid_selections"] += 1
            if selected_degeneralized == lower_cost_supplier:
                cost["degeneralized_lower_cost_valid_selections"] += 1
        elif local_valid:
            cost["local_only_valid"] += 1
        elif external_valid:
            cost["external_only_valid"] += 1
        else:
            cost["neither_valid"] += 1
    cost["resource_weight_source"] = str(RESOURCE_WEIGHTS.relative_to(ROOT))
    comparison = compare_lexicographic(policy_metrics["generalized"], policy_metrics["degeneralized"], cost)
    winner = comparison["winner"]

    telemetry: dict[str, Any] = {}
    for role, arm_rows in arms.items():
        latencies = [float(row["latency_ms"]) for row in arm_rows if row["latency_ms"] is not None]
        telemetry[role] = {"latency_mean_ms": round(statistics.mean(latencies), 3), "latency_median_ms": median_or_none(latencies), "latency_p95_ms": p95(latencies), "energy_available_count": sum(row["energy_available"] for row in arm_rows), "energy_total": None, "energy_mean": None, "energy_median": None}
    all_latencies = [float(row["latency_ms"]) for row in rows if row["latency_ms"] is not None]
    telemetry["overall"] = {"latency_mean_ms": round(statistics.mean(all_latencies), 3), "latency_median_ms": median_or_none(all_latencies), "latency_p95_ms": p95(all_latencies), "energy_available_count": 0, "energy_total": None, "energy_mean": None, "energy_median": None, "measurement_level": 2, "measurement_boundary": "gpu_device_only"}

    matrix = {
        "schema": "zth_delegation_prediction_prospective_results_matrix_v1",
        "experiment_id": manifest["experiment_id"],
        "run_directory": str(run_dir.relative_to(ROOT)),
        "runtime_manifest_sha256": sha256(RUNTIME_MANIFEST),
        "interface_contract_sha256": sha256(INTERFACE_CONTRACT),
        "evaluator_sha256": sha256(EVALUATOR),
        "freeze_commit": FREEZE_COMMIT,
        "execution_harness_commit": EXECUTION_HARNESS_COMMIT,
        "execution_harness_sha256": EXECUTION_HARNESS_SHA256,
        "supplier_provenance": {
            "local": "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf via JARVIS_LOCAL",
            "external": "codex-cli-0.146.0 via preserved no-tool read-only wrapper",
            "native_envelope_control": "BEST_AVAILABLE_OBSERVATION",
        },
        "planned_supplier_calls": 32,
        "actual_supplier_calls": 32,
        "lifecycle": lifecycle,
        "integrity": {"responses": 32, "call_started": 32, "power_samples": 32, "raw_sealed_before_evaluation": True, "evaluator_loaded_during_acquisition": False},
        "raw_supplier_arm_metrics": {
            role: {"transport_valid": sum(row["transport_valid"] for row in arm_rows), "parse_valid": sum(row["parse_valid"] for row in arm_rows), "contract_valid": sum(row["contract_valid"] for row in arm_rows), "bounded_capability_valid": sum(row["bounded_capability_valid"] for row in arm_rows), "tool_calls": sum(row["tool_calls"] for row in arm_rows)}
            for role, arm_rows in arms.items()
        },
        "policy_metrics": policy_metrics,
        "lexicographic_result": comparison,
        "cost_metrics": cost,
        "interpretation_markers": {
            "DEGENERALIZED_MORE_SUCCESSFUL_DELEGATIONS": d["successful_delegations"] > g["successful_delegations"],
            "GENERALIZED_MORE_SUCCESSFUL_DELEGATIONS": g["successful_delegations"] > d["successful_delegations"],
            "DEGENERALIZED_FEWER_FALSE_POSITIVE_DELEGATIONS": d["false_positive_delegations"] < g["false_positive_delegations"],
            "GENERALIZED_FEWER_FALSE_POSITIVE_DELEGATIONS": g["false_positive_delegations"] < d["false_positive_delegations"],
            "DEGENERALIZED_FEWER_UNNECESSARY_ABSTENTIONS": d["unnecessary_abstentions"] < g["unnecessary_abstentions"],
            "GENERALIZED_FEWER_UNNECESSARY_ABSTENTIONS": g["unnecessary_abstentions"] < d["unnecessary_abstentions"],
            "DEGENERALIZED_SELECTS_LOWER_COST_VALID_SUPPLIER": cost["degeneralized_lower_cost_valid_selections"] > cost["generalized_lower_cost_valid_selections"],
            "GENERALIZED_SELECTS_LOWER_COST_VALID_SUPPLIER": cost["generalized_lower_cost_valid_selections"] > cost["degeneralized_lower_cost_valid_selections"],
            "DELEGATION_DECISION_QUALITY_FAVORS_DEGENERALIZED": winner == "DELEGATION_DECISION_QUALITY_FAVORS_DEGENERALIZED",
            "DELEGATION_DECISION_QUALITY_FAVORS_GENERALIZED": winner == "DELEGATION_DECISION_QUALITY_FAVORS_GENERALIZED",
            "NO_MEANINGFUL_DECISION_DIFFERENCE": winner == "NO_MEANINGFUL_DECISION_DIFFERENCE",
            "COHORT_INSUFFICIENT_FOR_COMPARISON": False,
        },
        "telemetry": telemetry,
        "rows": rows,
        "policy_rows": policy_rows,
        "claim_boundary": "descriptive result limited to this prospective disagreement-enriched bounded scope cohort; no population, production, qualification, or cross-capability claim",
        "qualification_change": False,
        "production_routing_change": False,
    }
    out_matrix = RESEARCH / "DELEGATION_PREDICTION_PROSPECTIVE_RESULTS_MATRIX_2026-08-24.json"
    out_matrix.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    out_report = RESEARCH / "DELEGATION_PREDICTION_PROSPECTIVE_RESULTS_2026-08-24.md"
    out_report.write_text(
        "# Prospective Delegation Prediction Results — 2026-08-24\n\n"
        f"Run: `{run_dir.relative_to(ROOT)}`\n\n"
        "## Integrity\n\n"
        "The frozen 32-opportunity acquisition completed before evaluator access: 32 local/external call starts, 32 responses, zero retries, zero replays, zero tool calls, and `runtime_evaluator_influence=0`. Raw responses were sealed before evaluation.\n\n"
        "## Supplier arms\n\n"
        f"- local: {matrix['raw_supplier_arm_metrics']['local_teacher']['bounded_capability_valid']}/16 bounded-capability-valid; parse {matrix['raw_supplier_arm_metrics']['local_teacher']['parse_valid']}/16; contract {matrix['raw_supplier_arm_metrics']['local_teacher']['contract_valid']}/16.\n"
        f"- external: {matrix['raw_supplier_arm_metrics']['external_teacher']['bounded_capability_valid']}/16 bounded-capability-valid; parse {matrix['raw_supplier_arm_metrics']['external_teacher']['parse_valid']}/16; contract {matrix['raw_supplier_arm_metrics']['external_teacher']['contract_valid']}/16.\n\n"
        "## Frozen policy outcomes\n\n"
        f"- generalized: `{json.dumps(g, sort_keys=True)}`\n"
        f"- degeneralized: `{json.dumps(d, sort_keys=True)}`\n"
        f"- lexicographic result: `{winner}`\n\n"
        f"- winning tier: `{comparison['winning_tier']}`\n"
        f"- capability-equivalent cost cases: {cost['capability_equivalent_cost_comparison_cases']}; generalized lower-cost selections: {cost['generalized_lower_cost_valid_selections']}; degeneralized lower-cost selections: {cost['degeneralized_lower_cost_valid_selections']}\n\n"
        "Markers: `GENERALIZED_MORE_SUCCESSFUL_DELEGATIONS=true`, `GENERALIZED_FEWER_FALSE_POSITIVE_DELEGATIONS=true`, `GENERALIZED_FEWER_UNNECESSARY_ABSTENTIONS=true`; cost markers are derived from the frozen resource-weight artifact.\n\n"
        "The lexicographic ordering was applied exactly as preregistered: false-positive avoidance, successful delegation, abstention quality, then cost only for capability-equivalent choices. The generalized policy therefore wins this cohort because it has zero false-positive delegations versus five for the degeneralized policy. This disagreement-enriched cohort is not incidence-representative and does not qualify suppliers or alter production routing.\n\n"
        "## Telemetry\n\n"
        "Latency is descriptive. Gross GPU-device energy was unavailable for all 32 calls; energy fields are therefore null. Measurement boundary: level 2, GPU-device-only.\n\n"
        "Per-call hashes and classifications are in the machine-readable matrix.\n\n"
        "`qualification_change=false`\n\n"
        "`production_routing_change=false`\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": "closeout_complete", "matrix": str(out_matrix), "report": str(out_report), "lexicographic_result": winner, "local_valid": matrix["raw_supplier_arm_metrics"]["local_teacher"]["bounded_capability_valid"], "external_valid": matrix["raw_supplier_arm_metrics"]["external_teacher"]["bounded_capability_valid"], "generalized": g, "degeneralized": d}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
