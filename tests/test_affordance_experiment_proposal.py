import json
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_experiment_proposal import write_reports


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_experiment_proposal.py"


def run_proposal(*args: str | Path) -> subprocess.CompletedProcess[str]:
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


def write_eligibility(tmp_path: Path, **overrides) -> Path:
    payload = {
        "eligibility_verdict": "eligible_for_experiment_proposal",
        "promotion_verdict": "hold_pending_explicit_experiment_approval",
    }
    payload.update(overrides)
    path = tmp_path / "eligibility_report.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_repeatability(tmp_path: Path, text: str | None = None) -> Path:
    path = tmp_path / "repeatability.md"
    path.write_text(
        text
        if text is not None
        else "\n".join(
            [
                "Total prompt passes: 35 / 35",
                "No LARQL patch, LoRA training, or durable model mutation was applied",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def test_help_works():
    result = run_proposal("--help")

    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_clean_inputs_return_ready_for_operator_review(tmp_path):
    candidate = write_candidate(tmp_path)
    eligibility = write_eligibility(tmp_path)
    repeatability = write_repeatability(tmp_path)
    out = tmp_path / "out"

    result = run_proposal(
        "--candidate",
        candidate,
        "--eligibility-report",
        eligibility,
        "--repeatability-report",
        repeatability,
        "--out",
        out,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert sorted(path.name for path in out.iterdir()) == [
        "experiment_proposal.json",
        "experiment_proposal.md",
    ]
    proposal = json.loads((out / "experiment_proposal.json").read_text(encoding="utf-8"))
    assert proposal["report_type"] == "affordance_experiment_proposal.v0"
    assert proposal["proposal_verdict"] == "ready_for_operator_review"
    assert proposal["experiment_status"] == "proposal_only"
    assert proposal["promotion_verdict"] == "hold_pending_explicit_experiment_approval"
    assert all(proposal["checks"].values())


def test_missing_eligibility_report_returns_not_ready(tmp_path):
    candidate = write_candidate(tmp_path)
    repeatability = write_repeatability(tmp_path)

    proposal = write_reports(candidate, tmp_path / "missing.json", repeatability, tmp_path / "out")

    assert proposal["proposal_verdict"] == "not_ready_invalid_input"
    assert proposal["promotion_verdict"] == "hold_pending_explicit_experiment_approval"
    assert proposal["checks"]["eligibility_report_exists"] is False


def test_non_eligible_report_returns_not_ready(tmp_path):
    candidate = write_candidate(tmp_path)
    eligibility = write_eligibility(tmp_path, eligibility_verdict="not_eligible_needs_more_evidence")
    repeatability = write_repeatability(tmp_path)

    proposal = write_reports(candidate, eligibility, repeatability, tmp_path / "out")

    assert proposal["proposal_verdict"] == "not_ready_missing_eligibility"
    assert proposal["checks"]["eligibility_verdict_is_eligible"] is False


def test_missing_source_digests_returns_not_ready(tmp_path):
    candidate = write_candidate(tmp_path, source_digests={})
    eligibility = write_eligibility(tmp_path)
    repeatability = write_repeatability(tmp_path)

    proposal = write_reports(candidate, eligibility, repeatability, tmp_path / "out")

    assert proposal["proposal_verdict"] == "not_ready_missing_eligibility"
    assert proposal["checks"]["candidate_has_source_digests"] is False


def test_unsupported_repair_lane_returns_not_ready(tmp_path):
    candidate = write_candidate(tmp_path, repair_lane="review_only")
    eligibility = write_eligibility(tmp_path)
    repeatability = write_repeatability(tmp_path)

    proposal = write_reports(candidate, eligibility, repeatability, tmp_path / "out")

    assert proposal["proposal_verdict"] == "not_ready_missing_eligibility"
    assert proposal["checks"]["repair_lane_supported"] is False


def test_larql_plus_lora_candidate_recommends_comparison(tmp_path):
    candidate = write_candidate(tmp_path, repair_lane="larql_plus_lora_candidate")
    eligibility = write_eligibility(tmp_path)
    repeatability = write_repeatability(tmp_path)

    proposal = write_reports(candidate, eligibility, repeatability, tmp_path / "out")

    assert proposal["recommended_experiment_type"] == "larql_plus_lora_comparison"
    assert "larql_plus_lora_comparison" in proposal["experiment_type_options"]


def test_markdown_includes_boundary_language(tmp_path):
    candidate = write_candidate(tmp_path)
    eligibility = write_eligibility(tmp_path)
    repeatability = write_repeatability(tmp_path)
    out = tmp_path / "out"

    write_reports(candidate, eligibility, repeatability, out)
    markdown = (out / "experiment_proposal.md").read_text(encoding="utf-8")

    assert "This proposal is not a LARQL patch." in markdown
    assert "This proposal is not LoRA training." in markdown
    assert "This proposal is not durable memory promotion." in markdown
    assert "This proposal is not model mutation." in markdown
    assert "requires explicit approval" in markdown
    assert "post-experiment re-audition" in markdown
