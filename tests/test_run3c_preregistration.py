from pathlib import Path

from scripts.zth_run3_routing_experiment import arm_order, load_execution_preregistration


ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "docs/research/RUN_3C_PREREGISTRATION_2026-08-18.json"


def test_run3c_preregistration_freezes_24_tasks_and_orders():
    execution = load_execution_preregistration(PREREG, repository_root=ROOT, driver_path=ROOT / "scripts/zth_run3_routing_experiment.py")
    assert execution["seed"] == "20260820"
    assert len(execution["task_ids"]) == 24
    assert all(execution["arm_order"][task_id] == arm_order(task_id, "20260820") for task_id in execution["task_ids"])
    assert execution["preregistration"]["model_calls_made"] is False
    assert execution["preregistration"]["fixture_pack"]["pack_sha256"] == "b1428f126d619f61a600e04cb65f8f10feadc1dda0ee5da58fae393823663c74"
