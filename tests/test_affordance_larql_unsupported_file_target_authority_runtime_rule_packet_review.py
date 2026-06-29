from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_larql_unsupported_file_target_authority_runtime_rule_packet_review.py"
PACKET_PATH = (
    ROOT
    / ".work/affordance_larql_runtime_rule_packets/unsupported_file_target_authority/unsupported_file_target_authority_runtime_rule_packet.json"
)


def run_review(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def packet_payload() -> dict:
    return json.loads(PACKET_PATH.read_text(encoding="utf-8"))


def good_packet(tmp_path: Path) -> Path:
    path = tmp_path / "packet.json"
    path.write_text(PACKET_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    return path


def build_review(packet: dict, checks: dict[str, bool]) -> dict:
    from local_harness.affordance_larql_unsupported_file_target_authority_runtime_rule_packet_review import build_review

    return build_review(packet, checks)


def full_checks(packet: dict) -> dict[str, bool]:
    from local_harness.affordance_larql_unsupported_file_target_authority_runtime_rule_packet_review import draft_checks

    draft = packet.get("draft_runtime_rule") if isinstance(packet.get("draft_runtime_rule"), dict) else {}
    return {
        "packet_exists": True,
        "packet_parses": True,
        "packet_report_type_ok": packet.get("report_type") == "affordance_larql_runtime_rule_packet.v0",
        "packet_status_ok": packet.get("packet_status") == "draft_not_installed",
        "packet_verdict_ok": packet.get("packet_verdict") == "ready_for_runtime_rule_packet_review",
        "packet_next_step_ok": packet.get("allowed_next_step")
        == "review_unsupported_file_target_authority_runtime_rule_packet",
        "source_failure_id_ok": packet.get("source_failure_id") == "unsupported_file_target_authority.real",
        "candidate_id_ok": packet.get("candidate_id") == "unsupported_file_target_authority",
        "rule_id_ok": packet.get("rule_id") == "unsupported_file_target_authority_v0",
        "runtime_rule_status_ok": packet.get("runtime_rule_status") == "draft_not_installed",
        "runtime_rule_install_authorized_false": packet.get("runtime_rule_install_authorized") is False,
        "runtime_rule_modification_authorized_false": packet.get("runtime_rule_modification_authorized") is False,
        "model_call_performed_false": packet.get("model_call_performed") is False,
        "training_data_written_false": packet.get("training_data_written") is False,
        "dataset_artifact_written_false": packet.get("dataset_artifact_written") is False,
        "durable_memory_written_false": packet.get("durable_memory_written") is False,
        "candidate_promotion_authorized_false": packet.get("candidate_promotion_authorized") is False,
        "model_weights_mutated_false": packet.get("model_weights_mutated") is False,
        "automatic_failure_to_curriculum_capture_authorized_false": packet.get(
            "automatic_failure_to_curriculum_capture_authorized"
        )
        is False,
        "candidate_sha256_present": bool(packet.get("candidate_sha256")),
        "candidate_review_sha256_present": bool(packet.get("candidate_review_sha256")),
        **draft_checks(draft),
    }


def test_help_works():
    result = run_review("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


def test_accepts_valid_packet(tmp_path):
    packet = good_packet(tmp_path)
    result = run_review("--packet", packet, "--out", tmp_path / "out")
    assert result.returncode == 0
    payload = json.loads(
        (tmp_path / "out/unsupported_file_target_authority_runtime_rule_packet_review.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["report_type"] == "affordance_larql_runtime_rule_packet_review.v0"
    assert payload["review_status"] == "runtime_rule_packet_review_only"
    assert (
        payload["review_verdict"]
        == "approved_unsupported_file_target_authority_runtime_rule_packet_for_install_approval_boundary"
    )
    assert (
        payload["allowed_next_step"]
        == "hold_for_explicit_unsupported_file_target_authority_runtime_rule_install_approval"
    )
    assert payload["runtime_rule_install_authorized"] is False
    assert payload["runtime_rule_modification_authorized"] is False
    assert payload["model_call_performed_in_review"] is False
    assert payload["training_data_written"] is False
    assert payload["dataset_artifact_written"] is False
    assert payload["durable_memory_written"] is False
    assert payload["candidate_promotion_authorized"] is False
    assert payload["model_weights_mutated"] is False
    assert payload["automatic_failure_to_curriculum_capture_authorized"] is False
    assert all(payload["checks"].values())


def test_rejects_missing_packet(tmp_path):
    result = run_review("--packet", tmp_path / "missing.json", "--out", tmp_path / "out")
    assert result.returncode == 0
    payload = json.loads(
        (tmp_path / "out/unsupported_file_target_authority_runtime_rule_packet_review.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["checks"]["packet_exists"] is False
    assert payload["review_verdict"] == "rejected_unsupported_file_target_authority_runtime_rule_packet"


def test_rejects_wrong_top_level_fields():
    packet = packet_payload()
    bad_map = {
        "report_type": "wrong",
        "packet_status": "wrong",
        "packet_verdict": "wrong",
        "allowed_next_step": "wrong",
        "source_failure_id": "wrong.real",
        "candidate_id": "wrong",
        "rule_id": "wrong_v0",
    }
    expected = {
        "report_type": "packet_report_type_ok",
        "packet_status": "packet_status_ok",
        "packet_verdict": "packet_verdict_ok",
        "allowed_next_step": "packet_next_step_ok",
        "source_failure_id": "source_failure_id_ok",
        "candidate_id": "candidate_id_ok",
        "rule_id": "rule_id_ok",
    }
    for field, value in bad_map.items():
        bad = json.loads(json.dumps(packet))
        bad[field] = value
        review = build_review(bad, full_checks(bad))
        assert review["review_verdict"] == "rejected_unsupported_file_target_authority_runtime_rule_packet"
        assert review["checks"][expected[field]] is False


def test_rejects_boundary_flags_true():
    packet = packet_payload()
    fields = (
        "runtime_rule_install_authorized",
        "runtime_rule_modification_authorized",
        "model_call_performed",
        "training_data_written",
        "dataset_artifact_written",
        "durable_memory_written",
        "candidate_promotion_authorized",
        "model_weights_mutated",
        "automatic_failure_to_curriculum_capture_authorized",
    )
    for field in fields:
        bad = json.loads(json.dumps(packet))
        bad[field] = True
        review = build_review(bad, full_checks(bad))
        assert review["review_verdict"] == "rejected_unsupported_file_target_authority_runtime_rule_packet"


def test_rejects_missing_sha_fields_and_draft():
    packet = packet_payload()
    bad = json.loads(json.dumps(packet))
    bad["candidate_sha256"] = ""
    review = build_review(bad, full_checks(bad))
    assert review["checks"]["candidate_sha256_present"] is False
    bad = json.loads(json.dumps(packet))
    bad["candidate_review_sha256"] = ""
    review = build_review(bad, full_checks(bad))
    assert review["checks"]["candidate_review_sha256_present"] is False
    bad = json.loads(json.dumps(packet))
    bad.pop("draft_runtime_rule")
    review = build_review(bad, full_checks(bad))
    assert review["checks"]["draft_present"] is False


def test_rejects_wrong_draft_summary():
    packet = packet_payload()
    bad = json.loads(json.dumps(packet))
    bad["draft_runtime_rule"]["summary"] = "wrong"
    review = build_review(bad, full_checks(bad))
    assert review["checks"]["draft_summary_ok"] is False


def test_rejects_missing_applies_when_item():
    packet = packet_payload()
    bad = json.loads(json.dumps(packet))
    bad["draft_runtime_rule"]["applies_when"].remove("a checklist names target files")
    review = build_review(bad, full_checks(bad))
    assert review["checks"]["draft_applies_when_ok"] is False


def test_rejects_missing_block():
    packet = packet_payload()
    bad = json.loads(json.dumps(packet))
    bad["draft_runtime_rule"]["blocks"].remove("also fix")
    review = build_review(bad, full_checks(bad))
    assert review["checks"]["draft_blocks_ok"] is False


def test_rejects_missing_required_response_behavior_item():
    packet = packet_payload()
    bad = json.loads(json.dumps(packet))
    bad["draft_runtime_rule"]["required_response_behavior"].remove("outside file modification is not authorized")
    review = build_review(bad, full_checks(bad))
    assert review["checks"]["draft_required_response_behavior_ok"] is False


def test_rejects_wrong_json_contract_value():
    packet = packet_payload()
    bad = json.loads(json.dumps(packet))
    bad["draft_runtime_rule"]["json_contract"]["allowed_claim"] = "wrong"
    review = build_review(bad, full_checks(bad))
    assert review["checks"]["draft_json_contract_ok"] is False


def test_review_performs_no_model_call():
    packet = packet_payload()
    review = build_review(packet, full_checks(packet))
    assert review["model_call_performed_in_review"] is False
