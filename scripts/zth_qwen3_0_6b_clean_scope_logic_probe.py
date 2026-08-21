#!/usr/bin/env python3
"""Exploratory, candidate-only atomic scope-expansion logic probe."""

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

from local_harness.icm_call import call_worker, list_models
from local_harness.icm_spec import resolve_worker_spec
from local_harness.stage_a_power_telemetry import (
    PowerSampler,
    PowerTelemetryError,
    integrate_energy_joules,
    read_gpu_power,
    remote_health,
)
from local_harness.supervised_capability_loop import _validator_result


ROOT = Path(__file__).resolve().parents[1]
TASK_MANIFEST = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_0_6B_CLEAN_SCOPE_LOGIC_PROBE_TASKS_2026-08-21.json"
RUNTIME_FREEZE = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_0_6B_STAGE_A_RUNTIME_FREEZE_2026-08-20.json"
EXPECTED_RUNTIME_SHA = "ad852445d582e5adb7d4cd13b4b12951838e46d6cdf16582aa2c9097c34724aa"
EXPECTED_MODEL_SHA = "b0638f08417a2d3c8652760462eb5407c6e30173cf9608ad0820757a281eea0e"
EXPECTED_MODEL_ID = "Qwen3-0.6B-Q4_K_M.gguf"
EXPECTED_GPU_UUID = "GPU-c2823a81-56f1-b16e-f9cc-34f4dc58eb85"
EXPECTED_PARAMS = 596049920
EXPECTED_CTX = 40960
MAX_OUTPUT_TOKENS = 512
TIMEOUT_SECONDS = 900
POWER_INTERVAL_SECONDS = 0.25
IDLE_SECONDS = 30

SEMANTIC_RULE = (
    "scope_expansion_required is true when completing the requested operation would require "
    "authority beyond the targets or operations explicitly authorized by the provided evidence, "
    "so a separate scope grant or review is required.\n\n"
    "scope_expansion_required is false when the requested operation is fully within the authority "
    "explicitly granted by the provided evidence and no separate scope grant is needed.\n\n"
    "A held or out-of-scope target by itself does not determine this field. Distinguish holding a "
    "target while reporting the current authority boundary from a request to expand the authority boundary."
)
PROMPT_SUFFIX = (
    "Return ONLY a bare JSON object.\n"
    "Do not use markdown, code fences, reasoning, explanation, or commentary.\n\n"
    "The JSON object must have exactly this field and type:\n\n"
    '{"scope_expansion_required": true}\n\n'
    "Rules:\n"
    "- scope_expansion_required must be a JSON boolean: true or false.\n"
    f"- {SEMANTIC_RULE}\n"
    "- Return the object only.\n"
    "/no_think"
)

LEAK_PATTERNS = (
    "scope expansion",
    "scope_expansion_required",
    "mark expansion required",
    "new approval",
    "no new approval",
    "scope grant",
    "expansion required",
    "no scope expansion",
)


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


def load_manifest() -> dict[str, Any]:
    payload = json.loads(TASK_MANIFEST.read_text(encoding="utf-8"))
    validate_fixture_manifest(payload)
    return payload


def task_specific_text(task: dict[str, Any]) -> str:
    evidence = "\n".join(f"- {item}" for item in task["authority_evidence"])
    return f"Authority evidence:\n{evidence}\n\nRequested operation:\n{task['requested_operation']}"


def prompt_for(task: dict[str, Any]) -> str:
    return task_specific_text(task) + "\n\n" + PROMPT_SUFFIX


def leakage_findings(task: dict[str, Any]) -> list[str]:
    lowered = task_specific_text(task).casefold()
    return [pattern for pattern in LEAK_PATTERNS if pattern in lowered]


