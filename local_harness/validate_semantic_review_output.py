#!/usr/bin/env python3
"""Validation helpers for advisory semantic review outputs."""

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
    verdict = payload.get("verdict")
    if verdict not in {"pass_review", "hold"}:
        problems.append("verdict must be pass_review or hold")
    unsupported_claims = payload.get("unsupported_claims")
    if not isinstance(unsupported_claims, list):
        problems.append("unsupported_claims must be a list")
    else:
        projected = projected_paths or set()
        for idx, claim in enumerate(unsupported_claims):
            if not isinstance(claim, dict):
                problems.append(f"unsupported_claims[{idx}] must be an object")
                continue
            if not isinstance(claim.get("claim"), str) or not claim["claim"].strip():
                problems.append(f"unsupported_claims[{idx}].claim must be a non-empty string")
            if not isinstance(claim.get("reason"), str) or not claim["reason"].strip():
                problems.append(f"unsupported_claims[{idx}].reason must be a non-empty string")
            evidence = claim.get("evidence")
            if not isinstance(evidence, list):
                problems.append(f"unsupported_claims[{idx}].evidence must be a list")
                continue
            for eidx, item in enumerate(evidence):
                if not isinstance(item, dict):
                    problems.append(f"unsupported_claims[{idx}].evidence[{eidx}] must be an object")
                    continue
                path = item.get("path")
                detail = item.get("detail")
                if not isinstance(path, str) or not path.strip():
                    problems.append(
                        f"unsupported_claims[{idx}].evidence[{eidx}].path must be a non-empty string"
                    )
                elif projected and path not in projected:
                    problems.append(
                        f"unsupported_claims[{idx}].evidence[{eidx}].path is not projected"
                    )
                if not isinstance(detail, str) or not detail.strip():
                    problems.append(
                        f"unsupported_claims[{idx}].evidence[{eidx}].detail must be a non-empty string"
                    )
    internal_consistency = payload.get("internal_consistency")
    if internal_consistency not in {"consistent", "inconsistent"}:
        problems.append("internal_consistency must be consistent or inconsistent")
    review_reason = payload.get("review_reason")
    if not isinstance(review_reason, str) or not review_reason.strip():
        problems.append("review_reason must be a non-empty string")
    return problems
