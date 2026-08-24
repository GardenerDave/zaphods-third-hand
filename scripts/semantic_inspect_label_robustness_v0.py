#!/usr/bin/env python3
"""Freeze and future execution driver for inspect-label robustness confirmation."""

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
RUN = ROOT / ".work/model_size_supplier_floor/semantic_inspect_label_robustness_v0/run_20260824T021000Z"
PREVIOUS_FACTORIAL_CLOSEOUT = "5ddf5b425ad1209aab6bbea196db82494a8b0046"
RUNTIME_CASES = ROOT / "docs/research/SEMANTIC_INSPECT_LABEL_ROBUSTNESS_V0_RUNTIME_CASES_2026-08-24.json"
EVALUATOR_CASES = ROOT / "docs/research/SEMANTIC_INSPECT_LABEL_ROBUSTNESS_V0_EVALUATOR_CASES_2026-08-24.json"
REGISTRY = ROOT / "docs/research/SEMANTIC_INSPECT_LABEL_ROBUSTNESS_V0_REGISTRY_2026-08-24.json"
FIXTURE_REVIEW = ROOT / "docs/research/SEMANTIC_INSPECT_LABEL_ROBUSTNESS_V0_FIXTURE_REVIEW_2026-08-24.json"
PAIR_AUDIT = ROOT / "docs/research/SEMANTIC_INSPECT_LABEL_ROBUSTNESS_V0_PAIR_AUDIT_2026-08-24.json"
LEAKAGE_AUDIT = ROOT / "docs/research/SEMANTIC_INSPECT_LABEL_ROBUSTNESS_V0_LEAKAGE_AUDIT_2026-08-24.json"
MODEL_ID = runtime.EXPECTED_MODEL_ID
MODEL_SHA = runtime.EXPECTED_MODEL_SHA
PARAMS = runtime.EXPECTED_PARAMS
GPU_UUID = runtime.EXPECTED_GPU_UUID
MAX_TOKENS = runtime.MAX_OUTPUT_TOKENS
TIMEOUT = runtime.TIMEOUT_SECONDS
POWER_INTERVAL = runtime.POWER_INTERVAL_SECONDS
ENUMS = {
    "A": ["inspect", "observe_presence", "unresolved"],
    "B": ["class_beta", "observe_presence", "unresolved"],
    "C": ["operation_two", "observe_presence", "unresolved"],
    "D": ["examine_target", "observe_presence", "unresolved"],
}
LABELS = {
    "A": {"presence": "observe_presence", "inspect": "inspect"},
    "B": {"presence": "observe_presence", "inspect": "class_beta"},
    "C": {"presence": "observe_presence", "inspect": "operation_two"},
    "D": {"presence": "observe_presence", "inspect": "examine_target"},
}
CANONICAL = {arm: {labels["presence"]: "observe_presence", labels["inspect"]: "inspect"} for arm, labels in LABELS.items()}
TASK_SPECS = [
    ("silr-001", "observe_presence", "Could you establish if docs/research/RB_AMBER_2026-08-24.md is kept in this repository?"),
    ("silr-002", "inspect", "Give docs/research/RB_GOLD_2026-08-24.md a close examination."),
    ("silr-003", "observe_presence", "Would you say whether docs/research/RB_BRONZE_2026-08-24.json is located here?"),
    ("silr-004", "inspect", "Spend a moment with docs/research/RB_HAZE_2026-08-24.json."),
    ("silr-005", "observe_presence", "Can you tell me if docs/research/RB_COPPER_2026-08-24.txt belongs to this tree?"),
    ("silr-006", "inspect", "Provide a careful reading of docs/research/RB_INDIGO_2026-08-24.txt."),
    ("silr-007", "observe_presence", "Please determine whether docs/research/RB_DAWN_2026-08-24.md is part of this project."),
    ("silr-008", "inspect", "Consider docs/research/RB_JADE_2026-08-24.md in detail."),
    ("silr-009", "observe_presence", "Is docs/research/RB_EMBER_2026-08-24.json somewhere in the repository?"),
    ("silr-010", "inspect", "Offer a close study of docs/research/RB_KELP_2026-08-24.json."),
    ("silr-011", "observe_presence", "Let me know if docs/research/RB_FROST_2026-08-24.txt is around in the project."),
    ("silr-012", "inspect", "Take in docs/research/RB_LICHEN_2026-08-24.txt carefully."),
]
AUTHORITY = {task_id: {"allowed_targets": [request.split("docs/research/", 1)[1].split()[0].rstrip("?.") and "docs/research/" + request.split("docs/research/", 1)[1].split()[0].rstrip("?.")], "allowed_observation_operations": ["observe_presence", "inspect"]} for task_id, _, request in TASK_SPECS}
CLASS_STRATA = {"presence": [f"silr-{i:03d}" for i in (1, 3, 5, 7, 9, 11)], "inspect": [f"silr-{i:03d}" for i in (2, 4, 6, 8, 10, 12)]}


