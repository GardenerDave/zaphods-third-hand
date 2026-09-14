from __future__ import annotations

import json

from local_harness.local_fleet_snapshot import collect_local_fleet_snapshot, main, verified_workers


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


def test_cli_emits_snapshot_from_configured_environment(capsys, tmp_path):
    opener = _opener_factory([
        FakeResponse({"data": [{"id": "Qwen_Qwen3-1.7B-Q4_K_M.gguf"}]}),
        FakeResponse({"data": [{"id": "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf"}]}),
    ])
    out = tmp_path / "fleet.json"
    rc = main(
        ["--out", str(out), "--timeout", "5"],
        opener=opener,
        env={
            "ZTH_CAPABILITY_WORKER_NAME": "router",
            "ZTH_CAPABILITY_WORKER_BASE_URL": "http://127.0.0.1:8081/v1",
            "ZTH_CAPABILITY_WORKER_MODEL": "Qwen_Qwen3-1.7B-Q4_K_M.gguf",
            "ZTH_CAPABILITY_TEACHER_NAME": "handoff",
            "ZTH_CAPABILITY_TEACHER_BASE_URL": "http://127.0.0.1:8080/v1",
            "ZTH_CAPABILITY_TEACHER_MODEL": "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf",
        },
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    written = json.loads(out.read_text(encoding="utf-8"))
    assert payload == written
    assert payload["schema"] == "zth_local_fleet_snapshot_v1"
    assert [worker["binding_status"] for worker in payload["workers"]] == ["VERIFIED", "VERIFIED"]
    assert opener.calls == [
        "http://127.0.0.1:8081/v1/models",
        "http://127.0.0.1:8080/v1/models",
    ]


def test_cli_verified_only_filters_unverified_workers(capsys):
    opener = _opener_factory([
        FakeResponse({"data": [{"id": "Qwen_Qwen3-1.7B-Q4_K_M.gguf"}]}),
        FakeResponse({"data": [{"id": "other-model"}]}),
    ])
    rc = main(
        ["--verified-only"],
        opener=opener,
        env={
            "ZTH_CAPABILITY_WORKER_NAME": "router",
            "ZTH_CAPABILITY_WORKER_BASE_URL": "http://127.0.0.1:8081/v1",
            "ZTH_CAPABILITY_WORKER_MODEL": "Qwen_Qwen3-1.7B-Q4_K_M.gguf",
            "ZTH_CAPABILITY_TEACHER_NAME": "handoff",
            "ZTH_CAPABILITY_TEACHER_BASE_URL": "http://127.0.0.1:8080/v1",
            "ZTH_CAPABILITY_TEACHER_MODEL": "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf",
        },
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "zth_local_fleet_snapshot_verified_workers_v1"
    assert [worker["worker"] for worker in payload["workers"]] == ["router"]


def test_middle_tier_ladder_worker_slot_9b_teacher_slot_27b_both_verified():
    # 1.7B -> 9B -> 27B must stay expressible through the existing role slots:
    # the worker slot takes the registered 9B (registry defaults, no env URL/model)
    # and the teacher slot takes the 27B. No new routing mechanism is introduced.
    snapshot = collect_local_fleet_snapshot(
        opener=_opener_factory([
            FakeResponse({"data": [{"id": "qwen3.5-9b-claude-4.6-opus-reasoning-distilled"}]}),
            FakeResponse({"data": [{"id": "Qwen3.8-27B-UD-IQ4_XS.gguf"}]}),
        ]),
        env={
            "ZTH_CAPABILITY_WORKER_NAME": "qwen3_5_9b_rx580",
            "ZTH_CAPABILITY_TEACHER_NAME": "qwen3_8_27b",
            "ZTH_CAPABILITY_TEACHER_BASE_URL": "http://192.168.56.1:8080/v1",
            "ZTH_CAPABILITY_TEACHER_MODEL": "Qwen3.8-27B-UD-IQ4_XS.gguf",
        },
    )
    assert [worker["worker"] for worker in snapshot["workers"]] == ["qwen3_5_9b_rx580", "qwen3_8_27b"]
    for worker in snapshot["workers"]:
        assert worker["binding_status"] == "VERIFIED"
        assert worker["availability"] == "AVAILABLE"
    nine_b = snapshot["workers"][0]
    assert nine_b["configured_base_url"] == "http://192.168.56.1:1234/v1"
    assert nine_b["expected_model"] == "qwen3.5-9b-claude-4.6-opus-reasoning-distilled"
    assert [worker["worker"] for worker in verified_workers(snapshot)] == ["qwen3_5_9b_rx580", "qwen3_8_27b"]


def test_middle_tier_ladder_router_1p7b_worker_9b_teacher_both_verified():
    # The 1.7B-first research behavior stays intact: router slot with the 1.7B
    # gguf endpoint, and the 9B promoted into the teacher slot (registry defaults).
    snapshot = collect_local_fleet_snapshot(
        opener=_opener_factory([
            FakeResponse({"data": [{"id": "Qwen_Qwen3-1.7B-Q4_K_M.gguf"}]}),
            FakeResponse({"data": [{"id": "qwen3.5-9b-claude-4.6-opus-reasoning-distilled"}]}),
        ]),
        env={
            "ZTH_CAPABILITY_WORKER_NAME": "router",
            "ZTH_CAPABILITY_WORKER_BASE_URL": "http://127.0.0.1:8081/v1",
            "ZTH_CAPABILITY_WORKER_MODEL": "Qwen_Qwen3-1.7B-Q4_K_M.gguf",
            "ZTH_CAPABILITY_TEACHER_NAME": "qwen3_5_9b_rx580",
        },
    )
    assert [worker["worker"] for worker in snapshot["workers"]] == ["router", "qwen3_5_9b_rx580"]
    for worker in snapshot["workers"]:
        assert worker["binding_status"] == "VERIFIED"
        assert worker["availability"] == "AVAILABLE"
    assert [worker["worker"] for worker in verified_workers(snapshot)] == ["router", "qwen3_5_9b_rx580"]


def test_9b_wrong_advertised_model_remains_unverified():
    snapshot = collect_local_fleet_snapshot(
        opener=_opener_factory([FakeResponse({"data": [{"id": "some-other-model"}]})]),
        env={"ZTH_CAPABILITY_WORKER_NAME": "qwen3_5_9b_rx580"},
    )
    worker = snapshot["workers"][0]
    assert worker["worker"] == "qwen3_5_9b_rx580"
    assert worker["expected_model"] == "qwen3.5-9b-claude-4.6-opus-reasoning-distilled"
    assert worker["binding_status"] == "UNVERIFIED"
    assert worker["failure_class"] == "expected_model_not_advertised"
    assert verified_workers(snapshot) == []
