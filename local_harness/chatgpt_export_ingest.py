#!/usr/bin/env python3
"""Normalize ChatGPT export conversations into reviewable source files."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


SKIPPED_ROLES = {"system", "tool"}
TURN_SEPARATOR = " \u2014 "


@dataclass
class Turn:
    role: str
    timestamp: str
    content: str
    node_id: str


@dataclass
class ConversationRecord:
    conversation_id: str
    title: str
    slug: str
    created_at: str
    updated_at: str
    source_export: str
    source_hash: str
    turns: list[Turn]
    normalized_path: Path | None = None
    byte_count: int = 0


def ensure_trailing_newline(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def hash_json(value: Any) -> str:
    return hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def one_line(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    text = " ".join(line.strip() for line in text.split("\n")).strip()
    return text or default


def filesystem_token(value: str, default: str, *, lower: bool, max_length: int = 80) -> str:
    text = unicodedata.normalize("NFKD", value)
    text = text.encode("ascii", "ignore").decode("ascii")
    if lower:
        text = text.lower()
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("._-")
    if len(text) > max_length:
        text = text[:max_length].rstrip("._-")
    return text or default


def slugify(value: Any) -> str:
    return filesystem_token(one_line(value, "untitled"), "untitled", lower=True, max_length=72)


def stable_conversation_id(value: Any, source_hash: str) -> str:
    raw_id = one_line(value)
    if raw_id:
        return filesystem_token(raw_id, f"conversation-{source_hash[:12]}", lower=False, max_length=80)
    return f"conversation-{source_hash[:12]}"


def parse_timestamp_epoch(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        numeric = float(value)
        return numeric if math.isfinite(numeric) else None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            numeric = float(text)
            return numeric if math.isfinite(numeric) else None
        except ValueError:
            pass
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    return None


def format_timestamp(value: Any) -> str:
    epoch = parse_timestamp_epoch(value)
    if epoch is None:
        return "unknown"
    try:
        return datetime.fromtimestamp(epoch, timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    except (OverflowError, OSError, ValueError):
        return "unknown"


def stringify_part(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return json.dumps(value, ensure_ascii=False)
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except TypeError:
        return str(value)


def message_content_text(message: dict[str, Any]) -> str:
    content = message.get("content")
    pieces: list[str] = []

    if isinstance(content, dict):
        parts = content.get("parts")
        if isinstance(parts, list):
            pieces = [stringify_part(part) for part in parts]
        elif parts is not None:
            pieces = [stringify_part(parts)]
        else:
            for key in ("text", "result", "summary"):
                if key in content:
                    pieces = [stringify_part(content.get(key))]
                    break
    elif isinstance(content, list):
        pieces = [stringify_part(part) for part in content]
    else:
        pieces = [stringify_part(content)]

    text = "\n\n".join(piece.strip() for piece in pieces if piece and piece.strip())
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def message_role(message: dict[str, Any]) -> str:
    author = message.get("author")
    role = author.get("role") if isinstance(author, dict) else None
    return one_line(role, "unknown")


def turn_from_node(node_id: str, node: Any) -> Turn | None:
    if not isinstance(node, dict):
        return None
    message = node.get("message")
    if not isinstance(message, dict):
        return None

    role = message_role(message)
    content = message_content_text(message)
    if not content:
        return None
    if role.lower() in SKIPPED_ROLES:
        return None

    return Turn(
        role=role,
        timestamp=format_timestamp(message.get("create_time")),
        content=content,
        node_id=node_id,
    )


def primary_path_node_ids(mapping: dict[str, Any], current_node: Any) -> list[str] | None:
    if not mapping or current_node is None:
        return None

    node_id = str(current_node)
    if node_id not in mapping:
        return None

    seen: set[str] = set()
    path: list[str] = []
    while node_id:
        if node_id in seen:
            return None
        seen.add(node_id)

        node = mapping.get(node_id)
        if not isinstance(node, dict):
            return None
        path.append(node_id)

        parent = node.get("parent")
        if parent is None:
            break
        parent_id = str(parent)
        if parent_id not in mapping:
            return None
        node_id = parent_id

    return list(reversed(path))


def node_sort_key(item: tuple[str, Any]) -> tuple[int, float, str]:
    node_id, node = item
    timestamp = None
    if isinstance(node, dict) and isinstance(node.get("message"), dict):
        timestamp = parse_timestamp_epoch(node["message"].get("create_time"))
    if timestamp is None:
        return (1, 0.0, node_id)
    return (0, timestamp, node_id)


def fallback_turns(mapping: dict[str, Any]) -> list[Turn]:
    turns: list[Turn] = []
    for node_id, node in sorted(mapping.items(), key=node_sort_key):
        turn = turn_from_node(node_id, node)
        if turn is not None:
            turns.append(turn)
    return turns


def extract_turns(conversation: dict[str, Any]) -> list[Turn]:
    mapping = conversation.get("mapping")
    if not isinstance(mapping, dict):
        return []

    path = primary_path_node_ids(mapping, conversation.get("current_node"))
    if path is not None:
        turns = [turn for node_id in path if (turn := turn_from_node(node_id, mapping.get(node_id))) is not None]
        if turns:
            return turns

    return fallback_turns(mapping)


def build_record(conversation: Any, source_export: Path) -> ConversationRecord:
    conversation_data = conversation if isinstance(conversation, dict) else {}
    source_hash = hash_json(conversation)
    title = one_line(conversation_data.get("title"), "Untitled")
    return ConversationRecord(
        conversation_id=stable_conversation_id(conversation_data.get("id"), source_hash),
        title=title,
        slug=slugify(title),
        created_at=format_timestamp(conversation_data.get("create_time")),
        updated_at=format_timestamp(conversation_data.get("update_time")),
        source_export=str(source_export),
        source_hash=source_hash,
        turns=extract_turns(conversation_data),
    )


def deduplicate_record_ids(records: list[ConversationRecord]) -> None:
    seen_ids: set[str] = set()
    for record in records:
        base_id = record.conversation_id
        candidate = base_id
        if candidate in seen_ids:
            suffix = record.source_hash[:8]
            candidate = f"{base_id}-{suffix}"
            counter = 2
            while candidate in seen_ids:
                candidate = f"{base_id}-{suffix}-{counter}"
                counter += 1
            record.conversation_id = candidate
        seen_ids.add(record.conversation_id)


def build_markdown(record: ConversationRecord) -> str:
    lines = [
        "# ChatGPT Conversation Source",
        "",
        f"Conversation ID: {record.conversation_id}",
        f"Title: {record.title}",
        f"Created: {record.created_at}",
        f"Updated: {record.updated_at}",
        f"Source export: {record.source_export}",
        f"Source hash: {record.source_hash}",
        f"Turn count: {len(record.turns)}",
        "",
        "## Turns",
        "",
    ]

    for index, turn in enumerate(record.turns, start=1):
        lines.extend(
            [
                f"### Turn {index:04d}{TURN_SEPARATOR}{turn.role}{TURN_SEPARATOR}{turn.timestamp}",
                "",
                turn.content.rstrip(),
                "",
            ]
        )

    return ensure_trailing_newline("\n".join(lines).rstrip())


def manifest_row(record: ConversationRecord) -> dict[str, Any]:
    if record.normalized_path is None:
        raise ValueError("record has not been written yet")
    return {
        "conversation_id": record.conversation_id,
        "title": record.title,
        "slug": record.slug,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "normalized_path": str(record.normalized_path),
        "source_hash": record.source_hash,
        "turn_count": len(record.turns),
        "byte_count": record.byte_count,
    }


def load_conversations(export_dir: Path) -> tuple[Path, list[Any]]:
    export_file = export_dir / "conversations.json"
    data = json.loads(export_file.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{export_file} must contain a top-level JSON array")
    return export_file, data


def ingest_export(export_dir: Path, out_dir: Path) -> list[dict[str, Any]]:
    export_file, conversations = load_conversations(export_dir)
    normalized_dir = out_dir / "normalized"
    manifest_dir = out_dir / "manifests"
    normalized_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)

    records = [build_record(conversation, export_file) for conversation in conversations]
    records.sort(key=lambda record: (record.created_at == "unknown", record.created_at, record.conversation_id))
    deduplicate_record_ids(records)

    rows: list[dict[str, Any]] = []
    for record in records:
        output_path = normalized_dir / f"{record.conversation_id}_{record.slug}.md"
        markdown = build_markdown(record)
        output_path.write_text(markdown, encoding="utf-8")
        record.normalized_path = output_path
        record.byte_count = len(markdown.encode("utf-8"))
        rows.append(manifest_row(record))

    manifest_path = manifest_dir / "conversations.jsonl"
    manifest_text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    manifest_path.write_text(manifest_text, encoding="utf-8")
    return rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Normalize a ChatGPT conversations.json export into reviewable source files.",
    )
    parser.add_argument("--export-dir", required=True, help="Directory containing conversations.json.")
    parser.add_argument("--out-dir", required=True, help="Directory that will receive normalized/ and manifests/.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    rows = ingest_export(Path(args.export_dir), Path(args.out_dir))
    print(f"Wrote {len(rows)} conversation(s) to {Path(args.out_dir) / 'normalized'}")
    print(f"Manifest: {Path(args.out_dir) / 'manifests' / 'conversations.jsonl'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
