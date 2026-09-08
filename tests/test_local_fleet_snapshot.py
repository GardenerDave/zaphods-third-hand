from __future__ import annotations

from local_harness.local_fleet_snapshot import collect_local_fleet_snapshot, verified_workers


class FakeResponse:
    def __init__(self, payload: object, status: int = 200):
        self.payload = payload
        self.status = status

    def read(self) -> bytes:
        import json

        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _opener_factory(responses):
    calls = []

    def opener(request, timeout=30):
        calls.append(request.full_url)
        response = responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    opener.calls = calls  # type: ignore[attr-defined]
    return opener


def test_multiple_configured_workers_produce_one_fleet_snapshot():
    opener = _opener_factory([
        FakeResponse({"data": [{"id": "Qwen_Qwen3-1.7B-Q4_K_M.gguf"}]}),
        FakeResponse({"data": [{"id": "wrong-model"}]}),
    ])
    snapshot = collect_local_fleet_snapshot(
        bindings=[
            {"worker": "router", "base_url": "http://127.0.0.1:8081/v1", "model": "Qwen_Qwen3-1.7B-Q4_K_M.gguf"},
            {"worker": "handoff", "base_url": "http://127.0.0.1:8083/v1", "model": "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf"},
        ],
        opener=opener,
    )
    assert snapshot["schema"] == "zth_local_fleet_snapshot_v1"
    assert [worker["worker"] for worker in snapshot["workers"]] == ["router", "handoff"]
    assert len(opener.calls) == 2


def test_verified_worker_is_available():
    snapshot = collect_local_fleet_snapshot(
        bindings=[{"worker": "router", "base_url": "http://127.0.0.1:8081/v1", "model": "Qwen_Qwen3-1.7B-Q4_K_M.gguf"}],
        opener=_opener_factory([FakeResponse({"data": [{"id": "Qwen_Qwen3-1.7B-Q4_K_M.gguf"}]})]),
    )
    worker = snapshot["workers"][0]
    assert worker["binding_status"] == "VERIFIED"
    assert worker["availability"] == "AVAILABLE"
    assert worker["advertised_models"] == ["Qwen_Qwen3-1.7B-Q4_K_M.gguf"]


def test_unreachable_worker_is_unavailable_without_capability_penalty():
    import urllib.error

    snapshot = collect_local_fleet_snapshot(
        bindings=[{"worker": "router", "base_url": "http://127.0.0.1:8081/v1", "model": "Qwen_Qwen3-1.7B-Q4_K_M.gguf"}],
        opener=_opener_factory([urllib.error.URLError(OSError(111, "Connection refused"))]),
    )
    worker = snapshot["workers"][0]
    assert worker["binding_status"] == "UNVERIFIED"
    assert worker["availability"] == "UNAVAILABLE"
    assert worker["failure_class"] == "connection_refused"


def test_wrong_advertised_model_remains_unverified():
    snapshot = collect_local_fleet_snapshot(
        bindings=[{"worker": "handoff", "base_url": "http://127.0.0.1:8083/v1", "model": "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf"}],
        opener=_opener_factory([FakeResponse({"data": [{"id": "other-model"}]})]),
    )
    worker = snapshot["workers"][0]
    assert worker["binding_status"] == "UNVERIFIED"
    assert worker["failure_class"] == "expected_model_not_advertised"


def test_stale_or_unknown_state_is_not_treated_as_verified():
    snapshot = collect_local_fleet_snapshot(
        bindings=[{"worker": "deep", "base_url": "http://127.0.0.1:8080/completion", "model": "Llama-3.3-70B-Instruct-Q4_K_M.gguf"}],
        opener=_opener_factory([]),
    )
    worker = snapshot["workers"][0]
    assert worker["binding_status"] == "UNVERIFIED"
    assert worker["availability"] == "UNKNOWN"
    assert worker["freshness"]["stale"] is True


def test_snapshot_preserves_individual_preflight_evidence():
    snapshot = collect_local_fleet_snapshot(
        bindings=[{"worker": "router", "base_url": "http://127.0.0.1:8081/v1", "model": "Qwen_Qwen3-1.7B-Q4_K_M.gguf"}],
        opener=_opener_factory([FakeResponse({"data": [{"id": "Qwen_Qwen3-1.7B-Q4_K_M.gguf"}]})]),
    )
    worker = snapshot["workers"][0]
    preflight = worker["evidence"]["preflight"]
    assert preflight["schema"] == "zth_worker_binding_preflight_v1"
    assert preflight["worker"] == "router"
    assert preflight["advertised_models"] == ["Qwen_Qwen3-1.7B-Q4_K_M.gguf"]
    assert preflight["binding_status"] == "VERIFIED"


def test_eligibility_adapter_does_not_admit_static_config_only_workers():
    snapshot = {
        "schema": "zth_local_fleet_snapshot_v1",
        "generated_at": "2026-09-08T12:00:00+00:00",
        "workers": [
            {
                "worker": "router",
                "configured_base_url": "http://127.0.0.1:8081/v1",
                "expected_model": "Qwen_Qwen3-1.7B-Q4_K_M.gguf",
                "binding_status": "UNVERIFIED",
                "availability": "UNKNOWN",
                "advertised_models": [],
                "failure_class": None,
                "checked_at": None,
                "freshness": {"state": "unknown", "age_seconds": None, "stale": True},
                "capability_refs": [],
                "qualification_refs": [],
                "evidence": {"source": "static_config_only", "preflight": None},
            }
        ],
    }
    assert verified_workers(snapshot) == []
