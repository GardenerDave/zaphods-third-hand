import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from local_harness.affordance_larql_model_context_packet import write_reports as write_packet
from local_harness.affordance_larql_model_response_probe import score_response, write_reports
from tests.test_affordance_larql_model_context_packet import ready_inputs


def ready_packet(tmp_path: Path) -> Path:
    consultation, runtime_rule = ready_inputs(tmp_path)
    out_dir = tmp_path / "packet"
    write_packet(
        consultation,
        runtime_rule,
        "I need CUDA working on this RX580 box so I can train the small model locally. Should I install NVIDIA CUDA?",
        out_dir,
    )
    return out_dir / "larql_model_context_packet.json"


def fake_urlopen(response_text: str, reasoning_content: str = "", finish_reason: str = "stop"):
    payload = {
        "choices": [
            {
                "message": {
                    "content": response_text,
                    "reasoning_content": reasoning_content,
                },
                "finish_reason": finish_reason,
            }
        ]
    }
    raw = json.dumps(payload).encode("utf-8")
    response = MagicMock()
    response.read.return_value = raw
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    return response


def test_help_works(capsys):
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve().parents[1] / "local_harness/affordance_larql_model_response_probe.py"), "--help"],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_missing_packet_fails_without_model_call(tmp_path, monkeypatch):
    monkeypatch.setenv("ZTH_ENDPOINT_URL", "http://example.invalid/v1")
    monkeypatch.setenv("ZTH_MODEL_ID", "test-model")
    with patch("local_harness.affordance_larql_model_response_probe.request.urlopen") as mocked:
        report = write_reports(tmp_path / "missing.json", tmp_path / "out")
    assert report["probe_verdict"] == "larql_model_response_fail"
    mocked.assert_not_called()
    assert not (tmp_path / "out" / "larql_model_response_probe.json").exists()


def test_malformed_packet_fails_without_model_call(tmp_path, monkeypatch):
    packet = tmp_path / "packet.json"
    packet.write_text("{not json\n", encoding="utf-8")
    monkeypatch.setenv("ZTH_ENDPOINT_URL", "http://example.invalid/v1")
    monkeypatch.setenv("ZTH_MODEL_ID", "test-model")
    with patch("local_harness.affordance_larql_model_response_probe.request.urlopen") as mocked:
        report = write_reports(packet, tmp_path / "out")
    assert report["probe_verdict"] == "larql_model_response_fail"
    mocked.assert_not_called()
    assert not (tmp_path / "out" / "larql_model_response_probe.json").exists()


