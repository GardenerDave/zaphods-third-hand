import json
import subprocess
import sys
from pathlib import Path

from local_harness.failure_training.score_eval_jsonl import read_eval_rows, score_rows


ROOT = Path(__file__).resolve().parents[1]


SCRIPTS = [
    ROOT / "local_harness/failure_training/validate_jsonl.py",
    ROOT / "local_harness/failure_training/mix_curriculum.py",
    ROOT / "local_harness/failure_training/score_eval_jsonl.py",
    ROOT / "local_harness/failure_training/extract_non_exact_review.py",
    ROOT / "local_harness/failure_training/extract_extra_field_review.py",
    ROOT / "local_harness/failure_training/write_round_report.py",
]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def run_script(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def training_row(assistant_content: str = '{"accepted":false}') -> dict:
    return {
        "messages": [
            {"role": "system", "content": "Return only valid JSON."},
            {"role": "user", "content": "Return accepted false."},
            {"role": "assistant", "content": assistant_content},
        ],
        "metadata": {"curriculum": "test", "failure_mode": "test"},
    }


def eval_rows() -> list[dict]:
    return [
        {
            "index": 1,
            "target": '{"accepted":false}',
            "base_output": "not json",
            "adapter_output": '{"accepted":false}',
        },
        {
            "index": 2,
            "target": '{"items":[1,2],"count":2}',
            "base_output": '{"items":[1],"count":2,"extra":true}',
            "adapter_output": '{"items":[1,2],"count":"2","extra":true}',
        },
    ]


def test_validate_jsonl_accepts_valid_structured_jsonl(tmp_path):
    path = tmp_path / "train.jsonl"
    write_jsonl(path, [training_row()])

    result = run_script(
        ROOT / "local_harness/failure_training/validate_jsonl.py",
        "--input",
        path,
        "--require-assistant-json",
    )

    assert result.returncode == 0
    assert "rows: 1" in result.stdout
    assert "assistant_json_parseable: 1" in result.stdout


def test_validate_jsonl_rejects_invalid_jsonl(tmp_path):
    path = tmp_path / "broken.jsonl"
    path.write_text("{not json}\n", encoding="utf-8")

    result = run_script(
        ROOT / "local_harness/failure_training/validate_jsonl.py",
        "--input",
        path,
    )

    assert result.returncode == 1
    assert "invalid JSON" in result.stdout


def test_validate_jsonl_requires_assistant_json_when_requested(tmp_path):
    path = tmp_path / "train.jsonl"
    write_jsonl(path, [training_row("plain text")])

    result = run_script(
        ROOT / "local_harness/failure_training/validate_jsonl.py",
        "--input",
        path,
        "--require-assistant-json",
    )

    assert result.returncode == 1
    assert "final assistant content is not valid JSON" in result.stdout


def test_mix_curriculum_writes_expected_row_counts_with_weight(tmp_path):
    base_train = tmp_path / "base_train.jsonl"
    base_val = tmp_path / "base_val.jsonl"
    new_train = tmp_path / "new_train.jsonl"
    new_val = tmp_path / "new_val.jsonl"
    out_train = tmp_path / "out" / "train.jsonl"
    out_val = tmp_path / "out" / "validation.jsonl"

    write_jsonl(base_train, [{"id": "base-train"}])
    write_jsonl(base_val, [{"id": "base-val"}])
    write_jsonl(new_train, [{"id": "new-a"}, {"id": "new-b"}])
    write_jsonl(new_val, [{"id": "new-val"}])

    result = run_script(
        ROOT / "local_harness/failure_training/mix_curriculum.py",
        "--base-train",
        base_train,
        "--base-validation",
        base_val,
        "--new-train",
        new_train,
        "--new-validation",
        new_val,
        "--new-weight",
        "3",
        "--out-train",
        out_train,
        "--out-validation",
        out_val,
    )

    assert result.returncode == 0
    assert "wrote:" in result.stdout
    assert len(out_train.read_text(encoding="utf-8").splitlines()) == 7
    assert len(out_val.read_text(encoding="utf-8").splitlines()) == 2


def test_score_eval_jsonl_computes_known_metrics(tmp_path):
    path = tmp_path / "eval.jsonl"
    output_md = tmp_path / "metrics.md"
    write_jsonl(path, eval_rows())

    metrics = score_rows(read_eval_rows(path))

    assert metrics["base_valid"] == 1
    assert metrics["adapter_valid"] == 2
    assert metrics["base_key_match"] == 0
    assert metrics["adapter_key_match"] == 1
    assert metrics["base_exact"] == 0
    assert metrics["adapter_exact"] == 1
    assert metrics["base_extra_fields"] == 1
    assert metrics["adapter_extra_fields"] == 1
    assert metrics["base_type_match"] == 1
    assert metrics["adapter_type_match"] == 1
    assert metrics["base_array_count_match"] == 0
    assert metrics["adapter_array_count_match"] == 2

    result = run_script(
        ROOT / "local_harness/failure_training/score_eval_jsonl.py",
        "--input",
        path,
        "--output-md",
        output_md,
    )

    assert result.returncode == 0
    assert "adapter_exact: 1/2" in result.stdout
    assert "| adapter_extra_fields | 1/2 |" in output_md.read_text(encoding="utf-8")


def test_extract_non_exact_review_writes_todo_sections(tmp_path):
    path = tmp_path / "eval.jsonl"
    output = tmp_path / "review.md"
    write_jsonl(path, eval_rows())

    result = run_script(
        ROOT / "local_harness/failure_training/extract_non_exact_review.py",
        "--input",
        path,
        "--output",
        output,
    )

    text = output.read_text(encoding="utf-8")
    assert result.returncode == 0
    assert "non_exact_rows: 1" in result.stdout
    assert "## Row 2" in text
    assert "- classification: TODO" in text


def test_extract_extra_field_review_catches_extra_keys(tmp_path):
    path = tmp_path / "eval.jsonl"
    output = tmp_path / "extra.md"
    write_jsonl(path, eval_rows())

    result = run_script(
        ROOT / "local_harness/failure_training/extract_extra_field_review.py",
        "--input",
        path,
        "--output",
        output,
    )

    text = output.read_text(encoding="utf-8")
    assert result.returncode == 0
    assert "extra_field_rows: 1" in result.stdout
    assert "Extra fields: `['extra']`" in text
    assert "- corrected target needed: TODO" in text


def test_write_round_report_accepts_metrics_markdown(tmp_path):
    metrics = tmp_path / "metrics.md"
    output = tmp_path / "round.md"
    metrics.write_text("| Metric | Count |\n|---|---:|\n| adapter_exact | 1/2 |\n", encoding="utf-8")

    result = run_script(
        ROOT / "local_harness/failure_training/write_round_report.py",
        "--output",
        output,
        "--run-label",
        "v6",
        "--adapter-name",
        "adapter",
        "--dataset-name",
        "dataset",
        "--base-model",
        "Qwen3-1.7B",
        "--train-rows",
        "177",
        "--validation-rows",
        "48",
        "--final-eval-loss",
        "1.3099",
        "--metrics-md",
        metrics,
        "--summary",
        "Measured structured-output improvement.",
    )

    text = output.read_text(encoding="utf-8")
    assert result.returncode == 0
    assert "Measured structured-output improvement." in text
    assert "This report is supervised evidence." in text


def test_each_helper_script_has_help_exit_zero():
    for script in SCRIPTS:
        result = run_script(script, "--help")
        assert result.returncode == 0, (script, result.stdout, result.stderr)
        assert "usage:" in result.stdout
