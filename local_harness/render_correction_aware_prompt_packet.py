#!/usr/bin/env python3
"""Compose a bounded correction-aware prompt packet from a job packet and scaffold."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from validate_behavior_correction_cards import load_card, validate_card_or_raise


OUTPUT_JSON = "correction_aware_prompt_packet.json"
OUTPUT_MD = "correction_aware_prompt_packet.md"


def read_json_object(path: Path, kind: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing {kind} file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {kind} file: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{kind} must be a JSON object")
    return payload


def read_packet(path: Path) -> dict[str, Any]:
    return read_json_object(path, "job packet")


def read_scaffold(path: Path) -> dict[str, Any]:
    return read_json_object(path, "correction scaffold")


def _flags_false(payload: dict[str, Any], fields: Sequence[str]) -> None:
    for field in fields:
        if payload.get(field) is not False:
            raise ValueError(f"{field} must be false")


def validate_scaffold(scaffold: dict[str, Any]) -> None:
    if scaffold.get("report_type") != "behavior_correction_scaffold.v1":
        raise ValueError("correction scaffold report_type must be behavior_correction_scaffold.v1")
    if scaffold.get("auto_assigned") is not False:
        raise ValueError("correction scaffold auto_assigned must be false")
    if scaffold.get("packet_level_only") is not True:
        raise ValueError("correction scaffold packet_level_only must be true")
    _flags_false(
        scaffold,
        (
            "model_inference_performed",
            "training_performed",
            "delta_written",
            "patched_model_materialized",
            "promotion_authorized",
            "automatic_failure_curriculum_capture_authorized",
        ),
    )
    for card in scaffold.get("corrections") or []:
        if not isinstance(card, dict):
            raise ValueError("correction scaffold corrections must be objects")


def assignment_list(packet: dict[str, Any]) -> list[str]:
    corrections = packet.get("behavior_corrections")
    if corrections is None:
        return []
    if not isinstance(corrections, list):
        raise ValueError("behavior_corrections must be a list when present")
    return [str(item) for item in corrections]


def validate_assignment(packet: dict[str, Any], scaffold: dict[str, Any]) -> list[str]:
    packet_ids = assignment_list(packet)
    scaffold_ids = [str(item) for item in (scaffold.get("behavior_corrections") or [])]
    if packet_ids != scaffold_ids:
        raise ValueError("behavior_corrections must match scaffold behavior_corrections exactly")
    return packet_ids


def card_map(scaffold: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for card in scaffold.get("corrections") or []:
        if not isinstance(card, dict):
            raise ValueError("correction scaffold corrections must be objects")
        card_id = card.get("id")
        if not isinstance(card_id, str) or not card_id:
            raise ValueError("correction scaffold card id missing")
        result[card_id] = card
    return result


def render_markdown(packet: dict[str, Any], scaffold: dict[str, Any]) -> str:
    assigned = assignment_list(packet)
    cards = card_map(scaffold)
    lines = [
        "# Correction-Aware Prompt Packet",
        "",
        "## Task",
        f"- task summary: {packet.get('task_summary', '(none)')}",
        "",
        "## Scope boundary",
        f"- allowed files: {', '.join(packet.get('allowed_files') or []) or '(none)'}",
    ]
    for key in ("requested_targets", "candidate_targets"):
        if key in packet:
            lines.append(f"- {key}: {', '.join(packet.get(key) or []) or '(none)'}")
    lines.extend(
        [
            "",
            "## Behavior correction guidance",
            "- correction cards are packet-level guidance only",
            "- only explicitly allowed files are authorized targets",
            "- plausible but unauthorized files must be held out",
            "- corrections do not authorize file edits",
            "- corrections do not authorize scope expansion",
            "- corrections do not override supervised review",
            "- corrections do not authorize training data capture",
        ]
    )
    if assigned:
        for card_id in assigned:
            card = cards[card_id]
            lines.extend(
                [
                    "",
                    f"### {card_id}: {card['title']}",
                    "#### Correction instruction",
                ]
            )
            lines.extend(f"- {item}" for item in card["correction_instruction"])
            lines.append("#### Validator expectations")
            lines.extend(f"- {item}" for item in card["validator_expectations"])
            lines.append("#### Non-authorities")
            lines.extend(f"- {item}" for item in card["non_authorities"])
    else:
        lines.extend(["", "_No correction cards assigned._"])
    lines.extend(
        [
            "",
            "## Required output shape",
            f"- {packet.get('expected_output_shape', '(none)')}",
            "",
            "## Authority boundary",
            "- model_inference_performed: false",
            "- generation_performed: false",
            "- training_performed: false",
            "- delta_written: false",
            "- patched_model_materialized: false",
            "- promotion_authorized: false",
            "- automatic_failure_curriculum_capture_authorized: false",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def compose(packet_path: Path, scaffold_path: Path, out_dir: Path) -> dict[str, Any]:
    if out_dir.exists():
        raise ValueError(f"output directory already exists: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=False)

    packet = read_packet(packet_path)
    scaffold = read_scaffold(scaffold_path)
    validate_scaffold(scaffold)
    assigned = validate_assignment(packet, scaffold)
    cards = card_map(scaffold)
    for card_id in assigned:
        if card_id not in cards:
            raise ValueError(f"referenced correction card missing from scaffold: {card_id}")
        validate_card_or_raise(cards[card_id])

    rendered = {
        "report_type": "correction_aware_prompt_packet.v1",
        "source_job_packet": str(packet_path),
        "source_correction_scaffold": str(scaffold_path),
        "task_summary": packet.get("task_summary"),
        "allowed_files": packet.get("allowed_files") or [],
        "candidate_targets": packet.get("candidate_targets"),
        "requested_targets": packet.get("requested_targets"),
        "expected_output_shape": packet.get("expected_output_shape"),
        "behavior_corrections": assigned,
        "rendered_prompt_sections": {
            "task": {
                "task_summary": packet.get("task_summary"),
            },
            "scope_boundary": {
                "allowed_files": packet.get("allowed_files") or [],
                "requested_targets": packet.get("requested_targets"),
                "candidate_targets": packet.get("candidate_targets"),
            },
            "behavior_correction_guidance": {
                "assigned_corrections": [
                    {
                        "id": cards[card_id]["id"],
                        "title": cards[card_id]["title"],
                        "correction_instruction": cards[card_id]["correction_instruction"],
                        "validator_expectations": cards[card_id]["validator_expectations"],
                        "known_failure_modes": cards[card_id]["known_failure_modes"],
                        "non_authorities": cards[card_id]["non_authorities"],
                        "provenance_notes": cards[card_id]["provenance_notes"],
                    }
                    for card_id in assigned
                ],
            },
            "required_output_shape": {
                "expected_output_shape": packet.get("expected_output_shape"),
            },
            "authority_boundary": {
                "model_inference_performed": False,
                "generation_performed": False,
                "training_performed": False,
                "delta_written": False,
                "patched_model_materialized": False,
                "promotion_authorized": False,
                "automatic_failure_curriculum_capture_authorized": False,
            },
        },
        "auto_assigned_corrections": False,
        "packet_level_only": True,
        "model_inference_performed": False,
        "generation_performed": False,
        "training_performed": False,
        "delta_written": False,
        "patched_model_materialized": False,
        "promotion_authorized": False,
        "automatic_failure_curriculum_capture_authorized": False,
    }
    (out_dir / OUTPUT_JSON).write_text(
        json.dumps(rendered, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / OUTPUT_MD).write_text(render_markdown(packet, scaffold), encoding="utf-8")
    return rendered


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compose a correction-aware prompt packet.")
    parser.add_argument("--job-packet", required=True, type=Path)
    parser.add_argument("--correction-scaffold", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        compose(args.job_packet, args.correction_scaffold, args.out_dir)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
