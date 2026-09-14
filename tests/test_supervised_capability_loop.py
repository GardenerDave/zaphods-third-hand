from __future__ import annotations

import json
import hashlib
import subprocess
from pathlib import Path

import pytest

import local_harness.supervised_capability_loop as loop
from local_harness.icm_call import _render_request_payload
from local_harness.icm_spec import WorkerResponse, resolve_worker_spec
from local_harness.binding_preflight import preflight_worker_binding
from local_harness.prompt_patch_library import PromptPatchLibrary
from local_harness.supervised_capability_loop import aggregate_scorecard, binding_preflight_from_fleet_snapshot, run_capability_loop


def response(content: str, model: str) -> WorkerResponse:
    return WorkerResponse("ok", content, "http://fixture/v1/chat/completions", model, model, "stop", {"completion_tokens": 5}, {"total_ms": 1}, {})


def transport_response(status: str, error: str) -> WorkerResponse:
    return WorkerResponse(status, f"[{status}]", "http://fixture/v1/chat/completions", None, "small-1.7b", None, None, None, None, error=error)


def task() -> dict:
    return {"task_id": "task-001", "task_family": "json-fixture", "prompt": "Return JSON.", "output_contract": {"format": "json"}, "expected_output": {"answer": "ok"}}


def teacher_payload(corrected: bool = True) -> str:
    payload = {"failure_classification": "wrong_reference", "teacher_diagnosis": "Use the bounded reference.", "retry_guidance": "Return JSON only."}
    if corrected:
        payload["corrected_reference_output"] = {"answer": "ok"}
    return json.dumps(payload)


def counting_task() -> dict:
    """Fixture whose hidden expected output carries the counting values 18 and 8.

    The values 18 and 8 live solely in ``expected_output`` (the ``exact_json``
    validator has no ``reference_facts``), mirroring the frozen dogfood counting
    fixture. These are the values the reference-bearing detector must flag when a
    teacher's free text discloses them.
    """
    return {
        "task_id": "task-count-18",
        "task_family": "json-fixture",
        "prompt": "Count the fields. Return JSON.",
        "output_contract": {"format": "json"},
        "expected_output": {"field_count": 18, "usage_count": 8},
    }


COUNTING_CORRECTED = {"field_count": 18, "usage_count": 8}


