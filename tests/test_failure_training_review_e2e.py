from local_harness.failure_training.apply_reviews import apply_review_decisions_jsonl
from local_harness.failure_training.common import read_jsonl, write_jsonl
from local_harness.failure_training.finalize_review import finalize_reviewed_curriculum
from local_harness.failure_training.run_cycle import run_cycle


def raw_failure(probe_id, corrected_output):
    return {
        "probe_id": probe_id,
        "score_result": "fail",
        "prompt": "Return a JSON object with key ok.",
        "raw_output": "not json",
        "model_id": "tiny-model",
        "expected_contract": "Valid JSON object.",
        "corrected_output": corrected_output,
    }


def candidate_id_for_probe(candidates, probe_id):
    matches = [
        candidate
        for candidate in candidates
        if candidate["provenance"]["probe_id"] == probe_id
    ]
    assert len(matches) == 1
    return matches[0]["id"]


def test_review_e2e_accepts_training_row_and_locks_holdout_out_of_training(tmp_path):
    input_path = tmp_path / "raw_rows.jsonl"
    work_root = tmp_path / "work"

    write_jsonl(
        input_path,
        [
            raw_failure("accept_case", '{"ok": true}'),
            raw_failure("holdout_case", '{"ok": false}'),
        ],
    )

    run_cycle(
        input_path=input_path,
        work_root=work_root,
        cycle_id="cycle_review_e2e",
        source_run_id="audition_review_e2e",
        target_capability="strict_json_contract",
    )

    cycle_dir = work_root / "cycles" / "cycle_review_e2e"
    candidates_path = cycle_dir / "curriculum" / "candidates.jsonl"
    decisions_path = cycle_dir / "curriculum" / "review_decisions.jsonl"
    reviewed_path = cycle_dir / "curriculum" / "reviewed_candidates.jsonl"
    finalized_dir = cycle_dir / "finalized"

    candidates = read_jsonl(candidates_path)
    assert len(candidates) == 2
    assert [candidate["review_status"] for candidate in candidates] == [
        "candidate",
        "candidate",
    ]

    accept_candidate_id = candidate_id_for_probe(candidates, "accept_case")
    holdout_candidate_id = candidate_id_for_probe(candidates, "holdout_case")

    write_jsonl(
        decisions_path,
        [
            {
                "candidate_id": accept_candidate_id,
                "review_status": "accepted",
                "reviewer": "test-reviewer",
                "review_notes": "Gold answer checked for training.",
            },
            {
                "candidate_id": holdout_candidate_id,
                "review_status": "holdout_locked",
                "reviewer": "test-reviewer",
                "review_notes": "Reserved for proof-set evaluation.",
            },
        ],
    )

    reviewed = apply_review_decisions_jsonl(
        candidates_path=candidates_path,
        decisions_path=decisions_path,
        output_path=reviewed_path,
    )

    assert [row["review_status"] for row in reviewed] == [
        "accepted",
        "holdout_locked",
    ]

    manifest = finalize_reviewed_curriculum(
        reviewed_candidates_path=reviewed_path,
        output_dir=finalized_dir,
    )

    train_rows = read_jsonl(finalized_dir / "datasets" / "train.jsonl")
    validation_rows = read_jsonl(finalized_dir / "datasets" / "validation.jsonl")
    holdout_rows = read_jsonl(finalized_dir / "datasets" / "holdout.jsonl")
    sft_train_rows = read_jsonl(finalized_dir / "datasets" / "sft" / "sft_train.jsonl")

    assert manifest["accepted_count"] == 1
    assert manifest["holdout_locked_count"] == 1
    assert manifest["train_count"] == 1
    assert manifest["validation_count"] == 0
    assert manifest["holdout_count"] == 1

    assert train_rows[0]["metadata"]["candidate_id"] == accept_candidate_id
    assert sft_train_rows[0]["metadata"]["candidate_id"] == accept_candidate_id

    assert holdout_rows[0]["id"] == holdout_candidate_id
    assert holdout_candidate_id not in [
        row["metadata"]["candidate_id"]
        for row in train_rows + validation_rows + sft_train_rows
    ]
