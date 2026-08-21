#!/usr/bin/env python3
"""Exploratory, candidate-only Qwen3.5-0.8B atomic supplier audition."""

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

from local_harness.atomic_capability_press import score_scope_object
from local_harness.icm_call import call_worker, list_models
from local_harness.icm_spec import resolve_worker_spec
from local_harness.stage_a_power_telemetry import (
    PowerSampler,
    PowerTelemetryError,
    integrate_energy_joules,
    read_gpu_power,
    remote_health,
)
from local_harness.supervised_capability_loop import _validator_result, load_task_fixture


ROOT = Path(__file__).resolve().parents[1]
PREPARATION_COMMIT = "4dcdbac48b2b3e4e0a766950fd0fc9c7507ba1b4"
TASK_MANIFEST = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_5_0_8B_AUDITION_TASK_SET_2026-08-20.json"
SCORECARD_SCHEMA = ROOT / "docs/research/ATOMIC_SUPPLIER_SCORECARD_SCHEMA_V1.json"
RUNTIME_FREEZE = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_5_0_8B_RUNTIME_FREEZE_2026-08-20.json"
EXPECTED_MODEL_ID = "Qwen3.5-0.8B-Q4_K_M.gguf"
EXPECTED_MODEL_SHA = "bd258782e35f7f458f8aced1adc053e6e92e89bc735ba3be89d38a06121dc517"
EXPECTED_MODEL_SIZE = 532517120
OPERATIVE_PARAMS = 752393024
UPSTREAM_PARAMS = 873438784
EXPECTED_CTX = 40960
EXPECTED_NATIVE_CTX = 262144
EXPECTED_GPU_UUID = "GPU-c2823a81-56f1-b16e-f9cc-34f4dc58eb85"
EXPECTED_BUILD = "d55fb9717"
EXPECTED_LLAMA_VERSION = "9314"
MAX_OUTPUT_TOKENS = 768
TIMEOUT_SECONDS = 900
POWER_INTERVAL_SECONDS = 0.25
IDLE_SECONDS = 30

