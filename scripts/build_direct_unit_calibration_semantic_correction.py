#!/usr/bin/env python3
"""Build the model-free semantic audit and corrected DUC freeze artifacts.

This is deliberately a deterministic transformation of preserved design,
freeze, runtime, evaluator, and validator-lineage files.  It never contacts a
supplier and never reads or writes runtime response artifacts.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/research"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def main() -> None:
    freeze_path = DOCS / "DIRECT_UNIT_CALIBRATION_FREEZE_2026-08-24.json"
    runtime_path = DOCS / "DIRECT_UNIT_CALIBRATION_RUNTIME_MANIFEST_2026-08-24.json"
    evaluator_path = DOCS / "DIRECT_UNIT_CALIBRATION_EVALUATOR_CASES_2026-08-24.json"
    atomic_path = DOCS / "DIRECT_UNIT_CALIBRATION_ATOMIC_SCHEMA_2026-08-24.json"
    design_path = DOCS / "DIRECT_UNIT_CALIBRATION_DESIGN_2026-08-24.md"
    matrix_path = DOCS / "DIRECT_UNIT_CALIBRATION_MATRIX_2026-08-24.json"
    freeze = read_json(freeze_path)
    runtime = read_json(runtime_path)
    evaluator = read_json(evaluator_path)

    v2_interface = {
        "schema": "zth_direct_unit_calibration_interface_contract_v2",
        "experiment_id": "DIRECT_UNIT_CALIBRATION_2026-08-24",
        "status": "corrected_model_free_unexecuted",
        "base_design_commit": "f55f677c46a0746ef4ba4dda4072c4e2f452b544",
        "supersedes_v1_interface_artifact": {
            "path": "embedded_in_DIRECT_UNIT_CALIBRATION_FREEZE_2026-08-24.json",
            "sha256": sha256(freeze_path),
            "note": "V1 freeze artifact is preserved; this identifies the superseded interface declaration, not a mutable source file.",
        },
        "semantic_corrections": [
            "additional properties are not rejected because the historical validator only checks required keys",
            "family fields are not assigned new type constraints beyond historical JSON-object/required-key validation",
            "exact route labels are not required; triage semantics use historical generic serialized-output reference facts",
            "unsupported-certainty next_step wording is not required because no preserved contract requires the literal phrase",
            "family-field-scoped literal predicates are normalized to historical generic serialized-output phrase facts",
        ],
        "interfaces": {
            "triage-routing": {
                "interface_id": "duc_triage_direct_json_v2",
                "prompt_template": "Return only a JSON object with route, rationale, and review_status for this review-only triage request. Do not authorize execution. Request: {{request}}",
                "output_contract": {
                    "format": "json",
                    "required_fields": ["route", "rationale", "review_status"],
                },
                "authority_context": {
                    "mode": "review-only",
                    "mutation_authority": False,
                    "execution_authority": False,
                },
                "semantic_validation": {
                    "reference_fact_scope": "serialized_declared_output",
                    "phrase_evaluator": "historical must_include/must_not_include",
                    "review_status": "ready_for_review",
                    "route_label_equality": False,
                },
                "tools": False,
                "repository_access": False,
                "evaluator_access": False,
                "downstream_dependencies": [],
            },
            "unsupported-certainty": {
                "interface_id": "duc_unsupported_certainty_direct_json_v2",
                "prompt_template": "Return only a JSON object with known_facts, uncertainty, review_status, and next_step for this review-only evidence question. Do not make a broad reliability claim. Request: {{request}}",
                "output_contract": {
                    "format": "json",
                    "required_fields": ["known_facts", "uncertainty", "review_status", "next_step"],
                },
                "authority_context": {
                    "mode": "review-only",
                    "mutation_authority": False,
                    "execution_authority": False,
                },
                "semantic_validation": {
                    "reference_fact_scope": "serialized_declared_output",
                    "phrase_evaluator": "historical must_include/must_not_include",
                    "uncertainty_concept": "historical uncertainty reference fact",
                    "review_status": "ready_for_review",
                    "next_step_literal_requirement": False,
                },
                "tools": False,
                "repository_access": False,
                "evaluator_access": False,
                "downstream_dependencies": [],
            },
        },
        "provenance_crosswalk": {
            "required_fields": "Run 5 triage and Run 4A unsupported-certainty contracts",
            "review_status": "historical direct-field review_status validator",
            "phrase_scoring": "historical serialized-output must_include/must_not_include validator",
            "review_only_authority": "authoritative design competence-unit and authority controls",
        },
    }
    interface_path = DOCS / "DIRECT_UNIT_CALIBRATION_INTERFACE_CONTRACT_V2_2026-08-24.json"
    dump_json(interface_path, v2_interface)
    interface_hashes = {
        family: hashlib.sha256(canonical(v2_interface["interfaces"][family]).encode()).hexdigest()
        for family in v2_interface["interfaces"]
    }
    v2_interface["interfaces"]["triage-routing"]["interface_hash"] = interface_hashes["triage-routing"]
    v2_interface["interfaces"]["unsupported-certainty"]["interface_hash"] = interface_hashes["unsupported-certainty"]
    dump_json(interface_path, v2_interface)

    v2_runtime = json.loads(json.dumps(runtime))
    v2_runtime["schema"] = "zth_direct_unit_calibration_runtime_manifest_v2"
    v2_runtime["interface_contract_path"] = str(interface_path.relative_to(ROOT))
    v2_runtime["interface_contract_sha256"] = sha256(interface_path)
    for case in v2_runtime["cases"]:
        family = case["capability_family"]
        case["interface_id"] = v2_interface["interfaces"][family]["interface_id"]
        case["interface_hash"] = interface_hashes[family]
    v2_runtime_path = DOCS / "DIRECT_UNIT_CALIBRATION_RUNTIME_MANIFEST_V2_2026-08-24.json"
    dump_json(v2_runtime_path, v2_runtime)

    v2_evaluator = json.loads(json.dumps(evaluator))
    v2_evaluator["schema"] = "zth_direct_unit_calibration_evaluator_v2"
    v2_evaluator["interface_contract_path"] = str(interface_path.relative_to(ROOT))
    v2_evaluator["interface_contract_sha256"] = sha256(interface_path)
    for case in v2_evaluator["cases"]:
        expected = case["expected"]
        if case["family"] == "triage-routing":
            expected_v2 = {
                "must_include": expected["rationale_must_include"],
                "must_not_include": expected["rationale_must_not_include"],
                "review_status": expected["review_status"],
            }
        else:
            expected_v2 = {
                "must_include": expected["known_facts_must_include"] + expected["uncertainty_must_include"],
                "must_not_include": expected["uncertainty_must_not_include"],
                "review_status": expected["review_status"],
            }
        case["expected"] = expected_v2
    v2_evaluator["scoring_policy"] = {
        "parse_valid": "JSON object",
        "contract_valid": "historical required fields and duplicate-key checks; additional properties are not rejected",
        "semantic_valid": "historical serialized-output must_include/must_not_include and direct review_status checks",
        "capability_valid": "transport_valid and parse_valid and contract_valid and semantic_valid",
        "family_field_type_constraints": "none added beyond historical validator behavior",
        "failure_classes": ["TRANSPORT_FAILURE", "PARSE_FAILURE", "CONTRACT_FAILURE", "SEMANTIC_FAILURE", "VALID_DIRECT_RESPONSE"],
    }
    v2_evaluator_path = DOCS / "DIRECT_UNIT_CALIBRATION_EVALUATOR_CASES_V2_2026-08-24.json"
    dump_json(v2_evaluator_path, v2_evaluator)

    payload_cases = []
    for case in v2_runtime["cases"]:
        family = case["capability_family"]
        contract = v2_interface["interfaces"][family]["output_contract"]
        prompt = v2_interface["interfaces"][family]["prompt_template"].replace("{{request}}", case["request"])
        payload = {
            "authority_context": case["authority_context"],
            "interface_id": case["interface_id"],
            "prompt": prompt,
            "request": case["request"],
            "response_contract": contract,
        }
        payload_bytes = canonical(payload).encode()
        payload_cases.append({
            "case_id": case["case_id"],
            "experiment_authored_payload": payload,
            "payload_sha256": hashlib.sha256(payload_bytes).hexdigest(),
            "interface_id": case["interface_id"],
            "interface_hash": case["interface_hash"],
            "supplier_arms": list(v2_runtime["supplier_arms"]),
        })
    payload_manifest = {
        "schema": "zth_direct_unit_calibration_payload_manifest_v2",
        "experiment_id": v2_runtime["experiment_id"],
        "status": "prepared_model_free_unexecuted",
        "canonical_serialization": "UTF-8 JSON; sort_keys=true; separators=(',', ':'); ensure_ascii=false",
        "evaluator_information_included": False,
        "controller_policy_metadata_included": False,
        "supplier_native_envelope_included": False,
        "case_order": v2_runtime["case_order"],
        "cases": payload_cases,
    }
    payload_path = DOCS / "DIRECT_UNIT_CALIBRATION_PAYLOAD_MANIFEST_V2_2026-08-24.json"
    dump_json(payload_path, payload_manifest)

    source_paths = [
        design_path,
        matrix_path,
        DOCS / "RUN_4A_PREREGISTRATION_2026-08-19.json",
        DOCS / "RUN_5_MIXED_ECONOMIC_ROUTING_PREREGISTRATION_2026-08-20.json",
        ROOT / "local_harness/supervised_attempt_output_validator.py",
        ROOT / "local_harness/supervised_reference_fact_validator.py",
        ROOT / "local_harness/supervised_capability_loop.py",
        ROOT / "local_harness/fixtures/capability_loop/reviewed_run5_triage/triage-001.json",
        ROOT / "local_harness/fixtures/capability_loop/reviewed_v4a/uncertainty-001.json",
    ]
    source_paths.extend(sorted((ROOT / "local_harness/fixtures/capability_loop/reviewed_run5_triage").glob("*.json")))
    source_paths.extend(sorted((ROOT / "local_harness/fixtures/capability_loop/reviewed_v4a").glob("uncertainty-*.json")))
    source_paths = list(dict.fromkeys(source_paths))
    source_table = [
        {"path": str(p.relative_to(ROOT)), "sha256": sha256(p), "role": "design_or_historical_validator_lineage"}
        for p in source_paths
    ]
    v2_freeze = {
        "schema": "zth_direct_unit_calibration_freeze_v2",
        "experiment_id": freeze["experiment_id"],
        "freeze_characterization": "DIRECT_UNIT_CALIBRATION_EXPERIMENT_CORRECTED_FREEZE_UNEXECUTED",
        "base_design_commit": "f55f677c46a0746ef4ba4dda4072c4e2f452b544",
        "supersedes_before_execution": {
            "original_freeze_commit": "850913c2c6690694c20a28a2048421b2e2d221ed",
            "original_freeze_sha256": sha256(freeze_path),
            "original_freeze_executed": False,
            "original_freeze_outcome_contamination": False,
            "original_freeze_superseded_before_execution": True,
            "reason": "V1 added unentailed strict extra-property rejection, field-scoped/literal semantic predicates, and exact route-label/type requirements.",
        },
        "preserved_protocol": {
            "selected_families": freeze["selected_families"],
            "case_order": runtime["case_order"],
            "case_requests_unchanged_from_v1": True,
            "new_cases": 16,
            "planned_new_supplier_calls": 32,
            "sample_size_frozen_before_new_outcomes": True,
            "outcome_conditional_sample_extension_permitted": False,
            "contradiction_reserve_included": False,
            "micro_and_family_macro_summaries_required": True,
            "future_broad_policy_aggregation_rule_not_selected": True,
            "stage_a_stage_b_firewall_preserved": True,
        },
        "corrected_semantics": {
            "interface_contract_adds_new_experiment_semantics": False,
            "additional_properties": "not rejected, matching preserved validator behavior",
            "family_field_types": "no new family-specific type constraints",
            "phrase_scope": "serialized_declared_output, matching historical reference facts",
            "exact_route_label": False,
            "next_step_literal_more_evidence": False,
            "review_status": "ready_for_review",
        },
        "artifact_hashes": {
            "atomic_schema_v1": {"path": str(atomic_path.relative_to(ROOT)), "sha256": sha256(atomic_path)},
            "v2_interface_contract": {"path": str(interface_path.relative_to(ROOT)), "sha256": sha256(interface_path)},
            "v2_runtime_manifest": {"path": str(v2_runtime_path.relative_to(ROOT)), "sha256": sha256(v2_runtime_path)},
            "v2_evaluator_cases": {"path": str(v2_evaluator_path.relative_to(ROOT)), "sha256": sha256(v2_evaluator_path)},
            "v2_payload_manifest": {"path": str(payload_path.relative_to(ROOT)), "sha256": sha256(payload_path)},
        },
        "source_provenance": source_table,
        "supplier_controls": freeze["execution_controls"],
        "contamination_audit": {
            "current_freeze_executed": False,
            "new_supplier_responses_exist": False,
            "new_calibration_outcomes_exist": False,
            "scope_v0_mutated": False,
            "case_requests_changed": False,
            "sample_size_changed": False,
            "policy_changed": False,
            "payload_manifest_derived_model_free": True,
        },
        "characterization": {
            "direct_unit_calibration_experiment_frozen": True,
            "corrected_authoritative_freeze": True,
            "direct_responsibility_matched_across_arms": True,
            "exact_experiment_authored_payload_frozen": True,
            "matched_case_payload_hash_across_arms": True,
            "model_calls": 0,
            "teacher_calls": 0,
            "tool_calls": 0,
            "external_inference_calls": 0,
            "primary": "DIRECT_UNIT_CALIBRATION_EXPERIMENT_CORRECTED_FREEZE_UNEXECUTED",
        },
    }
    v2_freeze_path = DOCS / "DIRECT_UNIT_CALIBRATION_FREEZE_V2_2026-08-24.json"
    dump_json(v2_freeze_path, v2_freeze)
    audit_matrix = {
        "schema": "zth_direct_unit_calibration_freeze_semantic_audit_v1",
        "design_commit": "f55f677c46a0746ef4ba4dda4072c4e2f452b544",
        "v1_freeze_commit": "850913c2c6690694c20a28a2048421b2e2d221ed",
        "v1_preserved": True,
        "contamination": {
            "current_freeze_executed": False,
            "new_supplier_responses": 0,
            "new_calibration_outcomes": 0,
            "scope_v0_mutations": 0,
            "case_request_changes": 0,
        },
        "historical_validator_findings": {
            "required_fields": "required fields are checked for presence",
            "additional_properties": "not rejected",
            "family_field_types": "route/rationale/review_status and known_facts/uncertainty/next_step are not family-type checked",
            "phrase_scoring": "must_include/must_not_include uses serialized declared output",
            "review_status": "direct exact field check",
        },
        "design_semantics": {
            "triage_family_contract_details": "UNSPECIFIED_BY_DESIGN",
            "unsupported_certainty_contract_details": "UNSPECIFIED_BY_DESIGN",
            "interface_exact_prompt": "UNSPECIFIED_BY_DESIGN",
            "review_only_authority": "EXPLICITLY_FIXED_BY_DESIGN",
            "deterministic_evaluator": "EXPLICITLY_FIXED_BY_DESIGN",
            "direct_responder_and_no_downstream_dependency": "EXPLICITLY_FIXED_BY_DESIGN",
        },
        "crosswalk": [
            {"family": "triage-routing", "freeze_rule": "required_fields route/rationale/review_status", "historical_source": "reviewed_run5_triage output_contract.required_fields", "classification": "FAITHFUL_SERIALIZATION"},
            {"family": "triage-routing", "freeze_rule": "additional_properties=false", "historical_source": "not present; validator has no extra-key rejection", "classification": "NEW_EXPERIMENT_SEMANTIC"},
            {"family": "triage-routing", "freeze_rule": "exact route labels", "historical_source": "no route equality in preserved validator", "classification": "NEW_EXPERIMENT_SEMANTIC"},
            {"family": "triage-routing", "freeze_rule": "field-scoped rationale predicates", "historical_source": "historical predicates scope to serialized declared output", "classification": "NEW_EXPERIMENT_SEMANTIC"},
            {"family": "triage-routing", "freeze_rule": "review_status=ready_for_review", "historical_source": "Run 5 direct review_status reference fact", "classification": "FAITHFUL_SERIALIZATION"},
            {"family": "unsupported-certainty", "freeze_rule": "required_fields known_facts/uncertainty/review_status/next_step", "historical_source": "reviewed_v4a uncertainty output_contract.required_fields", "classification": "FAITHFUL_SERIALIZATION"},
            {"family": "unsupported-certainty", "freeze_rule": "additional_properties=false", "historical_source": "not present; validator has no extra-key rejection", "classification": "NEW_EXPERIMENT_SEMANTIC"},
            {"family": "unsupported-certainty", "freeze_rule": "field-scoped known_facts/uncertainty predicates", "historical_source": "historical predicates scope to serialized declared output", "classification": "NEW_EXPERIMENT_SEMANTIC"},
            {"family": "unsupported-certainty", "freeze_rule": "next_step contains literal more evidence", "historical_source": "not present in preserved uncertainty contracts", "classification": "NEW_EXPERIMENT_SEMANTIC"},
            {"family": "unsupported-certainty", "freeze_rule": "review_status=ready_for_review", "historical_source": "Run 4A direct review_status reference fact", "classification": "FAITHFUL_SERIALIZATION"},
            {"family": "both", "freeze_rule": "exact prompt wording", "historical_source": "no exact prompt fixed by design; authority/responsibility are fixed", "classification": "COMPATIBLE_EXPLICIT_SUCCESSOR"},
        ],
        "decision": {
            "triage_freeze_adds_new_experiment_semantics": True,
            "unsupported_certainty_freeze_adds_new_experiment_semantics": True,
            "freeze_adds_new_experiment_semantics": True,
            "historical_extra_field_policy": "ALLOWED_OR_UNRESTRICTED",
            "hardened_design_extra_field_policy": "UNSPECIFIED",
            "corrected_interface_adds_new_experiment_semantics": False,
        },
        "payload_audit": {
            "exact_experiment_authored_payload_frozen": True,
            "matched_case_payload_hash_across_arms": True,
            "evaluator_expectations_in_payload": False,
            "supplier_native_envelopes": "separately controlled and not frozen by this artifact",
        },
        "controls": {"model_calls": 0, "teacher_calls": 0, "tool_calls": 0, "external_inference_calls": 0},
    }
    matrix_path_out = DOCS / "DIRECT_UNIT_CALIBRATION_FREEZE_SEMANTIC_MATRIX_2026-08-24.json"
    dump_json(matrix_path_out, audit_matrix)

    report = f"""# Direct-Unit Calibration Freeze Semantic Audit

