#!/usr/bin/env python3
"""Experiment-only Run 7 validation-gated scope escalation policy."""

from __future__ import annotations

from typing import Any, Mapping

POLICY_NAMES = ("external_everywhere", "validation_gated_economic_escalation")
FAMILY = "scope-authority-boundary"
RESOURCE_PRIORS_MS = {
    "worker_time_ms": 5276.567,
    "local_teacher_time_ms": 16220.624,
    "external_teacher_time_ms": 28704.012,
}
LOCAL_ACTION_MS = RESOURCE_PRIORS_MS["local_teacher_time_ms"] + RESOURCE_PRIORS_MS["worker_time_ms"]
EXTERNAL_ACTION_MS = RESOURCE_PRIORS_MS["external_teacher_time_ms"] + RESOURCE_PRIORS_MS["worker_time_ms"]
TARGET_COUNT = 20
CANDIDATE_COUNT = 24
PAIR_ORDER_SEED = 20260826


class Run7PolicyError(ValueError):
    pass


def choose_intervention(policy: str) -> str:
    if policy == "external_everywhere":
        return "external_teacher"
    if policy == "validation_gated_economic_escalation":
        return "local_teacher"
    raise Run7PolicyError(f"unsupported Run 7 policy: {policy}")


def should_escalate(validation: Mapping[str, Any] | None) -> bool:
    """Escalate only after completed deterministic validation failure."""
    return bool(validation and validation.get("validation_status") == "failed")


def break_even_escalation_count(selected_count: int = TARGET_COUNT) -> int:
    """Largest integer E for which treatment remains strictly cheaper."""
    control = selected_count * EXTERNAL_ACTION_MS
    for e in range(selected_count + 1):
        if selected_count * LOCAL_ACTION_MS + e * EXTERNAL_ACTION_MS >= control:
            return e - 1
    return selected_count


def verify_policy() -> None:
    if choose_intervention("external_everywhere") != "external_teacher":
        raise Run7PolicyError("control action drift")
    if choose_intervention("validation_gated_economic_escalation") != "local_teacher":
        raise Run7PolicyError("treatment initial action drift")
    if should_escalate({"validation_status": "passed"}) or not should_escalate({"validation_status": "failed"}):
        raise Run7PolicyError("validation gate drift")
    if should_escalate({"validation_status": "infrastructure_error"}) or should_escalate(None):
        raise Run7PolicyError("infrastructure must not trigger escalation")
    if break_even_escalation_count() != 7:
        raise Run7PolicyError("break-even escalation count drift")
