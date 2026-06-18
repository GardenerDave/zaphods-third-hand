"""Compare model audition board capability cards."""

from __future__ import annotations

import argparse
import glob
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def card_model_id(card: dict[str, Any]) -> str:
    return str(card.get("model_id", "unknown_model"))


def card_board_id(card: dict[str, Any]) -> str:
    return str(card.get("board_id", "unknown_board"))


def resolve_card_paths(
    *,
    cards: list[str] | None,
    cards_glob: str | None,
) -> list[Path]:
    resolved: list[Path] = []

    for card in cards or []:
        resolved.append(Path(card).expanduser().resolve())

    if cards_glob:
        for match in sorted(glob.glob(cards_glob)):
            resolved.append(Path(match).expanduser().resolve())

    deduped: list[Path] = []
    seen: set[Path] = set()

    for path in resolved:
        if path not in seen:
            seen.add(path)
            deduped.append(path)

    if not deduped:
        raise ValueError("No capability cards provided. Use --cards or --cards-glob.")

    return deduped


def rank_cards_by_value(
    cards: list[dict[str, Any]],
    value_fn,
) -> list[str]:
    ranked = sorted(
        cards,
        key=lambda card: value_fn(card),
        reverse=True,
    )
    return [card_model_id(card) for card in ranked]


def compare_cards(
    cards: list[dict[str, Any]],
    *,
    input_paths: list[Path] | None = None,
) -> dict[str, Any]:
    input_paths = input_paths or []

    models = [
        {
            "model_id": card_model_id(card),
            "board_id": card_board_id(card),
            "run_id": str(card.get("run_id", "")),
            "overall": safe_float(card.get("overall")),
        }
        for card in cards
    ]

    suite_ids = sorted(
        {
            suite_id
            for card in cards
            for suite_id in (card.get("suite_scores") or {}).keys()
        }
    )
    metric_ids = sorted(
        {
            metric_id
            for card in cards
            for metric_id in (card.get("metric_averages") or {}).keys()
        }
    )

    rankings: dict[str, list[str]] = {
        "overall": rank_cards_by_value(
            cards,
            lambda card: safe_float(card.get("overall")),
        )
    }

    for suite_id in suite_ids:
        cards_with_suite = [
            card for card in cards if suite_id in (card.get("suite_scores") or {})
        ]
        rankings[suite_id] = rank_cards_by_value(
            cards_with_suite,
            lambda card, suite_id=suite_id: safe_float(
                (card.get("suite_scores") or {}).get(suite_id)
            ),
        )

    metric_rankings: dict[str, list[str]] = {}

    for metric_id in metric_ids:
        cards_with_metric = [
            card for card in cards if metric_id in (card.get("metric_averages") or {})
        ]
        metric_rankings[metric_id] = rank_cards_by_value(
            cards_with_metric,
            lambda card, metric_id=metric_id: safe_float(
                (card.get("metric_averages") or {}).get(metric_id)
            ),
        )

    failure_mode_summary: dict[str, list[str]] = {}

    for card in cards:
        model_id = card_model_id(card)
        for mode in card.get("failure_modes", []) or []:
            failure_mode_summary.setdefault(str(mode), []).append(model_id)

    runtime_rows = [
        {
            "model_id": card_model_id(card),
            "total_wall_time_seconds": safe_float(
                (card.get("runtime") or {}).get("total_wall_time_seconds")
            ),
            "median_case_wall_time_seconds": safe_float(
                (card.get("runtime") or {}).get("median_case_wall_time_seconds")
            ),
        }
        for card in cards
    ]

    return {
        "created_at": utc_now_iso(),
        "card_count": len(cards),
        "input_cards": [path.as_posix() for path in input_paths],
        "models": models,
        "rankings": rankings,
        "metric_rankings": metric_rankings,
        "failure_mode_summary": {
            mode: sorted(set(model_ids))
            for mode, model_ids in sorted(failure_mode_summary.items())
        },
        "runtime": runtime_rows,
    }


def markdown_table_row(values: list[Any]) -> str:
    return "| " + " | ".join(str(value) for value in values) + " |"


