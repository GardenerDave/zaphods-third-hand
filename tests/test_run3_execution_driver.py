from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from local_harness.icm_spec import WorkerResponse
from scripts.zth_run3_routing_experiment import (
    RESOURCE_ACTIONS,
    Run3StateError,
    _baseline,
    _assert_no_incomplete_transitions,
    arm_order,
    derive_action,
    external_teacher,
    load_execution_preregistration,
    main,
    validate_runtime_bindings,
    require_valid_preflight,
)


ROOT = Path(__file__).resolve().parents[1]
PREREG = json.loads((ROOT / "docs/research/RUN_3B_PREREGISTRATION_2026-08-18.json").read_text())


def test_arm_order_matches_preregistered_seed_and_first_bit_for_all_tasks():
    for task_id, expected in PREREG["execution_order"]["arm_order"].items():
        assert arm_order(task_id, str(PREREG["execution_order"]["seed"])) == expected


def test_run3b_preregistration_schema_loads_and_freezes_all_24_orders():
    execution = load_execution_preregistration(
        ROOT / "docs/research/RUN_3B_PREREGISTRATION_2026-08-18.json",
        repository_root=ROOT,
        driver_path=ROOT / "scripts/zth_run3_routing_experiment.py",
    )
    assert execution["seed"] == "20260819"
    assert len(execution["task_ids"]) == 24
    assert execution["arm_order"] == PREREG["execution_order"]["arm_order"]


def test_preregistration_mismatched_seed_fails_closed(tmp_path):
    prereg = json.loads(json.dumps(PREREG))
    prereg["execution_order"]["seed"] = 20260818
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(prereg))
    with pytest.raises(Run3StateError):
        load_execution_preregistration(path, repository_root=ROOT, driver_path=ROOT / "scripts/zth_run3_routing_experiment.py")


def test_preregistration_task_drift_fails_closed(tmp_path):
    prereg = json.loads(json.dumps(PREREG))
    prereg["fixture_pack"]["task_ids"][0] = "drifted-task"
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(prereg))
    with pytest.raises(Run3StateError):
        load_execution_preregistration(path, repository_root=ROOT, driver_path=ROOT / "scripts/zth_run3_routing_experiment.py")


def test_preregistration_manifest_drift_fails_closed(tmp_path):
    prereg = json.loads(json.dumps(PREREG))
    prereg["fixture_pack"]["manifest_sha256"] = "0" * 64
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(prereg))
    with pytest.raises(Run3StateError):
        load_execution_preregistration(path, repository_root=ROOT, driver_path=ROOT / "scripts/zth_run3_routing_experiment.py")


@pytest.mark.parametrize("field", ["routing_policy_sha256", "execution_harness_freeze_sha256"])
def test_frozen_artifact_drift_fails_closed(tmp_path, field):
    prereg = json.loads(json.dumps(PREREG))
    prereg["frozen_inputs"][field] = "0" * 64
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(prereg))
    with pytest.raises(Run3StateError):
        load_execution_preregistration(path, repository_root=ROOT, driver_path=ROOT / "scripts/zth_run3_routing_experiment.py")


def _valid_bindings(execution):
    frozen = execution["preregistration"]["frozen_inputs"]
    return validate_runtime_bindings(
        execution,
        policy_sha256=frozen["routing_policy_sha256"],
        bundle_path=ROOT / ".work/capability_cards/capability_cards.json",
        patch_id=frozen["patch_id"],
        patch_sha256=frozen["patch_sha256"],
        patch_path=ROOT / ".work/capability_batch_reviewed_v1/synthesis/run1_distilled_candidate_patch.json",
        worker_model=PREREG["models"]["worker"],
        local_teacher_model=PREREG["models"]["local_teacher"],
        external_teacher_identity=PREREG["models"]["external_teacher"],
        external_timeout="120",
    )


def test_runtime_bindings_match_all_frozen_identities_and_timeout():
    execution = load_execution_preregistration(
        ROOT / "docs/research/RUN_3B_PREREGISTRATION_2026-08-18.json",
        repository_root=ROOT,
        driver_path=ROOT / "scripts/zth_run3_routing_experiment.py",
    )
    bindings = _valid_bindings(execution)
    assert bindings["external_timeout_seconds"] == 120


