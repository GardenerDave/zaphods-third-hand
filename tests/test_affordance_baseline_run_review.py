import json
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_baseline_run_review import write_reports


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_baseline_run_review.py"


def run_review(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def prompt_result(prompt_id: str, response_text: str, prompt_verdict: str = "needs_review"):
    return {
        "prompt_id": prompt_id,
        "coverage": prompt_id,
        "request_sent": True,
        "response_text": response_text,
        "model_call_ok": True,
        "checks": {},
        "prompt_verdict": prompt_verdict,
        "elapsed_seconds": 0.1,
    }


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
        "prompt_results": [
            prompt_result("already_passed", "ok", "pass"),
            prompt_result(
                "baseline_direct_cuda_on_navigator",
                "Avoid CUDA-only setup on RX580 because no_cuda applies to AMD/non-NVIDIA hardware.",
            ),
            prompt_result(
                "baseline_cross_host_boundary",
                "This is not generalizable to another host without matching evidence.",
            ),
            prompt_result(
                "baseline_reverify_before_action",
                "Reverify the active host before action; revalidation is required.",
            ),
            prompt_result(
                "baseline_no_durable_promotion",
                "This did not apply LARQL or LoRA and grants no durable memory promotion.",
            ),
            prompt_result(
                "baseline_split_workflow_active_host",
                "Candidate applies only if: active host is navigator_desktop and constraints (no_cuda) are met.",
            ),
        ],
    }
    payload.update(overrides)
    return payload


def write_run_report(tmp_path: Path, **overrides) -> Path:
    path = tmp_path / "baseline_lane_result_report.json"
    path.write_text(
        json.dumps(run_report_payload(**overrides), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def write_audit(tmp_path: Path, verdict: str = "audit_needs_review") -> Path:
    path = tmp_path / "post_run_audit_report.md"
    path.write_text(
        "\n".join(
            [
                "# Baseline Affordance Post-Run Audit",
                "",
                f"Final audit verdict: `{verdict}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def labels_by_prompt(review: dict):
    return {
        item["prompt_id"]: item["adjudication"]
        for item in review["prompt_adjudications"]
    }


def test_help_works():
    result = run_review("--help")

    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_missing_run_report_returns_invalid_input(tmp_path):
    audit = write_audit(tmp_path)

    review = write_reports(
        tmp_path / "missing.json",
        audit,
        tmp_path / "out",
        "missing run report",
    )

    assert review["review_verdict"] == "invalid_input"
    assert review["checks"]["run_report_exists"] is False


def test_missing_audit_returns_invalid_input(tmp_path):
    run_report = write_run_report(tmp_path)

    review = write_reports(
        run_report,
        tmp_path / "missing.md",
        tmp_path / "out",
        "missing audit",
    )

    assert review["review_verdict"] == "invalid_input"
    assert review["checks"]["post_run_audit_exists"] is False


def test_non_baseline_lane_returns_invalid_input(tmp_path):
    run_report = write_run_report(tmp_path, selected_lane="larql_affordance_patch_probe_only")
    audit = write_audit(tmp_path)

    review = write_reports(run_report, audit, tmp_path / "out", "wrong lane")

    assert review["review_verdict"] == "invalid_input"
    assert review["checks"]["selected_lane_baseline"] is False


def test_unverified_candidate_digest_returns_invalid_input(tmp_path):
    run_report = write_run_report(tmp_path, candidate_digest_verified=False)
    audit = write_audit(tmp_path)

    review = write_reports(run_report, audit, tmp_path / "out", "bad digest")

    assert review["review_verdict"] == "invalid_input"
    assert review["checks"]["candidate_digest_verified"] is False


def test_unverified_prompt_suite_digest_returns_invalid_input(tmp_path):
    run_report = write_run_report(tmp_path, prompt_suite_digest_verified=False)
    audit = write_audit(tmp_path)

    review = write_reports(run_report, audit, tmp_path / "out", "bad prompt suite digest")

    assert review["review_verdict"] == "invalid_input"
    assert review["checks"]["prompt_suite_digest_verified"] is False


def test_promotion_not_held_returns_invalid_input(tmp_path):
    run_report = write_run_report(tmp_path, promotion_verdict="promoted")
    audit = write_audit(tmp_path)

    review = write_reports(run_report, audit, tmp_path / "out", "bad promotion")

    assert review["review_verdict"] == "invalid_input"
    assert review["checks"]["promotion_held"] is False


def test_prompt_adjudication_labels_expected_run_shape(tmp_path):
    run_report = write_run_report(tmp_path)
    audit = write_audit(tmp_path)

    review = write_reports(run_report, audit, tmp_path / "out", "review baseline needs review")
    labels = labels_by_prompt(review)

    assert labels["already_passed"] == "pass"
    assert labels["baseline_direct_cuda_on_navigator"] == "scorer_false_negative"
    assert labels["baseline_cross_host_boundary"] == "scorer_false_negative"
    assert labels["baseline_reverify_before_action"] == "scorer_false_negative"
    assert labels["baseline_no_durable_promotion"] == "scorer_false_negative"
    assert labels["baseline_split_workflow_active_host"] == "scorer_false_negative"
    assert review["aggregate_review"]["pass_count"] == 1
    assert review["aggregate_review"]["scorer_false_negative_count"] == 5
    assert review["aggregate_review"]["model_weakness_count"] == 0
    assert review["aggregate_review"]["true_failure_count"] == 0
    assert review["aggregate_review"]["promotion_held"] is True


def test_recommendation_with_scorer_false_negative_is_scorer_repair(tmp_path):
    run_report = write_run_report(tmp_path)
    audit = write_audit(tmp_path)

    review = write_reports(
        run_report,
        audit,
        tmp_path / "out",
        "split host answer is a scorer false negative",
    )

    assert review["review_verdict"] == "baseline_review_requires_scorer_repair"
    assert review["recommended_next_step"] == "draft_scorer_repair"
    assert review["aggregate_review"]["scorer_false_negative_count"] == 5
    assert review["aggregate_review"]["model_weakness_count"] == 0


def test_promotion_verdict_is_always_held(tmp_path):
    run_report = write_run_report(tmp_path)
    audit = write_audit(tmp_path)

    review = write_reports(run_report, audit, tmp_path / "out", "held")

    assert review["promotion_verdict"] == "hold_pending_explicit_experiment_approval"


def test_markdown_includes_boundary_language(tmp_path):
    run_report = write_run_report(tmp_path)
    audit = write_audit(tmp_path)
    out = tmp_path / "out"

    write_reports(run_report, audit, out, "review only")
    markdown = (out / "baseline_run_review.md").read_text(encoding="utf-8")

    assert "This is review only." in markdown
    assert "The original run verdict remains preserved." in markdown
    assert "This review does not modify the original run report." in markdown
    assert "This review is not a LARQL patch." in markdown
    assert "This review is not LoRA training." in markdown
    assert "This review is not model mutation." in markdown
    assert "This review is not durable memory promotion." in markdown
    assert "This review is not comparison lane execution." in markdown
    assert "This review grants no candidate promotion." in markdown
    assert "Promotion remains held." in markdown
