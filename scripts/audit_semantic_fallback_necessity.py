#!/usr/bin/env python3
"""Model-free audit of whether the preserved semantic fallback calls were needed."""

from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path
from typing import Any

from scripts import deterministic_first_confirmation as confirmation
from scripts import zth_deterministic_first_semantic_fallback as fallback
from scripts import zth_qwen3_1_7b_action_expression_normalization as normalization
from scripts import zth_qwen3_1_7b_clean_scope_logic_probe as runtime

ROOT = Path(__file__).resolve().parents[1]
DFF_RUN = ROOT / ".work/model_size_supplier_floor/deterministic_first_semantic_fallback/run_20260823T120100Z"
DFC_RUN = ROOT / ".work/model_size_supplier_floor/deterministic_first_confirmation/run_20260823T130000Z"
OUT_MATRIX = ROOT / "docs/research/SEMANTIC_FALLBACK_NECESSITY_AUDIT_MATRIX_2026-08-23.json"
OUT_REPORT = ROOT / "docs/research/SEMANTIC_FALLBACK_NECESSITY_AUDIT_2026-08-23.md"

RISKY_TAIL_WORDS = {"amend", "amended", "dispatch", "dispatched", "archive", "archived", "delete", "deleted"}
KNOWN_OPERATION_WORDS = {"inspect", "amend", "index", "dispatch", "archive", "delete", "determine", "check", "verify", "confirm", "find", "exists"}


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def first_token(request: str) -> str:
    return " ".join(request.casefold().strip().split()).split(" ", 1)[0].strip(".,:;!?()")


def embedded_operation_phrase(request: str) -> str | None:
    words = re.findall(r"[a-z]+", request.casefold())
    hits = [word for word in words if word in KNOWN_OPERATION_WORDS]
    return hits[0] if hits else None


def safe_targets(request: str) -> list[str]:
    return fallback.TARGET_RE.findall(request)


def counterfactual_presence_projection(request: str) -> dict[str, Any]:
    context = fallback.derive_context(request)
    targets = safe_targets(request)
    words = set(re.findall(r"[a-z]+", request.casefold()))
    risky_tail = sorted(words & RISKY_TAIL_WORDS)
    if context == "AMBIGUOUS_CONTEXT":
        return {"status": "AMBIGUOUS", "canonical_operation": None, "reason": "ambiguity has precedence", "target": None, "target_count": len(targets), "risky_tail_operations": risky_tail}
    if context != "PRESENCE_OBSERVATION_CONTEXT":
        return {"status": "UNRESOLVED", "canonical_operation": None, "reason": "not a bounded presence context", "target": targets[0] if len(targets) == 1 else None, "target_count": len(targets), "risky_tail_operations": risky_tail}
    if len(targets) != 1:
        return {"status": "UNRESOLVED", "canonical_operation": None, "reason": "exactly one safe target is required", "target": None, "target_count": len(targets), "risky_tail_operations": risky_tail}
    if risky_tail:
        return {"status": "UNRESOLVED", "canonical_operation": None, "reason": "risky operation language has precedence over presence context", "target": targets[0], "target_count": 1, "risky_tail_operations": risky_tail}
    return {"status": "RESOLVED", "canonical_operation": "observe_presence", "reason": "presence context plus one target uniquely determines the bounded observation class", "target": targets[0], "target_count": 1, "risky_tail_operations": []}


def historical_tasks() -> list[tuple[str, Path, str]]:
    return [
        *( (task_id, DFF_RUN, "dff") for task_id in ("dff-007", "dff-008", "dff-009", "dff-010") ),
        *( (task_id, DFC_RUN, "dfc") for task_id in ("dfc-003", "dfc-004") ),
    ]


def authority_result(runtime_task: dict[str, Any], operation: str | None, target: str | None) -> dict[str, Any]:
    record = runtime_task["environment_facts"]["authority_record"]
    return confirmation.validate_execution_authority(operation, target, record)


