from __future__ import annotations

import json
from pathlib import Path

import pytest

import local_harness.supervised_capability_loop as loop
from local_harness.icm_spec import WorkerResponse
from local_harness.prompt_patch_library import PromptPatchLibrary
from local_harness.supervised_capability_loop import aggregate_scorecard, run_capability_loop


def response(content: str, model: str) -> WorkerResponse:
    return WorkerResponse("ok", content, "http://fixture/v1/chat/completions", model, model, "stop", {"completion_tokens": 5}, {"total_ms": 1}, {})


def task() -> dict:
    return {"task_id": "task-001", "task_family": "json-fixture", "prompt": "Return JSON.", "output_contract": {"format": "json"}, "expected_output": {"answer": "ok"}}


def teacher_payload(corrected: bool = True) -> str:
    payload = {"failure_classification": "wrong_reference", "teacher_diagnosis": "Use the bounded reference.", "retry_guidance": "Return JSON only."}
    if corrected:
        payload["corrected_reference_output"] = {"answer": "ok"}
    return json.dumps(payload)


def records(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_worker_success_without_escalation(tmp_path: Path):
    calls: list[str] = []
    result = run_capability_loop(task(), out_dir=tmp_path, worker=lambda p: (calls.append(p) or response('{"answer":"ok"}', "small-1.7b")), local_teacher=lambda p: pytest.fail("teacher called"))
    assert result["disposition"] == "ready_for_review"
    assert result["successful_intervention_source"] == "none"
    assert result["intervention_outcome"] == "no-effect"
    assert len(calls) == 1


def test_teacher_sees_output_validation_and_previous_retry(tmp_path: Path):
    outputs = iter(['{"answer":"wrong"}', '{"answer":"wrong"}', '{"answer":"ok"}'])
    prompts: list[dict] = []
    def teacher(p: str) -> WorkerResponse:
        prompts.append(json.loads(p))
        return response(teacher_payload(), "large-30b")
    result = run_capability_loop(task(), out_dir=tmp_path, worker=lambda p: response(next(outputs), "small-1.7b"), local_teacher=teacher, max_worker_attempts=2, max_teacher_passes=2)
    assert result["successful_intervention_source"] == "local_teacher"
    assert len(prompts) == 1
    assert prompts[0]["failed_transitions"][0]["raw_output"] == '{"answer":"wrong"}'
    assert prompts[0]["failed_transitions"][0]["validation"]["diagnostics"]
    assert prompts[0]["task"]["output_contract"] == task()["output_contract"]
    assert any(r.get("record_type") == "worker_attempt" and r["validation"]["validation_status"] == "passed" for r in records(tmp_path / "trajectory.jsonl"))


def test_two_local_teacher_passes_are_distinct_and_exactly_once(tmp_path: Path):
    worker_calls = 0
    teacher_calls = 0
    outputs = iter(['{"answer":"wrong"}', '{"answer":"wrong"}', '{"answer":"ok"}'])
    def worker(p):
        nonlocal worker_calls
        worker_calls += 1
        return response(next(outputs), "small-1.7b")
    def teacher(p):
        nonlocal teacher_calls
        teacher_calls += 1
        return response(teacher_payload(), "large-30b")
    result = run_capability_loop(task(), out_dir=tmp_path, worker=worker, local_teacher=teacher, max_worker_attempts=1, max_teacher_passes=2)
    assert result["successful_intervention_source"] == "local_teacher"
    assert worker_calls == 3
    assert teacher_calls == 2
    rows = records(tmp_path / "trajectory.jsonl")
    teachers = [r for r in rows if r.get("record_type") == "transition" and r.get("transition") == "local_teacher_response_captured"]
    retries = [r for r in rows if r.get("record_type") == "worker_attempt" and r.get("intervention_source") == "local_teacher"]
    assert [r["attempt"] for r in teachers] == [1, 2]
    assert [r["intervention_id"] for r in retries] == ["local_teacher:1", "local_teacher:2"]
    assert [r["validation"]["validation_status"] for r in retries] == ["failed", "passed"]
    assert [e["subsequent_worker_result"] for e in result["candidate_curriculum_examples"]] == ["failed", "passed"]


def test_local_teacher_exhausted_then_external_resolution(tmp_path: Path):
    outputs = iter(['{"answer":"wrong"}', '{"answer":"wrong"}', '{"answer":"ok"}'])
    external_prompts: list[dict] = []
    def external(p: str):
        external_prompts.append(json.loads(p))
        payload = json.loads(teacher_payload())
        payload["candidate_prompt_patch"] = {"patch_id": "external-candidate", "title": "candidate", "status": "candidate", "failure_signature": ["wrong"], "applies_to": {"stage": ["validation"], "task_type": ["json-fixture"], "model_size": ["small"]}, "prompt_delta": "Use the bounded reference.", "required_output_fields": ["answer"], "validator_expectations": ["exact"]}
        return "codex-test", json.dumps(payload)
    result = run_capability_loop(task(), out_dir=tmp_path, worker=lambda p: response(next(outputs), "small-1.7b"), local_teacher=lambda p: response(teacher_payload(False), "large-30b"), external_teacher=external, max_worker_attempts=1, max_teacher_passes=1)
    assert result["successful_intervention_source"] == "external_teacher"
    assert result["pass_after_local_teacher_intervention"] is False
    assert result["pass_after_external_teacher_intervention"] is True
    assert result["candidate_prompt_patches"][0]["patch_id"] == "external-candidate"
    assert result["candidate_curriculum_examples"][0]["subsequent_worker_result"] == "passed"
    assert any(item.get("validation", {}).get("validation_status") == "failed" for item in external_prompts[0]["failed_transitions"])


def test_external_teacher_unavailable_fails_closed(tmp_path: Path):
    result = run_capability_loop(task(), out_dir=tmp_path, worker=lambda p: response('{"answer":"wrong"}', "small-1.7b"), max_worker_attempts=1, max_teacher_passes=0, external_teacher=lambda p: (_ for _ in ()).throw(RuntimeError("not configured")))
    assert result["disposition"] == "unresolved"
    assert any(r.get("transition") == "external_teacher_unavailable" for r in records(tmp_path / "trajectory.jsonl"))


def test_existing_patch_is_retrieved_applied_and_hashed(tmp_path: Path):
    patch = {"patch_id": "p1", "title": "patch", "status": "active", "failure_signature": ["wrong"], "applies_to": {"stage": ["validation"], "task_type": ["json-fixture"], "model_size": ["small"]}, "prompt_delta": "Be exact.", "required_output_fields": ["answer"], "validator_expectations": ["exact"]}
    library = PromptPatchLibrary(); library.add_patch(patch)
    prompts: list[str] = []
    outputs = iter(['{"answer":"wrong"}', '{"answer":"ok"}'])
    result = run_capability_loop(task(), out_dir=tmp_path, patch_library=library, existing_patch_ids=["p1"], worker=lambda p: (prompts.append(p) or response(next(outputs), "small-1.7b")), max_worker_attempts=1, max_teacher_passes=0, external_teacher=lambda p: (_ for _ in ()).throw(RuntimeError("off")))
    assert result["pass_after_existing_patch"] is True
    worker_records = [r for r in records(tmp_path / "trajectory.jsonl") if r.get("record_type") == "worker_attempt"]
    assert worker_records[0]["intervention_source"] == "none"
    assert worker_records[1]["intervention_source"] == "existing_patch"
    assert worker_records[1]["applied_patch_ids"] == ["p1"]
    assert worker_records[1]["applied_patch_hashes"]["p1"]
    assert "Be exact." not in prompts[0] and "Be exact." in prompts[1]


def test_inapplicable_existing_patch_is_rejected(tmp_path: Path):
    patch = {"patch_id": "p1", "title": "patch", "status": "active", "failure_signature": ["wrong"], "applies_to": {"stage": ["review"], "task_type": ["json-fixture"], "model_size": ["small"]}, "prompt_delta": "Be exact.", "required_output_fields": ["answer"], "validator_expectations": ["exact"]}
    library = PromptPatchLibrary(); library.add_patch(patch)
    with pytest.raises(ValueError, match="not applicable"):
        run_capability_loop(task(), out_dir=tmp_path, patch_library=library, existing_patch_ids=["p1"], worker=lambda p: response('{"answer":"ok"}', "small"))


def test_zth_validator_adapter_is_explicit_and_not_model_selected(tmp_path: Path):
    fixture = {**task(), "validator": {"kind": "zth_output_contract", "authorized_targets": [], "reference_facts": {"scope": "bounded"}}, "triage_id": "triage-1", "orchestration_id": "orch-1", "prompt_packet_id": "prompt-1"}
    result = run_capability_loop(fixture, out_dir=tmp_path, worker=lambda p: response('{"allowed_targets": [], "held_targets": [], "reason": "ok"}', "small"), max_worker_attempts=1)
    assert result["disposition"] == "ready_for_review"
    validation = json.loads((tmp_path / "attempt-1.validation.json").read_text())
    assert validation["validator"] if "validator" in validation else validation["validation_status"] == "passed"


def test_retry_ceiling_and_no_self_acceptance(tmp_path: Path):
    calls = 0
    def worker(p):
        nonlocal calls
        calls += 1
        return response("not-json", "small")
    result = run_capability_loop(task(), out_dir=tmp_path, worker=worker, max_worker_attempts=3, max_teacher_passes=0, external_teacher=lambda p: (_ for _ in ()).throw(RuntimeError("off")))
    assert calls == 3 and result["disposition"] == "unresolved"
    assert all(r.get("review_state") != "accepted" for r in records(tmp_path / "trajectory.jsonl"))


@pytest.mark.parametrize("case", [
    "existing_patch_validation",
    "local_teacher_1_validation",
    "local_teacher_2_response",
    "successful_local_retry",
    "external_worker_validation",
])
def test_restart_recovery_preserves_exact_model_call_counts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str):
    outputs = iter(['{"answer":"wrong"}', '{"answer":"ok"}'] if case in {"successful_local_retry", "existing_patch_validation"} else ['{"answer":"wrong"}', '{"answer":"wrong"}', '{"answer":"ok"}'])
    worker_calls = 0
    local_calls = 0
    external_calls = 0
    patch_library = None
    patch_ids = []
    if case == "existing_patch_validation":
        patch = {"patch_id": "p1", "title": "patch", "status": "active", "failure_signature": ["wrong"], "applies_to": {"stage": ["validation"], "task_type": ["json-fixture"], "model_size": ["small"]}, "prompt_delta": "Be exact.", "required_output_fields": ["answer"], "validator_expectations": ["exact"]}
        patch_library = PromptPatchLibrary(); patch_library.add_patch(patch); patch_ids = ["p1"]
    original = loop._transition
    interrupted = {"done": False}
    def flaky(path, **kwargs):
        result = original(path, **kwargs)
        should_interrupt = (
            case == "existing_patch_validation" and kwargs.get("transition") == "worker_output_validated" and kwargs.get("intervention_id") == "existing_patch:1"
        ) or (
            case == "local_teacher_1_validation" and kwargs.get("transition") == "worker_output_validated" and kwargs.get("intervention_id") == "local_teacher:1"
        ) or (
            case == "local_teacher_2_response" and kwargs.get("transition") == "local_teacher_response_captured" and kwargs.get("attempt") == 2
        ) or (
            case == "successful_local_retry" and kwargs.get("transition") == "local_teacher_retry_completed"
        ) or (
            case == "external_worker_validation" and kwargs.get("transition") == "worker_output_validated" and kwargs.get("intervention_id") == "external_teacher:1"
        )
        if should_interrupt and not interrupted["done"]:
            interrupted["done"] = True
            raise RuntimeError("simulated interruption")
        return result
    monkeypatch.setattr(loop, "_transition", flaky)
    def worker(p):
        nonlocal worker_calls
        worker_calls += 1
        return response(next(outputs), "small")
    def local(p):
        nonlocal local_calls
        local_calls += 1
        return response(teacher_payload(), "large")
    def external(p):
        nonlocal external_calls
        external_calls += 1
        return "codex", teacher_payload()
    kwargs = dict(worker=worker, local_teacher=local, external_teacher=external, max_worker_attempts=1, max_teacher_passes=2, patch_library=patch_library, existing_patch_ids=patch_ids)
    if case == "external_worker_validation":
        kwargs["max_teacher_passes"] = 0
    if case == "existing_patch_validation":
        kwargs["max_teacher_passes"] = 0
    with pytest.raises(RuntimeError):
        run_capability_loop(task(), out_dir=tmp_path, **kwargs)
    monkeypatch.setattr(loop, "_transition", original)
    result = run_capability_loop(task(), out_dir=tmp_path, **kwargs)
    assert result["disposition"] in {"ready_for_review", "unresolved"}
    expected = {
        "existing_patch_validation": (2, 0, 0),
        "local_teacher_1_validation": (3, 2, 0),
        "local_teacher_2_response": (3, 2, 0),
        "successful_local_retry": (2, 1, 0),
        "external_worker_validation": (2, 0, 1),
    }[case]
    assert (worker_calls, local_calls, external_calls) == expected
    worker_records = [r for r in records(tmp_path / "trajectory.jsonl") if r.get("record_type") == "worker_attempt"]
    assert all(json.loads((tmp_path / r["artifact_refs"]["metadata"]).read_text())["intervention_id"] == r["intervention_id"] for r in worker_records)
    terminal = [r for r in records(tmp_path / "trajectory.jsonl") if r.get("transition") in {"ready_for_review", "unresolved"}]
    assert len(terminal) == 1


