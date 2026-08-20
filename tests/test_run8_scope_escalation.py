from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from local_harness.icm_spec import WorkerResponse
from local_harness.run7_escalation_policy import EXTERNAL_ACTION_MS, LOCAL_ACTION_MS, break_even_escalation_count, verify_policy
from local_harness.supervised_capability_loop import _parse_teacher
from local_harness.run8_scope_fixture_pack import verify_manifest
from scripts import zth_run7_scope_escalation as repaired
from scripts import zth_run8_scope_escalation as driver
from scripts.zth_run4a_intervention_calibration import Run4ADriverError


ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "docs/research/RUN_8_VALIDATION_GATED_ESCALATION_PREREGISTRATION_2026-08-20.json"
HISTORICAL_PREREG = ROOT / "docs/research/RUN_7_VALIDATION_GATED_ESCALATION_PREREGISTRATION_2026-08-20.json"
PACK = ROOT / "local_harness/fixtures/capability_loop/run8_scope"


def _response(content: str, model: str = "fixture-model") -> WorkerResponse:
    return WorkerResponse("ok", content, "http://fixture.invalid/v1", model, model, "stop", {}, {}, None)


def _context() -> dict:
    context = driver._load_context(PREREG, ROOT, require_runtime=False)
    context["git_head"] = "synthetic-run8-head"
    return context


def _valid(task: dict) -> str:
    facts = task["validator"]["reference_facts"]
    return json.dumps({"allowed_targets": facts["required_allowed_targets"], "held_targets": facts["required_held_targets"], "scope_expansion_required": facts["requires_scope_expansion_flag"], "review_status": facts["review_status"]})


def _invalid(task: dict) -> str:
    return json.dumps({"allowed_targets": [], "held_targets": [], "scope_expansion_required": False, "review_status": "ready_for_review"})


def _callbacks(context: dict, calls: dict[str, int], *, local_pass: bool = False):
    tasks = context["tasks"]

    def worker(prompt: str) -> WorkerResponse:
        calls["worker"] += 1
        for task in tasks.values():
            if prompt == task["prompt"]:
                return _response(_invalid(task))
            if task["prompt"] in prompt:
                if local_pass or "local_first_validation_failure" in prompt:
                    return _response(_valid(task))
                return _response(_invalid(task))
        return _response("{}")

    def local(_: str) -> WorkerResponse:
        calls["local_teacher"] += 1
        return _response('{"teacher_diagnosis":"local diagnostic","retry_guidance":"preserve the recorded boundary"}', model="local-teacher")

    def external(_: str):
        calls["external_teacher"] += 1
        return "codex-fixture", json.dumps({"failure_classification": "scope_boundary", "teacher_diagnosis": "external diagnostic", "retry_guidance": "preserve allowed and held targets", "corrected_reference_output": {"allowed_targets": ["approved"], "held_targets": ["held"], "scope_expansion_required": False, "review_status": "review_only"}})

    return worker, local, external


def test_run8_fixture_pack_is_fresh_and_intervention_blind():
    manifest = verify_manifest(PACK, ROOT)
    assert manifest["candidate_count"] == 24
    assert manifest["target_included_count"] == 20
    assert manifest["pair_order"]["seed"] == 20260827
    assert manifest["target_evidence_resolution"] == "failure_class"
    audit = json.loads((PACK / "novelty_audit.json").read_text())
    assert audit["model_outputs_consulted"] is False
    assert audit["counts"]["new_source"] == 24
    assert not audit["task_id_collisions"]
    assert not audit["exact_prompt_duplicates"]
    assert not audit["normalized_prompt_duplicates"]
    assert not audit["high_similarity_pairs"]
    assert all(value == "new_source" for value in audit["novelty_classification"].values())


def test_run8_policy_repair_binding_and_break_even_are_frozen():
    verify_policy()
    prereg = json.loads(PREREG.read_text())
    assert prereg["repair_freeze"]["repaired_driver_sha256"] == repaired.sha256_file(ROOT / "scripts/zth_run7_scope_escalation.py")
    assert prereg["historical_run7"]["preregistration_sha256"] == "1c45ce7be83194d4adfb5cf1af6b04d90495712b6779956bc6f7691ac4055de6"
    assert prereg["historical_run7"]["driver_sha256"] == "f1bdac815109a2dce473529ae14ddc24d60b048b74f3268e25fa6f9d9b1ad547"
    assert prereg["driver"]["sha256"] == repaired.sha256_file(ROOT / "scripts/zth_run8_scope_escalation.py")
    assert break_even_escalation_count() == 7
    budget = prereg["planning_budget"]
    assert budget["maximum_calls"] == {"worker": 84, "external_teacher": 40, "local_teacher": 20, "total": 144}
    assert budget["all_local_pass_calls"] == {"worker": 64, "external_teacher": 20, "local_teacher": 20, "total": 104}
    assert budget["all_escalate_calls"] == {"worker": 84, "external_teacher": 40, "local_teacher": 20, "total": 144}
    assert budget["break_even_escalation_count"] == 7
    assert budget["break_even_escalation_rate"] == 0.35
    assert 20 * LOCAL_ACTION_MS + 7 * EXTERNAL_ACTION_MS < 20 * EXTERNAL_ACTION_MS
    assert 20 * LOCAL_ACTION_MS + 8 * EXTERNAL_ACTION_MS >= 20 * EXTERNAL_ACTION_MS


