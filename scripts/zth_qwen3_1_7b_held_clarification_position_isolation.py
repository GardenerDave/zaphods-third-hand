#!/usr/bin/env python3
"""Three-arm held-clarification position/presence isolation."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import statistics
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from local_harness.icm_call import list_models
from local_harness.stage_a_power_telemetry import PowerSampler, integrate_energy_joules, read_gpu_power
from scripts import zth_qwen3_0_6b_clean_scope_logic_probe as clean
from scripts import zth_qwen3_1_7b_crossed_scope_factorial_probe as crossed
from scripts import zth_qwen3_1_7b_neutral_constrained_scope_probe as neutral
from scripts import zth_qwen3_1_7b_single_predicate_scope_probe as single
from scripts.zth_qwen3_1_7b_clean_scope_logic_probe import EXPECTED_EFFECTIVE_CTX, EXPECTED_MODEL_ID, EXPECTED_MODEL_SHA, EXPECTED_PARAMS, EXPECTED_REQUESTED_CTX, EXPECTED_TRAIN_CTX, RUNTIME_FREEZE, RUNTIME_FREEZE_SHA

ROOT = clean.ROOT
TASK_MANIFEST = crossed.TASK_MANIFEST
EXPECTED_GPU_UUID = clean.EXPECTED_GPU_UUID
MAX_OUTPUT_TOKENS = clean.MAX_OUTPUT_TOKENS
TIMEOUT_SECONDS = clean.TIMEOUT_SECONDS
POWER_INTERVAL_SECONDS = clean.POWER_INTERVAL_SECONDS
IDLE_SECONDS = clean.IDLE_SECONDS
SEMANTIC_FIELD = "scope_expansion_required"
ORDER_SEED = "zth-held-clarification-position-isolation-v1"
ARMS = ("L", "M", "A")
ARM_PERMUTATIONS = ("L-M-A", "L-A-M", "M-L-A", "M-A-L", "A-L-M", "A-M-L")


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


def split_predicate() -> tuple[str, str, str, str]:
    parts = single.PREDICATE_TEXT.split("\n\n")
    if len(parts) != 4:
        raise ValueError("unexpected single-predicate clause count")
    return parts[0], parts[1], parts[2], parts[3]


def prompts_for(task: dict[str, Any]) -> dict[str, str]:
    task_text = clean.task_specific_text(task)
    evaluate, main_predicate, mapping, clarification = split_predicate()
    common = clean.task_specific_text(task) + "\n\n" + neutral.PROMPT_SUFFIX
    l = common + "\n\n" + single.PREDICATE_TEXT
    m = common + "\n\n" + "\n\n".join((evaluate, main_predicate, clarification, mapping))
    a = common + "\n\n" + "\n\n".join((evaluate, main_predicate, mapping))
    if not l.startswith(task_text + "\n\n"):
        raise ValueError("prompt construction mismatch")
    return {"L": l, "M": m, "A": a}


def arm_orders(task_ids: list[str]) -> dict[str, list[str]]:
    ranked = sorted(task_ids, key=lambda task_id: hashlib.sha256((ORDER_SEED + task_id).encode()).hexdigest())
    return {task_id: ARM_PERMUTATIONS[index % len(ARM_PERMUTATIONS)].split("-") for index, task_id in enumerate(ranked)}


def validate_inputs() -> dict[str, Any]:
    payload = json.loads(TASK_MANIFEST.read_text(encoding="utf-8"))
    audit = crossed.validate_factorial_manifest(payload)
    tasks = payload["tasks"]
    prompts = {task["task_id"]: prompts_for(task) for task in tasks}
    evaluate, main_predicate, mapping, clarification = split_predicate()
    if all(prompts[t["task_id"]]["L"] == single.prompt_for(t) for t in tasks) is not True:
        raise ValueError("L does not equal completed single-predicate prompt")
    if not neutral.schema_allows_both() or any(not neutral.no_worked_boolean_object(p) for row in prompts.values() for p in row.values()):
        raise ValueError("schema symmetry or worked-example audit failed")
    if max(len(p) for row in prompts.values() for p in row.values()) + MAX_OUTPUT_TOKENS >= EXPECTED_EFFECTIVE_CTX:
        raise ValueError("context could bind probe")
    if any("is true when" in p.casefold() or "is false when" in p.casefold() for row in prompts.values() for p in row.values()):
        raise ValueError("dual boolean clause found")
    orders = arm_orders([t["task_id"] for t in tasks])
    counts = {key: sum(order == list(key.split("-")) for order in orders.values()) for key in ARM_PERMUTATIONS}
    if max(counts.values()) - min(counts.values()) > 1:
        raise ValueError("arm permutation assignment is not as even as possible")
    diffs = {}
    for task in tasks:
        tid = task["task_id"]
        diffs[tid] = {
            "L_to_M": list(difflib.unified_diff(prompts[tid]["L"].splitlines(True), prompts[tid]["M"].splitlines(True), fromfile="L", tofile="M")),
            "M_to_A": list(difflib.unified_diff(prompts[tid]["M"].splitlines(True), prompts[tid]["A"].splitlines(True), fromfile="M", tofile="A")),
            "L_to_A": list(difflib.unified_diff(prompts[tid]["L"].splitlines(True), prompts[tid]["A"].splitlines(True), fromfile="L", tofile="A")),
        }
        if prompts[tid]["M"].replace(clarification, "").replace("\n\n\n\n", "\n\n") != prompts[tid]["A"]:
            raise ValueError(f"M to A difference is not clarification-only: {tid}")
    return {"payload": payload, "audit": audit, "tasks": tasks, "prompts": prompts, "orders": orders, "permutation_counts": counts, "main_predicate": main_predicate, "evaluate": evaluate, "mapping": mapping, "clarification": clarification, "task_manifest_sha256": sha_file(TASK_MANIFEST), "main_predicate_sha256": sha_bytes(main_predicate.encode()), "mapping_sha256": sha_bytes(mapping.encode()), "clarification_sha256": sha_bytes(clarification.encode()), "schema_sha256": sha_bytes(canonical(neutral.STRUCTURED_SCHEMA)), "response_format_sha256": sha_bytes(canonical(neutral.RESPONSE_FORMAT)), "prompt_sha256": {arm: {tid: sha_bytes(prompts[tid][arm].encode()) for tid in prompts} for arm in ARMS}, "diffs": diffs, "diff_sha256": {name: sha_bytes(canonical({tid: diffs[tid][name] for tid in diffs})) for name in ("L_to_M", "M_to_A", "L_to_A")}}


def runtime_payload() -> dict[str, Any]:
    payload = json.loads(RUNTIME_FREEZE.read_text(encoding="utf-8"))
    if sha_file(RUNTIME_FREEZE) != RUNTIME_FREEZE_SHA or payload["operative_supplier"]["n_params"] != EXPECTED_PARAMS or payload["context"]["effective_n_ctx"] != EXPECTED_EFFECTIVE_CTX:
        raise RuntimeError("runtime binding mismatch")
    return payload


def validate_raw(raw: str, expected: bool) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
        parse_valid = True
        parse_error = None
    except json.JSONDecodeError as exc:
        parsed = None
        parse_valid = False
        parse_error = str(exc)
    contract_valid = isinstance(parsed, dict) and set(parsed) == {SEMANTIC_FIELD} and isinstance(parsed.get(SEMANTIC_FIELD), bool)
    observed = parsed.get(SEMANTIC_FIELD) if contract_valid else None
    correct = bool(contract_valid and observed == expected)
    return {"validation_status": "passed" if correct else "failed", "parse_valid": parse_valid, "contract_valid": contract_valid, "observed": observed, "expected": expected, "checks": [{"check": "json_parse", "status": "passed" if parse_valid else "failed"}, {"check": "field_contract", "status": "passed" if contract_valid else "failed"}, {"check": "reference_boolean", "status": "passed" if correct else "failed"}], "diagnostics": ([parse_error] if parse_error else []) + ([] if correct else ["deterministic expected boolean mismatch"])}


def prepare(out: Path) -> None:
    if out.exists() and any(out.iterdir()):
        raise RuntimeError("output must be fresh")
    out.mkdir(parents=True, exist_ok=True)
    binding = validate_inputs()
    runtime = runtime_payload()
    write_json(out / "structured_schema.json", neutral.STRUCTURED_SCHEMA)
    write_json(out / "response_format.json", neutral.RESPONSE_FORMAT)
    rows = []
    for task in binding["tasks"]:
        tid = task["task_id"]
        d = out / "tasks" / tid
        d.mkdir(parents=True, exist_ok=True)
        write_json(d / "fixture.snapshot.json", task)
        row = {"task_id": tid, "expected": task["expected_scope_expansion_required"], "arm_order": binding["orders"][tid], "prompt_sha256": binding["prompt_sha256"]}
        for arm in ARMS:
            (d / arm).mkdir()
            (d / arm / "prompt.txt").write_text(binding["prompts"][tid][arm], encoding="utf-8")
        rows.append(row)
    manifest = {"schema": "zth_qwen3_1_7b_held_clarification_position_isolation_manifest_v1", "status": "prepared_exploratory_not_confirmatory", "prepared_at": now(), "prepared_from_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), "driver": str(Path(__file__).relative_to(ROOT)), "driver_sha256": sha_file(Path(__file__).resolve()), "task_manifest_sha256": binding["task_manifest_sha256"], "task_count": 16, "expected_true": 8, "expected_false": 8, "task_order": [t["task_id"] for t in binding["tasks"]], "main_predicate_sha256": binding["main_predicate_sha256"], "mapping_sha256": binding["mapping_sha256"], "clarification_sha256": binding["clarification_sha256"], "schema_sha256": binding["schema_sha256"], "response_format_sha256": binding["response_format_sha256"], "diff_sha256": binding["diff_sha256"], "worked_boolean_exemplars": 0, "structured_constraint_allows_true": True, "structured_constraint_allows_false": True, "permutation_counts": binding["permutation_counts"], "context_limit_non_binding": True, "runtime_freeze_sha256": sha_file(RUNTIME_FREEZE), "runtime": {"model_id": EXPECTED_MODEL_ID, "artifact_sha256": EXPECTED_MODEL_SHA, "operative_parameters": EXPECTED_PARAMS, "effective_n_ctx": EXPECTED_EFFECTIVE_CTX, "n_ctx_train": EXPECTED_TRAIN_CTX, "requested_n_ctx": EXPECTED_REQUESTED_CTX, "llama_cpp_version": runtime["runtime"]["llama_cpp_version"], "build_revision": runtime["runtime"]["build_revision"]}, "telemetry": {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "sample_interval_seconds": POWER_INTERVAL_SECONDS}, "hardware": {"gpu_uuid": EXPECTED_GPU_UUID, "v100_touched": False}, "execution_policy": {"supplier_model_calls": 48, "teacher_calls": 0, "retries": 0, "escalations": 0}, "tasks": rows, "model_calls_made": False}
    manifest["manifest_sha256"] = sha_bytes(canonical({**manifest, "manifest_sha256": None}))
    write_json(out / "probe_manifest.json", manifest)
    write_json(out / "diff_audit.json", {"main_predicate_sha256": binding["main_predicate_sha256"], "mapping_sha256": binding["mapping_sha256"], "clarification_sha256": binding["clarification_sha256"], "diff_sha256": binding["diff_sha256"], "l_equals_single_predicate": True, "schema_identical": True, "output_mapping_identical": True, "worked_boolean_exemplars": 0, "permutation_counts": binding["permutation_counts"], "diffs": binding["diffs"]})
    write_json(out / "lifecycle.json", {"status": "prepared", "model_calls_made": False, "updated_at": now()})
    print(json.dumps({"status": "prepared", "tasks": 16, "arms": 3, "calls": 48, "permutation_counts": binding["permutation_counts"], "model_calls": 0}, indent=2))


def execute(out: Path) -> None:
    manifest = json.loads((out / "probe_manifest.json").read_text(encoding="utf-8"))
    if manifest["manifest_sha256"] != sha_bytes(canonical({**manifest, "manifest_sha256": None})):
        raise RuntimeError("manifest hash mismatch")
    binding = validate_inputs()
    for key in ("task_manifest_sha256", "main_predicate_sha256", "mapping_sha256", "clarification_sha256"):
        if manifest[key] != binding[key]:
            raise RuntimeError(f"binding drift: {key}")
    for row in manifest["tasks"]:
        for arm in ARMS:
            if sha_file(out / "tasks" / row["task_id"] / arm / "prompt.txt") != binding["prompt_sha256"][arm][row["task_id"]]:
                raise RuntimeError("prompt drift")
    spec = clean.worker_spec()
    models = list_models(spec, timeout=30)
    candidate = next((x for x in models.get("data", []) if x.get("id") == EXPECTED_MODEL_ID), None)
    if candidate is None or (candidate.get("meta") or {}).get("n_params") != EXPECTED_PARAMS or (candidate.get("meta") or {}).get("n_ctx") != EXPECTED_EFFECTIVE_CTX:
        raise RuntimeError("runtime endpoint mismatch")
    telemetry_url = clean.telemetry_base_url()
    telemetry = clean.telemetry_preflight(telemetry_url)
    idle_samples, idle_summary = clean.sample_window(IDLE_SECONDS, telemetry_url)
    write_json(out / "preflight.json", {"schema": "zth_qwen3_1_7b_held_clarification_position_isolation_execution_v1", "prepared_manifest_sha256": sha_file(out / "probe_manifest.json"), "model_meta": candidate.get("meta"), "telemetry": telemetry, "task_manifest_sha256": manifest["task_manifest_sha256"], "main_predicate_sha256": manifest["main_predicate_sha256"], "diff_sha256": manifest["diff_sha256"], "execution_policy": manifest["execution_policy"]})
    write_json(out / "idle_power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "summary": idle_summary, "samples": idle_samples})
    write_json(out / "lifecycle.json", {"status": "running", "started_at": now(), "model_calls_made": False})
    by_id = {t["task_id"]: t for t in binding["tasks"]}
    for tid in manifest["task_order"]:
        task = by_id[tid]
        row = next(r for r in manifest["tasks"] if r["task_id"] == tid)
        for arm in row["arm_order"]:
            d = out / "tasks" / tid / arm
            prompt = (d / "prompt.txt").read_text(encoding="utf-8")
            sampler = PowerSampler(lambda: read_gpu_power(EXPECTED_GPU_UUID, base_url=telemetry_url), expected_gpu_uuid=EXPECTED_GPU_UUID, sample_interval_seconds=POWER_INTERVAL_SECONDS)
            started = time.monotonic()
            started_at = now()
            sampler.start()
            response = neutral.structured_call(spec, prompt, neutral.STRUCTURED_SCHEMA, MAX_OUTPUT_TOKENS, TIMEOUT_SECONDS)
            captured = time.monotonic()
            samples = sampler.stop()
            energy = integrate_energy_joules(samples, sample_interval_seconds=POWER_INTERVAL_SECONDS, expected_gpu_uuid=EXPECTED_GPU_UUID)
            metadata = response.metadata()
            metadata["request_url"] = None
            raw = {"status": response.status, "content": response.content, "metadata": metadata, "request_started_at": started_at, "response_captured_at": now(), "wall_elapsed_ms": round((captured - started) * 1000, 3)}
            write_json(d / "response.json", raw)
            transport = metadata.get("transport_classification") == "model_response"
            validation = validate_raw(response.content, task["expected_scope_expansion_required"]) if transport else {"validation_status": "failed", "parse_valid": False, "contract_valid": False, "observed": None, "expected": task["expected_scope_expansion_required"], "diagnostics": ["transport failure"]}
            write_json(d / "validation.json", validation)
            write_json(d / "power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "gpu_uuid": EXPECTED_GPU_UUID, "samples": [{"timestamp_utc": s.timestamp_utc, "monotonic_seconds": s.monotonic_seconds, "gpu_uuid": s.gpu_uuid, "power_watts": s.power_watts, "sequence": s.sequence} for s in samples]})
            write_json(d / "scorecard.json", {"schema": "zth_qwen3_1_7b_held_clarification_task_scorecard_v1", "task_id": tid, "arm": arm, "expected": task["expected_scope_expansion_required"], "operation_factor": task["operation_factor"], "authority_factor": task["authority_factor"], "distractor_factor": task["distractor_factor"], "transport_valid": transport, "raw_parse_valid": validation["parse_valid"] if transport else False, "contract_valid": validation["contract_valid"] if transport else False, "observed": validation["observed"], "correct": bool(transport and validation["contract_valid"] and validation["observed"] == task["expected_scope_expansion_required"]), "failure_class": None if transport and validation["contract_valid"] and validation["observed"] == task["expected_scope_expansion_required"] else (("SERIALIZATION_FAILURE" if transport and not validation["parse_valid"] else "INVALID_CONTRACT") if not validation["contract_valid"] else "SCOPE_DECISION_FAILURE"), "validator_status": validation["validation_status"], "wall_elapsed_ms": raw["wall_elapsed_ms"], "prompt_tokens": (metadata.get("usage") or {}).get("prompt_tokens"), "completion_tokens": (metadata.get("usage") or {}).get("completion_tokens"), "power_summary": {"sample_count": len(samples), "mean_active_watts": statistics.mean(s.power_watts for s in samples), "peak_observed_watts": max(s.power_watts for s in samples), "gross_energy_joules": energy}, "retry_count": 0, "escalation_count": 0, "teacher_calls": 0})
    write_json(out / "aggregate.json", aggregate(out, manifest, idle_summary))
    write_json(out / "lifecycle.json", {"status": "terminal", "completed_at": now(), "model_calls_made": True, "supplier_model_calls": 48, "teacher_calls": 0, "retries": 0, "escalations": 0})
    print(json.dumps({"status": "terminal", "calls": 48}, indent=2))


def aggregate(out: Path, manifest: dict[str, Any], idle: dict[str, Any]) -> dict[str, Any]:
    rows = [json.loads(p.read_text()) for p in sorted(out.glob("tasks/*/*/scorecard.json"))]
    by = {arm: [r for r in rows if r["arm"] == arm] for arm in ARMS}
    def sub(rs: list[dict[str, Any]], **filters: str) -> list[dict[str, Any]]:
        return [r for r in rs if all(r[k] == v for k, v in filters.items())]
    def summary(rs: list[dict[str, Any]]) -> dict[str, Any]:
        lat = [r["wall_elapsed_ms"] for r in rs]
        energy = [r["power_summary"]["gross_energy_joules"] for r in rs]
        ordered = sorted(lat)
        return {"true_selected": sum(r["observed"] is True for r in rs), "false_selected": sum(r["observed"] is False for r in rs), "correct": sum(r["correct"] for r in rs), "inside_correct": sum(r["correct"] for r in sub(rs, authority_factor="INSIDE_AUTHORITY")), "outside_correct": sum(r["correct"] for r in sub(rs, authority_factor="OUTSIDE_AUTHORITY")), "read_correct": sum(r["correct"] for r in sub(rs, operation_factor="READ")), "mutate_correct": sum(r["correct"] for r in sub(rs, operation_factor="MUTATE")), "distractor_present_correct": sum(r["correct"] for r in sub(rs, distractor_factor="HELD_DISTRACTOR_PRESENT")), "distractor_absent_correct": sum(r["correct"] for r in sub(rs, distractor_factor="HELD_DISTRACTOR_ABSENT")), "cells": {f"{op}_{auth}": {"correct": sum(r["correct"] for r in sub(rs, operation_factor=op, authority_factor=auth)), "total": len(sub(rs, operation_factor=op, authority_factor=auth))} for op in ("READ", "MUTATE") for auth in ("INSIDE_AUTHORITY", "OUTSIDE_AUTHORITY")}, "parse_valid": sum(r["raw_parse_valid"] for r in rs), "contract_valid": sum(r["contract_valid"] for r in rs), "confusion_matrix": {"TP": sum(r["expected"] and r["observed"] is True for r in rs), "FN": sum(r["expected"] and r["observed"] is False for r in rs), "FP": sum(not r["expected"] and r["observed"] is True for r in rs), "TN": sum(not r["expected"] and r["observed"] is False for r in rs)}, "serialization_failures": sum(r["failure_class"] == "SERIALIZATION_FAILURE" for r in rs), "contract_failures": sum(r["failure_class"] == "INVALID_CONTRACT" for r in rs), "scope_decision_failures": sum(r["failure_class"] == "SCOPE_DECISION_FAILURE" for r in rs), "latency_ms": {"median": statistics.median(lat), "mean": statistics.mean(lat), "p95": ordered[round((len(ordered) - 1) * 0.95)]}, "energy_joules": {"mean_per_action": statistics.mean(energy), "median_per_action": statistics.median(energy), "total": sum(energy)}}
    paired = {}
    for tid in manifest["task_order"]:
        vals = {arm: next(r for r in by[arm] if r["task_id"] == tid)["observed"] for arm in ARMS}
        paired[tid] = {"expected": next(r for r in by["L"] if r["task_id"] == tid)["expected"], **vals}
    return {"schema": "zth_qwen3_1_7b_held_clarification_position_isolation_aggregate_v1", "exploratory_not_confirmatory": True, "candidate": {"model_id": EXPECTED_MODEL_ID, "operative_parameters": EXPECTED_PARAMS, "artifact_sha256": EXPECTED_MODEL_SHA}, "arms": {arm: summary(by[arm]) for arm in ARMS}, "paired": paired, "pairwise_output_flips": {"L_to_M": sum(v["L"] != v["M"] for v in paired.values()), "M_to_A": sum(v["M"] != v["A"] for v in paired.values()), "L_to_A": sum(v["L"] != v["A"] for v in paired.values())}, "execution": {"supplier_model_calls": 48, "teacher_calls": 0, "retries": 0, "escalations": 0}, "idle_power": idle}


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare", action="store_true")
    group.add_argument("--execute", action="store_true")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.output_dir) if args.prepare else execute(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
