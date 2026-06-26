"""Write a compact supervised failure-curriculum round report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


BOUNDARY = (
    "This report is supervised evidence. It does not establish deployment "
    "readiness, autonomous capability, or authority to deploy the adapter "
    "without operator review."
)


def read_metrics_json(path: str | Path) -> str:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: metrics JSON must be an object")

    lines = ["| Metric | Count |", "|---|---:|"]
    for key in sorted(payload):
        lines.append(f"| {key} | {payload[key]} |")
    return "\n".join(lines)


def read_metrics_md(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8").strip()


def render_report(
    *,
    run_label: str,
    adapter_name: str,
    dataset_name: str,
    base_model: str,
    train_rows: int,
    validation_rows: int,
    final_eval_loss: str | None,
    summary: str,
    metrics_text: str,
) -> str:
    loss_text = final_eval_loss if final_eval_loss is not None else "not recorded"
    return "\n".join(
        [
            f"# Failure-Curriculum Round Report: {run_label}",
            "",
            "## Summary",
            "",
            summary,
            "",
            "## Setup",
            "",
            f"- Adapter: `{adapter_name}`",
            f"- Dataset: `{dataset_name}`",
            f"- Base model: `{base_model}`",
            f"- Train rows: {train_rows}",
            f"- Validation rows: {validation_rows}",
            f"- Final eval loss: {loss_text}",
            "",
            "## Metrics",
            "",
            metrics_text,
            "",
            "## Interpretation",
            "",
            "- TODO: summarize what changed relative to the base model.",
            "- TODO: distinguish behavior improvement from loss-only movement.",
            "",
            "## Remaining Failures",
            "",
            "- TODO: list persistent miss classes.",
            "",
            "## Next Recommendation",
            "",
            "- TODO: record whether to stop, add review tooling, or build a targeted next curriculum.",
            "",
            "## Safety Boundary",
            "",
            BOUNDARY,
            "",
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Write a compact supervised failure-curriculum round report."
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--run-label", required=True)
    parser.add_argument("--adapter-name", required=True)
    parser.add_argument("--dataset-name", required=True)
    parser.add_argument("--base-model", required=True)
    parser.add_argument("--train-rows", required=True, type=int)
    parser.add_argument("--validation-rows", required=True, type=int)
    parser.add_argument("--final-eval-loss")
    parser.add_argument("--metrics-json", type=Path)
    parser.add_argument("--metrics-md", type=Path)
    parser.add_argument("--summary", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.metrics_json and args.metrics_md:
        parser.error("use only one of --metrics-json or --metrics-md")

    try:
        if args.metrics_json:
            metrics_text = read_metrics_json(args.metrics_json)
            metrics_source = args.metrics_json
        elif args.metrics_md:
            metrics_text = read_metrics_md(args.metrics_md)
            metrics_source = args.metrics_md
        else:
            metrics_text = "Metrics not provided."
            metrics_source = None
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1

    text = render_report(
        run_label=args.run_label,
        adapter_name=args.adapter_name,
        dataset_name=args.dataset_name,
        base_model=args.base_model,
        train_rows=args.train_rows,
        validation_rows=args.validation_rows,
        final_eval_loss=args.final_eval_loss,
        summary=args.summary,
        metrics_text=metrics_text,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")

    if metrics_source:
        print(f"read: {metrics_source}")
    else:
        print("read: no metrics file")
    print(f"wrote: {args.output}")
    print(f"train_rows: {args.train_rows}")
    print(f"validation_rows: {args.validation_rows}")
    print("warnings: none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