def records(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_worker_success_without_escalation(tmp_path: Path):
    calls: list[str] = []
    result = run_capability_loop(task(), out_dir=tmp_path, worker=lambda p: (calls.append(p) or response('{"answer":"ok"}', "small-1.7b")), local_teacher=lambda p: pytest.fail("teacher called"))
    assert result["disposition"] == "ready_for_review"
    assert result["successful_intervention_source"] == "none"
    assert result["intervention_outcome"] == "no-effect"
    assert len(calls) == 1


def test_binding_preflight_blocks_unverified_capability_attempt(tmp_path: Path):
    worker_calls = 0

    def worker(_prompt):
        nonlocal worker_calls
        worker_calls += 1
        return response('{"answer":"ok"}', "small-1.7b")

    result = run_capability_loop(
        task(),
        out_dir=tmp_path,
        worker=worker,
        local_teacher=lambda _p: pytest.fail("teacher must not be called"),
        max_worker_attempts=1,
        max_teacher_passes=0,
        binding_preflight=lambda: {
            "schema": "zth_worker_binding_preflight_v1",
            "worker": "router",
            "configured_base_url": "http://127.0.0.1:8081/v1",
            "expected_model": "Qwen_Qwen3-1.7B-Q4_K_M.gguf",
            "endpoint_status": "ok",
            "advertised_models": ["wrong-model"],
            "binding_status": "UNVERIFIED",
            "failure_class": "expected_model_not_advertised",
            "reason": "expected model missing",
            "checked_at": "2026-09-08T00:00:00+00:00",
            "evidence": {"models_url": "http://127.0.0.1:8081/v1/models", "http_status": 200, "response_sha256": "0" * 64},
        },
    )
    assert result["capability_verdict_available"] is False
    assert result["disposition"] == "infrastructure_error"
    assert worker_calls == 0
    assert (tmp_path / "binding_preflight.json").is_file()
    saved = json.loads((tmp_path / "binding_preflight.json").read_text())
    assert saved["binding_status"] == "UNVERIFIED"


def fleet_snapshot(binding_status: str = "VERIFIED", availability: str = "AVAILABLE", failure_class: str = "binding_verified") -> dict:
    return {
        "schema": "zth_local_fleet_snapshot_v1",
        "generated_at": "2026-09-08T00:00:01+00:00",
        "workers": [
            {
                "worker": "router",
                "configured_base_url": "http://127.0.0.1:8081/v1",
                "expected_model": "small-1.7b",
                "binding_status": binding_status,
                "availability": availability,
                "advertised_models": ["small-1.7b"] if availability == "AVAILABLE" else [],
                "failure_class": failure_class,
                "checked_at": "2026-09-08T00:00:00+00:00",
                "evidence": {
                    "preflight": {
                        "schema": "zth_worker_binding_preflight_v1",
                        "worker": "router",
                        "configured_base_url": "http://127.0.0.1:8081/v1",
                        "expected_model": "small-1.7b",
                        "endpoint_status": "ok" if availability == "AVAILABLE" else "error",
                        "advertised_models": ["small-1.7b"] if availability == "AVAILABLE" else [],
                        "binding_status": binding_status,
                        "failure_class": failure_class,
                        "reason": "fixture",
                        "checked_at": "2026-09-08T00:00:00+00:00",
                        "evidence": {"models_url": "http://127.0.0.1:8081/v1/models", "http_status": 200 if availability == "AVAILABLE" else None, "response_sha256": "0" * 64},
                    }
                },
            }
        ],
    }


def test_supplied_fleet_snapshot_blocks_unavailable_worker_without_worker_call(tmp_path: Path):
    worker_calls = 0

    def worker(_prompt):
        nonlocal worker_calls
        worker_calls += 1
        return response('{"answer":"ok"}', "small-1.7b")

    result = run_capability_loop(
        task(),
        out_dir=tmp_path,
        worker=worker,
        local_teacher=lambda _p: pytest.fail("teacher must not be called"),
        max_worker_attempts=1,
        max_teacher_passes=0,
        fleet_snapshot=fleet_snapshot(binding_status="UNVERIFIED", availability="UNAVAILABLE", failure_class="connection_refused"),
        fleet_worker_name="router",
    )
    assert worker_calls == 0
    assert result["capability_verdict_available"] is False
    assert result["binding_preflight"]["failure_class"] == "connection_refused"
    assert result["fleet_snapshot_reference"]["artifact"] == "fleet_snapshot"
    assert (tmp_path / "fleet_snapshot.json").is_file()


def test_supplied_verified_fleet_snapshot_reuses_preflight_and_allows_worker_call(tmp_path: Path):
    calls = []
    result = run_capability_loop(
        task(),
        out_dir=tmp_path,
        worker=lambda p: (calls.append(p) or response('{"answer":"ok"}', "small-1.7b")),
        local_teacher=lambda _p: pytest.fail("teacher must not be called"),
        max_worker_attempts=1,
        max_teacher_passes=0,
        fleet_snapshot=fleet_snapshot(),
        fleet_worker_name="router",
    )
    assert result["capability_verdict_available"] is True
    assert result["fleet_snapshot_reference"]["artifact"] == "fleet_snapshot"
    assert json.loads((tmp_path / "binding_preflight.json").read_text())["binding_status"] == "VERIFIED"
    assert len(calls) == 1


def test_binding_preflight_from_fleet_snapshot_reports_missing_worker():
    preflight = binding_preflight_from_fleet_snapshot(fleet_snapshot(), "missing")
    assert preflight["binding_status"] == "UNVERIFIED"
    assert preflight["failure_class"] == "fleet_worker_not_found"


@pytest.mark.parametrize(
    ("error", "classification"),
    [
        (subprocess.TimeoutExpired("fake", 1), "external_teacher_timeout"),
        (RuntimeError("external teacher command failed with exit code 7"), "external_teacher_nonzero_exit"),
        (OSError("launch denied"), "external_teacher_launch_failure"),
        (RuntimeError("external teacher returned an empty response"), "external_teacher_empty_response"),
    ],
)
def test_external_infrastructure_failure_is_durable_and_not_capability_failure(tmp_path: Path, error, classification):
    outputs = iter(['{"answer":"wrong"}', '{"answer":"wrong"}'])

    def worker(_prompt):
        return response(next(outputs), "small-1.7b")

    def teacher(_prompt):
        return response(teacher_payload(False), "large-30b")

    def external(_prompt):
        raise error

    result = run_capability_loop(task(), out_dir=tmp_path, worker=worker, local_teacher=teacher, external_teacher=external, max_worker_attempts=1, max_teacher_passes=1)
    artifact = json.loads((tmp_path / "external-teacher.infrastructure.json").read_text())
    assert artifact["classification"] == classification
    assert artifact["response_present"] is False
    assert artifact["capability_verdict_available"] is False
    assert result["capability_verdict_available"] is False
    assert result["unresolved"] is False
    rows = records(tmp_path / "trajectory.jsonl")
    assert any(r.get("transition") == "external_teacher_infrastructure_failed" for r in rows)
    assert not (tmp_path / "external-teacher.json").exists()


def test_completed_external_response_is_reused_without_another_call(tmp_path: Path):
    outputs = iter(['{"answer":"wrong"}', '{"answer":"ok"}'])
    external_calls = []

    def worker(_prompt):
        return response(next(outputs), "small-1.7b")

    def external(_prompt):
        external_calls.append(1)
        return "codex-cli-0.146.0", teacher_payload(False)

    first = run_capability_loop(task(), out_dir=tmp_path, worker=worker, local_teacher=lambda _p: pytest.fail("local teacher called"), external_teacher=external, max_worker_attempts=1, max_teacher_passes=0)
    assert first["successful_intervention_source"] == "external_teacher"
    assert len(external_calls) == 1
    second = run_capability_loop(task(), out_dir=tmp_path, worker=lambda _p: pytest.fail("worker duplicated"), external_teacher=lambda _p: pytest.fail("external duplicated"), max_worker_attempts=1, max_teacher_passes=0)
    assert second["pass"] is True
    assert len(external_calls) == 1


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


def test_guidance_only_teacher_payload_strips_reference_keeps_guidance():
    from local_harness.supervised_capability_loop import _guidance_only_teacher_payload
    payload = {
        "failure_classification": "prompt_contract_gap",
        "teacher_diagnosis": "Use the bounded reference.",
        "retry_guidance": "Return JSON only.",
        "corrected_reference_output": {"answer": "ok"},
        "candidate_prompt_patch": {"instruction": "Return JSON."},
        "candidate_prompt_patch_raw": "not json",
        "teacher_parse_status": "parsed_json",
    }
    stripped = _guidance_only_teacher_payload(payload)
    assert stripped["failure_classification"] == "prompt_contract_gap"
    assert stripped["teacher_diagnosis"] == "Use the bounded reference."
    assert stripped["retry_guidance"] == "Return JSON only."
    assert stripped["teacher_parse_status"] == "parsed_json"
    assert "corrected_reference_output" not in stripped
    assert "candidate_prompt_patch" not in stripped
    assert "candidate_prompt_patch_raw" not in stripped
    assert _guidance_only_teacher_payload("raw text") == "raw text"
    assert _guidance_only_teacher_payload(None) is None


def test_local_teacher_retry_prompt_carries_no_reference(tmp_path: Path):
    outputs = iter(['{"answer":"wrong"}', '{"answer":"ok"}'])
    prompts: list[str] = []

    def worker(p: str) -> WorkerResponse:
        prompts.append(p)
        return response(next(outputs), "small-1.7b")

    def teacher(p: str) -> WorkerResponse:
        return response(teacher_payload(True), "large-30b")

    result = run_capability_loop(task(), out_dir=tmp_path, worker=worker, local_teacher=teacher, max_worker_attempts=1, max_teacher_passes=1)
    assert result["successful_intervention_source"] == "local_teacher"
    assert len(prompts) >= 2
    retry_prompt = prompts[1]
    assert "## Local teacher intervention" in retry_prompt
    assert "retry_guidance" in retry_prompt
    assert "teacher_diagnosis" in retry_prompt
    assert "failure_classification" in retry_prompt
    assert "corrected_reference_output" not in retry_prompt
    assert json.dumps(task()["expected_output"]) not in retry_prompt


def test_external_teacher_retry_prompt_carries_no_reference(tmp_path: Path):
    outputs = iter(['{"answer":"wrong"}', '{"answer":"ok"}'])
    prompts: list[str] = []

    def worker(p: str) -> WorkerResponse:
        prompts.append(p)
        return response(next(outputs), "small-1.7b")

    def external(p: str):
        return "codex-cli-0.146.0", teacher_payload(True)

    result = run_capability_loop(task(), out_dir=tmp_path, worker=worker, local_teacher=lambda _p: pytest.fail("local teacher called"), external_teacher=external, max_worker_attempts=1, max_teacher_passes=0)
    assert result["successful_intervention_source"] == "external_teacher"
    assert len(prompts) >= 2
    external_retry_prompt = prompts[-1]
    assert "## External teacher intervention" in external_retry_prompt
    assert "retry_guidance" in external_retry_prompt
    assert "teacher_diagnosis" in external_retry_prompt
    assert "corrected_reference_output" not in external_retry_prompt
    assert json.dumps(task()["expected_output"]) not in external_retry_prompt


def test_local_teacher_guidance_only_when_diagnosis_hides_answer(tmp_path: Path):
    # (a) A diagnosis that explains the counting mistake WITHOUT revealing the
    # hidden expected count (18/8) is method guidance: it stays usable in the
    # worker retry prompt and the intervention is classified guidance_only.
    prompts: list[str] = []

    def worker(p: str) -> WorkerResponse:
        prompts.append(p)
        return response(next(outputs), "small-1.7b")

    outputs = iter(['{"field_count":11,"usage_count":7}', '{"field_count":18,"usage_count":8}'])
    diagnosis = (
        "The model undercounts the first list, losing track partway through "
        "enumeration of the longer list. This is a known limitation of small "
        "quantized models on sequential counting, not a prompt ambiguity."
    )
    payload = {
        "failure_classification": "model_counting_error",
        "teacher_diagnosis": diagnosis,
        "retry_guidance": "Count the items twice: once in order and once reversed, and report the value that both passes agree on.",
        "corrected_reference_output": COUNTING_CORRECTED,
    }

    result = run_capability_loop(counting_task(), out_dir=tmp_path, worker=worker, local_teacher=lambda p: response(json.dumps(payload), "large-30b"), max_worker_attempts=1, max_teacher_passes=1)
    assert result["successful_intervention_source"] == "local_teacher"
    assert result["teacher_intervention_mode"] == "guidance_only"
    assert len(prompts) >= 2
    retry_prompt = prompts[1]
    assert "## Local teacher intervention" in retry_prompt
    assert diagnosis in retry_prompt  # method guidance is preserved and usable
    assert "reference_withheld" not in retry_prompt
    assert "corrected_reference_output" not in retry_prompt
    assert "18" not in retry_prompt


def test_local_teacher_reference_rescue_withholds_diagnosis_answer(tmp_path: Path):
    # (b) A diagnosis that states "the correct 18" discloses a hidden expected
    # value. The worker retry prompt must NOT carry 18, the diagnosis field is
    # replaced with the neutral placeholder, and the intervention is classified
    # teacher_reference_rescue (never credited as new capability).
    prompts: list[str] = []

    def worker(p: str) -> WorkerResponse:
        prompts.append(p)
        return response(next(outputs), "small-1.7b")

    outputs = iter(['{"field_count":11,"usage_count":7}', '{"field_count":18,"usage_count":8}'])
    payload = {
        "failure_classification": "model_counting_error",
        "teacher_diagnosis": "The model reported 11 instead of the correct 18, losing track of the second list.",
        "retry_guidance": "Recount carefully and report the count you verify twice.",
        "corrected_reference_output": COUNTING_CORRECTED,
    }

    result = run_capability_loop(counting_task(), out_dir=tmp_path, worker=worker, local_teacher=lambda p: response(json.dumps(payload), "large-30b"), max_worker_attempts=1, max_teacher_passes=1)
    assert result["successful_intervention_source"] == "local_teacher"
    assert result["teacher_intervention_mode"] == "teacher_reference_rescue"
    assert len(prompts) >= 2
    retry_prompt = prompts[1]
    assert "18" not in retry_prompt  # the hidden answer must not leak to the worker
    assert "reference_withheld" in retry_prompt
    assert "corrected_reference_output" not in retry_prompt
    # method guidance that does not reveal a value is preserved
    assert "Recount carefully and report the count you verify twice." in retry_prompt
    # durable record retains the full original teacher response (provenance);
    # the classification itself rides on the summary, not the raw-evidence file.
    record = json.loads((tmp_path / "local-teacher-1.json").read_text())
    assert "the correct 18" in record["parsed"]["teacher_diagnosis"]
    assert record["parsed"]["corrected_reference_output"] == COUNTING_CORRECTED


def test_local_teacher_reference_rescue_withholds_retry_guidance_answer(tmp_path: Path):
    # (c) retry_guidance that embeds the exact expected JSON is reference-bearing:
    # the whole field is withheld and the mode is teacher_reference_rescue.
    prompts: list[str] = []

    def worker(p: str) -> WorkerResponse:
        prompts.append(p)
        return response(next(outputs), "small-1.7b")

    outputs = iter(['{"field_count":11,"usage_count":7}', '{"field_count":18,"usage_count":8}'])
    payload = {
        "failure_classification": "model_counting_error",
        "teacher_diagnosis": "The model loses track partway through enumeration.",
        "retry_guidance": "Report exactly {\"field_count\":18,\"usage_count\":8}.",
        "corrected_reference_output": COUNTING_CORRECTED,
    }

    result = run_capability_loop(counting_task(), out_dir=tmp_path, worker=worker, local_teacher=lambda p: response(json.dumps(payload), "large-30b"), max_worker_attempts=1, max_teacher_passes=1)
    assert result["teacher_intervention_mode"] == "teacher_reference_rescue"
    retry_prompt = prompts[1]
    assert "18" not in retry_prompt
    assert "reference_withheld" in retry_prompt
    assert "corrected_reference_output" not in retry_prompt
    # the method-only diagnosis (no hidden value) is preserved
    assert "The model loses track partway through enumeration." in retry_prompt


def test_local_teacher_paraphrased_method_guidance_is_allowed(tmp_path: Path):
    # (d) A paraphrased method description that references the field name and the
    # counting approach but reveals neither 18 nor 8 is guidance_only.
    prompts: list[str] = []

    def worker(p: str) -> WorkerResponse:
        prompts.append(p)
        return response(next(outputs), "small-1.7b")

    outputs = iter(['{"field_count":11,"usage_count":7}', '{"field_count":18,"usage_count":8}'])
    payload = {
        "failure_classification": "model_counting_error",
        "teacher_diagnosis": "The model conflates the two lists and reports a blended total rather than the per-list field count.",
        "retry_guidance": "Enumerate each list independently and emit one integer per field.",
        "corrected_reference_output": COUNTING_CORRECTED,
    }

    result = run_capability_loop(counting_task(), out_dir=tmp_path, worker=worker, local_teacher=lambda p: response(json.dumps(payload), "large-30b"), max_worker_attempts=1, max_teacher_passes=1)
    assert result["teacher_intervention_mode"] == "guidance_only"
    retry_prompt = prompts[1]
    # the full method diagnosis survives intact (naming the field is method guidance)
    assert "per-list field count" in retry_prompt
    assert "blended total" in retry_prompt
    assert "reference_withheld" not in retry_prompt
    assert "18" not in retry_prompt
    assert "corrected_reference_output" not in retry_prompt


def test_structured_corrected_reference_output_stays_withheld(tmp_path: Path):
    # (e) Regardless of free-text handling, the structured
    # corrected_reference_output is always withheld from the worker retry prompt
    # (existing behaviour preserved alongside the new detector).
    prompts: list[str] = []

    def worker(p: str) -> WorkerResponse:
        prompts.append(p)
        return response(next(outputs), "small-1.7b")

    outputs = iter(['{"field_count":11,"usage_count":7}', '{"field_count":18,"usage_count":8}'])
    payload = {
        "failure_classification": "model_counting_error",
        "teacher_diagnosis": "The model miscounts the second list.",
        "retry_guidance": "Recount each list independently.",
        "corrected_reference_output": COUNTING_CORRECTED,
    }

    result = run_capability_loop(counting_task(), out_dir=tmp_path, worker=worker, local_teacher=lambda p: response(json.dumps(payload), "large-30b"), max_worker_attempts=1, max_teacher_passes=1)
    assert result["teacher_intervention_mode"] == "guidance_only"
    retry_prompt = prompts[1]
    assert "corrected_reference_output" not in retry_prompt
    assert "18" not in retry_prompt  # the reference value is never in the worker prompt
    assert "reference_withheld" not in retry_prompt  # method-only guidance is not flagged


def test_teacher_record_retains_full_original_response(tmp_path: Path):
    # (f) The durable teacher record on disk preserves the full original teacher
    # response — including the answer-bearing diagnosis and the structured
    # reference — even though the worker-facing retry was sanitized.
    prompts: list[str] = []

    def worker(p: str) -> WorkerResponse:
        prompts.append(p)
        return response(next(outputs), "small-1.7b")

    outputs = iter(['{"field_count":11,"usage_count":7}', '{"field_count":18,"usage_count":8}'])
    diagnosis = "The correct value of field_count is 18, not 11."
    payload = {
        "failure_classification": "model_counting_error",
        "teacher_diagnosis": diagnosis,
        "retry_guidance": "Recount and verify twice.",
        "corrected_reference_output": COUNTING_CORRECTED,
    }

    result = run_capability_loop(counting_task(), out_dir=tmp_path, worker=worker, local_teacher=lambda p: response(json.dumps(payload), "large-30b"), max_worker_attempts=1, max_teacher_passes=1)
    assert result["teacher_intervention_mode"] == "teacher_reference_rescue"
    record = json.loads((tmp_path / "local-teacher-1.json").read_text())
    # full original free text retained
    assert record["parsed"]["teacher_diagnosis"] == diagnosis
    assert "18" in record["parsed"]["teacher_diagnosis"]
    # full structured reference retained
    assert record["parsed"]["corrected_reference_output"] == COUNTING_CORRECTED
    # mode is classified on the summary (the durable file is raw evidence only)
    assert result["teacher_intervention_mode"] == "teacher_reference_rescue"
    # but the worker never saw the answer
    assert "18" not in prompts[1]


def test_external_teacher_reference_rescue_withholds_answer(tmp_path: Path):
    # External-teacher path: an answer-bearing diagnosis is withheld from the
    # worker and the intervention is classified teacher_reference_rescue.
    prompts: list[str] = []

    def worker(p: str) -> WorkerResponse:
        prompts.append(p)
        return response(next(outputs), "small-1.7b")

    outputs = iter(['{"field_count":11,"usage_count":7}', '{"field_count":18,"usage_count":8}'])
    payload = {
        "failure_classification": "model_counting_error",
        "teacher_diagnosis": "The model reported 11 instead of the correct 18.",
        "retry_guidance": "Recount carefully.",
        "corrected_reference_output": COUNTING_CORRECTED,
    }

    result = run_capability_loop(
        counting_task(),
        out_dir=tmp_path,
        worker=worker,
        local_teacher=lambda _p: pytest.fail("local teacher called"),
        external_teacher=lambda p: ("codex-cli-0.146.0", json.dumps(payload)),
        max_worker_attempts=1,
        max_teacher_passes=0,
    )
    assert result["successful_intervention_source"] == "external_teacher"
    assert result["teacher_intervention_mode"] == "teacher_reference_rescue"
    retry_prompt = prompts[-1]
    assert "18" not in retry_prompt
    assert "reference_withheld" in retry_prompt
    assert "corrected_reference_output" not in retry_prompt
    record = json.loads((tmp_path / "external-teacher.json").read_text())
    # durable file retains the full original parsed response (provenance); the
    # intervention_mode classification lives in the trajectory summary, asserted above
    assert "the correct 18" in record["parsed"]["teacher_diagnosis"]
    assert record["parsed"]["corrected_reference_output"] == COUNTING_CORRECTED


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
    assert result["disposition"] == "infrastructure_error"
    assert result["capability_verdict_available"] is False
    assert result["unresolved"] is False
    assert any(r.get("transition") == "external_teacher_infrastructure_failed" for r in records(tmp_path / "trajectory.jsonl"))


def test_infrastructure_error_restart_is_idempotent(tmp_path: Path):
    """A run terminating in ``infrastructure_error`` must be skipped on restart.

    Before the fix, ``infrastructure_error`` was absent from
    ``TERMINAL_DISPOSITIONS``, so a restart on the same out_dir re-ran the worker
    and re-attempted the external teacher, re-incurring model/teacher cost and
    appending duplicate trajectory records. Treating ``infrastructure_error`` as
    terminal makes the idempotency check return the prior summary, so a restart
    performs no additional worker/teacher calls and adds no records.
    """
    worker_calls = 0
    external_calls = 0

    def worker(_p):
        nonlocal worker_calls
        worker_calls += 1
        return response('{"answer":"wrong"}', "small-1.7b")

    def external(_p):
        nonlocal external_calls
        external_calls += 1
        raise RuntimeError("not configured")

    kwargs = dict(worker=worker, max_worker_attempts=1, max_teacher_passes=0, external_teacher=external)
    first = run_capability_loop(task(), out_dir=tmp_path, **kwargs)
    assert first["disposition"] == "infrastructure_error"
    assert first["capability_verdict_available"] is False
    assert first["unresolved"] is False
    assert worker_calls == 1
    assert external_calls == 1
    first_records = records(tmp_path / "trajectory.jsonl")
    assert any(r.get("transition") == "external_teacher_infrastructure_failed" for r in first_records)
    assert (tmp_path / "external-teacher.infrastructure.json").exists()

    second = run_capability_loop(task(), out_dir=tmp_path, **kwargs)
    # The restart must short-circuit: no new worker/teacher calls, no new
    # trajectory records, and the prior summary is returned intact.
    assert worker_calls == 1
    assert external_calls == 1
    assert second == first
    assert second["disposition"] == "infrastructure_error"
    assert second["capability_verdict_available"] is False
    assert second["unresolved"] is False
    assert records(tmp_path / "trajectory.jsonl") == first_records


@pytest.mark.parametrize(
    ("status", "error", "classification"),
    [
        ("request_error", "Operation not permitted", "transport_request_error"),
        ("http_error", "server unavailable", "transport_http_error"),
        ("request_error", "request timed out", "transport_timeout"),
    ],
)
def test_transport_failure_never_enters_validator_or_capability_verdict(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: str, error: str, classification: str):
    def validator_must_not_run(*args, **kwargs):
        raise AssertionError("transport failures must not be validated")

    monkeypatch.setattr(loop, "_validator_result", validator_must_not_run)
    result = run_capability_loop(
        task(),
        out_dir=tmp_path,
        worker=lambda prompt: transport_response(status, error),
        max_worker_attempts=1,
        max_teacher_passes=0,
        external_teacher=lambda prompt: (_ for _ in ()).throw(AssertionError("transport failure must not escalate")),
    )
    assert result["capability_verdict_available"] is False
    assert result["model_attempt_count"] == 0
    assert result["infrastructure_error_count"] == 1
    assert result["unresolved"] is False
    assert not (tmp_path / "attempt-1.validation.json").exists()
    attempt = next(row for row in records(tmp_path / "trajectory.jsonl") if row.get("record_type") == "worker_attempt")
    assert attempt["transport_classification"] == classification
    assert attempt["transport_valid"] is False
    assert attempt["validation"] is None
    assert "request error" not in json.dumps(attempt["validation"] or {}).lower()
    scorecard = aggregate_scorecard([tmp_path / "trajectory.jsonl"])
    assert scorecard["trials"] == 0
    assert scorecard["infrastructure_attempts_excluded"] == 1
    assert scorecard["infrastructure_error_count"] == 1


def test_valid_retry_after_transport_failure_is_scored_normally(tmp_path: Path):
    outputs = iter([transport_response("request_error", "Operation not permitted"), response('{"answer":"ok"}', "small-1.7b")])
    result = run_capability_loop(
        task(),
        out_dir=tmp_path,
        worker=lambda prompt: next(outputs),
        max_worker_attempts=2,
        max_teacher_passes=0,
        external_teacher=lambda prompt: (_ for _ in ()).throw(AssertionError("teacher must not be called")),
    )
    assert result["pass"] is True
    assert result["capability_verdict_available"] is True
    assert result["model_attempt_count"] == 1
    assert result["infrastructure_error_count"] == 1
    assert result["first_attempt_pass"] is False
    validations = list(tmp_path.glob("attempt-*.validation.json"))
    assert [path.name for path in validations] == ["attempt-2.validation.json"]
    scorecard = aggregate_scorecard([tmp_path / "trajectory.jsonl"])
    assert scorecard["trials"] == 1
    assert scorecard["passes"] == 1
    assert scorecard["first_attempt_passes"] == 0


def test_transport_raw_evidence_is_durable_and_content_is_not_capability_failure(tmp_path: Path):
    run_capability_loop(
        task(),
        out_dir=tmp_path,
        worker=lambda prompt: transport_response("request_error", "Operation not permitted"),
        max_worker_attempts=1,
        max_teacher_passes=0,
    )
    raw = json.loads((tmp_path / "attempt-1.raw.json").read_text())
    metadata = json.loads((tmp_path / "attempt-1.metadata.json").read_text())
    assert raw["content"] == "[request_error]"
    assert raw["metadata"]["status"] == "request_error"
    assert metadata["transport_classification"] == "transport_request_error"
    assert not (tmp_path / "attempt-1.validation.json").exists()


def test_worker_request_provenance_contains_replay_fingerprint_without_private_url():
    spec = resolve_worker_spec("router", base_url="http://endpoint.invalid/v1", model="small-1.7b")
    _, _, _, _, provenance = _render_request_payload(spec, "Return JSON.", 128, model=spec.model)
    assert provenance["prompt_sha256"]
    assert provenance["message_structure"] == ["system", "user"]
    assert provenance["model"] == "small-1.7b"
    assert provenance["configured_model"] == "small-1.7b"
    assert provenance["max_tokens"] == 128
    assert provenance["temperature"] == 0.2
    assert provenance["top_p"] is None
    assert provenance["seed"] is None
    assert provenance["stop"] is None
    assert provenance["chat_template_kwargs"] is None
    assert provenance["thinking_budget_tokens"] is None
    assert "endpoint.invalid" not in json.dumps(provenance)


def test_qwen38_worker_request_provenance_carries_bounded_reasoning_policy():
    spec = resolve_worker_spec("qwen3_8_27b", request_policy_name="exceptional")
    _, payload, _, _, provenance = _render_request_payload(spec, "Explain the failure.", 1536, model=spec.model)
    assert payload["chat_template_kwargs"] == {"reasoning_effort": "xhigh"}
    assert payload["thinking_budget_tokens"] == 512
    assert provenance["chat_template_kwargs"] == {"reasoning_effort": "xhigh"}
    assert provenance["thinking_budget_tokens"] == 512
    assert provenance["max_tokens"] == 1536


def test_qwen38_teacher_request_policy_env_override_binds_bounded_reasoning(monkeypatch: pytest.MonkeyPatch):
    # Mirrors the loop's teacher wiring (supervised_capability_loop.py):
    # resolve_worker_spec(name, base_url=..., model=...) with NO request_policy_name,
    # so the policy arrives via the `routine` default or the ICM_QWEN3_8_27B_REQUEST_POLICY env var.
    base_url = "http://192.168.137.3:8080/v1"
    model = "Qwen3.8-27B-UD-IQ4_XS.gguf"

    # (a) Dogfood fix: env UNSET -> defaults to the `routine` policy -> bounded reasoning.
    # The loop's plain resolve_worker_spec(name, base_url=..., model=...) teacher wiring
    # can no longer silently fall back to an unbounded no-policy request.
    monkeypatch.delenv("ICM_QWEN3_8_27B_REQUEST_POLICY", raising=False)
    spec = resolve_worker_spec("qwen3_8_27b", base_url=base_url, model=model)
    assert spec.request_policy_name == "routine"
    assert spec.request_policy["thinking_budget_tokens"] == 256
    _, payload, _, actual_prompt, provenance = _render_request_payload(spec, "Explain the failure.", 1200, model=model)
    assert payload["thinking_budget_tokens"] == 256
    assert provenance["thinking_budget_tokens"] == 256
    assert provenance["chat_template_kwargs"] == {"reasoning_effort": "low"}
    assert provenance["append_no_think"] is False
    assert provenance["max_tokens"] == 1200
    assert "/no_think" not in actual_prompt

    # (b) Config-only fix: env = routine -> bounded reasoning via env path only.
    monkeypatch.setenv("ICM_QWEN3_8_27B_REQUEST_POLICY", "routine")
    spec = resolve_worker_spec("qwen3_8_27b", base_url=base_url, model=model)
    assert spec.request_policy_name == "routine"
    assert spec.request_policy["thinking_budget_tokens"] == 256
    _, payload, _, actual_prompt, provenance = _render_request_payload(spec, "Explain the failure.", 1200, model=model)
    assert payload["thinking_budget_tokens"] == 256
    assert payload["chat_template_kwargs"] == {"reasoning_effort": "low"}
    assert provenance["thinking_budget_tokens"] == 256
    assert provenance["chat_template_kwargs"] == {"reasoning_effort": "low"}
    assert provenance["append_no_think"] is False
    assert provenance["max_tokens"] == 1200
    assert "/no_think" not in actual_prompt

    # (c) Config-only fix: env = direct -> append_no_think flows via env path.
    monkeypatch.setenv("ICM_QWEN3_8_27B_REQUEST_POLICY", "direct")
    spec = resolve_worker_spec("qwen3_8_27b", base_url=base_url, model=model)
    assert spec.request_policy_name == "direct"
    _, payload, _, actual_prompt, provenance = _render_request_payload(spec, "Explain the failure.", 1200, model=model)
    assert provenance["append_no_think"] is True
    assert "/no_think" in actual_prompt
    assert provenance["thinking_budget_tokens"] is None
    assert provenance["chat_template_kwargs"] is None
    assert provenance["max_tokens"] == 1200


def test_supervised_trajectory_summary_can_reference_router_evidence(tmp_path: Path):
    (tmp_path / "route_trace.json").write_text(json.dumps({"schema": "zth_router_v1_route_trace_v1", "capability_eligibility": [{"capability_id": "x", "candidate_suppliers": [{"supplier_id": "s1", "status": "QUALIFIED_EXPLORATORY"}], "qualified_candidates": [{"supplier_id": "s1"}], "eligibility_reason": "eligible"}], "capabilities": [{"capability_id": "x", "selected_supplier": {"supplier_id": "s1"}, "selection_reason": "selected"}]}), encoding="utf-8")
    (tmp_path / "capability_plan.json").write_text(json.dumps({"schema": "zth_router_v1_capability_plan_v1", "capability_eligibility": [{"capability_id": "x", "candidate_suppliers": [{"supplier_id": "s1", "status": "QUALIFIED_EXPLORATORY"}], "qualified_candidates": [{"supplier_id": "s1"}], "eligibility_reason": "eligible"}], "capabilities": [{"capability_id": "x", "selected_supplier": {"supplier_id": "s1"}, "selection_reason": "selected"}]}), encoding="utf-8")
    run_capability_loop(task(), out_dir=tmp_path, worker=lambda p: response('{"answer":"ok"}', "small-1.7b"), local_teacher=lambda p: pytest.fail("teacher called"))
    summary = json.loads((tmp_path / "trajectory_summary.json").read_text(encoding="utf-8"))
    assert summary["router_route_trace_reference"]["artifact"] == "route_trace"
    assert summary["capability_plan_reference"]["artifact"] == "capability_plan"


def test_optional_context_complete_retry_is_default_off_and_fail_closed(tmp_path: Path):
    prompts: list[str] = []
    patch = {"candidate_patch_id": "experimental", "prompt_delta": "Use the declared contract and evidence."}
    patch_path = tmp_path / "patch.json"
    patch_path.write_text(json.dumps(patch), encoding="utf-8")
    patch_hash = hashlib.sha256(patch_path.read_bytes()).hexdigest()
    outputs = iter(['{"answer":"wrong"}', '{"answer":"ok"}'])
    result = run_capability_loop(
        task(),
        out_dir=tmp_path / "enabled",
        worker=lambda prompt: (prompts.append(prompt) or response(next(outputs), "small-1.7b")),
        max_worker_attempts=1,
        max_teacher_passes=0,
        deterministic_patch_retry={"patch_id": "experimental", "patch_path": str(patch_path), "patch_sha256": patch_hash},
        external_teacher=lambda prompt: (_ for _ in ()).throw(AssertionError("teacher must not be called")),
    )
    assert result["patch_retry_attempted"] is True
    assert result["patch_retry_passed"] is True
    assert result["successful_intervention_source"] == "deterministic_patch_retry"
    assert result["teacher_escalation_avoided"] is True
    assert len(prompts) == 2
    assert '"declared_output_contract"' in prompts[1]
    assert '"bounded_reference_facts"' in prompts[1]
    assert "Use the declared contract and evidence." in prompts[1]
    retry = [row for row in records(tmp_path / "enabled" / "trajectory.jsonl") if row.get("record_type") == "worker_attempt" and row.get("intervention_source") == "deterministic_patch_retry"][0]
    assert retry["intervention_id"] == "deterministic_patch_retry:1"
    assert retry["deterministic_patch_hash"] == patch_hash

    default_outputs = iter(['{"answer":"wrong"}', '{"answer":"wrong"}'])
    default = run_capability_loop(
        task(),
        out_dir=tmp_path / "default",
        worker=lambda prompt: response(next(default_outputs), "small-1.7b"),
        max_worker_attempts=1,
        max_teacher_passes=0,
        external_teacher=lambda prompt: (_ for _ in ()).throw(RuntimeError("off")),
    )
    assert default["patch_retry_attempted"] is False
    assert default["successful_intervention_source"] == "none"


def test_optional_context_complete_retry_rejects_hash_mismatch(tmp_path: Path):
    patch_path = tmp_path / "patch.json"
    patch_path.write_text(json.dumps({"candidate_patch_id": "experimental", "prompt_delta": "Do it."}), encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        run_capability_loop(task(), out_dir=tmp_path / "bad", worker=lambda prompt: response('{"answer":"ok"}', "small"), deterministic_patch_retry={"patch_id": "experimental", "patch_path": str(patch_path), "patch_sha256": "0" * 64})


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
    fixture = {**task(), "validator": {"kind": "zth_output_contract", "authorized_targets": [], "reference_facts": {}}, "triage_id": "triage-1", "orchestration_id": "orch-1", "prompt_packet_id": "prompt-1"}
    result = run_capability_loop(fixture, out_dir=tmp_path, worker=lambda p: response('{"allowed_targets": [], "held_targets": [], "reason": "ok"}', "small"), max_worker_attempts=1)
    assert result["disposition"] == "ready_for_review"
    validation = json.loads((tmp_path / "attempt-1.validation.json").read_text())
    assert validation["validator"] if "validator" in validation else validation["validation_status"] == "passed"


@pytest.mark.parametrize(
    ("reference_facts", "output"),
    [
        ({"required_allowed_targets": ["docs/"], "forbidden_allowed_targets": ["training/"]}, {"allowed_targets": ["training/"], "held_targets": [], "reason": "review"}),
        ({"required_held_targets": ["training/"]}, {"allowed_targets": ["docs/"], "held_targets": [], "reason": "review"}),
        ({"forbidden_completion_claim": True}, {"allowed_targets": ["docs/"], "held_targets": ["training/"], "reason": "I will mark the task complete"}),
        ({"must_include": ["human review"]}, {"allowed_targets": ["docs/"], "held_targets": ["training/"], "reason": "bounded"}),
        ({"must_not_include": ["proceed with implementation"]}, {"allowed_targets": ["docs/"], "held_targets": ["training/"], "reason": "proceed with implementation"}),
        ({"queue_handoff_status": "not_inserted"}, {"allowed_targets": ["docs/"], "held_targets": ["training/"], "reason": "review", "queue_handoff_status": "inserted"}),
    ],
)
def test_structurally_valid_output_fails_reference_semantics(reference_facts, output):
    fixture = {
        **task(),
        "validator": {"kind": "zth_output_contract", "reference_facts": reference_facts},
        "output_contract": {"format": "json", "required_fields": ["allowed_targets", "held_targets", "reason"]},
    }
    result = loop._validator_result(json.dumps(output), fixture, attempt_id="adversarial")
    assert result["structural_checks"]
    assert result["semantic_checks"]
    assert result["validation_status"] == "failed"
    assert any(check["status"] == "failed" for check in result["semantic_checks"])


def test_unknown_reference_fact_fails_closed():
    fixture = {
        **task(),
        "validator": {"kind": "zth_output_contract", "reference_facts": {"future_unregistered_check": True}},
        "output_contract": {"format": "json", "required_fields": ["answer"]},
    }
    result = loop._validator_result('{"answer":"ok"}', fixture, attempt_id="unknown-reference")
    assert result["validation_status"] == "failed"
    assert "Unknown semantic reference fact" in " ".join(result["diagnostics"])


def test_retry_ceiling_and_no_self_acceptance(tmp_path: Path):
    calls = 0
    def worker(p):
        nonlocal calls
        calls += 1
        return response("not-json", "small")
    result = run_capability_loop(task(), out_dir=tmp_path, worker=worker, max_worker_attempts=3, max_teacher_passes=0, external_teacher=lambda p: (_ for _ in ()).throw(RuntimeError("off")))
    assert calls == 3 and result["disposition"] == "infrastructure_error"
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


def test_scorecard_aggregates_summary_success_fields_and_unresolved_source(tmp_path: Path):
    rows = [
        {"task_id": "baseline", "task_family": "family-a", "worker_model": "small", "pass": True, "first_attempt_pass": True, "pass_after_existing_patch": False, "pass_after_local_teacher_intervention": False, "pass_after_external_teacher_intervention": False, "successful_intervention_source": "none", "intervention_attempts": {"none": True, "existing_patch": False, "local_teacher": False, "external_teacher": False}, "unresolved": False, "external_escalation_count": 0, "intervention_outcome": "no-effect"},
        {"task_id": "local", "task_family": "family-a", "worker_model": "small", "pass": True, "first_attempt_pass": False, "pass_after_existing_patch": False, "pass_after_local_teacher_intervention": True, "pass_after_external_teacher_intervention": False, "successful_intervention_source": "local_teacher", "intervention_attempts": {"none": True, "existing_patch": False, "local_teacher": True, "external_teacher": False}, "unresolved": False, "external_escalation_count": 0, "intervention_outcome": "helped"},
        {"task_id": "external", "task_family": "family-b", "worker_model": "small", "pass": True, "first_attempt_pass": False, "pass_after_existing_patch": False, "pass_after_local_teacher_intervention": False, "pass_after_external_teacher_intervention": True, "successful_intervention_source": "external_teacher", "intervention_attempts": {"none": True, "existing_patch": False, "local_teacher": True, "external_teacher": True}, "unresolved": False, "external_escalation_count": 1, "intervention_outcome": "helped"},
        {"task_id": "unresolved", "task_family": "family-b", "worker_model": "small", "pass": False, "first_attempt_pass": False, "pass_after_existing_patch": False, "pass_after_local_teacher_intervention": False, "pass_after_external_teacher_intervention": False, "successful_intervention_source": "none", "intervention_attempts": {"none": True, "existing_patch": False, "local_teacher": True, "external_teacher": True}, "unresolved": True, "external_escalation_count": 1, "intervention_outcome": "no-effect"},
    ]
    trajectories = []
    for row in rows:
        task_dir = tmp_path / row["task_id"]
        task_dir.mkdir()
        (task_dir / "trajectory.jsonl").write_text("{}\n")
        (task_dir / "trajectory_summary.json").write_text(json.dumps(row))
        trajectories.append(task_dir / "trajectory.jsonl")

    scorecard = aggregate_scorecard(trajectories)
    assert scorecard["passes"] == 3
    assert scorecard["first_attempt_passes"] == 1
    assert scorecard["passes_after_existing_patch"] == 0
    assert scorecard["passes_after_local_teacher_intervention"] == 1
    assert scorecard["passes_after_external_teacher_intervention"] == 1
    assert scorecard["successful_intervention_source_counts"] == {"none": 1, "existing_patch": 0, "deterministic_patch_retry": 0, "local_teacher": 1, "external_teacher": 1}
    assert scorecard["unresolved_count"] == 1
    assert scorecard["external_escalation_count"] == 2
    assert scorecard["groups"]["small::family-a"]["passes_after_local_teacher_intervention"] == 1
    assert scorecard["groups"]["small::family-b"]["passes_after_external_teacher_intervention"] == 1
    assert scorecard["groups"]["small::family-b"]["unresolved"] == 1


def test_scorecard_counts_only_durable_worker_intervention_sources(tmp_path: Path):
    patch = {"patch_id": "p1", "title": "patch", "status": "active", "failure_signature": ["wrong"], "applies_to": {"stage": ["validation"], "task_type": ["json-fixture"], "model_size": ["small"]}, "prompt_delta": "Be exact.", "required_output_fields": ["answer"], "validator_expectations": ["exact"]}
    library = PromptPatchLibrary(); library.add_patch(patch)
    result = run_capability_loop(task(), out_dir=tmp_path / "baseline", patch_library=library, existing_patch_ids=["p1"], worker=lambda p: response('{"answer":"ok"}', "small"), max_worker_attempts=1, max_teacher_passes=1)
    assert result["intervention_attempts"] == {"none": True, "existing_patch": False, "deterministic_patch_retry": False, "local_teacher": False, "external_teacher": False}

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
    assert result["intervention_attempts"] == {"none": True, "existing_patch": False, "deterministic_patch_retry": False, "local_teacher": True, "external_teacher": False}
    assert result["external_escalation_count"] == 1
    assert result["external_teacher_call_count"] == 1

    scorecard = aggregate_scorecard([tmp_path / "baseline" / "trajectory.jsonl", tmp_path / "escalated" / "trajectory.jsonl"])
    assert scorecard["by_intervention_source"]["none"]["trials"] == 1
    assert scorecard["by_intervention_source"]["existing_patch"]["trials"] == 0
    # The task ended in an external infrastructure failure, so it is excluded
    # from capability metrics rather than counted as a local-teacher trial.
    assert scorecard["by_intervention_source"]["local_teacher"]["trials"] == 0
    assert scorecard["external_escalation_count"] == 1
    assert scorecard["external_teacher_call_count"] == 1


# ---------------------------------------------------------------------------
# Nested-fence teacher JSON extraction regressions.
#
# These pin the JSON-aware recovery contract in _extract_teacher_json_object:
# visible content only, (1) bare object, (2) a single explicit ```json fence
# recovered via json.JSONDecoder().raw_decode (so triple backticks embedded in
# a string value do NOT terminate extraction), (3) one unambiguous embedded
# object; and the rejections (malformed, competing, schema-invalid, absent,
# and the hidden reasoning channel).
# ---------------------------------------------------------------------------


def test_teacher_extraction_bare_json_object():
    from local_harness.supervised_capability_loop import _extract_teacher_json_object
    raw = '{"failure_classification": "wrong_reference", "teacher_diagnosis": "Use the bounded reference.", "retry_guidance": "Return JSON only."}'
    payload, diagnosis = _extract_teacher_json_object(raw)
    assert diagnosis == ""
    assert payload is not None
    assert payload["failure_classification"] == "wrong_reference"
    assert payload["retry_guidance"] == "Return JSON only."


def test_teacher_extraction_ordinary_json_fence():
    from local_harness.supervised_capability_loop import _extract_teacher_json_object
    raw = "```json\n{\"failure_classification\": \"prompt_contract_gap\", \"retry_guidance\": \"Return JSON only.\"}\n```"
    payload, diagnosis = _extract_teacher_json_object(raw)
    assert diagnosis == ""
    assert payload is not None
    assert payload["failure_classification"] == "prompt_contract_gap"
    # The whole fence must round-trip through _parse_teacher as a passed parse.
    from local_harness.supervised_capability_loop import _parse_teacher
    parsed = _parse_teacher(raw)
    assert parsed["teacher_parse_status"] == "passed"
    assert parsed["failure_classification"] == "prompt_contract_gap"


def test_teacher_extraction_fenced_json_with_one_nested_plain_block():
    from local_harness.supervised_capability_loop import _extract_teacher_json_object, _parse_teacher
    # A single explicit ```json fence whose string value embeds ONE plain
    # (untagged) ``` block. The nested fence must not truncate the object.
    diagnosis_value = "The worker omitted a block.\n\n```\n- one item\n- two items\n```\n\nAdd both items."
    payload_obj = {
        "failure_classification": "prompt_contract_gap",
        "teacher_diagnosis": diagnosis_value,
        "retry_guidance": "Return JSON only.",
    }
    raw = "```json\n" + json.dumps(payload_obj, indent=2) + "\n```"
    payload, diagnosis = _extract_teacher_json_object(raw)
    assert diagnosis == ""
    assert payload is not None
    assert payload == payload_obj
    assert "```" in payload["teacher_diagnosis"]
    assert "- one item" in payload["teacher_diagnosis"]
    assert "- two items" in payload["teacher_diagnosis"]
    assert payload["retry_guidance"] == "Return JSON only."
    parsed = _parse_teacher(raw)
    assert parsed["teacher_parse_status"] == "passed"
    assert parsed["teacher_diagnosis"] == diagnosis_value


def test_teacher_extraction_candidate_prompt_patch_with_multiple_nested_fenced_blocks():
    from local_harness.supervised_capability_loop import _extract_teacher_json_object
    # Mirrors the preserved spec-field-count-disagreement shape: one explicit
    # ```json fence whose candidate_prompt_patch string value embeds MULTIPLE
    # nested ``` fenced blocks (a NOTE TEMPLATE block plus an evidence list).
    # raw_decode must honor the JSON string and recover the whole object.
    patch_value = (
        "You are a bounded, read-only repository observer.\n\n"
        "Raw evidence A \u2014 verbatim NOTE TEMPLATE:\n\n"
        "```\n"
        "## Supervised Role-Run Evidence Note\n\n"
        "- Role used:\n"
        "- Source prompt file:\n"
        "- Human supervisor:\n"
        "```\n\n"
        "Raw evidence B \u2014 verbatim 'Evidence To Record' list:\n\n"
        "- Active packet path.\n"
        "- Output summary.\n"
        "- Human decision.\n\n"
        "Output EXACTLY one JSON object:\n"
        "{\n"
        "  \"a\": <integer>,\n"
        "  \"b\": <integer>\n"
        "}"
    )
    payload_obj = {
        "failure_classification": "model_capability_insufficient",
        "teacher_diagnosis": "The small model miscounts.",
        "candidate_prompt_patch": patch_value,
        "retry_guidance": "Escalate to a larger model.",
        "corrected_reference_output": {"a": 18, "b": 8},
    }
    raw = "```json\n" + json.dumps(payload_obj, indent=2) + "\n```"
    payload, diagnosis = _extract_teacher_json_object(raw)
    assert diagnosis == ""
    assert payload is not None
    assert payload == payload_obj
    # The embedded NOTE TEMPLATE fence and the JSON object literal inside the
    # string value must both survive intact.
    assert "## Supervised Role-Run Evidence Note" in payload["candidate_prompt_patch"]
    assert '"a": <integer>' in payload["candidate_prompt_patch"]
    assert payload["corrected_reference_output"] == {"a": 18, "b": 8}


def test_teacher_extraction_prose_plus_fenced_json_with_nested_fences():
    from local_harness.supervised_capability_loop import _extract_teacher_json_object
    # Prose before and after a single explicit ```json fence that itself
    # embeds a nested plain block; bounded trailing wrapper text is tolerated.
    diagnosis_value = "\n```\n- item one\n- item two\n```\n"
    payload_obj = {
        "failure_classification": "prompt_contract_gap",
        "teacher_diagnosis": diagnosis_value,
        "retry_guidance": "Return JSON only.",
    }
    raw = (
        "Here is my assessment of the failure.\n\n"
        "```json\n"
        + json.dumps(payload_obj, indent=2)
        + "\n```\n\n"
        "That should cover the observed failure mode."
    )
    payload, diagnosis = _extract_teacher_json_object(raw)
    assert diagnosis == ""
    assert payload is not None
    assert payload == payload_obj
    assert payload["failure_classification"] == "prompt_contract_gap"
    assert "- item one" in payload["teacher_diagnosis"]
    assert "- item two" in payload["teacher_diagnosis"]
    assert payload["retry_guidance"] == "Return JSON only."


def test_teacher_extraction_rejects_malformed_outer_json():
    from local_harness.supervised_capability_loop import _extract_teacher_json_object
    # A single explicit ```json fence whose body is NOT valid JSON (an
    # unterminated string) must be rejected, not silently truncated.
    raw = (
        "```json\n"
        "{\n"
        "  \"failure_classification\": \"model_capability_insufficient\",\n"
        "  \"teacher_diagnosis\": \"unterminated\n"
        "}\n"
        "```"
    )
    payload, diagnosis = _extract_teacher_json_object(raw)
    assert payload is None
    assert diagnosis != ""


def test_teacher_extraction_rejects_multiple_competing_objects():
    from local_harness.supervised_capability_loop import _extract_teacher_json_object
    # Two competing top-level objects with no explicit fence: ambiguous, so
    # the whole extraction is rejected rather than picking the first.
    raw = 'First object {"failure_classification": "a"} then second object {"failure_classification": "b"}'
    payload, diagnosis = _extract_teacher_json_object(raw)
    assert payload is None
    assert diagnosis != ""


def test_teacher_extraction_valid_json_but_invalid_teacher_schema():
    from local_harness.supervised_capability_loop import _extract_teacher_json_object, _parse_teacher
    # Extraction succeeds (a valid JSON object) but the teacher payload is
    # schema-invalid: its candidate_prompt_patch is a plain string rather than
    # a valid patch object, so the strict schema validation rejects it.
    # _parse_teacher keeps the parse "passed" (extraction recovered a dict) but
    # must flag the patch candidate as invalid_candidate.
    raw = json.dumps({
        "failure_classification": "model_capability_insufficient",
        "teacher_diagnosis": "Small model miscounts.",
        "candidate_prompt_patch": "just a plain string, not a patch object",
        "retry_guidance": "Escalate to a larger model.",
    })
    payload, diagnosis = _extract_teacher_json_object(raw)
    assert diagnosis == ""
    assert payload is not None
    parsed = _parse_teacher(raw)
    assert parsed["teacher_parse_status"] == "passed"
    assert parsed["candidate_patch_status"] == "invalid_candidate"
    # The invalid patch must NOT be carried through as a valid candidate.
    assert "candidate_prompt_patch" not in parsed


def test_teacher_extraction_ignores_hidden_reasoning_content():
    from local_harness.supervised_capability_loop import _extract_teacher_json_object
    from local_harness.icm_spec import WorkerResponse
    # A response whose ONLY recoverable JSON lives in a hidden reasoning
    # channel (raw_response.reasoning_content) and whose visible content is
    # prose-only must not yield an object: the hidden channel is never scanned.
    resp = WorkerResponse(
        "ok",
        "The model is miscounting the bullet items in the evidence block.",
        "http://fixture/v1/chat/completions",
        "small-1.7b",
        "small-1.7b",
        "stop",
        {"completion_tokens": 5},
        {"total_ms": 1},
        {"reasoning_content": '{"failure_classification": "model_capability_insufficient", "corrected_reference_output": {"answer": 18}}'},
    )
    assert "corrected_reference_output" in resp.raw_response["reasoning_content"]
    payload, diagnosis = _extract_teacher_json_object(resp.content)
    assert payload is None
    assert diagnosis != ""


def test_teacher_extraction_preserved_spec_field_count_disagreement_shape():
    from local_harness.supervised_capability_loop import _extract_teacher_json_object, _parse_teacher
    # Reproduces the exact shape of the preserved failing teacher response from
    # .work/dogfood/spec_field_count_disagreement_20260912/local-teacher-1.json
    # (raw is stored as {"content": ...}; the visible content is raw["content"]).
    # The old non-greedy fence regex truncated at the first nested ``` inside
    # candidate_prompt_patch ("Unterminated string starting at"); JSON-aware
    # recovery must now pass.
    patch_value = (
        "You are a bounded, read-only repository observer. Do not modify any file or state.\n"
        "Do not fetch anything and do not use any tool. Answer using ONLY the two raw-evidence blocks inlined below. Do not add keys. Do not emit prose.\n\n"
        "Task: Count the bullet-list items in each block below.\n\n"
        "METHOD (follow exactly):\n"
        "1. For Raw Evidence A, go line by line. For each line, check if it starts with the two characters '- '. If yes, increment a counter. Do not skip any line. The counter starts at 0.\n"
        "2. For Raw Evidence B, do the same.\n"
        "3. Report both final counters.\n\n"
        "Raw evidence A \u2014 verbatim role-run evidence NOTE TEMPLATE (workflows/SUPERVISED_ROLE_RUN_EVIDENCE_NOTE_FORMAT.md):\n\n"
        "```\n"
        "## Supervised Role-Run Evidence Note\n\n"
        "- Role used:\n"
        "- Source prompt file:\n"
        "- Active job packet:\n"
        "- Human supervisor:\n"
        "- Date:\n"
        "- Purpose of role run:\n"
        "- Authority source:\n"
        "- Authority granted by active packet:\n"
        "- Authorized file allowlist:\n"
        "- Inputs reviewed:\n"
        "- Output summary:\n"
        "- Recommendations:\n"
        "- Explicit non-authorizations:\n"
        "- Actions performed under granted authority:\n"
        "- Files changed:\n"
        "- Stop conditions encountered:\n"
        "- Follow-up packet candidates:\n"
        "- Human decision:\n"
        "```\n\n"
        "Raw evidence B \u2014 verbatim 'Evidence To Record' list (workflows/SUPERVISED_MANAGEMENT_TEAM_USAGE_RULES.md):\n\n"
        "- Active packet path.\n"
        "- Role used.\n"
        "- Prompt/input summary.\n"
        "- Output summary.\n"
        "- Files changed, if any.\n"
        "- Verification run, if any.\n"
        "- Human decision.\n"
        "- Follow-up packet needed, if any.\n\n"
        "Output EXACTLY one JSON object with these two keys and nothing else (no markdown, no code fences, no prose):\n"
        "{\n"
        "  \"evidence_note_template_field_count\": <integer>,\n"
        "  \"usage_rules_evidence_to_record_count\": <integer>\n"
        "}"
    )
    payload_obj = {
        "failure_classification": "model_capability_insufficient",
        "teacher_diagnosis": "The model (Qwen3-1.7B-Q4_K_M) consistently miscounts the bullet-list items in Raw Evidence A, reporting 11 instead of the correct 18. The count for Raw Evidence B (8) is correct in both attempts. The model likely truncates or loses track during enumeration of the longer list, a known limitation of small quantized models on sequential counting tasks. The prompt is unambiguous and the reference output is deterministic; the failure is purely a model capability gap, not a prompt ambiguity or transport issue.",
        "candidate_prompt_patch": patch_value,
        "retry_guidance": "The patch adds an explicit step-by-step counting method to reduce the chance of the small model losing track. However, given the model's consistent failure across two identical attempts (same prompt hash), there is low confidence this patch will succeed with Qwen3-1.7B-Q4_K_M. If the next attempt also fails, escalate to a larger model or accept the corrected reference output as the authoritative answer.",
        "corrected_reference_output": {
            "evidence_note_template_field_count": 18,
            "usage_rules_evidence_to_record_count": 8,
        },
    }
    content = "```json\n" + json.dumps(payload_obj, indent=2) + "\n```"
    # raw is persisted as a dict whose "content" field is the visible string.
    raw_record = {"raw": {"content": content}}

    payload, diagnosis = _extract_teacher_json_object(raw_record["raw"]["content"])
    assert diagnosis == ""
    assert payload is not None
    assert payload == payload_obj
    # Both nested fenced blocks survive inside the string value.
    assert "## Supervised Role-Run Evidence Note" in payload["candidate_prompt_patch"]
    assert "- Human decision:" in payload["candidate_prompt_patch"]

    parsed = _parse_teacher(raw_record["raw"]["content"])
    assert parsed["teacher_parse_status"] == "passed"
    assert parsed["failure_classification"] == "model_capability_insufficient"
    assert parsed["corrected_reference_output"] == {
        "evidence_note_template_field_count": 18,
        "usage_rules_evidence_to_record_count": 8,
    }
