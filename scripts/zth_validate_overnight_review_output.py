#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ALLOWED_VERDICTS = {"pass", "fail", "incomplete"}
ALLOWED_REVIEW_STATES = {"complete", "incomplete"}
ALLOWED_VERIFICATION = {"pass", "fail", "not_applicable", "not_run"}


def _is_repo_relative(path: str) -> bool:
    return not path.startswith("/") and ".." not in path


def _path_allowed(path: str, allow_paths: list[str]) -> bool:
    return any(path == p or path.startswith(p.rstrip("/") + "/") for p in allow_paths)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(payload: dict, *, deadline_reached: bool, allow_paths: list[str]) -> tuple[str, list[str]]:
    errors: list[str] = []
    if set(payload) != {"verdict", "review_state", "changed_paths", "verification", "evidence", "notes"}:
        errors.append("exact_keys")
        return "fail", errors
    if payload["verdict"] not in ALLOWED_VERDICTS:
        errors.append("verdict_enum")
    if payload["review_state"] not in ALLOWED_REVIEW_STATES:
        errors.append("review_state_enum")
    if not isinstance(payload["changed_paths"], list):
        errors.append("changed_paths_type")
    if not isinstance(payload["verification"], dict):
        errors.append("verification_type")
    if not isinstance(payload["evidence"], list) or not payload["evidence"]:
        errors.append("evidence_required")
    if not isinstance(payload["notes"], str) or not payload["notes"].strip():
        errors.append("notes_required")
    required_v = {"raw_output_structure", "changed_files_against_allowlist", "narrowest_relevant_local_checks"}
    if isinstance(payload.get("verification"), dict):
        if set(payload["verification"]) != required_v:
            errors.append("verification_keys")
        for key in required_v:
            if payload["verification"].get(key) not in ALLOWED_VERIFICATION:
                errors.append(f"{key}_enum")
    for path in payload.get("changed_paths", []):
        if not isinstance(path, str) or not _is_repo_relative(path):
            errors.append("changed_paths_repo_relative")
            break
        if allow_paths and not _path_allowed(path, allow_paths):
            errors.append("changed_paths_allowlist")
            break
    repo_root = Path(os.environ.get("ZTH_REPO", Path.cwd()))
    for item in payload.get("evidence", []):
        if not isinstance(item, dict):
            errors.append("evidence_keys")
            break
        path = item["path"]
        observation = item["observation"]
        existence = item.get("existence")
        if set(item) != {"path", "observation", "existence"}:
            errors.append("evidence_keys")
            break
        if not isinstance(path, str) or not _is_repo_relative(path):
            errors.append("evidence_path")
            break
        if not isinstance(observation, str) or not observation.strip():
            errors.append("evidence_observation")
            break
        if existence not in {"present", "absent"}:
            errors.append("evidence_existence")
            break
        exists = (repo_root / path).exists()
        if existence == "present" and not exists:
            errors.append("evidence_path_missing")
            break
        if existence == "absent" and exists:
            errors.append("evidence_path_present")
            break
        if not _path_allowed(path, allow_paths):
            errors.append("evidence_allowlist")
            break
    notes = payload.get("notes", "")
    normalized = notes.lower()
    if deadline_reached:
        if "deadline not reached" in normalized:
            errors.append("deadline_contradiction")
    else:
        if "deadline reached" in normalized and "deadline not reached" not in normalized:
            errors.append("deadline_contradiction")
    if any(token in normalized for token in ["waiting", "pending processing", "will review"]):
        errors.append("placeholder_notes")
    if not errors and payload["review_state"] == "complete" and payload["verdict"] in {"pass", "fail"}:
        result = "ready_for_review"
    elif not errors and payload["review_state"] == "incomplete" and payload["verdict"] == "incomplete":
        result = "incomplete"
    elif "deadline_contradiction" in errors:
        result = "semantic_validation_failed"
    elif "evidence_required" in errors or "notes_required" in errors:
        result = "semantic_validation_failed"
    elif "exact_keys" in errors or "verification_keys" in errors or "verdict_enum" in errors or "review_state_enum" in errors or "evidence_keys" in errors:
        result = "structure_valid"
    else:
        result = "semantic_validation_failed"
    return result, errors


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: validate <raw_output.json> <deadline_reached:true|false> [allowed_path ...]", file=sys.stderr)
        return 2
    payload = load(Path(sys.argv[1]))
    deadline_reached = sys.argv[2].lower() == "true"
    allow_paths = sys.argv[3:]
    result, errors = validate(payload, deadline_reached=deadline_reached, allow_paths=allow_paths)
    print(json.dumps({"state": result, "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
