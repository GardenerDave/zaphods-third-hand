from __future__ import annotations

from local_harness.model_audition_scorers import score_case


def test_json_parse_scorer_pass() -> None:
    result = score_case(
        fixture={"case_id": "case_001", "task_type": "classification"},
        model_text='{"label": "hardware"}',
        scorer_profile={
            "profile_id": "test",
            "metrics": [
                {"id": "json_parse", "type": "json_parse", "weight": 1.0},
            ],
        },
        runtime={"wall_time_seconds": 1.0},
    )

    assert result["overall"] == 1.0
    assert result["metrics"]["json_parse"]["score"] == 1.0
    assert result["failure_modes"] == []


def test_json_parse_scorer_fail() -> None:
    result = score_case(
        fixture={"case_id": "case_001", "task_type": "classification"},
        model_text="not json",
        scorer_profile={
            "profile_id": "test",
            "metrics": [
                {"id": "json_parse", "type": "json_parse", "weight": 1.0},
            ],
        },
        runtime={"wall_time_seconds": 1.0},
    )

    assert result["overall"] == 0.0
    assert result["metrics"]["json_parse"]["score"] == 0.0
    assert "json_parse_failed" in result["failure_modes"]


def test_required_keys_scorer() -> None:
    result = score_case(
        fixture={"case_id": "case_001", "task_type": "classification"},
        model_text='{"label": "hardware"}',
        scorer_profile={
            "profile_id": "test",
            "metrics": [
                {
                    "id": "required_keys",
                    "type": "required_keys",
                    "weight": 1.0,
                    "keys": ["label", "confidence"],
                },
            ],
        },
        runtime={"wall_time_seconds": 1.0},
    )

    assert result["overall"] == 0.5
    assert result["metrics"]["required_keys"]["details"]["present_keys"] == ["label"]
    assert result["metrics"]["required_keys"]["details"]["missing_keys"] == [
        "confidence"
    ]
    assert "missing_required_keys" in result["failure_modes"]


def test_expected_field_match_scorer() -> None:
    result = score_case(
        fixture={
            "case_id": "route_001",
            "task_type": "classification",
            "expected": {
                "label": "hardware",
                "confidence": 0.82,
            },
        },
        model_text='{"label": "hardware", "confidence": 0.5}',
        scorer_profile={
            "profile_id": "test",
            "metrics": [
                {
                    "id": "expected_field_match",
                    "type": "expected_field_match",
                    "weight": 1.0,
                },
            ],
        },
        runtime={"wall_time_seconds": 1.0},
    )

    assert result["overall"] == 0.5
    assert result["metrics"]["expected_field_match"]["details"]["matches"] == {
        "label": True,
        "confidence": False,
    }
    assert "expected_field_mismatch" in result["failure_modes"]


def test_runtime_scorer() -> None:
    result = score_case(
        fixture={"case_id": "case_001", "task_type": "classification"},
        model_text='{"label": "hardware"}',
        scorer_profile={
            "profile_id": "test",
            "metrics": [
                {
                    "id": "runtime",
                    "type": "runtime",
                    "weight": 1.0,
                    "target_seconds": 10,
                },
            ],
        },
        runtime={"wall_time_seconds": 20.0},
    )

    assert result["overall"] == 0.5
    assert result["metrics"]["runtime"]["score"] == 0.5
    assert "runtime_over_target" in result["failure_modes"]


def test_completion_scorer_empty_output() -> None:
    result = score_case(
        fixture={"case_id": "case_001", "task_type": "classification"},
        model_text="",
        scorer_profile={
            "profile_id": "test",
            "metrics": [
                {"id": "completed", "type": "completion", "weight": 1.0},
            ],
        },
        runtime={"wall_time_seconds": 1.0},
    )

    assert result["overall"] == 0.0
    assert "empty_output" in result["failure_modes"]


def test_score_case_weighted_overall() -> None:
    result = score_case(
        fixture={
            "case_id": "route_001",
            "task_type": "classification",
            "expected": {"label": "hardware"},
        },
        model_text='{"label": "hardware", "confidence": 0.9}',
        scorer_profile={
            "profile_id": "test",
            "metrics": [
                {"id": "completed", "type": "completion", "weight": 0.1},
                {"id": "json_parse", "type": "json_parse", "weight": 0.2},
                {
                    "id": "required_keys",
                    "type": "required_keys",
                    "weight": 0.2,
                    "keys": ["label", "confidence"],
                },
                {
                    "id": "expected_field_match",
                    "type": "expected_field_match",
                    "weight": 0.3,
                },
                {
                    "id": "runtime",
                    "type": "runtime",
                    "weight": 0.2,
                    "target_seconds": 10,
                },
            ],
        },
        runtime={"wall_time_seconds": 10.0},
    )

    assert result["overall"] == 1.0
    assert result["failure_modes"] == []
