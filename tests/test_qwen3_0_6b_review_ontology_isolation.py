from __future__ import annotations

import hashlib

from scripts import zth_qwen3_0_6b_review_ontology_isolation as isolation


def test_corrected_suffix_changes_only_review_ontology() -> None:
    assert hashlib.sha256(isolation.ORIGINAL_SUFFIX.encode()).hexdigest() == isolation.ORIGINAL_SUFFIX_SHA
    assert hashlib.sha256(isolation.NEW_SUFFIX.encode()).hexdigest() == "75dc7be7a5e782b3858276d28fd90ba9a7620a951a4b3e1d308b904d6d12b7cc"
    assert isolation.PROMPT_DIFF.count("+ -") == 0
    assert isolation.PROMPT_DIFF.count("+  \"ready_for_review\"") == 1
    assert "ready_for_review" not in isolation.ORIGINAL_SUFFIX


def test_corrected_prompt_preserves_explicit_interface() -> None:
    task = {"prompt": "Bounded task.", "output_contract": {"required_fields": ["allowed_targets", "held_targets", "scope_expansion_required", "review_status"]}}
    prompt = isolation.prompt_for(task)
    assert '"allowed_targets": ["string"]' in prompt
    assert '"held_targets": ["string"]' in prompt
    assert '"scope_expansion_required": true' in prompt
    assert '"review_status": "string"' in prompt
    assert '"ready_for_review"' in prompt
    assert prompt.endswith("/no_think")
