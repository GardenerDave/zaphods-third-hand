#!/usr/bin/env python3
"""Bounded, exploratory, candidate-only Qwen3-0.6B Stage A screening."""

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
from local_harness.supervised_capability_loop import _validator_result, load_task_fixture


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FREEZE = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_0_6B_STAGE_A_RUNTIME_FREEZE_2026-08-20.json"
TASK_ROOT = ROOT / "local_harness/fixtures/capability_loop/run7_scope"
TASK_IDS = [f"run7-scope-{index:03d}" for index in range(1, 13)]
EXPECTED_HEAD = "16c29e856d6145d720e510042d3719ccf05d8530"
EXPECTED_RUNTIME_SHA = "ad852445d582e5adb7d4cd13b4b12951838e46d6cdf16582aa2c9097c34724aa"
EXPECTED_MODEL_SHA = "b0638f08417a2d3c8652760462eb5407c6e30173cf9608ad0820757a281eea0e"
EXPECTED_MODEL_ID = "Qwen3-0.6B-Q4_K_M.gguf"
EXPECTED_GPU_UUID = "GPU-c2823a81-56f1-b16e-f9cc-34f4dc58eb85"
EXPECTED_CTX = 40960
MAX_OUTPUT_TOKENS = 768
TIMEOUT_SECONDS = 900
POWER_INTERVAL_SECONDS = 0.25
IDLE_SECONDS = 30


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
    payload = json.loads(RUNTIME_FREEZE.read_text(encoding="utf-8"))
    if sha256_file(RUNTIME_FREEZE) != EXPECTED_RUNTIME_SHA:
        raise RuntimeError("runtime-freeze hash mismatch")
    candidate = payload["candidate"]
    if candidate["sha256"] != EXPECTED_MODEL_SHA or candidate["filename"] != EXPECTED_MODEL_ID:
        raise RuntimeError("candidate artifact binding mismatch")
    return payload


def candidate_path(runtime: dict[str, Any]) -> Path | None:
    path = Path(runtime["candidate"]["local_path"])
    if not path.exists():
        # The frozen artifact was independently SHA-verified after placement
        # on the serving host.  This workspace may not mount that host's model
        # directory; the non-generative /v1/models identity check below still
        # binds the running server to the frozen artifact identity.
        if runtime["candidate"].get("sha_verified_after_final_placement") is True:
            return None
        raise RuntimeError("frozen candidate artifact is not present")
    if path.stat().st_size != runtime["candidate"]["size_bytes"]:
        raise RuntimeError("candidate artifact byte size mismatch")
    if sha256_file(path) != runtime["candidate"]["sha256"]:
        raise RuntimeError("candidate artifact SHA256 mismatch")
    return path


def task_records() -> list[dict[str, Any]]:
    records = []
    for task_id in TASK_IDS:
        path = TASK_ROOT / f"{task_id.replace('run7-', '')}.json"
        if not path.exists():
            raise RuntimeError(f"frozen screening task missing: {path}")
        task = load_task_fixture(path)
        if task["task_id"] != task_id or task["task_family"] != "scope-authority-boundary":
            raise RuntimeError(f"task binding mismatch: {task_id}")
        records.append({
            "task_id": task_id,
            "source_path": str(path.relative_to(ROOT)),
            "source_sha256": sha256_file(path),
            "task": task,
        })
    return records


def prompt_for(task: dict[str, Any]) -> str:
    contract = task["output_contract"]
    return (
        task["prompt"].rstrip()
        + "\n\nReturn only one JSON object with exactly these fields and no markdown: "
        + json.dumps(contract["required_fields"], separators=(",", ":"))
        + ". Use the required JSON types. Do not include reasoning or commentary. /no_think"
    )


def worker_spec():
    name = os.environ.get("ZTH_CAPABILITY_WORKER_NAME", "router")
    return resolve_worker_spec(
        name,
        base_url=os.environ.get("ZTH_CAPABILITY_WORKER_BASE_URL"),
        model=os.environ.get("ZTH_CAPABILITY_WORKER_MODEL"),
    )


def non_generative_preflight(spec) -> dict[str, Any]:
    models = list_models(spec, timeout=30)
    ids = [row.get("id") for row in models.get("data", [])] if isinstance(models, dict) else []
    if EXPECTED_MODEL_ID not in ids:
        raise RuntimeError("candidate model is not exposed by the frozen worker endpoint")
    return {"model_ids": ids, "candidate_exposed": True, "endpoint_alias": os.environ.get("ZTH_PUBLIC_HOST_ALIAS", "JARVIS_LOCAL")}


