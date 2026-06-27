import json
import re
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


def run_example_with_out(tmp_path: Path, profile: Path, note: Path) -> tuple[dict, Path]:
    out = tmp_path / "out"
    result = run_probe("--host-profile", profile, "--failure-note", note, "--out", out)
    assert result.returncode == 0, result.stdout + result.stderr
    return (
        json.loads((out / "affordance_patch_candidate.json").read_text(encoding="utf-8")),
        out,
    )


def test_script_runs_on_example_inputs_and_writes_valid_json(tmp_path):
    candidate = run_example(tmp_path, NAVIGATOR_PROFILE, CUDA_NOTE)

    assert candidate["candidate_id"].startswith("larql_affordance_candidate_")
    assert candidate["review_status"] == "draft"
    assert candidate["promotion_status"] == "needs_probe"


def test_candidate_includes_source_digests(tmp_path):
    candidate = run_example(tmp_path, NAVIGATOR_PROFILE, CUDA_NOTE)
    digests = candidate["source_digests"]

    assert re.fullmatch(r"[0-9a-f]{64}", digests["host_profile_sha256"])
    assert re.fullmatch(r"[0-9a-f]{64}", digests["failure_note_sha256"])
    assert digests["classifier_version"] == "larql_affordance_probe.v0"


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


def test_host_profile_digest_and_candidate_id_change_when_profile_content_changes(tmp_path):
    original = run_example(tmp_path / "original", NAVIGATOR_PROFILE, CUDA_NOTE)

    modified_profile = tmp_path / "modified_profile.json"
    profile = json.loads(NAVIGATOR_PROFILE.read_text(encoding="utf-8"))
    profile["constraints"] = [*profile["constraints"], "new_example_constraint"]
    profile["known_good_paths"] = [
        *profile["known_good_paths"],
        "new example known-good path",
    ]
    modified_profile.write_text(
        json.dumps(profile, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    modified = run_example(tmp_path / "modified", modified_profile, CUDA_NOTE)

    assert modified["repair_lane"] == original["repair_lane"]
    assert (
        modified["source_digests"]["host_profile_sha256"]
        != original["source_digests"]["host_profile_sha256"]
    )
    assert modified["source_digests"]["failure_note_sha256"] == (
        original["source_digests"]["failure_note_sha256"]
    )
    assert modified["candidate_id"] != original["candidate_id"]


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


def test_candidate_includes_host_affordance_context(tmp_path):
    candidate = run_example(tmp_path, NAVIGATOR_PROFILE, CUDA_NOTE)

    context = candidate["host_affordance_context"]
    assert "CPU fallback for small smoke tests" in context["known_good_paths"]
    assert "CUDA-only install or runtime commands on this example host" in context["known_bad_paths"]
    assert "no_cuda" in context["constraints"]


def test_prompts_use_specific_host_profile_affordances(tmp_path):
    candidate = run_example(tmp_path, NAVIGATOR_PROFILE, CUDA_NOTE)
    prompt_text = "\n".join(candidate["probe_prompts"] + candidate["regression_prompts"])

    assert "no_cuda" in prompt_text
    assert "CUDA-only install or runtime commands on this example host" in prompt_text
    assert "OpenCL/ROCm investigation before CUDA-specific commands" in prompt_text


def test_regression_prompts_cover_split_workflow_host_confusion(tmp_path):
    candidate = run_example(tmp_path, NAVIGATOR_PROFILE, CUDA_NOTE)
    prompt_text = "\n".join(candidate["regression_prompts"])

    assert "split workflow" in prompt_text
    assert "navigator_desktop_example is the active host" in prompt_text
    assert "another workflow host" in prompt_text
    assert "borrowing that other host's affordance map" in prompt_text


def test_reports_include_specific_host_affordance_context(tmp_path):
    _candidate, out = run_example_with_out(tmp_path, R420_PROFILE, AVX2_NOTE)
    report = (out / "classification_report.md").read_text(encoding="utf-8")
    plan = (out / "probe_plan.md").read_text(encoding="utf-8")

    assert "CPU binaries built without AVX2" in report
    assert "AVX2-required binaries on this example host" in report
    assert "no_avx2" in report
    assert "CPU binaries built without AVX2" in plan
    assert "AVX2-required binaries on this example host" in plan


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
