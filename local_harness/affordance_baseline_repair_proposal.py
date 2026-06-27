"""Draft a model-free baseline affordance prompt/scorer repair proposal.

This helper reads a completed baseline run report and review report, then
drafts a repair proposal. It does not call a model, rerun the baseline, modify
original reports, patch runner/scorer code, apply LARQL, train LoRA, mutate
models, write durable memory, or promote candidates.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_baseline_repair_proposal.v0"
PROPOSAL_STATUS = "proposal_only"
PROMOTION_VERDICT = "hold_pending_explicit_experiment_approval"
BASELINE_LANE = "baseline_prompt_context_only"

READY = "ready_for_repair_decision"
NOT_READY = "not_ready_missing_review"
INVALID_INPUT = "invalid_input"

REPAIR_REVIEW_VERDICTS = {
    "baseline_review_requires_prompt_repair",
    "baseline_review_requires_scorer_repair",
}

OUTPUT_FILES = ("baseline_repair_proposal.json", "baseline_repair_proposal.md")


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


def adjudications_by_prompt(run_review: dict[str, Any]) -> dict[str, str]:
    items = run_review.get("prompt_adjudications")
    if not isinstance(items, list):
        return {}
    result: dict[str, str] = {}
    for item in items:
        if isinstance(item, dict):
            prompt_id = item.get("prompt_id")
            adjudication = item.get("adjudication")
            if isinstance(prompt_id, str) and isinstance(adjudication, str):
                result[prompt_id] = adjudication
    return result


def scorer_repair_catalog() -> dict[str, dict[str, Any]]:
    return {
        "baseline_direct_cuda_on_navigator": {
            "prompt_id": "baseline_direct_cuda_on_navigator",
            "repair_type": "scorer_false_negative",
            "proposal": (
                "Accept phrasing that explicitly says to avoid CUDA-only setup and mentions "
                "`no_cuda`, `CUDA-only`, `RX580`, `AMD`, or `non-NVIDIA`."
            ),
            "accepted_language_examples": [
                "avoid CUDA-only setup",
                "no_cuda",
                "CUDA-only",
                "RX580",
                "AMD",
                "non-NVIDIA",
            ],
        },
        "baseline_cross_host_boundary": {
            "prompt_id": "baseline_cross_host_boundary",
            "repair_type": "scorer_false_negative",
            "proposal": (
                "Accept boundary phrasing such as 'not generalizable to other profiles "
                "without matching evidence'."
            ),
            "accepted_language_examples": [
                "not generalizable to other profiles without matching evidence",
                "not generalize without matching evidence",
            ],
        },
        "baseline_reverify_before_action": {
            "prompt_id": "baseline_reverify_before_action",
            "repair_type": "scorer_false_negative",
            "proposal": "Accept `revalidation` as equivalent to `reverify`.",
            "accepted_language_examples": ["revalidation", "reverify"],
        },
        "baseline_no_durable_promotion": {
            "prompt_id": "baseline_no_durable_promotion",
            "repair_type": "scorer_false_negative",
            "proposal": (
                "Accept language that says the run does not apply a LARQL patch, does "
                "not train LoRA, and does not perform durable memory/write/promotion."
            ),
            "accepted_language_examples": [
                "does not apply a LARQL patch",
                "train LoRA",
                "no durable memory",
                "no durable write",
                "no promotion",
            ],
        },
    }


def scorer_false_negative_repairs(run_review: dict[str, Any], allow_scorer_relaxation: bool) -> list[dict[str, Any]]:
    if not allow_scorer_relaxation:
        return []
    labels = adjudications_by_prompt(run_review)
    catalog = scorer_repair_catalog()
    return [
        catalog[prompt_id]
        for prompt_id, label in labels.items()
        if label == "scorer_false_negative" and prompt_id in catalog
    ]


def prompt_weakness_repairs(run_review: dict[str, Any]) -> list[dict[str, Any]]:
    labels = adjudications_by_prompt(run_review)
    if labels.get("baseline_split_workflow_active_host") != "model_weakness":
        return []
    return [
        {
            "prompt_id": "baseline_split_workflow_active_host",
            "repair_type": "prompt_and_scorer_tightening",
            "proposal": (
                "Strengthen the prompt so the expected answer explicitly distinguishes "
                "local host, remote host, active execution host, and that the active "
                "host profile controls which affordance applies."
            ),
            "scorer_requirement": (
                "Require local/remote distinction plus active-host/profile control language."
            ),
            "required_concepts": [
                "local host",
                "remote host",
                "active execution host",
                "active host profile controls which affordance applies",
            ],
        }
    ]


def required_outputs_ok(run_report: dict[str, Any]) -> bool:
    outputs = run_report.get("required_outputs_written")
    if not isinstance(outputs, dict):
        return True
    return all(bool(value) for value in outputs.values())


def runner_code_repair_needed(run_report: dict[str, Any], run_review: dict[str, Any]) -> bool:
    aggregate_checks = run_report.get("aggregate_checks")
    if not isinstance(aggregate_checks, dict):
        aggregate_checks = {}
    aggregate_review = run_review.get("aggregate_review")
    if not isinstance(aggregate_review, dict):
        aggregate_review = {}
    return not (
        bool(aggregate_checks.get("all_model_calls_ok"))
        and bool(run_report.get("candidate_digest_verified"))
        and bool(run_report.get("prompt_suite_digest_verified"))
        and bool(aggregate_checks.get("no_repo_write_requested"))
        and bool(aggregate_checks.get("disallowed_actions_preserved"))
        and bool(aggregate_review.get("boundaries_preserved"))
        and required_outputs_ok(run_report)
    )


def candidate_repair_needed(run_review: dict[str, Any]) -> bool:
    aggregate_review = run_review.get("aggregate_review")
    if not isinstance(aggregate_review, dict):
        return False
    return int(aggregate_review.get("true_failure_count") or 0) > 0


def build_checks(
    run_report: dict[str, Any],
    run_review: dict[str, Any],
    run_checks: dict[str, bool],
    review_checks: dict[str, bool],
) -> dict[str, bool]:
    aggregate_review = run_review.get("aggregate_review")
    if not isinstance(aggregate_review, dict):
        aggregate_review = {}
    checks = {}
    checks.update(run_checks)
    checks.update(review_checks)
    checks.update(
        {
            "selected_lane_baseline": run_report.get("selected_lane") == BASELINE_LANE,
            "run_promotion_held": run_report.get("promotion_verdict") == PROMOTION_VERDICT,
            "review_promotion_held": run_review.get("promotion_verdict") == PROMOTION_VERDICT,
            "review_verdict_requests_repair": run_review.get("review_verdict")
            in REPAIR_REVIEW_VERDICTS,
            "true_failure_count_zero": int(aggregate_review.get("true_failure_count") or 0) == 0,
            "digests_verified": bool(run_report.get("candidate_digest_verified"))
            and bool(run_report.get("prompt_suite_digest_verified"))
            and bool(aggregate_review.get("digests_verified", True)),
            "boundaries_preserved": bool(aggregate_review.get("boundaries_preserved", True)),
        }
    )
    return checks


def invalid_input_from_checks(checks: dict[str, bool]) -> bool:
    required = [
        "run_report_exists",
        "run_report_parses",
        "run_review_exists",
        "run_review_parses",
        "selected_lane_baseline",
        "run_promotion_held",
        "review_promotion_held",
    ]
    return not all(checks.get(name, False) for name in required)


def proposal_verdict(checks: dict[str, bool]) -> str:
    if invalid_input_from_checks(checks):
        return INVALID_INPUT
    readiness_required = [
        "review_verdict_requests_repair",
        "true_failure_count_zero",
        "digests_verified",
        "boundaries_preserved",
    ]
    if all(checks.get(name, False) for name in readiness_required):
        return READY
    return NOT_READY


def recommended_repair_scope(verdict: str) -> str:
    if verdict == READY:
        return "baseline_prompt_suite_and_scorer_only"
    if verdict == INVALID_INPUT:
        return "repair_inputs_before_repair_proposal"
    return "investigate_review_or_true_failures_before_prompt_scorer_repair"


def allowed_next_step(verdict: str) -> str:
    if verdict == READY:
        return "decide_baseline_prompt_scorer_repair"
    return "repair_or_complete_baseline_repair_proposal_inputs"


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
        "modify_original_review_report",
        "apply_repair_without_decision",
        "commit_or_push",
    ]


def build_proposal(run_report_path: Path, run_review_path: Path) -> dict[str, Any]:
    run_report, run_checks, run_notes = read_json_object(run_report_path, "run_report")
    run_review, review_checks, review_notes = read_json_object(run_review_path, "run_review")
    checks = build_checks(run_report, run_review, run_checks, review_checks)
    verdict = proposal_verdict(checks)
    allow_scorer_relaxation = checks.get("true_failure_count_zero", False)
    runner_repair = runner_code_repair_needed(run_report, run_review)
    candidate_repair = candidate_repair_needed(run_review)
    failed_checks = [name for name, passed in checks.items() if not passed]
    notes = [
        *run_notes,
        *review_notes,
        "Proposal only; original run and review reports are not modified.",
        "Repair still requires a separate decision.",
        "Rerun is required after any accepted repair.",
    ]
    if failed_checks:
        notes.append("Failed checks: " + ", ".join(failed_checks))
    if not allow_scorer_relaxation:
        notes.append("True failures are present or unknown; scorer relaxation is not sufficient.")

    return {
        "report_type": REPORT_TYPE,
        "candidate_id": run_report.get("candidate_id") or run_review.get("candidate_id"),
        "source_failure_id": run_report.get("source_failure_id")
        or run_review.get("source_failure_id"),
        "selected_lane": run_report.get("selected_lane") or run_review.get("selected_lane"),
        "input_result_verdict": run_report.get("result_verdict"),
        "input_review_verdict": run_review.get("review_verdict"),
        "promotion_verdict": PROMOTION_VERDICT,
        "proposal_status": PROPOSAL_STATUS,
        "proposal_verdict": verdict,
        "recommended_repair_scope": recommended_repair_scope(verdict),
        "scorer_false_negative_repairs": scorer_false_negative_repairs(
            run_review, allow_scorer_relaxation
        ),
        "prompt_weakness_repairs": prompt_weakness_repairs(run_review),
        "runner_code_repair_needed": runner_repair,
        "candidate_repair_needed": candidate_repair,
        "rerun_required_after_repair": True,
        "allowed_next_step": allowed_next_step(verdict),
        "disallowed_actions": disallowed_actions(),
        "checks": checks,
        "notes": notes,
    }


def markdown_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items]


def render_markdown(proposal: dict[str, Any]) -> str:
    lines = [
        "# Affordance Baseline Repair Proposal v0",
        "",
        f"Candidate id: `{proposal.get('candidate_id') or 'unknown'}`",
        f"Source failure id: `{proposal.get('source_failure_id') or 'unknown'}`",
        f"Selected lane: `{proposal.get('selected_lane') or 'unknown'}`",
        "",
        "## Verdict",
        "",
        f"- Input result verdict: `{proposal.get('input_result_verdict') or 'unknown'}`",
        f"- Input review verdict: `{proposal.get('input_review_verdict') or 'unknown'}`",
        f"- Proposal verdict: `{proposal['proposal_verdict']}`",
        f"- Promotion verdict: `{proposal['promotion_verdict']}`",
        f"- Recommended repair scope: `{proposal['recommended_repair_scope']}`",
        f"- Allowed next step: `{proposal['allowed_next_step']}`",
        f"- Rerun required after repair: `{str(proposal['rerun_required_after_repair']).lower()}`",
        "",
        "## Scorer False-Negative Repairs",
        "",
    ]
    if proposal["scorer_false_negative_repairs"]:
        for repair in proposal["scorer_false_negative_repairs"]:
            lines.extend(
                [
                    f"### {repair['prompt_id']}",
                    "",
                    repair["proposal"],
                    "",
                ]
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Prompt Weakness Repairs", ""])
    if proposal["prompt_weakness_repairs"]:
        for repair in proposal["prompt_weakness_repairs"]:
            lines.extend(
                [
                    f"### {repair['prompt_id']}",
                    "",
                    repair["proposal"],
                    "",
                    f"Scorer requirement: {repair['scorer_requirement']}",
                    "",
                ]
            )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Repair Flags",
            "",
            f"- Runner code repair needed: `{str(proposal['runner_code_repair_needed']).lower()}`",
            f"- Candidate repair needed: `{str(proposal['candidate_repair_needed']).lower()}`",
            "",
            "## Checks",
            "",
            "| Check | Passed |",
            "|---|---:|",
        ]
    )
    for name, passed in proposal["checks"].items():
        lines.append(f"| `{name}` | `{str(passed).lower()}` |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This is proposal only.",
            "The original run verdict remains preserved.",
            "The original review verdict remains preserved.",
            "This proposal does not modify the original run report.",
            "This proposal does not modify the original review report.",
            "This proposal is not a LARQL patch.",
            "This proposal is not LoRA training.",
            "This proposal is not model mutation.",
            "This proposal is not durable memory promotion.",
            "This proposal is not comparison lane execution.",
            "This proposal grants no candidate promotion.",
            "Repair still requires a separate decision.",
            "Rerun is required after repair.",
            "",
            "## Disallowed Actions",
            "",
            *markdown_list(proposal["disallowed_actions"]),
            "",
            "## Notes",
            "",
            *markdown_list(proposal["notes"]),
            "",
        ]
    )
    return "\n".join(lines)


def write_reports(
    run_report_path: Path,
    run_review_path: Path,
    out_dir: Path,
) -> dict[str, Any]:
    validate_out_dir(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    proposal = build_proposal(run_report_path, run_review_path)
    (out_dir / "baseline_repair_proposal.json").write_text(
        json.dumps(proposal, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "baseline_repair_proposal.md").write_text(
        render_markdown(proposal),
        encoding="utf-8",
    )
    return proposal


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Draft a model-free baseline affordance prompt/scorer repair proposal."
    )
    parser.add_argument("--run-report", required=True, type=Path)
    parser.add_argument("--run-review", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        proposal = write_reports(args.run_report, args.run_review, args.out)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    for filename in OUTPUT_FILES:
        print(f"wrote: {args.out / filename}")
    print(f"proposal_verdict: {proposal['proposal_verdict']}")
    print(f"promotion_verdict: {proposal['promotion_verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
