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
    assert "transport_qualification" not in prompt
    assert "bounded_handoff_success" not in prompt
    assert "raw_response_integrity" not in prompt
    assert "semantic_acceptance" not in prompt
    assert "frozen_experiment_gold" not in prompt
    assert "transport_qualification_implies_semantic_capability_not_established_v1" not in prompt


def test_effective_request_uses_case_specific_schema_and_template_hashes(tmp_path: Path):
    candidate = tmp_path / "candidate.txt"
    candidate.write_text("The supplied evidence establishes semantic capability.", encoding="utf-8")
    gold = tmp_path / "gold.json"
    gold.write_text(
        json.dumps(
            {
                "case_id": "semantic_capability_case",
                "property": "semantic_capability",
                "assertion_status": "established",
                "evidence_id": "case_semantic_capability_evidence",
                "typing_source": "frozen_experiment_gold",
                "source_candidate_path": str(candidate),
                "source_candidate_sha256": probe._sha256_text(candidate.read_text(encoding="utf-8")),
            }
        ),
        encoding="utf-8",
    )
    case = probe.ClassificationCase(
        case_id="semantic_capability_case",
        candidate_path=candidate,
        property_name="semantic_capability",
        gold_path=gold,
        evidence_id="case_semantic_capability_evidence",
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
        probe.run_case(
            case=case,
            endpoint="http://127.0.0.1:8080/v1",
            model="test-model",
            out_dir=out_dir,
            max_tokens=32,
            temperature=0.0,
            timeout_seconds=5,
        )

    request_body = seen["body"]
    schema = request_body["response_format"]["json_schema"]["schema"]
    assert schema["properties"]["property"]["enum"] == ["semantic_capability"]
    assert probe._schema_sha256(schema) == json.loads((out_dir / "model_call.json").read_text(encoding="utf-8"))["effective_schema_sha256"]
    assert probe.SCHEMA_TEMPLATE["properties"]["property"]["enum"] == [
        "transport_qualification",
        "bounded_handoff_success",
        "semantic_capability",
        "raw_response_integrity",
        "semantic_acceptance",
    ]
    request_dump = json.dumps(request_body)
    assert "transport_qualification" not in request_dump
    assert "bounded_handoff_success" not in request_dump
    assert "raw_response_integrity" not in request_dump
    assert "semantic_acceptance" not in request_dump
    assert "frozen_experiment_gold" not in request_dump
    assert "transport_qualification_implies_semantic_capability_not_established_v1" not in request_dump


def test_compile_not_asserted_emits_no_ir():
    assert probe._compile_to_typed_assertions(
        property_name="semantic_capability",
        assertion_status="not_asserted",
        evidence_id="case_p2_evidence",
    ) == []


def _write_gold(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_run_case_validates_and_preserves_schema(tmp_path: Path):
    candidate = tmp_path / "candidate.txt"
    candidate.write_text("The supplied evidence establishes semantic capability.", encoding="utf-8")
    gold = tmp_path / "gold.json"
    _write_gold(
        gold,
        {
            "case_id": "semantic_capability_case",
            "property": "semantic_capability",
            "assertion_status": "established",
            "evidence_id": "case_semantic_capability_evidence",
            "typing_source": "frozen_experiment_gold",
            "source_candidate_path": str(candidate),
            "source_candidate_sha256": probe._sha256_text(candidate.read_text(encoding="utf-8")),
        },
    )
    case = probe.ClassificationCase(
        case_id="semantic_capability_case",
        candidate_path=candidate,
        property_name="semantic_capability",
        gold_path=gold,
        evidence_id="case_semantic_capability_evidence",
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
    schema = request_body["response_format"]["json_schema"]["schema"]
    assert schema["properties"]["property"]["enum"] == ["semantic_capability"]
    assert probe._schema_sha256(schema) == json.loads((out_dir / "model_call.json").read_text(encoding="utf-8"))["effective_schema_sha256"]
    assert probe.SCHEMA_TEMPLATE["properties"]["property"]["enum"] == [
        "transport_qualification",
        "bounded_handoff_success",
        "semantic_capability",
        "raw_response_integrity",
        "semantic_acceptance",
    ]
    assert "transport_qualification" not in json.dumps(schema)
    assert "bounded_handoff_success" not in json.dumps(schema)
    assert "raw_response_integrity" not in json.dumps(schema)
    assert "semantic_acceptance" not in json.dumps(schema)
    prompt = request_body["messages"][0]["content"]
    assert "semantic_capability" in prompt
    assert "not_asserted" in prompt
    assert "transport_qualification" not in prompt
    assert "bounded_handoff_success" not in prompt
    assert "raw_response_integrity" not in prompt
    assert "semantic_acceptance" not in prompt
    assert "The supplied evidence establishes semantic capability." in prompt
    assert "frozen_experiment_gold" not in prompt
    assert "transport_qualification_implies_semantic_capability_not_established_v1" not in prompt
    request_dump = json.dumps(request_body)
    assert "frozen_experiment_gold" not in request_dump
    assert "transport_qualification_implies_semantic_capability_not_established_v1" not in request_dump
    validation = json.loads((out_dir / "validation.json").read_text(encoding="utf-8"))
    assert validation["overall_validation_status"] == "passed"
    assert validation["semantic_score_status"] == "scored"
    assert result["validation"]["overall_validation_status"] == "passed"
    assert result["validation"]["semantic_match"] is True


def test_run_case_marks_mechanical_failure_not_scored(tmp_path: Path):
    candidate = tmp_path / "candidate.txt"
    candidate.write_text("The supplied evidence establishes semantic capability.", encoding="utf-8")
    gold = tmp_path / "gold.json"
    _write_gold(
        gold,
        {
            "case_id": "semantic_capability_case",
            "property": "semantic_capability",
            "assertion_status": "established",
            "evidence_id": "case_semantic_capability_evidence",
            "typing_source": "frozen_experiment_gold",
            "source_candidate_path": str(candidate),
            "source_candidate_sha256": probe._sha256_text(candidate.read_text(encoding="utf-8")),
        },
    )
    case = probe.ClassificationCase(
        case_id="semantic_capability_case",
        candidate_path=candidate,
        property_name="semantic_capability",
        gold_path=gold,
        evidence_id="case_semantic_capability_evidence",
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


def test_compile_established_and_not_established_emit_ir():
    assert probe._compile_to_typed_assertions(
        property_name="semantic_capability",
        assertion_status="established",
        evidence_id="case_p1_evidence",
    ) == [
        {
            "property": "semantic_capability",
            "epistemic_status": "established",
            "evidence_refs": ["case_p1_evidence"],
        }
    ]


def test_run_case_rejects_bad_gold_binding_before_transport(tmp_path: Path):
    candidate = tmp_path / "candidate.txt"
    candidate.write_text("The supplied evidence establishes semantic capability.", encoding="utf-8")
    good_candidate_sha = probe._sha256_text(candidate.read_text(encoding="utf-8"))
    base_gold = {
        "case_id": "semantic_capability_case",
        "property": "semantic_capability",
        "assertion_status": "established",
        "evidence_id": "case_semantic_capability_evidence",
        "typing_source": "frozen_experiment_gold",
        "source_candidate_path": str(candidate),
        "source_candidate_sha256": good_candidate_sha,
    }
    cases = [
        ("property", {**base_gold, "property": "transport_qualification"}, "gold property must equal queried property"),
        ("evidence", {**base_gold, "evidence_id": "wrong_evidence"}, "gold evidence_id must equal case.evidence_id"),
        ("candidate_sha", {**base_gold, "source_candidate_sha256": "0" * 64}, "gold source_candidate_sha256 must match candidate content"),
        ("case_id", {**base_gold, "case_id": "wrong_case_id"}, "gold case_id must equal case.case_id"),
    ]
    for suffix, gold_payload, expected_message in cases:
        gold = tmp_path / f"gold_{suffix}.json"
        _write_gold(gold, gold_payload)
        case = probe.ClassificationCase(
            case_id="semantic_capability_case",
            candidate_path=candidate,
            property_name="semantic_capability",
            gold_path=gold,
            evidence_id="case_semantic_capability_evidence",
        )
        called = False

        def fail_call(*args, **kwargs):  # noqa: ANN001, ANN003
            nonlocal called
            called = True
            raise AssertionError("transport should not be reached for bad gold binding")

        with patch.object(probe, "_call_local", side_effect=fail_call):
            try:
                probe.run_case(
                    case=case,
                    endpoint="http://127.0.0.1:8080/v1",
                    model="test-model",
                    out_dir=tmp_path / f"out_{suffix}",
                    max_tokens=32,
                    temperature=0.0,
                    timeout_seconds=5,
                )
            except ValueError as exc:
                assert expected_message in str(exc)
            else:
                raise AssertionError("expected ValueError for bad gold binding")
        assert called is False
    assert probe._compile_to_typed_assertions(
        property_name="semantic_capability",
        assertion_status="not_established",
        evidence_id="case_p1_evidence",
    ) == [
        {
            "property": "semantic_capability",
            "epistemic_status": "not_established",
            "evidence_refs": ["case_p1_evidence"],
        }
    ]
