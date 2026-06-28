import json
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_larql_absence_of_evidence_packet import write_reports as write_packet
from local_harness.affordance_larql_absence_of_evidence_review import write_reports


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_larql_absence_of_evidence_review.py"


def run_review(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def ready_packet_file(tmp_path: Path) -> Path:
    out_dir = tmp_path / "packet"
    write_packet(
        "absence_of_evidence_file_authority.real",
        "absence_of_evidence_file_authority",
        "absence_of_evidence_file_authority_v0",
        "Evidence is bounded. Absence from search is not proof of absence. Use a targeted inspection command or review step. Keep lifecycle authority held until review evidence exists.",
        out_dir,
    )
    return out_dir / "absence_of_evidence_file_authority_packet.json"


def test_help_works():
    result = run_review("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_review_accepts_safe_packet(tmp_path):
    packet = ready_packet_file(tmp_path)
    review = write_reports(packet, tmp_path / "review")
    assert review["report_type"] == "affordance_larql_absence_of_evidence_review.v0"
    assert review["review_status"] == "review_only"
    assert review["review_verdict"] == "approved_for_absence_of_evidence_rule_draft_only"
    assert review["allowed_next_step"] == "draft_absence_of_evidence_runtime_rule_packet"
    assert review["promotion_verdict"] == "hold_pending_explicit_experiment_approval"
    assert review["candidate_promotion_authorized"] is False
    assert review["durable_memory_authorized"] is False
    assert review["lora_training_authorized"] is False
    assert review["model_weight_mutation_authorized"] is False
    assert review["runtime_rule_modification_authorized"] is False
    assert review["checks"]["packet_report_type_ok"] is True
    assert review["checks"]["draft_status_ok"] is True
    assert review["checks"]["draft_safe"] is True


def test_review_rejects_absence_overreach_packet(tmp_path):
    packet = ready_packet_file(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["behavior_note"] = "Search failed, so no file exists and it is safe to delete the path."
    packet.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    review = write_reports(packet, tmp_path / "review")
    assert review["review_verdict"] == "absence_of_evidence_review_rejected"
    assert review["allowed_next_step"] == "repair_absence_of_evidence_candidate_packet"
    assert review["checks"]["behavior_note_safe"] is False


def test_review_rejects_missing_targeted_inspection_and_boundary(tmp_path):
    packet = ready_packet_file(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["behavior_note"] = "Evidence is bounded."
    packet.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    review = write_reports(packet, tmp_path / "review")
    assert review["review_verdict"] == "absence_of_evidence_review_rejected"
    assert review["checks"]["behavior_note_safe"] is False


def test_review_writes_json_and_markdown(tmp_path):
    packet = ready_packet_file(tmp_path)
    out_dir = tmp_path / "review"
    review = write_reports(packet, out_dir)
    assert review["review_verdict"] == "approved_for_absence_of_evidence_rule_draft_only"
    payload = json.loads((out_dir / "absence_of_evidence_file_authority_review.json").read_text(encoding="utf-8"))
    assert payload["report_type"] == "affordance_larql_absence_of_evidence_review.v0"
    assert payload["allowed_next_step"] == "draft_absence_of_evidence_runtime_rule_packet"
    assert payload["promotion_verdict"] == "hold_pending_explicit_experiment_approval"
    assert payload["candidate_promotion_authorized"] is False
    assert payload["durable_memory_authorized"] is False
    assert payload["lora_training_authorized"] is False
    assert payload["model_weight_mutation_authorized"] is False
    assert (out_dir / "absence_of_evidence_file_authority_review.md").exists()

