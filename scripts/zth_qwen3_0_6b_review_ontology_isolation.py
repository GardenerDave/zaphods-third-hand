#!/usr/bin/env python3
"""Run the authorized exploratory Qwen3-0.6B review-token isolation."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import statistics
import subprocess
import time
from pathlib import Path

from local_harness.atomic_capability_press import score_scope_object
from local_harness.supervised_capability_loop import _validator_result
from scripts import zth_qwen3_0_6b_interface_disambiguation as prior
from scripts import zth_stage_a_qwen3_0_6b_screening as stage_a


ROOT = stage_a.ROOT
ORIGINAL_RUN = ROOT / ".work/model_size_supplier_floor/qwen3_0_6b_interface_disambiguation/run_20260820T181000Z"
ORIGINAL_MANIFEST_SHA = "5cbb191ca44318bb105980be489d9f9fda49c934ce601463a81cb73cc4b72f49"
ORIGINAL_AGGREGATE_SHA = "3d4807e5079f079664333e23320f27c7fea9caac52be475aecb64777c4be68c7"
ORIGINAL_SUFFIX_SHA = "8386cb934c15b3a07b6a668075961c505a2c5ecd2d57980a5509c885c67ff4bc"
EXPECTED_HEAD = "26b16f200573cdfbd10fab6589539344f851d559"
EXPECTED_RUNTIME_SHA = stage_a.EXPECTED_RUNTIME_SHA
EXPECTED_MODEL_SHA = stage_a.EXPECTED_MODEL_SHA
EXPECTED_MODEL_ID = stage_a.EXPECTED_MODEL_ID
EXPECTED_GPU_UUID = stage_a.EXPECTED_GPU_UUID
POWER_INTERVAL_SECONDS = stage_a.POWER_INTERVAL_SECONDS
IDLE_SECONDS = stage_a.IDLE_SECONDS
MAX_OUTPUT_TOKENS = stage_a.MAX_OUTPUT_TOKENS
TIMEOUT_SECONDS = stage_a.TIMEOUT_SECONDS
ORIGINAL_SUFFIX = prior.EXPLICIT_INTERFACE_SUFFIX

_old_review_line = "- review_status must be a JSON string.\n"
_new_review_lines = (
    "- review_status must be a JSON string.\n"
    "- For this task family, the valid review_status protocol value is:\n"
    "  \"ready_for_review\"\n"
    "- Use \"ready_for_review\" when the bounded result is ready to be returned for review.\n"
    "- Do not invent alternative status labels.\n"
)
if ORIGINAL_SUFFIX.count(_old_review_line) != 1:
    raise RuntimeError("original review-status line is not uniquely bound")
NEW_SUFFIX = ORIGINAL_SUFFIX.replace(_old_review_line, _new_review_lines)
PROMPT_DIFF = "".join(difflib.unified_diff(
    ORIGINAL_SUFFIX.splitlines(keepends=True),
    NEW_SUFFIX.splitlines(keepends=True),
    fromfile="original_explicit_interface_suffix",
    tofile="corrected_review_ontology_suffix",
))


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def prompt_for(task: dict) -> str:
    return task["prompt"].rstrip() + "\n\n" + NEW_SUFFIX


def fixture_records() -> list[dict]:
    records = prior.task_records()
    if [r["task_id"] for r in records] != stage_a.TASK_IDS:
        raise RuntimeError("frozen task order mismatch")
    return records


def telemetry_url() -> str:
    value = os.environ.get("ZTH_GPU_TELEMETRY_BASE_URL")
    if not value:
        raise RuntimeError("ZTH_GPU_TELEMETRY_BASE_URL is unset")
    return value


def preflight(spec, records: list[dict], runtime: dict) -> dict:
    if subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip() != EXPECTED_HEAD:
        raise RuntimeError("wrong execution commit")
    if sha_file(stage_a.RUNTIME_FREEZE) != EXPECTED_RUNTIME_SHA:
        raise RuntimeError("runtime freeze hash mismatch")
    if sha_file(ORIGINAL_RUN / "screening_manifest.json") != ORIGINAL_MANIFEST_SHA:
        raise RuntimeError("original explicit-interface manifest changed")
    if sha_file(ORIGINAL_RUN / "aggregate.json") != ORIGINAL_AGGREGATE_SHA:
        raise RuntimeError("original explicit-interface aggregate changed")
    if sha_bytes(ORIGINAL_SUFFIX.encode()) != ORIGINAL_SUFFIX_SHA:
        raise RuntimeError("original suffix hash mismatch")
    model_data = stage_a.non_generative_preflight(spec)
    telemetry = stage_a.telemetry_preflight(telemetry_url())
    if telemetry["gpu_uuid"] != EXPECTED_GPU_UUID or telemetry["measurement_level"] != 2 or telemetry["measurement_boundary"] != "gpu_device_only":
        raise RuntimeError("telemetry binding mismatch")
    old_manifest = json.loads((ORIGINAL_RUN / "screening_manifest.json").read_text(encoding="utf-8"))
    if old_manifest["selection"]["task_order"] != [r["task_id"] for r in records]:
        raise RuntimeError("original task order mismatch")
    for record in records:
        old_task = json.loads((ORIGINAL_RUN / "tasks" / record["task_id"] / "fixture.snapshot.json").read_text(encoding="utf-8"))
        if old_task["task_id"] != record["task_id"]:
            raise RuntimeError("original fixture task mismatch")
        if old_task != record["task"]:
            raise RuntimeError(f"original fixture bytes differ for {record['task_id']}")
        old_prompt = (ORIGINAL_RUN / "tasks" / record["task_id"] / "prompt.txt").read_text(encoding="utf-8")
        if old_prompt != prior.prompt_for(record["task"]):
            raise RuntimeError(f"original prompt differs for {record['task_id']}")
    return {
        "model_endpoint": model_data,
        "telemetry": telemetry,
        "original_manifest_sha256": ORIGINAL_MANIFEST_SHA,
        "original_aggregate_sha256": ORIGINAL_AGGREGATE_SHA,
        "original_suffix_sha256": ORIGINAL_SUFFIX_SHA,
        "corrected_suffix_sha256": sha_bytes(NEW_SUFFIX.encode()),
        "prompt_diff_sha256": sha_bytes(PROMPT_DIFF.encode()),
        "model_calls": 0,
        "public_telemetry_alias": os.environ.get("ZTH_GPU_TELEMETRY_PUBLIC_ALIAS", "JARVIS_LOCAL"),
    }


def score_row(task: dict, raw_content: str, validation: dict | None, metadata: dict, elapsed_ms: float, power_summary: dict | None) -> dict:
    parse_valid = False
    obj = None
    try:
        obj = json.loads(raw_content)
        parse_valid = True
    except json.JSONDecodeError:
        pass
    atomic = score_scope_object(obj, task["validator"]["reference_facts"])
    return {
        "schema": "zth_qwen3_0_6b_review_ontology_isolation_task_v1",
        "task_id": task["task_id"],
        "transport_valid": metadata.get("transport_classification") == "model_response",
        "raw_parse_valid": parse_valid,
        "raw_contract_valid": atomic["structural_contract_valid"],
        "reference_fact_valid": validation is not None and not any(c.get("status") == "failed" for c in validation.get("semantic_checks", [])),
        "full_validator_valid": validation is not None and validation.get("validation_status") == "passed",
        "atomic": atomic,
        "validation_failed_checks": [c.get("check_id") for c in (validation or {}).get("checks", []) if c.get("status") == "failed"],
        "wall_elapsed_ms": elapsed_ms,
        "prompt_tokens": (metadata.get("usage") or {}).get("prompt_tokens"),
        "completion_tokens": (metadata.get("usage") or {}).get("completion_tokens"),
        "total_tokens": (metadata.get("usage") or {}).get("total_tokens"),
        "power_summary": power_summary,
        "raw_response_preserved": True,
    }


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, int(round((len(ordered) - 1) * fraction)))], 3)


def aggregate(rows: list[dict], idle: dict) -> dict:
    latencies = [r["wall_elapsed_ms"] for r in rows]
    energies = [r["power_summary"]["gross_energy_joules"] for r in rows if r["power_summary"]]
    reference = lambda r: r["atomic"]
    false_branch = [r for r in rows if not reference(r)["scope_expansion"]["expected"]]
    true_branch = [r for r in rows if reference(r)["scope_expansion"]["expected"]]
    return {
        "schema": "zth_qwen3_0_6b_review_ontology_isolation_aggregate_v1",
        "screening_only_not_confirmatory": True,
        "protocol_compliance_isolation": True,
        "candidate": EXPECTED_MODEL_ID,
        "operative_supplier_parameter_count": 596049920,
        "tasks": len(rows),
        "transport_valid": sum(r["transport_valid"] for r in rows),
        "raw_parse_valid": sum(r["raw_parse_valid"] for r in rows),
        "raw_contract_valid": sum(r["raw_contract_valid"] for r in rows),
        "reference_fact_valid": sum(r["reference_fact_valid"] for r in rows),
        "full_validator_passes": sum(r["full_validator_valid"] for r in rows),
        "review_status_exact": sum(r["atomic"]["review_status"]["exact_match"] is True for r in rows),
        "allowed_targets_exact": sum(r["atomic"]["allowed_targets"]["exact_set_match"] for r in rows),
        "held_targets_exact": sum(r["atomic"]["held_targets"]["exact_set_match"] for r in rows),
        "authority_separation_observed_and_correct": sum(r["atomic"]["authority_separation"]["observability"] == "OBSERVED_AND_CORRECT" for r in rows),
        "scope_expansion": {
            "correct": sum(r["atomic"]["scope_expansion"]["correct"] is True for r in rows),
            "false_positive": sum(r["atomic"]["scope_expansion"]["false_positive"] for r in rows),
            "false_negative": sum(r["atomic"]["scope_expansion"]["false_negative"] for r in rows),
            "true_branch": {"tasks": len(true_branch), "correct": sum(r["atomic"]["scope_expansion"]["correct"] is True for r in true_branch)},
            "false_branch": {"tasks": len(false_branch), "correct": sum(r["atomic"]["scope_expansion"]["correct"] is True for r in false_branch)},
        },
        "semantic_fields_correct_distribution": {str(i): sum(r["atomic"]["semantic_fields_correct"] == i for r in rows) for i in range(5)},
        "three_of_four_tasks": [r["task_id"] for r in rows if r["atomic"]["semantic_fields_correct"] == 3],
        "latency_ms": {"metric": "candidate_action_wall_clock", "median": round(statistics.median(latencies), 3), "mean": round(statistics.mean(latencies), 3), "p95": percentile(latencies, .95)},
        "energy": {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "gross_joules_per_action_mean": round(statistics.mean(energies), 6) if energies else None, "gross_joules_per_action_median": round(statistics.median(energies), 6) if energies else None, "gross_joules_per_validated_task": round(sum(energies) / sum(r["full_validator_valid"] for r in rows), 6) if energies and any(r["full_validator_valid"] for r in rows) else None},
        "idle_power": idle,
        "execution": {"supplier_model_calls": len(rows), "teacher_calls": 0, "retry_count": 0, "escalation_count": 0},
        "historical_runs_changed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--execute", action="store_true", required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError("output directory must be fresh")
    runtime = stage_a.runtime_payload()
    stage_a.candidate_path(runtime)
    records = fixture_records()
    spec = stage_a.worker_spec()
    binding = preflight(spec, records, runtime)
    url = telemetry_url()
    idle_samples, idle_summary = stage_a.sample_window(IDLE_SECONDS, base_url=url)
    output.mkdir(parents=True, exist_ok=True)
    tasks_manifest = []
    for record in records:
        task = record["task"]
        task_dir = output / "tasks" / task["task_id"]
        task_dir.mkdir(parents=True, exist_ok=True)
        prompt = prompt_for(task)
        (task_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
        stage_a.write_json(task_dir / "fixture.snapshot.json", task)
        tasks_manifest.append({"task_id": task["task_id"], "source_path": record["source_path"], "source_sha256": record["source_sha256"], "prompt_sha256": sha_bytes(prompt.encode())})
    manifest = {
        "schema": "zth_qwen3_0_6b_review_ontology_isolation_manifest_v1",
        "screening_only_not_confirmatory": True,
        "protocol_compliance_isolation": True,
        "execution_commit": EXPECTED_HEAD,
        "driver": str(Path(__file__).resolve().relative_to(ROOT)),
        "driver_sha256": sha_file(Path(__file__).resolve()),
        "runtime_freeze_path": str(stage_a.RUNTIME_FREEZE.relative_to(ROOT)),
        "runtime_freeze_sha256": EXPECTED_RUNTIME_SHA,
        "candidate": {"model_id": EXPECTED_MODEL_ID, "artifact_sha256": EXPECTED_MODEL_SHA, "operative_supplier_parameter_count": 596049920},
        "original_explicit_interface_run": {"directory": str(ORIGINAL_RUN.relative_to(ROOT)), "manifest_sha256": ORIGINAL_MANIFEST_SHA, "aggregate_sha256": ORIGINAL_AGGREGATE_SHA},
        "prompt_interface": {"original_suffix_sha256": ORIGINAL_SUFFIX_SHA, "corrected_suffix_sha256": sha_bytes(NEW_SUFFIX.encode()), "diff_sha256": sha_bytes(PROMPT_DIFF.encode()), "diff": PROMPT_DIFF, "review_status_protocol_explicit": "ready_for_review", "all_tasks_expect_same_token": True},
        "selection": {"task_order": [r["task_id"] for r in records], "task_count": 12, "same_as_explicit_interface_screen": True, "fixture_bytes_unchanged": True},
        "runtime": runtime["runtime"],
        "telemetry": {"public_alias": binding["public_telemetry_alias"], "gpu_uuid": EXPECTED_GPU_UUID, "sample_interval_seconds": POWER_INTERVAL_SECONDS, "measurement_level": 2, "measurement_boundary": "gpu_device_only"},
        "execution": {"supplier_model_calls": 12, "teacher_calls": 0, "retry_count": 0, "escalation_count": 0},
        "preflight": binding,
        "tasks": tasks_manifest,
    }
    manifest["manifest_sha256"] = sha_bytes(json.dumps({**manifest, "manifest_sha256": None}, sort_keys=True, separators=(",", ":")).encode())
    stage_a.write_json(output / "screening_manifest.json", manifest)
    stage_a.write_json(output / "preflight.json", {"model_calls": 0, "binding": binding})
    stage_a.write_json(output / "idle_power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "samples": idle_samples, "summary": idle_summary})
    stage_a.write_json(output / "lifecycle.json", {"status": "isolation_running", "model_calls": 0})
    rows = []
    for record in records:
        task = record["task"]
        task_dir = output / "tasks" / task["task_id"]
        prompt = (task_dir / "prompt.txt").read_text(encoding="utf-8")
        sampler = stage_a.PowerSampler(lambda: stage_a.read_gpu_power(EXPECTED_GPU_UUID, base_url=url), expected_gpu_uuid=EXPECTED_GPU_UUID, sample_interval_seconds=POWER_INTERVAL_SECONDS)
        started = time.monotonic(); started_at = stage_a.now(); sampler.start()
        response = stage_a.call_worker(spec, prompt, MAX_OUTPUT_TOKENS, timeout=TIMEOUT_SECONDS)
        elapsed = round((time.monotonic() - started) * 1000, 3)
        samples = sampler.stop()
        metadata = response.metadata(); metadata["request_url"] = None; metadata["public_endpoint_alias"] = binding["public_telemetry_alias"]
        validation = _validator_result(response.content, task, attempt_id=f"qwen3-0.6b-review-ontology-{task['task_id']}") if metadata.get("transport_classification") == "model_response" else None
        stage_a.write_json(task_dir / "response.json", {"status": response.status, "content": response.content, "metadata": metadata, "request_started_at": started_at, "response_captured_at": stage_a.now(), "wall_elapsed_ms": elapsed})
        if validation is not None: stage_a.write_json(task_dir / "validation.json", validation)
        stage_a.write_json(task_dir / "power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "gpu_uuid": EXPECTED_GPU_UUID, "samples": [{"timestamp_utc": s.timestamp_utc, "monotonic_seconds": s.monotonic_seconds, "gpu_uuid": s.gpu_uuid, "power_watts": s.power_watts, "sequence": s.sequence} for s in samples]})
        powers = [s.power_watts for s in samples]
        power_summary = {"sample_count": len(samples), "sample_interval_seconds": POWER_INTERVAL_SECONDS, "mean_active_watts": round(statistics.mean(powers), 6), "peak_observed_watts": round(max(powers), 6), "gross_energy_joules": stage_a.integrate_energy_joules(samples, sample_interval_seconds=POWER_INTERVAL_SECONDS, expected_gpu_uuid=EXPECTED_GPU_UUID)}
        row = score_row(task, response.content, validation, metadata, elapsed, power_summary)
        stage_a.write_json(task_dir / "atomic_scorecard.json", row)
        rows.append(row)
    stage_a.write_json(output / "aggregate.json", aggregate(rows, idle_summary))
    stage_a.write_json(output / "lifecycle.json", {"status": "isolation_terminal", "completed_at": stage_a.now(), "model_calls": 12, "supplier_model_calls": 12, "teacher_calls": 0, "retries": 0, "escalations": 0})
    print(json.dumps({"status": "isolation_terminal", "output_dir": str(output), "model_calls": 12, "teacher_calls": 0, "retries": 0, "escalations": 0}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
