#!/usr/bin/env python3
"""Build review-only bundles from deduped raw-signal scaffolding."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence


SIGNAL_TYPE_TO_FILE = {
    "current_state": "current_state.md",
    "decision": "decisions.md",
    "open_question": "open_questions.md",
    "rule_or_preference": "rules_and_preferences.md",
    "artifact_or_file": "artifacts_and_files.md",
    "command_or_setting": "commands_and_settings.md",
    "next_action": "next_actions.md",
    "version_change": "version_changes.md",
    "contradiction_candidate": "conflicts.md",
}
FILE_TITLES = {
    "current_state.md": "Current State Candidates",
    "decisions.md": "Decision Candidates",
    "open_questions.md": "Open Question Candidates",
    "rules_and_preferences.md": "Rules And Preferences Candidates",
    "artifacts_and_files.md": "Artifacts And Files Candidates",
    "commands_and_settings.md": "Commands And Settings Candidates",
    "next_actions.md": "Next Action Candidates",
    "version_changes.md": "Version Change Candidates",
    "conflicts.md": "Conflict Candidates",
}
FILE_ORDER = (
    "current_state.md",
    "decisions.md",
    "open_questions.md",
    "rules_and_preferences.md",
    "artifacts_and_files.md",
    "commands_and_settings.md",
    "next_actions.md",
    "version_changes.md",
    "conflicts.md",
)


def ensure_trailing_newline(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_number} must be a JSON object")
        rows.append(row)
    return rows


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]


def append_value_block(lines: list[str], label: str, value: Any) -> None:
    lines.extend([f"{label}:", str(value or ""), ""])


def append_bullet_block(lines: list[str], label: str, values: list[str]) -> None:
    lines.append(f"{label}:")
    if values:
        lines.extend(f"- {value}" for value in values)
    else:
        lines.append("- unknown")
    lines.append("")


def append_review_decision(lines: list[str]) -> None:
    lines.extend(
        [
            "Review decision:",
            "- [ ] Accept",
            "- [ ] Reject",
            "- [ ] Needs rework",
            "- [ ] Superseded",
            "- [ ] Uncertain",
            "",
            "Reviewer notes:",
            "",
        ]
    )


def signal_target_file(signal: dict[str, Any]) -> str:
    signal_type = str(signal.get("signal_type", "current_state"))
    return SIGNAL_TYPE_TO_FILE.get(signal_type, "current_state.md")


def append_signal_candidate(lines: list[str], signal: dict[str, Any], index: int) -> None:
    lines.extend([f"### Candidate {index}", ""])
    append_value_block(lines, "Proposed claim", signal.get("claim", ""))
    append_value_block(lines, "Signal type", signal.get("signal_type", "unknown"))
    append_value_block(lines, "Status", signal.get("status", "unknown"))
    append_value_block(lines, "Confidence", signal.get("confidence", "unknown"))
    append_bullet_block(lines, "Supporting raw signals", string_list(signal.get("supporting_raw_signal_ids")))
    append_bullet_block(lines, "Source conversations", string_list(signal.get("source_conversation_ids")))
    append_bullet_block(lines, "Source chunks", string_list(signal.get("source_chunk_ids")))
    append_review_decision(lines)


def candidate_file_markdown(filename: str, signals: list[dict[str, Any]], conflicts: list[dict[str, Any]]) -> str:
    lines = [f"# {FILE_TITLES[filename]}", "", "Status: review_only", ""]

    normal_signals = [signal for signal in signals if str(signal.get("signal_type", "")) in SIGNAL_TYPE_TO_FILE]
    unclassified = [signal for signal in signals if str(signal.get("signal_type", "")) not in SIGNAL_TYPE_TO_FILE]

    if normal_signals:
        lines.extend(["## Candidates", ""])
        for index, signal in enumerate(normal_signals, start=1):
            append_signal_candidate(lines, signal, index)

    if unclassified:
        lines.extend(["## Unclassified", ""])
        for index, signal in enumerate(unclassified, start=1):
            append_signal_candidate(lines, signal, index)

    contradiction_signals = [
        signal for signal in normal_signals if str(signal.get("signal_type", "")) == "contradiction_candidate"
    ]
    if filename == "conflicts.md" and contradiction_signals and conflicts:
        lines.extend(["## Explicit Conflict Candidates", ""])

    if filename == "conflicts.md" and conflicts:
        if not contradiction_signals:
            lines.extend(["## Conflict Candidates", ""])
        for index, conflict in enumerate(conflicts, start=1):
            lines.extend([f"### Conflict {index}", ""])
            append_value_block(lines, "Conflict id", conflict.get("conflict_id", ""))
            append_value_block(lines, "Topic key", conflict.get("topic_key", ""))
            append_value_block(lines, "Classification", conflict.get("classification", ""))
            claims = conflict.get("claims", [])
            lines.extend(["Claims:", ""])
            if isinstance(claims, list) and claims:
                for claim_index, claim in enumerate(claims, start=1):
                    if not isinstance(claim, dict):
                        continue
                    lines.extend([f"Claim {claim_index}:", ""])
                    append_value_block(lines, "Raw signal id", claim.get("raw_signal_id", ""))
                    append_value_block(lines, "Claim", claim.get("claim", ""))
                    append_value_block(lines, "Status hint", claim.get("status_hint", ""))
            else:
                lines.extend(["- No claims recorded.", ""])
            append_review_decision(lines)

    return ensure_trailing_newline("\n".join(lines).rstrip())


def grouped_signals(deduped_signals: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for signal in deduped_signals:
        grouped.setdefault(signal_target_file(signal), []).append(signal)
    return grouped


def build_review_summary(
    summary: dict[str, Any],
    deduped_count: int,
    duplicate_count: int,
    conflict_count: int,
    candidate_files: list[str],
) -> str:
    raw_count = summary.get("raw_signal_count", 0)
    lines = [
        "# ChatGPT Export Review Bundle",
        "",
        "## Summary",
        "",
        f"Raw signals: {raw_count}",
        f"Deduped signals: {deduped_count}",
        f"Duplicate links: {duplicate_count}",
        f"Conflict candidates: {conflict_count}",
        "",
        "## Review Status",
        "",
        "- [ ] Reviewed deduped signals",
        "- [ ] Reviewed duplicate links",
        "- [ ] Reviewed conflict candidates",
        "- [ ] Accepted selected canonical candidates manually",
        "- [ ] Rejected or deferred uncertain candidates manually",
        "",
        "## Candidate Files",
        "",
    ]
    if candidate_files:
        lines.extend(f"- {path}" for path in candidate_files)
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Safety Notes",
            "",
            "These files are review material only. They are not canonical memory and must not be promoted automatically.",
            "",
        ]
    )
    return ensure_trailing_newline("\n".join(lines).rstrip())


def build_review_bundle(signals_dir: Path, out_dir: Path) -> dict[str, Any]:
    deduped_signals = load_jsonl(signals_dir / "deduped_signals.jsonl")
    duplicate_links = load_jsonl(signals_dir / "duplicate_links.jsonl")
    conflict_candidates = load_jsonl(signals_dir / "conflict_candidates.jsonl")
    dedupe_summary = load_json(signals_dir / "dedupe_summary.json")

    out_dir.mkdir(parents=True, exist_ok=True)
    candidate_dir = out_dir / "canonical_candidates"
    candidate_dir.mkdir(parents=True, exist_ok=True)

    grouped = grouped_signals(deduped_signals)
    candidate_files: list[str] = []
    for filename in FILE_ORDER:
        signals = grouped.get(filename, [])
        conflicts = conflict_candidates if filename == "conflicts.md" else []
        if not signals and not conflicts:
            continue
        candidate_path = candidate_dir / filename
        candidate_path.write_text(candidate_file_markdown(filename, signals, conflicts), encoding="utf-8")
        candidate_files.append(f"canonical_candidates/{filename}")

    review_summary = build_review_summary(
        dedupe_summary,
        len(deduped_signals),
        len(duplicate_links),
        len(conflict_candidates),
        candidate_files,
    )
    (out_dir / "review_summary.md").write_text(review_summary, encoding="utf-8")

    bundle = {
        "deduped_signal_count": len(deduped_signals),
        "duplicate_link_count": len(duplicate_links),
        "conflict_candidate_count": len(conflict_candidates),
        "candidate_file_count": len(candidate_files),
        "candidate_files": candidate_files,
        "review_summary_path": str(out_dir / "review_summary.md"),
        "review_only": True,
    }
    (out_dir / "review_bundle.json").write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return bundle


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build review-only canonical candidate files from deduped signals.")
    parser.add_argument("--signals-dir", required=True, help="Directory containing signal_dedupe.py outputs.")
    parser.add_argument("--out-dir", required=True, help="Directory that will receive review bundle files.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    bundle = build_review_bundle(Path(args.signals_dir), Path(args.out_dir))
    print(f"Review bundle files: {bundle['candidate_file_count']}")
    print(f"Review summary: {Path(args.out_dir) / 'review_summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
