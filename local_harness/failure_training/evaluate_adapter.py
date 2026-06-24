"""Compare baseline and adapted run summaries and write an evaluation report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .common import sha256_text, write_jsonl
from .status import utc_now_iso


SCORE_KEYS = (
    "overall_score",
    "score",
    "accuracy",
    "pass_rate",
    "success_rate",
)


def read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def numeric_value(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def score_from_summary(summary: dict[str, Any]) -> float | None:
    """Find a primary score in a summary object."""

    for key in SCORE_KEYS:
        score = numeric_value(summary.get(key))
        if score is not None:
            return score

    metrics = summary.get("metrics")
    if isinstance(metrics, dict):
        for key in SCORE_KEYS:
            score = numeric_value(metrics.get(key))
            if score is not None:
                return score

    return None


def numeric_metrics_from_summary(summary: dict[str, Any]) -> dict[str, float]:
    """Extract comparable numeric metrics from top level and metrics object."""

    metrics: dict[str, float] = {}

    for key, value in summary.items():
        numeric = numeric_value(value)
        if numeric is not None:
            metrics[key] = numeric

    nested = summary.get("metrics")
    if isinstance(nested, dict):
        for key, value in nested.items():
            numeric = numeric_value(value)
            if numeric is not None:
                metrics[key] = numeric

    return metrics


def compare_numeric_metrics(
    baseline_summary: dict[str, Any],
    adapted_summary: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return improvement and regression rows for shared numeric metrics.

    Higher values are treated as better. This is intended for score/pass-rate style
    metrics, not loss/perplexity metrics.
    """

    baseline_metrics = numeric_metrics_from_summary(baseline_summary)
    adapted_metrics = numeric_metrics_from_summary(adapted_summary)

    improvements: list[dict[str, Any]] = []
    regressions: list[dict[str, Any]] = []

    for metric in sorted(set(baseline_metrics) & set(adapted_metrics)):
        before = baseline_metrics[metric]
        after = adapted_metrics[metric]
        delta = after - before
        row = {
            "metric": metric,
            "baseline": before,
            "adapted": after,
            "delta": delta,
        }

        if delta > 0:
            improvements.append(row)
        elif delta < 0:
            regressions.append(row)

    return improvements, regressions


def verdict_from_delta(
    baseline_score: float | None,
    adapted_score: float | None,
    improvements: list[dict[str, Any]],
    regressions: list[dict[str, Any]],
) -> str:
    if baseline_score is None or adapted_score is None:
        if improvements and regressions:
            return "mixed"
        if improvements:
            return "improved"
        if regressions:
            return "regressed"
        return "unknown"

    delta = adapted_score - baseline_score
    if delta > 0:
        return "improved"
    if delta < 0:
        return "regressed"

    if improvements and regressions:
        return "mixed"
    return "no_change"


def default_evaluation_id(
    *,
    cycle_id: str,
    adapter_id: str,
    baseline_run_id: str,
    adapted_run_id: str,
) -> str:
    digest = sha256_text(f"{cycle_id}|{adapter_id}|{baseline_run_id}|{adapted_run_id}")[:12]
    safe_cycle = cycle_id.replace("/", "_").replace(" ", "_")
    return f"evaluation_{safe_cycle}_{digest}"


