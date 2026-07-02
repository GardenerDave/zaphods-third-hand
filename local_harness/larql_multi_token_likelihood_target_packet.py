#!/usr/bin/env python3
"""Build a model-free LARQL multi-token likelihood target packet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "larql_multi_token_likelihood_target_packet.v0"
REQUIRED_NEXT_STEP = "supervised_multi_token_likelihood_target_review"
TARGET_PROBES = {"original_larql_behavior_replay", "adjacent_file_anti_overfit"}
CONTROL_PROBES = {"all_files_authorized_control", "unrelated_task_regression"}
OUTPUT_TEXT_FIELDS = ("token_text",)


def require_authorization(authorized: bool) -> None:
    if not authorized:
        raise ValueError("LARQL multi-token likelihood target packet requires explicit opt-in authorization")


def load_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"{path}: required file path does not exist")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def load_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise ValueError(f"{path}: required file path does not exist")
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"{path}: expected JSON object line")
        rows.append(payload)
    return rows


def validate_authority_flags(payload: dict[str, Any]) -> None:
    for field in [
        "training_performed",
        "promotion_authorized",
        "registry_mutation_authorized",
        "install_authorized",
        "base_model_overwritten",
        "automatic_failure_to_curriculum_capture_authorized",
    ]:
        if payload.get(field) is not False:
            raise ValueError(f"{field} must be false")


def validate_generation_aware_comparison(payload: dict[str, Any]) -> None:
    if payload.get("evidence_only") is not True:
        raise ValueError("generation-aware comparison must be evidence_only true")
    if payload.get("promotion_authorized") is not False:
        raise ValueError("generation-aware comparison must not authorize promotion")
    if payload.get("automatic_failure_to_curriculum_capture_authorized") is not False:
        raise ValueError("generation-aware comparison must not authorize automatic failure-to-curriculum capture")


def token_identity(row: dict[str, Any]) -> tuple[Any, Any, Any, Any]:
    return row.get("probe_id"), row.get("continuation_type"), row.get("token_index"), row.get("token_id")


def get_token_text(row: dict[str, Any]) -> str:
    value = row.get("token_text")
    if not isinstance(value, str):
        raise ValueError("token row missing token_text")
    return value


def is_semantic(token_category: str) -> bool:
    return token_category == "semantic_text"


def select_tokens(rows: list[dict[str, Any]], *, top_n: int, generation_aware_status: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    boost: list[dict[str, Any]] = []
    suppress: list[dict[str, Any]] = []
    control: list[dict[str, Any]] = []
    excluded_template_or_structure = 0
    excluded_ambiguous = 0

    for row in rows:
        probe_id = row.get("probe_id")
        continuation_type = row.get("continuation_type")
        token_category = str(row.get("token_category", "unknown"))
        delta = float(row.get("patched_minus_base_logprob"))
        abs_delta = float(row.get("absolute_delta", abs(delta)))
        contributes = row.get("contributes_to_margin_direction")
        if probe_id not in TARGET_PROBES and probe_id not in CONTROL_PROBES:
            continue
        if token_category in {"structural_json", "whitespace_or_punctuation", "special_or_chat_template"}:
            excluded_template_or_structure += 1
            continue
        if not is_semantic(token_category):
            excluded_ambiguous += 1
            continue

        selection = {
            "probe_id": probe_id,
            "continuation_type": continuation_type,
            "token_index": int(row["token_index"]),
            "token_id": int(row["token_id"]),
            "token_text": get_token_text(row),
            "token_category": token_category,
            "patched_minus_base_logprob": delta,
            "absolute_delta": abs_delta,
            "contributes_to_margin_direction": contributes,
        }
        if probe_id in TARGET_PROBES:
            if continuation_type == "corrected" and delta > 0:
                boost.append({**selection, "selection_action": "boost_corrected_semantic_token", "selection_reason": "target semantic corrected token with positive logprob movement"})
            elif continuation_type == "failure" and delta < 0:
                suppress.append({**selection, "selection_action": "suppress_failure_semantic_token", "selection_reason": "target semantic failure token with negative logprob movement"})
            elif continuation_type == "corrected" and delta < 0:
                excluded_ambiguous += 1
            elif continuation_type == "failure" and delta > 0:
                excluded_ambiguous += 1
        elif probe_id in CONTROL_PROBES:
            if continuation_type == "corrected" and delta < 0:
                control.append({**selection, "selection_action": "protect_control_corrected_token", "selection_reason": "control corrected token became less likely"})
            elif continuation_type == "failure" and delta > 0:
                control.append({**selection, "selection_action": "protect_control_failure_token", "selection_reason": "control failure token became more likely"})

    boost.sort(key=lambda row: (-abs(float(row["patched_minus_base_logprob"])), TARGET_PROBES.__contains__(row["probe_id"]) is False, int(row["token_index"])))
    suppress.sort(key=lambda row: (-abs(float(row["patched_minus_base_logprob"])), int(row["token_index"])))
    control.sort(key=lambda row: (-abs(float(row["patched_minus_base_logprob"])), int(row["token_index"])))
    boost = boost[:top_n]
    suppress = suppress[:top_n]
    control = control[:top_n]
    summary = {
        "selected_boost_count": len(boost),
        "selected_suppress_count": len(suppress),
        "selected_control_protection_count": len(control),
        "excluded_template_or_structure_count": excluded_template_or_structure,
        "excluded_ambiguous_count": excluded_ambiguous,
        "target_candidate_count": sum(1 for row in rows if row.get("probe_id") in TARGET_PROBES and is_semantic(str(row.get("token_category", "")))),
        "control_protection_candidate_count": sum(1 for row in rows if row.get("probe_id") in CONTROL_PROBES and is_semantic(str(row.get("token_category", "")))),
        "generation_aware_status": generation_aware_status,
        "generation_was_unchanged": generation_aware_status == "patched_generation_unchanged",
    }
    return boost, suppress, control, summary


def render_review_packet(record: dict[str, Any], packet: dict[str, Any]) -> str:
    lines = [
        "# LARQL Multi-Token Likelihood Target Packet Review",
        "",
        f"- generation-aware status: `{packet['generation_aware_status']}`;",
        f"- selected boost count: `{packet['selected_boost_count']}`;",
        f"- selected suppress count: `{packet['selected_suppress_count']}`;",
        f"- selected control protection count: `{packet['selected_control_protection_count']}`;",
        f"- target candidate count: `{packet['target_candidate_count']}`;",
        f"- control protection candidate count: `{packet['control_protection_candidate_count']}`;",
        "",
        "## Claim Boundary",
        "",
        "- this packet selects token targets only;",
        "- it does not run inference, generation, training, weight edits, materialization, or promotion;",
        "- evidence, not authority.",
        "",
        "## Authority Flags",
        "",
        f"- model_inference_performed: `{record['model_inference_performed']}`;",
        f"- generation_performed: `{record['generation_performed']}`;",
        f"- training_performed: `{record['training_performed']}`;",
        f"- lora_or_peft_used: `{record['lora_or_peft_used']}`;",
        f"- weight_edit_performed: `{record['weight_edit_performed']}`;",
        f"- delta_artifact_written: `{record['delta_artifact_written']}`;",
        f"- patched_model_materialized: `{record['patched_model_materialized']}`;",
        f"- promotion_authorized: `{record['promotion_authorized']}`;",
        f"- automatic_failure_to_curriculum_capture_authorized: `{record['automatic_failure_to_curriculum_capture_authorized']}`;",
    ]
    return "\n".join(lines).rstrip() + "\n"


def write_multi_token_likelihood_target_packet(
    *,
    run_id: str,
    out_root: Path,
    token_position_diagnostic_path: Path,
    token_position_rows_jsonl: Path,
    generation_aware_comparison_path: Path,
    source_recipe_card_path: Path | None,
    source_materialization_record_path: Path | None,
    top_n: int,
    authorize_larql_multi_token_likelihood_target_packet: bool,
) -> dict[str, Any]:
    require_authorization(authorize_larql_multi_token_likelihood_target_packet)
    out_dir = out_root / run_id
    if out_dir.exists():
        raise ValueError("output directory already exists")
    out_dir.mkdir(parents=True, exist_ok=False)

    diagnostic = load_json_object(token_position_diagnostic_path)
    rows = load_jsonl_rows(token_position_rows_jsonl)
    comparison = load_json_object(generation_aware_comparison_path)
    validate_generation_aware_comparison(comparison)

    if source_recipe_card_path is not None:
        recipe_card = load_json_object(source_recipe_card_path)
        validate_authority_flags(recipe_card)
    if source_materialization_record_path is not None:
        materialization = load_json_object(source_materialization_record_path)
        validate_authority_flags(materialization)

    required_probes = TARGET_PROBES | CONTROL_PROBES
    probe_summaries = {str(row.get("probe_id")): row for row in diagnostic.get("probe_summaries", []) if isinstance(row, dict)}
    missing = required_probes - set(probe_summaries)
    if missing:
        raise ValueError(f"required probe summaries missing: {sorted(missing)}")

    seen_identities: set[tuple[Any, Any, Any, Any]] = set()
    for row in rows:
        identity = token_identity(row)
        if None in identity:
            raise ValueError("duplicate token row identity exists or identity missing")
        if identity in seen_identities:
            raise ValueError("duplicate token row identity exists")
        seen_identities.add(identity)
        if row.get("probe_id") not in required_probes:
            raise ValueError("required probe summaries missing")

    if comparison.get("summary", {}).get("generation_aware_status") is None:
        raise ValueError("generation-aware comparison missing status")

    boost, suppress, control, summary = select_tokens(rows, top_n=top_n, generation_aware_status=str(comparison["summary"]["generation_aware_status"]))

    packet = {
        "report_type": REPORT_TYPE,
        "run_id": run_id,
        "evidence_only": True,
        "model_free_packet": True,
        "source_token_position_diagnostic_path": str(token_position_diagnostic_path),
        "source_token_position_rows_path": str(token_position_rows_jsonl),
        "source_generation_aware_comparison_path": str(generation_aware_comparison_path),
        "source_recipe_card_path": str(source_recipe_card_path) if source_recipe_card_path is not None else None,
        "source_materialization_record_path": str(source_materialization_record_path) if source_materialization_record_path is not None else None,
        "generation_aware_status": str(comparison["summary"]["generation_aware_status"]),
        "target_probe_ids": sorted(TARGET_PROBES),
        "control_probe_ids": sorted(CONTROL_PROBES),
        "selected_boost_tokens": boost,
        "selected_suppress_tokens": suppress,
        "selected_control_protection_tokens": control,
        "excluded_tokens_summary": {
            "excluded_template_or_structure_count": summary["excluded_template_or_structure_count"],
            "excluded_ambiguous_count": summary["excluded_ambiguous_count"],
        },
        "recommended_next_step": "continuation_activation_capture",
        "claim_boundary": {
            "packet_selects_token_targets_only": True,
            "no_inference": True,
            "no_generation": True,
            "no_training": True,
            "no_weight_edit": True,
            "no_materialization": True,
            "no_promotion": True,
            "evidence_not_authority": True,
        },
        **summary,
        "model_inference_performed": False,
        "generation_performed": False,
        "training_performed": False,
        "lora_or_peft_used": False,
        "weight_edit_performed": False,
        "delta_artifact_written": False,
        "patched_model_materialized": False,
        "base_model_overwritten": False,
        "promotion_authorized": False,
        "production_deployment_authorized": False,
        "registry_mutation_authorized": False,
        "install_authorized": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
        "required_next_step": REQUIRED_NEXT_STEP,
    }

    (out_dir / "larql_multi_token_likelihood_target_packet_record.json").write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "multi_token_likelihood_target_packet.json").write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    selected_rows = boost + suppress + control
    (out_dir / "multi_token_likelihood_target_rows.jsonl").write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in selected_rows) + "\n",
        encoding="utf-8",
    )
    (out_dir / "multi_token_likelihood_target_review_packet.md").write_text(
        render_review_packet(packet, packet),
        encoding="utf-8",
    )
    return packet


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--token-position-diagnostic", required=True, type=Path)
    parser.add_argument("--token-position-rows-jsonl", required=True, type=Path)
    parser.add_argument("--generation-aware-comparison", required=True, type=Path)
    parser.add_argument("--source-recipe-card", type=Path)
    parser.add_argument("--source-materialization-record", type=Path)
    parser.add_argument("--top-n", type=int, default=24)
    parser.add_argument("--authorize-larql-multi-token-likelihood-target-packet", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_multi_token_likelihood_target_packet(
            run_id=args.run_id,
            out_root=args.out_root,
            token_position_diagnostic_path=args.token_position_diagnostic,
            token_position_rows_jsonl=args.token_position_rows_jsonl,
            generation_aware_comparison_path=args.generation_aware_comparison,
            source_recipe_card_path=args.source_recipe_card,
            source_materialization_record_path=args.source_materialization_record,
            top_n=args.top_n,
            authorize_larql_multi_token_likelihood_target_packet=args.authorize_larql_multi_token_likelihood_target_packet,
        )
    except (OSError, ValueError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
