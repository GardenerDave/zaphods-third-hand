"""Write a model-free dogfood report for one affordance patch candidate.

This helper reviews the shape of a generated LARQL affordance candidate. It
does not run LARQL, call models, train adapters, mutate weights, or promote
artifacts.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_dogfood_report.v0"
PROMOTION_VERDICT = "hold_pending_probe"
NEXT_STEP = "probe_before_larql_or_lora_promotion"
REQUIRED_FIELDS = {
    "candidate_id",
    "host_profile_ids",
    "source_failure_id",
    "repair_lane",
    "review_status",
    "promotion_status",
    "host_affordance_context",
    "positive_alternative",
    "negative_constraint",
    "do_not_generalize_to",
    "regression_prompts",
    "source_digests",
    "source_files",
}
OUTPUT_FILES = ("dogfood_report.md", "dogfood_report.json")
HEX_64 = re.compile(r"^[0-9a-f]{64}$")


def read_candidate(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise ValueError(f"{p}: missing candidate file")
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{p}: invalid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{p}: candidate must be a JSON object")
    validate_candidate(payload)
    return payload


def validate_candidate(candidate: dict[str, Any]) -> None:
    missing = sorted(REQUIRED_FIELDS - set(candidate))
    if missing:
        raise ValueError(f"candidate missing required fields: {', '.join(missing)}")

    if not isinstance(candidate["host_profile_ids"], list) or not candidate["host_profile_ids"]:
        raise ValueError("candidate host_profile_ids must be a non-empty list")

    context = candidate["host_affordance_context"]
    if not isinstance(context, dict):
        raise ValueError("candidate host_affordance_context must be an object")
    for key in ("known_good_paths", "known_bad_paths", "constraints"):
        if not isinstance(context.get(key), list):
            raise ValueError(f"candidate host_affordance_context.{key} must be a list")

    for key in ("do_not_generalize_to", "regression_prompts"):
        if not isinstance(candidate[key], list):
            raise ValueError(f"candidate {key} must be a list")

    for key in ("source_digests", "source_files"):
        if not isinstance(candidate[key], dict):
            raise ValueError(f"candidate {key} must be an object")


def text_contains_any(text: str, values: list[Any]) -> bool:
    lowered = text.lower()
    return any(str(value).strip().lower() in lowered for value in values if str(value).strip())


def classification_verdict(candidate: dict[str, Any]) -> str:
    if (
        candidate.get("repair_lane")
        and candidate.get("promotion_status") == "needs_probe"
        and candidate.get("review_status") == "draft"
    ):
        return "pass"
    return "fail"


def specificity_verdict(candidate: dict[str, Any]) -> str:
    context = candidate["host_affordance_context"]
    known_good = context["known_good_paths"]
    known_bad = context["known_bad_paths"]
    constraints = context["constraints"]
    positive = str(candidate.get("positive_alternative", ""))
    negative = str(candidate.get("negative_constraint", ""))

    if not known_good or not known_bad or not constraints:
        return "fail"
    if not (text_contains_any(positive, known_good) or "host" in positive.lower()):
        return "needs_tightening"
    if not (text_contains_any(negative, known_bad) or text_contains_any(negative, constraints)):
        return "needs_tightening"
    return "pass"


def split_host_safety_verdict(candidate: dict[str, Any]) -> str:
    prompts = "\n".join(str(prompt) for prompt in candidate["regression_prompts"]).lower()
    do_not_generalize_to = candidate["do_not_generalize_to"]

    checks = [
        bool(do_not_generalize_to),
        "unknown host" in prompts,
        "different host" in prompts or "different host profile" in prompts,
        ("stale" in prompts or "reverify" in prompts or "hardware changes" in prompts),
        "split workflow" in prompts or "host confusion" in prompts or "borrowing" in prompts,
    ]
    if all(checks):
        return "pass"
    if any(checks):
        return "needs_tightening"
    return "fail"


def provenance_verdict(candidate: dict[str, Any]) -> str:
    digests = candidate["source_digests"]
    files = candidate["source_files"]
    if not HEX_64.fullmatch(str(digests.get("host_profile_sha256", ""))):
        return "fail"
    if not HEX_64.fullmatch(str(digests.get("failure_note_sha256", ""))):
        return "fail"
    if not digests.get("classifier_version"):
        return "fail"
    if not files.get("host_profile") or not files.get("failure_note"):
        return "fail"
    return "pass"


def build_report(candidate: dict[str, Any]) -> dict[str, Any]:
    report = {
        "report_type": REPORT_TYPE,
        "candidate_id": candidate["candidate_id"],
        "host_profile_ids": candidate["host_profile_ids"],
        "source_failure_id": candidate["source_failure_id"],
        "repair_lane": candidate["repair_lane"],
        "review_status": "dogfood_reviewed",
        "classification_verdict": classification_verdict(candidate),
        "specificity_verdict": specificity_verdict(candidate),
        "split_host_safety_verdict": split_host_safety_verdict(candidate),
        "provenance_verdict": provenance_verdict(candidate),
        "promotion_verdict": PROMOTION_VERDICT,
        "recommended_next_step": NEXT_STEP,
        "notes": [
            "Model-free dogfood report.",
            "Candidate remains unaccepted and unpromoted.",
            "Probe before considering LARQL or LoRA promotion.",
        ],
    }
    return report


def markdown_list(values: list[Any]) -> list[str]:
    return [f"- {value}" for value in values]


def render_markdown(candidate: dict[str, Any], report: dict[str, Any]) -> str:
    context = candidate["host_affordance_context"]
    digests = candidate["source_digests"]
    lines = [
        "# Affordance Dogfood Report v0",
        "",
        f"Candidate id: `{report['candidate_id']}`",
        f"Source failure id: `{report['source_failure_id']}`",
        f"Host profile ids: `{', '.join(report['host_profile_ids'])}`",
        f"Repair lane: `{report['repair_lane']}`",
        "",
        "## Verdicts",
        "",
        "| Check | Verdict |",
        "|---|---|",
        f"| Classification | `{report['classification_verdict']}` |",
        f"| Specificity | `{report['specificity_verdict']}` |",
        f"| Split-host safety | `{report['split_host_safety_verdict']}` |",
        f"| Provenance | `{report['provenance_verdict']}` |",
        f"| Promotion | `{report['promotion_verdict']}` |",
        "",
        "## Host Affordance Context",
        "",
        "Known-good paths:",
        *markdown_list(context["known_good_paths"]),
        "",
        "Known-bad paths:",
        *markdown_list(context["known_bad_paths"]),
        "",
        "Constraints:",
        *markdown_list(context["constraints"]),
        "",
        "## Source Digests",
        "",
        f"- Host profile SHA-256: `{digests.get('host_profile_sha256')}`",
        f"- Failure note SHA-256: `{digests.get('failure_note_sha256')}`",
        f"- Classifier version: `{digests.get('classifier_version')}`",
        "",
        "## Recommended Next Step",
        "",
        report["recommended_next_step"],
        "",
        "## Safety Boundary",
        "",
        "This is not an applied LARQL patch, not LoRA training data, and not promotion evidence by itself.",
        "The candidate remains not accepted and unpromoted. Promotion is held pending probes.",
        "",
    ]
    return "\n".join(lines)


def validate_out_dir(path: Path) -> None:
    if any(part == ".." for part in path.parts):
        raise ValueError(f"{path}: output directory must not contain '..'")
    if path.exists() and not path.is_dir():
        raise ValueError(f"{path}: output path exists and is not a directory")


def write_report(candidate_path: str | Path, out_dir: str | Path) -> dict[str, Any]:
    candidate = read_candidate(candidate_path)
    report = build_report(candidate)
    out = Path(out_dir)
    validate_out_dir(out)
    out.mkdir(parents=True, exist_ok=True)

    json_path = out / "dogfood_report.json"
    md_path = out / "dogfood_report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(candidate, report), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Write a model-free dogfood report for one affordance candidate."
    )
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        report = write_report(args.candidate, args.out)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    for filename in OUTPUT_FILES:
        print(f"wrote: {args.out / filename}")
    print(f"candidate_id: {report['candidate_id']}")
    print(f"promotion_verdict: {report['promotion_verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
