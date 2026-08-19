import json
from pathlib import Path

import pytest

from local_harness.resource_calibration import calibrate_resource_telemetry, calibration_digest, expected_decision_cost, realized_resource_cost
from local_harness.resource_telemetry import load_approved_resource_weights, resource_weight_manifest_sha256, validate_resource_weight_bindings


ROOT = Path(__file__).resolve().parents[1]
RUN3C = ROOT / ".work/capability_batch_reviewed_v3c/run3c_execution_2026-08-20"
CANDIDATE = ROOT / "docs/research/RUN_4_RESOURCE_WEIGHTS_CANDIDATE_2026-08-19.json"
FREEZE = ROOT / "docs/research/RUN_4_RESOURCE_WEIGHTS_FREEZE_2026-08-19.json"


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


def test_approved_freeze_matches_reviewed_weights_and_bindings_fail_closed():
    manifest = load_approved_resource_weights(FREEZE)
    assert manifest["weights"]["worker_time_ms"] == 5276.567
    assert manifest["weights"]["local_teacher_time_ms"] == 16220.624
    assert manifest["weights"]["external_teacher_time_ms"] == 28704.012
    validate_resource_weight_bindings(
        manifest,
        worker_model="Qwen_Qwen3-1.7B-Q4_K_M.gguf",
        local_teacher_model="Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf",
        external_teacher_identity="codex-cli-0.146.0",
        external_timeout_seconds=120,
    )
    with pytest.raises(ValueError, match="binding mismatch"):
        validate_resource_weight_bindings(
            manifest,
            worker_model="changed-model",
            local_teacher_model="Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf",
            external_teacher_identity="codex-cli-0.146.0",
            external_timeout_seconds=120,
        )


def test_expected_decision_and_realized_cost_are_distinct():
    manifest = load_approved_resource_weights(FREEZE)
    expected = expected_decision_cost(manifest, {"worker": 2, "local_teacher": 1, "external_teacher": 1})
    realized = realized_resource_cost({"worker": [1000.0, 2000.0], "local_teacher": [3000.0], "external_teacher": [4000.0]})
    assert expected == 5276.567 * 2 + 16220.624 + 28704.012
    assert realized == 10000.0
    assert expected != realized
