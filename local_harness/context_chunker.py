#!/usr/bin/env python3
"""Plan reviewable context chunks from normalized ChatGPT export markdown."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


SUPPORTED_PROFILES = ("semantic", "small-model", "small-model-offset")
DEFAULT_TARGET_CHARS = 12000
DEFAULT_OVERLAP_TURNS = 1
DEFAULT_OFFSET_TURNS = 1
TURN_HEADING_RE = re.compile(r"^### Turn (\d+)\s+\u2014\s+(.+?)\s+\u2014\s+(.+)$", re.MULTILINE)


@dataclass
class SourceTurn:
    number: int
    role: str
    timestamp: str
    markdown: str

    @property
    def char_count(self) -> int:
        return len(self.markdown)


@dataclass
class PlannedChunk:
    chunk_pass: str
    chunk_index: int
    turns: list[SourceTurn]
    profile: str
    target_chars: int
    strategy: str

    @property
    def turn_start(self) -> int:
        return self.turns[0].number

    @property
    def turn_end(self) -> int:
        return self.turns[-1].number

    @property
    def char_count(self) -> int:
        return sum(turn.char_count for turn in self.turns)

    @property
    def oversized(self) -> bool:
        return len(self.turns) == 1 and self.turns[0].char_count > self.target_chars


def ensure_trailing_newline(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


def filesystem_token(value: Any, default: str = "conversation", max_length: int = 96) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("._-")
    if len(text) > max_length:
        text = text[:max_length].rstrip("._-")
    return text or default


def load_manifest(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_number} must be a JSON object")
        rows.append(row)
    return rows


def resolve_source_path(raw_path: Any, manifest_dir: Path) -> Path:
    source_path = Path(str(raw_path or ""))
    if source_path.is_absolute() or source_path.is_file():
        return source_path
    manifest_relative = manifest_dir / source_path
    if manifest_relative.is_file():
        return manifest_relative.resolve()
    return source_path


def parse_turns(markdown: str) -> list[SourceTurn]:
    matches = list(TURN_HEADING_RE.finditer(markdown))
    turns: list[SourceTurn] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        block = markdown[start:end].strip()
        if not block:
            continue
        turns.append(
            SourceTurn(
                number=int(match.group(1)),
                role=match.group(2).strip(),
                timestamp=match.group(3).strip(),
                markdown=ensure_trailing_newline(block),
            )
        )
    return turns


def semantic_chunks(turns: list[SourceTurn], profile: str, target_chars: int) -> list[PlannedChunk]:
    chunks: list[PlannedChunk] = []
    index = 0
    while index < len(turns):
        chunk_turns = [turns[index]]
        if (
            turns[index].role.lower() == "user"
            and index + 1 < len(turns)
            and turns[index + 1].role.lower() == "assistant"
        ):
            chunk_turns.append(turns[index + 1])
            index += 2
        else:
            index += 1

        chunks.append(
            PlannedChunk(
                chunk_pass="pass_A",
                chunk_index=len(chunks),
                turns=chunk_turns,
                profile=profile,
                target_chars=target_chars,
                strategy="semantic_exchange_preserve_turns",
            )
        )
    return chunks


def small_model_chunks(
    turns: list[SourceTurn],
    profile: str,
    target_chars: int,
    overlap_turns: int,
    chunk_pass: str,
    start_offset: int = 0,
) -> list[PlannedChunk]:
    if not turns:
        return []

    start = min(max(start_offset, 0), len(turns) - 1)
    chunks: list[PlannedChunk] = []

    while start < len(turns):
        first_turn = turns[start]
        if first_turn.char_count > target_chars:
            end = start
        else:
            end = start
            char_count = first_turn.char_count
            while end + 1 < len(turns):
                next_count = turns[end + 1].char_count
                if char_count + next_count > target_chars:
                    break
                end += 1
                char_count += next_count

        chunk_turns = turns[start : end + 1]
        chunks.append(
            PlannedChunk(
                chunk_pass=chunk_pass,
                chunk_index=len(chunks),
                turns=chunk_turns,
                profile=profile,
                target_chars=target_chars,
                strategy="target_chars_preserve_turns",
            )
        )

        if end >= len(turns) - 1:
            break

        next_start = end + 1 - max(overlap_turns, 0)
        if next_start <= start:
            next_start = end + 1
        start = next_start

    return chunks


def plan_passes(
    turns: list[SourceTurn],
    profile: str,
    target_chars: int,
    overlap_turns: int,
    offset_turns: int,
) -> list[tuple[str, list[PlannedChunk]]]:
    if profile == "semantic":
        return [("pass_A", semantic_chunks(turns, profile, target_chars))]

    pass_a = small_model_chunks(
        turns=turns,
        profile=profile,
        target_chars=target_chars,
        overlap_turns=overlap_turns,
        chunk_pass="pass_A",
        start_offset=0,
    )
    passes = [("pass_A", pass_a)]
    if profile == "small-model-offset":
        pass_b = small_model_chunks(
            turns=turns,
            profile=profile,
            target_chars=target_chars,
            overlap_turns=overlap_turns,
            chunk_pass="pass_B_offset",
            start_offset=offset_turns,
        )
        passes.append(("pass_B_offset", pass_b))
    return passes


def stable_chunk_id(
    conversation_id: str,
    chunk_pass: str,
    chunk_index: int,
    turn_start: int,
    turn_end: int,
    source_hash: str,
) -> str:
    payload = "\n".join(
        [
            conversation_id,
            chunk_pass,
            str(chunk_index),
            str(turn_start),
            str(turn_end),
            source_hash,
        ]
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"chunk-{digest}"


def build_chunk_markdown(
    manifest_row: dict[str, Any],
    chunk: PlannedChunk,
    chunk_id: str,
    source_path: Path,
) -> str:
    lines = [
        "# Distiller Chunk",
        "",
        f"Conversation ID: {manifest_row.get('conversation_id', '')}",
        f"Conversation Title: {manifest_row.get('title', '')}",
        f"Source Hash: {manifest_row.get('source_hash', '')}",
        f"Source Path: {source_path}",
        f"Chunk ID: {chunk_id}",
        f"Chunk Pass: {chunk.chunk_pass}",
        f"Chunk Index: {chunk.chunk_index}",
        f"Profile: {chunk.profile}",
        f"Turn Start: {chunk.turn_start}",
        f"Turn End: {chunk.turn_end}",
        f"Oversized: {str(chunk.oversized).lower()}",
        f"Chunk Strategy: {chunk.strategy}",
        "",
        "## Source Turns",
        "",
    ]
    for turn in chunk.turns:
        lines.append(turn.markdown.rstrip())
        lines.append("")
    return ensure_trailing_newline("\n".join(lines).rstrip())


def plan_manifest_row(
    manifest_row: dict[str, Any],
    manifest_dir: Path,
    out_dir: Path,
    profile: str,
    target_chars: int,
    overlap_turns: int,
    offset_turns: int,
) -> dict[str, Any]:
    source_path = resolve_source_path(manifest_row.get("normalized_path", ""), manifest_dir)
    markdown = source_path.read_text(encoding="utf-8")
    turns = parse_turns(markdown)

    conversation_id = str(manifest_row.get("conversation_id", "conversation"))
    conversation_dir = out_dir / filesystem_token(conversation_id)
    conversation_dir.mkdir(parents=True, exist_ok=True)

    source_hash = str(manifest_row.get("source_hash", ""))
    plan_pass_rows: list[dict[str, Any]] = []
    for pass_name, chunks in plan_passes(turns, profile, target_chars, overlap_turns, offset_turns):
        pass_dir = conversation_dir / pass_name
        pass_dir.mkdir(parents=True, exist_ok=True)
        chunk_rows: list[dict[str, Any]] = []
        for chunk in chunks:
            chunk_id = stable_chunk_id(
                conversation_id=conversation_id,
                chunk_pass=pass_name,
                chunk_index=chunk.chunk_index,
                turn_start=chunk.turn_start,
                turn_end=chunk.turn_end,
                source_hash=source_hash,
            )
            chunk_path = pass_dir / f"chunk_{chunk.chunk_index:03d}.md"
            chunk_path.write_text(build_chunk_markdown(manifest_row, chunk, chunk_id, source_path), encoding="utf-8")
            chunk_rows.append(
                {
                    "chunk_id": chunk_id,
                    "path": str(chunk_path),
                    "chunk_index": chunk.chunk_index,
                    "turn_start": chunk.turn_start,
                    "turn_end": chunk.turn_end,
                    "char_count": chunk.char_count,
                    "oversized": chunk.oversized,
                }
            )
        plan_pass_rows.append({"name": pass_name, "chunks": chunk_rows})

    plan = {
        "conversation_id": conversation_id,
        "title": str(manifest_row.get("title", "")),
        "source_hash": source_hash,
        "source_path": str(source_path),
        "profile": profile,
        "target_chars": target_chars,
        "overlap_turns": overlap_turns,
        "offset_turns": offset_turns,
        "approximation": "character_count",
        "passes": plan_pass_rows,
    }
    (conversation_dir / "chunk_plan.json").write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return plan


def plan_manifest(
    manifest_path: Path,
    out_dir: Path,
    profile: str,
    target_chars: int = DEFAULT_TARGET_CHARS,
    overlap_turns: int = DEFAULT_OVERLAP_TURNS,
    offset_turns: int = DEFAULT_OFFSET_TURNS,
) -> list[dict[str, Any]]:
    if profile not in SUPPORTED_PROFILES:
        raise ValueError(f"Unsupported profile: {profile}")
    if target_chars <= 0:
        raise ValueError("--target-chars must be greater than zero")
    if overlap_turns < 0:
        raise ValueError("--overlap-turns must be zero or greater")
    if offset_turns < 0:
        raise ValueError("--offset-turns must be zero or greater")

    out_dir.mkdir(parents=True, exist_ok=True)
    plans: list[dict[str, Any]] = []
    for row in load_manifest(manifest_path):
        plans.append(
            plan_manifest_row(
                manifest_row=row,
                manifest_dir=manifest_path.parent,
                out_dir=out_dir,
                profile=profile,
                target_chars=target_chars,
                overlap_turns=overlap_turns,
                offset_turns=offset_turns,
            )
        )
    return plans


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plan reviewable chunks from normalized ChatGPT export markdown.",
    )
    parser.add_argument("--manifest", required=True, help="Path to ingestion conversations.jsonl manifest.")
    parser.add_argument("--out-dir", required=True, help="Directory that will receive chunk plans.")
    parser.add_argument("--profile", required=True, choices=SUPPORTED_PROFILES, help="Chunk planning profile.")
    parser.add_argument(
        "--target-chars",
        type=int,
        default=DEFAULT_TARGET_CHARS,
        help="Approximate maximum characters per non-oversized chunk.",
    )
    parser.add_argument(
        "--overlap-turns",
        type=int,
        default=DEFAULT_OVERLAP_TURNS,
        help="Turn overlap between adjacent small-model chunks.",
    )
    parser.add_argument(
        "--offset-turns",
        type=int,
        default=DEFAULT_OFFSET_TURNS,
        help="Initial turn shift for the optional offset pass.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    plans = plan_manifest(
        manifest_path=Path(args.manifest),
        out_dir=Path(args.out_dir),
        profile=args.profile,
        target_chars=args.target_chars,
        overlap_turns=args.overlap_turns,
        offset_turns=args.offset_turns,
    )
    chunk_count = sum(len(pass_row["chunks"]) for plan in plans for pass_row in plan["passes"])
    print(f"Wrote chunk plans for {len(plans)} conversation(s) to {Path(args.out_dir)}")
    print(f"Chunk files: {chunk_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
