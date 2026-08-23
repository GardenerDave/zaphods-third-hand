from scripts import audit_semantic_fallback_necessity as audit
from scripts import deterministic_first_confirmation as confirmation
from scripts import zth_deterministic_first_semantic_fallback as fallback


def test_all_preserved_wrapper_fallbacks_are_pre_model_deterministic_presence_cases():
    rows = audit.audit_rows()
    assert len(rows) == 6
    assert all(row["derive_normalization_context"] == "PRESENCE_OBSERVATION_CONTEXT" for row in rows)
    assert all(row["counterfactual_deterministic_projection"]["status"] == "RESOLVED" for row in rows)
    assert all(row["counterfactual_deterministic_projection"]["canonical_operation"] == "observe_presence" for row in rows)
    assert all(row["counterfactual_model_call_would_be_avoided"] for row in rows)


def test_polite_wrappers_have_same_bounded_counterfactual_result():
    requests = [
        "Could you check whether docs/example-a.md is available in the tree?",
        "Please verify that docs/example-b.md can be found here.",
        "Can you confirm whether docs/example-c.md is present right now?",
        "Would you determine whether docs/example-d.md exists at this time?",
    ]
    for request in requests:
        result = audit.counterfactual_presence_projection(request)
        assert result["status"] == "RESOLVED"
        assert result["canonical_operation"] == "observe_presence"


def test_negative_cases_do_not_project_to_presence():
    cases = audit.negative_cases()
    assert len(cases) == 10
    assert all(row["safe"] for row in cases)
    assert all(row["projection"]["canonical_operation"] != "observe_presence" for row in cases)
    assert audit.counterfactual_presence_projection("Check and inspect docs/x.md")["status"] == "AMBIGUOUS"
    assert audit.counterfactual_presence_projection("Check whether docs/x.md should be amended")["status"] == "UNRESOLVED"


def test_evaluator_data_cannot_change_projection_or_authority():
    request = "Could you check whether docs/example.md is available in the tree?"
    projection = audit.counterfactual_presence_projection(request)
    corrupted_expectation = {"expected_canonical_operation": "delete", "expected_requested_target": "docs/other.md"}
    assert audit.counterfactual_presence_projection(request) == projection
    authority = {"allowed_observation_operations": ["observe_presence"], "allowed_targets": [projection["target"]]}
    assert confirmation.validate_execution_authority(projection["canonical_operation"], projection["target"], authority)["status"] == "AUTHORIZED"
    assert corrupted_expectation["expected_canonical_operation"] != projection["canonical_operation"]


def test_historical_fallback_artifacts_and_scores_remain_inspectable():
    rows = audit.audit_rows()
    assert {row["task_id"] for row in rows} == {"dff-007", "dff-008", "dff-009", "dff-010", "dfc-003", "dfc-004"}
    assert sum(row["historical_model_calls"] for row in rows) == 6
    assert sum(row["historical_tool_calls"] for row in rows) == 3
    assert all(row["raw_model_action"] for row in rows)
    assert fallback.derive_context(rows[0]["raw_request"]) == "PRESENCE_OBSERVATION_CONTEXT"
