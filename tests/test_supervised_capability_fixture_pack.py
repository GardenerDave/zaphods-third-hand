import json
from pathlib import Path

from local_harness.supervised_capability_loop import load_task_fixture
from local_harness.supervised_reference_fact_validator import REFERENCE_FACT_EVALUATORS


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
    assert keys <= set(REFERENCE_FACT_EVALUATORS)
