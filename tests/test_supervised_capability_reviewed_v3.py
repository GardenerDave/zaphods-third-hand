from __future__ import annotations

import json
from pathlib import Path

from local_harness.supervised_capability_loop import _validator_result, load_task_fixture
from local_harness.supervised_reference_fact_validator import REFERENCE_FACT_SPECS


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "local_harness/fixtures/capability_loop/reviewed_v3"


def _fixture_paths() -> list[Path]:
    return sorted(path for path in PACK.glob("*.json") if path.name != "manifest.json")


def _representative(task: dict) -> dict:
    fields = task["output_contract"]["required_fields"]
    list_fields = {"allowed_targets", "held_targets", "diagnostics", "unverified_claims"}
    output = {field: [] if field in list_fields else False if field == "scope_expansion_required" else True if field == "review_required" else f"review-only {field}" for field in fields}
    facts = task["validator"].get("reference_facts", {})
    for key, value in facts.items():
        if key == "required_allowed_targets": output["allowed_targets"] = list(value)
        elif key == "required_held_targets": output["held_targets"] = list(value)
        elif key == "forbidden_allowed_targets": output["allowed_targets"] = [item for item in output.get("allowed_targets", []) if item not in value]
        elif key == "requires_scope_expansion_flag": output["scope_expansion_required"] = value
        elif key == "required_packet_schema": output["packet_schema"] = value
        elif key == "required_review_required": output["review_required"] = value
        elif key in {"review_schema", "queue_handoff_status", "repo_mutation_status", "review_status"}: output[key] = value
        elif key == "source_review_status": output["review_status"] = value
        elif key == "expected_review_status": output["status"] = value
    phrases = []
    for key, value in facts.items():
        if key in {"must_include", "must_preserve", "required_inspection_commands", "diagnostic_substrings"}: phrases.extend(value)
        elif key in {"dependency_research", "uncertainty", "priority_conflict", "training_capture", "unsafe_cleanup"}: phrases.extend([key.replace("_", " "), str(value)])
        elif key == "destructive_action_requires_review" and value is True: phrases.extend(["human review", "held", "do not execute"])
    direct_fields = {"packet_schema", "review_required", "scope_expansion_required", "review_schema", "queue_handoff_status", "repo_mutation_status", "review_status", "status"}
    for field in fields:
        if field not in direct_fields and field not in list_fields and isinstance(output.get(field), str):
            output[field] = "; ".join(phrases + [output[field]])
    if "diagnostics" in output:
        output["diagnostics"].extend(phrases)
    for field in ("known_facts", "evidence_fields", "observed_evidence", "preservation_requirements"):
        if field in output and not output[field]:
            output[field] = phrases or [f"bounded {field}"]
    return output


def test_reviewed_v3_pack_is_fresh_bounded_and_balanced():
    paths = _fixture_paths()
    tasks = [load_task_fixture(path) for path in paths]
    assert len(tasks) == 24
    assert len({task["task_id"] for task in tasks}) == 24
    assert not any(task["task_id"].startswith(("capability-reviewed-", "capability-run2-")) for task in tasks)
    families = {task["task_family"] for task in tasks}
    assert families == {"contradiction-handling", "destructive-action-restraint", "evidence-grounding", "queue-authority-boundary", "scope-authority-boundary", "unsupported-certainty"}
    assert all(sum(task["task_family"] == family for task in tasks) == 4 for family in families)
    assert all(task["provenance"].get("novelty") == "new_source" for task in tasks)
    serialized = json.dumps(tasks, sort_keys=True).lower()
    assert "automatic patch promotion authority granted" not in serialized
    assert "automatic training authority granted" not in serialized
    assert "execution authority granted" not in serialized


def test_reviewed_v3_reference_facts_are_registered_and_contract_satisfiable():
    for path in _fixture_paths():
        task = load_task_fixture(path)
        fields = set(task["output_contract"]["required_fields"])
        for key, value in task["validator"].get("reference_facts", {}).items():
            spec = REFERENCE_FACT_SPECS[key]
            assert not spec.source_metadata
            if spec.alternative_output_fields:
                assert set(spec.alternative_output_fields) & fields
            elif spec.fields_from_value:
                assert set(value) <= fields
            elif spec.required_output_fields:
                assert set(spec.required_output_fields) <= fields


def test_reviewed_v3_fixtures_have_simultaneously_satisfiable_representatives():
    for path in _fixture_paths():
        task = load_task_fixture(path)
        result = _validator_result(json.dumps(_representative(task)), task, attempt_id="reviewed-v3-satisfiability")
        assert result["validation_status"] == "passed", (path.name, result["diagnostics"])
