#!/usr/bin/env python3
"""Freeze and future execution driver for the neutral semantic-label counterfactual."""

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
from scripts import true_semantic_fallback_v2 as base_v2
from scripts import zth_qwen3_0_6b_clean_scope_logic_probe as telemetry_provider
from scripts import zth_qwen3_1_7b_atomic_scope_relation_decomposition as decomposition
from scripts import zth_qwen3_1_7b_clean_scope_logic_probe as runtime

ROOT = runtime.ROOT
RUN = ROOT / ".work/model_size_supplier_floor/semantic_label_counterfactual_v0/run_20260823T222100Z"
PREDECESSOR_RUN = ROOT / ".work/model_size_supplier_floor/semantic_label_counterfactual_v0/run_20260823T220000Z"
RUNTIME_CASES = ROOT / "docs/research/SEMANTIC_LABEL_COUNTERFACTUAL_V0_RUNTIME_CASES_2026-08-23.json"
EVALUATOR_CASES = ROOT / "docs/research/SEMANTIC_LABEL_COUNTERFACTUAL_V0_EVALUATOR_CASES_2026-08-23.json"
PAIR_AUDIT = ROOT / "docs/research/SEMANTIC_LABEL_COUNTERFACTUAL_V0_PAIR_AUDIT_2026-08-23.json"
REGISTRY = ROOT / "docs/research/SEMANTIC_LABEL_COUNTERFACTUAL_V0_REGISTRY_2026-08-23.json"
FIXTURE_REVIEW = ROOT / "docs/research/SEMANTIC_LABEL_COUNTERFACTUAL_V0_FIXTURE_REVIEW_2026-08-23.json"
MODEL_ID = runtime.EXPECTED_MODEL_ID
MODEL_SHA = runtime.EXPECTED_MODEL_SHA
PARAMS = runtime.EXPECTED_PARAMS
GPU_UUID = runtime.EXPECTED_GPU_UUID
MAX_TOKENS = runtime.MAX_OUTPUT_TOKENS
TIMEOUT = runtime.TIMEOUT_SECONDS
POWER_INTERVAL = runtime.POWER_INTERVAL_SECONDS
ARM_A = {"presence": "observe_presence", "inspect": "inspect", "unresolved": "unresolved"}
ARM_B = {"presence": "class_alpha", "inspect": "class_beta", "unresolved": "unresolved"}
ARM_ENUMS = {"A": ["inspect", "observe_presence", "unresolved"], "B": ["class_beta", "class_alpha", "unresolved"]}
ARM_CANONICAL = {"A": {"observe_presence": "observe_presence", "inspect": "inspect"}, "B": {"class_alpha": "observe_presence", "class_beta": "inspect"}}
AUTHORITY_FIXTURES = {
    "slcf-001": {"allowed_targets": ["docs/research/Q1_VELVET_2026-08-23.md"], "allowed_observation_operations": ["observe_presence", "inspect"]},
    "slcf-002": {"allowed_targets": ["docs/research/Q2_WILLOW_2026-08-23.json"], "allowed_observation_operations": ["observe_presence", "inspect"]},
    "slcf-003": {"allowed_targets": ["docs/research/Q3_YONDER_2026-08-23.txt"], "allowed_observation_operations": ["observe_presence", "inspect"]},
    "slcf-004": {"allowed_targets": ["docs/research/Q4_ZEPHYR_2026-08-23.md"], "allowed_observation_operations": ["observe_presence", "inspect"]},
    "slcf-005": {"allowed_targets": ["docs/research/Q5_ALMOND_2026-08-23.json"], "allowed_observation_operations": ["observe_presence", "inspect"]},
    "slcf-006": {"allowed_targets": ["docs/research/Q6_BRIGHT_2026-08-23.txt"], "allowed_observation_operations": ["observe_presence", "inspect"]},
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
        ("slcf-001", "observe_presence", "Would you be able to establish if docs/research/Q1_VELVET_2026-08-23.md is available within this workspace?"),
        ("slcf-002", "inspect", "Take a detailed look at docs/research/Q2_WILLOW_2026-08-23.json."),
        ("slcf-003", "observe_presence", "Please say if docs/research/Q3_YONDER_2026-08-23.txt can be found in the repository."),
        ("slcf-004", "inspect", "Please assess docs/research/Q4_ZEPHYR_2026-08-23.md."),
        ("slcf-005", "observe_presence", "Could you establish whether docs/research/Q5_ALMOND_2026-08-23.json is present in the repository?"),
        ("slcf-006", "inspect", "Give docs/research/Q6_BRIGHT_2026-08-23.txt a close examination."),
    ]


