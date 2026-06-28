import json
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_larql_dry_run_packet import sha256_hex
from local_harness.affordance_larql_dry_run_review import write_reports
from local_harness.affordance_larql_dry_run_packet import write_reports as write_packet


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_larql_dry_run_review.py"


def run_review(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def candidate_payload():
    return {
        "candidate_id": "larql_affordance_candidate_48efff9852ea",
        "source_failure_id": "cuda_on_navigator_desktop.real",
        "host_profile_ids": ["navigator_desktop"],
        "host_affordance_context": {
            "constraints": ["no_cuda"],
            "known_bad_paths": ["CUDA-only setup on RX580"],
            "known_good_paths": [
                "LM Studio OpenAI-compatible endpoint for small-model GPU-backed workflow"
            ],
        },
    }


def baseline_result_payload(**overrides):
    candidate = candidate_payload()
    payload = {
        "report_type": "affordance_baseline_lane_result.v0",
        "candidate_id": "larql_affordance_candidate_48efff9852ea",
        "source_failure_id": "cuda_on_navigator_desktop.real",
        "selected_lane": "baseline_prompt_context_only",
        "result_verdict": "baseline_pass",
        "promotion_verdict": "hold_pending_explicit_experiment_approval",
        "candidate_digest": sha256_hex(candidate),
        "prompt_suite_digest": "20ded9c8b629030ec6e5f24800567cbc0d8ad594035b8c32c72775177acae2f7",
    }
    payload.update(overrides)
    return payload


def audit_text(verdict: str = "audit_pass") -> str:
    return "\n".join(
        [
            "# Baseline Affordance Post-Run Audit",
            "",
            f"Final audit verdict: `{verdict}`",
            "",
        ]
    )


def write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_candidate(tmp_path: Path) -> Path:
    return write_json(tmp_path / "candidate.json", candidate_payload())


def write_baseline_result(tmp_path: Path, **overrides) -> Path:
    return write_json(tmp_path / "baseline_lane_result_report.json", baseline_result_payload(**overrides))


def write_audit(tmp_path: Path, verdict: str = "audit_pass") -> Path:
    path = tmp_path / "post_run_audit_report.md"
    path.write_text(audit_text(verdict), encoding="utf-8")
    return path


def make_ready_packet(tmp_path: Path) -> Path:
    candidate = write_candidate(tmp_path)
    baseline_result = write_baseline_result(tmp_path)
    audit = write_audit(tmp_path)
    out = tmp_path / "packet"
    packet = write_packet(candidate, baseline_result, audit, out)
    assert packet["packet_verdict"] == "ready_for_larql_dry_run_review"
    return out / "larql_dry_run_packet.json"


def test_help_works():
    result = run_review("--help")

    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_missing_packet_fails(tmp_path):
    review = write_reports(
        tmp_path / "missing.json",
        "approve_for_larql_apply_packet_drafting",
        "summary",
        tmp_path / "out",
    )

    assert review["review_verdict"] == "invalid_input"


def test_malformed_json_fails(tmp_path):
    packet = tmp_path / "packet.json"
    packet.write_text("{not json\n", encoding="utf-8")

    review = write_reports(
        packet,
        "approve_for_larql_apply_packet_drafting",
        "summary",
        tmp_path / "out",
    )

    assert review["review_verdict"] == "invalid_input"


def test_wrong_report_type_fails(tmp_path):
    packet_path = make_ready_packet(tmp_path)
    payload = json.loads(packet_path.read_text(encoding="utf-8"))
    payload["report_type"] = "wrong"
    packet_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    review = write_reports(
        packet_path,
        "approve_for_larql_apply_packet_drafting",
        "summary",
        tmp_path / "out",
    )

    assert review["review_verdict"] == "invalid_input"


def test_wrong_packet_verdict_fails(tmp_path):
    packet_path = make_ready_packet(tmp_path)
    payload = json.loads(packet_path.read_text(encoding="utf-8"))
    payload["packet_verdict"] = "not_ready"
    packet_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    review = write_reports(
        packet_path,
        "approve_for_larql_apply_packet_drafting",
        "summary",
        tmp_path / "out",
    )

    assert review["review_verdict"] == "invalid_input"


def test_baseline_not_pass_fails(tmp_path):
    candidate = write_candidate(tmp_path)
    baseline_result = write_baseline_result(tmp_path, result_verdict="baseline_needs_review")
    audit = write_audit(tmp_path)
    packet = write_packet(candidate, baseline_result, audit, tmp_path / "packet")
    packet_path = tmp_path / "packet" / "larql_dry_run_packet.json"

    review = write_reports(
        packet_path,
        "approve_for_larql_apply_packet_drafting",
        "summary",
        tmp_path / "out",
    )

    assert review["review_verdict"] == "invalid_input"


def test_audit_not_pass_fails(tmp_path):
    candidate = write_candidate(tmp_path)
    baseline_result = write_baseline_result(tmp_path)
    audit = write_audit(tmp_path, verdict="audit_needs_review")
    write_packet(candidate, baseline_result, audit, tmp_path / "packet")
    packet_path = tmp_path / "packet" / "larql_dry_run_packet.json"

    review = write_reports(
        packet_path,
        "approve_for_larql_apply_packet_drafting",
        "summary",
        tmp_path / "out",
    )

    assert review["review_verdict"] == "invalid_input"


def test_candidate_digest_not_verified_fails(tmp_path):
    candidate = write_candidate(tmp_path)
    baseline_result = write_baseline_result(tmp_path, candidate_digest="0" * 64)
    audit = write_audit(tmp_path)
    write_packet(candidate, baseline_result, audit, tmp_path / "packet")
    packet_path = tmp_path / "packet" / "larql_dry_run_packet.json"

    review = write_reports(
        packet_path,
        "approve_for_larql_apply_packet_drafting",
        "summary",
        tmp_path / "out",
    )

    assert review["review_verdict"] == "invalid_input"


def test_promotion_not_held_fails(tmp_path):
    candidate = write_candidate(tmp_path)
    baseline_result = write_baseline_result(tmp_path, promotion_verdict="promoted")
    audit = write_audit(tmp_path)
    write_packet(candidate, baseline_result, audit, tmp_path / "packet")
    packet_path = tmp_path / "packet" / "larql_dry_run_packet.json"

    review = write_reports(
        packet_path,
        "approve_for_larql_apply_packet_drafting",
        "summary",
        tmp_path / "out",
    )

    assert review["review_verdict"] == "invalid_input"


def test_any_authorization_flag_true_fails(tmp_path):
    candidate = write_candidate(tmp_path)
    baseline_result = write_baseline_result(tmp_path)
    audit = write_audit(tmp_path)
    write_packet(candidate, baseline_result, audit, tmp_path / "packet")
    packet_path = tmp_path / "packet" / "larql_dry_run_packet.json"
    payload = json.loads(packet_path.read_text(encoding="utf-8"))
    payload["larql_application_authorized"] = True
    packet_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    review = write_reports(
        packet_path,
        "approve_for_larql_apply_packet_drafting",
        "summary",
        tmp_path / "out",
    )

    assert review["review_verdict"] == "invalid_input"


def test_draft_status_not_draft_not_applied_fails(tmp_path):
    candidate = write_candidate(tmp_path)
    baseline_result = write_baseline_result(tmp_path)
    audit = write_audit(tmp_path)
    write_packet(candidate, baseline_result, audit, tmp_path / "packet")
    packet_path = tmp_path / "packet" / "larql_dry_run_packet.json"
    payload = json.loads(packet_path.read_text(encoding="utf-8"))
    payload["larql_rule_draft"]["status"] = "applied"
    packet_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    review = write_reports(
        packet_path,
        "approve_for_larql_apply_packet_drafting",
        "summary",
        tmp_path / "out",
    )

    assert review["review_verdict"] == "invalid_input"


def test_approve_decision_produces_approved_review(tmp_path):
    packet_path = make_ready_packet(tmp_path)

    review = write_reports(
        packet_path,
        "approve_for_larql_apply_packet_drafting",
        "Approve for apply-packet drafting only.",
        tmp_path / "out",
    )

    assert review["review_verdict"] == "approved_for_larql_apply_packet_drafting_only"
    assert review["allowed_next_step"] == "draft_larql_apply_packet"
    assert review["larql_application_authorized"] is False
    assert review["candidate_promotion_authorized"] is False
    assert review["durable_memory_authorized"] is False
    assert review["lora_training_authorized"] is False


def test_reject_decision_produces_rejected_review(tmp_path):
    packet_path = make_ready_packet(tmp_path)

    review = write_reports(
        packet_path,
        "reject_larql_dry_run_packet",
        "Reject this dry-run packet.",
        tmp_path / "out",
    )

    assert review["review_verdict"] == "rejected_larql_dry_run_packet"
    assert review["allowed_next_step"] == "revise_larql_dry_run_packet"


def test_markdown_says_review_only_and_no_larql_patch_is_applied(tmp_path):
    packet_path = make_ready_packet(tmp_path)
    out = tmp_path / "out"

    write_reports(
        packet_path,
        "approve_for_larql_apply_packet_drafting",
        "Approve for apply-packet drafting only.",
        out,
    )
    markdown = (out / "larql_dry_run_review.md").read_text(encoding="utf-8")

    assert "This is review only." in markdown
    assert "No LARQL patch is applied." in markdown
    assert "No durable memory is written." in markdown
    assert "No LoRA training is authorized." in markdown
    assert "No candidate promotion is granted." in markdown
    assert "Approval only permits drafting a later apply packet." in markdown
