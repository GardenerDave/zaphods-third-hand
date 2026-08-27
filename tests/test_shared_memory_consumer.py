from __future__ import annotations

import hashlib
import json
from pathlib import Path

from historian.shared_memory_consumer import (
    DEFAULT_WORK_DIR_ROOT,
    build_model_request,
    build_worker_schema,
    canonical_bytes,
    question_fingerprint,
    query,
    retrieve_evidence,
    validate_worker_payload,
)


ROOT = Path(__file__).resolve().parents[1]


class FakeResponse:
    def __init__(self, payload: bytes, status: int = 200) -> None:
        self._payload = payload
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def read(self) -> bytes:
        return self._payload


class RecordingOpener:
    def __init__(self, responses: dict[str, bytes]) -> None:
        self.responses = responses
        self.calls: list[dict[str, object]] = []

    def __call__(self, request, timeout: int | None = None):
        body = json.loads(request.data.decode("utf-8")) if request.data else None
        record = {"url": request.full_url, "body": body, "timeout": timeout}
        self.calls.append(record)
        for suffix, payload in self.responses.items():
            if request.full_url.endswith(suffix):
                return FakeResponse(payload)
        raise AssertionError(f"unexpected URL {request.full_url}")


def _historian_payload(**overrides):
    payload = {
        "api_version": "v1",
        "request_id": "hist-001",
        "status": "ok",
        "question": "why was V2 capability considered unmeasured?",
        "question_fingerprint": "hist-fingerprint",
        "selected_record_ids": ["CLM-v2-unmeasured", "EVT-v2-acquisition"],
        "evidence": [{"id": "CLM-v2-unmeasured"}, {"id": "EVT-v2-acquisition"}],
        "retrieval_provenance_by_channel": {"semantic": {"selected": ["CLM-v2-unmeasured"]}, "structured": {"selected": ["EVT-v2-acquisition"]}},
        "parsed_constraints": {"task_class": "historical_fact_recovery"},
    }
    payload.update(overrides)
    return payload


def _model_payload(content: str) -> bytes:
    return json.dumps(
        {
            "choices": [
                {
                    "message": {
                        "content": content,
                    }
                }
            ],
            "usage": {"prompt_tokens": 17, "completion_tokens": 11, "total_tokens": 28},
            "finish_reason": "stop",
        }
    ).encode("utf-8")


def test_question_fingerprint_is_stable() -> None:
    assert question_fingerprint("  Why was V2 capability considered unmeasured?  ") == question_fingerprint("Why was V2   capability considered unmeasured?")


def test_build_worker_schema_binds_selected_ids_exactly() -> None:
    schema = build_worker_schema(["A", "B", "A"])
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "answer",
        "cited_record_ids",
        "evidence_used",
        "uncertainty_or_limitations",
        "contradictions_or_missing_evidence",
    }
    assert schema["properties"]["cited_record_ids"]["items"]["enum"] == ["A", "B"]
    assert schema["properties"]["evidence_used"]["items"]["enum"] == ["A", "B"]
    payload = json.dumps(schema)
    assert "expected_record_ids" not in payload
    assert "required_citation_ids" not in payload


def test_build_model_request_contains_only_allowed_id_schema() -> None:
    evidence = _historian_payload()
    request = build_model_request("Why was V2 capability considered unmeasured?", evidence, model_id="model-x", selected_record_ids=["CLM-v2-unmeasured", "EVT-v2-acquisition"])
    schema = request["response_format"]["json_schema"]["schema"]
    assert schema["properties"]["cited_record_ids"]["items"]["enum"] == ["CLM-v2-unmeasured", "EVT-v2-acquisition"]
    request_text = json.dumps(request)
    assert "expected_record_ids" not in request_text
    assert "required_citation_ids" not in request_text
    assert "answer_mode" not in request_text
    assert "forbidden_misconception" not in request_text


def test_validate_worker_payload_rejects_unsupported_ids_and_keeps_selected_ids_separate() -> None:
    selected = ["A", "B"]
    valid = {
        "answer": "ok",
        "cited_record_ids": ["A"],
        "evidence_used": ["A"],
        "uncertainty_or_limitations": "",
        "contradictions_or_missing_evidence": [],
    }
    result = validate_worker_payload(selected, valid)
    assert result["contract_valid"] is True
    assert result["schema_valid"] is True
    assert result["grounding_valid"] is True

    bad = dict(valid)
    bad["cited_record_ids"] = ["Z"]
    bad["evidence_used"] = ["Z"]
    result = validate_worker_payload(selected, bad)
    assert result["contract_valid"] is False
    assert result["grounding_valid"] is False
    assert any("unsupported cited IDs" in error for error in result["errors"])

    bad = dict(valid)
    bad["cited_record_ids"] = ["A", "A"]
    result = validate_worker_payload(selected, bad)
    assert result["contract_valid"] is False
    assert any("unique" in error for error in result["errors"])