def runtime_cases() -> list[dict[str, Any]]:
    return [{"task_id": task_id, "input_request": request, "environment_facts": {"authority_record": json.loads(json.dumps(AUTHORITY_FIXTURES[task_id]))}} for task_id, _, request in specs()]


def evaluator_cases() -> list[dict[str, Any]]:
    return [{"task_id": task_id, "expected_semantic_class": expected, "expected_model_required": True} for task_id, expected, _ in specs()]


def prompt(request: str, arm: str) -> str:
    labels = ARM_A if arm == "A" else ARM_B
    return (
        f"Request clause:\n{request}\n\n"
        "Classify only the requested operation class.\n"
        f"{labels['presence']} means determine whether the named target exists, is present, or is available.\n"
        f"{labels['inspect']} means examine or look at the named target.\n"
        f"{labels['unresolved']} means the operation class is ambiguous, unsupported, or cannot be determined safely.\n\n"
        "Return only operation_class_candidate in the required structured object. Do not identify the target, choose a tool, decide authorization, or decide task success.\n/no_think"
    )


def schema(arm: str) -> dict[str, Any]:
    return {"type": "object", "properties": {"operation_class_candidate": {"type": "string", "enum": list(ARM_ENUMS[arm])}}, "required": ["operation_class_candidate"], "additionalProperties": False}


def response_format(arm: str) -> dict[str, Any]:
    return {"type": "json_schema", "json_schema": {"name": "bounded_operation_class_candidate_label_counterfactual_v0", "schema": schema(arm)}}


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
    labels = ARM_A if arm == "A" else ARM_B
    return prompt_text.replace(labels["presence"], "__PRESENCE_LABEL__").replace(labels["inspect"], "__INSPECT_LABEL__").replace(labels["unresolved"], "__UNRESOLVED_LABEL__")


def paired_execution_order(task_ids: list[str]) -> list[dict[str, str]]:
    order = []
    for index, task_id in enumerate(task_ids):
        for arm in (("A", "B") if index % 2 == 0 else ("B", "A")):
            order.append({"task_id": task_id, "arm": arm})
    return order


def historical_requests() -> set[str]:
    paths = [
        ROOT / "docs/research/TRUE_SEMANTIC_FALLBACK_V1_RUNTIME_CASES_2026-08-23.json",
        ROOT / "docs/research/TRUE_SEMANTIC_FALLBACK_V2_RUNTIME_CASES_2026-08-23.json",
        ROOT / "docs/research/SEMANTIC_ENUM_ORDER_COUNTERFACTUAL_V0_RUNTIME_CASES_2026-08-23.json",
    ]
    requests = set()
    for path in paths:
        if path.exists():
            requests.update(item["input_request"] for item in read_json(path)["cases"])
    return requests


def predecessor_successor_audit(out: Path, cases: list[dict[str, Any]]) -> dict[str, Any]:
    unchanged = {"slcf-001", "slcf-003", "slcf-004", "slcf-006"}
    files = ("runtime_task.json", "preflight.json", "semantic_information_gap.json", "capability_plan_0.json", "model_settings.json", "prompt.txt", "schema.json")
    rows = []
    for case in cases:
        task_id = case["task_id"]
        if task_id not in unchanged:
            continue
        for arm in ("A", "B"):
            current = out / "tasks" / task_id / arm
            predecessor = PREDECESSOR_RUN / "tasks" / task_id / arm
            matches = {name: current.joinpath(name).read_bytes() == predecessor.joinpath(name).read_bytes() for name in files}
            rows.append({"task_id": task_id, "arm": arm, "files": matches, "all_identical": all(matches.values())})
    assert all(row["all_identical"] for row in rows)
    return {"predecessor_freeze": "bc7aaa5f959bd362456f09b68f951f03dc58d86e", "predecessor_run": str(PREDECESSOR_RUN.relative_to(ROOT)), "unchanged_task_ids": sorted(unchanged), "changed_task_ids": ["slcf-002", "slcf-005"], "rows": rows, "four_unchanged_tasks_identical": True, "arm_difference_remains_label_only": True, "authority_independent": True, "model_settings_unchanged": True, "enum_positions_unchanged": True, "definitions_unchanged_except_labels": True, "pass": True}


