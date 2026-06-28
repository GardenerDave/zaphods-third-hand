import json
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_larql_dry_run_packet import sha256_hex
from local_harness.affordance_larql_apply_packet import write_reports
from local_harness.affordance_larql_dry_run_packet import write_reports as write_dry_run_packet
from local_harness.affordance_larql_dry_run_review import write_reports as write_dry_run_review


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_larql_apply_packet.py"


def run_packet(*args: str | Path) -> subprocess.CompletedProcess[str]:
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
    payload = baseline_result_payload(**overrides)
    payload["candidate_digest"] = payload["candidate_digest"]
    return write_json(tmp_path / "baseline_lane_result_report.json", payload)


def write_audit(tmp_path: Path, verdict: str = "audit_pass") -> Path:
    path = tmp_path / "post_run_audit_report.md"
    path.write_text(audit_text(verdict), encoding="utf-8")
    return path


def make_ready_packet(tmp_path: Path) -> Path:
    candidate = write_candidate(tmp_path)
    baseline_result = write_baseline_result(tmp_path)
    audit = write_audit(tmp_path)
    packet_dir = tmp_path / "packet"
    packet = write_dry_run_packet(candidate, baseline_result, audit, packet_dir)
    assert packet["packet_verdict"] == "ready_for_larql_dry_run_review"
    return packet_dir / "larql_dry_run_packet.json"


def make_ready_review(tmp_path: Path) -> Path:
    packet = make_ready_packet(tmp_path)
    review_dir = tmp_path / "review"
    review = write_dry_run_review(
        packet,
        "approve_for_larql_apply_packet_drafting",
        "Approve for apply-packet drafting only.",
        review_dir,
    )
    assert review["review_verdict"] == "approved_for_larql_apply_packet_drafting_only"
    return review_dir / "larql_dry_run_review.json"


def test_help_works():
    result = run_packet("--help")

    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_missing_dry_run_packet_fails(tmp_path):
    review = make_ready_review(tmp_path)

    packet = write_reports(tmp_path / "missing.json", review, tmp_path / "out")

    assert packet["packet_verdict"] == "invalid_input"


def test_missing_dry_run_review_fails(tmp_path):
    packet = make_ready_packet(tmp_path)

    apply_packet = write_reports(packet, tmp_path / "missing.json", tmp_path / "out")

    assert apply_packet["packet_verdict"] == "invalid_input"


def test_malformed_json_fails(tmp_path):
    packet = tmp_path / "packet.json"
    packet.write_text("{not json\n", encoding="utf-8")
    review = make_ready_review(tmp_path)

    apply_packet = write_reports(packet, review, tmp_path / "out")

    assert apply_packet["packet_verdict"] == "invalid_input"


