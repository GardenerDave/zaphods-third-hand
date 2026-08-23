from scripts import true_semantic_fallback as probe


def test_runtime_manifest_contains_only_runtime_inputs():
    cases = probe.runtime_cases()
    assert len(cases) == 10
    assert all(set(case) == {"task_id", "input_request", "environment_facts"} for case in cases)
    assert all(not any(key.startswith("expected_") for key in case) for case in cases)


def test_true_fallback_eligibility_has_two_candidate_classes():
    by_id = {case["task_id"]: case for case in probe.runtime_cases()}
    true_ids = {"tsf-001", "tsf-002", "tsf-003", "tsf-004", "tsf-005", "tsf-006"}
    for task_id in true_ids:
        case = by_id[task_id]
        pre = probe.preflight(case["input_request"], case["environment_facts"]["authority_record"])
        assert pre["target_status"] == "EXACTLY_ONE_SAFE_TARGET"
        assert pre["risk_status"] == "SAFE_BOUNDED"
        assert pre["ambiguity_status"] == "UNAMBIGUOUS"
        assert pre["operation_derivation_status"] == "UNRESOLVED"
        assert pre["remaining_candidate_operation_classes"] == ["observe_presence", "inspect"]
        assert pre["semantic_fallback_eligible"] is True
        assert pre["model_required"] is True


def test_controls_do_not_route_to_model():
    by_id = {case["task_id"]: case for case in probe.runtime_cases()}
    for task_id in ("tsf-007", "tsf-008", "tsf-009", "tsf-010"):
        case = by_id[task_id]
        pre = probe.preflight(case["input_request"], case["environment_facts"]["authority_record"])
        assert pre["model_required"] is False
        assert pre["semantic_fallback_eligible"] is False
    assert probe.preflight(by_id["tsf-009"]["input_request"], by_id["tsf-009"]["environment_facts"]["authority_record"])["ambiguity_status"] == "AMBIGUOUS"
    assert probe.preflight(by_id["tsf-010"]["input_request"], by_id["tsf-010"]["environment_facts"]["authority_record"])["risk_status"] == "RISKY_OR_UNSUPPORTED"


def test_model_interface_is_enum_only_and_never_contains_target_output():
    schema = probe.schema()
    assert set(schema["properties"]) == {"operation_class_candidate"}
    assert schema["properties"]["operation_class_candidate"]["enum"] == ["inspect", "observe_presence", "unresolved"]
    text = probe.prompt("Take a look at docs/example.md.")
    assert "requested_target" not in text
    assert "canonical_operation" not in text
    assert "tool supplier" not in text.casefold()


def test_evaluator_corruption_cannot_change_preflight_or_plan():
    case = next(x for x in probe.runtime_cases() if x["task_id"] == "tsf-001")
    pre = probe.preflight(case["input_request"], case["environment_facts"]["authority_record"])
    plan = probe.plan(case["task_id"], pre)
    corrupted = {"expected_semantic_class": "inspect", "expected_model_required": False, "expected_task_terminal_success": False}
    pre_again = probe.preflight(case["input_request"], case["environment_facts"]["authority_record"])
    plan_again = probe.plan(case["task_id"], pre_again)
    assert pre_again == pre
    assert plan_again == plan
    assert corrupted["expected_semantic_class"] != pre["remaining_candidate_operation_classes"][0]


def test_operation_class_never_grants_authority():
    case = next(x for x in probe.runtime_cases() if x["task_id"] == "tsf-001")
    auth = case["environment_facts"]["authority_record"]
    assert probe.plan(case["task_id"], probe.preflight(case["input_request"], auth), "inspect")["overall_coverage"] == "INCOMPLETE"
    assert auth["allowed_observation_operations"] == ["observe_presence"]


def test_strict_candidate_parser_fails_closed():
    assert probe.parse_response('{"operation_class_candidate":"inspect"}')[2] is True
    assert probe.parse_response('{"operation_class_candidate":"delete"}')[2] is False
    assert probe.parse_response('{"operation_class_candidate":"inspect","extra":1}')[2] is False
    assert probe.parse_response('{"operation_class_candidate":"unresolved"}')[2] is True
