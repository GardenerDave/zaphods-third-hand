from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from .capability_profile import validate_capability_profile
from .fleet_router import route_initial_model, select_fallback_model


DETERMINISTIC_ESCALATION_TRIGGERS = {
    "TRANSPORT_FAILURE",
    "PARSE_FAILURE",
    "SCHEMA_FAILURE",
    "WORKER_CONTRACT_FAILURE",
    "CITATION_ID_FAILURE",
}


def summarize_task_rows(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    return {
        "task_count": total,
        "routing_policy_compliance": sum(bool(row.get("routing_policy_compliance")) for row in rows),
        "task_success": sum(bool(row.get("task_success")) for row in rows),
        "primary_structural_success": sum(bool(row.get("primary_structural_success")) for row in rows),
        "primary_semantic_success": sum(bool(row.get("primary_semantic_success")) for row in rows),
        "deterministic_escalation_triggers": sum(bool(row.get("escalation_trigger") and row.get("escalation_trigger") != "NONE") for row in rows),
        "fallback_attempts": sum(bool(row.get("fallback_model")) for row in rows),
        "fallback_structural_success": sum(bool(row.get("fallback_structural_success")) for row in rows),
        "fallback_semantic_success": sum(bool(row.get("fallback_semantic_success")) for row in rows),
        "resolved_without_fallback": sum(not row.get("fallback_model") for row in rows),
        "resolved_by_fallback": sum(bool(row.get("fallback_model")) for row in rows),
        "unresolved_tasks": sum(row.get("final_result_status") in {"NO_QUALIFIED_FALLBACK", "failed", "FAILED"} for row in rows),
        "unsupported_certainty_failures": sum(bool(row.get("unsupported_certainty_failure")) for row in rows),
        "citation_id_validity": sum(bool(row.get("citation_id_valid")) for row in rows),
        "primary_attempt_count": sum(int(row.get("primary_attempt_count", 1)) for row in rows),
        "fallback_attempt_count": sum(int(row.get("fallback_attempt_count", 0)) for row in rows),
        "latency_seconds_total": round(sum(float(row.get("latency_seconds", 0.0)) for row in rows), 6),
        "latency_seconds_by_model": {
            model_id: round(sum(float(row.get("latency_seconds", 0.0)) for row in rows if row.get("final_worker") == model_id), 6)
            for model_id in sorted({str(row.get("final_worker")) for row in rows if row.get("final_worker")})
        },
        "fraction_handled_by_primary": (sum(1 for row in rows if row.get("final_worker") == row.get("primary_model")) / total) if total else 0.0,
        "fraction_sent_to_fallback": (sum(1 for row in rows if row.get("fallback_model")) / total) if total else 0.0,
    }


def build_sanitized_manifest(
    *,
    experiment_name: str,
    historian_commit: str,
    capability_profile_sha256: str,
    fixture_sha256: str,
    router_commit: str,
    worker_contract_version: str,
    model_id: str,
    endpoint_alias: str,
    tasks: list[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "schema": "historian_dynamic_two_tier_escalation_manifest_v1",
        "experiment_name": experiment_name,
        "historian_commit": historian_commit,
        "router_commit": router_commit,
        "capability_profile_sha256": capability_profile_sha256,
        "fixture_sha256": fixture_sha256,
        "worker_contract_version": worker_contract_version,
        "model_id": model_id,
        "endpoint_alias": endpoint_alias,
        "tasks": tasks,
        "aggregate": summarize_task_rows(tasks),
        "zero_canonical_writeback": True,
    }


def _validation_trigger(result: Mapping[str, Any]) -> str | None:
    if result.get("status") != "ok":
        code = result.get("error_code")
        if code in {"retrieval_failed", "reasoner_unavailable"}:
            return "TRANSPORT_FAILURE"
        if code == "PARSE_FAILURE":
            return "PARSE_FAILURE"
        if code == "SCHEMA_FAILURE":
            return "SCHEMA_FAILURE"
        if code == "CITATION_ID_FAILURE":
            return "CITATION_ID_FAILURE"
        if code == "WORKER_CONTRACT_FAILURE":
            return "WORKER_CONTRACT_FAILURE"
        return "WORKER_CONTRACT_FAILURE"
    validation = result.get("validation", {})
    if not isinstance(validation, Mapping):
        return "WORKER_CONTRACT_FAILURE"
    if validation.get("transport_valid") is False:
        return "TRANSPORT_FAILURE"
    if validation.get("parse_valid") is False:
        return "PARSE_FAILURE"
    if validation.get("schema_valid") is False:
        return "SCHEMA_FAILURE"
    if validation.get("citation_id_valid") is False:
        return "CITATION_ID_FAILURE"
    if validation.get("contract_valid") is False:
        return "WORKER_CONTRACT_FAILURE"
    return None


def _fresh_historian_call(
    *,
    question: str,
    historian_base_url: str,
    model_spec: Mapping[str, Any],
    worker_fn: Callable[..., Mapping[str, Any]],
    request_label: str,
    work_dir_root: Path | None,
    historian_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    return dict(
        worker_fn(
            question,
            model_id=model_spec["model_id"],
            model_base_url=model_spec["base_url"],
            historian_base_url=historian_base_url,
            historian_evidence=historian_evidence,
            request_label=request_label,
            work_dir_root=work_dir_root,
        )
    )


def run_task_with_escalation(
    task: Mapping[str, Any],
    *,
    capability_profiles: Mapping[str, Any],
    available_models: list[Mapping[str, Any]],
    historian_base_url: str,
    worker_fn: Callable[..., Mapping[str, Any]],
    evidence_fn: Callable[..., Mapping[str, Any]],
    route_fn: Callable[[str, Mapping[str, Any], list[Mapping[str, Any]]], Mapping[str, Any]] = route_initial_model,
    work_dir_root: Path | None = Path(".work") / "historian_dynamic_escalation_v1",
) -> dict[str, Any]:
    validate_capability_profile(capability_profiles)
    task_id = task["id"]
    task_class = task["task_class"]
    question = task["question"]
    initial_route = dict(route_fn(task_class, capability_profiles, available_models))
    primary_model = initial_route.get("selected_model")
    if primary_model is None:
        return {
            "task_id": task_id,
            "task_class": task_class,
            "initial_routing_decision": initial_route,
            "primary_model": None,
            "primary_request": None,
            "primary_outcome": None,
            "escalation_trigger": None,
            "fallback_model": None,
            "fallback_request": None,
            "final_worker": None,
            "final_result_status": "NO_QUALIFIED_FALLBACK",
            "attempt_count": 0,
        }

    primary_spec = next(model for model in available_models if model["model_id"] == primary_model)
    primary_evidence = dict(
        evidence_fn(
            question,
            historian_base_url=historian_base_url,
            request_label=f"{task_id}:primary:evidence",
            work_dir_root=work_dir_root,
        )
    )
    primary_result = _fresh_historian_call(
        question=question,
        historian_base_url=historian_base_url,
        model_spec=primary_spec,
        worker_fn=worker_fn,
        historian_evidence=primary_evidence,
        request_label=f"{task_id}:primary",
        work_dir_root=work_dir_root,
    )
    trigger = _validation_trigger(primary_result)
    attempts = [
        {"worker": primary_model, "result": primary_result, "request_id": primary_result.get("request_id"), "historian_request_id": primary_result.get("historian_request_id")},
    ]
    fallback_result = None
    fallback_model = None
    if trigger in DETERMINISTIC_ESCALATION_TRIGGERS:
        fallback = select_fallback_model(task_class, capability_profiles, available_models, exclude_model=primary_model)
        if fallback is None:
            return {
                "task_id": task_id,
                "task_class": task_class,
                "initial_routing_decision": initial_route,
                "primary_model": primary_model,
                "primary_request": attempts[0],
                "primary_outcome": primary_result,
                "escalation_trigger": trigger,
                "fallback_model": None,
                "fallback_request": None,
                "final_worker": primary_model,
                "final_result_status": "NO_QUALIFIED_FALLBACK",
                "attempt_count": 1,
                "attempts": attempts,
            }
        fallback_model = fallback["selected_model"]
        fallback_spec = next(model for model in available_models if model["model_id"] == fallback_model)
        fallback_evidence = dict(
            evidence_fn(
                question,
                historian_base_url=historian_base_url,
                request_label=f"{task_id}:fallback:evidence",
                work_dir_root=work_dir_root,
            )
        )
        fallback_result = _fresh_historian_call(
            question=question,
            historian_base_url=historian_base_url,
            model_spec=fallback_spec,
            worker_fn=worker_fn,
            historian_evidence=fallback_evidence,
            request_label=f"{task_id}:fallback",
            work_dir_root=work_dir_root,
        )
        attempts.append(
            {
                "worker": fallback_model,
                "result": fallback_result,
                "request_id": fallback_result.get("request_id"),
                "historian_request_id": fallback_result.get("historian_request_id"),
            }
        )
    final_result = fallback_result or primary_result
    return {
        "task_id": task_id,
        "task_class": task_class,
        "initial_routing_decision": initial_route,
        "primary_model": primary_model,
        "primary_consumer_request_id": primary_result.get("consumer_request_id"),
        "primary_historian_request_id": primary_evidence.get("request_id") or primary_evidence.get("historian_request_id") or primary_evidence.get("id"),
        "primary_request": {
            "request_label": f"{task_id}:primary",
            "historian_request_id": primary_evidence.get("request_id") or primary_evidence.get("historian_request_id") or primary_evidence.get("id"),
            "consumer_request_id": primary_result.get("consumer_request_id"),
        },
        "primary_outcome": primary_result,
        "escalation_trigger": trigger or "NONE",
        "fallback_model": fallback_model,
        "fallback_consumer_request_id": fallback_result.get("consumer_request_id") if fallback_result is not None else None,
        "fallback_historian_request_id": fallback_evidence.get("request_id") or fallback_evidence.get("historian_request_id") or fallback_evidence.get("id") if fallback_result is not None else None,
        "fallback_request": {
            "request_label": f"{task_id}:fallback",
            "historian_request_id": fallback_evidence.get("request_id") or fallback_evidence.get("historian_request_id") or fallback_evidence.get("id") if fallback_result is not None else None,
            "consumer_request_id": fallback_result.get("consumer_request_id") if fallback_result is not None else None,
        }
        if fallback_result is not None
        else None,
        "final_worker": fallback_model or primary_model,
        "final_result_status": final_result.get("status"),
        "final_result": final_result,
        "attempt_count": len(attempts),
        "attempts": attempts,
    }