def exclusivity_record() -> dict[str, Any]:
    return {
        "gpu_uuid": EXPECTED_GPU_UUID,
        "candidate_runtime_manually_verified_immediately_before_screening": True,
        "reference_1_7b_unloaded_from_gpu": True,
        "process_level_remote_exclusivity_verified": False,
        "process_level_remote_exclusivity_limitation": "not_available_in_telemetry_endpoint_v1",
        "telemetry_identity_continuously_verified": True,
        "exclusive": None,
    }


def telemetry_base_url() -> str:
    value = os.environ.get("ZTH_GPU_TELEMETRY_BASE_URL")
    if not value:
        raise RuntimeError("ZTH_GPU_TELEMETRY_BASE_URL is unset")
    return value


def telemetry_preflight(base_url: str) -> dict[str, Any]:
    health = remote_health(base_url=base_url)
    reading = read_gpu_power(EXPECTED_GPU_UUID, base_url=base_url)
    return {
        "public_alias": os.environ.get("ZTH_GPU_TELEMETRY_PUBLIC_ALIAS", "UNSET"),
        "health_received": isinstance(health, dict),
        "gpu_uuid": reading.gpu_uuid,
        "measurement_level": 2,
        "measurement_boundary": "gpu_device_only",
        "process_level_remote_exclusivity_verified": False,
    }


