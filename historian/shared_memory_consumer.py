from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable, Mapping
from uuid import uuid4


WORKER_CONTRACT_VERSION = "shared_memory_worker_v2"
DEFAULT_HISTORIAN_BASE_URL = "http://127.0.0.1:8765"
DEFAULT_MODEL_TIMEOUT_SECONDS = 120
DEFAULT_WORK_DIR_ROOT = Path(".work") / "historian_shared_memory_worker"
DEFAULT_GENERATION_SETTINGS = {
    "temperature": 0,
    "top_p": 1,
    "seed": 42,
    "max_tokens": 1536,
    "stream": False,
    "timeout": DEFAULT_MODEL_TIMEOUT_SECONDS,
}
ANSWER_KEYS = (
    "answer",
    "cited_record_ids",
    "evidence_used",
    "uncertainty_or_limitations",
    "contradictions_or_missing_evidence",
)


class SharedMemoryConsumerError(RuntimeError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def question_fingerprint(question: str) -> str:
    normalized = " ".join(question.split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", delete=False, dir=str(path.parent)) as tmp:
        tmp.write(data)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def _atomic_write_json(path: Path, value: Any) -> None:
    _atomic_write_bytes(path, json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n")


def build_worker_schema(record_ids: list[str]) -> dict[str, Any]:
    allowed = list(dict.fromkeys(record_ids))
    allowed_items = {"type": "string", "enum": allowed}
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(ANSWER_KEYS),
        "properties": {
            "answer": {"type": "string"},
            "cited_record_ids": {
                "type": "array",
                "items": allowed_items,
                "uniqueItems": True,
            },
            "evidence_used": {
                "type": "array",
                "items": allowed_items,
                "uniqueItems": True,
            },
            "uncertainty_or_limitations": {"type": "string"},
            "contradictions_or_missing_evidence": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
    }


def build_model_request(
    question: str,
    historian_evidence: Mapping[str, Any],
    *,
    model_id: str,
    selected_record_ids: list[str],
    generation_settings: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    settings = dict(DEFAULT_GENERATION_SETTINGS)
    if generation_settings:
        settings.update(generation_settings)
    schema = build_worker_schema(selected_record_ids)
    system_prompt = (
        "You are a read-only Historian worker. Use only the supplied evidence. "
        "Return exactly one JSON object matching the schema. "
        "Cite only stable Historian record IDs from the supplied evidence. "
        "Do not invent external facts. "
        "If the evidence is insufficient, say so explicitly in uncertainty_or_limitations."
    )
    user_prompt = json.dumps(
        {
            "question": question,
            "historian_evidence": historian_evidence,
            "allowed_record_ids": selected_record_ids,
            "output_contract": {
                "worker_contract_version": WORKER_CONTRACT_VERSION,
                "answer_keys": list(ANSWER_KEYS),
            },
        },
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    )
    return {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": settings["temperature"],
        "top_p": settings["top_p"],
        "seed": settings["seed"],
        "max_tokens": settings["max_tokens"],
        "stream": settings["stream"],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "historian_shared_memory_worker_v2",
                "strict": True,
                "schema": schema,
            },
        },
    }


def _endpoint(url: str, suffix: str) -> str:
    return f"{url.rstrip('/')}{suffix}"


def _post_json(url: str, payload: Mapping[str, Any], *, timeout: int, opener: Callable[..., Any] = urllib.request.urlopen) -> tuple[int, bytes]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with opener(req, timeout=timeout) as response:  # nosec: B310 - configured local endpoint only
        return getattr(response, "status", 200), response.read()


def _load_json_bytes(raw: bytes) -> Any:
    return json.loads(raw.decode("utf-8"))


def _extract_model_content(model_response: Mapping[str, Any]) -> str | Mapping[str, Any]:
    if "choices" in model_response and isinstance(model_response["choices"], list) and model_response["choices"]:
        choice = model_response["choices"][0]
        if isinstance(choice, Mapping):
            message = choice.get("message")
            if isinstance(message, Mapping) and isinstance(message.get("content"), str):
                return message["content"]
            if isinstance(choice.get("text"), str):
                return choice["text"]
    if isinstance(model_response.get("content"), str):
        return model_response["content"]
    if isinstance(model_response, Mapping) and all(key in model_response for key in ANSWER_KEYS):
        return model_response
    raise SharedMemoryConsumerError("model response missing structured content")


def _parse_worker_content(content: str | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(content, Mapping):
        result = dict(content)
    else:
        result = json.loads(content)
    if not isinstance(result, dict):
        raise SharedMemoryConsumerError("worker content must be a JSON object")
    return result


def validate_worker_payload(selected_record_ids: list[str], payload: Mapping[str, Any]) -> dict[str, Any]:
    selected_set = set(selected_record_ids)
    result = {
        "schema_valid": False,
        "grounding_valid": False,
        "contract_valid": False,
        "errors": [],
    }
    if not isinstance(payload, Mapping):
        result["errors"].append("payload must be an object")
        return result
    if set(payload) != set(ANSWER_KEYS):
        result["errors"].append("payload must contain exactly the five worker keys")
        return result
    if not isinstance(payload["answer"], str):
        result["errors"].append("answer must be a string")
    if not isinstance(payload["uncertainty_or_limitations"], str):
        result["errors"].append("uncertainty_or_limitations must be a string")
    if not isinstance(payload["contradictions_or_missing_evidence"], list) or not all(isinstance(item, str) for item in payload["contradictions_or_missing_evidence"]):
        result["errors"].append("contradictions_or_missing_evidence must be a list[str]")
    cited = payload["cited_record_ids"]
    evidence = payload["evidence_used"]
    if not isinstance(cited, list) or not all(isinstance(item, str) for item in cited):
        result["errors"].append("cited_record_ids must be a list[str]")
    if not isinstance(evidence, list) or not all(isinstance(item, str) for item in evidence):
        result["errors"].append("evidence_used must be a list[str]")
    if result["errors"]:
        return result
    if len(cited) != len(set(cited)):
        result["errors"].append("cited_record_ids must be unique")
    if len(evidence) != len(set(evidence)):
        result["errors"].append("evidence_used must be unique")
    unsupported_cited = [item for item in cited if item not in selected_set]
    unsupported_evidence = [item for item in evidence if item not in selected_set]
    if unsupported_cited:
        result["errors"].append(f"unsupported cited IDs: {unsupported_cited}")
    if unsupported_evidence:
        result["errors"].append(f"unsupported evidence IDs: {unsupported_evidence}")
    if not set(cited).issubset(set(evidence)):
        result["errors"].append("cited_record_ids must be a subset of evidence_used")
    result["schema_valid"] = not any(msg.startswith(("answer must", "uncertainty_or_limitations must", "contradictions_or_missing_evidence must", "cited_record_ids must be a list", "evidence_used must be a list", "payload must contain exactly", "payload must be an object")) for msg in result["errors"])
    result["grounding_valid"] = not any(msg.startswith(("cited_record_ids must be unique", "evidence_used must be unique", "unsupported cited IDs:", "unsupported evidence IDs:", "cited_record_ids must be a subset of evidence_used")) for msg in result["errors"])
    result["contract_valid"] = result["schema_valid"] and result["grounding_valid"]
    return result


def _validation_error_code(validation: Mapping[str, Any]) -> str:
    errors = [str(item) for item in validation.get("errors", [])]
    if any("unsupported cited IDs" in msg or "unsupported evidence IDs" in msg or "subset of evidence_used" in msg for msg in errors):
        return "CITATION_ID_FAILURE"
    if any("must contain exactly the five worker keys" in msg or "must be a string" in msg or "must be a list[str]" in msg for msg in errors):
        return "SCHEMA_FAILURE"
    if any("must be unique" in msg for msg in errors):
        return "WORKER_CONTRACT_FAILURE"
    return "WORKER_CONTRACT_FAILURE"


def retrieve_evidence(
    question: str,
    *,
    historian_base_url: str = DEFAULT_HISTORIAN_BASE_URL,
    timeout: int = DEFAULT_MODEL_TIMEOUT_SECONDS,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> dict[str, Any]:
    url = _endpoint(historian_base_url, "/v1/evidence")
    status, raw = _post_json(url, {"question": question}, timeout=timeout, opener=opener)
    if status >= 400:
        raise SharedMemoryConsumerError(f"historian evidence request failed with HTTP {status}")
    payload = _load_json_bytes(raw)
    if not isinstance(payload, dict):
        raise SharedMemoryConsumerError("historian evidence response must be an object")
    if isinstance(payload.get("hybrid_record_ids"), list) and not payload.get("selected_record_ids"):
        payload["selected_record_ids"] = list(payload["hybrid_record_ids"])
    elif "selected_record_ids" not in payload:
        payload["selected_record_ids"] = []
    if "question_fingerprint" not in payload:
        payload["question_fingerprint"] = question_fingerprint(question)
    return payload


def _model_response_url(model_base_url: str) -> str:
    return _endpoint(model_base_url, "/chat/completions")


def query(
    question: str,
    *,
    model_id: str,
    model_base_url: str,
    historian_base_url: str = DEFAULT_HISTORIAN_BASE_URL,
    historian_evidence: Mapping[str, Any] | None = None,
    timeout: int = DEFAULT_MODEL_TIMEOUT_SECONDS,
    work_dir_root: Path | None = DEFAULT_WORK_DIR_ROOT,
    request_label: str | None = None,
    consumer_request_id: str | None = None,
    generation_settings: Mapping[str, Any] | None = None,
    historian_opener: Callable[..., Any] = urllib.request.urlopen,
    model_opener: Callable[..., Any] = urllib.request.urlopen,
) -> dict[str, Any]:
    consumer_request_id = consumer_request_id or request_label or f"consumer-{uuid4().hex}"
    started = time.monotonic()
    work_dir = None if work_dir_root is None else Path(work_dir_root) / consumer_request_id
    if work_dir is not None:
        work_dir.mkdir(parents=True, exist_ok=True)
        _atomic_write_json(work_dir / "question.json", {"question": question})
    historian_response = historian_evidence
    if historian_response is None:
        try:
            historian_response = retrieve_evidence(
                question,
                historian_base_url=historian_base_url,
                timeout=timeout,
                opener=historian_opener,
            )
        except Exception as exc:  # pragma: no cover - exercised in tests
            result = {
                "consumer_request_id": consumer_request_id,
                "request_id": consumer_request_id,
                "historian_request_id": None,
                "question_fingerprint": question_fingerprint(question),
                "model_id": model_id,
                "selected_record_ids": [],
                "status": "failed",
                "error_code": "retrieval_failed",
                "error": "historian evidence request failed",
                "validation": {
                    "schema_valid": False,
                    "grounding_valid": False,
                    "contract_valid": False,
                    "errors": [str(exc)],
                },
            }
            if work_dir is not None:
                _atomic_write_json(work_dir / "parsed_result.json", result)
                _atomic_write_json(work_dir / "validation.json", result["validation"])
                _atomic_write_json(
                    work_dir / "manifest.json",
                    {
                        "consumer_request_id": consumer_request_id,
                        "historian_request_id": None,
                        "question_fingerprint": result["question_fingerprint"],
                        "model_id": model_id,
                        "request_sha256": None,
                        "response_sha256": None,
                        "latency_seconds": round(time.monotonic() - started, 6),
                        "completion_status": "failed",
                        "worker_contract_version": WORKER_CONTRACT_VERSION,
                    },
                )
            return result
    else:
        if not isinstance(historian_response, Mapping):
            raise SharedMemoryConsumerError("historian_evidence must be a mapping when supplied")
        historian_response = dict(historian_response)
        if "selected_record_ids" not in historian_response:
            if isinstance(historian_response.get("hybrid_record_ids"), list):
                historian_response["selected_record_ids"] = list(historian_response["hybrid_record_ids"])
            else:
                historian_response["selected_record_ids"] = []
        if "question_fingerprint" not in historian_response:
            historian_response["question_fingerprint"] = question_fingerprint(question)
    if historian_response is not None and work_dir is not None:
        _atomic_write_json(work_dir / "historian_evidence_response.json", historian_response)
    if historian_response is None:
        raise SharedMemoryConsumerError("historian evidence response missing")
    historian_request_id = historian_response.get("request_id") or historian_response.get("historian_request_id") or historian_response.get("id")
    question_fp = historian_response.get("question_fingerprint") or question_fingerprint(question)
    selected_record_ids = list(historian_response.get("selected_record_ids", []))
    request_payload = build_model_request(
        question,
        historian_response,
        model_id=model_id,
        selected_record_ids=selected_record_ids,
        generation_settings=generation_settings,
    )
    request_bytes = canonical_bytes(request_payload)
    if work_dir is not None:
        _atomic_write_json(work_dir / "model_request.json", request_payload)
        _atomic_write_bytes(work_dir / "model_request.raw", request_bytes)
    try:
        raw_status, raw_response = _post_json(_model_response_url(model_base_url), request_payload, timeout=timeout, opener=model_opener)
    except Exception as exc:  # pragma: no cover - exercised in tests
        result = {
            "consumer_request_id": consumer_request_id,
            "request_id": consumer_request_id,
            "historian_request_id": historian_request_id,
            "question_fingerprint": question_fp,
            "model_id": model_id,
            "selected_record_ids": selected_record_ids,
            "status": "failed",
            "error_code": "reasoner_unavailable",
            "error": "reasoner endpoint unavailable",
            "validation": {
                "schema_valid": False,
                "grounding_valid": False,
                "contract_valid": False,
                "errors": [str(exc)],
            },
        }
        if work_dir is not None:
            _atomic_write_json(work_dir / "parsed_result.json", result)
            _atomic_write_json(work_dir / "validation.json", result["validation"])
            _atomic_write_json(
                work_dir / "manifest.json",
                {
                    "consumer_request_id": consumer_request_id,
                    "historian_request_id": historian_request_id,
                    "question_fingerprint": question_fp,
                    "model_id": model_id,
                    "request_sha256": hashlib.sha256(request_bytes).hexdigest(),
                    "response_sha256": None,
                    "latency_seconds": round(time.monotonic() - started, 6),
                    "completion_status": "failed",
                    "worker_contract_version": WORKER_CONTRACT_VERSION,
                },
            )
        return result
    response_sha256 = hashlib.sha256(raw_response).hexdigest()
    if work_dir is not None:
        _atomic_write_bytes(work_dir / "model_response.raw", raw_response)
    model_response: dict[str, Any] | None = None
    parse_error: str | None = None
    try:
        parsed_model_response = _load_json_bytes(raw_response)
        if not isinstance(parsed_model_response, dict):
            raise SharedMemoryConsumerError("model response must be an object")
        model_response = parsed_model_response
        if work_dir is not None:
            _atomic_write_json(work_dir / "model_response.json", model_response)
    except Exception as exc:  # pragma: no cover - exercised via tests
        parse_error = str(exc)
        model_response = None
    if model_response is None:
        result = {
            "consumer_request_id": consumer_request_id,
            "request_id": consumer_request_id,
            "historian_request_id": historian_request_id,
            "question_fingerprint": question_fp,
            "model_id": model_id,
            "status": "failed",
            "error_code": "PARSE_FAILURE",
            "error": "model response was not parseable JSON",
            "selected_record_ids": selected_record_ids,
            "validation": {
                "schema_valid": False,
                "grounding_valid": False,
                "contract_valid": False,
                "errors": [parse_error or "model response parse failure"],
            },
        }
        if work_dir is not None:
            _atomic_write_json(work_dir / "parsed_result.json", result)
            _atomic_write_json(work_dir / "validation.json", result["validation"])
            _atomic_write_json(
                work_dir / "manifest.json",
                {
                    "consumer_request_id": consumer_request_id,
                    "historian_request_id": historian_request_id,
                    "question_fingerprint": question_fp,
                    "model_id": model_id,
                    "request_sha256": hashlib.sha256(request_bytes).hexdigest(),
                    "response_sha256": response_sha256,
                    "latency_seconds": round(time.monotonic() - started, 6),
                    "completion_status": "failed",
                    "worker_contract_version": WORKER_CONTRACT_VERSION,
                },
            )
        return result
    content = _extract_model_content(model_response)
    parsed_result = _parse_worker_content(content)
    validation = validate_worker_payload(selected_record_ids, parsed_result)
    result = {
        "consumer_request_id": consumer_request_id,
        "request_id": consumer_request_id,
        "historian_request_id": historian_request_id,
        "question_fingerprint": question_fp,
        "model_id": model_id,
        "selected_record_ids": selected_record_ids,
        "answer": parsed_result.get("answer"),
        "cited_record_ids": parsed_result.get("cited_record_ids"),
        "evidence_used": parsed_result.get("evidence_used"),
        "uncertainty_or_limitations": parsed_result.get("uncertainty_or_limitations"),
        "contradictions_or_missing_evidence": parsed_result.get("contradictions_or_missing_evidence"),
        "validation": validation,
        "status": "ok" if validation["contract_valid"] else "failed",
        "error_code": None if validation["contract_valid"] else _validation_error_code(validation),
    }
    if work_dir is not None:
        _atomic_write_json(work_dir / "parsed_result.json", parsed_result)
        _atomic_write_json(work_dir / "validation.json", validation)
        _atomic_write_json(
            work_dir / "manifest.json",
            {
                "consumer_request_id": consumer_request_id,
                "historian_request_id": historian_request_id,
                "question_fingerprint": question_fp,
                "model_id": model_id,
                "request_sha256": hashlib.sha256(request_bytes).hexdigest(),
                "response_sha256": response_sha256,
                "latency_seconds": round(time.monotonic() - started, 6),
                "completion_status": "ok" if validation["contract_valid"] else "failed",
                "worker_contract_version": WORKER_CONTRACT_VERSION,
            },
        )
    return result
