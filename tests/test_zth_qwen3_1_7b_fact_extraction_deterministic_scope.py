import json
from pathlib import Path

from scripts import zth_qwen3_1_7b_fact_extraction_deterministic_scope as probe


def test_expected_manifest_and_policy_are_model_free():
    binding = probe.validate_model_free()
    assert len(binding["tasks"]) == 16
    assert sum(row["expected_scope_expansion_required"] for row in binding["derived"]) == 8
    assert sum(not row["expected_scope_expansion_required"] for row in binding["derived"]) == 8
    assert all(row["deterministic_scope_from_facts"] == row["expected_scope_expansion_required"] for row in binding["derived"])
    assert binding["schema"]["additionalProperties"] is False
    assert set(binding["schema"]["properties"]) == set(probe.FIELDS)


def test_extraction_prompt_has_no_decision_cues():
    binding = probe.validate_model_free()
    prompts = "\n".join(binding["prompts"].values()).casefold()
    assert "scope_expansion_required" not in prompts
    assert "scope expansion" not in prompts
    assert '"true"' not in prompts
    assert '"false"' not in prompts
    assert "target allowed" not in prompts
    assert "operation allowed" not in prompts