def sample_window(seconds: int, *, base_url: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
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
    serial = [
        {
            "timestamp_utc": sample.timestamp_utc,
            "monotonic_seconds": sample.monotonic_seconds,
            "gpu_uuid": sample.gpu_uuid,
            "power_watts": sample.power_watts,
            "sequence": sample.sequence,
        }
        for sample in samples
    ]
    return serial, {
        "sample_interval_seconds": POWER_INTERVAL_SECONDS,
        "requested_seconds": seconds,
        "observed_elapsed_seconds": round(elapsed, 6),
        "sample_count": len(samples),
        "gpu_uuid": EXPECTED_GPU_UUID,
        "mean_power_watts": round(statistics.mean(sample.power_watts for sample in samples), 6),
        "peak_power_watts": round(max(sample.power_watts for sample in samples), 6),
        "gross_energy_joules": integrate_energy_joules(
            samples,
            sample_interval_seconds=POWER_INTERVAL_SECONDS,
            expected_gpu_uuid=EXPECTED_GPU_UUID,
        ),
    }


def prepare(output_dir: Path) -> None:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError("Stage A output directory must be fresh")
    output_dir.mkdir(parents=True, exist_ok=True)
    runtime = runtime_payload()
    artifact = candidate_path(runtime)
    tasks = task_records()
    script_path = Path(__file__).resolve()
    task_manifest = []
    for record in tasks:
        task_dir = output_dir / "tasks" / record["task_id"]
        task_dir.mkdir(parents=True, exist_ok=True)
        write_json(task_dir / "fixture.snapshot.json", record["task"])
        prompt = prompt_for(record["task"])
        (task_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
        task_manifest.append({
            "task_id": record["task_id"],
            "source_path": record["source_path"],
            "source_sha256": record["source_sha256"],
            "prompt_sha256": sha256_bytes(prompt.encode()),
            "output_contract": record["task"]["output_contract"],
            "validator": record["task"]["validator"],
        })
    manifest = {
        "schema": "zth_qwen3_0_6b_stage_a_screening_manifest_v1",
        "screening_only_not_confirmatory": True,
        "prepared_at": now(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "expected_git_head": EXPECTED_HEAD,
        "driver": str(script_path.relative_to(ROOT)),
        "driver_sha256": sha256_file(script_path),
        "runtime_freeze_path": str(RUNTIME_FREEZE.relative_to(ROOT)),
        "runtime_freeze_sha256": sha256_file(RUNTIME_FREEZE),
        "candidate": {
            "model_id": EXPECTED_MODEL_ID,
            "model_sha256": runtime["candidate"]["sha256"],
            "model_size_bytes": artifact.stat().st_size if artifact is not None else runtime["candidate"]["size_bytes"],
            "artifact_visibility": "workspace_verified" if artifact is not None else "serving_host_verified_workspace_not_mounted",
            "parameters": runtime["model_metadata_exposed_by_llama_cpp"]["n_params"],
            "quantization": runtime["candidate"]["quantization"],
        },
        "reference": {
            "model_id": runtime["reference_1_7b"]["model_identity"],
            "sha256": runtime["reference_1_7b"]["sha256"],
            "same_hardware_required": True,
            "exclusive_gpu_required": True,
        },
        "runtime": {
            "llama_cpp_version": runtime["runtime"]["llama_cpp_version"],
            "build_revision": runtime["runtime"]["build_revision"],
            "binary": runtime["runtime"]["binary"],
            "context": EXPECTED_CTX,
            "reasoning": "off",
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "timeout_seconds": TIMEOUT_SECONDS,
            "retry_count": 0,
            "prompt_form": "fixture_prompt_plus_frozen_json_only_contract_suffix_and_no_think",
        },
        "telemetry": {
            "power_level": 2,
            "measurement_boundary": "GTX_1650_device_only",
            "gpu_uuid": EXPECTED_GPU_UUID,
            "sample_interval_seconds": POWER_INTERVAL_SECONDS,
            "energy_formula": "sum(power_watts * sample_interval_seconds)",
            "gross_energy_retained": True,
            "idle_baseline_seconds": IDLE_SECONDS,
        },
        "selection": {
            "task_family": "scope-authority-boundary",
            "task_order": [record["task_id"] for record in tasks],
            "selection_basis": "frozen_existing_screening_set; no candidate outputs consulted",
            "outcome_based_replacement": False,
        },
        "tasks": task_manifest,
        "model_calls_made": False,
    }
    manifest["manifest_sha256"] = sha256_bytes(canonical({**manifest, "manifest_sha256": None}))
    write_json(output_dir / "screening_manifest.json", manifest)
    write_json(output_dir / "lifecycle.json", {"status": "prepared", "model_calls_made": False, "updated_at": now()})
    print(json.dumps({"status": "prepared", "output_dir": str(output_dir), "task_count": len(tasks), "model_calls": 0}, indent=2))


def rebind_telemetry_manifest(output_dir: Path) -> None:
    """Rebind only the prepared manifest to this model-free transport repair."""
    manifest_path = output_dir / "screening_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if manifest["git_head"] != EXPECTED_HEAD or manifest["expected_git_head"] != EXPECTED_HEAD:
        raise RuntimeError("screening must remain bound to the authoritative repository commit")
    manifest["driver_sha256"] = sha256_file(Path(__file__).resolve())
    manifest["telemetry"]["transport"] = "remote_read_only_http"
    manifest["telemetry"]["public_alias"] = os.environ.get("ZTH_GPU_TELEMETRY_PUBLIC_ALIAS", "UNSET")
    manifest["gpu_exclusivity"] = {
        "candidate_runtime_manually_verified_immediately_before_screening": True,
        "reference_1_7b_unloaded_from_gpu": True,
        "process_level_remote_exclusivity_verified": False,
        "limitation": "not_available_in_telemetry_endpoint_v1",
    }
    manifest["binding_update_reason"] = "remote telemetry transport repair before any scientific model call"
    manifest["manifest_sha256"] = sha256_bytes(canonical({**manifest, "manifest_sha256": None}))
    write_json(manifest_path, manifest)
    print(json.dumps({"status": "manifest_rebound_model_free", "driver_sha256": manifest["driver_sha256"], "model_calls": 0}, indent=2))


def classify_validation(validation: dict[str, Any] | None) -> dict[str, Any]:
    if validation is None:
        return {"parse_valid": False, "contract_valid": False, "reference_fact_valid": False, "failure_classes": ["transport_or_missing_response"]}
    checks = validation.get("checks", [])
    structural = validation.get("structural_checks", checks)
    semantic = validation.get("semantic_checks", [])
    failed_ids = [str(check.get("check_id")) for check in checks if check.get("status") == "failed"]
    classes = []
    if any(check.get("check_id") == "json_parse" and check.get("status") == "failed" for check in checks):
        classes.append("parse_failure")
    if structural and any(check.get("status") == "failed" for check in structural):
        classes.append("contract_failure")
    if semantic and any(check.get("status") == "failed" for check in semantic):
        classes.append("reference_fact_failure")
    return {
        "parse_valid": any(check.get("check_id") == "parse_json" and check.get("status") == "passed" for check in checks),
        "contract_valid": bool(structural) and all(check.get("status") == "passed" for check in structural),
        "reference_fact_valid": bool(semantic) and all(check.get("status") == "passed" for check in semantic),
        "failure_classes": classes or ([] if validation.get("validation_status") == "passed" else ["deterministic_validation_failure"]),
        "failed_check_ids": failed_ids,
    }


def execute(output_dir: Path) -> None:
    manifest = json.loads((output_dir / "screening_manifest.json").read_text())
    if manifest["git_head"] != EXPECTED_HEAD or manifest["expected_git_head"] != EXPECTED_HEAD:
        raise RuntimeError("screening must run from the authoritative repository commit")
    if manifest["manifest_sha256"] != sha256_bytes(canonical({**manifest, "manifest_sha256": None})):
        raise RuntimeError("screening manifest hash mismatch")
    runtime = runtime_payload()
    artifact = candidate_path(runtime)
    spec = worker_spec()
    preflight = non_generative_preflight(spec)
    exclusive = exclusivity_record()
    telemetry_url = telemetry_base_url()
    telemetry = telemetry_preflight(telemetry_url)
    idle_samples, idle_summary = sample_window(IDLE_SECONDS, base_url=telemetry_url)
    write_json(output_dir / "preflight.json", {"non_generative_models": preflight, "gpu_exclusivity": exclusive, "telemetry": telemetry, "candidate_artifact_binding": {"source": "workspace_sha256" if artifact is not None else "immutable_runtime_freeze_and_serving_host_identity", "sha256": runtime["candidate"]["sha256"], "size_bytes": runtime["candidate"]["size_bytes"]}, "runtime_freeze_sha256": sha256_file(RUNTIME_FREEZE), "model_calls": 0})
    write_json(output_dir / "idle_power_samples.json", {"schema": "zth_stage_a_idle_power_v1", "measurement_level": 2, "measurement_boundary": "GTX_1650_device_only", "summary": idle_summary, "samples": idle_samples})
    write_json(output_dir / "lifecycle.json", {"status": "screening_running", "started_at": now(), "model_calls_made": False})
    task_summaries = []
    for task_id in manifest["selection"]["task_order"]:
        task_dir = output_dir / "tasks" / task_id
        scorecard_path = task_dir / "scorecard.json"
        if scorecard_path.exists():
            task_summaries.append(json.loads(scorecard_path.read_text()))
            continue
        exclusive = exclusivity_record()
        task = json.loads((task_dir / "fixture.snapshot.json").read_text())
        prompt = (task_dir / "prompt.txt").read_text()
        sampler = PowerSampler(lambda: read_gpu_power(EXPECTED_GPU_UUID, base_url=telemetry_url), expected_gpu_uuid=EXPECTED_GPU_UUID, sample_interval_seconds=POWER_INTERVAL_SECONDS)
        request_started = time.monotonic()
        request_started_at = now()
        sampler.start()
        response = call_worker(spec, prompt, MAX_OUTPUT_TOKENS, timeout=TIMEOUT_SECONDS)
        response_captured = time.monotonic()
        telemetry_error = None
        try:
            samples = sampler.stop()
            power_samples = [{"timestamp_utc": sample.timestamp_utc, "monotonic_seconds": sample.monotonic_seconds, "gpu_uuid": sample.gpu_uuid, "power_watts": sample.power_watts, "sequence": sample.sequence} for sample in samples]
            energy = integrate_energy_joules(samples, sample_interval_seconds=POWER_INTERVAL_SECONDS, expected_gpu_uuid=EXPECTED_GPU_UUID)
            power_summary = {"sample_count": len(samples), "mean_active_watts": round(statistics.mean(sample.power_watts for sample in samples), 6), "peak_observed_watts": round(max(sample.power_watts for sample in samples), 6), "gross_energy_joules": energy, "sample_interval_seconds": POWER_INTERVAL_SECONDS}
        except PowerTelemetryError as exc:
            power_samples = []
            power_summary = None
            telemetry_error = str(exc)
        metadata = response.metadata()
        metadata["request_url"] = None
        raw = {"status": response.status, "content": response.content, "metadata": metadata, "request_started_at": request_started_at, "response_captured_at": now(), "wall_elapsed_ms": round((response_captured - request_started) * 1000, 3)}
        write_json(task_dir / "response.json", raw)
        transport_classification = metadata.get("transport_classification")
        validation = _validator_result(response.content, task, attempt_id=f"stage-a-{task_id}") if transport_classification == "model_response" else None
        if validation is not None:
            write_json(task_dir / "validation.json", validation)
        write_json(task_dir / "power_samples.json", {"schema": "zth_stage_a_power_samples_v1", "measurement_level": 2, "measurement_boundary": "GTX_1650_device_only", "gpu_uuid": EXPECTED_GPU_UUID, "samples": power_samples, "error": telemetry_error})
        quality = classify_validation(validation)
        scorecard = {
            "schema": "zth_qwen3_0_6b_stage_a_task_scorecard_v1",
            "task_id": task_id,
            "candidate": EXPECTED_MODEL_ID,
            "transport_valid": transport_classification == "model_response",
            "transport_classification": transport_classification,
            "parse_valid": quality["parse_valid"],
            "contract_valid": quality["contract_valid"],
            "reference_fact_valid": quality["reference_fact_valid"],
            "deterministic_validation_status": validation.get("validation_status") if validation else None,
            "validated_pass": bool(validation and validation.get("validation_status") == "passed"),
            "failure_classes": quality["failure_classes"],
            "failed_check_ids": quality["failed_check_ids"],
            "wall_elapsed_ms": raw["wall_elapsed_ms"],
            "prompt_tokens": (metadata.get("usage") or {}).get("prompt_tokens"),
            "completion_tokens": (metadata.get("usage") or {}).get("completion_tokens"),
            "total_tokens": (metadata.get("usage") or {}).get("total_tokens"),
            "server_prompt_ms": (metadata.get("timings") or {}).get("prompt_ms"),
            "server_generation_ms": (metadata.get("timings") or {}).get("predicted_ms"),
            "power_summary": power_summary,
            "telemetry_valid": telemetry_error is None,
            "telemetry_error": telemetry_error,
            "retry_count": 0,
            "escalation_count": 0,
            "exclusive_gpu": exclusive["exclusive"],
            "raw_response_preserved": True,
            "screening_only": True,
        }
        write_json(scorecard_path, scorecard)
        task_summaries.append(scorecard)
    aggregate = build_aggregate(output_dir, manifest, task_summaries, idle_summary)
    write_json(output_dir / "aggregate.json", aggregate)
    write_json(output_dir / "lifecycle.json", {"status": "screening_terminal", "completed_at": now(), "model_calls_made": True, "task_count": len(task_summaries)})
    print(json.dumps({"status": "screening_terminal", "output_dir": str(output_dir), "tasks": len(task_summaries), "model_calls": len(task_summaries)}, indent=2))


def build_aggregate(output_dir: Path, manifest: dict[str, Any], summaries: list[dict[str, Any]], idle_summary: dict[str, Any]) -> dict[str, Any]:
    latencies = [row["wall_elapsed_ms"] for row in summaries if row.get("wall_elapsed_ms") is not None]
    energies = [row["power_summary"]["gross_energy_joules"] for row in summaries if row.get("power_summary")]
    transport_valid = [row for row in summaries if row.get("transport_valid")]
    passes = [row for row in summaries if row.get("validated_pass")]
    contract_valid = [row for row in summaries if row.get("contract_valid")]
    failure_classes: dict[str, int] = {}
    for row in summaries:
        for failure_class in row.get("failure_classes", []):
            failure_classes[failure_class] = failure_classes.get(failure_class, 0) + 1
    def percentile(values: list[float], fraction: float) -> float | None:
        if not values:
            return None
        ordered = sorted(values)
        index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * fraction))))
        return round(ordered[index], 3)
    return {
        "schema": "zth_qwen3_0_6b_stage_a_screening_aggregate_v1",
        "screening_only_not_confirmatory": True,
        "candidate": EXPECTED_MODEL_ID,
        "parameters": 596049920,
        "task_count": len(summaries),
        "transport_valid_responses": len(transport_valid),
        "parse_valid_responses": sum(row.get("parse_valid", False) for row in summaries),
        "contract_valid_responses": len(contract_valid),
        "reference_fact_valid_responses": sum(row.get("reference_fact_valid", False) for row in summaries),
        "validated_passes": len(passes),
        "deterministic_failures": len(summaries) - len(passes),
        "pass_rate": len(passes) / len(summaries) if summaries else None,
        "failure_classes": failure_classes,
        "latency_ms": {"metric": "candidate_action_wall_clock", "median": round(statistics.median(latencies), 3) if latencies else None, "mean": round(statistics.mean(latencies), 3) if latencies else None, "p95": percentile(latencies, 0.95)},
        "tokens": {"prompt": [row.get("prompt_tokens") for row in summaries if row.get("prompt_tokens") is not None], "completion": [row.get("completion_tokens") for row in summaries if row.get("completion_tokens") is not None], "total": [row.get("total_tokens") for row in summaries if row.get("total_tokens") is not None]},
        "energy": {"measurement_level": 2, "measurement_boundary": "GTX_1650_device_only", "gpu_uuid": EXPECTED_GPU_UUID, "gross_joules_per_action_median": round(statistics.median(energies), 6) if energies else None, "gross_joules_per_action_mean": round(statistics.mean(energies), 6) if energies else None, "gross_joules_per_validated_task": round(sum(energies) / len(passes), 6) if energies and passes else None, "energy_break_even": "ENERGY_BREAK_EVEN_NOT_YET_AVAILABLE"},
        "idle_power": idle_summary,
        "telemetry_complete": len(energies) == len(summaries),
        "validator_caught_transport_valid_failures": all(row.get("deterministic_validation_status") == "failed" for row in transport_valid if not row.get("validated_pass")),
        "retry_count": 0,
        "escalation_count": 0,
        "screening_disposition": "PENDING_REVIEW",
        "model_calls_made": True,
        "historical_evidence_merged": False,
        "production_routing_changed": False,
    }


