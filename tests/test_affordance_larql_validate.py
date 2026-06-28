import json
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_larql_apply import write_reports as write_apply
from local_harness.affordance_larql_apply_packet import write_reports as write_apply_packet
from local_harness.affordance_larql_apply_review import write_reports as write_apply_review
from local_harness.affordance_larql_dry_run_packet import sha256_hex, write_reports as write_dry_run_packet
from local_harness.affordance_larql_dry_run_review import write_reports as write_dry_run_review
from local_harness.affordance_larql_validate import write_reports


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_larql_validate.py"


def run_validate(*args: str | Path) -> subprocess.CompletedProcess[str]:
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


def make_ready_applied_bundle(tmp_path: Path) -> Path:
    candidate = write_candidate(tmp_path)
    baseline_result = write_json(
        tmp_path / "baseline_lane_result_report.json",
        baseline_result_payload(),
    )
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
    apply = write_apply(
        apply_dir / "larql_apply_packet.json",
        apply_review_dir / "larql_apply_review.json",
        tmp_path / "applied",
    )
    assert dry_run_packet["packet_verdict"] == "ready_for_larql_dry_run_review"
    assert dry_run_review["review_verdict"] == "approved_for_larql_apply_packet_drafting_only"
    assert apply_packet["packet_verdict"] == "ready_for_larql_apply_review"
    assert apply_review["review_verdict"] == "approved_for_larql_application_only"
    assert apply["apply_verdict"] == "larql_rule_artifact_written"
    return tmp_path / "applied"


def ready_rule_path(tmp_path: Path) -> Path:
    return make_ready_applied_bundle(tmp_path) / "larql_rule.json"


def ready_apply_report_path(tmp_path: Path) -> Path:
    return make_ready_applied_bundle(tmp_path) / "larql_apply_report.json"


