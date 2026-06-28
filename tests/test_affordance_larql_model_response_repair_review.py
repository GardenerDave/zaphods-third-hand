import json
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_larql_model_response_repair_packet import write_reports as write_packet
from local_harness.affordance_larql_model_response_repair_review import write_reports
from tests.test_affordance_larql_model_response_repair_packet import ready_review, repair_review_text


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_larql_model_response_repair_review.py"


def run_review(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def ready_packet(tmp_path: Path):
    review = ready_review(tmp_path, repair_review_text())
    repair_dir = tmp_path / "repair_packet"
    write_packet(review, repair_dir)
    return repair_dir / "larql_model_response_repair_packet.json"


def test_help_works():
    result = run_review("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_missing_packet_fails_closed(tmp_path):
    report = write_reports(tmp_path / "missing.json", tmp_path / "out")
    assert report["review_verdict"] == "larql_model_response_repair_review_rejected"


def test_malformed_packet_fails_closed(tmp_path):
    packet = tmp_path / "packet.json"
    packet.write_text("{not json\n", encoding="utf-8")
    report = write_reports(packet, tmp_path / "out")
    assert report["review_verdict"] == "larql_model_response_repair_review_rejected"


def test_wrong_report_type_fails_closed(tmp_path):
    packet = ready_packet(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["report_type"] = "wrong"
    packet.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(packet, tmp_path / "out")
    assert report["review_verdict"] == "larql_model_response_repair_review_rejected"


def test_wrong_packet_verdict_fails_closed(tmp_path):
    packet = ready_packet(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["packet_verdict"] = "wrong"
    packet.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(packet, tmp_path / "out")
    assert report["review_verdict"] == "larql_model_response_repair_review_rejected"


def test_wrong_next_step_fails_closed(tmp_path):
    packet = ready_packet(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["allowed_next_step"] = "wrong"
    packet.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(packet, tmp_path / "out")
    assert report["review_verdict"] == "larql_model_response_repair_review_rejected"


def test_missing_ids_digest_fail_closed(tmp_path):
    packet = ready_packet(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["candidate_digest"] = ""
    packet.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(packet, tmp_path / "out")
    assert report["review_verdict"] == "larql_model_response_repair_review_rejected"


def test_extra_allowed_file_fails_closed(tmp_path):
    packet = ready_packet(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["allowed_files"] = list(payload["allowed_files"]) + ["extra.py"]
    packet.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(packet, tmp_path / "out")
    assert report["review_verdict"] == "larql_model_response_repair_review_rejected"


def test_missing_allowed_file_fails_closed(tmp_path):
    packet = ready_packet(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["allowed_files"] = [payload["allowed_files"][0]]
    packet.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(packet, tmp_path / "out")
    assert report["review_verdict"] == "larql_model_response_repair_review_rejected"


def test_wrong_proposed_repair_target_fails_closed(tmp_path):
    packet = ready_packet(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["proposed_repairs"][0]["target_file"] = "wrong.py"
    packet.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(packet, tmp_path / "out")
    assert report["review_verdict"] == "larql_model_response_repair_review_rejected"


def test_missing_required_repair_phrase_fails_closed(tmp_path):
    packet = ready_packet(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["proposed_repairs"][0]["required_changes"][0] = "No LM Studio mention."
    packet.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(packet, tmp_path / "out")
    assert report["review_verdict"] == "larql_model_response_repair_review_rejected"


def test_any_auth_true_fails_closed(tmp_path):
    packet = ready_packet(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["durable_memory_authorized"] = True
    packet.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(packet, tmp_path / "out")
    assert report["review_verdict"] == "larql_model_response_repair_review_rejected"


def test_current_packet_approves_application_only(tmp_path):
    packet = ready_packet(tmp_path)
    report = write_reports(packet, tmp_path / "out")
    assert report["review_verdict"] == "approved_for_larql_model_response_repair_application_only"
    assert report["allowed_next_step"] == "apply_larql_model_response_repair"


def test_approval_does_not_authorize_memory_promotion_lora_or_weights(tmp_path):
    packet = ready_packet(tmp_path)
    report = write_reports(packet, tmp_path / "out")
    assert report["repair_application_authorized"] is True
    assert report["durable_memory_authorized"] is False
    assert report["candidate_promotion_authorized"] is False
    assert report["lora_training_authorized"] is False
    assert report["model_weight_mutation_authorized"] is False
