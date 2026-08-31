#!/usr/bin/env python3
"""Conservative evidence-side semantic typing from structured ZTH artifacts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ALLOWED_PROPERTIES = {
    "transport_qualification",
    "bounded_handoff_success",
    "semantic_capability",
    "raw_response_integrity",
    "semantic_acceptance",
}

ALLOWED_TRUST_CLASSES = {
    "system_derived",
    "operator_frozen",
    "model_inferred",
    "unknown",
}

ALLOWED_DERIVATION_METHODS = {
    "deterministic",
    "operator_labeled",
    "model_interpreted",
    "unknown",
}

ALLOWED_SEMANTIC_SOURCES = {
    "machine_observable",
    "operator",
    "reviewer_model",
    "worker_model",
    "mixed",
    "unknown",
}

ALLOWED_POLICY_TRUST = {
    "trusted",
    "bounded_trusted",
    "advisory",
    "unknown",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path}")
    return payload


def _load_json_or_jsonl(path: Path) -> dict[str, Any]:
    if path.suffix.lower() != ".jsonl":
        return _load_json(path)
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        raise ValueError(f"JSONL object sequence required: {path}")
    payload = json.loads(lines[-1])
    if not isinstance(payload, dict):
        raise ValueError(f"JSONL object required: {path}")
    return payload


@dataclass(frozen=True)
class DerivedProperty:
    property: str
    derivation: str
    rule_id: str
    source_refs: list[str]
    derivation_method: str
    semantic_source: str
    policy_trust: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "property": self.property,
            "derivation": self.derivation,
            "rule_id": self.rule_id,
            "source_refs": list(self.source_refs),
            "derivation_method": self.derivation_method,
            "semantic_source": self.semantic_source,
            "policy_trust": self.policy_trust,
        }


@dataclass(frozen=True)
class EvidenceTypingResult:
    evidence_id: str
    source_refs: list[str]
    derived_properties: list[DerivedProperty]
    unknown_properties: list[str]
    trust_summary: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "source_refs": list(self.source_refs),
            "derived_properties": [item.as_dict() for item in self.derived_properties],
            "unknown_properties": list(self.unknown_properties),
            "trust_summary": self.trust_summary,
        }


@dataclass(frozen=True)
class TransportQualificationRef:
    artifact_ref: str
    artifact_sha256: str
    qualification_id: str | None = None
    qualification_selector: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "artifact_ref": self.artifact_ref,
            "artifact_sha256": self.artifact_sha256,
            "qualification_id": self.qualification_id,
            "qualification_selector": self.qualification_selector,
        }


@dataclass(frozen=True)
class HandoffCompletionRef:
    artifact_ref: str
    artifact_sha256: str
    handoff_id: str | None = None
    downstream_attempt_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "artifact_ref": self.artifact_ref,
            "artifact_sha256": self.artifact_sha256,
            "handoff_id": self.handoff_id,
            "downstream_attempt_id": self.downstream_attempt_id,
        }


def _source_ref(path: Path) -> str:
    return str(path.resolve())


@dataclass(frozen=True)
class TransportQualificationVerification:
    artifact_integrity: bool
    qualification_passed: bool
    endpoint_match: bool | None
    model_match: bool | None
    scope_match: bool | None
    freshness_match: bool | None
    policy_usable: bool
    diagnostics: list[str]
    source_refs: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "artifact_integrity": self.artifact_integrity,
            "qualification_passed": self.qualification_passed,
            "endpoint_match": self.endpoint_match,
            "model_match": self.model_match,
            "scope_match": self.scope_match,
            "freshness_match": self.freshness_match,
            "policy_usable": self.policy_usable,
            "diagnostics": list(self.diagnostics),
            "source_refs": list(self.source_refs),
        }


@dataclass(frozen=True)
class HandoffCompletionVerification:
    artifact_integrity: bool
    completion_detected: bool
    handoff_match: bool | None
    downstream_attempt_match: bool | None
    endpoint_match: bool | None
    model_match: bool | None
    policy_usable: bool
    diagnostics: list[str]
    source_refs: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "artifact_integrity": self.artifact_integrity,
            "completion_detected": self.completion_detected,
            "handoff_match": self.handoff_match,
            "downstream_attempt_match": self.downstream_attempt_match,
            "endpoint_match": self.endpoint_match,
            "model_match": self.model_match,
            "policy_usable": self.policy_usable,
            "diagnostics": list(self.diagnostics),
            "source_refs": list(self.source_refs),
        }


def _resolve_artifact_ref(artifact_ref: str, artifact_sha256: str, *, kind: str) -> tuple[Path, dict[str, Any], list[str]]:
    if not isinstance(artifact_ref, str) or not artifact_ref.strip():
        raise ValueError(f"{kind}.artifact_ref must be a non-empty string")
    if not isinstance(artifact_sha256, str) or not artifact_sha256.strip():
        raise ValueError(f"{kind}.artifact_sha256 must be a non-empty string")
    path = Path(artifact_ref)
    if not path.is_file():
        raise FileNotFoundError(path)
    actual_sha = _sha256(path)
    if actual_sha != artifact_sha256:
        raise ValueError(f"{kind} artifact sha256 mismatch")
    payload = _load_json_or_jsonl(path)
    return path, payload, [str(path.resolve())]


def _first_string(payload: dict[str, Any], paths: list[tuple[str, ...]]) -> str | None:
    for path in paths:
        cursor: Any = payload
        for key in path:
            if not isinstance(cursor, dict):
                break
            cursor = cursor.get(key)
        if isinstance(cursor, str) and cursor.strip():
            return cursor
    return None


def resolve_transport_qualification_reference(
    *,
    qualification_ref: TransportQualificationRef,
    transaction_endpoint: str,
    transaction_model: str,
    transaction_scope: str | None = None,
) -> TransportQualificationVerification:
    path, payload, source_refs = _resolve_artifact_ref(
        qualification_ref.artifact_ref,
        qualification_ref.artifact_sha256,
        kind="transport qualification",
    )
    diagnostics: list[str] = []
    qualification_passed = bool(
        payload.get("local_transport_qualified") is True
        or payload.get("external_transport_qualified") is True
        or payload.get("qualification_passed") is True
        or payload.get("passed") is True
    )
    if not qualification_passed:
        diagnostics.append("qualification artifact did not indicate a passed transport qualification")
    endpoint = _first_string(
        payload,
        [("local", "request_url"), ("request_url",), ("endpoint",), ("local", "endpoint")],
    )
    model = _first_string(
        payload,
        [("local", "model"), ("model",), ("external", "model"), ("local", "resolved_model")],
    )
    endpoint_match = endpoint == transaction_endpoint if endpoint is not None else None
    model_match = model == transaction_model if model is not None else None
    if endpoint_match is False:
        diagnostics.append("endpoint mismatch")
    if model_match is False:
        diagnostics.append("model mismatch")
    scope = _first_string(payload, [("scope",), ("lane",), ("qualification_scope",), ("local", "scope")])
    if transaction_scope is None or scope is None:
        scope_match: bool | None = None
        diagnostics.append("scope match unresolved")
    else:
        scope_match = scope == transaction_scope
        if scope_match is False:
            diagnostics.append("scope mismatch")
    freshness = _first_string(payload, [("valid_until",), ("expires_at",), ("qualified_until",)])
    freshness_match: bool | None = None if freshness is None else True
    policy_usable = bool(
        qualification_passed
        and endpoint_match is not False
        and model_match is not False
        and scope_match is not False
        and freshness_match is not False
        and scope_match is not None
    )
    if not policy_usable:
        diagnostics.append("qualification not usable for policy consumption")
    return TransportQualificationVerification(
        artifact_integrity=True,
        qualification_passed=qualification_passed,
        endpoint_match=endpoint_match,
        model_match=model_match,
        scope_match=scope_match,
        freshness_match=freshness_match,
        policy_usable=policy_usable,
        diagnostics=diagnostics,
        source_refs=source_refs,
    )


def resolve_handoff_completion_reference(
    *,
    completion_ref: HandoffCompletionRef,
    prepared_handoff_id: str,
    transaction_endpoint: str,
    transaction_model: str,
) -> HandoffCompletionVerification:
    path, payload, source_refs = _resolve_artifact_ref(
        completion_ref.artifact_ref,
        completion_ref.artifact_sha256,
        kind="handoff completion",
    )
    diagnostics: list[str] = []
    completion_detected = bool(
        payload.get("call_status") == "completed"
        or payload.get("completed") is True
        or payload.get("completion_status") == "completed"
        or payload.get("state") == "completed"
    )
    if not completion_detected:
        diagnostics.append("completion artifact did not indicate completion")
    handoff_id = _first_string(payload, [("handoff_id",), ("source_handoff_id",), ("prepared_handoff_id",)])
    downstream_attempt_id = _first_string(
        payload,
        [("downstream_attempt_id",), ("attempt_id",), ("source_attempt_id",)],
    )
    endpoint = _first_string(
        payload,
        [("endpoint",), ("request_url",), ("local", "request_url"), ("request_provenance", "request_url")],
    )
    model = _first_string(payload, [("model",), ("resolved_model",), ("local", "model")])
    handoff_match = handoff_id == prepared_handoff_id if handoff_id is not None else None
    if handoff_match is False:
        diagnostics.append("handoff mismatch")
    downstream_attempt_match = downstream_attempt_id is not None
    if downstream_attempt_match is False:
        diagnostics.append("missing downstream attempt binding")
    endpoint_match = endpoint == transaction_endpoint if endpoint is not None else None
    model_match = model == transaction_model if model is not None else None
    if endpoint_match is False:
        diagnostics.append("endpoint mismatch")
    if model_match is False:
        diagnostics.append("model mismatch")
    policy_usable = bool(
        completion_detected
        and handoff_match is not False
        and downstream_attempt_match is not False
        and endpoint_match is not False
        and model_match is not False
    )
    if not policy_usable:
        diagnostics.append("completion not usable for policy consumption")
    return HandoffCompletionVerification(
        artifact_integrity=True,
        completion_detected=completion_detected,
        handoff_match=handoff_match,
        downstream_attempt_match=downstream_attempt_match,
        endpoint_match=endpoint_match,
        model_match=model_match,
        policy_usable=policy_usable,
        diagnostics=diagnostics,
        source_refs=source_refs,
    )


def derive_typed_evidence_from_bundle(*, evidence_id: str, source_paths: list[Path]) -> EvidenceTypingResult:
    source_refs = [_source_ref(path) for path in source_paths]
    derived: list[DerivedProperty] = []
    unknown: set[str] = set(ALLOWED_PROPERTIES)
    by_name = {path.name: path for path in source_paths}

    local_model_call = by_name.get("local_model_call.json")
    review_decision = by_name.get("review_decision.json")
    downstream_use_gate = by_name.get("downstream_use_gate.json")
    handoff_packet = by_name.get("handoff_packet.json")
    raw_output = by_name.get("raw_model_output.txt")

    if local_model_call and raw_output:
        call = _load_json(local_model_call)
        if call.get("call_status") == "completed" and call.get("raw_output_sha256") == _sha256(raw_output):
            derived.append(
                DerivedProperty(
                    property="raw_response_integrity",
                    derivation="raw_output_sha256_matches_preserved_artifact_and_call_completed",
                    rule_id="raw_response_integrity_v1",
                    source_refs=[_source_ref(raw_output), _source_ref(local_model_call)],
                    derivation_method="deterministic",
                    semantic_source="machine_observable",
                    policy_trust="trusted",
                )
            )
            unknown.discard("raw_response_integrity")

    if review_decision and downstream_use_gate and handoff_packet:
        decision = _load_json(review_decision)
        gate = _load_json(downstream_use_gate)
        handoff = _load_json(handoff_packet)
        if decision.get("decision") == "accepted" and gate.get("gate_status") == "allowed" and handoff.get("handoff_status") == "prepared":
            derived.append(
                DerivedProperty(
                    property="semantic_acceptance",
                    derivation="accepted_review_and_allowed_gate_with_prepared_handoff",
                    rule_id="semantic_acceptance_v1",
                    source_refs=[
                        _source_ref(review_decision),
                        _source_ref(downstream_use_gate),
                        _source_ref(handoff_packet),
                    ],
                    derivation_method="deterministic",
                    semantic_source="reviewer_model",
                    policy_trust="advisory",
                )
            )
            unknown.discard("semantic_acceptance")

    trust_values = {item.policy_trust for item in derived}
    if not derived:
        trust_summary = "unknown"
    elif len(trust_values) == 1:
        trust_summary = next(iter(trust_values))
    else:
        trust_summary = "mixed"

    return EvidenceTypingResult(
        evidence_id=evidence_id,
        source_refs=source_refs,
        derived_properties=derived,
        unknown_properties=sorted(unknown),
        trust_summary=trust_summary,
    )


def build_source_inventory(*, evidence_id: str, projected_evidence_path: Path, bundle_paths: list[Path], source_type: str) -> dict[str, Any]:
    evidence_projection = _load_json(projected_evidence_path)
    evidence_sources = []
    for path in bundle_paths:
        evidence_sources.append(
            {
                "path": str(path),
                "sha256": _sha256(path),
                "source_type": source_type,
                "file_name": path.name,
            }
        )
    return {
        "evidence_id": evidence_id,
        "projected_evidence_path": str(projected_evidence_path),
        "projected_evidence_sha256": _sha256(projected_evidence_path),
        "projected_evidence_source_count": len(evidence_projection.get("evidence_sources", [])),
        "structured_fields_available": sorted(k for k in evidence_projection.keys() if isinstance(k, str)),
        "bundle_sources": evidence_sources,
    }