def test_scorecard_attributes_sources_and_curriculum_evidence(tmp_path: Path):
    run_capability_loop(task(), out_dir=tmp_path / "one", worker=lambda p: response('{"answer":"ok"}', "small"), max_worker_attempts=1)
    scorecard = aggregate_scorecard([tmp_path / "one" / "trajectory.jsonl"])
    assert scorecard["by_intervention_source"]["none"]["passes"] == 1
    assert scorecard["intervention_no_effect"] == 1
    assert "candidate_curriculum_examples" in scorecard


def test_scorecard_counts_only_durable_worker_intervention_sources(tmp_path: Path):
    patch = {"patch_id": "p1", "title": "patch", "status": "active", "failure_signature": ["wrong"], "applies_to": {"stage": ["validation"], "task_type": ["json-fixture"], "model_size": ["small"]}, "prompt_delta": "Be exact.", "required_output_fields": ["answer"], "validator_expectations": ["exact"]}
    library = PromptPatchLibrary(); library.add_patch(patch)
    result = run_capability_loop(task(), out_dir=tmp_path / "baseline", patch_library=library, existing_patch_ids=["p1"], worker=lambda p: response('{"answer":"ok"}', "small"), max_worker_attempts=1, max_teacher_passes=1)
    assert result["intervention_attempts"] == {"none": True, "existing_patch": False, "local_teacher": False, "external_teacher": False}

    outputs = iter(['{"answer":"wrong"}', '{"answer":"wrong"}'])
    result = run_capability_loop(
        task(),
        out_dir=tmp_path / "escalated",
        worker=lambda p: response(next(outputs), "small"),
        local_teacher=lambda p: response(teacher_payload(False), "large"),
        external_teacher=lambda p: (_ for _ in ()).throw(RuntimeError("unavailable")),
        max_worker_attempts=1,
        max_teacher_passes=1,
    )
    assert result["intervention_attempts"] == {"none": True, "existing_patch": False, "local_teacher": True, "external_teacher": False}
    assert result["external_escalation_count"] == 1
    assert result["external_teacher_call_count"] == 1

    scorecard = aggregate_scorecard([tmp_path / "baseline" / "trajectory.jsonl", tmp_path / "escalated" / "trajectory.jsonl"])
    assert scorecard["by_intervention_source"]["none"]["trials"] == 2
    assert scorecard["by_intervention_source"]["existing_patch"]["trials"] == 0
    assert scorecard["by_intervention_source"]["local_teacher"]["trials"] == 1
    assert scorecard["external_escalation_count"] == 1
    assert scorecard["external_teacher_call_count"] == 1
