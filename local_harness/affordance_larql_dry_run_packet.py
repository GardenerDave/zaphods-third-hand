"""Draft a model-free LARQL dry-run packet for an accepted baseline candidate.

This helper reads a baseline result report, post-run audit, and candidate JSON
then writes an inert dry-run packet for later reviewer decision. It does not
call a model, apply LARQL, train LoRA, mutate durable memory, or promote the
candidate.
"""

from __future__ import annotations

import argparse
import json
import hashlib
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_larql_dry_run_packet.v0"
PACKET_STATUS = "packet_only"
PACKET_VERDICT = "ready_for_larql_dry_run_review"
ALLOWED_NEXT_STEP = "review_larql_dry_run_packet"
PROMOTION_VERDICT = "hold_pending_explicit_experiment_approval"
OUTPUT_FILES = ("larql_dry_run_packet.json", "larql_dry_run_packet.md")


def validate_out_dir(path: Path) -> None:
    if any(part == ".." for part in path.parts):
        raise ValueError(f"{path}: output directory must not contain '..'")
    if path.exists() and not path.is_dir():
        raise ValueError(f"{path}: output path exists and is not a directory")


def read_json_object(path: Path, label: str) -> tuple[dict[str, Any], dict[str, bool], list[str]]:
    checks = {f"{label}_exists": path.exists(), f"{label}_parses": False}
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


def audit_passes(text: str) -> bool:
    return "audit_pass" in text.lower()


def read_text_file(path: Path, label: str) -> tuple[str, dict[str, bool], list[str]]:
    checks = {f"{label}_exists": path.exists()}
    notes: list[str] = []
    if not checks[f"{label}_exists"]:
        notes.append(f"{label} missing: {path}")
        return "", checks, notes
    return path.read_text(encoding="utf-8"), checks, notes


def build_checks(
    candidate: dict[str, Any],
    baseline_result: dict[str, Any],
    audit_text: str,
    candidate_checks: dict[str, bool],
    baseline_checks: dict[str, bool],
    audit_checks: dict[str, bool],
) -> dict[str, bool]:
    checks = {}
    checks.update(candidate_checks)
    checks.update(baseline_checks)
    checks.update(audit_checks)
    checks.update(
        {
            "selected_lane_baseline": baseline_result.get("selected_lane")
            == "baseline_prompt_context_only",
            "baseline_result_verdict_pass": baseline_result.get("result_verdict")
            == "baseline_pass",
            "baseline_audit_verdict_pass": audit_passes(audit_text),
            "promotion_held": baseline_result.get("promotion_verdict")
            == PROMOTION_VERDICT,
            "candidate_id_matches": candidate.get("candidate_id") == baseline_result.get("candidate_id"),
            "candidate_digest_matches": sha256_hex(candidate) == baseline_result.get("candidate_digest"),
        }
    )
    return checks


def packet_verdict(checks: dict[str, bool]) -> str:
    required = [
        "candidate_exists",
        "candidate_parses",
        "baseline_result_exists",
        "baseline_result_parses",
        "post_run_audit_exists",
        "selected_lane_baseline",
        "baseline_result_verdict_pass",
        "baseline_audit_verdict_pass",
        "promotion_held",
        "candidate_id_matches",
        "candidate_digest_matches",
    ]
    if not all(checks.get(name, False) for name in required):
        return "invalid_input"
    return PACKET_VERDICT


def larql_rule_draft() -> dict[str, Any]:
    return {
        "rule_id": "navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0",
        "status": "draft_not_applied",
        "applies_when": [
            "active execution host matches navigator_desktop or matching host evidence/profile constraints",
            "host constraint includes no_cuda",
            "known-bad path includes CUDA-only setup on RX580",
        ],
        "blocks_or_warns_on": [
            "CUDA-only setup",
            "NVIDIA/CUDA troubleshooting path on RX580/no_cuda host",
        ],
        "recommends": [
            "LM Studio OpenAI-compatible endpoint for small-model GPU-backed workflow",
        ],
        "requires_reverify_when": [
            "active host is unknown",
            "local host and remote host differ",
            "hardware, GPU, driver, endpoint, or host profile may have changed",
            "candidate digest or source digests do not match",
        ],
    }