def test_help_works():
    result = run_validate("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_missing_rule_fails(tmp_path):
    apply_report = ready_apply_report_path(tmp_path)

    report = write_reports(tmp_path / "missing.json", apply_report, tmp_path / "out")

    assert report["validation_verdict"] == "invalid_input"


def test_missing_apply_report_fails(tmp_path):
    rule = ready_rule_path(tmp_path)

    report = write_reports(rule, tmp_path / "missing.json", tmp_path / "out")

    assert report["validation_verdict"] == "invalid_input"


def test_malformed_json_fails(tmp_path):
    rule = tmp_path / "rule.json"
    rule.write_text("{not json\n", encoding="utf-8")
    apply_report = ready_apply_report_path(tmp_path)

    report = write_reports(rule, apply_report, tmp_path / "out")

    assert report["validation_verdict"] == "invalid_input"


def test_wrong_rule_type_fails(tmp_path):
    rule = ready_rule_path(tmp_path)
    apply_report = ready_apply_report_path(tmp_path)
    payload = json.loads(rule.read_text(encoding="utf-8"))
    payload["report_type"] = "wrong"
    rule.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = write_reports(rule, apply_report, tmp_path / "out")

    assert report["validation_verdict"] == "invalid_input"


def test_wrong_rule_status_fails(tmp_path):
    rule = ready_rule_path(tmp_path)
    apply_report = ready_apply_report_path(tmp_path)
    payload = json.loads(rule.read_text(encoding="utf-8"))
    payload["rule_status"] = "installed"
    rule.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = write_reports(rule, apply_report, tmp_path / "out")

    assert report["validation_verdict"] == "invalid_input"


def test_runtime_installed_fails(tmp_path):
    rule = ready_rule_path(tmp_path)
    apply_report = ready_apply_report_path(tmp_path)
    payload = json.loads(rule.read_text(encoding="utf-8"))
    payload["runtime_installation_status"] = "installed"
    rule.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = write_reports(rule, apply_report, tmp_path / "out")

    assert report["validation_verdict"] == "invalid_input"


def test_durable_memory_written_fails(tmp_path):
    rule = ready_rule_path(tmp_path)
    apply_report = ready_apply_report_path(tmp_path)
    payload = json.loads(rule.read_text(encoding="utf-8"))
    payload["durable_memory_status"] = "written"
    rule.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = write_reports(rule, apply_report, tmp_path / "out")

    assert report["validation_verdict"] == "invalid_input"


def test_candidate_promoted_fails(tmp_path):
    rule = ready_rule_path(tmp_path)
    apply_report = ready_apply_report_path(tmp_path)
    payload = json.loads(rule.read_text(encoding="utf-8"))
    payload["candidate_promotion_status"] = "promoted"
    rule.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = write_reports(rule, apply_report, tmp_path / "out")

    assert report["validation_verdict"] == "invalid_input"


def test_wrong_apply_report_verdict_fails(tmp_path):
    rule = ready_rule_path(tmp_path)
    apply_report = ready_apply_report_path(tmp_path)
    payload = json.loads(apply_report.read_text(encoding="utf-8"))
    payload["apply_verdict"] = "wrong"
    apply_report.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = write_reports(rule, apply_report, tmp_path / "out")

    assert report["validation_verdict"] == "invalid_input"


def test_id_mismatch_fails(tmp_path):
    rule = ready_rule_path(tmp_path)
    apply_report = ready_apply_report_path(tmp_path)
    payload = json.loads(apply_report.read_text(encoding="utf-8"))
    payload["rule_id"] = "different"
    apply_report.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = write_reports(rule, apply_report, tmp_path / "out")

    assert report["validation_verdict"] == "invalid_input"


def test_digest_mismatch_fails(tmp_path):
    rule = ready_rule_path(tmp_path)
    apply_report = ready_apply_report_path(tmp_path)
    payload = json.loads(apply_report.read_text(encoding="utf-8"))
    payload["candidate_digest"] = "0" * 64
    apply_report.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = write_reports(rule, apply_report, tmp_path / "out")

    assert report["validation_verdict"] == "invalid_input"


def test_empty_rule_lists_fail(tmp_path):
    rule = ready_rule_path(tmp_path)
    apply_report = ready_apply_report_path(tmp_path)
    payload = json.loads(rule.read_text(encoding="utf-8"))
    payload["applies_when"] = []
    rule.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = write_reports(rule, apply_report, tmp_path / "out")

    assert report["validation_verdict"] == "invalid_input"


def test_missing_cuda_nvidia_block_fails(tmp_path):
    rule = ready_rule_path(tmp_path)
    apply_report = ready_apply_report_path(tmp_path)
    payload = json.loads(rule.read_text(encoding="utf-8"))
    payload["blocks_or_warns_on"] = ["CUDA-only setup"]
    rule.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = write_reports(rule, apply_report, tmp_path / "out")

    assert report["validation_verdict"] == "invalid_input"


def test_missing_lm_studio_recommendation_fails(tmp_path):
    rule = ready_rule_path(tmp_path)
    apply_report = ready_apply_report_path(tmp_path)
    payload = json.loads(rule.read_text(encoding="utf-8"))
    payload["recommends"] = ["safe endpoint"]
    rule.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = write_reports(rule, apply_report, tmp_path / "out")

    assert report["validation_verdict"] == "invalid_input"


def test_missing_reverify_conditions_fail(tmp_path):
    rule = ready_rule_path(tmp_path)
    apply_report = ready_apply_report_path(tmp_path)
    payload = json.loads(rule.read_text(encoding="utf-8"))
    payload["requires_reverify_when"] = ["active host is unknown"]
    rule.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = write_reports(rule, apply_report, tmp_path / "out")

    assert report["validation_verdict"] == "invalid_input"


def test_valid_inputs_produce_outputs(tmp_path):
    rule = ready_rule_path(tmp_path)
    apply_report = ready_apply_report_path(tmp_path)
    out = tmp_path / "out"

    report = write_reports(rule, apply_report, out)

    assert report["validation_verdict"] == "larql_rule_artifact_validated"
    assert report["allowed_next_step"] == "draft_larql_runtime_install_packet"
    assert sorted(path.name for path in out.iterdir()) == [
        "larql_rule_validation_report.json",
        "larql_rule_validation_report.md",
    ]


def test_valid_report_has_authorization_flags_false(tmp_path):
    rule = ready_rule_path(tmp_path)
    apply_report = ready_apply_report_path(tmp_path)

    report = write_reports(rule, apply_report, tmp_path / "out")

    assert report["runtime_installation_authorized"] is False
    assert report["durable_memory_authorized"] is False
    assert report["candidate_promotion_authorized"] is False
    assert report["lora_training_authorized"] is False
