from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from local_harness import semantic_property_classification_probe as probe


class _FakeResponse:
    def __init__(self, payload: dict[str, object]):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_prompt_is_candidate_only_and_single_property():
    prompt = probe._build_prompt(
        candidate_text="The supplied evidence does not establish semantic capability.",
        property_name="semantic_capability",
        evidence_id="case_p3_evidence",
    )
    assert "The supplied evidence does not establish semantic capability." in prompt
    assert "semantic_capability" in prompt
    assert "not_asserted" in prompt
    assert "evidence prose" not in prompt.lower()
    assert "frozen_experiment_gold" not in prompt
    assert "transport_qualification_implies_semantic_capability_not_established_v1" not in prompt


def test_compile_not_asserted_emits_no_ir():
    assert probe.compile_classification_to_typed_assertions(
        property_name="semantic_capability",
        assertion_status="not_asserted",
        evidence_id="case_p2_evidence",
    ) == []


def test_run_case_validates_and_preserves_schema(tmp_path: Path):
    candidate = tmp_path / "candidate.txt"
    candidate.write_text("The supplied evidence establishes semantic capability.", encoding="utf-8")
    case = probe.ClassificationCase(
        case_id="p1",
        candidate_path=candidate,
        property_name="semantic_capability",
        gold_status="established",
        evidence_id="case_p1_evidence",
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
                                    "property": "semantic_capability",
                                    "assertion_status": "established",
                                }
                            )
                        },
                    }
                ],
                "usage": {"prompt_tokens": 7, "completion_tokens": 4, "total_tokens": 11},
            }
        )

    with patch.object(probe.urllib.request, "urlopen", side_effect=fake_urlopen):
        result = probe.run_case(
            case=case,
            endpoint="http://127.0.0.1:8080/v1",
            model="test-model",
            out_dir=out_dir,
            max_tokens=32,
            temperature=0.0,
            timeout_seconds=5,
        )

    request_body = seen["body"]
    assert request_body["response_format"]["json_schema"]["schema"] == json.loads(
        probe.SCHEMA_PATH.read_text(encoding="utf-8")
    )
    prompt = request_body["messages"][0]["content"]
    assert "semantic_capability" in prompt
    assert "not_asserted" in prompt
    assert "transport_qualification" not in prompt
    assert "The supplied evidence establishes semantic capability." in prompt
    assert "frozen_experiment_gold" not in prompt
    assert "transport_qualification_implies_semantic_capability_not_established_v1" not in prompt
    validation = json.loads((out_dir / "validation.json").read_text(encoding="utf-8"))
    assert validation["overall_validation_status"] == "passed"
    assert validation["semantic_score_status"] == "scored"
    assert result["validation"]["overall_validation_status"] == "passed"


def test_run_case_marks_mechanical_failure_not_scored(tmp_path: Path):
    candidate = tmp_path / "candidate.txt"
    candidate.write_text("The supplied evidence establishes semantic capability.", encoding="utf-8")
    case = probe.ClassificationCase(
        case_id="p1",
        candidate_path=candidate,
        property_name="semantic_capability",
        gold_status="established",
        evidence_id="case_p1_evidence",
    )
    out_dir = tmp_path / "out"

    class BadJsonResponse(_FakeResponse):
        def __init__(self):
            super().__init__(
                {
                    "choices": [
                        {
                            "finish_reason": "length",
                            "message": {"content": '{"property": "semantic_capability"'},
                        }
                    ],
                    "usage": {"prompt_tokens": 7, "completion_tokens": 32, "total_tokens": 39},
                }
            )

    with patch.object(probe.urllib.request, "urlopen", return_value=BadJsonResponse()):
        probe.run_case(
            case=case,
            endpoint="http://127.0.0.1:8080/v1",
            model="test-model",
            out_dir=out_dir,
            max_tokens=32,
            temperature=0.0,
            timeout_seconds=5,
        )

    validation = json.loads((out_dir / "validation.json").read_text(encoding="utf-8"))
    assert validation["overall_validation_status"] == "failed"
    assert validation["semantic_score_status"] == "not_scored"
    assert validation["semantic_score_reason"] == "mechanical_output_failure"
