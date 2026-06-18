#!/usr/bin/env python3
"""Deduplicate synthetic raw signals into reviewable signal scaffolding."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence


NEAR_DUPLICATE_MIN_CONTAINMENT = 0.92
NEAR_DUPLICATE_MIN_JACCARD = 0.80
CONFLICT_STATUS_PAIRS = {frozenset(("historical", "current"))}
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "is",
    "of",
    "the",
    "to",
}
CONFIDENCE_ORDER = {"unknown": 0, "low": 1, "medium": 2, "high": 3}


@dataclass
class RawSignal:
    raw_signal_id: str
    claim: str
    normalized_claim: str
    tokens: set[str]
    signal_type: str
    status: str
    confidence: str
    conversation_id: str
    chunk_id: str
    chunk_pass: str
    turn_start: Any
    turn_end: Any
    source_path: str
    evidence_note: str
    topic_key: str
    normalized_topic_key: str
    input_index: int
    raw_row: dict[str, Any]


@dataclass
class SignalGroup:
    canonical: RawSignal
    raw_signals: list[RawSignal] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.raw_signals.append(self.canonical)


def one_line(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    text = " ".join(line.strip() for line in text.split("\n")).strip()
    return text or default


def normalize_label(value: Any, default: str = "unknown") -> str:
    text = one_line(value).lower()
    text = re.sub(r"[^a-z0-9._-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("._-")
    return text or default


def normalize_claim(value: Any) -> str:
    text = one_line(value).lower()
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def tokenize_claim(normalized_claim: str) -> set[str]:
    return {token for token in normalized_claim.split() if token not in STOPWORDS}


def stable_hash(parts: Sequence[Any], prefix: str) -> str:
    payload = "\n".join(str(part) for part in parts)
    return f"{prefix}-{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def load_raw_signals(path: Path) -> tuple[list[RawSignal], list[str], int]:
    raw_signals: list[RawSignal] = []
    skipped_empty_ids: list[str] = []
    raw_count = 0
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_number} must be a JSON object")
        raw_count += 1
        raw_signal_id = one_line(row.get("raw_signal_id"), f"raw-missing-{raw_count:04d}")
        claim = one_line(row.get("claim"))
        if not claim:
            skipped_empty_ids.append(raw_signal_id)
            continue

        normalized_claim = normalize_claim(claim)
        raw_signals.append(
            RawSignal(
                raw_signal_id=raw_signal_id,
                claim=claim,
                normalized_claim=normalized_claim,
                tokens=tokenize_claim(normalized_claim),
                signal_type=normalize_label(row.get("signal_type")),
                status=normalize_label(row.get("status_hint")),
                confidence=normalize_label(row.get("confidence")),
                conversation_id=one_line(row.get("conversation_id")),
                chunk_id=one_line(row.get("chunk_id")),
                chunk_pass=one_line(row.get("chunk_pass")),
                turn_start=row.get("turn_start"),
                turn_end=row.get("turn_end"),
                source_path=one_line(row.get("source_path")),
                evidence_note=one_line(row.get("evidence_note")),
                topic_key=one_line(row.get("topic_key")),
                normalized_topic_key=normalize_claim(row.get("topic_key")),
                input_index=len(raw_signals),
                raw_row=row,
            )
        )
    return raw_signals, skipped_empty_ids, raw_count


def dedupe_partition_key(signal: RawSignal) -> tuple[str, str, str]:
    return (signal.signal_type, signal.status, signal.normalized_topic_key)


def token_overlap(left: set[str], right: set[str]) -> tuple[float, float]:
    if not left or not right:
        return (0.0, 0.0)
    intersection = len(left & right)
    containment = intersection / min(len(left), len(right))
    jaccard = intersection / len(left | right)
    return (containment, jaccard)


def duplicate_reason(candidate: RawSignal, group: SignalGroup) -> str | None:
    if dedupe_partition_key(candidate) != dedupe_partition_key(group.canonical):
        return None
    if candidate.normalized_claim == group.canonical.normalized_claim:
        return "normalized_claim_match"

    containment, jaccard = token_overlap(candidate.tokens, group.canonical.tokens)
    if containment >= NEAR_DUPLICATE_MIN_CONTAINMENT and jaccard >= NEAR_DUPLICATE_MIN_JACCARD:
        return "high_token_overlap"
    return None


def dedupe_signals(raw_signals: list[RawSignal]) -> tuple[list[SignalGroup], list[dict[str, Any]]]:
    groups: list[SignalGroup] = []
    duplicate_links: list[dict[str, Any]] = []

    for signal in raw_signals:
        matching_group: SignalGroup | None = None
        matching_reason: str | None = None
        for group in groups:
            reason = duplicate_reason(signal, group)
            if reason is not None:
                matching_group = group
                matching_reason = reason
                break

        if matching_group is None:
            groups.append(SignalGroup(canonical=signal))
            continue

        matching_group.raw_signals.append(signal)
        duplicate_links.append(
            {
                "canonical_signal_id": canonical_signal_id(matching_group),
                "raw_signal_id": signal.raw_signal_id,
                "duplicate_of_raw_signal_id": matching_group.canonical.raw_signal_id,
                "reason": matching_reason,
            }
        )

    return groups, duplicate_links


def unique_sorted(values: list[str]) -> list[str]:
    return sorted({value for value in values if value})


def max_confidence(signals: list[RawSignal]) -> str:
    best = "unknown"
    for signal in signals:
        if CONFIDENCE_ORDER.get(signal.confidence, 0) > CONFIDENCE_ORDER.get(best, 0):
            best = signal.confidence
    return best


def canonical_signal_id(group: SignalGroup) -> str:
    canonical = group.canonical
    return stable_hash(
        [
            canonical.signal_type,
            canonical.status,
            canonical.normalized_topic_key,
            canonical.normalized_claim,
        ],
        "sig",
    )


def deduped_row(group: SignalGroup) -> dict[str, Any]:
    signals = group.raw_signals
    return {
        "canonical_signal_id": canonical_signal_id(group),
        "claim": group.canonical.claim,
        "signal_type": group.canonical.signal_type,
        "status": group.canonical.status,
        "confidence": max_confidence(signals),
        "supporting_raw_signal_ids": [signal.raw_signal_id for signal in signals],
        "source_conversation_ids": unique_sorted([signal.conversation_id for signal in signals]),
        "source_chunk_ids": unique_sorted([signal.chunk_id for signal in signals]),
    }


def conflict_candidate_id(topic_key: str, signals: list[RawSignal]) -> str:
    return stable_hash(
        [
            topic_key,
            ",".join(sorted({signal.status for signal in signals})),
            ",".join(signal.raw_signal_id for signal in signals),
        ],
        "conflict",
    )


def detect_conflict_candidates(raw_signals: list[RawSignal]) -> list[dict[str, Any]]:
    by_topic: dict[str, list[RawSignal]] = {}
    topic_labels: dict[str, str] = {}
    for signal in raw_signals:
        if not signal.normalized_topic_key:
            continue
        by_topic.setdefault(signal.normalized_topic_key, []).append(signal)
        topic_labels.setdefault(signal.normalized_topic_key, signal.topic_key)

    conflicts: list[dict[str, Any]] = []
    for normalized_topic in sorted(by_topic):
        topic_signals = sorted(by_topic[normalized_topic], key=lambda signal: (signal.input_index, signal.raw_signal_id))
        statuses = {signal.status for signal in topic_signals if signal.status}
        if not any(pair.issubset(statuses) for pair in CONFLICT_STATUS_PAIRS):
            continue
        topic_key = topic_labels[normalized_topic]
        conflicts.append(
            {
                "conflict_id": conflict_candidate_id(topic_key, topic_signals),
                "topic_key": topic_key,
                "classification": "version_or_conflict_candidate",
                "claims": [
                    {
                        "raw_signal_id": signal.raw_signal_id,
                        "claim": signal.claim,
                        "status_hint": signal.status,
                    }
                    for signal in topic_signals
                ],
            }
        )
    return conflicts


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def process_signals(raw_signals_path: Path, out_dir: Path) -> dict[str, Any]:
    raw_signals, skipped_empty_ids, raw_count = load_raw_signals(raw_signals_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    groups, duplicate_links = dedupe_signals(raw_signals)
    deduped_rows = [deduped_row(group) for group in groups]
    conflict_candidates = detect_conflict_candidates(raw_signals)
    summary = {
        "raw_signal_count": raw_count,
        "deduped_signal_count": len(deduped_rows),
        "duplicate_link_count": len(duplicate_links),
        "conflict_candidate_count": len(conflict_candidates),
        "skipped_empty_claim_count": len(skipped_empty_ids),
        "skipped_empty_raw_signal_ids": skipped_empty_ids,
    }

    write_jsonl(out_dir / "deduped_signals.jsonl", deduped_rows)
    write_jsonl(out_dir / "duplicate_links.jsonl", duplicate_links)
    write_jsonl(out_dir / "conflict_candidates.jsonl", conflict_candidates)
    (out_dir / "dedupe_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deduplicate raw ChatGPT export signals into reviewable signal scaffolding.",
    )
    parser.add_argument("--raw-signals", required=True, help="Path to raw_signals.jsonl.")
    parser.add_argument("--out-dir", required=True, help="Directory that will receive dedupe review files.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = process_signals(Path(args.raw_signals), Path(args.out_dir))
    print(f"Read raw signals: {summary['raw_signal_count']}")
    print(f"Wrote deduped signals: {summary['deduped_signal_count']}")
    print(f"Duplicate links: {summary['duplicate_link_count']}")
    print(f"Conflict candidates: {summary['conflict_candidate_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
