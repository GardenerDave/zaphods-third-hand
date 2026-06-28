from local_harness.affordance_larql_training_dataset_writer import (
    approval_text_ok,
    build_dataset_row,
    build_write_record,
)


APPROVAL = (
    "I approve writing this reviewed LARQL training candidate into a local training dataset artifact only. "
    "Do not train, promote, write durable memory, mutate weights, or modify runtime rules."
)


def clean_artifact():
    return {
        "report_type": "affordance_larql_training_candidate_artifact.v0",
        "candidate_status": "local_candidate_artifact_only",
        "candidate_id": "larql_affordance_candidate_48efff9852ea",
        "source_failure_id": "cuda_on_navigator_desktop.real",
        "rule_id": "navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0",
        "candidate_digest": "c79aae337b91fe8da8f67d61508b4140e8c61e7db9cc607307c53e72566ec520",
        "response_sha256": "2df58ff3939dca14276725766a8471fcea7677561722e1bea2f195642c703063",
        "training_candidate_written": True,
        "training_dataset_written": False,
        "durable_memory_written": False,
        "lora_training_started": False,
        "model_weights_mutated": False,
        "candidate_promoted": False,
        "runtime_rule_modified": False,
        "training_example_preview": {
            "messages": [
                {"role": "system", "content": "Use bounded advisory constraint. no_cuda. LM Studio OpenAI-compatible endpoint."},
                {"role": "user", "content": "Should I install NVIDIA CUDA on this RX580 box?"},
                {"role": "assistant", "content": "No, do not install NVIDIA CUDA on this RX580/no_cuda host."},
            ],
            "positive_requirements": ["Recommend the LM Studio OpenAI-compatible endpoint."],
            "negative_requirements": ["Do not claim CUDA is available."],
        },
        "evidence": {
            "probe_verdict": "larql_model_response_pass",
            "review_verdict": "larql_model_response_review_pass",
            "record_verdict": "larql_model_response_pass_recorded",
            "cuda_block_pass": True,
            "model_semantic_failures": [],
            "scorer_false_negatives": [],
            "scorer_false_positives": [],
        },
    }


def clean_artifact_review():
    return {
        "report_type": "affordance_larql_training_candidate_artifact_review.v0",
        "review_status": "review_only",
        "review_verdict": "approved_written_larql_training_candidate_artifact",
        "allowed_next_step": "hold_for_explicit_larql_training_dataset_write_approval",
        "candidate_id": "larql_affordance_candidate_48efff9852ea",
        "source_failure_id": "cuda_on_navigator_desktop.real",
        "rule_id": "navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0",
        "candidate_digest": "c79aae337b91fe8da8f67d61508b4140e8c61e7db9cc607307c53e72566ec520",
        "response_sha256": "2df58ff3939dca14276725766a8471fcea7677561722e1bea2f195642c703063",
        "training_candidate_written": True,
        "training_dataset_written": False,
        "durable_memory_written": False,
        "lora_training_started": False,
        "model_weights_mutated": False,
        "candidate_promoted": False,
        "runtime_rule_modified": False,
    }


def test_approval_text_ok_requires_dataset_boundary():
    assert approval_text_ok(APPROVAL) is True
    assert approval_text_ok("go ahead") is False


def test_dataset_write_record_accepts_clean_inputs():
    record = build_write_record(clean_artifact(), clean_artifact_review(), APPROVAL, "dataset.jsonl")

    assert record["write_verdict"] == "larql_training_dataset_local_artifact_written"
    assert record["allowed_next_step"] == "review_written_larql_training_dataset_artifact"
    assert record["training_dataset_write_authorized"] is True
    assert record["training_dataset_written"] is True
    assert record["dataset_rows_written"] == 1

    assert record["durable_memory_written"] is False
    assert record["lora_training_started"] is False
    assert record["model_weights_mutated"] is False
    assert record["candidate_promoted"] is False
    assert record["runtime_rule_modified"] is False
    assert all(record["checks"].values())


def test_dataset_write_record_rejects_bad_approval():
    record = build_write_record(clean_artifact(), clean_artifact_review(), "sure", "dataset.jsonl")

    assert record["write_verdict"] == "larql_training_dataset_local_artifact_write_rejected"
    assert record["allowed_next_step"] == "repair_larql_training_dataset_write_inputs"
    assert record["training_dataset_write_authorized"] is False
    assert record["training_dataset_written"] is False
    assert record["dataset_rows_written"] == 0


def test_dataset_row_has_supervised_sft_shape_and_metadata():
    row = build_dataset_row(clean_artifact())

    assert [message["role"] for message in row["messages"]] == ["system", "user", "assistant"]
    assert row["metadata"]["format"] == "larql_supervised_sft_candidate.v0"
    assert row["metadata"]["training_scope"] == "local_dataset_artifact_only"
    assert row["metadata"]["candidate_id"] == "larql_affordance_candidate_48efff9852ea"
    assert row["metadata"]["evidence"]["probe_verdict"] == "larql_model_response_pass"


def test_dataset_writer_never_authorizes_training_or_promotion():
    record = build_write_record(clean_artifact(), clean_artifact_review(), APPROVAL, "dataset.jsonl")

    assert "write_durable_memory" in record["disallowed_actions"]
    assert "train_lora_adapter" in record["disallowed_actions"]
    assert "mutate_model_weights" in record["disallowed_actions"]
    assert "promote_candidate" in record["disallowed_actions"]
    assert "modify_runtime_rule" in record["disallowed_actions"]

    assert record["durable_memory_written"] is False
    assert record["lora_training_started"] is False
    assert record["model_weights_mutated"] is False
    assert record["candidate_promoted"] is False
    assert record["runtime_rule_modified"] is False