def test_run8_dry_run_is_zero_call_and_historical_binding_is_separate():
    result = subprocess.run(["python3", "scripts/zth_run8_scope_escalation.py", "--preregistration", str(PREREG), "--output-dir", "/tmp/run8-scope-dry"], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"control": "external_direct", "model_calls": 0, "pair_order_seed": 20260827, "status": "dry_run_valid", "treatment": "validation_gated_economic_escalation"}
    historical = subprocess.run(["python3", "scripts/zth_run7_scope_escalation.py", "--preregistration", str(HISTORICAL_PREREG), "--output-dir", "/tmp/run8-historical-mismatch"], cwd=ROOT, capture_output=True, text=True)
    assert historical.returncode != 0
    assert "Run 7 driver binding mismatch" in historical.stderr


def test_run8_repaired_escalation_contract_and_artifact_integrity(tmp_path: Path):
    context = _context(); calls = {"worker": 0, "local_teacher": 0, "external_teacher": 0}; worker, local, external = _callbacks(context, calls); output = tmp_path / "all-escalate"
    result = repaired.run_experiment(context, output, worker=worker, local_teacher=local, external_teacher=external)
    assert result["status"] == "experiment_completed"
    assert calls == {"worker": 84, "local_teacher": 20, "external_teacher": 40}
    escalation = next((output / "tasks" / "scope").glob("*/escalation"))
    teacher_prompt = json.loads((escalation / "external_teacher.prompt.txt").read_text())
    retry_prompt = json.loads((escalation / "worker-retry.prompt.txt").read_text())
    intervention = retry_prompt["intervention"]
    assert teacher_prompt["failed_transitions"][1]["intervention_id"] == "local_first"
    assert intervention["teacher_parse_status"] == "passed"
    assert intervention["retry_guidance"]
    assert isinstance(intervention["corrected_reference_output"]["allowed_targets"], list)
    assert isinstance(intervention["corrected_reference_output"]["held_targets"], list)
    assert isinstance(intervention["corrected_reference_output"]["scope_expansion_required"], bool)
    assert isinstance(intervention["corrected_reference_output"]["review_status"], str)
    assert set(intervention) != {"teacher_parse_status"}
    assert (escalation / "baseline_reference.json").exists()
    assert "baseline_reference.json" in json.loads((escalation / "arm_artifacts.json").read_text())["files"]

    indexed = [p for p in escalation.iterdir() if p.name not in {"arm_artifacts.json"}]
    indexed[0].write_text(indexed[0].read_text() + "\ncorrupt\n")
    manifest = json.loads((output / "execution_manifest.json").read_text()); manifest.pop("completed_at"); manifest["status"] = "experiment_running"; (output / "execution_manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(Run4ADriverError, match="artifact hash mismatch"):
        repaired.run_experiment(context, output, worker=lambda _: (_ for _ in ()).throw(AssertionError("duplicate worker")), local_teacher=lambda _: (_ for _ in ()).throw(AssertionError("duplicate local")), external_teacher=lambda _: (_ for _ in ()).throw(AssertionError("duplicate external")))


def test_run8_local_pass_branch_has_no_escalation(tmp_path: Path):
    context = _context(); calls = {"worker": 0, "local_teacher": 0, "external_teacher": 0}; worker, local, external = _callbacks(context, calls, local_pass=True)
    repaired.run_experiment(context, tmp_path / "all-pass", worker=worker, local_teacher=local, external_teacher=external)
    assert calls == {"worker": 64, "local_teacher": 20, "external_teacher": 20}
    assert not list((tmp_path / "all-pass" / "tasks" / "scope").glob("*/escalation/arm_summary.json"))


def test_run8_parser_never_collapses_repaired_guidance_to_status_only():
    parsed = _parse_teacher(json.dumps({"failure_classification": "scope_boundary", "teacher_diagnosis": "diagnosis", "retry_guidance": "guidance", "corrected_reference_output": {"allowed_targets": ["a"], "held_targets": ["b"], "scope_expansion_required": False, "review_status": "review_only"}}))
    assert parsed["teacher_parse_status"] == "passed"
    assert parsed["teacher_diagnosis"] == "diagnosis"
    assert parsed["retry_guidance"] == "guidance"
    assert set(parsed) != {"teacher_parse_status"}
