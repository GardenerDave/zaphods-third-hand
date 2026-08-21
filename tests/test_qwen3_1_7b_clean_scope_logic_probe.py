from __future__ import annotations

from scripts.zth_qwen3_1_7b_clean_scope_logic_probe import (
    EXPECTED_EFFECTIVE_CTX,
    EXPECTED_PARAMS,
    runtime_payload,
    verify_matched_source,
)


def test_corrected_17b_runtime_binding_is_frozen():
    payload = runtime_payload()
    assert payload["operative_supplier"]["n_params"] == EXPECTED_PARAMS
    assert payload["context"]["requested_n_ctx"] == 40960
    assert payload["context"]["effective_n_ctx"] == EXPECTED_EFFECTIVE_CTX
    assert payload["context"]["n_ctx_train"] == 32768
    assert payload["context"]["cap_reason"] == "native_training_context_cap"


def test_all_prior_clean_probe_prompts_match_and_fit_context():
    source = verify_matched_source()
    assert source["task_count"] == 16
    assert source["true_count"] == 8
    assert source["false_count"] == 8
    assert source["answer_leakage_findings"] == 0
    assert source["max_prompt_chars"] == 1181
    assert source["conservative_prompt_plus_completion_bound"] == 1693
    assert source["conservative_prompt_plus_completion_bound"] < EXPECTED_EFFECTIVE_CTX
