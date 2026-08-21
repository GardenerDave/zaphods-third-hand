#!/usr/bin/env python3
"""Matched exploratory atomic scope probe for the loaded Qwen3.5 supplier."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import statistics
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from local_harness.icm_call import call_worker, list_models
from local_harness.stage_a_power_telemetry import PowerSampler, integrate_energy_joules, read_gpu_power
from local_harness.supervised_capability_loop import _validator_result
from scripts import zth_qwen3_0_6b_clean_scope_logic_probe as base


ROOT = base.ROOT
TASK_MANIFEST = base.TASK_MANIFEST
RUNTIME_FREEZE = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_5_0_8B_RUNTIME_FREEZE_2026-08-20.json"
EXPECTED_RUNTIME_SHA = "76d0f35fdc5f3ee5449fab61676563921d0dd395aefe43255f30ed20e4140ca4"
EXPECTED_MODEL_ID = "Qwen3.5-0.8B-Q4_K_M.gguf"
EXPECTED_MODEL_SHA = "bd258782e35f7f458f8aced1adc053e6e92e89bc735ba3be89d38a06121dc517"
EXPECTED_PARAMS = 752393024
EXPECTED_CTX = 40960
EXPECTED_GPU_UUID = base.EXPECTED_GPU_UUID
POWER_INTERVAL_SECONDS = base.POWER_INTERVAL_SECONDS
IDLE_SECONDS = base.IDLE_SECONDS
MAX_OUTPUT_TOKENS = base.MAX_OUTPUT_TOKENS
TIMEOUT_SECONDS = base.TIMEOUT_SECONDS
OLD_RUN = ROOT / ".work/model_size_supplier_floor/qwen3_0_6b_clean_scope_logic_probe/run_20260821T025430Z"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def runtime_payload() -> dict[str, Any]:
    payload = json.loads(RUNTIME_FREEZE.read_text())
    if sha256_file(RUNTIME_FREEZE) != EXPECTED_RUNTIME_SHA:
        raise RuntimeError("752M runtime freeze hash mismatch")
    candidate = payload["candidate"]
    metadata = payload["llama_cpp_exposed_metadata"]
    if candidate["filename"] != EXPECTED_MODEL_ID or candidate["sha256"] != EXPECTED_MODEL_SHA:
        raise RuntimeError("752M candidate artifact binding mismatch")
    if metadata["n_params"] != EXPECTED_PARAMS or metadata["n_ctx"] != EXPECTED_CTX:
        raise RuntimeError("752M operative runtime metadata mismatch")
    if metadata["thinking"] != 0:
        raise RuntimeError("752M thinking state is not off")
    return payload


def worker_spec():
    return base.worker_spec()


def verify_matched_source() -> dict[str, Any]:
    if not OLD_RUN.exists():
        raise RuntimeError("completed 596M clean probe is unavailable")
    old_manifest_path = OLD_RUN / "probe_manifest.json"
    old_manifest = json.loads(old_manifest_path.read_text())
    tasks = base.load_manifest()
    leakage = base.validate_fixture_manifest(tasks)
    if sha256_file(TASK_MANIFEST) != old_manifest["task_manifest"]["sha256"]:
        raise RuntimeError("frozen task manifest differs from 596M probe binding")
    if old_manifest["task_order"] != [task["task_id"] for task in tasks["tasks"]]:
        raise RuntimeError("task order differs from 596M probe")
    if old_manifest["semantic_contract"]["rule_sha256"] != leakage["semantic_rule_sha256"]:
        raise RuntimeError("semantic rule hash differs from 596M probe")
    old_prompt_hashes = {}
    for task in tasks["tasks"]:
        task_id = task["task_id"]
        expected = base.prompt_for(task).encode()
        old_prompt = (OLD_RUN / "tasks" / task_id / "prompt.txt").read_bytes()
        if old_prompt != expected:
            raise RuntimeError(f"596M prompt bytes differ from frozen construction: {task_id}")
        old_prompt_hashes[task_id] = sha256_bytes(old_prompt)
    return {
        "old_manifest_sha256": sha256_file(old_manifest_path),
        "old_aggregate_sha256": sha256_file(OLD_RUN / "aggregate.json"),
        "old_task_manifest_sha256": sha256_file(TASK_MANIFEST),
        "old_prompt_hashes": old_prompt_hashes,
        "task_order": [task["task_id"] for task in tasks["tasks"]],
        "task_count": len(tasks["tasks"]),
        "true_count": sum(task["expected_scope_expansion_required"] for task in tasks["tasks"]),
        "false_count": sum(not task["expected_scope_expansion_required"] for task in tasks["tasks"]),
        "answer_leakage_findings": leakage["answer_leakage_findings"],
        "semantic_rule_sha256": leakage["semantic_rule_sha256"],
        "prompt_suffix_sha256": leakage["prompt_suffix_sha256"],
        "prompt_construction_sha256": sha256_file(ROOT / "scripts/zth_qwen3_0_6b_clean_scope_logic_probe.py"),
    }


def prepare(output_dir: Path) -> None:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError("752M clean scope output directory must be fresh")
    output_dir.mkdir(parents=True, exist_ok=True)
    source = verify_matched_source()
    runtime = runtime_payload()
    tasks = base.load_manifest()["tasks"]
    task_rows = []
    for task in tasks:
        task_dir = output_dir / "tasks" / task["task_id"]
        task_dir.mkdir(parents=True, exist_ok=True)
        prompt = base.prompt_for(task)
        (task_dir / "prompt.txt").write_bytes(prompt.encode())
        write_json(task_dir / "fixture.snapshot.json", task)
        task_rows.append({"task_id": task["task_id"], "expected": task["expected_scope_expansion_required"], "prompt_sha256": sha256_bytes(prompt.encode()), "old_prompt_sha256": source["old_prompt_hashes"][task["task_id"]]})
    manifest = {
        "schema": "zth_qwen3_5_0_8b_clean_scope_logic_probe_manifest_v1",
        "status": "prepared_exploratory_matched_not_confirmatory",
        "prepared_at": now(),
        "prepared_from_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "driver": str(Path(__file__).relative_to(ROOT)),
        "driver_sha256": sha256_file(Path(__file__).resolve()),
        "matched_596m": {"run_path": str(OLD_RUN.relative_to(ROOT)), **source},
        "task_manifest_path": str(TASK_MANIFEST.relative_to(ROOT)),
        "task_manifest_sha256": source["old_task_manifest_sha256"],
        "semantic_rule_sha256": source["semantic_rule_sha256"],
        "prompt_suffix_sha256": source["prompt_suffix_sha256"],
        "prompt_construction_sha256": source["prompt_construction_sha256"],
        "task_order": source["task_order"],
        "branch_balance": {"true": source["true_count"], "false": source["false_count"]},
        "answer_leakage_findings": source["answer_leakage_findings"],
        "output_contract": {"exact_fields": ["scope_expansion_required"], "format": "bare_json_object", "field_type": "boolean"},
        "runtime": {"path": str(RUNTIME_FREEZE.relative_to(ROOT)), "sha256": sha256_file(RUNTIME_FREEZE), "model_id": EXPECTED_MODEL_ID, "artifact_sha256": EXPECTED_MODEL_SHA, "operative_parameters": EXPECTED_PARAMS, "upstream_total_parameters": runtime["candidate"]["upstream_total_parameter_count"], "context": EXPECTED_CTX, "native_context": runtime["llama_cpp_exposed_metadata"]["n_ctx_train"], "llama_cpp_version": runtime["runtime"]["llama_cpp_version"], "build_revision": runtime["runtime"]["build_revision"], "thinking": 0, "architecture_confound": runtime["candidate"]["architecture_confound"]},
        "hardware": {"gpu_uuid": EXPECTED_GPU_UUID, "gpu_class": "NVIDIA GeForce GTX 1650", "same_hardware_as_596m": True, "reference_unloaded": True},
        "telemetry": {"transport": "remote_read_only_http", "public_alias": os.environ.get("ZTH_GPU_TELEMETRY_PUBLIC_ALIAS", "UNSET"), "measurement_level": 2, "measurement_boundary": "gpu_device_only", "sample_interval_seconds": POWER_INTERVAL_SECONDS},
        "execution_policy": {"supplier_model_calls": 16, "teacher_calls": 0, "retries": 0, "escalations": 0},
        "tasks": task_rows,
        "model_calls_made": False,
    }
    manifest["manifest_sha256"] = sha256_bytes(canonical({**manifest, "manifest_sha256": None}))
    write_json(output_dir / "probe_manifest.json", manifest)
    write_json(output_dir / "lifecycle.json", {"status": "prepared", "model_calls_made": False, "updated_at": now()})
    print(json.dumps({"status": "prepared", "output_dir": str(output_dir), "task_count": 16, "task_manifest_identical": True, "model_calls": 0}, indent=2))


def parse_atomic(raw: str) -> dict[str, Any]:
    return base.parse_atomic(raw)


def execute(output_dir: Path) -> None:
    manifest_path = output_dir / "probe_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if manifest["manifest_sha256"] != sha256_bytes(canonical({**manifest, "manifest_sha256": None})):
        raise RuntimeError("752M probe manifest hash mismatch")
    source = verify_matched_source()
    if source["old_manifest_sha256"] != manifest["matched_596m"]["old_manifest_sha256"]:
        raise RuntimeError("596M probe manifest changed")
    runtime_payload()
    for row in manifest["tasks"]:
        prompt = (output_dir / "tasks" / row["task_id"] / "prompt.txt").read_bytes()
        if sha256_bytes(prompt) != row["prompt_sha256"] or row["prompt_sha256"] != row["old_prompt_sha256"]:
            raise RuntimeError(f"matched prompt binding changed: {row['task_id']}")
    spec = worker_spec()
    models = list_models(spec, timeout=30)
    model_ids = [item.get("id") for item in models.get("data", [])] if isinstance(models, dict) else []
    if EXPECTED_MODEL_ID not in model_ids:
        raise RuntimeError("752M model is not exposed by worker endpoint")
    telemetry_url = base.telemetry_base_url()
    telemetry = base.telemetry_preflight(telemetry_url)
    idle_samples, idle_summary = base.sample_window(IDLE_SECONDS, telemetry_url)
    preflight = {"schema": "zth_qwen3_5_0_8b_clean_scope_logic_probe_execution_manifest_v1", "execution_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), "prepared_manifest_sha256": sha256_file(manifest_path), "model_ids": model_ids, "candidate_model_id": EXPECTED_MODEL_ID, "operative_parameters": EXPECTED_PARAMS, "task_order": manifest["task_order"], "branch_balance": manifest["branch_balance"], "task_manifest_sha256": manifest["task_manifest_sha256"], "semantic_rule_sha256": manifest["semantic_rule_sha256"], "prompt_suffix_sha256": manifest["prompt_suffix_sha256"], "answer_leakage_findings": 0, "telemetry": telemetry, "execution_policy": manifest["execution_policy"]}
    write_json(output_dir / "preflight.json", preflight)
    write_json(output_dir / "idle_power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "summary": idle_summary, "samples": idle_samples})
    write_json(output_dir / "lifecycle.json", {"status": "running", "started_at": now(), "model_calls_made": False})
    tasks = {task["task_id"]: task for task in base.load_manifest()["tasks"]}
    rows = []
    for task_id in manifest["task_order"]:
        task_dir = output_dir / "tasks" / task_id
        task = tasks[task_id]
        sampler = PowerSampler(lambda: read_gpu_power(EXPECTED_GPU_UUID, base_url=telemetry_url), expected_gpu_uuid=EXPECTED_GPU_UUID, sample_interval_seconds=POWER_INTERVAL_SECONDS)
        started = time.monotonic()
        started_at = now()
        sampler.start()
        response = call_worker(spec, (task_dir / "prompt.txt").read_text(), MAX_OUTPUT_TOKENS, timeout=TIMEOUT_SECONDS)
        captured = time.monotonic()
        samples = sampler.stop()
        energy = integrate_energy_joules(samples, sample_interval_seconds=POWER_INTERVAL_SECONDS, expected_gpu_uuid=EXPECTED_GPU_UUID)
        metadata = response.metadata()
        metadata["request_url"] = None
        raw = {"status": response.status, "content": response.content, "metadata": metadata, "request_started_at": started_at, "response_captured_at": now(), "wall_elapsed_ms": round((captured - started) * 1000, 3)}
        write_json(task_dir / "response.json", raw)
        transport_valid = metadata.get("transport_classification") == "model_response"
        validation_task = {"task_id": task_id, "task_family": "scope-expansion-atomic", "prompt": base.task_specific_text(task), "output_contract": {"format": "json", "required_fields": ["scope_expansion_required"]}, "validator": {"kind": "zth_output_contract", "reference_facts": {"requires_scope_expansion_flag": task["expected_scope_expansion_required"]}}}
        validation = _validator_result(response.content, validation_task, attempt_id=f"clean-scope-752m-{task_id}") if transport_valid else None
        if validation is not None:
            write_json(task_dir / "validation.json", validation)
        parsed = parse_atomic(response.content) if transport_valid else {"raw_parse_valid": False, "contract_valid": False, "observed": None, "failure": "TRANSPORT_FAILURE"}
        correct = parsed["contract_valid"] and parsed["observed"] == task["expected_scope_expansion_required"]
        score = {"schema": "zth_qwen3_5_0_8b_clean_scope_logic_probe_task_scorecard_v1", "task_id": task_id, "expected_scope_expansion_required": task["expected_scope_expansion_required"], "transport_valid": transport_valid, "raw_parse_valid": parsed["raw_parse_valid"] if transport_valid else False, "contract_valid": parsed["contract_valid"] if transport_valid else False, "observed_scope_expansion_required": parsed["observed"], "correct": bool(correct), "failure_class": None if correct else (parsed["failure"] or "SCOPE_DECISION_FAILURE"), "validator_status": validation.get("validation_status") if validation else None, "wall_elapsed_ms": raw["wall_elapsed_ms"], "prompt_tokens": (metadata.get("usage") or {}).get("prompt_tokens"), "completion_tokens": (metadata.get("usage") or {}).get("completion_tokens"), "total_tokens": (metadata.get("usage") or {}).get("total_tokens"), "power_summary": {"sample_count": len(samples), "mean_active_watts": round(statistics.mean(sample.power_watts for sample in samples), 6), "peak_observed_watts": round(max(sample.power_watts for sample in samples), 6), "gross_energy_joules": energy, "sample_interval_seconds": POWER_INTERVAL_SECONDS}, "measurement_level": 2, "measurement_boundary": "gpu_device_only", "retry_count": 0, "escalation_count": 0, "teacher_calls": 0, "raw_response_preserved": True, "exploratory_matched_not_confirmatory": True}
        write_json(task_dir / "power_samples.json", {"schema": "zth_qwen3_5_0_8b_clean_scope_logic_probe_power_v1", "measurement_level": 2, "measurement_boundary": "gpu_device_only", "gpu_uuid": EXPECTED_GPU_UUID, "samples": [{"timestamp_utc": s.timestamp_utc, "monotonic_seconds": s.monotonic_seconds, "gpu_uuid": s.gpu_uuid, "power_watts": s.power_watts, "sequence": s.sequence} for s in samples]})
        write_json(task_dir / "scorecard.json", score)
        rows.append(score)
    write_json(output_dir / "aggregate.json", build_aggregate(rows, idle_summary))
    write_json(output_dir / "lifecycle.json", {"status": "terminal", "completed_at": now(), "model_calls_made": True, "supplier_model_calls": 16, "teacher_calls": 0, "retries": 0, "escalations": 0})
    print(json.dumps({"status": "terminal", "output_dir": str(output_dir), "tasks": 16, "model_calls": 16}, indent=2))


def build_aggregate(rows: list[dict[str, Any]], idle_summary: dict[str, Any]) -> dict[str, Any]:
    true_rows = [row for row in rows if row["expected_scope_expansion_required"]]
    false_rows = [row for row in rows if not row["expected_scope_expansion_required"]]
    tp = sum(row["correct"] and row["expected_scope_expansion_required"] for row in rows)
    tn = sum(row["correct"] and not row["expected_scope_expansion_required"] for row in rows)
    fp = sum(not row["expected_scope_expansion_required"] and row["observed_scope_expansion_required"] is True for row in rows)
    fn = sum(row["expected_scope_expansion_required"] and row["observed_scope_expansion_required"] is False for row in rows)
    latencies = [row["wall_elapsed_ms"] for row in rows]
    energies = [row["power_summary"]["gross_energy_joules"] for row in rows]
    ordered = sorted(latencies)
    return {"schema": "zth_qwen3_5_0_8b_clean_scope_logic_probe_aggregate_v1", "exploratory_matched_not_confirmatory": True, "candidate": {"model_id": EXPECTED_MODEL_ID, "operative_parameters": EXPECTED_PARAMS, "artifact_sha256": EXPECTED_MODEL_SHA}, "task_count": len(rows), "branch_results": {"true": {"tasks": len(true_rows), "correct": sum(row["correct"] for row in true_rows), "accuracy": sum(row["correct"] for row in true_rows) / len(true_rows)}, "false": {"tasks": len(false_rows), "correct": sum(row["correct"] for row in false_rows), "accuracy": sum(row["correct"] for row in false_rows) / len(false_rows)}}, "confusion_matrix": {"expected_true_observed_true": tp, "expected_true_observed_false": fn, "expected_false_observed_true": fp, "expected_false_observed_false": tn}, "overall_accuracy": sum(row["correct"] for row in rows) / len(rows), "true_precision": tp / (tp + fp) if tp + fp else None, "true_recall": tp / (tp + fn) if tp + fn else None, "true_f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None, "false_positive_rate": fp / len(false_rows), "false_negative_rate": fn / len(true_rows), "serialization_failures": sum(row["failure_class"] == "SERIALIZATION_FAILURE" for row in rows), "invalid_contract_failures": sum(row["failure_class"] == "INVALID_CONTRACT" for row in rows), "scope_decision_failures": sum(row["failure_class"] == "SCOPE_DECISION_FAILURE" for row in rows), "latency_ms": {"metric": "candidate_action_wall_clock", "median": statistics.median(latencies), "mean": statistics.mean(latencies), "p95": ordered[min(len(ordered) - 1, round((len(ordered) - 1) * 0.95))]}, "energy": {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "gpu_uuid": EXPECTED_GPU_UUID, "gross_joules_per_action_mean": statistics.mean(energies), "gross_joules_per_action_median": statistics.median(energies), "gross_joules_total": sum(energies), "gross_joules_per_validated_task": None}, "idle_power": idle_summary, "execution": {"supplier_model_calls": 16, "teacher_calls": 0, "retries": 0, "escalations": 0}, "historical_comparison": "not numerically merged with confounded historical scope evidence"}


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare", action="store_true")
    group.add_argument("--execute", action="store_true")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.prepare:
        prepare(args.output_dir)
    else:
        execute(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