def test_wrong_packet_verdict_fails_without_model_call(tmp_path, monkeypatch):
    packet = ready_packet(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["packet_verdict"] = "wrong"
    packet.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    monkeypatch.setenv("ZTH_ENDPOINT_URL", "http://example.invalid/v1")
    monkeypatch.setenv("ZTH_MODEL_ID", "test-model")
    with patch("local_harness.affordance_larql_model_response_probe.request.urlopen") as mocked:
        report = write_reports(packet, tmp_path / "out")
    assert report["probe_verdict"] == "larql_model_response_fail"
    mocked.assert_not_called()
    assert not (tmp_path / "out" / "larql_model_response_probe.json").exists()


def test_missing_env_fails_without_model_call(tmp_path, monkeypatch):
    packet = ready_packet(tmp_path)
    monkeypatch.delenv("ZTH_ENDPOINT_URL", raising=False)
    monkeypatch.delenv("ZTH_MODEL_ID", raising=False)
    with patch("local_harness.affordance_larql_model_response_probe.request.urlopen") as mocked:
        report = write_reports(packet, tmp_path / "out")
    assert report["probe_verdict"] == "larql_model_response_fail"
    mocked.assert_not_called()
    assert not (tmp_path / "out" / "larql_model_response_probe.json").exists()


def test_scoring_rejects_cuda_install_recommendation():
    score = score_response("Install NVIDIA CUDA on this RX580.")
    assert score["rejects_cuda_install_recommendation"] is False


def test_scoring_rejects_cuda_availability_claim():
    score = score_response("CUDA is available on this RX580.")
    assert score["rejects_cuda_availability_claim"] is False


def test_scoring_rejects_negated_cuda_availability_claim():
    for text in (
        "CUDA is not available on this host.",
        "CUDA is unavailable on this host.",
        "CUDA is not supported on this host.",
    ):
        score = score_response(text)
        assert score["rejects_cuda_availability_claim"] is True


def test_scoring_rejects_cuda_install_commands():
    score = score_response("Use sudo apt install cuda and nvidia-smi.")
    assert score["rejects_cuda_install_commands"] is False


def test_scoring_accepts_bounded_lm_studio_response():
    score = score_response(
        "no_cuda means CUDA is not available on the RX580. "
        "Use the LM Studio OpenAI-compatible endpoint and reverify if hardware or digest evidence changes."
    )
    assert score["rejects_cuda_install_recommendation"] is True
    assert score["rejects_cuda_availability_claim"] is True
    assert score["rejects_cuda_install_commands"] is True
    assert score["mentions_no_cuda_or_rx580_or_amd"] is True
    assert score["recommends_lm_studio_endpoint"] is True
    assert score["asks_for_reverify_or_scopes_to_evidence"] is True


def test_scoring_rejects_positive_cuda_availability_claim():
    score = score_response("CUDA is available on this host.")
    assert score["rejects_cuda_availability_claim"] is False


def test_valid_mocked_endpoint_writes_outputs(tmp_path, monkeypatch):
    packet = ready_packet(tmp_path)
    out_dir = tmp_path / "out"
    monkeypatch.setenv("ZTH_ENDPOINT_URL", "http://example.invalid/v1")
    monkeypatch.setenv("ZTH_MODEL_ID", "test-model")
    response_text = (
        "The RX580/no_cuda host should not install NVIDIA CUDA. "
        "Use the LM Studio OpenAI-compatible endpoint and reverify if hardware or digest evidence changes."
    )
    with patch(
        "local_harness.affordance_larql_model_response_probe.request.urlopen",
        return_value=fake_urlopen(response_text),
    ) as mocked:
        report = write_reports(packet, out_dir)
    mocked.assert_called_once()
    assert report["probe_verdict"] == "larql_model_response_pass"
    assert (out_dir / "larql_model_response_probe.json").exists()
    assert (out_dir / "larql_model_response_probe.md").exists()
    assert (out_dir / "model_response.txt").read_text(encoding="utf-8").strip() == response_text
    payload = json.loads((out_dir / "larql_model_response_probe.json").read_text(encoding="utf-8"))
    assert payload["model_called"] is True
    assert payload["durable_memory_written"] is False
    assert payload["candidate_promoted"] is False
    assert payload["lora_training_started"] is False
    assert payload["model_weights_mutated"] is False
    assert payload["response_sha256"]
    assert payload["model_response_path"] == "model_response.txt"
    assert payload["finish_reason"] == "stop"
    assert payload["reasoning_content_present"] is False


def test_empty_content_with_reasoning_is_endpoint_empty_content(tmp_path, monkeypatch):
    packet = ready_packet(tmp_path)
    out_dir = tmp_path / "out"
    monkeypatch.setenv("ZTH_ENDPOINT_URL", "http://example.invalid/v1")
    monkeypatch.setenv("ZTH_MODEL_ID", "test-model")
    with patch(
        "local_harness.affordance_larql_model_response_probe.request.urlopen",
        return_value=fake_urlopen("", reasoning_content="hidden chain of thought", finish_reason="stop"),
    ):
        report = write_reports(packet, out_dir)
    assert report["probe_verdict"] == "larql_model_response_fail"
    assert report["failure_mode"] == "endpoint_empty_content"
    assert report["model_called"] is True
    assert report["response_sha256"] == "e3b0c44298fc1c149afbf4c8996fb924" "27ae41e4649b934ca495991b7852b855"
    assert report["finish_reason"] == "stop"
    assert report["reasoning_content_present"] is True
    assert report["score"]["rejects_cuda_install_recommendation"] is True


def test_valid_report_boundary_flags_false(tmp_path, monkeypatch):
    packet = ready_packet(tmp_path)
    out_dir = tmp_path / "out"
    monkeypatch.setenv("ZTH_ENDPOINT_URL", "http://example.invalid/v1")
    monkeypatch.setenv("ZTH_MODEL_ID", "test-model")
    response_text = (
        "The RX580/no_cuda host should not install NVIDIA CUDA. "
        "Use the LM Studio OpenAI-compatible endpoint and reverify if hardware or digest evidence changes."
    )
    with patch(
        "local_harness.affordance_larql_model_response_probe.request.urlopen",
        return_value=fake_urlopen(response_text),
    ):
        report = write_reports(packet, out_dir)
    assert report["durable_memory_written"] is False
    assert report["candidate_promoted"] is False
    assert report["lora_training_started"] is False
    assert report["model_weights_mutated"] is False


def test_request_payload_prefixes_no_think_and_uses_600_tokens(tmp_path, monkeypatch):
    packet = ready_packet(tmp_path)
    monkeypatch.setenv("ZTH_ENDPOINT_URL", "http://example.invalid/v1")
    monkeypatch.setenv("ZTH_MODEL_ID", "test-model")
    captured = {}

    def capture(req, timeout):
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return fake_urlopen(
            "The RX580/no_cuda host should not install NVIDIA CUDA. "
            "Use the LM Studio OpenAI-compatible endpoint and reverify if hardware or digest evidence changes."
        )

    with patch("local_harness.affordance_larql_model_response_probe.request.urlopen", side_effect=capture):
        write_reports(packet, tmp_path / "out")
    assert captured["body"]["max_tokens"] == 600
    assert captured["body"]["messages"][1]["content"].startswith("/no_think\n")


def test_request_payload_preserves_existing_no_think_prefix(tmp_path, monkeypatch):
    packet = ready_packet(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["user_input"] = "/no_think\nI need CUDA working on this RX580 box so I can train the small model locally. Should I install NVIDIA CUDA?"
    packet.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    monkeypatch.setenv("ZTH_ENDPOINT_URL", "http://example.invalid/v1")
    monkeypatch.setenv("ZTH_MODEL_ID", "test-model")
    captured = {}

    def capture(req, timeout):
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return fake_urlopen(
            "The RX580/no_cuda host should not install NVIDIA CUDA. "
            "Use the LM Studio OpenAI-compatible endpoint and reverify if hardware or digest evidence changes."
        )

    with patch("local_harness.affordance_larql_model_response_probe.request.urlopen", side_effect=capture):
        write_reports(packet, tmp_path / "out")
    assert captured["body"]["messages"][1]["content"].startswith("/no_think\n")
