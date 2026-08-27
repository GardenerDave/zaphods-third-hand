from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .capability_profile import CapabilityProfileError, validate_capability_profile


def _priority(model: Mapping[str, Any]) -> tuple[int, str]:
    raw = model.get("priority")
    if isinstance(raw, int):
        return raw, str(model.get("model_id", ""))
    return 10_000, str(model.get("model_id", ""))


def legacy_normalize_capability_entry(entry: Mapping[str, Any] | None) -> dict[str, str]:
    if not entry:
        return {"qualification": "UNMEASURED", "routing_recommendation": "UNMEASURED"}
    qualification = entry.get("qualification")
    routing = entry.get("routing_recommendation")
    observed = entry.get("observed_outcome")
    if qualification is None and observed == "ESCALATION_CANDIDATE":
        return {"qualification": "NOT_QUALIFIED", "routing_recommendation": "ESCALATE"}
    if qualification is None and observed == "CAN_HANDLE":
        return {"qualification": "CAN_HANDLE", "routing_recommendation": "DIRECT"}
    if qualification is None and observed == "NOT_QUALIFIED":
        return {"qualification": "NOT_QUALIFIED", "routing_recommendation": "DO_NOT_SELECT"}
    qualification = qualification or "UNMEASURED"
    if routing is None:
        if qualification == "CAN_HANDLE":
            routing = "DIRECT"
        elif qualification == "NOT_QUALIFIED":
            routing = "DO_NOT_SELECT"
        else:
            routing = "UNMEASURED"
    return {"qualification": qualification, "routing_recommendation": routing}


def _select_model(task_class: str, capability_profiles: Mapping[str, Any], available_models: list[Mapping[str, Any]], *, exclude_model: str | None = None) -> dict[str, Any] | None:
    normalized = validate_capability_profile(capability_profiles)["models"]
    candidates: list[dict[str, Any]] = []
    for model in sorted(available_models, key=_priority):
        model_id = model.get("model_id")
        if not isinstance(model_id, str) or model_id == exclude_model:
            continue
        model_profile = normalized.get(model_id, {})
        capability = legacy_normalize_capability_entry(model_profile.get("capabilities", {}).get(task_class))
        candidates.append(
            {
                "model_id": model_id,
                "model": model,
                "qualification": capability["qualification"],
                "routing_recommendation": capability["routing_recommendation"],
            }
        )

    direct = [c for c in candidates if c["qualification"] == "CAN_HANDLE" and c["routing_recommendation"] == "DIRECT"]
    if direct:
        chosen = direct[0]
        return {
            "task_class": task_class,
            "selected_model": chosen["model_id"],
            "routing_basis": "smallest_qualified_capable_model",
            "profile_outcome": chosen["qualification"],
            "selection_status": "direct",
        }

    escalate = [c for c in candidates if c["routing_recommendation"] == "ESCALATE"]
    if escalate:
        chosen = escalate[0]
        return {
            "task_class": task_class,
            "selected_model": chosen["model_id"],
            "routing_basis": "legacy_escalation_candidate",
            "profile_outcome": chosen["qualification"],
            "selection_status": "escalation",
        }

    if candidates:
        chosen = candidates[0]
        return {
            "task_class": task_class,
            "selected_model": chosen["model_id"],
            "routing_basis": "no_measured_capable_model",
            "profile_outcome": chosen["qualification"],
            "selection_status": "unmeasured",
        }
    return None


def route_initial_model(task_class: str, capability_profiles: Mapping[str, Any], available_models: list[Mapping[str, Any]]) -> dict[str, Any]:
    selected = _select_model(task_class, capability_profiles, available_models)
    if selected is None:
        return {"task_class": task_class, "selected_model": None, "routing_basis": "no_available_model", "profile_outcome": "UNMEASURED", "selection_status": "unmeasured"}
    return selected


def select_fallback_model(task_class: str, capability_profiles: Mapping[str, Any], available_models: list[Mapping[str, Any]], *, exclude_model: str) -> dict[str, Any] | None:
    selected = _select_model(task_class, capability_profiles, available_models, exclude_model=exclude_model)
    if selected is None:
        return None
    if selected["selected_model"] == exclude_model:
        return None
    if selected["selection_status"] != "direct":
        return None
    return selected
