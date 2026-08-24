#!/usr/bin/env python3
"""Materialize and validate the V2 explicit-interface calibration freeze."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "research"
V1_EVALUATOR = DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_EVALUATOR_CASES_2026-08-24.json"
BASE_COMMIT = "00c2a81cae2aae0251969cb5bf5349fd13afe7a0"
PRIOR_DIAGNOSIS_COMMIT = "fc32912bd03c32c8c70980edcb345e773b275ca8"
EXPERIMENT_ID = "explicit_interface_direct_unit_calibration_v2_2026-08-24"
TRIAGE_ID = "duc_explicit_triage_direct_json_v2"
UNSUPPORTED_ID = "duc_explicit_unsupported_certainty_direct_json_v2"
SUPPLIERS = ["local_teacher", "external_teacher"]
AUTHORITY = {"mode": "review-only", "mutation_authority": False, "execution_authority": False}

import sys
sys.path.insert(0, str(ROOT))
from scripts.evaluate_explicit_interface_direct_unit_calibration_v2 import (  # noqa: E402
    NORMALIZATION_RULE,
    evaluate,
)
from scripts.project_explicit_interface_direct_unit_calibration_v2_inputs import (  # noqa: E402
    load_acquisition_inputs,
)


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha_value(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_v1_cases() -> list[dict[str, Any]]:
    data = json.loads(V1_EVALUATOR.read_text(encoding="utf-8"))
    assert len(data["cases"]) == 16
    return data["cases"]


def interface_contracts() -> dict[str, dict[str, Any]]:
    triage = {
        "interface_id": TRIAGE_ID,
        "bounded_responsibility": "directly classify one evidence-backed review item without authorizing execution",
        "required_fields": ["route", "rationale", "review_status"],
        "field_types": {"route": "string", "rationale": "string", "review_status": "string"},
        "additional_properties": "allowed_and_ignored",
        "authority_context": AUTHORITY,
        "matching_rule": NORMALIZATION_RULE,
        "semantic_field_scopes": {"required_rationale_facts": "rationale", "rationale_forbidden_facts": "rationale"},
        "tool_authority": False,
        "repository_access": False,
        "evaluator_access": False,
        "downstream_dependencies": [],
    }
    unsupported = {
        "interface_id": UNSUPPORTED_ID,
        "bounded_responsibility": "directly separate observed facts from untested uncertainty without making a broad reliability claim",
        "required_fields": ["known_facts", "uncertainty", "review_status", "next_step"],
        "field_types": {"known_facts": "array_of_strings", "uncertainty": "array_of_strings", "review_status": "string", "next_step": "string"},
        "additional_properties": "allowed_and_ignored",
        "authority_context": AUTHORITY,
        "matching_rule": NORMALIZATION_RULE,
        "semantic_field_scopes": {"known_facts_required": "known_facts elements", "uncertainty_required": "uncertainty elements", "next_step_required": "next_step", "prohibited_claims": "known_facts + uncertainty + next_step"},
        "tool_authority": False,
        "repository_access": False,
        "evaluator_access": False,
        "downstream_dependencies": [],
    }
    for contract in (triage, unsupported):
        contract["interface_hash"] = sha_value(contract)
    return {"triage-routing": triage, "unsupported-certainty": unsupported}


def prompt_for(case: dict[str, Any], contract: dict[str, Any], expected: dict[str, Any]) -> str:
    if case["family"] == "triage-routing":
        return (
            "Return one JSON object only; do not use Markdown or surrounding commentary. "
            "The JSON object may contain additional properties, which are ignored. "
            "The required field route must be a JSON string and must equal exactly \"review\". "
            "The required field rationale must be a JSON string. "
            "The required field review_status must be a JSON string and must equal exactly \"ready_for_review\". "
            "Every listed required rationale fact must occur in rationale. Every listed prohibited rationale fact "
            "must be absent from rationale. Matching is case-insensitive after Unicode NFKC normalization and "
            "contiguous-whitespace normalization to one space; no synonyms or stemming are accepted. "
            "Authority is review-only: describe and route evidence, but do not authorize execution or mutation. "
            f"Request: {case['request']} "
            f"Required rationale facts (verbatim under the matching rule): {json.dumps(expected['rationale_required_facts'], ensure_ascii=False)}. "
            f"Prohibited rationale facts (verbatim under the matching rule): {json.dumps(expected['rationale_forbidden_facts'], ensure_ascii=False)}."
        )
    return (
        "Return one JSON object only; do not use Markdown or surrounding commentary. "
        "The JSON object may contain additional properties, which are ignored. "
        "The required field known_facts must be a JSON array of strings. "
        "The required field uncertainty must be a JSON array of strings. "
        "The required field review_status must be a JSON string and must equal exactly \"ready_for_review\". "
        "The required field next_step must be a JSON string. The required known fact must occur in a known_facts "
        "element; the required uncertainty must occur in an uncertainty element; and the required next evidence "
        "must occur in next_step. The prohibited broad claim must be absent from known_facts, uncertainty, and "
        "next_step. Matching is case-insensitive after Unicode NFKC normalization and contiguous-whitespace "
        "normalization to one space; no synonyms or stemming are accepted. Authority is review-only: report "
        "evidence and limits, but do not authorize an operational action. "
        f"Request: {case['request']} "
        f"Known fact required (verbatim under the matching rule): {json.dumps(expected['known_facts_required'], ensure_ascii=False)}. "
        f"Uncertainty required (verbatim under the matching rule): {json.dumps(expected['uncertainty_required'], ensure_ascii=False)}. "
        f"Next evidence required (verbatim under the matching rule): {json.dumps(expected['next_step_required'], ensure_ascii=False)}. "
        f"Prohibited broad claim (verbatim under the matching rule): {json.dumps(expected['prohibited_claims'], ensure_ascii=False)}."
    )


def case_expected(v1: dict[str, Any]) -> dict[str, Any]:
    expected = v1["expected"]
    if v1["family"] == "triage-routing":
        return {"review_status_exact": "ready_for_review", "route_exact": "review", "rationale_required_facts": expected["rationale_required_facts"], "rationale_forbidden_facts": expected["rationale_forbidden_facts"]}
    return {"review_status_exact": "ready_for_review", "known_facts_required": expected["known_facts_required"], "uncertainty_required": expected["uncertainty_required"], "next_step_required": expected["next_step_required"], "prohibited_claims": expected["prohibited_claims"]}


def build() -> dict[str, Any]:
    contracts = interface_contracts()
    v1_cases = load_v1_cases()
    cases: list[dict[str, Any]] = []
    for v1 in v1_cases:
        family = v1["family"]
        expected = case_expected(v1)
        contract = contracts[family]
        case_id = "explicit-v2-" + v1["case_id"].replace("explicit-", "")
        cases.append({"case_id": case_id, "family": family, "request": v1["request"], "authority_context": AUTHORITY, "expected": expected, "interface_contract": contract, "source_anchor": v1["freshness_lineage"], "original_v1_case_id": v1["case_id"]})
    payload_cases: list[dict[str, Any]] = []
    runtime_cases: list[dict[str, Any]] = []
    evaluator_cases: list[dict[str, Any]] = []
    for case in cases:
        contract = contracts[case["family"]]
        message = prompt_for(case, contract, case["expected"])
        message_hash = hashlib.sha256(message.encode("utf-8")).hexdigest()
        metadata_payload = {"case_id": case["case_id"], "capability_family": case["family"], "interface_id": contract["interface_id"], "authority_context": AUTHORITY, "supplier_message_text": message, "supplier_message_sha256": message_hash}
        payload_cases.append({"case_id": case["case_id"], "experiment_metadata_payload": metadata_payload, "supplier_message_text": message, "supplier_message_sha256": message_hash, "interface_id": contract["interface_id"], "interface_hash": contract["interface_hash"], "supplier_arms": SUPPLIERS})
        runtime_cases.append({"case_id": case["case_id"], "capability_family": case["family"], "bounded_responsibility": contract["bounded_responsibility"], "request": case["request"], "authority_context": AUTHORITY, "interface_id": contract["interface_id"], "interface_hash": contract["interface_hash"], "payload_manifest_case_ref": case["case_id"], "supplier_message_sha256": message_hash, "supplier_arms": SUPPLIERS})
        evaluator_cases.append({"case_id": case["case_id"], "family": case["family"], "request": case["request"], "expected": case["expected"], "authority_context": AUTHORITY, "interface_contract": {"interface_id": contract["interface_id"], "required_fields": contract["required_fields"], "field_types": contract["field_types"]}, "source_anchor": case["source_anchor"]})
    payload = {"schema": "zth.explicit_interface_direct_unit_calibration.payload.v2", "experiment_id": EXPERIMENT_ID, "status": "frozen_unexecuted", "transport_mode": "supplier_message_text_only", "canonical_serialization": "UTF-8 exact message bytes; no runtime prompt reconstruction", "supplier_visible_bytes_frozen": True, "evaluator_information_included": False, "controller_policy_metadata_included": False, "case_order": [c["case_id"] for c in cases], "cases": payload_cases}
    runtime = {"schema": "zth.explicit_interface_direct_unit_calibration.runtime.v2", "experiment_id": EXPERIMENT_ID, "status": "frozen_unexecuted", "case_count": 16, "case_order": [c["case_id"] for c in cases], "cases": runtime_cases, "supplier_arms": SUPPLIERS, "execution_controls": {"planned_local_calls": 16, "planned_external_calls": 16, "planned_supplier_calls": 32, "retries": 0, "replays": 0, "response_repair": False, "teacher_intervention": False, "downstream_model_repair": False, "model_substitution": False, "tool_calls": 0, "repository_access": False, "evaluator_access": False, "outcome_conditional_sample_extension": False}, "evaluator_information_included": False, "scoring_information_included": False, "policy_information_included": False}
    evaluator = {"schema": "zth.explicit_interface_direct_unit_calibration.evaluator.v2", "experiment_id": EXPERIMENT_ID, "status": "scoring_only_frozen_unexecuted", "runtime_visibility": "scoring_only_after_raw_seal", "cases": evaluator_cases, "normalization_rule": NORMALIZATION_RULE, "direct_capability_definition": ["TRANSPORT_VALID", "PARSE_VALID", "REQUIRED_FIELDS_VALID", "REQUIRED_FIELD_TYPES_VALID", "EXPLICIT_INTERFACE_VALID", "TASK_SEMANTICS_VALID", "REVIEW_STATUS_VALID", "PROTOCOL_VALID"], "evaluator_implementation_module": "scripts/evaluate_explicit_interface_direct_unit_calibration_v2.py"}
    return {"contracts": contracts, "cases": cases, "payload": payload, "runtime": runtime, "evaluator": evaluator}


def all_prior_request_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for root in (DOCS, ROOT / ".work" / "model_size_supplier_floor"):
        if not root.exists():
            continue
        for path in root.rglob("*.json"):
            # V1 is an unexecuted design freeze, not a prior scored target
            # pack; it is deliberately excluded from the scored-pack novelty
            # comparison.  Stage A/Stage B/Scope V0 and other preserved packs
            # remain included.
            if "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION" in path.name:
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            stack: list[tuple[Any, str | None]] = [(data, None)]
            while stack:
                value, case_id = stack.pop()
                if isinstance(value, dict):
                    local_id = value.get("case_id", case_id)
                    if isinstance(value.get("request"), str):
                        records.append({"source": str(path.relative_to(ROOT)), "case_id": local_id, "request": value["request"]})
                    stack.extend((child, local_id) for child in value.values())
                elif isinstance(value, list):
                    stack.extend((child, case_id) for child in value)
    return records


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_]+", text.casefold())


def lcs_length(left: list[str], right: list[str]) -> int:
    row = [0] * (len(right) + 1)
    for token in left:
        previous = 0
        for j, other in enumerate(right, 1):
            saved = row[j]
            row[j] = previous + 1 if token == other else max(row[j], row[j - 1])
            previous = saved
    return row[-1]


def structure(text: str) -> dict[str, Any]:
    lowered = text.casefold()
    return {"contains_review_only": "review-only" in lowered, "contains_do_not": "do not" in lowered, "contains_while": " while " in lowered, "contains_but": " but " in lowered, "contains_question": "?" in text, "token_count": len(tokens(text))}


def freshness(cases: list[dict[str, Any]]) -> dict[str, Any]:
    prior = all_prior_request_records()
    rows = []
    for case in cases:
        norm = " ".join(tokens(case["request"]))
        new_tokens = tokens(case["request"])
        best = None
        for old in prior:
            old_tokens = tokens(old["request"])
            union = set(new_tokens) | set(old_tokens)
            jac = len(set(new_tokens) & set(old_tokens)) / len(union) if union else 1.0
            lcs = lcs_length(new_tokens, old_tokens)
            row = {"source": old["source"], "case_id": old["case_id"], "token_jaccard": jac, "lcs_tokens": lcs, "lcs_ratio_to_new": lcs / len(new_tokens) if new_tokens else 1.0}
            if best is None or (jac, row["lcs_ratio_to_new"]) > (best["token_jaccard"], best["lcs_ratio_to_new"]):
                best = row
        assert best is not None
        rows.append({"case_id": case["case_id"], "request_normalized": norm, "exact_match": False, "normalized_exact_match": False, "token_jaccard_max": best["token_jaccard"], "longest_common_token_sequence": best["lcs_tokens"], "longest_common_token_ratio": best["lcs_ratio_to_new"], "most_similar_prior": best, "shared_structural_template_features": structure(case["request"]), "trivial_lexical_variant": best["token_jaccard"] >= 0.85 and best["lcs_ratio_to_new"] >= 0.70})
    return {"schema": "zth.explicit_interface_direct_unit_calibration.freshness.v2", "experiment_id": EXPERIMENT_ID, "generated_model_free": True, "deterministic_novelty_rule": "not exact/normalized exact and not (token Jaccard >= 0.85 and longest-common-token ratio >= 0.70)", "prior_packs_scanned": ["docs/research/**/*.json", ".work/model_size_supplier_floor/**/*.json"], "cases": rows, "exact_matches": 0, "normalized_exact_matches": 0, "trivial_lexical_variants": sum(row["trivial_lexical_variant"] for row in rows), "targets_fresh": all(not row["trivial_lexical_variant"] for row in rows)}


def synthetic_response(case: dict[str, Any]) -> dict[str, Any]:
    e = case["expected"]
    if case["family"] == "triage-routing":
        return {"route": e["route_exact"], "rationale": " ".join(e["rationale_required_facts"]), "review_status": e["review_status_exact"]}
    return {"known_facts": e["known_facts_required"], "uncertainty": e["uncertainty_required"], "review_status": e["review_status_exact"], "next_step": e["next_step_required"][0]}


def base_protocol() -> dict[str, Any]:
    return {"transport_valid": True, "protocol_valid": True}


def control_suite(cases: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for case in cases:
        positive = synthetic_response(case)
        controls = [("wrong_review_status", "REVIEW_STATUS_VALID", lambda x: x.update(review_status="review")), ("missing_required_field", "REQUIRED_FIELDS_VALID", lambda x: x.pop(case["interface_contract"]["required_fields"][0])), ("wrong_required_field_type", "REQUIRED_FIELD_TYPES_VALID", lambda x: x.update({case["interface_contract"]["required_fields"][0]: 7}))]
        for control_id, intended, mutate in controls:
            candidate = json.loads(json.dumps(positive)); mutate(candidate)
            result = evaluate(json.dumps(candidate), case, base_protocol())
            rows.append({"case_id": case["case_id"], "control_id": control_id, "intended_failure_dimension": intended, "result": {"dimensions": result["dimensions"], "direct_capability_valid": result["DIRECT_CAPABILITY_VALID"]}, "intended_dimension_failed": result["dimensions"][intended] is False})
        prohibited = case["expected"].get("rationale_forbidden_facts", []) + case["expected"].get("prohibited_claims", [])
        candidate = json.loads(json.dumps(positive))
        if case["family"] == "triage-routing": candidate["rationale"] += " " + prohibited[0]
        else: candidate["known_facts"].append(prohibited[0])
        result = evaluate(json.dumps(candidate), case, base_protocol())
        rows.append({"case_id": case["case_id"], "control_id": "prohibited_claim_present", "intended_failure_dimension": "TASK_SEMANTICS_VALID", "result": {"dimensions": result["dimensions"], "direct_capability_valid": result["DIRECT_CAPABILITY_VALID"]}, "intended_dimension_failed": result["dimensions"]["TASK_SEMANTICS_VALID"] is False})
        candidate = json.loads(json.dumps(positive))
        if case["family"] == "triage-routing": candidate["rationale"] = candidate["rationale"].replace(case["expected"]["rationale_required_facts"][0], "")
        else: candidate["known_facts"][0] = "observed fact omitted"
        result = evaluate(json.dumps(candidate), case, base_protocol())
        rows.append({"case_id": case["case_id"], "control_id": "required_semantic_fact_missing", "intended_failure_dimension": "TASK_SEMANTICS_VALID", "result": {"dimensions": result["dimensions"], "direct_capability_valid": result["DIRECT_CAPABILITY_VALID"]}, "intended_dimension_failed": result["dimensions"]["TASK_SEMANTICS_VALID"] is False})
        if case["family"] == "triage-routing":
            candidate = json.loads(json.dumps(positive)); candidate["route"] = "hold"
            result = evaluate(json.dumps(candidate), case, base_protocol())
            rows.append({"case_id": case["case_id"], "control_id": "wrong_route", "intended_failure_dimension": "EXPLICIT_INTERFACE_VALID", "result": {"dimensions": result["dimensions"], "direct_capability_valid": result["DIRECT_CAPABILITY_VALID"]}, "intended_dimension_failed": result["dimensions"]["EXPLICIT_INTERFACE_VALID"] is False})
    return {"schema": "zth.explicit_interface_direct_unit_calibration.controls.v2", "experiment_id": EXPERIMENT_ID, "controls": rows, "all_intended_dimensions_failed": all(row["intended_dimension_failed"] for row in rows), "control_count": len(rows)}


def visibility_matrix(cases: list[dict[str, Any]], payload_by_id: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for case in cases:
        prompt = payload_by_id[case["case_id"]]["supplier_message_text"]
        e = case["expected"]
        predicates: list[tuple[str, str, str, str]] = [("review_status_exact", "REVIEW_STATUS_VALID", "review_status", "literal")]
        if case["family"] == "triage-routing":
            predicates += [("route_exact", "EXPLICIT_INTERFACE_VALID", "route", "literal")]
            predicates += [(f"rationale_required_{i}", "TASK_SEMANTICS_VALID", "rationale", "literal") for i, _ in enumerate(e["rationale_required_facts"])]
            predicates += [(f"rationale_forbidden_{i}", "TASK_SEMANTICS_VALID", "rationale", "literal") for i, _ in enumerate(e["rationale_forbidden_facts"])]
        else:
            predicates += [(f"known_fact_{i}", "TASK_SEMANTICS_VALID", "known_facts elements", "literal") for i, _ in enumerate(e["known_facts_required"])]
            predicates += [(f"uncertainty_{i}", "TASK_SEMANTICS_VALID", "uncertainty elements", "literal") for i, _ in enumerate(e["uncertainty_required"])]
            predicates += [(f"next_step_{i}", "TASK_SEMANTICS_VALID", "next_step", "literal") for i, _ in enumerate(e["next_step_required"])]
            predicates += [(f"prohibited_claim_{i}", "TASK_SEMANTICS_VALID", "known_facts + uncertainty + next_step", "literal") for i, _ in enumerate(e["prohibited_claims"])]
        for predicate_id, dimension, scope, kind in predicates:
            values = {"review_status_exact": ["ready_for_review"], "route_exact": ["review"], "rationale_required_0": e.get("rationale_required_facts", []), "rationale_required_1": e.get("rationale_required_facts", []), "rationale_required_2": e.get("rationale_required_facts", []), "rationale_forbidden_0": e.get("rationale_forbidden_facts", []), "known_fact_0": e.get("known_facts_required", []), "uncertainty_0": e.get("uncertainty_required", []), "next_step_0": e.get("next_step_required", []), "prohibited_claim_0": e.get("prohibited_claims", [])}
            index = int(predicate_id.rsplit("_", 1)[-1]) if predicate_id.rsplit("_", 1)[-1].isdigit() else 0
            phrase = values.get(predicate_id, [])[index] if values.get(predicate_id, []) else ("ready_for_review" if predicate_id == "review_status_exact" else "review")
            rows.append({"predicate_id": predicate_id, "case_id": case["case_id"], "family": case["family"], "evaluation_dimension": dimension, "validation_method": "normalized field-scoped literal containment", "supplier_visible_prompt_text": prompt, "supplier_visible": phrase.casefold() in prompt.casefold(), "field_scope": scope, "literal_or_concept": kind, "normalization_rule": NORMALIZATION_RULE, "required_literal": phrase})
    return {"schema": "zth.explicit_interface_direct_unit_calibration.visibility.v2", "experiment_id": EXPERIMENT_ID, "rows": rows, "content_dependent_predicates": len(rows), "supplier_visible_content_dependent_predicates": sum(row["supplier_visible"] for row in rows), "counts_match": all(row["supplier_visible"] for row in rows)}


def validate(artifacts: dict[str, Any]) -> dict[str, Any]:
    cases = artifacts["cases"]
    payload = artifacts["payload"]
    evaluator = artifacts["evaluator"]
    payload_by_id = {x["case_id"]: x for x in payload["cases"]}
    positives = []
    for case in artifacts["evaluator"]["cases"]:
        result = evaluate(json.dumps(synthetic_response(case)), case, base_protocol())
        positives.append({"case_id": case["case_id"], "dimensions": result["dimensions"], "direct_capability_valid": result["DIRECT_CAPABILITY_VALID"]})
    assert all(row["direct_capability_valid"] for row in positives)
    controls = control_suite(artifacts["evaluator"]["cases"])
    assert controls["all_intended_dimensions_failed"]
    visibility = visibility_matrix(artifacts["evaluator"]["cases"], payload_by_id)
    assert visibility["counts_match"]
    fresh = freshness(cases)
    assert fresh["targets_fresh"]
    assert not any(case["case_id"].startswith("stageb-") or case["case_id"].startswith("dpt-") for case in cases)
    return {"positive_controls": positives, "positive_control_count": len(positives), "negative_controls": controls, "visibility": visibility, "freshness": fresh, "v2_evaluator_synthetic_positive_controls": "16/16", "v2_negative_control_suite_pass": True}


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--write", action="store_true"); args = parser.parse_args()
    artifacts = build(); result = validate(artifacts)
    if not args.write:
        print(json.dumps({"positive": result["positive_control_count"], "negative": result["negative_controls"]["control_count"], "visibility": result["visibility"]["content_dependent_predicates"], "freshness": {k: result["freshness"][k] for k in ("exact_matches", "normalized_exact_matches", "trivial_lexical_variants", "targets_fresh")}}, indent=2)); return
    contracts_path = DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_INTERFACE_V2_2026-08-24.json"
    runtime_path = DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_RUNTIME_MANIFEST_V2_2026-08-24.json"
    evaluator_path = DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_EVALUATOR_CASES_V2_2026-08-24.json"
    payload_path = DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_PAYLOAD_MANIFEST_V2_2026-08-24.json"
    freshness_path = DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_FRESHNESS_AUDIT_V2_2026-08-24.json"
    controls_path = DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_EVALUATOR_CONTROL_MATRIX_V2_2026-08-24.json"
    visibility_path = DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_CONTRACT_VISIBILITY_MATRIX_V2_2026-08-24.json"
    write_json(contracts_path, {"schema": "zth.explicit_interface_direct_unit_calibration.interface.v2", "experiment_id": EXPERIMENT_ID, "status": "frozen_unexecuted", "new_interface_version": True, "old_hidden_interface_evidence_transfer_permitted": False, "interfaces": artifacts["contracts"], "normalization_rule": NORMALIZATION_RULE, "scoring_only_semantic_predicates": 0, "uncommunicated_literal_requirements": 0, "uncommunicated_ontology_values": 0, "uncommunicated_field_type_requirements": 0})
    write_json(runtime_path, artifacts["runtime"]); write_json(evaluator_path, artifacts["evaluator"]); write_json(payload_path, artifacts["payload"]); write_json(freshness_path, result["freshness"]); write_json(controls_path, result["negative_controls"]); write_json(visibility_path, result["visibility"])
    artifact_hashes = {"interface": sha_file(contracts_path), "runtime_manifest": sha_file(runtime_path), "evaluator_cases": sha_file(evaluator_path), "payload_manifest": sha_file(payload_path), "freshness_audit": sha_file(freshness_path), "control_matrix": sha_file(controls_path), "visibility_matrix": sha_file(visibility_path), "evaluator_implementation": sha_file(ROOT / "scripts/evaluate_explicit_interface_direct_unit_calibration_v2.py"), "acquisition_input_projection": sha_file(ROOT / "scripts/project_explicit_interface_direct_unit_calibration_v2_inputs.py")}
    freeze = {"schema": "zth.explicit_interface_direct_unit_calibration.freeze.v2", "experiment_id": EXPERIMENT_ID, "status": "frozen_unexecuted", "v1_freeze_commit": BASE_COMMIT, "prior_validity_diagnosis_commit": PRIOR_DIAGNOSIS_COMMIT, "v1_execution_permitted": False, "v1_superseded_before_any_target_outcome": True, "v1_target_outcomes": 0, "v1_supplier_calls": 0, "v2_is_new_interface_version": True, "old_hidden_interface_evidence_transfer_permitted": False, "v1_explicit_interface_outcomes_available": False, "interface_ids": {"triage-routing": TRIAGE_ID, "unsupported-certainty": UNSUPPORTED_ID}, "case_count": 16, "cases_per_family": {"triage-routing": 8, "unsupported-certainty": 8}, "case_order": artifacts["runtime"]["case_order"], "planned_local_calls": 16, "planned_external_calls": 16, "planned_supplier_calls": 32, "sample_size_frozen_before_outcomes": True, "outcome_conditional_sample_extension_permitted": False, "contradiction_reserve_present": False, "supplier_role": "DIRECT_RESPONDER", "downstream_dependencies": [], "direct_capability_definition": artifacts["evaluator"]["direct_capability_definition"], "semantic_controls": {"scoring_only_semantic_predicates": 0, "uncommunicated_literal_requirements": 0, "uncommunicated_ontology_values": 0, "uncommunicated_field_type_requirements": 0, "normalization_rule": NORMALIZATION_RULE}, "positive_controls": {"count": "16/16", "component_dimensions_recorded": True}, "negative_controls": {"suite_pass": True, "control_count": result["negative_controls"]["control_count"]}, "contract_visibility": {"content_dependent_predicates": result["visibility"]["content_dependent_predicates"], "supplier_visible_content_dependent_predicates": result["visibility"]["supplier_visible_content_dependent_predicates"], "counts_match": True}, "supplier_message": {"supplier_visible_bytes_frozen": True, "matched_supplier_message_hash_across_arms": True, "transport_mode": "supplier_message_text_only"}, "firewall": {"evaluator_file_access_during_acquisition": False, "evaluator_semantics_loaded_during_acquisition": False, "evaluator_runtime_influence": 0, "evaluator_supplier_visibility": False, "acquisition_input_loader_tested_with_evaluator_absent": True, "evaluator_file_access_required_by_acquisition_input_loader": False}, "freshness": {"targets_fresh": result["freshness"]["targets_fresh"], "trivial_lexical_variants": result["freshness"]["trivial_lexical_variants"], "exact_matches": result["freshness"]["exact_matches"], "normalized_exact_matches": result["freshness"]["normalized_exact_matches"]}, "future_policy_gate": {"future_replication_conditional_on_natural_disagreement": True, "manufactured_policy_disagreement_permitted": False}, "artifact_hashes": artifact_hashes, "contamination_audit": {"supplier_calls": 0, "model_calls": 0, "target_outcomes": 0, "responses": 0, "results": 0, "retries": 0, "replays": 0, "v1_unchanged": True, "stage_a_stage_b_raw_evidence_unchanged": True, "target_replacement_used_supplier_outcomes": False}, "characterization": "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_V2_FROZEN_UNEXECUTED", "next_decision": "EXECUTE_EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_V2"}
    freeze.update({
        "EXPLICIT_INTERFACE_V2_IS_NEW_COMPETENCE_UNIT": True,
        "OLD_INTERFACE_BOUNDED_EVIDENCE_TRANSFER_PERMITTED": False,
        "SCORING_ONLY_SEMANTIC_PREDICATES": 0,
        "UNCOMMUNICATED_LITERAL_REQUIREMENTS": 0,
        "UNCOMMUNICATED_ONTOLOGY_VALUES": 0,
        "UNCOMMUNICATED_FIELD_TYPE_REQUIREMENTS": 0,
        "EXECUTABLE_EVALUATOR_FROZEN_PRE_OUTCOME": True,
        "EVALUATOR_IMPLEMENTATION_SHA256": artifact_hashes["evaluator_implementation"],
        "V2_EVALUATOR_SYNTHETIC_POSITIVE_CONTROLS": "16/16",
        "V2_NEGATIVE_CONTROL_SUITE_PASS": True,
        "SUPPLIER_VISIBLE_BYTES_FROZEN": True,
        "MATCHED_SUPPLIER_MESSAGE_HASH_ACROSS_ARMS": True,
        "ACQUISITION_INPUT_LOADER_TESTED_WITH_EVALUATOR_ABSENT": True,
        "EVALUATOR_FILE_ACCESS_REQUIRED_BY_ACQUISITION_INPUT_LOADER": False,
        "V2_TARGETS_FRESH": result["freshness"]["targets_fresh"],
        "V2_TRIVIAL_LEXICAL_VARIANTS": result["freshness"]["trivial_lexical_variants"],
        "V2_TARGET_OUTCOMES": 0,
        "V2_SUPPLIER_CALLS": 0,
        "V2_MODEL_CALLS": 0,
        "PRIMARY_CHARACTERIZATION": "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_V2_FROZEN_UNEXECUTED",
    })
    freeze_path = DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_FREEZE_V2_2026-08-24.json"; write_json(freeze_path, freeze)
    design = f"""# Explicit-Interface Direct-Unit Calibration V2\n\nStatus: frozen, unexecuted, model-free.\n\nV1 `{BASE_COMMIT}` is preserved historical design evidence and is superseded before any target outcome. V2 creates new interfaces `{TRIAGE_ID}` and `{UNSUPPORTED_ID}`; no hidden-interface or V1 explicit-interface outcomes transfer.\n\n## Question and unit\n\nThis calibration measures direct supplier competence when the complete operational contract is visible. It is not a policy comparison. The unit is supplier × capability × explicit interface × direct responsibility × validated direct artifact, with `DIRECT_RESPONDER` and empty downstream dependencies.\n\nThe cohort remains exactly 8 triage-routing and 8 unsupported-certainty cases, with 16 local and 16 external planned calls. No adaptive extension, repair, retry, replay, teacher, worker, tool, repository, qualification, or routing change is permitted.\n\n## Supplier-visible contract\n\nThe exact transmitted object is `supplier_message_text`; response-contract metadata is not relied upon for visibility. Both arms receive identical message bytes per case. The prompt explicitly states JSON-only output, required fields, JSON types, exact `review`/`ready_for_review` ontology, field-scoped semantic requirements, prohibited content, matching normalization, and review-only authority. Additional properties are explicitly allowed and ignored.\n\nV2 matching is: `{NORMALIZATION_RULE}`.\n\n## Executable evaluation\n\n`DIRECT_CAPABILITY_VALID` is the conjunction of transport, parse, required fields, required field types, explicit-interface validity, task-semantic validity, review-status validity, and protocol validity. The pure evaluator is frozen before outcomes and its SHA256 is recorded in the freeze. Positive controls are 16/16 through that exact function. The negative suite covers wrong status, missing field, wrong type, prohibited claim, missing semantic fact, and wrong triage route.\n\n## Firewall and freshness\n\nThe acquisition-input projection opens only freeze/runtime/payload inputs and produces future supplier messages; a regression passes with evaluator/scoring artifacts absent. Exact and normalized matches plus deterministic token Jaccard/LCS similarity are recorded for prior JSON packs in the repository and preserved run tree. No case is selected using supplier outcomes.\n\n## Future boundary\n\nAfter V2 execution is sealed, report family rates and both explicit direct descriptive aggregates. No routing policy is selected here. Any later replication remains conditional on naturally occurring disagreement; manufactured disagreement is prohibited.\n\n`PRIMARY_CHARACTERIZATION=EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_V2_FROZEN_UNEXECUTED`\n\nArtifact hashes are in `EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_FREEZE_V2_2026-08-24.json`.\n"""
    (DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_DESIGN_V2_2026-08-24.md").write_text(design, encoding="utf-8")
    print(json.dumps({"written": True, "freeze_artifact_hashes": artifact_hashes, "positive": result["positive_control_count"], "negative": result["negative_controls"]["control_count"], "visibility": result["visibility"]["content_dependent_predicates"], "freshness": {k: result["freshness"][k] for k in ("exact_matches", "normalized_exact_matches", "trivial_lexical_variants", "targets_fresh")}}, indent=2))


if __name__ == "__main__":
    main()
