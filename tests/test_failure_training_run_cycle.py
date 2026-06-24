import json

from local_harness.failure_training.common import read_jsonl, write_jsonl
from local_harness.failure_training.run_cycle import run_cycle


def test_run_cycle_writes_expected_artifacts_without_auto_accepting(tmp_path):
    input_path = tmp_path / "raw_rows.jsonl"
    work_root = tmp_path / "work"

    write_jsonl(
        input_path,
        [
            {
                "probe_id": "pass_case",
                "score_result": "pass",
                "prompt": "Return JSON.",
                "raw_output": '{"ok": true}',
                "model_id": "tiny-model",
            },
            {
                "probe_id": "fail_case",
                "score_result": "fail",
                "prompt": "Return a JSON object with key ok.",
                "raw_output": "not json",
                "model_id": "tiny-model",
                "expected_contract": "Valid JSON object.",
            },
        ],
    )

    manifest = run_cycle(
        input_path=input_path,
        work_root=work_root,
        cycle_id="cycle_test",
        source_run_id="audition_test",
        target_capability="strict_json_contract",
    )

    cycle_dir = work_root / "cycles" / "cycle_test"

    assert manifest["cycle_id"] == "cycle_test"
    assert manifest["status"] == "completed"
    assert manifest["source_run_id"] == "audition_test"
    assert manifest["target_capability"] == "strict_json_contract"

    assert (cycle_dir / "cycle_manifest.json").exists()
    assert (cycle_dir / "status.log").exists()
    assert (cycle_dir / "status_events.jsonl").exists()

    failures = read_jsonl(cycle_dir / "failures" / "failure_events.jsonl")
    classified = read_jsonl(cycle_dir / "failures" / "classified_failure_events.jsonl")
    candidates = read_jsonl(cycle_dir / "curriculum" / "candidates.jsonl")

    assert len(failures) == 1
    assert failures[0]["probe_id"] == "fail_case"
    assert classified[0]["failure_mode"] == "invalid_json"
    assert candidates[0]["review_status"] == "needs_revision"

    assert read_jsonl(cycle_dir / "curriculum" / "review" / "accepted.jsonl") == []
    assert read_jsonl(cycle_dir / "datasets" / "train.jsonl") == []
    assert read_jsonl(cycle_dir / "datasets" / "validation.jsonl") == []
    assert read_jsonl(cycle_dir / "datasets" / "sft" / "sft_train.jsonl") == []

    saved_manifest = json.loads(
        (cycle_dir / "cycle_manifest.json").read_text(encoding="utf-8")
    )
    assert saved_manifest == manifest
    assert saved_manifest["counts"]["failure_events"] == 1
    assert saved_manifest["counts"]["accepted"] == 0
    assert saved_manifest["counts"]["train"] == 0


def test_run_cycle_preserves_corrected_rows_as_candidates_not_accepted(tmp_path):
    input_path = tmp_path / "raw_rows.jsonl"
    work_root = tmp_path / "work"

    write_jsonl(
        input_path,
        [
            {
                "probe_id": "fail_case",
                "score_result": "fail",
                "prompt": "Return a JSON object with key ok.",
                "raw_output": "not json",
                "model_id": "tiny-model",
                "expected_contract": "Valid JSON object.",
                "corrected_output": '{"ok": true}',
            },
        ],
    )

    manifest = run_cycle(
        input_path=input_path,
        work_root=work_root,
        cycle_id="cycle_candidate",
        source_run_id="audition_test",
        target_capability="strict_json_contract",
    )

    cycle_dir = work_root / "cycles" / "cycle_candidate"
    candidates = read_jsonl(cycle_dir / "curriculum" / "candidates.jsonl")
    review_candidates = read_jsonl(cycle_dir / "curriculum" / "review" / "candidate.jsonl")

    assert candidates[0]["review_status"] == "candidate"
    assert review_candidates[0]["id"] == candidates[0]["id"]
    assert manifest["counts"]["accepted"] == 0
    assert manifest["counts"]["train"] == 0
