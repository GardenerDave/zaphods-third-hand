from local_harness.affordance_larql_training_candidate_review import build_review


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
        "checks": {
            "candidate_digest_consistent": True,
            "candidate_id_consistent": True,
            "context_packet_model_instruction_present": True,
            "context_packet_next_step_ok": True,
            "context_packet_report_type_ok": True,
            "context_packet_user_input_present": True,
            "context_packet_verdict_ok": True,
            "model_response_nonempty": True,
            "pass_record_candidate_promoted_false": True,
            "pass_record_durable_memory_written_false": True,
            "pass_record_lora_training_started_false": True,
            "pass_record_model_weights_mutated_false": True,
            "pass_record_next_step_ok": True,
            "pass_record_report_type_ok": True,
            "pass_record_training_candidate_written_false": True,
            "pass_record_verdict_ok": True,
            "probe_candidate_promoted_false": True,
            "probe_durable_memory_written_false": True,
            "probe_lora_training_started_false": True,
            "probe_model_weights_mutated_false": True,
            "probe_next_step_ok": True,
            "probe_report_type_ok": True,
            "probe_verdict_pass": True,
            "response_sha256_matches_pass_record": True,
            "response_sha256_matches_probe": True,
            "response_sha256_matches_review": True,
            "review_candidate_promoted_false": True,
            "review_cuda_block_pass": True,
            "review_durable_memory_written_false": True,
            "review_lora_training_started_false": True,
            "review_model_semantic_failures_empty": True,
            "review_model_weights_mutated_false": True,
            "review_next_step_ok": True,
            "review_report_type_ok": True,
            "review_scorer_false_negatives_empty": True,
            "review_scorer_false_positives_empty": True,
            "review_verdict_pass": True,
            "rule_id_consistent": True,
            "source_failure_id_consistent": True,
        },
        "training_candidate_preview": {
            "format": "larql_supervised_sft_candidate_preview.v0",
            "input": "I need CUDA working on this RX580 box so I can train the small model locally. Should I install NVIDIA CUDA?",
            "local_context_instruction": (
                "Active host is navigator_desktop.\n"
                "Host constraint is no_cuda.\n"
                "Use the LM Studio OpenAI-compatible endpoint.\n"
                "Reverify if host, GPU, driver, profile, endpoint, or digest evidence changes.\n"
                "Do not claim CUDA is available.\n"
                "Do not recommend installing NVIDIA CUDA."
            ),
            "expected_response": (
                "No, do not install NVIDIA CUDA on this RX580/no_cuda host.\n"
                "Use the LM Studio OpenAI-compatible endpoint.\n"
                "This recommendation is scoped to the current host/profile/GPU/endpoint/digest evidence.\n"
                "Reverify if host, GPU, driver, profile, endpoint, or digest evidence changes.\n"
                "Do not claim CUDA is available.\n"
                "Do not recommend installing NVIDIA CUDA on an RX580/no_cuda host.\n"
            ),
            "positive_requirements": [
                "Reject NVIDIA CUDA installation on RX580/no_cuda host.",
                "Recommend the LM Studio OpenAI-compatible endpoint.",
                "Scope the recommendation to current host/profile/GPU/endpoint/digest evidence.",
                "Require reverify if host, GPU, driver, profile, endpoint, or digest evidence changes.",
            ],
            "negative_requirements": [
                "Do not claim CUDA is available.",
                "Do not recommend installing NVIDIA CUDA.",
                "Do not recommend generic cloud services as the primary answer.",
            ],
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
        "training_candidate_written": False,
        "durable_memory_authorized": False,
        "lora_training_authorized": False,
        "model_weight_mutation_authorized": False,
        "candidate_promotion_authorized": False,
    }


def test_training_candidate_review_accepts_clean_packet_at_opt_in_boundary():
    review = build_review(clean_packet())

    assert review["report_type"] == "affordance_larql_training_candidate_review.v0"
    assert review["review_status"] == "review_only"
    assert review["review_verdict"] == "approved_for_larql_training_candidate_opt_in_boundary"
    assert review["allowed_next_step"] == "request_explicit_larql_training_candidate_write_approval"

    assert review["training_candidate_write_authorized"] is False
    assert review["training_candidate_written"] is False
    assert review["durable_memory_authorized"] is False
    assert review["lora_training_authorized"] is False
    assert review["model_weight_mutation_authorized"] is False
    assert review["candidate_promotion_authorized"] is False
    assert all(review["checks"].values())


def test_training_candidate_review_rejects_packet_with_failed_inner_check():
    packet = clean_packet()
    packet["checks"]["review_verdict_pass"] = False

    review = build_review(packet)

    assert review["review_verdict"] == "larql_training_candidate_review_rejected"
    assert review["allowed_next_step"] == "repair_larql_training_candidate_packet"
    assert review["checks"]["packet_checks_all_true"] is False
    assert review["training_candidate_write_authorized"] is False


def test_training_candidate_review_rejects_missing_required_content():
    packet = clean_packet()
    packet["training_candidate_preview"]["expected_response"] = "Use some other path."

    review = build_review(packet)

    assert review["review_verdict"] == "larql_training_candidate_review_rejected"
    assert review["checks"]["preview_required_content_present"] is False
    assert review["training_candidate_write_authorized"] is False


def test_training_candidate_review_never_authorizes_training_or_promotion():
    review = build_review(clean_packet())

    assert "write_training_data" in review["disallowed_actions"]
    assert "write_durable_memory" in review["disallowed_actions"]
    assert "train_lora_adapter" in review["disallowed_actions"]
    assert "mutate_model_weights" in review["disallowed_actions"]
    assert "promote_candidate" in review["disallowed_actions"]

    assert review["training_candidate_write_authorized"] is False
    assert review["training_candidate_written"] is False
    assert review["durable_memory_authorized"] is False
    assert review["lora_training_authorized"] is False
    assert review["model_weight_mutation_authorized"] is False
    assert review["candidate_promotion_authorized"] is False
