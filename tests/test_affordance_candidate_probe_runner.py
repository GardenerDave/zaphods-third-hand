import json
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_candidate_probe_runner import run_probe, score_response
from local_harness.larql_affordance_probe import build_candidate, read_failure_note, read_json


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_candidate_probe_runner.py"
PROFILE = ROOT / "examples/host_profiles/navigator_desktop.example.json"
NOTE = ROOT / "examples/failure_notes/cuda_on_rx580_failure.example.md"


def run_runner(*args: str | Path) -> subprocess.CompletedProcess[str]:
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


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_help_works():
    result = run_runner("--help")

    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_dry_run_creates_exactly_four_files(tmp_path):
    candidate = write_candidate(tmp_path)
    out = tmp_path / "probe_run"

    result = run_runner("--candidate", candidate, "--out", out, "--dry-run")

    assert result.returncode == 0, result.stdout + result.stderr
    assert sorted(path.name for path in out.iterdir()) == [
        "probe_prompt_packet.json",
        "probe_report.json",
        "probe_report.md",
        "probe_run.jsonl",
    ]


def test_dry_run_writes_pending_model_call_events(tmp_path):
    candidate = write_candidate(tmp_path)
    out = tmp_path / "probe_run"

    run_probe(candidate_path=candidate, out_dir=out)
    events = read_jsonl(out / "probe_run.jsonl")

    assert events
    assert {event["status"] for event in events} == {"pending_model_call"}
    assert {event["event_type"] for event in events} == {"pending_model_call"}
    assert events[0]["prompt_id"] == "probe_001"
    assert events[-1]["prompt_id"].startswith("regression_")


def test_dry_run_report_has_hold_pending_values(tmp_path):
    candidate = write_candidate(tmp_path)
    out = tmp_path / "probe_run"

    report = run_probe(candidate_path=candidate, out_dir=out)

    assert report["run_mode"] == "dry_run"
    assert report["model_calls_performed"] is False
    assert report["overall_verdict"] == "not_evaluated"
    assert report["promotion_verdict"] == "hold_pending_probe"
    assert report["recommended_next_step"] == "run_endpoint_probe_or_review_prompt_packet"


def test_missing_candidate_fails_clearly(tmp_path):
    result = run_runner("--candidate", tmp_path / "missing.json", "--out", tmp_path / "out")

    assert result.returncode == 1
    assert "missing candidate file" in result.stdout


def test_output_path_traversal_is_refused(tmp_path):
    candidate = write_candidate(tmp_path)
    result = run_runner("--candidate", candidate, "--out", tmp_path / ".." / "escape")

    assert result.returncode == 1
    assert "must not contain '..'" in result.stdout


def test_allow_model_calls_requires_endpoint_and_model(tmp_path):
    candidate = write_candidate(tmp_path)
    result = run_runner("--candidate", candidate, "--out", tmp_path / "out", "--allow-model-calls")

    assert result.returncode == 1
    assert "requires --endpoint-url and --model-id" in result.stdout


def test_missing_required_candidate_field_fails_clearly(tmp_path):
    candidate = write_candidate(tmp_path)
    payload = json.loads(candidate.read_text(encoding="utf-8"))
    del payload["host_affordance_context"]
    candidate.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = run_runner("--candidate", candidate, "--out", tmp_path / "out")

    assert result.returncode == 1
    assert "missing required fields" in result.stdout
    assert "host_affordance_context" in result.stdout


def test_scoring_helpers_classify_probe_responses(tmp_path):
    candidate_path = write_candidate(tmp_path)
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))

    good = score_response(
        candidate,
        "probe",
        "The host profile says no_cuda. Use OpenCL/ROCm investigation before CUDA-specific commands.",
    )
    bad = score_response(
        candidate,
        "probe",
        "Use CUDA-only install or runtime commands on this example host.",
    )

    assert good["verdict"] == "pass"
    assert good["checks"]["constraint_mentioned"] is True
    assert good["checks"]["known_good_mentioned"] is True
    assert bad["verdict"] == "needs_review"
    assert bad["checks"]["known_bad_avoided"] is False


def test_known_bad_path_can_be_named_as_something_to_avoid(tmp_path):
    candidate_path = write_candidate(tmp_path)
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))

    result = score_response(
        candidate,
        "probe",
        (
            "The host profile says no_cuda, so avoid CUDA-only install or runtime "
            "commands on this example host. Use OpenCL/ROCm investigation before "
            "CUDA-specific commands."
        ),
    )

    assert result["verdict"] == "pass"
    assert result["checks"]["known_bad_avoided"] is True
    assert result["checks"]["constraint_mentioned"] is True
    assert result["checks"]["known_good_mentioned"] is True


def test_known_bad_path_recommendation_needs_review(tmp_path):
    candidate_path = write_candidate(tmp_path)
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))

    result = score_response(
        candidate,
        "probe",
        (
            "The host profile says no_cuda, but use CUDA-only install or runtime "
            "commands on this example host. Then inspect OpenCL/ROCm investigation "
            "before CUDA-specific commands later."
        ),
    )

    assert result["verdict"] == "needs_review"
    assert result["checks"]["known_bad_avoided"] is False
    assert result["checks"]["constraint_mentioned"] is True
    assert result["checks"]["known_good_mentioned"] is True


def test_probe_response_passes_with_constraint_and_known_good_path(tmp_path):
    candidate_path = write_candidate(tmp_path)
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))

    result = score_response(
        candidate,
        "probe",
        (
            "Use the host profile constraint no_cuda. The safer path is "
            "OpenCL/ROCm investigation before CUDA-specific commands."
        ),
    )

    assert result["verdict"] == "pass"
    assert result["checks"]["known_bad_avoided"] is True
    assert result["checks"]["constraint_mentioned"] is True
    assert result["checks"]["known_good_mentioned"] is True


def test_scoring_helpers_classify_regression_responses(tmp_path):
    candidate_path = write_candidate(tmp_path)
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))

    good = score_response(
        candidate,
        "regression",
        "Do not generalize this to a different host. Reverify the active host profile first.",
    )
    bad = score_response(
        candidate,
        "regression",
        "Apply the same CUDA workaround everywhere.",
    )

    assert good["verdict"] == "pass"
    assert good["checks"]["constraint_mentioned"] is True
    assert good["checks"]["no_cross_host_generalization"] is True
    assert bad["verdict"] == "needs_review"
    assert bad["checks"]["no_cross_host_generalization"] is False


def test_no_positive_acceptance_or_promotion_status_is_emitted(tmp_path):
    candidate = write_candidate(tmp_path)
    out = tmp_path / "probe_run"
    run_probe(candidate_path=candidate, out_dir=out)

    combined = "\n".join(path.read_text(encoding="utf-8") for path in out.iterdir()).lower()

    assert "accepted_for_training_candidate" not in combined
    assert "accepted_for_larql_patch_candidate" not in combined
    assert "promoted" not in combined
    assert "hold_pending_probe" in combined
