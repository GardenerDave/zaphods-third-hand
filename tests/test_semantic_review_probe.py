from __future__ import annotations

import json
import io
from pathlib import Path
from unittest.mock import patch

from local_harness import semantic_review_probe
from local_harness.semantic_review_probe import _build_prompt, run_probe
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


def test_run_probe_sends_structured_response_format_and_validates(tmp_path: Path):
    candidate = tmp_path / "candidate.txt"
    evidence_md = tmp_path / "evidence.md"
    evidence_json = tmp_path / "evidence.json"
    candidate.write_text('{"verdict":"hold"}', encoding="utf-8")
    evidence_md.write_text("evidence block", encoding="utf-8")
    evidence_json.write_text(
        json.dumps(
            {
                "evidence_sources": [
                    {"path": "docs/example.md", "excerpt": "evidence block"},
                ]
            }
        ),
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"
    seen_request = {}

    class _Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {
                                "content": json.dumps(
                                    {
                                        "verdict": "hold",
                                        "unsupported_claims": [],
                                        "internal_consistency": "consistent",
                                        "review_reason": "grounded",
                                    }
                                )
                            },
                        }
                    ],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                }
            ).encode("utf-8")

    def fake_urlopen(request, timeout=None):
        _ = timeout
        seen_request["body"] = json.loads(request.data.decode("utf-8"))
        return _Response()

    with patch.object(semantic_review_probe.urllib.request, "urlopen", side_effect=fake_urlopen):
        result = run_probe(
            candidate_path=candidate,
            evidence_path=evidence_md,
            out_dir=out_dir,
            endpoint="http://127.0.0.1:8080/v1",
            model="test-model",
            max_tokens=32,
            temperature=0.0,
            timeout_seconds=5,
        )

    request_body = seen_request["body"]
    assert request_body["response_format"]["type"] == "json_schema"
    assert request_body["response_format"]["json_schema"]["schema"] == json.loads(
        semantic_review_probe.REVIEW_SCHEMA_PATH.read_text(encoding="utf-8")
    )
    call = json.loads((out_dir / "review_model_call.json").read_text(encoding="utf-8"))
    validation = json.loads((out_dir / "review_validation.json").read_text(encoding="utf-8"))
    assert call["schema_source_path"] == str(semantic_review_probe.REVIEW_SCHEMA_PATH)
    assert call["schema_sha256"] == semantic_review_probe._sha256_file(semantic_review_probe.REVIEW_SCHEMA_PATH)
    assert call["endpoint_telemetry"]["finish_reason"] == "stop"
    assert call["endpoint_telemetry"]["usage"]["prompt_tokens"] == 1
    assert validation["overall_validation_status"] == "passed"
    assert result["prompt_sha256"]


def test_review_validator_rejects_previous_string_evidence_shape():
    payload = {
        "verdict": "hold",
        "unsupported_claims": [
            {
                "claim": "capability is demonstrated",
                "reason": "unsupported",
                "evidence": "The evidence indicates transport qualification only.",
            }
        ],
        "internal_consistency": "inconsistent",
        "review_reason": "grounded",
    }
    problems = validate(payload, {"docs/example.md"})
    assert any("evidence must be a list" in problem for problem in problems)
