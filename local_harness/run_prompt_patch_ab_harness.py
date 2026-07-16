#!/usr/bin/env python3
"""Deterministic fixture-based A/B harness for prompt patch comparisons."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence


SCHEMA_NAME = "prompt_patch_ab_cases_v1"
RESULT_SCHEMA_NAME = "prompt_patch_ab_result_v1"
SUPPORTED_EXPECTED_CONTRACT_KEYS = {
    "required_allowed_targets",
    "forbidden_allowed_targets",
    "required_held_targets",
    "required_json_fields",
    "forbidden_completion_claim",
    "requires_scope_expansion_flag",
}


class PromptPatchABHarnessError(ValueError):
    """Raised when harness cases or contracts are malformed."""


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PromptPatchABHarnessError(f"case file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PromptPatchABHarnessError(f"invalid JSON in {path}: {exc.msg}") from exc


def _require_object(value: Any, *, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PromptPatchABHarnessError(f"{context} must be a JSON object")
    return value


def _require_list(value: Any, *, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise PromptPatchABHarnessError(f"{context} must be a JSON list")
    return value


def _require_str(value: Any, *, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PromptPatchABHarnessError(f"{context} must be a non-empty string")
    return value


def _normalize_string_list(value: Any, *, context: str) -> list[str]:
    items = _require_list(value, context=context)
    result: list[str] = []
    for index, item in enumerate(items):
        if not isinstance(item, str) or not item.strip():
            raise PromptPatchABHarnessError(f"{context}[{index}] must be a non-empty string")
        result.append(item)
    return result


def _validate_case(case: Any, *, index: int) -> dict[str, Any]:
    payload = _require_object(case, context=f"cases[{index}]")
    required_keys = {
        "case_id",
        "failure_mode",
        "prompt_patch_id",
        "task_summary",
        "expected_contract",
        "baseline_output",
        "patched_output",
    }
    missing = sorted(required_keys - set(payload))
    if missing:
        raise PromptPatchABHarnessError(
            f"cases[{index}] missing required fields: {', '.join(missing)}"
        )

    case_id = _require_str(payload["case_id"], context=f"cases[{index}].case_id")
    _require_str(payload["failure_mode"], context=f"cases[{index}].failure_mode")
    _require_str(payload["prompt_patch_id"], context=f"cases[{index}].prompt_patch_id")
    _require_str(payload["task_summary"], context=f"cases[{index}].task_summary")
    expected_contract = _require_object(payload["expected_contract"], context=f"cases[{index}].expected_contract")

    unknown = sorted(set(expected_contract) - SUPPORTED_EXPECTED_CONTRACT_KEYS)
    if unknown:
        raise PromptPatchABHarnessError(
            f"cases[{index}].expected_contract contains unsupported keys: {', '.join(unknown)}"
        )

    for key in ("required_allowed_targets", "forbidden_allowed_targets", "required_held_targets"):
        if key in expected_contract:
            _normalize_string_list(expected_contract[key], context=f"cases[{index}].expected_contract.{key}")

    if "required_json_fields" in expected_contract:
        _normalize_string_list(expected_contract["required_json_fields"], context=f"cases[{index}].expected_contract.required_json_fields")

    if "forbidden_completion_claim" in expected_contract:
        if not isinstance(expected_contract["forbidden_completion_claim"], bool):
            raise PromptPatchABHarnessError(
                f"cases[{index}].expected_contract.forbidden_completion_claim must be boolean"
            )
    if "requires_scope_expansion_flag" in expected_contract:
        if not isinstance(expected_contract["requires_scope_expansion_flag"], bool):
            raise PromptPatchABHarnessError(
                f"cases[{index}].expected_contract.requires_scope_expansion_flag must be boolean"
            )

    baseline_output = _require_object(payload["baseline_output"], context=f"cases[{index}].baseline_output")
    patched_output = _require_object(payload["patched_output"], context=f"cases[{index}].patched_output")

    return {
        "case_id": case_id,
        "failure_mode": payload["failure_mode"],
        "prompt_patch_id": payload["prompt_patch_id"],
        "task_summary": payload["task_summary"],
        "expected_contract": expected_contract,
        "baseline_output": baseline_output,
        "patched_output": patched_output,
    }


def _get_str_list(payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key, [])
    if value is None:
        return []
    return _normalize_string_list(value, context=key)


def _evaluate_output(output: dict[str, Any], contract: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if "required_allowed_targets" in contract:
        required = _normalize_string_list(contract["required_allowed_targets"], context="expected_contract.required_allowed_targets")
        allowed_targets = _get_str_list(output, "allowed_targets")
        for target in required:
            if target not in allowed_targets:
                failures.append(f"missing required allowed target: {target}")

    if "forbidden_allowed_targets" in contract:
        forbidden = _normalize_string_list(contract["forbidden_allowed_targets"], context="expected_contract.forbidden_allowed_targets")
        allowed_targets = _get_str_list(output, "allowed_targets")
        for target in forbidden:
            if target in allowed_targets:
                failures.append(f"forbidden allowed target present: {target}")

    if "required_held_targets" in contract:
        required = _normalize_string_list(contract["required_held_targets"], context="expected_contract.required_held_targets")
        held_targets = _get_str_list(output, "held_targets")
        for target in required:
            if target not in held_targets:
                failures.append(f"missing required held target: {target}")

    if "required_json_fields" in contract:
        required_fields = _normalize_string_list(contract["required_json_fields"], context="expected_contract.required_json_fields")
        for field in required_fields:
            if field not in output:
                failures.append(f"missing required JSON field: {field}")

    if contract.get("forbidden_completion_claim") is True:
        text = json.dumps(output, sort_keys=True).lower()
        if "fixed" in text or "validated" in text or "pass" in text or "accepted" in text:
            failures.append("forbidden completion claim present")

    if "requires_scope_expansion_flag" in contract:
        required_flag = contract["requires_scope_expansion_flag"]
        actual = output.get("scope_expansion_required")
        if actual is not required_flag:
            failures.append(
                f"scope_expansion_required must be {str(required_flag).lower()}"
            )

    return failures


def _score_case(case: dict[str, Any]) -> dict[str, Any]:
    contract = case["expected_contract"]
    baseline_failures = _evaluate_output(case["baseline_output"], contract)
    patched_failures = _evaluate_output(case["patched_output"], contract)

    baseline_status = "passed" if not baseline_failures else "failed"
    patched_status = "passed" if not patched_failures else "failed"

    if baseline_status == "failed" and patched_status == "passed":
        result = "improved"
    elif baseline_status == "passed" and patched_status == "passed":
        result = "unchanged_pass"
    elif baseline_status == "failed" and patched_status == "failed":
        result = "unchanged_fail"
    else:
        result = "regressed"

    return {
        "case_id": case["case_id"],
        "failure_mode": case["failure_mode"],
        "prompt_patch_id": case["prompt_patch_id"],
        "task_summary": case["task_summary"],
        "baseline_status": baseline_status,
        "patched_status": patched_status,
        "result": result,
        "baseline_failures": baseline_failures,
        "patched_failures": patched_failures,
    }


def run_prompt_patch_ab_harness(cases_path: Path) -> dict[str, Any]:
    payload = _require_object(_read_json(cases_path), context="case file")
    if payload.get("harness_schema") != SCHEMA_NAME:
        raise PromptPatchABHarnessError(f"case file harness_schema must be {SCHEMA_NAME!r}")
    cases = _require_list(payload.get("cases"), context="cases")

    validated_cases = [_validate_case(case, index=index) for index, case in enumerate(cases)]
    results = [_score_case(case) for case in validated_cases]

    cases_total = len(results)
    improved_total = sum(1 for item in results if item["result"] == "improved")
    unchanged_pass_total = sum(1 for item in results if item["result"] == "unchanged_pass")
    unchanged_fail_total = sum(1 for item in results if item["result"] == "unchanged_fail")
    regressed_total = sum(1 for item in results if item["result"] == "regressed")
    diagnostics: list[str] = []
    if regressed_total:
        diagnostics.append("at least one case regressed")

    return {
        "harness_schema": RESULT_SCHEMA_NAME,
        "cases_total": cases_total,
        "improved_total": improved_total,
        "unchanged_pass_total": unchanged_pass_total,
        "unchanged_fail_total": unchanged_fail_total,
        "regressed_total": regressed_total,
        "results": results,
        "diagnostics": diagnostics,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = run_prompt_patch_ab_harness(args.cases)
    except PromptPatchABHarnessError as exc:
        payload = {
            "harness_schema": RESULT_SCHEMA_NAME,
            "cases_total": 0,
            "improved_total": 0,
            "unchanged_pass_total": 0,
            "unchanged_fail_total": 0,
            "regressed_total": 0,
            "results": [],
            "diagnostics": [str(exc)],
        }
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        json.dump(payload, sys.stdout, sort_keys=True, indent=2)
        sys.stdout.write("\n")
        return 1

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    json.dump(result, sys.stdout, sort_keys=True, indent=2)
    sys.stdout.write("\n")
    return 0 if result["regressed_total"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
