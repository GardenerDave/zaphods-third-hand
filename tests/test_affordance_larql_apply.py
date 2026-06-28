import json
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_larql_apply import write_reports
from local_harness.affordance_larql_apply_packet import write_reports as write_apply_packet
from local_harness.affordance_larql_apply_review import write_reports as write_apply_review
from local_harness.affordance_larql_dry_run_packet import sha256_hex, write_reports as write_dry_run_packet
from local_harness.affordance_larql_dry_run_review import write_reports as write_dry_run_review


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_larql_apply.py"


def run_apply(*args: str | Path) -> subprocess.CompletedProcess[str]:
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


def make_ready_apply_packet(tmp_path: Path) -> Path:
    candidate = write_candidate(tmp_path)
    baseline_result = write_baseline_result(tmp_path)
    audit = write_audit(tmp_path)
    packet_dir = tmp_path / "packet"
    dry_run_packet = write_dry_run_packet(candidate, baseline_result, audit, packet_dir)
    review_dir = tmp_path / "review"
    dry_run_review = write_dry_run_review(
        packet_dir / "larql_dry_run_packet.json",
        "approve_for_larql_apply_packet_drafting",
        "Approve for apply-packet drafting only.",
        review_dir,
    )
    apply_dir = tmp_path / "apply"
    apply_packet = write_apply_packet(
        packet_dir / "larql_dry_run_packet.json",
        review_dir / "larql_dry_run_review.json",
        apply_dir,
    )
    assert dry_run_packet["packet_verdict"] == "ready_for_larql_dry_run_review"
    assert dry_run_review["review_verdict"] == "approved_for_larql_apply_packet_drafting_only"
    assert apply_packet["packet_verdict"] == "ready_for_larql_apply_review"
    return apply_dir / "larql_apply_packet.json"


def make_ready_review(tmp_path: Path) -> Path:
    packet = make_ready_apply_packet(tmp_path)
    review_dir = tmp_path / "apply_review"
    review = write_apply_review(
        packet,
        "approve_larql_application",
        "Approve application only.",
        review_dir,
    )
    assert review["review_verdict"] == "approved_for_larql_application_only"
    return review_dir / "larql_apply_review.json"


def test_help_works():
    result = run_apply("--help")

    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_missing_apply_packet_fails(tmp_path):
    review = make_ready_review(tmp_path)

    report = write_reports(tmp_path / "missing.json", review, tmp_path / "out")

    assert report["apply_verdict"] == "invalid_input"


def test_missing_apply_review_fails(tmp_path):
    packet = make_ready_apply_packet(tmp_path)

    report = write_reports(packet, tmp_path / "missing.json", tmp_path / "out")

    assert report["apply_verdict"] == "invalid_input"


def test_malformed_json_fails(tmp_path):
    packet = tmp_path / "packet.json"
    packet.write_text("{not json\n", encoding="utf-8")
    review = make_ready_review(tmp_path)

    report = write_reports(packet, review, tmp_path / "out")

    assert report["apply_verdict"] == "invalid_input"


