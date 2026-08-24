from scripts import semantic_label_counterfactual_v0 as probe


def test_fresh_tasks_are_interleaved_and_true_fallback_eligible():
    rows = probe.specs()
    assert [expected for _, expected, _ in rows] == ["observe_presence", "inspect", "observe_presence", "inspect", "observe_presence", "inspect"]
    historical = probe.historical_requests()
    for task_id, _, request in rows:
        pre = probe.base_v2.preflight(request)
        assert request not in historical
        assert pre["semantic_fallback_eligible"] is True
        assert pre["model_required"] is True
        assert pre["remaining_candidate_operation_classes"] == ["observe_presence", "inspect"]


def test_current_and_neutral_labels_have_constant_semantic_positions():
    assert probe.ARM_ENUMS["A"] == ["inspect", "observe_presence", "unresolved"]
    assert probe.ARM_ENUMS["B"] == ["class_beta", "class_alpha", "unresolved"]
    assert probe.ARM_CANONICAL["A"] == {"observe_presence": "observe_presence", "inspect": "inspect"}
    assert probe.ARM_CANONICAL["B"] == {"class_alpha": "observe_presence", "class_beta": "inspect"}


def test_definition_text_is_identical_after_label_substitution():
    request = probe.specs()[0][2]
    assert probe.normalized_prompt(probe.prompt(request, "A"), "A") == probe.normalized_prompt(probe.prompt(request, "B"), "B")


def test_runtime_authority_is_shared_and_answer_key_free():
    cases = probe.runtime_cases()
    assert all(set(case) == {"task_id", "input_request", "environment_facts"} for case in cases)
    assert all(case["environment_facts"]["authority_record"]["allowed_observation_operations"] == ["observe_presence", "inspect"] for case in cases)
    assert all(not any(key.startswith("expected_") for key in case) for case in cases)


def test_strict_parsing_and_neutral_mapping():
    assert probe.parse_response('{"operation_class_candidate":"inspect"}', "A")[2]
    assert probe.parse_response('{"operation_class_candidate":"class_alpha"}', "B")[2]
    assert not probe.parse_response('{"operation_class_candidate":"observe_presence"}', "B")[2]
    assert not probe.parse_response('{"operation_class_candidate":"class_alpha","extra":1}', "B")[2]


def test_exact_counterbalanced_order():
    ids = [task_id for task_id, _, _ in probe.specs()]
    assert probe.paired_execution_order(ids) == [
        {"task_id": "slcf-001", "arm": "A"}, {"task_id": "slcf-001", "arm": "B"},
        {"task_id": "slcf-002", "arm": "B"}, {"task_id": "slcf-002", "arm": "A"},
        {"task_id": "slcf-003", "arm": "A"}, {"task_id": "slcf-003", "arm": "B"},
        {"task_id": "slcf-004", "arm": "B"}, {"task_id": "slcf-004", "arm": "A"},
        {"task_id": "slcf-005", "arm": "A"}, {"task_id": "slcf-005", "arm": "B"},
        {"task_id": "slcf-006", "arm": "B"}, {"task_id": "slcf-006", "arm": "A"},
    ]
