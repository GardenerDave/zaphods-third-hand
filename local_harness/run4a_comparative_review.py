#!/usr/bin/env python3
"""Freeze and audit completed Run 4A comparative intervention evidence.

This module is model-free and review-only.  It reads the terminal Run 4A
artifacts, verifies the preregistered result matrix, computes the expected-cost
Pareto frontier, and compares candidate objective functions.  It never writes
to the capability bundle, routing policy, or resource-weight manifest.
"""

from __future__ import annotations

import hashlib
import json
import statistics
from pathlib import Path
from typing import Any, Mapping


INTERVENTIONS = ("deterministic_patch_retry", "local_teacher", "external_teacher")
BLOCKS = ("contradiction-handling", "triage-routing", "scope-authority-boundary", "unsupported-certainty")
TARGET_RESOLUTIONS = {
    "contradiction-handling": "task_family",
    "triage-routing": "task_family",
    "scope-authority-boundary": "failure_class",
    "unsupported-certainty": "task_family",
}
EXPECTED_MATRIX = {
    "contradiction-handling": {
        "deterministic_patch_retry": (4, 2, "supported_positive"),
        "local_teacher": (4, 0, "supported_negative"),
        "external_teacher": (4, 1, "supported_negative"),
    },
    "triage-routing": {
        "deterministic_patch_retry": (4, 2, "supported_positive"),
        "local_teacher": (4, 2, "supported_positive"),
        "external_teacher": (4, 3, "supported_positive"),
    },
    "scope-authority-boundary": {
        "deterministic_patch_retry": (4, 1, "supported_negative"),
        "local_teacher": (4, 4, "supported_positive"),
        "external_teacher": (4, 4, "supported_positive"),
    },
    "unsupported-certainty": {
        "deterministic_patch_retry": (4, 3, "supported_positive"),
        "local_teacher": (4, 2, "supported_positive"),
        "external_teacher": (4, 3, "supported_positive"),
    },
}
TIME_PRIORS_MS = {
    "deterministic_patch_retry": 5276.567,
    "local_teacher": 21497.191,
    "external_teacher": 33980.579,
}
PREREG_PATH = Path("docs/research/RUN_4A_PREREGISTRATION_2026-08-19.json")
RESOURCE_MANIFEST_PATH = Path("docs/research/RUN_4_RESOURCE_WEIGHTS_FREEZE_2026-08-19.json")
CAPABILITY_BUNDLE_PATH = Path(".work/capability_cards/capability_cards.json")
ROUTING_POLICY_PATH = Path("docs/research/RUN_3_ROUTING_POLICY_FREEZE_2026-08-18.json")


