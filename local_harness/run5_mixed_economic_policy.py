#!/usr/bin/env python3
"""Experiment-only mixed-portfolio Run 5 policy.

This module is deliberately narrower than production routing.  It consumes
only the reviewed Run 4 evidence bindings and exposes the two frozen policy
matrices used by the Run 5 comparison.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


POLICY_NAMES = ("external_everywhere", "evidence_qualified_economic")
FAMILY_MATRIX = {
    "triage-routing": {
        "external_everywhere": "external_teacher",
        "evidence_qualified_economic": "external_teacher",
    },
    "scope-authority-boundary": {
        "external_everywhere": "external_teacher",
        "evidence_qualified_economic": "local_teacher",
    },
}
RESOLUTIONS = {"triage-routing": "task_family", "scope-authority-boundary": "failure_class"}
RESOURCE_PRIORS_MS = {
    "worker_time_ms": 5276.567,
    "local_teacher_time_ms": 16220.624,
    "external_teacher_time_ms": 28704.012,
}
ACTION_COSTS_MS = {
    "local_teacher": 21497.191,
    "external_teacher": 33980.579,
}


class Run5PolicyError(ValueError):
    pass


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def choose_intervention(family: str, policy: str) -> str:
    try:
        return FAMILY_MATRIX[family][policy]
    except KeyError as exc:
        raise Run5PolicyError(f"unsupported Run 5 policy/family: {policy}/{family}") from exc


def verify_matrix() -> None:
    if choose_intervention("triage-routing", "external_everywhere") != "external_teacher":
        raise Run5PolicyError("control triage drift")
    if choose_intervention("scope-authority-boundary", "external_everywhere") != "external_teacher":
        raise Run5PolicyError("control scope drift")
    if choose_intervention("triage-routing", "evidence_qualified_economic") != "external_teacher":
        raise Run5PolicyError("treatment triage drift")
    if choose_intervention("scope-authority-boundary", "evidence_qualified_economic") != "local_teacher":
        raise Run5PolicyError("treatment scope drift")
    if sum(FAMILY_MATRIX[family]["external_everywhere"] != FAMILY_MATRIX[family]["evidence_qualified_economic"] for family in FAMILY_MATRIX) != 1:
        raise Run5PolicyError("Run 5 policies must differ only on scope")


def load_policy_freeze(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    expected = dict(value)
    recorded = expected.get("policy_sha256")
    expected["policy_sha256"] = None
    digest = canonical_sha256(expected)
    if recorded != digest:
        raise Run5PolicyError("Run 5 policy freeze digest mismatch")
    if value.get("family_action_matrix") != FAMILY_MATRIX:
        raise Run5PolicyError("Run 5 policy matrix mismatch")
    verify_matrix()
    return value
