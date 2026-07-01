#!/usr/bin/env python3
"""Write a supervised, provenance-bound LARQL insertion recipe card."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPORT_TYPE = "larql_insertion_recipe_card.v0"
RECIPE_CARD_VERSION = "v0"
TARGET_PROBES = [
    "original_larql_behavior_replay",
    "adjacent_file_anti_overfit",
]
CONTROL_PROBES = [
    "all_files_authorized_control",
    "unrelated_task_regression",
]


def require_authorization(authorized: bool) -> None:
    if not authorized:
        raise ValueError("LARQL insertion recipe card requires explicit opt-in authorization")


def load_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"{path}: required file path does not exist")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def validate_false_flag(payload: dict[str, Any], field: str, label: str) -> None:
    if payload.get(field) is not False:
        raise ValueError(f"{label}: {field} must be false")


def validate_delta_design_packet(payload: dict[str, Any]) -> None:
    if payload.get("report_type") != "larql_delta_design_packet.v0":
        raise ValueError("delta design packet report_type mismatch")
    required_fields = [
        "direction_basis_mode",
        "selected_vector_source",
        "target_module",
        "target_module_family",
        "source_vector_target_module",
        "source_vector_target_module_family",
    ]
    for field in required_fields:
        value = payload.get(field)
        if value in (None, "", "unknown"):
            raise ValueError(f"delta design packet missing required field: {field}")
    for field in [
        "training_performed",
        "promotion_authorized",
        "registry_mutation_authorized",
        "install_authorized",
        "automatic_failure_to_curriculum_capture_authorized",
    ]:
        validate_false_flag(payload, field, "delta design packet")


def validate_rank1_delta_artifact_record(payload: dict[str, Any]) -> None:
    if payload.get("report_type") != "larql_rank1_delta_artifact.v0":
        raise ValueError("rank1 delta artifact record report_type mismatch")
    if payload.get("delta_artifact_written") is not True:
        raise ValueError("rank1 delta artifact record must have delta_artifact_written true")
    required_fields = [
        "target_module",
        "target_module_family",
        "selected_vector_source",
        "direction_basis_mode",
        "delta_scale",
        "delta_shape",
        "delta_tensor_norm",
        "artifact_sha256",
        "artifact_path",
    ]
    for field in required_fields:
        value = payload.get(field)
        if value in (None, "", "unknown"):
            raise ValueError(f"rank1 delta artifact record missing required field: {field}")
    artifact_path = Path(str(payload["artifact_path"]))
    if not artifact_path.exists():
        raise ValueError("rank1 delta artifact record artifact_path does not exist")
    for field in [
        "training_performed",
        "promotion_authorized",
        "registry_mutation_authorized",
        "install_authorized",
        "automatic_failure_to_curriculum_capture_authorized",
    ]:
        validate_false_flag(payload, field, "rank1 delta artifact record")


def summarize_likelihood_comparison(path: Path) -> dict[str, Any]:
    payload = load_json_object(path)
    probes = payload.get("probes")
    if not isinstance(probes, list):
        raise ValueError(f"{path}: probes must be a list")
    by_id: dict[str, float] = {}
    for probe in probes:
        if not isinstance(probe, dict):
            raise ValueError(f"{path}: probe entry must be an object")
        probe_id = probe.get("probe_id")
        if not isinstance(probe_id, str):
            raise ValueError(f"{path}: probe_id missing")
        if probe_id in by_id:
            raise ValueError(f"{path}: duplicate probe id: {probe_id}")
        if "exception" in probe:
            raise ValueError(f"{path}: probe {probe_id} contains exception")
        margin_delta = probe.get("margin_delta")
        if not isinstance(margin_delta, (int, float)):
            raise ValueError(f"{path}: probe {probe_id} missing numeric margin_delta")
        by_id[probe_id] = float(margin_delta)
    missing_target = [probe_id for probe_id in TARGET_PROBES if probe_id not in by_id]
    missing_control = [probe_id for probe_id in CONTROL_PROBES if probe_id not in by_id]
    if missing_target or missing_control:
        raise ValueError(
            f"{path}: missing required probes: {missing_target + missing_control}"
        )
    target_values = [by_id[probe_id] for probe_id in TARGET_PROBES]
    control_values = [by_id[probe_id] for probe_id in CONTROL_PROBES]
    return {
        "path": str(path),
        "target_mean": sum(target_values) / len(target_values),
        "target_min": min(target_values),
        "control_mean": sum(control_values) / len(control_values),
        "control_min": min(control_values),
        "per_probe": [{"probe_id": probe_id, "margin_delta": by_id[probe_id]} for probe_id in TARGET_PROBES + CONTROL_PROBES],
        "per_probe_map": by_id,
    }


def confirmation_matches(candidate: dict[str, Any], confirmation: dict[str, Any] | None) -> bool | None:
    if confirmation is None:
        return None
    return candidate["per_probe_map"] == confirmation["per_probe_map"]


def build_candidate_minus_baseline(
    baseline_metrics: dict[str, Any],
    candidate_metrics: dict[str, Any],
) -> dict[str, float]:
    return {
        "target_mean_delta": float(candidate_metrics["target_mean"] - baseline_metrics["target_mean"]),
        "target_min_delta": float(candidate_metrics["target_min"] - baseline_metrics["target_min"]),
        "control_mean_delta": float(candidate_metrics["control_mean"] - baseline_metrics["control_mean"]),
        "control_min_delta": float(candidate_metrics["control_min"] - baseline_metrics["control_min"]),
    }


def evaluate_recipe(
    *,
    baseline_metrics: dict[str, Any],
    candidate_metrics: dict[str, Any],
    confirmation_metrics: dict[str, Any] | None,
) -> tuple[str, str, list[str], bool | None]:
    reasons: list[str] = []
    if not candidate_metrics["target_mean"] > baseline_metrics["target_mean"]:
        reasons.append("candidate target_mean did not beat baseline")
    if not candidate_metrics["target_min"] >= baseline_metrics["target_min"]:
        reasons.append("candidate target_min was below baseline")
    if not candidate_metrics["control_mean"] > baseline_metrics["control_mean"]:
        reasons.append("candidate control_mean did not beat baseline")
    if not candidate_metrics["control_min"] > baseline_metrics["control_min"]:
        reasons.append("candidate control_min did not beat baseline")
    if not candidate_metrics["target_min"] > 0:
        reasons.append("candidate target_min was not positive")
    confirmation_match = confirmation_matches(candidate_metrics, confirmation_metrics)
    if confirmation_match is False:
        reasons.append("confirmation run did not exactly match candidate metrics")
    if reasons:
        return (
            "rejected_candidate",
            "candidate did not satisfy the supervised insertion recipe acceptance rule",
            reasons,
            confirmation_match,
        )
    return (
        "accepted_candidate",
        "candidate satisfied the supervised insertion recipe acceptance rule against the supplied baseline",
        [],
        confirmation_match,
    )


def render_markdown_card(card: dict[str, Any]) -> str:
    lines = [
        "# LARQL Insertion Recipe Card",
        "",
        f"- status: `{card['recipe_status']}`;",
        f"- recipe name: `{card['recipe_name']}`;",
        f"- behavior family: `{card['behavior_family']}`;",
        f"- model name: `{card['model_name']}`;",
        f"- target module: `{card['target_module']}`;",
        f"- vector source: `{card['selected_vector_source']}`;",
        f"- direction basis mode: `{card['direction_basis_mode']}`;",
        f"- orthogonalization strength: `{card['orthogonalization_strength']}`;",
        f"- orthogonalization side: `{card['orthogonalization_side']}`;",
        f"- delta scale: `{card['delta_scale']}`;",
        "",
        "## Baseline metrics",
        "",
        f"- target_mean: `{card['baseline_metrics']['target_mean']}`;",
        f"- target_min: `{card['baseline_metrics']['target_min']}`;",
        f"- control_mean: `{card['baseline_metrics']['control_mean']}`;",
        f"- control_min: `{card['baseline_metrics']['control_min']}`;",
        "",
        "## Candidate metrics",
        "",
        f"- target_mean: `{card['candidate_metrics']['target_mean']}`;",
        f"- target_min: `{card['candidate_metrics']['target_min']}`;",
        f"- control_mean: `{card['candidate_metrics']['control_mean']}`;",
        f"- control_min: `{card['candidate_metrics']['control_min']}`;",
    ]
    if card["confirmation_metrics"] is not None:
        lines.extend(
            [
                "",
                "## Confirmation metrics",
                "",
                f"- target_mean: `{card['confirmation_metrics']['target_mean']}`;",
                f"- target_min: `{card['confirmation_metrics']['target_min']}`;",
                f"- control_mean: `{card['confirmation_metrics']['control_mean']}`;",
                f"- control_min: `{card['confirmation_metrics']['control_min']}`;",
                f"- confirmation_matches_candidate: `{card['confirmation_matches_candidate']}`;",
            ]
        )
    lines.extend(
        [
            "",
            "## Acceptance rationale",
            "",
            f"- {card['acceptance_rationale']}",
            "",
            "## Claim boundary",
            "",
            f"- {card['claim_boundary']}",
            "",
            "## Unsupported claims",
            "",
            "- this is a local supervised insertion recipe, not a universal constant;",
            "- it does not prove general transfer across models, layers, or hardware classes;",
            "- it does not authorize unattended reuse, promotion, deployment, or registry mutation;",
            "",
            "## Authority flags",
            "",
            f"- model_inference_performed_by_card_writer: `{card['model_inference_performed_by_card_writer']}`;",
            f"- training_performed: `{card['training_performed']}`;",
            f"- lora_or_peft_used: `{card['lora_or_peft_used']}`;",
            f"- weight_edit_performed_by_card_writer: `{card['weight_edit_performed_by_card_writer']}`;",
            f"- delta_artifact_written_by_card_writer: `{card['delta_artifact_written_by_card_writer']}`;",
            f"- patched_model_materialized_by_card_writer: `{card['patched_model_materialized_by_card_writer']}`;",
            f"- promotion_authorized: `{card['promotion_authorized']}`;",
            f"- automatic_failure_to_curriculum_capture_authorized: `{card['automatic_failure_to_curriculum_capture_authorized']}`;",
        ]
    )
    if card.get("author_note"):
        lines.extend(["", "## Author note", "", f"- {card['author_note']}"])
    return "\n".join(lines).rstrip() + "\n"


def write_insertion_recipe_card(
    *,
    run_id: str,
    out_root: Path,
    recipe_name: str,
    behavior_family: str,
    model_name: str,
    base_model_path_or_id: str,
    delta_design_packet_path: Path,
    rank1_delta_artifact_record_path: Path,
    teacher_forced_likelihood_comparison_path: Path,
    baseline_teacher_forced_likelihood_comparison_path: Path,
    confirmation_teacher_forced_likelihood_comparison_path: Path | None,
    author_note: str | None,
    authorize_larql_insertion_recipe_card: bool,
) -> dict[str, Any]:
    require_authorization(authorize_larql_insertion_recipe_card)
    out_dir = out_root / run_id
    if out_dir.exists():
        raise ValueError("output directory already exists")

    delta_design_packet = load_json_object(delta_design_packet_path)
    rank1_delta_artifact_record = load_json_object(rank1_delta_artifact_record_path)
    validate_delta_design_packet(delta_design_packet)
    validate_rank1_delta_artifact_record(rank1_delta_artifact_record)

    baseline_metrics = summarize_likelihood_comparison(
        baseline_teacher_forced_likelihood_comparison_path
    )
    candidate_metrics = summarize_likelihood_comparison(
        teacher_forced_likelihood_comparison_path
    )
    confirmation_metrics = (
        summarize_likelihood_comparison(confirmation_teacher_forced_likelihood_comparison_path)
        if confirmation_teacher_forced_likelihood_comparison_path is not None
        else None
    )
    recipe_status, acceptance_rationale, rejection_reasons, confirmation_match = evaluate_recipe(
        baseline_metrics=baseline_metrics,
        candidate_metrics=candidate_metrics,
        confirmation_metrics=confirmation_metrics,
    )

    card = {
        "recipe_card_version": RECIPE_CARD_VERSION,
        "report_type": REPORT_TYPE,
        "run_id": run_id,
        "recipe_name": recipe_name,
        "behavior_family": behavior_family,
        "model_name": model_name,
        "base_model_path_or_id": base_model_path_or_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "claim_boundary": "This card records a supervised local insertion recipe with bounded evidence. It is evidence for local reuse review, not authority for unattended transfer or promotion.",
        "reuse_policy": "Reuse is supervised, provenance-bound, and requires explicit review plus fresh bounded reaudition.",
        "required_reaudition_before_reuse": True,
        "universal_constant": False,
        "local_insertion_recipe": True,
        "supervised_only": True,
        "target_module": rank1_delta_artifact_record["target_module"],
        "target_module_family": rank1_delta_artifact_record["target_module_family"],
        "source_vector_target_module": delta_design_packet["source_vector_target_module"],
        "source_vector_target_module_family": delta_design_packet["source_vector_target_module_family"],
        "selected_vector_source": rank1_delta_artifact_record["selected_vector_source"],
        "direction_basis_mode": rank1_delta_artifact_record["direction_basis_mode"],
        "orthogonalization_applied": rank1_delta_artifact_record.get("orthogonalization_applied", False),
        "orthogonalization_strength": rank1_delta_artifact_record.get("orthogonalization_strength"),
        "orthogonalization_side": rank1_delta_artifact_record.get("orthogonalization_side"),
        "target_probe_ids": rank1_delta_artifact_record.get("target_probe_ids", TARGET_PROBES),
        "control_probe_ids": rank1_delta_artifact_record.get("control_probe_ids", CONTROL_PROBES),
        "control_probe_subset": rank1_delta_artifact_record.get("control_probe_subset", CONTROL_PROBES),
        "delta_scale": rank1_delta_artifact_record["delta_scale"],
        "delta_shape": rank1_delta_artifact_record["delta_shape"],
        "delta_tensor_norm": rank1_delta_artifact_record["delta_tensor_norm"],
        "delta_artifact_sha256": rank1_delta_artifact_record["artifact_sha256"],
        "rank1_delta_artifact_path": rank1_delta_artifact_record.get("artifact_path"),
        "baseline_run_path": baseline_metrics["path"],
        "candidate_run_path": candidate_metrics["path"],
        "confirmation_run_path": confirmation_metrics["path"] if confirmation_metrics else None,
        "baseline_metrics": {
            "target_mean": baseline_metrics["target_mean"],
            "target_min": baseline_metrics["target_min"],
            "control_mean": baseline_metrics["control_mean"],
            "control_min": baseline_metrics["control_min"],
            "per_probe": baseline_metrics["per_probe"],
        },
        "candidate_metrics": {
            "target_mean": candidate_metrics["target_mean"],
            "target_min": candidate_metrics["target_min"],
            "control_mean": candidate_metrics["control_mean"],
            "control_min": candidate_metrics["control_min"],
            "per_probe": candidate_metrics["per_probe"],
        },
        "confirmation_metrics": (
            {
                "target_mean": confirmation_metrics["target_mean"],
                "target_min": confirmation_metrics["target_min"],
                "control_mean": confirmation_metrics["control_mean"],
                "control_min": confirmation_metrics["control_min"],
                "per_probe": confirmation_metrics["per_probe"],
            }
            if confirmation_metrics
            else None
        ),
        "candidate_minus_baseline": build_candidate_minus_baseline(
            baseline_metrics, candidate_metrics
        ),
        "confirmation_matches_candidate": confirmation_match,
        "model_inference_performed_by_card_writer": False,
        "training_performed": False,
        "lora_or_peft_used": False,
        "weight_edit_performed_by_card_writer": False,
        "delta_artifact_written_by_card_writer": False,
        "patched_model_materialized_by_card_writer": False,
        "base_model_overwritten": False,
        "promotion_authorized": False,
        "production_deployment_authorized": False,
        "registry_mutation_authorized": False,
        "install_authorized": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
        "recipe_status": recipe_status,
        "acceptance_rationale": acceptance_rationale,
        "rejection_reasons": rejection_reasons,
        "author_note": author_note,
    }

    out_dir.mkdir(parents=True, exist_ok=False)
    (out_dir / "larql_insertion_recipe_card.json").write_text(
        json.dumps(card, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "larql_insertion_recipe_card.md").write_text(
        render_markdown_card(card),
        encoding="utf-8",
    )
    return card


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--recipe-name", required=True)
    parser.add_argument("--behavior-family", required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--base-model-path-or-id", required=True)
    parser.add_argument("--delta-design-packet", required=True, type=Path)
    parser.add_argument("--rank1-delta-artifact-record", required=True, type=Path)
    parser.add_argument("--teacher-forced-likelihood-comparison", required=True, type=Path)
    parser.add_argument("--baseline-teacher-forced-likelihood-comparison", required=True, type=Path)
    parser.add_argument("--confirmation-teacher-forced-likelihood-comparison", type=Path)
    parser.add_argument("--author-note")
    parser.add_argument("--authorize-larql-insertion-recipe-card", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_insertion_recipe_card(
            run_id=args.run_id,
            out_root=args.out_root,
            recipe_name=args.recipe_name,
            behavior_family=args.behavior_family,
            model_name=args.model_name,
            base_model_path_or_id=args.base_model_path_or_id,
            delta_design_packet_path=args.delta_design_packet,
            rank1_delta_artifact_record_path=args.rank1_delta_artifact_record,
            teacher_forced_likelihood_comparison_path=args.teacher_forced_likelihood_comparison,
            baseline_teacher_forced_likelihood_comparison_path=args.baseline_teacher_forced_likelihood_comparison,
            confirmation_teacher_forced_likelihood_comparison_path=args.confirmation_teacher_forced_likelihood_comparison,
            author_note=args.author_note,
            authorize_larql_insertion_recipe_card=args.authorize_larql_insertion_recipe_card,
        )
    except (OSError, ValueError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
