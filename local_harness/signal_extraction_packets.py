#!/usr/bin/env python3
"""Generate offline raw-signal extraction packets from chunk plans."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence


EXPECTED_OUTPUT = "raw_signals_jsonl"
ALLOWED_SIGNAL_TYPES = (
    "current_state",
    "decision",
    "open_question",
    "bug_or_issue",
    "rule_or_preference",
    "artifact_or_file",
    "command_or_setting",
    "version_change",
    "next_action",
    "contradiction_candidate",
)
ALLOWED_STATUS_HINTS = (
    "current",
    "historical",
    "superseded",
    "open",
    "uncertain",
    "proposed",
    "resolved",
    "unknown",
)
ALLOWED_CONFIDENCES = ("high", "medium", "low", "unknown")


def ensure_trailing_newline(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


def ordinal(value: int) -> str:
    if 10 <= value % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


def stable_hash(parts: Sequence[Any], prefix: str) -> str:
    payload = "\n".join(str(part) for part in parts)
    return f"{prefix}-{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def resolve_chunk_path(raw_path: Any, plan_dir: Path) -> Path:
    chunk_path = Path(str(raw_path or ""))
    if chunk_path.is_absolute() or chunk_path.is_file():
        return chunk_path
    plan_relative = plan_dir / chunk_path
    if plan_relative.is_file():
        return plan_relative.resolve()
    return chunk_path


def discover_chunk_plans(chunk_root: Path) -> list[Path]:
    return sorted(chunk_root.glob("*/chunk_plan.json"))


def packet_id(conversation_id: str, chunk_id: str, chunk_pass: str, source_hash: str) -> str:
    return stable_hash([conversation_id, chunk_id, chunk_pass, source_hash], "packet")


def build_packet_markdown(
    packet_id_value: str,
    conversation_id: str,
    chunk_id: str,
    chunk_pass: str,
    chunk_path: Path,
    chunk_text: str,
    max_signals_per_packet: int | None = None,
) -> str:
    lines = [
        "# Raw Signal Extraction Packet",
        "",
        f"Packet ID: {packet_id_value}",
        f"Conversation ID: {conversation_id}",
        f"Chunk ID: {chunk_id}",
        f"Chunk Pass: {chunk_pass}",
        f"Chunk Path: {chunk_path}",
        f"Expected Output: {EXPECTED_OUTPUT}",
    ]
    if max_signals_per_packet is not None:
        lines.append(f"Max Signals Per Packet: {max_signals_per_packet}")
    lines.extend(
        [
            "",
            "## Task",
            "",
            "Extract durable raw signals from the source chunk below.",
            "",
            "Return JSONL only. One JSON object per line. No prose, no markdown fences.",
        ]
    )
    if max_signals_per_packet is not None:
        lines.extend(
            [
                "",
                f"Return at most {max_signals_per_packet} raw signal objects.",
                "Prefer highest-confidence, durable, user-specific signals.",
                f"If more than {max_signals_per_packet} candidates exist, omit weaker or redundant candidates.",
                f"Stop after the {ordinal(max_signals_per_packet)} object.",
                "If no good signal exists, return nothing.",
            ]
        )
    lines.extend(
        [
            "",
            "Each JSON object must include:",
            "",
            "- raw_signal_id",
            "- claim",
            "- signal_type",
            "- status_hint",
            "- confidence",
            "- conversation_id",
            "- chunk_id",
            "- chunk_pass",
            "- turn_start",
            "- turn_end",
            "- source_path",
            "- evidence_note",
            "",
            "Allowed signal_type values:",
            "",
        ]
    )
    lines.extend(f"- {value}" for value in ALLOWED_SIGNAL_TYPES)
    lines.extend(
        [
            "",
            "Allowed status_hint values:",
            "",
        ]
    )
    lines.extend(f"- {value}" for value in ALLOWED_STATUS_HINTS)
    lines.extend(
        [
            "",
            "Allowed confidence values:",
            "",
        ]
    )
    lines.extend(f"- {value}" for value in ALLOWED_CONFIDENCES)
    lines.extend(
        [
            "",
            "Rules:",
            "",
            "- Extract only information grounded in the chunk.",
            "- Do not invent facts.",
            "- Prefer small atomic claims.",
            "- Preserve uncertainty.",
            "- Use `topic_key` when multiple claims appear to refer to the same evolving subject.",
            "- This is review material, not canonical memory.",
            "",
            "## Source Chunk",
            "",
            chunk_text.rstrip(),
            "",
        ]
    )
    return ensure_trailing_newline("\n".join(lines).rstrip())


def packet_rows_from_plan(plan_path: Path) -> list[dict[str, Any]]:
    plan = load_json(plan_path)
    conversation_id = str(plan.get("conversation_id", ""))
    source_hash = str(plan.get("source_hash", ""))
    rows: list[dict[str, Any]] = []
    passes = plan.get("passes", [])
    if not isinstance(passes, list):
        return rows
    for pass_row in passes:
        if not isinstance(pass_row, dict):
            continue
        chunk_pass = str(pass_row.get("name", ""))
        chunks = pass_row.get("chunks", [])
        if not isinstance(chunks, list):
            continue
        for chunk in chunks:
            if not isinstance(chunk, dict):
                continue
            chunk_id = str(chunk.get("chunk_id", ""))
            chunk_path = resolve_chunk_path(chunk.get("path", ""), plan_path.parent)
            rows.append(
                {
                    "packet_id": packet_id(conversation_id, chunk_id, chunk_pass, source_hash),
                    "conversation_id": conversation_id,
                    "chunk_id": chunk_id,
                    "chunk_pass": chunk_pass,
                    "chunk_path": str(chunk_path),
                    "expected_output": EXPECTED_OUTPUT,
                    "source_hash": source_hash,
                }
            )
    return rows


def generate_packets(chunk_root: Path, out_dir: Path, max_signals_per_packet: int | None = None) -> dict[str, Any]:
    if max_signals_per_packet is not None and max_signals_per_packet <= 0:
        raise ValueError("--max-signals-per-packet must be greater than zero.")

    packet_dir = out_dir / "packet_files"
    packet_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for plan_path in discover_chunk_plans(chunk_root):
        rows.extend(packet_rows_from_plan(plan_path))
    rows.sort(key=lambda row: (row["conversation_id"], row["chunk_pass"], row["chunk_id"]))

    for index, row in enumerate(rows, start=1):
        chunk_path = Path(str(row["chunk_path"]))
        chunk_text = chunk_path.read_text(encoding="utf-8")
        packet_path = packet_dir / f"packet_{index:06d}.md"
        packet_path.write_text(
            build_packet_markdown(
                packet_id_value=str(row["packet_id"]),
                conversation_id=str(row["conversation_id"]),
                chunk_id=str(row["chunk_id"]),
                chunk_pass=str(row["chunk_pass"]),
                chunk_path=chunk_path,
                chunk_text=chunk_text,
                max_signals_per_packet=max_signals_per_packet,
            ),
            encoding="utf-8",
        )
        row["packet_path"] = str(packet_path)
        if max_signals_per_packet is not None:
            row["max_signals_per_packet"] = max_signals_per_packet

    out_dir.mkdir(parents=True, exist_ok=True)
    packets_path = out_dir / "packets.jsonl"
    packets_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    summary = {
        "chunk_root": str(chunk_root),
        "packet_count": len(rows),
        "conversation_count": len({row["conversation_id"] for row in rows}),
        "expected_output": EXPECTED_OUTPUT,
        "max_signals_per_packet": max_signals_per_packet,
        "packets_path": str(packets_path),
        "packet_files_dir": str(packet_dir),
    }
    (out_dir / "packet_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate offline raw-signal extraction packets from chunk plans.")
    parser.add_argument("--chunk-root", required=True, help="Directory containing <conversation_id>/chunk_plan.json files.")
    parser.add_argument("--out-dir", required=True, help="Directory that will receive packet files and packets.jsonl.")
    parser.add_argument(
        "--max-signals-per-packet",
        type=int,
        help="Optional cap for raw signal objects requested from each packet.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = generate_packets(
            Path(args.chunk_root),
            Path(args.out_dir),
            max_signals_per_packet=args.max_signals_per_packet,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"Wrote packets: {summary['packet_count']}")
    print(f"Packet manifest: {summary['packets_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
