from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from local_harness.run4a_fixture_pack import (
    ARM_ORDER_SEED,
    PERMUTATIONS,
    TARGET_BLOCKS,
    verify_manifest,
)
from local_harness.supervised_capability_loop import load_task_fixture


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "local_harness/fixtures/capability_loop/reviewed_v4a"


def test_run4a_pack_is_20_candidates_and_self_verifying():
    manifest = verify_manifest(PACK, ROOT)
    assert manifest["candidate_count"] == 20
    assert manifest["block_counts"] == {block: 5 for block in TARGET_BLOCKS}
    assert sum(len(ids) for ids in manifest["included_candidates_by_block"].values()) == 16
    assert sum(len(ids) for ids in manifest["reserve_candidates_by_block"].values()) == 4
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
        assert task["calibration"]["target_evidence_resolution"] == "task_family"
        assert task["calibration"]["target_evidence_key"] == task["task_family"]
