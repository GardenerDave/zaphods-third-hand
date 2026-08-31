#!/usr/bin/env python3
"""Model-free output-contract validation for supervised model attempts."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from local_harness.supervised_model_attempt import (
    REQUIRED_AUTHORITY_BOUNDARIES as ATTEMPT_REQUIRED_AUTHORITY_BOUNDARIES,
)
from local_harness.supervised_model_attempt import (
    SupervisedModelAttemptError,
    validate_supervised_model_attempt_record,
)
from local_harness.validate_epistemic_observation_output import validate as validate_epistemic_observation_output


REQUIRED_VALIDATION_RECORD_KEYS = {
    "validation_id",
    "attempt_id",
    "triage_id",
    "orchestration_id",
    "validation_status",
    "acceptance_status",
    "validated_at",
    "output_contract",
    "checks",
    "diagnostics",
    "raw_output_preserved",
    "authority_boundaries",
    "provenance",
    "review_required",
}
VALIDATION_STATUSES = {"passed", "failed"}
CHECK_STATUSES = {"passed", "failed", "not_applicable"}
REQUIRED_VALIDATION_AUTHORITY_BOUNDARIES = [
    "Validation is evidence, not acceptance.",
    *ATTEMPT_REQUIRED_AUTHORITY_BOUNDARIES,
]
FORBIDDEN_AUTHORITY_KEYS = {
    "execution_authority",
    "direct_file_modification_authority",
    "auto_promote",
    "auto_train",
    "auto_curriculum_capture",
}
FORBIDDEN_AUTHORITY_TERMS = {
    "execution authority granted",
    "direct file modification authority granted",
    "automatic patch promotion authority granted",
    "automatic training authority granted",
    "default failure-to-curriculum capture authority granted",
    "output accepted for use",
    "accepted for downstream use",
}


class SupervisedAttemptOutputValidationError(ValueError):
    """Raised when output-validation records or inputs are malformed or unsafe."""


def _require_nonempty_str(record: dict[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SupervisedAttemptOutputValidationError(
            f"record field {key!r} must be a non-empty string"
        )
    return value


def _require_str_list(record: dict[str, Any], key: str) -> list[str]:
    value = record.get(key)
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise SupervisedAttemptOutputValidationError(
            f"record field {key!r} must be a list of non-empty strings"
        )
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


def validate_supervised_attempt_output_validation_record(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise SupervisedAttemptOutputValidationError("validation record must be a JSON object")

    missing = sorted(REQUIRED_VALIDATION_RECORD_KEYS - set(record))
    if missing:
        raise SupervisedAttemptOutputValidationError(
            f"record missing required fields: {', '.join(missing)}"
        )

    forbidden = sorted(FORBIDDEN_AUTHORITY_KEYS & set(record))
    if forbidden:
        raise SupervisedAttemptOutputValidationError(
            f"record contains forbidden authority fields: {', '.join(forbidden)}"
        )

    _require_nonempty_str(record, "validation_id")
    _require_nonempty_str(record, "attempt_id")
    _require_nonempty_str(record, "triage_id")
    _require_nonempty_str(record, "orchestration_id")
    if "prompt_packet_id" in record and record["prompt_packet_id"] is not None:
        _require_nonempty_str(record, "prompt_packet_id")

    validation_status = record.get("validation_status")
    if validation_status not in VALIDATION_STATUSES:
        raise SupervisedAttemptOutputValidationError("validation_status must be 'passed' or 'failed'")

    if record.get("acceptance_status") != "not_reviewed":
        raise SupervisedAttemptOutputValidationError("acceptance_status must be 'not_reviewed'")

    _require_nonempty_str(record, "validated_at")

    output_contract = record.get("output_contract")
    if not isinstance(output_contract, dict) or not output_contract:
        raise SupervisedAttemptOutputValidationError(
            "record field 'output_contract' must be a non-empty object"
        )

    checks = record.get("checks")
    if not isinstance(checks, list) or not checks:
        raise SupervisedAttemptOutputValidationError("record field 'checks' must be a non-empty list")
    for check in checks:
        if not isinstance(check, dict):
            raise SupervisedAttemptOutputValidationError("each check must be an object")
        check_id = check.get("check_id")
        status = check.get("status")
        message = check.get("message")
        if not isinstance(check_id, str) or not check_id.strip():
            raise SupervisedAttemptOutputValidationError("check.check_id must be a non-empty string")
        if status not in CHECK_STATUSES:
            raise SupervisedAttemptOutputValidationError("check.status must be 'passed' or 'failed'")
        if not isinstance(message, str) or not message.strip():
            raise SupervisedAttemptOutputValidationError("check.message must be a non-empty string")

    diagnostics = record.get("diagnostics")
    if not isinstance(diagnostics, list):
        raise SupervisedAttemptOutputValidationError("record field 'diagnostics' must be a list")
    if not all(isinstance(item, str) and item.strip() for item in diagnostics):
        raise SupervisedAttemptOutputValidationError("diagnostics must contain non-empty strings")

    if record.get("raw_output_preserved") is not True:
        raise SupervisedAttemptOutputValidationError("raw_output_preserved must be true")

    authority_boundaries = _require_str_list(record, "authority_boundaries")
    missing_boundaries = [
        boundary
        for boundary in REQUIRED_VALIDATION_AUTHORITY_BOUNDARIES
        if boundary not in authority_boundaries
    ]
    if missing_boundaries:
        raise SupervisedAttemptOutputValidationError(
            "record missing required authority boundaries: " + ", ".join(missing_boundaries)
        )

    provenance = record.get("provenance")
    if not isinstance(provenance, dict) or not provenance:
        raise SupervisedAttemptOutputValidationError(
            "record field 'provenance' must be a non-empty object"
        )
    if not isinstance(provenance.get("source"), str) or not provenance["source"].strip():
        raise SupervisedAttemptOutputValidationError("provenance.source must be a non-empty string")

    if record.get("review_required") is not True:
        raise SupervisedAttemptOutputValidationError("review_required must be true")

    if validation_status == "passed" and any(
        check["status"] not in {"passed", "not_applicable"} for check in checks
    ):
        raise SupervisedAttemptOutputValidationError(
            "validation_status cannot be 'passed' when any required check failed"
        )

    lowered_strings = [value.lower() for value in _iter_strings(record)]
    for term in sorted(FORBIDDEN_AUTHORITY_TERMS):
        if any(term in value for value in lowered_strings):
            raise SupervisedAttemptOutputValidationError(
                f"record contains forbidden authority language: {term}"
            )

    return record


def _check_required_fields(
    payload: dict[str, Any],
    required_fields: list[str],
) -> tuple[list[str], dict[str, Any]]:
    missing_fields = [field for field in required_fields if field not in payload]
    if missing_fields:
        return missing_fields, {
            "check_id": "required_fields",
            "status": "failed",
            "message": "Missing required fields: " + ", ".join(sorted(missing_fields)),
        }
    return [], {
        "check_id": "required_fields",
        "status": "passed",
        "message": "All required fields are present.",
    }


def _check_required_field_types(payload: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    field_specs: list[tuple[str, str, Any]] = [
        ("allowed_targets", "list", list),
        ("held_targets", "list", list),
        ("scope_expansion_required", "boolean", bool),
        ("claims", "list", list),
        ("evidence_basis", "list", list),
        ("unverified_claims", "list", list),
        ("format", 'exactly "json"', "json"),
        ("required_fields_present", "boolean true", True),
        ("reason", "non-empty string", str),
    ]
    problems: list[str] = []
    for field, expected_label, expected_type in field_specs:
        if field not in payload:
            continue
        value = payload[field]
        if expected_type is list:
            if not isinstance(value, list):
                problems.append(f"{field} must be a list")
            continue
        if expected_type is bool:
            if not isinstance(value, bool):
                problems.append(f"{field} must be a boolean")
            continue
        if expected_type is str:
            if not isinstance(value, str) or not value.strip():
                problems.append(f"{field} must be a non-empty string")
            continue
        if value != expected_type:
            problems.append(f"{field} must be {expected_label}")
    if problems:
        return problems, {
            "check_id": "required_field_types",
            "status": "failed",
            "message": "Invalid required field types or values: " + "; ".join(problems),
        }
    return [], {
        "check_id": "required_field_types",
        "status": "passed",
        "message": "Required fields have valid types and values.",
    }


def _is_observation_contract(output_contract: dict[str, Any]) -> bool:
    required_fields = output_contract.get("required_fields")
    return (
        output_contract.get("format") == "json"
        and isinstance(required_fields, list)
        and "findings" in required_fields
        and "reason" in required_fields
    )


def _is_epistemic_observation_contract(output_contract: dict[str, Any]) -> bool:
    required_fields = output_contract.get("required_fields")
    if not (
        output_contract.get("format") == "json"
        and isinstance(required_fields, list)
        and "conclusion" in required_fields
        and "findings" in required_fields
        and "reason" in required_fields
    ):
        return False
    properties = output_contract.get("properties")
    return isinstance(properties, dict) and "conclusion" in properties


def _check_observation_output(
    payload: dict[str, Any],
    *,
    projected_source_paths: list[str] | None,
) -> tuple[list[dict[str, str]], list[str]]:
    checks: list[dict[str, str]] = []
    diagnostics: list[str] = []
    findings = payload.get("findings")
    if not isinstance(findings, list):
        checks.append(
            {
                "check_id": "observation_findings",
                "status": "failed",
                "message": "findings must be a list.",
            }
        )
        diagnostics.append("findings must be a list.")
        return checks, diagnostics

    projected_set = {path for path in projected_source_paths or [] if isinstance(path, str) and path.strip()}
    for finding_index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            checks.append(
                {
                    "check_id": "observation_finding_shape",
                    "status": "failed",
                    "message": f"finding[{finding_index}] must be an object.",
                }
            )
            diagnostics.append(f"finding[{finding_index}] must be an object.")
            continue
        claim = finding.get("claim")
        if not isinstance(claim, str) or not claim.strip():
            checks.append(
                {
                    "check_id": "observation_claim",
                    "status": "failed",
                    "message": f"finding[{finding_index}].claim must be a non-empty string.",
                }
            )
            diagnostics.append(f"finding[{finding_index}].claim must be a non-empty string.")
        evidence = finding.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            checks.append(
                {
                    "check_id": "observation_evidence",
                    "status": "failed",
                    "message": f"finding[{finding_index}].evidence must be a non-empty list.",
                }
            )
            diagnostics.append(f"finding[{finding_index}].evidence must be a non-empty list.")
            continue
        for evidence_index, evidence_item in enumerate(evidence):
            if not isinstance(evidence_item, dict):
                checks.append(
                    {
                        "check_id": "observation_evidence_item",
                        "status": "failed",
                        "message": f"finding[{finding_index}].evidence[{evidence_index}] must be an object.",
                    }
                )
                diagnostics.append(
                    f"finding[{finding_index}].evidence[{evidence_index}] must be an object."
                )
                continue
            path = evidence_item.get("path")
            detail = evidence_item.get("detail")
            if not isinstance(path, str) or not path.strip():
                checks.append(
                    {
                        "check_id": "observation_evidence_path",
                        "status": "failed",
                        "message": f"finding[{finding_index}].evidence[{evidence_index}].path must be a non-empty string.",
                    }
                )
                diagnostics.append(
                    f"finding[{finding_index}].evidence[{evidence_index}].path must be a non-empty string."
                )
            elif projected_set and path not in projected_set:
                checks.append(
                    {
                        "check_id": "observation_grounding",
                        "status": "failed",
                        "message": f"finding[{finding_index}].evidence[{evidence_index}].path is not in the projected evidence set.",
                    }
                )
                diagnostics.append(f"cited evidence path not projected: {path}")
            if not isinstance(detail, str) or not detail.strip():
                checks.append(
                    {
                        "check_id": "observation_evidence_detail",
                        "status": "failed",
                        "message": f"finding[{finding_index}].evidence[{evidence_index}].detail must be a non-empty string.",
                    }
                )
                diagnostics.append(
                    f"finding[{finding_index}].evidence[{evidence_index}].detail must be a non-empty string."
                )

    if not findings:
        checks.append(
            {
                "check_id": "observation_findings",
                "status": "failed",
                "message": "findings must contain at least one item.",
            }
        )
        diagnostics.append("findings must contain at least one item.")
    else:
        checks.append(
            {
                "check_id": "observation_findings",
                "status": "passed",
                "message": "findings is a list.",
            }
        )
        if not any(check["status"] == "failed" and check["check_id"].startswith("observation_") for check in checks):
            checks.append(
                {
                    "check_id": "observation_schema",
                    "status": "passed",
                    "message": "Observation findings/evidence shape is valid.",
                }
            )

    if projected_set:
        checks.append(
            {
                "check_id": "observation_grounding",
                "status": "passed"
                if not any(check["check_id"] == "observation_grounding" and check["status"] == "failed" for check in checks)
                else "failed",
                "message": "All cited evidence paths resolve to projected evidence sources."
                if not any(check["check_id"] == "observation_grounding" and check["status"] == "failed" for check in checks)
                else "Some cited evidence paths were not in the projected evidence set.",
            }
        )
    return checks, diagnostics


def _check_allowed_held_target_separation(
    payload: dict[str, Any],
) -> tuple[list[str], dict[str, Any]]:
    allowed_targets = payload.get("allowed_targets")
    held_targets = payload.get("held_targets")
    if not isinstance(allowed_targets, list) or not isinstance(held_targets, list):
        return [], {
            "check_id": "allowed_held_target_separation",
            "status": "not_applicable",
            "message": "Allowed/held target separation requires list-valued allowed_targets and held_targets.",
        }

    overlap = sorted(
        {
            target
            for target in allowed_targets
            if isinstance(target, str)
            and target.strip()
            and target in held_targets
        }
    )
    if overlap:
        return overlap, {
            "check_id": "allowed_held_target_separation",
            "status": "failed",
            "message": "Target cannot be both allowed and held: " + ", ".join(overlap),
        }
    return [], {
        "check_id": "allowed_held_target_separation",
        "status": "passed",
        "message": "Allowed and held targets are separated.",
    }


def _parse_json_with_duplicate_key_detection(raw_text: str) -> tuple[Any, list[str]]:
    duplicate_keys: list[str] = []

    def object_pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        obj: dict[str, Any] = {}
        for key, value in pairs:
            if key in obj and key not in duplicate_keys:
                duplicate_keys.append(key)
            obj[key] = value
        return obj

    parsed = json.loads(raw_text, object_pairs_hook=object_pairs_hook)
    return parsed, duplicate_keys


def validate_supervised_attempt_output_against_contract(
    *,
    attempt_record: dict[str, Any],
    output_contract: dict[str, Any],
    validation_id: str,
    validated_at: str,
    authorized_targets: list[str] | None = None,
    authoritative_held_targets: list[str] | None = None,
    projected_source_paths: list[str] | None = None,
) -> dict[str, Any]:
    try:
        validated_attempt = validate_supervised_model_attempt_record(attempt_record)
    except SupervisedModelAttemptError as exc:
        if "acceptance_status must be 'not_reviewed'" in str(exc):
            raise SupervisedAttemptOutputValidationError(
                "input attempt must not be accepted before output-contract validation"
            ) from exc
        raise SupervisedAttemptOutputValidationError(str(exc)) from exc

    if validated_attempt.get("acceptance_status") != "not_reviewed":
        raise SupervisedAttemptOutputValidationError(
            "input attempt must not be accepted before output-contract validation"
        )

    if not isinstance(output_contract, dict) or not output_contract:
        raise SupervisedAttemptOutputValidationError("output_contract must be a non-empty object")

    checks: list[dict[str, str]] = []
    diagnostics: list[str] = []
    parsed_output: Any = None
    duplicate_keys: list[str] = []

    contract_format = str(output_contract.get("format", "")).strip().lower()

    if contract_format == "json":
        try:
            parsed_output, duplicate_keys = _parse_json_with_duplicate_key_detection(validated_attempt["raw_model_output"])
            checks.append(
                {
                    "check_id": "parse_json",
                    "status": "passed",
                    "message": "Raw model output parsed as JSON.",
                }
            )
            if duplicate_keys:
                checks.append(
                    {
                        "check_id": "duplicate_json_keys",
                        "status": "failed",
                        "message": "Duplicate JSON key in raw model output: " + ", ".join(sorted(duplicate_keys)),
                    }
                )
                diagnostics.extend(
                    [f"Duplicate JSON key in raw model output: {key}" for key in sorted(duplicate_keys)]
                )
        except json.JSONDecodeError as exc:
            checks.append(
                {
                    "check_id": "parse_json",
                    "status": "failed",
                    "message": "Raw model output is not valid JSON.",
                }
            )
            diagnostics.append(f"JSON parse failed: {exc.msg} at line {exc.lineno}, column {exc.colno}")
    else:
        checks.append(
            {
                "check_id": "format_passthrough",
                "status": "passed",
                "message": "No parser configured for non-JSON format. Contract checks continue.",
            }
        )

    required_fields_raw = output_contract.get("required_fields", [])
    required_fields: list[str] = []
    if required_fields_raw is not None:
        if not isinstance(required_fields_raw, list) or not all(
            isinstance(field, str) and field.strip() for field in required_fields_raw
        ):
            raise SupervisedAttemptOutputValidationError(
                "output_contract.required_fields must be a list of non-empty strings"
            )
        required_fields = [field for field in required_fields_raw]

    if required_fields:
        if isinstance(parsed_output, dict):
            missing_fields, check = _check_required_fields(parsed_output, required_fields)
            checks.append(check)
            if missing_fields:
                diagnostics.append("Required fields missing from parsed output: " + ", ".join(sorted(missing_fields)))
        elif contract_format == "json":
            checks.append(
                {
                    "check_id": "required_fields",
                    "status": "failed",
                    "message": "Required fields could not be checked because JSON parsing failed.",
                }
            )
        else:
            checks.append(
                {
                    "check_id": "required_fields",
                    "status": "failed",
                    "message": "Required fields check requires structured output object.",
                }
            )
            diagnostics.append("Required fields check unavailable for non-JSON output format.")

    if isinstance(parsed_output, dict):
        if _is_epistemic_observation_contract(output_contract):
            problems = validate_epistemic_observation_output(
                parsed_output,
                set(projected_source_paths or []),
            )
            if problems:
                checks.append(
                    {
                        "check_id": "epistemic_observation_schema",
                        "status": "failed",
                        "message": "Epistemic observation output failed validation: " + "; ".join(problems),
                    }
                )
                diagnostics.extend(problems)
            else:
                checks.append(
                    {
                        "check_id": "epistemic_observation_schema",
                        "status": "passed",
                        "message": "Epistemic observation output shape is valid.",
                    }
                )
        else:
            invalid_types, type_check = _check_required_field_types(parsed_output)
            checks.append(type_check)
            if invalid_types:
                diagnostics.extend(invalid_types)
        if _is_observation_contract(output_contract):
            observation_checks, observation_diagnostics = _check_observation_output(
                parsed_output,
                projected_source_paths=projected_source_paths,
            )
            checks.extend(observation_checks)
            diagnostics.extend(observation_diagnostics)
        else:
            overlap_targets, separation_check = _check_allowed_held_target_separation(parsed_output)
            checks.append(separation_check)
            if overlap_targets:
                diagnostics.extend(
                    [f"Target cannot be both allowed and held: {target}" for target in overlap_targets]
                )
            if authoritative_held_targets is None:
                checks.append(
                    {
                        "check_id": "held_target_preservation",
                        "status": "not_applicable",
                        "message": "Authoritative held targets were not available for this run.",
                    }
                )
            else:
                held_targets_value = parsed_output.get("held_targets")
                if not isinstance(held_targets_value, list):
                    checks.append(
                        {
                            "check_id": "held_target_preservation",
                            "status": "failed",
                            "message": "held_targets must be a list to evaluate held-target preservation.",
                        }
                    )
                    diagnostics.append("held_targets must be a list to evaluate held-target preservation.")
                elif held_targets_value != authoritative_held_targets:
                    missing = [target for target in authoritative_held_targets if target not in held_targets_value]
                    unexpected = [target for target in held_targets_value if target not in authoritative_held_targets]
                    details: list[str] = []
                    if missing:
                        details.append("missing authoritative held targets: " + ", ".join(missing))
                    if unexpected:
                        details.append("unexpected held targets: " + ", ".join(unexpected))
                    checks.append(
                        {
                            "check_id": "held_target_preservation",
                            "status": "failed",
                            "message": "Held targets must match authoritative held targets exactly."
                            + (" " + "; ".join(details) if details else ""),
                        }
                    )
                    diagnostics.extend(details or ["Held targets do not match authoritative held targets exactly."])
                else:
                    checks.append(
                        {
                            "check_id": "held_target_preservation",
                            "status": "passed",
                            "message": "Held targets match authoritative held targets exactly.",
                        }
                    )
    elif contract_format == "json":
        checks.append(
            {
                "check_id": "required_field_types",
                "status": "failed",
                "message": "Required field type checks could not run because JSON parsing failed.",
            }
        )
    else:
        checks.append(
            {
                "check_id": "required_field_types",
                "status": "failed",
                "message": "Required field type checks require structured output object.",
            }
        )

    target_authority_status = "not_applicable"
    if _is_observation_contract(output_contract):
        checks.append(
            {
                "check_id": "target_authority",
                "status": "not_applicable",
                "message": "Target authority is not applicable to repository observation output.",
            }
        )
    elif isinstance(parsed_output, dict):
        allowed_targets = parsed_output.get("allowed_targets")
        if authorized_targets is None:
            target_authority_status = "not_applicable"
            checks.append(
                {
                    "check_id": "target_authority",
                    "status": "not_applicable",
                    "message": "Structured authorized targets were not available for this run.",
                }
            )
        elif isinstance(allowed_targets, list):
            unauthorized_targets = [
                target for target in allowed_targets if target not in authorized_targets
            ]
            if unauthorized_targets:
                target_authority_status = "failed"
                checks.append(
                    {
                        "check_id": "target_authority",
                        "status": "failed",
                        "message": "Unauthorized allowed target in raw model output: "
                        + ", ".join(sorted(unauthorized_targets)),
                    }
                )
                diagnostics.extend(
                    [f"Unauthorized allowed target in raw model output: {target}" for target in sorted(unauthorized_targets)]
                )
            else:
                target_authority_status = "passed"
                checks.append(
                    {
                        "check_id": "target_authority",
                        "status": "passed",
                        "message": "Allowed targets stay within structured authorized targets.",
                    }
                )
        else:
            target_authority_status = "failed"
            checks.append(
                {
                    "check_id": "target_authority",
                    "status": "failed",
                    "message": "allowed_targets must be a list to evaluate target authority.",
                }
            )
            diagnostics.append("allowed_targets must be a list to evaluate target authority.")
    else:
        checks.append(
            {
                "check_id": "target_authority",
                "status": "not_applicable",
                "message": "Target authority check requires a parsed JSON object.",
            }
        )

    requires_reason = bool(output_contract.get("requires_reason"))
    if requires_reason:
        if isinstance(parsed_output, dict):
            reason_value = parsed_output.get("reason")
            if isinstance(reason_value, str) and reason_value.strip():
                checks.append(
                    {
                        "check_id": "requires_reason",
                        "status": "passed",
                        "message": "Non-empty reason field is present.",
                    }
                )
            else:
                checks.append(
                    {
                        "check_id": "requires_reason",
                        "status": "failed",
                        "message": "reason field is missing or empty.",
                    }
                )
                diagnostics.append("Contract requires non-empty reason field.")
        elif contract_format == "json":
            checks.append(
                {
                    "check_id": "requires_reason",
                    "status": "failed",
                    "message": "reason field check could not run because JSON parsing failed.",
                }
            )
        else:
            checks.append(
                {
                    "check_id": "requires_reason",
                    "status": "failed",
                    "message": "reason field check requires structured output object.",
                }
            )

    validation_status = (
        "passed"
        if all(check["status"] in {"passed", "not_applicable"} for check in checks)
        else "failed"
    )

    validation_record = {
        "validation_id": validation_id,
        "attempt_id": validated_attempt["attempt_id"],
        "triage_id": validated_attempt["triage_id"],
        "orchestration_id": validated_attempt["orchestration_id"],
        "prompt_packet_id": validated_attempt.get("prompt_packet_id"),
        "validation_status": validation_status,
        "acceptance_status": "not_reviewed",
        "validated_at": validated_at,
        "output_contract": deepcopy(output_contract),
        "checks": checks,
        "diagnostics": diagnostics,
        "raw_output_preserved": True,
        "authority_boundaries": list(REQUIRED_VALIDATION_AUTHORITY_BOUNDARIES),
        "provenance": {
            "source": "supervised_attempt_output_validation",
            "input_attempt_id": validated_attempt["attempt_id"],
        },
        "review_required": True,
        "target_authority_status": target_authority_status,
    }

    return validate_supervised_attempt_output_validation_record(validation_record)