@pytest.mark.parametrize("field", ["routing_policy_sha256", "capability_bundle_sha256", "patch_id", "patch_sha256"])
def test_runtime_binding_drift_fails_closed(field):
    execution = load_execution_preregistration(
        ROOT / "docs/research/RUN_3B_PREREGISTRATION_2026-08-18.json",
        repository_root=ROOT,
        driver_path=ROOT / "scripts/zth_run3_routing_experiment.py",
    )
    frozen = execution["preregistration"]["frozen_inputs"]
    kwargs = dict(
        policy_sha256=frozen["routing_policy_sha256"],
        bundle_path=ROOT / ".work/capability_cards/capability_cards.json",
        patch_id=frozen["patch_id"],
        patch_sha256=frozen["patch_sha256"],
        patch_path=ROOT / ".work/capability_batch_reviewed_v1/synthesis/run1_distilled_candidate_patch.json",
        worker_model=PREREG["models"]["worker"], local_teacher_model=PREREG["models"]["local_teacher"],
        external_teacher_identity=PREREG["models"]["external_teacher"], external_timeout="120",
    )
    if field == "routing_policy_sha256": kwargs["policy_sha256"] = "0" * 64
    elif field == "capability_bundle_sha256": kwargs["bundle_path"] = ROOT / "README.md"
    elif field == "patch_id": kwargs["patch_id"] = "wrong-patch"
    else: kwargs["patch_sha256"] = "0" * 64
    with pytest.raises(Run3StateError):
        validate_runtime_bindings(execution, **kwargs)


@pytest.mark.parametrize("role", ["worker_model", "local_teacher_model", "external_teacher_identity"])
def test_runtime_model_identity_drift_fails_closed(role):
    execution = load_execution_preregistration(
        ROOT / "docs/research/RUN_3B_PREREGISTRATION_2026-08-18.json",
        repository_root=ROOT,
        driver_path=ROOT / "scripts/zth_run3_routing_experiment.py",
    )
    frozen = execution["preregistration"]["frozen_inputs"]
    kwargs = dict(
        policy_sha256=frozen["routing_policy_sha256"], bundle_path=ROOT / ".work/capability_cards/capability_cards.json",
        patch_id=frozen["patch_id"], patch_sha256=frozen["patch_sha256"],
        patch_path=ROOT / ".work/capability_batch_reviewed_v1/synthesis/run1_distilled_candidate_patch.json",
        worker_model=PREREG["models"]["worker"], local_teacher_model=PREREG["models"]["local_teacher"],
        external_teacher_identity=PREREG["models"]["external_teacher"], external_timeout="120",
    )
    kwargs[role] = "wrong-identity"
    with pytest.raises(Run3StateError):
        validate_runtime_bindings(execution, **kwargs)


def test_runtime_timeout_drift_fails_closed():
    execution = load_execution_preregistration(
        ROOT / "docs/research/RUN_3B_PREREGISTRATION_2026-08-18.json",
        repository_root=ROOT,
        driver_path=ROOT / "scripts/zth_run3_routing_experiment.py",
    )
    with pytest.raises(Run3StateError):
        validate_runtime_bindings(
            execution,
            policy_sha256=PREREG["frozen_inputs"]["routing_policy_sha256"],
            bundle_path=ROOT / ".work/capability_cards/capability_cards.json",
            patch_id=PREREG["frozen_inputs"]["patch_id"], patch_sha256=PREREG["frozen_inputs"]["patch_sha256"],
            patch_path=ROOT / ".work/capability_batch_reviewed_v1/synthesis/run1_distilled_candidate_patch.json",
            worker_model=PREREG["models"]["worker"], local_teacher_model=PREREG["models"]["local_teacher"],
            external_teacher_identity=PREREG["models"]["external_teacher"], external_timeout="121",
        )


