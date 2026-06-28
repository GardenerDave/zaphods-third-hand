import json
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_larql_absence_of_evidence_packet import build_packet, write_reports


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_larql_absence_of_evidence_packet.py"


def run_packet(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_help_works():
    result = run_packet("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_packet_accepts_safe_behavior_note(tmp_path):
    packet = build_packet(
        "absence_of_evidence_file_authority.real",
        "absence_of_evidence_file_authority",
        "absence_of_evidence_file_authority_v0",
        "Evidence is bounded. Absence from search is not proof of absence. Use a targeted inspection command or review step. Keep lifecycle authority held until review evidence exists.",
    )
    assert packet["packet_verdict"] == "ready_for_review"
    assert packet["allowed_next_step"] == "review_absence_of_evidence_file_authority_packet"
    assert packet["promotion_verdict"] == "hold_pending_explicit_experiment_approval"
    assert packet["durable_memory_authorized"] is False
    assert packet["candidate_promotion_authorized"] is False
    assert packet["lora_training_authorized"] is False
    assert packet["model_weight_mutation_authorized"] is False
    assert packet["runtime_rule_modification_authorized"] is False
    assert packet["absence_of_evidence_rule_draft"]["status"] == "draft_not_applied"
    assert "absence from search is not proof of absence" in packet["behavior_note"].lower()


def test_packet_rejects_absence_overreach_behavior_note():
    packet = build_packet(
        "absence_of_evidence_file_authority.real",
        "absence_of_evidence_file_authority",
        "absence_of_evidence_file_authority_v0",
        "Search failed, so no file exists and it is safe to delete the path.",
    )
    assert packet["packet_verdict"] == "absence_of_evidence_candidate_packet_rejected"
    assert packet["allowed_next_step"] == "repair_absence_of_evidence_candidate_packet"
    assert packet["checks"]["behavior_note_safe"] is False


def test_write_reports_writes_json_and_markdown(tmp_path):
    out_dir = tmp_path / "out"
    packet = write_reports(
        "absence_of_evidence_file_authority.real",
        "absence_of_evidence_file_authority",
        "absence_of_evidence_file_authority_v0",
        "Evidence is bounded. Absence from search is not proof of absence. Use a targeted inspection command or review step. Keep lifecycle authority held until review evidence exists.",
        out_dir,
    )
    assert packet["packet_verdict"] == "ready_for_review"
    payload = json.loads((out_dir / "absence_of_evidence_file_authority_packet.json").read_text(encoding="utf-8"))
    assert payload["report_type"] == "affordance_larql_absence_of_evidence_packet.v0"
    assert payload["absence_of_evidence_rule_draft"]["rule_id"] == "absence_of_evidence_file_authority_v0"
    assert (out_dir / "absence_of_evidence_file_authority_packet.md").exists()
    assert "absence from search is not proof of absence" in (out_dir / "absence_of_evidence_file_authority_packet.md").read_text(encoding="utf-8").lower()

