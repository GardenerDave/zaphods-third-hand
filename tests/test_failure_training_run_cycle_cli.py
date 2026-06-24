import json
import subprocess
import sys
from pathlib import Path

from local_harness.failure_training.common import read_jsonl


FIXTURE = Path("tests/fixtures/failure_training/raw_probe_rows.jsonl")


def test_run_cycle_cli_with_fixture(tmp_path):
    work_root = tmp_path / "work"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "local_harness.failure_training.run_cycle",
            "--input",
            str(FIXTURE),
            "--work-root",
            str(work_root),
            "--cycle-id",
            "cycle_fixture",
            "--source-run-id",
            "fixture_run",
            "--target-capability",
            "strict_json_contract",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0

    cycle_dir = work_root / "cycles" / "cycle_fixture"
    manifest_path = cycle_dir / "cycle_manifest.json"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    candidates = read_jsonl(cycle_dir / "curriculum" / "candidates.jsonl")
    needs_revision = read_jsonl(cycle_dir / "curriculum" / "review" / "needs_revision.jsonl")
    candidate_rows = read_jsonl(cycle_dir / "curriculum" / "review" / "candidate.jsonl")
    train_rows = read_jsonl(cycle_dir / "datasets" / "train.jsonl")

    assert manifest["cycle_id"] == "cycle_fixture"
    assert manifest["source_run_id"] == "fixture_run"
    assert manifest["target_capability"] == "strict_json_contract"
    assert manifest["counts"]["failure_events"] == 2
    assert manifest["counts"]["curriculum_candidates"] == 2
    assert manifest["counts"]["accepted"] == 0
    assert manifest["counts"]["train"] == 0

    assert len(candidates) == 2
    assert len(needs_revision) == 1
    assert len(candidate_rows) == 1
    assert train_rows == []

    assert (cycle_dir / "status.log").exists()
    assert (cycle_dir / "status_events.jsonl").exists()
    assert (cycle_dir / "datasets" / "sft" / "sft_manifest.jsonl").exists()
