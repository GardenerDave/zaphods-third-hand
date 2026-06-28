"""Generate a model-free baseline affordance prompt/scorer repair packet.

This helper reads a baseline repair proposal and repair decision, then writes
a bounded packet for later repair application. It does not call a model, rerun
the baseline, modify original reports, apply the repair, patch runner/scorer
code, apply LARQL, train LoRA, mutate models, write durable memory, or promote
candidates.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_baseline_repair_packet.v0"
PACKET_STATUS = "packet_only"
PROMOTION_VERDICT = "hold_pending_explicit_experiment_approval"
BASELINE_LANE = "baseline_prompt_context_only"
READY_PROPOSAL = "ready_for_repair_decision"
ACCEPTED_DECISION = "accepted_for_repair_packet_drafting_only"
REPAIR_SCOPE = "baseline_prompt_suite_and_scorer_only"

READY = "ready_for_bounded_repair_application"
NOT_READY = "not_ready_missing_decision"
INVALID_INPUT = "invalid_input"

OUTPUT_FILES = ("baseline_repair_packet.json", "baseline_repair_packet.md")

AUTHORIZED_TARGET_FILES = [
    "local_harness/affordance_baseline_execution_packet.py",
    "local_harness/affordance_baseline_runner.py",
    "tests/test_affordance_baseline_execution_packet.py",
    "tests/test_affordance_baseline_runner.py",
    "docs/experiments/AFFORDANCE_BASELINE_EXECUTION_PACKET_V0.md",
    "docs/experiments/AFFORDANCE_BASELINE_RUNNER_V0.md",
]

REQUIRED_TESTS = [
    "python3 -m pytest tests/test_affordance_baseline_execution_packet.py tests/test_affordance_baseline_runner.py",
    "python3 local_harness/repo_health_check.py",
    "git diff --check",
]

STRUCTURED_SPLIT_WORKFLOW_REQUIRED_LABELS = [
    "Local host:",
    "Remote host:",
    "Active execution host:",
    "Control rule:",
    "Candidate applies only if:",
]


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


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def default_scorer_repairs() -> list[dict[str, Any]]:
    return [
        {
            "prompt_id": "baseline_direct_cuda_on_navigator",
            "repair_type": "scorer_false_negative",
            "authorized_change": (
                "Accept phrasing that says to avoid CUDA-only setup and mentions "
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
        {
            "prompt_id": "baseline_cross_host_boundary",
            "repair_type": "scorer_false_negative",
            "authorized_change": (
                "Accept phrasing such as 'not generalizable to other profiles "
                "without matching evidence'."
            ),
            "accepted_language_examples": [
                "not generalizable to other profiles without matching evidence",
                "not generalize without matching evidence",
            ],
        },
        {
            "prompt_id": "baseline_reverify_before_action",
            "repair_type": "scorer_false_negative",
            "authorized_change": "Accept `revalidation` as equivalent to `reverify`.",
            "accepted_language_examples": ["revalidation", "reverify"],
        },
        {
            "prompt_id": "baseline_no_durable_promotion",
            "repair_type": "scorer_false_negative",
            "authorized_change": (
                "Accept language that says the run does not apply a LARQL patch, "
                "does not train LoRA, and does not perform durable "
                "memory/write/promotion."
            ),
            "accepted_language_examples": [
                "does not apply a LARQL patch",
                "does not train LoRA",
                "no durable memory",
                "no durable write",
                "no promotion",
            ],
        },
    ]


def normalize_scorer_repair(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "prompt_id": str(entry.get("prompt_id") or ""),
        "repair_type": str(entry.get("repair_type") or "scorer_false_negative"),
        "authorized_change": str(entry.get("authorized_change") or entry.get("proposal") or ""),
        "accepted_language_examples": string_list(entry.get("accepted_language_examples")),
    }


def scorer_repairs(proposal: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    if proposal is not None and "scorer_false_negative_repairs" in proposal:
        entries = proposal.get("scorer_false_negative_repairs")
        if isinstance(entries, list):
            return [normalize_scorer_repair(entry) for entry in entries if isinstance(entry, dict)]
        return []
    return default_scorer_repairs()


def default_prompt_repairs() -> list[dict[str, Any]]:
    return [
        {
            "prompt_id": "baseline_split_workflow_active_host",
            "repair_type": "prompt_and_scorer_tightening",
            "authorized_change": (
                "Update the prompt so the expected answer explicitly distinguishes "
                "local host, remote host, active execution host, and that the "
                "active host profile controls which affordance applies."
            ),
            "required_concepts": [
                "local host",
                "remote host",
                "active execution host",
                "active host profile controls which affordance applies",
            ],
            "scorer_requirement": (
                "Require local/remote distinction plus active-host/profile control language."
            ),
        }
    ]


def normalize_prompt_repair(entry: dict[str, Any]) -> dict[str, Any]:
    repair_type = str(entry.get("repair_type") or "prompt_and_scorer_tightening")
    required_labels = string_list(entry.get("required_labels"))
    if repair_type == "structured_prompt_and_scorer_tightening" and not required_labels:
        required_labels = list(STRUCTURED_SPLIT_WORKFLOW_REQUIRED_LABELS)
    normalized = {
        "prompt_id": str(entry.get("prompt_id") or ""),
        "repair_type": repair_type,
        "authorized_change": str(entry.get("authorized_change") or entry.get("proposal") or ""),
        "required_concepts": string_list(entry.get("required_concepts")),
        "scorer_requirement": str(entry.get("scorer_requirement") or ""),
    }
    if required_labels:
        normalized["required_labels"] = required_labels
    return normalized


def prompt_repairs(proposal: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    if proposal is not None and "prompt_weakness_repairs" in proposal:
        entries = proposal.get("prompt_weakness_repairs")
        if isinstance(entries, list):
            return [normalize_prompt_repair(entry) for entry in entries if isinstance(entry, dict)]
        return []
    return default_prompt_repairs()


def authorized_repair_actions(
    scorer_repair_entries: list[dict[str, Any]],
    prompt_repair_entries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    split_workflow_scorer = next(
        (
            repair
            for repair in scorer_repair_entries
            if repair.get("repair_type")
            == "split_workflow_active_host_applicability_scorer_acceptance"
        ),
        None,
    )
    line_separated_prompt = next(
        (
            repair
            for repair in prompt_repair_entries
            if repair.get("repair_type") == "line_separated_structured_prompt_tightening"
        ),
        None,
    )
    structured_prompt = next(
        (
            repair
            for repair in prompt_repair_entries
            if repair.get("repair_type") == "structured_prompt_and_scorer_tightening"
        ),
        None,
    )
    if line_separated_prompt is not None:
        required_labels = (
            line_separated_prompt.get("required_labels") or STRUCTURED_SPLIT_WORKFLOW_REQUIRED_LABELS
        )
        actions.append(
            {
                "action_id": "strengthen_split_workflow_prompt",
                "target_prompt": "baseline_split_workflow_active_host",
                "scope": "prompt_suite_and_scorer_only",
                "description": (
                    "Update the split-workflow prompt so it uses a line-separated answer "
                    "template, requires the model to copy the labels exactly, and keeps "
                    "the strict scorer unchanged; do not loosen scorer for these labels: "
                    f"{', '.join(required_labels)}."
                ),
                "required_labels": required_labels,
            }
        )
    elif split_workflow_scorer is not None:
        accepted_examples = split_workflow_scorer.get("accepted_language_examples") or []
        if not isinstance(accepted_examples, list):
            accepted_examples = []
        accepted_examples = [str(example) for example in accepted_examples if str(example)]
        required_labels = [
            "Local host:",
            "Remote host:",
            "Active execution host:",
            "Control rule:",
            "Candidate applies only if:",
        ]
        actions.append(
            {
                "action_id": "repair_scorer_false_negatives",
                "target_prompt": "baseline_split_workflow_active_host",
                "scope": "prompt_suite_and_scorer_only",
                "description": (
                    "Scorer-only repair: accept active-host applicability phrasing when the "
                    "response includes the exact structured labels and says the candidate "
                    "applies only when the active host matches the relevant host/profile "
                    f"constraints. Required labels: {', '.join(required_labels)}. Accepted "
                    "phrasing examples include active host is navigator_desktop, "
                    "constraints (no_cuda) are met, active host ... constraints ... met, "
                    "and Candidate applies only if: active host is ... and constraints ... "
                    "are met. No prompt repair is authorized. No runner execution "
                    "behavior change is authorized."
                ),
                "required_labels": required_labels,
                "accepted_language_examples": accepted_examples,
            }
        )
    elif structured_prompt is not None:
        required_labels = structured_prompt.get("required_labels") or STRUCTURED_SPLIT_WORKFLOW_REQUIRED_LABELS
        actions.append(
            {
                "action_id": "strengthen_split_workflow_prompt",
                "target_prompt": "baseline_split_workflow_active_host",
                "scope": "prompt_suite_and_scorer_only",
                "description": (
                    "Update the structured split-workflow prompt so it requires exact "
                    f"labels: {', '.join(required_labels)}."
                ),
                "required_labels": required_labels,
            }
        )
    elif prompt_repair_entries:
        prompt_ids = [repair["prompt_id"] for repair in prompt_repair_entries if repair.get("prompt_id")]
        actions.append(
            {
                "action_id": "strengthen_split_workflow_prompt",
                "target_prompts": prompt_ids,
                "scope": "prompt_suite_and_scorer_only",
                "description": (
                    "Update the split-workflow prompt so the expected answer distinguishes "
                    "local host, remote host, active execution host, and active-host-profile control language."
                ),
            }
        )
    if scorer_repair_entries:
        prompt_ids = [repair["prompt_id"] for repair in scorer_repair_entries if repair.get("prompt_id")]
        if split_workflow_scorer is not None:
            prompt_ids = [prompt_id for prompt_id in prompt_ids if prompt_id != "baseline_split_workflow_active_host"]
        if prompt_ids:
            actions.append(
                {
                    "action_id": "repair_scorer_false_negatives",
                    "target_prompts": prompt_ids,
                    "scope": "prompt_suite_and_scorer_only",
                    "description": (
                        "Update deterministic scorer acceptance for the reviewed "
                        f"false-negative prompts: {', '.join(f'`{prompt_id}`' for prompt_id in prompt_ids)}."
                    ),
                }
            )
    actions.extend(
        [
            {
                "action_id": "update_focused_tests",
                "scope": "tests_only",
                "description": (
                    "Update focused tests for revised scorer behavior and strengthened "
                    "split-workflow prompt coverage."
                ),
            },
            {
                "action_id": "update_experiment_docs",
                "scope": "docs_only",
                "description": (
                    "Update experiment docs to describe the revised baseline "
                    "prompt/scorer behavior."
                ),
            },
        ]
    )
    return actions


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
        "modify_original_decision_report",
        "modify_candidate",
        "modify_runner_execution_behavior",
        "authorize_runner_code_repair",
        "authorize_candidate_repair",
        "run_repaired_baseline_without_packet",
        "commit_or_push",
    ]


def build_checks(
    proposal: dict[str, Any],
    decision: dict[str, Any],
    proposal_checks: dict[str, bool],
    decision_checks: dict[str, bool],
) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    checks.update(proposal_checks)
    checks.update(decision_checks)
    checks.update(
        {
            "proposal_selected_lane_baseline": proposal.get("selected_lane") == BASELINE_LANE,
            "decision_selected_lane_baseline": decision.get("selected_lane") == BASELINE_LANE,
            "selected_lane_matches": proposal.get("selected_lane") == decision.get("selected_lane"),
            "proposal_promotion_held": proposal.get("promotion_verdict") == PROMOTION_VERDICT,
            "decision_promotion_held": decision.get("promotion_verdict") == PROMOTION_VERDICT,
            "proposal_verdict_ready": proposal.get("proposal_verdict") == READY_PROPOSAL,
            "decision_verdict_accepted": decision.get("decision_verdict") == ACCEPTED_DECISION,
            "accepted_repair_scope_ok": decision.get("accepted_repair_scope") == REPAIR_SCOPE,
            "runner_code_repair_not_authorized": (
                decision.get("runner_code_repair_authorized") is False
            ),
            "candidate_repair_not_authorized": (
                decision.get("candidate_repair_authorized") is False
            ),
            "proposal_rerun_required_after_repair": (
                proposal.get("rerun_required_after_repair") is True
            ),
            "decision_rerun_required_after_repair": (
                decision.get("rerun_required_after_repair") is True
            ),
        }
    )
    return checks


def invalid_input_from_checks(checks: dict[str, bool]) -> bool:
    required = [
        "repair_proposal_exists",
        "repair_proposal_parses",
        "repair_decision_exists",
        "repair_decision_parses",
        "proposal_selected_lane_baseline",
        "decision_selected_lane_baseline",
        "selected_lane_matches",
        "proposal_promotion_held",
        "decision_promotion_held",
        "proposal_verdict_ready",
        "accepted_repair_scope_ok",
        "runner_code_repair_not_authorized",
        "candidate_repair_not_authorized",
        "proposal_rerun_required_after_repair",
        "decision_rerun_required_after_repair",
    ]
    return not all(checks.get(name, False) for name in required)


def packet_verdict(checks: dict[str, bool]) -> str:
    if invalid_input_from_checks(checks):
        return INVALID_INPUT
    if not checks.get("decision_verdict_accepted", False):
        return NOT_READY
    return READY


def allowed_next_step(verdict: str) -> str:
    if verdict == READY:
        return "apply_baseline_prompt_scorer_repair_packet"
    if verdict == NOT_READY:
        return "complete_or_replace_baseline_repair_decision"
    return "repair_or_replace_baseline_repair_packet_inputs"


def build_packet(proposal_path: Path, decision_path: Path) -> dict[str, Any]:
    proposal, proposal_checks, proposal_notes = read_json_object(
        proposal_path,
        "repair_proposal",
    )
    decision, decision_checks, decision_notes = read_json_object(
        decision_path,
        "repair_decision",
    )
    checks = build_checks(proposal, decision, proposal_checks, decision_checks)
    verdict = packet_verdict(checks)
    failed_checks = [name for name, passed in checks.items() if not passed]
    scorer_repair_entries = scorer_repairs(proposal)
    prompt_repair_entries = prompt_repairs(proposal)
    notes = [
        *proposal_notes,
        *decision_notes,
        "Packet only; no repair is applied.",
        "Original run, review, proposal, and decision verdicts remain preserved.",
        "Runner execution behavior is not authorized for repair.",
        "Candidate repair is not authorized.",
        "Rerun is required after any accepted repair.",
    ]
    if failed_checks:
        notes.append("Failed checks: " + ", ".join(failed_checks))

    return {
        "report_type": REPORT_TYPE,
        "candidate_id": proposal.get("candidate_id") or decision.get("candidate_id"),
        "source_failure_id": proposal.get("source_failure_id")
        or decision.get("source_failure_id"),
        "selected_lane": proposal.get("selected_lane") or decision.get("selected_lane"),
        "repair_scope": REPAIR_SCOPE if verdict == READY else decision.get("accepted_repair_scope"),
        "packet_status": PACKET_STATUS,
        "packet_verdict": verdict,
        "promotion_verdict": PROMOTION_VERDICT,
        "input_proposal_verdict": proposal.get("proposal_verdict"),
        "input_decision_verdict": decision.get("decision_verdict"),
        "allowed_next_step": allowed_next_step(verdict),
        "authorized_target_files": AUTHORIZED_TARGET_FILES,
        "authorized_repair_actions": authorized_repair_actions(
            scorer_repair_entries,
            prompt_repair_entries,
        ),
        "scorer_repairs": scorer_repair_entries,
        "prompt_repairs": prompt_repair_entries,
        "required_tests": REQUIRED_TESTS,
        "rerun_required_after_repair": bool(
            proposal.get("rerun_required_after_repair")
            and decision.get("rerun_required_after_repair")
        ),
        "runner_code_repair_authorized": False,
        "candidate_repair_authorized": False,
        "disallowed_actions": disallowed_actions(),
        "checks": checks,
        "notes": notes,
    }


def markdown_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items]


def render_markdown(packet: dict[str, Any]) -> str:
    lines = [
        "# Affordance Baseline Repair Packet v0",
        "",
        f"Candidate id: `{packet.get('candidate_id') or 'unknown'}`",
        f"Source failure id: `{packet.get('source_failure_id') or 'unknown'}`",
        f"Selected lane: `{packet.get('selected_lane') or 'unknown'}`",
        "",
        "## Verdict",
        "",
        f"- Input proposal verdict: `{packet.get('input_proposal_verdict') or 'unknown'}`",
        f"- Input decision verdict: `{packet.get('input_decision_verdict') or 'unknown'}`",
        f"- Packet verdict: `{packet['packet_verdict']}`",
        f"- Promotion verdict: `{packet['promotion_verdict']}`",
        f"- Repair scope: `{packet.get('repair_scope') or 'none'}`",
        f"- Allowed next step: `{packet['allowed_next_step']}`",
        f"- Rerun required after repair: `{str(packet['rerun_required_after_repair']).lower()}`",
        "",
        "## Authorized Target Files",
        "",
        *markdown_list(packet["authorized_target_files"]),
        "",
        "## Authorized Repair Actions",
        "",
    ]
    for action in packet["authorized_repair_actions"]:
        lines.extend(
            [
                f"### `{action['action_id']}`",
                "",
                f"- Scope: `{action['scope']}`",
                f"- Description: {action['description']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Scorer Repairs",
            "",
        ]
    )
    for repair in packet["scorer_repairs"]:
        lines.extend(
            [
                f"- `{repair['prompt_id']}`: {repair['authorized_change']}",
            ]
        )
    lines.extend(
        [
            "",
            "## Prompt Repairs",
            "",
        ]
    )
    for repair in packet["prompt_repairs"]:
        lines.extend(
            [
                f"- `{repair['prompt_id']}`: {repair['authorized_change']}",
                f"  - Repair type: `{repair['repair_type']}`",
            ]
        )
        if repair.get("required_labels"):
            lines.extend(
                [
                    "  - Required labels:",
                    *[f"    - {label}" for label in repair["required_labels"]],
                ]
            )
    lines.extend(
        [
            "",
            "## Required Tests",
            "",
            *markdown_list(packet["required_tests"]),
            "",
            "## Checks",
            "",
            "| Check | Passed |",
            "|---|---:|",
        ]
    )
    for name, passed in packet["checks"].items():
        lines.append(f"| `{name}` | `{str(passed).lower()}` |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This is packet only.",
            "No repair is applied by this packet.",
            "The original run verdict remains preserved.",
            "The original review verdict remains preserved.",
            "The original proposal verdict remains preserved.",
            "The original decision verdict remains preserved.",
            "Only the exact target files listed above are authorized.",
            "Only the exact repair actions listed above are authorized.",
            "Runner execution behavior is not authorized for repair.",
            "Candidate repair is not authorized.",
            "This packet is not a LARQL patch.",
            "This packet is not LoRA training.",
            "This packet is not model mutation.",
            "This packet is not durable memory promotion.",
            "This packet is not comparison lane execution.",
            "This packet grants no candidate promotion.",
            "Rerun is required after any accepted repair.",
            "",
            "## Disallowed Actions",
            "",
            *markdown_list(packet["disallowed_actions"]),
            "",
            "## Notes",
            "",
            *markdown_list(packet["notes"]),
            "",
        ]
    )
    return "\n".join(lines)


def write_reports(
    proposal_path: Path,
    decision_path: Path,
    out_dir: Path,
) -> dict[str, Any]:
    validate_out_dir(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    packet = build_packet(proposal_path, decision_path)
    (out_dir / "baseline_repair_packet.json").write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "baseline_repair_packet.md").write_text(
        render_markdown(packet),
        encoding="utf-8",
    )
    return packet


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a model-free baseline prompt/scorer repair packet."
    )
    parser.add_argument("--repair-proposal", required=True, type=Path)
    parser.add_argument("--repair-decision", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        packet = write_reports(args.repair_proposal, args.repair_decision, args.out)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    for filename in OUTPUT_FILES:
        print(f"wrote: {args.out / filename}")
    print(f"packet_verdict: {packet['packet_verdict']}")
    print(f"promotion_verdict: {packet['promotion_verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
