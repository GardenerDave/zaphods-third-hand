#!/usr/bin/env python3
"""Experiment-only Run 6 validation-gated sequential policy."""

from __future__ import annotations

from typing import Any, Mapping

POLICY_NAMES = ("external_everywhere", "validation_gated_economic_escalation")
FAMILY_MATRIX = {
    "triage-routing": {
        "external_everywhere": "external_teacher",
        "validation_gated_economic_escalation": "external_teacher",
    },
    "scope-authority-boundary": {
        "external_everywhere": "external_teacher",
        "validation_gated_economic_escalation": "local_teacher",
    },
}
RESOURCE_PRIORS_MS = {
    "worker_time_ms": 5276.567,
    "local_teacher_time_ms": 16220.624,
    "external_teacher_time_ms": 28704.012,
}


class Run6PolicyError(ValueError):
    pass


def choose_initial_intervention(family: str, policy: str) -> str:
    try:
        return FAMILY_MATRIX[family][policy]
    except KeyError as exc:
        raise Run6PolicyError(f"unsupported Run 6 policy/family: {policy}/{family}") from exc


def should_escalate(validation: Mapping[str, Any] | None) -> bool:
    """Escalate only after a completed deterministic validation failure."""
    return bool(validation and validation.get("validation_status") == "failed")


def verify_policy() -> None:
    if choose_initial_intervention("triage-routing", "external_everywhere") != "external_teacher":
        raise Run6PolicyError("control triage drift")
    if choose_initial_intervention("scope-authority-boundary", "external_everywhere") != "external_teacher":
        raise Run6PolicyError("control scope drift")
    if choose_initial_intervention("triage-routing", "validation_gated_economic_escalation") != "external_teacher":
        raise Run6PolicyError("treatment triage drift")
    if choose_initial_intervention("scope-authority-boundary", "validation_gated_economic_escalation") != "local_teacher":
        raise Run6PolicyError("treatment scope drift")
    if should_escalate({"validation_status": "passed"}) or not should_escalate({"validation_status": "failed"}):
        raise Run6PolicyError("validation gate drift")
    if should_escalate({"validation_status": "infrastructure_error"}) or should_escalate(None):
        raise Run6PolicyError("infrastructure must not trigger capability escalation")
