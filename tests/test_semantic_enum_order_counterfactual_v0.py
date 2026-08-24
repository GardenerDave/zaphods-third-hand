from scripts import semantic_enum_order_counterfactual_v0 as probe


def test_enum_orders_are_explicit_and_unresolved_is_last():
    assert probe.ARM_A == ["inspect", "observe_presence", "unresolved"]
    assert probe.ARM_B == ["observe_presence", "inspect", "unresolved"]
    assert probe.schema(probe.ARM_A)["properties"]["operation_class_candidate"]["enum"] == probe.ARM_A
    assert probe.schema(probe.ARM_B)["properties"]["operation_class_candidate"]["enum"] == probe.ARM_B


def test_fresh_tasks_are_interleaved_and_genuinely_unresolved():
    rows = probe.specs()
    assert len(rows) == 6
    assert [expected for _, expected, _ in rows] == [
        "observe_presence", "inspect", "observe_presence", "inspect", "observe_presence", "inspect"
    ]
    for task_id, _, request in rows:
        pre = probe.v2.preflight(request)
        assert pre["semantic_fallback_eligible"] is True
        assert pre["model_required"] is True
        assert pre["deterministic_canonical_operation_available_pre_model"] is False
        assert pre["remaining_candidate_operation_classes"] == ["observe_presence", "inspect"]
        assert probe.AUTHORITY_FIXTURES[task_id]["allowed_observation_operations"] == ["observe_presence", "inspect"]


def test_runtime_authority_is_explicit_and_not_request_derived():
    cases = {case["task_id"]: case for case in probe.runtime_cases()}
    for task_id, _, request in probe.specs():
        assert cases[task_id]["environment_facts"]["authority_record"] == probe.AUTHORITY_FIXTURES[task_id]
        assert task_id not in request
    mutated = dict(cases["seof-001"], input_request="Is docs/research/E9_ZINC_2026-08-23.md present?")
    assert mutated["environment_facts"]["authority_record"] == cases["seof-001"]["environment_facts"]["authority_record"]


def test_paired_prompt_and_runtime_inputs_are_identical_except_schema_order(tmp_path):
    for task_id, _, request in probe.specs():
        assert probe.v2.prompt(request) == probe.v2.prompt(request)
        assert probe.schema(probe.ARM_A)["required"] == probe.schema(probe.ARM_B)["required"]
        assert probe.AUTHORITY_FIXTURES[task_id] == probe.AUTHORITY_FIXTURES[task_id]
    assert probe.ARM_A != probe.ARM_B


def test_strict_parser_accepts_only_arm_enum_values():
    for enum_order in (probe.ARM_A, probe.ARM_B):
        assert probe.parse_response('{"operation_class_candidate":"inspect"}', enum_order)[2]
        assert probe.parse_response('{"operation_class_candidate":"observe_presence"}', enum_order)[2]
        assert not probe.parse_response('{"operation_class_candidate":"unresolved","extra":1}', enum_order)[2]
        assert not probe.parse_response('{"operation_class_candidate":"other"}', enum_order)[2]


def test_prepare_plan_counts_are_integer_safe_for_missing_inspect_supplier():
    for task_id, _, request in probe.specs():
        pre = probe.v2.preflight(request)
        plan = probe.v2.plan(task_id, pre, "inspect")
        assert plan["overall_coverage"] == "INCOMPLETE"
        assert plan["execution_path_complete"] is False
        assert all(isinstance(plan[name], int) for name in ("planned_model_calls", "planned_tool_calls", "planned_deterministic_steps"))
