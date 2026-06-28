import json
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_baseline_execution_packet import write_reports


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_baseline_execution_packet.py"


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


def test_help_works():
    result = run_packet("--help")

    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_clean_inputs_return_ready_for_bounded_baseline_runner(tmp_path):
    candidate = write_candidate(tmp_path)
    approval = write_approval(tmp_path)
    plan = write_plan(tmp_path)
    out = tmp_path / "out"

    result = run_packet(
        "--candidate",
        candidate,
        "--approval",
        approval,
        "--plan",
        plan,
        "--out",
        out,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert sorted(path.name for path in out.iterdir()) == [
        "baseline_execution_packet.json",
        "baseline_execution_packet.md",
    ]
    packet = json.loads((out / "baseline_execution_packet.json").read_text(encoding="utf-8"))
    assert packet["report_type"] == "affordance_baseline_execution_packet.v0"
    assert packet["packet_type"] == "baseline_prompt_context_only"
    assert packet["packet_status"] == "packet_only"
    assert packet["packet_verdict"] == "ready_for_bounded_baseline_runner"
    assert packet["allowed_next_step"] == "run_bounded_baseline_prompt_context_packet"
    assert packet["promotion_verdict"] == "hold_pending_explicit_experiment_approval"
    assert all(packet["checks"].values())


def test_missing_candidate_returns_invalid_input(tmp_path):
    approval = write_approval(tmp_path)
    plan = write_plan(tmp_path)

    packet = write_reports(tmp_path / "missing.json", approval, plan, tmp_path / "out")

    assert packet["packet_verdict"] == "invalid_input"
    assert packet["checks"]["candidate_exists"] is False


def test_missing_approval_returns_invalid_input(tmp_path):
    candidate = write_candidate(tmp_path)
    plan = write_plan(tmp_path)

    packet = write_reports(candidate, tmp_path / "missing.json", plan, tmp_path / "out")

    assert packet["packet_verdict"] == "invalid_input"
    assert packet["checks"]["approval_exists"] is False


def test_missing_plan_returns_invalid_input(tmp_path):
    candidate = write_candidate(tmp_path)
    approval = write_approval(tmp_path)

    packet = write_reports(candidate, approval, tmp_path / "missing.json", tmp_path / "out")

    assert packet["packet_verdict"] == "invalid_input"
    assert packet["checks"]["plan_exists"] is False


def test_wrong_approval_verdict_returns_not_ready(tmp_path):
    candidate = write_candidate(tmp_path)
    approval = write_approval(tmp_path, approval_verdict="held_for_revision")
    plan = write_plan(tmp_path)

    packet = write_reports(candidate, approval, plan, tmp_path / "out")

    assert packet["packet_verdict"] == "not_ready_missing_approval"
    assert packet["checks"]["approval_verdict_baseline"] is False


def test_wrong_execution_verdict_returns_not_ready(tmp_path):
    candidate = write_candidate(tmp_path)
    approval = write_approval(tmp_path, execution_verdict="not_approved_for_execution")
    plan = write_plan(tmp_path)

    packet = write_reports(candidate, approval, plan, tmp_path / "out")

    assert packet["packet_verdict"] == "not_ready_missing_approval"
    assert packet["checks"]["approval_execution_verdict_baseline"] is False


def test_wrong_selected_lane_returns_not_ready(tmp_path):
    candidate = write_candidate(tmp_path)
    approval = write_approval(tmp_path, selected_lane="larql_affordance_patch_probe_only")
    plan = write_plan(tmp_path)

    packet = write_reports(candidate, approval, plan, tmp_path / "out")

    assert packet["packet_verdict"] == "not_ready_missing_approval"
    assert packet["checks"]["approval_selected_lane_baseline"] is False


def test_missing_source_digests_returns_not_ready(tmp_path):
    candidate = write_candidate(tmp_path, source_digests={})
    approval = write_approval(tmp_path)
    plan = write_plan(tmp_path)

    packet = write_reports(candidate, approval, plan, tmp_path / "out")

    assert packet["packet_verdict"] == "not_ready_missing_approval"
    assert packet["checks"]["candidate_has_source_digests"] is False


def test_plan_missing_baseline_lane_returns_not_ready(tmp_path):
    candidate = write_candidate(tmp_path)
    approval = write_approval(tmp_path)
    plan = write_plan(tmp_path, allowed_experiment_lanes=["larql_affordance_patch_probe_only"])

    packet = write_reports(candidate, approval, plan, tmp_path / "out")

    assert packet["packet_verdict"] == "not_ready_missing_approval"
    assert packet["checks"]["plan_allows_baseline_lane"] is False


def test_candidate_digest_is_stable_and_present(tmp_path):
    candidate = write_candidate(tmp_path)
    approval = write_approval(tmp_path)
    plan = write_plan(tmp_path)

    first = write_reports(candidate, approval, plan, tmp_path / "out1")
    second = write_reports(candidate, approval, plan, tmp_path / "out2")

    assert len(first["candidate_digest"]) == 64
    assert first["candidate_digest"] == second["candidate_digest"]


def test_prompt_suite_digest_is_stable_and_present(tmp_path):
    candidate = write_candidate(tmp_path)
    approval = write_approval(tmp_path)
    plan = write_plan(tmp_path)

    first = write_reports(candidate, approval, plan, tmp_path / "out1")
    second = write_reports(candidate, approval, plan, tmp_path / "out2")

    assert len(first["prompt_suite_digest"]) == 64
    assert first["prompt_suite_digest"] == second["prompt_suite_digest"]
    assert len(first["prompt_suite"]["prompts"]) >= 7


def test_split_workflow_prompt_names_required_host_roles(tmp_path):
    candidate = write_candidate(tmp_path)
    approval = write_approval(tmp_path)
    plan = write_plan(tmp_path)

    packet = write_reports(candidate, approval, plan, tmp_path / "out")
    prompts = {
        prompt["prompt_id"]: prompt["prompt"]
        for prompt in packet["prompt_suite"]["prompts"]
    }
    split_prompt = prompts["baseline_split_workflow_active_host"].lower()

    assert "answer using this exact line-separated template." in split_prompt
    assert "copy the labels exactly." in split_prompt
    assert "answer each label on its own line." in split_prompt
    assert "do not merge labels." in split_prompt
    assert "the active host profile controls whether the candidate applies." in split_prompt
    assert "the candidate applies only when the active execution host matches the candidate's host evidence/profile constraints." in split_prompt
    assert "local host:" in split_prompt
    assert "remote host:" in split_prompt
    assert "active execution host:" in split_prompt
    assert "control rule:" in split_prompt
    assert "candidate applies only if:" in split_prompt


def test_disallowed_actions_include_required_boundaries(tmp_path):
    candidate = write_candidate(tmp_path)
    approval = write_approval(tmp_path)
    plan = write_plan(tmp_path)

    packet = write_reports(candidate, approval, plan, tmp_path / "out")

    disallowed = set(packet["disallowed_runner_actions"])
    assert "apply_larql_patch" in disallowed
    assert "train_lora_adapter" in disallowed
    assert "mutate_model_weights" in disallowed
    assert "write_durable_memory" in disallowed
    assert "promote_candidate" in disallowed
    assert "commit_or_push" in disallowed


def test_markdown_includes_boundary_language(tmp_path):
    candidate = write_candidate(tmp_path)
    approval = write_approval(tmp_path)
    plan = write_plan(tmp_path)
    out = tmp_path / "out"

    write_reports(candidate, approval, plan, out)
    markdown = (out / "baseline_execution_packet.md").read_text(encoding="utf-8")

    assert "This is packet only." in markdown
    assert "This packet is not a LARQL patch." in markdown
    assert "This packet is not LoRA training." in markdown
    assert "This packet is not model mutation." in markdown
    assert "This packet is not durable memory promotion." in markdown
    assert "This packet is not comparison execution." in markdown
    assert "This packet grants no candidate promotion." in markdown
    assert "baseline prompt-context lane only" in markdown
    assert "Execution uses the existing candidate in prompt context." in markdown
    assert "The later runner must fail closed." in markdown
