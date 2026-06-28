import json
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_baseline_repair_decision import write_reports


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_baseline_repair_decision.py"


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
        "report_type": "affordance_baseline_repair_proposal.v0",
        "candidate_id": "larql_affordance_candidate_example",
        "source_failure_id": "navigator_cuda_failure",
        "selected_lane": "baseline_prompt_context_only",
        "input_result_verdict": "baseline_needs_review",
        "input_review_verdict": "baseline_review_requires_prompt_repair",
        "promotion_verdict": "hold_pending_explicit_experiment_approval",
        "proposal_status": "proposal_only",
        "proposal_verdict": "ready_for_repair_decision",
        "recommended_repair_scope": "baseline_prompt_suite_and_scorer_only",
        "runner_code_repair_needed": False,
        "candidate_repair_needed": False,
        "rerun_required_after_repair": True,
        "allowed_next_step": "decide_baseline_prompt_scorer_repair",
    }
    payload.update(overrides)
    return payload


def write_proposal(tmp_path: Path, **overrides) -> Path:
    path = tmp_path / "baseline_repair_proposal.json"
    path.write_text(
        json.dumps(proposal_payload(**overrides), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def test_help_works():
    result = run_decision("--help")

    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_missing_proposal_returns_invalid_input(tmp_path):
    decision = write_reports(
        tmp_path / "missing.json",
        "accept_prompt_scorer_repair_for_packet_drafting",
        "missing input",
        tmp_path / "out",
    )

    assert decision["decision_verdict"] == "invalid_input"
    assert decision["checks"]["repair_proposal_exists"] is False


def test_invalid_proposal_json_returns_invalid_input(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not json\n", encoding="utf-8")

    decision = write_reports(
        path,
        "accept_prompt_scorer_repair_for_packet_drafting",
        "bad json",
        tmp_path / "out",
    )

    assert decision["decision_verdict"] == "invalid_input"
    assert decision["checks"]["repair_proposal_parses"] is False


def test_non_baseline_lane_returns_invalid_input(tmp_path):
    proposal = write_proposal(tmp_path, selected_lane="larql_affordance_patch_probe_only")

    decision = write_reports(
        proposal,
        "accept_prompt_scorer_repair_for_packet_drafting",
        "wrong lane",
        tmp_path / "out",
    )

    assert decision["decision_verdict"] == "invalid_input"
    assert decision["checks"]["selected_lane_baseline"] is False


def test_promotion_not_held_returns_invalid_input(tmp_path):
    proposal = write_proposal(tmp_path, promotion_verdict="promoted")

    decision = write_reports(
        proposal,
        "accept_prompt_scorer_repair_for_packet_drafting",
        "bad promotion",
        tmp_path / "out",
    )

    assert decision["decision_verdict"] == "invalid_input"
    assert decision["checks"]["promotion_held"] is False


def test_proposal_not_ready_cannot_be_accepted(tmp_path):
    proposal = write_proposal(tmp_path, proposal_verdict="not_ready_missing_review")

    decision = write_reports(
        proposal,
        "accept_prompt_scorer_repair_for_packet_drafting",
        "not ready",
        tmp_path / "out",
    )

    assert decision["decision_verdict"] == "invalid_input"
    assert decision["checks"]["proposal_verdict_ready"] is False


def test_wrong_recommended_scope_cannot_be_accepted(tmp_path):
    proposal = write_proposal(tmp_path, recommended_repair_scope="candidate_repair")

    decision = write_reports(
        proposal,
        "accept_prompt_scorer_repair_for_packet_drafting",
        "wrong scope",
        tmp_path / "out",
    )

    assert decision["decision_verdict"] == "invalid_input"
    assert decision["checks"]["recommended_repair_scope_ok"] is False


def test_runner_code_repair_needed_prevents_accept(tmp_path):
    proposal = write_proposal(tmp_path, runner_code_repair_needed=True)

    decision = write_reports(
        proposal,
        "accept_prompt_scorer_repair_for_packet_drafting",
        "runner repair needed",
        tmp_path / "out",
    )

    assert decision["decision_verdict"] == "invalid_input"
    assert decision["checks"]["runner_code_repair_not_needed"] is False


def test_candidate_repair_needed_prevents_accept(tmp_path):
    proposal = write_proposal(tmp_path, candidate_repair_needed=True)

    decision = write_reports(
        proposal,
        "accept_prompt_scorer_repair_for_packet_drafting",
        "candidate repair needed",
        tmp_path / "out",
    )

    assert decision["decision_verdict"] == "invalid_input"
    assert decision["checks"]["candidate_repair_not_needed"] is False


def test_rerun_required_false_prevents_accept(tmp_path):
    proposal = write_proposal(tmp_path, rerun_required_after_repair=False)

    decision = write_reports(
        proposal,
        "accept_prompt_scorer_repair_for_packet_drafting",
        "rerun missing",
        tmp_path / "out",
    )

    assert decision["decision_verdict"] == "invalid_input"
    assert decision["checks"]["rerun_required_after_repair"] is False


def test_accept_decision_with_good_proposal_returns_accepted(tmp_path):
    proposal = write_proposal(tmp_path)

    decision = write_reports(
        proposal,
        "accept_prompt_scorer_repair_for_packet_drafting",
        "Accept for packet drafting only.",
        tmp_path / "out",
    )

    assert decision["decision_verdict"] == "accepted_for_repair_packet_drafting_only"
    assert decision["accepted_repair_scope"] == "baseline_prompt_suite_and_scorer_only"
    assert decision["allowed_next_step"] == "draft_baseline_prompt_scorer_repair_packet"


def test_reject_decision_returns_rejected(tmp_path):
    proposal = write_proposal(tmp_path)

    decision = write_reports(
        proposal,
        "reject_repair_proposal",
        "Reject this proposal.",
        tmp_path / "out",
    )

    assert decision["decision_verdict"] == "rejected_repair_proposal"
    assert decision["allowed_next_step"] == "preserve_rejection_or_draft_new_proposal"


def test_hold_decision_returns_held(tmp_path):
    proposal = write_proposal(tmp_path, proposal_verdict="not_ready_missing_review")

    decision = write_reports(
        proposal,
        "hold_for_more_review",
        "Hold for more review.",
        tmp_path / "out",
    )

    assert decision["decision_verdict"] == "held_for_more_review"
    assert decision["allowed_next_step"] == "collect_more_review_before_repair_decision"


def test_authorization_flags_and_promotion_are_held(tmp_path):
    proposal = write_proposal(tmp_path)

    decision = write_reports(
        proposal,
        "accept_prompt_scorer_repair_for_packet_drafting",
        "Accept for packet drafting only.",
        tmp_path / "out",
    )

    assert decision["runner_code_repair_authorized"] is False
    assert decision["candidate_repair_authorized"] is False
    assert decision["promotion_verdict"] == "hold_pending_explicit_experiment_approval"


def test_markdown_includes_boundary_language(tmp_path):
    proposal = write_proposal(tmp_path)
    out = tmp_path / "out"

    write_reports(
        proposal,
        "accept_prompt_scorer_repair_for_packet_drafting",
        "Accept for packet drafting only.",
        out,
    )
    markdown = (out / "baseline_repair_decision.md").read_text(encoding="utf-8")

    assert "This is decision only." in markdown
    assert "The original run verdict remains preserved." in markdown
    assert "The original review verdict remains preserved." in markdown
    assert "The original proposal verdict remains preserved." in markdown
    assert "No repair is applied by this record." in markdown
    assert "This decision is not a LARQL patch." in markdown
    assert "This decision is not LoRA training." in markdown
    assert "This decision is not model mutation." in markdown
    assert "This decision is not durable memory promotion." in markdown
    assert "This decision is not comparison lane execution." in markdown
    assert "This decision grants no candidate promotion." in markdown
    assert "Repair packet is still required before any code, prompt, or scorer change." in markdown
    assert "Rerun is required after any accepted repair." in markdown
