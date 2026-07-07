#!/usr/bin/env python3
"""Deterministic end-to-end supervised bureaucracy chain smoke harness."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from local_harness.orchestration_packet import assemble_orchestration_packet, validate_orchestration_packet
from local_harness.prompt_patch_library import PromptPatchLibrary
from local_harness.render_model_prompt_packet import (
    build_model_prompt_output_contract,
    render_model_prompt_packet,
)
from local_harness.supervised_attempt_output_validator import (
    validate_supervised_attempt_output_against_contract,
    validate_supervised_attempt_output_validation_record,
)
from local_harness.supervised_downstream_use_gate import (
    build_supervised_downstream_use_gate_record,
    validate_supervised_downstream_use_gate_record,
)
from local_harness.supervised_handoff_packet import build_supervised_handoff_packet, validate_supervised_handoff_packet
from local_harness.supervised_model_attempt import build_supervised_model_attempt_record, validate_supervised_model_attempt_record
from local_harness.supervised_review_decision import build_supervised_review_decision_record, validate_supervised_review_decision_record
from local_harness.triage_packet_schema import validate_triage_packet
from local_harness.triage_router_rules import route_messy_input


REQUIRED_SMOKE_RECORD_KEYS = {
    "smoke_id",
    "smoke_status",
    "started_from",
    "completed_at",
    "chain",
    "artifacts",
    "checks",
    "diagnostics",
    "authority_boundaries",
    "provenance",
}
ALLOWED_SMOKE_STATUSES = {"passed", "failed"}
REQUIRED_CHAIN_KEYS = {
    "triage_id",
    "orchestration_id",
    "prompt_packet_id",
    "attempt_id",
    "validation_id",
    "decision_id",
    "gate_id",
    "handoff_id",
}
REQUIRED_ARTIFACT_KEYS = {
    "triage_packet",
    "orchestration_packet",
    "model_prompt_packet",
    "supervised_model_attempt",
    "output_validation",
    "review_decision",
    "downstream_use_gate",
    "handoff_packet",
}
REQUIRED_CHECK_IDS = {
    "triage_id_preserved",
    "orchestration_id_preserved",
    "prompt_packet_id_preserved",
    "attempt_id_preserved",
    "validation_id_preserved",
    "decision_id_preserved",
    "gate_id_preserved",
    "handoff_prepared_requires_allowed_gate",
    "validation_is_evidence_not_acceptance",
    "review_decision_no_execution_authority",
    "gate_no_execution_or_mutation_authority",
    "handoff_no_execution_mutation_patch_promotion_training_curriculum_authority",
    "review_required_persisted",
    "no_forbidden_authority_language",
    "synthetic_fixture_output_provenance",
}
REQUIRED_AUTHORITY_BOUNDARIES = [
    "Smoke test is not command execution authority.",
    "Smoke test is not file modification authority.",
    "Smoke test is not patch application authority.",
    "No automatic patch promotion authority is granted.",
    "No automatic training authority is granted.",
    "No default failure-to-curriculum capture authority is granted.",
    "All downstream use must remain supervised.",
]
FORBIDDEN_AUTHORITY_KEYS = {
    "execution_authority",
    "direct_file_modification_authority",
    "patch_application_authority",
    "auto_promote",
    "auto_train",
    "auto_curriculum_capture",
}
FORBIDDEN_AUTHORITY_TERMS = {
    "execution authority granted",
    "direct file modification authority granted",
    "patch application authority granted",
    "automatic patch promotion authority granted",
    "automatic training authority granted",
    "default failure-to-curriculum capture authority granted",
}


class SupervisedChainSmokeError(ValueError):
    """Raised when smoke chain artifacts are malformed or unsafe."""


def _require_nonempty_str(record: dict[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SupervisedChainSmokeError(f"record field {key!r} must be a non-empty string")
    return value


def _require_str_list(record: dict[str, Any], key: str, *, allow_empty: bool = False) -> list[str]:
    value = record.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise SupervisedChainSmokeError(f"record field {key!r} must be a list of non-empty strings")
    if not value and not allow_empty:
        raise SupervisedChainSmokeError(f"record field {key!r} must not be empty")
    return value


def _iter_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        items: list[str] = []
        for entry in value:
            items.extend(_iter_strings(entry))
        return items
    if isinstance(value, dict):
        items: list[str] = []
        for key, entry in value.items():
            if isinstance(key, str):
                items.append(key)
            items.extend(_iter_strings(entry))
        return items
    return []


def _build_chain_checks(*, chain: dict[str, str], artifacts: dict[str, Any]) -> list[dict[str, str]]:
    triage = artifacts["triage_packet"]
    orchestration = artifacts["orchestration_packet"]
    attempt = artifacts["supervised_model_attempt"]
    validation = artifacts["output_validation"]
    decision = artifacts["review_decision"]
    gate = artifacts["downstream_use_gate"]
    handoff = artifacts["handoff_packet"]

    check_results = [
        {
            "check_id": "triage_id_preserved",
            "status": "passed" if triage["triage_id"] == orchestration["triage_id"] == chain["triage_id"] else "failed",
            "message": "triage_id is preserved through triage and orchestration artifacts.",
        },
        {
            "check_id": "orchestration_id_preserved",
            "status": "passed" if orchestration["orchestration_id"] == attempt["orchestration_id"] == chain["orchestration_id"] else "failed",
            "message": "orchestration_id is preserved through attempt artifact.",
        },
        {
            "check_id": "prompt_packet_id_preserved",
            "status": "passed" if attempt["prompt_packet_id"] == validation["prompt_packet_id"] == decision["prompt_packet_id"] == gate["prompt_packet_id"] == handoff["prompt_packet_id"] == chain["prompt_packet_id"] else "failed",
            "message": "prompt_packet_id is preserved where applicable.",
        },
        {
            "check_id": "attempt_id_preserved",
            "status": "passed" if attempt["attempt_id"] == validation["attempt_id"] == decision["attempt_id"] == gate["attempt_id"] == handoff["attempt_id"] == chain["attempt_id"] else "failed",
            "message": "attempt_id is preserved from attempt through handoff.",
        },
        {
            "check_id": "validation_id_preserved",
            "status": "passed" if validation["validation_id"] == decision["validation_id"] == gate["validation_id"] == handoff["validation_id"] == chain["validation_id"] else "failed",
            "message": "validation_id is preserved from validation through handoff.",
        },
        {
            "check_id": "decision_id_preserved",
            "status": "passed" if decision["decision_id"] == gate["decision_id"] == handoff["decision_id"] == chain["decision_id"] else "failed",
            "message": "decision_id is preserved from review decision through handoff.",
        },
        {
            "check_id": "gate_id_preserved",
            "status": "passed" if gate["gate_id"] == handoff["gate_id"] == chain["gate_id"] else "failed",
            "message": "gate_id is preserved into handoff.",
        },
        {
            "check_id": "handoff_prepared_requires_allowed_gate",
            "status": "passed" if ((handoff["handoff_status"] == "prepared" and gate["gate_status"] == "allowed") or (handoff["handoff_status"] == "blocked" and gate["gate_status"] == "blocked")) else "failed",
            "message": "handoff_status prepared occurs only when gate_status is allowed.",
        },
        {
            "check_id": "validation_is_evidence_not_acceptance",
            "status": "passed" if validation["acceptance_status"] == "not_reviewed" else "failed",
            "message": "validation output remains evidence and does not imply acceptance.",
        },
        {
            "check_id": "review_decision_no_execution_authority",
            "status": "passed" if "no_command_execution" in decision["prohibited_downstream_use"] else "failed",
            "message": "review decision record does not grant execution authority.",
        },
        {
            "check_id": "gate_no_execution_or_mutation_authority",
            "status": "passed" if "no_command_execution" in gate["prohibited_downstream_use"] and "no_direct_file_modification" in gate["prohibited_downstream_use"] else "failed",
            "message": "downstream-use gate does not grant execution or mutation authority.",
        },
        {
            "check_id": "handoff_no_execution_mutation_patch_promotion_training_curriculum_authority",
            "status": "passed" if all(item in handoff["prohibited_downstream_use"] for item in ["no_command_execution", "no_direct_file_modification", "no_patch_application", "no_automatic_patch_promotion", "no_automatic_training", "no_default_failure_to_curriculum_capture"]) else "failed",
            "message": "handoff does not grant execution/mutation/patch/promotion/training/curriculum authority.",
        },
        {
            "check_id": "review_required_persisted",
            "status": "passed" if validation["review_required"] is True and decision["reviewer_metadata"]["review_required"] is True and gate["operator_metadata"]["review_required"] is True and handoff["operator_metadata"]["review_required"] is True else "failed",
            "message": "review_required remains true across validation, decision, gate, and handoff.",
        },
        {
            "check_id": "no_forbidden_authority_language",
            "status": "passed" if not any(term in value.lower() for term in FORBIDDEN_AUTHORITY_TERMS for value in _iter_strings(artifacts)) else "failed",
            "message": "no artifact contains forbidden authority language.",
        },
        {
            "check_id": "synthetic_fixture_output_provenance",
            "status": "passed" if attempt["provenance"].get("source") == "synthetic_fixture_output" else "failed",
            "message": "raw model output provenance is synthetic_fixture_output.",
        },
    ]
    return check_results


def validate_supervised_chain_smoke_record(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise SupervisedChainSmokeError("supervised chain smoke record must be a JSON object")

    missing = sorted(REQUIRED_SMOKE_RECORD_KEYS - set(record))
    if missing:
        raise SupervisedChainSmokeError(f"record missing required fields: {', '.join(missing)}")

    forbidden = sorted(FORBIDDEN_AUTHORITY_KEYS & set(record))
    if forbidden:
        raise SupervisedChainSmokeError(
            f"record contains forbidden authority fields: {', '.join(forbidden)}"
        )

    _require_nonempty_str(record, "smoke_id")
    _require_nonempty_str(record, "started_from")
    _require_nonempty_str(record, "completed_at")

    smoke_status = record.get("smoke_status")
    if smoke_status not in ALLOWED_SMOKE_STATUSES:
        raise SupervisedChainSmokeError("smoke_status must be 'passed' or 'failed'")

    chain = record.get("chain")
    if not isinstance(chain, dict):
        raise SupervisedChainSmokeError("record field 'chain' must be an object")
    missing_chain = sorted(REQUIRED_CHAIN_KEYS - set(chain))
    if missing_chain:
        raise SupervisedChainSmokeError(
            "record chain missing required fields: " + ", ".join(missing_chain)
        )
    for key in sorted(REQUIRED_CHAIN_KEYS):
        _require_nonempty_str(chain, key)

    artifacts = record.get("artifacts")
    if not isinstance(artifacts, dict):
        raise SupervisedChainSmokeError("record field 'artifacts' must be an object")
    missing_artifacts = sorted(REQUIRED_ARTIFACT_KEYS - set(artifacts))
    if missing_artifacts:
        raise SupervisedChainSmokeError(
            "record artifacts missing required fields: " + ", ".join(missing_artifacts)
        )

    validate_triage_packet(artifacts["triage_packet"], model_facing=True)

    patch_library = PromptPatchLibrary()
    patch_library.load_dir("examples/prompt_patches")
    validate_orchestration_packet(artifacts["orchestration_packet"], patch_library)

    if not isinstance(artifacts["model_prompt_packet"], str) or not artifacts["model_prompt_packet"].strip():
        raise SupervisedChainSmokeError("artifacts.model_prompt_packet must be a non-empty string")

    validate_supervised_model_attempt_record(artifacts["supervised_model_attempt"])
    validate_supervised_attempt_output_validation_record(artifacts["output_validation"])
    validate_supervised_review_decision_record(artifacts["review_decision"])
    validate_supervised_downstream_use_gate_record(artifacts["downstream_use_gate"])
    validate_supervised_handoff_packet(artifacts["handoff_packet"])

    checks = record.get("checks")
    if not isinstance(checks, list) or not checks:
        raise SupervisedChainSmokeError("record field 'checks' must be a non-empty list")

    found_check_ids: set[str] = set()
    for check in checks:
        if not isinstance(check, dict):
            raise SupervisedChainSmokeError("each check must be an object")
        check_id = check.get("check_id")
        status = check.get("status")
        message = check.get("message")
        if not isinstance(check_id, str) or not check_id.strip():
            raise SupervisedChainSmokeError("check.check_id must be a non-empty string")
        if status not in {"passed", "failed"}:
            raise SupervisedChainSmokeError("check.status must be 'passed' or 'failed'")
        if not isinstance(message, str) or not message.strip():
            raise SupervisedChainSmokeError("check.message must be a non-empty string")
        found_check_ids.add(check_id)

    missing_required_checks = sorted(REQUIRED_CHECK_IDS - found_check_ids)
    if missing_required_checks:
        raise SupervisedChainSmokeError(
            "record checks missing required check_id values: " + ", ".join(missing_required_checks)
        )

    if smoke_status == "passed" and any(check["status"] != "passed" for check in checks):
        raise SupervisedChainSmokeError(
            "smoke_status cannot be 'passed' when any required check failed"
        )

    diagnostics = record.get("diagnostics")
    if not isinstance(diagnostics, list):
        raise SupervisedChainSmokeError("record field 'diagnostics' must be a list")
    if not all(isinstance(item, str) and item.strip() for item in diagnostics):
        raise SupervisedChainSmokeError("diagnostics must contain non-empty strings")

    authority_boundaries = _require_str_list(record, "authority_boundaries")
    missing_boundaries = [
        boundary for boundary in REQUIRED_AUTHORITY_BOUNDARIES if boundary not in authority_boundaries
    ]
    if missing_boundaries:
        raise SupervisedChainSmokeError(
            "record missing required authority boundaries: " + ", ".join(missing_boundaries)
        )

    provenance = record.get("provenance")
    if not isinstance(provenance, dict) or not provenance:
        raise SupervisedChainSmokeError("record field 'provenance' must be a non-empty object")
    if not isinstance(provenance.get("source"), str) or not provenance["source"].strip():
        raise SupervisedChainSmokeError("provenance.source must be a non-empty string")

    if chain["triage_id"] != artifacts["triage_packet"]["triage_id"]:
        raise SupervisedChainSmokeError("chain.triage_id must match artifacts.triage_packet.triage_id")
    if chain["orchestration_id"] != artifacts["orchestration_packet"]["orchestration_id"]:
        raise SupervisedChainSmokeError(
            "chain.orchestration_id must match artifacts.orchestration_packet.orchestration_id"
        )
    if chain["attempt_id"] != artifacts["supervised_model_attempt"]["attempt_id"]:
        raise SupervisedChainSmokeError(
            "chain.attempt_id must match artifacts.supervised_model_attempt.attempt_id"
        )
    if chain["validation_id"] != artifacts["output_validation"]["validation_id"]:
        raise SupervisedChainSmokeError(
            "chain.validation_id must match artifacts.output_validation.validation_id"
        )
    if chain["decision_id"] != artifacts["review_decision"]["decision_id"]:
        raise SupervisedChainSmokeError(
            "chain.decision_id must match artifacts.review_decision.decision_id"
        )
    if chain["gate_id"] != artifacts["downstream_use_gate"]["gate_id"]:
        raise SupervisedChainSmokeError(
            "chain.gate_id must match artifacts.downstream_use_gate.gate_id"
        )
    if chain["handoff_id"] != artifacts["handoff_packet"]["handoff_id"]:
        raise SupervisedChainSmokeError(
            "chain.handoff_id must match artifacts.handoff_packet.handoff_id"
        )

    lowered_strings = [value.lower() for value in _iter_strings(record)]
    for term in sorted(FORBIDDEN_AUTHORITY_TERMS):
        if any(term in value for value in lowered_strings):
            raise SupervisedChainSmokeError(f"record contains forbidden authority language: {term}")

    return record


def build_supervised_chain_smoke_record(
    *,
    smoke_id: str,
    started_from: str,
    completed_at: str,
    artifacts: dict[str, Any],
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    checks = _build_chain_checks(
        chain={
            "triage_id": artifacts["triage_packet"]["triage_id"],
            "orchestration_id": artifacts["orchestration_packet"]["orchestration_id"],
            "prompt_packet_id": artifacts["supervised_model_attempt"]["prompt_packet_id"],
            "attempt_id": artifacts["supervised_model_attempt"]["attempt_id"],
            "validation_id": artifacts["output_validation"]["validation_id"],
            "decision_id": artifacts["review_decision"]["decision_id"],
            "gate_id": artifacts["downstream_use_gate"]["gate_id"],
            "handoff_id": artifacts["handoff_packet"]["handoff_id"],
        },
        artifacts=artifacts,
    )

    diagnostics = [check["message"] for check in checks if check["status"] == "failed"]

    record = {
        "smoke_id": smoke_id,
        "smoke_status": "passed" if not diagnostics else "failed",
        "started_from": started_from,
        "completed_at": completed_at,
        "chain": {
            "triage_id": artifacts["triage_packet"]["triage_id"],
            "orchestration_id": artifacts["orchestration_packet"]["orchestration_id"],
            "prompt_packet_id": artifacts["supervised_model_attempt"]["prompt_packet_id"],
            "attempt_id": artifacts["supervised_model_attempt"]["attempt_id"],
            "validation_id": artifacts["output_validation"]["validation_id"],
            "decision_id": artifacts["review_decision"]["decision_id"],
            "gate_id": artifacts["downstream_use_gate"]["gate_id"],
            "handoff_id": artifacts["handoff_packet"]["handoff_id"],
        },
        "artifacts": deepcopy(artifacts),
        "checks": checks,
        "diagnostics": diagnostics,
        "authority_boundaries": list(REQUIRED_AUTHORITY_BOUNDARIES),
        "provenance": deepcopy(provenance)
        if provenance is not None
        else {
            "source": "supervised_chain_smoke",
            "fixture": "examples/supervised_chain_smoke/supervised_chain_smoke_example_001.json",
        },
    }
    return validate_supervised_chain_smoke_record(record)


def run_supervised_chain_smoke(
    *,
    messy_input: str,
    smoke_id: str = "supervised_chain_smoke_example_001",
    triage_id: str = "triage_example_001",
    orchestration_id: str = "orch_example_001",
    prompt_packet_id: str = "prompt_packet_example_001",
    attempt_id: str = "attempt_example_001",
    validation_id: str = "validation_example_001",
    decision_id: str = "decision_example_001",
    gate_id: str = "gate_example_001",
    handoff_id: str = "handoff_example_001",
    completed_at: str = "2026-07-06T00:00:00Z",
    review_decision: str = "accepted",
) -> dict[str, Any]:
    patch_library = PromptPatchLibrary()
    patch_library.load_dir("examples/prompt_patches")

    triage_packet = route_messy_input(messy_input, triage_id=triage_id, source="supervised_chain_smoke")
    validate_triage_packet(triage_packet, model_facing=True)

    orchestration_packet = assemble_orchestration_packet(
        triage_packet,
        patch_library,
        orchestration_id=orchestration_id,
    )
    validate_orchestration_packet(orchestration_packet, patch_library)

    model_prompt_packet = render_model_prompt_packet(orchestration_packet, patch_library)
    output_contract = build_model_prompt_output_contract(orchestration_packet, patch_library)

    synthetic_raw_model_output = json.dumps(
        {
            "allowed_targets": ["docs/reports/"],
            "held_targets": [
                "production automation",
                "automatic curriculum capture",
                "automatic promotion",
                "implementation_packet",
            ],
            "scope_expansion_required": False,
            "claims": [
                "The request is a design-planning task involving LoRA and prompt injection.",
                "docs/reports/ is the only allowed target in this packet.",
            ],
            "evidence_basis": [
                "Task summary mentions matched keywords: lora, prompt injection.",
                "Allowed Targets lists docs/reports/.",
                "Held Targets lists production automation, automatic curriculum capture, automatic promotion, and implementation_packet.",
            ],
            "unverified_claims": [],
            "format": "json",
            "required_fields_present": True,
            "reason": "The output stays within the declared allowed target and keeps implementation, automation, promotion, training, and curriculum-capture work held.",
        },
        indent=2,
        sort_keys=True,
    )

    attempt_record = build_supervised_model_attempt_record(
        attempt_id=attempt_id,
        orchestration_id=orchestration_packet["orchestration_id"],
        triage_id=triage_packet["triage_id"],
        prompt_packet_id=prompt_packet_id,
        raw_model_output=synthetic_raw_model_output,
        model_metadata={
            "model_id": "synthetic_fixture_model",
            "model_size": "fixture",
            "provider": "none",
        },
        operator_metadata={
            "operator": "manual",
            "review_required": True,
        },
        provenance={
            "source": "synthetic_fixture_output",
            "input_artifact": "model_prompt_packet",
            "raw_output_preserved": True,
            "orchestration_id": orchestration_packet["orchestration_id"],
            "triage_id": triage_packet["triage_id"],
            "prompt_packet_id": prompt_packet_id,
        },
    )
    validate_supervised_model_attempt_record(attempt_record)

    output_validation = validate_supervised_attempt_output_against_contract(
        attempt_record=attempt_record,
        output_contract=output_contract,
        validation_id=validation_id,
        validated_at=completed_at,
    )
    validate_supervised_attempt_output_validation_record(output_validation)

    decision_record = build_supervised_review_decision_record(
        decision_id=decision_id,
        attempt_record=attempt_record,
        validation_record=output_validation,
        decision=review_decision,
        decision_reason="Validation evidence reviewed under supervised decision process.",
        decided_at=completed_at,
        reviewer_metadata={
            "reviewer": "manual",
            "review_required": True,
        },
    )
    validate_supervised_review_decision_record(decision_record)

    gate_record = build_supervised_downstream_use_gate_record(
        gate_id=gate_id,
        decision_record=decision_record,
        requested_downstream_use="next_supervised_step_input",
        operator_metadata={
            "operator": "manual",
            "review_required": True,
        },
        gate_reason="Downstream use remains bounded to supervised input handling.",
        gated_at=completed_at,
    )
    validate_supervised_downstream_use_gate_record(gate_record)

    handoff_packet = build_supervised_handoff_packet(
        handoff_id=handoff_id,
        gate_record=gate_record,
        next_step_type="next_supervised_step_input",
        next_step_summary="Use reviewed output as bounded input for the next supervised planning step.",
        handoff_payload={
            "payload_kind": "reviewed_model_output_reference",
        },
        operator_metadata={
            "operator": "manual",
            "review_required": True,
        },
        handoff_reason="Gate outcome determines whether bounded supervised handoff is prepared.",
    )
    validate_supervised_handoff_packet(handoff_packet)

    artifacts = {
        "triage_packet": triage_packet,
        "orchestration_packet": orchestration_packet,
        "model_prompt_packet": model_prompt_packet,
        "supervised_model_attempt": attempt_record,
        "output_validation": output_validation,
        "review_decision": decision_record,
        "downstream_use_gate": gate_record,
        "handoff_packet": handoff_packet,
    }

    return build_supervised_chain_smoke_record(
        smoke_id=smoke_id,
        started_from="messy_input_fixture",
        completed_at=completed_at,
        artifacts=artifacts,
    )
