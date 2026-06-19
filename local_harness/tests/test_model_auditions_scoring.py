import json

from local_harness.model_auditions.common import (
    AuditionError,
    build_llama_command,
    load_models,
)
from local_harness.model_auditions.run_audition import (
    build_payload,
    main as run_audition_main,
)
from local_harness.model_auditions.scoring import (
    count_bullets,
    parse_json_candidate,
    score_record,
)


def make_route_record(content):
    return {
        "model_key": "model_under_test",
        "prompt_key": "router_docs_update",
        "prompt_kind": "json_route",
        "expected": {
            "route": "docs_update",
            "schema": {
                "route": "string",
                "confidence": "number",
                "reason": "string",
                "next_action": "string",
            },
        },
        "response": {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": content},
                }
            ],
            "timings": {"predicted_per_second": 4.2},
        },
    }


def test_raw_json_route_passes():
    env = score_record(
        make_route_record(
            '{"route":"docs_update","confidence":0.9,"reason":"README docs flow","next_action":"Inspect README"}'
        )
    )
    assert env.checks["raw_json_valid"] is True
    assert env.checks["schema_valid"] is True
    assert env.checks["route_match"] is True
    assert env.verdict == "pass"


def test_wrong_route_is_caught_even_when_json_is_valid():
    env = score_record(
        make_route_record(
            '{"route":"context_distill","confidence":0.9,"reason":"mentions distiller","next_action":"verify_model_behavior"}'
        )
    )
    assert env.checks["raw_json_valid"] is True
    assert env.checks["schema_valid"] is True
    assert env.checks["route_match"] is False
    assert any("Route mismatch" in note for note in env.notes)


def test_markdown_fenced_json_is_recoverable_but_not_raw():
    obj, diagnostics = parse_json_candidate(
        '```json\n{"route":"docs_update","confidence":0.95,"reason":"docs","next_action":"verify"}\n```'
    )
    assert obj["route"] == "docs_update"
    assert diagnostics["raw_json_valid"] is False
    assert diagnostics["recoverable_json_valid"] is True
    assert diagnostics["markdown_fence_leakage"] is True


def test_schema_type_drift_is_caught():
    env = score_record(
        make_route_record(
            '{"route":"docs_update","confidence":"high","reason":"README docs flow","next_action":"Inspect README"}'
        )
    )
    assert env.checks["route_match"] is True
    assert env.checks["schema_valid"] is False
    assert any("confidence expected number" in note for note in env.notes)


def test_reasoning_content_and_empty_content_are_caught():
    record = make_route_record("")
    record["response"]["choices"][0]["finish_reason"] = "length"
    record["response"]["choices"][0]["message"] = {
        "role": "assistant",
        "content": "",
        "reasoning_content": "Thinking consumed the token budget.",
    }
    env = score_record(record)
    assert env.checks["empty_content"] is True
    assert env.checks["reasoning_content_present"] is True
    assert env.verdict == "fail"


def test_bullet_counter_tracks_exact_bullet_shape():
    assert count_bullets("- one\n- two\n- three") == 3
    assert count_bullets("Token reduction: one\nAgent handoff: two") == 0


def test_high_confidence_unknown_on_workflow_terms_is_flagged():
    record = make_route_record('{"route":"unknown","confidence":0.95,"reason":"unclear","next_action":"clarify"}')
    record["prompt_key"] = "router_model_audition_defined_routes"
    record["expected"]["route"] = "model_audition"
    record["request"] = {
        "messages": [
            {"role": "system", "content": "Return JSON."},
            {
                "role": "user",
                "content": "The model produced JSON but needs model audition scoring and route ranking.",
            },
        ]
    }
    env = score_record(record)
    assert env.checks["high_confidence_unknown_on_workflow_terms"] is True
    assert any("High-confidence unknown" in note for note in env.notes)


def write_models(path, models):
    path.write_text(json.dumps({"models": models}), encoding="utf-8")


