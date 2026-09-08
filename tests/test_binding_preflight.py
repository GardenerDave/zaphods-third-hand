from __future__ import annotations

import json
import socket
import urllib.error
from pathlib import Path

import pytest

from local_harness.binding_preflight import preflight_worker_binding


class FakeResponse:
    def __init__(self, payload: object, status: int = 200):
        self.payload = payload
        self.status = status

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_preflight_verifies_expected_model():
    result = preflight_worker_binding(
        worker="router",
        configured_base_url="http://127.0.0.1:8081/v1",
        expected_model="Qwen_Qwen3-1.7B-Q4_K_M.gguf",
        opener=lambda request, timeout=30: FakeResponse({"data": [{"id": "Qwen_Qwen3-1.7B-Q4_K_M.gguf"}]}),
    )
    assert result["binding_status"] == "VERIFIED"
    assert result["failure_class"] == "binding_verified"
    assert result["advertised_models"] == ["Qwen_Qwen3-1.7B-Q4_K_M.gguf"]


def test_preflight_detects_wrong_model():
    result = preflight_worker_binding(
        worker="handoff",
        configured_base_url="http://127.0.0.1:8080/v1",
        expected_model="Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf",
        opener=lambda request, timeout=30: FakeResponse({"data": [{"id": "other-model.gguf"}]}),
    )
    assert result["binding_status"] == "UNVERIFIED"
    assert result["failure_class"] == "expected_model_not_advertised"


@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        (OSError(113, "No route to host"), "no_route"),
        (OSError(111, "Connection refused"), "connection_refused"),
        (socket.timeout("timed out"), "timeout"),
    ],
)
def test_preflight_classifies_transport_failures(reason, expected):
    def opener(request, timeout=30):
        raise urllib.error.URLError(reason)

    result = preflight_worker_binding(
        worker="router",
        configured_base_url="http://127.0.0.1:8081/v1",
        expected_model="Qwen_Qwen3-1.7B-Q4_K_M.gguf",
        opener=opener,
    )
    assert result["binding_status"] == "UNVERIFIED"
    assert result["failure_class"] == expected


def test_preflight_marks_malformed_models_response_unverified():
    result = preflight_worker_binding(
        worker="router",
        configured_base_url="http://127.0.0.1:8081/v1",
        expected_model="Qwen_Qwen3-1.7B-Q4_K_M.gguf",
        opener=lambda request, timeout=30: FakeResponse({"not_data": []}),
    )
    assert result["binding_status"] == "UNVERIFIED"
    assert result["failure_class"] == "malformed_response"


def test_preflight_handles_http_error_as_models_endpoint_error():
    def opener(request, timeout=30):
        raise urllib.error.HTTPError(request.full_url, 503, "service unavailable", hdrs=None, fp=None)

    result = preflight_worker_binding(
        worker="router",
        configured_base_url="http://127.0.0.1:8081/v1",
        expected_model="Qwen_Qwen3-1.7B-Q4_K_M.gguf",
        opener=opener,
    )
    assert result["binding_status"] == "UNVERIFIED"
    assert result["failure_class"] == "models_endpoint_error"