def test_help_works_via_cli():
    result = run_apply("--help")

    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_wrong_apply_packet_report_type_fails(tmp_path):
    packet = make_ready_apply_packet(tmp_path)
    review = make_ready_review(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["report_type"] = "wrong"
    packet.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    report = write_reports(packet, review, tmp_path / "out")

    assert report["apply_verdict"] == "invalid_input"


def test_wrong_apply_packet_verdict_fails(tmp_path):
    packet = make_ready_apply_packet(tmp_path)
    review = make_ready_review(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["packet_verdict"] = "not_ready"
    packet.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    report = write_reports(packet, review, tmp_path / "out")

    assert report["apply_verdict"] == "invalid_input"


def test_apply_packet_authorization_flags_not_false_fail(tmp_path):
    packet = make_ready_apply_packet(tmp_path)
    review = make_ready_review(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["larql_application_authorized"] = True
    packet.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = write_reports(packet, review, tmp_path / "out")

    assert report["apply_verdict"] == "invalid_input"


def test_proposed_rule_status_not_proposed_not_applied_fails(tmp_path):
    packet = make_ready_apply_packet(tmp_path)
    review = make_ready_review(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["proposed_larql_rule"]["status"] = "applied"
    packet.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = write_reports(packet, review, tmp_path / "out")

    assert report["apply_verdict"] == "invalid_input"


def test_missing_proposed_rule_fields_fail(tmp_path):
    packet = make_ready_apply_packet(tmp_path)
    review = make_ready_review(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    del payload["proposed_larql_rule"]["rule_id"]
    packet.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = write_reports(packet, review, tmp_path / "out")

    assert report["apply_verdict"] == "invalid_input"


def test_missing_other_proposed_rule_fields_fail(tmp_path):
    packet = make_ready_apply_packet(tmp_path)
    review = make_ready_review(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    del payload["proposed_larql_rule"]["applies_when"]
    packet.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = write_reports(packet, review, tmp_path / "out")

    assert report["apply_verdict"] == "invalid_input"


def test_wrong_apply_review_report_type_fails(tmp_path):
    packet = make_ready_apply_packet(tmp_path)
    review = make_ready_review(tmp_path)
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["report_type"] = "wrong"
    review.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    report = write_reports(packet, review, tmp_path / "out")

    assert report["apply_verdict"] == "invalid_input"


def test_apply_review_not_approved_fails(tmp_path):
    packet = make_ready_apply_packet(tmp_path)
    review = make_ready_review(tmp_path)
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["review_verdict"] = "rejected_larql_application"
    review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = write_reports(packet, review, tmp_path / "out")

    assert report["apply_verdict"] == "invalid_input"


def test_apply_review_allowed_next_step_wrong_fails(tmp_path):
    packet = make_ready_apply_packet(tmp_path)
    review = make_ready_review(tmp_path)
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["allowed_next_step"] = "revise_larql_apply_packet"
    review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = write_reports(packet, review, tmp_path / "out")

    assert report["apply_verdict"] == "invalid_input"


def test_apply_review_larql_application_not_true_fails(tmp_path):
    packet = make_ready_apply_packet(tmp_path)
    review = make_ready_review(tmp_path)
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["larql_application_authorized"] = False
    review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = write_reports(packet, review, tmp_path / "out")

    assert report["apply_verdict"] == "invalid_input"


def test_apply_review_authorization_flags_true_fail(tmp_path):
    packet = make_ready_apply_packet(tmp_path)
    review = make_ready_review(tmp_path)
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["candidate_promotion_authorized"] = True
    review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = write_reports(packet, review, tmp_path / "out")

    assert report["apply_verdict"] == "invalid_input"


def test_candidate_id_mismatch_fails(tmp_path):
    packet = make_ready_apply_packet(tmp_path)
    review = make_ready_review(tmp_path)
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["candidate_id"] = "different"
    review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = write_reports(packet, review, tmp_path / "out")

    assert report["apply_verdict"] == "invalid_input"


def test_source_failure_id_mismatch_fails(tmp_path):
    packet = make_ready_apply_packet(tmp_path)
    review = make_ready_review(tmp_path)
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["source_failure_id"] = "different"
    review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = write_reports(packet, review, tmp_path / "out")

    assert report["apply_verdict"] == "invalid_input"


def test_rule_id_mismatch_fails(tmp_path):
    packet = make_ready_apply_packet(tmp_path)
    review = make_ready_review(tmp_path)
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["rule_id"] = "different"
    review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = write_reports(packet, review, tmp_path / "out")

    assert report["apply_verdict"] == "invalid_input"


def test_candidate_digest_mismatch_fails(tmp_path):
    packet = make_ready_apply_packet(tmp_path)
    review = make_ready_review(tmp_path)
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["candidate_digest"] = "0" * 64
    review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = write_reports(packet, review, tmp_path / "out")

    assert report["apply_verdict"] == "invalid_input"


def test_valid_inputs_write_all_four_outputs(tmp_path):
    packet = make_ready_apply_packet(tmp_path)
    review = make_ready_review(tmp_path)
    out = tmp_path / "out"

    report = write_reports(packet, review, out)

    assert report["apply_verdict"] == "larql_rule_artifact_written"
    assert sorted(path.name for path in out.iterdir()) == [
        "larql_apply_report.json",
        "larql_apply_report.md",
        "larql_rule.json",
        "larql_rule.md",
    ]


def test_larql_rule_json_has_bounded_artifact_status(tmp_path):
    packet = make_ready_apply_packet(tmp_path)
    review = make_ready_review(tmp_path)
    out = tmp_path / "out"

    write_reports(packet, review, out)
    rule = json.loads((out / "larql_rule.json").read_text(encoding="utf-8"))

    assert rule["rule_status"] == "applied_as_bounded_artifact"
    assert rule["runtime_installation_status"] == "not_installed"
    assert rule["durable_memory_status"] == "not_written"
    assert rule["candidate_promotion_status"] == "not_promoted"


def test_apply_report_boundary_flags_are_false(tmp_path):
    packet = make_ready_apply_packet(tmp_path)
    review = make_ready_review(tmp_path)

    report = write_reports(packet, review, tmp_path / "out")

    assert report["runtime_behavior_modified"] is False
    assert report["durable_memory_written"] is False
    assert report["candidate_promoted"] is False
    assert report["lora_training_started"] is False
    assert report["model_weights_mutated"] is False


def test_markdown_states_boundary_clearly(tmp_path):
    packet = make_ready_apply_packet(tmp_path)
    review = make_ready_review(tmp_path)
    out = tmp_path / "out"

    write_reports(packet, review, out)
    markdown = (out / "larql_apply_report.md").read_text(encoding="utf-8")

    assert "This is packet only." in markdown
    assert "It is not an applied LARQL patch." in markdown
    assert "It is not durable memory." in markdown
    assert "It is not LoRA training." in markdown
    assert "It is not candidate promotion." in markdown
    assert "The rule artifact is written for later validation; runtime installation is not performed." in markdown


def test_script_writes_all_outputs(tmp_path):
    packet = make_ready_apply_packet(tmp_path)
    review = make_ready_review(tmp_path)
    out = tmp_path / "out"

    report = write_reports(packet, review, out)

    assert report["larql_rule_artifact_written"] is True
    assert report["candidate_promotion_authorized"] is False
    assert report["durable_memory_authorized"] is False
    assert report["lora_training_authorized"] is False
    assert sorted(path.name for path in out.iterdir()) == [
        "larql_apply_report.json",
        "larql_apply_report.md",
        "larql_rule.json",
        "larql_rule.md",
    ]
