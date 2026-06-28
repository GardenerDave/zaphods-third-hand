from local_harness.affordance_larql_model_response_pass_record import build_record


def passing_review():
    return {
        "report_type": "affordance_larql_model_response_review.v0",
        "allowed_next_step": "record_larql_model_response_pass",
        "candidate_id": "larql_affordance_candidate_48efff9852ea",
        "source_failure_id": "cuda_on_navigator_desktop.real",
        "rule_id": "navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0",
        "candidate_digest": "c79aae337b91fe8da8f67d61508b4140e8c61e7db9cc607307c53e72566ec520",
        "response_sha256": "2df58ff3939dca14276725766a8471fcea7677561722e1bea2f195642c703063",
        "review_verdict": "larql_model_response_review_pass",
        "cuda_block_pass": True,
        "model_semantic_failures": [],
        "scorer_false_negatives": [],
        "scorer_false_positives": [],
        "candidate_promoted": False,
        "durable_memory_written": False,
        "lora_training_started": False,
        "model_weights_mutated": False,
    }


def test_pass_record_accepts_clean_review():
    record = build_record(passing_review())

    assert record["report_type"] == "affordance_larql_model_response_pass_record.v0"
    assert record["record_status"] == "record_only"
    assert record["record_verdict"] == "larql_model_response_pass_recorded"
    assert record["allowed_next_step"] == "draft_larql_training_candidate_packet"

    assert record["candidate_promoted"] is False
    assert record["durable_memory_written"] is False
    assert record["lora_training_started"] is False
    assert record["model_weights_mutated"] is False
    assert record["training_candidate_written"] is False
    assert record["promotion_verdict"] == "hold_pending_explicit_experiment_approval"

    assert all(record["checks"].values())


def test_pass_record_rejects_nonpassing_review():
    review = passing_review()
    review["review_verdict"] = "larql_model_response_review_requires_repair"

    record = build_record(review)

    assert record["record_verdict"] == "larql_model_response_pass_record_rejected"
    assert record["allowed_next_step"] == "repair_larql_model_response_pass_record_inputs"
    assert record["checks"]["review_verdict_pass"] is False
    assert record["candidate_promoted"] is False
    assert record["training_candidate_written"] is False


def test_pass_record_rejects_semantic_failures():
    review = passing_review()
    review["model_semantic_failures"] = ["missing_lm_studio_specific_recommendation"]

    record = build_record(review)

    assert record["record_verdict"] == "larql_model_response_pass_record_rejected"
    assert record["checks"]["model_semantic_failures_empty"] is False
    assert record["evidence_summary"]["model_semantic_failures"] == [
        "missing_lm_studio_specific_recommendation"
    ]


def test_pass_record_never_authorizes_training_memory_or_promotion():
    record = build_record(passing_review())

    assert "write_durable_memory" in record["disallowed_actions"]
    assert "promote_candidate" in record["disallowed_actions"]
    assert "train_lora_adapter" in record["disallowed_actions"]
    assert "mutate_model_weights" in record["disallowed_actions"]

    assert record["candidate_promoted"] is False
    assert record["durable_memory_written"] is False
    assert record["lora_training_started"] is False
    assert record["model_weights_mutated"] is False
    assert record["training_candidate_written"] is False
