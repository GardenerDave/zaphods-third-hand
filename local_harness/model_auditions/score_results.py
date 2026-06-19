#!/usr/bin/env python3
"""Score model audition JSONL responses and emit ranked summaries."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

if __package__ in {None, ""}:
    from scoring import score_record
else:
    from .scoring import score_record


def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc


def model_rollup(score_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in score_rows:
        grouped[row["model_key"]].append(row)

    rollups: list[dict[str, Any]] = []
    for model_key, rows in grouped.items():
        ratios = [r["score"] / r["max_score"] for r in rows if r.get("max_score")]
        json_rows = [r for r in rows if r.get("prompt_kind") == "json_route"]
        route_matches = [r["checks"].get("route_match") for r in json_rows]
        raw_json_valid = [r["checks"].get("raw_json_valid") for r in json_rows]
        markdown_leaks = [r["checks"].get("markdown_fence_leakage") for r in json_rows]
        schema_valid = [r["checks"].get("schema_valid") for r in json_rows]
        tps_values = [r["checks"].get("predicted_tokens_per_second") for r in rows]
        tps_values = [v for v in tps_values if isinstance(v, (int, float))]
        rollups.append(
            {
                "model_key": model_key,
                "avg_score_ratio": round(mean(ratios), 3) if ratios else 0,
                "tests": len(rows),
                "json_route_tests": len(json_rows),
                "route_match_rate": round(sum(bool(x) for x in route_matches) / len(route_matches), 3) if route_matches else None,
                "raw_json_rate": round(sum(bool(x) for x in raw_json_valid) / len(raw_json_valid), 3) if raw_json_valid else None,
                "schema_valid_rate": round(sum(bool(x) for x in schema_valid) / len(schema_valid), 3) if schema_valid else None,
                "markdown_fence_leaks": sum(bool(x) for x in markdown_leaks),
                "avg_predicted_tps": round(mean(tps_values), 3) if tps_values else None,
                "verdicts": {v: sum(1 for r in rows if r["verdict"] == v) for v in ["pass", "watch", "fail"]},
            }
        )
    return sorted(rollups, key=lambda r: (r["avg_score_ratio"], r.get("avg_predicted_tps") or 0), reverse=True)


def markdown_summary(score_rows: list[dict[str, Any]], rollups: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    lines.append("# Model Audition Summary")
    lines.append("")
    lines.append("Human review is still required. This harness scores probe behavior; it does not promote models into production roles.")
    lines.append("")
    lines.append("## Model rollup")
    lines.append("")
    lines.append("| Model | Avg score | Tests | Route match | Raw JSON | Schema valid | Fence leaks | Avg tok/s | Verdicts |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---|")
    for row in rollups:
        verdicts = ", ".join(f"{k}:{v}" for k, v in row["verdicts"].items())
        lines.append(
            "| {model_key} | {avg_score_ratio:.3f} | {tests} | {route_match_rate} | {raw_json_rate} | "
            "{schema_valid_rate} | {markdown_fence_leaks} | {avg_predicted_tps} | {verdicts} |".format(
                verdicts=verdicts,
                **row,
            )
        )
    lines.append("")
    lines.append("## Prompt-level results")
    lines.append("")
    lines.append("| Model | Prompt | Kind | Score | Verdict | Notes |")
    lines.append("|---|---|---|---:|---|---|")
    for row in sorted(score_rows, key=lambda r: (r["prompt_key"], r["model_key"])):
        notes = "; ".join(row.get("notes") or [])
        lines.append(
            f"| {row['model_key']} | {row['prompt_key']} | {row['prompt_kind']} | "
            f"{row['score']}/{row['max_score']} | {row['verdict']} | {notes} |"
        )
    lines.append("")
    lines.append("## Known failure modes tracked")
    lines.append("")
    lines.append("- Empty `content` because a model spent its budget in `reasoning_content`.")
    lines.append("- Markdown-fenced JSON despite instructions to return only raw JSON.")
    lines.append("- Schema type drift such as `confidence: \"high\"` instead of a number.")
    lines.append("- Correctly shaped JSON with the wrong route.")
    lines.append("- Structured reports that invent file paths.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="Run directory containing responses.jsonl, or path to a responses JSONL file.")
    args = parser.parse_args()

    run_path = Path(args.run).expanduser()
    response_path = run_path if run_path.is_file() else run_path / "responses.jsonl"
    out_dir = response_path.parent

    scores = [score_record(record).to_dict() for record in iter_jsonl(response_path)]
    rollups = model_rollup(scores)

    scores_path = out_dir / "scores.jsonl"
    with scores_path.open("w", encoding="utf-8") as handle:
        for row in scores:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    rollup_path = out_dir / "rollup.json"
    rollup_path.write_text(json.dumps(rollups, indent=2), encoding="utf-8")

    summary_path = out_dir / "summary.md"
    summary_path.write_text(markdown_summary(scores, rollups), encoding="utf-8")

    print(f"WROTE: {scores_path}")
    print(f"WROTE: {rollup_path}")
    print(f"WROTE: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
