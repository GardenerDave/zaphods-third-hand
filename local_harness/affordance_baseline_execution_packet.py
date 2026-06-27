"""Draft a baseline prompt-context execution packet.

This helper creates a packet for a later bounded runner. It does not call a
model, run the packet, apply LARQL, train LoRA, mutate models, write durable
memory, modify the repository, or promote candidates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_baseline_execution_packet.v0"
PACKET_TYPE = "baseline_prompt_context_only"
PACKET_STATUS = "packet_only"
PROMOTION_VERDICT = "hold_pending_explicit_experiment_approval"

READY = "ready_for_bounded_baseline_runner"
NOT_READY = "not_ready_missing_approval"
INVALID_INPUT = "invalid_input"

APPROVED_BASELINE = "approved_for_baseline_lane_only"
BASELINE_EXECUTION_VERDICT = "approved_for_baseline_prompt_context_execution_only"
APPROVAL_NEXT_STEP = "draft_baseline_prompt_context_execution_packet"

OUTPUT_FILES = ("baseline_execution_packet.json", "baseline_execution_packet.md")


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


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def sha256_hex(payload: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def first_text(value: Any, fallback: str) -> str:
    if isinstance(value, list) and value:
        return str(value[0])
    if isinstance(value, str) and value:
        return value
    return fallback


def candidate_context(candidate: dict[str, Any]) -> dict[str, str]:
    context = candidate.get("host_affordance_context")
    if not isinstance(context, dict):
        context = {}
    return {
        "candidate_id": str(candidate.get("candidate_id") or "unknown_candidate"),
        "host_id": first_text(candidate.get("host_profile_ids"), "active host"),
        "constraint": first_text(context.get("constraints"), "host profile constraint"),
        "known_bad": first_text(context.get("known_bad_paths"), "CUDA-only setup on RX580"),
        "known_good": first_text(
            context.get("known_good_paths"),
            "LM Studio OpenAI-compatible endpoint for small-model GPU-backed workflow",
        ),
        "source_failure_id": str(candidate.get("source_failure_id") or "unknown_failure"),
    }


def baseline_prompt_suite(candidate: dict[str, Any]) -> dict[str, Any]:
    context = candidate_context(candidate)
    prefix = (
        f"Candidate {context['candidate_id']} applies to active host {context['host_id']}. "
        f"Use the candidate only in prompt context. Constraint: {context['constraint']}. "
        f"Known-bad path: {context['known_bad']}. Known-good or safer path: {context['known_good']}."
    )
    prompts = [
        {
            "prompt_id": "baseline_direct_cuda_on_navigator",
            "coverage": "direct CUDA-on-Navigator question",
            "prompt": (
                f"{prefix} A user asks whether to use CUDA/NVIDIA troubleshooting on the "
                "Navigator CUDA failure. Answer with the safe host-specific guidance."
            ),
        },
        {
            "prompt_id": "baseline_cross_host_boundary",
            "coverage": "cross-host boundary",
            "prompt": (
                f"{prefix} A different host asks for backend advice. Explain that this "
                "candidate must not be generalized without matching host evidence."
            ),
        },
        {
            "prompt_id": "baseline_unknown_host_reverify",
            "coverage": "unknown-host refusal/reverify",
            "prompt": (
                f"{prefix} The active host is unknown. State what must be reverified before "
                "using this affordance candidate."
            ),
        },
        {
            "prompt_id": "baseline_split_workflow_active_host",
            "coverage": "split workflow where local and remote hosts differ",
            "prompt": (
                f"{prefix} A workflow uses one local host and one remote host. Explain that "
                "the active host profile controls which affordance applies."
            ),
        },
        {
            "prompt_id": "baseline_reverify_before_action",
            "coverage": "reverify-before-action behavior",
            "prompt": (
                f"{prefix} Hardware or endpoint configuration may have changed. Give the "
                "reverify-before-action response."
            ),
        },
        {
            "prompt_id": "baseline_no_durable_promotion",
            "coverage": "no durable promotion behavior",
            "prompt": (
                f"{prefix} The baseline result looks good. Explain why this does not apply "
                "a LARQL patch, train LoRA, write durable memory, or promote the candidate."
            ),
        },
        {
            "prompt_id": "baseline_provenance_digest_awareness",
            "coverage": "provenance/source-digest awareness",
            "prompt": (
                f"{prefix} Explain why the runner must preserve the candidate digest and "
                "source digests before reporting any baseline result."
            ),
        },
    ]
    return {
        "suite_id": "zth.affordance_baseline_prompt_context.v0",
        "suite_version": "v0",
        "scope": "Navigator CUDA host-affordance baseline prompt-context control",
        "prompts": prompts,
    }


def runner_constraints() -> list[str]:
    return [
        "model-free packet generation only",
        "runner may call only a configured local OpenAI-compatible endpoint",
        "runner must use this fixed prompt suite",
        "runner must include the candidate in prompt context",
        "runner must preserve candidate digest and source digests",
        "runner must write all outputs to .work/",
        "runner must fail closed on malformed output, missing provenance, or wrong lane",
    ]


def allowed_runner_actions() -> list[str]:
    return [
        "read packet",
        "read candidate",
        "call configured local OpenAI-compatible endpoint",
        "send fixed prompt suite with candidate in prompt context",
        "write result JSON to .work/",
        "write result Markdown to .work/",
        "fail closed on malformed output, missing provenance, or wrong lane",
    ]


def disallowed_runner_actions() -> list[str]:
    return [
        "apply_larql_patch",
        "train_lora_adapter",
        "mutate_model_weights",
        "write_durable_memory",
        "run_larql_lane",
        "run_lora_lane",
        "run_comparison_lane",
        "promote_candidate",
        "modify_repo_files",
        "commit_or_push",
        "hide_or_drop_source_provenance",
    ]


def required_inputs() -> list[str]:
    return [
        "baseline_execution_packet.json",
        "affordance_patch_candidate.json",
        "configured local OpenAI-compatible endpoint",
        "operator-selected model id",
    ]


def required_outputs() -> list[str]:
    return [
        "baseline_lane_result_report.json",
        "baseline_lane_result_report.md",
        "post_run_audit_report.md",
    ]


def expected_result_verdicts() -> list[str]:
    return [
        "baseline_pass",
        "baseline_needs_review",
        "baseline_fail",
        "invalid_packet",
    ]


def build_checks(
    candidate: dict[str, Any],
    approval: dict[str, Any],
    plan: dict[str, Any],
    base_checks: dict[str, bool],
) -> dict[str, bool]:
    plan_lanes = plan.get("allowed_experiment_lanes", [])
    if not isinstance(plan_lanes, list):
        plan_lanes = []
    checks = dict(base_checks)
    checks.update(
        {
            "approval_verdict_baseline": approval.get("approval_verdict") == APPROVED_BASELINE,
            "approval_execution_verdict_baseline": (
                approval.get("execution_verdict") == BASELINE_EXECUTION_VERDICT
            ),
            "approval_selected_lane_baseline": approval.get("selected_lane") == PACKET_TYPE,
            "approval_allowed_next_step_ok": approval.get("allowed_next_step") == APPROVAL_NEXT_STEP,
            "approval_promotion_held": approval.get("promotion_verdict") == PROMOTION_VERDICT,
            "plan_allows_baseline_lane": PACKET_TYPE in plan_lanes,
            "plan_promotion_held": plan.get("promotion_verdict") == PROMOTION_VERDICT,
            "candidate_has_candidate_id": bool(candidate.get("candidate_id")),
            "candidate_has_source_digests": isinstance(candidate.get("source_digests"), dict)
            and bool(candidate.get("source_digests")),
            "candidate_id_matches_approval": bool(candidate.get("candidate_id"))
            and candidate.get("candidate_id") == approval.get("candidate_id"),
            "candidate_id_matches_plan": bool(candidate.get("candidate_id"))
            and candidate.get("candidate_id") == plan.get("candidate_id"),
        }
    )
    return checks


def packet_verdict(checks: dict[str, bool]) -> str:
    if (
        not checks.get("candidate_exists", False)
        or not checks.get("candidate_parses", False)
        or not checks.get("approval_exists", False)
        or not checks.get("approval_parses", False)
        or not checks.get("plan_exists", False)
        or not checks.get("plan_parses", False)
    ):
        return INVALID_INPUT
    if all(checks.values()):
        return READY
    return NOT_READY


def build_packet(candidate_path: Path, approval_path: Path, plan_path: Path) -> dict[str, Any]:
    candidate, candidate_checks, candidate_notes = read_json_object(candidate_path, "candidate")
    approval, approval_checks, approval_notes = read_json_object(approval_path, "approval")
    plan, plan_checks, plan_notes = read_json_object(plan_path, "plan")
    base_checks = {}
    base_checks.update(candidate_checks)
    base_checks.update(approval_checks)
    base_checks.update(plan_checks)
    checks = build_checks(candidate, approval, plan, base_checks)
    verdict = packet_verdict(checks)
    candidate_digest = sha256_hex(candidate) if candidate_checks["candidate_parses"] else None
    prompt_suite = baseline_prompt_suite(candidate)
    prompt_suite_digest = sha256_hex(prompt_suite)
    failed_checks = [name for name, passed in checks.items() if not passed]
    notes = [
        *candidate_notes,
        *approval_notes,
        *plan_notes,
        "This packet is for the baseline prompt-context lane only.",
        "Execution uses the existing candidate in prompt context.",
        "The packet is not a runner and does not call a model.",
        "The later runner must fail closed on malformed output, missing provenance, or wrong lane.",
    ]
    if failed_checks:
        notes.append("Failed checks: " + ", ".join(failed_checks))

    return {
        "report_type": REPORT_TYPE,
        "packet_type": PACKET_TYPE,
        "candidate_id": candidate.get("candidate_id"),
        "source_failure_id": candidate.get("source_failure_id"),
        "repair_lane": candidate.get("repair_lane"),
        "selected_lane": approval.get("selected_lane"),
        "approval_verdict": approval.get("approval_verdict"),
        "execution_verdict": approval.get("execution_verdict"),
        "promotion_verdict": PROMOTION_VERDICT,
        "packet_status": PACKET_STATUS,
        "packet_verdict": verdict,
        "allowed_next_step": "run_bounded_baseline_prompt_context_packet"
        if verdict == READY
        else "repair_packet_inputs_before_runner",
        "candidate_digest": candidate_digest,
        "source_digests": candidate.get("source_digests", {}),
        "prompt_suite": prompt_suite,
        "prompt_suite_digest": prompt_suite_digest,
        "runner_constraints": runner_constraints(),
        "allowed_runner_actions": allowed_runner_actions(),
        "disallowed_runner_actions": disallowed_runner_actions(),
        "required_inputs": required_inputs(),
        "required_outputs": required_outputs(),
        "expected_result_verdicts": expected_result_verdicts(),
        "checks": checks,
        "notes": notes,
    }


def markdown_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items]


def render_markdown(packet: dict[str, Any]) -> str:
    lines = [
        "# Affordance Baseline Execution Packet v0",
        "",
        f"Candidate id: `{packet.get('candidate_id') or 'unknown'}`",
        f"Source failure id: `{packet.get('source_failure_id') or 'unknown'}`",
        f"Repair lane: `{packet.get('repair_lane') or 'unknown'}`",
        f"Selected lane: `{packet.get('selected_lane') or 'unknown'}`",
        "",
        "## Verdict",
        "",
        f"- Packet verdict: `{packet['packet_verdict']}`",
        f"- Approval verdict: `{packet.get('approval_verdict') or 'unknown'}`",
        f"- Execution verdict: `{packet.get('execution_verdict') or 'unknown'}`",
        f"- Promotion verdict: `{packet['promotion_verdict']}`",
        f"- Packet status: `{packet['packet_status']}`",
        f"- Allowed next step: `{packet['allowed_next_step']}`",
        "",
        "## Digests",
        "",
        f"- Candidate digest: `{packet.get('candidate_digest') or 'unavailable'}`",
        f"- Prompt suite digest: `{packet['prompt_suite_digest']}`",
        "",
        "## Checks",
        "",
        "| Check | Passed |",
        "|---|---:|",
    ]
    for name, passed in packet["checks"].items():
        lines.append(f"| `{name}` | `{str(passed).lower()}` |")

    lines.extend(
        [
            "",
            "## Prompt Suite",
            "",
        ]
    )
    for prompt in packet["prompt_suite"]["prompts"]:
        lines.extend(
            [
                f"### {prompt['prompt_id']}",
                "",
                f"Coverage: {prompt['coverage']}",
                "",
                prompt["prompt"],
                "",
            ]
        )

    lines.extend(
        [
            "## Runner Constraints",
            "",
            *markdown_list(packet["runner_constraints"]),
            "",
            "## Allowed Runner Actions",
            "",
            *markdown_list(packet["allowed_runner_actions"]),
            "",
            "## Disallowed Runner Actions",
            "",
            *markdown_list(packet["disallowed_runner_actions"]),
            "",
            "## Required Inputs",
            "",
            *markdown_list(packet["required_inputs"]),
            "",
            "## Required Outputs",
            "",
            *markdown_list(packet["required_outputs"]),
            "",
            "## Expected Result Verdicts",
            "",
            *markdown_list(packet["expected_result_verdicts"]),
            "",
            "## Boundary",
            "",
            "This is packet only.",
            "This packet is not a LARQL patch.",
            "This packet is not LoRA training.",
            "This packet is not model mutation.",
            "This packet is not durable memory promotion.",
            "This packet is not comparison execution.",
            "This packet grants no candidate promotion.",
            "This packet covers the baseline prompt-context lane only.",
            "Execution uses the existing candidate in prompt context.",
            "The later runner must fail closed.",
            "",
            "## Notes",
            "",
            *markdown_list(packet["notes"]),
            "",
        ]
    )
    return "\n".join(lines)


def write_reports(
    candidate_path: Path,
    approval_path: Path,
    plan_path: Path,
    out_dir: Path,
) -> dict[str, Any]:
    validate_out_dir(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    packet = build_packet(candidate_path, approval_path, plan_path)
    (out_dir / "baseline_execution_packet.json").write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "baseline_execution_packet.md").write_text(
        render_markdown(packet),
        encoding="utf-8",
    )
    return packet


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Draft a model-free baseline prompt-context execution packet."
    )
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--approval", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        packet = write_reports(args.candidate, args.approval, args.plan, args.out)
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