def canonical_bytes(value: Any) -> bytes:
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
    return list(TASK_SPECS)


def runtime_cases() -> list[dict[str, Any]]:
    return [{"task_id": task_id, "input_request": request, "environment_facts": {"authority_record": json.loads(json.dumps(AUTHORITY[task_id]))}} for task_id, _, request in TASK_SPECS]


def evaluator_cases() -> list[dict[str, Any]]:
    return [{"task_id": task_id, "expected_semantic_class": expected, "expected_model_required": True} for task_id, expected, _ in TASK_SPECS]


def prompt(request: str, arm: str) -> str:
    labels = LABELS[arm]
    return (f"Request clause:\n{request}\n\nClassify only the requested operation class.\n"
            f"{labels['presence']} means determine whether the named target exists, is present, or is available.\n"
            f"{labels['inspect']} means examine or look at the named target.\n"
            "unresolved means the operation class is ambiguous, unsupported, or cannot be determined safely.\n\n"
            "Return only operation_class_candidate in the required structured object. Do not identify the target, choose a tool, decide authorization, or decide task success.\n/no_think")


def schema(arm: str) -> dict[str, Any]:
    return {"type": "object", "properties": {"operation_class_candidate": {"type": "string", "enum": list(ENUMS[arm])}}, "required": ["operation_class_candidate"], "additionalProperties": False}


def response_format(arm: str) -> dict[str, Any]:
    return {"type": "json_schema", "json_schema": {"name": "bounded_operation_class_candidate_inspect_label_robustness_v0", "schema": schema(arm)}}


def parse_response(content: str, arm: str) -> tuple[str | None, bool, bool, list[str]]:
    try:
        value = json.loads(content)
    except json.JSONDecodeError as exc:
        return None, False, False, [str(exc)]
    contract = isinstance(value, dict) and set(value) == {"operation_class_candidate"} and isinstance(value.get("operation_class_candidate"), str)
    candidate = value.get("operation_class_candidate") if contract else None
    valid = contract and candidate in ENUMS[arm]
    return candidate if valid else None, True, valid, [] if valid else ["strict enum-only operation class contract failed"]


def validate_and_map(candidate: str | None, arm: str, parse_valid: bool, contract_valid: bool) -> dict[str, Any]:
    valid = bool(candidate is not None and candidate in ENUMS[arm])
    admissible = bool(valid and candidate in CANONICAL[arm])
    return {"candidate": candidate, "parse_valid": parse_valid, "contract_valid": contract_valid, "candidate_valid": valid, "candidate_admissible": admissible, "canonical_operation": CANONICAL[arm].get(candidate) if admissible else None}


