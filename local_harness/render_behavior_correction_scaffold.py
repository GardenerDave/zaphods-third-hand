#!/usr/bin/env python3
"""Render an explicit behavior-correction scaffold from a job packet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from validate_behavior_correction_cards import load_card, validate_card_or_raise


CARD_DIR = Path("docs/behavior_correction_cards")
OUTPUT_JSON = "behavior_correction_scaffold.json"
OUTPUT_MD = "behavior_correction_scaffold.md"


def read_json_packet(path: Path) -> dict[str, Any]:
    try:
        packet = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing packet file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in packet file: {path}") from exc
    if not isinstance(packet, dict):
        raise ValueError("job packet must be a JSON object")
    return packet


def resolve_card(card_id: str, card_dir: Path = CARD_DIR) -> dict[str, Any]:
    card_path = card_dir / f"{card_id}.json"
    card = load_card(card_path)
    validate_card_or_raise(card)
    return card


def render_scaffold(packet: dict[str, Any], card_dir: Path = CARD_DIR) -> dict[str, Any]:
    assigned_ids = packet.get("behavior_corrections") or []
    if not isinstance(assigned_ids, list):
        raise ValueError("behavior_corrections must be a list when present")

    cards = [resolve_card(card_id, card_dir) for card_id in assigned_ids]
    rendered_cards = []
    for card in cards:
        rendered_cards.append(
            {
                "id": card["id"],
                "title": card["title"],
                "status": card["status"],
                "correction_instruction": card["correction_instruction"],
                "validator_expectations": card["validator_expectations"],
                "known_failure_modes": card["known_failure_modes"],
                "provenance_notes": card["provenance_notes"],
                "non_authorities": card["non_authorities"],
            }
        )

    scaffold = {
        "report_type": "behavior_correction_scaffold.v1",
        "behavior_corrections": assigned_ids,
        "corrections": rendered_cards,
        "correction_count": len(rendered_cards),
        "packet_level_only": True,
        "auto_assigned": False,
        "model_inference_performed": False,
        "training_performed": False,
        "delta_written": False,
        "patched_model_materialized": False,
        "promotion_authorized": False,
        "automatic_failure_curriculum_capture_authorized": False,
        "claim_boundary": [
            "corrections are packet-level guidance only",
            "corrections do not authorize scope expansion",
            "corrections do not authorize file edits",
            "corrections do not override supervised review",
            "corrections do not authorize training data capture",
        ],
    }
    return scaffold


def scaffold_markdown(scaffold: dict[str, Any]) -> str:
    lines = [
        "# Behavior Correction Scaffold",
        "",
        f"- assigned corrections: {', '.join(scaffold.get('behavior_corrections') or []) or '(none)'}",
        f"- correction count: {scaffold.get('correction_count', 0)}",
        "",
        "## Claim boundary",
    ]
    for item in scaffold["claim_boundary"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Authority flags",
            f"- model_inference_performed: {scaffold['model_inference_performed']}",
            f"- training_performed: {scaffold['training_performed']}",
            f"- delta_written: {scaffold['delta_written']}",
            f"- patched_model_materialized: {scaffold['patched_model_materialized']}",
            f"- promotion_authorized: {scaffold['promotion_authorized']}",
            f"- automatic_failure_curriculum_capture_authorized: {scaffold['automatic_failure_curriculum_capture_authorized']}",
            "",
        ]
    )
    for card in scaffold["corrections"]:
        lines.extend(
            [
                f"## {card['id']}",
                f"Title: {card['title']}",
                "### Correction instruction",
            ]
        )
        lines.extend(f"- {item}" for item in card["correction_instruction"])
        lines.append("### Non-authorities")
        lines.extend(f"- {item}" for item in card["non_authorities"])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_scaffold(packet_path: Path, out_dir: Path) -> dict[str, Any]:
    if out_dir.exists():
        raise ValueError(f"output directory already exists: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=False)
    packet = read_json_packet(packet_path)
    scaffold = render_scaffold(packet)
    (out_dir / OUTPUT_JSON).write_text(json.dumps(scaffold, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / OUTPUT_MD).write_text(scaffold_markdown(scaffold), encoding="utf-8")
    return scaffold


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render behavior correction scaffolds.")
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        write_scaffold(args.packet, args.out_dir)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
