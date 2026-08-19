from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from pathlib import Path

from local_harness.supervised_capability_loop import _validator_result, load_task_fixture
from local_harness.supervised_reference_fact_validator import REFERENCE_FACT_SPECS


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "local_harness/fixtures/capability_loop/reviewed_v3c"
PRIOR = [ROOT / "local_harness/fixtures/capability_loop" / name for name in ("reviewed_v1", "reviewed_v2", "reviewed_v3", "reviewed_v3b")]


def _paths() -> list[Path]:
    return sorted(path for path in PACK.glob("*.json") if path.name != "manifest.json")


def _representative(task: dict) -> dict:
    fields = task["output_contract"]["required_fields"]
    facts = task["validator"]["reference_facts"]
    list_fields = {"allowed_targets", "held_targets", "allowed_paths", "known_facts", "preservation_requirements", "inspection_plan", "unsupported_inferences"}
    output = {field: [] if field in list_fields else True if field == "review_required" else False if field == "scope_expansion_required" else "review-only response" for field in fields}
    phrases = []
    for key, value in facts.items():
        if key == "must_include": phrases.extend(value)
        elif key == "uncertainty": phrases.extend(["uncertain result requires review", "review"])
        elif key == "required_allowed_targets": output["allowed_targets"] = list(value)
        elif key == "required_held_targets": output["held_targets"] = list(value)
        elif key == "forbidden_allowed_targets": output["allowed_targets"] = [item for item in output.get("allowed_targets", []) if item not in value]
        elif key == "required_review_required": output["review_required"] = value
        elif key == "requires_scope_expansion_flag": output["scope_expansion_required"] = value
        elif key == "queue_handoff_status": output["queue_handoff_status"] = value
    for field in fields:
        if isinstance(output.get(field), str) and field != "queue_handoff_status":
            output[field] = "; ".join(phrases + [output[field]])
    for field in list_fields:
        if field in output and not output[field]: output[field] = phrases or [field]
    if "allowed_paths" in output: output["allowed_paths"] = ["review-only"]
    return output


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def test_reviewed_v3c_is_exactly_24_balanced_and_satisfiable():
    paths = _paths()
    tasks = [load_task_fixture(path) for path in paths]
    assert len(tasks) == 24
    assert {task["task_family"] for task in tasks} == {"contradiction-handling", "destructive-action-restraint", "evidence-grounding", "queue-authority-boundary", "scope-authority-boundary", "unsupported-certainty"}
    assert all(sum(task["task_family"] == family for task in tasks) == 4 for family in {task["task_family"] for task in tasks})
    assert len({task["task_id"] for task in tasks}) == 24
    assert all(task["provenance"]["novelty"] == "new_source" for task in tasks)
    for task in tasks:
        for key, value in task["validator"]["reference_facts"].items():
            spec = REFERENCE_FACT_SPECS[key]
            assert not spec.source_metadata
            if spec.alternative_output_fields: assert set(spec.alternative_output_fields) & set(task["output_contract"]["required_fields"])
        result = _validator_result(json.dumps(_representative(task)), task, attempt_id="v3c-satisfiability")
        assert result["validation_status"] == "passed", (task["task_id"], result["diagnostics"])


def test_reviewed_v3c_has_no_prior_prompt_or_id_collision():
    new = [load_task_fixture(path) for path in _paths()]
    old = [load_task_fixture(path) for pack in PRIOR for path in sorted(pack.glob("*.json")) if path.name != "manifest.json"]
    new_ids = {task["task_id"] for task in new}
    old_ids = {task["task_id"] for task in old}
    assert not new_ids & old_ids
    old_prompts = {task["prompt"] for task in old}
    old_normalized = {_normalize(task["prompt"]) for task in old}
    assert not any(task["prompt"] in old_prompts for task in new)
    assert not any(_normalize(task["prompt"]) in old_normalized for task in new)
    assert not any(SequenceMatcher(None, _normalize(new_task["prompt"]), _normalize(old_task["prompt"])).ratio() >= 0.8 for new_task in new for old_task in old)
