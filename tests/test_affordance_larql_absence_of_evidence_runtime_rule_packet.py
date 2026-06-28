import json
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_larql_absence_of_evidence_packet import write_reports as write_packet
from local_harness.affordance_larql_absence_of_evidence_review import write_reports as write_review
from local_harness.affordance_larql_absence_of_evidence_runtime_rule_packet import write_reports


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_larql_absence_of_evidence_runtime_rule_packet.py"


def run_rule_packet(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def ready_review_file(tmp_path: Path) -> Path:
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
    return review_dir / "absence_of_evidence_file_authority_review.json"


def test_help_works():
    result = run_rule_packet("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_runtime_rule_packet_accepts_review_ready_packet(tmp_path):
    review = ready_review_file(tmp_path)
    packet = write_reports(review, tmp_path / "out")
    assert packet["report_type"] == "affordance_larql_absence_of_evidence_runtime_rule_packet.v0"
    assert packet["packet_status"] == "runtime_rule_packet_only"
    assert packet["packet_verdict"] == "ready_for_absence_of_evidence_runtime_rule_review"
    assert packet["allowed_next_step"] == "review_absence_of_evidence_runtime_rule_packet"
    assert packet["runtime_rule_status"] == "draft_not_installed"
    assert packet["runtime_rule_modification_authorized"] is False
    assert packet["candidate_promotion_authorized"] is False
    assert packet["durable_memory_authorized"] is False
    assert packet["lora_training_authorized"] is False
    assert packet["model_weight_mutation_authorized"] is False
    assert packet["no_auto_capture"] is True
    assert packet["absence_of_evidence_runtime_rule_draft"]["status"] == "draft_not_installed"


def test_runtime_rule_packet_rejects_rejected_review(tmp_path):
    review = ready_review_file(tmp_path)
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["review_verdict"] = "absence_of_evidence_review_rejected"
    review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    packet = write_reports(review, tmp_path / "out")
    assert packet["packet_verdict"] == "absence_of_evidence_runtime_rule_packet_rejected"
    assert packet["allowed_next_step"] == "repair_or_reverify_absence_of_evidence_runtime_rule_inputs"


def test_runtime_rule_packet_rejects_wrong_next_step(tmp_path):
    review = ready_review_file(tmp_path)
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["allowed_next_step"] = "something_else"
    review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    packet = write_reports(review, tmp_path / "out")
    assert packet["packet_verdict"] == "absence_of_evidence_runtime_rule_packet_rejected"
    assert packet["checks"]["review_next_step_ok"] is False


def test_runtime_rule_packet_rejects_authority_flags_true(tmp_path):
    review = ready_review_file(tmp_path)
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["candidate_promotion_authorized"] = True
    review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    packet = write_reports(review, tmp_path / "out")
    assert packet["packet_verdict"] == "absence_of_evidence_runtime_rule_packet_rejected"
    assert packet["checks"]["review_candidate_promotion_authorized_false"] is False


def test_runtime_rule_packet_writes_json_and_markdown(tmp_path):
    review = ready_review_file(tmp_path)
    out_dir = tmp_path / "out"
    packet = write_reports(review, out_dir)
    assert packet["packet_verdict"] == "ready_for_absence_of_evidence_runtime_rule_review"
    payload = json.loads((out_dir / "absence_of_evidence_runtime_rule_packet.json").read_text(encoding="utf-8"))
    assert payload["runtime_rule_status"] == "draft_not_installed"
    assert payload["absence_of_evidence_runtime_rule_draft"]["purpose"].startswith("Prevent treating missing or incomplete evidence")
    assert (out_dir / "absence_of_evidence_runtime_rule_packet.md").exists()

