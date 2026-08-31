#!/usr/bin/env python3
"""Minimal validator for the experimental epistemic observation contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("JSON object required")
    return payload


def validate(payload: dict[str, Any], projected_paths: set[str] | None = None) -> list[str]:
    problems: list[str] = []
    conclusion = payload.get("conclusion")
    if not isinstance(conclusion, dict):
        problems.append("conclusion must be an object")
    else:
        established = conclusion.get("established")
        not_established = conclusion.get("not_established")
        if not isinstance(established, list) or not established:
            problems.append("conclusion.established must be a non-empty list")
        if not isinstance(not_established, list) or not not_established:
            problems.append("conclusion.not_established must be a non-empty list")
    findings = payload.get("findings")
    if not isinstance(findings, list) or not findings:
        problems.append("findings must be a non-empty list")
    else:
        projected = projected_paths or set()
        for idx, finding in enumerate(findings):
            if not isinstance(finding, dict):
                problems.append(f"finding[{idx}] must be an object")
                continue
            if not isinstance(finding.get("claim"), str) or not finding["claim"].strip():
                problems.append(f"finding[{idx}].claim must be a non-empty string")
            evidence = finding.get("evidence")
            if not isinstance(evidence, list) or not evidence:
                problems.append(f"finding[{idx}].evidence must be a non-empty list")
                continue
            for eidx, item in enumerate(evidence):
                if not isinstance(item, dict):
                    problems.append(f"finding[{idx}].evidence[{eidx}] must be an object")
                    continue
                path = item.get("path")
                detail = item.get("detail")
                if not isinstance(path, str) or not path.strip():
                    problems.append(f"finding[{idx}].evidence[{eidx}].path must be a non-empty string")
                elif projected and path not in projected:
                    problems.append(f"finding[{idx}].evidence[{eidx}].path is not projected")
                if not isinstance(detail, str) or not detail.strip():
                    problems.append(f"finding[{idx}].evidence[{eidx}].detail must be a non-empty string")
    reason = payload.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        problems.append("reason must be a non-empty string")
    return problems

