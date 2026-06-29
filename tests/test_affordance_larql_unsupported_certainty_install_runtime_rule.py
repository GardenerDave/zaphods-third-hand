from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_larql_unsupported_certainty_install_runtime_rule.py"
PACKET_PATH = ROOT / ".work/affordance_larql_runtime_rule_packets/unsupported_certainty_scope_claim/unsupported_certainty_scope_claim_runtime_rule_packet.json"
REVIEW_PATH = ROOT / ".work/affordance_larql_runtime_rule_packet_reviews/unsupported_certainty_scope_claim/unsupported_certainty_scope_claim_runtime_rule_packet_review.json"
APPROVAL_TEXT = (
    "I approve local runtime-rule artifact install only for unsupported_certainty_scope_claim_v0. "
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
    record = run_install("--packet", packet, "--packet-review", review, "--approval-text", APPROVAL_TEXT, "--out", tmp_path / "out")
    assert record.returncode == 0
    install_record = json.loads((tmp_path / "out/unsupported_certainty_scope_claim_runtime_rule_install.json").read_text(encoding="utf-8"))
    runtime_rule = json.loads((tmp_path / "out/runtime_rules/unsupported_certainty_scope_claim_v0.json").read_text(encoding="utf-8"))
    assert install_record["report_type"] == "affordance_larql_runtime_rule_install.v0"
    assert install_record["install_status"] == "local_runtime_rule_artifact_install_only"
    assert install_record["install_verdict"] == "local_runtime_rule_artifact_installed"
    assert install_record["allowed_next_step"] == "draft_unsupported_certainty_runtime_consultation_probe"
    assert install_record["runtime_rule_status"] == "installed_local_runtime_rule_artifact"
    assert install_record["runtime_rule_install_authorized"] is True
    assert install_record["runtime_rule_modification_authorized"] is False
    assert install_record["local_artifact_install_only"] is True
    assert install_record["model_call_performed"] is False
    assert install_record["training_data_written"] is False
    assert install_record["dataset_artifact_written"] is False
    assert install_record["durable_memory_written"] is False
    assert install_record["candidate_promotion_authorized"] is False
    assert install_record["model_weights_mutated"] is False
    assert install_record["automatic_failure_to_curriculum_capture_authorized"] is False
    assert install_record["approval_basis"] == "explicit_user_approval"
    assert install_record["checks"]["approval_text_safe"] is True
    assert runtime_rule["report_type"] == "affordance_larql_runtime_rule.v0"
    assert runtime_rule["rule_id"] == "unsupported_certainty_scope_claim_v0"
    assert runtime_rule["candidate_id"] == "unsupported_certainty_scope_claim"
    assert runtime_rule["source_failure_id"] == "unsupported_certainty_scope_claim.real"
    assert runtime_rule["rule_status"] == "installed_local_runtime_rule_artifact"
    assert runtime_rule["runtime_rule_scope"] == "local_artifact_only"
    assert runtime_rule["summary"].startswith("A bounded check may support a bounded claim")
    assert runtime_rule["applies_when"] == [
        "checked scope only",
        "a validation command checked only part of the repo",
        "a test suite checked only a specific subset",
        "a file inspection covered only named files",
        "search results covered only a limited scope",
        "a model response is tempted to summarize partial evidence as complete success",
    ]
    assert runtime_rule["blocks"] == [
        "all issues are fixed",
        "no problems remain",
        "whole repo is clean",
        "safe to merge",
        "task complete",
        "guaranteed",
        "always",
        "never",
        "any global certainty claim unsupported by the checked scope",
    ]
    assert runtime_rule["required_response_behavior"] == [
        "state the checked scope",
        "state only the checked scope passed",
        "global claim is not authorized",
        "set global_claim_authorized to false",
        "hold global completion merge cleanliness claims",
        "require broader validation or review before global claims",
        "preserve checked scope, validation output, and unreviewed scope",
    ]
    assert runtime_rule["json_contract"] == {
        "evidence_boundary": "checked scope only",
        "allowed_claim": "the checked scope passed",
        "global_claim_authorized": False,
        "held_claims": [
            "all issues are fixed",
            "no problems remain",
            "whole repo is clean",
            "safe to merge",
            "task complete",
        ],
        "required_next_step": "broader validation or review",
        "evidence_to_preserve": ["checked scope", "validation output", "unreviewed scope"],
    }
    assert runtime_rule["installed_from_packet_sha256"]
    assert runtime_rule["installed_from_review_sha256"]


def test_rejects_missing_approval_text(tmp_path):
    packet, review = good_inputs(tmp_path)
    result = run_install("--packet", packet, "--packet-review", review, "--out", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_wrong_rule_id_in_approval_text(tmp_path):
    packet, review = good_inputs(tmp_path)
    result = run_install(
        "--packet",
        packet,
        "--packet-review",
        review,
        "--approval-text",
        "I approve local runtime-rule artifact install only for other_rule_v0. Do not write training data, dataset artifacts, durable memory, promote a candidate, mutate model weights, modify runtime rules beyond this local install artifact, or perform automatic failure-to-curriculum capture.",
        "--out",
        tmp_path / "out",
    )
    assert result.returncode != 0


def test_rejects_permissive_language(tmp_path):
    packet, review = good_inputs(tmp_path)
    for text in (
        "I approve local runtime-rule artifact install only for unsupported_certainty_scope_claim_v0. You may write training data.",
        "I approve local runtime-rule artifact install only for unsupported_certainty_scope_claim_v0. You may write dataset artifacts.",
        "I approve local runtime-rule artifact install only for unsupported_certainty_scope_claim_v0. You may write durable memory.",
        "I approve local runtime-rule artifact install only for unsupported_certainty_scope_claim_v0. You may promote a candidate.",
        "I approve local runtime-rule artifact install only for unsupported_certainty_scope_claim_v0. You may mutate model weights.",
        "I approve local runtime-rule artifact install only for unsupported_certainty_scope_claim_v0. You may modify runtime rules beyond this local install artifact.",
        "I approve local runtime-rule artifact install only for unsupported_certainty_scope_claim_v0. Automatic failure-to-curriculum capture is allowed.",
    ):
        result = run_install("--packet", packet, "--packet-review", review, "--approval-text", text, "--out", tmp_path / "out")
        assert result.returncode != 0


def test_rejects_wrong_packet_verdict_and_review_verdict(tmp_path):
    packet, review = good_inputs(tmp_path)
    packet_payload = json.loads(packet.read_text(encoding="utf-8"))
    packet_payload["packet_verdict"] = "wrong"
    packet.write_text(json.dumps(packet_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = run_install("--packet", packet, "--packet-review", review, "--approval-text", APPROVAL_TEXT, "--out", tmp_path / "out")
    assert result.returncode != 0

    packet, review = good_inputs(tmp_path)
    review_payload = json.loads(review.read_text(encoding="utf-8"))
    review_payload["review_verdict"] = "wrong"
    review.write_text(json.dumps(review_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = run_install("--packet", packet, "--packet-review", review, "--approval-text", APPROVAL_TEXT, "--out", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_wrong_review_next_step_and_authority_flags(tmp_path):
    packet, review = good_inputs(tmp_path)
    review_payload = json.loads(review.read_text(encoding="utf-8"))
    review_payload["allowed_next_step"] = "wrong"
    review.write_text(json.dumps(review_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = run_install("--packet", packet, "--packet-review", review, "--approval-text", APPROVAL_TEXT, "--out", tmp_path / "out")
    assert result.returncode != 0

    packet, review = good_inputs(tmp_path)
    review_payload = json.loads(review.read_text(encoding="utf-8"))
    review_payload["runtime_rule_install_authorized"] = True
    review.write_text(json.dumps(review_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = run_install("--packet", packet, "--packet-review", review, "--approval-text", APPROVAL_TEXT, "--out", tmp_path / "out")
    assert result.returncode != 0


def test_reviewable_path_writes_record_and_rule(tmp_path):
    packet, review = good_inputs(tmp_path)
    from local_harness.affordance_larql_unsupported_certainty_install_runtime_rule import write_reports

    record = write_reports(packet, review, APPROVAL_TEXT, tmp_path / "out")
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
