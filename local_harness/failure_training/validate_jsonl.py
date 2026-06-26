"""Validate failure-curriculum JSONL files.

This is a model-free helper. It checks file shape only; it does not train,
evaluate, promote, or publish adapters.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ValidationResult:
    path: Path
    row_count: int
    assistant_json_count: int
    assistant_non_json_count: int
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


def _line_error(path: Path, line_number: int, message: str) -> str:
    return f"{path}:{line_number}: {message}"


def validate_file(path: str | Path, *, require_assistant_json: bool = False) -> ValidationResult:
    p = Path(path)
    errors: list[str] = []
    warnings: list[str] = []
    row_count = 0
    assistant_json_count = 0
    assistant_non_json_count = 0

    if not p.exists():
        return ValidationResult(
            path=p,
            row_count=0,
            assistant_json_count=0,
            assistant_non_json_count=0,
            errors=(f"{p}: missing input file",),
            warnings=(),
        )

    with p.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            stripped = line.strip()
            if not stripped:
                continue

            row_count += 1
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError as exc:
                errors.append(_line_error(p, line_number, f"invalid JSON: {exc.msg}"))
                continue

            if not isinstance(row, dict):
                errors.append(_line_error(p, line_number, "row must be a JSON object"))
                continue

            messages = row.get("messages")
            if not isinstance(messages, list) or not messages:
                errors.append(_line_error(p, line_number, "messages must be a non-empty list"))
                continue

            final = messages[-1]
            if not isinstance(final, dict):
                errors.append(_line_error(p, line_number, "final message must be an object"))
                continue

            if final.get("role") != "assistant":
                errors.append(_line_error(p, line_number, "final message role must be assistant"))
                continue

            content = final.get("content")
            if not isinstance(content, str):
                errors.append(_line_error(p, line_number, "final assistant content must be a string"))
                continue

            try:
                json.loads(content)
            except json.JSONDecodeError:
                assistant_non_json_count += 1
                if require_assistant_json:
                    errors.append(
                        _line_error(
                            p,
                            line_number,
                            "final assistant content is not valid JSON",
                        )
                    )
            else:
                assistant_json_count += 1

    if row_count == 0:
        warnings.append(f"{p}: no non-empty rows found")

    return ValidationResult(
        path=p,
        row_count=row_count,
        assistant_json_count=assistant_json_count,
        assistant_non_json_count=assistant_non_json_count,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def print_result(result: ValidationResult, *, quiet: bool = False) -> None:
    if not quiet:
        print(f"read: {result.path}")
        print(f"rows: {result.row_count}")
        print(f"assistant_json_parseable: {result.assistant_json_count}")
        print(f"assistant_non_json: {result.assistant_non_json_count}")

    for warning in result.warnings:
        print(f"WARNING: {warning}")

    for error in result.errors:
        print(f"ERROR: {error}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate failure-curriculum training or validation JSONL files."
    )
    parser.add_argument("--train", type=Path, help="Training JSONL path.")
    parser.add_argument("--validation", type=Path, help="Validation JSONL path.")
    parser.add_argument("--input", type=Path, help="Single JSONL input path.")
    parser.add_argument(
        "--require-assistant-json",
        action="store_true",
        help="Require the final assistant message content to parse as JSON.",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress success details.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    paths = [p for p in (args.input, args.train, args.validation) if p is not None]
    if not paths:
        parser.error("provide at least one of --input, --train, or --validation")

    results = [
        validate_file(path, require_assistant_json=args.require_assistant_json)
        for path in paths
    ]

    for index, result in enumerate(results):
        if index and not args.quiet:
            print("")
        print_result(result, quiet=args.quiet)

    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
