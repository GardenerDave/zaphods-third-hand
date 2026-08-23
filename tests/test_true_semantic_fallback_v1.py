from scripts import true_semantic_fallback_v1 as probe


def test_v1_runtime_cases_are_oracle_clean_and_authority_is_shared():
    cases = probe.runtime_cases()
    assert len(cases) == 10
    assert all(set(x) == {"task_id", "input_request", "environment_facts"} for x in cases)
    assert all(x["environment_facts"]["authority_record"]["allowed_observation_operations"] == ["observe_presence", "inspect"] for x in cases)
    assert all(not any(k.startswith("expected_") for k in x) for x in cases)


def test_v1_target_names_do_not_predict_semantic_class():
    cases, evaluators = probe.runtime_cases(), probe.evaluator_cases()
    rows = probe.leakage_audit(cases, evaluators)
    assert all(not x["target_semantic_label_leak"] for x in rows)
    assert all(not x["runtime_authority_class_leak"] for x in rows)
    assert all(not x["runtime_regime_label_present"] for x in rows)
    assert all(not x["evaluator_fields_present"] for x in rows)
    assert all(x["prompt_classification_specification_allowed"] for x in rows)


def test_v1_true_fallback_eligibility_is_six_of_six():
    cases = {x["task_id"]: x for x in probe.runtime_cases()}
    for task_id in ("tsfv1-001", "tsfv1-002", "tsfv1-003", "tsfv1-004", "tsfv1-005", "tsfv1-006"):
        pre = probe.preflight(cases[task_id]["input_request"])
        assert pre["target_status"] == "EXACTLY_ONE_SAFE_TARGET"
        assert pre["risk_status"] == "SAFE_BOUNDED"
        assert pre["ambiguity_status"] == "UNAMBIGUOUS"
        assert pre["operation_derivation_status"] == "UNRESOLVED"
        assert pre["remaining_candidate_operation_classes"] == ["observe_presence", "inspect"]
        assert pre["semantic_fallback_eligible"] is True
        assert pre["model_required"] is True


def test_v1_controls_plan_zero_model_calls():
    cases = {x["task_id"]: x for x in probe.runtime_cases()}
    for task_id in ("tsfv1-007", "tsfv1-008", "tsfv1-009", "tsfv1-010"):
        pre = probe.preflight(cases[task_id]["input_request"])
        assert pre["model_required"] is False
        assert probe.plan(task_id, pre)["planned_model_calls"] == 0
    assert probe.preflight(cases["tsfv1-009"]["input_request"])["ambiguity_status"] == "AMBIGUOUS"
    assert probe.preflight(cases["tsfv1-010"]["input_request"])["risk_status"] == "RISKY_OR_UNSUPPORTED"


def test_v1_evaluator_class_corruption_does_not_change_runtime_inputs_or_plans():
    cases = probe.runtime_cases()
    before = [(x["task_id"], probe.preflight(x["input_request"]), probe.plan(x["task_id"], probe.preflight(x["input_request"]))) for x in cases]
    corrupted = [{"task_id": x["task_id"], "expected_semantic_class": "inspect"} for x in probe.evaluator_cases()]
    after = [(x["task_id"], probe.preflight(x["input_request"]), probe.plan(x["task_id"], probe.preflight(x["input_request"]))) for x in cases]
    assert before == after
    assert corrupted != probe.evaluator_cases()


def test_v1_model_interface_has_one_enum_field_and_strict_parse():
    assert set(probe.schema()["properties"]) == {"operation_class_candidate"}
    assert probe.parse_response('{"operation_class_candidate":"inspect"}')[2] is True
    assert probe.parse_response('{"operation_class_candidate":"observe_presence"}')[2] is True
    assert probe.parse_response('{"operation_class_candidate":"delete"}')[2] is False
    assert probe.parse_response('{"operation_class_candidate":"inspect","target":"x"}')[2] is False


def test_v1_neutral_target_extensions_are_balanced():
    by_class = {"observe_presence": [], "inspect": []}
    for task_id, regime, request, operation in probe.fixture_specs()[:6]:
        by_class[operation].append(request.rsplit(".", 1)[-1])
    assert len(by_class["observe_presence"]) == len(by_class["inspect"]) == 3
