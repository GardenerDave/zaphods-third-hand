from __future__ import annotations

import json
from pathlib import Path

from local_harness.supervised_capability_loop import _validator_result, load_task_fixture
from local_harness.supervised_reference_fact_validator import REFERENCE_FACT_SPECS


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "local_harness/fixtures/capability_loop/reviewed_v3b"


def _fixture_paths():
    return sorted(p for p in PACK.glob("*.json") if p.name != "manifest.json")


def _representative(task: dict) -> dict:
    fields = task["output_contract"]["required_fields"]
    facts = task["validator"]["reference_facts"]
    phrases = []
    list_fields = {"allowed_targets", "held_targets", "unverified_claims", "observed_evidence", "claims", "records", "sources", "observations", "completed_items", "missing_items"}
    output = {field: [] if field in list_fields else True if field == "review_required" else False if field == "scope_expansion_required" else "review-only response" for field in fields}
    for key, value in facts.items():
        if key == "required_allowed_targets": output["allowed_targets"] = list(value)
        elif key == "required_held_targets": output["held_targets"] = list(value)
        elif key == "required_review_required": output["review_required"] = value
        elif key == "requires_scope_expansion_flag": output["scope_expansion_required"] = value
        elif key in {"queue_handoff_status", "review_status"} and key in output: output[key] = value
        elif key == "must_include": phrases.extend(value)
        elif key in {"uncertainty", "destructive_action_requires_review"}: phrases.extend(["uncertain", "review", "do not execute"])
    direct_fields = {"queue_handoff_status", "review_status"}
    for field in fields:
        if isinstance(output[field], str) and field not in direct_fields: output[field] = "; ".join(phrases + [output[field]])
    return output


def test_reviewed_v3b_is_fresh_balanced_and_satisfiable():
    tasks = [load_task_fixture(p) for p in _fixture_paths()]
    assert len(tasks) == 24
    assert len({t["task_id"] for t in tasks}) == 24
    assert not any(t["task_id"].startswith(("capability-reviewed-", "capability-run2-", "capability-run3-")) for t in tasks)
    families = {t["task_family"] for t in tasks}
    assert families == {"contradiction-handling", "destructive-action-restraint", "evidence-grounding", "queue-authority-boundary", "scope-authority-boundary", "unsupported-certainty"}
    assert all(sum(t["task_family"] == family for t in tasks) == 4 for family in families)
    assert all(t["provenance"]["novelty"] == "new_source" for t in tasks)
    serialized = json.dumps(tasks, sort_keys=True).lower()
    assert "automatic patch promotion authority granted" not in serialized
    assert "automatic training authority granted" not in serialized
    assert "execution authority granted" not in serialized
    for path, task in zip(_fixture_paths(), tasks):
        for key in task["validator"]["reference_facts"]:
            assert key in REFERENCE_FACT_SPECS
        result = _validator_result(json.dumps(_representative(task)), task, attempt_id="v3b-satisfiability")
        assert result["validation_status"] == "passed", (path.name, result["diagnostics"])
