#!/usr/bin/env python3
"""Bounded failure-diagnosis -> prompt-patch -> fresh retest experiment.

This driver deliberately keeps the teacher and student phases separate.  It
never replays the preserved composition failure and never changes the
canonical prompt-patch library or capability registry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from local_harness.run4a_intervention_harness import _default_local_teacher, _response_payload
from local_harness.stage_a_power_telemetry import PowerSampler, integrate_energy_joules, read_gpu_power
from scripts import zth_capability_router_v1 as router
from scripts import zth_qwen3_0_6b_clean_scope_logic_probe as base
from scripts import zth_qwen3_1_7b_atomic_scope_relation_decomposition as decomposition
from scripts import zth_qwen3_1_7b_clean_scope_logic_probe as runtime

ROOT = base.ROOT
PRIOR_RUN = ROOT / ".work/model_size_supplier_floor/capability_router_model_tool_composition_v0/run_20260823T052541Z"
BASE = ROOT / ".work/model_size_supplier_floor/capability_router_failure_teaching_v0"
STAGE_A = BASE / "stage_a"
STAGE_B = BASE / "stage_b/run_20260823T070000Z"
PATCH_ARTIFACT = ROOT / "docs/research/QWEN3_1_7B_ACTION_OPERATION_TEACHING_PATCH_V0_2026-08-23.json"
HOLDOUT_ARTIFACT = ROOT / "docs/research/CAPABILITY_ROUTER_FAILURE_TEACHING_HOLDOUT_V0_TASKS_2026-08-23.json"
CAPABILITY = "semantic.minimal_action_object_extraction"
INTERFACE = "router_v1_minimal_semantic_atom"
SUPPLIER = "qwen3_1_7b_minimal_action_object_supplier"
TEACHER_SUPPLIER = "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf"
MODEL_ID = runtime.EXPECTED_MODEL_ID
MODEL_SHA = runtime.EXPECTED_MODEL_SHA
PARAMS = runtime.EXPECTED_PARAMS
GPU_UUID = runtime.EXPECTED_GPU_UUID
MAX_TOKENS = runtime.MAX_OUTPUT_TOKENS
TIMEOUT = runtime.TIMEOUT_SECONDS
POWER_INTERVAL = runtime.POWER_INTERVAL_SECONDS

TEACHER_SCHEMA = {
    "type": "object",
    "properties": {
        "failure_mechanism": {"type": "string"},
        "intervention_type": {"type": "string", "enum": ["PROMPT_PATCH"]},
        "target_capability": {"type": "string"},
        "target_interface": {"type": "string"},
        "patch_instruction": {"type": "string"},
        "intended_effect": {"type": "string"},
        "must_not_change": {"type": "array", "items": {"type": "string"}},
        "regression_risks": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["failure_mechanism", "intervention_type", "target_capability", "target_interface", "patch_instruction", "intended_effect", "must_not_change", "regression_risks"],
    "additionalProperties": False,
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def failure_paths() -> dict[str, Path]:
    task = PRIOR_RUN / "tasks/composition-v0-003"
    return {name: task / name for name in ("runtime_task.json", "semantic_prompt.txt", "semantic_validation.json", "runtime_result.json", "success_contract_0.json", "route_trace.json", "evaluator.json")}


def localize_failure() -> dict[str, Any]:
    paths = failure_paths()
    semantic = read_json(paths["semantic_validation.json"])
    result = read_json(paths["runtime_result.json"])
    contract = read_json(paths["success_contract_0.json"])
    runtime_task = read_json(paths["runtime_task.json"])
    failed = [p for p in result["validator"]["predicates"] if not p["passed"]]
    failed_field = "action" if any(p["predicate"] == "action_allowed" for p in failed) else "unknown"
    observed = semantic.get("observed", {})
    return {
        "schema": "zth_failure_localization_v0",
        "task_id": "composition-v0-003",
        "supplier_id": SUPPLIER,
        "supplier_identity": {"model_id": MODEL_ID, "operative_parameters": PARAMS, "artifact_sha256": MODEL_SHA},
        "capability_id": CAPABILITY,
        "interface_id": INTERFACE,
        "failed_stage": "semantic_validation_before_tool_planning",
        "failed_field": failed_field,
        "validator_predicate": "action_allowed",
        "observed_value": observed.get("action"),
        "allowed_contract_information": {"allowed_observation_operations": ["determine"], "interface_fields": ["action", "object_expression"]},
        "downstream_actions_prevented": ["tool.read_only_repository_observation", "deterministic post-observation policy"],
        "failure_class": "ACTION_OPERATION_STATE_PREDICATE_CONFUSION",
        "evidence": {"runtime_task_sha256": digest_file(paths["runtime_task.json"]), "semantic_validation_sha256": digest_file(paths["semantic_validation.json"]), "runtime_result_sha256": digest_file(paths["runtime_result.json"]), "success_contract_sha256": digest_file(paths["success_contract_0.json"]), "route_trace_sha256": digest_file(paths["route_trace.json"])},
        "raw_evidence_unchanged": True,
    }


def teacher_packet(localization: dict[str, Any]) -> dict[str, Any]:
    paths = failure_paths()
    passing = []
    for tid in ("composition-v0-001", "composition-v0-002"):
        td = PRIOR_RUN / "tasks" / tid
        validation = read_json(td / "semantic_validation.json")
        passing.append({"task_id": tid, "semantic_output": validation["observed"], "evidence_sha256": digest_file(td / "semantic_validation.json")})
    return {
        "schema": "zth_teacher_diagnostic_packet_v0",
        "purpose": "diagnose one preserved bounded interface failure and propose one review-only prompt patch",
        "failure_localization": localization,
        "capability_definition": "Extract the operation and object expression from a request clause for the existing two-string semantic interface.",
        "interface_id": INTERFACE,
        "output_schema": TEACHER_SCHEMA,
        "frozen_semantic_prompt": paths["semantic_prompt.txt"].read_text(encoding="utf-8"),
        "failing_request": read_json(paths["runtime_task.json"])["input_request"],
        "actual_supplier_output": read_json(paths["semantic_validation.json"])["observed"],
        "validator_diagnostics": read_json(paths["runtime_result.json"])["validator"],
        "allowed_action_semantics": ["determine"],
        "prior_passing_examples": passing,
        "forbidden_teacher_actions": ["solve the repository task", "call a tool", "grant authority", "change the registry", "weaken validation", "modify weights"],
        "holdout_material_included": False,
    }


def teacher_prompt(packet: dict[str, Any]) -> str:
    return (
        "You are a bounded diagnostic teacher. Diagnose only the preserved interface failure in the packet below and propose exactly one prompt patch. "
        "Return JSON matching the supplied schema and no commentary. The intervention_type must be PROMPT_PATCH. "
        "Do not solve the repository request, select a tool, grant authority, weaken a validator, or propose weights/training.\n\n"
        + json.dumps(packet, indent=2, sort_keys=True)
        + "\n\nOutput schema:\n"
        + json.dumps(TEACHER_SCHEMA, indent=2, sort_keys=True)
    )


def parse_teacher(raw: str) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, [f"teacher JSON parse failure: {exc.msg}"]
    if not isinstance(value, dict) or set(value) != set(TEACHER_SCHEMA["properties"]):
        return None, ["teacher output does not have the exact required fields"]
    errors: list[str] = []
    for name in ("failure_mechanism", "target_capability", "target_interface", "patch_instruction", "intended_effect"):
        if not isinstance(value[name], str) or not value[name].strip():
            errors.append(f"{name} must be a non-empty string")
    if value["intervention_type"] != "PROMPT_PATCH":
        errors.append("intervention_type is not PROMPT_PATCH")
    for name in ("must_not_change", "regression_risks"):
        if not isinstance(value[name], list) or not all(isinstance(x, str) for x in value[name]):
            errors.append(f"{name} must be a string array")
    return (value if not errors else None), errors


def validate_patch(patch: dict[str, Any], holdout: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    text = json.dumps(patch, sort_keys=True).casefold()
    forbidden = ("holdout", "authority", "tool", "scope", "policy", "evaluator", "production", "registry", "fuzzy", "substring", "success-result", "success result", "answer key")
    findings = [term for term in forbidden if term in text]
    if patch["target_capability"] != CAPABILITY or patch["target_interface"] != INTERFACE:
        findings.append("target binding mismatch")
    if len(patch["patch_instruction"]) > 1800:
        findings.append("patch exceeds bounded size")
    if holdout:
        holdout_text = json.dumps(holdout, sort_keys=True).casefold()
        if any(task["input_request"].casefold() in text for task in holdout):
            findings.append("holdout request leaked into patch")
        if any(task["expected_action"].casefold() in text for task in holdout if task["expected_action"]):
            findings.append("holdout expected action leaked into patch")
    return {"schema": "zth_intervention_validation_v0", "valid": not findings, "findings": findings, "target_capability": patch["target_capability"], "target_interface": patch["target_interface"], "qualification_change": False}


def fresh_holdout() -> list[dict[str, Any]]:
    return [
        {"task_id": "teach-holdout-001", "regime": "OPERATION_VS_STATE_PREDICATE", "input_request": "Determine if docs/teaching-presence-alpha.txt exists in the current repository.", "expected_action": "determine", "expected_object_expression": "docs/teaching-presence-alpha.txt"},
        {"task_id": "teach-holdout-002", "regime": "OPERATION_VS_STATE_PREDICATE", "input_request": "Check whether docs/teaching-presence-beta.txt is present right now.", "expected_action": "check", "expected_object_expression": "docs/teaching-presence-beta.txt"},
        {"task_id": "teach-holdout-003", "regime": "OPERATION_VS_STATE_PREDICATE", "input_request": "Verify that docs/teaching-presence-gamma.txt can be found in the tree.", "expected_action": "verify", "expected_object_expression": "docs/teaching-presence-gamma.txt"},
        {"task_id": "teach-holdout-004", "regime": "OPERATION_VS_STATE_PREDICATE", "input_request": "Confirm whether docs/teaching-presence-delta.txt exists at this time.", "expected_action": "confirm", "expected_object_expression": "docs/teaching-presence-delta.txt"},
        {"task_id": "teach-holdout-005", "regime": "DIRECT_OPERATION_CONTROL", "input_request": "Inspect docs/teaching-control-epsilon.md.", "expected_action": "inspect", "expected_object_expression": "docs/teaching-control-epsilon.md"},
        {"task_id": "teach-holdout-006", "regime": "DIRECT_OPERATION_CONTROL", "input_request": "Amend docs/teaching-control-zeta.md.", "expected_action": "amend", "expected_object_expression": "docs/teaching-control-zeta.md"},
        {"task_id": "teach-holdout-007", "regime": "DIRECT_OPERATION_CONTROL", "input_request": "Index docs/teaching-control-eta.md.", "expected_action": "index", "expected_object_expression": "docs/teaching-control-eta.md"},
        {"task_id": "teach-holdout-008", "regime": "DIRECT_OPERATION_CONTROL", "input_request": "Dispatch docs/teaching-control-theta.md.", "expected_action": "dispatch", "expected_object_expression": "docs/teaching-control-theta.md"},
    ]


def model_free_stage_a(out: Path) -> None:
    if out.exists() and any(out.iterdir()):
        raise RuntimeError("stage A output must be fresh")
    out.mkdir(parents=True, exist_ok=True)
    loc = localize_failure()
    packet = teacher_packet(loc)
    if packet["holdout_material_included"] or "teach-holdout" in json.dumps(packet):
        raise RuntimeError("holdout material leaked into teacher packet")
    write_json(out / "failure_localization.json", loc)
    write_json(out / "teacher_diagnostic_packet.json", packet)
    write_json(out / "teacher_output_schema.json", TEACHER_SCHEMA)
    (out / "teacher_prompt.txt").write_text(teacher_prompt(packet), encoding="utf-8")
    manifest = {"schema": "zth_failure_teaching_stage_a_manifest_v0", "status": "prepared_teacher_call_pending", "prepared_at": now(), "prepared_from_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), "prior_run": str(PRIOR_RUN.relative_to(ROOT)), "prior_failure_task": "composition-v0-003", "prior_failure_response_replayed": False, "teacher_supplier": TEACHER_SUPPLIER, "teacher_calls_budget": 1, "student_calls": 0, "holdout_frozen": False, "holdout_visible_to_teacher": False, "qualification_change": False, "failure_localization_sha256": digest_file(out / "failure_localization.json"), "teacher_packet_sha256": digest_file(out / "teacher_diagnostic_packet.json"), "teacher_schema_sha256": digest_file(out / "teacher_output_schema.json"), "teacher_prompt_sha256": digest_file(out / "teacher_prompt.txt"), "model_calls_made": 0, "tool_calls_made": 0}
    manifest["manifest_sha256"] = digest_bytes(canonical({**manifest, "manifest_sha256": None}))
    write_json(out / "stage_a_manifest.json", manifest)
    write_json(out / "lifecycle.json", {"status": "prepared", "teacher_calls": 0, "student_calls": 0, "tool_calls": 0, "qualification_change": False})


def run_teacher(out: Path) -> None:
    manifest = read_json(out / "stage_a_manifest.json")
    if manifest["manifest_sha256"] != digest_bytes(canonical({**manifest, "manifest_sha256": None})):
        raise RuntimeError("stage A manifest hash mismatch")
    if (out / "teacher_response.json").exists():
        raise RuntimeError("teacher response already exists; refusing a second teacher call")
    prompt = (out / "teacher_prompt.txt").read_text(encoding="utf-8")
    (out / "teacher_call_started.json").write_text(json.dumps({"started_at": now(), "supplier": TEACHER_SUPPLIER, "prompt_sha256": digest_bytes(prompt.encode()), "call_number": 1}, indent=2) + "\n", encoding="utf-8")
    started = time.monotonic()
    response = _default_local_teacher(prompt)
    captured = time.monotonic()
    raw = _response_payload(response, role="local_teacher", started=started, captured=captured, timeout_seconds=int(os.environ.get("ZTH_CAPABILITY_TEACHER_TIMEOUT", "900")), adapter_identity=TEACHER_SUPPLIER)
    write_json(out / "teacher_response.json", raw)
    if raw["metadata"].get("transport_classification") != "model_response":
        raise RuntimeError("teacher transport failed; preserving raw response and stopping")
    parsed, errors = parse_teacher(raw["content"])
    write_json(out / "teacher_parsed.json", {"parse_valid": parsed is not None, "errors": errors, "parsed": parsed})
    if parsed is None:
        raise RuntimeError("teacher structured output invalid; stopping without a retest")
    write_json(out / "candidate_patch.json", parsed)
    validation = validate_patch(parsed)
    write_json(out / "intervention_validation.json", validation)
    if not validation["valid"]:
        raise RuntimeError("teacher patch failed deterministic validation")
    patch = {"schema": "zth_experimental_prompt_patch_v0", "patch_id": "qwen3_1_7b_action_operation_teaching_patch_v0", "status": "CANDIDATE_EXPERIMENTAL", "qualification_change": False, "supplier_id": SUPPLIER, "capability_id": CAPABILITY, "interface_id": INTERFACE, "teacher_supplier": TEACHER_SUPPLIER, "teacher_response_sha256": digest_file(out / "teacher_response.json"), "teacher_parsed_sha256": digest_file(out / "teacher_parsed.json"), "patch_instruction": parsed["patch_instruction"], "intended_effect": parsed["intended_effect"], "must_not_change": parsed["must_not_change"], "regression_risks": parsed["regression_risks"]}
    write_json(PATCH_ARTIFACT, patch)
    write_json(out / "candidate_patch_binding.json", {"artifact": str(PATCH_ARTIFACT.relative_to(ROOT)), "sha256": digest_file(PATCH_ARTIFACT), "status": "CANDIDATE_EXPERIMENTAL", "promoted": False})
    write_json(out / "lifecycle.json", {"status": "teacher_complete", "teacher_calls": 1, "student_calls": 0, "tool_calls": 0, "qualification_change": False})


def prepare_stage_b(out: Path) -> None:
    if not PATCH_ARTIFACT.exists():
        raise RuntimeError("validated candidate patch is required")
    patch = read_json(PATCH_ARTIFACT)
    validation = validate_patch(patch)
    if not validation["valid"]:
        raise RuntimeError("candidate patch no longer validates")
    tasks = fresh_holdout()
    if len(tasks) != 8 or len({t["task_id"] for t in tasks}) != 8:
        raise RuntimeError("holdout must contain eight unique tasks")
    if sum(t["regime"] == "OPERATION_VS_STATE_PREDICATE" for t in tasks) != 4 or sum(t["regime"] == "DIRECT_OPERATION_CONTROL" for t in tasks) != 4:
        raise RuntimeError("holdout regime balance failed")
    if out.exists() and any(out.iterdir()):
        raise RuntimeError("stage B output must be fresh")
    out.mkdir(parents=True, exist_ok=True)
    write_json(HOLDOUT_ARTIFACT, {"schema": "zth_failure_teaching_holdout_v0", "tasks": tasks, "teacher_visible": False, "teacher_calls_complete": True, "qualification_change": False})
    (out / "baseline_schema.json").write_text(json.dumps(router.minimal_schema(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "patched_schema.json").write_text(json.dumps(router.minimal_schema(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    order = [{"arm": arm, "task_id": task["task_id"]} for i, task in enumerate(tasks) for arm in (("baseline", "patched") if i % 2 == 0 else ("patched", "baseline"))]
    for task in tasks:
        td = out / "tasks" / task["task_id"]
        td.mkdir(parents=True, exist_ok=True)
        (td / "baseline_prompt.txt").write_text(router.semantic_prompt(task["input_request"]), encoding="utf-8")
        patched_prompt = router.semantic_prompt(task["input_request"]) + "\n\nBounded interface clarification:\n" + patch["patch_instruction"] + "\n"
        (td / "patched_prompt.txt").write_text(patched_prompt, encoding="utf-8")
        write_json(td / "evaluator.json", {"task_id": task["task_id"], "regime": task["regime"], "expected_action": task["expected_action"], "expected_object_expression": task["expected_object_expression"]})
    manifest = {"schema": "zth_failure_teaching_stage_b_manifest_v0", "status": "prepared_paired_retest", "prepared_at": now(), "prepared_from_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), "teacher_calls_complete": True, "teacher_response_sha256": digest_file(STAGE_A / "teacher_response.json"), "patch_sha256": digest_file(PATCH_ARTIFACT), "holdout_sha256": digest_file(HOLDOUT_ARTIFACT), "holdout_visible_to_teacher": False, "task_count": 8, "baseline_calls": 8, "patched_calls": 8, "task_order": [t["task_id"] for t in tasks], "execution_order": order, "schema_sha256": digest_file(out / "baseline_schema.json"), "prompt_hashes": {t["task_id"]: {"baseline": digest_file(out / "tasks" / t["task_id"] / "baseline_prompt.txt"), "patched": digest_file(out / "tasks" / t["task_id"] / "patched_prompt.txt")} for t in tasks}, "student_model": {"model_id": MODEL_ID, "artifact_sha256": MODEL_SHA, "operative_parameters": PARAMS, "gpu_uuid": GPU_UUID}, "student_calls_made": 0, "teacher_calls_made": 1, "tool_calls_made": 0, "retries": 0, "qualification_change": False}
    manifest["manifest_sha256"] = digest_bytes(canonical({**manifest, "manifest_sha256": None}))
    write_json(out / "stage_b_manifest.json", manifest)
    write_json(out / "lifecycle.json", {"status": "prepared", "teacher_calls": 1, "student_calls": 0, "tool_calls": 0, "retries": 0, "qualification_change": False})


def preflight_model(out: Path) -> tuple[Any, str]:
    spec = runtime.worker_spec()
    models = decomposition.list_models(spec, timeout=30)
    candidate = next((m for m in models.get("data", []) if m.get("id") == MODEL_ID), None)
    meta = (candidate or {}).get("meta") or {}
    if candidate is None or meta.get("n_params") != PARAMS:
        raise RuntimeError("1.7B model preflight binding failed")
    telemetry_url = base.telemetry_base_url()
    telemetry = base.telemetry_preflight(telemetry_url)
    write_json(out / "preflight.json", {"model_meta": meta, "telemetry": telemetry, "model_id": MODEL_ID, "gpu_uuid": GPU_UUID})
    return spec, telemetry_url


def parse_student(content: str) -> tuple[dict[str, str] | None, bool, bool, list[str]]:
    try:
        value = json.loads(content)
    except json.JSONDecodeError as exc:
        return None, False, False, [str(exc)]
    valid = isinstance(value, dict) and set(value) == {"action", "object_expression"} and all(isinstance(value.get(k), str) for k in ("action", "object_expression"))
    return (value if valid else None), True, valid, [] if valid else ["exact two-string contract failed"]


def execute_stage_b(out: Path) -> None:
    manifest = read_json(out / "stage_b_manifest.json")
    if manifest["manifest_sha256"] != digest_bytes(canonical({**manifest, "manifest_sha256": None})):
        raise RuntimeError("stage B manifest hash mismatch")
    if manifest["student_calls_made"] != 0 or manifest["teacher_calls_made"] != 1:
        raise RuntimeError("invalid stage B call state")
    spec, telemetry_url = preflight_model(out)
    total = 0
    for item in manifest["execution_order"]:
        task_id, arm = item["task_id"], item["arm"]
        td = out / "tasks" / task_id
        raw_path = td / f"{arm}_response.json"
        if raw_path.exists():
            raise RuntimeError(f"refusing replay of {task_id}/{arm}")
        prompt_path = td / f"{arm}_prompt.txt"
        prompt = prompt_path.read_text(encoding="utf-8")
        call = {"task_id": task_id, "arm": arm, "started_at": now(), "prompt_sha256": digest_file(prompt_path), "schema_sha256": digest_file(out / f"{arm}_schema.json"), "supplier_id": SUPPLIER, "model_id": MODEL_ID}
        write_json(td / f"{arm}_call_started.json", call)
        started = time.monotonic()
        sampler = PowerSampler(lambda: read_gpu_power(GPU_UUID, base_url=telemetry_url), expected_gpu_uuid=GPU_UUID, sample_interval_seconds=POWER_INTERVAL)
        sampler.start()
        response = decomposition.structured_call(spec, prompt, router.response_format(), MAX_TOKENS, TIMEOUT)
        captured = time.monotonic()
        samples = sampler.stop()
        energy = integrate_energy_joules(samples, sample_interval_seconds=POWER_INTERVAL, expected_gpu_uuid=GPU_UUID)
        raw = {"status": response.status, "content": response.content, "metadata": response.metadata(), "wall_elapsed_ms": round((captured - started) * 1000, 3), "gross_energy_joules": energy, "arm": arm, "task_id": task_id}
        write_json(raw_path, raw)
        write_json(td / f"{arm}_power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "gpu_uuid": GPU_UUID, "samples": [{"timestamp_utc": s.timestamp_utc, "power_watts": s.power_watts, "gpu_uuid": s.gpu_uuid, "sequence": s.sequence} for s in samples]})
        total += 1
    write_json(out / "lifecycle.json", {"status": "student_execution_complete", "teacher_calls": 1, "student_calls": total, "tool_calls": 0, "retries": 0, "qualification_change": False})


def classify(observed: dict[str, str] | None, task: dict[str, Any], parse_valid: bool, contract_valid: bool) -> dict[str, Any]:
    if not parse_valid:
        failure = "INVALID_CONTRACT"
    elif not contract_valid:
        failure = "INVALID_CONTRACT"
    elif observed["action"] == task["expected_action"] and observed["object_expression"] == task["expected_object_expression"]:
        failure = None
    elif observed["action"] in {"exists", "present", "found", "available"}:
        failure = "STATE_PREDICATE_AS_ACTION"
    elif observed["action"] in {"extract", "return", "report", "record", "identify"}:
        failure = "INSTRUCTION_VERB_AS_ACTION"
    elif observed["object_expression"] != task["expected_object_expression"]:
        failure = "OBJECT_EXPRESSION_FAILURE"
    else:
        failure = "OTHER_ACTION_FAILURE"
    safe = bool(contract_valid and observed and observed["action"] in {"determine", "check", "verify", "confirm", "inspect", "amend", "index", "dispatch"} and observed["object_expression"].startswith("docs/"))
    return {"parse_valid": parse_valid, "contract_valid": contract_valid, "action_exact": bool(contract_valid and observed and observed["action"] == task["expected_action"]), "object_expression_exact": bool(contract_valid and observed and observed["object_expression"] == task["expected_object_expression"]), "both_fields_exact": bool(contract_valid and observed and observed["action"] == task["expected_action"] and observed["object_expression"] == task["expected_object_expression"]), "safe_semantic_binding": safe, "failure_class": failure}


def closeout(out: Path) -> None:
    tasks = {t["task_id"]: t for t in read_json(HOLDOUT_ARTIFACT)["tasks"]}
    rows: list[dict[str, Any]] = []
    for tid, task in tasks.items():
        row: dict[str, Any] = {"task_id": tid, "regime": task["regime"]}
        for arm in ("baseline", "patched"):
            raw = read_json(out / "tasks" / tid / f"{arm}_response.json")
            obs, parse_valid, contract_valid, diagnostics = parse_student(raw.get("content", ""))
            scoring = classify(obs, task, parse_valid, contract_valid)
            row[arm] = {"observed": obs, "diagnostics": diagnostics, **scoring, "latency_ms": raw.get("wall_elapsed_ms"), "gross_energy_joules": raw.get("gross_energy_joules")}
        rows.append(row)
    def agg(arm: str, subset: list[dict[str, Any]]) -> dict[str, Any]:
        vals = [r[arm] for r in subset]
        return {"tasks": len(vals), "parse_valid": sum(v["parse_valid"] for v in vals), "contract_valid": sum(v["contract_valid"] for v in vals), "action_exact": sum(v["action_exact"] for v in vals), "object_expression_exact": sum(v["object_expression_exact"] for v in vals), "both_fields_exact": sum(v["both_fields_exact"] for v in vals), "safe_semantic_binding": sum(v["safe_semantic_binding"] for v in vals), "state_predicate_as_action": sum(v["failure_class"] == "STATE_PREDICATE_AS_ACTION" for v in vals), "invalid_contract": sum(v["failure_class"] == "INVALID_CONTRACT" for v in vals), "latency_ms": {"median": statistics.median([v["latency_ms"] for v in vals]), "mean": statistics.mean([v["latency_ms"] for v in vals]), "p95": sorted(v["latency_ms"] for v in vals)[min(len(vals) - 1, round((len(vals) - 1) * .95))]}, "gross_energy_joules": {"mean": statistics.mean([v["gross_energy_joules"] for v in vals]), "median": statistics.median([v["gross_energy_joules"] for v in vals]), "total": sum(v["gross_energy_joules"] for v in vals)}}
    targeted = [r for r in rows if r["regime"] == "OPERATION_VS_STATE_PREDICATE"]
    controls = [r for r in rows if r["regime"] == "DIRECT_OPERATION_CONTROL"]
    baseline = agg("baseline", rows); patched = agg("patched", rows)
    comparison = {"schema": "zth_teaching_effect_comparison_v0", "baseline": baseline, "patched": patched, "baseline_targeted": agg("baseline", targeted), "patched_targeted": agg("patched", targeted), "baseline_control": agg("baseline", controls), "patched_control": agg("patched", controls), "new_invalid_contracts": patched["invalid_contract"] - baseline["invalid_contract"], "target_state_predicate_delta": patched["state_predicate_as_action"] - baseline["state_predicate_as_action"], "intervention_supported": patched["baseline_targeted" if False else "action_exact"] > baseline["action_exact"] and agg("patched", targeted)["action_exact"] > agg("baseline", targeted)["action_exact"] and agg("patched", targeted)["state_predicate_as_action"] < agg("baseline", targeted)["state_predicate_as_action"] and patched["invalid_contract"] <= baseline["invalid_contract"], "qualification_change": False}
    write_json(out / "teaching_effect_comparison.json", comparison)
    write_json(out / "matrix.json", {"schema": "zth_failure_teaching_matrix_v0", "rows": rows, "comparison": comparison, "primary_markers": {"FAILURE_LOCALIZATION_TO_CAPABILITY_INTERFACE_DEMONSTRATED": True, "BOUNDED_TEACHER_INTERVENTION_LOOP_DEMONSTRATED": True, "TEACHER_PROPOSED_INTERVENTION_IMPROVED_FRESH_HOLDOUT": comparison["intervention_supported"], "SUPPLIER_CAPABILITY_IMPROVEMENT_EVIDENCE_DEMONSTRATED": comparison["intervention_supported"], "SELF_TEACHING_DEMONSTRATED": False, "QUALIFICATION_PROMOTED": False, "NEXT_DECISION": "SUPERVISED_REVIEW_OF_DEVELOPMENTAL_CAPABILITY_EVIDENCE" if comparison["intervention_supported"] else "DIAGNOSE_INTERVENTION_FAILURE"}})
    write_json(out / "lifecycle.json", {"status": "closeout_complete", "teacher_calls": 1, "student_calls": 16, "tool_calls": 0, "retries": 0, "escalations": 0, "qualification_change": False})
    print(json.dumps(comparison, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare-stage-a", action="store_true")
    group.add_argument("--run-teacher", action="store_true")
    group.add_argument("--prepare-stage-b", action="store_true")
    group.add_argument("--execute-stage-b", action="store_true")
    group.add_argument("--closeout", action="store_true")
    parser.add_argument("--stage-a", type=Path, default=STAGE_A)
    parser.add_argument("--stage-b", type=Path, default=STAGE_B)
    args = parser.parse_args()
    if args.prepare_stage_a:
        model_free_stage_a(args.stage_a)
    elif args.run_teacher:
        run_teacher(args.stage_a)
    elif args.prepare_stage_b:
        prepare_stage_b(args.stage_b)
    elif args.execute_stage_b:
        execute_stage_b(args.stage_b)
    else:
        closeout(args.stage_b)


if __name__ == "__main__":
    main()