class Run4AReviewError(ValueError):
    """Raised when terminal evidence is missing or inconsistent."""


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def repo_ref(path: Path) -> str:
    """Use repository-relative provenance in tracked artifacts when possible."""
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        raise Run4AReviewError("cannot summarize an empty timing series")
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def summarize_timings(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {"count": 0}
    return {
        "count": len(values),
        "min_ms": min(values),
        "p25_ms": _percentile(values, 0.25),
        "median_ms": statistics.median(values),
        "mean_ms": statistics.mean(values),
        "p75_ms": _percentile(values, 0.75),
        "max_ms": max(values),
    }


def _load(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Run4AReviewError(f"cannot load {path}: {exc}") from exc


def _assert_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise Run4AReviewError(f"{label} mismatch: expected {expected!r}, got {actual!r}")


def _terminal_arm_paths(run_root: Path) -> list[Path]:
    return sorted(run_root.glob("tasks/*/arms/*/arm_summary.json"))


def verify_terminal_run4a(
    run_root: Path,
    *,
    prereg_path: Path = PREREG_PATH,
    capability_bundle_path: Path = CAPABILITY_BUNDLE_PATH,
    routing_policy_path: Path = ROUTING_POLICY_PATH,
    resource_manifest_path: Path = RESOURCE_MANIFEST_PATH,
) -> dict[str, Any]:
    """Verify terminal Run 4A evidence and return its source objects."""
    prereg = _load(prereg_path)
    manifest = _load(run_root / "execution_manifest.json")
    aggregate = _load(run_root / "aggregate.json")
    _assert_equal(manifest.get("status"), "experiment_completed", "execution status")
    _assert_equal(aggregate.get("status"), "review_required", "aggregate status")
    _assert_equal(aggregate.get("capability_bundle_modified"), False, "capability bundle mutation flag")
    _assert_equal(aggregate.get("routing_policy_modified"), False, "routing policy mutation flag")

    selected = []
    for block in BLOCKS:
        selection = manifest.get("selections", {}).get(block)
        if not selection or not selection.get("block_complete"):
            raise Run4AReviewError(f"block is not complete: {block}")
        _assert_equal(selection.get("selected_count"), 4, f"selected count for {block}")
        selected.extend(selection["included_task_ids"])
        for task_id, eligible in selection.get("eligibility", {}).items():
            _assert_equal(eligible, True, f"baseline eligibility for {task_id}")
    _assert_equal(len(manifest.get("selections", {})), 4, "selection block count")
    _assert_equal(len(selected), 16, "included task count")
    _assert_equal(len(manifest.get("candidate_states", {})), 20, "baseline candidate count")
    _assert_equal(sum(state == "baseline_terminal" for state in manifest["candidate_states"].values()), 4, "reserve baseline count")
    _assert_equal(len(_terminal_arm_paths(run_root)), 48, "terminal intervention arm count")
    _assert_equal(manifest.get("model_calls_started"), True, "model-call execution marker")

    for path in _terminal_arm_paths(run_root):
        arm = _load(path)
        _assert_equal(arm.get("transport_valid"), True, f"transport validity for {path}")
        _assert_equal(arm.get("transport_classification"), "model_response", f"transport classification for {path}")
        _assert_equal(arm.get("capability_verdict_available"), True, f"capability verdict for {path}")

    for block, interventions in EXPECTED_MATRIX.items():
        for intervention, (opportunities, rescues, status) in interventions.items():
            row = aggregate["blocks"][block][intervention]
            _assert_equal(row["comparable_opportunities"], opportunities, f"opportunities {block}/{intervention}")
            _assert_equal(row["valid_model_responses"], opportunities, f"valid responses {block}/{intervention}")
            _assert_equal(row["infrastructure_exclusions"], 0, f"infrastructure exclusions {block}/{intervention}")
            _assert_equal(row["validated_rescues"], rescues, f"rescues {block}/{intervention}")
            _assert_equal(row["evidence_status"], status, f"evidence status {block}/{intervention}")

    if sha256_path(capability_bundle_path) != prereg["frozen_inputs"]["capability_bundle_sha256"]:
        raise Run4AReviewError("capability bundle changed")
    if sha256_path(routing_policy_path) != prereg["frozen_inputs"]["routing_policy_sha256"]:
        raise Run4AReviewError("routing policy changed")
    resource_manifest = _load(resource_manifest_path)
    _assert_equal(resource_manifest.get("manifest_sha256"), prereg["frozen_inputs"]["resource_weight_manifest_sha256"], "resource manifest canonical digest")
    for key, expected in {"worker_time_ms": 5276.567, "local_teacher_time_ms": 16220.624, "external_teacher_time_ms": 28704.012}.items():
        _assert_equal(resource_manifest["weights"][key], expected, f"resource prior {key}")

    return {"preregistration": prereg, "execution_manifest": manifest, "aggregate": aggregate, "selected_task_ids": selected, "resource_manifest": resource_manifest}


def _timing_summary(row: Mapping[str, Any]) -> dict[str, Any]:
    return summarize_timings([float(value) for value in row.get("realized_elapsed_ms", [])])


def build_comparative_freeze(
    verified: Mapping[str, Any],
    *,
    run_root: Path,
    execution_commit: str,
    closeout_report_path: Path,
    harness_path: Path,
    driver_path: Path,
) -> dict[str, Any]:
    prereg = verified["preregistration"]
    aggregate = verified["aggregate"]
    blocks: dict[str, Any] = {}
    for block in BLOCKS:
        blocks[block] = {}
        source_tasks = [task_id for task_id in verified["selected_task_ids"] if task_id.startswith({
            "contradiction-handling": "run4a-candidate-contradiction-",
            "triage-routing": "run4a-candidate-triage-",
            "scope-authority-boundary": "run4a-candidate-scope-",
            "unsupported-certainty": "run4a-candidate-uncertainty-",
        }[block])]
        for intervention in INTERVENTIONS:
            row = aggregate["blocks"][block][intervention]
            blocks[block][intervention] = {
                "resolution": TARGET_RESOLUTIONS[block],
                "evidence_key": block,
                "opportunities": row["comparable_opportunities"],
                "validated_rescues": row["validated_rescues"],
                "rescue_rate": row["rescue_rate"],
                "evidence_status": row["evidence_status"],
                "expected_immediate_action_cost_ms": TIME_PRIORS_MS[intervention],
                "realized_elapsed_ms": _timing_summary(row),
                "source_task_ids": source_tasks,
                "source_artifact": repo_ref(run_root / "aggregate.json"),
            }
    resource_manifest = verified["resource_manifest"]
    artifact = {
        "schema": "zth_run4a_comparative_evidence_freeze_v1",
        "status": "reviewed_frozen_calibration_evidence",
        "authority": "not_production_routing_authority",
        "calibration_only": True,
        "execution_commit": execution_commit,
        "source": {
            "preregistration_path": str(PREREG_PATH),
            "preregistration_sha256": sha256_path(PREREG_PATH),
            "fixture_pack_sha256": prereg["fixture_pack"]["pack_sha256"],
            "driver_path": repo_ref(driver_path),
            "driver_sha256": sha256_path(driver_path),
            "harness_path": repo_ref(harness_path),
            "harness_sha256": sha256_path(harness_path),
            "execution_manifest_path": repo_ref(run_root / "execution_manifest.json"),
            "execution_manifest_sha256": sha256_path(run_root / "execution_manifest.json"),
            "aggregate_path": repo_ref(run_root / "aggregate.json"),
            "aggregate_sha256": sha256_path(run_root / "aggregate.json"),
            "closeout_report_path": repo_ref(closeout_report_path),
            "closeout_report_sha256": sha256_path(closeout_report_path),
            "resource_manifest_path": str(RESOURCE_MANIFEST_PATH),
            "resource_manifest_canonical_sha256": resource_manifest["manifest_sha256"],
        },
        "thresholds": {"minimum_comparable_opportunities": 3, "minimum_rescue_rate": 0.5},
        "blocks": blocks,
        "evidence_formation": {
            "criterion": "At least 2 of 4 blocks have >=2 supported-positive interventions",
            "blocks_with_at_least_two_supported_positive": aggregate["blocks_with_at_least_two_supported_positive_interventions"],
            "met": aggregate["evidence_formation_criterion_met"],
        },
        "capability_bundle_unchanged": True,
        "routing_policy_unchanged": True,
        "resource_weights_unchanged": True,
        "freeze_sha256": None,
    }
    basis = dict(artifact)
    basis["freeze_sha256"] = None
    artifact["freeze_sha256"] = sha256_bytes(canonical(basis).encode("utf-8"))
    return artifact


def verify_comparative_freeze(path: Path) -> dict[str, Any]:
    """Verify the non-self-referential digest and review-only authority flags."""
    artifact = _load(path)
    recorded = artifact.get("freeze_sha256")
    basis = dict(artifact)
    basis["freeze_sha256"] = None
    _assert_equal(sha256_bytes(canonical(basis).encode("utf-8")), recorded, "comparative freeze digest")
    _assert_equal(artifact.get("status"), "reviewed_frozen_calibration_evidence", "comparative freeze status")
    _assert_equal(artifact.get("authority"), "not_production_routing_authority", "comparative freeze authority")
    _assert_equal(artifact.get("calibration_only"), True, "comparative freeze calibration boundary")
    return artifact


def pareto_frontier(block_rows: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    supported = [
        {"intervention": intervention, "rescue_rate": float(row["rescue_rate"]), "expected_cost_ms": TIME_PRIORS_MS[intervention]}
        for intervention, row in block_rows.items()
        if row["evidence_status"] == "supported_positive"
    ]
    frontier = []
    dominated = []
    for candidate in supported:
        is_dominated = any(
            other["intervention"] != candidate["intervention"]
            and other["rescue_rate"] >= candidate["rescue_rate"]
            and other["expected_cost_ms"] <= candidate["expected_cost_ms"]
            and (other["rescue_rate"] > candidate["rescue_rate"] or other["expected_cost_ms"] < candidate["expected_cost_ms"])
            for other in supported
        )
        (dominated if is_dominated else frontier).append(candidate)
    return {"supported_positive": supported, "frontier": frontier, "dominated": dominated}


def objective_audit(block_rows: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    positive = {name: row for name, row in block_rows.items() if row["evidence_status"] == "supported_positive"}
    if not positive:
        return {"cheapest_supported_positive": None, "highest_rescue_then_cheapest": None, "rescue_per_ms": None, "cost_per_rescue": None}
    cheapest = min(positive, key=lambda name: (TIME_PRIORS_MS[name], -float(positive[name]["rescue_rate"])))
    highest = min(positive, key=lambda name: (-float(positive[name]["rescue_rate"]), TIME_PRIORS_MS[name]))
    efficiency = max(positive, key=lambda name: (float(positive[name]["rescue_rate"]) / TIME_PRIORS_MS[name], -TIME_PRIORS_MS[name]))
    cost_per_rescue = min(positive, key=lambda name: (TIME_PRIORS_MS[name] / float(positive[name]["rescue_rate"]), TIME_PRIORS_MS[name]))
    return {
        "cheapest_supported_positive": cheapest,
        "highest_rescue_then_cheapest": highest,
        "rescue_per_ms": efficiency,
        "cost_per_rescue": cost_per_rescue,
        "expected_terminal_cost": {"status": "not_evaluable", "reason": "No frozen downstream failure cost or sequential conditional probabilities exist."},
        "explicit_budget": {"status": "not_evaluable", "reason": "No independently grounded budget parameter is frozen."},
    }


def build_objective_review(verified: Mapping[str, Any], freeze: Mapping[str, Any]) -> dict[str, Any]:
    frontiers = {block: pareto_frontier(verified["aggregate"]["blocks"][block]) for block in BLOCKS}
    objectives = {block: objective_audit(verified["aggregate"]["blocks"][block]) for block in BLOCKS}
    triage = verified["aggregate"]["blocks"]["triage-routing"]
    incremental_probability = float(triage["external_teacher"]["rescue_rate"]) - float(triage["deterministic_patch_retry"]["rescue_rate"])
    incremental_cost = TIME_PRIORS_MS["external_teacher"] - TIME_PRIORS_MS["deterministic_patch_retry"]
    return {
        "schema": "zth_run4_economic_objective_review_v1",
        "basis": "Run 4A frozen comparative evidence and frozen expected elapsed-time priors only",
        "frontiers": frontiers,
        "objective_candidates": objectives,
        "triage_tradeoff": {
            "deterministic": {"rescue_rate": 0.5, "cost_ms": TIME_PRIORS_MS["deterministic_patch_retry"]},
            "external": {"rescue_rate": 0.75, "cost_ms": TIME_PRIORS_MS["external_teacher"]},
            "incremental_expected_cost_ms": incremental_cost,
            "incremental_empirical_rescue_probability": incremental_probability,
            "ms_per_additional_percentage_point": incremental_cost / (incremental_probability * 100),
        },
        "recommended_rule": {
            "name": "cheapest_supported_positive",
            "definition": "At the selected frozen evidence resolution, choose the lowest expected-cost intervention among supported-positive actions; otherwise preserve fail-closed abstention/negative behavior.",
            "parameter_free": True,
            "behavioral_distinction_available": True,
            "quality_constraint": "Future treatment final validated solve rate must be at least control.",
        },
        "comparison_design": {
            "preferred": "Option 2",
            "control": "same frozen comparative evidence; highest empirical rescue rate, cheapest tie-break",
            "treatment": "same frozen comparative evidence; cheapest supported-positive action",
            "causal_question": "Does quantitative elapsed-time information reduce realized resource use when capability evidence is held identical, without reducing validated solve rate?",
            "alternative": "Option 1 compares against the historical Run 3 router but changes the evidence base and is less clean for isolating cost information.",
        },
        "resource_priors_unchanged": True,
        "freeze_sha256": freeze["freeze_sha256"],
    }


def write_review_artifacts(
    *,
    run_root: Path,
    freeze_path: Path,
    objective_path: Path,
    execution_commit: str,
    closeout_report_path: Path,
    harness_path: Path,
    driver_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    verified = verify_terminal_run4a(run_root)
    freeze = build_comparative_freeze(verified, run_root=run_root, execution_commit=execution_commit, closeout_report_path=closeout_report_path, harness_path=harness_path, driver_path=driver_path)
    objective = build_objective_review(verified, freeze)
    freeze_path.write_text(json.dumps(freeze, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    objective_path.write_text(json.dumps(objective, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return freeze, objective
