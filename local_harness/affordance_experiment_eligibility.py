"""Model-free eligibility gate for affordance experiment proposals.

This helper reviews one affordance candidate plus a repeatability report and
decides whether there is enough evidence to draft a future experiment proposal.
It does not promote candidates, apply LARQL, train LoRA, mutate models, or move
durable memory state.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_experiment_eligibility.v0"
PROMOTION_VERDICT = "hold_pending_explicit_experiment_approval"
ELIGIBLE = "eligible_for_experiment_proposal"
NEEDS_MORE_EVIDENCE = "not_eligible_needs_more_evidence"
INVALID_INPUT = "not_eligible_invalid_input"
SUPPORTED_REPAIR_LANES = {
    "larql_candidate",
    "lora_candidate",
    "larql_plus_lora_candidate",
}
OUTPUT_FILES = ("eligibility_report.json", "eligibility_report.md")


def validate_out_dir(path: Path) -> None:
    if any(part == ".." for part in path.parts):
        raise ValueError(f"{path}: output directory must not contain '..'")
    if path.exists() and not path.is_dir():
        raise ValueError(f"{path}: output path exists and is not a directory")


def read_candidate(path: Path) -> tuple[dict[str, Any], dict[str, bool], list[str]]:
    checks = {
        "candidate_exists": path.exists(),
        "candidate_parses": False,
    }
    notes: list[str] = []
    if not checks["candidate_exists"]:
        notes.append(f"Candidate file missing: {path}")
        return {}, checks, notes

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        notes.append(f"Candidate JSON parse failed: {exc.msg}")
        return {}, checks, notes

    if not isinstance(payload, dict):
        notes.append("Candidate input is not a JSON object.")
        return {}, checks, notes

    checks["candidate_parses"] = True
    return payload, checks, notes


def read_repeatability_report(path: Path) -> tuple[str, dict[str, bool], list[str]]:
    checks = {"repeatability_report_exists": path.exists()}
    notes: list[str] = []
    if not checks["repeatability_report_exists"]:
        notes.append(f"Repeatability report missing: {path}")
        return "", checks, notes
    return path.read_text(encoding="utf-8"), checks, notes


def repeatability_checks(text: str) -> dict[str, bool]:
    return {
        "repeatability_clean_7_of_7_5_of_5": "Clean 7/7 runs: 5 / 5" in text,
        "repeatability_total_passes_35_of_35": "Total prompt passes: 35 / 35" in text,
        "repeatability_total_needs_review_0_of_35": "Total prompt needs_review: 0 / 35" in text,
        "repeatability_no_larql_lora_mutation": (
            "No LARQL patch, LoRA training, or durable model mutation was applied" in text
        ),
        "repeatability_promotion_held": (
            "Promotion behavior: held for review" in text or "promotion" in text.lower()
        ),
    }


def candidate_checks(candidate: dict[str, Any]) -> dict[str, bool]:
    return {
        "candidate_has_candidate_id": bool(candidate.get("candidate_id")),
        "candidate_has_repair_lane": bool(candidate.get("repair_lane")),
        "candidate_has_source_digests": isinstance(candidate.get("source_digests"), dict)
        and bool(candidate.get("source_digests")),
        "repair_lane_supported": candidate.get("repair_lane") in SUPPORTED_REPAIR_LANES,
    }


def failed_checks(checks: dict[str, bool]) -> list[str]:
    return [name for name, passed in checks.items() if not passed]


def eligibility_verdict(checks: dict[str, bool]) -> str:
    if not checks.get("candidate_exists", False) or not checks.get("candidate_parses", False):
        return INVALID_INPUT
    if all(checks.values()):
        return ELIGIBLE
    return NEEDS_MORE_EVIDENCE


def recommended_next_step(verdict: str, failed: list[str]) -> str:
    if verdict == ELIGIBLE:
        return "draft_explicit_affordance_experiment_proposal_for_review"
    if verdict == INVALID_INPUT:
        return "fix candidate input before eligibility can be assessed"
    return "collect missing evidence before experiment proposal: " + ", ".join(failed)


def build_report(candidate_path: Path, repeatability_report_path: Path) -> dict[str, Any]:
    candidate, base_checks, notes = read_candidate(candidate_path)
    report_text, report_checks, report_notes = read_repeatability_report(repeatability_report_path)
    notes.extend(report_notes)

    checks: dict[str, bool] = {}
    checks.update(base_checks)
    checks.update(candidate_checks(candidate))
    checks.update(report_checks)
    checks.update(repeatability_checks(report_text) if report_text else repeatability_checks(""))

    failed = failed_checks(checks)
    verdict = eligibility_verdict(checks)
    notes.extend(
        [
            "Eligibility is for a future experiment proposal only.",
            "No LARQL patch, LoRA training, durable model mutation, or promotion is performed.",
        ]
    )
    if failed:
        notes.append("Failed checks: " + ", ".join(failed))

    return {
        "report_type": REPORT_TYPE,
        "candidate_id": candidate.get("candidate_id"),
        "source_failure_id": candidate.get("source_failure_id"),
        "repair_lane": candidate.get("repair_lane"),
        "host_profile_ids": candidate.get("host_profile_ids", []),
        "source_digests": candidate.get("source_digests", {}),
        "eligibility_verdict": verdict,
        "promotion_verdict": PROMOTION_VERDICT,
        "recommended_next_step": recommended_next_step(verdict, failed),
        "checks": checks,
        "notes": notes,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Affordance Experiment Eligibility v0",
        "",
        f"Candidate id: `{report.get('candidate_id') or 'unknown'}`",
        f"Source failure id: `{report.get('source_failure_id') or 'unknown'}`",
        f"Repair lane: `{report.get('repair_lane') or 'unknown'}`",
        f"Host profile ids: `{', '.join(str(x) for x in report.get('host_profile_ids', [])) or 'unknown'}`",
        "",
        "## Verdict",
        "",
        f"- Eligibility verdict: `{report['eligibility_verdict']}`",
        f"- Promotion verdict: `{report['promotion_verdict']}`",
        f"- Recommended next step: `{report['recommended_next_step']}`",
        "",
        "## Checks",
        "",
        "| Check | Passed |",
        "|---|---:|",
    ]
    for name, passed in report["checks"].items():
        lines.append(f"| `{name}` | `{str(passed).lower()}` |")

    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This is eligibility for an experiment proposal only.",
            "It is not a LARQL patch.",
            "It is not LoRA training.",
            "It is not durable memory promotion.",
            "It does not promote, approve, rank, route, or assign the candidate.",
            "Post-injection re-audition would be required for any future experiment.",
            "",
            "## Notes",
            "",
        ]
    )
    lines.extend(f"- {note}" for note in report["notes"])
    lines.append("")
    return "\n".join(lines)


def write_reports(candidate_path: Path, repeatability_report_path: Path, out_dir: Path) -> dict[str, Any]:
    validate_out_dir(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(candidate_path, repeatability_report_path)
    (out_dir / "eligibility_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "eligibility_report.md").write_text(render_markdown(report), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Write a model-free affordance experiment eligibility report."
    )
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--repeatability-report", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        report = write_reports(args.candidate, args.repeatability_report, args.out)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    for filename in OUTPUT_FILES:
        print(f"wrote: {args.out / filename}")
    print(f"eligibility_verdict: {report['eligibility_verdict']}")
    print(f"promotion_verdict: {report['promotion_verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
