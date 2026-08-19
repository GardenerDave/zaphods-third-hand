import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "docs/research/RUN_3B_PREREGISTRATION_2026-08-18.json"
PACK = ROOT / "local_harness/fixtures/capability_loop/reviewed_v3b"


def _pack_hash(manifest):
    return hashlib.sha256(
        ("\n".join(sorted(item["fixture_sha256"] for item in manifest["fixtures"])) + "\n").encode()
    ).hexdigest()


def _sha256_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _arm_order(seed, task_id):
    digest = hashlib.sha256(f"{seed}:{task_id}".encode()).hexdigest()
    return ["control", "treatment"] if int(digest[0], 16) < 8 else ["treatment", "control"]


def test_run3b_preregistration_is_self_verifying_and_model_free():
    prereg = json.loads(PREREG.read_text())
    manifest_path = ROOT / prereg["fixture_pack"]["manifest_path"]
    manifest = json.loads(manifest_path.read_text())
    entries = manifest["fixtures"]
    task_ids = [item["task_id"] for item in entries]

    assert prereg["model_calls_made"] is False
    assert prereg["status"] == "ready_for_review"
    assert prereg["fixture_pack"]["task_count"] == 24
    assert len(entries) == 24
    assert len(task_ids) == len(set(task_ids))
    assert _sha256_file(manifest_path) == prereg["fixture_pack"]["manifest_sha256"]
    assert _pack_hash(manifest) == prereg["fixture_pack"]["pack_sha256"]
    assert task_ids == prereg["fixture_pack"]["task_ids"]

    expected = {
        "docs/research/RUN_3_ROUTING_POLICY_FREEZE_2026-08-18.json": prereg["frozen_inputs"]["routing_policy_sha256"],
        "docs/research/RUN_3_EXECUTION_HARNESS_FREEZE_2026-08-18.json": prereg["frozen_inputs"]["execution_harness_freeze_sha256"],
        "scripts/zth_run3_routing_experiment.py": prereg["frozen_inputs"]["driver_sha256"],
    }
    for relative, digest in expected.items():
        assert _sha256_file(ROOT / relative) == digest

    assert prereg["execution_order"]["seed"] != 20260818
    assert prereg["execution_order"]["arm_order"] == {
        task_id: _arm_order(prereg["execution_order"]["seed"], task_id)
        for task_id in task_ids
    }
    assert prereg["external_teacher_timeout_seconds"] == 120
    assert "invalid_incomplete_execution_pilot" == prereg["pilot_exclusion"]["status"]
