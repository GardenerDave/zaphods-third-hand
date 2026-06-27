"""Record bounded execution approval for one affordance experiment lane.

This helper records approval for a bounded lane only. In v0, only the
baseline prompt-context control lane may be approved. It does not apply
LARQL, train LoRA, mutate models, write durable memory, execute an experiment,
or promote candidates.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_experiment_execution_approval.v0"
EXPERIMENT_STATUS = "execution_approval_only"
PROMOTION_VERDICT = "hold_pending_explicit_experiment_approval"
NOT_APPROVED_FOR_EXECUTION = "not_approved_for_execution"
BASELINE_EXECUTION_VERDICT = "approved_for_baseline_prompt_context_execution_only"

READY_PLAN = "ready_for_execution_approval_review"
APPROVED_DECISION = "approved_for_bounded_lane_execution"
HELD_DECISION = "held_for_revision"
REJECTED_DECISION = "rejected"
SUPPORTED_APPROVAL_DECISIONS = (APPROVED_DECISION, HELD_DECISION, REJECTED_DECISION)

BASELINE_LANE = "baseline_prompt_context_only"
LARQL_LANE = "larql_affordance_patch_probe_only"
LORA_LANE = "lora_failure_curriculum_candidate_only"
SUPPORTED_LANES = (BASELINE_LANE, LARQL_LANE, LORA_LANE)

APPROVED_BASELINE = "approved_for_baseline_lane_only"
UNSUPPORTED_LANE = "unsupported_lane_requires_separate_approval"
INVALID_INPUT = "invalid_input"

OUTPUT_FILES = ("execution_approval.json", "execution_approval.md")


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


def build_checks(plan: dict[str, Any], lane: str, base_checks: dict[str, bool]) -> dict[str, bool]:
    allowed_lanes = plan.get("allowed_experiment_lanes", [])
    if not isinstance(allowed_lanes, list):
        allowed_lanes = []
    checks = dict(base_checks)
    checks.update(
        {
            "plan_verdict_ready": plan.get("plan_verdict") == READY_PLAN,
            "plan_execution_not_approved": (
                plan.get("execution_verdict") == NOT_APPROVED_FOR_EXECUTION
            ),
            "plan_promotion_held": plan.get("promotion_verdict") == PROMOTION_VERDICT,
            "lane_supported": lane in SUPPORTED_LANES,
            "lane_allowed_by_plan": lane in allowed_lanes,
            "lane_is_baseline_prompt_context": lane == BASELINE_LANE,
        }
    )
    return checks


def approval_verdict(approval_decision: str, lane: str, checks: dict[str, bool]) -> str:
    if not checks.get("plan_exists", False) or not checks.get("plan_parses", False):
        return INVALID_INPUT
    if not checks.get("lane_supported", False) or not checks.get("lane_allowed_by_plan", False):
        return INVALID_INPUT
    if lane in {LARQL_LANE, LORA_LANE}:
        return UNSUPPORTED_LANE
    if approval_decision == HELD_DECISION:
        return HELD_DECISION
    if approval_decision == REJECTED_DECISION:
        return REJECTED_DECISION
    if approval_decision == APPROVED_DECISION:
        required = (
            checks.get("plan_verdict_ready", False)
            and checks.get("plan_execution_not_approved", False)
            and checks.get("plan_promotion_held", False)
            and checks.get("lane_is_baseline_prompt_context", False)
        )
        if required:
            return APPROVED_BASELINE
        return INVALID_INPUT
    return INVALID_INPUT


def execution_verdict(verdict: str) -> str:
    if verdict == APPROVED_BASELINE:
        return BASELINE_EXECUTION_VERDICT
    return NOT_APPROVED_FOR_EXECUTION


def allowed_next_step(verdict: str) -> str:
    if verdict == APPROVED_BASELINE:
        return "draft_baseline_prompt_context_execution_packet"
    if verdict == HELD_DECISION:
        return "revise_execution_approval_request"
    if verdict == REJECTED_DECISION:
        return "no_lane_execution_action"
    if verdict == UNSUPPORTED_LANE:
        return "draft_separate_lane_specific_approval_support"
    return "repair_or_replace_execution_approval_inputs"


def allowed_actions(verdict: str) -> list[str]:
    if verdict != APPROVED_BASELINE:
        return []
    return [
        "use_existing_candidate_in_prompt_context",
        "run_bounded_baseline_probe_prompts",
        "write_baseline_lane_result_report",
        "write_post_run_audit_report",
    ]


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
        "hide_or_drop_source_provenance",
    ]


def required_runner_constraints() -> list[str]:
    return [
        "no mutation",
        "no network dependency beyond already configured local endpoint",
        "fixed prompt suite or explicitly recorded prompt suite digest",
        "source candidate digest preserved",
        "write all outputs to .work/",
        "produce Markdown and JSON result reports",
        "fail closed on missing provenance or unexpected lane",
    ]


def required_pre_run_artifacts() -> list[str]:
    return [
        "execution_approval.json",
        "experiment_plan.json",
        "affordance_patch_candidate.json with source digests",
        "fixed prompt suite or prompt suite digest",
    ]


def required_post_run_artifacts() -> list[str]:
    return [
        "baseline_lane_result_report.json",
        "baseline_lane_result_report.md",
        "post_run_audit_report.md",
    ]


def build_execution_approval(
    plan_path: Path,
    lane: str,
    approval_decision: str,
    operator_note: str,
) -> dict[str, Any]:
    plan, plan_checks, plan_notes = read_json_object(plan_path, "plan")
    checks = build_checks(plan, lane, plan_checks)
    verdict = approval_verdict(approval_decision, lane, checks)
    exec_verdict = execution_verdict(verdict)
    failed_checks = [name for name, passed in checks.items() if not passed]
    notes = [
        *plan_notes,
        "This records approval status for one bounded lane only.",
        "Baseline lane approval does not authorize LARQL, LoRA, comparison, durable memory, model mutation, or candidate promotion.",
    ]
    if lane in {LARQL_LANE, LORA_LANE}:
        notes.append("The selected lane requires separate lane-specific approval support in a later version.")
    if failed_checks:
        notes.append("Failed checks: " + ", ".join(failed_checks))

    return {
        "report_type": REPORT_TYPE,
        "candidate_id": plan.get("candidate_id"),
        "source_failure_id": plan.get("source_failure_id"),
        "repair_lane": plan.get("repair_lane"),
        "recommended_experiment_type": plan.get("recommended_experiment_type"),
        "selected_lane": lane,
        "plan_verdict": plan.get("plan_verdict"),
        "approval_decision": approval_decision,
        "approval_verdict": verdict,
        "experiment_status": EXPERIMENT_STATUS,
        "execution_verdict": exec_verdict,
        "promotion_verdict": PROMOTION_VERDICT,
        "allowed_next_step": allowed_next_step(verdict),
        "allowed_actions": allowed_actions(verdict),
        "disallowed_actions": disallowed_actions(),
        "required_runner_constraints": required_runner_constraints(),
        "required_pre_run_artifacts": required_pre_run_artifacts(),
        "required_post_run_artifacts": required_post_run_artifacts(),
        "checks": checks,
        "notes": notes,
        "operator_note": operator_note,
    }


def markdown_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items]


def render_markdown(approval: dict[str, Any]) -> str:
    lines = [
        "# Affordance Experiment Execution Approval v0",
        "",
        f"Candidate id: `{approval.get('candidate_id') or 'unknown'}`",
        f"Source failure id: `{approval.get('source_failure_id') or 'unknown'}`",
        f"Repair lane: `{approval.get('repair_lane') or 'unknown'}`",
        f"Recommended experiment type: `{approval.get('recommended_experiment_type') or 'unknown'}`",
        f"Selected lane: `{approval['selected_lane']}`",
        "",
        "## Verdict",
        "",
        f"- Approval decision: `{approval['approval_decision']}`",
        f"- Approval verdict: `{approval['approval_verdict']}`",
        f"- Execution verdict: `{approval['execution_verdict']}`",
        f"- Promotion verdict: `{approval['promotion_verdict']}`",
        f"- Experiment status: `{approval['experiment_status']}`",
        f"- Allowed next step: `{approval['allowed_next_step']}`",
        "",
        "## Operator Note",
        "",
        approval["operator_note"] or "_No operator note provided._",
        "",
        "## Checks",
        "",
        "| Check | Passed |",
        "|---|---:|",
    ]
    for name, passed in approval["checks"].items():
        lines.append(f"| `{name}` | `{str(passed).lower()}` |")

    lines.extend(
        [
            "",
            "## Allowed Actions",
            "",
            *markdown_list(approval["allowed_actions"] or ["none"]),
            "",
            "## Disallowed Actions",
            "",
            *markdown_list(approval["disallowed_actions"]),
            "",
            "## Required Runner Constraints",
            "",
            *markdown_list(approval["required_runner_constraints"]),
            "",
            "## Required Pre-Run Artifacts",
            "",
            *markdown_list(approval["required_pre_run_artifacts"]),
            "",
            "## Required Post-Run Artifacts",
            "",
            *markdown_list(approval["required_post_run_artifacts"]),
            "",
            "## Boundary",
            "",
            "This approval record is not a LARQL patch.",
            "This approval record is not LoRA training.",
            "This approval record is not model mutation.",
            "This approval record is not durable memory promotion.",
            "This approval record is not comparison execution.",
            "This approval record grants no candidate promotion.",
            "For v0, approval can cover the baseline lane only.",
            "",
            "## Notes",
            "",
            *markdown_list(approval["notes"]),
            "",
        ]
    )
    return "\n".join(lines)


def write_reports(
    plan_path: Path,
    lane: str,
    approval_decision: str,
    operator_note: str,
    out_dir: Path,
) -> dict[str, Any]:
    validate_out_dir(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    approval = build_execution_approval(plan_path, lane, approval_decision, operator_note)
    (out_dir / "execution_approval.json").write_text(
        json.dumps(approval, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "execution_approval.md").write_text(
        render_markdown(approval),
        encoding="utf-8",
    )
    return approval


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Record model-free execution approval for one affordance experiment lane."
    )
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--lane", required=True, choices=SUPPORTED_LANES)
    parser.add_argument("--approval-decision", required=True, choices=SUPPORTED_APPROVAL_DECISIONS)
    parser.add_argument("--operator-note", required=True)
    parser.add_argument("--out", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        approval = write_reports(
            args.plan,
            args.lane,
            args.approval_decision,
            args.operator_note,
            args.out,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    for filename in OUTPUT_FILES:
        print(f"wrote: {args.out / filename}")
    print(f"approval_verdict: {approval['approval_verdict']}")
    print(f"execution_verdict: {approval['execution_verdict']}")
    print(f"promotion_verdict: {approval['promotion_verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