PROMPT_SUFFIX = """Return ONLY a bare JSON object.
Do not use markdown or code fences.
Do not include reasoning, explanation, or commentary.

The JSON object must have exactly these fields and types:

{
  \"allowed_targets\": [\"string\"],
  \"held_targets\": [\"string\"],
  \"scope_expansion_required\": true,
  \"review_status\": \"string\"
}

Rules:
- allowed_targets must be a JSON array of strings.
- held_targets must be a JSON array of strings.
- scope_expansion_required must be a JSON boolean: true or false.
- review_status must be a JSON string.
- Use the task evidence to determine the values.
- Do not copy the example values unless they are correct.
- Return the object only.

/no_think"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def worker_spec():
    name = os.environ.get("ZTH_CAPABILITY_WORKER_NAME", "router")
    return resolve_worker_spec(
        name,
        base_url=os.environ.get("ZTH_CAPABILITY_WORKER_BASE_URL"),
        model=os.environ.get("ZTH_CAPABILITY_WORKER_MODEL"),
    )


def prompt_for(task: dict[str, Any]) -> str:
    return task["prompt"].rstrip() + "\n\n" + PROMPT_SUFFIX


def task_records() -> list[dict[str, Any]]:
    manifest = load_json(TASK_MANIFEST)
    records: list[dict[str, Any]] = []
    for row in manifest["tasks"]:
        path = ROOT / row["path"]
        if not path.exists() or sha256_file(path) != row["sha256"]:
            raise RuntimeError(f"frozen fixture binding mismatch: {row['task_id']}")
        task = load_task_fixture(path)
        if task["task_id"] != row["task_id"]:
            raise RuntimeError(f"fixture task id mismatch: {row['task_id']}")
        records.append({"manifest": row, "task": task, "path": path})
    if len(records) != 16 or [r["task"]["task_id"] for r in records] != manifest["task_order"]:
        raise RuntimeError("frozen task order/count mismatch")
    if sum(bool(r["manifest"]["scope_expansion_required"]) for r in records) != 8:
        raise RuntimeError("frozen scope-expansion branch balance mismatch")
    return records


def runtime_payload() -> dict[str, Any]:
    runtime = load_json(RUNTIME_FREEZE)
    candidate = runtime["candidate"]
    if candidate["filename"] != EXPECTED_MODEL_ID or candidate["sha256"] != EXPECTED_MODEL_SHA:
        raise RuntimeError("runtime candidate binding mismatch")
    if candidate["size_bytes"] != EXPECTED_MODEL_SIZE:
        raise RuntimeError("runtime candidate size binding mismatch")
    exposed = runtime["llama_cpp_exposed_metadata"]
    if exposed["n_params"] != OPERATIVE_PARAMS or exposed["n_ctx"] != EXPECTED_CTX:
        raise RuntimeError("runtime exposed metadata mismatch")
    if candidate["upstream_total_parameter_count"] != UPSTREAM_PARAMS:
        raise RuntimeError("upstream parameter provenance mismatch")
    return runtime


def telemetry_base_url() -> str:
    value = os.environ.get("ZTH_GPU_TELEMETRY_BASE_URL")
    if not value:
        raise RuntimeError("ZTH_GPU_TELEMETRY_BASE_URL is unset")
    return value


def preflight(spec, records: list[dict[str, Any]], runtime: dict[str, Any]) -> dict[str, Any]:
    if sha256_file(TASK_MANIFEST) != runtime["bindings"]["task_manifest_sha256"]:
        raise RuntimeError("task manifest hash mismatch")
    if sha256_file(SCORECARD_SCHEMA) != runtime["bindings"]["scorecard_schema_sha256"]:
        raise RuntimeError("scorecard schema hash mismatch")
    models = list_models(spec, timeout=30)
    data = models.get("data", []) if isinstance(models, dict) else []
    model_row = next((row for row in data if row.get("id") == EXPECTED_MODEL_ID), None)
    if model_row is None:
        raise RuntimeError("candidate model is not exposed by /v1/models")
    meta = model_row.get("meta") or {}
    for key, expected in {
        "n_ctx": EXPECTED_CTX,
        "n_ctx_train": EXPECTED_NATIVE_CTX,
        "n_embd": 1024,
        "n_params": OPERATIVE_PARAMS,
        "size": 521555200,
    }.items():
        if meta.get(key) != expected:
            raise RuntimeError(f"model metadata mismatch for {key}: {meta.get(key)!r}")
    telemetry_url = telemetry_base_url()
    health = remote_health(base_url=telemetry_url)
    reading = read_gpu_power(EXPECTED_GPU_UUID, base_url=telemetry_url)
    if reading.gpu_uuid != EXPECTED_GPU_UUID:
        raise RuntimeError("telemetry GPU UUID mismatch")
    return {
        "model_ids": [row.get("id") for row in data],
        "candidate_metadata": meta,
        "telemetry_health_schema": health.get("schema"),
        "telemetry_sample": {
            "gpu_uuid": reading.gpu_uuid,
            "measurement_level": 2,
            "measurement_boundary": "gpu_device_only",
        },
        "public_endpoint_alias": os.environ.get("ZTH_PUBLIC_HOST_ALIAS", "JARVIS_LOCAL"),
        "telemetry_public_alias": os.environ.get("ZTH_GPU_TELEMETRY_PUBLIC_ALIAS", "UNSET"),
        "task_count": len(records),
        "prompt_suffix_sha256": sha256_bytes(PROMPT_SUFFIX.encode()),
    }


def sample_window(seconds: int, base_url: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    sampler = PowerSampler(
        lambda: read_gpu_power(EXPECTED_GPU_UUID, base_url=base_url),
        expected_gpu_uuid=EXPECTED_GPU_UUID,
        sample_interval_seconds=POWER_INTERVAL_SECONDS,
    )
    started = time.monotonic()
    sampler.start()
    time.sleep(seconds)
    samples = sampler.stop()
    elapsed = time.monotonic() - started
    serialized = [
        {
            "timestamp_utc": s.timestamp_utc,
            "monotonic_seconds": s.monotonic_seconds,
            "gpu_uuid": s.gpu_uuid,
            "power_watts": s.power_watts,
            "sequence": s.sequence,
        }
        for s in samples
    ]
    return serialized, {
        "sample_interval_seconds": POWER_INTERVAL_SECONDS,
        "requested_seconds": seconds,
        "observed_elapsed_seconds": round(elapsed, 6),
        "sample_count": len(samples),
        "gpu_uuid": EXPECTED_GPU_UUID,
        "measurement_level": 2,
        "measurement_boundary": "gpu_device_only",
        "mean_power_watts": round(statistics.mean(s.power_watts for s in samples), 6),
        "peak_power_watts": round(max(s.power_watts for s in samples), 6),
        "gross_energy_joules": integrate_energy_joules(
            samples, sample_interval_seconds=POWER_INTERVAL_SECONDS, expected_gpu_uuid=EXPECTED_GPU_UUID
        ),
    }


def classify(validation: dict[str, Any] | None) -> dict[str, Any]:
    if validation is None:
        return {
            "parse_valid": False,
            "contract_valid": False,
            "reference_fact_valid": False,
            "failure_classes": ["transport_or_missing_response"],
            "failed_check_ids": [],
        }
    checks = validation.get("checks", [])
    structural = validation.get("structural_checks", [])
    semantic = validation.get("semantic_checks", [])
    status = {check.get("check_id"): check.get("status") for check in checks}
    failure_classes: list[str] = []
    if status.get("parse_json") == "failed":
        failure_classes.append("parse_failure")
    if structural and any(check.get("status") == "failed" for check in structural):
        failure_classes.append("contract_failure")
    if semantic and any(check.get("status") == "failed" for check in semantic):
        failure_classes.append("reference_fact_failure")
    if not failure_classes and validation.get("validation_status") != "passed":
        failure_classes.append("deterministic_validation_failure")
    return {
        "parse_valid": status.get("parse_json") == "passed",
        "contract_valid": bool(structural) and all(check.get("status") == "passed" for check in structural),
        "reference_fact_valid": bool(semantic) and all(check.get("status") == "passed" for check in semantic),
        "failure_classes": failure_classes,
        "failed_check_ids": [check.get("check_id") for check in checks if check.get("status") == "failed"],
    }


def scorecard(task: dict[str, Any], raw: str, validation: dict[str, Any] | None, metadata: dict[str, Any], wall_ms: float, power: dict[str, Any] | None, telemetry_error: str | None) -> dict[str, Any]:
    quality = classify(validation)
    parsed: Any = None
    parse_error = None
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        parse_error = str(exc)
    reference = task["validator"]["reference_facts"]
    atomic = score_scope_object(
        parsed,
        {
            "required_allowed_targets": reference["required_allowed_targets"],
            "required_held_targets": reference["required_held_targets"],
            "requires_scope_expansion_flag": reference["requires_scope_expansion_flag"],
            "review_status": reference["review_status"],
        },
    )
    usage = metadata.get("usage") or {}
    timings = metadata.get("timings") or {}
    return {
        "schema": "zth_atomic_supplier_task_scorecard_v1",
        "task_id": task["task_id"],
        "candidate": EXPECTED_MODEL_ID,
        "screening_only_not_confirmatory": True,
        "transport_valid": metadata.get("transport_classification") == "model_response",
        "transport_classification": metadata.get("transport_classification"),
        "raw_parse_valid": quality["parse_valid"],
        "contract_valid": quality["contract_valid"],
        "reference_fact_valid": quality["reference_fact_valid"],
        "full_validator_pass": bool(validation and validation.get("validation_status") == "passed"),
        "failure_classes": quality["failure_classes"],
        "failed_check_ids": quality["failed_check_ids"],
        "raw_parse_error": parse_error,
        "atomic": atomic,
        "reference_facts": reference,
        "wall_elapsed_ms": wall_ms,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "server_prompt_ms": timings.get("prompt_ms"),
        "server_generation_ms": timings.get("predicted_ms"),
        "power_summary": power,
        "telemetry_valid": telemetry_error is None,
        "telemetry_error": telemetry_error,
        "supplier_model_calls_made": 1,
        "retry_count": 0,
        "escalation_count": 0,
        "teacher_calls": 0,
        "raw_response_preserved": True,
    }


def serialize_samples(samples: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "timestamp_utc": s.timestamp_utc,
            "monotonic_seconds": s.monotonic_seconds,
            "gpu_uuid": s.gpu_uuid,
            "power_watts": s.power_watts,
            "sequence": s.sequence,
        }
        for s in samples
    ]


def execute(output_dir: Path) -> None:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError("audition output directory must be fresh")
    output_dir.mkdir(parents=True, exist_ok=True)
    runtime = runtime_payload()
    records = task_records()
    spec = worker_spec()
    preflight_result = preflight(spec, records, runtime)
    telemetry_url = telemetry_base_url()
    idle_samples, idle_summary = sample_window(IDLE_SECONDS, telemetry_url)
    task_manifest: list[dict[str, Any]] = []
    for record in records:
        task = record["task"]
        task_dir = output_dir / "tasks" / task["task_id"]
        task_dir.mkdir(parents=True, exist_ok=True)
        prompt = prompt_for(task)
        (task_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
        write_json(task_dir / "fixture.snapshot.json", task)
        task_manifest.append({
            "task_id": task["task_id"],
            "source_path": record["manifest"]["path"],
            "source_sha256": record["manifest"]["sha256"],
            "prompt_sha256": sha256_bytes(prompt.encode()),
            "scope_expansion_required": record["manifest"]["scope_expansion_required"],
        })
    manifest = {
        "schema": "zth_qwen3_5_0_8b_atomic_audition_manifest_v1",
        "screening_only_not_confirmatory": True,
        "prepared_at": now(),
        "execution_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "preparation_commit": PREPARATION_COMMIT,
        "driver": str(Path(__file__).resolve().relative_to(ROOT)),
        "driver_sha256": sha256_file(Path(__file__).resolve()),
        "runtime_freeze_path": str(RUNTIME_FREEZE.relative_to(ROOT)),
        "runtime_freeze_sha256": sha256_file(RUNTIME_FREEZE),
        "task_manifest_path": str(TASK_MANIFEST.relative_to(ROOT)),
        "task_manifest_sha256": sha256_file(TASK_MANIFEST),
        "scorecard_schema_path": str(SCORECARD_SCHEMA.relative_to(ROOT)),
        "scorecard_schema_sha256": sha256_file(SCORECARD_SCHEMA),
        "candidate": {
            "model_id": EXPECTED_MODEL_ID,
            "artifact_sha256": EXPECTED_MODEL_SHA,
            "artifact_size_bytes": EXPECTED_MODEL_SIZE,
            "operative_supplier_parameter_count": OPERATIVE_PARAMS,
            "upstream_total_parameter_count": UPSTREAM_PARAMS,
            "quantization": "Q4_K_M",
        },
        "runtime": {
            "context": EXPECTED_CTX,
            "native_context": EXPECTED_NATIVE_CTX,
            "llama_cpp_version": EXPECTED_LLAMA_VERSION,
            "build_revision": EXPECTED_BUILD,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "timeout_seconds": TIMEOUT_SECONDS,
            "parallel": 1,
            "threads": 2,
            "threads_batch": 4,
            "split_mode": "none",
            "fit": "on",
            "fit_target": 512,
            "reasoning": "off",
        },
        "telemetry": {
            "transport": "remote_read_only_http",
            "public_alias": os.environ.get("ZTH_GPU_TELEMETRY_PUBLIC_ALIAS", "UNSET"),
            "measurement_level": 2,
            "measurement_boundary": "gpu_device_only",
            "gpu_uuid": EXPECTED_GPU_UUID,
            "sample_interval_seconds": POWER_INTERVAL_SECONDS,
            "energy_formula": "sum(power_watts * sample_interval_seconds)",
            "idle_baseline_seconds": IDLE_SECONDS,
        },
        "selection": {
            "task_family": "scope-authority-boundary",
            "task_order": [r["task"]["task_id"] for r in records],
            "branch_balance": {"true": 8, "false": 8},
            "intervention_blind": True,
            "outcome_based_replacement": False,
        },
        "execution": {"supplier_model_calls": 16, "retry_count": 0, "escalation_count": 0, "teacher_calls": 0},
        "task_manifest": task_manifest,
        "preflight": preflight_result,
        "gpu_exclusivity": {
            "candidate_runtime_manually_verified": True,
            "reference_1_7b_unloaded": True,
            "v100_teacher_untouched": True,
            "process_level_remote_exclusivity_verified": False,
            "limitation": "telemetry_endpoint_v1_does_not_expose_process_inventory",
        },
    }
    manifest["manifest_sha256"] = sha256_bytes(canonical({**manifest, "manifest_sha256": None}))
    write_json(output_dir / "screening_manifest.json", manifest)
    write_json(output_dir / "idle_power_samples.json", {"summary": idle_summary, "samples": idle_samples})
    write_json(output_dir / "preflight.json", {"status": "passed", "model_calls": 0, "details": preflight_result})
    write_json(output_dir / "lifecycle.json", {"status": "audition_running", "started_at": now(), "model_calls": 0})

    summaries: list[dict[str, Any]] = []
    for record in records:
        task = record["task"]
        task_dir = output_dir / "tasks" / task["task_id"]
        prompt = (task_dir / "prompt.txt").read_text(encoding="utf-8")
        sampler = PowerSampler(
            lambda: read_gpu_power(EXPECTED_GPU_UUID, base_url=telemetry_url),
            expected_gpu_uuid=EXPECTED_GPU_UUID,
            sample_interval_seconds=POWER_INTERVAL_SECONDS,
        )
        request_start = time.monotonic()
        request_start_at = now()
        sampler.start()
        response = call_worker(spec, prompt, MAX_OUTPUT_TOKENS, timeout=TIMEOUT_SECONDS)
        response_end = time.monotonic()
        telemetry_error = None
        try:
            samples = sampler.stop()
            power_samples = serialize_samples(samples)
            powers = [sample.power_watts for sample in samples]
            power_summary = {
                "sample_count": len(samples),
                "sample_interval_seconds": POWER_INTERVAL_SECONDS,
                "measurement_level": 2,
                "measurement_boundary": "gpu_device_only",
                "mean_active_watts": round(statistics.mean(powers), 6),
                "peak_observed_watts": round(max(powers), 6),
                "gross_energy_joules": integrate_energy_joules(samples, sample_interval_seconds=POWER_INTERVAL_SECONDS, expected_gpu_uuid=EXPECTED_GPU_UUID),
            }
        except PowerTelemetryError as exc:
            power_samples = []
            power_summary = None
            telemetry_error = str(exc)
        metadata = response.metadata()
        metadata["request_url"] = None
        metadata["endpoint_alias"] = os.environ.get("ZTH_PUBLIC_HOST_ALIAS", "JARVIS_LOCAL")
        validation = _validator_result(response.content, task, attempt_id=f"qwen35-08b-{task['task_id']}") if metadata.get("transport_classification") == "model_response" else None
        write_json(task_dir / "response.json", {"status": response.status, "content": response.content, "metadata": metadata, "request_started_at": request_start_at, "response_captured_at": now(), "wall_elapsed_ms": round((response_end - request_start) * 1000, 3)})
        if validation is not None:
            write_json(task_dir / "validation.json", validation)
        write_json(task_dir / "power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "gpu_uuid": EXPECTED_GPU_UUID, "samples": power_samples, "error": telemetry_error})
        row = scorecard(task, response.content, validation, metadata, round((response_end - request_start) * 1000, 3), power_summary, telemetry_error)
        write_json(task_dir / "atomic_scorecard.json", row)
        summaries.append(row)
        if telemetry_error:
            raise RuntimeError(f"telemetry failed during {task['task_id']}: {telemetry_error}")

    aggregate = aggregate_rows(summaries, idle_summary)
    write_json(output_dir / "aggregate.json", aggregate)
    write_json(output_dir / "lifecycle.json", {"status": "audition_terminal", "completed_at": now(), "model_calls": 16, "supplier_model_calls": 16, "teacher_calls": 0, "retries": 0, "escalations": 0})
    print(json.dumps({"status": "audition_terminal", "output_dir": str(output_dir), "model_calls": 16, "teacher_calls": 0}, indent=2))


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, int(round((len(ordered) - 1) * fraction)))], 3)


def aggregate_rows(rows: list[dict[str, Any]], idle_summary: dict[str, Any]) -> dict[str, Any]:
    def count(predicate):
        return sum(1 for row in rows if predicate(row))
    wall = [row["wall_elapsed_ms"] for row in rows]
    energy = [row["power_summary"]["gross_energy_joules"] for row in rows if row.get("power_summary")]
    profile = {str(i): count(lambda row, i=i: row["atomic"]["semantic_fields_correct"] == i) for i in range(5)}
    branch = {}
    for expected in (False, True):
        subset = [r for r in rows if r["reference_facts"]["requires_scope_expansion_flag"] is expected]
        branch[str(expected).lower()] = {
            "tasks": len(subset),
            "scope_expansion_correct": count(lambda row: row in subset and row["atomic"]["scope_expansion"]["correct"]),
            "full_validator_passes": sum(bool(row["full_validator_pass"]) for row in subset),
        }
    def exact(field):
        return sum(bool(row["atomic"][field]["exact_set_match"]) for row in rows)
    return {
        "schema": "zth_qwen3_5_0_8b_atomic_audition_aggregate_v1",
        "screening_only_not_confirmatory": True,
        "candidate": EXPECTED_MODEL_ID,
        "operative_supplier_parameter_count": OPERATIVE_PARAMS,
        "upstream_total_parameter_count": UPSTREAM_PARAMS,
        "tasks": len(rows),
        "transport_valid": count(lambda r: r["transport_valid"]),
        "raw_parse_valid": count(lambda r: r["raw_parse_valid"]),
        "contract_valid": count(lambda r: r["contract_valid"]),
        "reference_fact_valid": count(lambda r: r["reference_fact_valid"]),
        "full_validator_passes": count(lambda r: r["full_validator_pass"]),
        "allowed_targets": {"exact": exact("allowed_targets"), "precision_mean": statistics.mean([r["atomic"]["allowed_targets"]["precision"] or 0 for r in rows]), "recall_mean": statistics.mean([r["atomic"]["allowed_targets"]["recall"] or 0 for r in rows])},
        "held_targets": {"exact": exact("held_targets"), "precision_mean": statistics.mean([r["atomic"]["held_targets"]["precision"] or 0 for r in rows]), "recall_mean": statistics.mean([r["atomic"]["held_targets"]["recall"] or 0 for r in rows])},
        "authority_separation": {"observed_and_correct": count(lambda r: r["atomic"]["authority_separation"]["observability"] == "OBSERVED_AND_CORRECT"), "observed": count(lambda r: r["atomic"]["object_observable"]), "overlap": count(lambda r: bool(r["atomic"]["authority_separation"]["overlap_targets"]))},
        "scope_expansion": {"correct": count(lambda r: r["atomic"]["scope_expansion"]["correct"] is True), "false_positive": count(lambda r: r["atomic"]["scope_expansion"]["false_positive"]), "false_negative": count(lambda r: r["atomic"]["scope_expansion"]["false_negative"]), "not_observable": count(lambda r: r["atomic"]["scope_expansion"]["correct"] is None)},
        "review_status": {"exact": count(lambda r: r["atomic"]["review_status"]["exact_match"] is True), "confusion": sorted({r["atomic"]["review_status"]["confusion_pair"] for r in rows if r["atomic"]["review_status"]["confusion_pair"]})},
        "semantic_fields_correct_distribution": profile,
        "three_of_four_near_misses": [r["task_id"] for r in rows if r["atomic"]["semantic_fields_correct"] == 3],
        "three_of_four_missing_fields": {r["task_id"]: [k for k, v in r["atomic"]["semantic_field_vector"].items() if not v] for r in rows if r["atomic"]["semantic_fields_correct"] == 3},
        "branch_results": branch,
        "latency_ms": {"metric": "candidate_action_wall_clock", "median": round(statistics.median(wall), 3), "mean": round(statistics.mean(wall), 3), "p95": percentile(wall, 0.95)},
        "energy": {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "gross_joules_per_action_median": round(statistics.median(energy), 6) if energy else None, "gross_joules_per_action_mean": round(statistics.mean(energy), 6) if energy else None, "gross_joules_per_validated_task": round(sum(energy) / sum(bool(r["full_validator_pass"]) for r in rows), 6) if energy and any(r["full_validator_pass"] for r in rows) else None, "energy_break_even": "NOT_COMPUTED_EXPLORATORY"},
        "idle_power": idle_summary,
        "execution": {"supplier_model_calls": 16, "teacher_calls": 0, "retry_count": 0, "escalation_count": 0},
        "historical_evidence_merged": False,
        "production_routing_changed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--execute", action="store_true", required=True)
    args = parser.parse_args()
    execute(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