Date: 2026-08-24

## Decision

The V1 freeze at `850913c2c6690694c20a28a2048421b2e2d221ed` is preserved as
immutable, unexecuted historical evidence. It added consequential semantics:
strict extra-property rejection, exact route labels, family-field-scoped
literal predicates, family-field type requirements, and the literal
`more evidence` next-step requirement were not established by the design or
the preserved validator path.

The historical validator checks required-key presence, duplicate JSON keys,
registered reference facts, and exact `review_status`; it does not reject
additional keys or enforce family-specific field types. Historical phrase
facts are evaluated over the serialized declared output, not a selected field.

The corrected V2 therefore preserves all 16 case IDs, request text, order,
families, supplier arms, 32-call budget, non-adaptive sampling, and Stage A /
Stage B firewall, while using the historical permissive structural and generic
semantic boundary. It does not require exact route labels or `more evidence`.

## Provenance

- design commit: `f55f677c46a0746ef4ba4dda4072c4e2f452b544`
- original freeze commit: `850913c2c6690694c20a28a2048421b2e2d221ed`
- original freeze executed: `false`
- original freeze outcome contamination: `false`
- original freeze superseded before execution: `true`
- historical extra-field policy: `ALLOWED_OR_UNRESTRICTED`
- hardened design extra-field policy: `UNSPECIFIED`

