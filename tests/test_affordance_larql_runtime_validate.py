import json
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_larql_runtime_install import write_reports as write_install
from local_harness.affordance_larql_runtime_install_review import write_reports as write_review
from local_harness.affordance_larql_runtime_validate import write_reports
from tests.test_affordance_larql_runtime_install import ready_packet_path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_larql_runtime_validate.py"


def run_validate(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def ready_runtime_bundle(tmp_path: Path) -> Path:
    packet = ready_packet_path(tmp_path)
    review_dir = tmp_path / "runtime_review"
    write_review(packet, "approve_runtime_install", "Approve runtime install only.", review_dir)
    install_dir = tmp_path / "install"
    write_install(packet, review_dir / "larql_runtime_install_review.json", install_dir)
    return install_dir


def test_help_works():
    result = run_validate("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_missing_runtime_rule_fails(tmp_path):
    install_dir = ready_runtime_bundle(tmp_path)
    report = write_reports(tmp_path / "missing.json", install_dir / "larql_runtime_install_report.json", tmp_path / "out")
    assert report["validation_verdict"] == "invalid_input"


def test_missing_install_report_fails(tmp_path):
    install_dir = ready_runtime_bundle(tmp_path)
    report = write_reports(install_dir / "runtime_rules" / "navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0.json", tmp_path / "missing.json", tmp_path / "out")
    assert report["validation_verdict"] == "invalid_input"


def test_malformed_json_fails(tmp_path):
    runtime_rule = tmp_path / "rule.json"
    runtime_rule.write_text("{not json\n", encoding="utf-8")
    install_dir = ready_runtime_bundle(tmp_path)
    report = write_reports(runtime_rule, install_dir / "larql_runtime_install_report.json", tmp_path / "out")
    assert report["validation_verdict"] == "invalid_input"


def test_wrong_runtime_status_fails(tmp_path):
    install_dir = ready_runtime_bundle(tmp_path)
    runtime_rule = install_dir / "runtime_rules" / "navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0.json"
    payload = json.loads(runtime_rule.read_text(encoding="utf-8"))
    payload["runtime_installation_status"] = "wrong"
    runtime_rule.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(runtime_rule, install_dir / "larql_runtime_install_report.json", tmp_path / "out")
    assert report["validation_verdict"] == "invalid_input"


def test_wrong_runtime_scope_fails(tmp_path):
    install_dir = ready_runtime_bundle(tmp_path)
    runtime_rule = install_dir / "runtime_rules" / "navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0.json"
    payload = json.loads(runtime_rule.read_text(encoding="utf-8"))
    payload["runtime_scope"] = "wrong"
    runtime_rule.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(runtime_rule, install_dir / "larql_runtime_install_report.json", tmp_path / "out")
    assert report["validation_verdict"] == "invalid_input"


def test_wrong_installed_from_review_fails(tmp_path):
    install_dir = ready_runtime_bundle(tmp_path)
    runtime_rule = install_dir / "runtime_rules" / "navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0.json"
    payload = json.loads(runtime_rule.read_text(encoding="utf-8"))
    payload["installed_from_review"] = "wrong"
    runtime_rule.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(runtime_rule, install_dir / "larql_runtime_install_report.json", tmp_path / "out")
    assert report["validation_verdict"] == "invalid_input"


def test_durable_memory_written_fails(tmp_path):
    install_dir = ready_runtime_bundle(tmp_path)
    runtime_rule = install_dir / "runtime_rules" / "navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0.json"
    payload = json.loads(runtime_rule.read_text(encoding="utf-8"))
    payload["durable_memory_status"] = "written"
    runtime_rule.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(runtime_rule, install_dir / "larql_runtime_install_report.json", tmp_path / "out")
    assert report["validation_verdict"] == "invalid_input"


def test_candidate_promoted_fails(tmp_path):
    install_dir = ready_runtime_bundle(tmp_path)
    runtime_rule = install_dir / "runtime_rules" / "navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0.json"
    payload = json.loads(runtime_rule.read_text(encoding="utf-8"))
    payload["candidate_promotion_status"] = "promoted"
    runtime_rule.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(runtime_rule, install_dir / "larql_runtime_install_report.json", tmp_path / "out")
    assert report["validation_verdict"] == "invalid_input"


def test_wrong_install_verdict_fails(tmp_path):
    install_dir = ready_runtime_bundle(tmp_path)
    report = install_dir / "larql_runtime_install_report.json"
    payload = json.loads(report.read_text(encoding="utf-8"))
    payload["install_verdict"] = "wrong"
    report.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    runtime_rule = install_dir / "runtime_rules" / "navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0.json"
    report_out = write_reports(runtime_rule, report, tmp_path / "out")
    assert report_out["validation_verdict"] == "invalid_input"


def test_runtime_rule_written_false_fails(tmp_path):
    install_dir = ready_runtime_bundle(tmp_path)
    report = install_dir / "larql_runtime_install_report.json"
    payload = json.loads(report.read_text(encoding="utf-8"))
    payload["runtime_rule_written"] = False
    report.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    runtime_rule = install_dir / "runtime_rules" / "navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0.json"
    report_out = write_reports(runtime_rule, report, tmp_path / "out")
    assert report_out["validation_verdict"] == "invalid_input"


def test_model_mutation_and_lora_flags_true_fail(tmp_path):
    install_dir = ready_runtime_bundle(tmp_path)
    report = install_dir / "larql_runtime_install_report.json"
    payload = json.loads(report.read_text(encoding="utf-8"))
    payload["lora_training_started"] = True
    report.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    runtime_rule = install_dir / "runtime_rules" / "navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0.json"
    report_out = write_reports(runtime_rule, report, tmp_path / "out")
    assert report_out["validation_verdict"] == "invalid_input"


def test_id_digest_mismatch_fails(tmp_path):
    install_dir = ready_runtime_bundle(tmp_path)
    runtime_rule = install_dir / "runtime_rules" / "navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0.json"
    report = install_dir / "larql_runtime_install_report.json"
    payload = json.loads(report.read_text(encoding="utf-8"))
    payload["candidate_digest"] = "0" * 64
    report.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_out = write_reports(runtime_rule, report, tmp_path / "out")
    assert report_out["validation_verdict"] == "invalid_input"


def test_missing_cuda_nvidia_block_fails(tmp_path):
    install_dir = ready_runtime_bundle(tmp_path)
    runtime_rule = install_dir / "runtime_rules" / "navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0.json"
    payload = json.loads(runtime_rule.read_text(encoding="utf-8"))
    payload["blocks_or_warns_on"] = ["safe thing"]
    runtime_rule.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(runtime_rule, install_dir / "larql_runtime_install_report.json", tmp_path / "out")
    assert report["validation_verdict"] == "invalid_input"


def test_missing_lm_studio_recommendation_fails(tmp_path):
    install_dir = ready_runtime_bundle(tmp_path)
    runtime_rule = install_dir / "runtime_rules" / "navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0.json"
    payload = json.loads(runtime_rule.read_text(encoding="utf-8"))
    payload["recommends"] = ["safe thing"]
    runtime_rule.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(runtime_rule, install_dir / "larql_runtime_install_report.json", tmp_path / "out")
    assert report["validation_verdict"] == "invalid_input"


def test_missing_reverify_conditions_fail(tmp_path):
    install_dir = ready_runtime_bundle(tmp_path)
    runtime_rule = install_dir / "runtime_rules" / "navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0.json"
    payload = json.loads(runtime_rule.read_text(encoding="utf-8"))
    payload["requires_reverify_when"] = ["unknown host"]
    runtime_rule.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(runtime_rule, install_dir / "larql_runtime_install_report.json", tmp_path / "out")
    assert report["validation_verdict"] == "invalid_input"


def test_valid_inputs_produce_outputs(tmp_path):
    install_dir = ready_runtime_bundle(tmp_path)
    out = tmp_path / "out"
    report = write_reports(
        install_dir / "runtime_rules" / "navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0.json",
        install_dir / "larql_runtime_install_report.json",
        out,
    )
    assert report["validation_verdict"] == "larql_runtime_install_validated"
    assert report["allowed_next_step"] == "run_larql_runtime_consultation_probe"
    assert sorted(path.name for path in out.iterdir()) == [
        "larql_runtime_install_validation_report.json",
        "larql_runtime_install_validation_report.md",
    ]


def test_valid_report_flags_false_and_no_model_or_memory(tmp_path):
    install_dir = ready_runtime_bundle(tmp_path)
    report = write_reports(
        install_dir / "runtime_rules" / "navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0.json",
        install_dir / "larql_runtime_install_report.json",
        tmp_path / "out",
    )
    assert report["runtime_rule_validated_for_consultation"] is True
    assert report["durable_memory_written"] is False
    assert report["candidate_promoted"] is False
    assert report["lora_training_started"] is False
    assert report["model_weights_mutated"] is False
