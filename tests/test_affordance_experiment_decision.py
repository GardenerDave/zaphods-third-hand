import json
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_experiment_decision import write_reports


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_experiment_decision.py"


def run_decision(*args: str | Path) -> subprocess.CompletedProcess[str]:
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


def write_proposal(tmp_path: Path, **overrides) -> Path:
    path = tmp_path / "experiment_proposal.json"
    path.write_text(
        json.dumps(proposal_payload(**overrides), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def test_help_works():
    result = run_decision("--help")

    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_ready_proposal_approved_returns_plan_drafting_only(tmp_path):
    proposal = write_proposal(tmp_path)
    out = tmp_path / "out"

    result = run_decision(
        "--proposal",
        proposal,
        "--decision",
        "approved_to_draft_experiment_plan",
        "--operator-note",
        "Approve drafting a bounded experiment plan only.",
        "--out",
        out,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert sorted(path.name for path in out.iterdir()) == [
        "experiment_decision.json",
        "experiment_decision.md",
    ]
    decision = json.loads((out / "experiment_decision.json").read_text(encoding="utf-8"))
    assert decision["report_type"] == "affordance_experiment_decision.v0"
    assert decision["experiment_status"] == "decision_only"
    assert decision["decision_verdict"] == "accepted_for_plan_drafting_only"
    assert decision["allowed_next_step"] == "draft_bounded_affordance_experiment_plan"
    assert decision["promotion_verdict"] == "hold_pending_explicit_experiment_approval"


def test_ready_proposal_held_returns_held_for_revision(tmp_path):
    proposal = write_proposal(tmp_path)

    decision = write_reports(
        proposal,
        "held_for_revision",
        "Revise boundaries before plan drafting.",
        tmp_path / "out",
    )

    assert decision["decision_verdict"] == "held_for_revision"
    assert decision["allowed_next_step"] == "revise_experiment_proposal_before_plan_drafting"
    assert decision["promotion_verdict"] == "hold_pending_explicit_experiment_approval"


def test_ready_proposal_rejected_returns_rejected(tmp_path):
    proposal = write_proposal(tmp_path)

    decision = write_reports(
        proposal,
        "rejected",
        "Do not pursue this experiment.",
        tmp_path / "out",
    )

    assert decision["decision_verdict"] == "rejected"
    assert decision["allowed_next_step"] == "no_experiment_action"
    assert decision["promotion_verdict"] == "hold_pending_explicit_experiment_approval"


def test_missing_proposal_returns_invalid_input(tmp_path):
    decision = write_reports(
        tmp_path / "missing.json",
        "approved_to_draft_experiment_plan",
        "Cannot approve missing input.",
        tmp_path / "out",
    )

    assert decision["decision_verdict"] == "invalid_input"
    assert decision["checks"]["proposal_exists"] is False
    assert decision["promotion_verdict"] == "hold_pending_explicit_experiment_approval"


def test_non_ready_proposal_cannot_be_accepted(tmp_path):
    proposal = write_proposal(tmp_path, proposal_verdict="not_ready_missing_eligibility")

    decision = write_reports(
        proposal,
        "approved_to_draft_experiment_plan",
        "Attempted approval should fail closed.",
        tmp_path / "out",
    )

    assert decision["decision_verdict"] == "invalid_input"
    assert decision["checks"]["proposal_verdict_ready"] is False
    assert decision["allowed_next_step"] == "repair_or_replace_proposal_decision_inputs"


def test_unsupported_decision_returns_cli_error(tmp_path):
    proposal = write_proposal(tmp_path)

    result = run_decision(
        "--proposal",
        proposal,
        "--decision",
        "execute_experiment_now",
        "--operator-note",
        "bad decision",
        "--out",
        tmp_path / "out",
    )

    assert result.returncode != 0
    assert "invalid choice" in result.stderr


def test_markdown_includes_boundary_language(tmp_path):
    proposal = write_proposal(tmp_path)
    out = tmp_path / "out"

    write_reports(
        proposal,
        "approved_to_draft_experiment_plan",
        "Approve drafting a bounded experiment plan only.",
        out,
    )
    markdown = (out / "experiment_decision.md").read_text(encoding="utf-8")

    assert "This decision record is not a LARQL patch." in markdown
    assert "This decision record is not LoRA training." in markdown
    assert "This decision record is not model mutation." in markdown
    assert "This decision record is not durable memory promotion." in markdown
    assert "This decision record is not experiment execution." in markdown
    assert "This decision record grants no candidate promotion." in markdown
    assert "Execution still requires a separate explicit approval." in markdown
