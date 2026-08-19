from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from local_harness.run4a_fixture_pack import (
    ARM_ORDER_SEED,
    PERMUTATIONS,
    TARGET_BLOCKS,
    select_included_candidates,
    verify_manifest,
)
from local_harness.capability_cards import failure_classes, failure_signature
from local_harness.supervised_capability_loop import _validator_result
from local_harness.supervised_capability_loop import load_task_fixture


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "local_harness/fixtures/capability_loop/reviewed_v4a"


def test_run4a_pack_is_20_candidates_and_self_verifying():
    manifest = verify_manifest(PACK, ROOT)
    assert manifest["candidate_count"] == 20
    assert manifest["block_counts"] == {block: 5 for block in TARGET_BLOCKS}
    assert all(value is None for value in manifest["included_candidates_by_block"].values())
    assert all(value is None for value in manifest["reserve_candidates_by_block"].values())
    assert manifest["target_included_count_by_block"] == {block: 4 for block in TARGET_BLOCKS}
    assert manifest["model_outputs_consulted"] is False


def test_run4a_novelty_and_prompt_id_audit_are_clean():
    audit = json.loads((PACK / "novelty_audit.json").read_text())
    assert audit["task_id_collisions"] == []
    assert audit["exact_prompt_duplicates"] == []
    assert audit["normalized_prompt_duplicates"] == []
    assert audit["high_similarity_pairs"] == []
    assert audit["source_anchor_collisions"] == []
    assert audit["counts"] == {"candidates": 20, "new_source": 19, "new_scenario_same_family": 1, "source_document_reuse": 1, "source_anchor_reuse": 0}


def test_run4a_arm_order_has_all_six_permutations_balanced():
    manifest = verify_manifest(PACK, ROOT)
    assert manifest["arm_order"]["seed"] == ARM_ORDER_SEED
    orders = [tuple(value) for value in manifest["arm_order"]["orders"].values()]
    assert set(orders) == set(PERMUTATIONS)
    counts = Counter(orders)
    assert sorted(counts.values()) == [3, 3, 3, 3, 4, 4]


def test_run4a_fixture_witnesses_are_satisfiable_and_have_target_metadata():
    manifest = verify_manifest(PACK, ROOT)
    for fixture in manifest["fixtures"]:
        task = load_task_fixture(ROOT / fixture["path"])
        expected_resolution = "failure_class" if task["task_family"] == "scope-authority-boundary" else "task_family"
        assert task["calibration"]["target_evidence_resolution"] == expected_resolution
        assert task["calibration"]["target_evidence_key"] == task["task_family"]
        if task["task_family"] == "scope-authority-boundary":
            bad = {"allowed_targets": [], "held_targets": [], "scope_expansion_required": True, "review_status": "ready_for_review"}
            result = _validator_result(json.dumps(bad, sort_keys=True), task, attempt_id=f"run4a-scope-signature-{task['task_id']}")
            signature = failure_signature(task["task_family"], result)
            assert task["calibration"]["target_failure_classes"] == failure_classes(signature)


def test_run4a_baseline_selection_uses_first_eligible_failures_and_reserves_rest():
    candidate_order = ["001", "002", "003", "004", "005"]
    assert select_included_candidates(candidate_order, {"001", "003", "004", "005"}) == (["001", "003", "004", "005"], ["002"])
    assert select_included_candidates(candidate_order, {"001", "002", "003", "004"}) == (["001", "002", "003", "004"], ["005"])
