from scripts import semantic_label_factorial_v0 as probe


def test_fresh_interleaved_tasks_are_true_fallback_eligible():
    assert [expected for _, expected, _ in probe.specs()] == ["observe_presence", "inspect", "observe_presence", "inspect", "observe_presence", "inspect"]
    historical = probe.historical_requests()
    for task_id, _, request in probe.specs():
        pre = probe.base_v2.preflight(request)
        assert request not in historical
        assert pre["semantic_fallback_eligible"] is True
        assert pre["model_required"] is True


def test_four_arm_mappings_and_constant_semantic_positions():
    assert probe.ARM_ENUMS == {
        "A": ["inspect", "observe_presence", "unresolved"],
        "B": ["class_beta", "class_alpha", "unresolved"],
        "C": ["inspect", "class_alpha", "unresolved"],
        "D": ["class_beta", "observe_presence", "unresolved"],
    }
    for arm in ("A", "B", "C", "D"):
        assert probe.ARM_CANONICAL[arm][probe.ARM_LABELS[arm]["presence"]] == "observe_presence"
        assert probe.ARM_CANONICAL[arm][probe.ARM_LABELS[arm]["inspect"]] == "inspect"


def test_prompt_definitions_normalize_identically_across_all_arms():
    request = probe.specs()[0][2]
    normalized = {probe.normalized_prompt(probe.prompt(request, arm), arm) for arm in ("A", "B", "C", "D")}
    assert len(normalized) == 1


def test_runtime_authority_is_shared_and_answer_key_free():
    cases = probe.runtime_cases()
    assert all(set(case) == {"task_id", "input_request", "environment_facts"} for case in cases)
    assert all(case["environment_facts"]["authority_record"]["allowed_observation_operations"] == ["observe_presence", "inspect"] for case in cases)
    assert all(not any(key.startswith("expected_") for key in case) for case in cases)


def test_arm_relative_candidate_mapping_is_strict():
    for arm in ("A", "B", "C", "D"):
        for surface, canonical in probe.ARM_CANONICAL[arm].items():
            candidate, parse_valid, contract_valid, _ = probe.parse_response('{"operation_class_candidate":"' + surface + '"}', arm)
            result = probe.validate_and_map_candidate(candidate, arm, parse_valid, contract_valid)
            assert result["candidate_valid"] is True
            assert result["candidate_admissible"] is True
            assert result["canonical_operation"] == canonical
        candidate, parse_valid, contract_valid, _ = probe.parse_response('{"operation_class_candidate":"unresolved"}', arm)
        result = probe.validate_and_map_candidate(candidate, arm, parse_valid, contract_valid)
        assert result["candidate_valid"] is True
        assert result["candidate_admissible"] is False
        assert result["canonical_operation"] is None


def test_latin_style_schedule_has_24_calls_and_balanced_positions():
    schedule = probe.execution_schedule([row[0] for row in probe.specs()])
    assert len(schedule) == 24
    assert all(sum(item["arm"] == arm for item in schedule) == 6 for arm in ("A", "B", "C", "D"))
    for position in range(4):
        counts = {arm: sum(schedule[index * 4 + position]["arm"] == arm for index in range(6)) for arm in ("A", "B", "C", "D")}
        assert sorted(counts.values()) == [1, 1, 2, 2]
