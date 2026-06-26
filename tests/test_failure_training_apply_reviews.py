import pytest

from local_harness.failure_training.apply_reviews import (
    apply_review_decisions,
    apply_review_decisions_jsonl,
    decisions_by_candidate_id,
    normalize_decision_status,
)
from local_harness.failure_training.common import read_jsonl, write_jsonl


def candidate(candidate_id, review_status="candidate"):
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


def test_normalize_decision_status_accepts_review_statuses():
    assert normalize_decision_status("accepted") == "accepted"
    assert normalize_decision_status(" HOLDOUT_LOCKED ") == "holdout_locked"
    assert normalize_decision_status("needs_revision") == "needs_revision"


def test_normalize_decision_status_rejects_candidate_status():
    with pytest.raises(ValueError, match="unsupported review decision status"):
        normalize_decision_status("candidate")


def test_decisions_by_candidate_id_requires_candidate_id():
    with pytest.raises(ValueError, match="missing candidate_id"):
        decisions_by_candidate_id([{"review_status": "accepted"}])


def test_decisions_by_candidate_id_indexes_last_decision_for_candidate():
    indexed = decisions_by_candidate_id(
        [
            {"candidate_id": "c1", "review_status": "rejected"},
            {"candidate_id": "c1", "review_status": "accepted", "reviewer": "dave"},
        ]
    )

    assert indexed["c1"]["review_status"] == "accepted"
    assert indexed["c1"]["reviewer"] == "dave"


def test_apply_review_decisions_promotes_only_explicit_matches():
    reviewed = apply_review_decisions(
        [
            candidate("c1"),
            candidate("c2"),
            candidate("c3", review_status="needs_revision"),
        ],
        [
            {
                "candidate_id": "c1",
                "review_status": "accepted",
                "reviewer": "dave",
                "review_notes": "gold output checked",
            },
            {
                "candidate_id": "c2",
                "review_status": "holdout_locked",
                "reviewer": "dave",
            },
        ],
    )

    assert reviewed[0]["review_status"] == "accepted"
    assert reviewed[0]["review"]["reviewer"] == "dave"
    assert reviewed[0]["review"]["review_notes"] == "gold output checked"

    assert reviewed[1]["review_status"] == "holdout_locked"
    assert reviewed[1]["review"]["decision_source"] == "review_decisions_jsonl"

    assert reviewed[2]["review_status"] == "needs_revision"
    assert "review" not in reviewed[2]


def test_apply_review_decisions_defaults_bad_candidate_status_to_needs_revision():
    reviewed = apply_review_decisions(
        [candidate("c1", review_status="weird")],
        [],
    )

    assert reviewed[0]["review_status"] == "needs_revision"


def test_apply_review_decisions_jsonl_round_trip(tmp_path):
    candidates_path = tmp_path / "candidates.jsonl"
    decisions_path = tmp_path / "review_decisions.jsonl"
    output_path = tmp_path / "reviewed_candidates.jsonl"

    write_jsonl(candidates_path, [candidate("c1"), candidate("c2")])
    write_jsonl(
        decisions_path,
        [
            {"candidate_id": "c1", "review_status": "accepted", "reviewer": "dave"},
            {"candidate_id": "c2", "review_status": "rejected", "reviewer": "dave"},
        ],
    )

    reviewed = apply_review_decisions_jsonl(
        candidates_path=candidates_path,
        decisions_path=decisions_path,
        output_path=output_path,
    )
    loaded = read_jsonl(output_path)

    assert loaded == reviewed
    assert [row["review_status"] for row in loaded] == ["accepted", "rejected"]
