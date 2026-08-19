#!/usr/bin/env python3
"""Model-free Run 4 cost-aware routing design audit.

This module enumerates the existing Run 1/Run 2 capability evidence without
reading Run 3C outcomes and without executing any intervention.  It is an
audit/design tool, not the Run 4 router.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from local_harness.capability_cards import (
    EVIDENCE_RESOLUTIONS,
    INTERVENTION_SOURCES,
    RESOURCE_TIERS,
    _resolution_key,
    build_hierarchical_evidence,
    recommend_intervention,
)
from local_harness.resource_telemetry import (
    load_approved_resource_weights,
    validate_resource_weight_bindings,
)


FROZEN_RUN3_BUNDLE_SHA256 = "383274a27c89345b3a8bcede75123420973a7a3e53318224e6460c0d05b47fc1"
FROZEN_RUN3_ROUTER_SOURCE_SHA256 = "3ded696a64c12a58979d4b6af3e6662f17463ed9f991da01585ad586f490e053"
FROZEN_RESOURCE_MANIFEST_SHA256 = "33ad2521dc5acc0be5a67b3ef77c167e882cf6ce53140dc60acc8f89c9ad76ab"
FROZEN_TIME_PRIORS = {
    "worker_time_ms": 5276.567,
    "local_teacher_time_ms": 16220.624,
    "external_teacher_time_ms": 28704.012,
}
COST_AWARE_INTERVENTIONS = (
    "deterministic_patch_retry",
    "local_teacher",
    "external_teacher",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def immediate_action_cost(intervention: str, weights: Mapping[str, Any]) -> float:
    """Expected immediate action cost, including the resulting worker retry."""
    if intervention == "deterministic_patch_retry":
        return float(weights["worker_time_ms"])
    if intervention == "local_teacher":
        return float(weights["local_teacher_time_ms"]) + float(weights["worker_time_ms"])
    if intervention == "external_teacher":
        return float(weights["external_teacher_time_ms"]) + float(weights["worker_time_ms"])
    raise ValueError(f"unsupported cost-aware intervention: {intervention}")


def verify_cost_audit_inputs(
    *,
    policy_path: Path,
    bundle_path: Path,
    router_source_path: Path,
    resource_manifest_path: Path,
) -> dict[str, Any]:
    """Fail closed if the audit is not bound to the frozen Run 3 inputs."""
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    if policy.get("capability_bundle_sha256") != FROZEN_RUN3_BUNDLE_SHA256:
        raise ValueError("Run 3 capability bundle binding changed")
    if policy.get("router_source_sha256") != FROZEN_RUN3_ROUTER_SOURCE_SHA256:
        raise ValueError("Run 3 router source binding changed")
    if _sha256(bundle_path) != policy["capability_bundle_sha256"]:
        raise ValueError("capability bundle digest mismatch")
    if _sha256(router_source_path) != policy["router_source_sha256"]:
        raise ValueError("router source digest mismatch")
    manifest = load_approved_resource_weights(resource_manifest_path)
    if manifest.get("manifest_sha256") != FROZEN_RESOURCE_MANIFEST_SHA256:
        raise ValueError("approved resource manifest binding changed")
    for name, expected in FROZEN_TIME_PRIORS.items():
        if manifest.get("weights", {}).get(name) != expected:
            raise ValueError(f"frozen resource prior changed: {name}")
    provenance = manifest["provenance"]
    validate_resource_weight_bindings(
        manifest,
        worker_model=provenance["worker_model"],
        local_teacher_model=provenance["local_teacher_model"],
        external_teacher_identity=provenance["external_teacher_identity"],
        external_timeout_seconds=provenance["external_timeout_seconds"],
    )
    return {"policy": policy, "bundle": bundle, "resource_manifest": manifest}


def _representative_signatures(bundle: Mapping[str, Any], resolution: str) -> dict[str, dict[str, Any]]:
    representatives: dict[str, dict[str, Any]] = {}
    for card in bundle.get("cards", []):
        signature = card["context"]["failure_signature"]
        key = _resolution_key(signature, resolution)
        representatives.setdefault(key, signature)
    return representatives


def _validation_for_signature(signature: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "structural_checks": [{"check_id": check_id, "status": "failed"} for check_id in signature.get("structural", [])],
        "semantic_checks": [{"check_id": check_id, "status": "failed"} for check_id in signature.get("semantic", [])],
    }


def enumerate_cost_choice_sets(bundle: Mapping[str, Any], resource_manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Enumerate all evidence keys and all cost-aware intervention choices."""
    hierarchy = build_hierarchical_evidence(bundle)
    weights = resource_manifest["weights"]
    choice_sets: list[dict[str, Any]] = []
    for resolution in EVIDENCE_RESOLUTIONS:
        representatives = _representative_signatures(bundle, resolution)
        rows = hierarchy[resolution]
        for resolution_key in sorted(representatives):
            signature = representatives[resolution_key]
            existing = {
                row["intervention"]: row
                for row in rows
                if row["resolution_key"] == resolution_key
            }
            choices = []
            for intervention in COST_AWARE_INTERVENTIONS:
                row = existing.get(intervention)
                if row is None:
                    row = {
                        "resolution": resolution,
                        "resolution_key": resolution_key,
                        "task_family": signature["task_family"],
                        "intervention": intervention,
                        "eligible_task_opportunities": 0,
                        "worker_retry_attempts": 0,
                        "rescued_tasks": 0,
                        "rescue_rate": 0.0,
                        "evidence_status": "insufficient",
                        "evidence_polarity": "insufficient",
                        "source_runs": [],
                        "source_card_ids": [],
                    }
                choices.append({
                    "resolution": resolution,
                    "evidence_key": resolution_key,
                    "task_family": signature["task_family"],
                    "intervention": intervention,
                    "resource_tier": RESOURCE_TIERS[intervention],
                    "immediate_expected_elapsed_ms": immediate_action_cost(intervention, weights),
                    "eligible_task_opportunities": row["eligible_task_opportunities"],
                    "worker_retry_attempts": row["worker_retry_attempts"],
                    "rescued_tasks": row["rescued_tasks"],
                    "rescue_rate": row["rescue_rate"],
                    "evidence_status": row["evidence_status"],
                    "evidence_polarity": row["evidence_polarity"],
                    "source_runs": row.get("source_runs", []),
                    "source_card_ids": row.get("source_card_ids", []),
                })
            current = recommend_intervention(
                task_family=signature["task_family"],
                validation=_validation_for_signature(signature),
                available_interventions=INTERVENTION_SOURCES,
                cards={**bundle, "hierarchy": hierarchy},
            )
            positive = [choice for choice in choices if choice["evidence_polarity"] == "supported_positive"]
            min_cost = min((choice["immediate_expected_elapsed_ms"] for choice in positive), default=None)
            choice_sets.append({
                "resolution": resolution,
                "evidence_key": resolution_key,
                "task_family": signature["task_family"],
                "representative_signature": signature,
                "choices": choices,
                "supported_positive_interventions": [choice["intervention"] for choice in positive],
                "supported_negative_interventions": [choice["intervention"] for choice in choices if choice["evidence_polarity"] == "supported_negative"],
                "current_run3_routing": {
                    "recommended_intervention": current["recommended_intervention"],
                    "routing_disposition": current["routing_disposition"],
                    "evidence_resolution": current["evidence_resolution"],
                },
                "cheapest_supported_positive_interventions": [choice["intervention"] for choice in positive if choice["immediate_expected_elapsed_ms"] == min_cost],
                "more_expensive_supported_positive_interventions": [choice["intervention"] for choice in positive if min_cost is not None and choice["immediate_expected_elapsed_ms"] > min_cost],
            })
    return {
        "schema": "zth_run4_cost_choice_sets_v1",
        "basis": "frozen median elapsed-time priors; capability evidence from Run 1 and Run 2 only",
        "interventions": list(COST_AWARE_INTERVENTIONS),
        "resource_weights_ms": {key: weights[key] for key in FROZEN_TIME_PRIORS},
        "choice_sets": choice_sets,
    }


