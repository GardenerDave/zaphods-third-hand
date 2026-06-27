import json
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_baseline_repair_proposal import write_reports


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_baseline_repair_proposal.py"


def run_repair(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def run_report_payload(**overrides):
    payload = {
        "report_type": "affordance_baseline_lane_result.v0",
        "candidate_id": "larql_affordance_candidate_example",
        "source_failure_id": "navigator_cuda_failure",
        "selected_lane": "baseline_prompt_context_only",
        "result_verdict": "baseline_needs_review",
        "promotion_verdict": "hold_pending_explicit_experiment_approval",
        "candidate_digest_verified": True,
        "prompt_suite_digest_verified": True,
        "aggregate_checks": {
            "all_model_calls_ok": True,
            "all_prompt_checks_passed": False,
            "candidate_digest_verified": True,
            "prompt_suite_digest_verified": True,
            "selected_lane_baseline": True,
            "promotion_held": True,
            "no_repo_write_requested": True,
            "disallowed_actions_preserved": True,
        },
        "required_outputs_written": {
            "baseline_lane_result_report.json": True,
            "baseline_lane_result_report.md": True,
            "post_run_audit_report.md": True,
        },
    }
    payload.update(overrides)
    return payload


def prompt_adjudication(prompt_id: str, adjudication: str):
    return {
        "prompt_id": prompt_id,
        "coverage": prompt_id,
        "input_prompt_verdict": "needs_review" if adjudication != "pass" else "pass",
        "model_call_ok": True,
        "adjudication": adjudication,
    }


def review_payload(**overrides):
    payload = {
        "report_type": "affordance_baseline_run_review.v0",
        "candidate_id": "larql_affordance_candidate_example",
        "source_failure_id": "navigator_cuda_failure",
        "selected_lane": "baseline_prompt_context_only",
        "input_result_verdict": "baseline_needs_review",
        "input_review_verdict": "baseline_review_requires_prompt_repair",
        "review_status": "review_only",
        "review_verdict": "baseline_review_requires_prompt_repair",
        "promotion_verdict": "hold_pending_explicit_experiment_approval",
        "prompt_adjudications": [
            prompt_adjudication("already_passed_a", "pass"),
            prompt_adjudication("already_passed_b", "pass"),
            prompt_adjudication("baseline_direct_cuda_on_navigator", "scorer_false_negative"),
            prompt_adjudication("baseline_cross_host_boundary", "scorer_false_negative"),
            prompt_adjudication("baseline_reverify_before_action", "scorer_false_negative"),
            prompt_adjudication("baseline_no_durable_promotion", "scorer_false_negative"),
            prompt_adjudication("baseline_split_workflow_active_host", "model_weakness"),
        ],
        "aggregate_review": {
            "pass_count": 2,
            "scorer_false_negative_count": 4,
            "model_weakness_count": 1,
            "true_failure_count": 0,
            "not_reviewed_count": 0,
            "all_model_calls_ok": True,
            "digests_verified": True,
            "promotion_held": True,
            "boundaries_preserved": True,
        },
        "recommended_next_step": "draft_baseline_prompt_or_scorer_repair",
    }
    payload.update(overrides)
    return payload


def write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_run_report(tmp_path: Path, **overrides) -> Path:
    return write_json(tmp_path / "baseline_lane_result_report.json", run_report_payload(**overrides))


def write_review(tmp_path: Path, **overrides) -> Path:
    return write_json(tmp_path / "baseline_run_review.json", review_payload(**overrides))


def repair_by_prompt(proposal: dict):
    return {item["prompt_id"]: item for item in proposal["scorer_false_negative_repairs"]}


def test_help_works():
    result = run_repair("--help")

    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_missing_run_report_returns_invalid_input(tmp_path):
    review = write_review(tmp_path)

    proposal = write_reports(tmp_path / "missing.json", review, tmp_path / "out")

    assert proposal["proposal_verdict"] == "invalid_input"
    assert proposal["checks"]["run_report_exists"] is False


def test_missing_review_returns_invalid_input(tmp_path):
    run_report = write_run_report(tmp_path)

    proposal = write_reports(run_report, tmp_path / "missing.json", tmp_path / "out")

    assert proposal["proposal_verdict"] == "invalid_input"
    assert proposal["checks"]["run_review_exists"] is False


def test_non_baseline_lane_returns_invalid_input(tmp_path):
    run_report = write_run_report(tmp_path, selected_lane="larql_affordance_patch_probe_only")
    review = write_review(tmp_path)

    proposal = write_reports(run_report, review, tmp_path / "out")

    assert proposal["proposal_verdict"] == "invalid_input"
    assert proposal["checks"]["selected_lane_baseline"] is False


def test_promotion_not_held_in_run_report_returns_invalid_input(tmp_path):
    run_report = write_run_report(tmp_path, promotion_verdict="promoted")
    review = write_review(tmp_path)

    proposal = write_reports(run_report, review, tmp_path / "out")

    assert proposal["proposal_verdict"] == "invalid_input"
    assert proposal["checks"]["run_promotion_held"] is False


def test_promotion_not_held_in_review_returns_invalid_input(tmp_path):
    run_report = write_run_report(tmp_path)
    review = write_review(tmp_path, promotion_verdict="promoted")

    proposal = write_reports(run_report, review, tmp_path / "out")

    assert proposal["proposal_verdict"] == "invalid_input"
    assert proposal["checks"]["review_promotion_held"] is False


def test_review_requiring_prompt_repair_returns_ready(tmp_path):
    run_report = write_run_report(tmp_path)
    review = write_review(tmp_path)

    proposal = write_reports(run_report, review, tmp_path / "out")

    assert proposal["proposal_verdict"] == "ready_for_repair_decision"
    assert proposal["recommended_repair_scope"] == "baseline_prompt_suite_and_scorer_only"
    assert proposal["allowed_next_step"] == "decide_baseline_prompt_scorer_repair"


def test_review_requiring_scorer_repair_returns_ready(tmp_path):
    run_report = write_run_report(tmp_path)
    review = write_review(
        tmp_path,
        review_verdict="baseline_review_requires_scorer_repair",
        aggregate_review={
            "pass_count": 3,
            "scorer_false_negative_count": 4,
            "model_weakness_count": 0,
            "true_failure_count": 0,
            "not_reviewed_count": 0,
            "all_model_calls_ok": True,
            "digests_verified": True,
            "promotion_held": True,
            "boundaries_preserved": True,
        },
        prompt_adjudications=[
            prompt_adjudication("baseline_direct_cuda_on_navigator", "scorer_false_negative"),
            prompt_adjudication("baseline_cross_host_boundary", "scorer_false_negative"),
            prompt_adjudication("baseline_reverify_before_action", "scorer_false_negative"),
            prompt_adjudication("baseline_no_durable_promotion", "scorer_false_negative"),
        ],
    )

    proposal = write_reports(run_report, review, tmp_path / "out")

    assert proposal["proposal_verdict"] == "ready_for_repair_decision"


def test_review_with_true_failures_does_not_propose_scorer_relaxation_as_sufficient(tmp_path):
    run_report = write_run_report(tmp_path)
    review = write_review(
        tmp_path,
        aggregate_review={
            "pass_count": 1,
            "scorer_false_negative_count": 1,
            "model_weakness_count": 0,
            "true_failure_count": 1,
            "not_reviewed_count": 0,
            "all_model_calls_ok": True,
            "digests_verified": True,
            "promotion_held": True,
            "boundaries_preserved": True,
        },
    )

    proposal = write_reports(run_report, review, tmp_path / "out")

    assert proposal["proposal_verdict"] == "not_ready_missing_review"
    assert proposal["recommended_repair_scope"] != "baseline_prompt_suite_and_scorer_only"
    assert proposal["scorer_false_negative_repairs"] == []


def test_scorer_false_negative_repair_entries_are_generated(tmp_path):
    run_report = write_run_report(tmp_path)
    review = write_review(tmp_path)

    proposal = write_reports(run_report, review, tmp_path / "out")
    repairs = repair_by_prompt(proposal)

    assert "baseline_direct_cuda_on_navigator" in repairs
    assert "avoid CUDA-only setup" in repairs["baseline_direct_cuda_on_navigator"]["proposal"]
    assert "baseline_cross_host_boundary" in repairs
    assert "not generalizable to other profiles without matching evidence" in repairs[
        "baseline_cross_host_boundary"
    ]["proposal"]
    assert "baseline_reverify_before_action" in repairs
    assert "revalidation" in repairs["baseline_reverify_before_action"]["proposal"]
    assert "baseline_no_durable_promotion" in repairs
    assert "LARQL patch" in repairs["baseline_no_durable_promotion"]["proposal"]


def test_split_workflow_prompt_weakness_repair_is_generated(tmp_path):
    run_report = write_run_report(tmp_path)
    review = write_review(tmp_path)

    proposal = write_reports(run_report, review, tmp_path / "out")
    repairs = proposal["prompt_weakness_repairs"]

    assert len(repairs) == 1
    assert repairs[0]["prompt_id"] == "baseline_split_workflow_active_host"
    assert "local host" in repairs[0]["required_concepts"]
    assert "remote host" in repairs[0]["required_concepts"]
    assert "active execution host" in repairs[0]["required_concepts"]


def test_runner_code_repair_false_when_run_integrity_is_good(tmp_path):
    run_report = write_run_report(tmp_path)
    review = write_review(tmp_path)

    proposal = write_reports(run_report, review, tmp_path / "out")

    assert proposal["runner_code_repair_needed"] is False


def test_candidate_repair_false_when_true_failure_count_is_zero(tmp_path):
    run_report = write_run_report(tmp_path)
    review = write_review(tmp_path)

    proposal = write_reports(run_report, review, tmp_path / "out")

    assert proposal["candidate_repair_needed"] is False


def test_rerun_required_and_promotion_held(tmp_path):
    run_report = write_run_report(tmp_path)
    review = write_review(tmp_path)

    proposal = write_reports(run_report, review, tmp_path / "out")

    assert proposal["rerun_required_after_repair"] is True
    assert proposal["promotion_verdict"] == "hold_pending_explicit_experiment_approval"


def test_markdown_includes_boundary_language(tmp_path):
    run_report = write_run_report(tmp_path)
    review = write_review(tmp_path)
    out = tmp_path / "out"

    write_reports(run_report, review, out)
    markdown = (out / "baseline_repair_proposal.md").read_text(encoding="utf-8")

    assert "This is proposal only." in markdown
    assert "The original run verdict remains preserved." in markdown
    assert "The original review verdict remains preserved." in markdown
    assert "This proposal does not modify the original run report." in markdown
    assert "This proposal does not modify the original review report." in markdown
    assert "This proposal is not a LARQL patch." in markdown
    assert "This proposal is not LoRA training." in markdown
    assert "This proposal is not model mutation." in markdown
    assert "This proposal is not durable memory promotion." in markdown
    assert "This proposal is not comparison lane execution." in markdown
    assert "This proposal grants no candidate promotion." in markdown
    assert "Repair still requires a separate decision." in markdown
    assert "Rerun is required after repair." in markdown
