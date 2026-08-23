from scripts import deterministic_first_confirmation as confirmation


def test_runtime_and_evaluator_manifests_are_independent():
    runtime_cases, evaluator_cases = confirmation.runtime_and_evaluator()
    assert len(runtime_cases) == len(evaluator_cases) == 8
    assert all(not any(key.startswith("expected_") for key in case) for case in runtime_cases)
    assert all(any(key.startswith("expected_") for key in case) for case in evaluator_cases)


def test_missing_actuator_is_incomplete_and_read_only_tool_is_not_an_actuator():
    case = next(x for x in confirmation.runtime_cases() if x["task_id"] == "dfc-005")
    derivation = confirmation.derive(case["input_request"])
    plan = confirmation.plan(case["task_id"], derivation, case["environment_facts"]["authority_record"])
    assert derivation["canonical_operation"] == "amend"
    assert plan["routing_success"] is True
    assert plan["overall_coverage"] == "INCOMPLETE"
    assert plan["incomplete_reason"] == "NO_QUALIFIED_EXECUTION_SUPPLIER"
    assert plan["planned_tool_calls"] == 0


def test_ambiguous_and_unsupported_fail_closed_without_execution_supplier():
    for task_id in ("dfc-007", "dfc-008"):
        case = next(x for x in confirmation.runtime_cases() if x["task_id"] == task_id)
        derivation = confirmation.derive(case["input_request"])
        plan = confirmation.plan(task_id, derivation, case["environment_facts"]["authority_record"])
        assert plan["overall_coverage"] == "INCOMPLETE"
        assert plan["planned_model_calls"] == 0
        assert plan["planned_tool_calls"] == 0


def test_model_output_cannot_grant_authority():
    case = next(x for x in confirmation.runtime_cases() if x["task_id"] == "dfc-003")
    altered = {"action":"check", "object_expression":"docs/unauthorized.md"}
    derivation = confirmation.derive(case["input_request"], altered)
    assert derivation["status"] == "RESOLVED"
    assert case["environment_facts"]["authority_record"]["allowed_targets"] != [altered["object_expression"]]
