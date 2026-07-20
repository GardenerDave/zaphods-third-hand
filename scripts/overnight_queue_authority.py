from __future__ import annotations

import json
from pathlib import Path


class AuthorityValidationError(ValueError):
    pass


def _normalize_target(target: str) -> str:
    stripped = target.strip()
    if not stripped:
        raise AuthorityValidationError("empty_or_whitespace_target")
    if stripped.startswith("/"):
        raise AuthorityValidationError("absolute_target")
    if ".." in Path(stripped).parts:
        raise AuthorityValidationError("traversal_target")
    return stripped


def validate_allowed_targets(value: object) -> list[str]:
    if not isinstance(value, list):
        raise AuthorityValidationError("authority_not_array")
    if not value:
        raise AuthorityValidationError("empty_authority")
    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            raise AuthorityValidationError("authority_not_string")
        target = _normalize_target(item)
        if target in seen:
            raise AuthorityValidationError("duplicate_target")
        seen.add(target)
        normalized.append(target)
    return normalized


def load_registry(path: Path) -> dict[str, list[str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    families = payload.get("families")
    if not isinstance(families, dict):
        raise AuthorityValidationError("registry_missing_families")
    result: dict[str, list[str]] = {}
    for family, targets in families.items():
        result[family] = validate_allowed_targets(targets)
    return result


def load_stage_definitions(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise AuthorityValidationError("stage_definitions_not_array")
    defs: list[dict[str, object]] = []
    for item in payload:
        if not isinstance(item, dict):
            raise AuthorityValidationError("stage_definition_not_object")
        for key in ("priority", "slug", "family", "objective"):
            if key not in item or not isinstance(item[key], str) or not item[key].strip():
                raise AuthorityValidationError(f"stage_definition_missing_{key}")
        defs.append(item)
    return defs


def render_queue_template(stage_defs: list[dict[str, object]], registry: dict[str, list[str]]) -> str:
    lines = ["# zth-roadmap-queue-schema: 2"]
    for item in stage_defs:
        family = str(item["family"])
        if family not in registry:
            raise AuthorityValidationError(f"missing_family_authority:{family}")
        allowed = registry[family]
        lines.append(
            "\t".join(
                [
                    str(item["priority"]).strip(),
                    str(item["slug"]).strip(),
                    str(item["objective"]).strip(),
                    json.dumps(allowed, sort_keys=True),
                ]
            )
        )
    return "\n".join(lines) + "\n"
