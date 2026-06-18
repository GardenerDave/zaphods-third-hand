from __future__ import annotations

import json
from pathlib import Path

from local_harness.compare_model_auditions import (
    compare_cards,
    load_json,
    resolve_card_paths,
    write_comparison,
)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def make_card(
    *,
    model_id: str,
    run_id: str,
    overall: float,
    suite_scores: dict | None = None,
    metric_averages: dict | None = None,
    failure_modes: list[str] | None = None,
    runtime: dict | None = None,
) -> dict:
    return {
        "board_id": "local_baseline_board_v0",
        "run_id": run_id,
        "model_id": model_id,
        "overall": overall,
        "suite_scores": suite_scores or {},
        "metric_averages": metric_averages or {},
        "failure_modes": failure_modes or [],
        "runtime": runtime or {},
        "role_fit": {
            "status": "not_evaluated",
            "note": "Role eligibility is derived by later MTNG/ZTH policy layers.",
        },
    }


def test_compare_two_cards() -> None:
    small = make_card(
        model_id="small-model",
        run_id="small_run",
        overall=0.60,
        suite_scores={"routing_micro_v0": 0.80, "coding_micro_v0": 0.40},
        metric_averages={"json_parse": 1.0, "runtime": 1.0},
    )
    coder = make_card(
        model_id="coder-model",
        run_id="coder_run",
        overall=0.75,
        suite_scores={"routing_micro_v0": 0.70, "coding_micro_v0": 0.90},
        metric_averages={"json_parse": 0.9, "runtime": 0.7},
    )

    comparison = compare_cards([small, coder])

    assert comparison["card_count"] == 2
    assert comparison["rankings"]["overall"] == ["coder-model", "small-model"]
    assert comparison["rankings"]["routing_micro_v0"] == [
        "small-model",
        "coder-model",
    ]
    assert comparison["rankings"]["coding_micro_v0"] == [
        "coder-model",
        "small-model",
    ]


def test_compare_cards_with_missing_suite_scores() -> None:
    first = make_card(
        model_id="first-model",
        run_id="first_run",
        overall=0.80,
        suite_scores={"routing_micro_v0": 0.80},
    )
    second = make_card(
        model_id="second-model",
        run_id="second_run",
        overall=0.70,
        suite_scores={},
    )

    comparison = compare_cards([first, second])

    assert comparison["rankings"]["overall"] == ["first-model", "second-model"]
    assert comparison["rankings"]["routing_micro_v0"] == ["first-model"]


def test_cards_glob(tmp_path: Path) -> None:
    first = tmp_path / "a" / "board_capability_card.json"
    second = tmp_path / "b" / "board_capability_card.json"

    write_json(first, make_card(model_id="a-model", run_id="a", overall=0.5))
    write_json(second, make_card(model_id="b-model", run_id="b", overall=0.6))

    paths = resolve_card_paths(
        cards=None,
        cards_glob=str(tmp_path / "*" / "board_capability_card.json"),
    )

    assert paths == [first.resolve(), second.resolve()]


def test_writes_json_and_markdown(tmp_path: Path) -> None:
    card_path = tmp_path / "card.json"
    card = make_card(
        model_id="model-a",
        run_id="run-a",
        overall=0.9,
        suite_scores={"routing_micro_v0": 0.9},
        metric_averages={"json_parse": 1.0},
    )
    write_json(card_path, card)

    out_dir = tmp_path / "out"
    comparison = write_comparison(
        cards=[card],
        card_paths=[card_path],
        out_dir=out_dir,
    )

    written = load_json(out_dir / "comparison.json")
    markdown = (out_dir / "comparison.md").read_text(encoding="utf-8")

    assert written == comparison
    assert written["card_count"] == 1
    assert "# Model Audition Comparison" in markdown
    assert "model-a" in markdown
    assert "not production assignments" in markdown


def test_failure_mode_summary() -> None:
    first = make_card(
        model_id="first-model",
        run_id="first",
        overall=0.5,
        failure_modes=["json_parse_failed", "slow_decode"],
    )
    second = make_card(
        model_id="second-model",
        run_id="second",
        overall=0.6,
        failure_modes=["json_parse_failed"],
    )

    comparison = compare_cards([first, second])

    assert comparison["failure_mode_summary"] == {
        "json_parse_failed": ["first-model", "second-model"],
        "slow_decode": ["first-model"],
    }


def test_runtime_table_handles_missing_values(tmp_path: Path) -> None:
    first = make_card(
        model_id="first-model",
        run_id="first",
        overall=0.5,
        runtime={
            "total_wall_time_seconds": 100.0,
            "median_case_wall_time_seconds": 10.0,
        },
    )
    second = make_card(
        model_id="second-model",
        run_id="second",
        overall=0.6,
        runtime={},
    )

    out_dir = tmp_path / "out"
    comparison = write_comparison(
        cards=[first, second],
        card_paths=[],
        out_dir=out_dir,
    )

    markdown = (out_dir / "comparison.md").read_text(encoding="utf-8")

    assert comparison["runtime"][0]["total_wall_time_seconds"] == 100.0
    assert comparison["runtime"][1]["total_wall_time_seconds"] == 0.0
    assert "second-model" in markdown
    assert "| `second-model` | 0.000 | 0.000 |" in markdown
