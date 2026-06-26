from local_harness.failure_training.build_curriculum import (
    build_candidate_from_failure,
    build_curriculum_candidates,
    build_curriculum_jsonl,
    corrected_output_from_event,
    target_behavior_for_failure_mode,
)
from local_harness.failure_training.common import read_jsonl, write_jsonl


def failure_event(**overrides):
    event = {
        "id": "failure_0001_abc",
        "cycle_id": "cycle_0001",
        "source_run_id": "run_1",
        "model_id": "tiny-model",
        "probe_id": "json_probe",
        "prompt": "Return a JSON object with key ok.",
        "raw_output": "Sure, here you go: ok",
        "score_result": "fail",
        "failure_mode": "invalid_json",
        "severity": "high",
        "expected_contract": "Valid JSON object.",
        "prompt_hash": "prompt_hash",
        "raw_output_hash": "raw_output_hash",
        "source_artifact_paths": ["runs/run_1/result.json"],
    }
    event.update(overrides)
    return event


def test_target_behavior_for_known_failure_mode():
    assert target_behavior_for_failure_mode("invalid_json") == (
        "Return only valid JSON that satisfies the requested contract."
    )


def test_target_behavior_for_unknown_failure_mode_uses_default():
    assert target_behavior_for_failure_mode("strange_failure") == (
        "Return an answer that corrects the observed failure."
    )


def test_corrected_output_from_event_prefers_available_gold_field():
    assert corrected_output_from_event(failure_event(corrected_output="fixed")) == "fixed"
    assert corrected_output_from_event(failure_event(expected_output="expected")) == "expected"
    assert corrected_output_from_event(failure_event()) == ""


def test_build_candidate_without_correction_needs_revision():
    candidate = build_candidate_from_failure(failure_event())

    assert candidate["id"].startswith("candidate_")
    assert candidate["failure_event_id"] == "failure_0001_abc"
    assert candidate["cycle_id"] == "cycle_0001"
    assert candidate["task_type"] == "supervised_failure_correction"
    assert candidate["review_status"] == "needs_revision"
    assert candidate["failure_modes_targeted"] == ["invalid_json"]
    assert len(candidate["messages"]) == 2
    assert candidate["messages"][0]["role"] == "system"
    assert candidate["messages"][1]["role"] == "user"


def test_build_candidate_with_correction_includes_assistant_message():
    candidate = build_candidate_from_failure(
        failure_event(corrected_output='{"ok": true}')
    )

    assert candidate["review_status"] == "candidate"
    assert len(candidate["messages"]) == 3
    assert candidate["messages"][2] == {
        "role": "assistant",
        "content": '{"ok": true}',
    }


def test_build_candidate_preserves_provenance():
    candidate = build_candidate_from_failure(failure_event())

    provenance = candidate["provenance"]
    assert provenance["source_failure_event_id"] == "failure_0001_abc"
    assert provenance["source_run_id"] == "run_1"
    assert provenance["model_id"] == "tiny-model"
    assert provenance["probe_id"] == "json_probe"
    assert provenance["prompt_hash"] == "prompt_hash"
    assert provenance["raw_output_hash"] == "raw_output_hash"
    assert provenance["source_artifact_paths"] == ["runs/run_1/result.json"]


def test_build_curriculum_candidates_returns_one_candidate_per_failure():
    candidates = build_curriculum_candidates(
        [
            failure_event(id="failure_1"),
            failure_event(id="failure_2", failure_mode="empty_output"),
        ]
    )

    assert len(candidates) == 2
    assert candidates[0]["failure_event_id"] == "failure_1"
    assert candidates[1]["failure_modes_targeted"] == ["empty_output"]


def test_build_curriculum_jsonl_round_trip(tmp_path):
    input_path = tmp_path / "classified_failures.jsonl"
    output_path = tmp_path / "candidates.jsonl"

    write_jsonl(input_path, [failure_event()])

    candidates = build_curriculum_jsonl(input_path, output_path)
    loaded = read_jsonl(output_path)

    assert loaded == candidates
    assert loaded[0]["review_status"] == "needs_revision"