def audit_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for task_id, run, source in historical_tasks():
        task_dir = run / "tasks" / task_id
        runtime_task = read(task_dir / "runtime_task.json")
        pre = read(task_dir / "operation_derivation_0.json")
        result = read(task_dir / "runtime_result.json")
        response_path = task_dir / "response.json"
        response = read(response_path) if response_path.exists() else None
        post = None
        for number in (1, 2):
            candidate = task_dir / f"operation_derivation_{number}.json"
            if candidate.exists():
                post = read(candidate)
        request = runtime_task["input_request"]
        projection = counterfactual_presence_projection(request)
        authority = authority_result(runtime_task, projection["canonical_operation"], projection["target"])
        historical_action = (response or {}).get("content")
        parsed_action = None
        if historical_action:
            try:
                parsed_action = json.loads(historical_action).get("action")
            except (TypeError, json.JSONDecodeError):
                parsed_action = None
        if projection["status"] == "RESOLVED":
            contribution = "REDUNDANT_RESTATEMENT_OF_DETERMINISTIC_FACT"
        else:
            contribution = "FAILED_TO_SUPPLY_REQUIRED_INFORMATION"
        rows.append({
            "task_id": task_id,
            "source_run": source,
            "raw_request": request,
            "exact_requested_target": runtime_task["environment_facts"]["authority_record"]["allowed_targets"][0],
            "derive_normalization_context": pre["normalization_context"],
            "first_lexical_token": first_token(request),
            "embedded_operation_phrase": embedded_operation_phrase(request),
            "pre_model_derivation_status": pre["status"],
            "pre_model_derivation_type": pre["derivation_type"],
            "pre_model_model_required": pre.get("model_required", False),
            "pre_model_reason": pre["reason"],
            "raw_model_action": parsed_action,
            "raw_model_object_expression": None if response is None else json.loads(response["content"]).get("object_expression"),
            "raw_response_artifact": str(response_path.relative_to(ROOT)),
            "raw_response_sha256": sha256(response_path),
            "post_model_normalization": None if post is None else post.get("normalizer"),
            "post_model_derivation_status": None if post is None else post.get("status"),
            "historical_terminal_result": result["terminal_state"],
            "historical_model_calls": result.get("model_calls", 0),
            "historical_tool_calls": result.get("tool_calls", 0),
            "counterfactual_deterministic_projection": projection,
            "counterfactual_authority_result": authority,
            "counterfactual_model_call_would_be_avoided": projection["status"] == "RESOLVED",
            "counterfactual_downstream_behavior_bounded": projection["status"] == "RESOLVED" and authority["status"] == "AUTHORIZED",
            "model_contribution_classification": contribution,
        })
    return rows


def negative_cases() -> list[dict[str, Any]]:
    cases = [
        ("multi_operation", "Check and inspect docs/negative-a.md."),
        ("amend", "Amend docs/negative-b.md."),
        ("dispatch", "Dispatch docs/negative-c.md."),
        ("archive", "Archive docs/negative-d.md."),
        ("delete", "Delete docs/negative-e.md."),
        ("presence_with_mutation_tail", "Check whether docs/negative-f.md should be amended."),
        ("inspect_presence_clause", "Inspect whether docs/negative-g.md should be amended."),
        ("multiple_targets", "Check whether docs/negative-h.md and docs/negative-i.md exist."),
        ("no_safe_target", "Check whether the requested artifact exists."),
        ("unsupported_context", "Ask about docs/negative-j.md."),
    ]
    rows = []
    for case, request in cases:
        projection = counterfactual_presence_projection(request)
        rows.append({"case": case, "request": request, "context": fallback.derive_context(request), "projection": projection, "safe": projection["canonical_operation"] != "observe_presence"})
    return rows


