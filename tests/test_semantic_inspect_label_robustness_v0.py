import json
from pathlib import Path

from scripts import semantic_inspect_label_robustness_v0 as probe


def test_fresh_holdout_is_interleaved_and_true_fallback_eligible():
    assert [expected for _, expected, _ in probe.specs()] == ["observe_presence", "inspect"] * 6
    historical = probe.historical_requests()
    for task_id, _, request in probe.specs():
        assert request not in historical
        pre = probe.base_v2.preflight(request)
        assert pre["semantic_fallback_eligible"] is True
        assert pre["model_required"] is True
        assert pre["remaining_candidate_operation_classes"] == ["observe_presence", "inspect"]


def test_only_inspect_surface_label_varies_and_positions_are_constant():
    assert probe.LABELS == {
        "A": {"presence": "observe_presence", "inspect": "inspect"},
        "B": {"presence": "observe_presence", "inspect": "class_beta"},
        "C": {"presence": "observe_presence", "inspect": "operation_two"},
        "D": {"presence": "observe_presence", "inspect": "examine_target"},
    }
    assert [probe.ENUMS[arm][1] for arm in "ABCD"] == ["observe_presence"] * 4
    assert [probe.CANONICAL[arm][probe.LABELS[arm]["inspect"]] for arm in "ABCD"] == ["inspect"] * 4


def test_prompt_definitions_normalize_identically():
    request = probe.specs()[0][2]
    assert len({probe.normalized_prompt(probe.prompt(request, arm), arm) for arm in "ABCD"}) == 1


def test_runtime_authority_is_shared_and_answer_key_free():
    cases = probe.runtime_cases()
    assert all(set(case) == {"task_id", "input_request", "environment_facts"} for case in cases)
    assert all(case["environment_facts"]["authority_record"]["allowed_observation_operations"] == ["observe_presence", "inspect"] for case in cases)
    assert all(not any(key.startswith("expected_") for key in case) for case in cases)


def test_strict_surface_label_mapping_and_unresolved_fail_closed():
    for arm in "ABCD":
        for label, canonical in probe.CANONICAL[arm].items():
            candidate, parse_valid, contract_valid, _ = probe.parse_response(json.dumps({"operation_class_candidate": label}), arm)
            result = probe.validate_and_map(candidate, arm, parse_valid, contract_valid)
            assert result["candidate_valid"] is True
            assert result["candidate_admissible"] is True
            assert result["canonical_operation"] == canonical
        candidate, parse_valid, contract_valid, _ = probe.parse_response('{"operation_class_candidate":"unresolved"}', arm)
        result = probe.validate_and_map(candidate, arm, parse_valid, contract_valid)
        assert result["candidate_valid"] is True
        assert result["candidate_admissible"] is False
        assert result["canonical_operation"] is None


def test_class_stratified_schedule_and_prepared_artifact():
    task_ids = [task_id for task_id, _, _ in probe.specs()]
    order = probe.schedule(task_ids)
    audit = probe.schedule_audit(order, task_ids)
    assert len(order) == 48
    assert all(sum(item["arm"] == arm for item in order) == 12 for arm in "ABCD")
    assert audit["class_stratified_balance"] is True
    for strata in audit["strata_positions"].values():
        for positions in strata.values():
            counts = {position: positions.count(position) for position in range(1, 5)}
            assert max(counts.values()) - min(counts.values()) <= 1
    prepared = json.loads((Path(probe.RUN) / "execution_order.json").read_text(encoding="utf-8"))
    assert prepared["schedule"] == order


def test_prepared_freeze_has_zero_calls_and_no_responses():
    run = Path(probe.RUN)
    manifest = json.loads((run / "router_manifest.json").read_text(encoding="utf-8"))
    lifecycle = json.loads((run / "lifecycle.json").read_text(encoding="utf-8"))
    assert manifest["planned_model_calls"] == 48
    assert manifest["true_fallback_eligibility"] == 12
    assert lifecycle["model_calls"] == 0
    assert lifecycle["tool_calls"] == 0
    assert len(list(run.rglob("response.json"))) == 0


def test_evaluator_mutation_changes_score_but_not_runtime_inputs():
    observed = [{"task_id": "silr-001", "canonical_operation": "observe_presence"}]
    evaluator = [{"task_id": "silr-001", "expected_semantic_class": "observe_presence"}]
    corrupted = [{"task_id": "silr-001", "expected_semantic_class": "inspect"}]
    assert probe.score_rows(observed, evaluator)[0]["semantic_correct"] is True
    assert probe.score_rows(observed, corrupted)[0]["semantic_correct"] is False
    runtime = probe.runtime_cases()[0]
    assert "expected_semantic_class" not in runtime
