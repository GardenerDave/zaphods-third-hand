#!/usr/bin/env python3
"""Frozen, model-free Run 4 capability-first/economic policy helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from local_harness.run4a_comparative_review import verify_comparative_freeze


POLICY_MODES = ("capability_first", "cheapest_supported_positive")
INTERVENTION_ORDER = ("deterministic_patch_retry", "local_teacher", "external_teacher")
TIME_COSTS_MS = {
    "deterministic_patch_retry": 5276.567,
    "local_teacher": 21497.191,
    "external_teacher": 33980.579,
}


class Run4PolicyError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _positive_rows(evidence: Mapping[str, Any], evidence_key: str) -> list[dict[str, Any]]:
    block = evidence.get("blocks", {}).get(evidence_key)
    if block is None:
        raise Run4PolicyError(f"unknown frozen evidence key: {evidence_key}")
    rows = []
    for intervention, row in block.items():
        if row.get("evidence_status") == "supported_positive":
            rows.append({
                "intervention": intervention,
                "rescue_rate": float(row["rescue_rate"]),
                "expected_cost_ms": float(row["expected_immediate_action_cost_ms"]),
            })
    return rows


def choose_intervention(evidence: Mapping[str, Any], evidence_key: str, mode: str) -> dict[str, Any]:
    """Select only from supported-positive frozen evidence."""
    if mode not in POLICY_MODES:
        raise Run4PolicyError(f"unknown policy mode: {mode}")
    rows = _positive_rows(evidence, evidence_key)
    if not rows:
        return {
            "policy_mode": mode,
            "evidence_key": evidence_key,
            "routing_disposition": "abstain",
            "recommended_intervention": None,
            "supported_positive_candidates": [],
            "authority": "experiment_advisory_policy_only",
        }
    if mode == "capability_first":
        key = lambda row: (-row["rescue_rate"], row["expected_cost_ms"], row["intervention"])
    else:
        key = lambda row: (row["expected_cost_ms"], -row["rescue_rate"], row["intervention"])
    selected = sorted(rows, key=key)[0]
    return {
        "policy_mode": mode,
        "evidence_key": evidence_key,
        "routing_disposition": "recommend",
        "recommended_intervention": selected["intervention"],
        "supported_positive_candidates": sorted(rows, key=lambda row: (row["expected_cost_ms"], row["intervention"])),
        "authority": "experiment_advisory_policy_only",
    }


def expected_policy_matrix(evidence: Mapping[str, Any]) -> dict[str, dict[str, str | None]]:
    return {
        key: {mode: choose_intervention(evidence, key, mode)["recommended_intervention"] for mode in POLICY_MODES}
        for key in ("contradiction-handling", "triage-routing", "scope-authority-boundary", "unsupported-certainty")
    }


def build_policy_freeze(*, comparative_freeze_path: Path, policy_source_path: Path) -> dict[str, Any]:
    evidence = verify_comparative_freeze(comparative_freeze_path)
    matrix = expected_policy_matrix(evidence)
    artifact = {
        "schema": "zth_run4_economic_routing_policy_freeze_v1",
        "status": "reviewed_frozen_policy",
        "authority": "experiment_only_advisory_policy",
        "comparative_evidence_freeze_path": str(comparative_freeze_path),
        "comparative_evidence_freeze_sha256": evidence["freeze_sha256"],
        "support_thresholds": {"minimum_comparable_opportunities": 3, "minimum_rescue_rate": 0.5},
        "eligibility": "supported_positive only; negative, observed, and insufficient evidence are never selectable",
        "policies": {
            "capability_first": "highest empirical validated rescue rate, then lowest expected cost, then intervention ID",
            "cheapest_supported_positive": "lowest expected cost, then highest empirical validated rescue rate, then intervention ID",
            "no_supported_positive": "abstain/fail closed",
        },
        "resource_costs_ms": dict(TIME_COSTS_MS),
        "target_evidence_keys": list(matrix),
        "expected_policy_matrix": matrix,
        "router_source_path": str(policy_source_path),
        "router_source_sha256": sha256_path(policy_source_path),
        "execution_authority": "This freeze authorizes only the explicitly preregistered Run 4 comparison; it does not alter normal ZTH routing.",
        "policy_sha256": None,
    }
    basis = dict(artifact)
    basis["policy_sha256"] = None
    artifact["policy_sha256"] = sha256_bytes(canonical(basis).encode())
    return artifact


def verify_policy_freeze(path: Path, comparative_freeze_path: Path, source_path: Path) -> dict[str, Any]:
    artifact = json.loads(path.read_text(encoding="utf-8"))
    basis = dict(artifact)
    recorded = basis.pop("policy_sha256")
    expected = sha256_bytes(canonical({**basis, "policy_sha256": None}).encode())
    if recorded != expected:
        raise Run4PolicyError("policy freeze digest mismatch")
    evidence = verify_comparative_freeze(comparative_freeze_path)
    if artifact["comparative_evidence_freeze_sha256"] != evidence["freeze_sha256"]:
        raise Run4PolicyError("comparative evidence binding mismatch")
    if artifact["router_source_sha256"] != sha256_path(source_path):
        raise Run4PolicyError("router source binding mismatch")
    if artifact["expected_policy_matrix"] != expected_policy_matrix(evidence):
        raise Run4PolicyError("policy matrix drift")
    return artifact