def test_wrong_dry_run_report_type_fails(tmp_path):
    packet = make_ready_packet(tmp_path)
    review = make_ready_review(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["report_type"] = "wrong"
    packet.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    apply_packet = write_reports(packet, review, tmp_path / "out")

    assert apply_packet["packet_verdict"] == "invalid_input"


def test_wrong_dry_run_packet_verdict_fails(tmp_path):
    packet = make_ready_packet(tmp_path)
    review = make_ready_review(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["packet_verdict"] = "not_ready"
    packet.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    apply_packet = write_reports(packet, review, tmp_path / "out")

    assert apply_packet["packet_verdict"] == "invalid_input"


def test_dry_run_packet_authorization_flag_true_fails(tmp_path):
    packet = make_ready_packet(tmp_path)
    review = make_ready_review(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["larql_application_authorized"] = True
    packet.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    apply_packet = write_reports(packet, review, tmp_path / "out")

    assert apply_packet["packet_verdict"] == "invalid_input"


def test_dry_run_rule_status_not_draft_not_applied_fails(tmp_path):
    packet = make_ready_packet(tmp_path)
    review = make_ready_review(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["larql_rule_draft"]["status"] = "applied"
    packet.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    apply_packet = write_reports(packet, review, tmp_path / "out")

    assert apply_packet["packet_verdict"] == "invalid_input"


def test_wrong_review_report_type_fails(tmp_path):
    packet = make_ready_packet(tmp_path)
    review = make_ready_review(tmp_path)
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["report_type"] = "wrong"
    review.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    apply_packet = write_reports(packet, review, tmp_path / "out")

    assert apply_packet["packet_verdict"] == "invalid_input"


def test_review_not_approved_fails(tmp_path):
    packet = make_ready_packet(tmp_path)
    review = make_ready_review(tmp_path)
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["review_verdict"] = "rejected_larql_dry_run_packet"
    review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    apply_packet = write_reports(packet, review, tmp_path / "out")

    assert apply_packet["packet_verdict"] == "invalid_input"


def test_review_allowed_next_step_not_draft_larql_apply_packet_fails(tmp_path):
    packet = make_ready_packet(tmp_path)
    review = make_ready_review(tmp_path)
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["allowed_next_step"] = "revise_larql_dry_run_packet"
    review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    apply_packet = write_reports(packet, review, tmp_path / "out")

    assert apply_packet["packet_verdict"] == "invalid_input"


def test_review_authorization_flag_true_fails(tmp_path):
    packet = make_ready_packet(tmp_path)
    review = make_ready_review(tmp_path)
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["larql_application_authorized"] = True
    review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    apply_packet = write_reports(packet, review, tmp_path / "out")

    assert apply_packet["packet_verdict"] == "invalid_input"


def test_candidate_id_mismatch_fails(tmp_path):
    packet = make_ready_packet(tmp_path)
    review = make_ready_review(tmp_path)
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["candidate_id"] = "different"
    review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    apply_packet = write_reports(packet, review, tmp_path / "out")

    assert apply_packet["packet_verdict"] == "invalid_input"


def test_source_failure_id_mismatch_fails(tmp_path):
    packet = make_ready_packet(tmp_path)
    review = make_ready_review(tmp_path)
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["source_failure_id"] = "different"
    review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    apply_packet = write_reports(packet, review, tmp_path / "out")

    assert apply_packet["packet_verdict"] == "invalid_input"


def test_rule_id_mismatch_fails(tmp_path):
    packet = make_ready_packet(tmp_path)
    review = make_ready_review(tmp_path)
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["rule_id"] = "different"
    review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    apply_packet = write_reports(packet, review, tmp_path / "out")

    assert apply_packet["packet_verdict"] == "invalid_input"


def test_valid_inputs_produce_packet_and_markdown(tmp_path):
    packet = make_ready_packet(tmp_path)
    review = make_ready_review(tmp_path)
    out = tmp_path / "out"

    apply_packet = write_reports(packet, review, out)

    assert apply_packet["packet_verdict"] == "ready_for_larql_apply_review"
    assert (out / "larql_apply_packet.json").exists()
    assert (out / "larql_apply_packet.md").exists()


def test_packet_boundary_flags_are_false(tmp_path):
    packet = make_ready_packet(tmp_path)
    review = make_ready_review(tmp_path)

    apply_packet = write_reports(packet, review, tmp_path / "out")

    assert apply_packet["larql_application_authorized"] is False
    assert apply_packet["candidate_promotion_authorized"] is False
    assert apply_packet["durable_memory_authorized"] is False
    assert apply_packet["lora_training_authorized"] is False


def test_packet_contains_proposed_rule_and_criteria(tmp_path):
    packet = make_ready_packet(tmp_path)
    review = make_ready_review(tmp_path)

    apply_packet = write_reports(packet, review, tmp_path / "out")

    proposed = apply_packet["proposed_larql_rule"]
    assert proposed["status"] == "proposed_not_applied"
    assert proposed["rule_id"] == "navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0"
    assert apply_packet["apply_review_criteria"] == [
        "Rule remains scoped to navigator_desktop or matching host evidence/profile constraints.",
        "Rule blocks or warns on CUDA/NVIDIA troubleshooting for RX580/no_cuda hosts.",
        "Rule recommends the LM Studio OpenAI-compatible endpoint path only under matching evidence.",
        "Rule requires reverify when active host is unknown, split, stale, or digest evidence mismatches.",
        "Rule does not promote the candidate or write durable memory.",
    ]


def test_markdown_says_packet_only_and_not_applied(tmp_path):
    packet = make_ready_packet(tmp_path)
    review = make_ready_review(tmp_path)
    out = tmp_path / "out"

    write_reports(packet, review, out)
    markdown = (out / "larql_apply_packet.md").read_text(encoding="utf-8")

    assert "This is packet only." in markdown
    assert "It is not an applied LARQL patch." in markdown
    assert "It is not durable memory." in markdown
    assert "It is not LoRA training." in markdown
    assert "It is not candidate promotion." in markdown
    assert "This packet only permits later review of whether LARQL application should be authorized." in markdown
