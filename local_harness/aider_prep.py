#!/usr/bin/env python3
"""Prompt packing, read-input preparation, and preflight helpers for Aider runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def ensure_trailing_newline(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


def write_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(ensure_trailing_newline(content), encoding="utf-8")


def scaffold_required_files(run_folder: Path) -> None:
    write_if_missing(
        run_folder / "TASK.md",
        "# Local Agent Task\n\nPopulate this audit record before promoting the run.\n",
    )
    write_if_missing(
        run_folder / "INPUT.md",
        "# Input Bundle\n\nList the files, excerpts, or repo paths given to the worker.\n",
    )
    write_if_missing(
        run_folder / "MODEL_REQUEST.md",
        "# Model Request\n\nWrite the compact Aider prompt here.\n",
    )


def missing_inputs(run_folder: Path, required_input_files: Sequence[str]) -> list[str]:
    return [name for name in required_input_files if not (run_folder / name).is_file()]


def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


def resolve_project_path(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def compact_request_text(prompt_text: str, editable_files: Sequence[str], max_chars: int) -> str:
    lines = [" ".join(line.strip().split()) for line in prompt_text.splitlines() if line.strip()]
    output_lines = ["Task:"]
    for line in lines:
        if line.startswith(("- ", "* ")):
            normalized = line
        elif line.endswith(":"):
            normalized = line
        else:
            normalized = f"- {line}"

        tentative = "\n".join(output_lines + [normalized])
        if len(tentative) > max_chars:
            break
        output_lines.append(normalized)

    output_lines.extend(
        [
            "Editable files:",
            *[f"- {path}" for path in editable_files],
            "Gemma local rules:",
            "- Edit only the listed files.",
            "- Do not narrate plan or analysis.",
            "- Return only valid Aider edits.",
        ]
    )

    compact = "\n".join(output_lines)
    if len(compact) <= max_chars:
        return compact + "\n"

    clipped = compact[: max_chars - 4].rstrip() + "...\n"
    return clipped


def build_effective_prompt(args: Any, prompt_text: str) -> tuple[str, str]:
    if args.compact_request:
        return (
            compact_request_text(prompt_text, args.files, args.compact_request_max_chars),
            "compacted",
        )
    return (ensure_trailing_newline(prompt_text), "verbatim")


def estimate_file_tokens(file_paths: Sequence[str]) -> int:
    total = 0
    for file_path in file_paths:
        resolved = resolve_project_path(file_path)
        if resolved.is_file():
            total += estimate_tokens(resolved.read_text(encoding="utf-8", errors="replace"))
    return total


def compute_safe_input_budget(args: Any) -> int | None:
    if args.context_window is None or args.completion_reserve is None:
        return None
    return max(args.context_window - args.completion_reserve, 0)


def compute_available_read_tokens(args: Any, effective_prompt: str) -> int | None:
    if not args.fit_read_context:
        return None

    safe_input_budget = compute_safe_input_budget(args)
    if safe_input_budget is None:
        return None

    non_read_tokens = (
        estimate_tokens(effective_prompt)
        + estimate_file_tokens(args.files)
        + max(args.map_tokens, 0)
        + max(args.protocol_overhead_tokens, 0)
    )
    return max(safe_input_budget - non_read_tokens, 0)


def build_read_snippet_text(
    read_path: str,
    source_lines: Sequence[str],
    max_lines: int | None,
    max_chars: int | None,
) -> tuple[str, dict[str, Any]]:
    candidate_lines = list(source_lines if max_lines is None else source_lines[:max_lines])
    output_lines = [
        "# Read-only snippet",
        f"# Source: {read_path}",
        "",
    ]
    kept_count = 0

    for line in candidate_lines:
        tentative = "\n".join(output_lines + [line]) + "\n"
        if max_chars is not None and len(tentative) > max_chars:
            break
        output_lines.append(line)
        kept_count += 1

    truncated = kept_count < len(source_lines)
    if truncated:
        trailer_lines = ["", f"[truncated after {kept_count} lines]"]
        tentative = "\n".join(output_lines + trailer_lines) + "\n"
        if max_chars is None or len(tentative) <= max_chars:
            output_lines.extend(trailer_lines)

    snippet_text = "\n".join(output_lines) + "\n"
    metadata = {
        "source_line_count": len(source_lines),
        "kept_line_count": kept_count,
        "prepared_char_count": len(snippet_text),
        "prepared_estimated_tokens": estimate_tokens(snippet_text),
        "truncated": truncated,
    }
    return (snippet_text, metadata)


def prepare_read_inputs(
    args: Any,
    run_folder: Path,
    effective_prompt: str,
) -> tuple[list[str], list[dict[str, Any]]]:
    read_budget_tokens = compute_available_read_tokens(args, effective_prompt)
    use_snippets = args.read_head_lines is not None or read_budget_tokens is not None
    if not use_snippets:
        return (list(args.read), [{"source": path, "mode": "verbatim"} for path in args.read])

    snippet_dir = run_folder / "00_read_snippets"
    snippet_dir.mkdir(parents=True, exist_ok=True)
    prepared_paths: list[str] = []
    metadata: list[dict[str, Any]] = []
    total_char_budget = None if read_budget_tokens is None else max(read_budget_tokens * 4, 0)
    remaining_chars = total_char_budget
    remaining_files = len(args.read)

    for index, read_path in enumerate(args.read, start=1):
        source_path = resolve_project_path(read_path)
        lines = source_path.read_text(encoding="utf-8", errors="replace").splitlines()
        snippet_path = snippet_dir / f"{index:02d}_{source_path.name}"
        char_budget = None
        if remaining_chars is not None and remaining_files > 0:
            char_budget = max(remaining_chars // remaining_files, 96)

        snippet_text, snippet_metadata = build_read_snippet_text(
            read_path,
            lines,
            args.read_head_lines,
            char_budget,
        )
        snippet_path.write_text(snippet_text, encoding="utf-8")
        prepared_paths.append(str(snippet_path))
        if remaining_chars is not None:
            remaining_chars = max(remaining_chars - len(snippet_text), 0)
            remaining_files -= 1
        metadata.append(
            {
                "source": read_path,
                "prepared_path": str(snippet_path),
                "mode": "fit-head" if read_budget_tokens is not None else "head",
                "char_budget": char_budget,
                "read_budget_tokens": read_budget_tokens,
                **snippet_metadata,
            }
        )

    return (prepared_paths, metadata)


def build_aider_read_inputs(
    args: Any,
    run_folder: Path,
    prepared_reads: Sequence[str],
    read_metadata: Sequence[dict[str, Any]],
) -> tuple[list[str], dict[str, Any] | None]:
    if not args.bundle_read_inputs or len(prepared_reads) <= 1:
        return (list(prepared_reads), None)

    snippet_dir = run_folder / "00_read_snippets"
    bundle_path = snippet_dir / "00_READ_BUNDLE.md"
    sections = ["# Bundled read-only context", ""]

    for index, (prepared_path, metadata) in enumerate(zip(prepared_reads, read_metadata, strict=True), start=1):
        prepared_text = resolve_project_path(prepared_path).read_text(encoding="utf-8", errors="replace")
        prepared_lines = prepared_text.splitlines()
        bundle_lines = prepared_lines
        if len(prepared_lines) >= 3 and prepared_lines[0] == "# Read-only snippet":
            bundle_lines = prepared_lines[3:]

        sections.append(f"## Source {index}: {metadata['source']}")
        sections.append("")
        sections.append("\n".join(bundle_lines).rstrip())
        sections.append("")

    bundle_text = "\n".join(sections).rstrip() + "\n"
    bundle_path.write_text(bundle_text, encoding="utf-8")
    bundle_metadata = {
        "bundle_path": str(bundle_path),
        "source_count": len(prepared_reads),
        "bundle_char_count": len(bundle_text),
        "bundle_estimated_tokens": estimate_tokens(bundle_text),
    }
    return ([str(bundle_path)], bundle_metadata)


def should_inline_read_digest(args: Any, read_metadata: Sequence[dict[str, Any]]) -> bool:
    if not args.inline_read_digest or not read_metadata:
        return False
    if len(read_metadata) > 1:
        return True

    total_prepared_tokens = sum(int(metadata.get("prepared_estimated_tokens", 0)) for metadata in read_metadata)
    return total_prepared_tokens > args.inline_read_digest_token_threshold


def build_inline_read_digest(
    args: Any,
    run_folder: Path,
    prepared_reads: Sequence[str],
    read_metadata: Sequence[dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    digest_lines = ["Read-only digest:"]
    chars_per_file = max(args.inline_read_digest_chars_per_file, 0)

    for prepared_path, metadata in zip(prepared_reads, read_metadata, strict=True):
        prepared_text = resolve_project_path(prepared_path).read_text(encoding="utf-8", errors="replace")
        prepared_lines = prepared_text.splitlines()
        body_lines = prepared_lines[3:] if len(prepared_lines) >= 3 and prepared_lines[0] == "# Read-only snippet" else prepared_lines
        excerpt = " ".join(
            line.strip()
            for line in body_lines
            if line.strip() and not line.startswith("[truncated")
        )
        if chars_per_file:
            excerpt = excerpt[:chars_per_file].rstrip()

        entry = f"- {metadata['source']}"
        if excerpt:
            entry += f": {excerpt}"
        digest_lines.append(entry)

    digest_text = "\n".join(digest_lines) + "\n"
    digest_path = run_folder / "AIDER_READ_DIGEST.md"
    digest_path.write_text(digest_text, encoding="utf-8")
    metadata = {
        "digest_path": str(digest_path),
        "source_count": len(read_metadata),
        "digest_char_count": len(digest_text),
        "digest_estimated_tokens": estimate_tokens(digest_text),
    }
    return (digest_text, metadata)


def build_preflight(
    args: Any,
    effective_prompt: str,
    prepared_reads: Sequence[str],
    read_metadata: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []

    def add_item(label: str, path: str | None, text: str) -> None:
        items.append(
            {
                "label": label,
                "path": path,
                "chars": len(text),
                "estimated_tokens": estimate_tokens(text),
            }
        )

    add_item("prompt", None, effective_prompt)

    for file_path in args.files:
        resolved = resolve_project_path(file_path)
        if resolved.is_file():
            text = resolved.read_text(encoding="utf-8", errors="replace")
            add_item("editable_file", file_path, text)
        else:
            items.append(
                {
                    "label": "editable_file",
                    "path": file_path,
                    "chars": 0,
                    "estimated_tokens": 0,
                    "missing": True,
                }
            )

    for path in prepared_reads:
        resolved = resolve_project_path(path)
        if resolved.is_file():
            text = resolved.read_text(encoding="utf-8", errors="replace")
            add_item("read_only_file", path, text)

    estimated_total = sum(item["estimated_tokens"] for item in items) + max(args.map_tokens, 0)
    estimated_total_with_overhead = estimated_total + max(args.protocol_overhead_tokens, 0)
    safe_input_budget = compute_safe_input_budget(args)
    within_budget = None
    if safe_input_budget is not None:
        within_budget = estimated_total_with_overhead <= safe_input_budget

    sorted_items = sorted(items, key=lambda item: item["estimated_tokens"], reverse=True)
    editable_file_count = len(args.files)
    read_only_file_count = len(read_metadata)
    read_only_estimated_tokens = sum(
        item["estimated_tokens"] for item in items if item["label"] == "read_only_file"
    )
    validated_shape_match = (
        args.profile == "gemma-local"
        and args.map_tokens == 0
        and args.compact_request is True
        and editable_file_count <= 10
        and read_only_file_count <= 1
        and estimated_total <= 500
        and within_budget is True
    )
    return {
        "profile": args.profile,
        "model": args.model,
        "openai_api_base": args.openai_api_base,
        "map_tokens": args.map_tokens,
        "protocol_overhead_tokens": args.protocol_overhead_tokens,
        "context_window": args.context_window,
        "completion_reserve": args.completion_reserve,
        "safe_input_budget": safe_input_budget,
        "estimated_total_input_tokens": estimated_total,
        "estimated_total_with_overhead_tokens": estimated_total_with_overhead,
        "within_budget": within_budget,
        "prompt_mode": args.prompt_mode,
        "editable_file_count": editable_file_count,
        "read_only_file_count": read_only_file_count,
        "read_only_estimated_tokens": read_only_estimated_tokens,
        "validated_shape_match": validated_shape_match,
        "original_prompt_est_tokens": estimate_tokens(args.original_prompt_text),
        "effective_prompt_est_tokens": estimate_tokens(effective_prompt),
        "read_inputs": list(read_metadata),
        "largest_inputs": sorted_items[:5],
    }


def build_preflight_output(preflight: dict[str, Any], blocked: bool, preflight_only: bool) -> str:
    status = "blocked" if blocked else "ok"
    if preflight_only and not blocked:
        status = "preflight_only"
    lines = [
        "# Aider Preflight",
        "",
        f"- Status: {status}",
        f"- Profile: {preflight['profile']}",
        f"- Model: {preflight['model']}",
        f"- Prompt mode: {preflight['prompt_mode']}",
        f"- Editable files: {preflight['editable_file_count']}",
        f"- Read-only files: {preflight['read_only_file_count']}",
        f"- Estimated total input tokens: {preflight['estimated_total_input_tokens']}",
        f"- Protocol overhead tokens: {preflight['protocol_overhead_tokens']}",
        f"- Estimated total with overhead: {preflight['estimated_total_with_overhead_tokens']}",
        f"- Repo map tokens: {preflight['map_tokens']}",
        f"- Matches validated pilot shape: {preflight['validated_shape_match']}",
    ]
    direct_edit_candidate = preflight.get("direct_edit_candidate")
    if isinstance(direct_edit_candidate, dict):
        lines.append(f"- Direct-edit eligible: {direct_edit_candidate.get('eligible')}")
        lines.append(f"- Direct-edit reason: {direct_edit_candidate.get('reason')}")
        if direct_edit_candidate.get("operation"):
            lines.append(f"- Direct-edit operation: {direct_edit_candidate.get('operation')}")
        if direct_edit_candidate.get("target_file"):
            lines.append(f"- Direct-edit target: {direct_edit_candidate['target_file']}")
        if direct_edit_candidate.get("file_bytes") is not None:
            lines.append(
                "- Direct-edit file bytes: "
                f"{direct_edit_candidate['file_bytes']} / {direct_edit_candidate['file_size_limit_bytes']}"
            )
        if direct_edit_candidate.get("start_anchor_match_count") is not None:
            lines.append(
                "- Direct-edit anchor counts: "
                f"start={direct_edit_candidate['start_anchor_match_count']}, "
                f"end={direct_edit_candidate.get('end_anchor_match_count')}"
            )
    if "direct_edit_budget_bypass_available" in preflight:
        lines.append(
            "- Direct-edit bypasses Aider budget gate: "
            f"{preflight['direct_edit_budget_bypass_available']}"
        )
    if preflight["safe_input_budget"] is not None:
        lines.append(f"- Safe input budget: {preflight['safe_input_budget']}")
        lines.append(f"- Within budget: {preflight['within_budget']}")
    lines.append("")
    lines.append("## Largest Inputs")
    for item in preflight["largest_inputs"]:
        path = item["path"] or "(prompt)"
        lines.append(f"- {item['label']}: {path} ({item['estimated_tokens']} est tokens)")
    lines.append("")
    if blocked:
        lines.append("Preflight blocked the run. Reduce prompt size, trim read-only inputs, or override the budget gate.")
    elif preflight_only and preflight.get("direct_edit_budget_bypass_available") and preflight["within_budget"] is False:
        lines.append("Preflight completed without running Aider. Direct-edit is eligible, so the manager can bypass the Aider budget gate.")
    elif preflight_only:
        lines.append("Preflight completed without running Aider.")
    return "\n".join(lines) + "\n"
