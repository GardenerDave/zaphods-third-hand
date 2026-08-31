#!/usr/bin/env python3
"""Model-free prompt patch library for supervised prompt-packet assembly.

A prompt patch records a known failure signature, a conservative prompt
correction, the output fields the correction requires, and the validator
expectations that make the correction checkable. The library loads, validates,
filters, and renders patches. It performs no model calls, no training, no
curriculum capture, and no promotion.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ALLOWED_STATUSES = {"candidate", "active", "deprecated"}
DEFAULT_SELECTABLE_STATUSES = {"candidate", "active"}
ALLOWED_SELECTION_POLICIES = {None, "explicit_only"}
ALLOWED_STAGES = {
    "intake",
    "triage",
    "target_selection",
    "prompt_assembly",
    "output_contract",
    "validation",
    "review",
}
REQUIRED_PATCH_KEYS = {
    "patch_id",
    "title",
    "status",
    "failure_signature",
    "applies_to",
    "prompt_delta",
    "required_output_fields",
    "validator_expectations",
}
REQUIRED_APPLIES_TO_KEYS = {"stage", "task_type", "model_size"}
FORBIDDEN_AUTHORITY_KEYS = {
    "auto_train",
    "auto_promote",
    "auto_curriculum",
    "execution_authority",
}


class PromptPatchError(ValueError):
    """Raised when a prompt patch is malformed."""


def _require_nonempty_str(patch: dict[str, Any], key: str) -> str:
    value = patch.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PromptPatchError(f"patch field {key!r} must be a non-empty string")
    return value


def _require_str_list(patch: dict[str, Any], key: str) -> list[str]:
    value = patch.get(key)
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(item, str) and item.strip() for item in value)
    ):
        raise PromptPatchError(f"patch field {key!r} must be a non-empty list of strings")
    return value


def validate_patch(patch: Any) -> dict[str, Any]:
    """Validate one prompt patch dictionary. Returns the patch on success."""
    if not isinstance(patch, dict):
        raise PromptPatchError("patch must be a JSON object")
    missing = sorted(REQUIRED_PATCH_KEYS - set(patch))
    if missing:
        raise PromptPatchError(f"patch missing required fields: {', '.join(missing)}")
    forbidden = sorted(FORBIDDEN_AUTHORITY_KEYS & set(patch))
    if forbidden:
        raise PromptPatchError(
            f"patch contains forbidden authority fields: {', '.join(forbidden)}"
        )

    _require_nonempty_str(patch, "patch_id")
    _require_nonempty_str(patch, "title")
    _require_nonempty_str(patch, "prompt_delta")
    _require_str_list(patch, "failure_signature")
    _require_str_list(patch, "required_output_fields")
    _require_str_list(patch, "validator_expectations")
    selection_policy = patch.get("selection_policy")
    if selection_policy not in ALLOWED_SELECTION_POLICIES:
        raise PromptPatchError(
            "patch selection_policy must be omitted or one of: explicit_only"
        )

    status = _require_nonempty_str(patch, "status")
    if status not in ALLOWED_STATUSES:
        raise PromptPatchError(
            f"patch status {status!r} not in allowed statuses: {sorted(ALLOWED_STATUSES)}"
        )

    applies_to = patch.get("applies_to")
    if not isinstance(applies_to, dict):
        raise PromptPatchError("patch field 'applies_to' must be an object")
    missing_applies = sorted(REQUIRED_APPLIES_TO_KEYS - set(applies_to))
    if missing_applies:
        raise PromptPatchError(
            f"patch applies_to missing required fields: {', '.join(missing_applies)}"
        )
    stages = _require_str_list(applies_to, "stage")
    unknown_stages = sorted(set(stages) - ALLOWED_STAGES)
    if unknown_stages:
        raise PromptPatchError(
            f"patch applies_to.stage has unknown stages: {', '.join(unknown_stages)}"
        )
    _require_str_list(applies_to, "task_type")
    _require_str_list(applies_to, "model_size")
    return patch


class PromptPatchLibrary:
    """In-memory, validated collection of prompt patches."""

    def __init__(self) -> None:
        self._patches: dict[str, dict[str, Any]] = {}

    def add_patch(self, patch: dict[str, Any]) -> dict[str, Any]:
        validated = validate_patch(patch)
        patch_id = validated["patch_id"]
        if patch_id in self._patches:
            raise PromptPatchError(f"duplicate patch_id: {patch_id}")
        self._patches[patch_id] = validated
        return validated

    def load_file(self, path: Path) -> dict[str, Any]:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return self.add_patch(payload)

    def load_dir(self, directory: Path) -> list[dict[str, Any]]:
        loaded = []
        for path in sorted(Path(directory).glob("*.json")):
            loaded.append(self.load_file(path))
        return loaded

    @property
    def patch_ids(self) -> list[str]:
        return sorted(self._patches)

    def get(self, patch_id: str) -> dict[str, Any]:
        if patch_id not in self._patches:
            raise KeyError(f"unknown patch_id: {patch_id}")
        return self._patches[patch_id]

    def _selectable(self, include_deprecated: bool) -> list[dict[str, Any]]:
        statuses = set(DEFAULT_SELECTABLE_STATUSES)
        if include_deprecated:
            statuses.add("deprecated")
        return [
            patch
            for _, patch in sorted(self._patches.items())
            if patch["status"] in statuses and patch.get("selection_policy") != "explicit_only"
        ]

    def selectable_patch_ids(self, *, include_deprecated: bool = False) -> list[str]:
        return [patch["patch_id"] for patch in self._selectable(include_deprecated)]

    def filter_by_stage(
        self, stage: str, *, include_deprecated: bool = False
    ) -> list[dict[str, Any]]:
        return [
            patch
            for patch in self._selectable(include_deprecated)
            if stage in patch["applies_to"]["stage"]
        ]

    def filter_by_task_type(
        self, task_type: str, *, include_deprecated: bool = False
    ) -> list[dict[str, Any]]:
        return [
            patch
            for patch in self._selectable(include_deprecated)
            if task_type in patch["applies_to"]["task_type"]
            or "any" in patch["applies_to"]["task_type"]
        ]

    def filter_by_failure_signature(
        self, keyword: str, *, include_deprecated: bool = False
    ) -> list[dict[str, Any]]:
        needle = keyword.strip().lower()
        if not needle:
            raise PromptPatchError("failure signature keyword must be non-empty")
        return [
            patch
            for patch in self._selectable(include_deprecated)
            if any(needle in signature.lower() for signature in patch["failure_signature"])
        ]


def render_prompt_deltas(patches: list[dict[str, Any]]) -> str:
    """Render selected patch deltas into one prompt-packet-safe text block."""
    if not patches:
        return "No prompt patches selected.\n"
    lines = ["## Applied Prompt Patches", ""]
    for patch in patches:
        lines.extend(
            [
                f"### Patch: {patch['patch_id']} ({patch['status']})",
                "",
                patch["prompt_delta"].strip(),
                "",
                "Required output fields: " + ", ".join(patch["required_output_fields"]),
                "",
            ]
        )
    lines.extend(
        [
            "These patches constrain output shape only. They grant no execution,",
            "promotion, training, or curriculum-capture authority.",
            "",
        ]
    )
    return "\n".join(lines)


def render_validator_expectations(patches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return validator expectation records for downstream model-free checks."""
    return [
        {
            "patch_id": patch["patch_id"],
            "validator_expectations": list(patch["validator_expectations"]),
            "required_output_fields": list(patch["required_output_fields"]),
        }
        for patch in patches
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--patch-dir", required=True, type=Path)
    parser.add_argument("--stage")
    parser.add_argument("--task-type")
    parser.add_argument("--failure-keyword")
    parser.add_argument("--include-deprecated", action="store_true")
    parser.add_argument("--render", action="store_true", help="print rendered prompt deltas")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    library = PromptPatchLibrary()
    try:
        library.load_dir(args.patch_dir)
        selected = library._selectable(args.include_deprecated)
        if args.stage:
            selected = [p for p in selected if p in library.filter_by_stage(args.stage, include_deprecated=args.include_deprecated)]
        if args.task_type:
            selected = [p for p in selected if p in library.filter_by_task_type(args.task_type, include_deprecated=args.include_deprecated)]
        if args.failure_keyword:
            selected = [p for p in selected if p in library.filter_by_failure_signature(args.failure_keyword, include_deprecated=args.include_deprecated)]
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 1
    if args.render:
        print(render_prompt_deltas(selected))
    else:
        print(json.dumps({"selected_patch_ids": [p["patch_id"] for p in selected]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
