"""Mix failure-curriculum JSONL files with explicit weighting.

This helper is model-free. It preserves input row order and does not shuffle,
train, promote, or publish adapters.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        raise ValueError(f"{p}: missing input file")

    rows: list[dict[str, Any]] = []
    with p.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{p}:{line_number}: invalid JSON: {exc.msg}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{p}:{line_number}: row must be a JSON object")
            rows.append(row)
    return rows


def write_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def mix_curriculum(
    *,
    base_train: str | Path,
    base_validation: str | Path,
    new_train: str | Path,
    new_validation: str | Path,
    new_weight: int,
    out_train: str | Path,
    out_validation: str | Path,
) -> dict[str, int]:
    if new_weight < 1:
        raise ValueError("--new-weight must be >= 1")

    base_train_rows = read_jsonl(base_train)
    base_validation_rows = read_jsonl(base_validation)
    new_train_rows = read_jsonl(new_train)
    new_validation_rows = read_jsonl(new_validation)

    mixed_train = base_train_rows + (new_train_rows * new_weight)
    mixed_validation = base_validation_rows + new_validation_rows

    write_jsonl(out_train, mixed_train)
    write_jsonl(out_validation, mixed_validation)

    return {
        "base_train": len(base_train_rows),
        "base_validation": len(base_validation_rows),
        "new_train": len(new_train_rows),
        "new_validation": len(new_validation_rows),
        "out_train": len(mixed_train),
        "out_validation": len(mixed_validation),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Mix base and new failure-curriculum JSONL files with weighting."
    )
    parser.add_argument("--base-train", required=True, type=Path)
    parser.add_argument("--base-validation", required=True, type=Path)
    parser.add_argument("--new-train", required=True, type=Path)
    parser.add_argument("--new-validation", required=True, type=Path)
    parser.add_argument("--new-weight", required=True, type=int)
    parser.add_argument("--out-train", required=True, type=Path)
    parser.add_argument("--out-validation", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        counts = mix_curriculum(
            base_train=args.base_train,
            base_validation=args.base_validation,
            new_train=args.new_train,
            new_validation=args.new_validation,
            new_weight=args.new_weight,
            out_train=args.out_train,
            out_validation=args.out_validation,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"read: {args.base_train} rows={counts['base_train']}")
    print(f"read: {args.base_validation} rows={counts['base_validation']}")
    print(f"read: {args.new_train} rows={counts['new_train']}")
    print(f"read: {args.new_validation} rows={counts['new_validation']}")
    print(f"new_weight: {args.new_weight}")
    print(f"wrote: {args.out_train} rows={counts['out_train']}")
    print(f"wrote: {args.out_validation} rows={counts['out_validation']}")
    print("warnings: none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