def build_packet(candidate_path: Path, baseline_result_path: Path, audit_path: Path) -> dict[str, Any]:
    candidate, candidate_checks, candidate_notes = read_json_object(candidate_path, "candidate")
    baseline_result, baseline_checks, baseline_notes = read_json_object(
        baseline_result_path, "baseline_result"
    )
    audit_text, audit_checks, audit_notes = read_text_file(audit_path, "post_run_audit")
    checks = build_checks(
        candidate,
        baseline_result,
        audit_text,
        candidate_checks,
        baseline_checks,
        audit_checks,
    )
    verdict = packet_verdict(checks)
    notes = [
        *candidate_notes,
        *baseline_notes,
        *audit_notes,
        "Dry-run packet only; no LARQL patch is applied.",
        "No durable memory, LoRA training, or candidate promotion is authorized.",
    ]
    candidate_digest = str(baseline_result.get("candidate_digest") or "")
    source_failure_id = str(candidate.get("source_failure_id") or baseline_result.get("source_failure_id") or "")
    return {
        "report_type": REPORT_TYPE,
        "packet_status": PACKET_STATUS,
        "packet_verdict": verdict,
        "allowed_next_step": ALLOWED_NEXT_STEP,
        "candidate_id": candidate.get("candidate_id") or baseline_result.get("candidate_id"),
        "source_failure_id": source_failure_id,
        "candidate_digest": candidate_digest,
        "candidate_digest_verified": checks.get("candidate_digest_matches", False),
        "baseline_result_verdict": baseline_result.get("result_verdict"),
        "baseline_audit_verdict": "audit_pass" if audit_passes(audit_text) else "unknown",
        "promotion_verdict": PROMOTION_VERDICT,
        "larql_application_authorized": False,
        "candidate_promotion_authorized": False,
        "durable_memory_authorized": False,
        "lora_training_authorized": False,
        "selected_lane": baseline_result.get("selected_lane"),
        "larql_rule_draft": larql_rule_draft(),
        "checks": checks,
        "notes": notes,
    }


def render_markdown(packet: dict[str, Any]) -> str:
    applies_when = packet["larql_rule_draft"]["applies_when"]
    blocks_or_warns_on = packet["larql_rule_draft"]["blocks_or_warns_on"]
    recommends = packet["larql_rule_draft"]["recommends"]
    requires_reverify_when = packet["larql_rule_draft"]["requires_reverify_when"]
    return "\n".join(
        [
            "# LARQL Dry-Run Packet v0",
            "",
            f"Candidate id: `{packet.get('candidate_id') or 'unknown'}`",
            f"Source failure id: `{packet.get('source_failure_id') or 'unknown'}`",
            f"Packet verdict: `{packet['packet_verdict']}`",
            f"Allowed next step: `{packet['allowed_next_step']}`",
            f"Promotion verdict: `{packet['promotion_verdict']}`",
            "",
            "This is a dry-run packet only.",
            "It is not an applied LARQL patch.",
            "It is not durable memory.",
            "It is not LoRA training.",
            "It is not promotion.",
            "It exists to let a reviewer decide whether a later LARQL apply packet should be drafted.",
            "",
            "## Draft LARQL Rule",
            "",
            f"- Rule id: `{packet['larql_rule_draft']['rule_id']}`",
            f"- Status: `{packet['larql_rule_draft']['status']}`",
            "- Applies when:",
            *[f"  - {item}" for item in applies_when],
            "- Blocks or warns on:",
            *[f"  - {item}" for item in blocks_or_warns_on],
            "- Recommends:",
            *[f"  - {item}" for item in recommends],
            "- Requires reverify when:",
            *[f"  - {item}" for item in requires_reverify_when],
            "",
            "## Boundary",
            "",
            "This packet does not authorize LARQL application, LoRA training, durable memory, or candidate promotion.",
        ]
    )


def write_reports(candidate_path: Path, baseline_result_path: Path, audit_path: Path, out_dir: Path) -> dict[str, Any]:
    validate_out_dir(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    packet = build_packet(candidate_path, baseline_result_path, audit_path)
    (out_dir / OUTPUT_FILES[0]).write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / OUTPUT_FILES[1]).write_text(render_markdown(packet) + "\n", encoding="utf-8")
    return packet


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--baseline-result", required=True, type=Path)
    parser.add_argument("--post-run-audit", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_reports(args.candidate, args.baseline_result, args.post_run_audit, args.out)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
