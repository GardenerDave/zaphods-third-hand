import json
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_larql_absence_of_evidence_packet import write_reports as write_packet
from local_harness.affordance_larql_absence_of_evidence_review import write_reports as write_review
from local_harness.affordance_larql_absence_of_evidence_runtime_rule_packet import write_reports as write_runtime_rule_packet
from local_harness.affordance_larql_absence_of_evidence_runtime_rule_review import write_reports


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_larql_absence_of_evidence_runtime_rule_review.py"


def run_rule_review(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def ready_runtime_rule_packet_file(tmp_path: Path) -> Path:
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
    runtime_rule_review_dir = tmp_path / "runtime_rule_review"
    write_runtime_rule_packet(
        review_dir / "absence_of_evidence_file_authority_review.json",
        runtime_rule_review_dir,
    )
    return runtime_rule_review_dir / "absence_of_evidence_runtime_rule_packet.json"


def test_help_works():
    result = run_rule_review("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_runtime_rule_review_accepts_ready_packet(tmp_path):
    packet = ready_runtime_rule_packet_file(tmp_path)
    review = write_reports(packet, tmp_path / "out")
    assert review["report_type"] == "affordance_larql_absence_of_evidence_runtime_rule_review.v0"
    assert review["review_status"] == "runtime_rule_review_only"
    assert review["review_verdict"] == "approved_for_absence_of_evidence_runtime_rule_install_approval_boundary"
    assert review["allowed_next_step"] == "hold_for_explicit_absence_of_evidence_runtime_rule_install_approval"
    assert review["runtime_rule_status"] == "reviewed_not_installed"
    assert review["runtime_rule_install_authorized"] is False
    assert review["runtime_rule_modification_authorized"] is False
    assert review["candidate_promotion_authorized"] is False
    assert review["durable_memory_authorized"] is False
    assert review["lora_training_authorized"] is False
    assert review["model_weight_mutation_authorized"] is False


def test_runtime_rule_review_rejects_wrong_next_step(tmp_path):
    packet = ready_runtime_rule_packet_file(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["allowed_next_step"] = "something_else"
    packet.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    review = write_reports(packet, tmp_path / "out")
    assert review["review_verdict"] == "absence_of_evidence_runtime_rule_review_rejected"
    assert review["checks"]["packet_next_step_ok"] is False


def test_runtime_rule_review_rejects_authority_flags_true(tmp_path):
    packet = ready_runtime_rule_packet_file(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["candidate_promotion_authorized"] = True
    packet.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    review = write_reports(packet, tmp_path / "out")
    assert review["review_verdict"] == "absence_of_evidence_runtime_rule_review_rejected"
    assert review["checks"]["candidate_promotion_authorized_false"] is False


def test_runtime_rule_review_rejects_missing_boundary_language(tmp_path):
    packet = ready_runtime_rule_packet_file(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["absence_of_evidence_runtime_rule_draft"]["required_response_behavior"] = [
        "state the evidence boundary explicitly",
        "recommend targeted inspection or review",
    ]
    packet.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    review = write_reports(packet, tmp_path / "out")
    assert review["review_verdict"] == "absence_of_evidence_runtime_rule_review_rejected"
    assert review["checks"]["draft_safe"] is False


def test_runtime_rule_review_writes_json_and_markdown(tmp_path):
    packet = ready_runtime_rule_packet_file(tmp_path)
    out_dir = tmp_path / "out"
    review = write_reports(packet, out_dir)
    assert review["review_verdict"] == "approved_for_absence_of_evidence_runtime_rule_install_approval_boundary"
    payload = json.loads((out_dir / "absence_of_evidence_runtime_rule_review.json").read_text(encoding="utf-8"))
    assert payload["runtime_rule_status"] == "reviewed_not_installed"
    assert payload["runtime_rule_install_authorized"] is False
    assert (out_dir / "absence_of_evidence_runtime_rule_review.md").exists()