def summarize_cost_choice_sets(audit: Mapping[str, Any]) -> dict[str, Any]:
    choice_sets = list(audit["choice_sets"])
    distribution = {"zero": 0, "one": 0, "two": 0, "three_or_more": 0}
    by_resolution: dict[str, dict[str, int]] = {}
    current_cheapest = 0
    cheaper_alternative = 0
    lower_success_cheaper = 0
    for choice_set in choice_sets:
        count = len(choice_set["supported_positive_interventions"])
        bucket = "zero" if count == 0 else "one" if count == 1 else "two" if count == 2 else "three_or_more"
        distribution[bucket] += 1
        resolution = choice_set["resolution"]
        by_resolution.setdefault(resolution, {key: 0 for key in distribution})[bucket] += 1
        if count == 0:
            continue
        current = choice_set["current_run3_routing"]["recommended_intervention"]
        cheapest = choice_set["cheapest_supported_positive_interventions"]
        if current in cheapest:
            current_cheapest += 1
        if current and current not in cheapest:
            cheaper_alternative += 1
        positive = {choice["intervention"]: choice for choice in choice_set["choices"] if choice["evidence_polarity"] == "supported_positive"}
        if count >= 2 and cheapest:
            cheapest_rate = positive[cheapest[0]]["rescue_rate"]
            if any(choice["rescue_rate"] > cheapest_rate for choice in positive.values()):
                lower_success_cheaper += 1
    total = len(choice_sets)
    return {
        "schema": "zth_run4_cost_choice_summary_v1",
        "evidence_key_count": total,
        "supported_positive_choice_distribution": distribution,
        "by_resolution": by_resolution,
        "current_recommendation_already_cheapest_supported_positive": current_cheapest,
        "current_recommendation_with_cheaper_supported_alternative": cheaper_alternative,
        "cheaper_supported_alternative_with_lower_empirical_success": lower_success_cheaper,
        "cost_can_change_supported_choice_count": distribution["two"] + distribution["three_or_more"],
        "cost_can_change_supported_choice_percent": (distribution["two"] + distribution["three_or_more"]) / total * 100 if total else 0.0,
        "resource_weights_ms": audit["resource_weights_ms"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--router-source", type=Path, required=True)
    parser.add_argument("--resource-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    inputs = verify_cost_audit_inputs(
        policy_path=args.policy,
        bundle_path=args.bundle,
        router_source_path=args.router_source,
        resource_manifest_path=args.resource_manifest,
    )
    audit = enumerate_cost_choice_sets(inputs["bundle"], inputs["resource_manifest"])
    summary = summarize_cost_choice_sets(audit)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "run4_cost_aware_choice_sets.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_dir / "run4_cost_aware_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
