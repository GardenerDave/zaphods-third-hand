#!/usr/bin/env python3
"""Canonical transaction manifest and next-worker handoff context helpers."""

from __future__ import annotations

import json
import hashlib
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TRANSACTION_MANIFEST_SCHEMA = "zth.transaction_manifest.v0.1"
NEXT_WORKER_CONTEXT_SCHEMA = "zth.next_worker_context.v0.1"
LIFECYCLE_STATES = {
    "CREATED",
    "EVIDENCE_BOUND",
    "DISPATCHED",
    "CAPTURED",
    "VALIDATED",
    "REVIEW_REQUIRED",
    "ACCEPTED",
    "REJECTED",
    "ESCALATION_REQUESTED",
    "HANDOFF",
    "COMPLETE",
}


class TransactionHandoffError(ValueError):
    """Raised when transaction-manifest or next-worker context construction fails."""


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path, *, kind: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TransactionHandoffError(f"missing {kind}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise TransactionHandoffError(f"invalid JSON in {kind}: {path}") from exc
    if not isinstance(payload, dict):
        raise TransactionHandoffError(f"{kind} must be a JSON object")
    return payload


def _require_nonempty(record: dict[str, Any], key: str, *, kind: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise TransactionHandoffError(f"{kind}.{key} must be a non-empty string")
    return value


def _require_list(record: dict[str, Any], key: str, *, kind: str) -> list[Any]:
    value = record.get(key)
    if not isinstance(value, list):
        raise TransactionHandoffError(f"{kind}.{key} must be a list")
    return value


def _require_exact_list_match(
    *,
    left: list[Any],
    right: list[Any],
    left_kind: str,
    right_kind: str,
    field: str,
) -> None:
    if left != right:
        field_label = field.replace("_", " ")
        raise TransactionHandoffError(f"{field_label} mismatch between {left_kind} and {right_kind}")


def _read_optional_json(run_dir: Path, filename: str, *, kind: str) -> dict[str, Any] | None:
    path = run_dir / filename
    if not path.is_file():
        return None
    return _read_json(path, kind=kind)


def _evidence_reference(path: Path, payload: dict[str, Any], *, id_field: str) -> dict[str, Any]:
    reference: dict[str, Any] = {
        "path": str(path),
        "schema": payload.get("schema", payload.get("report_type", payload.get("output_contract_version"))),
    }
    value = payload.get(id_field)
    if isinstance(value, str) and value.strip():
        reference[id_field] = value
    if path.is_file():
        reference["sha256"] = _sha256(path)
    return reference


def _artifact_reference(path: Path, *, artifact: str, id_key: str | None = None, id_value: Any = None) -> dict[str, Any]:
    reference: dict[str, Any] = {
        "artifact": artifact,
        "path": str(path),
    }
    if id_key and isinstance(id_value, str) and id_value.strip():
        reference[id_key] = id_value
    if path.is_file():
        reference["sha256"] = _sha256(path)
    return reference


def _reference_by_artifact(evidence_references: list[dict[str, Any]], artifact: str) -> dict[str, Any]:
    for reference in evidence_references:
        if reference.get("artifact") == artifact:
            return reference
    raise TransactionHandoffError(f"missing evidence reference for {artifact}")


def _read_tracked_artifact(reference: dict[str, Any], *, kind: str, require_sha256: bool = True) -> tuple[Path, str]:
    path_value = reference.get("path")
    if not isinstance(path_value, str) or not path_value.strip():
        raise TransactionHandoffError(f"{kind} reference must include a path")
    path = Path(path_value)
    if not path.is_file():
        raise TransactionHandoffError(f"missing {kind}: {path}")
    bytes_text = path.read_text(encoding="utf-8")
    recorded_sha256 = reference.get("sha256")
    if require_sha256:
        if not isinstance(recorded_sha256, str) or not recorded_sha256.strip():
            raise TransactionHandoffError(f"{kind} reference must include sha256")
        actual_sha256 = _sha256(path)
        if actual_sha256 != recorded_sha256:
            raise TransactionHandoffError(f"{kind} bytes do not match recorded sha256")
    return path, bytes_text


def derive_transaction_id(*, run_id: str, orchestration_id: str | None = None, attempt_id: str | None = None) -> str:
    base = run_id.strip()
    for candidate in (orchestration_id, attempt_id):
        if isinstance(candidate, str) and candidate.strip():
            base = candidate.strip()
            break
    return base


def derive_lifecycle_state(
    *,
    validation_record: dict[str, Any] | None,
    decision_record: dict[str, Any] | None,
    gate_record: dict[str, Any] | None,
    handoff_record: dict[str, Any] | None,
) -> str:
    if handoff_record is not None:
        handoff_status = handoff_record.get("handoff_status")
        if handoff_status == "prepared":
            return "HANDOFF"
        if handoff_status == "blocked":
            return "REVIEW_REQUIRED"
    if decision_record is not None:
        decision = decision_record.get("decision")
        if decision == "accepted":
            return "ACCEPTED"
        if decision == "rejected":
            return "REJECTED"
        if decision == "revision_requested":
            return "ESCALATION_REQUESTED"
    if validation_record is not None:
        status = validation_record.get("validation_status")
        if status == "passed":
            return "VALIDATED"
        if status == "failed":
            return "REVIEW_REQUIRED"
    if validation_record is None:
        return "DISPATCHED"
    return "CAPTURED"


def build_transaction_manifest(
    *,
    run_id: str,
    task_state: dict[str, Any],
    first_worker_identity: str,
    intended_next_worker_identity: str | None,
    attempt_record: dict[str, Any] | None,
    validation_record: dict[str, Any] | None,
    decision_record: dict[str, Any] | None,
    gate_record: dict[str, Any] | None,
    handoff_record: dict[str, Any] | None,
    evidence_references: list[dict[str, Any]],
    created_at: str | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    attempt_id = attempt_record.get("attempt_id") if isinstance(attempt_record, dict) else None
    validation_id = validation_record.get("validation_id") if isinstance(validation_record, dict) else None
    decision_id = decision_record.get("decision_id") if isinstance(decision_record, dict) else None
    gate_id = gate_record.get("gate_id") if isinstance(gate_record, dict) else None
    handoff_id = handoff_record.get("handoff_id") if isinstance(handoff_record, dict) else None

    if isinstance(attempt_record, dict) and isinstance(validation_record, dict):
        if validation_record.get("attempt_id") != attempt_record.get("attempt_id"):
            raise TransactionHandoffError("validation attempt_id does not match attempt record")
        if validation_record.get("orchestration_id") != attempt_record.get("orchestration_id"):
            raise TransactionHandoffError("validation orchestration_id does not match attempt record")
        if validation_record.get("triage_id") != attempt_record.get("triage_id"):
            raise TransactionHandoffError("validation triage_id does not match attempt record")
    if isinstance(decision_record, dict) and isinstance(validation_record, dict):
        if decision_record.get("attempt_id") != validation_record.get("attempt_id"):
            raise TransactionHandoffError("decision attempt_id does not match validation record")
        if decision_record.get("validation_id") != validation_record.get("validation_id"):
            raise TransactionHandoffError("decision validation_id does not match validation record")
        if decision_record.get("triage_id") != validation_record.get("triage_id"):
            raise TransactionHandoffError("decision triage_id does not match validation record")
    if isinstance(gate_record, dict) and isinstance(decision_record, dict):
        if gate_record.get("decision_id") != decision_record.get("decision_id"):
            raise TransactionHandoffError("gate decision_id does not match decision record")
        if gate_record.get("attempt_id") != decision_record.get("attempt_id"):
            raise TransactionHandoffError("gate attempt_id does not match decision record")
        if gate_record.get("validation_id") != decision_record.get("validation_id"):
            raise TransactionHandoffError("gate validation_id does not match decision record")
    if isinstance(handoff_record, dict) and isinstance(gate_record, dict):
        if handoff_record.get("gate_id") != gate_record.get("gate_id"):
            raise TransactionHandoffError("handoff gate_id does not match gate record")
        if handoff_record.get("decision_id") != gate_record.get("decision_id"):
            raise TransactionHandoffError("handoff decision_id does not match gate record")
        if handoff_record.get("attempt_id") != gate_record.get("attempt_id"):
            raise TransactionHandoffError("handoff attempt_id does not match gate record")
        if handoff_record.get("validation_id") != gate_record.get("validation_id"):
            raise TransactionHandoffError("handoff validation_id does not match gate record")

    orchestration_id = task_state.get("orchestration_id")
    triage_id = task_state.get("triage_id")
    transaction_id = derive_transaction_id(
        run_id=run_id,
        orchestration_id=orchestration_id if isinstance(orchestration_id, str) else None,
        attempt_id=attempt_id,
    )
    lifecycle_state = derive_lifecycle_state(
        validation_record=validation_record,
        decision_record=decision_record,
        gate_record=gate_record,
        handoff_record=handoff_record,
    )
    manifest = {
        "schema_version": TRANSACTION_MANIFEST_SCHEMA,
        "transaction_id": transaction_id,
        "lifecycle_state": lifecycle_state,
        "run_id": run_id,
        "task_reference": {
            "triage_id": triage_id,
            "orchestration_id": orchestration_id,
            "prompt_packet_id": task_state.get("prompt_packet_id"),
        },
        "first_worker_identity": first_worker_identity,
        "intended_next_worker_identity": intended_next_worker_identity,
        "records": {
            "attempt_id": attempt_id,
            "validation_id": validation_id,
            "decision_id": decision_id,
            "gate_id": gate_id,
            "handoff_id": handoff_id,
        },
        "evidence_references": evidence_references,
        "created_at": created_at or _utc_iso(),
        "updated_at": updated_at or _utc_iso(),
    }
    return manifest


def build_next_worker_context(
    *,
    transaction_manifest: dict[str, Any],
    task_state: dict[str, Any],
    attempt_record: dict[str, Any],
    validation_record: dict[str, Any],
    decision_record: dict[str, Any],
    gate_record: dict[str, Any],
    handoff_record: dict[str, Any],
    next_worker_identity: str | None,
    handoff_packet_path: Path,
) -> dict[str, Any]:
    if transaction_manifest.get("schema_version") != TRANSACTION_MANIFEST_SCHEMA:
        raise TransactionHandoffError("transaction manifest schema_version is unsupported")
    if transaction_manifest.get("lifecycle_state") == "COMPLETE":
        raise TransactionHandoffError("transaction cannot prepare next-worker context after COMPLETE")
    if decision_record.get("decision") != "accepted":
        raise TransactionHandoffError("next-worker context requires accepted review decision")
    if validation_record.get("validation_status") != "passed":
        raise TransactionHandoffError("next-worker context requires passed validation")
    if gate_record.get("gate_status") != "allowed":
        raise TransactionHandoffError("next-worker context requires allowed downstream-use gate")
    if handoff_record.get("handoff_status") != "prepared":
        raise TransactionHandoffError("next-worker context requires prepared handoff packet")

    allowed_targets = task_state.get("allowed_targets")
    held_targets = task_state.get("held_targets")
    if not isinstance(allowed_targets, list) or not isinstance(held_targets, list):
        raise TransactionHandoffError("task state must include allowed_targets and held_targets lists")

    triage_packet = _read_json(
        Path(task_state["run_manifest_path"]).parent / "triage_packet.json",
        kind="triage packet",
    )
    orchestration_packet = _read_json(
        Path(task_state["run_manifest_path"]).parent / "orchestration_packet.json",
        kind="orchestration packet",
    )
    raw_output_reference = attempt_record.get("provenance", {}).get("raw_output_source_path")
    if not isinstance(raw_output_reference, str) or not raw_output_reference.strip():
        raise TransactionHandoffError("previous attempt must reference a raw model output artifact")
    raw_output_payload = _read_json(Path(raw_output_reference), kind="raw model output")
    _require_exact_list_match(
        left=allowed_targets,
        right=_require_list(raw_output_payload, "allowed_targets", kind="raw model output"),
        left_kind="task state",
        right_kind="raw model output",
        field="allowed_targets",
    )
    _require_exact_list_match(
        left=held_targets,
        right=_require_list(raw_output_payload, "held_targets", kind="raw model output"),
        left_kind="task state",
        right_kind="raw model output",
        field="held_targets",
    )
    if _require_list(triage_packet, "allowed_targets", kind="triage packet") != allowed_targets:
        raise TransactionHandoffError("triage packet allowed targets disagree with raw model output")
    if _require_list(orchestration_packet, "held_targets", kind="orchestration packet") != held_targets:
        raise TransactionHandoffError("orchestration packet held targets disagree with raw model output")

    gate_allowed_use = _require_list(gate_record, "allowed_downstream_use", kind="downstream use gate")
    handoff_allowed_use = _require_list(handoff_record, "allowed_downstream_use", kind="handoff packet")
    _require_exact_list_match(
        left=gate_allowed_use,
        right=handoff_allowed_use,
        left_kind="downstream use gate",
        right_kind="handoff packet",
        field="allowed_downstream_use",
    )
    if gate_record.get("gate_scope") != handoff_record.get("handoff_scope"):
        raise TransactionHandoffError("handoff scope must match downstream-use gate scope")

    task_request = task_state.get("task_request")
    if not isinstance(task_request, str) or not task_request.strip():
        raise TransactionHandoffError("task state must include a non-empty task_request")
    raw_output_reference = _reference_by_artifact(
        transaction_manifest["evidence_references"],
        "raw_model_output",
    )

    next_worker_context = {
        "schema_version": NEXT_WORKER_CONTEXT_SCHEMA,
        "transaction_id": transaction_manifest["transaction_id"],
        "lifecycle_state": transaction_manifest["lifecycle_state"],
        "run_id": transaction_manifest["run_id"],
        "task_state": deepcopy(task_state),
        "task_request": task_request,
        "selected_next_worker_identity": next_worker_identity,
        "first_worker_identity": transaction_manifest["first_worker_identity"],
        "authority_boundaries": {
            "attempt": list(attempt_record["authority_boundaries"]),
            "validation": list(validation_record["authority_boundaries"]),
            "decision": list(decision_record["authority_boundaries"]),
            "gate": list(gate_record["authority_boundaries"]),
            "handoff": list(handoff_record["authority_boundaries"]),
        },
        "evidence_references": deepcopy(transaction_manifest["evidence_references"]),
        "previous_attempt": {
            "attempt_id": attempt_record["attempt_id"],
            "result_reference": {
                "raw_output_artifact": deepcopy(raw_output_reference),
                "raw_output_reference": raw_output_reference.get("path"),
                "raw_output_sha256": raw_output_reference.get("sha256"),
            },
        },
        "validation": {
            "validation_id": validation_record["validation_id"],
            "validation_status": validation_record["validation_status"],
            "validation_report_reference": validation_record.get("provenance", {}).get("source"),
        },
        "review": {
            "decision_id": decision_record["decision_id"],
            "decision": decision_record["decision"],
            "decision_reason": decision_record["decision_reason"],
        },
        "downstream_use_gate": {
            "gate_id": gate_record["gate_id"],
            "gate_status": gate_record["gate_status"],
            "gate_reason": gate_record["gate_reason"],
        },
        "handoff": {
            "handoff_id": handoff_record["handoff_id"],
            "handoff_status": handoff_record["handoff_status"],
            "handoff_reason": handoff_record["handoff_reason"],
            "next_step_summary": handoff_record["next_step_summary"],
            "next_step_objective": handoff_record.get("next_step_objective"),
            "handoff_packet_reference": _artifact_reference(
                handoff_packet_path,
                artifact="handoff_packet",
                id_key="handoff_id",
                id_value=handoff_record["handoff_id"],
            ),
        },
        "constraints": {
            "allowed_targets": list(allowed_targets),
            "held_targets": list(held_targets),
            "authority_boundaries": list(handoff_record["authority_boundaries"]),
            "handoff_reason": handoff_record["handoff_reason"],
            "next_step_scope": handoff_record["handoff_scope"],
        },
        "ready_for_next_worker": True,
    }
    return next_worker_context


def build_next_worker_continuation_context(
    *,
    transaction_manifest: dict[str, Any],
    next_worker_context: dict[str, Any],
    output_dir: Path | None = None,
) -> dict[str, Any]:
    if transaction_manifest.get("schema_version") != TRANSACTION_MANIFEST_SCHEMA:
        raise TransactionHandoffError("transaction manifest schema_version is unsupported")
    if next_worker_context.get("schema_version") != NEXT_WORKER_CONTEXT_SCHEMA:
        raise TransactionHandoffError("next-worker context schema_version is unsupported")
    if transaction_manifest.get("transaction_id") != next_worker_context.get("transaction_id"):
        raise TransactionHandoffError("continuation context requires matching transaction IDs")
    if transaction_manifest.get("lifecycle_state") == "COMPLETE":
        raise TransactionHandoffError("continuation context cannot be built after COMPLETE")

    raw_output_reference = _reference_by_artifact(
        transaction_manifest["evidence_references"],
        "raw_model_output",
    )
    model_prompt_reference = _reference_by_artifact(
        transaction_manifest["evidence_references"],
        "model_prompt_packet",
    )

    raw_output_path, raw_output_text = _read_tracked_artifact(raw_output_reference, kind="raw model output")
    raw_output_recorded_sha256 = raw_output_reference.get("sha256")
    handoff_packet_reference = next_worker_context["handoff"]["handoff_packet_reference"]
    if not isinstance(handoff_packet_reference, dict):
        raise TransactionHandoffError("handoff packet reference must be a JSON object")
    handoff_packet_path, _ = _read_tracked_artifact(handoff_packet_reference, kind="handoff packet")
    handoff_packet_payload = _read_json(handoff_packet_path, kind="handoff packet")
    handoff_manifest_reference = _reference_by_artifact(
        transaction_manifest["evidence_references"],
        "handoff_packet",
    )
    if handoff_packet_reference.get("path") != handoff_manifest_reference.get("path"):
        raise TransactionHandoffError("handoff packet reference path does not match transaction manifest evidence")

    previous_attempt = next_worker_context.get("previous_attempt", {})
    result_reference = previous_attempt.get("result_reference", {})
    raw_output_artifact_reference = result_reference.get("raw_output_artifact")
    if not isinstance(raw_output_artifact_reference, dict):
        raise TransactionHandoffError("previous result must include raw_output_artifact reference")
    if raw_output_artifact_reference.get("artifact") != "raw_model_output":
        raise TransactionHandoffError("previous result must reference raw_model_output")
    if raw_output_artifact_reference.get("path") != str(raw_output_path):
        raise TransactionHandoffError("previous result reference path does not match evidence")
    artifact_sha256 = raw_output_artifact_reference.get("sha256")
    if raw_output_recorded_sha256 is not None:
        if artifact_sha256 is not None and artifact_sha256 != raw_output_recorded_sha256:
            raise TransactionHandoffError("previous result sha256 does not match evidence")
        if _sha256(raw_output_path) != raw_output_recorded_sha256:
            raise TransactionHandoffError("previous result bytes do not match recorded sha256")

    task_state = deepcopy(next_worker_context["task_state"])
    bounded_task_request = task_state.get("bounded_task_request")
    if not isinstance(bounded_task_request, str) or not bounded_task_request.strip():
        raise TransactionHandoffError("task_state must include bounded_task_request")

    allowed_targets = list(next_worker_context["constraints"]["allowed_targets"])
    held_targets = list(next_worker_context["constraints"]["held_targets"])
    authority_boundaries = next_worker_context["authority_boundaries"]
    next_step_scope = next_worker_context["constraints"]["next_step_scope"]
    review = next_worker_context["review"]
    validation = next_worker_context["validation"]
    downstream_use_gate = next_worker_context["downstream_use_gate"]
    handoff = next_worker_context["handoff"]
    next_step_objective = handoff_packet_payload.get("next_step_objective")
    if not isinstance(next_step_objective, str) or not next_step_objective.strip():
        raise TransactionHandoffError("handoff packet must provide a concrete next_step_objective")
    transition_summary = handoff_packet_payload.get("next_step_summary")
    if not isinstance(transition_summary, str) or not transition_summary.strip():
        raise TransactionHandoffError("handoff packet must provide next_step_summary")

    if next_worker_context.get("ready_for_next_worker") is not True:
        raise TransactionHandoffError("continuation context requires a ready next-worker context")

    continuation_lines = [
        "Continue from the accepted previous-worker result. Do not redo the original worker task.",
        "",
        "# ZTH Executable Continuation Prompt",
        "",
        "## Next-Worker Directive",
        "Continue from the accepted previous-worker result. Do not redo the original worker task.",
        "",
        "## Already Completed",
        f"- transaction_id: {transaction_manifest['transaction_id']}",
        f"- lifecycle_state: {transaction_manifest['lifecycle_state']}",
        f"- review_decision: {review['decision']}",
        f"- validation_status: {validation['validation_status']}",
        f"- downstream_use_gate: {downstream_use_gate['gate_status']}",
        f"- handoff_status: {handoff['handoff_status']}",
        f"- handoff_reason: {handoff['handoff_reason']}",
        f"- next_step_summary: {transition_summary}",
        f"- next_step_objective: {next_step_objective}",
        "",
        "### Accepted Previous-Worker Result",
        f"```text\n{raw_output_text.rstrip()}\n```",
        "",
        "### Bounded Original Task",
        f"```text\n{bounded_task_request.rstrip()}\n```",
        "",
        "### Perform Now",
        next_step_objective,
        "",
        "### Transition Summary",
        transition_summary,
        "",
        "### Authorized Scope",
        next_step_scope,
        "",
        "### Allowed Targets",
        f"```json\n{json.dumps(allowed_targets, indent=2, sort_keys=True)}\n```",
        "",
        "### Held Targets",
        f"```json\n{json.dumps(held_targets, indent=2, sort_keys=True)}\n```",
        "",
        "### Inherited Authority Boundaries",
        f"```json\n{json.dumps(authority_boundaries, indent=2, sort_keys=True)}\n```",
        "",
        "### Second-Worker Output Contract",
        "Return the downstream continuation result only.",
        "State how you used the accepted prior result, confirm scope compliance, and report any unresolved issue preventing continuation.",
        "Do not redo the first-worker task.",
        "",
        "### Provenance",
        f"- transaction_id: {transaction_manifest['transaction_id']}",
        f"- run_id: {transaction_manifest['run_id']}",
        f"- first_worker_identity: {next_worker_context['first_worker_identity']}",
        f"- selected_next_worker_identity: {next_worker_context.get('selected_next_worker_identity') or '<none>'}",
        f"- raw_model_output_path: {raw_output_path}",
        f"- raw_model_output_sha256: {raw_output_recorded_sha256}",
        f"- handoff_packet_path: {handoff_packet_path}",
        f"- model_prompt_packet_path: {model_prompt_reference.get('path')}",
        "",
        "### Authority Notice",
        "- This prompt authorizes only the stated downstream task.",
        "- It does not grant repository modification, promotion, training, autonomous routing, or other held authority unless explicitly present in the source transaction.",
        "",
        "### Review Boundary",
        "- This artifact is a derived executable continuation view, not an authority source.",
    ]
    continuation_text = "\n".join(continuation_lines).rstrip() + "\n"
    result: dict[str, Any] = {
        "transaction_id": transaction_manifest["transaction_id"],
        "schema_version": "zth.next_worker_continuation.v0.1",
        "source_context_schema_version": next_worker_context["schema_version"],
        "ready_for_continuation": True,
        "continuation_text": continuation_text,
        "source_references": {
            "transaction_manifest": transaction_manifest,
            "next_worker_context": {
                "schema_version": next_worker_context["schema_version"],
                "path": next_worker_context.get("path"),
            },
            "raw_model_output": raw_output_artifact_reference,
            "handoff_packet": handoff_packet_reference,
        },
    }
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "next_worker_continuation.md"
        output_path.write_text(continuation_text, encoding="utf-8")
        result["continuation_path"] = output_path
    return result


def render_next_worker_context(context: dict[str, Any]) -> str:
    if context.get("schema_version") != NEXT_WORKER_CONTEXT_SCHEMA:
        raise TransactionHandoffError("next-worker context schema_version is unsupported")
    lines = [
        "# ZTH Next Worker Context",
        "",
        f"- transaction_id: {context['transaction_id']}",
        f"- lifecycle_state: {context['lifecycle_state']}",
        f"- run_id: {context['run_id']}",
        f"- selected_next_worker_identity: {context.get('selected_next_worker_identity') or '<none>'}",
        "",
        "## Task State",
        f"```json\n{json.dumps(context['task_state'], indent=2, sort_keys=True)}\n```",
        "",
        "## Evidence References",
        f"```json\n{json.dumps(context['evidence_references'], indent=2, sort_keys=True)}\n```",
        "",
        "## Authority Boundaries",
        f"```json\n{json.dumps(context['authority_boundaries'], indent=2, sort_keys=True)}\n```",
        "",
        "## Previous Attempt",
        f"```json\n{json.dumps(context['previous_attempt'], indent=2, sort_keys=True)}\n```",
        "",
        "## Validation",
        f"```json\n{json.dumps(context['validation'], indent=2, sort_keys=True)}\n```",
        "",
        "## Review",
        f"```json\n{json.dumps(context['review'], indent=2, sort_keys=True)}\n```",
        "",
        "## Downstream-Use Gate",
        f"```json\n{json.dumps(context['downstream_use_gate'], indent=2, sort_keys=True)}\n```",
        "",
        "## Handoff",
        f"```json\n{json.dumps(context['handoff'], indent=2, sort_keys=True)}\n```",
        "",
        "## Constraints",
        f"```json\n{json.dumps(context['constraints'], indent=2, sort_keys=True)}\n```",
        "",
        "## Review Boundary",
        "- This bundle is a next-worker input only.",
        "- It does not grant execution, file modification, promotion, or training authority.",
        "- It does not select a worker semantically.",
    ]
    return "\n".join(lines).rstrip() + "\n"


def build_transaction_handoff_artifacts(
    *,
    run_dir: Path,
    next_worker_identity: str | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    manifest = _read_json(run_dir / "run_manifest.json", kind="run manifest")
    if manifest.get("report_type") != "manual_supervised_attempt_run_manifest.v1":
        raise TransactionHandoffError("run manifest report_type must be manual_supervised_attempt_run_manifest.v1")

    attempt = _read_json(run_dir / "supervised_model_attempt.json", kind="supervised model attempt")
    validation = _read_json(run_dir / "output_validation.json", kind="output validation")
    decision = _read_optional_json(run_dir, "review_decision.json", kind="review decision")
    gate = _read_optional_json(run_dir, "downstream_use_gate.json", kind="downstream use gate")
    handoff = _read_optional_json(run_dir, "handoff_packet.json", kind="handoff packet")
    if decision is None or gate is None or handoff is None:
        raise TransactionHandoffError("transaction handoff artifacts require review_decision.json, downstream_use_gate.json, and handoff_packet.json")

    if not (run_dir / "model_prompt_packet.md").is_file():
        raise TransactionHandoffError("missing model prompt packet: " + str(run_dir / "model_prompt_packet.md"))

    # `task_request` is the full prepared first-worker prompt packet.
    # `bounded_task_request` preserves the original bounded task/request text.
    task_state = {
        "triage_id": manifest.get("triage_id"),
        "orchestration_id": manifest.get("orchestration_id"),
        "prompt_packet_id": manifest.get("prompt_packet_id"),
        "task_request": (run_dir / "model_prompt_packet.md").read_text(encoding="utf-8"),
        "bounded_task_request": (run_dir / "messy_input.txt").read_text(encoding="utf-8"),
        "allowed_targets": _read_json(run_dir / "triage_packet.json", kind="triage packet").get("allowed_targets", []),
        "held_targets": _read_json(run_dir / "orchestration_packet.json", kind="orchestration packet").get("held_targets", []),
        "source_prompt_packet_path": attempt.get("source_prompt_packet_path"),
        "run_manifest_path": str(run_dir / "run_manifest.json"),
    }

    evidence_references = [
        _artifact_reference(run_dir / "run_manifest.json", artifact="run_manifest"),
        _artifact_reference(run_dir / "model_prompt_packet.md", artifact="model_prompt_packet"),
        _artifact_reference(run_dir / "raw_model_output.txt", artifact="raw_model_output"),
        _artifact_reference(run_dir / "supervised_model_attempt.json", artifact="supervised_model_attempt", id_key="attempt_id", id_value=attempt["attempt_id"]),
        _artifact_reference(run_dir / "output_validation.json", artifact="output_validation", id_key="validation_id", id_value=validation["validation_id"]),
        _artifact_reference(run_dir / "review_decision.json", artifact="review_decision", id_key="decision_id", id_value=decision["decision_id"]),
        _artifact_reference(run_dir / "downstream_use_gate.json", artifact="downstream_use_gate", id_key="gate_id", id_value=gate["gate_id"]),
        _artifact_reference(run_dir / "handoff_packet.json", artifact="handoff_packet", id_key="handoff_id", id_value=handoff["handoff_id"]),
    ]

    transaction_manifest = build_transaction_manifest(
        run_id=manifest["run_id"],
        task_state=task_state,
        first_worker_identity=str(attempt["model_metadata"]["model_id"]),
        intended_next_worker_identity=next_worker_identity,
        attempt_record=attempt,
        validation_record=validation,
        decision_record=decision,
        gate_record=gate,
        handoff_record=handoff,
        evidence_references=evidence_references,
        created_at=manifest.get("created_at"),
        updated_at=_utc_iso(),
    )

    next_worker_context = build_next_worker_context(
        transaction_manifest=transaction_manifest,
        task_state=task_state,
        attempt_record=attempt,
        validation_record=validation,
        decision_record=decision,
        gate_record=gate,
        handoff_record=handoff,
        next_worker_identity=next_worker_identity,
        handoff_packet_path=run_dir / "handoff_packet.json",
    )

    target_dir = output_dir or run_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = target_dir / "transaction_manifest.json"
    context_path = target_dir / "next_worker_context.json"
    context_md_path = target_dir / "next_worker_context.md"
    _write_json(manifest_path, transaction_manifest)
    _write_json(context_path, next_worker_context)
    context_md_path.write_text(render_next_worker_context(next_worker_context), encoding="utf-8")

    return {
        "transaction_manifest_path": manifest_path,
        "next_worker_context_path": context_path,
        "next_worker_context_md_path": context_md_path,
        "transaction_manifest": transaction_manifest,
        "next_worker_context": next_worker_context,
    }
