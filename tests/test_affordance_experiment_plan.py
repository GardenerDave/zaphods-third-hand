import json
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_experiment_plan import write_reports


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_experiment_plan.py"


def run_plan(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def proposal_payload(**overrides):
    payload = {
        "report_type": "affordance_experiment_proposal.v0",
        "candidate_id": "larql_affordance_candidate_example",
        "source_failure_id": "navigator_cuda_failure",
        "repair_lane": "larql_plus_lora_candidate",
        "recommended_experiment_type": "larql_plus_lora_comparison",
        "proposal_verdict": "ready_for_operator_review",
        "promotion_verdict": "hold_pending_explicit_experiment_approval",
    }
    payload.update(overrides)
    return payload


def decision_payload(**overrides):
    payload = {
        "report_type": "affordance_experiment_decision.v0",
        "candidate_id": "larql_affordance_candidate_example",
        "source_failure_id": "navigator_cuda_failure",
        "repair_lane": "larql_plus_lora_candidate",
        "recommended_experiment_type": "larql_plus_lora_comparison",
        "proposal_verdict": "ready_for_operator_review",
        "decision_verdict": "accepted_for_plan_drafting_only",
        "promotion_verdict": "hold_pending_explicit_experiment_approval",
        "allowed_next_step": "draft_bounded_affordance_experiment_plan",
    }
    payload.update(overrides)
    return payload


def write_proposal(tmp_path: Path, **overrides) -> Path:
    path = tmp_path / "experiment_proposal.json"
    path.write_text(
        json.dumps(proposal_payload(**overrides), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def write_decision(tmp_path: Path, **overrides) -> Path:
    path = tmp_path / "experiment_decision.json"
    path.write_text(
        json.dumps(decision_payload(**overrides), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def test_help_works():
    result = run_plan("--help")

    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_ready_proposal_and_accepted_decision_returns_ready_for_execution_review(tmp_path):
    proposal = write_proposal(tmp_path)
    decision = write_decision(tmp_path)
    out = tmp_path / "out"

    result = run_plan("--proposal", proposal, "--decision", decision, "--out", out)

    assert result.returncode == 0, result.stdout + result.stderr
    assert sorted(path.name for path in out.iterdir()) == [
        "experiment_plan.json",
        "experiment_plan.md",
    ]
    plan = json.loads((out / "experiment_plan.json").read_text(encoding="utf-8"))
    assert plan["report_type"] == "affordance_experiment_plan.v0"
    assert plan["experiment_status"] == "plan_only"
    assert plan["plan_verdict"] == "ready_for_execution_approval_review"
    assert plan["execution_verdict"] == "not_approved_for_execution"
    assert plan["promotion_verdict"] == "hold_pending_explicit_experiment_approval"
    assert plan["selected_plan_lane"] == "larql_plus_lora_comparison"
    assert all(plan["checks"].values())


def test_missing_proposal_returns_invalid_input(tmp_path):
    decision = write_decision(tmp_path)

    plan = write_reports(tmp_path / "missing.json", decision, tmp_path / "out")

    assert plan["plan_verdict"] == "invalid_input"
    assert plan["checks"]["proposal_exists"] is False
    assert plan["execution_verdict"] == "not_approved_for_execution"
    assert plan["promotion_verdict"] == "hold_pending_explicit_experiment_approval"


def test_missing_decision_returns_invalid_input(tmp_path):
    proposal = write_proposal(tmp_path)

    plan = write_reports(proposal, tmp_path / "missing.json", tmp_path / "out")

    assert plan["plan_verdict"] == "invalid_input"
    assert plan["checks"]["decision_exists"] is False


def test_non_ready_proposal_returns_not_ready(tmp_path):
    proposal = write_proposal(tmp_path, proposal_verdict="not_ready_missing_eligibility")
    decision = write_decision(tmp_path)

    plan = write_reports(proposal, decision, tmp_path / "out")

    assert plan["plan_verdict"] == "not_ready_missing_decision"
    assert plan["checks"]["proposal_verdict_ready"] is False


def test_non_accepted_decision_returns_not_ready(tmp_path):
    proposal = write_proposal(tmp_path)
    decision = write_decision(tmp_path, decision_verdict="held_for_revision")

    plan = write_reports(proposal, decision, tmp_path / "out")

    assert plan["plan_verdict"] == "not_ready_missing_decision"
    assert plan["checks"]["decision_verdict_accepted"] is False


def test_wrong_allowed_next_step_returns_not_ready(tmp_path):
    proposal = write_proposal(tmp_path)
    decision = write_decision(tmp_path, allowed_next_step="revise_experiment_proposal")

    plan = write_reports(proposal, decision, tmp_path / "out")

    assert plan["plan_verdict"] == "not_ready_missing_decision"
    assert plan["checks"]["decision_allowed_next_step_ok"] is False


def test_larql_plus_lora_comparison_includes_baseline_larql_and_lora_lanes(tmp_path):
    proposal = write_proposal(tmp_path, recommended_experiment_type="larql_plus_lora_comparison")
    decision = write_decision(tmp_path)

    plan = write_reports(proposal, decision, tmp_path / "out")

    assert "baseline_prompt_context_only" in plan["allowed_experiment_lanes"]
    assert "larql_affordance_patch_probe_only" in plan["allowed_experiment_lanes"]
    assert "lora_failure_curriculum_candidate_only" in plan["allowed_experiment_lanes"]


def test_markdown_includes_boundary_language(tmp_path):
    proposal = write_proposal(tmp_path)
    decision = write_decision(tmp_path)
    out = tmp_path / "out"

    write_reports(proposal, decision, out)
    markdown = (out / "experiment_plan.md").read_text(encoding="utf-8")

    assert "This plan is not a LARQL patch." in markdown
    assert "This plan is not LoRA training." in markdown
    assert "This plan is not model mutation." in markdown
    assert "This plan is not durable memory promotion." in markdown
    assert "This plan is not experiment execution." in markdown
    assert "This plan grants no candidate promotion." in markdown
    assert "requires separate execution approval" in markdown
    assert "Post-experiment re-audition is required" in markdown
