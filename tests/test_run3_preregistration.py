from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "local_harness/fixtures/capability_loop/reviewed_v3"
MANIFEST_PATH = PACK / "manifest.json"
PREREG_PATH = ROOT / "docs/research/RUN_3_PREREGISTRATION_2026-08-18.json"
FREEZE_PATH = ROOT / "docs/research/RUN_3_ROUTING_POLICY_FREEZE_2026-08-18.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_run3_manifest_is_self_verifying_and_satisfiable_pack_is_frozen():
    manifest = json.loads(MANIFEST_PATH.read_text())
    entries = manifest["fixtures"]
    assert len(entries) == 24
    assert len({entry["task_id"] for entry in entries}) == 24
    for entry in entries:
        path = PACK / entry["path"]
        assert path.is_file()
        assert _sha256(path) == entry["fixture_sha256"]
        task = json.loads(path.read_text())
        assert task["task_id"] == entry["task_id"]
        assert task["task_family"] == entry["task_family"]
        assert task["provenance"]["novelty"] == entry["novelty"] == "new_source"
        assert hashlib.sha256(json.dumps(task["output_contract"], sort_keys=True, separators=(",", ":")).encode()).hexdigest() == entry["output_contract_sha256"]
        assert hashlib.sha256(json.dumps(task["validator"]["reference_facts"], sort_keys=True, separators=(",", ":")).encode()).hexdigest() == entry["reference_facts_sha256"]


def test_run3_preregistration_matches_policy_and_declares_no_calls():
    prereg = json.loads(PREREG_PATH.read_text())
    freeze = json.loads(FREEZE_PATH.read_text())
    assert prereg["task_pack"]["manifest_sha256"] == _sha256(MANIFEST_PATH)
    assert prereg["policy_freeze"]["sha256"] == _sha256(FREEZE_PATH)
    assert prereg["policy_freeze"]["router_source_sha256"] == freeze["router_source_sha256"]
    assert prereg["policy_freeze"]["evidence_bundle_sha256"] == freeze["capability_bundle_sha256"]
    assert prereg["task_pack"]["task_count"] == len(prereg["task_pack"]["task_ids"]) == 24
    assert prereg["task_pack"]["pre_behavioral_routing_classification"]["status"] == "not_yet_observed"
    assert prereg["transport"]["included_only_when"] == "transport_classification=model_response"
    assert prereg["status"] == "ready_for_review"
    assert prereg["model_calls_made"] is False
    assert prereg["arms"]["control"]["policy"] == ["baseline", "deterministic_patch_retry", "local_teacher", "external_teacher", "review/unresolved"]
