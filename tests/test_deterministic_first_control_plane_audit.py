from scripts import audit_deterministic_first_control_plane as audit
from scripts import zth_deterministic_first_semantic_fallback as probe


def test_historical_audit_detects_evaluator_derived_authority_without_calls():
    result = audit.audit()
    assert result["runtime_expected_field_direct_reads"] == 0
    assert result["evaluator_derived_runtime_authority"] is True
    assert result["oracle_free_runtime_authority_demonstrated"] is False
    assert result["authority_value_correctness_not_disputed"] is True
    assert result["summary"]["no_call_audit_model_calls"] == 0
    assert result["summary"]["no_call_audit_tool_calls"] == 0


def test_historical_audit_separates_routing_from_actual_execution():
    result = audit.audit()
    assert result["non_observation_operations_terminated_without_actuation"] is True
    assert result["end_to_end_task_completion_demonstrated"] is False
    assert result["summary"]["operation_actually_executed"] == 4
    assert result["summary"]["task_terminal_success"] == 4


def test_corrupting_evaluator_values_changes_only_historical_authority_derivation():
    original = probe.runtime_task(probe.tasks()[0])
    corrupted = probe.runtime_task({**probe.tasks()[0], "expected_requested_target":"corrupted.md", "expected_authority_operations":["delete"]})
    assert original["environment_facts"]["authority_record"] != corrupted["environment_facts"]["authority_record"]
    assert audit.audit()["evaluator_derived_runtime_authority"] is True
