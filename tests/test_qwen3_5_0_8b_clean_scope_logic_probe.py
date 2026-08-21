from __future__ import annotations

from scripts.zth_qwen3_5_0_8b_clean_scope_logic_probe import (
    EXPECTED_PARAMS,
    EXPECTED_MODEL_ID,
    EXPECTED_RUNTIME_SHA,
    runtime_payload,
    verify_matched_source,
)


def test_752m_runtime_binding_is_frozen():
    payload = runtime_payload()
    assert payload["candidate"]["filename"] == EXPECTED_MODEL_ID
    assert payload["llama_cpp_exposed_metadata"]["n_params"] == EXPECTED_PARAMS
    assert EXPECTED_RUNTIME_SHA


def test_clean_scope_source_is_byte_matched_to_596m():
    source = verify_matched_source()
    assert source["task_count"] == 16
    assert source["true_count"] == 8
    assert source["false_count"] == 8
    assert source["answer_leakage_findings"] == 0
    assert len(source["old_prompt_hashes"]) == 16
