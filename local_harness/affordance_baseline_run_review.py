"""Record review/adjudication of a completed baseline affordance run.

This helper reviews a completed baseline prompt-context run report and its
post-run audit. It does not call a model, rerun the baseline, modify the
original report, apply LARQL, train LoRA, mutate models, write durable memory,
or promote candidates.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_baseline_run_review.v0"
REVIEW_STATUS = "review_only"
PROMOTION_VERDICT = "hold_pending_explicit_experiment_approval"
BASELINE_LANE = "baseline_prompt_context_only"

ACCEPTS_EVIDENCE = "baseline_review_accepts_needs_review_evidence"
REQUIRES_SCORER_REPAIR = "baseline_review_requires_scorer_repair"
REQUIRES_PROMPT_REPAIR = "baseline_review_requires_prompt_repair"
REJECTS_RUN = "baseline_review_rejects_run"
INVALID_INPUT = "invalid_input"

OUTPUT_FILES = ("baseline_run_review.json", "baseline_run_review.md")


def validate_out_dir(path: Path) -> None:
    if any(part == ".." for part in path.parts):
        raise ValueError(f"{path}: output directory must not contain '..'")
    if path.exists() and not path.is_dir():
        raise ValueError(f"{path}: output path exists and is not a directory")


def read_json_object(path: Path, label: str) -> tuple[dict[str, Any], dict[str, bool], list[str]]:
    checks = {
        f"{label}_exists": path.exists(),
        f"{label}_parses": False,
    }
    notes: list[str] = []
    if not checks[f"{label}_exists"]:
        notes.append(f"{label} missing: {path}")
        return {}, checks, notes

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        notes.append(f"{label} JSON parse failed: {exc.msg}")
        return {}, checks, notes

    if not isinstance(payload, dict):
        notes.append(f"{label} is not a JSON object.")
        return {}, checks, notes

    checks[f"{label}_parses"] = True
    return payload, checks, notes


def read_text_file(path: Path, label: str) -> tuple[str, dict[str, bool], list[str]]:
    checks = {f"{label}_exists": path.exists()}
    notes: list[str] = []
    if not checks[f"{label}_exists"]:
        notes.append(f"{label} missing: {path}")
        return "", checks, notes
    return path.read_text(encoding="utf-8"), checks, notes


def parse_audit_verdict(text: str) -> str:
    match = re.search(r"Final audit verdict:\s*`?([A-Za-z0-9_]+)`?", text)
    if match:
        return match.group(1)
    return "unknown"


def contains_all(text: str, terms: list[str]) -> bool:
    lowered = text.lower()
    return all(term.lower() in lowered for term in terms)


def contains_any(text: str, terms: list[str]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def direct_cuda_false_negative(response_text: str) -> bool:
    return (
        contains_any(response_text, ["avoid", "unsafe", "do not", "don't", "not use"])
        and "cuda-only" in response_text.lower()
        and contains_any(response_text, ["no_cuda", "rx580", "rx 580", "amd", "non-nvidia"])
    )


def cross_host_false_negative(response_text: str) -> bool:
    return contains_any(response_text, ["not generalizable", "not generalize"]) and contains_any(
        response_text, ["matching evidence"]
    )


def reverify_false_negative(response_text: str) -> bool:
    return contains_any(response_text, ["reverify", "revalidation"])


def no_durable_promotion_false_negative(response_text: str) -> bool:
    return contains_all(response_text, ["larql", "lora"]) and contains_any(
        response_text, ["durable memory", "promotion"]
    )


def split_workflow_is_clear(response_text: str) -> bool:
    return contains_any(response_text, ["local", "remote"]) and contains_any(
        response_text,
        [
            "active host profile controls",
            "active host controls",
            "active host profile",
            "host profile controls",
        ],
    )


def split_workflow_has_applicability_language(response_text: str) -> bool:
    return contains_any(
        response_text,
        [
            "active host is",
            "constraints are met",
            "candidate applies only if",
            "constraints",
            "no_cuda",
        ],
    )


def adjudicate_prompt(prompt: dict[str, Any]) -> str:
    prompt_id = str(prompt.get("prompt_id") or "")
    response_text = str(prompt.get("response_text") or "")
    prompt_verdict = prompt.get("prompt_verdict")
    model_call_ok = bool(prompt.get("model_call_ok"))

    if prompt_verdict == "pass":
        return "pass"
    if not model_call_ok or prompt_verdict == "fail":
        return "true_failure"
    if prompt_id == "baseline_direct_cuda_on_navigator" and direct_cuda_false_negative(
        response_text
    ):
        return "scorer_false_negative"
    if prompt_id == "baseline_cross_host_boundary" and cross_host_false_negative(response_text):
        return "scorer_false_negative"
    if prompt_id == "baseline_reverify_before_action" and reverify_false_negative(response_text):
        return "scorer_false_negative"
    if prompt_id == "baseline_no_durable_promotion" and no_durable_promotion_false_negative(
        response_text
    ):
        return "scorer_false_negative"
    if prompt_id == "baseline_split_workflow_active_host":
        if split_workflow_is_clear(response_text) or split_workflow_has_applicability_language(
            response_text
        ):
            return "scorer_false_negative"
        return "model_weakness"
    return "not_reviewed"


def prompt_adjudications(prompt_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    adjudications = []
    for prompt in prompt_results:
        label = adjudicate_prompt(prompt)
        adjudications.append(
            {
                "prompt_id": prompt.get("prompt_id"),
                "coverage": prompt.get("coverage"),
                "input_prompt_verdict": prompt.get("prompt_verdict"),
                "model_call_ok": bool(prompt.get("model_call_ok")),
                "adjudication": label,
            }
        )
    return adjudications


def aggregate_review(
    adjudications: list[dict[str, Any]],
    run_report: dict[str, Any],
) -> dict[str, Any]:
    labels = [item["adjudication"] for item in adjudications]
    aggregate_checks = run_report.get("aggregate_checks")
    if not isinstance(aggregate_checks, dict):
        aggregate_checks = {}
    return {
        "pass_count": labels.count("pass"),
        "scorer_false_negative_count": labels.count("scorer_false_negative"),
        "model_weakness_count": labels.count("model_weakness"),
        "true_failure_count": labels.count("true_failure"),
        "not_reviewed_count": labels.count("not_reviewed"),
        "all_model_calls_ok": bool(aggregate_checks.get("all_model_calls_ok")),
        "digests_verified": bool(run_report.get("candidate_digest_verified"))
        and bool(run_report.get("prompt_suite_digest_verified")),
        "promotion_held": run_report.get("promotion_verdict") == PROMOTION_VERDICT,
        "boundaries_preserved": bool(aggregate_checks.get("disallowed_actions_preserved"))
        and bool(aggregate_checks.get("no_repo_write_requested"))
        and run_report.get("promotion_verdict") == PROMOTION_VERDICT,
    }


def recommended_next_step(aggregate: dict[str, Any]) -> str:
    if aggregate["true_failure_count"]:
        return "repair_baseline_packet_or_candidate_before_rerun"
    if aggregate["model_weakness_count"]:
        return "draft_baseline_prompt_or_scorer_repair"
    if aggregate["scorer_false_negative_count"] and not aggregate["not_reviewed_count"]:
        return "draft_scorer_repair"
    if aggregate["not_reviewed_count"]:
        return "draft_baseline_prompt_or_scorer_repair"
    return "preserve_baseline_review_evidence"


def review_verdict(
    run_report: dict[str, Any],
    aggregate: dict[str, Any],
    input_valid: bool,
) -> str:
    if not input_valid:
        return INVALID_INPUT
    if not aggregate["all_model_calls_ok"] or run_report.get("result_verdict") == "baseline_fail":
        return REJECTS_RUN
    if aggregate["true_failure_count"]:
        return REJECTS_RUN
    if aggregate["model_weakness_count"]:
        return REQUIRES_PROMPT_REPAIR
    if aggregate["scorer_false_negative_count"] or aggregate["not_reviewed_count"]:
        return REQUIRES_SCORER_REPAIR
    return ACCEPTS_EVIDENCE


def disallowed_actions() -> list[str]:
    return [
        "apply_larql_patch",
        "train_lora_adapter",
        "mutate_model_weights",
        "write_durable_memory",
        "run_larql_lane",
        "run_lora_lane",
        "run_comparison_lane",
        "promote_candidate",
        "modify_original_run_report",
        "commit_or_push",
    ]


def build_checks(
    run_report: dict[str, Any],
    run_checks: dict[str, bool],
    audit_checks: dict[str, bool],
) -> dict[str, bool]:
    checks = {}
    checks.update(run_checks)
    checks.update(audit_checks)
    checks.update(
        {
            "selected_lane_baseline": run_report.get("selected_lane") == BASELINE_LANE,
            "promotion_held": run_report.get("promotion_verdict") == PROMOTION_VERDICT,
            "candidate_digest_verified": bool(run_report.get("candidate_digest_verified")),
            "prompt_suite_digest_verified": bool(run_report.get("prompt_suite_digest_verified")),
        }
    )
    return checks


def invalid_input_from_checks(checks: dict[str, bool]) -> bool:
    required = [
        "run_report_exists",
        "run_report_parses",
        "post_run_audit_exists",
        "selected_lane_baseline",
        "promotion_held",
        "candidate_digest_verified",
        "prompt_suite_digest_verified",
    ]
    return not all(checks.get(name, False) for name in required)


def build_review(
    run_report_path: Path,
    post_run_audit_path: Path,
    operator_summary: str,
) -> dict[str, Any]:
    run_report, run_checks, run_notes = read_json_object(run_report_path, "run_report")
    audit_text, audit_checks, audit_notes = read_text_file(post_run_audit_path, "post_run_audit")
    checks = build_checks(run_report, run_checks, audit_checks)
    invalid_input = invalid_input_from_checks(checks)
    prompt_results = run_report.get("prompt_results")
    if not isinstance(prompt_results, list):
        prompt_results = []
    adjudications = prompt_adjudications(prompt_results) if not invalid_input else []
    aggregate = aggregate_review(adjudications, run_report)
    verdict = review_verdict(run_report, aggregate, not invalid_input)
    failed_checks = [name for name, passed in checks.items() if not passed]
    notes = [
        *run_notes,
        *audit_notes,
        "Review only; original run report is not modified.",
        "Original run verdict remains preserved.",
        "Promotion remains held.",
    ]
    if failed_checks:
        notes.append("Failed checks: " + ", ".join(failed_checks))

    return {
        "report_type": REPORT_TYPE,
        "candidate_id": run_report.get("candidate_id"),
        "source_failure_id": run_report.get("source_failure_id"),
        "selected_lane": run_report.get("selected_lane"),
        "input_result_verdict": run_report.get("result_verdict"),
        "input_audit_verdict": parse_audit_verdict(audit_text),
        "review_status": REVIEW_STATUS,
        "review_verdict": verdict,
        "promotion_verdict": PROMOTION_VERDICT,
        "operator_summary": operator_summary,
        "prompt_adjudications": adjudications,
        "aggregate_review": aggregate,
        "recommended_next_step": recommended_next_step(aggregate)
        if verdict != INVALID_INPUT
        else "repair_review_inputs",
        "disallowed_actions": disallowed_actions(),
        "checks": checks,
        "notes": notes,
    }


def markdown_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items]


def render_markdown(review: dict[str, Any]) -> str:
    lines = [
        "# Affordance Baseline Run Review v0",
        "",
        f"Candidate id: `{review.get('candidate_id') or 'unknown'}`",
        f"Source failure id: `{review.get('source_failure_id') or 'unknown'}`",
        f"Selected lane: `{review.get('selected_lane') or 'unknown'}`",
        "",
        "## Verdict",
        "",
        f"- Input result verdict: `{review.get('input_result_verdict') or 'unknown'}`",
        f"- Input audit verdict: `{review.get('input_audit_verdict') or 'unknown'}`",
        f"- Review verdict: `{review['review_verdict']}`",
        f"- Promotion verdict: `{review['promotion_verdict']}`",
        f"- Recommended next step: `{review['recommended_next_step']}`",
        "",
        "## Operator Summary",
        "",
        review["operator_summary"] or "_No operator summary provided._",
        "",
        "## Aggregate Review",
        "",
    ]
    for key, value in review["aggregate_review"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(
        [
            "",
            "## Prompt Adjudications",
            "",
            "| Prompt | Input verdict | Adjudication |",
            "|---|---|---|",
        ]
    )
    for item in review["prompt_adjudications"]:
        lines.append(
            f"| `{item.get('prompt_id')}` | `{item.get('input_prompt_verdict')}` | `{item.get('adjudication')}` |"
        )
    lines.extend(
        [
            "",
            "## Checks",
            "",
            "| Check | Passed |",
            "|---|---:|",
        ]
    )
    for name, passed in review["checks"].items():
        lines.append(f"| `{name}` | `{str(passed).lower()}` |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This is review only.",
            "The original run verdict remains preserved.",
            "This review does not modify the original run report.",
            "This review is not a LARQL patch.",
            "This review is not LoRA training.",
            "This review is not model mutation.",
            "This review is not durable memory promotion.",
            "This review is not comparison lane execution.",
            "This review grants no candidate promotion.",
            "Promotion remains held.",
            "",
            "## Disallowed Actions",
            "",
            *markdown_list(review["disallowed_actions"]),
            "",
            "## Notes",
            "",
            *markdown_list(review["notes"]),
            "",
        ]
    )
    return "\n".join(lines)


def write_reports(
    run_report_path: Path,
    post_run_audit_path: Path,
    out_dir: Path,
    operator_summary: str,
) -> dict[str, Any]:
    validate_out_dir(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    review = build_review(run_report_path, post_run_audit_path, operator_summary)
    (out_dir / "baseline_run_review.json").write_text(
        json.dumps(review, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "baseline_run_review.md").write_text(
        render_markdown(review),
        encoding="utf-8",
    )
    return review


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Record model-free review/adjudication of a baseline affordance run."
    )
    parser.add_argument("--run-report", required=True, type=Path)
    parser.add_argument("--post-run-audit", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--operator-summary", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        review = write_reports(
            args.run_report,
            args.post_run_audit,
            args.out,
            args.operator_summary,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    for filename in OUTPUT_FILES:
        print(f"wrote: {args.out / filename}")
    print(f"review_verdict: {review['review_verdict']}")
    print(f"promotion_verdict: {review['promotion_verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