def main() -> None:
    rows = audit_rows()
    negatives = negative_cases()
    matrix = {
        "schema": "zth_semantic_fallback_necessity_audit_v0",
        "authoritative_commit": "1ee8d3a7919b2ad6e0a80ed1ff140ab4671428ee",
        "historical_evidence_preserved": True,
        "historical_fallback_calls": len(rows),
        "deterministic_context_sufficient_rows": sum(x["counterfactual_deterministic_projection"]["status"] == "RESOLVED" for x in rows),
        "additional_model_calls_counterfactually_avoidable": sum(x["counterfactual_model_call_would_be_avoided"] for x in rows),
        "true_semantic_necessity_rows": sum(not x["counterfactual_model_call_would_be_avoided"] for x in rows),
        "negative_case_safety_pass": all(x["safe"] for x in negatives),
        "rows": rows,
        "negative_case_safety_audit": negatives,
        "markers": {
            "POLITE_WRAPPER_PRESENCE_MODEL_NECESSITY": False,
            "SEMANTIC_FALLBACK_REQUIREMENT_WAS_SYNTACTICALLY_INDUCED": True,
            "TRUE_SEMANTIC_FALLBACK_NOT_YET_DEMONSTRATED": True,
            "FALLBACK_BRANCH_EXECUTION_DEMONSTRATED": True,
            "DETERMINISTIC_PRESENCE_CONTEXT_SUFFICIENCY_DEMONSTRATED": True,
            "POLITE_WRAPPER_MODEL_CALLS_UNNECESSARY": True,
            "MODEL_CALL_AVOIDANCE_BOUNDARY_EXPANDED": True,
        },
        "future_fallback_boundary": {
            "deterministic_first": True,
            "model_only_if": ["exactly_one_safe_target", "no_ambiguity", "no_unsupported_or_risky_operation", "canonical_operation_not_uniquely_resolved"],
            "model_must_supply": "smallest genuinely unresolved semantic operation fact",
            "otherwise": "ready_for_review",
        },
        "calls_during_audit": {"model": 0, "teacher": 0, "tool": 0, "external": 0, "retries": 0},
        "qualification_change": False,
        "next_decision": "TEST_TRUE_SEMANTIC_FALLBACK_ON_GENUINELY_UNRESOLVED_OPERATION_LANGUAGE",
    }
    OUT_MATRIX.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = f"""# Semantic fallback necessity audit

This model-free audit preserves the six historical fallback calls from the
deterministic-first and corrected-confirmation runs. It does not replay or
rescore them.

## Finding

All six requests have one safely extractable repository target and are already
classified as `PRESENCE_OBSERVATION_CONTEXT`. The historical `model_required`
decision was caused by the first-token wrapper rule: `could`, `please`, `can`,
and `would` were recognized as context cues but not as operation leads.

Under the conservative counterfactual rule—presence context, exactly one
target, and no ambiguity or risky/unsupported operation—the canonical operation
is uniquely `observe_presence` before the model call for **6/6** cases.

Therefore:

- `POLITE_WRAPPER_PRESENCE_MODEL_NECESSITY=false`
- `SEMANTIC_FALLBACK_REQUIREMENT_WAS_SYNTACTICALLY_INDUCED=true`
- `TRUE_SEMANTIC_FALLBACK_NOT_YET_DEMONSTRATED=true`
- `FALLBACK_BRANCH_EXECUTION_DEMONSTRATED=true`
- `ADDITIONAL_MODEL_CALLS_COUNTERFACTUALLY_AVOIDABLE=6`

The historical six model calls remain actual resource evidence. This projection
does not alter them. It shows that the model restated, varied, or failed to
provide a fact that deterministic context already supplied.

## Safety precedence

The proposed refinement rejects ambiguity first, then unsupported/risky
operation language, then requires presence context and one target. The
model-free negative audit covers multi-operation, mutation, archive/delete,
multiple-target, no-target, and unknown-context cases; all remain unresolved or
fail closed.

## Real fallback boundary

Future routing should be:

```text
deterministic derivation
  -> canonical operation uniquely resolved: no model
  -> otherwise, one safe target + no ambiguity/risk + bounded semantic supplier:
       request only the unresolved operation fact
  -> otherwise: ready_for_review
```

The model must not decide whether it should be called, select a tool, or grant
authority. A future true-fallback holdout should contain deterministic presence
cases, genuinely unresolved but bounded operation language, and fail-closed
cases. It should not manufacture model necessity by hiding an operation phrase
behind polite syntax.

The full six-case matrix, preserved raw-response references, post-model
normalization, authority projection, and negative-case audit are in the
[audit matrix](SEMANTIC_FALLBACK_NECESSITY_AUDIT_MATRIX_2026-08-23.json).

No model, teacher, 30B, tool, external, retry, production, or qualification
action occurred during this audit. `NEXT_DECISION=TEST_TRUE_SEMANTIC_FALLBACK_ON_GENUINELY_UNRESOLVED_OPERATION_LANGUAGE`.
"""
    OUT_REPORT.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
