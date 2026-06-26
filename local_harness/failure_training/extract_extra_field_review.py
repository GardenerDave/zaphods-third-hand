"""Extract adapter rows with extra top-level fields into Markdown review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_json_value(value: Any) -> Any | None:
    if not isinstance(value, str):
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def read_eval_rows(path: str | Path) -> list[dict[str, Any]]:
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
            for key in ("target", "adapter_output"):
                if key not in row:
                    raise ValueError(f"{p}:{line_number}: missing required field {key!r}")
            if parse_json_value(row["target"]) is None:
                raise ValueError(f"{p}:{line_number}: target must be valid JSON text")
            rows.append(row)
    return rows


def render_review(rows: list[dict[str, Any]], *, source_path: str | Path) -> tuple[str, int]:
    lines = [
        "# Extra-Field Leak Review",
        "",
        f"Source: `{source_path}`",
        "",
    ]
    count = 0

    for row in rows:
        target = parse_json_value(row["target"])
        adapter = parse_json_value(row["adapter_output"])
        if not isinstance(target, dict) or not isinstance(adapter, dict):
            continue

        extra = sorted(set(adapter) - set(target))
        if not extra:
            continue

        count += 1
        lines.append(f"## Row {row.get('index', count)}")
        lines.append("")
        lines.append(f"Extra fields: `{extra}`")
        lines.append("")
        lines.append("Target:")
        lines.append("```json")
        lines.append(json.dumps(target, ensure_ascii=False, indent=2))
        lines.append("```")
        lines.append("")
        lines.append("Adapter:")
        lines.append("```json")
        lines.append(json.dumps(adapter, ensure_ascii=False, indent=2))
        lines.append("```")
        lines.append("")
        lines.append("Review:")
        lines.append("- classification: TODO")
        lines.append("- likely cause: TODO")
        lines.append("- keep for next curriculum: TODO")
        lines.append("- corrected target needed: TODO")
        lines.append("")

    return "\n".join(lines), count


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract adapter outputs that add extra top-level fields."
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        rows = read_eval_rows(args.input)
        text, count = render_review(rows, source_path=args.input)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(f"read: {args.input} rows={len(rows)}")
    print(f"wrote: {args.output}")
    print(f"extra_field_rows: {count}")
    print("warnings: none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
