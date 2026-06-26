from local_harness.failure_training.common import read_jsonl, write_jsonl
from local_harness.failure_training.review_curriculum import (
    CONTROLLED_REVIEW_STATUSES,
    normalized_review_status,
    review_summary_markdown,
    split_candidates_by_review_status,
    split_review_jsonl,
    write_review_splits,
)


def candidate(candidate_id, review_status):
    return {
        "id": candidate_id,
        "failure_event_id": f"failure_{candidate_id}",
        "cycle_id": "cycle_0001",
        "task_type": "supervised_failure_correction",
        "target_behavior": "Return a corrected answer.",
        "messages": [
            {"role": "system", "content": "Return corrected output."},
            {"role": "user", "content": "Fix this."},
        ],
        "failure_modes_targeted": ["invalid_json"],
        "review_status": review_status,
        "provenance": {"source_failure_event_id": f"failure_{candidate_id}"},
    }


def test_normalized_review_status_accepts_controlled_values():
    assert normalized_review_status(candidate("1", "accepted")) == "accepted"
    assert normalized_review_status(candidate("2", "ACCEPTED")) == "accepted"
    assert normalized_review_status(candidate("3", " holdout_locked ")) == "holdout_locked"


def test_normalized_review_status_defaults_to_needs_revision():
    assert normalized_review_status(candidate("1", "weird")) == "needs_revision"
    assert normalized_review_status({"id": "missing_status"}) == "needs_revision"


def test_split_candidates_by_review_status_initializes_all_buckets():
    splits = split_candidates_by_review_status([])

    assert set(splits) == set(CONTROLLED_REVIEW_STATUSES)
    assert all(rows == [] for rows in splits.values())


def test_split_candidates_by_review_status_routes_rows():
    splits = split_candidates_by_review_status(
        [
            candidate("1", "accepted"),
            candidate("2", "rejected"),
            candidate("3", "holdout_locked"),
            candidate("4", "candidate"),
            candidate("5", "needs_revision"),
            candidate("6", "bad_status"),
        ]
    )

    assert [row["id"] for row in splits["accepted"]] == ["1"]
    assert [row["id"] for row in splits["rejected"]] == ["2"]
    assert [row["id"] for row in splits["holdout_locked"]] == ["3"]
    assert [row["id"] for row in splits["candidate"]] == ["4"]
    assert [row["id"] for row in splits["needs_revision"]] == ["5", "6"]
    assert splits["needs_revision"][1]["review_status"] == "needs_revision"


def test_review_summary_markdown_marks_only_accepted_trainable():
    splits = split_candidates_by_review_status(
        [
            candidate("1", "accepted"),
            candidate("2", "holdout_locked"),
        ]
    )

    summary = review_summary_markdown(splits)

    assert "| accepted | 1 | yes |" in summary
    assert "| holdout_locked | 1 | no |" in summary
    assert "Only `accepted` candidates are eligible for training export." in summary


def test_write_review_splits_writes_all_outputs(tmp_path):
    splits = write_review_splits(
        [
            candidate("1", "accepted"),
            candidate("2", "rejected"),
            candidate("3", "holdout_locked"),
        ],
        tmp_path,
    )

    assert len(splits["accepted"]) == 1
    assert read_jsonl(tmp_path / "accepted.jsonl")[0]["id"] == "1"
    assert read_jsonl(tmp_path / "rejected.jsonl")[0]["id"] == "2"
    assert read_jsonl(tmp_path / "holdout_locked.jsonl")[0]["id"] == "3"
    assert read_jsonl(tmp_path / "candidate.jsonl") == []
    assert read_jsonl(tmp_path / "needs_revision.jsonl") == []
    assert (tmp_path / "review_summary.md").exists()


def test_split_review_jsonl_round_trip(tmp_path):
    input_path = tmp_path / "candidates.jsonl"
    output_dir = tmp_path / "review"

    write_jsonl(
        input_path,
        [
            candidate("1", "accepted"),
            candidate("2", "needs_revision"),
        ],
    )

    splits = split_review_jsonl(input_path, output_dir)

    assert [row["id"] for row in splits["accepted"]] == ["1"]
    assert [row["id"] for row in splits["needs_revision"]] == ["2"]
    assert read_jsonl(output_dir / "accepted.jsonl")[0]["id"] == "1"