def comparison_markdown(comparison: dict[str, Any], cards: list[dict[str, Any]]) -> str:
    suite_ids = sorted(
        {
            suite_id
            for card in cards
            for suite_id in (card.get("suite_scores") or {}).keys()
        }
    )
    metric_ids = sorted(
        {
            metric_id
            for card in cards
            for metric_id in (card.get("metric_averages") or {}).keys()
        }
    )

    lines = [
        "# Model Audition Comparison",
        "",
        "This report compares existing board capability cards. It does not rerun models and does not assign production roles.",
        "",
        "## Input cards",
        "",
    ]

    for path in comparison.get("input_cards", []):
        lines.append(f"- `{path}`")

    lines.extend(
        [
            "",
            "## Overall ranking",
            "",
            "| Rank | Model | Board | Overall |",
            "|---:|---|---|---:|",
        ]
    )

    ranked_models = comparison["rankings"].get("overall", [])
    model_lookup = {model["model_id"]: model for model in comparison["models"]}

    for index, model_id in enumerate(ranked_models, start=1):
        model = model_lookup[model_id]
        lines.append(
            markdown_table_row(
                [
                    index,
                    f"`{model_id}`",
                    model["board_id"],
                    f"{safe_float(model.get('overall')):.3f}",
                ]
            )
        )

    lines.extend(["", "## Suite scores", ""])

    if suite_ids:
        lines.append(
            markdown_table_row(["Model", *suite_ids])
        )
        lines.append(
            markdown_table_row(["---", *["---:" for _ in suite_ids]])
        )

        for card in cards:
            suite_scores = card.get("suite_scores") or {}
            row = [f"`{card_model_id(card)}`"]
            for suite_id in suite_ids:
                value = suite_scores.get(suite_id)
                row.append("—" if value is None else f"{safe_float(value):.3f}")
            lines.append(markdown_table_row(row))
    else:
        lines.append("No suite scores found.")

    lines.extend(["", "## Metric averages", ""])

    if metric_ids:
        lines.append(markdown_table_row(["Model", *metric_ids]))
        lines.append(markdown_table_row(["---", *["---:" for _ in metric_ids]]))

        for card in cards:
            metric_averages = card.get("metric_averages") or {}
            row = [f"`{card_model_id(card)}`"]
            for metric_id in metric_ids:
                value = metric_averages.get(metric_id)
                row.append("—" if value is None else f"{safe_float(value):.3f}")
            lines.append(markdown_table_row(row))
    else:
        lines.append("No metric averages found.")

    lines.extend(
        [
            "",
            "## Runtime",
            "",
            "| Model | Total wall time seconds | Median case wall time seconds |",
            "|---|---:|---:|",
        ]
    )

    for row in comparison.get("runtime", []):
        lines.append(
            markdown_table_row(
                [
                    f"`{row['model_id']}`",
                    f"{safe_float(row.get('total_wall_time_seconds')):.3f}",
                    f"{safe_float(row.get('median_case_wall_time_seconds')):.3f}",
                ]
            )
        )

    lines.extend(["", "## Failure mode summary", ""])

    failure_mode_summary = comparison.get("failure_mode_summary", {})
    if failure_mode_summary:
        for mode, model_ids in failure_mode_summary.items():
            lines.append(f"- `{mode}`: " + ", ".join(f"`{model}`" for model in model_ids))
    else:
        lines.append("No failure modes recorded.")

    lines.extend(
        [
            "",
            "## Notes / caveats",
            "",
            "- These are potential fit signals, not production assignments.",
            "- Missing suite or metric scores are shown as absent rather than scored as zero.",
            "- Use constrained follow-up testing before making model-role decisions.",
            "",
        ]
    )

    return "\n".join(lines)


def write_comparison(
    *,
    cards: list[dict[str, Any]],
    card_paths: list[Path],
    out_dir: Path,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)

    comparison = compare_cards(cards, input_paths=card_paths)

    write_json(out_dir / "comparison.json", comparison)
    (out_dir / "comparison.md").write_text(
        comparison_markdown(comparison, cards),
        encoding="utf-8",
    )

    return comparison


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("--cards", nargs="*")
    parser.add_argument("--cards-glob")
    parser.add_argument("--out-dir", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        card_paths = resolve_card_paths(cards=args.cards, cards_glob=args.cards_glob)
        cards = [load_json(path) for path in card_paths]
        write_comparison(
            cards=cards,
            card_paths=card_paths,
            out_dir=Path(args.out_dir).expanduser().resolve(),
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
