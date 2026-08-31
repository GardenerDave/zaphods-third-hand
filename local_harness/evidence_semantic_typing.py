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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path}")
    return payload


@dataclass(frozen=True)
class DerivedProperty:
    property: str
    derivation: str
    rule_id: str
    source_refs: list[str]
    trust_class: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "property": self.property,
            "derivation": self.derivation,
            "rule_id": self.rule_id,
            "source_refs": list(self.source_refs),
            "trust_class": self.trust_class,
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


def _source_ref(path: Path) -> str:
    return str(path.resolve())


def derive_typed_evidence_from_bundle(*, evidence_id: str, source_paths: list[Path]) -> EvidenceTypingResult:
    source_refs = [_source_ref(path) for path in source_paths]
    derived: list[DerivedProperty] = []
    unknown: set[str] = set(ALLOWED_PROPERTIES)
    by_name = {path.name: path for path in source_paths}

    local_model_call = by_name.get("local_model_call.json")
    output_validation = by_name.get("output_validation.json")
    review_decision = by_name.get("review_decision.json")
    downstream_use_gate = by_name.get("downstream_use_gate.json")
    handoff_packet = by_name.get("handoff_packet.json")
    raw_output = by_name.get("raw_model_output.txt")

    if local_model_call and output_validation and raw_output:
        call = _load_json(local_model_call)
        validation = _load_json(output_validation)
        if call.get("raw_output_sha256") == _sha256(raw_output) and validation.get("validation_status") == "passed":
            derived.append(
                DerivedProperty(
                    property="raw_response_integrity",
                    derivation="raw_output_sha256_matches_preserved_artifact_and_validation_passed",
                    rule_id="raw_response_integrity_v1",
                    source_refs=[_source_ref(raw_output), _source_ref(local_model_call), _source_ref(output_validation)],
                    trust_class="system_derived",
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
                    property="bounded_handoff_success",
                    derivation="accepted_review_and_allowed_gate_with_prepared_handoff",
                    rule_id="bounded_handoff_success_v1",
                    source_refs=[
                        _source_ref(review_decision),
                        _source_ref(downstream_use_gate),
                        _source_ref(handoff_packet),
                    ],
                    trust_class="system_derived",
                )
            )
            unknown.discard("bounded_handoff_success")
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
                    trust_class="system_derived",
                )
            )
            unknown.discard("semantic_acceptance")

    return EvidenceTypingResult(
        evidence_id=evidence_id,
        source_refs=source_refs,
        derived_properties=derived,
        unknown_properties=sorted(unknown),
        trust_summary="system_derived" if derived else "unknown",
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
