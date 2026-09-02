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
    raw_allowed_targets = raw_output_payload.get("allowed_targets")
    raw_held_targets = raw_output_payload.get("held_targets")
    if raw_allowed_targets is None and raw_held_targets is None:
        semantic_mode = True
    else:
        semantic_mode = False
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
    if semantic_mode and (_require_list(triage_packet, "allowed_targets", kind="triage packet") != allowed_targets or _require_list(orchestration_packet, "held_targets", kind="orchestration packet") != held_targets):
        raise TransactionHandoffError("authoritative scope does not match task state")

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
        "transaction_binding": {
            "transaction_id": transaction_manifest["transaction_id"],
            "run_id": transaction_manifest["run_id"],
            "attempt_id": attempt_record["attempt_id"],
            "validation_id": validation_record["validation_id"],
            "decision_id": decision_record["decision_id"],
            "gate_id": gate_record["gate_id"],
            "handoff_id": handoff_record["handoff_id"],
            "raw_output_sha256": raw_output_reference.get("sha256"),
        },
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


def _extract_markdown_section(text: str, heading: str) -> str:
    marker = f"### {heading}"
    start = text.find(marker)
    if start == -1:
        raise TransactionHandoffError(f"missing markdown section: {heading}")
    section_start = text.find("\n", start)
    if section_start == -1:
        raise TransactionHandoffError(f"missing markdown body for section: {heading}")
    next_heading = text.find("\n### ", section_start + 1)
    end = len(text) if next_heading == -1 else next_heading
    return text[section_start + 1 : end].strip()


def _extract_json_code_block(text: str, heading: str, *, kind: str) -> Any:
    section = _extract_markdown_section(text, heading)
    if not section.startswith("```json\n") or not section.endswith("\n```"):
        raise TransactionHandoffError(f"{kind} section {heading} must contain a JSON code block")
    payload_text = section[len("```json\n") : -len("\n```")]
    try:
        return json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise TransactionHandoffError(f"{kind} section {heading} must contain valid JSON") from exc


def _read_preflight_artifact(run_dir: Path, filename: str, *, kind: str, checks: list[dict[str, Any]]) -> dict[str, Any] | None:
    path = run_dir / filename
    if not path.is_file():
        checks.append({"check_id": kind, "status": "failed", "message": f"missing {kind}: {path}"})
        return None
    try:
        return _read_json(path, kind=kind)
    except TransactionHandoffError as exc:
        checks.append({"check_id": kind, "status": "failed", "message": str(exc)})
        return None


