import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_affordance_probe.py"
NAVIGATOR_PROFILE = ROOT / "examples/host_profiles/navigator_desktop.example.json"
R420_PROFILE = ROOT / "examples/host_profiles/r420_server.example.json"
UNKNOWN_PROFILE = ROOT / "examples/host_profiles/unknown_host.example.json"
CUDA_NOTE = ROOT / "examples/failure_notes/cuda_on_rx580_failure.example.md"
AVX2_NOTE = ROOT / "examples/failure_notes/avx2_on_r420_failure.example.md"
UNKNOWN_NOTE = ROOT / "examples/failure_notes/unknown_host_failure.example.md"


def run_probe(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def run_example(tmp_path: Path, profile: Path, note: Path) -> dict:
    out = tmp_path / "out"
    result = run_probe("--host-profile", profile, "--failure-note", note, "--out", out)
    assert result.returncode == 0, result.stdout + result.stderr
    files = sorted(path.name for path in out.iterdir())
    assert files == [
        "affordance_patch_candidate.json",
        "classification_report.md",
        "probe_plan.md",
    ]
    return json.loads((out / "affordance_patch_candidate.json").read_text(encoding="utf-8"))


def test_script_runs_on_example_inputs_and_writes_valid_json(tmp_path):
    candidate = run_example(tmp_path, NAVIGATOR_PROFILE, CUDA_NOTE)

    assert candidate["candidate_id"].startswith("larql_affordance_candidate_")
    assert candidate["review_status"] == "draft"
    assert candidate["promotion_status"] == "needs_probe"


def test_cuda_gpu_mismatch_classifies_as_stacked_candidate(tmp_path):
    candidate = run_example(tmp_path, NAVIGATOR_PROFILE, CUDA_NOTE)

    assert candidate["repair_lane"] == "larql_plus_lora_candidate"
    assert "CUDA" in candidate["failure_summary"]


def test_avx2_mismatch_classifies_as_larql_candidate(tmp_path):
    candidate = run_example(tmp_path, R420_PROFILE, AVX2_NOTE)

    assert candidate["repair_lane"] == "larql_candidate"
    assert "AVX2" in candidate["failure_summary"]


def test_unknown_host_classifies_as_review_only(tmp_path):
    candidate = run_example(tmp_path, UNKNOWN_PROFILE, UNKNOWN_NOTE)

    assert candidate["repair_lane"] == "review_only"
    assert "Insufficient" in candidate["failure_summary"]


def test_output_never_marks_anything_accepted(tmp_path):
    candidate = run_example(tmp_path, NAVIGATOR_PROFILE, CUDA_NOTE)
    serialized = json.dumps(candidate).lower()

    assert "accepted_for_training_candidate" not in serialized
    assert "accepted_for_larql_patch_candidate" not in serialized
    assert candidate["review_status"] == "draft"
    assert candidate["promotion_status"] == "needs_probe"


def test_output_includes_probe_and_regression_prompts(tmp_path):
    candidate = run_example(tmp_path, NAVIGATOR_PROFILE, CUDA_NOTE)

    assert len(candidate["probe_prompts"]) >= 3
    assert len(candidate["regression_prompts"]) >= 3


def test_script_refuses_missing_files(tmp_path):
    result = run_probe(
        "--host-profile",
        tmp_path / "missing.json",
        "--failure-note",
        CUDA_NOTE,
        "--out",
        tmp_path / "out",
    )

    assert result.returncode == 1
    assert "missing input file" in result.stdout


def test_script_refuses_out_dir_path_traversal(tmp_path):
    result = run_probe(
        "--host-profile",
        NAVIGATOR_PROFILE,
        "--failure-note",
        CUDA_NOTE,
        "--out",
        tmp_path / ".." / "escape",
    )

    assert result.returncode == 1
    assert "must not contain '..'" in result.stdout
