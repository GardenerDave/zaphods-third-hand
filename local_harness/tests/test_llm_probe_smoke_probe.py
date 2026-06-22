from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from local_harness.llm_probe_preflight_ingest import ingest_probe_output
from local_harness.llm_probe_smoke_probe import (
    PROBES,
    ProducerConfig,
    evaluate_visible_response,
    main,
    produce_smoke_evidence,
    request_headers,
)


FIXED_NOW = datetime(2026, 6, 21, 12, 0, tzinfo=timezone.utc)


def response(content: str) -> dict[str, Any]:
    return {
        "choices": [
            {
                "message": {"content": content},
                "finish_reason": "stop",
            }
        ]
    }


def all_pass_client(
    _url: str,
    payload: dict[str, Any],
    _headers: dict[str, str],
    _timeout: int,
) -> tuple[int, Any]:
    prompt = payload["messages"][0]["content"]
    if "tool_call_basic" in prompt:
        content = json.dumps(
            {
                "route": "smoke",
                "confidence": 0.9,
                "next_action": "review",
            }
        )
    elif "json_schema_basic" in prompt:
        content = json.dumps(
            {
                "status": "ok",
                "checks": ["endpoint"],
                "next_action": "review",
            }
        )
    else:
        content = "READY"
    return 200, response(content)


def one_fail_client(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: int,
) -> tuple[int, Any]:
    prompt = payload["messages"][0]["content"]
    if "json_schema_basic" in prompt:
        return 200, response('{"status":"ok"}')
    return all_pass_client(url, payload, headers, timeout)


def transport_error_client(
    _url: str,
    _payload: dict[str, Any],
    _headers: dict[str, str],
    _timeout: int,
) -> tuple[int, Any]:
    raise TimeoutError("synthetic timeout")


