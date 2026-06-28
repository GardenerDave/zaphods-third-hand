"""Draft a bounded repair packet from a LARQL model response review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_larql_model_response_repair_packet.v0"
PACKET_STATUS = "packet_only"
PACKET_VERDICT = "ready_for_larql_model_response_repair_review"
ALLOWED_NEXT_STEP = "review_larql_model_response_repair_packet"
PROMOTION_VERDICT = "hold_pending_explicit_experiment_approval"
OUTPUT_FILES = ("larql_model_response_repair_packet.json", "larql_model_response_repair_packet.md")

ALLOWED_FILES = [
    "local_harness/affordance_larql_model_context_packet.py",
    "local_harness/affordance_larql_model_response_probe.py",
]


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


def review_ready(review: dict[str, Any]) -> bool:
    return all(
        [
            review.get("report_type") == "affordance_larql_model_response_review.v0",
            review.get("review_verdict") == "larql_model_response_review_requires_repair",
            review.get("allowed_next_step") == "draft_larql_model_response_repair_packet",
            review.get("cuda_block_pass") is True,
            review.get("durable_memory_written") is False,
            review.get("candidate_promoted") is False,
            review.get("lora_training_started") is False,
            review.get("model_weights_mutated") is False,
            bool(review.get("candidate_id")),
            bool(review.get("candidate_digest")),
            bool(review.get("rule_id")),
            bool(review.get("source_failure_id")),
        ]
    )


def review_needs_instruction_skeleton_repair(review: dict[str, Any]) -> bool:
    return (
        review_ready(review)
        and "missing_lm_studio_specific_recommendation" in review.get("model_semantic_failures", [])
        and "missing_reverify_or_current_evidence_scope" in review.get("model_semantic_failures", [])
        and not review.get("scorer_false_positives")
        and not review.get("scorer_false_negatives")
    )


def build_proposed_repairs() -> list[dict[str, Any]]:
    return [
        {
            "target_file": "local_harness/affordance_larql_model_context_packet.py",
            "repair_type": "instruction_skeleton_tightening",
            "required_changes": [
                "Replace advisory wording with a required answer skeleton.",
                "The model response must include these exact lines or equivalent fields:",
                "1. \"No, do not install NVIDIA CUDA on this RX580/no_cuda host.\"",
                "2. \"Use the LM Studio OpenAI-compatible endpoint.\"",
                "3. \"This recommendation is scoped to the current host/profile/GPU/endpoint/digest evidence.\"",
                "4. \"Reverify if host, GPU, driver, profile, endpoint, or digest evidence changes.\"",
                "The model must not recommend OpenAI Inference API, Hugging Face Inference API, generic cloud services, PyTorch with a different compatible GPU, or replacing hardware as the primary answer.",
            ],
        },
        {
            "target_file": "local_harness/affordance_larql_model_response_probe.py",
            "repair_type": "response_scorer_drift_tightening",
            "required_changes": [
                "Normalize markdown emphasis before detecting negated CUDA install language.",
                "Treat `**not** install NVIDIA CUDA`, `do not install NVIDIA CUDA`, and `should not install NVIDIA CUDA` as rejecting CUDA install recommendations.",
                "Require `LM Studio` explicitly for `recommends_lm_studio_endpoint`.",
                "Do not count generic `OpenAI-compatible endpoint` alone as LM Studio-specific.",
                "Do not count OpenAI Inference API or Hugging Face Inference API as LM Studio-specific.",
                "Treat `cloud-based service`, `compatible GPU`, and `PyTorch with a compatible GPU` as endpoint/path drift when LM Studio is absent.",
            ],
        },
    ]


def disallowed_actions() -> list[str]:
    return [
        "call_model",
        "apply_repair",
        "write_durable_memory",
        "promote_candidate",
        "train_lora_adapter",
        "mutate_model_weights",
        "modify_runtime_rule",
        "commit_or_push",
    ]


def build_report(review: dict[str, Any], checks: dict[str, bool]) -> dict[str, Any]:
    ready = review_ready(review)
    repair_ready = review_needs_instruction_skeleton_repair(review)
    return {
        "report_type": REPORT_TYPE,
        "packet_status": PACKET_STATUS,
        "packet_verdict": PACKET_VERDICT if ready and repair_ready else "invalid_input",
        "allowed_next_step": ALLOWED_NEXT_STEP if ready and repair_ready else "repair_or_reverify_larql_model_response_review",
        "candidate_id": review.get("candidate_id"),
        "source_failure_id": review.get("source_failure_id"),
        "rule_id": review.get("rule_id"),
        "candidate_digest": review.get("candidate_digest"),
        "proposed_repairs": build_proposed_repairs() if ready and repair_ready else [],
        "allowed_files": ALLOWED_FILES,
        "disallowed_actions": disallowed_actions(),
        "durable_memory_authorized": False,
        "candidate_promotion_authorized": False,
        "lora_training_authorized": False,
        "model_weight_mutation_authorized": False,
        "promotion_verdict": PROMOTION_VERDICT,
        "checks": checks,
        "notes": [],
    }


def render_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# LARQL Model Response Repair Packet v0",
            "",
            f"Candidate id: `{report.get('candidate_id') or 'unknown'}`",
            f"Source failure id: `{report.get('source_failure_id') or 'unknown'}`",
            f"Rule id: `{report.get('rule_id') or 'unknown'}`",
            f"Packet verdict: `{report['packet_verdict']}`",
            f"Allowed next step: `{report['allowed_next_step']}`",
            "",
            "This is packet evidence only.",
            "No repair is applied.",
            "No durable memory is written.",
            "No candidate promotion is granted.",
            "No LoRA training is authorized.",
            "No model weights are mutated.",
        ]
    )


def write_reports(review_path: Path, out_dir: Path) -> dict[str, Any]:
    validate_out_dir(out_dir)
    review, review_checks, review_notes = read_json_object(review_path, "review")
    checks = {**review_checks, **{f"review_{k}": v for k, v in review.items() if isinstance(v, bool)}}
    report = build_report(review, checks)
    if report["packet_verdict"] == "ready_for_larql_model_response_repair_review":
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / OUTPUT_FILES[0]).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (out_dir / OUTPUT_FILES[1]).write_text(render_markdown(report) + "\n", encoding="utf-8")
        report["notes"] = review_notes
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_reports(args.review, args.out)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
