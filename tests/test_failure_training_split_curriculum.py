from local_harness.failure_training.common import read_jsonl, write_jsonl
from local_harness.failure_training.split_curriculum import (
    candidate_to_training_row,
    dataset_manifest,
    split_train_validation,
    training_rows_from_accepted,
    write_dataset_splits,
)


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


def test_candidate_to_training_row_preserves_messages_and_metadata():
    row = candidate_to_training_row(candidate("1"))

    assert row["messages"][2]["role"] == "assistant"
    assert row["metadata"]["candidate_id"] == "1"
    assert row["metadata"]["failure_event_id"] == "failure_1"
    assert row["metadata"]["failure_modes_targeted"] == ["invalid_json"]


def test_training_rows_from_accepted_ignores_non_accepted_rows():
    rows = training_rows_from_accepted(
        [
            candidate("1", "accepted"),
            candidate("2", "candidate"),
            candidate("3", "needs_revision"),
            candidate("4", "holdout_locked"),
            candidate("5", "rejected"),
        ]
    )

    assert len(rows) == 1
    assert rows[0]["metadata"]["candidate_id"] == "1"


def test_split_train_validation_handles_empty_and_singleton():
    assert split_train_validation([]) == ([], [])

    train, validation = split_train_validation([{"id": "1"}])

    assert train == [{"id": "1"}]
    assert validation == []


def test_split_train_validation_is_deterministic():
    rows = [{"id": str(i)} for i in range(10)]

    train, validation = split_train_validation(rows, validation_ratio=0.2)

    assert [row["id"] for row in train] == ["0", "1", "2", "3", "4", "5", "6", "7"]
    assert [row["id"] for row in validation] == ["8", "9"]


def test_dataset_manifest_counts_rows():
    manifest = dataset_manifest(
        train_rows=[{"id": "train"}],
        validation_rows=[{"id": "validation"}],
        holdout_rows=[{"id": "holdout"}],
    )

    assert manifest["train_count"] == 1
    assert manifest["validation_count"] == 1
    assert manifest["holdout_count"] == 1
    assert "must not be used for training" in manifest["holdout_policy"]


def test_write_dataset_splits_outputs_train_validation_holdout_and_manifest(tmp_path):
    accepted_path = tmp_path / "accepted.jsonl"
    holdout_path = tmp_path / "holdout_locked.jsonl"
    output_dir = tmp_path / "datasets"

    write_jsonl(
        accepted_path,
        [
            candidate("1", "accepted"),
            candidate("2", "accepted"),
            candidate("3", "accepted"),
            candidate("4", "candidate"),
        ],
    )
    write_jsonl(holdout_path, [candidate("h1", "holdout_locked")])

    manifest = write_dataset_splits(
        accepted_path=accepted_path,
        holdout_locked_path=holdout_path,
        output_dir=output_dir,
        validation_ratio=0.34,
    )

    train_rows = read_jsonl(output_dir / "train.jsonl")
    validation_rows = read_jsonl(output_dir / "validation.jsonl")
    holdout_rows = read_jsonl(output_dir / "holdout.jsonl")
    manifest_rows = read_jsonl(output_dir / "dataset_manifest.jsonl")

    assert manifest["train_count"] == 2
    assert manifest["validation_count"] == 1
    assert manifest["holdout_count"] == 1
    assert [row["metadata"]["candidate_id"] for row in train_rows] == ["1", "2"]
    assert [row["metadata"]["candidate_id"] for row in validation_rows] == ["3"]
    assert holdout_rows[0]["id"] == "h1"
    assert manifest_rows == [manifest]
