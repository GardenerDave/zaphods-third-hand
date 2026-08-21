#!/usr/bin/env python3
"""Paired exploratory review-ontology interface isolation for Qwen3.5-0.8B."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

from local_harness.icm_call import call_worker
from local_harness.stage_a_power_telemetry import PowerSampler, PowerTelemetryError, integrate_energy_joules, read_gpu_power
from local_harness.supervised_capability_loop import _validator_result
from scripts.zth_qwen3_5_0_8b_atomic_audition import (
    EXPECTED_GPU_UUID,
    EXPECTED_MODEL_ID,
    EXPECTED_MODEL_SHA,
    EXPECTED_MODEL_SIZE,
    EXPECTED_CTX,
    EXPECTED_NATIVE_CTX,
    IDLE_SECONDS,
    MAX_OUTPUT_TOKENS,
    POWER_INTERVAL_SECONDS,
    PREPARATION_COMMIT,
    RUNTIME_FREEZE,
    SCORECARD_SCHEMA,
    TASK_MANIFEST,
    TIMEOUT_SECONDS,
    PROMPT_SUFFIX as ORIGINAL_SUFFIX,
    aggregate_rows,
    now,
    preflight,
    runtime_payload,
    scorecard,
    serialize_samples,
    sha256_bytes,
    sha256_file,
    sample_window,
    task_records,
    worker_spec,
    write_json,
)


ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_RUN = ROOT / ".work/model_size_supplier_floor/qwen3_5_0_8b_atomic_audition/run_20260821T004420Z"
ORIGINAL_MANIFEST_SHA = "96770484dc302de63619f58ff88397937b01b654b4f376d54eda53b74c4d1808"
ORIGINAL_AGGREGATE_SHA = "27a6757bfc7d3c356182d7a3d8995d32bc1967c35fa0eb7ef05e097d8ba5e330"
ORIGINAL_SUFFIX_SHA = "3a1003f506379b1fd21eae3103cc683bf86a12f5667bdcc07a76828a58b0b9c8"


def new_suffix() -> str:
    old = '- review_status must be a JSON string.\n'
    new = ('- review_status must be a JSON string.\n'
           '- For this task family, the valid review_status protocol value is:\n'
           '  "ready_for_review"\n'
           '- Use "ready_for_review" when the bounded result is ready to be returned for review.\n'
           '- Do not invent alternative status labels such as: "ready", "approved", "pending", "allowed", "unapproved", or "stale".\n')
    if ORIGINAL_SUFFIX.count(old) != 1:
        raise RuntimeError("original review-status line is not uniquely bound")
    return ORIGINAL_SUFFIX.replace(old, new)


NEW_SUFFIX = new_suffix()
PROMPT_DIFF = "".join(difflib.unified_diff(
    ORIGINAL_SUFFIX.splitlines(keepends=True),
    NEW_SUFFIX.splitlines(keepends=True),
    fromfile="original_suffix",
    tofile="ontology_explicit_suffix",
))


def prompt_for(task: dict) -> str:
    return task["prompt"].rstrip() + "\n\n" + NEW_SUFFIX


def execute(output_dir: Path) -> None:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError("isolation output directory must be fresh")
    if sha256_file(ORIGINAL_RUN / "screening_manifest.json") != ORIGINAL_MANIFEST_SHA:
        raise RuntimeError("original execution manifest changed")
    if sha256_file(ORIGINAL_RUN / "aggregate.json") != ORIGINAL_AGGREGATE_SHA:
        raise RuntimeError("original aggregate changed")
    if sha256_bytes(ORIGINAL_SUFFIX.encode()) != ORIGINAL_SUFFIX_SHA:
        raise RuntimeError("original prompt suffix binding changed")
    output_dir.mkdir(parents=True, exist_ok=True)
    runtime = runtime_payload()
    records = task_records()
    spec = worker_spec()
    preflight_result = preflight(spec, records, runtime)
    telemetry_url = os.environ.get("ZTH_GPU_TELEMETRY_BASE_URL")
    if not telemetry_url:
        raise RuntimeError("ZTH_GPU_TELEMETRY_BASE_URL is unset")
    idle_samples, idle_summary = sample_window(IDLE_SECONDS, telemetry_url)
    task_manifest = []
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
        })
    manifest = {
        "schema": "zth_qwen3_5_0_8b_review_ontology_interface_isolation_manifest_v1",
        "screening_only_not_confirmatory": True,
        "interface_isolation_only": True,
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
        "original_run": {
            "run_directory": str(ORIGINAL_RUN.relative_to(ROOT)),
            "manifest_sha256": ORIGINAL_MANIFEST_SHA,
            "aggregate_sha256": ORIGINAL_AGGREGATE_SHA,
            "prompt_suffix_sha256": ORIGINAL_SUFFIX_SHA,
        },
        "prompt_interface": {
            "original_suffix_sha256": ORIGINAL_SUFFIX_SHA,
            "new_suffix_sha256": sha256_bytes(NEW_SUFFIX.encode()),
            "diff_sha256": sha256_bytes(PROMPT_DIFF.encode()),
            "diff": PROMPT_DIFF,
            "review_status_protocol_explicit": "ready_for_review",
            "all_frozen_tasks_expect_same_protocol_token": True,
        },
        "candidate": {
            "model_id": EXPECTED_MODEL_ID,
            "artifact_sha256": EXPECTED_MODEL_SHA,
            "artifact_size_bytes": EXPECTED_MODEL_SIZE,
            "operative_supplier_parameter_count": runtime["candidate"]["operative_supplier_parameter_count"],
        },
        "runtime": runtime["runtime"],
        "telemetry": runtime["telemetry"],
        "selection": {"task_order": [r["task"]["task_id"] for r in records], "task_count": 16, "task_bytes_unchanged": True},
        "execution": {"supplier_model_calls": 16, "teacher_calls": 0, "retry_count": 0, "escalation_count": 0},
        "preflight": preflight_result,
        "task_manifest": task_manifest,
    }
    manifest["manifest_sha256"] = sha256_bytes(json.dumps({**manifest, "manifest_sha256": None}, sort_keys=True, separators=(",", ":")).encode())
    write_json(output_dir / "screening_manifest.json", manifest)
    write_json(output_dir / "idle_power_samples.json", {"summary": idle_summary, "samples": idle_samples})
    write_json(output_dir / "preflight.json", {"status": "passed", "model_calls": 0, "details": preflight_result})
    write_json(output_dir / "lifecycle.json", {"status": "isolation_running", "started_at": now(), "model_calls": 0})

    rows = []
    for record in records:
        task = record["task"]
        task_dir = output_dir / "tasks" / task["task_id"]
        prompt = (task_dir / "prompt.txt").read_text(encoding="utf-8")
        sampler = PowerSampler(lambda: read_gpu_power(EXPECTED_GPU_UUID, base_url=telemetry_url), expected_gpu_uuid=EXPECTED_GPU_UUID, sample_interval_seconds=POWER_INTERVAL_SECONDS)
        started = time.monotonic()
        started_at = now()
        sampler.start()
        response = call_worker(spec, prompt, MAX_OUTPUT_TOKENS, timeout=TIMEOUT_SECONDS)
        ended = time.monotonic()
        telemetry_error = None
        try:
            samples = sampler.stop()
            powers = [s.power_watts for s in samples]
            power_summary = {
                "sample_count": len(samples),
                "sample_interval_seconds": POWER_INTERVAL_SECONDS,
                "measurement_level": 2,
                "measurement_boundary": "gpu_device_only",
                "mean_active_watts": sum(powers) / len(powers),
                "peak_observed_watts": max(powers),
                "gross_energy_joules": integrate_energy_joules(samples, sample_interval_seconds=POWER_INTERVAL_SECONDS, expected_gpu_uuid=EXPECTED_GPU_UUID),
            }
            power_samples = serialize_samples(samples)
        except PowerTelemetryError as exc:
            telemetry_error = str(exc)
            power_summary = None
            power_samples = []
        metadata = response.metadata()
        metadata["request_url"] = None
        metadata["endpoint_alias"] = os.environ.get("ZTH_PUBLIC_HOST_ALIAS", "JARVIS_LOCAL")
        validation = _validator_result(response.content, task, attempt_id=f"qwen35-review-ontology-{task['task_id']}") if metadata.get("transport_classification") == "model_response" else None
        raw = {"status": response.status, "content": response.content, "metadata": metadata, "request_started_at": started_at, "response_captured_at": now(), "wall_elapsed_ms": round((ended - started) * 1000, 3)}
        write_json(task_dir / "response.json", raw)
        if validation is not None:
            write_json(task_dir / "validation.json", validation)
        write_json(task_dir / "power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "gpu_uuid": EXPECTED_GPU_UUID, "samples": power_samples, "error": telemetry_error})
        row = scorecard(task, response.content, validation, metadata, raw["wall_elapsed_ms"], power_summary, telemetry_error)
        write_json(task_dir / "atomic_scorecard.json", row)
        rows.append(row)
        if telemetry_error:
            raise RuntimeError(f"telemetry failed during {task['task_id']}: {telemetry_error}")
    aggregate = aggregate_rows(rows, idle_summary)
    aggregate["interface_isolation_only"] = True
    aggregate["original_run_unchanged"] = True
    write_json(output_dir / "aggregate.json", aggregate)
    write_json(output_dir / "lifecycle.json", {"status": "isolation_terminal", "completed_at": now(), "model_calls": 16, "supplier_model_calls": 16, "teacher_calls": 0, "retries": 0, "escalations": 0})
    print(json.dumps({"status": "isolation_terminal", "output_dir": str(output_dir), "model_calls": 16, "teacher_calls": 0}, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--execute", action="store_true", required=True)
    args = parser.parse_args()
    execute(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
