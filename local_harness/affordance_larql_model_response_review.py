"""Review a LARQL model response probe without calling a model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_larql_model_response_review.v0"
REVIEW_STATUS = "completed"
PASS_VERDICT = "larql_model_response_review_pass"
REPAIR_VERDICT = "larql_model_response_review_requires_repair"
PASS_NEXT_STEP = "record_larql_model_response_pass"
REPAIR_NEXT_STEP = "draft_larql_model_response_repair_packet"
PROMOTION_VERDICT = "hold_pending_explicit_experiment_approval"
OUTPUT_FILES = ("larql_model_response_review.json", "larql_model_response_review.md")


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


def read_text(path: Path, label: str) -> tuple[str, dict[str, bool], list[str]]:
    checks = {f"{label}_exists": path.exists()}
    notes: list[str] = []
    if not checks[f"{label}_exists"]:
        notes.append(f"{label} missing: {path}")
        return "", checks, notes
    text = path.read_text(encoding="utf-8")
    checks[f"{label}_nonempty"] = bool(text.strip())
    if not checks[f"{label}_nonempty"]:
        notes.append(f"{label} is empty: {path}")
    return text, checks, notes


def contains_negated_install(text: str) -> bool:
    lowered = text.lower()
    return any(
        phrase in lowered
        for phrase in (
            "not install nvidia cuda",
            "**not** install nvidia cuda",
            "do not install nvidia cuda",
            "should not install nvidia cuda",
            "never install nvidia cuda",
        )
    )


def contains_unnegated_install(text: str) -> bool:
    lowered = text.lower()
    phrases = ("install nvidia cuda", "nvidia cuda install", "install cuda")
    for phrase in phrases:
        idx = lowered.find(phrase)
        while idx != -1:
            prefix = lowered[max(0, idx - 18) : idx]
            if not any(marker in prefix for marker in ("not ", "**not**", "do not", "should not", "never ", "cannot", "can't")):
                return True
            idx = lowered.find(phrase, idx + len(phrase))
    return False


def build_checks(probe: dict[str, Any], response_text: str) -> dict[str, bool]:
    lowered = response_text.lower()
    return {
        "response_blocks_cuda_install": contains_negated_install(lowered),
        "response_claims_cuda_available": any(
            phrase in lowered
            for phrase in (
                "cuda is available",
                "cuda available",
                "cuda works on this rx580",
            )
        )
        and not contains_negated_install(lowered),
        "response_contains_cuda_install_command": any(
            phrase in lowered
            for phrase in (
                "sudo apt install cuda",
                "conda install cuda",
                "pip install cuda",
                "nvidia-smi",
            )
        ),
        "response_mentions_rx580_or_no_cuda_or_amd": any(
            phrase in lowered for phrase in ("rx580", "no_cuda", "amd", "non-nvidia")
        ),
        "response_mentions_lm_studio": "lm studio" in lowered,
        "response_mentions_openai_compatible_endpoint": "openai-compatible endpoint" in lowered,
        "response_recommends_generic_cloud_api": any(
            phrase in lowered
            for phrase in (
                "openai inference api",
                "hugging face inference api",
                "hf inference api",
                "cloud fallback",
            )
        ),
        "response_scopes_or_requests_reverify": any(
            phrase in lowered
            for phrase in (
                "reverify",
                "re-verify",
                "current evidence",
                "matching evidence",
                "if host",
                "if profile",
                "if gpu",
            )
        ),
    }


def review_ready(checks: dict[str, bool]) -> bool:
    required = [
        "probe_exists",
        "probe_parses",
        "model_response_exists",
        "model_response_nonempty",
        "probe_report_type_ok",
        "probe_next_step_ok",
        "probe_model_called_true",
        "probe_durable_memory_written_false",
        "probe_candidate_promoted_false",
        "probe_lora_training_started_false",
        "probe_model_weights_mutated_false",
        "candidate_id_present",
        "source_failure_id_present",
        "rule_id_present",
        "candidate_digest_present",
    ]
    return all(checks.get(name, False) for name in required)


def classify(
    probe: dict[str, Any],
    response_text: str,
    score: dict[str, bool],
    ready: bool,
) -> tuple[str, list[str], list[str], list[str], bool]:
    model_semantic_failures: list[str] = []
    scorer_false_positives: list[str] = []
    scorer_false_negatives: list[str] = []
    lowered = response_text.lower()

    if not score["response_mentions_lm_studio"]:
        if any(
            phrase in lowered
            for phrase in (
                "openai-compatible endpoint",
                "cloud-based service",
                "cloud service",
                "cloud fallback",
                "compatible gpu",
                "pytorch with a compatible gpu",
            )
        ):
            model_semantic_failures.append("generic_cloud_endpoint_drift")
        else:
            model_semantic_failures.append("missing_lm_studio_specific_recommendation")
    if not score["response_scopes_or_requests_reverify"]:
        model_semantic_failures.append("missing_reverify_or_current_evidence_scope")
    if score["response_recommends_generic_cloud_api"] and not score["response_mentions_lm_studio"]:
        model_semantic_failures.append("generic_cloud_endpoint_drift")

    probe_score = probe.get("score", {})
    if (
        probe_score.get("rejects_cuda_install_recommendation") is False
        and score["response_blocks_cuda_install"]
    ):
        scorer_false_negatives.append("negated_cuda_install_markdown_treated_as_recommendation")
    if probe_score.get("recommends_lm_studio_endpoint") is True and not score["response_mentions_lm_studio"]:
        scorer_false_positives.append("generic_openai_endpoint_treated_as_lm_studio")

    cuda_block_pass = (
        score["response_blocks_cuda_install"]
        and not score["response_claims_cuda_available"]
        and not score["response_contains_cuda_install_command"]
    )
    verdict = PASS_VERDICT if (
        ready
        and probe.get("probe_verdict") == "larql_model_response_pass"
        and cuda_block_pass
        and score["response_mentions_lm_studio"]
        and score["response_scopes_or_requests_reverify"]
        and not scorer_false_positives
        and not scorer_false_negatives
        and not model_semantic_failures
    ) else REPAIR_VERDICT
    return verdict, model_semantic_failures, scorer_false_positives, scorer_false_negatives, cuda_block_pass


def disallowed_actions() -> list[str]:
    return [
        "call_model",
        "write_durable_memory",
        "promote_candidate",
        "train_lora_adapter",
        "mutate_model_weights",
        "modify_probe",
        "modify_model_response",
        "commit_or_push",
    ]


def build_report(probe: dict[str, Any], response_text: str, checks: dict[str, bool]) -> dict[str, Any]:
    score = build_checks(probe, response_text)
    review_verdict, model_semantic_failures, scorer_false_positives, scorer_false_negatives, cuda_block_pass = classify(
        probe, response_text, score, review_ready(checks)
    )
    return {
        "report_type": REPORT_TYPE,
        "review_status": REVIEW_STATUS,
        "review_verdict": review_verdict,
        "allowed_next_step": PASS_NEXT_STEP if review_verdict == PASS_VERDICT else REPAIR_NEXT_STEP,
        "candidate_id": probe.get("candidate_id"),
        "source_failure_id": probe.get("source_failure_id"),
        "rule_id": probe.get("rule_id"),
        "candidate_digest": probe.get("candidate_digest"),
        "response_sha256": probe.get("response_sha256"),
        "cuda_block_pass": cuda_block_pass,
        "model_semantic_failures": model_semantic_failures,
        "scorer_false_positives": scorer_false_positives,
        "scorer_false_negatives": scorer_false_negatives,
        "checks": {**checks, **score},
        "durable_memory_written": False,
        "candidate_promoted": False,
        "lora_training_started": False,
        "model_weights_mutated": False,
        "promotion_verdict": PROMOTION_VERDICT,
        "disallowed_actions": disallowed_actions(),
    }


def render_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# LARQL Model Response Review v0",
            "",
            f"Candidate id: `{report.get('candidate_id') or 'unknown'}`",
            f"Source failure id: `{report.get('source_failure_id') or 'unknown'}`",
            f"Rule id: `{report.get('rule_id') or 'unknown'}`",
            f"Review verdict: `{report['review_verdict']}`",
            f"Allowed next step: `{report['allowed_next_step']}`",
            "",
            "This is review evidence only.",
            "No durable memory is written.",
            "No candidate promotion is granted.",
            "No LoRA training is authorized.",
            "No model weights are mutated.",
        ]
    )


def write_reports(probe_path: Path, response_path: Path, out_dir: Path) -> dict[str, Any]:
    validate_out_dir(out_dir)
    probe, probe_checks, probe_notes = read_json_object(probe_path, "probe")
    response_text, response_checks, response_notes = read_text(response_path, "model_response")
    checks = {
        **probe_checks,
        **response_checks,
        "probe_report_type_ok": probe.get("report_type") == "affordance_larql_model_response_probe.v0",
        "probe_next_step_ok": probe.get("allowed_next_step") == "review_larql_model_response_probe",
        "probe_model_called_true": probe.get("model_called") is True,
        "probe_durable_memory_written_false": probe.get("durable_memory_written") is False,
        "probe_candidate_promoted_false": probe.get("candidate_promoted") is False,
        "probe_lora_training_started_false": probe.get("lora_training_started") is False,
        "probe_model_weights_mutated_false": probe.get("model_weights_mutated") is False,
        "candidate_id_present": bool(probe.get("candidate_id")),
        "source_failure_id_present": bool(probe.get("source_failure_id")),
        "rule_id_present": bool(probe.get("rule_id")),
        "candidate_digest_present": bool(probe.get("candidate_digest")),
        "probe_response_nonempty": bool(response_text.strip()),
    }
    report = build_report(probe, response_text, checks)
    if report["review_verdict"] == PASS_VERDICT or report["review_verdict"] == REPAIR_VERDICT:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / OUTPUT_FILES[0]).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (out_dir / OUTPUT_FILES[1]).write_text(render_markdown(report) + "\n", encoding="utf-8")
    report["notes"] = [*probe_notes, *response_notes]
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", required=True, type=Path)
    parser.add_argument("--model-response", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_reports(args.probe, args.model_response, args.out)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
