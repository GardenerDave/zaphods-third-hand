import json
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_larql_absence_of_evidence_packet import write_reports as write_packet
from local_harness.affordance_larql_absence_of_evidence_review import write_reports as write_review
from local_harness.affordance_larql_absence_of_evidence_runtime_rule_install import write_reports
from local_harness.affordance_larql_absence_of_evidence_runtime_rule_packet import write_reports as write_runtime_rule_packet
from local_harness.affordance_larql_absence_of_evidence_runtime_rule_review import write_reports as write_runtime_rule_review


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_larql_absence_of_evidence_runtime_rule_install.py"
APPROVAL_TEXT = (
    "I approve installing the reviewed absence-of-evidence LARQL runtime rule as a local runtime rule artifact only. "
    "Do not call a model, write training data, write dataset artifacts, write durable memory, promote a candidate, "
    "train LoRA, mutate model weights, or perform automatic failure-to-curriculum capture."
)


def run_install(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def ready_runtime_rule_review_file(tmp_path: Path) -> tuple[Path, Path]:
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
    write_runtime_rule_packet(
        review_dir / "absence_of_evidence_file_authority_review.json",
        runtime_rule_packet_dir,
    )
    runtime_rule_review_dir = tmp_path / "runtime_rule_review"
    write_runtime_rule_review(
        runtime_rule_packet_dir / "absence_of_evidence_runtime_rule_packet.json",
        runtime_rule_review_dir,
    )
    return (
        runtime_rule_packet_dir / "absence_of_evidence_runtime_rule_packet.json",
        runtime_rule_review_dir / "absence_of_evidence_runtime_rule_review.json",
    )


def test_help_works():
    result = run_install("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_install_writes_json_artifacts_and_markdown(tmp_path):
    packet, review = ready_runtime_rule_review_file(tmp_path)
    out_dir = tmp_path / "out"
    record = write_reports(packet, review, APPROVAL_TEXT, out_dir)
    runtime_rule_path = out_dir / "runtime_rules/absence_of_evidence_file_authority_v0.json"
    assert runtime_rule_path.exists()
    assert (out_dir / "runtime_rule_install_record.json").exists()
    assert (out_dir / "runtime_rule_install_record.md").exists()
    runtime_rule = json.loads(runtime_rule_path.read_text(encoding="utf-8"))
    assert runtime_rule["report_type"] == "affordance_larql_runtime_rule.v0"
    assert runtime_rule["runtime_rule_status"] == "installed_local_runtime_rule_artifact"
    assert runtime_rule["installation_scope"] == "local_runtime_rule_artifact_only"
    assert runtime_rule["provenance"]["explicit_user_approval_captured"] is True
    record_json = json.loads((out_dir / "runtime_rule_install_record.json").read_text(encoding="utf-8"))
    assert record_json["install_verdict"] == "local_runtime_rule_artifact_installed"
    assert record_json["model_call_performed"] is False
    assert record_json["training_data_written"] is False
    assert record_json["dataset_artifact_written"] is False
    assert record_json["durable_memory_written"] is False
    assert record_json["automatic_failure_to_curriculum_capture_authorized"] is False
    assert record["runtime_rule_install_authorized"] is True


def test_missing_approval_text_rejected(tmp_path):
    packet, review = ready_runtime_rule_review_file(tmp_path)
    result = run_install(packet, review, "--out", tmp_path / "out")
    assert result.returncode != 0


def test_approval_text_rejects_permissive_training_language(tmp_path):
    packet, review = ready_runtime_rule_review_file(tmp_path)
    record = write_reports(
        packet,
        review,
        "I approve installing the reviewed absence-of-evidence LARQL runtime rule as a local runtime rule artifact only. "
        "You may write training data and you may promote a candidate.",
        tmp_path / "out",
    )
    assert record["install_verdict"] == "absence_of_evidence_runtime_rule_install_rejected"
    assert record["checks"]["approval_text_safe"] is False


def test_approval_text_rejects_permissive_weight_language(tmp_path):
    packet, review = ready_runtime_rule_review_file(tmp_path)
    record = write_reports(
        packet,
        review,
        "I approve installing the reviewed absence-of-evidence LARQL runtime rule as a local runtime rule artifact only. "
        "You may mutate model weights and automatic failure-to-curriculum capture is allowed.",
        tmp_path / "out",
    )
    assert record["install_verdict"] == "absence_of_evidence_runtime_rule_install_rejected"
    assert record["checks"]["approval_text_safe"] is False


def test_wrong_review_verdict_rejected(tmp_path):
    packet, review = ready_runtime_rule_review_file(tmp_path)
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["review_verdict"] = "rejected"
    review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    record = write_reports(packet, review, APPROVAL_TEXT, tmp_path / "out")
    assert record["install_verdict"] == "absence_of_evidence_runtime_rule_install_rejected"
    assert record["checks"]["review_verdict_ok"] is False


def test_wrong_review_next_step_rejected(tmp_path):
    packet, review = ready_runtime_rule_review_file(tmp_path)
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["allowed_next_step"] = "something_else"
    review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    record = write_reports(packet, review, APPROVAL_TEXT, tmp_path / "out")
    assert record["install_verdict"] == "absence_of_evidence_runtime_rule_install_rejected"
    assert record["checks"]["review_next_step_ok"] is False


def test_id_mismatch_rejected(tmp_path):
    packet, review = ready_runtime_rule_review_file(tmp_path)
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["candidate_id"] = "other"
    review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    record = write_reports(packet, review, APPROVAL_TEXT, tmp_path / "out")
    assert record["install_verdict"] == "absence_of_evidence_runtime_rule_install_rejected"
    assert record["checks"]["ids_match"] is False


def test_runtime_mutation_flags_rejected(tmp_path):
    packet, review = ready_runtime_rule_review_file(tmp_path)
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["runtime_rule_modification_authorized"] = True
    review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    record = write_reports(packet, review, APPROVAL_TEXT, tmp_path / "out")
    assert record["install_verdict"] == "absence_of_evidence_runtime_rule_install_rejected"
    assert record["checks"]["review_runtime_rule_modification_authorized_false"] is False


def test_candidate_promotion_flag_rejected(tmp_path):
    packet, review = ready_runtime_rule_review_file(tmp_path)
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["candidate_promotion_authorized"] = True
    review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    record = write_reports(packet, review, APPROVAL_TEXT, tmp_path / "out")
    assert record["install_verdict"] == "absence_of_evidence_runtime_rule_install_rejected"
    assert record["checks"]["review_candidate_promotion_authorized_false"] is False


def test_model_mutation_flag_rejected(tmp_path):
    packet, review = ready_runtime_rule_review_file(tmp_path)
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["model_weight_mutation_authorized"] = True
    review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    record = write_reports(packet, review, APPROVAL_TEXT, tmp_path / "out")
    assert record["install_verdict"] == "absence_of_evidence_runtime_rule_install_rejected"
    assert record["checks"]["review_model_weight_mutation_authorized_false"] is False


def test_runtime_rule_boundary_fields_present(tmp_path):
    packet, review = ready_runtime_rule_review_file(tmp_path)
    record = write_reports(packet, review, APPROVAL_TEXT, tmp_path / "out")
    runtime_rule_path = Path(record["runtime_rule_artifact_path"])
    runtime_rule = json.loads(runtime_rule_path.read_text(encoding="utf-8"))
    assert runtime_rule["purpose"].startswith("Prevent treating missing or incomplete evidence")
    combined_blocks = "\n".join(runtime_rule["blocks_or_warns_on"]).lower()
    combined_behavior = "\n".join(runtime_rule["required_response_behavior"]).lower()
    assert "held pending review evidence" in combined_behavior
    assert "does not exist merely because it was not found" in combined_blocks
    assert "distinguish not found in searched scope from does not exist" in combined_behavior
    assert "recommend targeted inspection or review" in combined_behavior
    assert "preserve failed-run or search-boundary evidence where relevant" in combined_behavior
    assert runtime_rule["provenance"]["explicit_user_approval_captured"] is True
    assert record["model_call_performed"] is False
    assert record["training_data_written"] is False
    assert record["dataset_artifact_written"] is False
    assert record["durable_memory_written"] is False
    assert record["automatic_failure_to_curriculum_capture_authorized"] is False
