from scripts import true_semantic_fallback_v2 as probe
from scripts import zth_qwen3_0_6b_clean_scope_logic_probe as telemetry_provider


def test_v2_fresh_interleaved_matrix_and_no_v1_reuse():
    specs = probe.fixture_specs()
    assert len(specs) == 10
    assert [row[3] for row in specs[:6]] == ["observe_presence", "inspect", "observe_presence", "inspect", "observe_presence", "inspect"]
    assert not any("tsfv1" in request for _, _, request, _ in specs)
    v1_requests = {case["input_request"] for case in probe.read_json(probe.V1_RUNTIME)["cases"]}
    assert not any(request in v1_requests for _, _, request, _ in specs)


def test_v2_runtime_cases_are_answer_key_free_and_semantic_authority_is_shared():
    cases = probe.runtime_cases()
    assert all(set(case) == {"task_id", "input_request", "environment_facts"} for case in cases)
    semantic = cases[:6]
    assert all(case["environment_facts"]["authority_record"]["allowed_observation_operations"] == ["observe_presence", "inspect"] for case in semantic)
    assert all(not any(key.startswith("expected_") for key in case) for case in cases)


def test_v2_true_fallback_eligibility_is_six_of_six_and_controls_are_model_free():
    cases = {case["task_id"]: case for case in probe.runtime_cases()}
    for task_id in [f"tsfv2-{i:03d}" for i in range(1, 7)]:
        pre = probe.preflight(cases[task_id]["input_request"])
        assert pre["semantic_fallback_eligible"] is True
        assert pre["model_required"] is True
        assert pre["deterministic_canonical_operation_available_pre_model"] is False
        assert pre["remaining_candidate_operation_classes"] == ["observe_presence", "inspect"]
    for task_id in [f"tsfv2-{i:03d}" for i in range(7, 11)]:
        pre = probe.preflight(cases[task_id]["input_request"])
        assert pre["model_required"] is False
        assert probe.plan(task_id, pre)["planned_model_calls"] == 0


def test_v2_optional_supplier_counts_are_integer_safe():
    records = [{"selected_supplier": {"supplier_type": "MODEL"}}, {"selected_supplier": {"supplier_type": "TOOL"}}, {"selected_supplier": {"supplier_type": "DETERMINISTIC_CODE"}}, {"selected_supplier": None}]
    assert probe.supplier_counts(records) == {"planned_model_calls": 1, "planned_tool_calls": 1, "planned_deterministic_steps": 1}
    inspect_case = next(case for case in probe.runtime_cases() if case["task_id"] == "tsfv2-002")
    inspect_plan = probe.plan("tsfv2-002", probe.preflight(inspect_case["input_request"]), "inspect")
    assert inspect_plan["overall_coverage"] == "INCOMPLETE"
    assert inspect_plan["execution_path_complete"] is False
    assert all(isinstance(inspect_plan[key], int) for key in ("planned_model_calls", "planned_tool_calls", "planned_deterministic_steps"))


def test_v2_telemetry_provider_exports_required_helpers_directly():
    assert callable(telemetry_provider.telemetry_base_url)
    assert callable(telemetry_provider.telemetry_preflight)


def test_v2_strict_enum_interface_is_unchanged_baseline_shape():
    assert probe.schema()["required"] == ["operation_class_candidate"]
    assert probe.parse_response('{"operation_class_candidate":"inspect"}')[2] is True
    assert probe.parse_response('{"operation_class_candidate":"observe_presence"}')[2] is True
    assert probe.parse_response('{"operation_class_candidate":"inspect","target":"x"}')[2] is False


def test_v2_leakage_audit_has_no_runtime_answer_channels():
    rows = probe.leakage_audit(probe.runtime_cases(), probe.evaluator_cases())
    assert all(not row["target_semantic_label_leak"] for row in rows)
    assert all(not row["runtime_authority_class_leak"] for row in rows[:6])
    assert all(not row["runtime_regime_label_present"] for row in rows)
    assert all(not row["evaluator_fields_present"] for row in rows)
    assert all(not row["task_id_class_leak"] for row in rows)


def test_v2_request_target_mutation_does_not_mutate_independent_authority():
    original = next(case for case in probe.runtime_cases() if case["task_id"] == "tsfv2-001")
    mutated = dict(original, input_request="Could you tell me whether docs/research/V2_OTHER_2026-08-23.md is part of this repository?")
    assert probe.preflight(mutated["input_request"])["target"] != probe.authority_record("tsfv2-001")["allowed_targets"][0]
    assert mutated["environment_facts"]["authority_record"] == original["environment_facts"]["authority_record"]


def test_v2_request_operation_mutation_does_not_mutate_independent_authority():
    original = next(case for case in probe.runtime_cases() if case["task_id"] == "tsfv2-007")
    mutated = dict(original, input_request="Inspect docs/research/V2_HARBOR_2026-08-23.py.")
    assert mutated["environment_facts"]["authority_record"] == original["environment_facts"]["authority_record"]


def test_v2_target_authority_denies_before_stubbed_observer_actuation():
    case = probe.authority_record("tsfv2-001")
    calls = []
    result, _, _, _, count = __import__("scripts.deterministic_first_confirmation", fromlist=["execute_read_only_observation"]).execute_read_only_observation(
        "observe_presence", "docs/research/V2_OTHER_2026-08-23.md", case, observer=lambda *_: calls.append(True)
    )
    assert result["status"] == "TARGET_AUTHORITY_DENIED"
    assert count == 0
    assert calls == []
