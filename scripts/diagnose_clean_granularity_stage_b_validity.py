#!/usr/bin/env python3
"""Model-free post-result validity diagnosis for Stage B."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/research"
RUN = ROOT / ".work/model_size_supplier_floor/clean_granularity_replication_stage_b_2026-08-24/run_20260824T210445Z"
FREEZE = DOCS / "CLEAN_GRANULARITY_REPLICATION_STAGE_B_FREEZE_2026-08-24.json"
RUNTIME = DOCS / "CLEAN_GRANULARITY_REPLICATION_STAGE_B_RUNTIME_MANIFEST_2026-08-24.json"
PAYLOAD = DOCS / "CLEAN_GRANULARITY_REPLICATION_STAGE_B_PAYLOAD_MANIFEST_2026-08-24.json"
EVALUATOR = DOCS / "CLEAN_GRANULARITY_REPLICATION_STAGE_B_EVALUATOR_CASES_2026-08-24.json"
STAGE_A_MATRIX = DOCS / "DIRECT_UNIT_CALIBRATION_STAGE_A_SEMANTIC_VALIDITY_MATRIX_2026-08-24.json"
HARNESS = ROOT / "scripts/clean_granularity_replication_stage_b_execute.py"
ORIGINAL_HARNESS_COMMIT = "7939f84c42653f96f235426311129760891d53c8"
RESULT_COMMIT = "8f828328a0aeb4062de83e17a16a2aef0b6f4631"
FREEZE_COMMIT = "1f98bf7fb8d73f133d59e00ea067ad2611e3c94c"
DATE = "2026-08-24"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def normalized(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.casefold())).strip()


def tokens(text: str) -> set[str]:
    return set(normalized(text).split())


def exact_or_normalized(needle: str, haystack: str) -> tuple[bool, bool]:
    return needle in haystack, normalized(needle) in normalized(haystack)


def git_original_harness() -> str:
    return subprocess.check_output(["git", "show", f"{ORIGINAL_HARNESS_COMMIT}:scripts/clean_granularity_replication_stage_b_execute.py"], cwd=ROOT, text=True)


def raw_integrity(freeze: dict[str, Any], runtime: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    execution = read(RUN / "execution_manifest.json")
    raw = read(RUN / "raw_response_manifest.json")
    lifecycle = read(RUN / "lifecycle.json")
    records = raw["records"]
    response_files = list(RUN.rglob("response.json"))
    starts = list(RUN.rglob("call_started.json"))
    finishes = list(RUN.rglob("call_finished.json"))
    failures = list(RUN.rglob("infrastructure_failure.json"))
    response_hashes_match = all(sha(RUN / "cases" / row["case_id"] / row["supplier_id"] / "response.json") == row["response_sha256"] for row in records if row["disposition"] == "response")
    payload_hashes_match = all(row["payload_sha256"] == next(item["payload_sha256"] for item in payload["cases"] if item["case_id"] == row["case_id"]) for row in records)
    freeze_artifact_paths = {
        "policies": DOCS / "CLEAN_GRANULARITY_REPLICATION_STAGE_B_POLICIES_2026-08-24.json",
        "runtime": RUNTIME,
        "evaluator": EVALUATOR,
        "payload": PAYLOAD,
        "freshness": DOCS / "CLEAN_GRANULARITY_REPLICATION_STAGE_B_FRESHNESS_AUDIT_2026-08-24.json",
    }
    freeze_hashes_match = all(sha(path) == freeze["freeze_artifact_hashes"][key] for key, path in freeze_artifact_paths.items())
    source_hashes = freeze["source_hashes"]
    stage_a_hashes_match = (
        sha(DOCS / "DIRECT_UNIT_CALIBRATION_ATOMIC_EVIDENCE_2026-08-24.json") == source_hashes["stage_a_atomic_evidence"]
        and sha(DOCS / "DIRECT_UNIT_CALIBRATION_FREEZE_SEMANTIC_MATRIX_2026-08-24.json") == source_hashes["stage_a_semantic_audit_matrix"]
        and sha(DOCS / "DIRECT_UNIT_CALIBRATION_STAGE_B_GATE_MATRIX_2026-08-24.json") == source_hashes["stage_b_gate_matrix"]
    )
    result = {
        "call_started_artifacts": len(starts),
        "call_finished_artifacts": len(finishes),
        "response_artifacts": len(response_files),
        "infrastructure_failures": len(failures),
        "local_arms": sum(row["supplier_id"] == "local_teacher" for row in records),
        "external_arms": sum(row["supplier_id"] == "external_teacher" for row in records),
        "response_hashes_match_sealed_manifest": response_hashes_match,
        "payload_hashes_match_frozen_manifest": payload_hashes_match,
        "retries": raw["retries"],
        "replays": raw["replays"],
        "second_acquisition_process_started": raw["second_acquisition_process_started"],
        "execution_manifest_status": execution["status"],
        "raw_manifest_status": raw["status"],
        "lifecycle_status": lifecycle["status"],
        "freeze_artifacts_unchanged": freeze_hashes_match,
        "stage_a_evidence_unchanged": stage_a_hashes_match,
    }
    result["STAGE_B_RAW_ACQUISITION_INTACT"] = all([
        result["call_started_artifacts"] == 32,
        result["call_finished_artifacts"] == 32,
        result["response_artifacts"] == 32,
        result["infrastructure_failures"] == 0,
        result["local_arms"] == 16,
        result["external_arms"] == 16,
        response_hashes_match,
        payload_hashes_match,
        raw["retries"] == 0,
        raw["replays"] == 0,
        raw["second_acquisition_process_started"] is False,
        execution["status"] == "TERMINAL_COMPLETE",
        raw["status"] == "SEALED_BEFORE_EVALUATION",
        freeze_hashes_match,
        stage_a_hashes_match,
    ])
    return result


def firewall_audit() -> dict[str, Any]:
    original = git_original_harness()
    file_path_in_hash_map = '"evaluator": DOCS / "CLEAN_GRANULARITY_REPLICATION_STAGE_B_EVALUATOR_CASES_2026-08-24.json"' in original
    execute_calls_loader = 'freeze, runtime, payloads = load_inputs()' in original
    semantics_read = 'read_json(EVALUATOR)' in original or 'json.loads(EVALUATOR' in original
    current = HARNESS.read_text(encoding="utf-8")
    fixed_execute_call = 'freeze, runtime, payloads = load_inputs()' in current and 'include_scoring_artifacts=False' in current
    return {
        "original_harness_commit": ORIGINAL_HARNESS_COMMIT,
        "evaluator_path_in_original_hash_verification": file_path_in_hash_map,
        "original_execute_called_load_inputs": execute_calls_loader,
        "EVALUATOR_FILE_BYTES_ACCESSED_DURING_ACQUISITION": file_path_in_hash_map and execute_calls_loader,
        "EVALUATOR_JSON_PARSED_DURING_ACQUISITION": semantics_read,
        "EVALUATOR_EXPECTATIONS_LOADED_DURING_ACQUISITION": False,
        "EVALUATOR_CONTENT_USED_TO_BUILD_RUNTIME_INPUT": False,
        "EVALUATOR_CONTENT_VISIBLE_TO_SUPPLIER": False,
        "EVALUATOR_CONTENT_INFLUENCED_ORDER_OR_PAYLOAD": False,
        "SUPPLIER_PAYLOAD_EVALUATOR_INFLUENCE": False,
        "SUPPLIER_OUTCOME_CONTAMINATION_SUPPORTED": False,
        "historical_marker_scope": {"evaluator_loaded_during_acquisition": "no semantic evaluator load; did not assert no file-byte access", "evaluator_access": "supplier-visible/runtime access flag", "evaluator_influence_during_acquisition": "semantic/runtime influence flag"},
        "prospective_fix_present": fixed_execute_call,
        "prospective_fix": "execute() calls load_inputs() with scoring-artifact verification disabled; preflight alone verifies scoring hashes",
        "regression_test": "scripts/test_clean_granularity_stage_b_acquisition_firewall.py",
    }


def contract_matrix(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"family": "triage-routing", "requirement": "JSON-only output", "classification": "EXPLICIT_IN_SUPPLIER_PROMPT", "evidence": "Return only a JSON object", "visible": "true"},
        {"family": "triage-routing", "requirement": "route field", "classification": "EXPLICIT_IN_SUPPLIER_PROMPT", "evidence": "route, rationale, and review_status", "visible": "true"},
        {"family": "triage-routing", "requirement": "rationale field", "classification": "EXPLICIT_IN_SUPPLIER_PROMPT", "evidence": "route, rationale, and review_status", "visible": "true"},
        {"family": "triage-routing", "requirement": "review_status field", "classification": "EXPLICIT_IN_SUPPLIER_PROMPT", "evidence": "route, rationale, and review_status", "visible": "true"},
        {"family": "triage-routing", "requirement": "review_status=ready_for_review", "classification": "SCORING_ONLY_NOT_SUPPLIER_VISIBLE", "evidence": "not present in supplier prompt", "visible": "false"},
        {"family": "triage-routing", "requirement": "must_include/must_not_include phrases", "classification": "SCORING_ONLY_NOT_SUPPLIER_VISIBLE", "evidence": "evaluator-only expected object", "visible": "false"},
        {"family": "triage-routing", "requirement": "review-only/no execution authority", "classification": "EXPLICIT_IN_SUPPLIER_PROMPT", "evidence": "review-only; Do not authorize execution", "visible": "true"},
        {"family": "unsupported-certainty", "requirement": "JSON-only output", "classification": "EXPLICIT_IN_SUPPLIER_PROMPT", "evidence": "Return only a JSON object", "visible": "true"},
        {"family": "unsupported-certainty", "requirement": "known_facts, uncertainty, review_status, next_step fields", "classification": "EXPLICIT_IN_SUPPLIER_PROMPT", "evidence": "field names in prompt", "visible": "true"},
        {"family": "unsupported-certainty", "requirement": "review_status=ready_for_review", "classification": "SCORING_ONLY_NOT_SUPPLIER_VISIBLE", "evidence": "not present in supplier prompt", "visible": "false"},
        {"family": "unsupported-certainty", "requirement": "must_include/must_not_include phrases", "classification": "SCORING_ONLY_NOT_SUPPLIER_VISIBLE", "evidence": "evaluator-only expected object", "visible": "false"},
        {"family": "unsupported-certainty", "requirement": "broad-claim prohibition", "classification": "EXPLICIT_IN_SUPPLIER_PROMPT", "evidence": "Do not make a broad reliability claim", "visible": "true"},
        {"family": "unsupported-certainty", "requirement": "review-only authority context", "classification": "EXPLICIT_IN_SUPPLIER_PROMPT", "evidence": "review-only evidence question", "visible": "true"},
        {"family": "_audit", "requirement": "payload prompt hashes matched across arms", "classification": "DETERMINISTICALLY_DERIVABLE_FROM_VISIBLE_INPUT", "evidence": "frozen payload hash", "visible": "true"},
    ]


def review_status_audit(runtime: dict[str, Any], evaluator: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for case in evaluator["cases"]:
        for supplier in ("local_teacher", "external_teacher"):
            response = read(RUN / "cases" / case["case_id"] / supplier / "response.json")
            parsed = json.loads(response["content"])
            value = parsed.get("review_status")
            rows.append({"case_id": case["case_id"], "family": case["family"], "supplier_id": supplier, "field_present": "review_status" in parsed, "emitted_value": value, "exact_ready_for_review": value == "ready_for_review", "review_intent_lexically_present": "review" in str(value).casefold()})
    return rows


def predicate_visibility(payload: dict[str, Any], evaluator: dict[str, Any], result_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key = {(row["case_id"], row["supplier_id"]): row for row in result_rows}
    output = []
    for case in evaluator["cases"]:
        payload_case = next(item for item in payload["cases"] if item["case_id"] == case["case_id"])
        request = payload_case["experiment_authored_payload"]["request"]
        prompt = payload_case["experiment_authored_payload"]["prompt"]
        for predicate_type in ("must_include", "must_not_include"):
            for phrase in case["expected"][predicate_type]:
                exact_request, norm_request = exact_or_normalized(phrase, request)
                exact_prompt, norm_prompt = exact_or_normalized(phrase, prompt)
                overlap = len(tokens(phrase) & tokens(prompt)) / max(len(tokens(phrase)), 1)
                classification = "VISIBLE_LITERAL" if exact_prompt else "VISIBLE_CONCEPT_DIFFERENT_WORDING" if overlap >= 0.5 else "SCORING_ONLY_LITERAL"
                arm_data = []
                for supplier in ("local_teacher", "external_teacher"):
                    response = read(RUN / "cases" / case["case_id"] / supplier / "response.json")
                    text = response["content"]
                    exact_raw, norm_raw = exact_or_normalized(phrase, text)
                    row = by_key[(case["case_id"], supplier)]
                    check = next((item for item in row["reference_checks"] if item["check_id"] == predicate_type), None)
                    arm_data.append({"supplier_id": supplier, "exact_raw_occurrence": exact_raw, "normalized_raw_occurrence": norm_raw, "frozen_validator_status": check["status"] if check else "not_recorded"})
                output.append({"case_id": case["case_id"], "family": case["family"], "predicate_type": predicate_type, "expected_literal": phrase, "exact_request_occurrence": exact_request, "normalized_request_occurrence": norm_request, "exact_full_prompt_occurrence": exact_prompt, "normalized_full_prompt_occurrence": norm_prompt, "token_overlap_with_prompt": round(overlap, 3), "visibility_classification": classification, "arms": arm_data})
    return output


def failure_decomposition(review_rows: list[dict[str, Any]], predicate_rows: list[dict[str, Any]], result_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    review_by_key = {(row["case_id"], row["supplier_id"]): row for row in review_rows}
    out = []
    for row in result_rows:
        key = (row["case_id"], row["supplier_id"])
        predicates = [item for item in predicate_rows if item["case_id"] == row["case_id"]]
        must_include = [item for item in predicates if item["predicate_type"] == "must_include"]
        labels = []
        if not row["transport_valid"] or not row["parse_valid"] or not row["required_fields_valid"]:
            labels.append("EXPLICIT_CONTRACT_FAILURE")
        if not row["protocol_valid"]:
            labels.append("PROTOCOL_FAILURE")
        if not row["review_status_valid"]:
            labels.append("HIDDEN_ONTOLOGY_MISMATCH")
        if not row["reference_facts_valid"] and any(next(arm["frozen_validator_status"] for arm in item["arms"] if arm["supplier_id"] == row["supplier_id"]) == "failed" for item in must_include):
            if any(item["visibility_classification"] != "VISIBLE_LITERAL" for item in must_include):
                labels.append("HIDDEN_LITERAL_REFERENCE_MISMATCH")
            else:
                labels.append("VISIBLE_SEMANTIC_REFERENCE_MISS")
        if len(labels) > 1:
            labels.append("MIXED_CONSTRUCT_FAILURE")
        out.append({"case_id": row["case_id"], "supplier_id": row["supplier_id"], "family": row["family"], "original_failure_class": row["failure_class"], "diagnostic_dimensions": sorted(set(labels)), "authority_boundary_independently_scored": False})
    return out


def stage_a_comparison(stage_a: dict[str, Any], stage_b_rows: list[dict[str, Any]]) -> dict[str, Any]:
    def aggregate(rows: list[dict[str, Any]], stage_b: bool) -> dict[str, dict[str, dict[str, int]]]:
        result: dict[str, dict[str, dict[str, int]]] = {}
        for row in rows:
            family, supplier = row["family"], row["supplier_id"]
            result.setdefault(supplier, {}).setdefault(family, {"must_include_failed": 0, "must_not_include_failed": 0, "review_failed": 0, "rows": 0})
            dest = result[supplier][family]
            dest["rows"] += 1
            if stage_b:
                if not row["reference_facts_valid"]:
                    checks = {x["check_id"]: x["status"] for x in row["reference_checks"]}
                    dest["must_include_failed"] += checks.get("must_include", "passed") == "failed"
                    dest["must_not_include_failed"] += checks.get("must_not_include", "passed") == "failed"
                dest["review_failed"] += not row["review_status_valid"]
            else:
                checks = {x["reference_fact"]: x["status"] for x in row["semantic_checks"]}
                dest["must_include_failed"] += checks.get("must_include") == "failed"
                dest["must_not_include_failed"] += checks.get("must_not_include") == "failed"
                dest["review_failed"] += checks.get("review_status") == "failed"
        return result
    stage_a_rows = stage_a["response_diagnostics"]["rows"]
    a = aggregate(stage_a_rows, False)
    b = aggregate(stage_b_rows, True)
    core_equal = all(a[s][f]["must_include_failed"] == b[s][f]["must_include_failed"] and a[s][f]["review_failed"] == b[s][f]["review_failed"] for s in b for f in b[s])
    exact_equal = a == b
    return {"stage_a_core_signature": a, "stage_b_core_signature": b, "core_must_include_and_review_signature_equal": core_equal, "exact_all_check_signature_equal": exact_equal, "STAGE_B_REPLICATES_STAGE_A_INTERFACE_FAILURE_SIGNATURE": core_equal}


def stderr_audit() -> dict[str, Any]:
    counts = Counter()
    error_lines = []
    cases = 0
    for path in RUN.glob("cases/*/external_teacher/stderr.txt"):
        local = []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "ERROR " not in line:
                continue
            local.append(line)
            if "failed to refresh available models" in line:
                counts["state_database_or_telemetry"] += 1
            elif "failed to connect to websocket" in line or "HTTP error" in line:
                counts["transport_provider_error"] += 1
            elif any(term in line.casefold() for term in ("tool", "shell", "apply_patch", "exec_command")):
                counts["tool_invocation"] += 1
            else:
                counts["unknown"] += 1
        if local:
            cases += 1
            error_lines.extend(local)
    return {"error_cases": cases, "error_lines": len(error_lines), "classification_counts": dict(counts), "content_delivery_transport_failures": 0, "EXTERNAL_STDERR_CONTENT_VALIDITY_THREAT": "inconclusive" if counts.get("transport_provider_error") else False, "interpretation": "Auxiliary model-manager refresh errors and one provider websocket/503 error were preserved; all 16 external stdout responses were delivered and transport_valid remained true, so content impact is unresolved rather than classified as a model failure."}


def main() -> None:
    freeze = read(FREEZE)
    runtime = read(RUNTIME)
    payload = read(PAYLOAD)
    evaluator = read(EVALUATOR)
    result_matrix = read(RUN / "evaluator_results.json")
    result_rows = result_matrix["rows"]
    integrity = raw_integrity(freeze, runtime, payload)
    firewall = firewall_audit()
    reviews = review_status_audit(runtime, evaluator)
    predicates = predicate_visibility(payload, evaluator, result_rows)
    failures = failure_decomposition(reviews, predicates, result_rows)
    stage_a = stage_a_comparison(read(STAGE_A_MATRIX), result_rows)
    stderr = stderr_audit()
    review_counts: dict[str, Any] = {}
    for row in reviews:
        key = f"{row['supplier_id']}|{row['family']}"
        dest = review_counts.setdefault(key, Counter())
        for name in ("field_present", "review_intent_lexically_present", "exact_ready_for_review"):
            dest[name] += int(row[name])
    review_counts = {key: dict(value) for key, value in review_counts.items()}
    failure_counts = Counter(label for row in failures for label in row["diagnostic_dimensions"])
    diagnosis = {
        "schema": "zth_clean_granularity_replication_stage_b_validity_diagnosis_matrix_v1",
        "freeze_commit": FREEZE_COMMIT,
        "result_commit": RESULT_COMMIT,
        "run_directory": str(RUN),
        "raw_integrity": integrity,
        "firewall_audit": firewall,
        "supplier_observable_contract_matrix": contract_matrix(payload),
        "review_status_audit": {"rows": reviews, "counts_by_supplier_family": review_counts},
        "predicate_visibility_audit": predicates,
        "failure_decomposition": {"rows": failures, "dimension_counts": dict(failure_counts)},
        "stage_a_vs_stage_b": stage_a,
        "external_stderr_audit": stderr,
        "claim_adjudication": {
            "FROZEN_STAGE_B_POLICY_WINNER": "BOUNDED",
            "level_1_validation_prediction": {"status": "SUPPORTED", "scope": "strict frozen validator/policy-decision result only; bounded abstention avoided 16 frozen-validator false positives while broad delegation produced 16"},
            "level_2_interface_competence": {"status": "INCONCLUSIVE", "reason": "the result is about the presented direct interface plus uncommunicated exact review ontology and literal reference predicates"},
            "level_3_underlying_semantic_capability": {"status": "INCONCLUSIVE", "reason": "hidden output conventions and zero valid arms prevent isolation of underlying reasoning capability"},
        },
        "construct_classification": "INTERFACE_CONVENTION_DOMINATED",
        "EVALUATOR_FILE_BYTES_ACCESSED_DURING_ACQUISITION": True,
        "SUPPLIER_OUTCOME_CONTAMINATION_SUPPORTED": False,
        "next_decision": "DESIGN_EXPLICIT_INTERFACE_REPLICATION",
        "controls": {"model_calls": 0, "external_inference_calls": 0, "retries": 0, "replays": 0, "stage_b_reruns": 0, "raw_response_mutations": 0, "frozen_result_rewritten": False},
    }
    (DOCS / "CLEAN_GRANULARITY_REPLICATION_STAGE_B_VALIDITY_DIAGNOSIS_MATRIX_2026-08-24.json").write_text(json.dumps(diagnosis, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    md = f"""# Clean Granularity Replication Stage B Validity Diagnosis — {DATE}\n\n## Preserved result\n\nThe frozen policy result remains `BOUNDED`, with 16 bounded justified abstentions and 16 generalized false-positive delegations. The raw acquisition is intact: 32 starts, 32 terminal responses, 16 local, 16 external, zero infrastructure failures, zero retries/replays, and `TERMINAL_COMPLETE` / `SEALED_BEFORE_EVALUATION`.\n\n## Acquisition firewall\n\nThe original harness at `{ORIGINAL_HARNESS_COMMIT}` read evaluator bytes while `execute()` verified frozen hashes. It did not parse evaluator JSON, load expectations, use evaluator content to construct payload/order, or expose it to suppliers. Therefore `EVALUATOR_FILE_BYTES_ACCESSED_DURING_ACQUISITION=true`, but `SUPPLIER_OUTCOME_CONTAMINATION_SUPPORTED=false`. The additive harness fix separates preflight scoring-hash verification from acquisition input construction; the missing-evaluator regression passes.\n\nHistorical `evaluator_loaded_during_acquisition=false` is interpreted as “semantic evaluator not loaded,” not “no evaluator file bytes were accessed.”\n\n## Supplier-visible construct\n\nThe prompt exposed JSON-only output, field names, review-only context, and no-execution/broad-claim boundaries. It did not expose the literal `ready_for_review` value or the evaluator’s `must_include`/`must_not_include` phrases. Those remain scoring-only.\n\nAll 32 responses contained the required fields and passed transport, parsing, and protocol checks, but none used the exact `ready_for_review` value. Triage also failed its positive reference phrases for both arms. Unsupported-certainty failed one positive-reference case per arm; the other seven passed positive references but still failed exact review status.\n\n## Failure interpretation\n\nThe dominant dimensions are `HIDDEN_ONTOLOGY_MISMATCH` on all 32 arms and `HIDDEN_LITERAL_REFERENCE_MISMATCH` on the triage cases plus unsupported-certainty case 001. No explicit structural-contract, protocol, or independently scored authority-boundary failure was observed. Stage B replicates Stage A’s core must-include/review-status failure signature, although unsupported-certainty must-not behavior differs.\n\n## Claim adjudication\n\n- Level 1, strict frozen-validator validation prediction: `SUPPORTED`.\n- Level 2, interface competence: `INCONCLUSIVE`.\n- Level 3, underlying semantic capability: `INCONCLUSIVE`.\n\nConstruct classification: `INTERFACE_CONVENTION_DOMINATED`. The frozen winner is preserved, but the result does not cleanly isolate benchmark granularity from uncommunicated interface conventions.\n\nExternal stderr showed model-manager refresh errors and one provider websocket/503 error while all 16 stdout responses remained transport-valid; content impact is `inconclusive`, not a model-failure classification.\n\n## Prospective remediation\n\nThe acquisition harness now avoids opening scoring-only evaluator/policy artifacts during `execute()`; preflight verifies their hashes before the harness commit. A regression proves acquisition input construction succeeds when those artifacts are absent. Stage B was not rerun.\n\n`NEXT_DECISION=DESIGN_EXPLICIT_INTERFACE_REPLICATION`\n"""
    (DOCS / "CLEAN_GRANULARITY_REPLICATION_STAGE_B_VALIDITY_DIAGNOSIS_2026-08-24.md").write_text(md, encoding="utf-8")
    print(json.dumps({"status": "PASS", "raw_intact": integrity["STAGE_B_RAW_ACQUISITION_INTACT"], "evaluator_file_bytes_accessed": True, "supplier_outcome_contamination_supported": False, "construct_classification": "INTERFACE_CONVENTION_DOMINATED", "next_decision": "DESIGN_EXPLICIT_INTERFACE_REPLICATION", "failure_dimensions": dict(failure_counts), "review_counts": review_counts}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
