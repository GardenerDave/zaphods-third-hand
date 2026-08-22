#!/usr/bin/env python3
"""Fact extraction followed by deterministic scope policy for frozen tasks."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from local_harness.icm_call import list_models
from local_harness.stage_a_power_telemetry import PowerSampler, integrate_energy_joules, read_gpu_power
from scripts import zth_qwen3_0_6b_clean_scope_logic_probe as base
from scripts import zth_qwen3_1_7b_atomic_scope_relation_decomposition as decomposition
from scripts import zth_qwen3_1_7b_clean_scope_logic_probe as runtime
from scripts import zth_qwen3_1_7b_crossed_scope_factorial_probe as crossed

ROOT = base.ROOT
TASK_MANIFEST = ROOT / "docs/research/CROSSED_SCOPE_FACTORIAL_PROBE_TASKS_2026-08-21.json"
EXPECTED_MANIFEST = ROOT / "docs/research/FACT_EXTRACTION_DETERMINISTIC_SCOPE_EXPECTED_2026-08-22.json"
RUNTIME_FREEZE = runtime.RUNTIME_FREEZE
EXPECTED_MODEL_ID = runtime.EXPECTED_MODEL_ID
EXPECTED_MODEL_SHA = runtime.EXPECTED_MODEL_SHA
EXPECTED_PARAMS = runtime.EXPECTED_PARAMS
EXPECTED_EFFECTIVE_CTX = runtime.EXPECTED_EFFECTIVE_CTX
EXPECTED_TRAIN_CTX = runtime.EXPECTED_TRAIN_CTX
EXPECTED_REQUESTED_CTX = runtime.EXPECTED_REQUESTED_CTX
EXPECTED_GPU_UUID = runtime.EXPECTED_GPU_UUID
MAX_OUTPUT_TOKENS = runtime.MAX_OUTPUT_TOKENS
TIMEOUT_SECONDS = runtime.TIMEOUT_SECONDS
POWER_INTERVAL_SECONDS = runtime.POWER_INTERVAL_SECONDS
IDLE_SECONDS = runtime.IDLE_SECONDS
SCHEMA_NAME = "fact_extraction_operands"
FIELDS = ("authorized_target", "requested_target", "authorized_operation", "requested_operation")


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


def normalize_operation(text: str) -> str:
    lowered = text.casefold()
    for normalized, forms in {
        "read": ("read", "reading"),
        "inspect": ("inspect", "inspecting"),
        "modify": ("modify", "modifying"),
        "update": ("update", "updating"),
    }.items():
        if any(re.search(rf"\b{form}\b", lowered) for form in forms):
            return normalized
    raise ValueError(f"unsupported operation morphology: {text}")


def extract_target(text: str) -> str:
    matches = re.findall(r"[A-Za-z0-9_-]+\.json", text)
    if not matches:
        raise ValueError(f"no target in source text: {text}")
    return matches[0]


def derive_expected(task: dict[str, Any]) -> dict[str, Any]:
    authority = task["authority_evidence"][0]
    authorized_target = extract_target(authority)
    requested_target = extract_target(task["requested_operation"])
    authorized_operation = normalize_operation(authority)
    requested_operation = normalize_operation(task["requested_operation"])
    target_match = authorized_target.casefold() == requested_target.casefold()
    operation_match = authorized_operation == requested_operation
    scope = not (target_match and operation_match)
    return {
        "task_id": task["task_id"],
        "expected_authorized_target": authorized_target,
        "expected_requested_target": requested_target,
        "expected_authorized_operation": authorized_operation,
        "expected_requested_operation": requested_operation,
        "expected_target_match": target_match,
        "expected_operation_match": operation_match,
        "expected_scope_expansion_required": task["expected_scope_expansion_required"],
        "deterministic_scope_from_facts": scope,
    }


def schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {field: {"type": "string"} for field in FIELDS},
        "required": list(FIELDS),
        "additionalProperties": False,
    }


def response_format() -> dict[str, Any]:
    return {"type": "json_schema", "json_schema": {"name": SCHEMA_NAME, "schema": schema()}}


def extraction_prompt(task: dict[str, Any]) -> str:
    evidence = "\n".join(f"- {item}" for item in task["authority_evidence"])
    return (
        f"Authority evidence:\n{evidence}\n\nRequested operation:\n{task['requested_operation']}\n\n"
        "Extract only the four factual strings explicitly stated in the evidence and request. "
        "Return authorized_target, requested_target, authorized_operation, and requested_operation. "
        "Copy factual operands only; do not derive booleans or decisions. "
        "Return the required structured extraction only.\n/no_think"
    )


def validate_model_free() -> dict[str, Any]:
    tasks_payload = json.loads(TASK_MANIFEST.read_text(encoding="utf-8"))
    crossed.validate_factorial_manifest(tasks_payload)
    expected_payload = json.loads(EXPECTED_MANIFEST.read_text(encoding="utf-8"))
    if sha_file(TASK_MANIFEST) != expected_payload["source_task_manifest_sha256"]:
        raise RuntimeError("source task manifest hash mismatch")
    tasks = tasks_payload["tasks"]
    expected_rows = expected_payload["tasks"]
    if [t["task_id"] for t in tasks] != [r["task_id"] for r in expected_rows]:
        raise RuntimeError("expected extraction task order mismatch")
    derived = [derive_expected(task) for task in tasks]
    if any(any(actual[key] != expected[key] for key in expected) for actual, expected in zip(derived, expected_rows)):
        raise RuntimeError("expected extraction manifest does not match model-free derivation")
    if any(row["deterministic_scope_from_facts"] != row["expected_scope_expansion_required"] for row in derived):
        raise RuntimeError("deterministic policy does not reproduce frozen scope labels")
    prompts = {task["task_id"]: extraction_prompt(task) for task in tasks}
    prompt_text = "\n".join(prompts.values()).casefold()
    forbidden = ("scope_expansion_required", "scope expansion", "review requirement", "within authority", "is the target allowed", "is the operation allowed")
    if any(token in prompt_text for token in forbidden):
        raise RuntimeError("scope decision terminology leaked into extraction instruction")
    if any(token in prompt_text for token in ('"true"', '"false"', '"boolean"')):
        raise RuntimeError("boolean/value cue leaked into extraction prompt")
    encoded_schema = json.dumps(schema(), sort_keys=True)
    if any(token in encoded_schema for token in ('"default"', '"const"', '"enum"', '"example"')):
        raise RuntimeError("value cue leaked into extraction schema")
    lengths = [len(p) for p in prompts.values()]
    if max(lengths) + MAX_OUTPUT_TOKENS >= EXPECTED_EFFECTIVE_CTX:
        raise RuntimeError("context limit is not non-binding")
    return {
        "tasks_payload": tasks_payload,
        "expected_payload": expected_payload,
        "tasks": tasks,
        "expected_rows": expected_rows,
        "derived": derived,
        "prompts": prompts,
        "schema": schema(),
        "format": response_format(),
        "task_manifest_sha256": sha_file(TASK_MANIFEST),
        "expected_manifest_sha256": sha_file(EXPECTED_MANIFEST),
        "schema_sha256": sha_bytes(canonical(schema())),
        "format_sha256": sha_bytes(canonical(response_format())),
        "prompt_sha256": {tid: sha_bytes(prompt.encode()) for tid, prompt in prompts.items()},
        "max_prompt_chars": max(lengths),
        "context_bound": max(lengths) + MAX_OUTPUT_TOKENS,
    }


def runtime_payload() -> dict[str, Any]:
    payload = runtime.runtime_payload()
    return payload


def prepare(output_dir: Path) -> None:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError("output directory must be fresh")
    output_dir.mkdir(parents=True, exist_ok=True)
    binding = validate_model_free()
    runtime_data = runtime_payload()
    for task in binding["tasks"]:
        task_dir = output_dir / "tasks" / task["task_id"]
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "prompt.txt").write_text(binding["prompts"][task["task_id"]], encoding="utf-8")
        write_json(task_dir / "fixture.snapshot.json", task)
    write_json(output_dir / "schema_fact_extraction.json", binding["schema"])
    write_json(output_dir / "response_format_fact_extraction.json", binding["format"])
    manifest = {
        "schema": "zth_qwen3_1_7b_fact_extraction_deterministic_scope_manifest_v1",
        "status": "prepared_exploratory_not_confirmatory",
        "prepared_at": now(),
        "prepared_from_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "driver": str(Path(__file__).relative_to(ROOT)),
        "driver_sha256": sha_file(Path(__file__).resolve()),
        "task_manifest_sha256": binding["task_manifest_sha256"],
        "expected_manifest_sha256": binding["expected_manifest_sha256"],
        "task_count": 16,
        "task_order": [task["task_id"] for task in binding["tasks"]],
        "expected_true": 8,
        "expected_false": 8,
        "schema_sha256": binding["schema_sha256"],
        "response_format_sha256": binding["format_sha256"],
        "prompt_sha256": binding["prompt_sha256"],
        "max_prompt_chars": binding["max_prompt_chars"],
        "conservative_prompt_plus_completion_bound": binding["context_bound"],
        "context_limit_non_binding": True,
        "runtime_freeze_sha256": sha_file(RUNTIME_FREEZE),
        "runtime": {"model_id": EXPECTED_MODEL_ID, "artifact_sha256": EXPECTED_MODEL_SHA, "operative_parameters": EXPECTED_PARAMS, "requested_n_ctx": EXPECTED_REQUESTED_CTX, "effective_n_ctx": EXPECTED_EFFECTIVE_CTX, "n_ctx_train": EXPECTED_TRAIN_CTX, "context_cap_reason": "native_training_context_cap"},
        "telemetry": {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "sample_interval_seconds": POWER_INTERVAL_SECONDS},
        "hardware": {"gpu_uuid": EXPECTED_GPU_UUID, "v100_touched": False},
        "execution_policy": {"supplier_model_calls": 16, "teacher_calls": 0, "retries": 0, "escalations": 0},
        "model_calls_made": False,
        "source_runtime_metadata": runtime_data["runtime"],
    }
    manifest["manifest_sha256"] = sha_bytes(canonical({**manifest, "manifest_sha256": None}))
    write_json(output_dir / "probe_manifest.json", manifest)
    write_json(output_dir / "expected_snapshot.json", {"source_manifest_sha256": binding["expected_manifest_sha256"], "rows": binding["expected_rows"], "policy": "NOT(target_match AND operation_match)"})
    write_json(output_dir / "lifecycle.json", {"status": "prepared", "model_calls_made": False, "updated_at": now()})
    print(json.dumps({"status": "prepared", "tasks": 16, "expected_manifest_valid": True, "deterministic_policy_reproduces": "16/16", "model_calls": 0}, indent=2))


def parse_extraction(raw: str) -> tuple[dict[str, Any] | None, bool, bool, list[str]]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, False, False, [str(exc)]
    contract = isinstance(parsed, dict) and set(parsed) == set(FIELDS) and all(isinstance(parsed.get(field), str) for field in FIELDS)
    return (parsed if contract else None), True, contract, ([] if contract else ["exact four-string extraction contract failed"])


def normalized_equal(left: str, right: str, field: str) -> bool:
    if field.endswith("operation"):
        return normalize_operation(left) == normalize_operation(right)
    return left.casefold() == right.casefold()


def score_extraction(observed: dict[str, Any] | None, expected: dict[str, Any], parse_valid: bool, contract_valid: bool) -> dict[str, Any]:
    field_correct = {}
    if observed is not None:
        field_correct = {
            "authorized_target": normalized_equal(observed["authorized_target"], expected["expected_authorized_target"], "authorized_target"),
            "requested_target": normalized_equal(observed["requested_target"], expected["expected_requested_target"], "requested_target"),
            "authorized_operation": normalized_equal(observed["authorized_operation"], expected["expected_authorized_operation"], "authorized_operation"),
            "requested_operation": normalized_equal(observed["requested_operation"], expected["expected_requested_operation"], "requested_operation"),
        }
    all_correct = contract_valid and all(field_correct.values())
    derived_scope = None
    if all(field in observed for field in ("authorized_target", "requested_target", "authorized_operation", "requested_operation")) if observed else False:
        target_match = normalized_equal(observed["authorized_target"], observed["requested_target"], "authorized_target")
        operation_match = normalized_equal(observed["authorized_operation"], observed["requested_operation"], "authorized_operation")
        derived_scope = not (target_match and operation_match)
    failures = [field.upper() + "_EXTRACTION_FAILURE" for field, ok in field_correct.items() if not ok]
    if not contract_valid:
        failure_localization = "INVALID_EXTRACTION_CONTRACT"
    elif not failures:
        failure_localization = "ALL_FACTS_CORRECT"
    elif len(failures) > 1:
        failure_localization = "MULTIPLE_EXTRACTION_FAILURES"
    else:
        failure_localization = failures[0]
    expected_scope = expected["expected_scope_expansion_required"]
    if derived_scope is None:
        policy_class = "INVALID_EXTRACTION_CONTRACT"
    elif all_correct and derived_scope == expected_scope:
        policy_class = "FACTS_CORRECT_POLICY_CORRECT"
    elif not all_correct and derived_scope == expected_scope:
        policy_class = "EXTRACTION_ERROR_POLICY_STILL_CORRECT"
    else:
        policy_class = "EXTRACTION_ERROR_POLICY_INCORRECT"
    return {"parse_valid": parse_valid, "contract_valid": contract_valid, "observed": observed, "field_correct": field_correct, "all_four_fields_correct": all_correct, "derived_scope_expansion_required": derived_scope, "expected_scope_expansion_required": expected_scope, "derived_scope_correct": derived_scope == expected_scope, "failure_localization": failure_localization, "policy_class": policy_class}


def execute(output_dir: Path) -> None:
    manifest_path = output_dir / "probe_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["manifest_sha256"] != sha_bytes(canonical({**manifest, "manifest_sha256": None})):
        raise RuntimeError("prepared manifest hash mismatch")
    binding = validate_model_free()
    if sha_file(TASK_MANIFEST) != manifest["task_manifest_sha256"] or sha_file(EXPECTED_MANIFEST) != manifest["expected_manifest_sha256"]:
        raise RuntimeError("frozen source drift")
    for task in binding["tasks"]:
        tid = task["task_id"]
        if sha_file(output_dir / "tasks" / tid / "prompt.txt") != binding["prompt_sha256"][tid]:
            raise RuntimeError(f"prompt drift: {tid}")
    spec = runtime.worker_spec()
    models = list_models(spec, timeout=30)
    candidate = next((item for item in models.get("data", []) if item.get("id") == EXPECTED_MODEL_ID), None)
    if candidate is None or (candidate.get("meta") or {}).get("n_params") != EXPECTED_PARAMS or (candidate.get("meta") or {}).get("n_ctx") != EXPECTED_EFFECTIVE_CTX or (candidate.get("meta") or {}).get("n_ctx_train") != EXPECTED_TRAIN_CTX:
        raise RuntimeError("runtime endpoint binding mismatch")
    telemetry_url = base.telemetry_base_url()
    telemetry = base.telemetry_preflight(telemetry_url)
    idle_samples, idle_summary = base.sample_window(IDLE_SECONDS, telemetry_url)
    write_json(output_dir / "preflight.json", {"schema": "zth_fact_extraction_deterministic_scope_execution_v1", "prepared_manifest_sha256": sha_file(manifest_path), "model_meta": candidate.get("meta"), "telemetry": telemetry, "task_manifest_sha256": manifest["task_manifest_sha256"], "expected_manifest_sha256": manifest["expected_manifest_sha256"], "execution_policy": manifest["execution_policy"]})
    write_json(output_dir / "idle_power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "summary": idle_summary, "samples": idle_samples})
    write_json(output_dir / "lifecycle.json", {"status": "running", "started_at": now(), "model_calls_made": False})
    rows = []
    for task in binding["tasks"]:
        tid = task["task_id"]
        task_dir = output_dir / "tasks" / tid
        prompt = (task_dir / "prompt.txt").read_text(encoding="utf-8")
        sampler = PowerSampler(lambda: read_gpu_power(EXPECTED_GPU_UUID, base_url=telemetry_url), expected_gpu_uuid=EXPECTED_GPU_UUID, sample_interval_seconds=POWER_INTERVAL_SECONDS)
        started = time.monotonic(); started_at = now(); sampler.start()
        response = decomposition.structured_call(spec, prompt, binding["format"], MAX_OUTPUT_TOKENS, TIMEOUT_SECONDS)
        captured = time.monotonic(); samples = sampler.stop()
        energy = integrate_energy_joules(samples, sample_interval_seconds=POWER_INTERVAL_SECONDS, expected_gpu_uuid=EXPECTED_GPU_UUID)
        metadata = response.metadata(); metadata["request_url"] = None
        raw = {"status": response.status, "content": response.content, "metadata": metadata, "request_started_at": started_at, "response_captured_at": now(), "wall_elapsed_ms": round((captured - started) * 1000, 3)}
        write_json(task_dir / "response.json", raw)
        transport = metadata.get("transport_classification") == "model_response"
        parsed, parse_valid, contract_valid, diagnostics = parse_extraction(response.content) if transport else (None, False, False, ["transport failure"])
        scored = score_extraction(parsed, binding["derived"][tid], parse_valid, contract_valid)
        scored["task_id"] = tid
        scored["transport_valid"] = transport
        scored["diagnostics"] = diagnostics
        scored["wall_elapsed_ms"] = raw["wall_elapsed_ms"]
        scored["prompt_tokens"] = (metadata.get("usage") or {}).get("prompt_tokens")
        scored["completion_tokens"] = (metadata.get("usage") or {}).get("completion_tokens")
        scored["power_summary"] = {"sample_count": len(samples), "mean_active_watts": statistics.mean(s.power_watts for s in samples), "peak_observed_watts": max(s.power_watts for s in samples), "gross_energy_joules": energy}
        scored["authority_factor"] = task["authority_factor"]
        scored["operation_factor"] = task["operation_factor"]
        scored["distractor_factor"] = task["distractor_factor"]
        scored["retry_count"] = 0; scored["escalation_count"] = 0; scored["teacher_calls"] = 0
        write_json(task_dir / "validation.json", {"schema": "zth_fact_extraction_deterministic_scope_validation_v1", **scored})
        write_json(task_dir / "scorecard.json", {"schema": "zth_fact_extraction_deterministic_scope_scorecard_v1", **scored})
        write_json(task_dir / "power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "gpu_uuid": EXPECTED_GPU_UUID, "samples": [{"timestamp_utc": s.timestamp_utc, "monotonic_seconds": s.monotonic_seconds, "gpu_uuid": s.gpu_uuid, "power_watts": s.power_watts, "sequence": s.sequence} for s in samples]})
        rows.append(scored)
    write_json(output_dir / "aggregate.json", aggregate(rows, idle_summary, candidate.get("meta") or {}))
    write_json(output_dir / "lifecycle.json", {"status": "terminal", "completed_at": now(), "model_calls_made": True, "supplier_model_calls": 16, "teacher_calls": 0, "retries": 0, "escalations": 0})
    print(json.dumps({"status": "terminal", "calls": 16}, indent=2))


def aggregate(rows: list[dict[str, Any]], idle: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    lat = [row["wall_elapsed_ms"] for row in rows]; energy = [row["power_summary"]["gross_energy_joules"] for row in rows]; ordered = sorted(lat)
    field_counts = {field: sum(row["field_correct"].get(field, False) for row in rows) for field in FIELDS}
    all_correct = sum(row["all_four_fields_correct"] for row in rows)
    derived_correct = sum(row["derived_scope_correct"] for row in rows)
    expected_true = [row for row in rows if row["expected_scope_expansion_required"]]
    expected_false = [row for row in rows if not row["expected_scope_expansion_required"]]
    matrix = {"TP": sum(row["expected_scope_expansion_required"] and row["derived_scope_expansion_required"] is True for row in rows), "FN": sum(row["expected_scope_expansion_required"] and row["derived_scope_expansion_required"] is False for row in rows), "FP": sum(not row["expected_scope_expansion_required"] and row["derived_scope_expansion_required"] is True for row in rows), "TN": sum(not row["expected_scope_expansion_required"] and row["derived_scope_expansion_required"] is False for row in rows)}
    return {"schema": "zth_qwen3_1_7b_fact_extraction_deterministic_scope_aggregate_v1", "exploratory_not_confirmatory": True, "candidate": {"model_id": EXPECTED_MODEL_ID, "operative_parameters": meta.get("n_params"), "effective_n_ctx": meta.get("n_ctx"), "n_ctx_train": meta.get("n_ctx_train"), "artifact_sha256": EXPECTED_MODEL_SHA}, "counts": {"tasks": 16, "parse_valid": sum(row["parse_valid"] for row in rows), "contract_valid": sum(row["contract_valid"] for row in rows), "authorized_target_correct": field_counts["authorized_target"], "requested_target_correct": field_counts["requested_target"], "authorized_operation_correct": field_counts["authorized_operation"], "requested_operation_correct": field_counts["requested_operation"], "all_four_fields_correct": all_correct, "derived_scope_correct": derived_correct, "expected_true": len(expected_true), "expected_false": len(expected_false), "derived_inside_correct": sum(row["derived_scope_correct"] for row in expected_false), "derived_outside_correct": sum(row["derived_scope_correct"] for row in expected_true)}, "deterministic_scope_confusion_matrix": matrix, "factor_conditioned": {"read_correct": sum(row["derived_scope_correct"] for row in rows if row["operation_factor"] == "READ"), "mutate_correct": sum(row["derived_scope_correct"] for row in rows if row["operation_factor"] == "MUTATE"), "held_present_correct": sum(row["derived_scope_correct"] for row in rows if row["distractor_factor"] == "HELD_DISTRACTOR_PRESENT"), "held_absent_correct": sum(row["derived_scope_correct"] for row in rows if row["distractor_factor"] == "HELD_DISTRACTOR_ABSENT")}, "failure_localization": {"authorized_target": sum(row["failure_localization"] == "AUTHORIZED_TARGET_EXTRACTION_FAILURE" for row in rows), "requested_target": sum(row["failure_localization"] == "REQUESTED_TARGET_EXTRACTION_FAILURE" for row in rows), "authorized_operation": sum(row["failure_localization"] == "AUTHORIZED_OPERATION_EXTRACTION_FAILURE" for row in rows), "requested_operation": sum(row["failure_localization"] == "REQUESTED_OPERATION_EXTRACTION_FAILURE" for row in rows), "multiple": sum(row["failure_localization"] == "MULTIPLE_EXTRACTION_FAILURES" for row in rows), "all_facts_correct": sum(row["failure_localization"] == "ALL_FACTS_CORRECT" for row in rows), "invalid_contract": sum(row["failure_localization"] == "INVALID_EXTRACTION_CONTRACT" for row in rows)}, "policy_classification": {"facts_correct_policy_correct": sum(row["policy_class"] == "FACTS_CORRECT_POLICY_CORRECT" for row in rows), "extraction_error_policy_still_correct": sum(row["policy_class"] == "EXTRACTION_ERROR_POLICY_STILL_CORRECT" for row in rows), "extraction_error_policy_incorrect": sum(row["policy_class"] == "EXTRACTION_ERROR_POLICY_INCORRECT" for row in rows), "invalid_extraction_contract": sum(row["policy_class"] == "INVALID_EXTRACTION_CONTRACT" for row in rows)}, "paired_rows": rows, "latency_ms": {"median": statistics.median(lat), "mean": statistics.mean(lat), "p95": ordered[min(len(ordered) - 1, round((len(ordered) - 1) * 0.95))]}, "energy_joules": {"mean_per_action": statistics.mean(energy), "median_per_action": statistics.median(energy), "total": sum(energy), "j_per_correct_four_field_extraction": sum(energy) / all_correct if all_correct else None, "j_per_correct_deterministic_scope": sum(energy) / derived_correct if derived_correct else None}, "idle_power": idle, "execution": {"supplier_model_calls": 16, "teacher_calls": 0, "retries": 0, "escalations": 0}}


def main() -> int:
    parser = argparse.ArgumentParser(); group = parser.add_mutually_exclusive_group(required=True); group.add_argument("--prepare", action="store_true"); group.add_argument("--execute", action="store_true"); parser.add_argument("--output-dir", type=Path, required=True); args = parser.parse_args()
    (prepare if args.prepare else execute)(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
