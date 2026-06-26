import subprocess
import sys

from local_harness.failure_training.common import read_jsonl, write_jsonl
from local_harness.failure_training.finalize_review import finalize_reviewed_curriculum


def candidate(candidate_id, review_status="accepted"):
    return {
        "id": candidate_id,
        "failure_event_id": f"failure_{candidate_id}",
        "cycle_id": "cycle_0001",
        "task_type": "supervised_failure_correction",
        "target_behavior": "Return corrected output.",
        "messages": [
            {"role": "system", "content": "Return corrected output."},
            {"role": "user", "content": "Fix this."},
            {"role": "assistant", "content": '{"ok": true}'},
        ],
        "failure_modes_targeted": ["invalid_json"],
        "review_status": review_status,
        "provenance": {"source_failure_event_id": f"failure_{candidate_id}"},
    }


def test_finalize_reviewed_curriculum_writes_review_datasets_sft_and_manifest(tmp_path):
    reviewed_path = tmp_path / "reviewed_candidates.jsonl"
    output_dir = tmp_path / "finalized"

    write_jsonl(
        reviewed_path,
        [
            candidate("a1", "accepted"),
            candidate("a2", "accepted"),
            candidate("a3", "accepted"),
            candidate("h1", "holdout_locked"),
            candidate("r1", "rejected"),
            candidate("n1", "needs_revision"),
        ],
    )

    manifest = finalize_reviewed_curriculum(
        reviewed_candidates_path=reviewed_path,
        output_dir=output_dir,
        validation_ratio=0.34,
    )

    assert manifest["reviewed_candidates_count"] == 6
    assert manifest["accepted_count"] == 3
    assert manifest["holdout_locked_count"] == 1
    assert manifest["rejected_count"] == 1
    assert manifest["needs_revision_count"] == 1
    assert manifest["train_count"] == 2
    assert manifest["validation_count"] == 1
    assert manifest["holdout_count"] == 1
    assert manifest["sft_train_count"] == 2
    assert manifest["sft_validation_count"] == 1

    assert len(read_jsonl(output_dir / "review" / "accepted.jsonl")) == 3
    assert len(read_jsonl(output_dir / "datasets" / "train.jsonl")) == 2
    assert len(read_jsonl(output_dir / "datasets" / "validation.jsonl")) == 1
    assert len(read_jsonl(output_dir / "datasets" / "holdout.jsonl")) == 1
    assert len(read_jsonl(output_dir / "datasets" / "sft" / "sft_train.jsonl")) == 2
    assert read_jsonl(output_dir / "finalize_manifest.jsonl") == [manifest]


def test_finalize_reviewed_curriculum_can_strip_sft_metadata(tmp_path):
    reviewed_path = tmp_path / "reviewed_candidates.jsonl"
    output_dir = tmp_path / "finalized"

    write_jsonl(reviewed_path, [candidate("a1", "accepted")])

    manifest = finalize_reviewed_curriculum(
        reviewed_candidates_path=reviewed_path,
        output_dir=output_dir,
        include_metadata=False,
    )

    assert manifest["include_metadata"] is False
    assert "metadata" not in read_jsonl(output_dir / "datasets" / "sft" / "sft_train.jsonl")[0]


def test_finalize_review_cli_prints_summary(tmp_path):
    reviewed_path = tmp_path / "reviewed_candidates.jsonl"
    output_dir = tmp_path / "finalized"

    write_jsonl(
        reviewed_path,
        [
            candidate("a1", "accepted"),
            candidate("h1", "holdout_locked"),
        ],
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "local_harness.failure_training.finalize_review",
            "--reviewed-candidates",
            str(reviewed_path),
            "--output-dir",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Finalized reviewed curriculum:" in result.stdout
    assert "accepted=1" in result.stdout
    assert "holdout_locked=1" in result.stdout
    assert (output_dir / "finalize_manifest.jsonl").exists()
