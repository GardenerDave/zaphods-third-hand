"""Record a model-free decision about a baseline repair proposal.

This helper records whether a baseline prompt/scorer repair proposal may move
to repair packet drafting. It does not call a model, rerun the baseline,
modify original reports, patch runner/scorer code, apply LARQL, train LoRA,
mutate models, write durable memory, or promote candidates.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_baseline_repair_decision.v0"
DECISION_STATUS = "decision_only"
PROMOTION_VERDICT = "hold_pending_explicit_experiment_approval"
BASELINE_LANE = "baseline_prompt_context_only"
READY_PROPOSAL = "ready_for_repair_decision"
REPAIR_SCOPE = "baseline_prompt_suite_and_scorer_only"

ACCEPT = "accept_prompt_scorer_repair_for_packet_drafting"
REJECT = "reject_repair_proposal"
HOLD = "hold_for_more_review"
ALLOWED_DECISIONS = (ACCEPT, REJECT, HOLD)

ACCEPTED = "accepted_for_repair_packet_drafting_only"
REJECTED = "rejected_repair_proposal"
HELD = "held_for_more_review"
INVALID_INPUT = "invalid_input"

OUTPUT_FILES = ("baseline_repair_decision.json", "baseline_repair_decision.md")


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


def build_checks(proposal: dict[str, Any], base_checks: dict[str, bool]) -> dict[str, bool]:
    checks = dict(base_checks)
    checks.update(
        {
            "selected_lane_baseline": proposal.get("selected_lane") == BASELINE_LANE,
            "proposal_verdict_ready": proposal.get("proposal_verdict") == READY_PROPOSAL,
            "recommended_repair_scope_ok": (
                proposal.get("recommended_repair_scope") == REPAIR_SCOPE
            ),
            "promotion_held": proposal.get("promotion_verdict") == PROMOTION_VERDICT,
            "runner_code_repair_not_needed": proposal.get("runner_code_repair_needed") is False,
            "candidate_repair_not_needed": proposal.get("candidate_repair_needed") is False,
            "rerun_required_after_repair": proposal.get("rerun_required_after_repair") is True,
        }
    )
    return checks


def input_is_unusable(checks: dict[str, bool]) -> bool:
    required = [
        "repair_proposal_exists",
        "repair_proposal_parses",
        "selected_lane_baseline",
        "promotion_held",
    ]
    return not all(checks.get(name, False) for name in required)


def accept_checks_pass(checks: dict[str, bool]) -> bool:
    required = [
        "proposal_verdict_ready",
        "recommended_repair_scope_ok",
        "runner_code_repair_not_needed",
        "candidate_repair_not_needed",
        "rerun_required_after_repair",
    ]
    return all(checks.get(name, False) for name in required)


def decision_verdict(operator_decision: str, checks: dict[str, bool]) -> str:
    if input_is_unusable(checks):
        return INVALID_INPUT
    if operator_decision == HOLD:
        return HELD
    if operator_decision == REJECT:
        return REJECTED
    if operator_decision == ACCEPT:
        if accept_checks_pass(checks):
            return ACCEPTED
        return INVALID_INPUT
    return INVALID_INPUT


def accepted_repair_scope(verdict: str) -> str | None:
    if verdict == ACCEPTED:
        return REPAIR_SCOPE
    return None


def allowed_next_step(verdict: str) -> str:
    if verdict == ACCEPTED:
        return "draft_baseline_prompt_scorer_repair_packet"
    if verdict == REJECTED:
        return "preserve_rejection_or_draft_new_proposal"
    if verdict == HELD:
        return "collect_more_review_before_repair_decision"
    return "repair_or_replace_baseline_repair_decision_inputs"


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
        "modify_original_proposal_report",
        "apply_repair_without_packet",
        "apply_repair_without_decision",
        "run_repaired_baseline_without_packet",
        "commit_or_push",
    ]


def build_decision(
    proposal_path: Path,
    operator_decision: str,
    operator_rationale: str,
) -> dict[str, Any]:
    proposal, proposal_checks, proposal_notes = read_json_object(
        proposal_path,
        "repair_proposal",
    )
    checks = build_checks(proposal, proposal_checks)
    verdict = decision_verdict(operator_decision, checks)
    failed_checks = [name for name, passed in checks.items() if not passed]
    notes = [
        *proposal_notes,
        "Decision only; no repair is applied.",
        "Original run, review, and proposal verdicts remain preserved.",
        "Repair packet is still required before any code, prompt, or scorer change.",
        "Rerun is required after any accepted repair.",
    ]
    if failed_checks:
        notes.append("Failed checks: " + ", ".join(failed_checks))

    return {
        "report_type": REPORT_TYPE,
        "candidate_id": proposal.get("candidate_id"),
        "source_failure_id": proposal.get("source_failure_id"),
        "selected_lane": proposal.get("selected_lane"),
        "input_proposal_verdict": proposal.get("proposal_verdict"),
        "input_recommended_repair_scope": proposal.get("recommended_repair_scope"),
        "decision_status": DECISION_STATUS,
        "operator_decision": operator_decision,
        "decision_verdict": verdict,
        "promotion_verdict": PROMOTION_VERDICT,
        "operator_rationale": operator_rationale,
        "accepted_repair_scope": accepted_repair_scope(verdict),
        "allowed_next_step": allowed_next_step(verdict),
        "rerun_required_after_repair": bool(proposal.get("rerun_required_after_repair")),
        "runner_code_repair_authorized": False,
        "candidate_repair_authorized": False,
        "disallowed_actions": disallowed_actions(),
        "checks": checks,
        "notes": notes,
    }


def markdown_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items]


def render_markdown(decision: dict[str, Any]) -> str:
    lines = [
        "# Affordance Baseline Repair Decision v0",
        "",
        f"Candidate id: `{decision.get('candidate_id') or 'unknown'}`",
        f"Source failure id: `{decision.get('source_failure_id') or 'unknown'}`",
        f"Selected lane: `{decision.get('selected_lane') or 'unknown'}`",
        "",
        "## Verdict",
        "",
        f"- Input proposal verdict: `{decision.get('input_proposal_verdict') or 'unknown'}`",
        f"- Input recommended repair scope: `{decision.get('input_recommended_repair_scope') or 'unknown'}`",
        f"- Operator decision: `{decision['operator_decision']}`",
        f"- Decision verdict: `{decision['decision_verdict']}`",
        f"- Promotion verdict: `{decision['promotion_verdict']}`",
        f"- Accepted repair scope: `{decision.get('accepted_repair_scope') or 'none'}`",
        f"- Allowed next step: `{decision['allowed_next_step']}`",
        f"- Rerun required after repair: `{str(decision['rerun_required_after_repair']).lower()}`",
        "",
        "## Operator Rationale",
        "",
        decision["operator_rationale"] or "_No rationale provided._",
        "",
        "## Authorization Flags",
        "",
        f"- Runner code repair authorized: `{str(decision['runner_code_repair_authorized']).lower()}`",
        f"- Candidate repair authorized: `{str(decision['candidate_repair_authorized']).lower()}`",
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
            "This is decision only.",
            "The original run verdict remains preserved.",
            "The original review verdict remains preserved.",
            "The original proposal verdict remains preserved.",
            "No repair is applied by this record.",
            "This decision is not a LARQL patch.",
            "This decision is not LoRA training.",
            "This decision is not model mutation.",
            "This decision is not durable memory promotion.",
            "This decision is not comparison lane execution.",
            "This decision grants no candidate promotion.",
            "Repair packet is still required before any code, prompt, or scorer change.",
            "Rerun is required after any accepted repair.",
            "",
            "## Disallowed Actions",
            "",
            *markdown_list(decision["disallowed_actions"]),
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
    operator_rationale: str,
    out_dir: Path,
) -> dict[str, Any]:
    validate_out_dir(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    decision = build_decision(proposal_path, operator_decision, operator_rationale)
    (out_dir / "baseline_repair_decision.json").write_text(
        json.dumps(decision, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "baseline_repair_decision.md").write_text(
        render_markdown(decision),
        encoding="utf-8",
    )
    return decision


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Record a model-free decision about a baseline prompt/scorer repair proposal."
    )
    parser.add_argument("--repair-proposal", required=True, type=Path)
    parser.add_argument("--decision", required=True, choices=ALLOWED_DECISIONS)
    parser.add_argument("--operator-rationale", required=True)
    parser.add_argument("--out", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        decision = write_reports(
            args.repair_proposal,
            args.decision,
            args.operator_rationale,
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
