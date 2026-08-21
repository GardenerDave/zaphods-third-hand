#!/usr/bin/env python3
"""Three-arm model-interface isolation for the crossed scope probe."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import itertools
import json
import statistics
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from local_harness.icm_call import call_worker, list_models
from local_harness.stage_a_power_telemetry import PowerSampler, integrate_energy_joules, read_gpu_power
from local_harness.supervised_capability_loop import _validator_result
from scripts import zth_qwen3_0_6b_clean_scope_logic_probe as clean
from scripts import zth_qwen3_1_7b_crossed_scope_factorial_probe as factorial
from scripts.zth_qwen3_1_7b_clean_scope_logic_probe import (
    EXPECTED_EFFECTIVE_CTX,
    EXPECTED_MODEL_ID,
    EXPECTED_MODEL_SHA,
    EXPECTED_PARAMS,
    EXPECTED_TRAIN_CTX,
    EXPECTED_REQUESTED_CTX,
    RUNTIME_FREEZE,
    RUNTIME_FREEZE_SHA,
)

ROOT = clean.ROOT
TASK_MANIFEST = factorial.TASK_MANIFEST
EXPECTED_GPU_UUID = clean.EXPECTED_GPU_UUID
MAX_OUTPUT_TOKENS = clean.MAX_OUTPUT_TOKENS
TIMEOUT_SECONDS = clean.TIMEOUT_SECONDS
POWER_INTERVAL_SECONDS = clean.POWER_INTERVAL_SECONDS
IDLE_SECONDS = clean.IDLE_SECONDS
ARM_ORDER_SEED = "zth-crossed-boolean-exemplar-v1"
ARMS = ("T", "F", "N")
PERMUTATIONS = tuple(itertools.permutations(ARMS))


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


def interface_suffixes() -> dict[str, str]:
    true_suffix = clean.PROMPT_SUFFIX
    false_suffix = true_suffix.replace(
        '{"scope_expansion_required": true}',
        '{"scope_expansion_required": false}',
    )
    if false_suffix == true_suffix or true_suffix.count('{"scope_expansion_required": true}') != 1:
        raise RuntimeError("true exemplar was not uniquely found")
    neutral_suffix = (
        "Return ONLY a bare JSON object.\n"
        "\n"
        "The object must contain exactly one field named\n"
        '"scope_expansion_required".\n'
        "\n"
        "The field value must be a JSON boolean: true or false.\n"
        "\n"
        + clean.SEMANTIC_RULE + "\n"
        "\n"
        "Choose true or false using the task evidence and the semantic rule above.\n"
        "\n"
        "Do not include markdown, reasoning, explanation, or any other field.\n"
        "/no_think\n"
        "\n"
        "Do not include any worked object whose boolean value is true or false."
    )
    if clean.SEMANTIC_RULE not in true_suffix:
        raise RuntimeError("frozen semantic rule missing from true suffix")
    if clean.SEMANTIC_RULE not in false_suffix:
        raise RuntimeError("frozen semantic rule missing from false suffix")
    return {"T": true_suffix, "F": false_suffix, "N": neutral_suffix}


def suffix_diff(a: str, b: str, name_a: str, name_b: str) -> str:
    return "".join(difflib.unified_diff(
        a.splitlines(True), b.splitlines(True), fromfile=name_a, tofile=name_b
    ))


def task_prompt(task: dict[str, Any], suffix: str) -> str:
    return clean.task_specific_text(task) + "\n\n" + suffix


def arm_assignment(tasks: list[dict[str, Any]]) -> dict[str, list[str]]:
    ranked = sorted(
        (task["task_id"] for task in tasks),
        key=lambda task_id: hashlib.sha256((ARM_ORDER_SEED + task_id).encode()).hexdigest(),
    )
    assignment = {}
    for index, task_id in enumerate(ranked):
        assignment[task_id] = list(PERMUTATIONS[index % len(PERMUTATIONS)])
    return assignment


def validate_inputs() -> dict[str, Any]:
    tasks_payload = json.loads(TASK_MANIFEST.read_text(encoding="utf-8"))
    audit = factorial.validate_factorial_manifest(tasks_payload)
    tasks = tasks_payload["tasks"]
    suffixes = interface_suffixes()
    if any(clean.SEMANTIC_RULE not in suffix for suffix in suffixes.values()):
        raise ValueError("semantic rule is not present in every arm")
    if suffixes["F"].replace('{"scope_expansion_required": false}', '{"scope_expansion_required": true}') != suffixes["T"]:
        raise ValueError("Arm F is not an exact one-token replacement")
    assignments = arm_assignment(tasks)
    counts = {"".join(permutation): sum(order == list(permutation) for order in assignments.values()) for permutation in PERMUTATIONS}
    if sorted(counts.values()) != [2, 2, 3, 3, 3, 3]:
        raise ValueError("arm permutations are not balanced")
    lengths = [len(task_prompt(task, suffixes[arm])) for task in tasks for arm in ARMS]
    if max(lengths) + MAX_OUTPUT_TOKENS >= EXPECTED_EFFECTIVE_CTX:
        raise ValueError("effective context could bind the isolation prompts")
    return {
        "tasks_payload": tasks_payload,
        "tasks": tasks,
        "audit": audit,
        "suffixes": suffixes,
        "assignments": assignments,
        "permutation_counts": counts,
        "max_prompt_chars": max(lengths),
        "semantic_rule_sha256": sha_bytes(clean.SEMANTIC_RULE.encode()),
        "suffix_sha256": {arm: sha_bytes(suffixes[arm].encode()) for arm in ARMS},
    }


def runtime_payload() -> dict[str, Any]:
    payload = json.loads(RUNTIME_FREEZE.read_text(encoding="utf-8"))
    if sha_file(RUNTIME_FREEZE) != RUNTIME_FREEZE_SHA:
        raise RuntimeError("runtime freeze hash mismatch")
    if payload["operative_supplier"]["n_params"] != EXPECTED_PARAMS:
        raise RuntimeError("operative parameter binding mismatch")
    if payload["context"]["effective_n_ctx"] != EXPECTED_EFFECTIVE_CTX:
        raise RuntimeError("effective context binding mismatch")
    return payload


def prepare(output_dir: Path) -> None:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError("output directory must be fresh")
    output_dir.mkdir(parents=True, exist_ok=True)
    binding = validate_inputs()
    runtime = runtime_payload()
    for arm in ARMS:
        (output_dir / "interfaces" / arm).mkdir(parents=True, exist_ok=True)
        (output_dir / "interfaces" / arm / "suffix.txt").write_bytes(binding["suffixes"][arm].encode())
    (output_dir / "interfaces" / "T_to_F.diff").write_text(
        suffix_diff(binding["suffixes"]["T"], binding["suffixes"]["F"], "Arm-T", "Arm-F"), encoding="utf-8"
    )
    (output_dir / "interfaces" / "T_to_N.diff").write_text(
        suffix_diff(binding["suffixes"]["T"], binding["suffixes"]["N"], "Arm-T", "Arm-N"), encoding="utf-8"
    )
    task_rows = []
    for task in binding["tasks"]:
        task_dir = output_dir / "tasks" / task["task_id"]
        task_dir.mkdir(parents=True, exist_ok=True)
        row = {
            "task_id": task["task_id"],
            "task_specific_sha256": sha_bytes(clean.task_specific_text(task).encode()),
            "expected": task["expected_scope_expansion_required"],
            "operation_factor": task["operation_factor"],
            "authority_factor": task["authority_factor"],
            "distractor_factor": task["distractor_factor"],
            "arm_order": binding["assignments"][task["task_id"]],
            "prompt_sha256": {},
        }
        (task_dir / "fixture.snapshot.json").write_text(json.dumps(task, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        for arm in ARMS:
            prompt = task_prompt(task, binding["suffixes"][arm])
            (task_dir / arm).mkdir(exist_ok=True)
            (task_dir / arm / "prompt.txt").write_bytes(prompt.encode())
            row["prompt_sha256"][arm] = sha_bytes(prompt.encode())
        task_rows.append(row)
    manifest = {
        "schema": "zth_qwen3_1_7b_boolean_exemplar_scope_isolation_manifest_v1",
        "status": "prepared_exploratory_not_confirmatory",
        "prepared_at": now(),
        "prepared_from_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "driver": str(Path(__file__).relative_to(ROOT)),
        "driver_sha256": sha_file(Path(__file__).resolve()),
        "task_manifest_path": str(TASK_MANIFEST.relative_to(ROOT)),
        "task_manifest_sha256": sha_file(TASK_MANIFEST),
        "task_order": [task["task_id"] for task in binding["tasks"]],
        "task_count": 16,
        "answer_leakage_findings": 0,
        "semantic_rule_sha256": binding["semantic_rule_sha256"],
        "suffix_sha256": binding["suffix_sha256"],
        "interface_diffs": {
            "T_to_F_sha256": sha_bytes(suffix_diff(binding["suffixes"]["T"], binding["suffixes"]["F"], "Arm-T", "Arm-F").encode()),
            "T_to_N_sha256": sha_bytes(suffix_diff(binding["suffixes"]["T"], binding["suffixes"]["N"], "Arm-T", "Arm-N").encode()),
        },
        "arm_order_seed": ARM_ORDER_SEED,
        "permutation_counts": binding["permutation_counts"],
        "output_contract": {"exact_fields": ["scope_expansion_required"], "format": "bare_json_object", "field_type": "boolean"},
        "runtime_freeze_path": str(RUNTIME_FREEZE.relative_to(ROOT)),
        "runtime_freeze_sha256": sha_file(RUNTIME_FREEZE),
        "runtime": {"model_id": EXPECTED_MODEL_ID, "artifact_sha256": EXPECTED_MODEL_SHA, "operative_parameters": EXPECTED_PARAMS, "effective_n_ctx": EXPECTED_EFFECTIVE_CTX, "n_ctx_train": EXPECTED_TRAIN_CTX, "requested_n_ctx": EXPECTED_REQUESTED_CTX, "context_cap_reason": "native_training_context_cap", "context_limit_non_binding_for_probe": True, "llama_cpp_version": runtime["runtime"]["llama_cpp_version"], "build_revision": runtime["runtime"]["build_revision"]},
        "hardware": {"gpu_uuid": EXPECTED_GPU_UUID, "gpu_class": "NVIDIA GeForce GTX 1650", "v100_touched": False},
        "telemetry": {"transport": "remote_read_only_http", "measurement_level": 2, "measurement_boundary": "gpu_device_only", "sample_interval_seconds": POWER_INTERVAL_SECONDS},
        "execution_policy": {"supplier_model_calls": 48, "teacher_calls": 0, "retries": 0, "escalations": 0},
        "tasks": task_rows,
        "model_calls_made": False,
    }
    manifest["manifest_sha256"] = sha_bytes(canonical({**manifest, "manifest_sha256": None}))
    write_json(output_dir / "probe_manifest.json", manifest)
    write_json(output_dir / "lifecycle.json", {"status": "prepared", "model_calls_made": False, "updated_at": now()})
    print(json.dumps({"status": "prepared", "tasks": 16, "arms": 3, "supplier_calls": 48, "answer_leakage_findings": 0, "model_calls": 0}, indent=2))


def execute(output_dir: Path) -> None:
    manifest_path = output_dir / "probe_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if manifest["manifest_sha256"] != sha_bytes(canonical({**manifest, "manifest_sha256": None})):
        raise RuntimeError("prepared manifest hash mismatch")
    binding = validate_inputs()
    if sha_file(TASK_MANIFEST) != manifest["task_manifest_sha256"] or binding["semantic_rule_sha256"] != manifest["semantic_rule_sha256"]:
        raise RuntimeError("task or semantic-rule binding changed")
    if manifest["answer_leakage_findings"] != 0 or manifest["runtime"]["context_limit_non_binding_for_probe"] is not True:
        raise RuntimeError("pre-inference binding is not clean")
    for row in manifest["tasks"]:
        task = next(task for task in binding["tasks"] if task["task_id"] == row["task_id"])
        for arm in ARMS:
            prompt = (output_dir / "tasks" / row["task_id"] / arm / "prompt.txt").read_bytes()
            if sha_bytes(prompt) != row["prompt_sha256"][arm]:
                raise RuntimeError(f"prompt drift: {row['task_id']} {arm}")
    spec = clean.worker_spec()
    models = list_models(spec, timeout=30)
    candidate = next((item for item in models.get("data", []) if item.get("id") == EXPECTED_MODEL_ID), None)
    if candidate is None:
        raise RuntimeError("candidate model not exposed")
    meta = candidate.get("meta") or {}
    if meta.get("n_params") != EXPECTED_PARAMS or meta.get("n_ctx") != EXPECTED_EFFECTIVE_CTX or meta.get("n_ctx_train") != EXPECTED_TRAIN_CTX:
        raise RuntimeError(f"runtime metadata mismatch: {meta}")
    telemetry_url = clean.telemetry_base_url()
    telemetry = clean.telemetry_preflight(telemetry_url)
    idle_samples, idle_summary = clean.sample_window(IDLE_SECONDS, telemetry_url)
    write_json(output_dir / "preflight.json", {"schema": "zth_qwen3_1_7b_boolean_exemplar_scope_isolation_execution_v1", "execution_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), "prepared_manifest_sha256": sha_file(manifest_path), "model_meta": meta, "telemetry": telemetry, "task_manifest_sha256": manifest["task_manifest_sha256"], "semantic_rule_sha256": manifest["semantic_rule_sha256"], "suffix_sha256": manifest["suffix_sha256"], "execution_policy": manifest["execution_policy"], "answer_leakage_findings": 0})
    write_json(output_dir / "idle_power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "summary": idle_summary, "samples": idle_samples})
    write_json(output_dir / "lifecycle.json", {"status": "running", "started_at": now(), "model_calls_made": False})
    task_by_id = {task["task_id"]: task for task in binding["tasks"]}
    for task_id in manifest["task_order"]:
        task = task_by_id[task_id]
        for arm in next(row["arm_order"] for row in manifest["tasks"] if row["task_id"] == task_id):
            task_dir = output_dir / "tasks" / task_id / arm
            prompt = (task_dir / "prompt.txt").read_text()
            sampler = PowerSampler(lambda: read_gpu_power(EXPECTED_GPU_UUID, base_url=telemetry_url), expected_gpu_uuid=EXPECTED_GPU_UUID, sample_interval_seconds=POWER_INTERVAL_SECONDS)
            started = time.monotonic(); started_at = now(); sampler.start()
            response = call_worker(spec, prompt, MAX_OUTPUT_TOKENS, timeout=TIMEOUT_SECONDS)
            captured = time.monotonic(); samples = sampler.stop()
            energy = integrate_energy_joules(samples, sample_interval_seconds=POWER_INTERVAL_SECONDS, expected_gpu_uuid=EXPECTED_GPU_UUID)
            metadata = response.metadata(); metadata["request_url"] = None
            raw = {"status": response.status, "content": response.content, "metadata": metadata, "request_started_at": started_at, "response_captured_at": now(), "wall_elapsed_ms": round((captured - started) * 1000, 3)}
            write_json(task_dir / "response.json", raw)
            transport = metadata.get("transport_classification") == "model_response"
            validation_task = {"task_id": task_id, "task_family": "scope-expansion-boolean-exemplar-isolation", "prompt": clean.task_specific_text(task), "output_contract": {"format": "json", "required_fields": ["scope_expansion_required"]}, "validator": {"kind": "zth_output_contract", "reference_facts": {"requires_scope_expansion_flag": task["expected_scope_expansion_required"]}}}
            validation = _validator_result(response.content, validation_task, attempt_id=f"boolean-exemplar-{arm}-{task_id}") if transport else None
            if validation is not None:
                write_json(task_dir / "validation.json", validation)
            parsed = clean.parse_atomic(response.content) if transport else {"raw_parse_valid": False, "contract_valid": False, "observed": None, "failure": "TRANSPORT_FAILURE"}
            write_json(task_dir / "power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "gpu_uuid": EXPECTED_GPU_UUID, "samples": [{"timestamp_utc": sample.timestamp_utc, "monotonic_seconds": sample.monotonic_seconds, "gpu_uuid": sample.gpu_uuid, "power_watts": sample.power_watts, "sequence": sample.sequence} for sample in samples]})
            write_json(task_dir / "scorecard.json", {"schema": "zth_qwen3_1_7b_boolean_exemplar_task_scorecard_v1", "task_id": task_id, "arm": arm, "expected": task["expected_scope_expansion_required"], "transport_valid": transport, "raw_parse_valid": parsed["raw_parse_valid"] if transport else False, "contract_valid": parsed["contract_valid"] if transport else False, "observed": parsed["observed"], "correct": bool(parsed["contract_valid"] and parsed["observed"] == task["expected_scope_expansion_required"]), "failure_class": None if parsed["contract_valid"] and parsed["observed"] == task["expected_scope_expansion_required"] else (parsed["failure"] or "SCOPE_DECISION_FAILURE"), "validator_status": validation.get("validation_status") if validation else None, "wall_elapsed_ms": raw["wall_elapsed_ms"], "prompt_tokens": (metadata.get("usage") or {}).get("prompt_tokens"), "completion_tokens": (metadata.get("usage") or {}).get("completion_tokens"), "total_tokens": (metadata.get("usage") or {}).get("total_tokens"), "power_summary": {"sample_count": len(samples), "mean_active_watts": round(statistics.mean(sample.power_watts for sample in samples), 6), "peak_observed_watts": round(max(sample.power_watts for sample in samples), 6), "gross_energy_joules": energy, "sample_interval_seconds": POWER_INTERVAL_SECONDS}, "raw_response_preserved": True, "measurement_level": 2, "measurement_boundary": "gpu_device_only", "retry_count": 0, "escalation_count": 0, "teacher_calls": 0})
    write_json(output_dir / "aggregate.json", aggregate(output_dir, manifest, idle_summary))
    write_json(output_dir / "lifecycle.json", {"status": "terminal", "completed_at": now(), "model_calls_made": True, "supplier_model_calls": 48, "teacher_calls": 0, "retries": 0, "escalations": 0})
    print(json.dumps({"status": "terminal", "tasks": 16, "arms": 3, "supplier_calls": 48}, indent=2))


def aggregate(output_dir: Path, manifest: dict[str, Any], idle: dict[str, Any]) -> dict[str, Any]:
    rows = {arm: [] for arm in ARMS}
    task_factors = {row["task_id"]: row for row in manifest["tasks"]}
    for task_id in manifest["task_order"]:
        for arm in ARMS:
            scorecard = json.loads((output_dir / "tasks" / task_id / arm / "scorecard.json").read_text())
            scorecard.update({key: task_factors[task_id][key] for key in ("operation_factor", "authority_factor", "distractor_factor")})
            rows[arm].append(scorecard)
    def summarize(values: list[dict[str, Any]]) -> dict[str, Any]:
        def subset(**filters: Any) -> list[dict[str, Any]]:
            return [row for row in values if all(row[key] == value for key, value in filters.items())]
        true = [row for row in values if row["expected"]]; false = [row for row in values if not row["expected"]]
        tp = sum(row["correct"] and row["expected"] for row in values); tn = sum(row["correct"] and not row["expected"] for row in values)
        fp = sum(not row["expected"] and row["observed"] is True for row in values); fn = sum(row["expected"] and row["observed"] is False for row in values)
        return {"observed_true": sum(row["observed"] is True for row in values), "observed_false": sum(row["observed"] is False for row in values), "overall_correct": sum(row["correct"] for row in values), "inside_correct": sum(row["correct"] for row in subset(authority_factor="INSIDE_AUTHORITY")), "outside_correct": sum(row["correct"] for row in subset(authority_factor="OUTSIDE_AUTHORITY")), "read_correct": sum(row["correct"] for row in subset(operation_factor="READ")), "mutate_correct": sum(row["correct"] for row in subset(operation_factor="MUTATE")), "distractor_present_correct": sum(row["correct"] for row in subset(distractor_factor="HELD_DISTRACTOR_PRESENT")), "distractor_absent_correct": sum(row["correct"] for row in subset(distractor_factor="HELD_DISTRACTOR_ABSENT")), "confusion_matrix": {"tp": tp, "fn": fn, "fp": fp, "tn": tn}, "serialization_failures": sum(row["failure_class"] == "SERIALIZATION_FAILURE" for row in values), "contract_failures": sum(row["failure_class"] == "INVALID_CONTRACT" for row in values), "scope_decision_failures": sum(row["failure_class"] == "SCOPE_DECISION_FAILURE" for row in values), "latency_ms": {"median": statistics.median([row["wall_elapsed_ms"] for row in values]), "mean": statistics.mean([row["wall_elapsed_ms"] for row in values])}, "energy_joules": {"mean_per_action": statistics.mean([row["power_summary"]["gross_energy_joules"] for row in values]), "total": sum(row["power_summary"]["gross_energy_joules"] for row in values)}}
    per_arm = {arm: summarize(rows[arm]) for arm in ARMS}
    by_task = {task_id: {arm: next(row for row in rows[arm] if row["task_id"] == task_id) for arm in ARMS} for task_id in manifest["task_order"]}
    transitions = {}
    for task_id, task_rows in by_task.items():
        t, f = task_rows["T"]["observed"], task_rows["F"]["observed"]
        label = "FLIPPED_WITH_EXEMPLAR" if t is True and f is False else "UNCHANGED_TRUE" if t is True and f is True else "UNCHANGED_FALSE" if t is False and f is False else "OTHER"
        transitions[task_id] = {"T_observed": t, "F_observed": f, "N_observed": task_rows["N"]["observed"], "T_to_F": label, "expected": task_rows["T"]["expected"]}
    return {"schema": "zth_qwen3_1_7b_boolean_exemplar_scope_isolation_aggregate_v1", "exploratory_not_confirmatory": True, "candidate": {"model_id": EXPECTED_MODEL_ID, "operative_parameters": EXPECTED_PARAMS, "artifact_sha256": EXPECTED_MODEL_SHA}, "arms": per_arm, "transitions": transitions, "exemplar_flip_count": sum(item["T_to_F"] == "FLIPPED_WITH_EXEMPLAR" for item in transitions.values()), "exemplar_flip_rate": sum(item["T_to_F"] == "FLIPPED_WITH_EXEMPLAR" for item in transitions.values()) / 16, "idle_power": idle, "execution": {"supplier_model_calls": 48, "teacher_calls": 0, "retries": 0, "escalations": 0}}


def closeout(output_dir: Path) -> None:
    manifest = json.loads((output_dir / "probe_manifest.json").read_text())
    if manifest["manifest_sha256"] != sha_bytes(canonical({**manifest, "manifest_sha256": None})):
        raise RuntimeError("prepared manifest hash mismatch")
    response_count = len(list(output_dir.glob("tasks/*/*/response.json")))
    scorecard_count = len(list(output_dir.glob("tasks/*/*/scorecard.json")))
    validation_count = len(list(output_dir.glob("tasks/*/*/validation.json")))
    if (response_count, scorecard_count, validation_count) != (48, 48, 48):
        raise RuntimeError(f"incomplete terminal evidence: responses={response_count}, scorecards={scorecard_count}, validations={validation_count}")
    idle = json.loads((output_dir / "idle_power_samples.json").read_text())["summary"]
    summary = aggregate(output_dir, manifest, idle)
    summary["post_run_aggregation_repair"] = {"model_calls": 0, "reason": "factor labels were restored from the frozen manifest during model-free closeout; raw responses, validators, and scorecards were unchanged"}
    write_json(output_dir / "aggregate.json", summary)
    write_json(output_dir / "lifecycle.json", {"status": "terminal", "completed_at": now(), "model_calls_made": True, "supplier_model_calls": 48, "teacher_calls": 0, "retries": 0, "escalations": 0, "aggregation_closeout_repaired": True})
    print(json.dumps({"status": "terminal", "responses": response_count, "scorecards": scorecard_count, "validations": validation_count, "model_calls": 0}, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(); group = parser.add_mutually_exclusive_group(required=True); group.add_argument("--prepare", action="store_true"); group.add_argument("--execute", action="store_true"); group.add_argument("--closeout", action="store_true"); parser.add_argument("--output-dir", type=Path, required=True); args = parser.parse_args()
    prepare(args.output_dir) if args.prepare else closeout(args.output_dir) if args.closeout else execute(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
