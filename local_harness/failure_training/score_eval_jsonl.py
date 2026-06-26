"""Score base-vs-adapter evaluation JSONL for structured-output behavior."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


METRIC_KEYS = (
    "base_valid",
    "adapter_valid",
    "base_key_match",
    "adapter_key_match",
    "base_exact",
    "adapter_exact",
    "base_extra_fields",
    "adapter_extra_fields",
    "base_type_match",
    "adapter_type_match",
    "base_array_count_match",
    "adapter_array_count_match",
)


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
            for key in ("target", "base_output", "adapter_output"):
                if key not in row:
                    raise ValueError(f"{p}:{line_number}: missing required field {key!r}")
            if parse_json_value(row["target"]) is None:
                raise ValueError(f"{p}:{line_number}: target must be valid JSON text")
            rows.append(row)
    return rows


def array_count_match(target: Any, output: Any) -> bool:
    if not isinstance(target, dict) or not isinstance(output, dict):
        return False
    for key, value in target.items():
        if isinstance(value, list):
            if key not in output or not isinstance(output[key], list):
                return False
            if len(output[key]) != len(value):
                return False
    return True


def type_match(target: Any, output: Any) -> bool:
    if not isinstance(target, dict) or not isinstance(output, dict):
        return False
    return all(key in output and type(output[key]) is type(value) for key, value in target.items())


def score_rows(rows: list[dict[str, Any]]) -> dict[str, int]:
    metrics = {key: 0 for key in METRIC_KEYS}

    for row in rows:
        target = parse_json_value(row["target"])
        base = parse_json_value(row["base_output"])
        adapter = parse_json_value(row["adapter_output"])

        if base is not None:
            metrics["base_valid"] += 1
        if adapter is not None:
            metrics["adapter_valid"] += 1

        if isinstance(target, dict) and isinstance(base, dict):
            if set(base) == set(target):
                metrics["base_key_match"] += 1
            if set(base) - set(target):
                metrics["base_extra_fields"] += 1
            if type_match(target, base):
                metrics["base_type_match"] += 1
            if array_count_match(target, base):
                metrics["base_array_count_match"] += 1

        if isinstance(target, dict) and isinstance(adapter, dict):
            if set(adapter) == set(target):
                metrics["adapter_key_match"] += 1
            if set(adapter) - set(target):
                metrics["adapter_extra_fields"] += 1
            if type_match(target, adapter):
                metrics["adapter_type_match"] += 1
            if array_count_match(target, adapter):
                metrics["adapter_array_count_match"] += 1

        if base == target:
            metrics["base_exact"] += 1
        if adapter == target:
            metrics["adapter_exact"] += 1

    return metrics


def render_markdown(metrics: dict[str, int], row_count: int, *, source_path: str | Path) -> str:
    lines = [
        "# Failure-Curriculum Evaluation Metrics",
        "",
        f"Source: `{source_path}`",
        f"Rows: {row_count}",
        "",
        "| Metric | Count |",
        "|---|---:|",
    ]
    for key in METRIC_KEYS:
        lines.append(f"| {key} | {metrics[key]}/{row_count} |")
    lines.extend(
        [
            "",
            "These metrics are supervised evidence. They do not promote, route, rank,",
            "approve, or deploy an adapter.",
            "",
        ]
    )
    return "\n".join(lines)


def print_metrics(metrics: dict[str, int], row_count: int, *, source_path: str | Path) -> None:
    print(f"read: {source_path}")
    print(f"rows: {row_count}")
    for key in METRIC_KEYS:
        print(f"{key}: {metrics[key]}/{row_count}")
    print("warnings: none")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Score base-vs-adapter evaluation JSONL mechanically."
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-md", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        rows = read_eval_rows(args.input)
        metrics = score_rows(rows)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    print_metrics(metrics, len(rows), source_path=args.input)
    if args.output_md:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(
            render_markdown(metrics, len(rows), source_path=args.input),
            encoding="utf-8",
        )
        print(f"wrote: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
