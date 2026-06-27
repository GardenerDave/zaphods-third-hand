"""Record a model-free decision about an affordance experiment proposal.

This helper records an operator decision about a proposal artifact. It does
not apply LARQL, train LoRA, mutate models, write durable memory, execute an
experiment, or promote candidates.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_experiment_decision.v0"
EXPERIMENT_STATUS = "decision_only"
PROMOTION_VERDICT = "hold_pending_explicit_experiment_approval"
READY_PROPOSAL = "ready_for_operator_review"

APPROVED_TO_DRAFT = "approved_to_draft_experiment_plan"
HELD = "held_for_revision"
REJECTED = "rejected"
SUPPORTED_DECISIONS = (APPROVED_TO_DRAFT, HELD, REJECTED)

ACCEPTED_FOR_PLAN = "accepted_for_plan_drafting_only"
INVALID_INPUT = "invalid_input"

OUTPUT_FILES = ("experiment_decision.json", "experiment_decision.md")


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


def decision_verdict(operator_decision: str, proposal: dict[str, Any], checks: dict[str, bool]) -> str:
    if not checks.get("proposal_exists", False) or not checks.get("proposal_parses", False):
        return INVALID_INPUT

    if operator_decision == APPROVED_TO_DRAFT:
        if proposal.get("proposal_verdict") == READY_PROPOSAL:
            return ACCEPTED_FOR_PLAN
        return INVALID_INPUT
    if operator_decision == HELD:
        return HELD
    if operator_decision == REJECTED:
        return REJECTED
    return INVALID_INPUT


def allowed_next_step(verdict: str) -> str:
    if verdict == ACCEPTED_FOR_PLAN:
        return "draft_bounded_affordance_experiment_plan"
    if verdict == HELD:
        return "revise_experiment_proposal_before_plan_drafting"
    if verdict == REJECTED:
        return "no_experiment_action"
    return "repair_or_replace_proposal_decision_inputs"


def disallowed_actions() -> list[str]:
    return [
        "apply_larql_patch",
        "train_lora_adapter",
        "mutate_model_weights",
        "write_durable_memory",
        "execute_experiment",
        "promote_candidate",
        "move_lifecycle_state_without_separate_approval",
    ]


def required_followup_artifacts(verdict: str) -> list[str]:
    if verdict == ACCEPTED_FOR_PLAN:
        return [
            "bounded_affordance_experiment_plan",
            "explicit_experiment_execution_approval_record_before_any_execution",
            "post_experiment_reaudition_report_if_execution_is_later_approved",
        ]
    if verdict == HELD:
        return [
            "revised_experiment_proposal_or_operator_revision_notes",
        ]
    if verdict == REJECTED:
        return [
            "rejection_rationale_preserved_with_candidate_evidence",
        ]
    return [
        "valid_experiment_proposal_json",
        "new_decision_record_after_input_repair",
    ]


def build_checks(proposal: dict[str, Any], base_checks: dict[str, bool]) -> dict[str, bool]:
    checks = dict(base_checks)
    checks.update(
        {
            "proposal_verdict_ready": proposal.get("proposal_verdict") == READY_PROPOSAL,
            "proposal_promotion_held": proposal.get("promotion_verdict") == PROMOTION_VERDICT,
            "proposal_has_recommended_experiment_type": bool(
                proposal.get("recommended_experiment_type")
            ),
        }
    )
    return checks


def build_decision(
    proposal_path: Path,
    operator_decision: str,
    operator_note: str,
) -> dict[str, Any]:
    proposal, proposal_checks, proposal_notes = read_json_object(proposal_path, "proposal")
    checks = build_checks(proposal, proposal_checks)
    verdict = decision_verdict(operator_decision, proposal, checks)
    notes = [
        *proposal_notes,
        "This records an operator decision about proposal handling only.",
        "Approval to draft a plan is not approval to execute the experiment.",
        "Execution still requires a separate explicit approval.",
    ]
    failed_checks = [name for name, passed in checks.items() if not passed]
    if failed_checks:
        notes.append("Failed checks: " + ", ".join(failed_checks))

    return {
        "report_type": REPORT_TYPE,
        "candidate_id": proposal.get("candidate_id"),
        "source_failure_id": proposal.get("source_failure_id"),
        "repair_lane": proposal.get("repair_lane"),
        "recommended_experiment_type": proposal.get("recommended_experiment_type"),
        "proposal_verdict": proposal.get("proposal_verdict"),
        "experiment_status": EXPERIMENT_STATUS,
        "operator_decision": operator_decision,
        "operator_note": operator_note,
        "decision_verdict": verdict,
        "promotion_verdict": PROMOTION_VERDICT,
        "allowed_next_step": allowed_next_step(verdict),
        "disallowed_actions": disallowed_actions(),
        "required_followup_artifacts": required_followup_artifacts(verdict),
        "checks": checks,
        "notes": notes,
    }


def markdown_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items]


def render_markdown(decision: dict[str, Any]) -> str:
    lines = [
        "# Affordance Experiment Decision v0",
        "",
        f"Candidate id: `{decision.get('candidate_id') or 'unknown'}`",
        f"Source failure id: `{decision.get('source_failure_id') or 'unknown'}`",
        f"Repair lane: `{decision.get('repair_lane') or 'unknown'}`",
        f"Recommended experiment type: `{decision.get('recommended_experiment_type') or 'unknown'}`",
        "",
        "## Decision",
        "",
        f"- Operator decision: `{decision['operator_decision']}`",
        f"- Decision verdict: `{decision['decision_verdict']}`",
        f"- Proposal verdict: `{decision.get('proposal_verdict') or 'unknown'}`",
        f"- Promotion verdict: `{decision['promotion_verdict']}`",
        f"- Experiment status: `{decision['experiment_status']}`",
        f"- Allowed next step: `{decision['allowed_next_step']}`",
        "",
        "## Operator Note",
        "",
        decision["operator_note"] or "_No operator note provided._",
        "",
        "## Checks",
        "",
        "| Check | Passed |",
        "|---|---:|",
    ]
    for name, passed in decision["checks"].items():
        lines.append(f"| `{name}` | `{str(passed).lower()}` |")

    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This decision record is not a LARQL patch.",
            "This decision record is not LoRA training.",
            "This decision record is not model mutation.",
            "This decision record is not durable memory promotion.",
            "This decision record is not experiment execution.",
            "This decision record grants no candidate promotion.",
            "Execution still requires a separate explicit approval.",
            "",
            "Approval to draft a plan is not approval to execute the experiment.",
            "",
            "## Disallowed Actions",
            "",
            *markdown_list(decision["disallowed_actions"]),
            "",
            "## Required Follow-Up Artifacts",
            "",
            *markdown_list(decision["required_followup_artifacts"]),
            "",
            "## Notes",
            "",
            *markdown_list(decision["notes"]),
            "",
        ]
    )
    return "\n".join(lines)


def write_reports(
    proposal_path: Path,
    operator_decision: str,
    operator_note: str,
    out_dir: Path,
) -> dict[str, Any]:
    validate_out_dir(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    decision = build_decision(proposal_path, operator_decision, operator_note)
    (out_dir / "experiment_decision.json").write_text(
        json.dumps(decision, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "experiment_decision.md").write_text(
        render_markdown(decision),
        encoding="utf-8",
    )
    return decision


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Record a model-free decision about an affordance experiment proposal."
    )
    parser.add_argument("--proposal", required=True, type=Path)
    parser.add_argument("--decision", required=True, choices=SUPPORTED_DECISIONS)
    parser.add_argument("--operator-note", required=True)
    parser.add_argument("--out", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        decision = write_reports(
            args.proposal,
            args.decision,
            args.operator_note,
            args.out,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    for filename in OUTPUT_FILES:
        print(f"wrote: {args.out / filename}")
    print(f"decision_verdict: {decision['decision_verdict']}")
    print(f"promotion_verdict: {decision['promotion_verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
