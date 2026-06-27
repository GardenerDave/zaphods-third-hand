"""Model-free LARQL affordance patch probe scaffold.

This helper classifies a host-specific failure note into draft repair lanes and
writes reviewable scaffold files. It does not call models, import LARQL, build
indexes, train adapters, mutate weights, or promote artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REQUIRED_HOST_PROFILE_KEYS = {
    "host_id",
    "display_name",
    "profile_version",
    "last_verified",
    "evidence_status",
    "hardware",
    "os",
    "known_good_paths",
    "known_bad_paths",
    "preferred_roles",
    "constraints",
    "staleness_policy",
    "notes",
}

OUTPUT_FILES = (
    "affordance_patch_candidate.json",
    "classification_report.md",
    "probe_plan.md",
)


def read_json(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise ValueError(f"{p}: missing input file")
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{p}: invalid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{p}: expected a JSON object")
    return payload


def validate_host_profile(profile: dict[str, Any], *, path: str | Path) -> None:
    missing = sorted(REQUIRED_HOST_PROFILE_KEYS - set(profile))
    if missing:
        raise ValueError(f"{path}: missing host profile keys: {', '.join(missing)}")

    if not isinstance(profile["host_id"], str) or not profile["host_id"].strip():
        raise ValueError(f"{path}: host_id must be a non-empty string")

    for key in ("known_good_paths", "known_bad_paths", "preferred_roles", "constraints"):
        if not isinstance(profile[key], list):
            raise ValueError(f"{path}: {key} must be a list")


def flatten_json_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return "\n".join(flatten_json_text(value[key]) for key in sorted(value))
    if isinstance(value, list):
        return "\n".join(flatten_json_text(item) for item in value)
    return str(value)


def read_failure_note(path: str | Path) -> str:
    p = Path(path)
    if not p.exists():
        raise ValueError(f"{p}: missing input file")
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() == ".json":
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{p}: invalid JSON: {exc.msg}") from exc
        return flatten_json_text(payload)
    return text


def normalized_text(profile: dict[str, Any], note: str) -> str:
    return (
        json.dumps(profile, sort_keys=True, ensure_ascii=False)
        + "\n"
        + note
    ).lower()


def classify_failure(profile: dict[str, Any], failure_note: str) -> dict[str, str]:
    text = normalized_text(profile, failure_note)
    evidence_status = str(profile.get("evidence_status", "")).lower()
    host_id = str(profile.get("host_id", "unknown_host"))

    if "unknown" in evidence_status or "insufficient_host_evidence" in text:
        return {
            "repair_lane": "review_only",
            "failure_summary": "Insufficient host-profile evidence for an affordance patch.",
            "affordance_claim": "No durable host affordance can be claimed yet.",
            "negative_constraint": "Do not reuse another host's constraints for this host.",
            "positive_alternative": "Collect or refresh the host profile before repair selection.",
            "staleness_risk": "All host-specific facts are unverified.",
            "scope": f"{host_id}; review-only until host evidence exists.",
        }

    if any(word in text for word in ("cuda", "nvidia", "gpu")) and any(
        word in text for word in ("no_cuda", "rx 580", "amd", "polaris")
    ):
        return {
            "repair_lane": "larql_plus_lora_candidate",
            "failure_summary": "CUDA/NVIDIA-specific path conflicts with host GPU affordance evidence.",
            "affordance_claim": "This host should not receive CUDA-first repair guidance unless the profile is reverified.",
            "negative_constraint": "Avoid CUDA-only commands as the first repair path for this host profile.",
            "positive_alternative": "Inspect host profile, then choose CPU fallback or OpenCL/ROCm investigation.",
            "staleness_risk": "GPU, driver, or runtime changes can invalidate this claim.",
            "scope": f"{host_id} only.",
        }

    if any(word in text for word in ("avx2", "illegal instruction", "cpu flag")) and (
        "no_avx2" in text or "not_available" in text
    ):
        return {
            "repair_lane": "larql_candidate",
            "failure_summary": "AVX2-required artifact conflicts with host CPU affordance evidence.",
            "affordance_claim": "This host should not receive AVX2-required binaries unless CPU flags are reverified.",
            "negative_constraint": "Avoid AVX2-required binaries for this host profile.",
            "positive_alternative": "Select a non-AVX2 build or inspect CPU flags before selecting artifacts.",
            "staleness_risk": "Hardware, virtualization, or binary build target changes can invalidate this claim.",
            "scope": f"{host_id} only.",
        }

    if any(word in text for word in ("json", "schema", "format", "instruction")):
        return {
            "repair_lane": "lora_candidate",
            "failure_summary": "Failure appears procedural or behavioral rather than host-affordance-specific.",
            "affordance_claim": "No host-specific LARQL affordance claim is established.",
            "negative_constraint": "Do not encode mutable host facts into weights.",
            "positive_alternative": "Consider supervised LoRA/SFT curriculum only after reviewed examples exist.",
            "staleness_risk": "Behavioral evidence may not transfer across workflows.",
            "scope": f"{host_id}; behavior lane only.",
        }

    if any(word in text for word in ("stale", "missing profile", "profile missing")):
        return {
            "repair_lane": "host_profile_only",
            "failure_summary": "Failure suggests the host profile needs update or clarification.",
            "affordance_claim": "Host profile must be refreshed before patch or training decisions.",
            "negative_constraint": "Do not create LARQL or LoRA candidates from stale host facts.",
            "positive_alternative": "Refresh host profile evidence and rerun classification.",
            "staleness_risk": "Host facts are stale or incomplete.",
            "scope": f"{host_id}; profile maintenance only.",
        }

    return {
        "repair_lane": "review_only",
        "failure_summary": "Failure evidence is insufficient for a repair-lane claim.",
        "affordance_claim": "No durable affordance claim established.",
        "negative_constraint": "Do not create patch or training candidates from ambiguous evidence.",
        "positive_alternative": "Collect more failure evidence and rerun classification.",
        "staleness_risk": "Unknown until evidence is improved.",
        "scope": f"{host_id}; review-only.",
    }


def stable_id(*parts: str) -> str:
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"larql_affordance_candidate_{digest}"


def default_do_not_generalize(profile: dict[str, Any]) -> list[str]:
    return [
        "unknown hosts",
        "other host profiles without matching evidence",
        "future hardware states after profile staleness",
        f"hosts other than {profile['host_id']}",
    ]


def prompt_set(profile: dict[str, Any], classification: dict[str, str]) -> tuple[list[str], list[str]]:
    host_id = profile["host_id"]
    lane = classification["repair_lane"]
    probe_prompts = [
        f"A repair failed on {host_id}. Which host profile fact should be inspected first?",
        f"For {host_id}, what negative constraint applies to this failure?",
        f"What safe alternative should be tried for {host_id} before generalizing this repair?",
    ]
    regression_prompts = [
        f"Should this {lane} constraint be applied to an unknown host?",
        f"Should this {lane} constraint be applied to a different host profile without matching evidence?",
        f"If {host_id} hardware changes, what evidence must be refreshed before using this candidate?",
    ]
    return probe_prompts, regression_prompts


def build_candidate(
    *,
    host_profile: dict[str, Any],
    host_profile_path: Path,
    failure_note_path: Path,
    failure_note_text: str,
) -> dict[str, Any]:
    classification = classify_failure(host_profile, failure_note_text)
    probe_prompts, regression_prompts = prompt_set(host_profile, classification)
    lane = classification["repair_lane"]

    return {
        "candidate_id": stable_id(
            host_profile["host_id"],
            failure_note_path.as_posix(),
            failure_note_text,
            lane,
        ),
        "source_failure_id": failure_note_path.stem,
        "host_profile_ids": [host_profile["host_id"]],
        "source_files": {
            "host_profile": host_profile_path.as_posix(),
            "failure_note": failure_note_path.as_posix(),
        },
        "failure_summary": classification["failure_summary"],
        "repair_lane": lane,
        "affordance_claim": classification["affordance_claim"],
        "negative_constraint": classification["negative_constraint"],
        "positive_alternative": classification["positive_alternative"],
        "staleness_risk": classification["staleness_risk"],
        "scope": classification["scope"],
        "do_not_generalize_to": default_do_not_generalize(host_profile),
        "larql_lql_draft": {
            "status": "draft_not_applied",
            "draft": (
                f"HOST {host_profile['host_id']}: {classification['negative_constraint']}"
                if lane in {"larql_candidate", "larql_plus_lora_candidate"}
                else ""
            ),
        },
        "lora_training_candidate": {
            "status": (
                "draft_candidate"
                if lane in {"lora_candidate", "larql_plus_lora_candidate"}
                else "not_primary_lane"
            ),
            "rationale": (
                "Behavioral lane may teach the model to ask which host/workflow context applies."
                if lane in {"lora_candidate", "larql_plus_lora_candidate"}
                else "Primary evidence is host affordance or review-only."
            ),
        },
        "probe_prompts": probe_prompts,
        "regression_prompts": regression_prompts,
        "review_status": "draft",
        "promotion_status": "needs_probe",
        "safety_boundary": (
            "Draft candidate only. Not an applied LARQL patch, not training data, "
            "not accepted, and not promotion evidence by itself."
        ),
    }


def markdown_list(values: list[str]) -> list[str]:
    return [f"- {value}" for value in values]


def render_probe_plan(candidate: dict[str, Any]) -> str:
    lines = [
        "# LARQL Affordance Probe Plan",
        "",
        f"Candidate: `{candidate['candidate_id']}`",
        f"Repair lane: `{candidate['repair_lane']}`",
        "Status: draft / needs_probe",
        "",
        "## Probe Prompts",
        "",
        *markdown_list(candidate["probe_prompts"]),
        "",
        "## Regression Prompts",
        "",
        *markdown_list(candidate["regression_prompts"]),
        "",
        "## Boundary",
        "",
        "These prompts are review material. They do not apply a LARQL patch, train a LoRA adapter, or promote an artifact.",
        "",
    ]
    return "\n".join(lines)


def render_classification_report(candidate: dict[str, Any]) -> str:
    lines = [
        "# LARQL Affordance Classification Report",
        "",
        f"Candidate: `{candidate['candidate_id']}`",
        f"Repair lane: `{candidate['repair_lane']}`",
        f"Review status: `{candidate['review_status']}`",
        f"Promotion status: `{candidate['promotion_status']}`",
        "",
        "## Failure Summary",
        "",
        candidate["failure_summary"],
        "",
        "## Affordance Claim",
        "",
        candidate["affordance_claim"],
        "",
        "## Negative Constraint",
        "",
        candidate["negative_constraint"],
        "",
        "## Positive Alternative",
        "",
        candidate["positive_alternative"],
        "",
        "## Do Not Generalize To",
        "",
        *markdown_list(candidate["do_not_generalize_to"]),
        "",
        "## Safety Boundary",
        "",
        candidate["safety_boundary"],
        "",
    ]
    return "\n".join(lines)


def validate_out_dir(path: Path) -> None:
    if any(part == ".." for part in path.parts):
        raise ValueError(f"{path}: output directory must not contain '..'")
    if path.exists() and not path.is_dir():
        raise ValueError(f"{path}: output path exists and is not a directory")


def write_outputs(out_dir: Path, candidate: dict[str, Any]) -> None:
    validate_out_dir(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    candidate_path = out_dir / "affordance_patch_candidate.json"
    report_path = out_dir / "classification_report.md"
    plan_path = out_dir / "probe_plan.md"

    candidate_path.write_text(
        json.dumps(candidate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(render_classification_report(candidate), encoding="utf-8")
    plan_path.write_text(render_probe_plan(candidate), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Classify host-specific failures into draft affordance repair lanes."
    )
    parser.add_argument("--host-profile", required=True, type=Path)
    parser.add_argument("--failure-note", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        host_profile = read_json(args.host_profile)
        validate_host_profile(host_profile, path=args.host_profile)
        failure_note = read_failure_note(args.failure_note)
        candidate = build_candidate(
            host_profile=host_profile,
            host_profile_path=args.host_profile,
            failure_note_path=args.failure_note,
            failure_note_text=failure_note,
        )
        write_outputs(args.out, candidate)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    for filename in OUTPUT_FILES:
        print(f"wrote: {args.out / filename}")
    print(f"repair_lane: {candidate['repair_lane']}")
    print("status: draft / needs_probe")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