def prepare(out: Path) -> None:
    if out.exists() and any(out.iterdir()):
        raise RuntimeError("fresh label counterfactual run required")
    cases, evaluators = runtime_cases(), evaluator_cases()
    assert len(cases) == len(evaluators) == 6
    assert all(case["input_request"] not in historical_requests() for case in cases)
    preflights = [base_v2.preflight(case["input_request"]) for case in cases]
    assert all(pre["semantic_fallback_eligible"] and pre["model_required"] and pre["remaining_candidate_operation_classes"] == ["observe_presence", "inspect"] for pre in preflights)
    task_ids = [case["task_id"] for case in cases]
    order = paired_execution_order(task_ids)
    assert len(order) == 12 and sum(item["arm"] == "A" for item in order[::2]) == 3 and sum(item["arm"] == "B" for item in order[::2]) == 3
    out.mkdir(parents=True, exist_ok=True)
    write_json(RUNTIME_CASES, {"schema": "zth_semantic_label_counterfactual_v0_runtime_cases", "cases": cases})
    write_json(EVALUATOR_CASES, {"schema": "zth_semantic_label_counterfactual_v0_evaluator_cases", "cases": evaluators})
    write_json(REGISTRY, {"schema": "zth_semantic_label_counterfactual_v0_registry", "automatic_promotion": False, "semantic_mapping": {"A": ARM_CANONICAL["A"], "B": ARM_CANONICAL["B"]}, "entries": [{"capability_id": "semantic.bounded_operation_classification", "supplier_id": "qwen3_1_7b_bounded_operation_class_candidate_supplier", "supplier_type": "MODEL", "status": "EXPERIMENTAL_CANDIDATE", "qualification_decision": "no promotion"}]})
    fixture_review = []
    pair_rows = []
    for index, case in enumerate(cases):
        pre = preflights[index]
        expected = evaluators[index]["expected_semantic_class"]
        definition = "observe_presence means determine whether the named target exists, is present, or is available." if expected == "observe_presence" else "inspect means examine or look at the named target."
        fixture_review.append({"task_id": case["task_id"], "request": case["input_request"], "intended_semantic_class": expected, "definition_supporting_intended_class": definition, "preflight_status": pre["operation_derivation_status"], "semantic_fallback_eligible": pre["semantic_fallback_eligible"]})
        gap = {"known_facts_before_model": ["exactly_one_safe_target", "safe_bounded_request", "unambiguous_request", "shared_runtime_authority_allows_both_classes"], "unknown_decision_critical_fact": "which bounded semantic operation class the request expresses", "remaining_candidate_classes": ["observe_presence", "inspect"], "why_deterministic_resolution_is_insufficient": "request is outside the frozen deterministic operation grammar", "why_model_is_permitted": "two safe classes remain semantically plausible"}
        for arm in ("A", "B"):
            arm_dir = out / "tasks" / case["task_id"] / arm
            write_json(arm_dir / "runtime_task.json", case)
            write_json(arm_dir / "preflight.json", pre)
            write_json(arm_dir / "semantic_information_gap.json", gap)
            write_json(arm_dir / "capability_plan_0.json", base_v2.plan(case["task_id"], pre))
            (arm_dir / "prompt.txt").write_text(prompt(case["input_request"], arm), encoding="utf-8")
            write_json(arm_dir / "schema.json", schema(arm))
            write_json(arm_dir / "model_settings.json", model_settings())
        a, b = out / "tasks" / case["task_id"] / "A", out / "tasks" / case["task_id"] / "B"
        pair_rows.append({"task_id": case["task_id"], "request_identity": sha_file(a / "runtime_task.json") == sha_file(b / "runtime_task.json"), "authority_identity": canonical(read_json(a / "runtime_task.json")["environment_facts"]["authority_record"]) == canonical(read_json(b / "runtime_task.json")["environment_facts"]["authority_record"]), "preflight_identity": sha_file(a / "preflight.json") == sha_file(b / "preflight.json"), "model_settings_identity": sha_file(a / "model_settings.json") == sha_file(b / "model_settings.json"), "prompt_definition_equivalence": normalized_prompt((a / "prompt.txt").read_text(), "A") == normalized_prompt((b / "prompt.txt").read_text(), "B"), "semantic_positions_identical": schema("A")["properties"]["operation_class_candidate"]["enum"][0] == "inspect" and schema("B")["properties"]["operation_class_candidate"]["enum"][0] == "class_beta" and schema("A")["properties"]["operation_class_candidate"]["enum"][1] == "observe_presence" and schema("B")["properties"]["operation_class_candidate"]["enum"][1] == "class_alpha", "schema_a_enum": ARM_ENUMS["A"], "schema_b_enum": ARM_ENUMS["B"]})
    assert all(all(row[key] for key in ("request_identity", "authority_identity", "preflight_identity", "model_settings_identity", "prompt_definition_equivalence", "semantic_positions_identical")) for row in pair_rows)
    assert [row["intended_semantic_class"] for row in fixture_review] == ["observe_presence", "inspect", "observe_presence", "inspect", "observe_presence", "inspect"]
    write_json(FIXTURE_REVIEW, {"schema": "zth_semantic_label_counterfactual_v0_fixture_review", "runtime_input": False, "rows": fixture_review})
    predecessor_audit = predecessor_successor_audit(out, cases)
    write_json(out / "predecessor_successor_audit.json", predecessor_audit)
    write_json(PAIR_AUDIT, {"schema": "zth_semantic_label_counterfactual_v0_pair_audit", "rows": pair_rows, "paired_request_identity": True, "paired_authority_identity": True, "paired_preflight_identity": True, "paired_model_settings_identity": True, "definitions_equivalent_except_label_tokens": True, "semantic_enum_positions_identical": True, "only_model_visible_intervention": "LABEL_TOKENS", "predecessor_successor_audit": predecessor_audit})
    write_json(out / "execution_order.json", {"order": order, "counterbalanced": True, "a_first_count": 3, "b_first_count": 3, "a_second_count": 3, "b_second_count": 3, "cross_arm_input": False})
    manifest = {"schema": "zth_semantic_label_counterfactual_v0_manifest", "status": "prepared_model_free", "supersedes_unexecuted_pre_inference_freeze": "bc7aaa5f959bd362456f09b68f951f03dc58d86e", "task_count": 6, "paired_opportunities": 6, "planned_model_calls": 12, "model_calls_made": 0, "tool_calls_made": 0, "response_files": 0, "true_fallback_eligibility": 6, "historical_request_reuse": 0, "paired_input_identity_audit": True, "authority_provenance_audit": True, "definition_equivalence_audit": True, "semantic_enum_positions_identical": True, "counterbalance_audit": True, "a_first_count": 3, "b_first_count": 3, "a_second_count": 3, "b_second_count": 3, "arm_b_class_alpha_admissible": True, "arm_b_class_beta_admissible": True, "arm_b_unresolved_admissible": False, "predecessor_successor_audit": True, "runtime_evaluator_influence": 0, "model_output_granted_authority": 0, "qualification_change": False, "teacher_calls": 0, "30b_calls": 0, "external_calls": 0, "retries": 0, "driver_sha256": sha_file(Path(__file__).resolve()), "model_settings": model_settings(), "arm_a_labels": ARM_A, "arm_b_labels": ARM_B, "arm_a_enum": ARM_ENUMS["A"], "arm_b_enum": ARM_ENUMS["B"]}
    write_json(out / "router_manifest.json", manifest)
    write_json(out / "lifecycle.json", {"status": "prepared", "model_calls": 0, "tool_calls": 0, "retries": 0})
    print(json.dumps({"status": "prepared", "fresh_tasks": 6, "paired_opportunities": 6, "planned_model_calls": 12, "MODEL_CALLS_MADE": 0, "TOOL_CALLS_MADE": 0, "response_files": 0}, indent=2))


