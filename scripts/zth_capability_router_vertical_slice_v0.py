#!/usr/bin/env python3
"""Experimental, fixture-backed ZTH capability-router vertical slice."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from local_harness.orchestration_packet import assemble_orchestration_packet, validate_orchestration_packet
from local_harness.prompt_patch_library import PromptPatchLibrary
from local_harness.resource_telemetry import build_resource_telemetry
from local_harness.stage_a_power_telemetry import PowerSampler, integrate_energy_joules, read_gpu_power
from local_harness.triage_router_rules import route_messy_input
from scripts import zth_qwen3_0_6b_clean_scope_logic_probe as base
from scripts import zth_qwen3_1_7b_atomic_scope_relation_decomposition as decomposition
from scripts import zth_qwen3_1_7b_clean_scope_logic_probe as runtime

ROOT = base.ROOT
TASKS = ROOT / "docs/research/CAPABILITY_ROUTER_VERTICAL_SLICE_V0_TASKS_2026-08-22.json"
REGISTRY = ROOT / "docs/research/CAPABILITY_ROUTER_EXPERIMENTAL_REGISTRY_V0_2026-08-22.json"
PATCH_DIR = ROOT / "examples/prompt_patches"
EXPECTED_MODEL_ID = runtime.EXPECTED_MODEL_ID
EXPECTED_MODEL_SHA = runtime.EXPECTED_MODEL_SHA
EXPECTED_PARAMS = runtime.EXPECTED_PARAMS
EXPECTED_CTX = runtime.EXPECTED_EFFECTIVE_CTX
EXPECTED_TRAIN_CTX = runtime.EXPECTED_TRAIN_CTX
EXPECTED_GPU_UUID = runtime.EXPECTED_GPU_UUID
MAX_OUTPUT_TOKENS = runtime.MAX_OUTPUT_TOKENS
TIMEOUT_SECONDS = runtime.TIMEOUT_SECONDS
POWER_INTERVAL_SECONDS = runtime.POWER_INTERVAL_SECONDS
IDLE_SECONDS = runtime.IDLE_SECONDS


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def norm(value: Any) -> str:
    return " ".join(str(value).casefold().strip().split())


def load_tasks() -> list[dict[str, Any]]:
    payload = json.loads(TASKS.read_text(encoding="utf-8"))
    tasks = payload.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != 8:
        raise RuntimeError("Router V0 requires exactly 8 frozen tasks")
    if len({task.get("task_id") for task in tasks}) != 8:
        raise RuntimeError("Router V0 task IDs must be unique")
    return tasks


def load_registry() -> dict[str, Any]:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if payload.get("automatic_promotion") is not False:
        raise RuntimeError("registry automatic promotion must be false")
    entries = payload.get("entries")
    required = {"capability_id", "supplier_id", "supplier_type", "interface_id", "evidence_artifact", "evidence_scope", "status"}
    if not isinstance(entries, list) or not entries:
        raise RuntimeError("registry has no entries")
    for entry in entries:
        if not required <= set(entry):
            raise RuntimeError("registry entry missing evidence-linked fields")
        if entry["status"] not in {"QUALIFIED_EXPLORATORY", "NOT_QUALIFIED", "UNKNOWN"}:
            raise RuntimeError("unsupported supplier status")
        if not (ROOT / entry["evidence_artifact"]).is_file():
            raise RuntimeError(f"registry evidence missing: {entry['evidence_artifact']}")
    return payload


def registry_index(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {entry["capability_id"]: entry for entry in registry["entries"]}


def minimal_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {"action": {"type": "string"}, "object_expression": {"type": "string"}},
        "required": ["action", "object_expression"],
        "additionalProperties": False,
    }


def response_format() -> dict[str, Any]:
    return {"type": "json_schema", "json_schema": {"name": "router_v0_minimal_semantic_atom", "schema": minimal_schema()}}


def semantic_prompt(task: dict[str, Any]) -> str:
    return (
        f"Request clause:\n{task['input_request']}\n\n"
        "Required structured fields describe the request clause.\n\n"
        "action:\n"
        "the operation expressed in the request clause.\n\n"
        "object_expression:\n"
        "the phrase describing what the action is applied to.\n\n"
        "/no_think"
    )


def validate_model_free() -> dict[str, Any]:
    tasks = load_tasks()
    registry = load_registry()
    index = registry_index(registry)
    expected_counts = {"DETERMINISTIC_CODE": 2, "MODEL": 4, "REVIEW_OR_ESCALATION": 2}
    actual_counts: dict[str, int] = {}
    for task in tasks:
        supplier_type = task["expected_supplier_type"]
        actual_counts[supplier_type] = actual_counts.get(supplier_type, 0) + 1
        for capability in task["required_capabilities"]:
            if capability not in index:
                raise RuntimeError(f"task references unknown capability: {capability}")
        if supplier_type == "DETERMINISTIC_CODE" and task["expected_model_call_count"] != 0:
            raise RuntimeError("deterministic task has nonzero model budget")
        if supplier_type == "MODEL" and task["expected_model_call_count"] != 1:
            raise RuntimeError("model task must have one model call")
        if supplier_type == "REVIEW_OR_ESCALATION" and task["expected_model_call_count"] != 0:
            raise RuntimeError("review task has a model budget")
        if supplier_type == "REVIEW_OR_ESCALATION":
            for capability in task["required_capabilities"]:
                if index[capability]["status"] not in {"NOT_QUALIFIED", "UNKNOWN"}:
                    raise RuntimeError("review fixture is not bound to an unsupported capability")
    if actual_counts != expected_counts:
        raise RuntimeError(f"fixture distribution mismatch: {actual_counts}")
    return {
        "tasks": tasks,
        "registry": registry,
        "registry_index": index,
        "task_sha256": sha_file(TASKS),
        "registry_sha256": sha_file(REGISTRY),
        "schema_sha256": sha_bytes(canonical(minimal_schema())),
        "format_sha256": sha_bytes(canonical(response_format())),
        "prompts": {task["task_id"]: semantic_prompt(task) for task in tasks if task["expected_supplier_type"] == "MODEL"},
    }


def build_packets(task: dict[str, Any], index: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    triage = route_messy_input(task["input_request"], triage_id=f"triage_{task['task_id']}", source="capability_router_vertical_slice_v0")
    library = PromptPatchLibrary()
    library.load_dir(PATCH_DIR)
    orchestration = assemble_orchestration_packet(triage, library, orchestration_id=f"orch_{task['task_id']}")
    validate_orchestration_packet(orchestration, library)
    candidates = [index[capability] for capability in task["required_capabilities"]]
    selected = next((entry for entry in candidates if entry["status"] == "QUALIFIED_EXPLORATORY"), None)
    if selected is None:
        selected_type = "REVIEW_OR_ESCALATION"
        selected_id = "review_queue_v0"
        reason = "No qualified exploratory supplier exists for the required capability; fail closed to review."
        terminal = "ready_for_review"
    elif selected["supplier_type"] == "DETERMINISTIC_CODE":
        selected_type = "DETERMINISTIC_CODE"
        selected_id = selected["supplier_id"]
        reason = "Qualified deterministic supplier is sufficient for canonical packet operands."
        terminal = "terminal_success"
    else:
        selected_type = "MODEL"
        selected_id = selected["supplier_id"]
        reason = "Qualified exploratory model supplier is required for the bounded semantic atom."
        terminal = "pending_validation"
    packet = {
        "schema": "zth_experimental_router_packet_v0",
        "task_id": task["task_id"],
        "input_request": task["input_request"],
        "requested_target": task.get("packet_facts", {}).get("requested_target"),
        "packet_facts": task.get("packet_facts", {}),
        "required_capabilities": task["required_capabilities"],
        "candidate_suppliers": [{"supplier_id": item["supplier_id"], "supplier_type": item["supplier_type"], "status": item["status"], "interface_id": item["interface_id"]} for item in candidates],
        "selected_supplier": {"supplier_id": selected_id, "supplier_type": selected_type},
        "selection_reason": reason,
        "initial_terminal_state": terminal,
        "triage_id": triage["triage_id"],
        "orchestration_id": orchestration["orchestration_id"],
        "authority_boundary": "experimental fixture-backed read-only/dry-run path; no execution authority",
    }
    return triage, orchestration, packet


def parse_model_output(content: str) -> tuple[dict[str, str] | None, bool, bool, list[str]]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        return None, False, False, [str(exc)]
    if not isinstance(parsed, dict):
        return None, True, False, ["response is not an object"]
    if set(parsed) != {"action", "object_expression"} or not all(isinstance(parsed.get(field), str) for field in ("action", "object_expression")):
        return None, True, False, ["exact two-string semantic atom contract failed"]
    return parsed, True, True, []


def deterministic_policy(task: dict[str, Any]) -> bool:
    facts = task["packet_facts"]
    return not (bool(facts.get("target_match")) and bool(facts.get("operation_match")))


def prepare(out: Path) -> None:
    if out.exists() and any(out.iterdir()):
        raise RuntimeError("output must be fresh")
    out.mkdir(parents=True, exist_ok=True)
    binding = validate_model_free()
    for task in binding["tasks"]:
        triage, orchestration, packet = build_packets(task, binding["registry_index"])
        task_dir = out / "tasks" / task["task_id"]
        task_dir.mkdir(parents=True, exist_ok=True)
        write_json(task_dir / "fixture.json", task)
        write_json(task_dir / "vogon_triage_packet.json", triage)
        write_json(task_dir / "orchestration_packet.json", orchestration)
        write_json(task_dir / "router_packet.json", packet)
        if task["expected_supplier_type"] == "MODEL":
            (task_dir / "semantic_prompt.txt").write_text(binding["prompts"][task["task_id"]], encoding="utf-8")
    manifest = {
        "schema": "zth_capability_router_vertical_slice_v0_manifest_v1",
        "status": "prepared_exploratory_not_production",
        "prepared_at": now(),
        "prepared_from_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "driver": str(Path(__file__).relative_to(ROOT)),
        "driver_sha256": sha_file(Path(__file__).resolve()),
        "task_manifest_sha256": binding["task_sha256"],
        "registry_sha256": binding["registry_sha256"],
        "schema_sha256": binding["schema_sha256"],
        "response_format_sha256": binding["format_sha256"],
        "task_count": 8,
        "expected_model_calls": 4,
        "expected_deterministic_calls": 0,
        "expected_external_calls": 0,
        "expected_teacher_calls": 0,
        "runtime": {"model_id": EXPECTED_MODEL_ID, "artifact_sha256": EXPECTED_MODEL_SHA, "operative_parameters": EXPECTED_PARAMS, "effective_n_ctx": EXPECTED_CTX, "n_ctx_train": EXPECTED_TRAIN_CTX},
        "hardware": {"gpu_uuid": EXPECTED_GPU_UUID, "v100_touched": False},
        "telemetry": {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "sample_interval_seconds": POWER_INTERVAL_SECONDS},
        "model_calls_made": False,
    }
    manifest["manifest_sha256"] = sha_bytes(canonical({**manifest, "manifest_sha256": None}))
    write_json(out / "router_manifest.json", manifest)
    write_json(out / "lifecycle.json", {"status": "prepared", "model_calls_made": False, "model_calls": 0, "updated_at": now()})
    print(json.dumps({"status": "prepared", "tasks": 8, "expected_model_calls": 4, "model_calls": 0}, indent=2))


def execute(out: Path) -> None:
    binding = validate_model_free()
    manifest = json.loads((out / "router_manifest.json").read_text(encoding="utf-8"))
    if manifest["manifest_sha256"] != sha_bytes(canonical({**manifest, "manifest_sha256": None})):
        raise RuntimeError("router manifest digest mismatch")
    for key, value in (("task_manifest_sha256", binding["task_sha256"]), ("registry_sha256", binding["registry_sha256"]), ("schema_sha256", binding["schema_sha256"]), ("response_format_sha256", binding["format_sha256"])):
        if manifest[key] != value:
            raise RuntimeError(f"frozen router binding mismatch: {key}")
    spec = runtime.worker_spec()
    models = decomposition.list_models(spec, timeout=30)
    model = next((item for item in models.get("data", []) if item.get("id") == EXPECTED_MODEL_ID), None)
    meta = (model or {}).get("meta") or {}
    if model is None or meta.get("n_params") != EXPECTED_PARAMS or meta.get("n_ctx") != EXPECTED_CTX or meta.get("n_ctx_train") != EXPECTED_TRAIN_CTX:
        raise RuntimeError("runtime binding mismatch")
    telemetry_url = base.telemetry_base_url()
    telemetry_preflight = base.telemetry_preflight(telemetry_url)
    idle_samples, idle_summary = base.sample_window(IDLE_SECONDS, telemetry_url)
    write_json(out / "preflight.json", {"model_meta": meta, "telemetry": telemetry_preflight, "task_manifest_sha256": binding["task_sha256"], "registry_sha256": binding["registry_sha256"]})
    write_json(out / "idle_power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "summary": idle_summary, "samples": idle_samples})
    write_json(out / "lifecycle.json", {"status": "running", "model_calls_made": False, "model_calls": 0, "started_at": now()})
    rows: list[dict[str, Any]] = []
    model_calls = 0
    for task in binding["tasks"]:
        task_dir = out / "tasks" / task["task_id"]
        router_packet = json.loads((task_dir / "router_packet.json").read_text(encoding="utf-8"))
        selected_type = router_packet["selected_supplier"]["supplier_type"]
        trace: dict[str, Any] = {"schema": "zth_router_v0_route_trace_v1", "task_id": task["task_id"], "input": task["input_request"], "packet": {"triage": "vogon_triage_packet.json", "orchestration": "orchestration_packet.json", "router": "router_packet.json"}, "required_capabilities": task["required_capabilities"], "candidate_suppliers": router_packet["candidate_suppliers"], "selected_supplier": router_packet["selected_supplier"], "selection_reason": router_packet["selection_reason"], "model_call": None, "validator_result": None, "terminal_state": None}
        if selected_type == "DETERMINISTIC_CODE":
            observed_policy = deterministic_policy(task)
            validation = observed_policy == task["expected_policy_result"]
            trace["validator_result"] = {"status": "passed" if validation else "failed", "policy_result": observed_policy}
            trace["terminal_state"] = "terminal_success" if validation else "ready_for_review"
            row = {"task_id": task["task_id"], "expected_supplier_type": task["expected_supplier_type"], "selected_supplier_type": selected_type, "expected_model_calls": 0, "model_calls": 0, "validator_status": "passed" if validation else "failed", "terminal_state": trace["terminal_state"], "task_correct": validation, "model_avoided": True, "policy_result": observed_policy}
        elif selected_type == "MODEL":
            model_calls += 1
            prompt = (task_dir / "semantic_prompt.txt").read_text(encoding="utf-8")
            started = time.monotonic()
            started_at = now()
            sampler = PowerSampler(lambda: read_gpu_power(EXPECTED_GPU_UUID, base_url=telemetry_url), expected_gpu_uuid=EXPECTED_GPU_UUID, sample_interval_seconds=POWER_INTERVAL_SECONDS)
            sampler.start()
            response = decomposition.structured_call(spec, prompt, response_format(), MAX_OUTPUT_TOKENS, TIMEOUT_SECONDS)
            captured = time.monotonic()
            samples = sampler.stop()
            energy = integrate_energy_joules(samples, sample_interval_seconds=POWER_INTERVAL_SECONDS, expected_gpu_uuid=EXPECTED_GPU_UUID)
            metadata = response.metadata()
            raw = {"status": response.status, "content": response.content, "metadata": metadata, "request_started_at": started_at, "response_captured_at": now(), "wall_elapsed_ms": round((captured - started) * 1000, 3)}
            write_json(task_dir / "response.json", raw)
            parsed, parse_valid, contract_valid, diagnostics = parse_model_output(response.content)
            action_correct = bool(parsed and norm(parsed["action"]) == norm(task["packet_facts"]["expected_action"]))
            object_correct = bool(parsed and norm(parsed["object_expression"]) == norm(task["packet_facts"]["expected_object_expression"]))
            binding_correct = bool(parsed and norm(parsed["object_expression"]) == norm(task["packet_facts"]["requested_target"]))
            validation = parse_valid and contract_valid and action_correct and object_correct and binding_correct
            write_json(task_dir / "validation.json", {"validation_status": "passed" if validation else "failed", "parse_valid": parse_valid, "contract_valid": contract_valid, "diagnostics": diagnostics, "action_correct": action_correct, "object_expression_correct": object_correct, "direct_target_binding": binding_correct})
            write_json(task_dir / "power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "gpu_uuid": EXPECTED_GPU_UUID, "samples": [{"timestamp_utc": sample.timestamp_utc, "monotonic_seconds": sample.monotonic_seconds, "gpu_uuid": sample.gpu_uuid, "power_watts": sample.power_watts, "sequence": sample.sequence} for sample in samples]})
            trace["model_call"] = {"count": 1, "prompt_sha256": sha_bytes(prompt.encode()), "response_artifact": "response.json", "model_id": EXPECTED_MODEL_ID}
            trace["validator_result"] = {"status": "passed" if validation else "failed", "parse_valid": parse_valid, "contract_valid": contract_valid, "action_correct": action_correct, "object_expression_correct": object_correct, "direct_target_binding": binding_correct, "gross_energy_joules": energy}
            trace["terminal_state"] = "terminal_success" if validation else "ready_for_review"
            row = {"task_id": task["task_id"], "expected_supplier_type": task["expected_supplier_type"], "selected_supplier_type": selected_type, "expected_model_calls": 1, "model_calls": 1, "validator_status": "passed" if validation else "failed", "terminal_state": trace["terminal_state"], "task_correct": validation, "model_avoided": False, "parse_valid": parse_valid, "contract_valid": contract_valid, "action_correct": action_correct, "object_expression_correct": object_correct, "direct_target_binding": binding_correct, "latency_ms": raw["wall_elapsed_ms"], "gross_energy_joules": energy}
        else:
            trace["validator_result"] = {"status": "not_attempted", "reason": "unqualified_or_unknown_capability"}
            trace["terminal_state"] = "ready_for_review"
            row = {"task_id": task["task_id"], "expected_supplier_type": task["expected_supplier_type"], "selected_supplier_type": selected_type, "expected_model_calls": 0, "model_calls": 0, "validator_status": "not_attempted_fail_closed", "terminal_state": "ready_for_review", "task_correct": True, "model_avoided": True, "fail_closed": True}
        write_json(task_dir / "route_trace.json", trace)
        write_json(task_dir / "scorecard.json", {"schema": "zth_router_v0_task_scorecard_v1", **row, "expected_terminal_state": task["expected_terminal_state"], "expected_validation_result": task["expected_validation_result"], "required_capabilities": task["required_capabilities"]})
        rows.append(row)
    aggregate = {
        "schema": "zth_router_v0_aggregate_v1",
        "task_count": len(rows),
        "tasks_terminally_correct": sum(row["task_correct"] for row in rows),
        "router_supplier_choice_correct": sum(row["selected_supplier_type"] == task["expected_supplier_type"] for row, task in zip(rows, binding["tasks"])),
        "no_model_opportunities": 2,
        "no_model_opportunities_avoided": sum(row["model_avoided"] for row in rows if row["expected_supplier_type"] == "DETERMINISTIC_CODE"),
        "semantic_routes": 4,
        "semantic_routes_correct": sum(row["task_correct"] for row in rows if row["expected_supplier_type"] == "MODEL"),
        "unsupported_tasks": 2,
        "unsupported_failed_closed": sum(row["task_correct"] for row in rows if row["expected_supplier_type"] == "REVIEW_OR_ESCALATION"),
        "unnecessary_model_calls": sum(max(0, row["model_calls"] - row["expected_model_calls"]) for row in rows),
        "unnecessary_escalations": 0,
        "duplicate_calls": 0,
        "validator_disagreements": 0,
        "final_review_states": sum(row["terminal_state"] == "ready_for_review" for row in rows),
        "resource": {"total_model_calls": model_calls, "model_calls_avoided": sum(row["model_avoided"] for row in rows), "model_1_7b_calls": model_calls, "model_30b_calls": 0, "external_calls": 0},
        "idle_power": idle_summary,
        "execution": {"teacher_calls": 0, "retries": 0, "escalations": 0, "adaptations": 0},
    }
    write_json(out / "aggregate.json", aggregate)
    write_json(out / "lifecycle.json", {"status": "terminal", "completed_at": now(), "model_calls_made": model_calls > 0, "model_calls": model_calls, "supplier_model_calls": model_calls, "deterministic_calls": 2, "teacher_calls": 0, "retries": 0, "escalations": 0, "duplicate_calls": 0})
    print(json.dumps({"status": "terminal", "tasks": 8, "model_calls": model_calls, "review_states": aggregate["final_review_states"]}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare", action="store_true")
    group.add_argument("--execute", action="store_true")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    (prepare if args.prepare else execute)(args.output_dir)


if __name__ == "__main__":
    main()
