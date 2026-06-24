"""Export reviewed training rows into chat-style SFT JSONL."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .common import read_jsonl, write_jsonl


def normalize_message(message: dict[str, Any]) -> dict[str, str]:
    role = message.get("role")
    content = message.get("content")

    if role not in {"system", "user", "assistant"}:
        raise ValueError(f"unsupported message role: {role!r}")

    if not isinstance(content, str) or not content.strip():
        raise ValueError("message content must be a non-empty string")

    return {
        "role": role,
        "content": content,
    }


def normalize_sft_row(row: dict[str, Any], *, include_metadata: bool = True) -> dict[str, Any]:
    messages = row.get("messages")

    if not isinstance(messages, list) or len(messages) < 2:
        raise ValueError("SFT row must contain at least two messages")

    normalized: dict[str, Any] = {
        "messages": [normalize_message(message) for message in messages],
    }

    if include_metadata and isinstance(row.get("metadata"), dict):
        normalized["metadata"] = row["metadata"]

    return normalized


def export_sft_rows(
    rows: list[dict[str, Any]],
    *,
    include_metadata: bool = True,
) -> list[dict[str, Any]]:
    return [
        normalize_sft_row(row, include_metadata=include_metadata)
        for row in rows
    ]


def export_sft_jsonl(
    input_path: str | Path,
    output_path: str | Path,
    *,
    include_metadata: bool = True,
) -> list[dict[str, Any]]:
    exported = export_sft_rows(
        read_jsonl(input_path),
        include_metadata=include_metadata,
    )
    write_jsonl(output_path, exported)
    return exported


def write_sft_exports(
    *,
    train_path: str | Path,
    validation_path: str | Path,
    output_dir: str | Path,
    include_metadata: bool = True,
) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    train_rows = export_sft_jsonl(
        train_path,
        out / "sft_train.jsonl",
        include_metadata=include_metadata,
    )
    validation_rows = export_sft_jsonl(
        validation_path,
        out / "sft_validation.jsonl",
        include_metadata=include_metadata,
    )

    manifest = {
        "sft_train_path": "sft_train.jsonl",
        "sft_validation_path": "sft_validation.jsonl",
        "train_count": len(train_rows),
        "validation_count": len(validation_rows),
        "include_metadata": include_metadata,
        "format": "chat_messages_jsonl",
    }
    write_jsonl(out / "sft_manifest.jsonl", [manifest])
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", required=True, help="train.jsonl from dataset split")
    parser.add_argument("--validation", required=True, help="validation.jsonl from dataset split")
    parser.add_argument("--output-dir", required=True, help="SFT export output directory")
    parser.add_argument(
        "--strip-metadata",
        action="store_true",
        help="Write only messages, omitting metadata",
    )
    args = parser.parse_args(argv)

    write_sft_exports(
        train_path=args.train,
        validation_path=args.validation,
        output_dir=args.output_dir,
        include_metadata=not args.strip_metadata,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