def config(tmp_path: Path, name: str = "run") -> ProducerConfig:
    return ProducerConfig(
        base_url="http://private-endpoint.invalid:8080/v1",
        model="synthetic-local-model",
        out_dir=tmp_path / name,
        timeout_seconds=5,
        max_tokens=64,
        producer_run_id="synthetic-producer-run",
    )


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_dry_run_writes_nothing_and_redacts_endpoint(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    out_dir = tmp_path / "planned"
    result = main(
        [
            "--base-url",
            "http://private-endpoint.invalid:8080/v1",
            "--model",
            "synthetic-local-model",
            "--out-dir",
            str(out_dir),
            "--dry-run",
        ]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert not out_dir.exists()
    assert "private-endpoint.invalid" not in captured.out
    assert '"endpoint": "<redacted>"' in captured.out
    assert '"network_calls_performed": 0' in captured.out
    assert '"files_written": 0' in captured.out


def test_print_plan_is_dry_run_alias(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    out_dir = tmp_path / "planned"
    assert (
        main(
            [
                "--base-url",
                "http://private-endpoint.invalid:8080/v1",
                "--model",
                "synthetic-local-model",
                "--out-dir",
                str(out_dir),
                "--print-plan",
            ]
        )
        == 0
    )
    assert not out_dir.exists()
    assert "plan_only" in capsys.readouterr().out


@pytest.mark.parametrize("existing_kind", ["directory", "file"])
def test_existing_output_path_refuses_overwrite(
    tmp_path: Path,
    existing_kind: str,
) -> None:
    out_dir = tmp_path / "existing"
    if existing_kind == "directory":
        out_dir.mkdir()
    else:
        out_dir.write_text("existing evidence\n", encoding="utf-8")
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        produce_smoke_evidence(
            ProducerConfig(
                base_url="http://example.invalid/v1",
                model="model",
                out_dir=out_dir,
            ),
            client=all_pass_client,
            now=FIXED_NOW,
        )


def test_local_api_key_sentinel_does_not_add_auth_header() -> None:
    assert request_headers("not-needed-for-local") == {
        "Content-Type": "application/json"
    }
    assert request_headers("") == {"Content-Type": "application/json"}
    assert request_headers("synthetic-secret")["Authorization"] == (
        "Bearer synthetic-secret"
    )


def test_fake_endpoint_success_writes_expected_files(tmp_path: Path) -> None:
    producer_config = config(tmp_path)
    metadata = produce_smoke_evidence(
        producer_config,
        client=all_pass_client,
        now=FIXED_NOW,
    )

    files = {
        path.relative_to(producer_config.out_dir).as_posix()
        for path in producer_config.out_dir.rglob("*")
        if path.is_file()
    }
    assert files == {
        "verified/zth-smoke-probe.yaml",
        "run_metadata.json",
        "raw/tool_call_basic.json",
        "raw/json_schema_basic.json",
        "raw/think_block_leak.json",
    }
    assert metadata["producer"] == "zth_smoke_probe"
    assert metadata["all_required_probes_passed"] is True
    assert metadata["status_counts"] == {"pass": 3}


def test_verified_yaml_round_trips_to_pass_manifest(tmp_path: Path) -> None:
    producer_config = config(tmp_path, "producer")
    produce_smoke_evidence(
        producer_config,
        client=all_pass_client,
        now=FIXED_NOW,
    )

    preflight_dir = tmp_path / "preflight"
    ingest_probe_output(
        producer_config.out_dir / "verified" / "zth-smoke-probe.yaml",
        preflight_dir,
        input_format="llm-probe-yaml",
    )

    manifest = read_json(preflight_dir / "preflight_capability_manifest.json")
    assert manifest["input_schema_version"] == "llm_probe.verified_yaml.v1"
    assert manifest["model_ids_observed"] == ["synthetic-local-model"]
    assert manifest["probe_ids_observed"] == [
        "json_schema_basic",
        "think_block_leak",
        "tool_call_basic",
    ]
    assert manifest["status_counts"] == {"pass": 3}
    assert manifest["preflight_status"] == "pass"


def test_one_failed_probe_round_trips_to_fail_manifest(tmp_path: Path) -> None:
    producer_config = config(tmp_path, "producer")
    produce_smoke_evidence(
        producer_config,
        client=one_fail_client,
        now=FIXED_NOW,
    )

    preflight_dir = tmp_path / "preflight"
    ingest_probe_output(
        producer_config.out_dir / "verified" / "zth-smoke-probe.yaml",
        preflight_dir,
        input_format="llm-probe-yaml",
    )

    manifest = read_json(preflight_dir / "preflight_capability_manifest.json")
    assert manifest["status_counts"] == {"fail": 1, "pass": 2}
    assert manifest["preflight_status"] == "fail"


def test_transport_errors_are_error_evidence_and_import_as_fail(
    tmp_path: Path,
) -> None:
    producer_config = config(tmp_path, "producer")
    metadata = produce_smoke_evidence(
        producer_config,
        client=transport_error_client,
        now=FIXED_NOW,
    )

    assert metadata["status_counts"] == {"error": 3}
    for probe in PROBES:
        raw = read_json(
            producer_config.out_dir / "raw" / f"{probe.probe_id}.json"
        )
        assert raw["status"] == "error"
        assert raw["passed"] is False
        assert raw["failures"] == ["timeout_error"]

    preflight_dir = tmp_path / "preflight"
    ingest_probe_output(
        producer_config.out_dir / "verified" / "zth-smoke-probe.yaml",
        preflight_dir,
        input_format="llm-probe-yaml",
    )
    manifest = read_json(preflight_dir / "preflight_capability_manifest.json")
    assert manifest["status_counts"] == {"fail": 3}
    assert manifest["preflight_status"] == "fail"


def test_endpoint_url_is_absent_from_report_oriented_metadata(
    tmp_path: Path,
) -> None:
    producer_config = config(tmp_path)
    produce_smoke_evidence(
        producer_config,
        client=all_pass_client,
        now=FIXED_NOW,
    )

    metadata_text = (
        producer_config.out_dir / "run_metadata.json"
    ).read_text(encoding="utf-8")
    assert "private-endpoint.invalid" not in metadata_text
    assert '"endpoint": "<redacted>"' in metadata_text


def test_hidden_reasoning_marker_detection() -> None:
    probe = next(probe for probe in PROBES if probe.probe_id == "think_block_leak")
    passed, failures, _, evaluation = evaluate_visible_response(
        probe,
        "<think>secret reasoning</think>\nREADY",
    )

    assert passed is False
    assert "visible_reasoning_marker_leak" in failures
    assert evaluation["visible_reasoning_marker_leaked"] is True


def test_required_json_key_detection() -> None:
    probe = next(probe for probe in PROBES if probe.probe_id == "json_schema_basic")
    passed, failures, _, evaluation = evaluate_visible_response(
        probe,
        '{"status":"ok","checks":[]}',
    )

    assert passed is False
    assert failures == ("missing_required_keys",)
    assert evaluation["missing_required_keys"] == ["next_action"]


def test_producer_writes_nothing_outside_out_dir(tmp_path: Path) -> None:
    producer_config = config(tmp_path, "only-output")
    produce_smoke_evidence(
        producer_config,
        client=all_pass_client,
        now=FIXED_NOW,
    )

    assert {
        path.name for path in tmp_path.iterdir()
    } == {"only-output"}