def write_prompts(path):
    path.write_text(
        json.dumps(
            {
                "prompts": {
                    "smoke": {
                        "kind": "prose",
                        "system": "Reply briefly.",
                        "user": "Say ok.",
                    }
                }
            }
        ),
        encoding="utf-8",
    )


def test_existing_path_and_port_config_resolves_local_endpoint(tmp_path):
    config_path = tmp_path / "models.json"
    write_models(
        config_path,
        {
            "local_model": {
                "path": "/models/local.gguf",
                "port": 8112,
            }
        },
    )

    model = load_models(config_path)[0]

    assert model.endpoint_base_url == "http://127.0.0.1:8112/v1"
    assert model.url == "http://127.0.0.1:8112/v1/chat/completions"
    assert model.managed_locally is True


def test_host_and_port_config_resolves_lan_endpoint(tmp_path):
    config_path = tmp_path / "models.json"
    write_models(
        config_path,
        {
            "lan_model": {
                "host": "192.168.1.13",
                "port": 8112,
            }
        },
    )

    model = load_models(config_path)[0]

    assert model.endpoint_base_url == "http://192.168.1.13:8112/v1"
    assert model.managed_locally is False


def test_full_base_url_config_resolves_lan_endpoint(tmp_path):
    config_path = tmp_path / "models.json"
    write_models(
        config_path,
        {
            "lan_model": {
                "base_url": "http://192.168.1.13:8112/v1",
                "api_model": "served-model-id",
            }
        },
    )

    model = load_models(config_path)[0]

    assert model.url == "http://192.168.1.13:8112/v1/chat/completions"
    assert model.api_model == "served-model-id"
    assert model.managed_locally is False


def test_payload_uses_configured_api_model(tmp_path):
    prompts_path = tmp_path / "prompts.json"
    write_prompts(prompts_path)
    from local_harness.model_auditions.common import load_prompts

    prompt = load_prompts(prompts_path)[0]
    payload = build_payload(prompt, api_model="served-model-id")

    assert payload["model"] == "served-model-id"


def test_local_start_uses_server_host_without_changing_client_endpoint(tmp_path):
    config_path = tmp_path / "models.json"
    write_models(
        config_path,
        {
            "local_model": {
                "path": "/models/local.gguf",
                "host": "127.0.0.1",
                "server_host": "0.0.0.0",
                "port": 8112,
            }
        },
    )
    model = load_models(config_path)[0]

    command = build_llama_command(model, "/opt/llama-server")

    assert command[command.index("--host") + 1] == "0.0.0.0"
    assert model.endpoint_base_url == "http://127.0.0.1:8112/v1"


def test_model_config_requires_base_url_or_port(tmp_path):
    config_path = tmp_path / "models.json"
    write_models(config_path, {"broken": {"path": "/models/broken.gguf"}})

    try:
        load_models(config_path)
    except AuditionError as exc:
        assert "requires either base_url or port" in str(exc)
    else:
        raise AssertionError("Expected invalid endpoint config to fail.")


def test_audition_dry_run_validates_configs_without_creating_output(
    tmp_path,
    capsys,
):
    models_path = tmp_path / "models.json"
    prompts_path = tmp_path / "prompts.json"
    out_dir = tmp_path / "should-not-exist"
    write_models(
        models_path,
        {
            "lan_model": {
                "base_url": "http://192.168.1.13:8112/v1",
            }
        },
    )
    write_prompts(prompts_path)

    exit_code = run_audition_main(
        [
            "--models",
            str(models_path),
            "--prompts",
            str(prompts_path),
            "--out",
            str(out_dir),
            "--dry-run",
        ]
    )

    inspection = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert inspection["network_calls_performed"] is False
    assert inspection["models"][0]["endpoint"] == "http://192.168.1.13:8112/v1"
    assert inspection["models"][0]["managed_locally"] is False
    assert not out_dir.exists()