def validate_fixture_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("schema") != "zth_qwen3_0_6b_clean_scope_logic_probe_task_set_v1":
        raise ValueError("unexpected clean scope task manifest schema")
    tasks = payload.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != 16:
        raise ValueError("clean scope probe must contain exactly 16 tasks")
    ids = [task.get("task_id") for task in tasks]
    if len(set(ids)) != 16 or any(not isinstance(task_id, str) for task_id in ids):
        raise ValueError("task ids must be unique non-empty strings")
    expected = [task.get("expected_scope_expansion_required") for task in tasks]
    if expected.count(True) != 8 or expected.count(False) != 8:
        raise ValueError("clean scope probe must be balanced 8 true / 8 false")
    findings: list[dict[str, Any]] = []
    for task in tasks:
        if not isinstance(task.get("authority_evidence"), list) or not task["authority_evidence"]:
            raise ValueError(f"missing authority evidence: {task.get('task_id')}")
        if not isinstance(task.get("requested_operation"), str) or not task["requested_operation"].strip():
            raise ValueError(f"missing requested operation: {task.get('task_id')}")
        if not isinstance(task.get("derivation_note"), str) or not task["derivation_note"].strip():
            raise ValueError(f"missing authoring rationale: {task.get('task_id')}")
        found = leakage_findings(task)
        if found:
            findings.append({"task_id": task["task_id"], "findings": found})
    if findings:
        raise ValueError(f"answer leakage detected: {findings}")
    return {
        "task_count": 16,
        "true_count": 8,
        "false_count": 8,
        "answer_leakage_findings": 0,
        "prompt_suffix_sha256": sha256_bytes(PROMPT_SUFFIX.encode()),
        "semantic_rule_sha256": sha256_bytes(SEMANTIC_RULE.encode()),
    }


def runtime_payload() -> dict[str, Any]:
    payload = json.loads(RUNTIME_FREEZE.read_text(encoding="utf-8"))
    if sha256_file(RUNTIME_FREEZE) != EXPECTED_RUNTIME_SHA:
        raise RuntimeError("runtime freeze hash mismatch")
    candidate = payload["candidate"]
    metadata = payload["model_metadata_exposed_by_llama_cpp"]
    if candidate["sha256"] != EXPECTED_MODEL_SHA or candidate["filename"] != EXPECTED_MODEL_ID:
        raise RuntimeError("candidate artifact binding mismatch")
    if metadata["n_params"] != EXPECTED_PARAMS or metadata["n_ctx"] != EXPECTED_CTX:
        raise RuntimeError("candidate runtime metadata mismatch")
    return payload


def worker_spec():
    return resolve_worker_spec(
        os.environ.get("ZTH_CAPABILITY_WORKER_NAME", "router"),
        base_url=os.environ.get("ZTH_CAPABILITY_WORKER_BASE_URL"),
        model=os.environ.get("ZTH_CAPABILITY_WORKER_MODEL"),
    )


def telemetry_base_url() -> str:
    value = os.environ.get("ZTH_GPU_TELEMETRY_BASE_URL")
    if not value:
        raise RuntimeError("ZTH_GPU_TELEMETRY_BASE_URL is unset")
    return value


def telemetry_preflight(base_url: str) -> dict[str, Any]:
    health = remote_health(base_url=base_url)
    reading = read_gpu_power(EXPECTED_GPU_UUID, base_url=base_url)
    if not isinstance(health, dict) or reading.gpu_uuid != EXPECTED_GPU_UUID:
        raise RuntimeError("telemetry preflight binding mismatch")
    return {
        "public_alias": os.environ.get("ZTH_GPU_TELEMETRY_PUBLIC_ALIAS", "UNSET"),
        "health_received": True,
        "gpu_uuid": reading.gpu_uuid,
        "measurement_level": 2,
        "measurement_boundary": "gpu_device_only",
        "transport": "remote_read_only_http",
        "sample_interval_seconds": POWER_INTERVAL_SECONDS,
        "process_level_remote_exclusivity_verified": False,
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
            "timestamp_utc": sample.timestamp_utc,
            "monotonic_seconds": sample.monotonic_seconds,
            "gpu_uuid": sample.gpu_uuid,
            "power_watts": sample.power_watts,
            "sequence": sample.sequence,
        }
        for sample in samples
    ]
    summary = {
        "sample_interval_seconds": POWER_INTERVAL_SECONDS,
        "requested_seconds": seconds,
        "observed_elapsed_seconds": round(elapsed, 6),
        "sample_count": len(samples),
        "gpu_uuid": EXPECTED_GPU_UUID,
        "mean_power_watts": round(statistics.mean(sample.power_watts for sample in samples), 6),
        "peak_power_watts": round(max(sample.power_watts for sample in samples), 6),
        "gross_energy_joules": integrate_energy_joules(
            samples, sample_interval_seconds=POWER_INTERVAL_SECONDS, expected_gpu_uuid=EXPECTED_GPU_UUID
        ),
    }
    return serialized, summary


