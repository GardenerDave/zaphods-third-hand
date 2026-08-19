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
    assert execution["preregistration"]["fixture_pack"]["pack_sha256"] == "b0744d9610ea1a5357b8097c3bf536580c568b4e140d15fb3f10ebf7ef5b67fa"
    frozen = execution["preregistration"]["frozen_inputs"]
    assert frozen["durable_launcher_path"] == "scripts/zth_run3_durable_launch.py"
    assert frozen["durable_launcher_sha256"]
