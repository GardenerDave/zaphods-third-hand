#!/usr/bin/env python3
"""Exploratory Qwen3-0.6B interface-disambiguation screen."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from scripts import zth_stage_a_qwen3_0_6b_screening as stage_a


ROOT = stage_a.ROOT
EXPECTED_HEAD = "d01cd5a68e0f77ec5a141d66d3b21f9e3e1f9350"
TASK_IDS = stage_a.TASK_IDS
POWER_INTERVAL_SECONDS = stage_a.POWER_INTERVAL_SECONDS
IDLE_SECONDS = stage_a.IDLE_SECONDS
MAX_OUTPUT_TOKENS = stage_a.MAX_OUTPUT_TOKENS
TIMEOUT_SECONDS = stage_a.TIMEOUT_SECONDS
EXPECTED_GPU_UUID = stage_a.EXPECTED_GPU_UUID
EXPLICIT_INTERFACE_SUFFIX = '''Return ONLY a bare JSON object.
Do not use markdown or code fences.
Do not include reasoning, explanation, or commentary.

The JSON object must have exactly these fields and types:

{
  "allowed_targets": ["string"],
  "held_targets": ["string"],
  "scope_expansion_required": true,
  "review_status": "string"
}

Rules:

- allowed_targets must be a JSON array of strings.
- held_targets must be a JSON array of strings.
- scope_expansion_required must be a JSON boolean: true or false.
- review_status must be a JSON string.
- Use the task evidence to determine the values.
- Do not copy the example values unless they are correct.
- Return the object only.

/no_think'''


def prompt_for(task: dict) -> str:
    return task["prompt"].rstrip() + "\n\n" + EXPLICIT_INTERFACE_SUFFIX


def raw_quality(validation: dict | None) -> dict:
    if validation is None:
        return {"parse_valid": False, "contract_valid": False, "reference_valid": False, "fully_validated": False}
    checks = validation.get("checks", [])
    structural = validation.get("structural_checks", [])
    semantic = validation.get("semantic_checks", [])
    parse_valid = any(c.get("check_id") == "parse_json" and c.get("status") == "passed" for c in checks)
    # not_applicable is neutral: this screen does not supply a separate
    # authorized-target list, so it is not a structural contract failure.
    contract_valid = parse_valid and not any(c.get("status") == "failed" for c in structural)
    reference_valid = not any(c.get("status") == "failed" for c in semantic)
    fully_validated = validation.get("validation_status") == "passed"
    return {
        "parse_valid": parse_valid,
        "contract_valid": contract_valid,
        "reference_valid": reference_valid,
        "fully_validated": fully_validated,
    }


def task_records() -> list[dict]:
    return stage_a.task_records()


def prepare(output_dir: Path) -> None:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError("interface screen output directory must be fresh")
    output_dir.mkdir(parents=True, exist_ok=True)
    runtime = stage_a.runtime_payload()
    stage_a.candidate_path(runtime)
    records = task_records()
    task_manifest = []
    for record in records:
        task_dir = output_dir / "tasks" / record["task_id"]
        task_dir.mkdir(parents=True, exist_ok=True)
        stage_a.write_json(task_dir / "fixture.snapshot.json", record["task"])
        prompt = prompt_for(record["task"])
        (task_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
        task_manifest.append({
            "task_id": record["task_id"],
            "source_path": record["source_path"],
            "source_sha256": record["source_sha256"],
            "prompt_sha256": stage_a.sha256_bytes(prompt.encode()),
            "output_interface_variant": "explicit_typed_json_object_v1",
            "output_contract": record["task"]["output_contract"],
            "validator": record["task"]["validator"],
        })
    manifest = {
        "schema": "zth_qwen3_0_6b_interface_disambiguation_manifest_v1",
        "screening_only_not_confirmatory": True,
        "prepared_at": stage_a.now(),
        "git_head": __import__("subprocess").check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "expected_git_head": EXPECTED_HEAD,
        "driver": str(Path(__file__).resolve().relative_to(ROOT)),
        "driver_sha256": stage_a.sha256_file(Path(__file__).resolve()),
        "prior_stage_a_report_sha256": "51543cc07aa89922e86c554b669b8da689d151ace7f181f5f39cac3eb6eda14b",
        "forensic_report_sha256": "c3b95e43a9e9c5d68ca2f54f8920f02886bd8f0930561618ca1bf60bb57e361b",
        "runtime_freeze_path": str(stage_a.RUNTIME_FREEZE.relative_to(ROOT)),
        "runtime_freeze_sha256": stage_a.sha256_file(stage_a.RUNTIME_FREEZE),
        "candidate": {
            "model_id": stage_a.EXPECTED_MODEL_ID,
            "model_sha256": runtime["candidate"]["sha256"],
            "parameters": runtime["model_metadata_exposed_by_llama_cpp"]["n_params"],
            "quantization": runtime["candidate"]["quantization"],
        },
        "reference": {
            "model_id": runtime["reference_1_7b"]["model_identity"],
            "sha256": runtime["reference_1_7b"]["sha256"],
            "loaded_concurrently": False,
        },
        "runtime": {
            "llama_cpp_version": runtime["runtime"]["llama_cpp_version"],
            "context": stage_a.EXPECTED_CTX,
            "reasoning": "off",
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "timeout_seconds": TIMEOUT_SECONDS,
        },
        "selection": {
            "task_order": TASK_IDS,
            "task_count": len(TASK_IDS),
            "same_as_stage_a": True,
            "outcome_based_replacement": False,
        },
        "output_interface": {
            "suffix_sha256": stage_a.sha256_bytes(EXPLICIT_INTERFACE_SUFFIX.encode()),
            "suffix": EXPLICIT_INTERFACE_SUFFIX,
            "changed_variable": "output_interface_instruction_only",
        },
        "execution": {"retry_count": 0, "escalation_count": 0, "model_calls_made": False},
        "telemetry": {
            "transport": "remote_read_only_http",
            "public_alias": "bound_at_execution",
            "gpu_uuid": EXPECTED_GPU_UUID,
            "sample_interval_seconds": POWER_INTERVAL_SECONDS,
            "measurement_level": 2,
            "measurement_boundary": "GTX_1650_device_only",
        },
        "tasks": task_manifest,
        "raw_response_preserved": True,
        "historical_stage_a_modified": False,
    }
    manifest["manifest_sha256"] = stage_a.sha256_bytes(stage_a.canonical({**manifest, "manifest_sha256": None}))
    stage_a.write_json(output_dir / "screening_manifest.json", manifest)
    print(json.dumps({"status": "prepared", "task_count": len(TASK_IDS), "model_calls": 0}, indent=2))


def execute(output_dir: Path) -> None:
    manifest = json.loads((output_dir / "screening_manifest.json").read_text())
    if manifest["git_head"] != EXPECTED_HEAD or manifest["expected_git_head"] != EXPECTED_HEAD:
        raise RuntimeError("interface screen must run from the forensic-authority commit")
    if manifest["manifest_sha256"] != stage_a.sha256_bytes(stage_a.canonical({**manifest, "manifest_sha256": None})):
        raise RuntimeError("interface screening manifest hash mismatch")
    runtime = stage_a.runtime_payload()
    artifact = stage_a.candidate_path(runtime)
    spec = stage_a.worker_spec()
    preflight = stage_a.non_generative_preflight(spec)
    telemetry_url = stage_a.telemetry_base_url()
    telemetry = stage_a.telemetry_preflight(telemetry_url)
    exclusive = stage_a.exclusivity_record()
    idle_samples, idle_summary = stage_a.sample_window(IDLE_SECONDS, base_url=telemetry_url)
    stage_a.write_json(output_dir / "preflight.json", {
        "non_generative_models": preflight,
        "telemetry": telemetry,
        "gpu_exclusivity": exclusive,
        "candidate_artifact_binding": {
            "source": "workspace_sha256" if artifact is not None else "immutable_runtime_freeze_and_serving_host_identity",
            "sha256": runtime["candidate"]["sha256"],
            "size_bytes": runtime["candidate"]["size_bytes"],
        },
        "public_telemetry_alias": telemetry["public_alias"],
        "model_calls": 0,
    })
    stage_a.write_json(output_dir / "idle_power_samples.json", {
        "schema": "zth_interface_screen_idle_power_v1",
        "measurement_level": 2,
        "measurement_boundary": "GTX_1650_device_only",
        "summary": idle_summary,
        "samples": idle_samples,
    })
    stage_a.write_json(output_dir / "lifecycle.json", {"status": "screening_running", "started_at": stage_a.now(), "model_calls_made": False})
    summaries = []
    for task_id in manifest["selection"]["task_order"]:
        task_dir = output_dir / "tasks" / task_id
        task = json.loads((task_dir / "fixture.snapshot.json").read_text())
        prompt = (task_dir / "prompt.txt").read_text()
        sampler = stage_a.PowerSampler(
            lambda: stage_a.read_gpu_power(EXPECTED_GPU_UUID, base_url=telemetry_url),
            expected_gpu_uuid=EXPECTED_GPU_UUID,
            sample_interval_seconds=POWER_INTERVAL_SECONDS,
        )
        request_started = __import__("time").monotonic()
        request_started_at = stage_a.now()
        sampler.start()
        response = stage_a.call_worker(spec, prompt, MAX_OUTPUT_TOKENS, timeout=TIMEOUT_SECONDS)
        response_captured = __import__("time").monotonic()
        samples = sampler.stop()
        power_samples = [{
            "timestamp_utc": s.timestamp_utc,
            "monotonic_seconds": s.monotonic_seconds,
            "gpu_uuid": s.gpu_uuid,
            "power_watts": s.power_watts,
            "sequence": s.sequence,
        } for s in samples]
        energy = stage_a.integrate_energy_joules(samples, sample_interval_seconds=POWER_INTERVAL_SECONDS, expected_gpu_uuid=EXPECTED_GPU_UUID)
        metadata = response.metadata()
        metadata["request_url"] = None
        raw = {
            "status": response.status,
            "content": response.content,
            "metadata": metadata,
            "request_started_at": request_started_at,
            "response_captured_at": stage_a.now(),
            "wall_elapsed_ms": round((response_captured - request_started) * 1000, 3),
        }
        stage_a.write_json(task_dir / "response.json", raw)
        transport = metadata.get("transport_classification")
        validation = stage_a._validator_result(response.content, task, attempt_id=f"interface-{task_id}") if transport == "model_response" else None
        if validation is not None:
            stage_a.write_json(task_dir / "validation.json", validation)
        stage_a.write_json(task_dir / "power_samples.json", {
            "schema": "zth_interface_screen_power_samples_v1",
            "measurement_level": 2,
            "measurement_boundary": "GTX_1650_device_only",
            "gpu_uuid": EXPECTED_GPU_UUID,
            "samples": power_samples,
        })
        quality = raw_quality(validation)
        power_summary = {
            "sample_count": len(samples),
            "mean_active_watts": round(statistics.mean(s.power_watts for s in samples), 6),
            "peak_observed_watts": round(max(s.power_watts for s in samples), 6),
            "gross_energy_joules": energy,
            "sample_interval_seconds": POWER_INTERVAL_SECONDS,
        }
        scorecard = {
            "schema": "zth_qwen3_0_6b_interface_screen_task_v1",
            "task_id": task_id,
            "transport_valid": transport == "model_response",
            "transport_classification": transport,
            "markdown_fenced": response.content.strip().startswith("```") and response.content.strip().endswith("```"),
            "parse_valid": quality["parse_valid"],
            "contract_valid": quality["contract_valid"],
            "reference_fact_valid": quality["reference_valid"],
            "deterministic_validation_status": validation.get("validation_status") if validation else None,
            "validated_pass": quality["fully_validated"],
            "failed_check_ids": [c.get("check_id") for c in validation.get("checks", []) if c.get("status") == "failed"] if validation else [],
            "wall_elapsed_ms": raw["wall_elapsed_ms"],
            "prompt_tokens": (metadata.get("usage") or {}).get("prompt_tokens"),
            "completion_tokens": (metadata.get("usage") or {}).get("completion_tokens"),
            "total_tokens": (metadata.get("usage") or {}).get("total_tokens"),
            "power_summary": power_summary,
            "telemetry_valid": True,
            "retry_count": 0,
            "escalation_count": 0,
            "exclusive_gpu": None,
            "raw_response_preserved": True,
            "screening_only": True,
        }
        stage_a.write_json(task_dir / "scorecard.json", scorecard)
        summaries.append(scorecard)
    aggregate = build_aggregate(summaries, idle_summary)
    stage_a.write_json(output_dir / "aggregate.json", aggregate)
    stage_a.write_json(output_dir / "lifecycle.json", {"status": "screening_terminal", "completed_at": stage_a.now(), "model_calls_made": True, "task_count": len(summaries)})
    print(json.dumps({"status": "screening_terminal", "tasks": len(summaries), "model_calls": len(summaries)}, indent=2))


def build_aggregate(summaries: list[dict], idle_summary: dict) -> dict:
    latencies = [s["wall_elapsed_ms"] for s in summaries]
    energies = [s["power_summary"]["gross_energy_joules"] for s in summaries]
    def p95(values):
        ordered = sorted(values)
        return round(ordered[min(len(ordered)-1, int(round((len(ordered)-1)*0.95)))], 3) if values else None
    return {
        "schema": "zth_qwen3_0_6b_interface_disambiguation_aggregate_v1",
        "screening_only_not_confirmatory": True,
        "candidate": stage_a.EXPECTED_MODEL_ID,
        "parameters": 596049920,
        "task_count": len(summaries),
        "transport_valid_responses": sum(s["transport_valid"] for s in summaries),
        "parse_valid_responses": sum(s["parse_valid"] for s in summaries),
        "contract_valid_responses": sum(s["contract_valid"] for s in summaries),
        "reference_fact_valid_responses": sum(s["reference_fact_valid"] for s in summaries),
        "validated_passes": sum(s["validated_pass"] for s in summaries),
        "deterministic_failures": sum(not s["validated_pass"] for s in summaries),
        "fence_count": sum(s.get("markdown_fenced", False) for s in summaries),
        "latency_ms": {"metric": "candidate_action_wall_clock", "median": round(statistics.median(latencies), 3), "mean": round(statistics.mean(latencies), 3), "p95": p95(latencies)},
        "tokens": {"prompt": [s["prompt_tokens"] for s in summaries], "completion": [s["completion_tokens"] for s in summaries], "total": [s["total_tokens"] for s in summaries]},
        "energy": {"measurement_level": 2, "measurement_boundary": "GTX_1650_device_only", "gpu_uuid": EXPECTED_GPU_UUID, "gross_joules_per_action_mean": round(statistics.mean(energies), 6), "gross_joules_per_action_median": round(statistics.median(energies), 6), "gross_joules_per_validated_task": None},
        "idle_power": idle_summary,
        "telemetry_complete": all(s["telemetry_valid"] for s in summaries),
        "retry_count": 0,
        "escalation_count": 0,
        "screening_disposition": "PENDING_REVIEW",
        "model_calls_made": True,
        "historical_stage_a_modified": False,
    }


def finalize(output_dir: Path, interpretation: str) -> None:
    allowed = {"INTERFACE_CHANGE_MATERIALLY_IMPROVED_USABILITY", "INTERFACE_CHANGE_DID_NOT_RESCUE_CAPABILITY", "INTERFACE_CHANGE_NO_MEANINGFUL_EFFECT", "INCONCLUSIVE"}
    if interpretation not in allowed:
        raise ValueError("invalid interface interpretation")
    path = output_dir / "aggregate.json"
    aggregate = json.loads(path.read_text())
    aggregate["interpretation"] = interpretation
    aggregate["finalized_at"] = stage_a.now()
    stage_a.write_json(path, aggregate)
    print(json.dumps({"status": "finalized", "interpretation": interpretation, "model_calls": 0}, indent=2))


def reaggregate(output_dir: Path) -> None:
    path = output_dir / "aggregate.json"
    aggregate = json.loads(path.read_text())
    prior_hash = stage_a.sha256_file(path)
    fence_count = 0
    for response_path in sorted((output_dir / "tasks").glob("*/response.json")):
        content = json.loads(response_path.read_text()).get("content", "").strip()
        fence_count += content.startswith("```") and content.endswith("```")
    aggregate["fence_count"] = fence_count
    aggregate["derived_aggregate_correction"] = "fence_count recomputed from preserved raw response text; raw responses and validator artifacts unchanged"
    aggregate["pre_correction_aggregate_sha256"] = prior_hash
    stage_a.write_json(path, aggregate)
    print(json.dumps({"status": "derived_aggregate_recomputed", "model_calls": 0, "raw_artifacts_changed": False}, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--finalize", action="store_true")
    mode.add_argument("--reaggregate", action="store_true")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--interpretation")
    args = parser.parse_args()
    if args.prepare:
        prepare(args.output_dir)
    elif args.execute:
        execute(args.output_dir)
    else:
        if args.reaggregate:
            reaggregate(args.output_dir)
            return 0
        if not args.interpretation:
            raise SystemExit("--finalize requires --interpretation")
        finalize(args.output_dir, args.interpretation)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