def test_retrieve_evidence_normalizes_hybrid_record_ids() -> None:
    opener = RecordingOpener({"/v1/evidence": json.dumps(_historian_payload(selected_record_ids=[], hybrid_record_ids=["X", "Y"])).encode("utf-8")})
    payload = retrieve_evidence("question text", historian_base_url="http://historian.example", opener=opener)
    assert payload["selected_record_ids"] == ["X", "Y"]
    assert opener.calls[0]["url"].endswith("/v1/evidence")


def test_query_uses_evidence_endpoint_and_persists_artifacts(tmp_path: Path) -> None:
    historian = RecordingOpener(
        {
            "/v1/evidence": json.dumps(_historian_payload(request_id="hist-001", question_fingerprint="fp-hist", selected_record_ids=["CLM-v2-unmeasured", "EVT-v2-acquisition"])).encode("utf-8"),
            "/chat/completions": _model_payload(
                json.dumps(
                    {
                        "answer": "Because the transport failure only proved the transport boundary.",
                        "cited_record_ids": ["CLM-v2-unmeasured"],
                        "evidence_used": ["CLM-v2-unmeasured"],
                        "uncertainty_or_limitations": "",
                        "contradictions_or_missing_evidence": [],
                    }
                )
            ),
        }
    )
    result = query(
        "Why was V2 capability considered unmeasured?",
        model_id="Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf",
        model_base_url="http://model.example/v1",
        historian_base_url="http://historian.example",
        timeout=30,
        work_dir_root=tmp_path,
        request_label="consumer-1",
        historian_opener=historian,
        model_opener=historian,
    )
    assert result["consumer_request_id"] == "consumer-1"
    assert result["request_id"] == "consumer-1"
    assert result["historian_request_id"] == "hist-001"
    assert result["question_fingerprint"] == "fp-hist"
    assert result["cited_record_ids"] == ["CLM-v2-unmeasured"]
    assert result["evidence_used"] == ["CLM-v2-unmeasured"]
    assert result["validation"]["contract_valid"] is True
    assert result["status"] == "ok"
    assert [call["url"] for call in historian.calls] == ["http://historian.example/v1/evidence", "http://model.example/v1/chat/completions"]

    request_dir = tmp_path / "consumer-1"
    for name in ("question.json", "historian_evidence_response.json", "model_request.json", "model_request.raw", "model_response.raw", "model_response.json", "parsed_result.json", "validation.json", "manifest.json"):
        assert (request_dir / name).exists(), name
    manifest = json.loads((request_dir / "manifest.json").read_text())
    assert manifest["worker_contract_version"] == "shared_memory_worker_v2"
    assert manifest["consumer_request_id"] == "consumer-1"
    assert manifest["historian_request_id"] == "hist-001"
    assert manifest["completion_status"] == "ok"
    assert manifest["request_sha256"] == hashlib.sha256((request_dir / "model_request.raw").read_bytes()).hexdigest()
    model_request = json.loads((request_dir / "model_request.json").read_text())
    schema = model_request["response_format"]["json_schema"]["schema"]
    assert schema["properties"]["cited_record_ids"]["items"]["enum"] == ["CLM-v2-unmeasured", "EVT-v2-acquisition"]
    request_text = json.dumps(model_request)
    assert "expected_record_ids" not in request_text
    assert "required_citation_ids" not in request_text
    assert "answer_mode" not in request_text
    assert "forbidden_misconception" not in request_text


def test_query_malformed_model_response_fails_cleanly(tmp_path: Path) -> None:
    historian = RecordingOpener(
        {
            "/v1/evidence": json.dumps(_historian_payload(request_id="hist-002", question_fingerprint="fp-hist-2", selected_record_ids=["A"])).encode("utf-8"),
            "/chat/completions": b"not-json",
        }
    )
    result = query(
        "Why was transport qualification a prerequisite?",
        model_id="Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf",
        model_base_url="http://model.example/v1",
        historian_base_url="http://historian.example",
        work_dir_root=tmp_path,
        request_label="consumer-2",
        historian_opener=historian,
        model_opener=historian,
    )
    assert result["status"] == "failed"
    assert result["error_code"] == "PARSE_FAILURE"
    assert result["validation"]["contract_valid"] is False
    assert (tmp_path / "consumer-2" / "model_response.raw").exists()


def test_default_runtime_artifacts_live_under_dot_work() -> None:
    assert str(DEFAULT_WORK_DIR_ROOT).startswith(".work")
