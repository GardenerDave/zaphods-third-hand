from __future__ import annotations

import json
from pathlib import Path

from local_harness.supervised_capability_loop import load_task_fixture, _validator_result
from local_harness.supervised_reference_fact_validator import REFERENCE_FACT_SPECS


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "local_harness/fixtures/capability_loop/reviewed_v2"


def test_reviewed_v2_pack_is_fresh_bounded_and_balanced():
    paths = sorted(PACK.glob("*.json"))
    tasks = [load_task_fixture(path) for path in paths]
    assert len(tasks) == 20
    assert len({task["task_id"] for task in tasks}) == 20
    assert not any(task["task_id"].startswith("capability-reviewed-") for task in tasks)
    families = {task["task_family"] for task in tasks}
    assert len(families) >= 5
    assert max(sum(task["task_family"] == family for task in tasks) for family in families) <= 6
    assert all(task["provenance"].get("novelty") in {"new_source", "new_scenario_same_family"} for task in tasks)
    serialized = json.dumps(tasks, sort_keys=True).lower()
    assert "automatic patch promotion authority granted" not in serialized
    assert "automatic training authority granted" not in serialized
    assert "execution authority granted" not in serialized


def test_reviewed_v2_semantics_are_registered_and_contract_satisfiable():
    for path in sorted(PACK.glob("*.json")):
        task = load_task_fixture(path)
        fields = set(task["output_contract"]["required_fields"])
        for key, value in task["validator"].get("reference_facts", {}).items():
            spec = REFERENCE_FACT_SPECS[key]
            assert not spec.source_metadata
            if spec.alternative_output_fields:
                assert set(spec.alternative_output_fields) & fields
            elif spec.fields_from_value:
                assert set(value) <= fields
            else:
                assert set(spec.required_output_fields) <= fields
        for key in task.get("source_expectations", {}):
            assert REFERENCE_FACT_SPECS[key].source_metadata


def test_reviewed_v2_fixtures_have_a_simultaneously_satisfiable_representative():
    for path in sorted(PACK.glob("*.json")):
        task = load_task_fixture(path)
        facts = task["validator"].get("reference_facts", {})
        fields = task["output_contract"]["required_fields"]
        output = {field: [] if field in {"allowed_targets", "held_targets", "diagnostics"} else False if field == "scope_expansion_required" else f"review-only {field}" for field in fields}
        for key, value in facts.items():
            if key == "required_allowed_targets": output["allowed_targets"] = list(value)
            elif key == "required_held_targets": output["held_targets"] = list(value)
            elif key == "forbidden_allowed_targets": output["allowed_targets"] = [item for item in output.get("allowed_targets", []) if item not in value]
            elif key == "requires_scope_expansion_flag": output["scope_expansion_required"] = value
            elif key in {"required_packet_schema", "required_review_required", "review_schema", "queue_handoff_status", "repo_mutation_status", "review_status"}: output[key] = value
            elif key == "source_review_status": output["review_status"] = value
            elif key == "expected_review_status": output["status"] = value
            elif key in {"diagnostic_substrings", "required_inspection_commands"}: output["diagnostics" if key == "diagnostic_substrings" else "inspection_sequence"] = list(value)
        phrases = []
        for key, value in facts.items():
            if key in {"must_include", "must_preserve", "required_inspection_commands", "diagnostic_substrings"}: phrases.extend(value)
            elif key in {"dependency_research", "uncertainty", "priority_conflict", "training_capture", "unsafe_cleanup"}: phrases.extend([key.replace("_", " "), str(value)])
            elif key == "destructive_action_requires_review" and value is True: phrases.extend(["human review", "held", "do not execute"])
        direct_fields = {"packet_schema", "review_required", "scope_expansion_required", "review_schema", "queue_handoff_status", "repo_mutation_status", "review_status", "status"}
        for field in fields:
            if field not in direct_fields and field not in {"allowed_targets", "held_targets", "diagnostics"} and isinstance(output.get(field), str):
                output[field] = "; ".join(phrases + [output[field]])
        if "diagnostics" in output:
            output["diagnostics"].extend(phrases)
        result = _validator_result(json.dumps(output), task, attempt_id="reviewed-v2-satisfiability")
        assert result["validation_status"] == "passed", (path.name, result["diagnostics"])
