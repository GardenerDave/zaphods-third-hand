from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_larql_unsupported_file_target_authority_install_runtime_rule.py"
PACKET_PATH = (
    ROOT
    / ".work/affordance_larql_runtime_rule_packets/unsupported_file_target_authority/unsupported_file_target_authority_runtime_rule_packet.json"
)
REVIEW_PATH = (
    ROOT
    / ".work/affordance_larql_runtime_rule_packet_reviews/unsupported_file_target_authority/unsupported_file_target_authority_runtime_rule_packet_review.json"
)
APPROVAL_TEXT = (
    "I approve local runtime-rule artifact install only for unsupported_file_target_authority_v0. "
    "Do not write training data, dataset artifacts, durable memory, promote a candidate, mutate model weights, "
    "modify runtime rules beyond this local install artifact, or perform automatic failure-to-curriculum capture."
)


def run_install(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def good_inputs(tmp_path: Path) -> tuple[Path, Path]:
    packet = tmp_path / "packet.json"
    review = tmp_path / "review.json"
    packet.write_text(PACKET_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    review.write_text(REVIEW_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    return packet, review


def test_help_works():
    result = run_install("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


def test_accepts_exact_explicit_approval_text(tmp_path):
    packet, review = good_inputs(tmp_path)
    result = run_install("--packet", packet, "--packet-review", review, "--approval-text", APPROVAL_TEXT, "--out", tmp_path / "out")
    assert result.returncode == 0
    record = json.loads(
        (tmp_path / "out/unsupported_file_target_authority_runtime_rule_install.json").read_text(encoding="utf-8")
    )
    rule = json.loads(
        (tmp_path / "out/runtime_rules/unsupported_file_target_authority_v0.json").read_text(encoding="utf-8")
    )
    assert record["report_type"] == "affordance_larql_runtime_rule_install.v0"
    assert record["install_status"] == "local_runtime_rule_artifact_install_only"
    assert record["install_verdict"] == "local_runtime_rule_artifact_installed"
    assert record["allowed_next_step"] == "draft_unsupported_file_target_authority_runtime_consultation_probe"
    assert record["runtime_rule_status"] == "installed_local_runtime_rule_artifact"
    assert record["runtime_rule_install_authorized"] is True
    assert record["runtime_rule_modification_authorized"] is False
    assert record["local_artifact_install_only"] is True
    assert record["model_call_performed"] is False
    assert record["training_data_written"] is False
    assert record["dataset_artifact_written"] is False
    assert record["durable_memory_written"] is False
    assert record["candidate_promotion_authorized"] is False
    assert record["model_weights_mutated"] is False
    assert record["automatic_failure_to_curriculum_capture_authorized"] is False
    assert record["approval_basis"] == "explicit_user_approval"
    assert record["approval_text_sha256"]
    assert record["packet_sha256"]
    assert record["review_sha256"]
    assert record["installed_rule_sha256"]
    assert rule["report_type"] == "affordance_larql_runtime_rule.v0"
    assert rule["rule_id"] == "unsupported_file_target_authority_v0"
    assert rule["candidate_id"] == "unsupported_file_target_authority"
    assert rule["source_failure_id"] == "unsupported_file_target_authority.real"
    assert rule["rule_status"] == "installed_local_runtime_rule_artifact"
    assert rule["runtime_rule_scope"] == "local_artifact_only"
    assert rule["summary"] == (
        "An allowed_files list authorizes only listed target files; it does not authorize modifying adjacent, generated, unrelated, or any other repo files."
    )


def test_rejects_missing_approval_text(tmp_path):
    packet, review = good_inputs(tmp_path)
    result = run_install("--packet", packet, "--packet-review", review, "--approval-text", "", "--out", tmp_path / "out")
    assert result.returncode != 0
    assert not (tmp_path / "out/runtime_rules/unsupported_file_target_authority_v0.json").exists()


def test_rejects_wrong_rule_id_in_approval_text(tmp_path):
    packet, review = good_inputs(tmp_path)
    text = APPROVAL_TEXT.replace("unsupported_file_target_authority_v0", "wrong_rule_v0")
    result = run_install("--packet", packet, "--packet-review", review, "--approval-text", text, "--out", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_permissive_approval_language(tmp_path):
    packet, review = good_inputs(tmp_path)
    bad_texts = [
        "I approve local runtime-rule artifact install only for unsupported_file_target_authority_v0. You may write training data.",
        "I approve local runtime-rule artifact install only for unsupported_file_target_authority_v0. You may write dataset artifacts.",
        "I approve local runtime-rule artifact install only for unsupported_file_target_authority_v0. You may write durable memory.",
        "I approve local runtime-rule artifact install only for unsupported_file_target_authority_v0. You may promote a candidate.",
        "I approve local runtime-rule artifact install only for unsupported_file_target_authority_v0. You may mutate model weights.",
        "I approve local runtime-rule artifact install only for unsupported_file_target_authority_v0. You may modify runtime rules beyond this local install artifact.",
        "I approve local runtime-rule artifact install only for unsupported_file_target_authority_v0. Automatic failure-to-curriculum capture is allowed.",
    ]
    for text in bad_texts:
        result = run_install("--packet", packet, "--packet-review", review, "--approval-text", text, "--out", tmp_path / "out")
        assert result.returncode != 0


def test_rejects_wrong_packet_fields(tmp_path):
    packet, review = good_inputs(tmp_path)
    fields = {
        "report_type": "wrong",
        "packet_status": "wrong",
        "packet_verdict": "wrong",
        "allowed_next_step": "wrong",
    }
    for field, value in fields.items():
        payload = json.loads(packet.read_text(encoding="utf-8"))
        payload[field] = value
        packet.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        result = run_install("--packet", packet, "--packet-review", review, "--approval-text", APPROVAL_TEXT, "--out", tmp_path / "out")
        assert result.returncode != 0
        packet, review = good_inputs(tmp_path)


def test_rejects_packet_install_and_modification_flags(tmp_path):
    packet, review = good_inputs(tmp_path)
    for field in ("runtime_rule_install_authorized", "runtime_rule_modification_authorized"):
        payload = json.loads(packet.read_text(encoding="utf-8"))
        payload[field] = True
        packet.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        result = run_install("--packet", packet, "--packet-review", review, "--approval-text", APPROVAL_TEXT, "--out", tmp_path / "out")
        assert result.returncode != 0
        packet, review = good_inputs(tmp_path)


def test_rejects_wrong_review_fields(tmp_path):
    packet, review = good_inputs(tmp_path)
    fields = {
        "report_type": "wrong",
        "review_status": "wrong",
        "review_verdict": "wrong",
        "allowed_next_step": "wrong",
    }
    for field, value in fields.items():
        payload = json.loads(review.read_text(encoding="utf-8"))
        payload[field] = value
        review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        result = run_install("--packet", packet, "--packet-review", review, "--approval-text", APPROVAL_TEXT, "--out", tmp_path / "out")
        assert result.returncode != 0
        packet, review = good_inputs(tmp_path)


def test_rejects_review_install_and_modification_flags(tmp_path):
    packet, review = good_inputs(tmp_path)
    for field in ("runtime_rule_install_authorized", "runtime_rule_modification_authorized"):
        payload = json.loads(review.read_text(encoding="utf-8"))
        payload[field] = True
        review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        result = run_install("--packet", packet, "--packet-review", review, "--approval-text", APPROVAL_TEXT, "--out", tmp_path / "out")
        assert result.returncode != 0
        packet, review = good_inputs(tmp_path)


def test_rejects_mismatched_identifiers(tmp_path):
    packet, review = good_inputs(tmp_path)
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["candidate_id"] = "wrong"
    review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = run_install("--packet", packet, "--packet-review", review, "--approval-text", APPROVAL_TEXT, "--out", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_model_and_boundary_flags(tmp_path):
    packet, review = good_inputs(tmp_path)
    packet_fields = (
        "model_call_performed",
        "training_data_written",
        "dataset_artifact_written",
        "durable_memory_written",
        "candidate_promotion_authorized",
        "model_weights_mutated",
        "automatic_failure_to_curriculum_capture_authorized",
    )
    for field in packet_fields:
        payload = json.loads(packet.read_text(encoding="utf-8"))
        payload[field] = True
        packet.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        result = run_install("--packet", packet, "--packet-review", review, "--approval-text", APPROVAL_TEXT, "--out", tmp_path / "out")
        assert result.returncode != 0
        packet, review = good_inputs(tmp_path)
    review_fields = (
        "model_call_performed_in_review",
        "training_data_written",
        "dataset_artifact_written",
        "durable_memory_written",
        "candidate_promotion_authorized",
        "model_weights_mutated",
        "automatic_failure_to_curriculum_capture_authorized",
    )
    for field in review_fields:
        payload = json.loads(review.read_text(encoding="utf-8"))
        payload[field] = True
        review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        result = run_install("--packet", packet, "--packet-review", review, "--approval-text", APPROVAL_TEXT, "--out", tmp_path / "out")
        assert result.returncode != 0
        packet, review = good_inputs(tmp_path)


def test_installed_runtime_rule_has_exact_expected_content(tmp_path):
    packet, review = good_inputs(tmp_path)
    from local_harness.affordance_larql_unsupported_file_target_authority_install_runtime_rule import write_reports

    write_reports(packet, review, APPROVAL_TEXT, tmp_path / "out")
    rule = json.loads(
        (tmp_path / "out/runtime_rules/unsupported_file_target_authority_v0.json").read_text(encoding="utf-8")
    )
    assert rule["applies_when"] == [
        "allowed_files list is present",
        "a patch packet names allowed files",
        "a checklist names target files",
        "a requested target file is not in allowed_files",
        "a model response proposes adjacent file edits",
        "a workflow is tempted to do broader cleanup while here",
    ]
    assert rule["blocks"] == [
        "modify any repo file",
        "touch adjacent files",
        "update generated files",
        "fix unrelated files",
        "expand patch scope",
        "broader cleanup",
        "while here",
        "also fix",
        "any out-of-scope file modification unsupported by allowed_files",
    ]
    assert rule["required_response_behavior"] == [
        "state the allowed_files boundary",
        "state only listed files are authorized targets",
        "outside file modification is not authorized",
        "set outside_file_modification_authorized to false",
        "hold adjacent generated unrelated file modifications",
        "request explicit scope expansion or review before out-of-scope edits",
        "preserve allowed_files list, requested target file, and out-of-scope file",
    ]
    assert rule["json_contract"] == {
        "evidence_boundary": "allowed files only",
        "allowed_claim": "only listed files are authorized targets",
        "outside_file_modification_authorized": False,
        "held_claims": [
            "modify any repo file",
            "touch adjacent files",
            "update generated files",
            "fix unrelated files",
            "expand patch scope",
        ],
        "required_next_step": "request explicit scope expansion or review",
        "evidence_to_preserve": [
            "allowed_files list",
            "requested target file",
            "out-of-scope file",
        ],
    }


def test_install_record_has_exact_expected_authority_flags(tmp_path):
    packet, review = good_inputs(tmp_path)
    result = run_install("--packet", packet, "--packet-review", review, "--approval-text", APPROVAL_TEXT, "--out", tmp_path / "out")
    assert result.returncode == 0
    record = json.loads(
        (tmp_path / "out/unsupported_file_target_authority_runtime_rule_install.json").read_text(encoding="utf-8")
    )
    assert record["runtime_rule_install_authorized"] is True
    assert record["runtime_rule_modification_authorized"] is False
    assert record["model_call_performed"] is False
    assert record["training_data_written"] is False
    assert record["dataset_artifact_written"] is False
    assert record["durable_memory_written"] is False
    assert record["candidate_promotion_authorized"] is False
    assert record["model_weights_mutated"] is False
    assert record["automatic_failure_to_curriculum_capture_authorized"] is False


def test_install_does_not_call_model(tmp_path):
    packet, review = good_inputs(tmp_path)
    result = run_install("--packet", packet, "--packet-review", review, "--approval-text", APPROVAL_TEXT, "--out", tmp_path / "out")
    assert result.returncode == 0
    assert "call_model" not in result.stdout.lower()
