"""Build reviewable curriculum candidates from classified failure events."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Iterable

from .common import read_jsonl, sha256_text, write_jsonl


SYSTEM_PROMPTS = {
    "invalid_json": "Return only valid JSON that satisfies the requested contract.",
    "empty_output": "Return a complete response that satisfies the requested task.",
    "placeholder_leak": "Return final content only. Do not include placeholders.",
    "unsupported_certainty": "Use only supported claims. Do not overstate certainty.",
    "underspecified_output": "Return a specific, complete answer with enough detail to be useful.",
    "unclassified_failure": "Return an answer that corrects the observed failure.",
}


def clean_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def target_behavior_for_failure_mode(failure_mode: str) -> str:
    return SYSTEM_PROMPTS.get(failure_mode, SYSTEM_PROMPTS["unclassified_failure"])


def corrected_output_from_event(event: dict[str, Any]) -> str:
    for key in ("corrected_output", "expected_output", "gold_output", "desired_output"):
        value = clean_text(event.get(key))
        if value:
            return value
    return ""


def user_message_from_failure(event: dict[str, Any]) -> str:
    prompt = clean_text(event.get("prompt"))
    expected_contract = clean_text(event.get("expected_contract"))
    failure_mode = clean_text(event.get("failure_mode")) or "unclassified_failure"
    raw_output = clean_text(event.get("raw_output"))

    parts = [
        "Rewrite the failed model response so it satisfies the task and contract.",
        "",
        "Original task:",
        prompt or "(missing prompt)",
        "",
        "Expected contract:",
        expected_contract or "(no explicit contract provided)",
        "",
        "Observed failure mode:",
        failure_mode,
        "",
        "Failed model output:",
        raw_output or "(empty output)",
    ]
    return "\n".join(parts)


def build_candidate_from_failure(event: dict[str, Any]) -> dict[str, Any]:
    failure_event_id = clean_text(event.get("id")) or "unknown_failure"
    cycle_id = clean_text(event.get("cycle_id")) or "unknown_cycle"
    failure_mode = clean_text(event.get("failure_mode")) or "unclassified_failure"

    candidate_id = "candidate_" + sha256_text(f"{cycle_id}|{failure_event_id}")[:12]

    messages = [
        {
            "role": "system",
            "content": target_behavior_for_failure_mode(failure_mode),
        },
        {
            "role": "user",
            "content": user_message_from_failure(event),
        },
    ]

    corrected_output = corrected_output_from_event(event)
    review_status = "needs_revision"
    if corrected_output:
        messages.append({"role": "assistant", "content": corrected_output})
        review_status = "candidate"

    return {
        "id": candidate_id,
        "failure_event_id": failure_event_id,
        "cycle_id": cycle_id,
        "task_type": "supervised_failure_correction",
        "target_behavior": target_behavior_for_failure_mode(failure_mode),
        "messages": messages,
        "failure_modes_targeted": [failure_mode],
        "review_status": review_status,
        "provenance": {
            "source_failure_event_id": failure_event_id,
            "source_run_id": clean_text(event.get("source_run_id")),
            "model_id": clean_text(event.get("model_id")),
            "probe_id": clean_text(event.get("probe_id")),
            "prompt_hash": clean_text(event.get("prompt_hash")),
            "raw_output_hash": clean_text(event.get("raw_output_hash")),
            "source_artifact_paths": event.get("source_artifact_paths", []),
        },
    }


def build_curriculum_candidates(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [build_candidate_from_failure(event) for event in events]


def build_curriculum_jsonl(input_path: str | Path, output_path: str | Path) -> list[dict[str, Any]]:
    candidates = build_curriculum_candidates(read_jsonl(input_path))
    write_jsonl(output_path, candidates)
    return candidates


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Classified failure events JSONL")
    parser.add_argument("--output", required=True, help="Curriculum candidates JSONL")
    args = parser.parse_args(argv)

    build_curriculum_jsonl(args.input, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
