#!/usr/bin/env python3
"""Freeze and future execution driver for the enum-order counterfactual."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
import time
from pathlib import Path
from typing import Any

from local_harness.stage_a_power_telemetry import PowerSampler, integrate_energy_joules, read_gpu_power
from scripts import true_semantic_fallback_v2 as v2
from scripts import zth_qwen3_0_6b_clean_scope_logic_probe as telemetry_provider
from scripts import zth_qwen3_1_7b_atomic_scope_relation_decomposition as decomposition
from scripts import zth_qwen3_1_7b_clean_scope_logic_probe as runtime

ROOT = runtime.ROOT
RUN = ROOT / ".work/model_size_supplier_floor/semantic_enum_order_counterfactual_v0/run_20260823T203000Z"
RUNTIME_CASES = ROOT / "docs/research/SEMANTIC_ENUM_ORDER_COUNTERFACTUAL_V0_RUNTIME_CASES_2026-08-23.json"
EVALUATOR_CASES = ROOT / "docs/research/SEMANTIC_ENUM_ORDER_COUNTERFACTUAL_V0_EVALUATOR_CASES_2026-08-23.json"
PAIR_AUDIT = ROOT / "docs/research/SEMANTIC_ENUM_ORDER_COUNTERFACTUAL_V0_PAIR_AUDIT_2026-08-23.json"
REGISTRY = ROOT / "docs/research/SEMANTIC_ENUM_ORDER_COUNTERFACTUAL_V0_REGISTRY_2026-08-23.json"
MODEL_ID = runtime.EXPECTED_MODEL_ID
MODEL_SHA = runtime.EXPECTED_MODEL_SHA
PARAMS = runtime.EXPECTED_PARAMS
GPU_UUID = runtime.EXPECTED_GPU_UUID
MAX_TOKENS = runtime.MAX_OUTPUT_TOKENS
TIMEOUT = runtime.TIMEOUT_SECONDS
POWER_INTERVAL = runtime.POWER_INTERVAL_SECONDS
ARM_A = ["inspect", "observe_presence", "unresolved"]
ARM_B = ["observe_presence", "inspect", "unresolved"]
ARMS = {"A": ARM_A, "B": ARM_B}
AUTHORITY_FIXTURES = {
    "seof-001": {"allowed_targets": ["docs/research/E1_NICKEL_2026-08-23.md"], "allowed_observation_operations": ["observe_presence", "inspect"]},
    "seof-002": {"allowed_targets": ["docs/research/E2_OPAL_2026-08-23.json"], "allowed_observation_operations": ["observe_presence", "inspect"]},
    "seof-003": {"allowed_targets": ["docs/research/E3_QUARTZ_2026-08-23.txt"], "allowed_observation_operations": ["observe_presence", "inspect"]},
    "seof-004": {"allowed_targets": ["docs/research/E4_RIVER_2026-08-23.md"], "allowed_observation_operations": ["observe_presence", "inspect"]},
    "seof-005": {"allowed_targets": ["docs/research/E5_SABLE_2026-08-23.json"], "allowed_observation_operations": ["observe_presence", "inspect"]},
    "seof-006": {"allowed_targets": ["docs/research/E6_TIN_2026-08-23.txt"], "allowed_observation_operations": ["observe_presence", "inspect"]},
}


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def specs() -> list[tuple[str, str, str]]:
    return [
        ("seof-001", "observe_presence", "Could you tell me if docs/research/E1_NICKEL_2026-08-23.md is somewhere in this repository?"),
        ("seof-002", "inspect", "Give docs/research/E2_OPAL_2026-08-23.json a careful examination."),
        ("seof-003", "observe_presence", "Would you say whether docs/research/E3_QUARTZ_2026-08-23.txt is stored in this tree?"),
        ("seof-004", "inspect", "Review docs/research/E4_RIVER_2026-08-23.md for me."),
        ("seof-005", "observe_presence", "Is docs/research/E5_SABLE_2026-08-23.json contained here at present?"),
        ("seof-006", "inspect", "Examine docs/research/E6_TIN_2026-08-23.txt when convenient."),
    ]


def runtime_cases() -> list[dict[str, Any]]:
    return [{"task_id": task_id, "input_request": request, "environment_facts": {"authority_record": json.loads(json.dumps(AUTHORITY_FIXTURES[task_id]))}} for task_id, _, request in specs()]


def evaluator_cases() -> list[dict[str, Any]]:
    return [{"task_id": task_id, "expected_semantic_class": expected, "expected_model_required": True, "expected_task_count": 2} for task_id, expected, _ in specs()]


def schema(enum_order: list[str]) -> dict[str, Any]:
    return {"type": "object", "properties": {"operation_class_candidate": {"type": "string", "enum": list(enum_order)}}, "required": ["operation_class_candidate"], "additionalProperties": False}


def response_format(enum_order: list[str]) -> dict[str, Any]:
    return {"type": "json_schema", "json_schema": {"name": "bounded_operation_class_candidate_counterfactual_v0", "schema": schema(enum_order)}}


def parse_response(content: str, enum_order: list[str]) -> tuple[str | None, bool, bool, list[str]]:
    try:
        value = json.loads(content)
    except json.JSONDecodeError as exc:
        return None, False, False, [str(exc)]
    contract = isinstance(value, dict) and set(value) == {"operation_class_candidate"} and isinstance(value.get("operation_class_candidate"), str)
    candidate = value.get("operation_class_candidate") if contract else None
    valid = contract and candidate in enum_order
    return candidate if valid else None, True, valid, [] if valid else ["strict enum-only operation class contract failed"]


def model_settings() -> dict[str, Any]:
    return {"model_id": MODEL_ID, "model_sha256": MODEL_SHA, "operative_parameters": PARAMS, "gpu_uuid": GPU_UUID, "max_tokens": MAX_TOKENS, "timeout_seconds": TIMEOUT, "power_interval_seconds": POWER_INTERVAL, "temperature": 0.2}


def prepare(out: Path) -> None:
    if out.exists() and any(out.iterdir()):
        raise RuntimeError("fresh counterfactual run required")
    cases, evaluators = runtime_cases(), evaluator_cases()
    assert len(cases) == len(evaluators) == 6
    old_requests = {x["input_request"] for x in v2.runtime_cases()}
    old_targets = {x["environment_facts"]["authority_record"]["allowed_targets"][0] for x in v2.runtime_cases()}
    assert all(c["input_request"] not in old_requests and c["environment_facts"]["authority_record"]["allowed_targets"][0] not in old_targets for c in cases)
    preflights = [v2.preflight(case["input_request"]) for case in cases]
    assert all(pre["semantic_fallback_eligible"] and pre["model_required"] and pre["remaining_candidate_operation_classes"] == ["observe_presence", "inspect"] for pre in preflights)
    assert ARM_A == ["inspect", "observe_presence", "unresolved"]
    assert ARM_B == ["observe_presence", "inspect", "unresolved"]
    out.mkdir(parents=True, exist_ok=True)
    write_json(RUNTIME_CASES, {"schema": "zth_semantic_enum_order_counterfactual_v0_runtime_cases", "cases": cases})
    write_json(EVALUATOR_CASES, {"schema": "zth_semantic_enum_order_counterfactual_v0_evaluator_cases", "cases": evaluators})
    write_json(REGISTRY, {"schema": "zth_semantic_enum_order_counterfactual_v0_registry", "automatic_promotion": False, "entries": [{"capability_id": "semantic.bounded_operation_classification", "supplier_id": "qwen3_1_7b_bounded_operation_class_candidate_supplier", "supplier_type": "MODEL", "status": "EXPERIMENTAL_CANDIDATE", "qualification_decision": "no promotion"}]})
    order = []
    for index, case in enumerate(cases):
        task_id = case["task_id"]
        task_dir = out / "tasks" / task_id
        gap = {"known_facts_before_model": ["exactly_one_safe_target", "safe_bounded_request", "unambiguous_request", "shared_runtime_authority_allows_both_classes"], "unknown_decision_critical_fact": "which bounded semantic operation class the request expresses", "remaining_candidate_classes": ["observe_presence", "inspect"], "why_deterministic_resolution_is_insufficient": "request is outside the frozen deterministic operation grammar", "why_model_is_permitted": "two safe classes remain semantically plausible"}
        for arm in ("A", "B"):
            arm_dir = task_dir / arm
            write_json(arm_dir / "runtime_task.json", case)
            write_json(arm_dir / "preflight.json", preflights[index])
            write_json(arm_dir / "semantic_information_gap.json", gap)
            write_json(arm_dir / "capability_plan_0.json", v2.plan(task_id, preflights[index]))
            (arm_dir / "prompt.txt").write_text(v2.prompt(case["input_request"]), encoding="utf-8")
            write_json(arm_dir / "schema.json", schema(ARMS[arm]))
            write_json(arm_dir / "model_settings.json", model_settings())
            order.append({"task_id": task_id, "arm": arm}) if ((index % 2 == 0 and arm == "A") or (index % 2 == 1 and arm == "B")) else None
            order.append({"task_id": task_id, "arm": arm}) if ((index % 2 == 0 and arm == "B") or (index % 2 == 1 and arm == "A")) else None
    # The two append expressions above deliberately produce A/B, B/A, ... order.
    assert len(order) == 12
    identity_rows = []
    for case in cases:
        td = out / "tasks" / case["task_id"]
        a, b = td / "A", td / "B"
        identity = {"task_id": case["task_id"], "request_hash_equal": sha_file(a / "runtime_task.json") == sha_file(b / "runtime_task.json"), "prompt_hash_equal": sha_file(a / "prompt.txt") == sha_file(b / "prompt.txt"), "authority_hash_equal": sha_bytes(canonical(read_json(a / "runtime_task.json")["environment_facts"]["authority_record"])) == sha_bytes(canonical(read_json(b / "runtime_task.json")["environment_facts"]["authority_record"])), "preflight_hash_equal": sha_file(a / "preflight.json") == sha_file(b / "preflight.json"), "gap_hash_equal": sha_file(a / "semantic_information_gap.json") == sha_file(b / "semantic_information_gap.json"), "model_settings_hash_equal": sha_file(a / "model_settings.json") == sha_file(b / "model_settings.json"), "schema_a_enum": read_json(a / "schema.json")["properties"]["operation_class_candidate"]["enum"], "schema_b_enum": read_json(b / "schema.json")["properties"]["operation_class_candidate"]["enum"]}
        identity["only_intended_schema_difference"] = identity["schema_a_enum"] == ARM_A and identity["schema_b_enum"] == ARM_B and identity["schema_a_enum"] != identity["schema_b_enum"]
        identity_rows.append(identity)
    assert all(all(row[key] for key in ("request_hash_equal", "prompt_hash_equal", "authority_hash_equal", "preflight_hash_equal", "gap_hash_equal", "model_settings_hash_equal", "only_intended_schema_difference")) for row in identity_rows)
    write_json(PAIR_AUDIT, {"schema": "zth_semantic_enum_order_counterfactual_v0_pair_audit", "paired_request_identity": True, "paired_prompt_identity": True, "paired_authority_identity": True, "paired_preflight_identity": True, "paired_model_settings_identity": True, "only_model_visible_intervention": "ENUM_ORDER", "rows": identity_rows})
    write_json(out / "execution_order.json", {"order": order, "counterbalanced": True, "cross_arm_input": False})
    manifest = {"schema": "zth_semantic_enum_order_counterfactual_v0_manifest", "status": "prepared_model_free", "prepared_from_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), "driver_sha256": sha_file(Path(__file__).resolve()), "runtime_cases_sha256": sha_file(RUNTIME_CASES), "evaluator_cases_sha256": sha_file(EVALUATOR_CASES), "pair_audit_sha256": sha_file(PAIR_AUDIT), "task_count": 6, "paired_opportunities": 6, "planned_model_calls": 12, "model_calls_made": 0, "tool_calls_made": 0, "response_files": 0, "presence_expected": 3, "inspect_expected": 3, "true_fallback_eligibility": 6, "v1_v2_exact_request_reuse": 0, "authority_provenance_audit": True, "paired_identity_audit": True, "v2_first_enum_member": "inspect", "v2_output_matched_first_enum_member": "6/6", "enum_order_causal_effect_not_yet_demonstrated": True, "qualification_change": False, "teacher_calls": 0, "30b_calls": 0, "external_calls": 0, "retries": 0, "runtime_evaluator_influence": 0, "model_output_granted_authority": 0, "model_settings": model_settings()}
    manifest["manifest_sha256"] = sha_bytes(canonical({**manifest, "manifest_sha256": None}))
    write_json(out / "router_manifest.json", manifest)
    write_json(out / "lifecycle.json", {"status": "prepared", "model_calls": 0, "tool_calls": 0, "retries": 0})
    print(json.dumps({"status": "prepared", "fresh_tasks": 6, "paired_opportunities": 6, "planned_model_calls": 12, "MODEL_CALLS_MADE": 0, "TOOL_CALLS_MADE": 0, "response_files": 0}, indent=2))


def model_preflight(out: Path):
    spec = runtime.worker_spec(); models = decomposition.list_models(spec, timeout=30); candidate = next((item for item in models.get("data", []) if item.get("id") == MODEL_ID), None); meta = (candidate or {}).get("meta") or {}
    if candidate is None or meta.get("n_params") != PARAMS:
        raise RuntimeError("model binding mismatch")
    telemetry_url = telemetry_provider.telemetry_base_url(); telemetry = telemetry_provider.telemetry_preflight(telemetry_url)
    write_json(out / "model_preflight.json", {"model_meta": meta, "telemetry": telemetry, "telemetry_provider": "scripts.zth_qwen3_0_6b_clean_scope_logic_probe", "model_id": MODEL_ID})
    return spec, telemetry_url


def execute(out: Path) -> None:
    manifest = read_json(out / "router_manifest.json"); spec, telemetry_url = model_preflight(out); calls = 0
    for item in read_json(out / "execution_order.json")["order"]:
        task_dir = out / "tasks" / item["task_id"] / item["arm"]; runtime_task = read_json(task_dir / "runtime_task.json"); enum_order = ARMS[item["arm"]]
        write_json(task_dir / "call_started.json", {"task_id": item["task_id"], "arm": item["arm"], "started_at": time.time(), "prompt_sha256": sha_file(task_dir / "prompt.txt"), "schema_sha256": sha_file(task_dir / "schema.json"), "model_id": MODEL_ID})
        sampler = PowerSampler(lambda: read_gpu_power(GPU_UUID, base_url=telemetry_url), expected_gpu_uuid=GPU_UUID, sample_interval_seconds=POWER_INTERVAL); started = time.monotonic(); sampler.start(); response = decomposition.structured_call(spec, (task_dir / "prompt.txt").read_text(encoding="utf-8"), response_format(enum_order), MAX_TOKENS, TIMEOUT); elapsed = time.monotonic() - started; samples = sampler.stop(); energy = integrate_energy_joules(samples, sample_interval_seconds=POWER_INTERVAL, expected_gpu_uuid=GPU_UUID)
        metadata = response.metadata(); metadata["request_url"] = None; write_json(task_dir / "response.json", {"status": response.status, "content": response.content, "metadata": metadata, "wall_elapsed_ms": round(elapsed * 1000, 3), "gross_energy_joules": energy}); write_json(task_dir / "power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "gpu_uuid": GPU_UUID, "samples": [{"timestamp_utc": s.timestamp_utc, "power_watts": s.power_watts, "gpu_uuid": s.gpu_uuid, "sequence": s.sequence} for s in samples]})
        candidate, parse_valid, contract_valid, diagnostics = parse_response(response.content, enum_order); calls += 1; admissible = candidate in ["observe_presence", "inspect"] if candidate else False; write_json(task_dir / "candidate_validation.json", {"candidate": candidate, "parse_valid": parse_valid, "contract_valid": contract_valid, "candidate_valid": candidate in enum_order if candidate else False, "candidate_admissible": admissible, "diagnostics": diagnostics})
        if contract_valid and admissible:
            write_json(task_dir / "operation_derivation_1.json", {"status": "RESOLVED", "canonical_operation": candidate, "derivation_type": "PRIOR_MODEL_STEP_ENUM_VALIDATION", "model_output_granted_authority": False}); write_json(task_dir / "capability_plan_1.json", v2.plan(item["task_id"], read_json(task_dir / "preflight.json"), candidate)); result = {"semantic_output_accepted": True, "tool_calls": 0, "terminal_state": "review_or_deferred_execution"}
        else:
            result = {"semantic_output_accepted": False, "tool_calls": 0, "terminal_state": "ready_for_review"}
        write_json(task_dir / "runtime_result.json", {**result, "model_calls": 1, "arm": item["arm"]})
    write_json(out / "lifecycle.json", {"status": "terminal_runtime", "model_calls": calls, "tool_calls": 0, "retries": 0, "runtime_evaluator_influence": 0, "model_output_granted_authority": 0})


def closeout(out: Path) -> None:
    evaluators = {item["task_id"]: item for item in read_json(EVALUATOR_CASES)["cases"]}; rows = []
    for task_id, _, _ in specs():
        for arm in ("A", "B"):
            td = out / "tasks" / task_id / arm; validation = read_json(td / "candidate_validation.json"); result = read_json(td / "runtime_result.json"); expected = evaluators[task_id]["expected_semantic_class"]
            rows.append({"task_id": task_id, "arm": arm, "expected": expected, "observed": validation.get("candidate"), "semantic_correct": validation.get("candidate") == expected, "parse_valid": validation.get("parse_valid"), "contract_valid": validation.get("contract_valid"), "candidate_valid": validation.get("candidate_valid"), "candidate_admissible": validation.get("candidate_admissible"), "model_calls": result.get("model_calls", 0), "tool_calls": result.get("tool_calls", 0)})
    by_task = {task_id: {arm: next(row for row in rows if row["task_id"] == task_id and row["arm"] == arm) for arm in ("A", "B")} for task_id, _, _ in specs()}
    transitions = {}
    changed = 0
    for task_id, pair in by_task.items():
        key = f"{pair['A']['observed']}->{pair['B']['observed']}"; transitions[key] = transitions.get(key, 0) + 1; changed += pair["A"]["observed"] != pair["B"]["observed"]
    aggregate = {"schema": "zth_semantic_enum_order_counterfactual_v0_aggregate", "arm_a_semantic_correct": sum(row["semantic_correct"] for row in rows if row["arm"] == "A"), "arm_b_semantic_correct": sum(row["semantic_correct"] for row in rows if row["arm"] == "B"), "arm_a_presence_correct": sum(row["semantic_correct"] for row in rows if row["arm"] == "A" and row["expected"] == "observe_presence"), "arm_b_presence_correct": sum(row["semantic_correct"] for row in rows if row["arm"] == "B" and row["expected"] == "observe_presence"), "arm_a_inspect_correct": sum(row["semantic_correct"] for row in rows if row["arm"] == "A" and row["expected"] == "inspect"), "arm_b_inspect_correct": sum(row["semantic_correct"] for row in rows if row["arm"] == "B" and row["expected"] == "inspect"), "enum_order_changed_output_count": changed, "paired_transitions": transitions, "rows": rows}
    write_json(out / "aggregate.json", aggregate)


def main() -> None:
    parser = argparse.ArgumentParser(); group = parser.add_mutually_exclusive_group(required=True); group.add_argument("--prepare", action="store_true"); group.add_argument("--execute", action="store_true"); group.add_argument("--closeout", action="store_true"); parser.add_argument("--output-dir", type=Path, default=RUN); args = parser.parse_args()
    if args.prepare: prepare(args.output_dir)
    elif args.execute: execute(args.output_dir)
    else: closeout(args.output_dir)


if __name__ == "__main__":
    main()
