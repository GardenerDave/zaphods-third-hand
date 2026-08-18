import json
from pathlib import Path

from local_harness.supervised_capability_loop import load_task_fixture
from local_harness.supervised_reference_fact_validator import REFERENCE_FACT_SPECS, validate_reference_facts


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "local_harness/fixtures/capability_loop/reviewed_v1"


def test_reviewed_capability_pack_is_bounded_and_loadable():
    paths = sorted(PACK.glob("*.json"))
    tasks = [load_task_fixture(path) for path in paths]

    assert 20 <= len(tasks) <= 40
    assert len({task["task_id"] for task in tasks}) == len(tasks)
    assert all(task["validator"]["kind"] == "zth_output_contract" for task in tasks)
    assert all(isinstance(task.get("provenance"), dict) and task["provenance"] for task in tasks)
    assert all(task["output_contract"].get("format") == "json" for task in tasks)

    serialized = json.dumps(tasks, sort_keys=True).lower()
    assert "automatic patch promotion authority granted" not in serialized
    assert "automatic training authority granted" not in serialized
    assert "execution authority granted" not in serialized


def test_reviewed_pack_reference_facts_are_all_registered():
    tasks = [load_task_fixture(path) for path in sorted(PACK.glob("*.json"))]
    keys = {key for task in tasks for key in task["validator"].get("reference_facts", {})}
    assert keys
    assert keys <= set(REFERENCE_FACT_SPECS)


def test_reviewed_pack_reference_facts_are_satisfiable_by_contracts():
    tasks = [load_task_fixture(path) for path in sorted(PACK.glob("*.json"))]
    for task in tasks:
        contract_fields = set(task["output_contract"].get("required_fields", []))
        for key, value in task["validator"].get("reference_facts", {}).items():
            spec = REFERENCE_FACT_SPECS[key]
            assert not spec.source_metadata
            if spec.alternative_output_fields:
                assert set(spec.alternative_output_fields) & contract_fields, (task["task_id"], key)
            elif spec.fields_from_value:
                assert set(value) <= contract_fields, (task["task_id"], key, value)
            else:
                assert set(spec.required_output_fields) <= contract_fields, (task["task_id"], key)
            if spec.evaluator_class == "content_semantic":
                assert task["output_contract"].get("format") == "json"
                assert contract_fields

        for key in task.get("source_expectations", {}):
            assert key in REFERENCE_FACT_SPECS
            assert REFERENCE_FACT_SPECS[key].source_metadata


def test_reference_fact_evaluator_golden_shapes():
    direct = validate_reference_facts('{"packet_schema":"messy_input_triage_packet_v1"}', {"required_packet_schema": "messy_input_triage_packet_v1"})
    aliased = validate_reference_facts('{"scope_expansion_required":false}', {"requires_scope_expansion_flag": False})
    content = validate_reference_facts('{"reason":"human review; do not execute"}', {"must_include": ["human review", "do not execute"]})
    source = validate_reference_facts('{"answer":"ok"}', {"source_expected_validation_status": "passed"})
    assert direct["validation_status"] == "passed"
    assert aliased["validation_status"] == "passed"
    assert content["validation_status"] == "passed"
    assert source["validation_status"] == "passed" and source["checks"] == []