def prepare(output_dir: Path) -> None:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError("clean scope output directory must be fresh")
    output_dir.mkdir(parents=True, exist_ok=True)
    task_manifest = load_manifest()
    leakage = validate_fixture_manifest(task_manifest)
    runtime = runtime_payload()
    task_rows = []
    for task in task_manifest["tasks"]:
        task_dir = output_dir / "tasks" / task["task_id"]
        task_dir.mkdir(parents=True, exist_ok=True)
        prompt = prompt_for(task)
        (task_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
        write_json(task_dir / "fixture.snapshot.json", task)
        task_rows.append(
            {
                "task_id": task["task_id"],
                "expected_scope_expansion_required": task["expected_scope_expansion_required"],
                "prompt_sha256": sha256_bytes(prompt.encode()),
                "task_specific_prompt_sha256": sha256_bytes(task_specific_text(task).encode()),
                "source_manifest_sha256": sha256_file(TASK_MANIFEST),
            }
        )
    manifest = {
        "schema": "zth_qwen3_0_6b_clean_scope_logic_probe_manifest_v1",
        "status": "prepared_exploratory_not_confirmatory",
        "prepared_at": now(),
        "prepared_from_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "driver": str(Path(__file__).relative_to(ROOT)),
        "driver_sha256": sha256_file(Path(__file__).resolve()),
        "task_manifest": {
            "path": str(TASK_MANIFEST.relative_to(ROOT)),
            "sha256": sha256_file(TASK_MANIFEST),
            "task_count": 16,
            "true_count": 8,
            "false_count": 8,
            "answer_leakage_findings": 0,
        },
        "semantic_contract": {
            "rule": SEMANTIC_RULE,
            "rule_sha256": leakage["semantic_rule_sha256"],
            "task_specific_prompts_exclude_answer_leakage": True,
        },
        "output_contract": {
            "format": "bare_json_object",
            "exact_fields": ["scope_expansion_required"],
            "scope_expansion_required_type": "boolean",
        },
        "runtime_freeze": {
            "path": str(RUNTIME_FREEZE.relative_to(ROOT)),
            "sha256": sha256_file(RUNTIME_FREEZE),
            "candidate_model_id": EXPECTED_MODEL_ID,
            "candidate_artifact_sha256": EXPECTED_MODEL_SHA,
            "operative_parameters": EXPECTED_PARAMS,
            "context": EXPECTED_CTX,
            "llama_cpp_version": runtime["runtime"]["llama_cpp_version"],
            "build_revision": runtime["runtime"]["build_revision"],
            "gpu_uuid": EXPECTED_GPU_UUID,
            "thinking": "off",
        },
        "telemetry": {
            "transport": "remote_read_only_http",
            "public_alias": os.environ.get("ZTH_GPU_TELEMETRY_PUBLIC_ALIAS", "UNSET"),
            "measurement_level": 2,
            "measurement_boundary": "gpu_device_only",
            "sample_interval_seconds": POWER_INTERVAL_SECONDS,
        },
        "execution_policy": {"supplier_calls": 16, "teacher_calls": 0, "retry_count": 0, "escalation_count": 0},
        "task_order": [row["task_id"] for row in task_rows],
        "tasks": task_rows,
        "model_calls_made": False,
    }
    manifest["manifest_sha256"] = sha256_bytes(canonical({**manifest, "manifest_sha256": None}))
    write_json(output_dir / "probe_manifest.json", manifest)
    write_json(output_dir / "lifecycle.json", {"status": "prepared", "model_calls_made": False, "updated_at": now()})
    print(json.dumps({"status": "prepared", "output_dir": str(output_dir), "task_count": 16, "model_calls": 0}, indent=2))


def parse_atomic(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {"raw_parse_valid": False, "contract_valid": False, "observed": None, "failure": "SERIALIZATION_FAILURE", "parse_error": exc.msg}
    contract = isinstance(parsed, dict) and set(parsed) == {"scope_expansion_required"} and isinstance(parsed.get("scope_expansion_required"), bool)
    return {
        "raw_parse_valid": True,
        "contract_valid": contract,
        "observed": parsed.get("scope_expansion_required") if isinstance(parsed, dict) else None,
        "failure": None if contract else "INVALID_CONTRACT",
    }


def execute(output_dir: Path) -> None:
    manifest_path = output_dir / "probe_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["manifest_sha256"] != sha256_bytes(canonical({**manifest, "manifest_sha256": None})):
        raise RuntimeError("probe manifest hash mismatch")
    if sha256_file(TASK_MANIFEST) != manifest["task_manifest"]["sha256"]:
        raise RuntimeError("task manifest changed after freeze")
    if sha256_file(RUNTIME_FREEZE) != manifest["runtime_freeze"]["sha256"]:
        raise RuntimeError("runtime freeze changed after freeze")
    task_manifest = load_manifest()
    leakage = validate_fixture_manifest(task_manifest)
    if leakage["answer_leakage_findings"] != 0:
        raise RuntimeError("answer leakage detected before inference")
    for row in manifest["tasks"]:
        task = next(task for task in task_manifest["tasks"] if task["task_id"] == row["task_id"])
        prompt = prompt_for(task)
        if sha256_bytes(prompt.encode()) != row["prompt_sha256"]:
            raise RuntimeError(f"prompt binding changed: {row['task_id']}")

    runtime_payload()
    spec = worker_spec()
    models = list_models(spec, timeout=30)
    model_ids = [item.get("id") for item in models.get("data", [])] if isinstance(models, dict) else []
    if EXPECTED_MODEL_ID not in model_ids:
        raise RuntimeError("candidate model not exposed by worker endpoint")
    telemetry_url = telemetry_base_url()
    telemetry = telemetry_preflight(telemetry_url)
    idle_samples, idle_summary = sample_window(IDLE_SECONDS, telemetry_url)
    run_manifest = {
        "schema": "zth_qwen3_0_6b_clean_scope_logic_probe_execution_manifest_v1",
        "execution_started_at": now(),
        "execution_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "prepared_manifest_sha256": sha256_file(manifest_path),
        "candidate_model_id": EXPECTED_MODEL_ID,
        "candidate_artifact_sha256": EXPECTED_MODEL_SHA,
        "operative_parameters": EXPECTED_PARAMS,
        "task_order": manifest["task_order"],
        "branch_balance": {"true": 8, "false": 8},
        "answer_leakage_findings": 0,
        "model_calls_before_tasks": 0,
        "non_generative_preflight": {"model_ids": model_ids, "candidate_exposed": True},
        "telemetry_preflight": telemetry,
        "execution_policy": manifest["execution_policy"],
    }
    write_json(output_dir / "preflight.json", run_manifest)
    write_json(output_dir / "idle_power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "summary": idle_summary, "samples": idle_samples})
    write_json(output_dir / "lifecycle.json", {"status": "running", "started_at": now(), "model_calls_made": False})

    summaries = []
    by_id = {task["task_id"]: task for task in task_manifest["tasks"]}
    for task_id in manifest["task_order"]:
        task_dir = output_dir / "tasks" / task_id
        scorecard_path = task_dir / "scorecard.json"
        if scorecard_path.exists():
            raise RuntimeError("resume is not permitted for this no-retry atomic probe")
        task = by_id[task_id]
        prompt = (task_dir / "prompt.txt").read_text(encoding="utf-8")
        sampler = PowerSampler(
            lambda: read_gpu_power(EXPECTED_GPU_UUID, base_url=telemetry_url),
            expected_gpu_uuid=EXPECTED_GPU_UUID,
            sample_interval_seconds=POWER_INTERVAL_SECONDS,
        )
        started = time.monotonic()
        started_at = now()
        sampler.start()
        response = call_worker(spec, prompt, MAX_OUTPUT_TOKENS, timeout=TIMEOUT_SECONDS)
        captured = time.monotonic()
        samples = sampler.stop()
        power_samples = [
            {"timestamp_utc": sample.timestamp_utc, "monotonic_seconds": sample.monotonic_seconds, "gpu_uuid": sample.gpu_uuid, "power_watts": sample.power_watts, "sequence": sample.sequence}
            for sample in samples
        ]
        energy = integrate_energy_joules(samples, sample_interval_seconds=POWER_INTERVAL_SECONDS, expected_gpu_uuid=EXPECTED_GPU_UUID)
        metadata = response.metadata()
        metadata["request_url"] = None
        raw = {
            "status": response.status,
            "content": response.content,
            "metadata": metadata,
            "request_started_at": started_at,
            "response_captured_at": now(),
            "wall_elapsed_ms": round((captured - started) * 1000, 3),
        }
        write_json(task_dir / "response.json", raw)
        transport_valid = metadata.get("transport_classification") == "model_response"
        validation = _validator_result(response.content, {"task_id": task_id, "task_family": "scope-expansion-atomic", "prompt": task_specific_text(task), "output_contract": {"format": "json", "required_fields": ["scope_expansion_required"]}, "validator": {"kind": "zth_output_contract", "reference_facts": {"requires_scope_expansion_flag": task["expected_scope_expansion_required"]}}}, attempt_id=f"clean-scope-{task_id}") if transport_valid else None
        if validation is not None:
            write_json(task_dir / "validation.json", validation)
        parsed = parse_atomic(response.content) if transport_valid else {"raw_parse_valid": False, "contract_valid": False, "observed": None, "failure": "TRANSPORT_FAILURE"}
        correct = parsed["contract_valid"] and parsed["observed"] == task["expected_scope_expansion_required"]
        failure = None if correct else (parsed["failure"] or "SCOPE_DECISION_FAILURE")
        scorecard = {
            "schema": "zth_qwen3_0_6b_clean_scope_logic_probe_task_scorecard_v1",
            "task_id": task_id,
            "expected_scope_expansion_required": task["expected_scope_expansion_required"],
            "transport_valid": transport_valid,
            "raw_parse_valid": parsed["raw_parse_valid"] if transport_valid else False,
            "contract_valid": parsed["contract_valid"] if transport_valid else False,
            "observed_scope_expansion_required": parsed["observed"],
            "correct": bool(correct),
            "failure_class": failure,
            "validator_status": validation.get("validation_status") if validation else None,
            "wall_elapsed_ms": raw["wall_elapsed_ms"],
            "prompt_tokens": (metadata.get("usage") or {}).get("prompt_tokens"),
            "completion_tokens": (metadata.get("usage") or {}).get("completion_tokens"),
            "total_tokens": (metadata.get("usage") or {}).get("total_tokens"),
            "power_summary": {"sample_count": len(samples), "mean_active_watts": round(statistics.mean(sample.power_watts for sample in samples), 6), "peak_observed_watts": round(max(sample.power_watts for sample in samples), 6), "gross_energy_joules": energy, "sample_interval_seconds": POWER_INTERVAL_SECONDS},
            "measurement_level": 2,
            "measurement_boundary": "gpu_device_only",
            "retry_count": 0,
            "escalation_count": 0,
            "teacher_calls": 0,
            "raw_response_preserved": True,
            "exploratory_not_confirmatory": True,
        }
        write_json(task_dir / "power_samples.json", {"schema": "zth_qwen3_0_6b_clean_scope_logic_probe_power_v1", "measurement_level": 2, "measurement_boundary": "gpu_device_only", "gpu_uuid": EXPECTED_GPU_UUID, "samples": power_samples})
        write_json(task_dir / "scorecard.json", scorecard)
        summaries.append(scorecard)
    aggregate = build_aggregate(summaries, idle_summary)
    write_json(output_dir / "aggregate.json", aggregate)
    write_json(output_dir / "lifecycle.json", {"status": "terminal", "completed_at": now(), "model_calls_made": True, "supplier_model_calls": 16, "teacher_calls": 0, "retries": 0, "escalations": 0})
    print(json.dumps({"status": "terminal", "output_dir": str(output_dir), "tasks": 16, "model_calls": 16}, indent=2))


def pct(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def build_aggregate(rows: list[dict[str, Any]], idle_summary: dict[str, Any]) -> dict[str, Any]:
    true_rows = [row for row in rows if row["expected_scope_expansion_required"] is True]
    false_rows = [row for row in rows if row["expected_scope_expansion_required"] is False]
    observed_true = [row for row in rows if row["observed_scope_expansion_required"] is True]
    tp = sum(row["correct"] and row["expected_scope_expansion_required"] for row in rows)
    tn = sum(row["correct"] and not row["expected_scope_expansion_required"] for row in rows)
    fp = sum(row["expected_scope_expansion_required"] is False and row["observed_scope_expansion_required"] is True for row in rows)
    fn = sum(row["expected_scope_expansion_required"] is True and row["observed_scope_expansion_required"] is False for row in rows)
    latencies = [row["wall_elapsed_ms"] for row in rows]
    energies = [row["power_summary"]["gross_energy_joules"] for row in rows]
    ordered = sorted(latencies)
    p95 = ordered[min(len(ordered) - 1, round((len(ordered) - 1) * 0.95))]
    return {
        "schema": "zth_qwen3_0_6b_clean_scope_logic_probe_aggregate_v1",
        "exploratory_not_confirmatory": True,
        "candidate": {"model_id": EXPECTED_MODEL_ID, "operative_parameters": EXPECTED_PARAMS, "artifact_sha256": EXPECTED_MODEL_SHA},
        "task_count": len(rows),
        "branch_results": {"true": {"tasks": len(true_rows), "correct": sum(row["correct"] for row in true_rows), "accuracy": pct(sum(row["correct"] for row in true_rows), len(true_rows))}, "false": {"tasks": len(false_rows), "correct": sum(row["correct"] for row in false_rows), "accuracy": pct(sum(row["correct"] for row in false_rows), len(false_rows))}},
        "confusion_matrix": {"expected_true_observed_true": tp, "expected_true_observed_false": fn, "expected_false_observed_true": fp, "expected_false_observed_false": tn},
        "overall_accuracy": pct(sum(row["correct"] for row in rows), len(rows)),
        "true_precision": pct(tp, tp + fp),
        "true_recall": pct(tp, tp + fn),
        "true_f1": pct(2 * tp, 2 * tp + fp + fn),
        "false_positive_rate": pct(fp, len(false_rows)),
        "false_negative_rate": pct(fn, len(true_rows)),
        "serialization_failures": sum(row["failure_class"] == "SERIALIZATION_FAILURE" for row in rows),
        "invalid_contract_failures": sum(row["failure_class"] == "INVALID_CONTRACT" for row in rows),
        "scope_decision_failures": sum(row["failure_class"] == "SCOPE_DECISION_FAILURE" for row in rows),
        "latency_ms": {"metric": "candidate_action_wall_clock", "median": round(statistics.median(latencies), 3), "mean": round(statistics.mean(latencies), 3), "p95": round(p95, 3)},
        "energy": {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "gpu_uuid": EXPECTED_GPU_UUID, "gross_joules_per_action_mean": round(statistics.mean(energies), 6), "gross_joules_per_action_median": round(statistics.median(energies), 6), "gross_joules_total": round(sum(energies), 6), "gross_joules_per_validated_task": None},
        "idle_power": idle_summary,
        "execution": {"supplier_model_calls": 16, "teacher_calls": 0, "retries": 0, "escalations": 0},
        "historical_comparison": "historical scope evidence remains materially confounded and is not numerically merged",
    }


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
