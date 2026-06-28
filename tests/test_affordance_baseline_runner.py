import json
import subprocess
import sys
import urllib.error
from pathlib import Path

from local_harness import affordance_baseline_runner
from local_harness.affordance_baseline_execution_packet import write_reports as write_packet
from local_harness.affordance_baseline_runner import score_prompt_response, write_reports


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_baseline_runner.py"


def run_runner(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def candidate_payload(**overrides):
    payload = {
        "candidate_id": "larql_affordance_candidate_example",
        "source_failure_id": "navigator_cuda_failure",
        "repair_lane": "larql_plus_lora_candidate",
        "host_profile_ids": ["navigator_desktop"],
        "host_affordance_context": {
            "constraints": ["no_cuda"],
            "known_bad_paths": ["CUDA-only setup on RX580"],
            "known_good_paths": [
                "LM Studio OpenAI-compatible endpoint for small-model GPU-backed workflow"
            ],
        },
        "source_digests": {
            "host_profile_sha256": "a" * 64,
            "failure_note_sha256": "b" * 64,
            "classifier_version": "larql_affordance_probe.v0",
        },
    }
    payload.update(overrides)
    return payload


def approval_payload(**overrides):
    payload = {
        "candidate_id": "larql_affordance_candidate_example",
        "source_failure_id": "navigator_cuda_failure",
        "repair_lane": "larql_plus_lora_candidate",
        "selected_lane": "baseline_prompt_context_only",
        "approval_verdict": "approved_for_baseline_lane_only",
        "execution_verdict": "approved_for_baseline_prompt_context_execution_only",
        "promotion_verdict": "hold_pending_explicit_experiment_approval",
        "allowed_next_step": "draft_baseline_prompt_context_execution_packet",
    }
    payload.update(overrides)
    return payload


def plan_payload(**overrides):
    payload = {
        "candidate_id": "larql_affordance_candidate_example",
        "source_failure_id": "navigator_cuda_failure",
        "repair_lane": "larql_plus_lora_candidate",
        "plan_verdict": "ready_for_execution_approval_review",
        "execution_verdict": "not_approved_for_execution",
        "promotion_verdict": "hold_pending_explicit_experiment_approval",
        "allowed_experiment_lanes": [
            "baseline_prompt_context_only",
            "larql_affordance_patch_probe_only",
            "lora_failure_curriculum_candidate_only",
        ],
    }
    payload.update(overrides)
    return payload


def write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_candidate(tmp_path: Path, **overrides) -> Path:
    return write_json(tmp_path / "candidate.json", candidate_payload(**overrides))


def write_approval(tmp_path: Path, **overrides) -> Path:
    return write_json(tmp_path / "execution_approval.json", approval_payload(**overrides))


def write_plan(tmp_path: Path, **overrides) -> Path:
    return write_json(tmp_path / "experiment_plan.json", plan_payload(**overrides))


def make_ready_packet(tmp_path: Path) -> tuple[Path, Path]:
    candidate = write_candidate(tmp_path)
    approval = write_approval(tmp_path)
    plan = write_plan(tmp_path)
    packet_dir = tmp_path / "packet"
    packet = write_packet(candidate, approval, plan, packet_dir)
    assert packet["packet_verdict"] == "ready_for_bounded_baseline_runner"
    return packet_dir / "baseline_execution_packet.json", candidate


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def overwrite_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def good_response_for_prompt(user_prompt: str) -> str:
    if "baseline_direct_cuda_on_navigator" in user_prompt:
        return (
            "Avoid CUDA because RX580 is AMD/non-NVIDIA and no CUDA is supported here; "
            "use the LM Studio OpenAI-compatible local endpoint or reverify."
        )
    if "baseline_cross_host_boundary" in user_prompt:
        return "Do not generalize to other hosts; require matching host evidence and host profile."
    if "baseline_unknown_host_reverify" in user_prompt:
        return "Reverify the active host hardware and host profile before using this candidate."
    if "baseline_split_workflow_active_host" in user_prompt:
        return (
            "In a local host and remote host split workflow, the active execution "
            "host is the host whose active host profile controls the affordance decision."
        )
    if "baseline_reverify_before_action" in user_prompt:
        return "Reverify before action if configuration changed."
    if "baseline_no_durable_promotion" in user_prompt:
        return "No LARQL, no LoRA, no durable memory, and no promotion has occurred."
    if "baseline_provenance_digest_awareness" in user_prompt:
        return "Preserve the candidate digest and source digest provenance evidence before reporting."
    return "Reverify the host profile and preserve evidence."


def test_help_works():
    result = run_runner("--help")

    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_missing_packet_gives_invalid_packet_report(tmp_path):
    candidate = write_candidate(tmp_path)

    report = write_reports(
        tmp_path / "missing.json",
        candidate,
        "http://example.invalid/v1",
        "test-model",
        tmp_path / "out",
        64,
        1,
    )

    assert report["result_verdict"] == "invalid_packet"
    assert report["required_outputs_written"]["baseline_lane_result_report.json"] is True


def test_missing_candidate_gives_invalid_packet_report(tmp_path):
    packet, _candidate = make_ready_packet(tmp_path)

    report = write_reports(
        packet,
        tmp_path / "missing.json",
        "http://example.invalid/v1",
        "test-model",
        tmp_path / "out",
        64,
        1,
    )

    assert report["result_verdict"] == "invalid_packet"
    assert report["candidate_digest_verified"] is False


def test_wrong_selected_lane_gives_invalid_packet(tmp_path):
    packet, candidate = make_ready_packet(tmp_path)
    payload = load_json(packet)
    payload["selected_lane"] = "larql_affordance_patch_probe_only"
    overwrite_json(packet, payload)

    report = write_reports(
        packet,
        candidate,
        "http://example.invalid/v1",
        "test-model",
        tmp_path / "out",
        64,
        1,
    )

    assert report["result_verdict"] == "invalid_packet"
    assert report["aggregate_checks"]["selected_lane_baseline"] is False


def test_candidate_digest_mismatch_gives_invalid_packet(tmp_path):
    packet, candidate = make_ready_packet(tmp_path)
    mutated = load_json(candidate)
    mutated["source_failure_id"] = "different_failure"
    overwrite_json(candidate, mutated)

    report = write_reports(
        packet,
        candidate,
        "http://example.invalid/v1",
        "test-model",
        tmp_path / "out",
        64,
        1,
    )

    assert report["result_verdict"] == "invalid_packet"
    assert report["candidate_digest_verified"] is False


def test_prompt_suite_digest_mismatch_gives_invalid_packet(tmp_path):
    packet, candidate = make_ready_packet(tmp_path)
    payload = load_json(packet)
    payload["prompt_suite"]["prompts"][0]["prompt"] = "tampered prompt"
    overwrite_json(packet, payload)

    report = write_reports(
        packet,
        candidate,
        "http://example.invalid/v1",
        "test-model",
        tmp_path / "out",
        64,
        1,
    )

    assert report["result_verdict"] == "invalid_packet"
    assert report["prompt_suite_digest_verified"] is False


def test_fake_successful_model_responses_produce_baseline_pass(tmp_path, monkeypatch):
    packet, candidate = make_ready_packet(tmp_path)

    def fake_call(endpoint_url, model_id, system_prompt, user_prompt, max_tokens, timeout):
        return good_response_for_prompt(user_prompt)

    monkeypatch.setattr(affordance_baseline_runner, "call_openai_chat", fake_call)

    report = write_reports(
        packet,
        candidate,
        "http://example.invalid/v1",
        "test-model",
        tmp_path / "out",
        128,
        5,
    )

    assert report["result_verdict"] == "baseline_pass"
    assert report["aggregate_checks"]["all_model_calls_ok"] is True
    assert report["aggregate_checks"]["all_prompt_checks_passed"] is True


def test_direct_cuda_false_negative_phrasing_is_accepted():
    checks = score_prompt_response(
        "baseline_direct_cuda_on_navigator",
        "Avoid CUDA-only setup on RX580 because no_cuda applies to this AMD host.",
    )

    assert all(checks.values())


def test_cross_host_false_negative_phrasing_is_accepted():
    checks = score_prompt_response(
        "baseline_cross_host_boundary",
        "This is not generalizable to other profiles without matching evidence.",
    )

    assert all(checks.values())


def test_revalidation_is_accepted_as_reverify():
    checks = score_prompt_response(
        "baseline_reverify_before_action",
        "Revalidation is required before backend advice if configuration changed.",
    )

    assert all(checks.values())


def test_no_durable_promotion_false_negative_phrasing_is_accepted():
    checks = score_prompt_response(
        "baseline_no_durable_promotion",
        (
            "The run does not apply a LARQL patch, does not train LoRA, and "
            "does not perform durable memory/write/promotion."
        ),
    )

    assert all(checks.values())


def test_split_workflow_scoring_requires_active_execution_host_language():
    checks = score_prompt_response(
        "baseline_split_workflow_active_host",
        (
            "The local host and remote host are distinct; the active execution "
            "host uses the active host profile controls for this affordance."
        ),
    )

    assert all(checks.values())


def test_weak_response_produces_baseline_needs_review(tmp_path, monkeypatch):
    packet, candidate = make_ready_packet(tmp_path)

    monkeypatch.setattr(
        affordance_baseline_runner,
        "call_openai_chat",
        lambda *args, **kwargs: "ok",
    )

    report = write_reports(
        packet,
        candidate,
        "http://example.invalid/v1",
        "test-model",
        tmp_path / "out",
        128,
        5,
    )

    assert report["result_verdict"] == "baseline_needs_review"
    assert report["aggregate_checks"]["all_model_calls_ok"] is True
    assert report["aggregate_checks"]["all_prompt_checks_passed"] is False


def test_failed_model_call_produces_baseline_fail(tmp_path, monkeypatch):
    packet, candidate = make_ready_packet(tmp_path)

    def fake_call(*args, **kwargs):
        raise urllib.error.URLError("endpoint unavailable")

    monkeypatch.setattr(affordance_baseline_runner, "call_openai_chat", fake_call)

    report = write_reports(
        packet,
        candidate,
        "http://example.invalid/v1",
        "test-model",
        tmp_path / "out",
        128,
        5,
    )

    assert report["result_verdict"] == "baseline_fail"
    assert report["aggregate_checks"]["all_model_calls_ok"] is False


def test_output_files_are_written(tmp_path, monkeypatch):
    packet, candidate = make_ready_packet(tmp_path)
    monkeypatch.setattr(
        affordance_baseline_runner,
        "call_openai_chat",
        lambda endpoint_url, model_id, system_prompt, user_prompt, max_tokens, timeout: good_response_for_prompt(
            user_prompt
        ),
    )
    out = tmp_path / "out"

    write_reports(packet, candidate, "http://example.invalid/v1", "test-model", out, 128, 5)

    assert sorted(path.name for path in out.iterdir()) == [
        "baseline_lane_result_report.json",
        "baseline_lane_result_report.md",
        "post_run_audit_report.md",
    ]


def test_endpoint_host_is_redacted(tmp_path, monkeypatch):
    packet, candidate = make_ready_packet(tmp_path)
    monkeypatch.setattr(
        affordance_baseline_runner,
        "call_openai_chat",
        lambda *args, **kwargs: "ok",
    )

    report = write_reports(
        packet,
        candidate,
        "http://127.0.0.1:1234/v1",
        "test-model",
        tmp_path / "out",
        128,
        5,
    )

    assert report["endpoint_host_redacted"] == "http://<redacted-host>"
    assert "127.0.0.1" not in report["endpoint_host_redacted"]


def test_promotion_verdict_is_always_held(tmp_path, monkeypatch):
    packet, candidate = make_ready_packet(tmp_path)
    monkeypatch.setattr(
        affordance_baseline_runner,
        "call_openai_chat",
        lambda *args, **kwargs: "ok",
    )

    report = write_reports(
        packet,
        candidate,
        "http://example.invalid/v1",
        "test-model",
        tmp_path / "out",
        128,
        5,
    )

    assert report["promotion_verdict"] == "hold_pending_explicit_experiment_approval"


def test_disallowed_actions_include_required_boundaries(tmp_path):
    packet, candidate = make_ready_packet(tmp_path)

    report = write_reports(
        packet,
        candidate,
        "http://example.invalid/v1",
        "test-model",
        tmp_path / "out",
        128,
        5,
    )

    packet_payload = load_json(packet)
    disallowed = set(packet_payload["disallowed_runner_actions"])
    assert "apply_larql_patch" in disallowed
    assert "train_lora_adapter" in disallowed
    assert "mutate_model_weights" in disallowed
    assert "write_durable_memory" in disallowed
    assert "run_comparison_lane" in disallowed
    assert "promote_candidate" in disallowed
    assert "modify_repo_files" in disallowed
    assert "commit_or_push" in disallowed
    assert report["disallowed_actions_preserved"] is True


def test_markdown_includes_boundary_language(tmp_path, monkeypatch):
    packet, candidate = make_ready_packet(tmp_path)
    monkeypatch.setattr(
        affordance_baseline_runner,
        "call_openai_chat",
        lambda endpoint_url, model_id, system_prompt, user_prompt, max_tokens, timeout: good_response_for_prompt(
            user_prompt
        ),
    )
    out = tmp_path / "out"

    write_reports(packet, candidate, "http://example.invalid/v1", "test-model", out, 128, 5)
    markdown = (out / "baseline_lane_result_report.md").read_text(encoding="utf-8")

    assert "baseline lane only" in markdown
    assert "no LARQL" in markdown
    assert "no LoRA" in markdown
    assert "no model mutation" in markdown
    assert "no durable memory" in markdown
    assert "no comparison lane" in markdown
    assert "no candidate promotion" in markdown
    assert "no repo modification" in markdown
    assert "no commit or push" in markdown
