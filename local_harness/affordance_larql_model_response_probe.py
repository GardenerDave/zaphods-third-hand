"""Run a bounded LARQL model response probe against a model-context packet.

This helper performs one explicit endpoint call to the configured
OpenAI-compatible server, then scores the response locally. It does not write
durable memory, train LoRA, mutate model weights, or promote the candidate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any
from urllib import request


REPORT_TYPE = "affordance_larql_model_response_probe.v0"
PROBE_STATUS = "completed"
PASS_VERDICT = "larql_model_response_pass"
FAIL_VERDICT = "larql_model_response_fail"
ALLOWED_NEXT_STEP = "review_larql_model_response_probe"
PROMOTION_VERDICT = "hold_pending_explicit_experiment_approval"
OUTPUT_FILES = ("larql_model_response_probe.json", "larql_model_response_probe.md", "model_response.txt")


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


def contains_trigger(text: str) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in ("cuda", "nvidia"))


def normalize_response_text(text: str) -> str:
    return text.replace("**", "")


def contains_unnegated_phrase(lowered: str, phrase: str) -> bool:
    index = lowered.find(phrase)
    while index != -1:
        prefix = lowered[max(0, index - 18) : index]
        if not any(marker in prefix for marker in ("not ", "don't", "do not", "should not", "never ", "cannot", "can't")):
            return True
        index = lowered.find(phrase, index + len(phrase))
    return False


def packet_ready(checks: dict[str, bool]) -> bool:
    required = [
        "packet_exists",
        "packet_parses",
        "packet_report_type_ok",
        "packet_verdict_ok",
        "packet_next_step_ok",
        "packet_model_call_authorized_false",
        "packet_durable_memory_authorized_false",
        "packet_candidate_promotion_authorized_false",
        "packet_lora_training_authorized_false",
        "packet_model_weight_mutation_authorized_false",
        "packet_has_model_instruction",
        "packet_has_user_input",
        "packet_instruction_has_bounded_advisory_constraint",
        "packet_instruction_has_navigator_desktop",
        "packet_instruction_has_no_cuda",
        "packet_instruction_has_blocked_cuda_nvidia",
        "packet_instruction_has_no_cuda_available_claim",
        "packet_instruction_has_no_cuda_install_recommendation",
        "packet_has_runtime_rule_context",
        "candidate_id_present",
        "source_failure_id_present",
        "rule_id_present",
        "candidate_digest_present",
        "blocked_path_present",
        "recommended_path_present",
        "active_host_is_navigator_desktop",
        "host_constraint_no_cuda",
        "input_has_cuda_nvidia_trigger",
        "endpoint_env_present",
        "model_id_env_present",
    ]
    return all(checks.get(name, False) for name in required)


def score_response(response_text: str) -> dict[str, bool]:
    lowered = normalize_response_text(response_text).lower()
    return {
        "rejects_cuda_install_recommendation": not any(
            contains_unnegated_phrase(lowered, phrase)
            for phrase in (
                "install nvidia cuda",
                "nvidia cuda install",
                "install cuda",
            )
        ),
        "rejects_cuda_availability_claim": not any(
            phrase in lowered
            for phrase in (
                "cuda is available",
                "cuda available on",
                "cuda works on this rx580",
            )
        ),
        "rejects_cuda_install_commands": not any(
            phrase in lowered
            for phrase in (
                "sudo apt install cuda",
                "conda install cuda",
                "pip install cuda",
                "nvidia-smi",
            )
        ),
        "mentions_no_cuda_or_rx580_or_amd": any(
            phrase in lowered
            for phrase in ("no_cuda", "rx580", "amd", "non-nvidia")
        ),
        "recommends_lm_studio_endpoint": any(
            phrase in lowered
            for phrase in (
                "lm studio openai-compatible endpoint",
                "lm studio",
            )
        ),
        "asks_for_reverify_or_scopes_to_evidence": any(
            phrase in lowered
            for phrase in (
                "reverify",
                "re-verify",
                "if host",
                "if hardware",
                "current evidence",
                "matching evidence",
                "scope this advice to the current evidence",
            )
        ),
    }


def response_verdict(score: dict[str, bool]) -> str:
    required = [
        "rejects_cuda_install_recommendation",
        "rejects_cuda_availability_claim",
        "rejects_cuda_install_commands",
        "mentions_no_cuda_or_rx580_or_amd",
        "recommends_lm_studio_endpoint",
        "asks_for_reverify_or_scopes_to_evidence",
    ]
    return PASS_VERDICT if all(score.get(name, False) for name in required) else FAIL_VERDICT


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def disallowed_actions() -> list[str]:
    return [
        "write_durable_memory",
        "promote_candidate",
        "train_lora_adapter",
        "mutate_model_weights",
        "modify_packet",
        "modify_runtime_rule",
        "commit_or_push",
    ]


def call_model(endpoint_url: str, model_id: str, instruction: str, user_input: str) -> dict[str, Any]:
    payload = {
        "model": model_id,
        "temperature": 0,
        "max_tokens": 600,
        "messages": [
            {"role": "system", "content": instruction},
            {"role": "user", "content": user_input if user_input.startswith("/no_think") else f"/no_think\n{user_input}"},
        ],
    }
    req = request.Request(
        endpoint_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=120) as resp:  # nosec: B310 - configured endpoint only
        raw = resp.read().decode("utf-8")
    data = json.loads(raw)
    choice = data["choices"][0]
    message = choice.get("message", {})
    content = message.get("content", "") or ""
    reasoning_content = message.get("reasoning_content", "") or ""
    return {
        "text": content,
        "response_sha256": sha256_text(content),
        "finish_reason": choice.get("finish_reason"),
        "reasoning_content_present": bool(reasoning_content),
    }


def build_report(
    packet: dict[str, Any],
    endpoint_url: str,
    model_id: str,
    response_text: str,
    response_sha256: str,
    finish_reason: str | None,
    reasoning_content_present: bool,
    checks: dict[str, bool],
) -> dict[str, Any]:
    score = score_response(response_text)
    if not response_text.strip():
        verdict = FAIL_VERDICT
        failure_mode = "endpoint_empty_content"
    else:
        verdict = response_verdict(score)
        failure_mode = ""
    return {
        "report_type": REPORT_TYPE,
        "probe_status": PROBE_STATUS,
        "probe_verdict": verdict,
        "failure_mode": failure_mode,
        "allowed_next_step": ALLOWED_NEXT_STEP,
        "candidate_id": packet.get("candidate_id"),
        "source_failure_id": packet.get("source_failure_id"),
        "rule_id": packet.get("rule_id"),
        "candidate_digest": packet.get("candidate_digest"),
        "model_called": True,
        "model_id": model_id,
        "endpoint_url": endpoint_url,
        "response_sha256": response_sha256,
        "finish_reason": finish_reason,
        "reasoning_content_present": reasoning_content_present,
        "checks": checks,
        "score": score,
        "model_response_path": "model_response.txt",
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
            "# LARQL Model Response Probe v0",
            "",
            f"Candidate id: `{report.get('candidate_id') or 'unknown'}`",
            f"Source failure id: `{report.get('source_failure_id') or 'unknown'}`",
            f"Rule id: `{report.get('rule_id') or 'unknown'}`",
            f"Probe verdict: `{report['probe_verdict']}`",
            f"Allowed next step: `{report['allowed_next_step']}`",
            f"Model response path: `{report['model_response_path']}`",
            "",
            "This is model-response probe evidence only.",
            "No durable memory is written.",
            "No candidate promotion is granted.",
            "No LoRA training is authorized.",
            "No model weights are mutated.",
        ]
    )


def write_reports(packet_path: Path, out_dir: Path) -> dict[str, Any]:
    validate_out_dir(out_dir)
    packet, packet_checks, packet_notes = read_json_object(packet_path, "packet")
    endpoint_url = os.environ.get("ZTH_ENDPOINT_URL")
    model_id = os.environ.get("ZTH_MODEL_ID")
    checks = {
        **packet_checks,
        "packet_report_type_ok": packet.get("report_type") == "affordance_larql_model_context_packet.v0",
        "packet_verdict_ok": packet.get("packet_verdict") == "ready_for_larql_model_response_probe",
        "packet_next_step_ok": packet.get("allowed_next_step") == "run_larql_model_response_probe",
        "packet_model_call_authorized_false": packet.get("model_call_authorized") is False,
        "packet_durable_memory_authorized_false": packet.get("durable_memory_authorized") is False,
        "packet_candidate_promotion_authorized_false": packet.get("candidate_promotion_authorized") is False,
        "packet_lora_training_authorized_false": packet.get("lora_training_authorized") is False,
        "packet_model_weight_mutation_authorized_false": packet.get("model_weight_mutation_authorized") is False,
        "packet_has_model_instruction": isinstance(packet.get("model_instruction"), str)
        and bool(packet.get("model_instruction")),
        "packet_has_user_input": isinstance(packet.get("user_input"), str) and bool(packet.get("user_input")),
        "packet_instruction_has_bounded_advisory_constraint": "bounded advisory constraint"
        in packet.get("model_instruction", "").lower(),
        "packet_instruction_has_navigator_desktop": "navigator_desktop" in packet.get("model_instruction", "").lower(),
        "packet_instruction_has_no_cuda": "no_cuda" in packet.get("model_instruction", "").lower(),
        "packet_instruction_has_blocked_cuda_nvidia": "cuda/nvidia troubleshooting is blocked"
        in packet.get("model_instruction", "").lower(),
        "packet_instruction_has_no_cuda_available_claim": "do not claim cuda is available"
        in packet.get("model_instruction", "").lower(),
        "packet_instruction_has_no_cuda_install_recommendation": "do not recommend installing nvidia cuda on an rx580/no_cuda host"
        in packet.get("model_instruction", "").lower(),
        "packet_has_runtime_rule_context": isinstance(packet.get("runtime_rule_context"), dict)
        and bool(packet.get("runtime_rule_context")),
        "candidate_id_present": bool(packet.get("candidate_id")),
        "source_failure_id_present": bool(packet.get("source_failure_id")),
        "rule_id_present": bool(packet.get("rule_id")),
        "candidate_digest_present": bool(packet.get("candidate_digest")),
        "blocked_path_present": bool(packet.get("runtime_rule_context", {}).get("blocks_or_warns_on")),
        "recommended_path_present": bool(packet.get("runtime_rule_context", {}).get("recommends")),
        "active_host_is_navigator_desktop": packet.get("checks", {}).get("active_host_is_navigator_desktop") is True,
        "host_constraint_no_cuda": packet.get("checks", {}).get("host_constraint_no_cuda") is True,
        "input_has_cuda_nvidia_trigger": contains_trigger(packet.get("user_input", "")),
        "endpoint_env_present": bool(endpoint_url),
        "model_id_env_present": bool(model_id),
    }
    if endpoint_url and model_id and packet_ready(checks):
        model_result = call_model(
            endpoint_url,
            model_id,
            packet["model_instruction"],
            packet["user_input"],
        )
        response_text = model_result["text"]
        response_sha256 = model_result["response_sha256"]
        finish_reason = model_result["finish_reason"]
        reasoning_content_present = model_result["reasoning_content_present"]
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / OUTPUT_FILES[2]).write_text(response_text + "\n", encoding="utf-8")
        report = build_report(
            packet,
            endpoint_url,
            model_id,
            response_text,
            response_sha256,
            finish_reason,
            reasoning_content_present,
            checks,
        )
        (out_dir / OUTPUT_FILES[0]).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (out_dir / OUTPUT_FILES[1]).write_text(render_markdown(report) + "\n", encoding="utf-8")
        return report

    report = {
        "report_type": REPORT_TYPE,
        "probe_status": PROBE_STATUS,
        "probe_verdict": FAIL_VERDICT,
        "allowed_next_step": ALLOWED_NEXT_STEP,
        "candidate_id": packet.get("candidate_id"),
        "source_failure_id": packet.get("source_failure_id"),
        "rule_id": packet.get("rule_id"),
        "candidate_digest": packet.get("candidate_digest"),
        "model_called": False,
        "model_id": model_id,
        "endpoint_url": endpoint_url,
        "response_sha256": "",
        "finish_reason": None,
        "reasoning_content_present": False,
        "checks": checks,
        "score": {},
        "model_response_path": "model_response.txt",
        "durable_memory_written": False,
        "candidate_promoted": False,
        "lora_training_started": False,
        "model_weights_mutated": False,
        "promotion_verdict": PROMOTION_VERDICT,
        "disallowed_actions": disallowed_actions(),
        "notes": packet_notes,
    }
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_reports(args.packet, args.out)
    except (OSError, ValueError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
