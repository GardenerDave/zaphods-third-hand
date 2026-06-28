import json
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_larql_apply import write_reports as write_apply
from local_harness.affordance_larql_apply_packet import write_reports as write_apply_packet
from local_harness.affordance_larql_apply_review import write_reports as write_apply_review
from local_harness.affordance_larql_dry_run_packet import sha256_hex, write_reports as write_dry_run_packet
from local_harness.affordance_larql_dry_run_review import write_reports as write_dry_run_review
from local_harness.affordance_larql_runtime_install_packet import write_reports
from local_harness.affordance_larql_validate import write_reports as write_validate


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_larql_runtime_install_packet.py"


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
        "candidate_id": candidate["candidate_id"],
        "source_failure_id": candidate["source_failure_id"],
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


def ready_bundle_path(tmp_path: Path) -> tuple[Path, Path]:
    candidate = write_candidate(tmp_path)
    baseline_result = write_json(tmp_path / "baseline_lane_result_report.json", baseline_result_payload())
    audit = tmp_path / "post_run_audit_report.md"
    audit.write_text(audit_text(), encoding="utf-8")
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
    apply_review_dir = tmp_path / "apply_review"
    apply_review = write_apply_review(
        apply_dir / "larql_apply_packet.json",
        "approve_larql_application",
        "Approve application only.",
        apply_review_dir,
    )
    applied_dir = tmp_path / "applied"
    applied = write_apply(
        apply_dir / "larql_apply_packet.json",
        apply_review_dir / "larql_apply_review.json",
        applied_dir,
    )
    validation_dir = tmp_path / "validated"
    validation = write_validate(
        applied_dir / "larql_rule.json",
        applied_dir / "larql_apply_report.json",
        validation_dir,
    )
    assert dry_run_packet["packet_verdict"] == "ready_for_larql_dry_run_review"
    assert dry_run_review["review_verdict"] == "approved_for_larql_apply_packet_drafting_only"
    assert apply_packet["packet_verdict"] == "ready_for_larql_apply_review"
    assert apply_review["review_verdict"] == "approved_for_larql_application_only"
    assert applied["apply_verdict"] == "larql_rule_artifact_written"
    assert validation["validation_verdict"] == "larql_rule_artifact_validated"
    return applied_dir, validation_dir


def ready_rule_path(tmp_path: Path) -> Path:
    return ready_bundle_path(tmp_path)[0] / "larql_rule.json"


def ready_validation_path(tmp_path: Path) -> Path:
    return ready_bundle_path(tmp_path)[1] / "larql_rule_validation_report.json"


def test_help_works():
    result = run_packet("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_missing_rule_fails(tmp_path):
    validation = ready_validation_path(tmp_path)
    report = write_reports(tmp_path / "missing.json", validation, tmp_path / "out")
    assert report["packet_verdict"] == "invalid_input"


def test_missing_validation_fails(tmp_path):
    bundle = ready_bundle_path(tmp_path)[0]
    report = write_reports(bundle / "larql_rule.json", tmp_path / "missing.json", tmp_path / "out")
    assert report["packet_verdict"] == "invalid_input"


def test_malformed_json_fails(tmp_path):
    rule = tmp_path / "rule.json"
    rule.write_text("{not json\n", encoding="utf-8")
    validation = ready_validation_path(tmp_path)
    report = write_reports(rule, validation, tmp_path / "out")
    assert report["packet_verdict"] == "invalid_input"


def test_wrong_rule_status_fails(tmp_path):
    bundle = ready_bundle_path(tmp_path)[0]
    validation = ready_validation_path(tmp_path)
    payload = json.loads((bundle / "larql_rule.json").read_text(encoding="utf-8"))
    payload["rule_status"] = "installed"
    (bundle / "larql_rule.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(bundle / "larql_rule.json", validation, tmp_path / "out")
    assert report["packet_verdict"] == "invalid_input"


def test_runtime_already_installed_fails(tmp_path):
    bundle = ready_bundle_path(tmp_path)[0]
    validation = ready_validation_path(tmp_path)
    payload = json.loads((bundle / "larql_rule.json").read_text(encoding="utf-8"))
    payload["runtime_installation_status"] = "installed"
    (bundle / "larql_rule.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(bundle / "larql_rule.json", validation, tmp_path / "out")
    assert report["packet_verdict"] == "invalid_input"


def test_validation_not_validated_fails(tmp_path):
    bundle = ready_bundle_path(tmp_path)[0]
    validation = ready_validation_path(tmp_path)
    payload = json.loads(validation.read_text(encoding="utf-8"))
    payload["validation_verdict"] = "wrong"
    validation.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(bundle / "larql_rule.json", validation, tmp_path / "out")
    assert report["packet_verdict"] == "invalid_input"


def test_validation_next_step_wrong_fails(tmp_path):
    bundle = ready_bundle_path(tmp_path)[0]
    validation = ready_validation_path(tmp_path)
    payload = json.loads(validation.read_text(encoding="utf-8"))
    payload["allowed_next_step"] = "wrong"
    validation.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(bundle / "larql_rule.json", validation, tmp_path / "out")
    assert report["packet_verdict"] == "invalid_input"


def test_validation_authorization_flags_true_fail(tmp_path):
    bundle = ready_bundle_path(tmp_path)[0]
    validation = ready_validation_path(tmp_path)
    payload = json.loads(validation.read_text(encoding="utf-8"))
    payload["runtime_installation_authorized"] = True
    validation.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(bundle / "larql_rule.json", validation, tmp_path / "out")
    assert report["packet_verdict"] == "invalid_input"


def test_id_digest_mismatch_fails(tmp_path):
    bundle = ready_bundle_path(tmp_path)[0]
    validation = ready_validation_path(tmp_path)
    payload = json.loads(validation.read_text(encoding="utf-8"))
    payload["candidate_digest"] = "0" * 64
    validation.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(bundle / "larql_rule.json", validation, tmp_path / "out")
    assert report["packet_verdict"] == "invalid_input"


def test_valid_inputs_produce_outputs(tmp_path):
    bundle = ready_bundle_path(tmp_path)[0]
    out = tmp_path / "out"
    report = write_reports(bundle / "larql_rule.json", ready_validation_path(tmp_path), out)
    assert report["packet_verdict"] == "ready_for_runtime_install_review"
    assert sorted(path.name for path in out.iterdir()) == [
        "larql_runtime_install_packet.json",
        "larql_runtime_install_packet.md",
    ]


def test_valid_report_has_false_authorization_flags(tmp_path):
    bundle = ready_bundle_path(tmp_path)[0]
    report = write_reports(bundle / "larql_rule.json", ready_validation_path(tmp_path), tmp_path / "out")
    assert report["runtime_installation_authorized"] is False
    assert report["durable_memory_authorized"] is False
    assert report["candidate_promotion_authorized"] is False
    assert report["lora_training_authorized"] is False
