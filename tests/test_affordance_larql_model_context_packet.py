import json
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_larql_model_context_packet import write_reports
from tests.test_affordance_larql_runtime_consultation_probe import ready_runtime_rule_path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_larql_model_context_packet.py"


def run_packet(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def ready_inputs(tmp_path: Path) -> tuple[Path, Path]:
    consultation_dir = tmp_path / "consultation"
    runtime_rule, validation = ready_runtime_rule_path(tmp_path)
    from local_harness.affordance_larql_runtime_consultation_probe import write_reports as write_consultation

    write_consultation(
        runtime_rule,
        validation,
        "navigator_desktop",
        "no_cuda",
        "I need CUDA working on this RX580 box so I can train the small model locally. Should I install NVIDIA CUDA?",
        consultation_dir,
    )
    return (
        consultation_dir / "larql_runtime_consultation_probe.json",
        runtime_rule,
    )


def test_help_works():
    result = run_packet("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_missing_consultation_fails(tmp_path):
    runtime_rule, _ = ready_runtime_rule_path(tmp_path)
    report = write_reports(tmp_path / "missing.json", runtime_rule, "CUDA", tmp_path / "out")
    assert report["packet_verdict"] == "invalid_input"


def test_missing_runtime_rule_fails(tmp_path):
    consultation, _ = ready_inputs(tmp_path)
    report = write_reports(consultation, tmp_path / "missing.json", "CUDA", tmp_path / "out")
    assert report["packet_verdict"] == "invalid_input"


def test_malformed_json_fails(tmp_path):
    consultation = tmp_path / "consultation.json"
    consultation.write_text("{not json\n", encoding="utf-8")
    runtime_rule, _ = ready_runtime_rule_path(tmp_path)
    report = write_reports(consultation, runtime_rule, "CUDA", tmp_path / "out")
    assert report["packet_verdict"] == "invalid_input"


def test_not_consulted_verdict_fails(tmp_path):
    consultation, runtime_rule = ready_inputs(tmp_path)
    payload = json.loads(consultation.read_text(encoding="utf-8"))
    payload["consultation_verdict"] = "runtime_rule_not_consulted"
    consultation.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(consultation, runtime_rule, "CUDA", tmp_path / "out")
    assert report["packet_verdict"] == "invalid_input"


def test_model_called_true_fails(tmp_path):
    consultation, runtime_rule = ready_inputs(tmp_path)
    payload = json.loads(consultation.read_text(encoding="utf-8"))
    payload["model_called"] = True
    consultation.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(consultation, runtime_rule, "CUDA", tmp_path / "out")
    assert report["packet_verdict"] == "invalid_input"


def test_boundary_flags_true_fail(tmp_path):
    consultation, runtime_rule = ready_inputs(tmp_path)
    payload = json.loads(consultation.read_text(encoding="utf-8"))
    payload["durable_memory_written"] = True
    consultation.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(consultation, runtime_rule, "CUDA", tmp_path / "out")
    assert report["packet_verdict"] == "invalid_input"


def test_id_digest_mismatch_fails(tmp_path):
    consultation, runtime_rule = ready_inputs(tmp_path)
    payload = json.loads(runtime_rule.read_text(encoding="utf-8"))
    payload["candidate_digest"] = "bad"
    runtime_rule.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(consultation, runtime_rule, "CUDA", tmp_path / "out")
    assert report["packet_verdict"] == "invalid_input"


def test_missing_blocked_path_fails(tmp_path):
    consultation, runtime_rule = ready_inputs(tmp_path)
    payload = json.loads(consultation.read_text(encoding="utf-8"))
    payload["blocked_path"] = ""
    consultation.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(consultation, runtime_rule, "CUDA", tmp_path / "out")
    assert report["packet_verdict"] == "invalid_input"


def test_missing_recommended_path_fails(tmp_path):
    consultation, runtime_rule = ready_inputs(tmp_path)
    payload = json.loads(consultation.read_text(encoding="utf-8"))
    payload["recommended_path"] = ""
    consultation.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(consultation, runtime_rule, "CUDA", tmp_path / "out")
    assert report["packet_verdict"] == "invalid_input"


def test_non_cuda_user_input_fails(tmp_path):
    consultation, runtime_rule = ready_inputs(tmp_path)
    out_dir = tmp_path / "out"
    report = write_reports(consultation, runtime_rule, "hello world", out_dir)
    assert report["packet_verdict"] == "invalid_input"
    assert not (out_dir / "larql_model_context_packet.json").exists()
    assert not (out_dir / "larql_model_context_packet.md").exists()


def test_valid_packet_writes_outputs(tmp_path):
    consultation, runtime_rule = ready_inputs(tmp_path)
    out_dir = tmp_path / "out"
    report = write_reports(
        consultation,
        runtime_rule,
        "I need CUDA working on this RX580 box so I can train the small model locally. Should I install NVIDIA CUDA?",
        out_dir,
    )
    assert report["packet_verdict"] == "ready_for_larql_model_response_probe"
    json_path = out_dir / "larql_model_context_packet.json"
    md_path = out_dir / "larql_model_context_packet.md"
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["model_call_authorized"] is False
    assert payload["durable_memory_authorized"] is False
    assert payload["candidate_promotion_authorized"] is False
    assert payload["lora_training_authorized"] is False
    assert payload["model_weight_mutation_authorized"] is False
    assert "navigator_desktop" in payload["model_instruction"]
    assert "no_cuda" in payload["model_instruction"]
    assert "CUDA/NVIDIA troubleshooting is blocked on this host." in payload["model_instruction"]
    text = md_path.read_text(encoding="utf-8")
    assert "This is packet evidence only." in text
    assert "No candidate promotion is granted." in text


def test_valid_packet_does_not_call_model(tmp_path):
    consultation, runtime_rule = ready_inputs(tmp_path)
    report = write_reports(
        consultation,
        runtime_rule,
        "I need CUDA working on this RX580 box so I can train the small model locally. Should I install NVIDIA CUDA?",
        tmp_path / "out",
    )
    assert report["model_call_authorized"] is False
