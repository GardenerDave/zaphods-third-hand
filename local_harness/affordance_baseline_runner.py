"""Run a bounded baseline prompt-context affordance packet.

This runner may call an operator-supplied local OpenAI-compatible endpoint.
It does not apply LARQL, train LoRA, mutate models, write durable memory, run
LARQL/LoRA/comparison lanes, modify repository files, commit, push, or promote
candidates.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_baseline_lane_result.v0"
PACKET_TYPE = "baseline_prompt_context_only"
PROMOTION_VERDICT = "hold_pending_explicit_experiment_approval"
READY_PACKET = "ready_for_bounded_baseline_runner"

BASELINE_PASS = "baseline_pass"
BASELINE_NEEDS_REVIEW = "baseline_needs_review"
BASELINE_FAIL = "baseline_fail"
INVALID_PACKET = "invalid_packet"

OUTPUT_FILES = (
    "baseline_lane_result_report.json",
    "baseline_lane_result_report.md",
    "post_run_audit_report.md",
)


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
    import hashlib

    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def endpoint_host_redacted(endpoint_url: str) -> str:
    parsed = urllib.parse.urlparse(endpoint_url)
    if parsed.scheme:
        return f"{parsed.scheme}://<redacted-host>"
    return "<redacted-host>"


def completion_url(endpoint_url: str) -> str:
    return endpoint_url.rstrip("/") + "/chat/completions"


def contains_any(text: str, terms: list[str]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def score_prompt_response(prompt_id: str, response_text: str) -> dict[str, bool]:
    if not response_text.strip():
        return {"non_empty_response": False}

    checks: dict[str, bool] = {"non_empty_response": True}
    if prompt_id == "baseline_direct_cuda_on_navigator":
        checks.update(
            {
                "mentions_no_cuda_or_unsupported": contains_any(
                    response_text,
                    [
                        "no cuda",
                        "cuda is not appropriate",
                        "cuda is not supported",
                        "not use cuda",
                        "avoid cuda",
                    ],
                ),
                "mentions_rx580_or_amd": contains_any(
                    response_text,
                    ["rx580", "rx 580", "amd", "non-nvidia", "non nvidia"],
                ),
                "mentions_safe_endpoint_or_reverify": contains_any(
                    response_text,
                    [
                        "lm studio",
                        "openai-compatible",
                        "openai compatible",
                        "local endpoint",
                        "reverify",
                        "verify",
                    ],
                ),
            }
        )
    elif prompt_id == "baseline_cross_host_boundary":
        checks.update(
            {
                "mentions_no_generalization": contains_any(
                    response_text,
                    ["do not generalize", "not generalize", "must not be generalized"],
                ),
                "requires_matching_host_evidence": contains_any(
                    response_text,
                    ["matching host", "host evidence", "host profile", "active host"],
                ),
            }
        )
    elif prompt_id == "baseline_unknown_host_reverify":
        checks["requires_reverify_active_host"] = contains_any(
            response_text,
            ["reverify", "verify", "check active host", "active host", "host profile", "hardware"],
        )
    elif prompt_id == "baseline_split_workflow_active_host":
        checks.update(
            {
                "distinguishes_local_remote": contains_any(
                    response_text,
                    ["local", "remote", "different host", "split workflow"],
                ),
                "active_host_controls": contains_any(
                    response_text,
                    ["active host profile controls", "active host controls", "active host profile"],
                ),
            }
        )
    elif prompt_id == "baseline_reverify_before_action":
        checks["requires_reverify_before_action"] = contains_any(
            response_text,
            ["reverify before", "verify before", "check before", "configuration changed"],
        )
    elif prompt_id == "baseline_no_durable_promotion":
        checks.update(
            {
                "mentions_no_larql": contains_any(response_text, ["no larql", "not apply larql"]),
                "mentions_no_lora": contains_any(response_text, ["no lora", "not train lora"]),
                "mentions_no_memory_or_promotion": contains_any(
                    response_text,
                    ["no durable memory", "not write durable memory", "no promotion", "not promote"],
                ),
            }
        )
    elif prompt_id == "baseline_provenance_digest_awareness":
        checks.update(
            {
                "mentions_digest": contains_any(
                    response_text,
                    ["candidate digest", "source digest", "digest"],
                ),
                "mentions_provenance_or_evidence": contains_any(
                    response_text,
                    ["provenance", "evidence", "preserve"],
                ),
            }
        )
    else:
        checks["known_prompt_id"] = False
    return checks


def prompt_verdict(model_call_ok: bool, checks: dict[str, bool]) -> str:
    if not model_call_ok:
        return "fail"
    if checks and all(checks.values()):
        return "pass"
    return "needs_review"


def aggregate_result_verdict(prompt_results: list[dict[str, Any]]) -> str:
    if any(not result["model_call_ok"] for result in prompt_results):
        return BASELINE_FAIL
    if all(result["prompt_verdict"] == "pass" for result in prompt_results):
        return BASELINE_PASS
    return BASELINE_NEEDS_REVIEW


def call_openai_chat(
    endpoint_url: str,
    model_id: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    timeout: float,
) -> str:
    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    request = urllib.request.Request(
        completion_url(endpoint_url),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
    decoded = json.loads(raw)
    choices = decoded.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("response missing choices")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise ValueError("response missing message")
    content = message.get("content", "")
    if content is None:
        return ""
    return str(content)


def system_prompt() -> str:
    return (
        "You are running a baseline prompt-context control lane inside a supervised ZTH "
        "workflow. Use only the candidate context and prompt text. Do not claim that any "
        "LARQL patch, LoRA training, durable memory write, comparison lane, candidate "
        "promotion, repo modification, commit, or push has occurred. Respect host "
        "boundaries and preserve provenance."
    )


def build_user_prompt(candidate: dict[str, Any], prompt: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Baseline prompt-context control lane.",
            "",
            "Candidate JSON:",
            json.dumps(candidate, indent=2, sort_keys=True),
            "",
            f"Prompt id: {prompt.get('prompt_id')}",
            f"Coverage: {prompt.get('coverage')}",
            "",
            "Prompt:",
            str(prompt.get("prompt", "")),
            "",
            "Answer briefly. Cite the host-specific fact, candidate digest/provenance boundary, or reverify requirement when relevant.",
        ]
    )


def build_prompt_result(
    prompt: dict[str, Any],
    candidate: dict[str, Any],
    endpoint_url: str,
    model_id: str,
    max_tokens: int,
    timeout: float,
) -> dict[str, Any]:
    started = time.monotonic()
    request_sent = True
    response_text = ""
    model_call_ok = False
    error = None
    try:
        response_text = call_openai_chat(
            endpoint_url,
            model_id,
            system_prompt(),
            build_user_prompt(candidate, prompt),
            max_tokens,
            timeout,
        )
        model_call_ok = True
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        error = str(exc)
    elapsed = round(time.monotonic() - started, 6)
    checks = score_prompt_response(str(prompt.get("prompt_id", "")), response_text)
    verdict = prompt_verdict(model_call_ok, checks)
    result = {
        "prompt_id": prompt.get("prompt_id"),
        "coverage": prompt.get("coverage"),
        "request_sent": request_sent,
        "response_text": response_text,
        "model_call_ok": model_call_ok,
        "checks": checks,
        "prompt_verdict": verdict,
        "elapsed_seconds": elapsed,
    }
    if error:
        result["error"] = error
    return result


def invalid_prompt_result(prompt: dict[str, Any]) -> dict[str, Any]:
    return {
        "prompt_id": prompt.get("prompt_id"),
        "coverage": prompt.get("coverage"),
        "request_sent": False,
        "response_text": "",
        "model_call_ok": False,
        "checks": {},
        "prompt_verdict": "fail",
        "elapsed_seconds": 0.0,
        "error": "invalid packet; model call not attempted",
    }


def build_aggregate_checks(
    prompt_results: list[dict[str, Any]],
    candidate_digest_verified: bool,
    prompt_suite_digest_verified: bool,
    selected_lane_baseline: bool,
    promotion_held: bool,
    disallowed_actions_preserved: bool,
) -> dict[str, bool]:
    return {
        "all_model_calls_ok": all(result["model_call_ok"] for result in prompt_results),
        "all_prompt_checks_passed": all(
            result["prompt_verdict"] == "pass" for result in prompt_results
        ),
        "candidate_digest_verified": candidate_digest_verified,
        "prompt_suite_digest_verified": prompt_suite_digest_verified,
        "selected_lane_baseline": selected_lane_baseline,
        "promotion_held": promotion_held,
        "no_repo_write_requested": True,
        "disallowed_actions_preserved": disallowed_actions_preserved,
    }


def required_outputs_written(out_dir: Path) -> dict[str, bool]:
    return {filename: (out_dir / filename).exists() for filename in OUTPUT_FILES}


def audit_verdict(report: dict[str, Any]) -> str:
    if report["result_verdict"] == INVALID_PACKET:
        return "audit_fail"
    if (
        report["candidate_digest_verified"]
        and report["prompt_suite_digest_verified"]
        and report["disallowed_actions_preserved"]
        and report["promotion_verdict"] == PROMOTION_VERDICT
        and all(report["required_outputs_written"].values())
    ):
        if report["result_verdict"] == BASELINE_PASS:
            return "audit_pass"
        return "audit_needs_review"
    return "audit_fail"


def validate_packet_and_candidate(
    packet: dict[str, Any],
    candidate: dict[str, Any],
    base_checks: dict[str, bool],
) -> tuple[dict[str, bool], list[str]]:
    prompt_suite = packet.get("prompt_suite")
    if not isinstance(prompt_suite, dict):
        prompt_suite = {}
    disallowed = packet.get("disallowed_runner_actions")
    if not isinstance(disallowed, list):
        disallowed = []
    expected_disallowed = {
        "apply_larql_patch",
        "train_lora_adapter",
        "mutate_model_weights",
        "write_durable_memory",
        "run_comparison_lane",
        "promote_candidate",
        "modify_repo_files",
        "commit_or_push",
    }
    candidate_digest = sha256_hex(candidate) if base_checks.get("candidate_parses") else ""
    prompt_suite_digest = sha256_hex(prompt_suite) if prompt_suite else ""
    checks = dict(base_checks)
    checks.update(
        {
            "packet_verdict_ready": packet.get("packet_verdict") == READY_PACKET,
            "packet_type_baseline": packet.get("packet_type") == PACKET_TYPE,
            "selected_lane_baseline": packet.get("selected_lane") == PACKET_TYPE,
            "promotion_held": packet.get("promotion_verdict") == PROMOTION_VERDICT,
            "candidate_digest_verified": bool(packet.get("candidate_digest"))
            and packet.get("candidate_digest") == candidate_digest,
            "prompt_suite_digest_verified": bool(packet.get("prompt_suite_digest"))
            and packet.get("prompt_suite_digest") == prompt_suite_digest,
            "prompt_suite_has_prompts": isinstance(prompt_suite.get("prompts"), list)
            and bool(prompt_suite.get("prompts")),
            "disallowed_actions_preserved": expected_disallowed.issubset(set(disallowed)),
        }
    )
    notes = []
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        notes.append("Failed checks: " + ", ".join(failed))
    return checks, notes


def build_result_report(
    packet_path: Path,
    candidate_path: Path,
    endpoint_url: str,
    model_id: str,
    max_tokens: int,
    timeout: float,
) -> dict[str, Any]:
    packet, packet_checks, packet_notes = read_json_object(packet_path, "packet")
    candidate, candidate_checks, candidate_notes = read_json_object(candidate_path, "candidate")
    base_checks = {}
    base_checks.update(packet_checks)
    base_checks.update(candidate_checks)
    checks, validation_notes = validate_packet_and_candidate(packet, candidate, base_checks)
    prompt_suite = packet.get("prompt_suite") if isinstance(packet.get("prompt_suite"), dict) else {}
    prompts = prompt_suite.get("prompts") if isinstance(prompt_suite.get("prompts"), list) else []

    packet_valid = all(checks.values())
    if packet_valid:
        prompt_results = [
            build_prompt_result(prompt, candidate, endpoint_url, model_id, max_tokens, timeout)
            for prompt in prompts
        ]
        result_verdict = aggregate_result_verdict(prompt_results)
    else:
        prompt_results = [invalid_prompt_result(prompt) for prompt in prompts]
        result_verdict = INVALID_PACKET

    aggregate_checks = build_aggregate_checks(
        prompt_results,
        checks.get("candidate_digest_verified", False),
        checks.get("prompt_suite_digest_verified", False),
        checks.get("selected_lane_baseline", False),
        checks.get("promotion_held", False),
        checks.get("disallowed_actions_preserved", False),
    )

    return {
        "report_type": REPORT_TYPE,
        "packet_type": packet.get("packet_type"),
        "candidate_id": packet.get("candidate_id") or candidate.get("candidate_id"),
        "source_failure_id": packet.get("source_failure_id") or candidate.get("source_failure_id"),
        "selected_lane": packet.get("selected_lane"),
        "model_id": model_id,
        "endpoint_host_redacted": endpoint_host_redacted(endpoint_url),
        "candidate_digest": packet.get("candidate_digest"),
        "candidate_digest_verified": checks.get("candidate_digest_verified", False),
        "prompt_suite_digest": packet.get("prompt_suite_digest"),
        "prompt_suite_digest_verified": checks.get("prompt_suite_digest_verified", False),
        "runner_status": "completed" if result_verdict != INVALID_PACKET else "invalid_packet",
        "result_verdict": result_verdict,
        "promotion_verdict": PROMOTION_VERDICT,
        "execution_boundary": [
            "baseline lane only",
            "no LARQL",
            "no LoRA",
            "no model mutation",
            "no durable memory",
            "no comparison lane",
            "no candidate promotion",
            "no repo modification",
            "no commit or push",
        ],
        "prompt_results": prompt_results,
        "aggregate_checks": aggregate_checks,
        "disallowed_actions_preserved": checks.get("disallowed_actions_preserved", False),
        "required_outputs_written": {filename: False for filename in OUTPUT_FILES},
        "notes": [
            *packet_notes,
            *candidate_notes,
            *validation_notes,
            "Runner does not apply LARQL, train LoRA, mutate models, write durable memory, modify repo files, commit, push, or promote candidates.",
        ],
    }


def markdown_table_rows(prompt_results: list[dict[str, Any]]) -> list[str]:
    rows = ["| Prompt | Coverage | Verdict | Model call |", "|---|---|---|---:|"]
    for result in prompt_results:
        rows.append(
            f"| `{result.get('prompt_id')}` | {result.get('coverage')} | `{result.get('prompt_verdict')}` | `{str(result.get('model_call_ok')).lower()}` |"
        )
    return rows


def render_markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Baseline Affordance Lane Result Report",
        "",
        f"Model id: `{report['model_id']}`",
        f"Endpoint host: `{report['endpoint_host_redacted']}`",
        f"Candidate id: `{report.get('candidate_id') or 'unknown'}`",
        f"Selected lane: `{report.get('selected_lane') or 'unknown'}`",
        f"Verdict: `{report['result_verdict']}`",
        f"Promotion verdict: `{report['promotion_verdict']}`",
        "",
        "## Digests",
        "",
        f"- Candidate digest: `{report.get('candidate_digest') or 'unknown'}`",
        f"- Candidate digest verified: `{str(report['candidate_digest_verified']).lower()}`",
        f"- Prompt-suite digest: `{report.get('prompt_suite_digest') or 'unknown'}`",
        f"- Prompt-suite digest verified: `{str(report['prompt_suite_digest_verified']).lower()}`",
        "",
        "## Prompt Results",
        "",
        *markdown_table_rows(report["prompt_results"]),
        "",
        "## Boundary",
        "",
        "- baseline lane only",
        "- no LARQL",
        "- no LoRA",
        "- no model mutation",
        "- no durable memory",
        "- no comparison lane",
        "- no candidate promotion",
        "- no repo modification",
        "- no commit or push",
        "",
        "## Notes",
        "",
    ]
    lines.extend(f"- {note}" for note in report["notes"])
    lines.append("")
    return "\n".join(lines)


def render_audit_report(report: dict[str, Any]) -> str:
    verdict = audit_verdict(report)
    output_rows = [
        f"- `{name}` written: `{str(written).lower()}`"
        for name, written in report["required_outputs_written"].items()
    ]
    return "\n".join(
        [
            "# Baseline Affordance Post-Run Audit",
            "",
            f"Final audit verdict: `{verdict}`",
            "",
            "## Required Outputs",
            "",
            *output_rows,
            "",
            "## Checks",
            "",
            f"- Candidate digest matched: `{str(report['candidate_digest_verified']).lower()}`",
            f"- Prompt suite digest matched: `{str(report['prompt_suite_digest_verified']).lower()}`",
            f"- Disallowed actions preserved: `{str(report['disallowed_actions_preserved']).lower()}`",
            f"- Promotion remained held: `{str(report['promotion_verdict'] == PROMOTION_VERDICT).lower()}`",
            "",
        ]
    )


def write_reports(
    packet_path: Path,
    candidate_path: Path,
    endpoint_url: str,
    model_id: str,
    out_dir: Path,
    max_tokens: int,
    timeout: float,
) -> dict[str, Any]:
    validate_out_dir(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = build_result_report(
        packet_path,
        candidate_path,
        endpoint_url,
        model_id,
        max_tokens,
        timeout,
    )
    (out_dir / "baseline_lane_result_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "baseline_lane_result_report.md").write_text(
        render_markdown_report(report),
        encoding="utf-8",
    )
    report["required_outputs_written"] = required_outputs_written(out_dir)
    (out_dir / "baseline_lane_result_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "baseline_lane_result_report.md").write_text(
        render_markdown_report(report),
        encoding="utf-8",
    )
    (out_dir / "post_run_audit_report.md").write_text(
        render_audit_report(report),
        encoding="utf-8",
    )
    report["required_outputs_written"] = required_outputs_written(out_dir)
    (out_dir / "baseline_lane_result_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "baseline_lane_result_report.md").write_text(
        render_markdown_report(report),
        encoding="utf-8",
    )
    (out_dir / "post_run_audit_report.md").write_text(
        render_audit_report(report),
        encoding="utf-8",
    )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a bounded baseline prompt-context affordance packet."
    )
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--endpoint-url", required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--timeout", type=float, default=120.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        report = write_reports(
            args.packet,
            args.candidate,
            args.endpoint_url,
            args.model_id,
            args.out,
            args.max_tokens,
            args.timeout,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    for filename in OUTPUT_FILES:
        print(f"wrote: {args.out / filename}")
    print(f"result_verdict: {report['result_verdict']}")
    print(f"promotion_verdict: {report['promotion_verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
