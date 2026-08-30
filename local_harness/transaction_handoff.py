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
                "raw_output_artifact": None,
                "raw_output_reference": attempt_record.get("provenance", {}).get("raw_output_source_path"),
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
    next_worker_context["previous_attempt"]["result_reference"]["raw_output_artifact"] = _artifact_reference(
        Path(raw_output_reference),
        artifact="raw_model_output",
    )
    return next_worker_context


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
