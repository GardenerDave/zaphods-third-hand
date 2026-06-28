import json
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_larql_runtime_consultation_probe import write_reports
from local_harness.affordance_larql_runtime_validate import write_reports as write_validate
from tests.test_affordance_larql_runtime_validate import ready_runtime_bundle


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_larql_runtime_consultation_probe.py"


def run_probe(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def ready_runtime_rule_path(tmp_path: Path) -> tuple[Path, Path]:
    install_dir = ready_runtime_bundle(tmp_path)
    validation_dir = tmp_path / "validation"
    write_validate(
        install_dir / "runtime_rules" / "navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0.json",
        install_dir / "larql_runtime_install_report.json",
        validation_dir,
    )
    return (
        install_dir / "runtime_rules" / "navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0.json",
        validation_dir / "larql_runtime_install_validation_report.json",
    )


def test_help_works():
    result = run_probe("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_missing_runtime_rule_fails(tmp_path):
    _, validation = ready_runtime_rule_path(tmp_path)
    report = write_reports(tmp_path / "missing.json", validation, "navigator_desktop", "no_cuda", "CUDA", tmp_path / "out")
    assert report["consultation_verdict"] == "runtime_rule_not_consulted"


def test_missing_validation_fails(tmp_path):
    runtime_rule, _ = ready_runtime_rule_path(tmp_path)
    report = write_reports(runtime_rule, tmp_path / "missing.json", "navigator_desktop", "no_cuda", "CUDA", tmp_path / "out")
    assert report["consultation_verdict"] == "runtime_rule_not_consulted"


def test_malformed_json_fails(tmp_path):
    runtime_rule = tmp_path / "rule.json"
    runtime_rule.write_text("{not json\n", encoding="utf-8")
    _, validation = ready_runtime_rule_path(tmp_path)
    report = write_reports(runtime_rule, validation, "navigator_desktop", "no_cuda", "CUDA", tmp_path / "out")
    assert report["consultation_verdict"] == "runtime_rule_not_consulted"


def test_unvalidated_runtime_rule_fails(tmp_path):
    runtime_rule, validation = ready_runtime_rule_path(tmp_path)
    payload = json.loads(validation.read_text(encoding="utf-8"))
    payload["validation_verdict"] = "wrong"
    validation.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(runtime_rule, validation, "navigator_desktop", "no_cuda", "CUDA", tmp_path / "out")
    assert report["consultation_verdict"] == "runtime_rule_not_consulted"


def test_wrong_active_host_requires_reverify(tmp_path):
    runtime_rule, validation = ready_runtime_rule_path(tmp_path)
    report = write_reports(runtime_rule, validation, "other_host", "no_cuda", "CUDA", tmp_path / "out")
    assert report["consultation_verdict"] == "runtime_rule_not_consulted"
    assert report["requires_reverify"] is True


def test_missing_no_cuda_constraint_requires_reverify(tmp_path):
    runtime_rule, validation = ready_runtime_rule_path(tmp_path)
    report = write_reports(runtime_rule, validation, "navigator_desktop", "cuda_ok", "CUDA", tmp_path / "out")
    assert report["consultation_verdict"] == "runtime_rule_not_consulted"
    assert report["requires_reverify"] is True


def test_non_cuda_input_does_not_consult_rule(tmp_path):
    runtime_rule, validation = ready_runtime_rule_path(tmp_path)
    report = write_reports(runtime_rule, validation, "navigator_desktop", "no_cuda", "hello world", tmp_path / "out")
    assert report["consultation_verdict"] == "runtime_rule_not_consulted"


def test_cuda_input_consults_rule(tmp_path):
    runtime_rule, validation = ready_runtime_rule_path(tmp_path)
    report = write_reports(
        runtime_rule,
        validation,
        "navigator_desktop",
        "no_cuda",
        "I need CUDA working on this RX580 box so I can train the small model locally. Should I install NVIDIA CUDA?",
        tmp_path / "out",
    )
    assert report["consultation_verdict"] == "runtime_rule_consulted"
    assert report["blocked_path"] == "CUDA/NVIDIA troubleshooting path on RX580/no_cuda host"
    assert report["recommended_path"] == "LM Studio OpenAI-compatible endpoint for small-model GPU-backed workflow"


def test_valid_probe_flags_false_for_model_and_memory(tmp_path):
    runtime_rule, validation = ready_runtime_rule_path(tmp_path)
    report = write_reports(
        runtime_rule,
        validation,
        "navigator_desktop",
        "no_cuda",
        "I need CUDA working on this RX580 box so I can train the small model locally. Should I install NVIDIA CUDA?",
        tmp_path / "out",
    )
    assert report["model_called"] is False
    assert report["durable_memory_written"] is False
    assert report["candidate_promoted"] is False
    assert report["lora_training_started"] is False
    assert report["model_weights_mutated"] is False
