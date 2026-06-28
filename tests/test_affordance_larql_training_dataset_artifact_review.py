from local_harness.affordance_larql_training_dataset_artifact_review import build_review
from local_harness.affordance_larql_training_dataset_writer import build_dataset_row, build_write_record
from tests.test_affordance_larql_training_dataset_writer import (
    APPROVAL,
    clean_artifact,
    clean_artifact_review,
)


def clean_record_and_rows():
    artifact = clean_artifact()
    artifact["training_example_preview"]["messages"] = [
        {
            "role": "system",
            "content": (
                "Use the supplied LARQL runtime rule context as a bounded advisory constraint for this response.\n"
                "Active host is navigator_desktop.\n"
                "Host constraint is no_cuda.\n"
                "Use the LM Studio OpenAI-compatible endpoint."
            ),
        },
        {
            "role": "user",
            "content": "I need CUDA working on this RX580 box. Should I install NVIDIA CUDA?",
        },
        {
            "role": "assistant",
            "content": (
                "No, do not install NVIDIA CUDA on this RX580/no_cuda host.\n"
                "Use the LM Studio OpenAI-compatible endpoint.\n"
                "Reverify if host, GPU, driver, profile, endpoint, or digest evidence changes.\n"
                "Do not claim CUDA is available."
            ),
        },
    ]
    record = build_write_record(artifact, clean_artifact_review(), APPROVAL, "dataset.jsonl")
    return record, [build_dataset_row(artifact)]


def test_dataset_artifact_review_accepts_clean_dataset():
    record, rows = clean_record_and_rows()

    review = build_review(record, rows)

    assert review["report_type"] == "affordance_larql_training_dataset_artifact_review.v0"
    assert review["review_status"] == "review_only"
    assert review["review_verdict"] == "approved_written_larql_training_dataset_artifact"
    assert review["allowed_next_step"] == "hold_for_explicit_larql_training_run_approval"
    assert review["dataset_rows_reviewed"] == 1
    assert review["training_dataset_written"] is True

    assert review["durable_memory_written"] is False
    assert review["lora_training_started"] is False
    assert review["model_weights_mutated"] is False
    assert review["candidate_promoted"] is False
    assert review["runtime_rule_modified"] is False
    assert all(review["checks"].values())


def test_dataset_artifact_review_rejects_bad_row_shape():
    record, rows = clean_record_and_rows()
    rows[0]["messages"][2]["content"] = "Use some other path."

    review = build_review(record, rows)

    assert review["review_verdict"] == "written_larql_training_dataset_artifact_rejected"
    assert review["allowed_next_step"] == "repair_written_larql_training_dataset_artifact"
    assert review["checks"]["dataset_row_shape_ok"] is False


def test_dataset_artifact_review_rejects_metadata_mismatch():
    record, rows = clean_record_and_rows()
    rows[0]["metadata"]["candidate_id"] = "wrong"

    review = build_review(record, rows)

    assert review["review_verdict"] == "written_larql_training_dataset_artifact_rejected"
    assert review["checks"]["dataset_metadata_matches_record"] is False


def test_dataset_artifact_review_rejects_unexpected_row_count():
    record, rows = clean_record_and_rows()
    rows.append(rows[0])

    review = build_review(record, rows)

    assert review["review_verdict"] == "written_larql_training_dataset_artifact_rejected"
    assert review["checks"]["dataset_single_row_for_candidate"] is False


def test_dataset_artifact_review_never_authorizes_training_or_promotion():
    record, rows = clean_record_and_rows()

    review = build_review(record, rows)

    assert "write_durable_memory" in review["disallowed_actions"]
    assert "train_lora_adapter" in review["disallowed_actions"]
    assert "mutate_model_weights" in review["disallowed_actions"]
    assert "promote_candidate" in review["disallowed_actions"]
    assert "modify_runtime_rule" in review["disallowed_actions"]

    assert review["durable_memory_written"] is False
    assert review["lora_training_started"] is False
    assert review["model_weights_mutated"] is False
    assert review["candidate_promoted"] is False
    assert review["runtime_rule_modified"] is False
