from local_harness.affordance_larql_training_candidate_writer import (
    approval_text_ok,
    build_candidate_artifact,
    build_write_record,
)


APPROVAL = (
    "I approve writing this reviewed LARQL training candidate as a local candidate artifact only. "
    "Do not train, promote, write durable memory, mutate weights, or modify runtime rules."
)


def clean_packet():
    return {
        "report_type": "affordance_larql_training_candidate_packet.v0",
        "packet_status": "packet_only",
        "packet_verdict": "ready_for_larql_training_candidate_review",
        "allowed_next_step": "review_larql_training_candidate_packet",
        "candidate_id": "larql_affordance_candidate_48efff9852ea",
        "source_failure_id": "cuda_on_navigator_desktop.real",
        "rule_id": "navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0",
        "candidate_digest": "c79aae337b91fe8da8f67d61508b4140e8c61e7db9cc607307c53e72566ec520",
        "response_sha256": "2df58ff3939dca14276725766a8471fcea7677561722e1bea2f195642c703063",
        "training_candidate_written": False,
        "durable_memory_authorized": False,
        "lora_training_authorized": False,
        "model_weight_mutation_authorized": False,
        "candidate_promotion_authorized": False,
        "training_candidate_preview": {
            "format": "larql_supervised_sft_candidate_preview.v0",
            "input": "I need CUDA working on this RX580 box so I can train the small model locally. Should I install NVIDIA CUDA?",
            "local_context_instruction": "Use the supplied LARQL runtime rule context as a bounded advisory constraint for this response.",
            "expected_response": "No, do not install NVIDIA CUDA on this RX580/no_cuda host.\nUse the LM Studio OpenAI-compatible endpoint.\nReverify if host, GPU, driver, profile, endpoint, or digest evidence changes.\nDo not claim CUDA is available.\n",
            "positive_requirements": ["Recommend the LM Studio OpenAI-compatible endpoint."],
            "negative_requirements": ["Do not recommend installing NVIDIA CUDA."],
            "evidence": {
                "probe_verdict": "larql_model_response_pass",
                "review_verdict": "larql_model_response_review_pass",
                "record_verdict": "larql_model_response_pass_recorded",
                "cuda_block_pass": True,
                "model_semantic_failures": [],
                "scorer_false_negatives": [],
                "scorer_false_positives": [],
            },
        },
    }


def clean_review():
    return {
        "report_type": "affordance_larql_training_candidate_review.v0",
        "review_status": "review_only",
        "review_verdict": "approved_for_larql_training_candidate_opt_in_boundary",
        "allowed_next_step": "request_explicit_larql_training_candidate_write_approval",
        "candidate_id": "larql_affordance_candidate_48efff9852ea",
        "source_failure_id": "cuda_on_navigator_desktop.real",
        "rule_id": "navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0",
        "candidate_digest": "c79aae337b91fe8da8f67d61508b4140e8c61e7db9cc607307c53e72566ec520",
        "response_sha256": "2df58ff3939dca14276725766a8471fcea7677561722e1bea2f195642c703063",
        "training_candidate_write_authorized": False,
        "training_candidate_written": False,
        "durable_memory_authorized": False,
        "lora_training_authorized": False,
        "model_weight_mutation_authorized": False,
        "candidate_promotion_authorized": False,
    }


def test_approval_text_ok_requires_explicit_boundary():
    assert approval_text_ok(APPROVAL) is True
    assert approval_text_ok("write it") is False


def test_write_record_accepts_clean_inputs():
    record = build_write_record(clean_packet(), clean_review(), APPROVAL, "candidate.json")

    assert record["write_verdict"] == "larql_training_candidate_local_artifact_written"
    assert record["allowed_next_step"] == "review_written_larql_training_candidate_artifact"
    assert record["training_candidate_write_authorized"] is True
    assert record["training_candidate_written"] is True
    assert record["training_dataset_written"] is False
    assert record["durable_memory_written"] is False
    assert record["lora_training_started"] is False
    assert record["model_weights_mutated"] is False
    assert record["candidate_promoted"] is False
    assert record["runtime_rule_modified"] is False
    assert all(record["checks"].values())


def test_write_record_rejects_bad_approval():
    record = build_write_record(clean_packet(), clean_review(), "sure", "candidate.json")

    assert record["write_verdict"] == "larql_training_candidate_local_artifact_write_rejected"
    assert record["allowed_next_step"] == "repair_larql_training_candidate_write_inputs"
    assert record["training_candidate_write_authorized"] is False
    assert record["training_candidate_written"] is False


def test_candidate_artifact_is_local_only():
    artifact = build_candidate_artifact(clean_packet(), clean_review(), APPROVAL)

    assert artifact["report_type"] == "affordance_larql_training_candidate_artifact.v0"
    assert artifact["candidate_status"] == "local_candidate_artifact_only"
    assert artifact["training_candidate_written"] is True
    assert artifact["training_dataset_written"] is False
    assert artifact["durable_memory_written"] is False
    assert artifact["lora_training_started"] is False
    assert artifact["model_weights_mutated"] is False
    assert artifact["candidate_promoted"] is False
    assert artifact["runtime_rule_modified"] is False
    assert [m["role"] for m in artifact["training_example_preview"]["messages"]] == [
        "system",
        "user",
        "assistant",
    ]
