import json
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_experiment_execution_approval import write_reports


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_experiment_execution_approval.py"


def run_approval(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def plan_payload(**overrides):
    payload = {
        "report_type": "affordance_experiment_plan.v0",
        "candidate_id": "larql_affordance_candidate_example",
        "source_failure_id": "navigator_cuda_failure",
        "repair_lane": "larql_plus_lora_candidate",
        "recommended_experiment_type": "larql_plus_lora_comparison",
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


def write_plan(tmp_path: Path, **overrides) -> Path:
    path = tmp_path / "experiment_plan.json"
    path.write_text(
        json.dumps(plan_payload(**overrides), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def test_help_works():
    result = run_approval("--help")

    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_ready_plan_baseline_approved_returns_baseline_execution_only(tmp_path):
    plan = write_plan(tmp_path)
    out = tmp_path / "out"

    result = run_approval(
        "--plan",
        plan,
        "--lane",
        "baseline_prompt_context_only",
        "--approval-decision",
        "approved_for_bounded_lane_execution",
        "--operator-note",
        "Approve baseline prompt-context lane only.",
        "--out",
        out,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert sorted(path.name for path in out.iterdir()) == [
        "execution_approval.json",
        "execution_approval.md",
    ]
    approval = json.loads((out / "execution_approval.json").read_text(encoding="utf-8"))
    assert approval["report_type"] == "affordance_experiment_execution_approval.v0"
    assert approval["experiment_status"] == "execution_approval_only"
    assert approval["approval_verdict"] == "approved_for_baseline_lane_only"
    assert (
        approval["execution_verdict"]
        == "approved_for_baseline_prompt_context_execution_only"
    )
    assert approval["promotion_verdict"] == "hold_pending_explicit_experiment_approval"
    assert approval["allowed_next_step"] == "draft_baseline_prompt_context_execution_packet"
    assert "run_bounded_baseline_probe_prompts" in approval["allowed_actions"]


def test_ready_plan_held_decision_returns_held_for_revision(tmp_path):
    plan = write_plan(tmp_path)

    approval = write_reports(
        plan,
        "baseline_prompt_context_only",
        "held_for_revision",
        "Hold for revision.",
        tmp_path / "out",
    )

    assert approval["approval_verdict"] == "held_for_revision"
    assert approval["execution_verdict"] == "not_approved_for_execution"
    assert approval["promotion_verdict"] == "hold_pending_explicit_experiment_approval"


def test_ready_plan_rejected_decision_returns_rejected(tmp_path):
    plan = write_plan(tmp_path)

    approval = write_reports(
        plan,
        "baseline_prompt_context_only",
        "rejected",
        "Reject lane execution.",
        tmp_path / "out",
    )

    assert approval["approval_verdict"] == "rejected"
    assert approval["execution_verdict"] == "not_approved_for_execution"


def test_missing_plan_returns_invalid_input(tmp_path):
    approval = write_reports(
        tmp_path / "missing.json",
        "baseline_prompt_context_only",
        "approved_for_bounded_lane_execution",
        "Cannot approve missing input.",
        tmp_path / "out",
    )

    assert approval["approval_verdict"] == "invalid_input"
    assert approval["checks"]["plan_exists"] is False
    assert approval["execution_verdict"] == "not_approved_for_execution"
    assert approval["promotion_verdict"] == "hold_pending_explicit_experiment_approval"


def test_non_ready_plan_cannot_be_approved(tmp_path):
    plan = write_plan(tmp_path, plan_verdict="not_ready_missing_decision")

    approval = write_reports(
        plan,
        "baseline_prompt_context_only",
        "approved_for_bounded_lane_execution",
        "Attempted approval should fail closed.",
        tmp_path / "out",
    )

    assert approval["approval_verdict"] == "invalid_input"
    assert approval["checks"]["plan_verdict_ready"] is False
    assert approval["execution_verdict"] == "not_approved_for_execution"


def test_lane_not_in_plan_cannot_be_approved(tmp_path):
    plan = write_plan(tmp_path, allowed_experiment_lanes=["larql_affordance_patch_probe_only"])

    approval = write_reports(
        plan,
        "baseline_prompt_context_only",
        "approved_for_bounded_lane_execution",
        "Baseline lane is missing from plan.",
        tmp_path / "out",
    )

    assert approval["approval_verdict"] == "invalid_input"
    assert approval["checks"]["lane_allowed_by_plan"] is False
    assert approval["execution_verdict"] == "not_approved_for_execution"


def test_larql_lane_requires_separate_approval_support(tmp_path):
    plan = write_plan(tmp_path)

    approval = write_reports(
        plan,
        "larql_affordance_patch_probe_only",
        "approved_for_bounded_lane_execution",
        "Attempt LARQL lane approval.",
        tmp_path / "out",
    )

    assert approval["approval_verdict"] == "unsupported_lane_requires_separate_approval"
    assert approval["execution_verdict"] == "not_approved_for_execution"


def test_lora_lane_requires_separate_approval_support(tmp_path):
    plan = write_plan(tmp_path)

    approval = write_reports(
        plan,
        "lora_failure_curriculum_candidate_only",
        "approved_for_bounded_lane_execution",
        "Attempt LoRA lane approval.",
        tmp_path / "out",
    )

    assert approval["approval_verdict"] == "unsupported_lane_requires_separate_approval"
    assert approval["execution_verdict"] == "not_approved_for_execution"


def test_markdown_includes_boundary_language(tmp_path):
    plan = write_plan(tmp_path)
    out = tmp_path / "out"

    write_reports(
        plan,
        "baseline_prompt_context_only",
        "approved_for_bounded_lane_execution",
        "Approve baseline prompt-context lane only.",
        out,
    )
    markdown = (out / "execution_approval.md").read_text(encoding="utf-8")

    assert "This approval record is not a LARQL patch." in markdown
    assert "This approval record is not LoRA training." in markdown
    assert "This approval record is not model mutation." in markdown
    assert "This approval record is not durable memory promotion." in markdown
    assert "This approval record is not comparison execution." in markdown
    assert "This approval record grants no candidate promotion." in markdown
    assert "baseline lane only" in markdown
