"""Model-free relation-object IR selection utilities."""

from __future__ import annotations

from typing import Any


def normalize_text(value: Any) -> str:
    return " ".join(str(value).casefold().strip().split())


def direct_target_binding(relation: dict[str, str], requested_target: str) -> bool:
    """Only direct_object equality establishes target binding."""
    return normalize_text(relation["direct_object"]) == normalize_text(requested_target)


def select_direct_target(relations: list[dict[str, str]], requested_target: str) -> dict[str, Any]:
    matches = [index for index, relation in enumerate(relations) if direct_target_binding(relation, requested_target)]
    if len(matches) == 1:
        index = matches[0]
        return {"selected_operation": relations[index]["action"], "selected_index": index, "classification": "DIRECT_TARGET_BINDING"}
    if len(matches) > 1:
        return {"selected_operation": None, "selected_index": None, "classification": "AMBIGUOUS_DIRECT_TARGET_BINDING"}
    return {"selected_operation": None, "selected_index": None, "classification": "NO_DIRECT_TARGET_BINDING"}