def build_evaluation_report(
    *,
    baseline_summary: dict[str, Any],
    adapted_summary: dict[str, Any],
    cycle_id: str,
    adapter_id: str,
    base_model_id: str,
    target_capability: str,
    baseline_run_id: str,
    adapted_run_id: str,
    adapted_model_id: str = "",
    notes: str = "",
    artifact_paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    baseline_score = score_from_summary(baseline_summary)
    adapted_score = score_from_summary(adapted_summary)
    delta = None
    if baseline_score is not None and adapted_score is not None:
        delta = adapted_score - baseline_score

    improvements, regressions = compare_numeric_metrics(baseline_summary, adapted_summary)
    verdict = verdict_from_delta(baseline_score, adapted_score, improvements, regressions)

    evaluation_id = default_evaluation_id(
        cycle_id=cycle_id,
        adapter_id=adapter_id,
        baseline_run_id=baseline_run_id,
        adapted_run_id=adapted_run_id,
    )

    return {
        "evaluation_id": evaluation_id,
        "cycle_id": cycle_id,
        "adapter_id": adapter_id,
        "created_at": utc_now_iso(),
        "base_model_id": base_model_id,
        "adapted_model_id": adapted_model_id,
        "baseline_run_id": baseline_run_id,
        "adapted_run_id": adapted_run_id,
        "target_capability": target_capability,
        "status": "completed",
        "verdict": verdict,
        "metrics": {
            "baseline_score": baseline_score,
            "adapted_score": adapted_score,
            "delta": delta,
            "improvements": improvements,
            "regressions": regressions,
        },
        "artifact_paths": artifact_paths or {},
        "notes": notes,
    }


def evaluation_markdown(report: dict[str, Any]) -> str:
    metrics = report["metrics"]

    lines = [
        "# Adapter Evaluation Report",
        "",
        f"- Evaluation ID: `{report['evaluation_id']}`",
        f"- Cycle ID: `{report['cycle_id']}`",
        f"- Adapter ID: `{report['adapter_id']}`",
        f"- Target capability: `{report['target_capability']}`",
        f"- Verdict: `{report['verdict']}`",
        f"- Baseline score: `{metrics['baseline_score']}`",
        f"- Adapted score: `{metrics['adapted_score']}`",
        f"- Delta: `{metrics['delta']}`",
        "",
        "## Improvements",
        "",
    ]

    if metrics["improvements"]:
        for row in metrics["improvements"]:
            lines.append(
                f"- `{row['metric']}`: {row['baseline']} -> {row['adapted']} "
                f"(delta {row['delta']})"
            )
    else:
        lines.append("- None recorded.")

    lines.extend(["", "## Regressions", ""])

    if metrics["regressions"]:
        for row in metrics["regressions"]:
            lines.append(
                f"- `{row['metric']}`: {row['baseline']} -> {row['adapted']} "
                f"(delta {row['delta']})"
            )
    else:
        lines.append("- None recorded.")

    lines.append("")
    return "\n".join(lines)


def write_evaluation_report(
    *,
    baseline_summary_path: str | Path,
    adapted_summary_path: str | Path,
    output_dir: str | Path,
    cycle_id: str,
    adapter_id: str,
    base_model_id: str,
    target_capability: str,
    baseline_run_id: str,
    adapted_run_id: str,
    adapted_model_id: str = "",
    notes: str = "",
) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    artifact_paths = {
        "baseline_summary": str(baseline_summary_path),
        "adapted_summary": str(adapted_summary_path),
        "evaluation_report": str(out / "evaluation_report.json"),
        "evaluation_report_markdown": str(out / "evaluation_report.md"),
    }

    report = build_evaluation_report(
        baseline_summary=read_json(baseline_summary_path),
        adapted_summary=read_json(adapted_summary_path),
        cycle_id=cycle_id,
        adapter_id=adapter_id,
        base_model_id=base_model_id,
        adapted_model_id=adapted_model_id,
        target_capability=target_capability,
        baseline_run_id=baseline_run_id,
        adapted_run_id=adapted_run_id,
        notes=notes,
        artifact_paths=artifact_paths,
    )

    write_json(out / "evaluation_report.json", report)
    write_jsonl(out / "evaluation_report.jsonl", [report])
    (out / "evaluation_report.md").write_text(
        evaluation_markdown(report),
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-summary", required=True)
    parser.add_argument("--adapted-summary", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--adapter-id", required=True)
    parser.add_argument("--base-model-id", required=True)
    parser.add_argument("--target-capability", required=True)
    parser.add_argument("--baseline-run-id", required=True)
    parser.add_argument("--adapted-run-id", required=True)
    parser.add_argument("--adapted-model-id", default="")
    parser.add_argument("--notes", default="")
    args = parser.parse_args(argv)

    report = write_evaluation_report(
        baseline_summary_path=args.baseline_summary,
        adapted_summary_path=args.adapted_summary,
        output_dir=args.output_dir,
        cycle_id=args.cycle_id,
        adapter_id=args.adapter_id,
        base_model_id=args.base_model_id,
        adapted_model_id=args.adapted_model_id,
        target_capability=args.target_capability,
        baseline_run_id=args.baseline_run_id,
        adapted_run_id=args.adapted_run_id,
        notes=args.notes,
    )

    print(
        "Evaluation report written: "
        f"verdict={report['verdict']} "
        f"baseline={report['metrics']['baseline_score']} "
        f"adapted={report['metrics']['adapted_score']} "
        f"delta={report['metrics']['delta']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
