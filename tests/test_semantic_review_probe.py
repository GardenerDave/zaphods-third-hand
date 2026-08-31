from __future__ import annotations

import json
from pathlib import Path

from local_harness.semantic_review_probe import _build_prompt
from local_harness.validate_semantic_review_output import validate


def test_review_validator_accepts_grounded_output():
    payload = {
        "verdict": "hold",
        "unsupported_claims": [
            {
                "claim": "capability is demonstrated",
                "reason": "evidence only shows transport and validation",
                "evidence": [
                    {"path": "docs/example.md", "detail": "bounded evidence"}
                ],
            }
        ],
        "internal_consistency": "consistent",
        "review_reason": "grounded",
    }
    assert validate(payload, {"docs/example.md"}) == []


def test_review_validator_rejects_unprojected_path():
    payload = {
        "verdict": "hold",
        "unsupported_claims": [
            {
                "claim": "capability is demonstrated",
                "reason": "evidence only shows transport and validation",
                "evidence": [
                    {"path": "docs/not_projected.md", "detail": "bounded evidence"}
                ],
            }
        ],
        "internal_consistency": "consistent",
        "review_reason": "grounded",
    }
    assert any("not projected" in problem for problem in validate(payload, {"docs/example.md"}))


def test_review_prompt_includes_candidate_and_evidence():
    prompt = _build_prompt(
        evidence_text="evidence block",
        candidate_text='{"verdict":"hold"}',
    )
    assert "Advisory Semantic Review Packet" in prompt
    assert "evidence block" in prompt
    assert '{"verdict":"hold"}' in prompt
