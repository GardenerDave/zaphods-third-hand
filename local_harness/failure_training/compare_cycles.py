"""Compare failure curriculum evaluation reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .common import write_jsonl


VERDICT_RANK = {
    "improved": 4,
    "mixed": 3,
    "no_change": 2,
    "unknown": 1,
    "regressed": 0,
}


def read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def report_row(report: dict[str, Any], *, source_path: str | Path = "") -> dict[str, Any]:
    metrics = report.get("metrics", {})
    if not isinstance(metrics, dict):
        metrics = {}

    return {
        "evaluation_id": report.get("evaluation_id", ""),
        "cycle_id": report.get("cycle_id", ""),
        "adapter_id": report.get("adapter_id", ""),
        "target_capability": report.get("target_capability", ""),
        "verdict": report.get("verdict", "unknown"),
        "baseline_score": metrics.get("baseline_score"),
        "adapted_score": metrics.get("adapted_score"),
        "delta": metrics.get("delta"),
        "improvement_count": len(metrics.get("improvements", []) or []),
        "regression_count": len(metrics.get("regressions", []) or []),
        "source_path": str(source_path),
    }


def sort_report_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            VERDICT_RANK.get(str(row.get("verdict")), 1),
            row.get("delta") if isinstance(row.get("delta"), int | float) else float("-inf"),
            str(row.get("evaluation_id")),
        ),
        reverse=True,
    )


def compare_reports(reports: list[dict[str, Any]], *, source_paths: list[str] | None = None) -> dict[str, Any]:
    if source_paths is None:
        source_paths = [""] * len(reports)

    rows = [
        report_row(report, source_path=source_paths[index] if index < len(source_paths) else "")
        for index, report in enumerate(reports)
    ]
    sorted_rows = sort_report_rows(rows)

    verdict_counts: dict[str, int] = {}
    for row in rows:
        verdict = str(row.get("verdict", "unknown"))
        verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1

    best = sorted_rows[0] if sorted_rows else None

    return {
        "report_count": len(rows),
        "verdict_counts": verdict_counts,
        "best": best,
        "rows": sorted_rows,
    }


def comparison_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Failure Curriculum Evaluation Comparison",
        "",
        f"- Reports compared: `{summary['report_count']}`",
        "",
        "## Verdict counts",
        "",
    ]

    verdict_counts = summary["verdict_counts"]
    if verdict_counts:
        for verdict in sorted(verdict_counts):
            lines.append(f"- `{verdict}`: {verdict_counts[verdict]}")
    else:
        lines.append("- None.")

    lines.extend(
        [
            "",
            "## Ranked reports",
            "",
            "| verdict | delta | evaluation_id | cycle_id | adapter_id | target_capability |",
            "| --- | ---: | --- | --- | --- | --- |",
        ]
    )

    for row in summary["rows"]:
        lines.append(
            "| {verdict} | {delta} | `{evaluation_id}` | `{cycle_id}` | `{adapter_id}` | `{target_capability}` |".format(
                verdict=row["verdict"],
                delta=row["delta"],
                evaluation_id=row["evaluation_id"],
                cycle_id=row["cycle_id"],
                adapter_id=row["adapter_id"],
                target_capability=row["target_capability"],
            )
        )

    if summary["best"]:
        best = summary["best"]
        lines.extend(
            [
                "",
                "## Best report",
                "",
                f"- Evaluation ID: `{best['evaluation_id']}`",
                f"- Verdict: `{best['verdict']}`",
                f"- Delta: `{best['delta']}`",
                f"- Source: `{best['source_path']}`",
            ]
        )

    lines.append("")
    return "\n".join(lines)


def write_comparison(
    *,
    report_paths: list[str | Path],
    output_dir: str | Path,
) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    reports = [read_json(path) for path in report_paths]
    summary = compare_reports(reports, source_paths=[str(path) for path in report_paths])

    write_jsonl(out / "comparison_summary.jsonl", [summary])
    write_jsonl(out / "comparison_rows.jsonl", summary["rows"])
    (out / "comparison_report.md").write_text(
        comparison_markdown(summary),
        encoding="utf-8",
    )

    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports", nargs="+", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    summary = write_comparison(
        report_paths=args.reports,
        output_dir=args.output_dir,
    )

    best = summary["best"] or {}
    print(
        "Comparison written: "
        f"reports={summary['report_count']} "
        f"best={best.get('evaluation_id', '')} "
        f"verdict={best.get('verdict', 'unknown')} "
        f"delta={best.get('delta')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