def model_preflight(out: Path):
    spec = runtime.worker_spec()
    models = decomposition.list_models(spec, timeout=30)
    candidate = next((item for item in models.get("data", []) if item.get("id") == MODEL_ID), None)
    meta = (candidate or {}).get("meta") or {}
    if candidate is None or meta.get("n_params") != PARAMS:
        raise RuntimeError("model binding mismatch")
    telemetry_url = telemetry_provider.telemetry_base_url()
    telemetry = telemetry_provider.telemetry_preflight(telemetry_url)
    write_json(out / "model_preflight.json", {"model_meta": meta, "telemetry": telemetry, "telemetry_provider": "scripts.zth_qwen3_0_6b_clean_scope_logic_probe", "model_id": MODEL_ID})
    return spec, telemetry_url


def execute(out: Path) -> None:
    spec, telemetry_url = model_preflight(out)
    calls = 0
    for item in read_json(out / "execution_order.json")["order"]:
        task_dir = out / "tasks" / item["task_id"] / item["arm"]
        write_json(task_dir / "call_started.json", {"task_id": item["task_id"], "arm": item["arm"], "started_at": time.time(), "prompt_sha256": sha_file(task_dir / "prompt.txt"), "schema_sha256": sha_file(task_dir / "schema.json"), "model_id": MODEL_ID})
        sampler = PowerSampler(lambda: read_gpu_power(GPU_UUID, base_url=telemetry_url), expected_gpu_uuid=GPU_UUID, sample_interval_seconds=POWER_INTERVAL)
        started = time.monotonic(); sampler.start(); response = decomposition.structured_call(spec, (task_dir / "prompt.txt").read_text(encoding="utf-8"), response_format(item["arm"]), MAX_TOKENS, TIMEOUT); elapsed = time.monotonic() - started; samples = sampler.stop(); energy = integrate_energy_joules(samples, sample_interval_seconds=POWER_INTERVAL, expected_gpu_uuid=GPU_UUID)
        metadata = response.metadata(); metadata["request_url"] = None
        write_json(task_dir / "response.json", {"status": response.status, "content": response.content, "metadata": metadata, "wall_elapsed_ms": round(elapsed * 1000, 3), "gross_energy_joules": energy})
        write_json(task_dir / "power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "gpu_uuid": GPU_UUID, "samples": [{"timestamp_utc": s.timestamp_utc, "power_watts": s.power_watts, "gpu_uuid": s.gpu_uuid, "sequence": s.sequence} for s in samples]})
        candidate, parse_valid, contract_valid, diagnostics = parse_response(response.content, item["arm"]); calls += 1; validation = validate_and_map_candidate(candidate, item["arm"], parse_valid, contract_valid); validation["diagnostics"] = diagnostics
        write_json(task_dir / "candidate_validation.json", validation)
        if validation["contract_valid"] and validation["candidate_admissible"]:
            canonical_operation = validation["canonical_operation"]
            write_json(task_dir / "operation_derivation_1.json", {"status": "RESOLVED", "surface_label": candidate, "canonical_operation": canonical_operation, "derivation_type": "PRIOR_MODEL_STEP_LABEL_MAPPING", "model_output_granted_authority": False})
            write_json(task_dir / "capability_plan_1.json", base_v2.plan(item["task_id"], read_json(task_dir / "preflight.json"), canonical_operation))
            result = {"surface_label": candidate, "canonical_operation": canonical_operation, "semantic_output_accepted": True, "tool_calls": 0, "terminal_state": "review_or_deferred_execution", "model_calls": 1}
        else:
            result = {"surface_label": candidate, "canonical_operation": None, "semantic_output_accepted": False, "tool_calls": 0, "terminal_state": "ready_for_review", "model_calls": 1}
        write_json(task_dir / "runtime_result.json", result)
    write_json(out / "lifecycle.json", {"status": "terminal_runtime", "model_calls": calls, "tool_calls": 0, "retries": 0, "runtime_evaluator_influence": 0, "model_output_granted_authority": 0})


def closeout(out: Path) -> None:
    evaluators = {item["task_id"]: item for item in read_json(EVALUATOR_CASES)["cases"]}; rows = []
    for task_id, expected, _ in specs():
        for arm in ("A", "B"):
            d = out / "tasks" / task_id / arm; val = read_json(d / "candidate_validation.json"); result = read_json(d / "runtime_result.json"); observed = result.get("canonical_operation")
            rows.append({"task_id": task_id, "arm": arm, "expected": expected, "surface_label": val.get("candidate"), "observed_canonical": observed, "semantic_correct": observed == expected, "parse_valid": val.get("parse_valid"), "contract_valid": val.get("contract_valid"), "candidate_valid": val.get("candidate_valid"), "candidate_admissible": val.get("candidate_admissible")})
    pairs = {task_id: {arm: next(row for row in rows if row["task_id"] == task_id and row["arm"] == arm) for arm in ("A", "B")} for task_id, _, _ in specs()}
    transitions = {}
    for task_id, pair in pairs.items():
        key = f"{pair['A']['observed_canonical']}->{pair['B']['observed_canonical']}"; transitions[key] = transitions.get(key, 0) + 1
    write_json(out / "aggregate.json", {"schema": "zth_semantic_label_counterfactual_v0_aggregate", "arm_a_semantic_correct": sum(row["semantic_correct"] for row in rows if row["arm"] == "A"), "arm_b_semantic_correct": sum(row["semantic_correct"] for row in rows if row["arm"] == "B"), "paired_canonical_transitions": transitions, "rows": rows})


def main() -> None:
    parser = argparse.ArgumentParser(); group = parser.add_mutually_exclusive_group(required=True); group.add_argument("--prepare", action="store_true"); group.add_argument("--execute", action="store_true"); group.add_argument("--closeout", action="store_true"); parser.add_argument("--output-dir", type=Path, default=RUN); args = parser.parse_args()
    if args.prepare: prepare(args.output_dir)
    elif args.execute: execute(args.output_dir)
    else: closeout(args.output_dir)


if __name__ == "__main__":
    main()
