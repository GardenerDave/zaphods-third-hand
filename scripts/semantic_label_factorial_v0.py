#!/usr/bin/env python3
"""Freeze and future execution driver for the 2x2 semantic-label factorial."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from pathlib import Path
from typing import Any

from local_harness.stage_a_power_telemetry import PowerSampler, integrate_energy_joules, read_gpu_power
from scripts import true_semantic_fallback_v2 as base_v2
from scripts import zth_qwen3_0_6b_clean_scope_logic_probe as telemetry_provider
from scripts import zth_qwen3_1_7b_atomic_scope_relation_decomposition as decomposition
from scripts import zth_qwen3_1_7b_clean_scope_logic_probe as runtime

ROOT = runtime.ROOT
RUN = ROOT / ".work/model_size_supplier_floor/semantic_label_factorial_v0/run_20260823T230100Z"
RUNTIME_CASES = ROOT / "docs/research/SEMANTIC_LABEL_FACTORIAL_V0_RUNTIME_CASES_2026-08-23.json"
EVALUATOR_CASES = ROOT / "docs/research/SEMANTIC_LABEL_FACTORIAL_V0_EVALUATOR_CASES_2026-08-23.json"
PAIR_AUDIT = ROOT / "docs/research/SEMANTIC_LABEL_FACTORIAL_V0_PAIR_AUDIT_2026-08-23.json"
REGISTRY = ROOT / "docs/research/SEMANTIC_LABEL_FACTORIAL_V0_REGISTRY_2026-08-23.json"
FIXTURE_REVIEW = ROOT / "docs/research/SEMANTIC_LABEL_FACTORIAL_V0_FIXTURE_REVIEW_2026-08-23.json"
MODEL_ID = runtime.EXPECTED_MODEL_ID
MODEL_SHA = runtime.EXPECTED_MODEL_SHA
PARAMS = runtime.EXPECTED_PARAMS
GPU_UUID = runtime.EXPECTED_GPU_UUID
MAX_TOKENS = runtime.MAX_OUTPUT_TOKENS
TIMEOUT = runtime.TIMEOUT_SECONDS
POWER_INTERVAL = runtime.POWER_INTERVAL_SECONDS
ARM_LABELS = {
    "A": {"presence": "observe_presence", "inspect": "inspect", "unresolved": "unresolved"},
    "B": {"presence": "class_alpha", "inspect": "class_beta", "unresolved": "unresolved"},
    "C": {"presence": "class_alpha", "inspect": "inspect", "unresolved": "unresolved"},
    "D": {"presence": "observe_presence", "inspect": "class_beta", "unresolved": "unresolved"},
}
ARM_ENUMS = {
    "A": ["inspect", "observe_presence", "unresolved"],
    "B": ["class_beta", "class_alpha", "unresolved"],
    "C": ["inspect", "class_alpha", "unresolved"],
    "D": ["class_beta", "observe_presence", "unresolved"],
}
ARM_CANONICAL = {arm: {labels["presence"]: "observe_presence", labels["inspect"]: "inspect"} for arm, labels in ARM_LABELS.items()}
AUTHORITY_FIXTURES = {
    "slff-001": {"allowed_targets": ["docs/research/R1_COPPER_2026-08-23.md"], "allowed_observation_operations": ["observe_presence", "inspect"]},
    "slff-002": {"allowed_targets": ["docs/research/R2_DUSK_2026-08-23.json"], "allowed_observation_operations": ["observe_presence", "inspect"]},
    "slff-003": {"allowed_targets": ["docs/research/R3_FIR_2026-08-23.txt"], "allowed_observation_operations": ["observe_presence", "inspect"]},
    "slff-004": {"allowed_targets": ["docs/research/R4_MOSS_2026-08-23.md"], "allowed_observation_operations": ["observe_presence", "inspect"]},
    "slff-005": {"allowed_targets": ["docs/research/R5_PEPPER_2026-08-23.json"], "allowed_observation_operations": ["observe_presence", "inspect"]},
    "slff-006": {"allowed_targets": ["docs/research/R6_SUNSET_2026-08-23.txt"], "allowed_observation_operations": ["observe_presence", "inspect"]},
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
        ("slff-001", "observe_presence", "Would you determine if docs/research/R1_COPPER_2026-08-23.md is on hand in this repository?"),
        ("slff-002", "inspect", "Provide a close reading of docs/research/R2_DUSK_2026-08-23.json."),
        ("slff-003", "observe_presence", "Can you establish whether docs/research/R3_FIR_2026-08-23.txt resides in this tree?"),
        ("slff-004", "inspect", "Take some time with docs/research/R4_MOSS_2026-08-23.md."),
        ("slff-005", "observe_presence", "Please tell me whether docs/research/R5_PEPPER_2026-08-23.json is available here."),
        ("slff-006", "inspect", "Give docs/research/R6_SUNSET_2026-08-23.txt your attention."),
    ]


def runtime_cases() -> list[dict[str, Any]]:
    return [{"task_id": task_id, "input_request": request, "environment_facts": {"authority_record": json.loads(json.dumps(AUTHORITY_FIXTURES[task_id]))}} for task_id, _, request in specs()]


def evaluator_cases() -> list[dict[str, Any]]:
    return [{"task_id": task_id, "expected_semantic_class": expected, "expected_model_required": True} for task_id, expected, _ in specs()]


def prompt(request: str, arm: str) -> str:
    labels = ARM_LABELS[arm]
    return (f"Request clause:\n{request}\n\nClassify only the requested operation class.\n"
            f"{labels['presence']} means determine whether the named target exists, is present, or is available.\n"
            f"{labels['inspect']} means examine or look at the named target.\n"
            f"{labels['unresolved']} means the operation class is ambiguous, unsupported, or cannot be determined safely.\n\n"
            "Return only operation_class_candidate in the required structured object. Do not identify the target, choose a tool, decide authorization, or decide task success.\n/no_think")


def schema(arm: str) -> dict[str, Any]:
    return {"type": "object", "properties": {"operation_class_candidate": {"type": "string", "enum": list(ARM_ENUMS[arm])}}, "required": ["operation_class_candidate"], "additionalProperties": False}


def response_format(arm: str) -> dict[str, Any]:
    return {"type": "json_schema", "json_schema": {"name": "bounded_operation_class_candidate_factorial_v0", "schema": schema(arm)}}


def parse_response(content: str, arm: str) -> tuple[str | None, bool, bool, list[str]]:
    try:
        value = json.loads(content)
    except json.JSONDecodeError as exc:
        return None, False, False, [str(exc)]
    contract = isinstance(value, dict) and set(value) == {"operation_class_candidate"} and isinstance(value.get("operation_class_candidate"), str)
    candidate = value.get("operation_class_candidate") if contract else None
    valid = contract and candidate in ARM_ENUMS[arm]
    return candidate if valid else None, True, valid, [] if valid else ["strict enum-only operation class contract failed"]


def validate_and_map_candidate(candidate: str | None, arm: str, parse_valid: bool, contract_valid: bool) -> dict[str, Any]:
    candidate_valid = bool(candidate is not None and candidate in ARM_ENUMS[arm])
    candidate_admissible = bool(candidate_valid and candidate in ARM_CANONICAL[arm])
    return {"candidate": candidate, "parse_valid": parse_valid, "contract_valid": contract_valid, "candidate_valid": candidate_valid, "candidate_admissible": candidate_admissible, "canonical_operation": ARM_CANONICAL[arm].get(candidate) if candidate_admissible else None}


def model_settings() -> dict[str, Any]:
    return {"model_id": MODEL_ID, "model_sha256": MODEL_SHA, "operative_parameters": PARAMS, "gpu_uuid": GPU_UUID, "max_tokens": MAX_TOKENS, "timeout_seconds": TIMEOUT, "power_interval_seconds": POWER_INTERVAL, "temperature": 0.2}


def normalized_prompt(prompt_text: str, arm: str) -> str:
    labels = ARM_LABELS[arm]
    return prompt_text.replace(labels["presence"], "__PRESENCE_LABEL__").replace(labels["inspect"], "__INSPECT_LABEL__").replace(labels["unresolved"], "__UNRESOLVED_LABEL__")


def execution_schedule(task_ids: list[str]) -> list[dict[str, str]]:
    rotations = [("A", "B", "C", "D"), ("B", "C", "D", "A"), ("C", "D", "A", "B"), ("D", "A", "B", "C"), ("A", "C", "B", "D"), ("B", "D", "A", "C")]
    return [{"task_id": task_id, "arm": arm} for task_id, rotation in zip(task_ids, rotations) for arm in rotation]


def historical_requests() -> set[str]:
    paths = [
        ROOT / "docs/research/TRUE_SEMANTIC_FALLBACK_V1_RUNTIME_CASES_2026-08-23.json",
        ROOT / "docs/research/TRUE_SEMANTIC_FALLBACK_V2_RUNTIME_CASES_2026-08-23.json",
        ROOT / "docs/research/SEMANTIC_ENUM_ORDER_COUNTERFACTUAL_V0_RUNTIME_CASES_2026-08-23.json",
        ROOT / "docs/research/SEMANTIC_LABEL_COUNTERFACTUAL_V0_RUNTIME_CASES_2026-08-23.json",
    ]
    result = set()
    for path in paths:
        if path.exists():
            result.update(item["input_request"] for item in read_json(path)["cases"])
    return result


def prepare(out: Path) -> None:
    if out.exists() and any(out.iterdir()):
        raise RuntimeError("fresh factorial run required")
    cases, evaluators = runtime_cases(), evaluator_cases()
    assert len(cases) == len(evaluators) == 6
    assert all(case["input_request"] not in historical_requests() for case in cases)
    preflights = [base_v2.preflight(case["input_request"]) for case in cases]
    assert all(pre["semantic_fallback_eligible"] and pre["model_required"] and pre["remaining_candidate_operation_classes"] == ["observe_presence", "inspect"] for pre in preflights)
    task_ids = [case["task_id"] for case in cases]
    schedule = execution_schedule(task_ids)
    assert len(schedule) == 24
    assert all(sum(item["arm"] == arm for item in schedule) == 6 for arm in ("A", "B", "C", "D"))
    assert all(sum(schedule[index * 4 + position]["arm"] == arm for index in range(6)) in (1, 2) for arm in ("A", "B", "C", "D") for position in range(4))
    out.mkdir(parents=True, exist_ok=True)
    write_json(RUNTIME_CASES, {"schema": "zth_semantic_label_factorial_v0_runtime_cases", "cases": cases})
    write_json(EVALUATOR_CASES, {"schema": "zth_semantic_label_factorial_v0_evaluator_cases", "cases": evaluators})
    write_json(REGISTRY, {"schema": "zth_semantic_label_factorial_v0_registry", "automatic_promotion": False, "arms": ARM_LABELS, "entries": [{"capability_id": "semantic.bounded_operation_classification", "supplier_id": "qwen3_1_7b_bounded_operation_class_candidate_supplier", "supplier_type": "MODEL", "status": "EXPERIMENTAL_CANDIDATE", "qualification_decision": "no promotion"}]})
    fixture_rows, pair_rows = [], []
    for index, case in enumerate(cases):
        pre = preflights[index]; expected = evaluators[index]["expected_semantic_class"]
        definition = "observe_presence means determine whether the named target exists, is present, or is available." if expected == "observe_presence" else "inspect means examine or look at the named target."
        fixture_rows.append({"task_id": case["task_id"], "request": case["input_request"], "intended_semantic_class": expected, "definition_supporting_intended_class": definition, "preflight_status": pre["operation_derivation_status"], "semantic_fallback_eligible": pre["semantic_fallback_eligible"]})
        for arm in ("A", "B", "C", "D"):
            arm_dir = out / "tasks" / case["task_id"] / arm
            write_json(arm_dir / "runtime_task.json", case); write_json(arm_dir / "preflight.json", pre); write_json(arm_dir / "semantic_information_gap.json", {"unknown_decision_critical_fact": "which bounded semantic operation class the request expresses", "remaining_candidate_classes": ["observe_presence", "inspect"], "why_deterministic_resolution_is_insufficient": "request is outside the frozen deterministic operation grammar"}); write_json(arm_dir / "capability_plan_0.json", base_v2.plan(case["task_id"], pre)); (arm_dir / "prompt.txt").write_text(prompt(case["input_request"], arm), encoding="utf-8"); write_json(arm_dir / "schema.json", schema(arm)); write_json(arm_dir / "model_settings.json", model_settings())
        arm_dirs = {arm: out / "tasks" / case["task_id"] / arm for arm in ("A", "B", "C", "D")}
        pair_rows.append({"task_id": case["task_id"], "request_identity": len({sha_file(d / "runtime_task.json") for d in arm_dirs.values()}) == 1, "authority_identity": len({sha_bytes(canonical(read_json(d / "runtime_task.json")["environment_facts"]["authority_record"])) for d in arm_dirs.values()}) == 1, "preflight_identity": len({sha_file(d / "preflight.json") for d in arm_dirs.values()}) == 1, "model_settings_identity": len({sha_file(d / "model_settings.json") for d in arm_dirs.values()}) == 1, "definition_equivalence": len({normalized_prompt((d / "prompt.txt").read_text(), arm) for arm, d in arm_dirs.items()}) == 1, "semantic_positions_identical": [ARM_ENUMS[arm][0] for arm in ("A", "B", "C", "D")] == ["inspect", "class_beta", "inspect", "class_beta"] and [ARM_ENUMS[arm][1] for arm in ("A", "B", "C", "D")] == ["observe_presence", "class_alpha", "class_alpha", "observe_presence"]})
    assert [row["intended_semantic_class"] for row in fixture_rows] == ["observe_presence", "inspect", "observe_presence", "inspect", "observe_presence", "inspect"]
    assert all(all(row[key] for key in ("request_identity", "authority_identity", "preflight_identity", "model_settings_identity", "definition_equivalence", "semantic_positions_identical")) for row in pair_rows)
    write_json(FIXTURE_REVIEW, {"schema": "zth_semantic_label_factorial_v0_fixture_review", "runtime_input": False, "rows": fixture_rows})
    write_json(PAIR_AUDIT, {"schema": "zth_semantic_label_factorial_v0_pair_audit", "rows": pair_rows, "request_identity": True, "authority_identity": True, "preflight_identity": True, "model_settings_identity": True, "definitions_equivalent_after_label_normalization": True, "semantic_enum_positions_identical": True, "surface_label_mapping_frozen": True, "only_model_visible_intervention": "LABEL_TOKENS"})
    write_json(out / "execution_order.json", {"schedule": schedule, "counterbalanced": True, "arm_counts": {arm: 6 for arm in ("A", "B", "C", "D")}, "position_counts": [{arm: sum(schedule[index * 4 + position]["arm"] == arm for index in range(6)) for arm in ("A", "B", "C", "D")} for position in range(4)], "cross_arm_input": False})
    write_json(out / "router_manifest.json", {"schema": "zth_semantic_label_factorial_v0_manifest", "status": "prepared_model_free", "task_count": 6, "arm_count": 4, "planned_model_calls": 24, "model_calls_made": 0, "tool_calls_made": 0, "response_files": 0, "true_fallback_eligibility": 6, "historical_request_reuse": 0, "paired_input_identity_audit": True, "authority_provenance_audit": True, "definition_equivalence_audit": True, "semantic_enum_positions_identical": True, "surface_label_mapping_frozen": True, "balanced_schedule_audit": True, "runtime_evaluator_influence": 0, "model_output_granted_authority": 0, "qualification_change": False, "driver_sha256": sha_file(Path(__file__).resolve()), "model_settings": model_settings(), "arms": ARM_LABELS, "enums": ARM_ENUMS})
    write_json(out / "lifecycle.json", {"status": "prepared", "model_calls": 0, "tool_calls": 0, "retries": 0})
    print(json.dumps({"status": "prepared", "fresh_tasks": 6, "arms": 4, "planned_model_calls": 24, "MODEL_CALLS_MADE": 0, "TOOL_CALLS_MADE": 0, "response_files": 0}, indent=2))


def model_preflight(out: Path):
    spec = runtime.worker_spec(); models = decomposition.list_models(spec, timeout=30); candidate = next((item for item in models.get("data", []) if item.get("id") == MODEL_ID), None); meta = (candidate or {}).get("meta") or {}
    if candidate is None or meta.get("n_params") != PARAMS: raise RuntimeError("model binding mismatch")
    telemetry_url = telemetry_provider.telemetry_base_url(); telemetry = telemetry_provider.telemetry_preflight(telemetry_url); write_json(out / "model_preflight.json", {"model_meta": meta, "telemetry": telemetry, "model_id": MODEL_ID, "telemetry_provider": "scripts.zth_qwen3_0_6b_clean_scope_logic_probe"}); return spec, telemetry_url


def execute(out: Path) -> None:
    spec, telemetry_url = model_preflight(out); calls = 0
    for item in read_json(out / "execution_order.json")["schedule"]:
        d = out / "tasks" / item["task_id"] / item["arm"]; write_json(d / "call_started.json", {"task_id": item["task_id"], "arm": item["arm"], "started_at": time.time(), "prompt_sha256": sha_file(d / "prompt.txt"), "schema_sha256": sha_file(d / "schema.json"), "model_id": MODEL_ID})
        sampler = PowerSampler(lambda: read_gpu_power(GPU_UUID, base_url=telemetry_url), expected_gpu_uuid=GPU_UUID, sample_interval_seconds=POWER_INTERVAL); started = time.monotonic(); sampler.start(); response = decomposition.structured_call(spec, (d / "prompt.txt").read_text(encoding="utf-8"), response_format(item["arm"]), MAX_TOKENS, TIMEOUT); elapsed = time.monotonic() - started; samples = sampler.stop(); energy = integrate_energy_joules(samples, sample_interval_seconds=POWER_INTERVAL, expected_gpu_uuid=GPU_UUID); metadata = response.metadata(); metadata["request_url"] = None
        write_json(d / "response.json", {"status": response.status, "content": response.content, "metadata": metadata, "wall_elapsed_ms": round(elapsed * 1000, 3), "gross_energy_joules": energy}); write_json(d / "power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "gpu_uuid": GPU_UUID, "samples": [{"timestamp_utc": s.timestamp_utc, "power_watts": s.power_watts, "gpu_uuid": s.gpu_uuid, "sequence": s.sequence} for s in samples]}); candidate, parse_valid, contract_valid, diagnostics = parse_response(response.content, item["arm"]); validation = validate_and_map_candidate(candidate, item["arm"], parse_valid, contract_valid); validation["diagnostics"] = diagnostics; calls += 1; write_json(d / "candidate_validation.json", validation)
        if validation["candidate_admissible"]: write_json(d / "operation_derivation_1.json", {"status": "RESOLVED", "surface_label": candidate, "canonical_operation": validation["canonical_operation"], "derivation_type": "PRIOR_MODEL_STEP_LABEL_MAPPING", "model_output_granted_authority": False}); write_json(d / "capability_plan_1.json", base_v2.plan(item["task_id"], read_json(d / "preflight.json"), validation["canonical_operation"])); result = {"canonical_operation": validation["canonical_operation"], "model_calls": 1, "tool_calls": 0, "terminal_state": "review_or_deferred_execution"}
        else: result = {"canonical_operation": None, "model_calls": 1, "tool_calls": 0, "terminal_state": "ready_for_review"}
        write_json(d / "runtime_result.json", result)
    write_json(out / "lifecycle.json", {"status": "terminal_runtime", "model_calls": calls, "tool_calls": 0, "retries": 0, "runtime_evaluator_influence": 0, "model_output_granted_authority": 0})


def closeout(out: Path) -> None:
    evaluators = {item["task_id"]: item for item in read_json(EVALUATOR_CASES)["cases"]}; rows = []
    for task_id, expected, _ in specs():
        for arm in ("A", "B", "C", "D"):
            d = out / "tasks" / task_id / arm; val = read_json(d / "candidate_validation.json"); result = read_json(d / "runtime_result.json"); rows.append({"task_id": task_id, "arm": arm, "expected": expected, "surface_label": val.get("candidate"), "canonical_operation": result.get("canonical_operation"), "semantic_correct": result.get("canonical_operation") == expected, "parse_valid": val.get("parse_valid"), "contract_valid": val.get("contract_valid"), "candidate_valid": val.get("candidate_valid"), "candidate_admissible": val.get("candidate_admissible")})
    write_json(out / "aggregate.json", {"schema": "zth_semantic_label_factorial_v0_aggregate", "arm_scores": {arm: sum(row["semantic_correct"] for row in rows if row["arm"] == arm) for arm in ("A", "B", "C", "D")}, "rows": rows})


def main() -> None:
    parser = argparse.ArgumentParser(); group = parser.add_mutually_exclusive_group(required=True); group.add_argument("--prepare", action="store_true"); group.add_argument("--execute", action="store_true"); group.add_argument("--closeout", action="store_true"); parser.add_argument("--output-dir", type=Path, default=RUN); args = parser.parse_args(); (prepare if args.prepare else execute if args.execute else closeout)(args.output_dir)


if __name__ == "__main__":
    main()
