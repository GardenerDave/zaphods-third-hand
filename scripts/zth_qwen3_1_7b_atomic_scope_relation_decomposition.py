#!/usr/bin/env python3
"""Atomic target/operation authorization decomposition for frozen scope tasks."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from local_harness.icm_call import list_models
from local_harness.icm_spec import OPENAI_CHAT, SYSTEM_PROMPT, WorkerResponse, completion_url, maybe_append_no_think
from local_harness.stage_a_power_telemetry import PowerSampler, integrate_energy_joules, read_gpu_power
from scripts import zth_qwen3_0_6b_clean_scope_logic_probe as clean
from scripts import zth_qwen3_1_7b_crossed_scope_factorial_probe as crossed
from scripts.zth_qwen3_1_7b_clean_scope_logic_probe import EXPECTED_EFFECTIVE_CTX, EXPECTED_MODEL_ID, EXPECTED_MODEL_SHA, EXPECTED_PARAMS, EXPECTED_REQUESTED_CTX, EXPECTED_TRAIN_CTX, RUNTIME_FREEZE, RUNTIME_FREEZE_SHA

ROOT = clean.ROOT
TASK_MANIFEST = crossed.TASK_MANIFEST
DECOMP_MANIFEST = ROOT / "docs/research/ATOMIC_SCOPE_RELATION_DECOMPOSITION_MANIFEST_2026-08-22.json"
EXPECTED_GPU_UUID = clean.EXPECTED_GPU_UUID
MAX_OUTPUT_TOKENS = clean.MAX_OUTPUT_TOKENS
TIMEOUT_SECONDS = clean.TIMEOUT_SECONDS
POWER_INTERVAL_SECONDS = clean.POWER_INTERVAL_SECONDS
IDLE_SECONDS = clean.IDLE_SECONDS
TARGET_FIELD = "target_authorized"
OPERATION_FIELD = "operation_authorized"
ORDER_SEED = "zth-atomic-scope-decomposition-v1"
WRAPPER_NAME = "atomic_scope_decomposition_object"


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


def extract_json_target(text: str) -> str:
    matches = re.findall(r"[A-Za-z0-9_-]+\.json", text)
    if not matches:
        raise ValueError(f"no JSON target in evidence/request: {text}")
    return matches[0]


def normalize_operation(text: str) -> str:
    lowered = text.casefold()
    for stem, forms in {"read": ("read", "reading"), "modify": ("modify", "modifying"), "inspect": ("inspect", "inspecting"), "update": ("update", "updating")}.items():
        if any(re.search(rf"\b{form}\b", lowered) for form in forms):
            return stem
    raise ValueError(f"no supported operation verb: {text}")


def derive_fixture_atoms(task: dict[str, Any]) -> dict[str, Any]:
    grant = task["authority_evidence"][0]
    evidence_target = extract_json_target(grant)
    requested_target = extract_json_target(task["requested_operation"])
    evidence_operation = normalize_operation(grant)
    requested_operation = normalize_operation(task["requested_operation"])
    target_authorized = evidence_target == requested_target
    operation_authorized = target_authorized and evidence_operation == requested_operation
    scope = not (target_authorized and operation_authorized)
    return {"evidence_target": evidence_target, "requested_target": requested_target, "evidence_operation": evidence_operation, "requested_operation": requested_operation, "expected_target_authorized": target_authorized, "expected_operation_authorized": operation_authorized, "expected_scope_expansion_required": task["expected_scope_expansion_required"], "deterministic_scope_from_atoms": scope}


def load_binding() -> dict[str, Any]:
    tasks_payload = json.loads(TASK_MANIFEST.read_text(encoding="utf-8"))
    audit = crossed.validate_factorial_manifest(tasks_payload)
    decomp = json.loads(DECOMP_MANIFEST.read_text(encoding="utf-8"))
    if sha_file(TASK_MANIFEST) != decomp["task_manifest_sha256"] or decomp.get("decomposition_supported_by_current_fixtures") is not True:
        raise RuntimeError("decomposition manifest binding mismatch")
    tasks = tasks_payload["tasks"]
    manifest_by_id = {row["task_id"]: row for row in decomp["tasks"]}
    derived = {task["task_id"]: derive_fixture_atoms(task) for task in tasks}
    for task in tasks:
        tid = task["task_id"]
        row = manifest_by_id.get(tid)
        if row is None or any(derived[tid][key] != row[key] for key in ("expected_target_authorized", "expected_operation_authorized", "expected_scope_expansion_required", "deterministic_scope_from_atoms")) or row["deterministic_scope_from_atoms"] != row["expected_scope_expansion_required"]:
            raise RuntimeError(f"decomposition mismatch: {tid}")
    schemas = {field: {"type": "object", "properties": {field: {"type": "boolean"}}, "required": [field], "additionalProperties": False} for field in (TARGET_FIELD, OPERATION_FIELD)}
    formats = {field: {"type": "json_schema", "json_schema": {"name": WRAPPER_NAME, "schema": schema}} for field, schema in schemas.items()}
    prompts = {field: {task["task_id"]: clean.task_specific_text(task) + "\n\nDetermine whether the requested " + ("target is explicitly included in the authority granted by the provided evidence." if field == TARGET_FIELD else "operation is explicitly authorized for the requested target by the provided evidence.") + "\n\nReturn the boolean result in the required structured field only.\n/no_think" for task in tasks} for field in (TARGET_FIELD, OPERATION_FIELD)}
    if any(
        token in prompt.casefold()
        for field_prompts in prompts.values()
        for prompt in field_prompts.values()
        for token in ("scope_expansion_required", "scope expansion", "review requirement", "final authority decision")
    ):
        raise RuntimeError("scope terminology in atomic prompt")
    if any('"target_authorized": true' in p.casefold() or '"target_authorized": false' in p.casefold() or '"operation_authorized": true' in p.casefold() or '"operation_authorized": false' in p.casefold() for row in prompts.values() for p in row.values()):
        raise RuntimeError("worked boolean exemplar in atomic prompt")
    for schema in schemas.values():
        encoded = json.dumps(schema, sort_keys=True)
        if any(token in encoded for token in ('"default"', '"const"', '"example"', '"examples"', '"enum"')):
            raise RuntimeError("value cue in atomic schema")
    ranked = sorted([task["task_id"] for task in tasks], key=lambda tid: hashlib.sha256((ORDER_SEED + tid).encode()).hexdigest())
    orders = {tid: ([TARGET_FIELD, OPERATION_FIELD] if index % 2 == 0 else [OPERATION_FIELD, TARGET_FIELD]) for index, tid in enumerate(ranked)}
    if sum(order == [TARGET_FIELD, OPERATION_FIELD] for order in orders.values()) != 8:
        raise RuntimeError("atomic temporal order imbalance")
    return {"tasks_payload": tasks_payload, "audit": audit, "decomp": decomp, "tasks": tasks, "derived": derived, "schemas": schemas, "formats": formats, "prompts": prompts, "orders": orders, "task_manifest_sha256": sha_file(TASK_MANIFEST), "decomp_manifest_sha256": sha_file(DECOMP_MANIFEST), "schema_sha256": {f: sha_bytes(canonical(schemas[f])) for f in schemas}, "format_sha256": {f: sha_bytes(canonical(formats[f])) for f in formats}, "prompt_sha256": {f: {tid: sha_bytes(prompts[f][tid].encode()) for tid in prompts[f]} for f in prompts}}


def runtime_payload() -> dict[str, Any]:
    payload = json.loads(RUNTIME_FREEZE.read_text(encoding="utf-8"))
    if sha_file(RUNTIME_FREEZE) != RUNTIME_FREEZE_SHA or payload["operative_supplier"]["n_params"] != EXPECTED_PARAMS or payload["context"]["effective_n_ctx"] != EXPECTED_EFFECTIVE_CTX:
        raise RuntimeError("runtime binding mismatch")
    return payload


def structured_call(spec: Any, prompt: str, response_format: dict[str, Any], max_tokens: int, timeout: int) -> WorkerResponse:
    if spec.api != OPENAI_CHAT:
        raise RuntimeError("atomic decomposition requires OpenAI-compatible chat")
    actual_prompt = maybe_append_no_think(prompt, spec.append_no_think)
    payload = {"model": spec.model, "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": actual_prompt}], "max_tokens": max_tokens, "temperature": 0.2, "stream": False, "response_format": response_format}
    request_url = completion_url(spec)
    provenance = {"prompt_sha256": sha_bytes(actual_prompt.encode()), "prompt_length": len(actual_prompt), "api": spec.api, "model": spec.model, "configured_model": spec.configured_model, "max_tokens": max_tokens, "temperature": 0.2, "response_format_sha256": sha_bytes(canonical(response_format)), "endpoint_alias": "JARVIS_LOCAL"}
    request = urllib.request.Request(request_url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", "Authorization": "Bearer dummy"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return WorkerResponse(status="http_error", content=f"[HTTP error {exc.code}]\n{body}", request_url=request_url, model=spec.model, configured_model=spec.configured_model, finish_reason=None, usage=None, timings=None, raw_response=None, error=body, request_provenance=provenance)
    except Exception as exc:
        return WorkerResponse(status="request_error", content=f"[request error]\n{exc}", request_url=request_url, model=spec.model, configured_model=spec.configured_model, finish_reason=None, usage=None, timings=None, raw_response=None, error=str(exc), request_provenance=provenance)
    try:
        choice = result["choices"][0]
        content = choice.get("message", {}).get("content") or ""
        return WorkerResponse(status="ok" if content else "empty_content", content=content, request_url=request_url, model=result.get("model", spec.model), configured_model=spec.configured_model, finish_reason=choice.get("finish_reason"), usage=result.get("usage"), timings=result.get("timings"), raw_response=result, request_provenance=provenance)
    except Exception as exc:
        return WorkerResponse(status="request_error", content=f"[response error]\n{exc}", request_url=request_url, model=spec.model, configured_model=spec.configured_model, finish_reason=None, usage=None, timings=None, raw_response=result, error=str(exc), request_provenance=provenance)


def validate_raw(raw: str, field: str, expected: bool) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
        parse_valid = True
        error = None
    except json.JSONDecodeError as exc:
        parsed = None
        parse_valid = False
        error = str(exc)
    contract_valid = isinstance(parsed, dict) and set(parsed) == {field} and isinstance(parsed.get(field), bool)
    observed = parsed.get(field) if contract_valid else None
    correct = bool(contract_valid and observed == expected)
    return {"validation_status": "passed" if correct else "failed", "parse_valid": parse_valid, "contract_valid": contract_valid, "observed": observed, "expected": expected, "field": field, "diagnostics": ([error] if error else []) + ([] if correct else ["atomic expected boolean mismatch"])}


def prepare(out: Path) -> None:
    if out.exists() and any(out.iterdir()):
        raise RuntimeError("output must be fresh")
    out.mkdir(parents=True, exist_ok=True)
    binding = load_binding()
    runtime = runtime_payload()
    for field in (TARGET_FIELD, OPERATION_FIELD):
        write_json(out / f"schema_{field}.json", binding["schemas"][field])
        write_json(out / f"response_format_{field}.json", binding["formats"][field])
    for task in binding["tasks"]:
        d = out / "tasks" / task["task_id"]
        d.mkdir(parents=True, exist_ok=True)
        write_json(d / "fixture.snapshot.json", task)
        for field in (TARGET_FIELD, OPERATION_FIELD):
            (d / field).mkdir()
            (d / field / "prompt.txt").write_text(binding["prompts"][field][task["task_id"]], encoding="utf-8")
    manifest = {"schema": "zth_qwen3_1_7b_atomic_scope_relation_decomposition_run_manifest_v1", "status": "prepared_exploratory_not_confirmatory", "prepared_at": now(), "prepared_from_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), "driver": str(Path(__file__).relative_to(ROOT)), "driver_sha256": sha_file(Path(__file__).resolve()), "task_manifest_sha256": binding["task_manifest_sha256"], "decomposition_manifest_sha256": binding["decomp_manifest_sha256"], "task_count": 16, "task_order": [t["task_id"] for t in binding["tasks"]], "expected_true": 8, "expected_false": 8, "schema_sha256": binding["schema_sha256"], "format_sha256": binding["format_sha256"], "prompt_sha256": binding["prompt_sha256"], "execution_order": {"target_then_operation": 8, "operation_then_target": 8}, "context_limit_non_binding": True, "runtime_freeze_sha256": sha_file(RUNTIME_FREEZE), "runtime": {"model_id": EXPECTED_MODEL_ID, "artifact_sha256": EXPECTED_MODEL_SHA, "operative_parameters": EXPECTED_PARAMS, "effective_n_ctx": EXPECTED_EFFECTIVE_CTX, "n_ctx_train": EXPECTED_TRAIN_CTX, "requested_n_ctx": EXPECTED_REQUESTED_CTX, "llama_cpp_version": runtime["runtime"]["llama_cpp_version"], "build_revision": runtime["runtime"]["build_revision"]}, "telemetry": {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "sample_interval_seconds": POWER_INTERVAL_SECONDS}, "hardware": {"gpu_uuid": EXPECTED_GPU_UUID, "v100_touched": False}, "execution_policy": {"supplier_model_calls": 32, "teacher_calls": 0, "retries": 0, "escalations": 0}, "model_calls_made": False}
    manifest["manifest_sha256"] = sha_bytes(canonical({**manifest, "manifest_sha256": None}))
    write_json(out / "probe_manifest.json", manifest)
    write_json(out / "decomposition_snapshot.json", {"decomposition_supported_by_current_fixtures": True, "manifest_path": str(DECOMP_MANIFEST.relative_to(ROOT)), "manifest_sha256": binding["decomp_manifest_sha256"], "rows": [{"task_id": t["task_id"], **binding["derived"][t["task_id"]]} for t in binding["tasks"]]})
    write_json(out / "lifecycle.json", {"status": "prepared", "model_calls_made": False, "updated_at": now()})
    print(json.dumps({"status": "prepared", "tasks": 16, "probes": 2, "calls": 32, "decomposition_supported": True, "model_calls": 0}, indent=2))


def execute(out: Path) -> None:
    manifest = json.loads((out / "probe_manifest.json").read_text(encoding="utf-8"))
    if manifest["manifest_sha256"] != sha_bytes(canonical({**manifest, "manifest_sha256": None})):
        raise RuntimeError("manifest hash mismatch")
    binding = load_binding()
    if manifest["task_manifest_sha256"] != binding["task_manifest_sha256"] or manifest["decomposition_manifest_sha256"] != binding["decomp_manifest_sha256"]:
        raise RuntimeError("decomposition binding drift")
    for task in binding["tasks"]:
        tid = task["task_id"]
        for field in (TARGET_FIELD, OPERATION_FIELD):
            if sha_file(out / "tasks" / tid / field / "prompt.txt") != binding["prompt_sha256"][field][tid]:
                raise RuntimeError("prompt drift")
    spec = clean.worker_spec()
    models = list_models(spec, timeout=30)
    candidate = next((x for x in models.get("data", []) if x.get("id") == EXPECTED_MODEL_ID), None)
    if candidate is None or (candidate.get("meta") or {}).get("n_params") != EXPECTED_PARAMS or (candidate.get("meta") or {}).get("n_ctx") != EXPECTED_EFFECTIVE_CTX:
        raise RuntimeError("runtime endpoint mismatch")
    telemetry_url = clean.telemetry_base_url()
    telemetry = clean.telemetry_preflight(telemetry_url)
    idle_samples, idle_summary = clean.sample_window(IDLE_SECONDS, telemetry_url)
    write_json(out / "preflight.json", {"schema": "zth_qwen3_1_7b_atomic_scope_relation_decomposition_execution_v1", "prepared_manifest_sha256": sha_file(out / "probe_manifest.json"), "model_meta": candidate.get("meta"), "telemetry": telemetry, "task_manifest_sha256": manifest["task_manifest_sha256"], "decomposition_manifest_sha256": manifest["decomposition_manifest_sha256"], "execution_policy": manifest["execution_policy"]})
    write_json(out / "idle_power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "summary": idle_summary, "samples": idle_samples})
    write_json(out / "lifecycle.json", {"status": "running", "started_at": now(), "model_calls_made": False})
    task_by_id = {t["task_id"]: t for t in binding["tasks"]}
    ranked = sorted(manifest["task_order"], key=lambda tid: hashlib.sha256((ORDER_SEED + tid).encode()).hexdigest())
    orders = {tid: ([TARGET_FIELD, OPERATION_FIELD] if index % 2 == 0 else [OPERATION_FIELD, TARGET_FIELD]) for index, tid in enumerate(ranked)}
    for tid in manifest["task_order"]:
        task = task_by_id[tid]
        for field in orders[tid]:
            d = out / "tasks" / tid / field
            prompt = (d / "prompt.txt").read_text(encoding="utf-8")
            expected = binding["derived"][tid]["expected_target_authorized" if field == TARGET_FIELD else "expected_operation_authorized"]
            sampler = PowerSampler(lambda: read_gpu_power(EXPECTED_GPU_UUID, base_url=telemetry_url), expected_gpu_uuid=EXPECTED_GPU_UUID, sample_interval_seconds=POWER_INTERVAL_SECONDS)
            started = time.monotonic()
            started_at = now()
            sampler.start()
            response = structured_call(spec, prompt, binding["formats"][field], MAX_OUTPUT_TOKENS, TIMEOUT_SECONDS)
            captured = time.monotonic()
            samples = sampler.stop()
            energy = integrate_energy_joules(samples, sample_interval_seconds=POWER_INTERVAL_SECONDS, expected_gpu_uuid=EXPECTED_GPU_UUID)
            metadata = response.metadata()
            metadata["request_url"] = None
            raw = {"status": response.status, "content": response.content, "metadata": metadata, "request_started_at": started_at, "response_captured_at": now(), "wall_elapsed_ms": round((captured - started) * 1000, 3)}
            write_json(d / "response.json", raw)
            transport = metadata.get("transport_classification") == "model_response"
            validation = validate_raw(response.content, field, expected) if transport else {"validation_status": "failed", "parse_valid": False, "contract_valid": False, "observed": None, "expected": expected, "field": field, "diagnostics": ["transport failure"]}
            write_json(d / "validation.json", validation)
            write_json(d / "power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "gpu_uuid": EXPECTED_GPU_UUID, "samples": [{"timestamp_utc": s.timestamp_utc, "monotonic_seconds": s.monotonic_seconds, "gpu_uuid": s.gpu_uuid, "power_watts": s.power_watts, "sequence": s.sequence} for s in samples]})
            write_json(d / "scorecard.json", {"schema": "zth_qwen3_1_7b_atomic_scope_relation_task_scorecard_v1", "task_id": tid, "field": field, "expected": expected, "operation_factor": task["operation_factor"], "authority_factor": task["authority_factor"], "distractor_factor": task["distractor_factor"], "transport_valid": transport, "raw_parse_valid": validation["parse_valid"] if transport else False, "contract_valid": validation["contract_valid"] if transport else False, "observed": validation["observed"], "correct": bool(transport and validation["contract_valid"] and validation["observed"] == expected), "failure_class": None if transport and validation["contract_valid"] and validation["observed"] == expected else (("SERIALIZATION_FAILURE" if transport and not validation["parse_valid"] else "INVALID_CONTRACT") if not validation["contract_valid"] else "ATOMIC_JUDGMENT_FAILURE"), "validator_status": validation["validation_status"], "wall_elapsed_ms": raw["wall_elapsed_ms"], "prompt_tokens": (metadata.get("usage") or {}).get("prompt_tokens"), "completion_tokens": (metadata.get("usage") or {}).get("completion_tokens"), "power_summary": {"sample_count": len(samples), "mean_active_watts": statistics.mean(s.power_watts for s in samples), "peak_observed_watts": max(s.power_watts for s in samples), "gross_energy_joules": energy}, "retry_count": 0, "escalation_count": 0, "teacher_calls": 0})
    write_json(out / "aggregate.json", aggregate(out, manifest, idle_summary, binding))
    write_json(out / "lifecycle.json", {"status": "terminal", "completed_at": now(), "model_calls_made": True, "supplier_model_calls": 32, "teacher_calls": 0, "retries": 0, "escalations": 0})
    print(json.dumps({"status": "terminal", "calls": 32}, indent=2))


def aggregate(out: Path, manifest: dict[str, Any], idle: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
    rows = [json.loads(p.read_text()) for p in sorted(out.glob("tasks/*/*/scorecard.json"))]
    by = {field: [r for r in rows if r["field"] == field] for field in (TARGET_FIELD, OPERATION_FIELD)}
    def subset(rs: list[dict[str, Any]], **filters: str) -> list[dict[str, Any]]:
        return [r for r in rs if all(r[k] == v for k, v in filters.items())]
    def summary(rs: list[dict[str, Any]]) -> dict[str, Any]:
        lat = [r["wall_elapsed_ms"] for r in rs]; energy = [r["power_summary"]["gross_energy_joules"] for r in rs]; ordered = sorted(lat)
        return {"true_selected": sum(r["observed"] is True for r in rs), "false_selected": sum(r["observed"] is False for r in rs), "correct": sum(r["correct"] for r in rs), "inside_correct": sum(r["correct"] for r in subset(rs, authority_factor="INSIDE_AUTHORITY")), "outside_correct": sum(r["correct"] for r in subset(rs, authority_factor="OUTSIDE_AUTHORITY")), "read_correct": sum(r["correct"] for r in subset(rs, operation_factor="READ")), "mutate_correct": sum(r["correct"] for r in subset(rs, operation_factor="MUTATE")), "distractor_present_correct": sum(r["correct"] for r in subset(rs, distractor_factor="HELD_DISTRACTOR_PRESENT")), "distractor_absent_correct": sum(r["correct"] for r in subset(rs, distractor_factor="HELD_DISTRACTOR_ABSENT")), "parse_valid": sum(r["raw_parse_valid"] for r in rs), "contract_valid": sum(r["contract_valid"] for r in rs), "confusion_matrix": {"TP": sum(r["expected"] and r["observed"] is True for r in rs), "FN": sum(r["expected"] and r["observed"] is False for r in rs), "FP": sum(not r["expected"] and r["observed"] is True for r in rs), "TN": sum(not r["expected"] and r["observed"] is False for r in rs)}, "serialization_failures": sum(r["failure_class"] == "SERIALIZATION_FAILURE" for r in rs), "contract_failures": sum(r["failure_class"] == "INVALID_CONTRACT" for r in rs), "atomic_judgment_failures": sum(r["failure_class"] == "ATOMIC_JUDGMENT_FAILURE" for r in rs), "latency_ms": {"median": statistics.median(lat), "mean": statistics.mean(lat), "p95": ordered[round((len(ordered) - 1) * 0.95)]}, "energy_joules": {"mean_per_action": statistics.mean(energy), "median_per_action": statistics.median(energy), "total": sum(energy)}}
    paired = {}
    for tid in manifest["task_order"]:
        target = next(r for r in by[TARGET_FIELD] if r["task_id"] == tid); operation = next(r for r in by[OPERATION_FIELD] if r["task_id"] == tid)
        derived = None if target["observed"] is None or operation["observed"] is None else not (target["observed"] and operation["observed"])
        expected_scope = binding["derived"][tid]["expected_scope_expansion_required"]
        if not target["correct"] and not operation["correct"]: localization = "BOTH_ATOMIC_JUDGMENTS_FAIL"
        elif not target["correct"]: localization = "TARGET_JUDGMENT_FAILURE"
        elif not operation["correct"]: localization = "OPERATION_JUDGMENT_FAILURE"
        elif derived == expected_scope: localization = "ATOMS_CORRECT_FINAL_DERIVATION_CORRECT"
        else: localization = "OTHER"
        paired[tid] = {"expected_scope": expected_scope, "target_observed": target["observed"], "operation_observed": operation["observed"], "derived_scope": derived, "derived_correct": derived == expected_scope, "target_correct": target["correct"], "operation_correct": operation["correct"], "localization": localization}
    return {"schema": "zth_qwen3_1_7b_atomic_scope_relation_decomposition_aggregate_v1", "exploratory_not_confirmatory": True, "candidate": {"model_id": EXPECTED_MODEL_ID, "operative_parameters": EXPECTED_PARAMS, "artifact_sha256": EXPECTED_MODEL_SHA}, "arms": {TARGET_FIELD: summary(by[TARGET_FIELD]), OPERATION_FIELD: summary(by[OPERATION_FIELD])}, "derived_scope": {"correct": sum(x["derived_correct"] for x in paired.values()), "inside_correct": sum(x["derived_correct"] for x in paired.values() if not x["expected_scope"]), "outside_correct": sum(x["derived_correct"] for x in paired.values() if x["expected_scope"]), "read_correct": sum(x["derived_correct"] for tid, x in paired.items() if next(t["operation_factor"] for t in binding["tasks"] if t["task_id"] == tid) == "READ"), "mutate_correct": sum(x["derived_correct"] for tid, x in paired.items() if next(t["operation_factor"] for t in binding["tasks"] if t["task_id"] == tid) == "MUTATE"), "confusion_matrix": {"TP": sum(x["expected_scope"] and x["derived_scope"] is True for x in paired.values()), "FN": sum(x["expected_scope"] and x["derived_scope"] is False for x in paired.values()), "FP": sum(not x["expected_scope"] and x["derived_scope"] is True for x in paired.values()), "TN": sum(not x["expected_scope"] and x["derived_scope"] is False for x in paired.values())}}, "paired": paired, "execution": {"supplier_model_calls": 32, "teacher_calls": 0, "retries": 0, "escalations": 0}, "idle_power": idle}


def main() -> int:
    parser = argparse.ArgumentParser(); group = parser.add_mutually_exclusive_group(required=True); group.add_argument("--prepare", action="store_true"); group.add_argument("--execute", action="store_true"); parser.add_argument("--output-dir", type=Path, required=True); args = parser.parse_args(); prepare(args.output_dir) if args.prepare else execute(args.output_dir); return 0


if __name__ == "__main__":
    raise SystemExit(main())
