from __future__ import annotations

import json
from pathlib import Path

import pytest

from local_harness.icm_spec import WorkerResponse
from local_harness.run4_economic_fixture_pack import pair_orders, verify_manifest
from local_harness.run4_economic_policy import choose_intervention, verify_policy_freeze
from local_harness.supervised_capability_loop import load_task_fixture
from scripts.zth_run4_economic_routing import Run4ADriverError, run_experiment, validate_preregistration


ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "docs/research/RUN_4_ECONOMIC_ROUTING_PREREGISTRATION_2026-08-19.json"
PACK = ROOT / "local_harness/fixtures/capability_loop/reviewed_run4_economic_triage"
POLICY = ROOT / "docs/research/RUN_4_ECONOMIC_ROUTING_POLICY_FREEZE_2026-08-19.json"
COMPARATIVE = ROOT / "docs/research/RUN_4A_COMPARATIVE_EVIDENCE_FREEZE_2026-08-19.json"


def _response(content: str, *, model: str = "fixture-model") -> WorkerResponse:
    return WorkerResponse("ok", content, "http://fixture.invalid/v1", model, model, "stop", {}, {}, None)


def _valid_output(task: dict) -> str:
    facts = task["validator"]["reference_facts"]
    phrase = " ".join(facts["must_include"])
    return json.dumps({"route": phrase, "rationale": phrase, "review_status": facts["review_status"]})


def test_policy_matrix_exactly_matches_frozen_run4a_evidence():
    evidence = json.loads(COMPARATIVE.read_text())
    expected = {
        "contradiction-handling": ("deterministic_patch_retry", "deterministic_patch_retry"),
        "triage-routing": ("external_teacher", "deterministic_patch_retry"),
        "scope-authority-boundary": ("local_teacher", "local_teacher"),
        "unsupported-certainty": ("deterministic_patch_retry", "deterministic_patch_retry"),
    }
    for key, (control, treatment) in expected.items():
        assert choose_intervention(evidence, key, "capability_first")["recommended_intervention"] == control
        assert choose_intervention(evidence, key, "cheapest_supported_positive")["recommended_intervention"] == treatment
    assert sum(control != treatment for control, treatment in expected.values()) == 1


def test_negative_and_missing_positive_evidence_cannot_be_selected():
    evidence = {"blocks": {"triage-routing": {
        "deterministic_patch_retry": {"evidence_status": "supported_negative", "rescue_rate": 0.0, "expected_immediate_action_cost_ms": 5276.567},
        "local_teacher": {"evidence_status": "observed", "rescue_rate": 1.0, "expected_immediate_action_cost_ms": 21497.191},
        "external_teacher": {"evidence_status": "insufficient", "rescue_rate": 1.0, "expected_immediate_action_cost_ms": 33980.579},
    }}}
    assert choose_intervention(evidence, "triage-routing", "capability_first")["routing_disposition"] == "abstain"


def test_fixture_manifest_has_fifteen_candidates_and_pair_order_is_reproducible():
    manifest = verify_manifest(PACK, ROOT)
    assert manifest["candidate_count"] == 15
    assert manifest["target_included_count"] == 12
    assert manifest["candidate_order"] == sorted(manifest["candidate_order"])
    assert manifest["pair_order"]["orders"] == pair_orders(manifest["candidate_order"])
    assert len(manifest["pair_order"]["orders"]) == 15


def test_policy_freeze_is_self_verifying():
    freeze = verify_policy_freeze(POLICY, COMPARATIVE, ROOT / "local_harness/run4_economic_policy.py")
    assert freeze["authority"] == "experiment_only_advisory_policy"


def test_dry_run_validation_requires_no_model_calls():
    context = validate_preregistration(PREREG, ROOT)
    assert context["preregistration"]["model_calls_made"] is False


def test_paired_driver_with_stubs_runs_two_arms_and_no_local_teacher(tmp_path: Path):
    context = validate_preregistration(PREREG, ROOT)
    context["preregistration_path"] = PREREG
    context["git_head"] = "synthetic"
    tasks = {row["task_id"]: load_task_fixture(PACK / Path(row["path"]).name) for row in context["manifest"]["fixtures"]}
    calls = {"worker": 0, "local": 0, "external": 0}

    def worker(prompt: str) -> WorkerResponse:
        calls["worker"] += 1
        for task in tasks.values():
            if prompt == task["prompt"]:
                return _response("{}")
            if task["prompt"] in prompt:
                return _response(_valid_output(task))
        return _response("{}")

    def local(_: str) -> WorkerResponse:
        calls["local"] += 1
        return _response("{}", model="local")

    def external(_: str):
        calls["external"] += 1
        return "codex-fixture", json.dumps({"failure_classification": "synthetic", "teacher_diagnosis": "review", "retry_guidance": "Return the bounded JSON."})

    frozen = context["preregistration"]["frozen_inputs"]
    patch = {"patch_id": frozen["deterministic_patch_id"], "patch_path": str(ROOT / frozen["deterministic_patch_path"]), "patch_sha256": frozen["deterministic_patch_sha256"]}
    result = run_experiment(context, tmp_path / "run", worker=worker, local_teacher=local, external_teacher=external, deterministic_patch=patch)
    assert result["status"] == "experiment_completed"
    assert calls == {"worker": 39, "local": 0, "external": 12}
    aggregate = json.loads((tmp_path / "run" / "aggregate.json").read_text())
    assert aggregate["included_pairs"] == 12
    assert aggregate["control"]["validated_passes"] == 12
    assert aggregate["treatment"]["validated_passes"] == 12
    assert aggregate["control"]["external_teacher_calls"] == 12
    assert aggregate["treatment"]["external_teacher_calls"] == 0


def test_active_call_fails_closed_before_any_resume_call(tmp_path: Path):
    context = validate_preregistration(PREREG, ROOT)
    context["preregistration_path"] = PREREG
    context["git_head"] = "synthetic"
    output = tmp_path / "run"
    output.mkdir()
    (output / "execution_manifest.json").write_text(json.dumps({"status": "experiment_running", "active_call": {"task_id": "x", "arm": "control"}}))
    with pytest.raises(Run4ADriverError, match="ambiguous active call"):
        run_experiment(context, output, worker=lambda _: (_ for _ in ()).throw(AssertionError("call")), local_teacher=lambda _: _response("{}"), external_teacher=lambda _: ("x", "{}"), deterministic_patch={})
