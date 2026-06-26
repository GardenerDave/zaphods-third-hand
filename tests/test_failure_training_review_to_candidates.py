import json
import subprocess
import sys
from pathlib import Path

from local_harness.failure_training.review_to_curriculum_candidates import (
    convert_review_files,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/failure_training/review_to_curriculum_candidates.py"


def run_script(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def write_review(
    path: Path,
    *,
    classification: str = "generic key substitution",
    likely_cause: str = "copied placeholder schema shape",
    keep: str = "yes",
    corrected: str = "no",
    adapter_lang: str = "json",
    adapter_body: str = '{"key1": 1, "key2": 2, "key3": 3}',
) -> None:
    path.write_text(
        f"""# Non-Exact Failure Review

## Row 7

Target:
```json
{{"count": 3}}
```

Adapter:
```{adapter_lang}
{adapter_body}
```

Review:
- classification: {classification}
- likely cause: {likely_cause}
- keep for next curriculum: {keep}
- corrected target needed: {corrected}
""",
        encoding="utf-8",
    )


def test_convert_review_file_to_draft_candidate(tmp_path):
    review = tmp_path / "review.md"
    write_review(review)

    result = convert_review_files([review], curriculum="v7_precision")

    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate["messages"][-1] == {
        "role": "assistant",
        "content": '{"count":3}',
    }
    assert candidate["metadata"]["candidate_status"] == "draft"
    assert candidate["metadata"]["requires_human_review"] is True
    assert candidate["metadata"]["not_final_training_data"] is True
    assert candidate["metadata"]["failure_mode"] == "generic_key_substitution"
    assert candidate["metadata"]["source_row"] == "7"


def test_corrected_target_overrides_target_block(tmp_path):
    review = tmp_path / "review.md"
    write_review(review, corrected='{"accepted":false}')

    result = convert_review_files([review], curriculum="v7_precision")

    candidate = result.candidates[0]
    assert candidate["messages"][-1]["content"] == '{"accepted":false}'
    assert candidate["metadata"]["corrected_target_source"] == "review_corrected_target"


def test_keep_no_skips_row(tmp_path):
    review = tmp_path / "review.md"
    write_review(review, keep="no", corrected="TODO")

    result = convert_review_files([review], curriculum="v7_precision")

    assert result.candidates == ()
    assert result.skipped_rows == 1


def test_keep_no_still_requires_completed_classification(tmp_path):
    review = tmp_path / "review.md"
    output = tmp_path / "out.jsonl"
    write_review(review, classification="TODO", keep="no", corrected="TODO")

    result = run_script("--input", review, "--output", output, "--curriculum", "v7")

    assert result.returncode == 1
    assert "classification is incomplete" in result.stdout
    assert not output.exists()


def test_cli_writes_jsonl_and_refuses_overwrite(tmp_path):
    review = tmp_path / "review.md"
    output = tmp_path / "candidates.jsonl"
    write_review(review)

    first = run_script("--input", review, "--output", output, "--curriculum", "v7")

    assert first.returncode == 0
    assert "candidate_rows: 1" in first.stdout
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["metadata"]["curriculum"] == "v7"

    second = run_script("--input", review, "--output", output, "--curriculum", "v7")

    assert second.returncode == 1
    assert "output already exists" in second.stdout


def test_cli_rejects_invalid_target_json(tmp_path):
    review = tmp_path / "review.md"
    review.write_text(
        """# Non-Exact Failure Review

## Row 1

Target:
```json
{not json}
```

Adapter:
```text
raw
```

Review:
- classification: parse failure
- likely cause: malformed target
- keep for next curriculum: yes
- corrected target needed: no
""",
        encoding="utf-8",
    )
    output = tmp_path / "out.jsonl"

    result = run_script("--input", review, "--output", output, "--curriculum", "v7")

    assert result.returncode == 1
    assert "invalid JSON" in result.stdout
    assert not output.exists()


def test_classification_todo_fails_closed(tmp_path):
    review = tmp_path / "review.md"
    output = tmp_path / "out.jsonl"
    write_review(review, classification="TODO")

    result = run_script("--input", review, "--output", output, "--curriculum", "v7")

    assert result.returncode == 1
    assert "classification is incomplete" in result.stdout
    assert not output.exists()


def test_likely_cause_todo_fails_closed(tmp_path):
    review = tmp_path / "review.md"
    output = tmp_path / "out.jsonl"
    write_review(review, likely_cause="TODO")

    result = run_script("--input", review, "--output", output, "--curriculum", "v7")

    assert result.returncode == 1
    assert "likely cause is incomplete" in result.stdout
    assert not output.exists()


def test_keep_todo_fails_closed(tmp_path):
    review = tmp_path / "review.md"
    output = tmp_path / "out.jsonl"
    write_review(review, keep="TODO")

    result = run_script("--input", review, "--output", output, "--curriculum", "v7")

    assert result.returncode == 1
    assert "keep for next curriculum must be explicit yes or no" in result.stdout
    assert not output.exists()


def test_corrected_target_todo_fails_closed(tmp_path):
    review = tmp_path / "review.md"
    output = tmp_path / "out.jsonl"
    write_review(review, corrected="TODO")

    result = run_script("--input", review, "--output", output, "--curriculum", "v7")

    assert result.returncode == 1
    assert "corrected target needed must be no" in result.stdout
    assert not output.exists()


def test_corrected_target_no_uses_original_target(tmp_path):
    review = tmp_path / "review.md"
    write_review(review, corrected="no")

    result = convert_review_files([review], curriculum="v7_precision")

    candidate = result.candidates[0]
    assert candidate["messages"][-1]["content"] == '{"count":3}'
    assert candidate["metadata"]["corrected_target_source"] == "target_block"


def test_corrected_target_yes_without_json_fails_closed(tmp_path):
    review = tmp_path / "review.md"
    output = tmp_path / "out.jsonl"
    write_review(review, corrected="yes")

    result = run_script("--input", review, "--output", output, "--curriculum", "v7")

    assert result.returncode == 1
    assert "corrected target needed is yes but no corrected JSON was provided" in result.stdout
    assert not output.exists()


def test_invalid_adapter_json_in_text_block_is_preserved_raw(tmp_path):
    review = tmp_path / "review.md"
    write_review(
        review,
        adapter_lang="text",
        adapter_body="{not valid json}",
        corrected="no",
    )

    result = convert_review_files([review], curriculum="v7_precision")

    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate["messages"][-1]["content"] == '{"count":3}'
    assert candidate["metadata"]["candidate_status"] == "draft"
    assert candidate["metadata"]["adapter_output_raw"] == "{not valid json}"


def test_help_exits_zero():
    result = run_script("--help")

    assert result.returncode == 0
    assert "usage:" in result.stdout
