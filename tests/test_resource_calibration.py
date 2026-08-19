import json
from pathlib import Path

from local_harness.resource_calibration import calibrate_resource_telemetry, calibration_digest
from local_harness.resource_telemetry import resource_weight_manifest_sha256


ROOT = Path(__file__).resolve().parents[1]
RUN3C = ROOT / ".work/capability_batch_reviewed_v3c/run3c_execution_2026-08-20"
CANDIDATE = ROOT / "docs/research/RUN_4_RESOURCE_WEIGHTS_CANDIDATE_2026-08-19.json"


def test_calibration_has_complete_elapsed_coverage_for_all_roles_and_external_tokens_are_unavailable():
    result = calibrate_resource_telemetry(RUN3C)
    roles = result["resource_roles"]
    assert {role: roles[role]["elapsed_ms_coverage"] for role in roles} == {"worker": 156, "local_teacher": 41, "external_teacher": 27}
    assert roles["external_teacher"]["model_identities"] == ["codex-cli-0.146.0"]
    assert roles["external_teacher"]["hardware_identity"] is None
    assert result["basis"] == "median_observed_elapsed_ms_per_call"
    assert "pass" not in result["used_fields"]


def test_calibration_ignores_outcome_fields(tmp_path: Path):
    trajectory = tmp_path / "control" / "task" / "trajectory.jsonl"
    trajectory.parent.mkdir(parents=True)
    records = [
        {"transition": "worker_call_started", "attempt": 1, "intervention_id": "none:1", "intervention_source": "none", "timestamp": "2026-08-19T00:00:00+00:00"},
        {"transition": "worker_output_captured", "attempt": 1, "intervention_id": "none:1", "intervention_source": "none", "timestamp": "2026-08-19T00:00:01+00:00"},
    ]
    trajectory.write_text("\n".join(json.dumps(x) for x in records) + "\n")
    (trajectory.parent / "attempt-1.raw.json").write_text(json.dumps({"metadata": {"model": "worker"}}))
    first = calibrate_resource_telemetry(tmp_path)
    (trajectory.parent / "trajectory_summary.json").write_text(json.dumps({"pass": True, "routing_disposition": "recommend"}))
    second = calibrate_resource_telemetry(tmp_path)
    assert first["resource_roles"] == second["resource_roles"]


def test_candidate_manifest_is_draft_and_digest_is_internal():
    payload = json.loads(CANDIDATE.read_text())
    assert payload["frozen"] is False
    assert payload["review_status"] == "draft"
    assert resource_weight_manifest_sha256(payload) == payload["manifest_sha256"]
    assert calibration_digest(payload)
