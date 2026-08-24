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
    assert schedule == probe.EXPECTED_SCHEDULE
    assert all(sum(item["arm"] == arm for item in schedule) == 6 for arm in ("A", "B", "C", "D"))
    for position in range(4):
        counts = {arm: sum(schedule[index * 4 + position]["arm"] == arm for index in range(6)) for arm in ("A", "B", "C", "D")}
        assert sorted(counts.values()) == [1, 1, 2, 2]


def test_class_stratified_positions_are_unique_within_each_semantic_class():
    audit = probe.schedule_audit(probe.execution_schedule([row[0] for row in probe.specs()]), [row[0] for row in probe.specs()])
    assert audit["within_class_position_balance"] is True
    assert audit["strata_positions"]["presence"] == {"A": [1, 3, 4], "B": [1, 2, 4], "C": [1, 2, 3], "D": [2, 3, 4]}
    assert audit["strata_positions"]["inspect"] == {"A": [2, 3, 4], "B": [1, 2, 3], "C": [1, 2, 4], "D": [1, 3, 4]}


def test_prepared_execution_order_artifact_is_exactly_class_stratified():
    import json
    from pathlib import Path

    prepared = Path(probe.RUN) / "execution_order.json"
    assert json.loads(prepared.read_text(encoding="utf-8"))["schedule"] == probe.EXPECTED_SCHEDULE


def test_evaluator_manifest_is_the_closeout_scoring_authority():
    runtime_rows = [{"task_id": "slff-001", "arm": "A", "canonical_operation": "observe_presence", "parse_valid": True, "contract_valid": True, "candidate_valid": True, "candidate_admissible": True}]
    evaluator = [{"task_id": "slff-001", "expected_semantic_class": "observe_presence"}]
    assert probe.score_rows(runtime_rows, evaluator)[0]["semantic_correct"] is True
    evaluator[0]["expected_semantic_class"] = "inspect"
    assert probe.score_rows(runtime_rows, evaluator)[0]["semantic_correct"] is False


def test_factorial_metrics_keep_presence_and_inspect_denominators_visible():
    rows = []
    for arm in ("A", "B", "C", "D"):
        rows.extend([
            {"task_id": "slff-001", "arm": arm, "expected": "observe_presence", "canonical_operation": "observe_presence", "semantic_correct": True, "parse_valid": True, "contract_valid": True, "candidate_valid": True, "candidate_admissible": True},
            {"task_id": "slff-002", "arm": arm, "expected": "inspect", "canonical_operation": "inspect", "semantic_correct": True, "parse_valid": True, "contract_valid": True, "candidate_valid": True, "candidate_admissible": True},
        ])
    metrics = probe.arm_metrics(rows)
    assert all(metrics[arm]["presence_total"] == 1 and metrics[arm]["inspect_total"] == 1 for arm in ("A", "B", "C", "D"))


def test_factorial_contrasts_distinguish_presence_main_effect_from_interaction():
    contrasts = probe.factorial_contrasts_from_rates({"A": 0.5, "B": 1.0, "C": 1.0, "D": 0.5})
    assert contrasts["presence_label_main_effect"] == 0.5
    assert contrasts["inspect_label_main_effect"] == 0.0
    assert contrasts["label_interaction_contrast"] == 0.0
    assert probe.factorial_pattern_markers({"A": 0.5, "B": 1.0, "C": 1.0, "D": 0.5})["LABEL_INTERACTION_EFFECT_PLAUSIBLE"] is False


def test_factorial_contrasts_distinguish_inspect_main_effect():
    contrasts = probe.factorial_contrasts_from_rates({"A": 0.5, "B": 1.0, "C": 0.5, "D": 1.0})
    assert contrasts["presence_label_main_effect"] == 0.0
    assert contrasts["inspect_label_main_effect"] == 0.5
    assert contrasts["label_interaction_contrast"] == 0.0


def test_factorial_contrasts_identify_joint_only_recovery():
    contrasts = probe.factorial_contrasts_from_rates({"A": 0.5, "B": 1.0, "C": 0.5, "D": 0.5})
    markers = probe.factorial_pattern_markers({"A": 0.5, "B": 1.0, "C": 0.5, "D": 0.5})
    assert contrasts["label_interaction_contrast"] == 0.5
    assert markers["JOINT_NEUTRAL_LABEL_DEPENDENCE_OBSERVED"] is True
    assert markers["LABEL_INTERACTION_EFFECT_PLAUSIBLE"] is True


def test_two_single_label_recoveries_are_not_pair_interaction():
    markers = probe.factorial_pattern_markers({"A": 0.5, "B": 1.0, "C": 1.0, "D": 1.0})
    assert markers["JOINT_NEUTRAL_LABEL_DEPENDENCE_OBSERVED"] is False
    assert "ORIGINAL_LABEL_PAIR_INTERACTION_SUPPORTED" not in markers
