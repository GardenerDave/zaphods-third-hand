from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from local_harness import semantic_assertion_extraction_probe as probe
from local_harness.validate_semantic_assertion_extraction_output import validate


class _FakeResponse:
    def __init__(self, payload: dict[str, object]):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_validator_accepts_single_ref_and_controlled_vocab():
    payload = {
        "assertions": [
            {
                "property": "semantic_capability",
                "epistemic_status": "established",
                "evidence_refs": ["case_a1_evidence"],
            }
        ]
    }
    assert validate(payload, expected_evidence_id="case_a1_evidence") == []


def test_validator_rejects_wrong_ref_and_multiple_refs():
    payload = {
        "assertions": [
            {
                "property": "semantic_capability",
                "epistemic_status": "established",
                "evidence_refs": ["case_a1_evidence", "bogus"],
            }
        ]
    }
    problems = validate(payload, expected_evidence_id="case_a1_evidence")
    assert any("exactly one reference" in problem for problem in problems)


def test_run_case_sends_structured_schema_and_preserves_telemetry(tmp_path: Path):
    candidate = tmp_path / "candidate.txt"
    evidence = tmp_path / "evidence.txt"
    gold = tmp_path / "gold.json"
    candidate.write_text("The supplied evidence establishes semantic capability.", encoding="utf-8")
    evidence_text = "Frozen synthetic evidence context for extraction only."
    evidence.write_text(evidence_text, encoding="utf-8")
    gold.write_text(
        json.dumps(
            {
                "assertions": [
                    {
                        "property": "semantic_capability",
                        "epistemic_status": "established",
                        "evidence_refs": ["case_x1_evidence"],
                    }
                ],
                "typing_source": "frozen_experiment_gold",
            }
        ),
        encoding="utf-8",
    )
    case = probe.ExtractionCase(
        case_id="x1",
        candidate_path=candidate,
        evidence_path=evidence,
        evidence_id="case_x1_evidence",
        gold_path=gold,
    )
    out_dir = tmp_path / "out"
    seen: dict[str, object] = {}

    def fake_urlopen(request, timeout=None):
        _ = timeout
        seen["body"] = json.loads(request.data.decode("utf-8"))
        return _FakeResponse(
            {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": json.dumps(
                                {
                                    "assertions": [
                                        {
                                            "property": "semantic_capability",
                                            "epistemic_status": "established",
                                            "evidence_refs": ["case_x1_evidence"],
                                        }
                                    ]
                                }
                            )
                        },
                    }
                ],
                "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18},
            }
        )

    with patch.object(probe.urllib.request, "urlopen", side_effect=fake_urlopen):
        result = probe.run_case(
            case=case,
            endpoint="http://127.0.0.1:8080/v1",
            model="test-model",
            out_dir=out_dir,
            max_tokens=64,
            temperature=0.0,
            timeout_seconds=5,
        )

    request_body = seen["body"]
    assert request_body["response_format"]["type"] == "json_schema"
    assert request_body["response_format"]["json_schema"]["schema"] == json.loads(
        probe.SCHEMA_PATH.read_text(encoding="utf-8")
    )
    prompt_text = request_body["messages"][0]["content"]
    assert "semantic_capability" in prompt_text
    assert evidence_text not in prompt_text
    assert "frozen_experiment_gold" not in prompt_text
    assert "transport_qualification_implies_semantic_capability_not_established_v1" not in prompt_text
    model_call = json.loads((out_dir / "model_call.json").read_text(encoding="utf-8"))
    validation = json.loads((out_dir / "validation.json").read_text(encoding="utf-8"))
    assert model_call["schema_sha256"] == probe._sha256_file(probe.SCHEMA_PATH)
    assert model_call["endpoint_telemetry"]["finish_reason"] == "stop"
    assert model_call["endpoint_telemetry"]["usage"]["prompt_tokens"] == 11
    assert validation["overall_validation_status"] == "passed"
    assert validation["semantic_score_status"] == "scored"
    assert result["prompt_sha256"]