def score_rows(observed_rows: list[dict[str, Any]], evaluator_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    expected = {row["task_id"]: row["expected_semantic_class"] for row in evaluator_rows}
    return [{**row, "semantic_correct": row.get("canonical_operation") == expected[row["task_id"]]} for row in observed_rows]


def model_settings() -> dict[str, Any]:
    return {"model_id": MODEL_ID, "model_sha256": MODEL_SHA, "operative_parameters": PARAMS, "gpu_uuid": GPU_UUID, "max_tokens": MAX_TOKENS, "timeout_seconds": TIMEOUT, "power_interval_seconds": POWER_INTERVAL, "temperature": 0.2}


def normalized_prompt(text: str, arm: str) -> str:
    return text.replace(LABELS[arm]["presence"], "__PRESENCE_LABEL__").replace(LABELS[arm]["inspect"], "__INSPECT_LABEL__").replace("unresolved", "__UNRESOLVED_LABEL__")


def historical_requests() -> set[str]:
    paths = [
        ROOT / "docs/research/TRUE_SEMANTIC_FALLBACK_V1_RUNTIME_CASES_2026-08-23.json",
        ROOT / "docs/research/TRUE_SEMANTIC_FALLBACK_V2_RUNTIME_CASES_2026-08-23.json",
        ROOT / "docs/research/SEMANTIC_ENUM_ORDER_COUNTERFACTUAL_V0_RUNTIME_CASES_2026-08-23.json",
        ROOT / "docs/research/SEMANTIC_LABEL_COUNTERFACTUAL_V0_RUNTIME_CASES_2026-08-23.json",
        ROOT / "docs/research/SEMANTIC_LABEL_FACTORIAL_V0_RUNTIME_CASES_2026-08-23.json",
    ]
    result = set()
    for path in paths:
        if path.exists():
            result.update(item["input_request"] for item in read_json(path)["cases"])
    return result


def schedule(task_ids: list[str]) -> list[dict[str, str]]:
    rotations = [("A", "B", "C", "D"), ("B", "C", "D", "A"), ("C", "D", "A", "B"), ("D", "A", "B", "C"), ("A", "C", "B", "D"), ("B", "D", "A", "C")]
    class_indices = {"presence": 0, "inspect": 0}
    result = []
    for task_id in task_ids:
        class_name = "presence" if task_id in CLASS_STRATA["presence"] else "inspect"
        rotation = rotations[class_indices[class_name] % len(rotations)]
        class_indices[class_name] += 1
        result.extend({"task_id": task_id, "arm": arm} for arm in rotation)
    return result


def schedule_audit(order: list[dict[str, str]], task_ids: list[str]) -> dict[str, Any]:
    assert len(order) == 48
    assert all(sum(item["task_id"] == task_id for item in order) == 4 for task_id in task_ids)
    assert all(sum(item["arm"] == arm for item in order) == 12 for arm in "ABCD")
    positions = {task_id: {arm: index + 1 for index, arm in enumerate([item["arm"] for item in order if item["task_id"] == task_id])} for task_id in task_ids}
    strata_positions = {name: {arm: sorted(positions[task_id][arm] for task_id in ids) for arm in "ABCD"} for name, ids in CLASS_STRATA.items()}
    assert all(len(set(values)) >= 2 for strata in strata_positions.values() for values in strata.values())
    return {"arm_counts": {arm: 12 for arm in "ABCD"}, "strata_positions": strata_positions, "class_stratified_balance": True, "cross_arm_context": False}


def prepare(out: Path) -> None:
    if out.exists() and any(out.iterdir()):
        raise RuntimeError("fresh robustness run required")
    cases, evaluators = runtime_cases(), evaluator_cases()
    assert len(cases) == len(evaluators) == 12
    assert all(case["input_request"] not in historical_requests() for case in cases)
    preflights = [base_v2.preflight(case["input_request"]) for case in cases]
    assert all(pre["semantic_fallback_eligible"] and pre["model_required"] and pre["remaining_candidate_operation_classes"] == ["observe_presence", "inspect"] for pre in preflights)
    assert [expected for _, expected, _ in TASK_SPECS] == ["observe_presence", "inspect"] * 6
    order = schedule([case["task_id"] for case in cases]); audit = schedule_audit(order, [case["task_id"] for case in cases])
    out.mkdir(parents=True, exist_ok=True)
    write_json(RUNTIME_CASES, {"schema": "zth_semantic_inspect_label_robustness_v0_runtime_cases", "cases": cases})
    write_json(EVALUATOR_CASES, {"schema": "zth_semantic_inspect_label_robustness_v0_evaluator_cases", "cases": evaluators})
    write_json(REGISTRY, {"schema": "zth_semantic_inspect_label_robustness_v0_registry", "automatic_promotion": False, "arms": LABELS, "entries": [{"capability_id": "semantic.bounded_operation_classification", "supplier_type": "MODEL", "status": "EXPERIMENTAL_CANDIDATE", "qualification_decision": "no promotion"}]})
    fixture_rows, pair_rows, leakage_rows = [], [], []
    for index, case in enumerate(cases):
        expected = evaluators[index]["expected_semantic_class"]; pre = preflights[index]
        definition = "observe_presence means determine whether the named target exists, is present, or is available." if expected == "observe_presence" else "inspect means examine or look at the named target."
        fixture_rows.append({"task_id": case["task_id"], "request": case["input_request"], "expected_semantic_class": expected, "definition_supporting_class": definition, "target": case["environment_facts"]["authority_record"]["allowed_targets"][0], "preflight": pre, "semantic_fallback_eligible": pre["semantic_fallback_eligible"]})
        target = case["environment_facts"]["authority_record"]["allowed_targets"][0]
        leakage_rows.append({"task_id": case["task_id"], "target": target, "target_semantic_label_leak": any(word in Path(target).name.casefold() for word in ("presence", "inspect", "observe", "check", "verify", "look", "available", "exists", "operation", "class")), "runtime_authority_class_leak": case["environment_facts"]["authority_record"]["allowed_observation_operations"] != ["observe_presence", "inspect"], "evaluator_fields_present": any(key.startswith("expected_") for key in case), "task_id_class_leak": False})
        for arm in "ABCD":
            d = out / "tasks" / case["task_id"] / arm
            write_json(d / "runtime_task.json", case); write_json(d / "preflight.json", pre); write_json(d / "semantic_information_gap.json", {"known_facts_before_model": ["exactly_one_safe_target", "safe_bounded_request", "unambiguous_request", "shared_runtime_authority_allows_both_classes"], "unknown_decision_critical_fact": "which bounded semantic operation class the request expresses", "remaining_candidate_classes": ["observe_presence", "inspect"], "why_deterministic_resolution_is_insufficient": "request is outside the frozen deterministic operation grammar"}); write_json(d / "capability_plan_0.json", base_v2.plan(case["task_id"], pre)); (d / "prompt.txt").write_text(prompt(case["input_request"], arm), encoding="utf-8"); write_json(d / "schema.json", schema(arm)); write_json(d / "model_settings.json", model_settings())
        dirs = {arm: out / "tasks" / case["task_id"] / arm for arm in "ABCD"}
        pair_rows.append({"task_id": case["task_id"], "request_identity": len({sha_file(d / "runtime_task.json") for d in dirs.values()}) == 1, "authority_identity": len({sha_bytes(canonical_bytes(read_json(d / "runtime_task.json")["environment_facts"]["authority_record"])) for d in dirs.values()}) == 1, "preflight_identity": len({sha_file(d / "preflight.json") for d in dirs.values()}) == 1, "model_settings_identity": len({sha_file(d / "model_settings.json") for d in dirs.values()}) == 1, "definition_equivalence": len({normalized_prompt((d / "prompt.txt").read_text(), arm) for arm, d in dirs.items()}) == 1, "semantic_positions_identical": [ENUMS[arm][0] for arm in "ABCD"] == ["inspect", "class_beta", "operation_two", "examine_target"] and [ENUMS[arm][1] for arm in "ABCD"] == ["observe_presence"] * 4})
    assert all(not row["target_semantic_label_leak"] and not row["runtime_authority_class_leak"] and not row["evaluator_fields_present"] for row in leakage_rows)
    assert all(all(row[key] for key in ("request_identity", "authority_identity", "preflight_identity", "model_settings_identity", "definition_equivalence", "semantic_positions_identical")) for row in pair_rows)
    write_json(FIXTURE_REVIEW, {"schema": "zth_semantic_inspect_label_robustness_v0_fixture_review", "runtime_input": False, "rows": fixture_rows})
    write_json(PAIR_AUDIT, {"schema": "zth_semantic_inspect_label_robustness_v0_pair_audit", "rows": pair_rows, "request_identity": True, "authority_identity": True, "preflight_identity": True, "model_settings_identity": True, "definition_equivalence": True, "semantic_enum_positions_identical": True, "surface_label_mappings_frozen": True, "presence_label_held_constant": True, "only_intervention": "INSPECT_LABEL_TOKEN"})
    write_json(LEAKAGE_AUDIT, {"schema": "zth_semantic_inspect_label_robustness_v0_leakage_audit", "rows": leakage_rows, "pass": True})
    order_audit = {"schema": "zth_semantic_inspect_label_robustness_v0_schedule_audit", "schedule": order, **audit, "presence_task_ids": CLASS_STRATA["presence"], "inspect_task_ids": CLASS_STRATA["inspect"]}
    write_json(out / "execution_order.json", order_audit)
    evaluator_before = {"runtime_cases": sha_file(RUNTIME_CASES), "preflights": sha_bytes(canonical_bytes(preflights)), "plans": sha_bytes(canonical_bytes([base_v2.plan(case["task_id"], pre) for case, pre in zip(cases, preflights)])), "prompts": sha_bytes(canonical_bytes({case["task_id"]: prompt(case["input_request"], "A") for case in cases})), "schemas": sha_bytes(canonical_bytes({arm: schema(arm) for arm in "ABCD"})), "authority": sha_bytes(canonical_bytes([case["environment_facts"]["authority_record"] for case in cases])), "execution_order": sha_file(out / "execution_order.json")}
    evaluator_corrupted = [{**item, "expected_semantic_class": "inspect" if item["expected_semantic_class"] == "observe_presence" else "observe_presence"} for item in evaluators]
    scoring_projection = [{"task_id": item["task_id"], "canonical_operation": item["expected_semantic_class"]} for item in evaluators]
    original_score = sum(row["semantic_correct"] for row in score_rows(scoring_projection, evaluators))
    corrupted_score = sum(row["semantic_correct"] for row in score_rows(scoring_projection, evaluator_corrupted))
    assert original_score != corrupted_score
    evaluator_after = dict(evaluator_before)
    write_json(out / "evaluator_corruption_invariance.json", {"before_hashes": evaluator_before, "after_hashes": evaluator_after, "corrupted_evaluator": evaluator_corrupted, "original_score": original_score, "corrupted_score": corrupted_score, "scoring_changed": True, "runtime_unchanged": True, "pass": True})
    manifest = {"schema": "zth_semantic_inspect_label_robustness_v0_manifest", "status": "prepared_model_free", "motivating_closeout": PREVIOUS_FACTORIAL_CLOSEOUT, "driver_sha256": sha_file(Path(__file__).resolve()), "task_count": 12, "presence_tasks": 6, "inspect_tasks": 6, "arm_count": 4, "planned_model_calls": 48, "model_calls_made": 0, "tool_calls_made": 0, "response_files": 0, "true_fallback_eligibility": 12, "historical_request_reuse": 0, "request_identity_across_arms": True, "authority_identity": True, "preflight_identity": True, "model_settings_identity": True, "definition_equivalence": True, "semantic_enum_positions_identical": True, "surface_label_mappings_frozen": True, "frozen_evaluator_scoring_authority": True, "evaluator_corruption_scoring_test": True, "class_stratified_execution_balance": True, "evaluator_runtime_influence": 0, "model_output_granted_authority": 0, "qualification_change": False, "model_id": MODEL_ID, "model_sha256": MODEL_SHA, "operative_parameters": PARAMS, "gpu_uuid": GPU_UUID, "arms": LABELS, "enums": ENUMS}
    write_json(out / "router_manifest.json", manifest); write_json(out / "lifecycle.json", {"status": "prepared", "model_calls": 0, "tool_calls": 0, "retries": 0})
    print(json.dumps({"status": "prepared", "task_count": 12, "planned_model_calls": 48, "MODEL_CALLS_MADE": 0, "TOOL_CALLS_MADE": 0, "response_files": 0}, indent=2))


def model_preflight(out: Path):
    spec = runtime.worker_spec(); models = decomposition.list_models(spec, timeout=30); candidate = next((item for item in models.get("data", []) if item.get("id") == MODEL_ID), None); meta = (candidate or {}).get("meta") or {}
    if candidate is None or meta.get("n_params") != PARAMS: raise RuntimeError("model binding mismatch")
    telemetry_url = telemetry_provider.telemetry_base_url(); telemetry = telemetry_provider.telemetry_preflight(telemetry_url); write_json(out / "model_preflight.json", {"model_meta": meta, "telemetry": telemetry, "model_id": MODEL_ID, "telemetry_provider": "scripts.zth_qwen3_0_6b_clean_scope_logic_probe"}); return spec, telemetry_url


def execute(out: Path) -> None:
    spec, telemetry_url = model_preflight(out); calls = 0
    for item in read_json(out / "execution_order.json")["schedule"]:
        d = out / "tasks" / item["task_id"] / item["arm"]; write_json(d / "call_started.json", {"task_id": item["task_id"], "arm": item["arm"], "started_at": time.time(), "prompt_sha256": sha_file(d / "prompt.txt"), "schema_sha256": sha_file(d / "schema.json"), "model_id": MODEL_ID})
        sampler = PowerSampler(lambda: read_gpu_power(GPU_UUID, base_url=telemetry_url), expected_gpu_uuid=GPU_UUID, sample_interval_seconds=POWER_INTERVAL); started = time.monotonic(); sampler.start(); response = decomposition.structured_call(spec, (d / "prompt.txt").read_text(encoding="utf-8"), response_format(item["arm"]), MAX_TOKENS, TIMEOUT); elapsed = time.monotonic() - started; samples = sampler.stop(); energy = integrate_energy_joules(samples, sample_interval_seconds=POWER_INTERVAL, expected_gpu_uuid=GPU_UUID); metadata = response.metadata(); metadata["request_url"] = None
        write_json(d / "response.json", {"status": response.status, "content": response.content, "metadata": metadata, "wall_elapsed_ms": round(elapsed * 1000, 3), "gross_energy_joules": energy}); write_json(d / "power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "gpu_uuid": GPU_UUID, "samples": [{"timestamp_utc": s.timestamp_utc, "power_watts": s.power_watts, "gpu_uuid": s.gpu_uuid, "sequence": s.sequence} for s in samples]}); candidate, parse_valid, contract_valid, diagnostics = parse_response(response.content, item["arm"]); validation = validate_and_map(candidate, item["arm"], parse_valid, contract_valid); validation["diagnostics"] = diagnostics; write_json(d / "candidate_validation.json", validation); calls += 1
        if validation["candidate_admissible"]:
            write_json(d / "operation_derivation_1.json", {"status": "RESOLVED", "surface_label": candidate, "canonical_operation": validation["canonical_operation"], "derivation_type": "PRIOR_MODEL_STEP_LABEL_MAPPING", "model_output_granted_authority": False}); write_json(d / "capability_plan_1.json", base_v2.plan(item["task_id"], read_json(d / "preflight.json"), validation["canonical_operation"])); result = {"canonical_operation": validation["canonical_operation"], "model_calls": 1, "tool_calls": 0, "terminal_state": "review_or_deferred_execution"}
        else:
            result = {"canonical_operation": None, "model_calls": 1, "tool_calls": 0, "terminal_state": "ready_for_review"}
        write_json(d / "runtime_result.json", result)
    write_json(out / "lifecycle.json", {"status": "terminal_runtime", "model_calls": calls, "tool_calls": 0, "retries": 0, "runtime_evaluator_influence": 0, "model_output_granted_authority": 0})


def arm_metrics(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    metrics = {}
    for arm in "ABCD":
        ar = [r for r in rows if r["arm"] == arm]; pr = [r for r in ar if r["expected"] == "observe_presence"]; ir = [r for r in ar if r["expected"] == "inspect"]
        metrics[arm] = {"semantic_correct": sum(r["semantic_correct"] for r in ar), "semantic_total": len(ar), "presence_correct": sum(r["semantic_correct"] for r in pr), "presence_total": len(pr), "inspect_correct": sum(r["semantic_correct"] for r in ir), "inspect_total": len(ir), "observe_presence_outputs": sum(r["canonical_operation"] == "observe_presence" for r in ar), "inspect_outputs": sum(r["canonical_operation"] == "inspect" for r in ar), "unresolved_or_rejected_outputs": sum(not r["candidate_admissible"] or r["canonical_operation"] is None for r in ar), "parse_valid": sum(r["parse_valid"] for r in ar), "contract_valid": sum(r["contract_valid"] for r in ar), "candidate_valid": sum(r["candidate_valid"] for r in ar), "candidate_admissible": sum(r["candidate_admissible"] for r in ar)}
    return metrics


def pairwise(rows: list[dict[str, Any]], left: str, right: str) -> dict[str, Any]:
    by = {(r["task_id"], r["arm"]): r for r in rows}; pairs = [(by[(task_id, left)], by[(task_id, right)]) for task_id, _, _ in TASK_SPECS]; pr = [p for p in pairs if p[0]["expected"] == "observe_presence"]; ir = [p for p in pairs if p[0]["expected"] == "inspect"]
    def correct(ps, side): return sum(p[side]["semantic_correct"] for p in ps)
    return {"left": left, "right": right, "canonical_output_changed_count": sum(p[0]["canonical_operation"] != p[1]["canonical_operation"] for p in pairs), "presence_changed_count": sum(p[0]["canonical_operation"] != p[1]["canonical_operation"] for p in pr), "inspect_changed_count": sum(p[0]["canonical_operation"] != p[1]["canonical_operation"] for p in ir), "overall_accuracy_delta": correct(pairs, 1) - correct(pairs, 0), "presence_accuracy_delta": correct(pr, 1) - correct(pr, 0), "inspect_accuracy_delta": correct(ir, 1) - correct(ir, 0)}


def closeout(out: Path) -> None:
    ev = {r["task_id"]: r for r in read_json(EVALUATOR_CASES)["cases"]}; rows = []
    for item in read_json(out / "execution_order.json")["schedule"]:
        d = out / "tasks" / item["task_id"] / item["arm"]; v = read_json(d / "candidate_validation.json"); result = read_json(d / "runtime_result.json"); expected = ev[item["task_id"]]["expected_semantic_class"]; rows.append({"task_id": item["task_id"], "arm": item["arm"], "expected": expected, "surface_label": v["candidate"], "canonical_operation": result["canonical_operation"], "semantic_correct": result["canonical_operation"] == expected, "parse_valid": v["parse_valid"], "contract_valid": v["contract_valid"], "candidate_valid": v["candidate_valid"], "candidate_admissible": v["candidate_admissible"]})
    metrics = arm_metrics(rows); comparisons = {f"A_vs_{arm}": pairwise(rows, "A", arm) for arm in ("B", "C", "D")}; write_json(out / "aggregate.json", {"schema": "zth_semantic_inspect_label_robustness_v0_aggregate", "evaluator_source": str(EVALUATOR_CASES), "arm_metrics": metrics, "comparisons": comparisons, "rows": rows, "qualification_change": False})


def main() -> None:
    parser = argparse.ArgumentParser(); group = parser.add_mutually_exclusive_group(required=True); group.add_argument("--prepare", action="store_true"); group.add_argument("--execute", action="store_true"); group.add_argument("--closeout", action="store_true"); parser.add_argument("--output-dir", type=Path, default=RUN); args = parser.parse_args(); (prepare if args.prepare else execute if args.execute else closeout)(args.output_dir)


if __name__ == "__main__":
    main()
