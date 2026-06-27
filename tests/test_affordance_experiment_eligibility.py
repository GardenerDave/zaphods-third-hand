import json
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_experiment_eligibility import write_reports


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_experiment_eligibility.py"


def run_eligibility(*args: str | Path) -> subprocess.CompletedProcess[str]:
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
        "source_digests": {
            "host_profile_sha256": "a" * 64,
            "failure_note_sha256": "b" * 64,
            "classifier_version": "larql_affordance_probe.v0",
        },
    }
    payload.update(overrides)
    return payload


def write_candidate(tmp_path: Path, **overrides) -> Path:
    path = tmp_path / "candidate.json"
    path.write_text(
        json.dumps(candidate_payload(**overrides), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def write_repeatability_report(tmp_path: Path, text: str | None = None) -> Path:
    path = tmp_path / "repeatability.md"
    path.write_text(
        text
        if text is not None
        else "\n".join(
            [
                "# Repeatability",
                "",
                "No LARQL patch, LoRA training, or durable model mutation was applied.",
                "- Promotion behavior: held for review",
                "- Clean 7/7 runs: 5 / 5",
                "- Total prompt passes: 35 / 35",
                "- Total prompt needs_review: 0 / 35",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def test_help_works():
    result = run_eligibility("--help")

    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_clean_repeatability_report_is_eligible(tmp_path):
    candidate = write_candidate(tmp_path)
    repeatability = write_repeatability_report(tmp_path)
    out = tmp_path / "out"

    result = run_eligibility(
        "--candidate",
        candidate,
        "--repeatability-report",
        repeatability,
        "--out",
        out,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert sorted(path.name for path in out.iterdir()) == [
        "eligibility_report.json",
        "eligibility_report.md",
    ]
    report = json.loads((out / "eligibility_report.json").read_text(encoding="utf-8"))
    assert report["report_type"] == "affordance_experiment_eligibility.v0"
    assert report["eligibility_verdict"] == "eligible_for_experiment_proposal"
    assert report["promotion_verdict"] == "hold_pending_explicit_experiment_approval"
    assert all(report["checks"].values())


def test_missing_repeatability_report_is_not_eligible(tmp_path):
    candidate = write_candidate(tmp_path)
    out = tmp_path / "out"

    report = write_reports(candidate, tmp_path / "missing.md", out)

    assert report["eligibility_verdict"] == "not_eligible_needs_more_evidence"
    assert report["checks"]["repeatability_report_exists"] is False
    assert report["promotion_verdict"] == "hold_pending_explicit_experiment_approval"


def test_partial_repeatability_report_is_not_eligible(tmp_path):
    candidate = write_candidate(tmp_path)
    repeatability = write_repeatability_report(
        tmp_path,
        "Clean 7/7 runs: 5 / 5\nTotal prompt passes: 35 / 35\n",
    )

    report = write_reports(candidate, repeatability, tmp_path / "out")

    assert report["eligibility_verdict"] == "not_eligible_needs_more_evidence"
    assert report["checks"]["repeatability_total_needs_review_0_of_35"] is False
    assert report["checks"]["repeatability_no_larql_lora_mutation"] is False


def test_missing_source_digests_is_not_eligible(tmp_path):
    candidate = write_candidate(tmp_path, source_digests={})
    repeatability = write_repeatability_report(tmp_path)

    report = write_reports(candidate, repeatability, tmp_path / "out")

    assert report["eligibility_verdict"] == "not_eligible_needs_more_evidence"
    assert report["checks"]["candidate_has_source_digests"] is False


def test_unsupported_repair_lane_is_not_eligible(tmp_path):
    candidate = write_candidate(tmp_path, repair_lane="review_only")
    repeatability = write_repeatability_report(tmp_path)

    report = write_reports(candidate, repeatability, tmp_path / "out")

    assert report["eligibility_verdict"] == "not_eligible_needs_more_evidence"
    assert report["checks"]["repair_lane_supported"] is False


def test_missing_candidate_is_invalid_input(tmp_path):
    repeatability = write_repeatability_report(tmp_path)

    report = write_reports(tmp_path / "missing.json", repeatability, tmp_path / "out")

    assert report["eligibility_verdict"] == "not_eligible_invalid_input"
    assert report["checks"]["candidate_exists"] is False
    assert report["promotion_verdict"] == "hold_pending_explicit_experiment_approval"


def test_markdown_report_includes_boundary_language(tmp_path):
    candidate = write_candidate(tmp_path)
    repeatability = write_repeatability_report(tmp_path)
    out = tmp_path / "out"

    write_reports(candidate, repeatability, out)
    markdown = (out / "eligibility_report.md").read_text(encoding="utf-8")

    assert "eligibility for an experiment proposal only" in markdown
    assert "It is not a LARQL patch." in markdown
    assert "It is not LoRA training." in markdown
    assert "It is not durable memory promotion." in markdown
    assert "Post-injection re-audition would be required" in markdown
