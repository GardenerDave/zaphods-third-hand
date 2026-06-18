#!/usr/bin/env python3
"""Validate raw signal JSONL without deduplicating or calling models."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Sequence


ALLOWED_SIGNAL_TYPES = {
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
    "unknown",
}
ALLOWED_STATUS_HINTS = {
    "current",
    "historical",
    "superseded",
    "open",
    "uncertain",
    "proposed",
    "resolved",
    "unknown",
}
ALLOWED_CONFIDENCES = {"high", "medium", "low", "unknown"}
REQUIRED_OUTPUT_FIELDS = (
    "raw_signal_id",
    "claim",
    "signal_type",
    "status_hint",
    "confidence",
    "conversation_id",
    "chunk_id",
    "chunk_pass",
    "turn_start",
    "turn_end",
    "source_path",
    "evidence_note",
)


def one_line(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    text = " ".join(line.strip() for line in text.split("\n")).strip()
    return text or default


def normalize_label(value: Any, allowed: set[str]) -> str:
    text = one_line(value).lower()
    text = re.sub(r"[^a-z0-9._-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("._-")
    return text if text in allowed else "unknown"


def generated_raw_signal_id(row: dict[str, Any], line_number: int) -> str:
    payload = json.dumps(
        {
            "line_number": line_number,
            "claim": one_line(row.get("claim")),
            "conversation_id": one_line(row.get("conversation_id")),
            "chunk_id": one_line(row.get("chunk_id")),
            "chunk_pass": one_line(row.get("chunk_pass")),
            "turn_start": row.get("turn_start"),
            "turn_end": row.get("turn_end"),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"raw-generated-{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def invalid_row(line_number: int, reason: str, raw_line: str, row: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "line_number": line_number,
        "reason": reason,
        "raw_line": raw_line,
    }
    if row is not None:
        payload["raw_signal_id"] = one_line(row.get("raw_signal_id"))
    return payload


def normalize_valid_row(row: dict[str, Any], line_number: int) -> dict[str, Any]:
    raw_signal_id = one_line(row.get("raw_signal_id"))
    if not raw_signal_id:
        raw_signal_id = generated_raw_signal_id(row, line_number)

    normalized = {
        "raw_signal_id": raw_signal_id,
        "claim": one_line(row.get("claim")),
        "signal_type": normalize_label(row.get("signal_type"), ALLOWED_SIGNAL_TYPES),
        "status_hint": normalize_label(row.get("status_hint"), ALLOWED_STATUS_HINTS),
        "confidence": normalize_label(row.get("confidence"), ALLOWED_CONFIDENCES),
        "conversation_id": one_line(row.get("conversation_id")),
        "chunk_id": one_line(row.get("chunk_id")),
        "chunk_pass": one_line(row.get("chunk_pass")),
        "turn_start": row.get("turn_start"),
        "turn_end": row.get("turn_end"),
        "source_path": one_line(row.get("source_path")),
        "evidence_note": one_line(row.get("evidence_note")),
    }
    topic_key = one_line(row.get("topic_key"))
    if topic_key:
        normalized["topic_key"] = topic_key
    return normalized


def validate_raw_signals(raw_signals_path: Path, out_dir: Path) -> dict[str, Any]:
    valid_rows: list[dict[str, Any]] = []
    invalid_rows: list[dict[str, Any]] = []
    input_count = 0
    generated_id_count = 0
    normalized_unknown_count = 0

    for line_number, line in enumerate(raw_signals_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        input_count += 1
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            invalid_rows.append(invalid_row(line_number, f"invalid_json: {exc.msg}", line))
            continue
        if not isinstance(row, dict):
            invalid_rows.append(invalid_row(line_number, "row_is_not_object", line))
            continue
        if not one_line(row.get("claim")):
            invalid_rows.append(invalid_row(line_number, "empty_claim", line, row))
            continue

        before_labels = (
            one_line(row.get("signal_type")).lower(),
            one_line(row.get("status_hint")).lower(),
            one_line(row.get("confidence")).lower(),
        )
        normalized = normalize_valid_row(row, line_number)
        after_labels = (
            normalized["signal_type"],
            normalized["status_hint"],
            normalized["confidence"],
        )
        for before, after in zip(before_labels, after_labels):
            if before and before != after and after == "unknown":
                normalized_unknown_count += 1
        if not one_line(row.get("raw_signal_id")):
            generated_id_count += 1
        valid_rows.append(normalized)

    out_dir.mkdir(parents=True, exist_ok=True)
    valid_path = out_dir / "valid_raw_signals.jsonl"
    invalid_path = out_dir / "invalid_raw_signals.jsonl"
    valid_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in valid_rows),
        encoding="utf-8",
    )
    invalid_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in invalid_rows),
        encoding="utf-8",
    )
    summary = {
        "input_row_count": input_count,
        "valid_count": len(valid_rows),
        "invalid_count": len(invalid_rows),
        "generated_raw_signal_id_count": generated_id_count,
        "normalized_unknown_label_count": normalized_unknown_count,
        "deduped": False,
        "valid_path": str(valid_path),
        "invalid_path": str(invalid_path),
    }
    (out_dir / "validation_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate raw signal JSONL without deduplication.")
    parser.add_argument("--raw-signals", required=True, help="Path to raw signal JSONL.")
    parser.add_argument("--out-dir", required=True, help="Directory that will receive validation outputs.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = validate_raw_signals(Path(args.raw_signals), Path(args.out_dir))
    print(f"Valid raw signals: {summary['valid_count']}")
    print(f"Invalid raw signals: {summary['invalid_count']}")
    print(f"Validation summary: {Path(args.out_dir) / 'validation_summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
