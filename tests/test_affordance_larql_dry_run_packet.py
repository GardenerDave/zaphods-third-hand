import json
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_larql_dry_run_packet import sha256_hex, write_reports


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_larql_dry_run_packet.py"


def run_packet(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def candidate_payload(**overrides):
    payload = {
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
    payload.update(overrides)
    return payload


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


def write_candidate(tmp_path: Path, **overrides) -> Path:
    return write_json(tmp_path / "candidate.json", candidate_payload(**overrides))


def write_baseline_result(tmp_path: Path, **overrides) -> Path:
    return write_json(tmp_path / "baseline_lane_result_report.json", baseline_result_payload(**overrides))


def write_audit(tmp_path: Path, verdict: str = "audit_pass") -> Path:
    path = tmp_path / "post_run_audit_report.md"
    path.write_text(audit_text(verdict), encoding="utf-8")
    return path


def test_help_works():
    result = run_packet("--help")

    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_missing_files_fail(tmp_path):
    baseline_result = write_baseline_result(tmp_path)
    audit = write_audit(tmp_path)

    packet = write_reports(tmp_path / "missing.json", baseline_result, audit, tmp_path / "out")

    assert packet["packet_verdict"] == "invalid_input"


def test_malformed_json_fails(tmp_path):
    candidate = tmp_path / "candidate.json"
    candidate.write_text("{not json\n", encoding="utf-8")
    baseline_result = write_baseline_result(tmp_path)
    audit = write_audit(tmp_path)

    packet = write_reports(candidate, baseline_result, audit, tmp_path / "out")

    assert packet["packet_verdict"] == "invalid_input"


def test_non_pass_baseline_fails(tmp_path):
    candidate = write_candidate(tmp_path)
    baseline_result = write_baseline_result(tmp_path, result_verdict="baseline_needs_review")
    audit = write_audit(tmp_path)

    packet = write_reports(candidate, baseline_result, audit, tmp_path / "out")

    assert packet["packet_verdict"] == "invalid_input"


def test_audit_without_audit_pass_fails(tmp_path):
    candidate = write_candidate(tmp_path)
    baseline_result = write_baseline_result(tmp_path)
    audit = write_audit(tmp_path, verdict="audit_needs_review")

    packet = write_reports(candidate, baseline_result, audit, tmp_path / "out")

    assert packet["packet_verdict"] == "invalid_input"


def test_candidate_digest_mismatch_fails(tmp_path):
    candidate = write_candidate(tmp_path)
    baseline_result = write_baseline_result(tmp_path, candidate_digest="0" * 64)
    audit = write_audit(tmp_path)

    packet = write_reports(candidate, baseline_result, audit, tmp_path / "out")

    assert packet["packet_verdict"] == "invalid_input"
    assert packet["checks"]["candidate_digest_matches"] is False


def test_promotion_not_held_fails(tmp_path):
    candidate = write_candidate(tmp_path)
    baseline_result = write_baseline_result(tmp_path, promotion_verdict="promoted")
    audit = write_audit(tmp_path)

    packet = write_reports(candidate, baseline_result, audit, tmp_path / "out")

    assert packet["packet_verdict"] == "invalid_input"


def test_selected_lane_mismatch_fails(tmp_path):
    candidate = write_candidate(tmp_path)
    baseline_result = write_baseline_result(tmp_path, selected_lane="larql_affordance_patch_probe_only")
    audit = write_audit(tmp_path)

    packet = write_reports(candidate, baseline_result, audit, tmp_path / "out")

    assert packet["packet_verdict"] == "invalid_input"


def test_valid_inputs_produce_packet_and_markdown(tmp_path):
    candidate = write_candidate(tmp_path)
    baseline_result = write_baseline_result(tmp_path)
    audit = write_audit(tmp_path)
    out = tmp_path / "out"

    packet = write_reports(candidate, baseline_result, audit, out)

    assert packet["packet_verdict"] == "ready_for_larql_dry_run_review"
    assert (out / "larql_dry_run_packet.json").exists()
    assert (out / "larql_dry_run_packet.md").exists()


def test_packet_boundary_flags_are_false(tmp_path):
    candidate = write_candidate(tmp_path)
    baseline_result = write_baseline_result(tmp_path)
    audit = write_audit(tmp_path)

    packet = write_reports(candidate, baseline_result, audit, tmp_path / "out")

    assert packet["larql_application_authorized"] is False
    assert packet["candidate_promotion_authorized"] is False
    assert packet["durable_memory_authorized"] is False
    assert packet["lora_training_authorized"] is False


def test_packet_contains_larql_rule_draft_fields(tmp_path):
    candidate = write_candidate(tmp_path)
    baseline_result = write_baseline_result(tmp_path)
    audit = write_audit(tmp_path)

    packet = write_reports(candidate, baseline_result, audit, tmp_path / "out")

    draft = packet["larql_rule_draft"]
    assert draft["rule_id"] == "navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0"
    assert draft["status"] == "draft_not_applied"
    assert "active execution host matches navigator_desktop" in draft["applies_when"][0]
    assert "host constraint includes no_cuda" in draft["applies_when"][1]
    assert "CUDA-only setup on RX580" in draft["applies_when"][2]


def test_markdown_says_dry_run_only_and_not_applied(tmp_path):
    candidate = write_candidate(tmp_path)
    baseline_result = write_baseline_result(tmp_path)
    audit = write_audit(tmp_path)
    out = tmp_path / "out"

    write_reports(candidate, baseline_result, audit, out)
    markdown = (out / "larql_dry_run_packet.md").read_text(encoding="utf-8")

    assert "This is a dry-run packet only." in markdown
    assert "It is not an applied LARQL patch." in markdown
    assert "It is not durable memory." in markdown
    assert "It is not LoRA training." in markdown
    assert "It is not promotion." in markdown
    assert "whether a later LARQL apply packet should be drafted" in markdown
