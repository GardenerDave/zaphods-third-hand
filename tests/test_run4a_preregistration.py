from __future__ import annotations

import hashlib
import json
from pathlib import Path

from local_harness.resource_telemetry import load_approved_resource_weights, resource_weight_manifest_sha256
from local_harness.run4a_fixture_pack import PERMUTATIONS, TARGET_BLOCKS, verify_manifest


ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "docs/research/RUN_4A_PREREGISTRATION_2026-08-19.json"
PACK = ROOT / "local_harness/fixtures/capability_loop/reviewed_v4a"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_run4a_preregistration_binds_all_frozen_inputs_without_calls():
    prereg = json.loads(PREREG.read_text())
    manifest = verify_manifest(PACK, ROOT)
    assert prereg["model_calls_made"] is False
    assert prereg["fixture_pack"]["manifest_sha256"] == manifest["manifest_sha256"]
    assert prereg["fixture_pack"]["pack_sha256"] == manifest["pack_sha256"]
    assert prereg["fixture_pack"]["candidate_count"] == 20
    assert prereg["fixture_pack"]["task_ids"] == [fixture["task_id"] for fixture in manifest["fixtures"]]
    assert prereg["frozen_inputs"]["routing_policy_sha256"] == _sha256(ROOT / prereg["frozen_inputs"]["routing_policy_path"])
    assert prereg["frozen_inputs"]["capability_bundle_sha256"] == _sha256(ROOT / prereg["frozen_inputs"]["capability_bundle_path"])
    resource_path = ROOT / prereg["frozen_inputs"]["resource_weight_manifest_path"]
    resource = load_approved_resource_weights(resource_path)
    assert resource_weight_manifest_sha256(resource) == prereg["frozen_inputs"]["resource_weight_manifest_sha256"]
    assert resource["weights"] == {
        **resource["weights"],
        "worker_time_ms": 5276.567,
        "local_teacher_time_ms": 16220.624,
        "external_teacher_time_ms": 28704.012,
    }
    assert prereg["frozen_inputs"]["deterministic_patch_sha256"] == _sha256(ROOT / prereg["frozen_inputs"]["deterministic_patch_path"])


def test_run4a_preregistration_freezes_orders_and_all_six_permutations():
    prereg = json.loads(PREREG.read_text())
    manifest = verify_manifest(PACK, ROOT)
    assert prereg["arm_order"]["seed"] == 20260821
    assert prereg["arm_order"]["orders"] == manifest["arm_order"]["orders"]
    orders = [tuple(order) for order in prereg["arm_order"]["orders"].values()]
    assert set(orders) == set(PERMUTATIONS)
    assert all(prereg["fixture_pack"]["included_candidates_by_block"][block] is None for block in TARGET_BLOCKS)
    assert all(prereg["fixture_pack"]["reserve_candidates_by_block"][block] is None for block in TARGET_BLOCKS)
    assert prereg["fixture_pack"]["target_included_count_by_block"] == {block: 4 for block in TARGET_BLOCKS}
    assert "first target count" in prereg["fixture_pack"]["selection_rule"]


def test_run4a_preregistration_binds_harness_and_validators():
    prereg = json.loads(PREREG.read_text())
    assert prereg["harness"]["sha256"] == _sha256(ROOT / prereg["harness"]["path"])
    for validator in prereg["validators"]:
        assert validator["sha256"] == _sha256(ROOT / validator["path"])
    assert prereg["timeouts_seconds"] == {"worker": 900, "local_teacher": 900, "external_teacher": 120}
    assert prereg["models"]["worker"] == "Qwen_Qwen3-1.7B-Q4_K_M.gguf"
    assert prereg["models"]["local_teacher"] == "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf"
    assert prereg["models"]["external_teacher"] == "codex-cli-0.146.0"
    assert prereg["metrics"]["support_threshold"] == {"minimum_comparable_opportunities": 3, "minimum_rescue_rate": 0.5}
    assert prereg["planning_budget_maximum"] == {
        "candidate_baseline_calls": 20,
        "included_tasks": 16,
        "baseline_worker_calls": 20,
        "post_intervention_worker_calls": 48,
        "local_teacher_calls": 16,
        "external_teacher_calls": 16,
        "total_model_calls": 100,
        "expected_elapsed_ms": 1077600.732,
    }


def test_run4a_preregistration_binds_driver_and_incomplete_block_semantics():
    prereg = json.loads(PREREG.read_text())
    assert prereg["driver"]["sha256"] == _sha256(ROOT / prereg["driver"]["path"])
    assert prereg["driver"]["explicit_execute_gate"] is True
    assert prereg["execution_stop_semantics"]["intervention_outcomes_do_not_affect_selection"] is True
    assert "mark the experiment incomplete" in prereg["execution_stop_semantics"]["incomplete_block"]
