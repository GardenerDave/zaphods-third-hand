from local_harness.affordance_larql_training_candidate_artifact_review import build_review
from tests.test_affordance_larql_training_candidate_writer import (
    APPROVAL,
    clean_packet,
    clean_review,
)
from local_harness.affordance_larql_training_candidate_writer import (
    build_candidate_artifact,
    build_write_record,
)


def clean_written_pair():
    record = build_write_record(clean_packet(), clean_review(), APPROVAL, "candidate.json")
    artifact = build_candidate_artifact(clean_packet(), clean_review(), APPROVAL)

    artifact["training_example_preview"]["messages"][0]["content"] = (
        "Use the supplied LARQL runtime rule context as a bounded advisory constraint for this response.\n"
        "Active host is navigator_desktop.\n"
        "Host constraint is no_cuda.\n"
        "Use the LM Studio OpenAI-compatible endpoint."
    )
    artifact["training_example_preview"]["messages"][1]["content"] = (
        "I need CUDA working on this RX580 box so I can train the small model locally. Should I install NVIDIA CUDA?"
    )
    artifact["training_example_preview"]["messages"][2]["content"] = (
        "No, do not install NVIDIA CUDA on this RX580/no_cuda host.\n"
        "Use the LM Studio OpenAI-compatible endpoint.\n"
        "Reverify if host, GPU, driver, profile, endpoint, or digest evidence changes.\n"
        "Do not claim CUDA is available.\n"
    )
    return record, artifact


def test_artifact_review_accepts_clean_written_candidate():
    record, artifact = clean_written_pair()

    review = build_review(record, artifact)

    assert review["report_type"] == "affordance_larql_training_candidate_artifact_review.v0"
    assert review["review_status"] == "review_only"
    assert review["review_verdict"] == "approved_written_larql_training_candidate_artifact"
    assert review["allowed_next_step"] == "hold_for_explicit_larql_training_dataset_write_approval"
    assert review["training_candidate_written"] is True
    assert review["training_dataset_written"] is False
    assert review["durable_memory_written"] is False
    assert review["lora_training_started"] is False
    assert review["model_weights_mutated"] is False
    assert review["candidate_promoted"] is False
    assert review["runtime_rule_modified"] is False
    assert all(review["checks"].values())


def test_artifact_review_rejects_bad_training_shape():
    record, artifact = clean_written_pair()
    artifact["training_example_preview"]["messages"][2]["content"] = "Use some other path."

    review = build_review(record, artifact)

    assert review["review_verdict"] == "written_larql_training_candidate_artifact_rejected"
    assert review["allowed_next_step"] == "repair_written_larql_training_candidate_artifact"
    assert review["checks"]["artifact_training_shape_ok"] is False
    assert review["training_dataset_written"] is False


def test_artifact_review_rejects_dataset_written_flag():
    record, artifact = clean_written_pair()
    artifact["training_dataset_written"] = True

    review = build_review(record, artifact)

    assert review["review_verdict"] == "written_larql_training_candidate_artifact_rejected"
    assert review["checks"]["artifact_training_dataset_written_false"] is False


def test_artifact_review_never_authorizes_training_or_promotion():
    record, artifact = clean_written_pair()

    review = build_review(record, artifact)

    assert "write_training_dataset" in review["disallowed_actions"]
    assert "write_durable_memory" in review["disallowed_actions"]
    assert "train_lora_adapter" in review["disallowed_actions"]
    assert "mutate_model_weights" in review["disallowed_actions"]
    assert "promote_candidate" in review["disallowed_actions"]

    assert review["training_dataset_written"] is False
    assert review["durable_memory_written"] is False
    assert review["lora_training_started"] is False
    assert review["model_weights_mutated"] is False
    assert review["candidate_promoted"] is False
    assert review["runtime_rule_modified"] is False
