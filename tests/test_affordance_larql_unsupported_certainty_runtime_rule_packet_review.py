from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_larql_unsupported_certainty_runtime_rule_packet_review.py"
PACKET_PATH = ROOT / ".work/affordance_larql_runtime_rule_packets/unsupported_certainty_scope_claim/unsupported_certainty_scope_claim_runtime_rule_packet.json"


def run_review(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def good_packet(tmp_path: Path) -> Path:
    path = tmp_path / "packet.json"
    path.write_text(PACKET_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    return path


def test_help_works():
    result = run_review("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


def test_accepts_valid_packet(tmp_path):
    packet = good_packet(tmp_path)
    review = run_review("--packet", packet, "--out", tmp_path / "out")
    assert review.returncode == 0
    payload = json.loads((tmp_path / "out/unsupported_certainty_scope_claim_runtime_rule_packet_review.json").read_text(encoding="utf-8"))
    assert payload["report_type"] == "affordance_larql_runtime_rule_packet_review.v0"
    assert payload["review_status"] == "runtime_rule_packet_review_only"
    assert payload["review_verdict"] == "approved_unsupported_certainty_scope_claim_runtime_rule_packet_for_install_approval_boundary"
    assert payload["allowed_next_step"] == "hold_for_explicit_unsupported_certainty_runtime_rule_install_approval"
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


def test_rejects_wrong_report_type(tmp_path):
    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
    packet["report_type"] = "wrong"
    path = tmp_path / "packet.json"
    path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    from local_harness.affordance_larql_unsupported_certainty_runtime_rule_packet_review import build_review

    review = build_review(packet, {"packet_parses": True})
    assert review["review_verdict"] == "rejected_unsupported_certainty_scope_claim_runtime_rule_packet"


def test_rejects_wrong_packet_verdict_and_next_step():
    from local_harness.affordance_larql_unsupported_certainty_runtime_rule_packet_review import build_review

    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
    packet["packet_verdict"] = "wrong"
    review = build_review(packet, {"packet_parses": True})
    assert review["review_verdict"] == "rejected_unsupported_certainty_scope_claim_runtime_rule_packet"

    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
    packet["allowed_next_step"] = "wrong"
    review = build_review(packet, {"packet_parses": True})
    assert review["review_verdict"] == "rejected_unsupported_certainty_scope_claim_runtime_rule_packet"


def test_rejects_authority_flags_true(tmp_path):
    from local_harness.affordance_larql_unsupported_certainty_runtime_rule_packet_review import build_review

    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
    for key in (
        "runtime_rule_install_authorized",
        "runtime_rule_modification_authorized",
        "model_call_performed",
        "training_data_written",
        "dataset_artifact_written",
        "durable_memory_written",
        "candidate_promotion_authorized",
        "model_weights_mutated",
        "automatic_failure_to_curriculum_capture_authorized",
    ):
        bad = json.loads(json.dumps(packet))
        bad[key] = True
        assert build_review(bad, {"packet_parses": True})["review_verdict"] == "rejected_unsupported_certainty_scope_claim_runtime_rule_packet"


def test_rejects_missing_draft_and_contract_items():
    from local_harness.affordance_larql_unsupported_certainty_runtime_rule_packet_review import build_review

    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
    bad = json.loads(json.dumps(packet))
    bad.pop("draft_runtime_rule")
    assert build_review(bad, {"packet_parses": True})["review_verdict"] == "rejected_unsupported_certainty_scope_claim_runtime_rule_packet"

    bad = json.loads(json.dumps(packet))
    bad["draft_runtime_rule"]["rule_id"] = "wrong"
    assert build_review(bad, {"packet_parses": True})["review_verdict"] == "rejected_unsupported_certainty_scope_claim_runtime_rule_packet"

    bad = json.loads(json.dumps(packet))
    bad["draft_runtime_rule"]["applies_when"].remove("checked scope only")
    assert build_review(bad, {"packet_parses": True})["review_verdict"] == "rejected_unsupported_certainty_scope_claim_runtime_rule_packet"

    bad = json.loads(json.dumps(packet))
    bad["draft_runtime_rule"]["blocks"].remove("safe to merge")
    assert build_review(bad, {"packet_parses": True})["review_verdict"] == "rejected_unsupported_certainty_scope_claim_runtime_rule_packet"

    bad = json.loads(json.dumps(packet))
    bad["draft_runtime_rule"]["required_response_behavior"].remove("global claim is not authorized")
    assert build_review(bad, {"packet_parses": True})["review_verdict"] == "rejected_unsupported_certainty_scope_claim_runtime_rule_packet"

    bad = json.loads(json.dumps(packet))
    bad["json_contract"]["allowed_claim"] = "wrong"
    assert build_review(bad, {"packet_parses": True})["review_verdict"] == "rejected_unsupported_certainty_scope_claim_runtime_rule_packet"


def test_review_does_not_call_model():
    from local_harness.affordance_larql_unsupported_certainty_runtime_rule_packet_review import build_review

    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
    review = build_review(packet, {"packet_parses": True})
    assert review["model_call_performed_in_review"] is False
