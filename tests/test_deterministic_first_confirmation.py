from scripts import deterministic_first_confirmation as confirmation


def test_runtime_and_evaluator_manifests_are_independent():
    runtime_cases, evaluator_cases = confirmation.runtime_and_evaluator()
    assert len(runtime_cases) == len(evaluator_cases) == 8
    assert all(not any(key.startswith("expected_") for key in case) for case in runtime_cases)
    assert all(any(key.startswith("expected_") for key in case) for case in evaluator_cases)


def test_missing_actuator_is_incomplete_and_read_only_tool_is_not_an_actuator():
    for task_id, operation in (("dfc-005", "amend"), ("dfc-006", "dispatch")):
        case = next(x for x in confirmation.runtime_cases() if x["task_id"] == task_id)
        derivation = confirmation.derive(case["input_request"])
        plan = confirmation.plan(case["task_id"], derivation, case["environment_facts"]["authority_record"])
        assert derivation["canonical_operation"] == operation
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
    plan = confirmation.plan(case["task_id"], derivation, case["environment_facts"]["authority_record"])
    assert plan["overall_coverage"] == "COMPLETE"
    request = {
        "schema": "zth_tool_request_v0",
        "capability_id": confirmation.TOOL_CAPABILITY,
        "supplier_id": confirmation.tool.TOOL_SUPPLIER,
        "repository_relative_path": altered["object_expression"],
        "authorized_targets": case["environment_facts"]["authority_record"]["allowed_targets"],
        "authority_source": "ENVIRONMENT_AUTHORITY_RECORD",
    }
    assert confirmation.tool.validate_tool_request(request)["status"] == "DENIED"


def test_evaluator_corruption_cannot_change_runtime_cases_or_plans():
    runtime_cases, evaluator_cases = confirmation.runtime_and_evaluator()
    original = []
    for case in runtime_cases:
        derivation = confirmation.derive(case["input_request"])
        original.append((case["task_id"], derivation, confirmation.plan(case["task_id"], derivation, case["environment_facts"]["authority_record"])))
    corrupted = [{**case, "expected_canonical_operation":"delete", "expected_terminal_state":"terminal_success", "expected_model_required":True, "expected_tool_required":False} for case in evaluator_cases]
    assert [case["task_id"] for case in corrupted] == [case["task_id"] for case in evaluator_cases]
    repeated = []
    for case in runtime_cases:
        derivation = confirmation.derive(case["input_request"])
        repeated.append((case["task_id"], derivation, confirmation.plan(case["task_id"], derivation, case["environment_facts"]["authority_record"])))
    assert original == repeated
    assert evaluator_cases != corrupted


def test_pre_actuation_authority_allows_authorized_operation_and_target_without_real_observer():
    calls = []

    def stub_observer(request, authority):
        calls.append((request, authority))
        return {"status": "VALID_OBSERVATION", "repository_relative_path": request["repository_relative_path"]}

    authority = {"allowed_observation_operations": ["observe_presence"], "allowed_targets": ["docs/research/DETERMINISTIC_FIRST_CONFIRMATION_DESIGN_2026-08-23.md"]}
    result, request, tool_authority, observation, count = confirmation.execute_read_only_observation(
        "observe_presence", authority["allowed_targets"][0], authority, observer=stub_observer
    )
    assert result["status"] == "AUTHORIZED"
    assert tool_authority["status"] == "AUTHORIZED"
    assert observation["status"] == "VALID_OBSERVATION"
    assert count == 1
    assert len(calls) == 1


def test_pre_actuation_denies_unauthorized_operation_before_observer():
    calls = []
    authority = {"allowed_observation_operations": [], "allowed_targets": ["docs/research/DETERMINISTIC_FIRST_CONFIRMATION_DESIGN_2026-08-23.md"]}
    result, _, _, _, count = confirmation.execute_read_only_observation(
        "observe_presence", authority["allowed_targets"][0], authority, observer=lambda *_: calls.append(True)
    )
    assert result["status"] == "OPERATION_AUTHORITY_DENIED"
    assert count == 0
    assert calls == []


def test_pre_actuation_denies_unauthorized_target_before_observer():
    calls = []
    authority = {"allowed_observation_operations": ["observe_presence"], "allowed_targets": []}
    result, _, _, _, count = confirmation.execute_read_only_observation(
        "observe_presence", "docs/research/DETERMINISTIC_FIRST_CONFIRMATION_DESIGN_2026-08-23.md", authority, observer=lambda *_: calls.append(True)
    )
    assert result["status"] == "TARGET_AUTHORITY_DENIED"
    assert count == 0
    assert calls == []


def test_model_output_cannot_grant_operation_or_target_authority():
    authority = {"allowed_observation_operations": ["observe_presence"], "allowed_targets": ["docs/research/DETERMINISTIC_FIRST_CONFIRMATION_DESIGN_2026-08-23.md"]}
    operation_denied = confirmation.validate_execution_authority("amend", authority["allowed_targets"][0], authority)
    target_denied = confirmation.validate_execution_authority("observe_presence", "docs/research/not-authorized.md", authority)
    assert operation_denied["status"] == "OPERATION_AUTHORITY_DENIED"
    assert target_denied["status"] == "TARGET_AUTHORITY_DENIED"
    assert operation_denied["authority_source"] == target_denied["authority_source"] == "ENVIRONMENT_AUTHORITY_RECORD"


def test_coverage_uses_latest_plan_and_separates_stage_zero():
    stage_zero = {"overall_coverage": "COMPLETE"}
    final_incomplete = {"overall_coverage": "INCOMPLETE"}
    coverage = confirmation.coverage_state(stage_zero, final_incomplete)
    assert coverage == {"stage_0_coverage": "COMPLETE", "final_execution_coverage": "INCOMPLETE", "execution_path_complete": False}
    unresolved = confirmation.coverage_state(stage_zero, unresolved_after_plan_0=True)
    assert unresolved["stage_0_coverage"] == "COMPLETE"
    assert unresolved["execution_path_complete"] is False


def test_fail_closed_requests_are_correct_routing_but_not_complete_execution_paths():
    for task_id in ("dfc-007", "dfc-008"):
        case = next(x for x in confirmation.runtime_cases() if x["task_id"] == task_id)
        derivation = confirmation.derive(case["input_request"])
        plan = confirmation.plan(task_id, derivation, case["environment_facts"]["authority_record"])
        coverage = confirmation.coverage_state(plan)
        assert plan["routing_success"] is False
        assert coverage["execution_path_complete"] is False
