import json
import re
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_dogfood_report import write_report
from local_harness.larql_affordance_probe import build_candidate, read_failure_note, read_json


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_dogfood_report.py"
PROFILE = ROOT / "examples/host_profiles/navigator_desktop.example.json"
NOTE = ROOT / "examples/failure_notes/cuda_on_rx580_failure.example.md"


def run_report(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def write_candidate(tmp_path: Path, overrides: dict | None = None) -> Path:
    profile = read_json(PROFILE)
    note = read_failure_note(NOTE)
    candidate = build_candidate(
        host_profile=profile,
        host_profile_path=PROFILE,
        failure_note_path=NOTE,
        failure_note_text=note,
    )
    if overrides:
        candidate.update(overrides)
    path = tmp_path / "candidate.json"
    path.write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def test_help_works():
    result = run_report("--help")

    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_sample_candidate_produces_exactly_two_files(tmp_path):
    candidate_path = write_candidate(tmp_path)
    out = tmp_path / "report"

    result = run_report("--candidate", candidate_path, "--out", out)

    assert result.returncode == 0, result.stdout + result.stderr
    assert sorted(path.name for path in out.iterdir()) == [
        "dogfood_report.json",
        "dogfood_report.md",
    ]


def test_json_report_is_parseable_and_verdicts_pass(tmp_path):
    candidate_path = write_candidate(tmp_path)
    out = tmp_path / "report"

    write_report(candidate_path, out)
    report = json.loads((out / "dogfood_report.json").read_text(encoding="utf-8"))

    assert report["report_type"] == "affordance_dogfood_report.v0"
    assert report["classification_verdict"] == "pass"
    assert report["specificity_verdict"] == "pass"
    assert report["split_host_safety_verdict"] == "pass"
    assert report["provenance_verdict"] == "pass"
    assert report["promotion_verdict"] == "hold_pending_probe"
    assert report["recommended_next_step"] == "probe_before_larql_or_lora_promotion"


def test_missing_candidate_file_fails_clearly(tmp_path):
    result = run_report("--candidate", tmp_path / "missing.json", "--out", tmp_path / "out")

    assert result.returncode == 1
    assert "missing candidate file" in result.stdout


def test_output_path_traversal_is_refused(tmp_path):
    candidate_path = write_candidate(tmp_path)
    result = run_report("--candidate", candidate_path, "--out", tmp_path / ".." / "escape")

    assert result.returncode == 1
    assert "must not contain '..'" in result.stdout


def test_missing_required_candidate_fields_fail_clearly(tmp_path):
    candidate_path = write_candidate(tmp_path)
    payload = json.loads(candidate_path.read_text(encoding="utf-8"))
    del payload["source_digests"]
    candidate_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = run_report("--candidate", candidate_path, "--out", tmp_path / "out")

    assert result.returncode == 1
    assert "missing required fields" in result.stdout
    assert "source_digests" in result.stdout


def test_no_positive_accepted_or_promotion_wording_is_emitted(tmp_path):
    candidate_path = write_candidate(tmp_path)
    out = tmp_path / "report"
    write_report(candidate_path, out)

    combined = (
        (out / "dogfood_report.json").read_text(encoding="utf-8")
        + "\n"
        + (out / "dogfood_report.md").read_text(encoding="utf-8")
    ).lower()

    assert "accepted_for_training_candidate" not in combined
    assert "accepted_for_larql_patch_candidate" not in combined
    assert "promotion_verdict" in combined
    assert "hold_pending_probe" in combined
    assert re.search(r"not accepted|unpromoted|promotion is held", combined)