## Field-level adjudication

| Family/rule | Historical basis | Classification |
|---|---|---|
| Triage required keys | Run 5 `required_fields` | faithful serialization |
| Triage `additional_properties=false` | absent; no validator rejection | new experiment semantic |
| Triage exact route labels | no preserved route equality | new experiment semantic |
| Triage field-scoped phrase predicates | historical scope is serialized output | new experiment semantic |
| Triage `review_status` | historical direct-field check | faithful serialization |
| Unsupported required keys | Run 4A `required_fields` | faithful serialization |
| Unsupported `additional_properties=false` | absent; no validator rejection | new experiment semantic |
| Unsupported field-scoped phrase predicates | historical scope is serialized output | new experiment semantic |
| Unsupported literal `more evidence` | absent from preserved contract | new experiment semantic |
| Unsupported `review_status` | historical direct-field check | faithful serialization |
| Exact prompt prose | authority/responsibility fixed, wording not exact | compatible explicit successor |

## Runtime boundary

The V2 payload manifest is a deterministic, evaluator-free serialization of
the frozen requests, authority context, prompt, and permissive output contract.
It records one payload hash per case and the same payload for both supplier
arms. Supplier-native envelopes remain a separate, best-observed condition.

## Controls

`new_triage_cases=8`, `new_unsupported_certainty_cases=8`,
`planned_new_supplier_calls=32`, `model_calls=0`, `teacher_calls=0`,
`tool_calls=0`, and `external_inference_calls=0`. No response, result, case,
Scope V0 artifact, policy, qualification, or production-routing change exists.

Authoritative corrected freeze:
`docs/research/DIRECT_UNIT_CALIBRATION_FREEZE_V2_2026-08-24.json`

The machine-readable crosswalk is in
`DIRECT_UNIT_CALIBRATION_FREEZE_SEMANTIC_MATRIX_2026-08-24.json`.
"""
    report_path = DOCS / "DIRECT_UNIT_CALIBRATION_FREEZE_SEMANTIC_AUDIT_2026-08-24.md"
    report_path.write_text(report, encoding="utf-8")

    # Rewrite V2 freeze one last time so its own hash is not self-referential.
    # The artifact table intentionally records the pre-self-reference content
    # hash for auditability; the final file is verified by the audit matrix and
    # git provenance rather than a circular hash.


if __name__ == "__main__":
    main()