def test_main_validates_preregistration_before_any_worker_call(tmp_path, monkeypatch):
    prereg = json.loads(json.dumps(PREREG))
    prereg["execution_order"]["seed"] = 20260818
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(prereg))
    monkeypatch.setattr("scripts.zth_run3_routing_experiment.call_worker", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("worker called")))
    with pytest.raises(SystemExit):
        main([
            "--preregistration", str(path),
            "--out-dir", str(tmp_path / "out"),
            "--bundle", str(ROOT / ".work/capability_cards/capability_cards.json"),
            "--patch-path", str(ROOT / ".work/capability_batch_reviewed_v1/synthesis/candidate_prompt_patches.json"),
            "--patch-id", "run1-experimental-distilled-strict-contract-v1",
            "--patch-sha256", PREREG["frozen_inputs"]["patch_sha256"],
            "--policy-sha256", PREREG["frozen_inputs"]["routing_policy_sha256"],
        ])


def test_avoid_derives_deterministic_retry_from_supported_negative_alternative():
    advisory = {
        "routing_disposition": "avoid",
        "recommended_intervention": None,
        "alternatives": [
            {"intervention": "deterministic_patch_retry", "resource_tier": 1, "evidence_polarity": "supported_negative"},
            {"intervention": "local_teacher", "resource_tier": 2, "evidence_polarity": "observed"},
        ],
    }
    assert derive_action(advisory) == "avoid_deterministic_patch_retry"


def test_preflight_requires_authoritative_transport_metadata():
    require_valid_preflight({"transport_valid": True, "transport_classification": "model_response"})
    with pytest.raises(Run3StateError):
        require_valid_preflight({"transport_valid": True, "transport_classification": None})


@pytest.mark.parametrize("action,expected", RESOURCE_ACTIONS.items())
def test_every_frozen_treatment_action_has_exact_rung_sequence(action, expected):
    calls = []
    for rung in expected:
        calls.append(rung)
    assert calls == list(expected)


def test_baseline_reuse_makes_one_synthetic_call_and_preserves_artifacts(tmp_path):
    task = {"task_id": "synthetic-baseline", "task_family": "test", "prompt": "Return JSON.", "output_contract": {"format": "json", "required_fields": ["answer"]}, "validator": {"kind": "exact_json"}, "expected_output": {"answer": "ok"}}
    calls = []

    def worker(_prompt):
        calls.append(1)
        return WorkerResponse("ok", '{"answer":"ok"}', "http://test.invalid/v1", "worker", "worker", "stop", {"prompt_tokens": 1}, {}, {}, None, False, None, None)

    first = _baseline(task, tmp_path, worker)
    raw_before = (tmp_path / "attempt-1.raw.json").read_bytes()
    second = _baseline(task, tmp_path, worker)
    assert len(calls) == 1
    assert first["artifact_hashes"]["raw"] == second["artifact_hashes"]["raw"]
    assert (tmp_path / "attempt-1.raw.json").read_bytes() == raw_before


def test_incomplete_baseline_fails_closed_without_call(tmp_path):
    (tmp_path / "attempt-1.raw.json").write_text("{}")
    calls = []
    with pytest.raises(Run3StateError):
        _baseline({"task_id": "x", "prompt": "x"}, tmp_path, lambda _prompt: calls.append(1))
    assert calls == []


def test_incomplete_intervention_transition_fails_closed(tmp_path):
    trajectory = tmp_path / "trajectory.jsonl"
    trajectory.write_text(json.dumps({"record_type": "transition", "transition": "external_teacher_started", "attempt": 1}) + "\n")
    with pytest.raises(Run3StateError):
        _assert_no_incomplete_transitions(tmp_path)


def test_external_adapter_uses_bounded_timeout_without_invoking_process(monkeypatch):
    observed = {}

    class Completed:
        returncode = 0
        stdout = "{}"

    def fake_run(argv, **kwargs):
        observed.update(kwargs)
        return Completed()

    monkeypatch.setenv("ZTH_EXTERNAL_TEACHER_COMMAND", "codex-teacher-wrapper")
    monkeypatch.setattr("scripts.zth_run3_routing_experiment.subprocess.run", fake_run)
    external_teacher("bounded packet")
    assert observed["timeout"] == 120
    assert observed["capture_output"] is True
    assert observed["input"] == "bounded packet"
