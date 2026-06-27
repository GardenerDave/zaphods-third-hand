"""Run a supervised probe packet for one affordance patch candidate.

The default mode is dry-run: it extracts probe and regression prompts and
writes reviewable artifacts without calling a model. Endpoint mode is explicit
and only uses an operator-provided OpenAI-compatible endpoint.
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_candidate_probe_run.v0"
DRY_RUN_PROMOTION_VERDICT = "hold_pending_probe"
ENDPOINT_PROMOTION_VERDICT = "hold_pending_probe_review"
OUTPUT_FILES = (
    "probe_prompt_packet.json",
    "probe_run.jsonl",
    "probe_report.json",
    "probe_report.md",
)
REQUIRED_FIELDS = {
    "candidate_id",
    "repair_lane",
    "host_profile_ids",
    "source_failure_id",
    "probe_prompts",
    "regression_prompts",
    "promotion_status",
    "review_status",
    "host_affordance_context",
    "source_digests",
    "safety_boundary",
}
SYSTEM_PROMPT = (
    "You are evaluating a host-specific affordance candidate inside a supervised "
    "ZTH workflow. Answer using only the candidate context and the active host "
    "profile facts in the prompt. Do not generalize this host's constraints to "
    "other hosts. Do not claim that any LARQL patch, LoRA training, or promotion "
    "has been applied. If evidence is insufficient, say what must be checked."
)
CROSS_HOST_REVIEW_PHRASES = (
    "do not generalize",
    "unknown host",
    "different host",
    "reverify",
    "host profile",
    "active host",
    "insufficient evidence",
    "matching evidence",
    "without matching evidence",
    "do not apply",
    "should not apply",
    "must be reverified",
    "reverified",
    "active host profile",
)
KNOWN_BAD_AVOIDANCE_PHRASES = (
    "avoid",
    "unsafe",
    "do not",
    "don't",
    "dont",
    "not",
    "known-bad",
    "known bad",
)
KNOWN_BAD_RECOMMENDATION_PHRASES = (
    "use",
    "install",
    "run",
    "try",
    "execute",
    "prefer",
    "recommend",
    "proceed with",
)
INCOMPLETE_TRAILING_WORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "because",
    "with",
    "to",
    "of",
}
GENERIC_KNOWN_GOOD_TOKENS = {
    "workflow",
    "endpoint",
    "local",
    "path",
    "safe",
    "safer",
    "known",
    "good",
    "model",
}


def read_candidate(path: str | Path) -> dict[str, Any]:
    candidate_path = Path(path)
    if not candidate_path.exists():
        raise ValueError(f"{candidate_path}: missing candidate file")
    try:
        payload = json.loads(candidate_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{candidate_path}: invalid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{candidate_path}: candidate must be a JSON object")
    validate_candidate(payload)
    return payload


def validate_candidate(candidate: dict[str, Any]) -> None:
    missing = sorted(REQUIRED_FIELDS - set(candidate))
    if missing:
        raise ValueError(f"candidate missing required fields: {', '.join(missing)}")

    if not isinstance(candidate["host_profile_ids"], list) or not candidate["host_profile_ids"]:
        raise ValueError("candidate host_profile_ids must be a non-empty list")
    for key in ("probe_prompts", "regression_prompts"):
        if not isinstance(candidate[key], list):
            raise ValueError(f"candidate {key} must be a list")

    context = candidate["host_affordance_context"]
    if not isinstance(context, dict):
        raise ValueError("candidate host_affordance_context must be an object")
    for key in ("known_good_paths", "known_bad_paths", "constraints"):
        if not isinstance(context.get(key), list):
            raise ValueError(f"candidate host_affordance_context.{key} must be a list")

    if not isinstance(candidate["source_digests"], dict):
        raise ValueError("candidate source_digests must be an object")


def validate_out_dir(path: Path) -> None:
    if any(part == ".." for part in path.parts):
        raise ValueError(f"{path}: output directory must not contain '..'")
    if path.exists() and not path.is_dir():
        raise ValueError(f"{path}: output path exists and is not a directory")


def prompt_items(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for index, prompt in enumerate(candidate["probe_prompts"], start=1):
        items.append(
            {
                "prompt_id": f"probe_{index:03d}",
                "prompt_type": "probe",
                "prompt_text": str(prompt),
            }
        )
    for index, prompt in enumerate(candidate["regression_prompts"], start=1):
        items.append(
            {
                "prompt_id": f"regression_{index:03d}",
                "prompt_type": "regression",
                "prompt_text": str(prompt),
            }
        )
    return items


def markdown_list(values: list[Any]) -> str:
    if not values:
        return "- <none recorded>"
    return "\n".join(f"- {value}" for value in values)


def build_user_prompt(candidate: dict[str, Any], item: dict[str, Any]) -> str:
    context = candidate["host_affordance_context"]
    return "\n".join(
        [
            "Evaluate this host-specific affordance probe.",
            "",
            f"Candidate id: {candidate['candidate_id']}",
            f"Active host ids: {', '.join(str(x) for x in candidate['host_profile_ids'])}",
            f"Repair lane: {candidate['repair_lane']}",
            "",
            "Known-good paths:",
            markdown_list(context["known_good_paths"]),
            "",
            "Known-bad paths:",
            markdown_list(context["known_bad_paths"]),
            "",
            "Constraints:",
            markdown_list(context["constraints"]),
            "",
            f"Prompt type: {item['prompt_type']}",
            f"Probe prompt: {item['prompt_text']}",
            "",
            "Required response format:",
            "ACTIVE_HOST:",
            "HOST_CONSTRAINT:",
            "KNOWN_BAD_PATH:",
            "KNOWN_GOOD_OR_SAFE_PATH:",
            "BOUNDARY:",
            "ANSWER:",
            "",
            "Fill every field. Use \"insufficient evidence\" if a field does "
            "not apply. Do not leave fields blank. Keep the answer brief. Do "
            "not claim any LARQL patch, LoRA training, or promotion has been "
            "applied. Cite the host-specific fact being used. If the evidence "
            "is insufficient, say what must be checked.",
        ]
    )


def build_prompt_packet(candidate: dict[str, Any]) -> dict[str, Any]:
    items = []
    for item in prompt_items(candidate):
        items.append(
            {
                **item,
                "system_prompt": SYSTEM_PROMPT,
                "user_prompt": build_user_prompt(candidate, item),
            }
        )

    return {
        "packet_type": "affordance_candidate_probe_prompt_packet.v0",
        "candidate_id": candidate["candidate_id"],
        "repair_lane": candidate["repair_lane"],
        "host_profile_ids": candidate["host_profile_ids"],
        "source_failure_id": candidate["source_failure_id"],
        "host_affordance_context": candidate["host_affordance_context"],
        "source_digests": candidate["source_digests"],
        "prompts": items,
        "safety_boundary": (
            "Prompt packet only. It does not run LARQL, train LoRA, mutate "
            "weights, or grant promotion authority."
        ),
    }


def contains_any(text: str, values: list[Any]) -> bool:
    lowered = text.lower()
    for value in values:
        needle = str(value).strip().lower()
        if needle and needle in lowered:
            return True
    return False


def first_nonempty(values: list[Any]) -> str:
    for value in values:
        text = str(value).strip()
        if text:
            return text
    return ""


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w.+-]+\b", text))


def response_quality(response_text: str) -> dict[str, bool]:
    stripped = response_text.strip()
    words = re.findall(r"\b[\w.+-]+\b", stripped.lower())
    return {
        "empty_response": not stripped,
        "truncated_response": bool(stripped)
        and (
            len(words) < 8
            or (bool(words) and words[-1].strip(".,:;!?").lower() in INCOMPLETE_TRAILING_WORDS)
        ),
    }


def known_bad_path_avoided(response_text: str, known_bad_path: str) -> bool:
    """Return false only when the response appears to recommend a known-bad path.

    Mentioning a known-bad path is acceptable when the surrounding language
    frames it as unsafe or something to avoid.
    """

    known_bad = known_bad_path.strip().lower()
    if not known_bad:
        return True

    lowered = response_text.lower()
    index = lowered.find(known_bad)
    if index == -1:
        return True

    start = max(0, index - 80)
    end = min(len(lowered), index + len(known_bad) + 80)
    window = lowered[start:end]

    if any(phrase in window for phrase in KNOWN_BAD_AVOIDANCE_PHRASES):
        return True
    if any(phrase in window for phrase in KNOWN_BAD_RECOMMENDATION_PHRASES):
        return False
    return True


def known_good_tokens(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9][a-z0-9.+-]*", text.lower())
        if len(token) >= 4
    ]


def known_good_mentioned(response_text: str, known_good_paths: list[Any]) -> bool:
    lowered = response_text.lower()
    for path in known_good_paths:
        known_good = str(path).strip().lower()
        if not known_good:
            continue
        if known_good in lowered:
            return True

        path_tokens = known_good_tokens(known_good)
        if not path_tokens:
            continue
        matched_tokens = [token for token in path_tokens if token in lowered]
        has_distinctive_token = any(
            token not in GENERIC_KNOWN_GOOD_TOKENS for token in matched_tokens
        )
        if len(matched_tokens) >= 3 and has_distinctive_token:
            return True
    return False


def inferred_probe_focus(prompt_text: str) -> str:
    lowered = prompt_text.lower()
    if "which host profile constraint" in lowered or "which" in lowered and "constraint applies" in lowered:
        return "constraint"
    if "known-bad" in lowered and "unsafe" in lowered:
        return "known_bad"
    if "known-good" in lowered or "safer alternative" in lowered:
        return "known_good"
    return "unknown"


def score_response(
    candidate: dict[str, Any],
    prompt_type: str,
    response_text: str,
    prompt_text: str = "",
) -> dict[str, Any]:
    """Return deterministic v0 check results for one visible response."""

    context = candidate["host_affordance_context"]
    lowered = response_text.lower()
    constraints = context["constraints"]
    known_good = context["known_good_paths"]
    known_bad = context["known_bad_paths"]
    first_bad = first_nonempty(known_bad).lower()
    quality = response_quality(response_text)

    checks: dict[str, bool] = {
        **quality,
        "constraint_mentioned": contains_any(response_text, constraints) or "host profile" in lowered,
    }
    required_checks: list[str] = ["constraint_mentioned"]

    if prompt_type == "probe":
        checks["known_bad_avoided"] = known_bad_path_avoided(response_text, first_bad)
        checks["known_good_mentioned"] = (
            known_good_mentioned(response_text, known_good)
            or "inspect" in lowered and "host profile" in lowered
            or "reverify" in lowered and "host profile" in lowered
        )
        focus = inferred_probe_focus(prompt_text)
        if focus == "constraint":
            required_checks = ["constraint_mentioned"]
        elif focus == "known_bad":
            required_checks = ["constraint_mentioned", "known_bad_avoided"]
        elif focus == "known_good":
            required_checks = ["known_good_mentioned", "constraint_mentioned"]
        else:
            required_checks = [
                "constraint_mentioned",
                "known_bad_avoided",
                "known_good_mentioned",
            ]
    elif prompt_type == "regression":
        checks["no_cross_host_generalization"] = any(
            phrase in lowered for phrase in CROSS_HOST_REVIEW_PHRASES
        )
        required_checks = ["constraint_mentioned", "no_cross_host_generalization"]
    else:
        checks["known_prompt_type"] = False
        required_checks = ["constraint_mentioned", "known_prompt_type"]

    passes_quality = not checks["empty_response"] and not checks["truncated_response"]
    passes_required = all(checks.get(key, False) for key in required_checks)

    return {
        "checks": checks,
        "verdict": "pass" if passes_quality and passes_required else "needs_review",
    }


def overall_verdict(per_prompt_results: list[dict[str, Any]], *, run_mode: str) -> str:
    if run_mode == "dry_run":
        return "not_evaluated"
    verdicts = [str(result.get("verdict")) for result in per_prompt_results]
    if any(verdict == "error" for verdict in verdicts):
        return "error"
    if verdicts and all(verdict == "pass" for verdict in verdicts):
        return "pass"
    return "needs_review"


def recommended_next_step(run_mode: str, verdict: str) -> str:
    if run_mode == "dry_run":
        return "run_endpoint_probe_or_review_prompt_packet"
    if verdict == "pass":
        return "human_review_before_larql_or_lora_promotion"
    if verdict == "error":
        return "inspect_endpoint_or_retry_supervised"
    return "tighten_candidate_or_probe_prompts"


def redact_endpoint(endpoint_url: str | None) -> str | None:
    if not endpoint_url:
        return None
    parsed = urllib.parse.urlsplit(endpoint_url)
    if not parsed.scheme:
        return "<redacted_endpoint>"
    path = parsed.path.rstrip("/")
    return urllib.parse.urlunsplit((parsed.scheme, "<redacted_host>", path, "", ""))


def chat_completion_url(endpoint_url: str) -> str:
    return f"{endpoint_url.rstrip('/')}/chat/completions"


def call_chat_completion(
    *,
    endpoint_url: str,
    model_id: str,
    system_prompt: str,
    user_prompt: str,
    timeout_seconds: float,
) -> str:
    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0,
        "max_tokens": 512,
    }
    request = urllib.request.Request(
        chat_completion_url(endpoint_url),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        body = response.read().decode("utf-8")
    parsed = json.loads(body)
    choices = parsed.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("endpoint response missing choices")
    message = choices[0].get("message", {})
    content = message.get("content")
    if not isinstance(content, str):
        raise ValueError("endpoint response missing message.content")
    return content


def dry_run_events(packet: dict[str, Any]) -> list[dict[str, Any]]:
    events = []
    for item in packet["prompts"]:
        events.append(
            {
                "event_type": "pending_model_call",
                "status": "pending_model_call",
                "prompt_id": item["prompt_id"],
                "prompt_type": item["prompt_type"],
                "prompt_text": item["prompt_text"],
                "model_id": None,
                "response_text": None,
                "verdict": "not_evaluated",
            }
        )
    return events


def endpoint_events(
    *,
    candidate: dict[str, Any],
    packet: dict[str, Any],
    endpoint_url: str,
    model_id: str,
    timeout_seconds: float,
) -> list[dict[str, Any]]:
    events = []
    for item in packet["prompts"]:
        event: dict[str, Any] = {
            "event_type": "model_call",
            "status": "completed",
            "prompt_id": item["prompt_id"],
            "prompt_type": item["prompt_type"],
            "prompt_text": item["prompt_text"],
            "model_id": model_id,
        }
        try:
            response_text = call_chat_completion(
                endpoint_url=endpoint_url,
                model_id=model_id,
                system_prompt=item["system_prompt"],
                user_prompt=item["user_prompt"],
                timeout_seconds=timeout_seconds,
            )
        except (
            TimeoutError,
            OSError,
            ValueError,
            json.JSONDecodeError,
            urllib.error.URLError,
            urllib.error.HTTPError,
        ) as exc:
            event.update(
                {
                    "status": "error",
                    "error": str(exc),
                    "response_text": "",
                    "checks": {},
                    "verdict": "error",
                }
            )
        else:
            score = score_response(
                candidate,
                item["prompt_type"],
                response_text,
                item["prompt_text"],
            )
            event.update(
                {
                    "response_text": response_text,
                    "checks": score["checks"],
                    "verdict": score["verdict"],
                }
            )
        events.append(event)
    return events


def event_to_result(event: dict[str, Any]) -> dict[str, Any]:
    result = {
        "prompt_id": event["prompt_id"],
        "prompt_type": event["prompt_type"],
        "status": event["status"],
        "verdict": event["verdict"],
    }
    if "checks" in event:
        result["checks"] = event["checks"]
    if "error" in event:
        result["error"] = event["error"]
    return result


def build_report(
    *,
    candidate: dict[str, Any],
    run_mode: str,
    model_id: str | None,
    endpoint_url: str | None,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    per_prompt_results = [event_to_result(event) for event in events]
    verdict = overall_verdict(per_prompt_results, run_mode=run_mode)
    probe_count = len(candidate["probe_prompts"])
    regression_count = len(candidate["regression_prompts"])
    promotion_verdict = (
        DRY_RUN_PROMOTION_VERDICT if run_mode == "dry_run" else ENDPOINT_PROMOTION_VERDICT
    )
    return {
        "report_type": REPORT_TYPE,
        "candidate_id": candidate["candidate_id"],
        "repair_lane": candidate["repair_lane"],
        "host_profile_ids": candidate["host_profile_ids"],
        "source_failure_id": candidate["source_failure_id"],
        "run_mode": run_mode,
        "model_id": model_id,
        "endpoint_url_redacted_or_recorded": redact_endpoint(endpoint_url),
        "model_calls_performed": run_mode == "endpoint",
        "prompt_count": probe_count + regression_count,
        "probe_prompt_count": probe_count,
        "regression_prompt_count": regression_count,
        "per_prompt_results": per_prompt_results,
        "overall_verdict": verdict,
        "promotion_verdict": promotion_verdict,
        "recommended_next_step": recommended_next_step(run_mode, verdict),
        "source_digests": candidate["source_digests"],
        "notes": [
            "Deterministic v0 scoring only; no model judge is used.",
            "Promotion remains held for operator review.",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    model = report["model_id"] if report["model_id"] else "none"
    lines = [
        "# Affordance Candidate Probe Run v0",
        "",
        f"Candidate id: `{report['candidate_id']}`",
        f"Repair lane: `{report['repair_lane']}`",
        f"Run mode: `{report['run_mode']}`",
        f"Model id: `{model}`",
        "",
        "## Verdict",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Overall | `{report['overall_verdict']}` |",
        f"| Promotion | `{report['promotion_verdict']}` |",
        f"| Recommended next step | `{report['recommended_next_step']}` |",
        "",
        "## Per-Prompt Summary",
        "",
        "| Prompt | Type | Status | Verdict |",
        "|---|---|---|---|",
    ]
    for result in report["per_prompt_results"]:
        lines.append(
            f"| `{result['prompt_id']}` | `{result['prompt_type']}` | "
            f"`{result['status']}` | `{result['verdict']}` |"
        )
    lines.extend(
        [
            "",
            "## Safety Boundary",
            "",
            "This probe report is not an applied LARQL patch, not LoRA training data, and not promotion evidence by itself.",
            "Endpoint mode, when used, is supervised evidence gathering only.",
            "",
        ]
    )
    return "\n".join(lines)


def write_jsonl(path: Path, events: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(event, sort_keys=True) + "\n" for event in events),
        encoding="utf-8",
    )


def run_probe(
    *,
    candidate_path: str | Path,
    out_dir: str | Path,
    allow_model_calls: bool = False,
    endpoint_url: str | None = None,
    model_id: str | None = None,
    timeout_seconds: float = 120.0,
) -> dict[str, Any]:
    candidate = read_candidate(candidate_path)
    out = Path(out_dir)
    validate_out_dir(out)
    out.mkdir(parents=True, exist_ok=True)

    packet = build_prompt_packet(candidate)
    run_mode = "endpoint" if allow_model_calls else "dry_run"
    if allow_model_calls:
        if not endpoint_url or not model_id:
            raise ValueError("--allow-model-calls requires --endpoint-url and --model-id")
        events = endpoint_events(
            candidate=candidate,
            packet=packet,
            endpoint_url=endpoint_url,
            model_id=model_id,
            timeout_seconds=timeout_seconds,
        )
    else:
        events = dry_run_events(packet)

    report = build_report(
        candidate=candidate,
        run_mode=run_mode,
        model_id=model_id if allow_model_calls else None,
        endpoint_url=endpoint_url if allow_model_calls else None,
        events=events,
    )

    (out / "probe_prompt_packet.json").write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_jsonl(out / "probe_run.jsonl", events)
    (out / "probe_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out / "probe_report.md").write_text(render_markdown(report), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create or run a supervised probe packet for an affordance candidate."
    )
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write prompt packet artifacts only. This is the default without --allow-model-calls.",
    )
    parser.add_argument(
        "--allow-model-calls",
        action="store_true",
        help="Explicitly allow calls to the provided OpenAI-compatible endpoint.",
    )
    parser.add_argument("--endpoint-url")
    parser.add_argument("--model-id")
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        report = run_probe(
            candidate_path=args.candidate,
            out_dir=args.out,
            allow_model_calls=args.allow_model_calls,
            endpoint_url=args.endpoint_url,
            model_id=args.model_id,
            timeout_seconds=args.timeout_seconds,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    for filename in OUTPUT_FILES:
        print(f"wrote: {args.out / filename}")
    print(f"run_mode: {report['run_mode']}")
    print(f"overall_verdict: {report['overall_verdict']}")
    print(f"promotion_verdict: {report['promotion_verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
