import json
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_larql_absence_of_evidence_packet import write_reports as write_packet
from local_harness.affordance_larql_absence_of_evidence_review import write_reports as write_review
from local_harness.affordance_larql_absence_of_evidence_runtime_rule_install import write_reports as write_install
from local_harness.affordance_larql_absence_of_evidence_runtime_rule_packet import write_reports as write_runtime_packet
from local_harness.affordance_larql_absence_of_evidence_runtime_rule_review import write_reports as write_runtime_review
from local_harness.affordance_larql_absence_of_evidence_runtime_consultation_probe import write_reports


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_larql_absence_of_evidence_runtime_consultation_probe.py"
APPROVAL_TEXT = (
    "I approve installing the reviewed absence-of-evidence LARQL runtime rule as a local runtime rule artifact only. "
    "Do not call a model, write training data, write dataset artifacts, write durable memory, promote a candidate, "
    "train LoRA, mutate model weights, or perform automatic failure-to-curriculum capture."
)


def run_probe(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def ready_install_record_file(tmp_path: Path) -> tuple[Path, Path]:
    packet_dir = tmp_path / "packet"
    write_packet(
        "absence_of_evidence_file_authority.real",
        "absence_of_evidence_file_authority",
        "absence_of_evidence_file_authority_v0",
        "Evidence is bounded. Absence from search is not proof of absence. Use a targeted inspection command or review step. Keep lifecycle authority held until review evidence exists.",
        packet_dir,
    )
    review_dir = tmp_path / "review"
    write_review(packet_dir / "absence_of_evidence_file_authority_packet.json", review_dir)
    runtime_rule_packet_dir = tmp_path / "runtime_rule_packet"
    write_runtime_packet(
        review_dir / "absence_of_evidence_file_authority_review.json",
        runtime_rule_packet_dir,
    )
    runtime_rule_review_dir = tmp_path / "runtime_rule_review"
    write_runtime_review(
        runtime_rule_packet_dir / "absence_of_evidence_runtime_rule_packet.json",
        runtime_rule_review_dir,
    )
    install_dir = tmp_path / "install"
    write_install(
        runtime_rule_packet_dir / "absence_of_evidence_runtime_rule_packet.json",
        runtime_rule_review_dir / "absence_of_evidence_runtime_rule_review.json",
        APPROVAL_TEXT,
        install_dir,
    )
    return (
        install_dir / "runtime_rule_install_record.json",
        install_dir / "runtime_rules/absence_of_evidence_file_authority_v0.json",
    )


def test_help_works():
    result = run_probe("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_runtime_consultation_probe_accepts_installed_rule(tmp_path):
    install_record, runtime_rule = ready_install_record_file(tmp_path)
    probe = write_reports(install_record, runtime_rule, tmp_path / "out")
    assert probe["report_type"] == "affordance_larql_absence_of_evidence_runtime_consultation_probe.v0"
    assert probe["probe_status"] == "runtime_consultation_context_packet_only"
    assert probe["probe_verdict"] == "ready_for_absence_of_evidence_model_context_probe"
    assert probe["allowed_next_step"] == "run_absence_of_evidence_model_context_probe"
    assert probe["context_packet_status"] == "drafted_not_injected"
    assert probe["model_call_performed"] is False
    assert probe["training_data_written"] is False
    assert probe["dataset_artifact_written"] is False
    assert probe["durable_memory_written"] is False
    assert probe["candidate_promotion_authorized"] is False
    assert probe["runtime_rule_modification_authorized"] is False
    assert probe["model_weights_mutated"] is False
    assert probe["automatic_failure_to_curriculum_capture_authorized"] is False


def test_missing_install_verdict_rejected(tmp_path):
    install_record, runtime_rule = ready_install_record_file(tmp_path)
    payload = json.loads(install_record.read_text(encoding="utf-8"))
    payload["install_verdict"] = "not_installed"
    install_record.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    probe = write_reports(install_record, runtime_rule, tmp_path / "out")
    assert probe["probe_verdict"] == "absence_of_evidence_model_context_probe_rejected"
    assert probe["checks"]["install_safe"] is False


def test_wrong_rule_id_rejected(tmp_path):
    install_record, runtime_rule = ready_install_record_file(tmp_path)
    payload = json.loads(runtime_rule.read_text(encoding="utf-8"))
    payload["rule_id"] = "other"
    runtime_rule.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    probe = write_reports(install_record, runtime_rule, tmp_path / "out")
    assert probe["probe_verdict"] == "absence_of_evidence_model_context_probe_rejected"
    assert probe["checks"]["ids_match"] is False


def test_missing_held_boundary_rejected(tmp_path):
    install_record, runtime_rule = ready_install_record_file(tmp_path)
    payload = json.loads(runtime_rule.read_text(encoding="utf-8"))
    payload["blocks_or_warns_on"] = [
        "claiming a file, rule, test, artifact, path, branch, or record does not exist merely because it was not found",
    ]
    runtime_rule.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    probe = write_reports(install_record, runtime_rule, tmp_path / "out")
    assert probe["probe_verdict"] == "absence_of_evidence_model_context_probe_rejected"
    assert probe["checks"]["rule_safe"] is False


def test_missing_search_scope_distinction_rejected(tmp_path):
    install_record, runtime_rule = ready_install_record_file(tmp_path)
    payload = json.loads(runtime_rule.read_text(encoding="utf-8"))
    payload["required_response_behavior"] = [
        "state the evidence boundary explicitly",
        "recommend targeted inspection or review",
        "keep cleanup deletion promotion canonicalization overwrite held pending review evidence",
        "preserve failed-run or search-boundary evidence where relevant",
    ]
    runtime_rule.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    probe = write_reports(install_record, runtime_rule, tmp_path / "out")
    assert probe["probe_verdict"] == "absence_of_evidence_model_context_probe_rejected"
    assert probe["checks"]["rule_safe"] is False


def test_missing_targeted_inspection_rejected(tmp_path):
    install_record, runtime_rule = ready_install_record_file(tmp_path)
    payload = json.loads(runtime_rule.read_text(encoding="utf-8"))
    payload["required_response_behavior"] = [
        "state the evidence boundary explicitly",
        "distinguish not found in searched scope from does not exist",
        "keep cleanup deletion promotion canonicalization overwrite held pending review evidence",
        "preserve failed-run or search-boundary evidence where relevant",
    ]
    runtime_rule.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    probe = write_reports(install_record, runtime_rule, tmp_path / "out")
    assert probe["probe_verdict"] == "absence_of_evidence_model_context_probe_rejected"
    assert probe["checks"]["rule_safe"] is False


def test_missing_search_boundary_evidence_preservation_rejected(tmp_path):
    install_record, runtime_rule = ready_install_record_file(tmp_path)
    payload = json.loads(runtime_rule.read_text(encoding="utf-8"))
    payload["required_response_behavior"] = [
        "state the evidence boundary explicitly",
        "distinguish not found in searched scope from does not exist",
        "recommend targeted inspection or review",
        "keep cleanup deletion promotion canonicalization overwrite held pending review evidence",
    ]
    runtime_rule.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    probe = write_reports(install_record, runtime_rule, tmp_path / "out")
    assert probe["probe_verdict"] == "absence_of_evidence_model_context_probe_rejected"
    assert probe["checks"]["rule_safe"] is False


def test_runtime_consultation_probe_writes_json_and_markdown(tmp_path):
    install_record, runtime_rule = ready_install_record_file(tmp_path)
    out_dir = tmp_path / "out"
    probe = write_reports(install_record, runtime_rule, out_dir)
    assert probe["probe_verdict"] == "ready_for_absence_of_evidence_model_context_probe"
    payload = json.loads((out_dir / "absence_of_evidence_runtime_consultation_probe.json").read_text(encoding="utf-8"))
    assert payload["context_packet_status"] == "drafted_not_injected"
    assert (out_dir / "absence_of_evidence_runtime_consultation_context.md").exists()
