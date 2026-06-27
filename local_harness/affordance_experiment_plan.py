"""Draft a bounded affordance experiment plan.

This helper turns a ready proposal and accepted decision record into a
reviewable plan artifact. It does not apply LARQL, train LoRA, mutate models,
write durable memory, execute an experiment, or promote candidates.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_experiment_plan.v0"
EXPERIMENT_STATUS = "plan_only"
PROMOTION_VERDICT = "hold_pending_explicit_experiment_approval"
EXECUTION_VERDICT = "not_approved_for_execution"

READY_PROPOSAL = "ready_for_operator_review"
ACCEPTED_DECISION = "accepted_for_plan_drafting_only"
ALLOWED_DECISION_NEXT_STEP = "draft_bounded_affordance_experiment_plan"

READY_PLAN = "ready_for_execution_approval_review"
MISSING_DECISION = "not_ready_missing_decision"
INVALID_INPUT = "invalid_input"

OUTPUT_FILES = ("experiment_plan.json", "experiment_plan.md")


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


def allowed_experiment_lanes(recommended_type: str | None) -> list[str]:
    if recommended_type == "larql_plus_lora_comparison":
        return [
            "baseline_prompt_context_only",
            "larql_affordance_patch_probe_only",
            "lora_failure_curriculum_candidate_only",
        ]
    if recommended_type == "larql_affordance_patch_probe":
        return [
            "baseline_prompt_context_only",
            "larql_affordance_patch_probe_only",
        ]
    if recommended_type == "lora_failure_curriculum_candidate":
        return [
            "baseline_prompt_context_only",
            "lora_failure_curriculum_candidate_only",
        ]
    return ["baseline_prompt_context_only"]


def baseline_artifacts() -> list[str]:
    return [
        "affordance_patch_candidate.json",
        "endpoint_probe_report",
        "repeatability_probe_report",
        "eligibility_report.json",
        "experiment_proposal.json",
        "experiment_decision.json",
    ]


def planned_artifacts(recommended_type: str | None) -> list[str]:
    artifacts = [
        "bounded_experiment_execution_approval_record",
        "pre_experiment_probe_baseline_snapshot",
        "post_experiment_probe_report",
        "post_experiment_repeatability_report",
        "experiment_closeout_report",
    ]
    if recommended_type == "larql_plus_lora_comparison":
        artifacts.extend(
            [
                "larql_lane_result_report_if_separately_approved",
                "lora_lane_result_report_if_separately_approved",
                "comparison_result_report_only_after_separate_approval",
            ]
        )
    elif recommended_type == "larql_affordance_patch_probe":
        artifacts.append("larql_lane_result_report_if_separately_approved")
    elif recommended_type == "lora_failure_curriculum_candidate":
        artifacts.append("lora_lane_result_report_if_separately_approved")
    return artifacts


def allowed_inputs() -> list[str]:
    return [
        "current affordance candidate and source digests",
        "held-promotion proposal and decision records",
        "sanitized repeatability report",
        "host profile facts already represented in the candidate",
        "operator-approved experiment execution packet if one is later created",
    ]


def disallowed_actions() -> list[str]:
    return [
        "apply_larql_patch",
        "train_lora_adapter",
        "mutate_model_weights",
        "write_durable_memory",
        "execute_experiment",
        "promote_candidate",
        "treat_plan_as_execution_approval",
        "hide_or_drop_source_provenance",
    ]


def pre_experiment_checks() -> list[str]:
    return [
        "Confirm proposal and decision records are still current.",
        "Confirm promotion and execution remain held.",
        "Re-run or inspect baseline probe evidence before any separately approved execution.",
        "Confirm private endpoint details and local paths are not committed.",
    ]


def execution_stop_rules() -> list[str]:
    return [
        "Stop if explicit execution approval is absent.",
        "Stop if source provenance is missing or stale.",
        "Stop if the candidate starts generalizing host-specific affordances to unsupported hosts.",
        "Stop if any lane requires hidden evidence or unreviewed local output.",
        "Stop if any step would mutate model weights, durable memory, or LARQL state without separate approval.",
    ]


def success_criteria() -> list[str]:
    return [
        "Any later approved lane preserves or improves the baseline prompt-context behavior.",
        "Post-experiment re-audition passes the same probe suite and repeatability checks.",
        "No unknown-host, different-host, split-workflow, or reverify regression appears.",
        "All experiment artifacts retain provenance and held-promotion language.",
    ]


def failure_criteria() -> list[str]:
    return [
        "Any regression, overgeneralization, missing provenance, hidden evidence, or automatic promotion rejects the experiment.",
        "Any execution without separate explicit approval rejects the experiment.",
        "Any result that requires weakening host-profile authority rejects the experiment.",
    ]


def post_experiment_required_audits() -> list[str]:
    return [
        "Run the same affordance probe suite after any separately approved experiment.",
        "Run repeatability checks comparable to the clean baseline.",
        "Compare baseline prompt-context behavior with any LARQL, LoRA, or later comparison lane.",
        "Record whether context burden changed without weakening boundaries.",
        "Preserve a closeout report before any future acceptance discussion.",
    ]


def required_execution_approval() -> dict[str, Any]:
    return {
        "required": True,
        "status": "not_granted",
        "allowed_by_this_plan": False,
        "required_record": "explicit_bounded_affordance_experiment_execution_approval",
    }


def build_checks(
    proposal: dict[str, Any],
    decision: dict[str, Any],
    base_checks: dict[str, bool],
) -> dict[str, bool]:
    checks = dict(base_checks)
    checks.update(
        {
            "proposal_verdict_ready": proposal.get("proposal_verdict") == READY_PROPOSAL,
            "decision_verdict_accepted": decision.get("decision_verdict") == ACCEPTED_DECISION,
            "decision_allowed_next_step_ok": (
                decision.get("allowed_next_step") == ALLOWED_DECISION_NEXT_STEP
            ),
            "recommended_experiment_type_exists": bool(
                proposal.get("recommended_experiment_type")
            ),
            "proposal_promotion_held": proposal.get("promotion_verdict") == PROMOTION_VERDICT,
            "decision_promotion_held": decision.get("promotion_verdict") == PROMOTION_VERDICT,
        }
    )
    return checks


def plan_verdict(checks: dict[str, bool]) -> str:
    if (
        not checks.get("proposal_exists", False)
        or not checks.get("proposal_parses", False)
        or not checks.get("decision_exists", False)
        or not checks.get("decision_parses", False)
    ):
        return INVALID_INPUT
    if all(checks.values()):
        return READY_PLAN
    return MISSING_DECISION


def build_plan(proposal_path: Path, decision_path: Path) -> dict[str, Any]:
    proposal, proposal_checks, proposal_notes = read_json_object(proposal_path, "proposal")
    decision, decision_checks, decision_notes = read_json_object(decision_path, "decision")
    base_checks = {}
    base_checks.update(proposal_checks)
    base_checks.update(decision_checks)
    checks = build_checks(proposal, decision, base_checks)
    verdict = plan_verdict(checks)
    recommended_type = proposal.get("recommended_experiment_type")
    failed_checks = [name for name, passed in checks.items() if not passed]
    notes = [
        *proposal_notes,
        *decision_notes,
        "The baseline candidate remains the safe prompt-context version.",
        "No lane is executed by this plan.",
        "LARQL, LoRA, and any later comparison lane require separate explicit execution approval.",
        "Post-experiment re-audition is required before any result can be accepted.",
    ]
    if recommended_type == "larql_plus_lora_comparison":
        notes.append(
            "The comparison lane is intentionally later-only and requires separate approval after bounded LARQL and LoRA lane planning."
        )
    if failed_checks:
        notes.append("Failed checks: " + ", ".join(failed_checks))

    return {
        "report_type": "affordance_experiment_plan.v0",
        "candidate_id": proposal.get("candidate_id"),
        "source_failure_id": proposal.get("source_failure_id"),
        "repair_lane": proposal.get("repair_lane"),
        "recommended_experiment_type": recommended_type,
        "proposal_verdict": proposal.get("proposal_verdict"),
        "decision_verdict": decision.get("decision_verdict"),
        "experiment_status": EXPERIMENT_STATUS,
        "plan_verdict": verdict,
        "promotion_verdict": PROMOTION_VERDICT,
        "execution_verdict": EXECUTION_VERDICT,
        "allowed_experiment_lanes": allowed_experiment_lanes(recommended_type),
        "selected_plan_lane": recommended_type or "insufficient_evidence",
        "baseline_artifacts": baseline_artifacts(),
        "planned_artifacts": planned_artifacts(recommended_type),
        "allowed_inputs": allowed_inputs(),
        "disallowed_actions": disallowed_actions(),
        "pre_experiment_checks": pre_experiment_checks(),
        "execution_stop_rules": execution_stop_rules(),
        "success_criteria": success_criteria(),
        "failure_criteria": failure_criteria(),
        "post_experiment_required_audits": post_experiment_required_audits(),
        "required_execution_approval": required_execution_approval(),
        "checks": checks,
        "notes": notes,
    }


def markdown_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items]


def render_markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# Affordance Experiment Plan v0",
        "",
        f"Candidate id: `{plan.get('candidate_id') or 'unknown'}`",
        f"Source failure id: `{plan.get('source_failure_id') or 'unknown'}`",
        f"Repair lane: `{plan.get('repair_lane') or 'unknown'}`",
        f"Recommended experiment type: `{plan.get('recommended_experiment_type') or 'unknown'}`",
        f"Selected plan lane: `{plan['selected_plan_lane']}`",
        "",
        "## Verdict",
        "",
        f"- Plan verdict: `{plan['plan_verdict']}`",
        f"- Execution verdict: `{plan['execution_verdict']}`",
        f"- Promotion verdict: `{plan['promotion_verdict']}`",
        f"- Experiment status: `{plan['experiment_status']}`",
        "",
        "## Checks",
        "",
        "| Check | Passed |",
        "|---|---:|",
    ]
    for name, passed in plan["checks"].items():
        lines.append(f"| `{name}` | `{str(passed).lower()}` |")

    lines.extend(
        [
            "",
            "## Planned Lanes",
            "",
            *markdown_list(plan["allowed_experiment_lanes"]),
            "",
            "The baseline candidate remains the safe prompt-context version.",
            "No lane is executed by this plan.",
            "LARQL lane, LoRA lane, and any later comparison lane require separate explicit execution approval before running.",
            "",
            "## Baseline Artifacts",
            "",
            *markdown_list(plan["baseline_artifacts"]),
            "",
            "## Planned Artifacts",
            "",
            *markdown_list(plan["planned_artifacts"]),
            "",
            "## Allowed Inputs",
            "",
            *markdown_list(plan["allowed_inputs"]),
            "",
            "## Pre-Experiment Checks",
            "",
            *markdown_list(plan["pre_experiment_checks"]),
            "",
            "## Execution Stop Rules",
            "",
            *markdown_list(plan["execution_stop_rules"]),
            "",
            "## Success Criteria",
            "",
            *markdown_list(plan["success_criteria"]),
            "",
            "## Failure Criteria",
            "",
            *markdown_list(plan["failure_criteria"]),
            "",
            "## Post-Experiment Required Audits",
            "",
            *markdown_list(plan["post_experiment_required_audits"]),
            "",
            "Post-experiment re-audition is required before any result can be accepted.",
            "",
            "## Required Execution Approval",
            "",
            f"- Required: `{str(plan['required_execution_approval']['required']).lower()}`",
            f"- Status: `{plan['required_execution_approval']['status']}`",
            f"- Allowed by this plan: `{str(plan['required_execution_approval']['allowed_by_this_plan']).lower()}`",
            f"- Required record: `{plan['required_execution_approval']['required_record']}`",
            "",
            "## Boundary",
            "",
            "This plan is not a LARQL patch.",
            "This plan is not LoRA training.",
            "This plan is not model mutation.",
            "This plan is not durable memory promotion.",
            "This plan is not experiment execution.",
            "This plan grants no candidate promotion.",
            "It requires separate execution approval before anything runs.",
            "",
            "## Disallowed Actions",
            "",
            *markdown_list(plan["disallowed_actions"]),
            "",
            "## Notes",
            "",
            *markdown_list(plan["notes"]),
            "",
        ]
    )
    return "\n".join(lines)


def write_reports(proposal_path: Path, decision_path: Path, out_dir: Path) -> dict[str, Any]:
    validate_out_dir(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    plan = build_plan(proposal_path, decision_path)
    (out_dir / "experiment_plan.json").write_text(
        json.dumps(plan, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "experiment_plan.md").write_text(render_markdown(plan), encoding="utf-8")
    return plan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Draft a model-free bounded affordance experiment plan."
    )
    parser.add_argument("--proposal", required=True, type=Path)
    parser.add_argument("--decision", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        plan = write_reports(args.proposal, args.decision, args.out)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    for filename in OUTPUT_FILES:
        print(f"wrote: {args.out / filename}")
    print(f"plan_verdict: {plan['plan_verdict']}")
    print(f"execution_verdict: {plan['execution_verdict']}")
    print(f"promotion_verdict: {plan['promotion_verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
