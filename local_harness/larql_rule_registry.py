#!/usr/bin/env python3
"""Validate and summarize the completed LARQL rule registry."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_TOP_LEVEL_KEYS = {"registry_id", "rules"}
REQUIRED_ENTRY_KEYS = {
    "rule_family_id",
    "source_failure_id",
    "candidate_id",
    "rule_id",
    "status",
    "current_lifecycle_step",
    "allowed_next_step",
    "closeout_report",
    "installed_rule_artifact",
    "json_contract",
    "evidence_paths",
}
REQUIRED_RULE_IDS = {
    "absence_of_evidence_file_authority_v0",
    "unsupported_certainty_scope_claim_v0",
    "unsupported_file_target_authority_v0",
}


def load_registry(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("registry must be a JSON object")
    if not REQUIRED_TOP_LEVEL_KEYS.issubset(payload):
        missing = sorted(REQUIRED_TOP_LEVEL_KEYS - set(payload))
        raise ValueError(f"registry missing required top-level keys: {', '.join(missing)}")
    if not isinstance(payload["rules"], list):
        raise ValueError("registry rules must be a list")
    return payload


def validate_registry(registry: dict[str, Any], repo_root: Path) -> dict[str, bool]:
    rules = registry["rules"]
    checks: dict[str, bool] = {
        "registry_has_three_rules": len(rules) == 3,
        "registry_has_unique_rule_ids": False,
        "registry_has_required_rule_ids": False,
        "registry_has_all_required_entries": True,
        "registry_has_valid_json_contracts": True,
        "registry_docs_closeout_links_exist": True,
    }

    seen_rule_ids: set[str] = set()
    required_rule_ids = set(REQUIRED_RULE_IDS)

    for entry in rules:
        if not isinstance(entry, dict):
            checks["registry_has_all_required_entries"] = False
            continue
        if not REQUIRED_ENTRY_KEYS.issubset(entry):
            checks["registry_has_all_required_entries"] = False
        rule_id = entry.get("rule_id")
        if not isinstance(rule_id, str):
            checks["registry_has_all_required_entries"] = False
        elif rule_id in seen_rule_ids:
            checks["registry_has_unique_rule_ids"] = False
        else:
            seen_rule_ids.add(rule_id)

        json_contract = entry.get("json_contract")
        if not isinstance(json_contract, dict):
            checks["registry_has_valid_json_contracts"] = False

        closeout_report = entry.get("closeout_report")
        if isinstance(closeout_report, str) and closeout_report.startswith("docs/"):
            if not (repo_root / closeout_report).exists():
                checks["registry_docs_closeout_links_exist"] = False
        else:
            checks["registry_has_all_required_entries"] = False

    checks["registry_has_unique_rule_ids"] = len(seen_rule_ids) == len(rules)
    checks["registry_has_required_rule_ids"] = set(seen_rule_ids) == required_rule_ids
    return checks


def render_markdown(registry: dict[str, Any], checks: dict[str, bool]) -> str:
    lines = [
        "# LARQL Rule Registry Status",
        "",
        f"Registry id: `{registry['registry_id']}`",
        "",
        "## Lifecycle status",
        "",
        "| Rule id | Status | Current step | Next step | Transport repair required | Failed probe preserved | Closeout |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for entry in registry["rules"]:
        closeout_label = Path(entry["closeout_report"]).name
        lines.append(
            "| {rule_id} | {status} | {current_lifecycle_step} | {allowed_next_step} | {transport} | {failed} | {closeout} |".format(
                rule_id=entry["rule_id"],
                status=entry["status"],
                current_lifecycle_step=entry["current_lifecycle_step"],
                allowed_next_step=entry["allowed_next_step"],
                transport=str(bool(entry.get("transport_repair_required", False))).lower(),
                failed=str(bool(entry.get("failed_probe_preserved", False))).lower(),
                closeout=f"[link]({closeout_label})",
            )
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- The registry is model-free metadata.",
            "- It summarizes the completed hand-built rule trials.",
            "- The unsupported-file-target authority entry records that the first probe was preserved and a transport repair was required.",
            "- The unsupported-file-target authority entry includes `failed_probe_preserved: true` and `transport_repair_required: true`.",
            "- It does not add a new rule or authorize runtime modification.",
            "",
            "## Next machinery step",
            "",
            "Implement a one-command evidence packet collector.",
            "",
            "## Checks",
            "",
            *[f"- `{key}`: `{value}`" for key, value in sorted(checks.items())],
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def write_status(registry_path: Path, out_path: Path) -> dict[str, Any]:
    repo_root = registry_path.resolve().parents[3]
    registry = load_registry(registry_path)
    checks = validate_registry(registry, repo_root)
    if not all(checks.values()):
        raise ValueError("registry validation failed")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    markdown = render_markdown(registry, checks)
    out_path.write_text(markdown, encoding="utf-8")
    return {"registry": registry, "checks": checks, "markdown": markdown}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_status(args.registry, args.out)
    except (OSError, ValueError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
