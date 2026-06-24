import json
import subprocess
import sys

from local_harness.failure_training.common import read_jsonl
from local_harness.failure_training.compare_cycles import (
    compare_reports,
    comparison_markdown,
    report_row,
    sort_report_rows,
    write_comparison,
)


def report(evaluation_id, verdict, delta, baseline=0.5, adapted=0.5):
    return {
        "evaluation_id": evaluation_id,
        "cycle_id": f"cycle_{evaluation_id}",
        "adapter_id": f"adapter_{evaluation_id}",
        "target_capability": "strict_json_contract",
        "verdict": verdict,
        "metrics": {
            "baseline_score": baseline,
            "adapted_score": adapted,
            "delta": delta,
            "improvements": [{"metric": "json"}] if delta and delta > 0 else [],
            "regressions": [{"metric": "json"}] if delta and delta < 0 else [],
        },
    }


def test_report_row_extracts_summary_fields():
    row = report_row(report("eval_1", "improved", 0.5), source_path="eval.json")

    assert row["evaluation_id"] == "eval_1"
    assert row["cycle_id"] == "cycle_eval_1"
    assert row["adapter_id"] == "adapter_eval_1"
    assert row["verdict"] == "improved"
    assert row["delta"] == 0.5
    assert row["improvement_count"] == 1
    assert row["regression_count"] == 0
    assert row["source_path"] == "eval.json"


def test_sort_report_rows_ranks_improved_before_regressed():
    rows = [
        report_row(report("bad", "regressed", -0.2)),
        report_row(report("good", "improved", 0.2)),
        report_row(report("better", "improved", 0.5)),
    ]

    sorted_rows = sort_report_rows(rows)

    assert [row["evaluation_id"] for row in sorted_rows] == ["better", "good", "bad"]


def test_compare_reports_returns_counts_best_and_ranked_rows():
    summary = compare_reports(
        [
            report("eval_regressed", "regressed", -0.1),
            report("eval_improved", "improved", 0.4),
            report("eval_mixed", "mixed", 0.0),
        ],
        source_paths=["a.json", "b.json", "c.json"],
    )

    assert summary["report_count"] == 3
    assert summary["verdict_counts"] == {
        "regressed": 1,
        "improved": 1,
        "mixed": 1,
    }
    assert summary["best"]["evaluation_id"] == "eval_improved"
    assert summary["best"]["source_path"] == "b.json"


def test_comparison_markdown_contains_ranked_table():
    summary = compare_reports([report("eval_1", "improved", 0.5)])

    text = comparison_markdown(summary)

    assert "# Failure Curriculum Evaluation Comparison" in text
    assert "Reports compared: `1`" in text
    assert "| improved | 0.5 | `eval_1`" in text
    assert "## Best report" in text


def test_write_comparison_outputs_jsonl_and_markdown(tmp_path):
    report_a = tmp_path / "a.json"
    report_b = tmp_path / "b.json"
    output_dir = tmp_path / "comparison"

    report_a.write_text(json.dumps(report("eval_a", "improved", 0.25)), encoding="utf-8")
    report_b.write_text(json.dumps(report("eval_b", "regressed", -0.1)), encoding="utf-8")

    summary = write_comparison(report_paths=[report_a, report_b], output_dir=output_dir)

    assert summary["report_count"] == 2
    assert read_jsonl(output_dir / "comparison_summary.jsonl") == [summary]
    assert len(read_jsonl(output_dir / "comparison_rows.jsonl")) == 2
    assert (output_dir / "comparison_report.md").exists()


def test_compare_cycles_cli_writes_summary_and_prints_best(tmp_path):
    report_a = tmp_path / "a.json"
    report_b = tmp_path / "b.json"
    output_dir = tmp_path / "comparison"

    report_a.write_text(json.dumps(report("eval_a", "improved", 0.25)), encoding="utf-8")
    report_b.write_text(json.dumps(report("eval_b", "regressed", -0.1)), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "local_harness.failure_training.compare_cycles",
            "--reports",
            str(report_a),
            str(report_b),
            "--output-dir",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Comparison written:" in result.stdout
    assert "reports=2" in result.stdout
    assert "best=eval_a" in result.stdout
    assert (output_dir / "comparison_report.md").exists()
