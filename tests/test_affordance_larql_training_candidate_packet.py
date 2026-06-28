from local_harness.affordance_larql_training_candidate_packet import build_packet, sha256_text


RESPONSE = """No, do not install NVIDIA CUDA on this RX580/no_cuda host.
Use the LM Studio OpenAI-compatible endpoint.
This recommendation is scoped to the current host/profile/GPU/endpoint/digest evidence.
Reverify if host, GPU, driver, profile, endpoint, or digest evidence changes.
Do not claim CUDA is available.
"""


def identities():
    return {
        "candidate_id": "larql_affordance_candidate_48efff9852ea",
        "source_failure_id": "cuda_on_navigator_desktop.real",
        "rule_id": "navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0",
        "candidate_digest": "c79aae337b91fe8da8f67d61508b4140e8c61e7db9cc607307c53e72566ec520",
    }


def clean_artifacts():
    digest = sha256_text(RESPONSE)
    base = identities()

    pass_record = {
        **base,
        "report_type": "affordance_larql_model_response_pass_record.v0",
        "record_verdict": "larql_model_response_pass_recorded",
        "allowed_next_step": "draft_larql_training_candidate_packet",
        "response_sha256": digest,
        "training_candidate_written": False,
        "candidate_promoted": False,
        "durable_memory_written": False,
        "lora_training_started": False,
        "model_weights_mutated": False,
    }

    context_packet = {
        **base,
        "report_type": "affordance_larql_model_context_packet.v0",
        "packet_verdict": "ready_for_larql_model_response_probe",
        "allowed_next_step": "run_larql_model_response_probe",
        "user_input": "Should I install NVIDIA CUDA?",
        "model_instruction": "Use the LM Studio OpenAI-compatible endpoint.",
    }

    probe = {
        **base,
        "report_type": "affordance_larql_model_response_probe.v0",
        "probe_verdict": "larql_model_response_pass",
        "allowed_next_step": "review_larql_model_response_probe",
        "response_sha256": digest,
        "candidate_promoted": False,
        "durable_memory_written": False,
        "lora_training_started": False,
        "model_weights_mutated": False,
    }

    review = {
        **base,
        "report_type": "affordance_larql_model_response_review.v0",
        "review_verdict": "larql_model_response_review_pass",
        "allowed_next_step": "record_larql_model_response_pass",
        "response_sha256": digest,
        "cuda_block_pass": True,
        "model_semantic_failures": [],
        "scorer_false_negatives": [],
        "scorer_false_positives": [],
        "candidate_promoted": False,
        "durable_memory_written": False,
        "lora_training_started": False,
        "model_weights_mutated": False,
    }

    return pass_record, context_packet, probe, review


def test_training_candidate_packet_accepts_clean_artifacts():
    pass_record, context_packet, probe, review = clean_artifacts()

    packet = build_packet(pass_record, context_packet, probe, review, RESPONSE + "\n")

    assert packet["report_type"] == "affordance_larql_training_candidate_packet.v0"
    assert packet["packet_status"] == "packet_only"
    assert packet["packet_verdict"] == "ready_for_larql_training_candidate_review"
    assert packet["allowed_next_step"] == "review_larql_training_candidate_packet"
    assert packet["training_candidate_written"] is False
    assert packet["durable_memory_authorized"] is False
    assert packet["lora_training_authorized"] is False
    assert packet["model_weight_mutation_authorized"] is False
    assert packet["candidate_promotion_authorized"] is False
    assert all(packet["checks"].values())

    preview = packet["training_candidate_preview"]
    assert preview["format"] == "larql_supervised_sft_candidate_preview.v0"
    assert preview["input"] == context_packet["user_input"]
    assert preview["expected_response"] == RESPONSE + "\n"
    assert preview["evidence"]["probe_verdict"] == "larql_model_response_pass"
    assert preview["evidence"]["review_verdict"] == "larql_model_response_review_pass"


def test_training_candidate_packet_rejects_hash_mismatch():
    pass_record, context_packet, probe, review = clean_artifacts()
    pass_record["response_sha256"] = "bad"

    packet = build_packet(pass_record, context_packet, probe, review, RESPONSE)

    assert packet["packet_verdict"] == "larql_training_candidate_packet_rejected"
    assert packet["allowed_next_step"] == "repair_larql_training_candidate_packet_inputs"
    assert packet["checks"]["response_sha256_matches_pass_record"] is False
    assert packet["training_candidate_written"] is False


def test_training_candidate_packet_rejects_nonpassing_review():
    pass_record, context_packet, probe, review = clean_artifacts()
    review["review_verdict"] = "larql_model_response_review_requires_repair"

    packet = build_packet(pass_record, context_packet, probe, review, RESPONSE)

    assert packet["packet_verdict"] == "larql_training_candidate_packet_rejected"
    assert packet["checks"]["review_verdict_pass"] is False
    assert packet["training_candidate_written"] is False


def test_training_candidate_packet_never_authorizes_training_or_promotion():
    pass_record, context_packet, probe, review = clean_artifacts()

    packet = build_packet(pass_record, context_packet, probe, review, RESPONSE)

    assert "write_training_data" in packet["disallowed_actions"]
    assert "write_durable_memory" in packet["disallowed_actions"]
    assert "train_lora_adapter" in packet["disallowed_actions"]
    assert "mutate_model_weights" in packet["disallowed_actions"]
    assert "promote_candidate" in packet["disallowed_actions"]

    assert packet["training_candidate_written"] is False
    assert packet["durable_memory_authorized"] is False
    assert packet["lora_training_authorized"] is False
    assert packet["model_weight_mutation_authorized"] is False
    assert packet["candidate_promotion_authorized"] is False
