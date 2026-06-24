from local_harness.failure_training.collect_failures import (
    collect_failure_events,
    collect_failures_from_jsonl,
    is_failure_row,
    normalized_score_result,
)
from local_harness.failure_training.common import read_jsonl, write_jsonl


def test_normalized_score_result_handles_common_values():
    assert normalized_score_result({"score_result": "fail"}) == "fail"
    assert normalized_score_result({"result": "PARTIAL"}) == "partial"
    assert normalized_score_result({"status": "accepted"}) == "pass"
    assert normalized_score_result({"passed": False}) == "fail"
    assert normalized_score_result({}) == "unknown"


def test_is_failure_row_filters_passes():
    assert is_failure_row({"score_result": "fail"})
    assert is_failure_row({"score_result": "partial"})
    assert is_failure_row({"score_result": "unknown"})
    assert not is_failure_row({"score_result": "pass"})


def test_collect_failure_events_normalizes_core_fields():
    rows = [
        {
            "probe_id": "pass_case",
            "score_result": "pass",
            "prompt": "ok prompt",
            "raw_output": "ok output",
        },
        {
            "probe_id": "json_case",
            "score_result": "fail",
            "prompt": "return json",
            "raw_output": "not json",
            "model_id": "tiny-model",
            "failure_mode": "json_contract",
            "severity": "high",
        },
    ]

    events = collect_failure_events(
        rows,
        cycle_id="cycle_0001",
        source_run_id="audition_001",
    )

    assert len(events) == 1
    event = events[0]
    assert event["id"].startswith("failure_0002_")
    assert event["cycle_id"] == "cycle_0001"
    assert event["source_run_id"] == "audition_001"
    assert event["model_id"] == "tiny-model"
    assert event["probe_id"] == "json_case"
    assert event["score_result"] == "fail"
    assert event["failure_mode"] == "json_contract"
    assert event["severity"] == "high"
    assert event["prompt_hash"]
    assert event["raw_output_hash"]


def test_collect_failures_from_jsonl_round_trip(tmp_path):
    input_path = tmp_path / "raw.jsonl"
    output_path = tmp_path / "failures.jsonl"

    write_jsonl(
        input_path,
        [
            {
                "task_id": "case_1",
                "result": "partial",
                "input": "Give strict JSON",
                "output": "{broken",
                "model": "small-model",
                "failure_type": "invalid_json",
            }
        ],
    )

    events = collect_failures_from_jsonl(
        input_path,
        output_path,
        cycle_id="cycle_0002",
        source_run_id="run_abc",
    )

    assert len(events) == 1

    loaded = read_jsonl(output_path)
    assert loaded == events
    assert loaded[0]["probe_id"] == "case_1"
    assert loaded[0]["prompt"] == "Give strict JSON"
    assert loaded[0]["raw_output"] == "{broken"


def test_collect_failure_events_preserves_corrected_outputs():
    rows = [
        {
            "probe_id": "json_case",
            "score_result": "fail",
            "prompt": "return json",
            "raw_output": "not json",
            "model_id": "tiny-model",
            "corrected_output": '{"ok": true}',
        },
    ]

    events = collect_failure_events(
        rows,
        cycle_id="cycle_0001",
        source_run_id="audition_001",
    )

    assert events[0]["corrected_output"] == '{"ok": true}'