def finalize(output_dir: Path, disposition: str) -> None:
    if disposition not in {"PROMISING_FOR_STAGE_B", "NOT_PROMISING_AT_THIS_SIZE", "INCONCLUSIVE"}:
        raise ValueError("invalid Stage A disposition")
    aggregate_path = output_dir / "aggregate.json"
    aggregate = json.loads(aggregate_path.read_text())
    aggregate["screening_disposition"] = disposition
    aggregate["finalized_at"] = now()
    write_json(aggregate_path, aggregate)
    print(json.dumps({"status": "finalized", "disposition": disposition, "model_calls": 0}, indent=2))


def reaggregate(output_dir: Path) -> None:
    """Recompute only derived summaries from terminal validator artifacts."""
    manifest = json.loads((output_dir / "screening_manifest.json").read_text())
    prior_path = output_dir / "aggregate.json"
    prior = json.loads(prior_path.read_text())
    summaries = []
    for task_id in manifest["selection"]["task_order"]:
        task_dir = output_dir / "tasks" / task_id
        row = json.loads((task_dir / "scorecard.json").read_text())
        validation_path = task_dir / "validation.json"
        validation = json.loads(validation_path.read_text()) if validation_path.exists() else None
        quality = classify_validation(validation)
        row.update({
            "parse_valid": quality["parse_valid"],
            "contract_valid": quality["contract_valid"],
            "reference_fact_valid": quality["reference_fact_valid"],
            "failure_classes": quality["failure_classes"],
            "failed_check_ids": quality["failed_check_ids"],
        })
        summaries.append(row)
    idle_summary = json.loads((output_dir / "idle_power_samples.json").read_text())["summary"]
    aggregate = build_aggregate(output_dir, manifest, summaries, idle_summary)
    aggregate["pre_correction_aggregate_sha256"] = sha256_file(prior_path)
    aggregate["aggregation_correction"] = "derived parse-valid classification corrected from terminal validator check_id=parse_json; raw response and validation artifacts unchanged"
    write_json(prior_path, aggregate)
    print(json.dumps({"status": "derived_aggregate_recomputed", "model_calls": 0, "raw_artifacts_changed": False}, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--finalize", action="store_true")
    mode.add_argument("--rebind-telemetry", action="store_true")
    mode.add_argument("--reaggregate", action="store_true")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--disposition")
    args = parser.parse_args()
    if args.prepare:
        prepare(args.output_dir)
    elif args.execute:
        execute(args.output_dir)
    elif args.rebind_telemetry:
        rebind_telemetry_manifest(args.output_dir)
    elif args.reaggregate:
        reaggregate(args.output_dir)
    else:
        if not args.disposition:
            raise SystemExit("--finalize requires --disposition")
        finalize(args.output_dir, args.disposition)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
