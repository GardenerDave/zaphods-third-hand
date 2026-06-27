"""Draft a model-free affordance experiment proposal.

This helper turns a candidate, eligibility report, and repeatability report
into a reviewable proposal artifact. It does not apply LARQL, train LoRA,
mutate models, write durable memory, or promote candidates.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_experiment_proposal.v0"
EXPERIMENT_STATUS = "proposal_only"
PROMOTION_VERDICT = "hold_pending_explicit_experiment_approval"
READY = "ready_for_operator_review"
MISSING_ELIGIBILITY = "not_ready_missing_eligibility"
INVALID_INPUT = "not_ready_invalid_input"
ELIGIBLE = "eligible_for_experiment_proposal"
SUPPORTED_REPAIR_LANES = {
    "larql_candidate",
    "lora_candidate",
    "larql_plus_lora_candidate",
}
EXPERIMENT_TYPE_OPTIONS = [
    "larql_affordance_patch_probe",
    "lora_failure_curriculum_candidate",
    "larql_plus_lora_comparison",
]
OUTPUT_FILES = ("experiment_proposal.json", "experiment_proposal.md")


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


def read_repeatability_report(path: Path) -> tuple[str, dict[str, bool], list[str]]:
    checks = {"repeatability_report_exists": path.exists()}
    notes: list[str] = []
    if not checks["repeatability_report_exists"]:
        notes.append(f"repeatability report missing: {path}")
        return "", checks, notes
    return path.read_text(encoding="utf-8"), checks, notes


def recommended_experiment_type(repair_lane: str | None) -> str:
    if repair_lane == "larql_plus_lora_candidate":
        return "larql_plus_lora_comparison"
    if repair_lane == "lora_candidate":
        return "lora_failure_curriculum_candidate"
    if repair_lane == "larql_candidate":
        return "larql_affordance_patch_probe"
    return "insufficient_evidence"


def readiness_checks(
    candidate: dict[str, Any],
    eligibility: dict[str, Any],
    repeatability_text: str,
    base_checks: dict[str, bool],
) -> dict[str, bool]:
    checks = dict(base_checks)
    checks.update(
        {
            "eligibility_verdict_is_eligible": (
                eligibility.get("eligibility_verdict") == ELIGIBLE
            ),
            "eligibility_promotion_held": (
                eligibility.get("promotion_verdict") == PROMOTION_VERDICT
            ),
            "candidate_has_source_digests": isinstance(candidate.get("source_digests"), dict)
            and bool(candidate.get("source_digests")),
            "repair_lane_supported": candidate.get("repair_lane") in SUPPORTED_REPAIR_LANES,
            "repeatability_total_passes_35_of_35": "Total prompt passes: 35 / 35"
            in repeatability_text,
            "repeatability_no_larql_lora_mutation": (
                "No LARQL patch, LoRA training, or durable model mutation was applied"
                in repeatability_text
            ),
        }
    )
    return checks


def failed_checks(checks: dict[str, bool]) -> list[str]:
    return [name for name, passed in checks.items() if not passed]


def proposal_verdict(checks: dict[str, bool]) -> str:
    if (
        not checks.get("candidate_exists", False)
        or not checks.get("candidate_parses", False)
        or not checks.get("eligibility_report_exists", False)
        or not checks.get("eligibility_report_parses", False)
    ):
        return INVALID_INPUT
    if all(checks.values()):
        return READY
    return MISSING_ELIGIBILITY


def preconditions() -> list[str]:
    return [
        "Operator has reviewed the candidate, repeatability report, and eligibility report.",
        "Any injection, training, or durable-memory experiment has separate explicit approval.",
        "Private endpoint details, host paths, and raw local evidence remain uncommitted unless sanitized.",
    ]


def experiment_boundaries() -> list[str]:
    return [
        "Proposal only; no LARQL patch is applied.",
        "No LoRA training is started.",
        "No model weights, adapters, vindexes, or durable memory are mutated.",
        "No candidate is promoted or accepted by this artifact.",
        "The current candidate is already usable in prompt context; the experiment asks whether another lane reduces that context burden safely.",
    ]


def success_criteria() -> list[str]:
    return [
        "Post-experiment probe suite matches the baseline affordance probe suite.",
        "Repeatability checks meet or exceed the 35 / 35 prompt-pass baseline.",
        "No regression on unknown-host, different-host, split-workflow, or reverify prompts.",
        "Provenance remains attached to any experimental patch or training artifact.",
    ]


def failure_criteria() -> list[str]:
    return [
        "Any regression, overgeneralization to other hosts, missing provenance, or promotion without review rejects the experiment.",
        "Any automatic application, training, durable memory write, or lifecycle movement outside explicit approval rejects the experiment.",
        "Any need to hide or omit source evidence rejects the experiment.",
    ]


def post_experiment_required_audits() -> list[str]:
    return [
        "Run the same affordance probe suite after the experiment.",
        "Run repeatability checks comparable to the 5 clean-run baseline.",
        "Review outputs for host confusion and overgeneralization.",
        "Record whether context burden changed without weakening safety boundaries.",
    ]


def rollback_or_rejection_rules() -> list[str]:
    return [
        "Reject rather than repair in place if provenance is missing.",
        "Reject if the candidate generalizes host-specific affordances to unsupported hosts.",
        "Reject if post-experiment probes fail or require waived promotion.",
        "Keep the original prompt-context candidate as the safe baseline.",
    ]


def build_proposal(
    candidate_path: Path,
    eligibility_report_path: Path,
    repeatability_report_path: Path,
) -> dict[str, Any]:
    candidate, candidate_checks, candidate_notes = read_json_object(candidate_path, "candidate")
    eligibility, eligibility_checks, eligibility_notes = read_json_object(
        eligibility_report_path, "eligibility_report"
    )
    repeatability_text, repeatability_checks, repeatability_notes = read_repeatability_report(
        repeatability_report_path
    )
    base_checks = {}
    base_checks.update(candidate_checks)
    base_checks.update(eligibility_checks)
    base_checks.update(repeatability_checks)
    checks = readiness_checks(candidate, eligibility, repeatability_text, base_checks)
    failed = failed_checks(checks)
    verdict = proposal_verdict(checks)
    repair_lane = candidate.get("repair_lane")

    notes = [
        *candidate_notes,
        *eligibility_notes,
        *repeatability_notes,
        "The current candidate is already usable in prompt context.",
        "The proposed experiment compares whether LARQL-style patching, LoRA fine-tuning, or both improve behavior without needing the full affordance record in prompt context.",
        "Any injection or training must be explicitly approved separately.",
    ]
    if failed:
        notes.append("Failed checks: " + ", ".join(failed))

    return {
        "report_type": REPORT_TYPE,
        "candidate_id": candidate.get("candidate_id"),
        "source_failure_id": candidate.get("source_failure_id"),
        "repair_lane": repair_lane,
        "host_profile_ids": candidate.get("host_profile_ids", []),
        "source_digests": candidate.get("source_digests", {}),
        "eligibility_verdict": eligibility.get("eligibility_verdict"),
        "experiment_status": EXPERIMENT_STATUS,
        "proposal_verdict": verdict,
        "promotion_verdict": PROMOTION_VERDICT,
        "experiment_type_options": EXPERIMENT_TYPE_OPTIONS,
        "recommended_experiment_type": recommended_experiment_type(repair_lane),
        "preconditions": preconditions(),
        "experiment_boundaries": experiment_boundaries(),
        "success_criteria": success_criteria(),
        "failure_criteria": failure_criteria(),
        "post_experiment_required_audits": post_experiment_required_audits(),
        "rollback_or_rejection_rules": rollback_or_rejection_rules(),
        "checks": checks,
        "notes": notes,
    }


def markdown_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items]


def render_markdown(proposal: dict[str, Any]) -> str:
    lines = [
        "# Affordance Experiment Proposal v0",
        "",
        f"Candidate id: `{proposal.get('candidate_id') or 'unknown'}`",
        f"Source failure id: `{proposal.get('source_failure_id') or 'unknown'}`",
        f"Repair lane: `{proposal.get('repair_lane') or 'unknown'}`",
        f"Recommended experiment type: `{proposal['recommended_experiment_type']}`",
        "",
        "## Verdict",
        "",
        f"- Proposal verdict: `{proposal['proposal_verdict']}`",
        f"- Promotion verdict: `{proposal['promotion_verdict']}`",
        f"- Experiment status: `{proposal['experiment_status']}`",
        "",
        "## Checks",
        "",
        "| Check | Passed |",
        "|---|---:|",
    ]
    for name, passed in proposal["checks"].items():
        lines.append(f"| `{name}` | `{str(passed).lower()}` |")

    lines.extend(
        [
            "",
            "## Proposed Experiment",
            "",
            "The current candidate is already usable in context.",
            "The proposed experiment is to compare whether LARQL-style patching, LoRA fine-tuning, or both improve behavior without needing the full affordance record in prompt context.",
            "Any injection/training must be explicitly approved separately.",
            "",
            "## Preconditions",
            "",
            *markdown_list(proposal["preconditions"]),
            "",
            "## Boundaries",
            "",
            *markdown_list(proposal["experiment_boundaries"]),
            "",
            "This proposal is not a LARQL patch.",
            "This proposal is not LoRA training.",
            "This proposal is not durable memory promotion.",
            "This proposal is not model mutation.",
            "It requires explicit approval before any injection, training, or durable-memory step.",
            "",
            "## Success Criteria",
            "",
            *markdown_list(proposal["success_criteria"]),
            "",
            "## Failure Criteria",
            "",
            *markdown_list(proposal["failure_criteria"]),
            "",
            "## Post-Experiment Required Audits",
            "",
            *markdown_list(proposal["post_experiment_required_audits"]),
            "",
            "Any future experiment requires post-experiment re-audition.",
            "",
            "## Rollback / Rejection Rules",
            "",
            *markdown_list(proposal["rollback_or_rejection_rules"]),
            "",
            "## Notes",
            "",
            *markdown_list(proposal["notes"]),
            "",
        ]
    )
    return "\n".join(lines)


def write_reports(
    candidate_path: Path,
    eligibility_report_path: Path,
    repeatability_report_path: Path,
    out_dir: Path,
) -> dict[str, Any]:
    validate_out_dir(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    proposal = build_proposal(candidate_path, eligibility_report_path, repeatability_report_path)
    (out_dir / "experiment_proposal.json").write_text(
        json.dumps(proposal, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "experiment_proposal.md").write_text(render_markdown(proposal), encoding="utf-8")
    return proposal


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Write a model-free affordance experiment proposal."
    )
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--eligibility-report", required=True, type=Path)
    parser.add_argument("--repeatability-report", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        proposal = write_reports(
            args.candidate,
            args.eligibility_report,
            args.repeatability_report,
            args.out,
        )
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
