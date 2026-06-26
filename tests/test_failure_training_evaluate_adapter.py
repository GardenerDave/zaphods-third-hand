import json
import subprocess
import sys

from local_harness.failure_training.evaluate_adapter import (
    build_evaluation_report,
    compare_numeric_metrics,
    default_evaluation_id,
    evaluation_markdown,
    numeric_metrics_from_summary,
    score_from_summary,
    verdict_from_delta,
    write_evaluation_report,
)


def test_score_from_summary_finds_top_level_score():
    assert score_from_summary({"overall_score": 0.7}) == 0.7
    assert score_from_summary({"score": 0.6}) == 0.6


def test_score_from_summary_finds_nested_score():
    assert score_from_summary({"metrics": {"accuracy": 0.8}}) == 0.8


def test_score_from_summary_ignores_booleans_and_missing_values():
    assert score_from_summary({"overall_score": True}) is None
    assert score_from_summary({"metrics": {"accuracy": "high"}}) is None


def test_numeric_metrics_from_summary_extracts_top_level_and_nested_metrics():
    metrics = numeric_metrics_from_summary(
        {
            "overall_score": 0.5,
            "ignored": "x",
            "passed": True,
            "metrics": {
                "routing": 0.8,
                "coding": 0.4,
            },
        }
    )

    assert metrics == {
        "overall_score": 0.5,
        "routing": 0.8,
        "coding": 0.4,
    }


def test_compare_numeric_metrics_reports_improvements_and_regressions():
    improvements, regressions = compare_numeric_metrics(
        {"metrics": {"json": 0.5, "routing": 1.0}},
        {"metrics": {"json": 0.75, "routing": 0.5}},
    )

    assert improvements == [
        {"metric": "json", "baseline": 0.5, "adapted": 0.75, "delta": 0.25}
    ]
    assert regressions == [
        {"metric": "routing", "baseline": 1.0, "adapted": 0.5, "delta": -0.5}
    ]


def test_verdict_from_delta_prefers_primary_score_delta():
    assert verdict_from_delta(0.5, 0.7, [], []) == "improved"
    assert verdict_from_delta(0.7, 0.5, [], []) == "regressed"
    assert verdict_from_delta(0.7, 0.7, [], []) == "no_change"


def test_verdict_from_delta_uses_metric_lists_when_primary_score_missing():
    assert verdict_from_delta(None, None, [{"metric": "x"}], []) == "improved"
    assert verdict_from_delta(None, None, [], [{"metric": "x"}]) == "regressed"
    assert verdict_from_delta(None, None, [{"metric": "x"}], [{"metric": "y"}]) == "mixed"
    assert verdict_from_delta(None, None, [], []) == "unknown"


def test_default_evaluation_id_is_stable():
    first = default_evaluation_id(
        cycle_id="cycle 1",
        adapter_id="adapter_1",
        baseline_run_id="base",
        adapted_run_id="adapted",
    )
    second = default_evaluation_id(
        cycle_id="cycle 1",
        adapter_id="adapter_1",
        baseline_run_id="base",
        adapted_run_id="adapted",
    )

    assert first.startswith("evaluation_cycle_1_")
    assert first == second


def test_build_evaluation_report_sets_verdict_and_metrics():
    report = build_evaluation_report(
        baseline_summary={"overall_score": 0.4, "metrics": {"json": 0.25}},
        adapted_summary={"overall_score": 0.9, "metrics": {"json": 1.0}},
        cycle_id="cycle_0001",
        adapter_id="adapter_1",
        base_model_id="tiny-model",
        target_capability="strict_json_contract",
        baseline_run_id="baseline",
        adapted_run_id="adapted",
    )

    assert report["status"] == "completed"
    assert report["verdict"] == "improved"
    assert report["metrics"]["baseline_score"] == 0.4
    assert report["metrics"]["adapted_score"] == 0.9
    assert report["metrics"]["delta"] == 0.5
    assert report["metrics"]["improvements"]


def test_evaluation_markdown_contains_core_summary():
    report = build_evaluation_report(
        baseline_summary={"overall_score": 0.4},
        adapted_summary={"overall_score": 0.9},
        cycle_id="cycle_0001",
        adapter_id="adapter_1",
        base_model_id="tiny-model",
        target_capability="strict_json_contract",
        baseline_run_id="baseline",
        adapted_run_id="adapted",
    )

    text = evaluation_markdown(report)

    assert "# Adapter Evaluation Report" in text
    assert "Verdict: `improved`" in text
    assert "Baseline score: `0.4`" in text
    assert "Adapted score: `0.9`" in text


def test_write_evaluation_report_outputs_json_jsonl_and_markdown(tmp_path):
    baseline_path = tmp_path / "baseline.json"
    adapted_path = tmp_path / "adapted.json"
    output_dir = tmp_path / "evaluation"

    baseline_path.write_text(json.dumps({"overall_score": 0.4}), encoding="utf-8")
    adapted_path.write_text(json.dumps({"overall_score": 0.9}), encoding="utf-8")

    report = write_evaluation_report(
        baseline_summary_path=baseline_path,
        adapted_summary_path=adapted_path,
        output_dir=output_dir,
        cycle_id="cycle_0001",
        adapter_id="adapter_1",
        base_model_id="tiny-model",
        target_capability="strict_json_contract",
        baseline_run_id="baseline",
        adapted_run_id="adapted",
    )

    saved = json.loads((output_dir / "evaluation_report.json").read_text(encoding="utf-8"))
    jsonl = (output_dir / "evaluation_report.jsonl").read_text(encoding="utf-8")
    markdown = (output_dir / "evaluation_report.md").read_text(encoding="utf-8")

    assert saved == report
    assert json.loads(jsonl) == report
    assert "Verdict: `improved`" in markdown


def test_evaluate_adapter_cli_writes_report_and_prints_summary(tmp_path):
    baseline_path = tmp_path / "baseline.json"
    adapted_path = tmp_path / "adapted.json"
    output_dir = tmp_path / "evaluation"

    baseline_path.write_text(json.dumps({"overall_score": 0.4}), encoding="utf-8")
    adapted_path.write_text(json.dumps({"overall_score": 0.9}), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "local_harness.failure_training.evaluate_adapter",
            "--baseline-summary",
            str(baseline_path),
            "--adapted-summary",
            str(adapted_path),
            "--output-dir",
            str(output_dir),
            "--cycle-id",
            "cycle_0001",
            "--adapter-id",
            "adapter_1",
            "--base-model-id",
            "tiny-model",
            "--target-capability",
            "strict_json_contract",
            "--baseline-run-id",
            "baseline",
            "--adapted-run-id",
            "adapted",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Evaluation report written:" in result.stdout
    assert "verdict=improved" in result.stdout
    assert (output_dir / "evaluation_report.json").exists()
    assert (output_dir / "evaluation_report.md").exists()