def test_run_case_rejects_wrong_evidence_ref(tmp_path: Path):
    candidate = tmp_path / "candidate.txt"
    evidence = tmp_path / "evidence.txt"
    gold = tmp_path / "gold.json"
    candidate.write_text("The transport path was successfully qualified.", encoding="utf-8")
    evidence.write_text("Frozen synthetic evidence context for extraction only.", encoding="utf-8")
    gold.write_text(
        json.dumps(
            {
                "assertions": [
                    {
                        "property": "transport_qualification",
                        "epistemic_status": "established",
                        "evidence_refs": ["case_x3_evidence"],
                    }
                ],
                "typing_source": "frozen_experiment_gold",
            }
        ),
        encoding="utf-8",
    )
    case = probe.ExtractionCase(
        case_id="x3",
        candidate_path=candidate,
        evidence_path=evidence,
        evidence_id="case_x3_evidence",
        gold_path=gold,
    )
    out_dir = tmp_path / "out"

    class BadRefResponse(_FakeResponse):
        def __init__(self):
            super().__init__(
                {
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {
                                "content": json.dumps(
                                    {
                                        "assertions": [
                                            {
                                                "property": "transport_qualification",
                                                "epistemic_status": "established",
                                                "evidence_refs": ["bogus"],
                                            }
                                        ]
                                    }
                                )
                            },
                        }
                    ]
                }
            )

    with patch.object(probe.urllib.request, "urlopen", return_value=BadRefResponse()):
        result = probe.run_case(
            case=case,
            endpoint="http://127.0.0.1:8080/v1",
            model="test-model",
            out_dir=out_dir,
            max_tokens=64,
            temperature=0.0,
            timeout_seconds=5,
        )

    validation = json.loads((out_dir / "validation.json").read_text(encoding="utf-8"))
    assert validation["overall_validation_status"] == "failed"
    assert validation["semantic_score_status"] == "not_scored"
    assert any("must equal expected evidence id" in problem for problem in validation["diagnostics"])
    assert result["validation"]["overall_validation_status"] == "failed"


def test_run_case_marks_mechanical_failure_as_not_scored(tmp_path: Path):
    candidate = tmp_path / "candidate.txt"
    evidence = tmp_path / "evidence.txt"
    gold = tmp_path / "gold.json"
    candidate.write_text("The supplied evidence establishes semantic capability.", encoding="utf-8")
    evidence.write_text("Frozen synthetic evidence context for extraction only.", encoding="utf-8")
    gold.write_text(
        json.dumps(
            {
                "assertions": [
                    {
                        "property": "semantic_capability",
                        "epistemic_status": "established",
                        "evidence_refs": ["case_x1_evidence"],
                    }
                ],
                "typing_source": "frozen_experiment_gold",
            }
        ),
        encoding="utf-8",
    )
    case = probe.ExtractionCase(
        case_id="x1",
        candidate_path=candidate,
        evidence_path=evidence,
        evidence_id="case_x1_evidence",
        gold_path=gold,
    )
    out_dir = tmp_path / "out"

    class BadJsonResponse(_FakeResponse):
        def __init__(self):
            super().__init__(
                {
                    "choices": [
                        {
                            "finish_reason": "length",
                            "message": {
                                "content": '{"assertions": [{"property": "semantic_capability"'
                            },
                        }
                    ],
                    "usage": {"prompt_tokens": 11, "completion_tokens": 256, "total_tokens": 267},
                }
            )

    with patch.object(probe.urllib.request, "urlopen", return_value=BadJsonResponse()):
        probe.run_case(
            case=case,
            endpoint="http://127.0.0.1:8080/v1",
            model="test-model",
            out_dir=out_dir,
            max_tokens=64,
            temperature=0.0,
            timeout_seconds=5,
        )

    validation = json.loads((out_dir / "validation.json").read_text(encoding="utf-8"))
    assert validation["parse_status"] == "failed"
    assert validation["semantic_score_status"] == "not_scored"
    assert validation["semantic_score_reason"] == "mechanical_output_failure"
    assert validation["overall_validation_status"] == "failed"


def test_semantic_score_is_scored_only_when_overall_validation_passes():
    assert probe._semantic_score_status("passed") == "scored"
    assert probe._semantic_score_status("failed") == "not_scored"
    assert probe._semantic_score_reason("passed") == "semantic_comparison_completed"
    assert probe._semantic_score_reason("failed") == "mechanical_output_failure"
