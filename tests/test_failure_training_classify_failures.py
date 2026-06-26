from local_harness.failure_training.classify_failures import (
    classify_failure_event,
    classify_failure_events,
    classify_failures_jsonl,
    classify_failure_mode,
    classify_severity,
)
from local_harness.failure_training.common import read_jsonl, write_jsonl


def event_with_output(raw_output, **overrides):
    event = {
        "id": "failure_1",
        "cycle_id": "cycle_0001",
        "source_run_id": "run_1",
        "model_id": "tiny-model",
        "probe_id": "probe_1",
        "prompt": "Return valid JSON.",
        "raw_output": raw_output,
        "score_result": "fail",
        "failure_mode": "unknown",
        "severity": "medium",
        "expected_contract": "JSON object",
        "prompt_hash": "prompt_hash",
        "raw_output_hash": "output_hash",
    }
    event.update(overrides)
    return event


def test_classify_failure_mode_preserves_existing_specific_label():
    event = event_with_output("not json", failure_mode="custom_label")

    assert classify_failure_mode(event) == "custom_label"


def test_classify_failure_mode_detects_empty_output():
    assert classify_failure_mode(event_with_output("")) == "empty_output"


def test_classify_failure_mode_detects_placeholder_leak():
    event = event_with_output("TODO: replace me with the real answer")

    assert classify_failure_mode(event) == "placeholder_leak"


def test_classify_failure_mode_detects_invalid_json_contract():
    event = event_with_output("{broken")

    assert classify_failure_mode(event) == "invalid_json"


def test_classify_failure_mode_detects_unsupported_certainty():
    event = event_with_output(
        "I checked all files and there are no files with this issue.",
        prompt="Use only cited evidence.",
        expected_contract="evidence summary",
    )

    assert classify_failure_mode(event) == "unsupported_certainty"


def test_classify_failure_mode_falls_back_to_unclassified_failure():
    event = event_with_output(
        "This answer is long enough but still wrong.",
        prompt="Explain the failure.",
        expected_contract="plain text",
    )

    assert classify_failure_mode(event) == "unclassified_failure"


def test_classify_severity_promotes_invalid_json_and_empty_output():
    assert classify_severity(event_with_output("{broken"), "invalid_json") == "high"
    assert classify_severity(event_with_output(""), "empty_output") == "high"


def test_classify_failure_event_sets_method_mode_and_severity():
    classified = classify_failure_event(event_with_output("{broken"))

    assert classified["failure_mode"] == "invalid_json"
    assert classified["severity"] == "high"
    assert classified["classification_method"] == "deterministic_rules_v1"


def test_classify_failure_events_returns_list():
    events = classify_failure_events([event_with_output(""), event_with_output("{broken")])

    assert [event["failure_mode"] for event in events] == ["empty_output", "invalid_json"]


def test_classify_failures_jsonl_round_trip(tmp_path):
    input_path = tmp_path / "failures.jsonl"
    output_path = tmp_path / "classified.jsonl"

    write_jsonl(input_path, [event_with_output("{broken")])

    classified = classify_failures_jsonl(input_path, output_path)
    loaded = read_jsonl(output_path)

    assert loaded == classified
    assert loaded[0]["failure_mode"] == "invalid_json"
    assert loaded[0]["classification_method"] == "deterministic_rules_v1"