def build_worker_b_preflight(
    *,
    run_dir: Path,
    expected_next_worker_identity: str,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def record(check_id: str, status: str, message: str) -> None:
        checks.append({"check_id": check_id, "status": status, "message": message})

    try:
        run_manifest = _read_preflight_artifact(run_dir, "run_manifest.json", kind="run manifest", checks=checks)
        transaction_manifest = _read_preflight_artifact(run_dir, "transaction_manifest.json", kind="transaction manifest", checks=checks)
        next_worker_context = _read_preflight_artifact(run_dir, "next_worker_context.json", kind="next-worker context", checks=checks)
        gate_record = _read_preflight_artifact(run_dir, "downstream_use_gate.json", kind="downstream use gate", checks=checks)
        handoff_packet = _read_preflight_artifact(run_dir, "handoff_packet.json", kind="handoff packet", checks=checks)
        triage_packet = _read_preflight_artifact(run_dir, "triage_packet.json", kind="triage packet", checks=checks)
        orchestration_packet = _read_preflight_artifact(run_dir, "orchestration_packet.json", kind="orchestration packet", checks=checks)
        next_worker_continuation_path = run_dir / "next_worker_continuation.md"
        if not next_worker_continuation_path.is_file():
            raise TransactionHandoffError("missing next-worker continuation markdown")
        continuation_text = next_worker_continuation_path.read_text(encoding="utf-8")
        if run_manifest is None or transaction_manifest is None or next_worker_context is None or gate_record is None or handoff_packet is None or triage_packet is None or orchestration_packet is None:
            raise TransactionHandoffError("missing required Worker-B preflight artifacts")

        if run_manifest.get("report_type") != "manual_supervised_attempt_run_manifest.v1":
            raise TransactionHandoffError("run manifest report_type must be manual_supervised_attempt_run_manifest.v1")
        record("run_manifest", "passed", "Run manifest resolved.")

        if transaction_manifest.get("lifecycle_state") != "HANDOFF":
            raise TransactionHandoffError("transaction lifecycle must be HANDOFF")
        record("transaction_lifecycle", "passed", "Transaction lifecycle is HANDOFF.")

        if transaction_manifest.get("intended_next_worker_identity") != expected_next_worker_identity:
            raise TransactionHandoffError("selected next worker identity mismatch")
        record("next_worker_identity", "passed", "Intended next worker identity matches.")

        if next_worker_context.get("selected_next_worker_identity") != expected_next_worker_identity:
            raise TransactionHandoffError("next-worker context selected_next_worker_identity mismatch")
        record("worker_identity", "passed", "Worker identity agrees across artifacts.")

        previous_attempt = next_worker_context.get("previous_attempt", {})
        result_reference = previous_attempt.get("result_reference", {})
        raw_sha = result_reference.get("raw_output_sha256")
        raw_artifact = result_reference.get("raw_output_artifact", {})
        raw_ref_path = raw_artifact.get("path")
        if not isinstance(raw_sha, str) or not raw_sha.strip():
            raise TransactionHandoffError("missing previous result sha256")
        if not isinstance(raw_ref_path, str) or not raw_ref_path.strip():
            raise TransactionHandoffError("missing previous result path")
        raw_ref_file = Path(raw_ref_path)
        if not raw_ref_file.is_file():
            raise TransactionHandoffError("missing previous result evidence file")
        if _sha256(raw_ref_file) != raw_sha:
            raise TransactionHandoffError("previous result sha256 does not match evidence")
        record("previous_result_binding", "passed", "Previous result sha256 matches evidence.")

        attempt_id = previous_attempt.get("attempt_id")
        if not isinstance(attempt_id, str) or not attempt_id.strip():
            raise TransactionHandoffError("previous attempt must include attempt_id")
        if transaction_manifest.get("records", {}).get("attempt_id") != attempt_id:
            raise TransactionHandoffError("transaction manifest attempt_id mismatch")
        if handoff_packet.get("source_attempt_id") not in {None, attempt_id}:
            raise TransactionHandoffError("handoff packet source attempt id mismatch")
        if next_worker_context.get("review", {}).get("decision_id") != transaction_manifest.get("records", {}).get("decision_id"):
            raise TransactionHandoffError("review decision provenance mismatch")
        record("previous_result_identity", "passed", "Attempt/result identity agrees across transaction artifacts.")

        objective = next_worker_context.get("handoff", {}).get("next_step_objective")
        if not isinstance(objective, str) or not objective.strip():
            raise TransactionHandoffError("missing next_step_objective")
        handoff_objective = handoff_packet.get("next_step_objective")
        if not isinstance(handoff_objective, str) or not handoff_objective.strip():
            raise TransactionHandoffError("handoff packet missing next_step_objective")
        if handoff_objective != objective:
            raise TransactionHandoffError("handoff packet next_step_objective mismatch")
        perform_now = _extract_markdown_section(continuation_text, "Perform Now")
        if perform_now.strip() != objective.strip():
            raise TransactionHandoffError("Perform Now does not match next_step_objective")
        record("objective_propagation", "passed", "Objective appears in handoff and continuation.")

        allowed_targets = next_worker_context.get("constraints", {}).get("allowed_targets")
        held_targets = next_worker_context.get("constraints", {}).get("held_targets")
        if not isinstance(allowed_targets, list) or not isinstance(held_targets, list):
            raise TransactionHandoffError("missing authority targets in next-worker context")
        triage_allowed_targets = _require_list(triage_packet, "allowed_targets", kind="triage packet")
        orchestration_held_targets = _require_list(orchestration_packet, "held_targets", kind="orchestration packet")
        continuation_allowed_targets = _extract_json_code_block(continuation_text, "Allowed Targets", kind="continuation")
        continuation_held_targets = _extract_json_code_block(continuation_text, "Held Targets", kind="continuation")
        if not isinstance(continuation_allowed_targets, list) or not isinstance(continuation_held_targets, list):
            raise TransactionHandoffError("continuation authority sections must decode to lists")
        if next_worker_context.get("task_state", {}).get("allowed_targets") != triage_allowed_targets:
            raise TransactionHandoffError("triage packet allowed targets disagree with next-worker context")
        if next_worker_context.get("task_state", {}).get("held_targets") != orchestration_held_targets:
            raise TransactionHandoffError("orchestration packet held targets disagree with next-worker context")
        if allowed_targets != triage_allowed_targets:
            raise TransactionHandoffError("allowed targets disagree across transaction artifacts")
        if held_targets != orchestration_held_targets:
            raise TransactionHandoffError("held targets disagree across transaction artifacts")
        if continuation_allowed_targets != allowed_targets:
            raise TransactionHandoffError("continuation allowed targets disagree with transaction scope")
        if continuation_held_targets != held_targets:
            raise TransactionHandoffError("continuation held targets disagree with transaction scope")
        if _require_list(gate_record, "allowed_downstream_use", kind="downstream use gate") != _require_list(
            handoff_packet, "allowed_downstream_use", kind="handoff packet"
        ):
            raise TransactionHandoffError("handoff packet allowed downstream use mismatch")
        record("authority", "passed", "Allowed/held authority preserved across artifacts.")

        evidence_references = transaction_manifest.get("evidence_references", [])
        for required_artifact in ("run_manifest", "model_prompt_packet", "raw_model_output", "supervised_model_attempt", "output_validation", "review_decision", "downstream_use_gate", "handoff_packet"):
            reference = next((ref for ref in evidence_references if ref.get("artifact") == required_artifact), None)
            if reference is None:
                raise TransactionHandoffError(f"missing evidence reference for {required_artifact}")
            if not isinstance(reference.get("path"), str) or not reference["path"].strip():
                raise TransactionHandoffError(f"missing path for {required_artifact}")
            if not Path(reference["path"]).is_file():
                raise TransactionHandoffError(f"missing referenced file for {required_artifact}")
            if "sha256" in reference and reference["sha256"] != _sha256(Path(reference["path"])):
                raise TransactionHandoffError(f"{required_artifact} sha256 does not match referenced file")
        record("evidence_references", "passed", "Required evidence references present.")

        status = "passed"
    except TransactionHandoffError as exc:
        record("preflight", "failed", str(exc))
        status = "failed"

    result = {
        "run_dir": str(run_dir),
        "expected_next_worker_identity": expected_next_worker_identity,
        "status": status,
        "checks": checks,
    }
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / "worker_b_preflight.json"
        _write_json(path, result)
        result["preflight_path"] = path
    return result


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
        "Return raw JSON only.",
        "Return the downstream semantic result only.",
        "Required output fields:",
        "- findings",
        "- reason",
        "Each finding must include a claim and evidence objects with path and detail fields.",
        "Do not reproduce allowed_targets, held_targets, or other deterministic authority facts.",
        "State how you used the accepted prior result and report the bounded downstream conclusion.",
        "Do not redo the first-worker task or expand scope.",
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
        "## Transaction Binding",
        f"```json\n{json.dumps(context['transaction_binding'], indent=2, sort_keys=True)}\n```",
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


def build_worker_b_recipient_run_artifacts(
    *,
    source_run_dir: Path,
    recipient_run_dir: Path,
    recipient_identity: str,
    continuation_path: Path | None = None,
) -> dict[str, Any]:
    if not source_run_dir.is_dir():
        raise TransactionHandoffError(f"missing source run dir: {source_run_dir}")
    if continuation_path is None:
        continuation_path = source_run_dir / "next_worker_continuation.md"
    if not continuation_path.is_file():
        raise TransactionHandoffError(f"missing next-worker continuation: {continuation_path}")
    continuation_text = continuation_path.read_text(encoding="utf-8")
    recipient_run_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = recipient_run_dir / "prompt_to_paste.md"
    prompt_path.write_text(continuation_text, encoding="utf-8")

    source_manifest = _read_json(source_run_dir / "transaction_manifest.json", kind="transaction manifest")
    source_context = _read_json(source_run_dir / "next_worker_context.json", kind="next-worker context")
    source_run_manifest = _read_json(source_run_dir / "run_manifest.json", kind="run manifest")
    recipient_manifest = {
        "schema_version": "zth.recipient_run_manifest.v0.1",
        "source_run_dir": str(source_run_dir),
        "recipient_run_dir": str(recipient_run_dir),
        "recipient_identity": recipient_identity,
        "transaction_id": source_manifest.get("transaction_id"),
        "continuation_path": str(continuation_path),
        "continuation_sha256": _sha256(continuation_path),
        "prompt_path": str(prompt_path),
        "prompt_sha256": _sha256(prompt_path),
        "source_transaction_binding": source_context.get("transaction_binding"),
        "source_run_manifest": {
            "run_id": source_run_manifest.get("run_id"),
            "orchestration_id": source_run_manifest.get("orchestration_id"),
            "triage_id": source_run_manifest.get("triage_id"),
            "prompt_packet_id": source_run_manifest.get("prompt_packet_id"),
        },
    }
    manifest_path = recipient_run_dir / "recipient_run_manifest.json"
    _write_json(manifest_path, recipient_manifest)
    output_contract_path = recipient_run_dir / "output_contract.json"
    _write_json(
        output_contract_path,
        {
            "format": "json",
            "required_fields": ["findings", "reason"],
            "requires_reason": True,
        },
    )
    run_manifest_path = recipient_run_dir / "run_manifest.json"
    _write_json(
        run_manifest_path,
        {
            "report_type": "manual_supervised_attempt_run_manifest.v1",
            "run_id": f"{source_manifest.get('transaction_id')}-recipient",
            "source_transaction_id": source_manifest.get("transaction_id"),
            "source_run_id": source_manifest.get("run_id"),
            "source_run_manifest_path": str(source_run_dir / "run_manifest.json"),
            "recipient_run_manifest_path": str(manifest_path),
            "created_at": _utc_iso(),
            "artifacts": {
                "prompt_to_paste": str(prompt_path),
                "model_prompt_packet": str(prompt_path),
                "output_contract": str(output_contract_path),
                "recipient_run_manifest": str(manifest_path),
                "continuation": str(continuation_path),
            },
        },
    )
    return {
        "recipient_run_dir": recipient_run_dir,
        "run_manifest_path": run_manifest_path,
        "recipient_manifest_path": manifest_path,
        "prompt_path": prompt_path,
        "prompt_sha256": recipient_manifest["prompt_sha256"],
        "continuation_path": continuation_path,
        "continuation_sha256": recipient_manifest["continuation_sha256"],
        "recipient_manifest": recipient_manifest,
    }


def build_authority_bound_semantic_result(
    *,
    semantic_output: dict[str, Any],
    raw_output_path: Path,
    transaction_manifest: dict[str, Any],
    next_worker_context: dict[str, Any],
    output_dir: Path | None = None,
) -> dict[str, Any]:
    if transaction_manifest.get("schema_version") != TRANSACTION_MANIFEST_SCHEMA:
        raise TransactionHandoffError("authority binding requires a transaction manifest")
    if next_worker_context.get("schema_version") != NEXT_WORKER_CONTEXT_SCHEMA:
        raise TransactionHandoffError("authority binding requires a next-worker context")
    if not raw_output_path.is_file():
        raise TransactionHandoffError(f"missing semantic raw output: {raw_output_path}")
    if semantic_output.get("allowed_targets") is not None or semantic_output.get("held_targets") is not None:
        raise TransactionHandoffError("semantic output must not contain authoritative target fields")
    findings = semantic_output.get("findings")
    reason = semantic_output.get("reason")
    if not isinstance(findings, list) or not isinstance(reason, str) or not reason.strip():
        raise TransactionHandoffError("semantic output must contain findings and reason")

    task_state = next_worker_context.get("task_state", {})
    authoritative_allowed_targets = task_state.get("allowed_targets")
    authoritative_held_targets = task_state.get("held_targets")
    if not isinstance(authoritative_allowed_targets, list) or not isinstance(authoritative_held_targets, list):
        raise TransactionHandoffError("next-worker context must include authoritative target lists")

    transaction_binding = next_worker_context.get("transaction_binding")
    if not isinstance(transaction_binding, dict):
        raise TransactionHandoffError("next-worker context must include transaction binding")

    semantic_payload = {
        "findings": deepcopy(findings),
        "reason": reason,
    }
    normalized_result = {
        "schema_version": "zth.authority_bound_semantic_result.v0.1",
        "transaction_id": transaction_manifest.get("transaction_id"),
        "run_id": transaction_manifest.get("run_id"),
        "source_raw_output_path": str(raw_output_path),
        "source_raw_output_sha256": _sha256(raw_output_path),
        "source_transaction_binding": deepcopy(transaction_binding),
        "semantic_output": semantic_payload,
        "authority": {
            "allowed_targets": list(authoritative_allowed_targets),
            "held_targets": list(authoritative_held_targets),
            "next_step_scope": next_worker_context.get("constraints", {}).get("next_step_scope"),
        },
        "derived": {
            "scope_expansion_required": False,
            "authority_conflict": False,
            "normalized": True,
        },
    }
    normalized_path = None
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        normalized_path = output_dir / "authority_bound_semantic_result.json"
        _write_json(normalized_path, normalized_result)
        normalized_result["authority_bound_semantic_result_path"] = str(normalized_path)
    return normalized_result
