#!/usr/bin/env python3
"""Validate behavior correction card shape without model calls."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence


REQUIRED_FIELDS = (
    "id",
    "title",
    "status",
    "applies_when",
    "correction_instruction",
    "validator_expectations",
    "known_failure_modes",
    "provenance_notes",
    "non_authorities",
)


def load_card(path: Path) -> dict[str, Any]:
    try:
        card = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing card file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in card file: {path}") from exc
    if not isinstance(card, dict):
        raise ValueError("card must be a JSON object")
    return card


def validate_card(card: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in card:
            errors.append(f"missing required field: {field}")

    if card.get("non_authorities") in (None, []):
        errors.append("non_authorities must be present and non-empty")

    if card.get("id") and not isinstance(card["id"], str):
        errors.append("id must be a string")
    if card.get("status") and card["status"] not in {"active", "draft", "held"}:
        errors.append("status must be active, draft, or held")

    for field in (
        "applies_when",
        "correction_instruction",
        "validator_expectations",
        "known_failure_modes",
        "provenance_notes",
        "non_authorities",
    ):
        value = card.get(field)
        if value is not None and not isinstance(value, list):
            errors.append(f"{field} must be a list")

    return errors


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate behavior correction cards.")
    parser.add_argument("card", type=Path)
    args = parser.parse_args(argv)

    try:
        card = load_card(args.card)
        errors = validate_card(card)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
