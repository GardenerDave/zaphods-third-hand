#!/usr/bin/env python3
"""Summarize LARQL lifecycle state from the registry and evidence packets."""

from __future__ import annotations

import argparse
import hashlib
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


def validate_registry(registry: dict[str, Any], repo_root: Path) -> None:
    seen: set[str] = set()
    for entry in registry["rules"]:
        if not isinstance(entry, dict):
            raise ValueError("registry rule entry must be a JSON object")
        if not REQUIRED_ENTRY_KEYS.issubset(entry):
            missing = sorted(REQUIRED_ENTRY_KEYS - set(entry))
            raise ValueError(f"registry entry missing required keys: {', '.join(missing)}")
        if not isinstance(entry["json_contract"], dict):
            raise ValueError("registry json_contract must be a JSON object")
        rule_id = entry["rule_id"]
        if rule_id in seen:
            raise ValueError(f"duplicate rule_id: {rule_id}")
        seen.add(rule_id)
        closeout = entry["closeout_report"]
        if isinstance(closeout, str) and closeout.startswith("docs/") and not (repo_root / closeout).exists():
            raise ValueError(f"missing closeout report: {closeout}")


def sha256_for_path(path: Path) -> str | None:
    if path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    return None


def load_packet_manifest(packet_root: Path, rule_id: str) -> dict[str, Any] | None:
    manifest_path = packet_root / rule_id / "evidence_packet_manifest.json"
    if not manifest_path.exists():
        return None
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"packet manifest must be a JSON object: {manifest_path}")
    required = {"report_type", "rule_id", "evidence_items"}
    if not required.issubset(payload):
        missing = sorted(required - set(payload))
        raise ValueError(f"packet manifest missing required keys: {', '.join(missing)}")
    if payload["report_type"] != "larql_evidence_packet.v0":
        raise ValueError(f"packet manifest has unexpected report_type: {manifest_path}")
    if payload["rule_id"] != rule_id:
        raise ValueError(f"packet manifest rule_id mismatch: {manifest_path}")
    if not isinstance(payload["evidence_items"], list):
        raise ValueError(f"packet manifest evidence_items must be a list: {manifest_path}")
    return payload


def summarize_packet(packet: dict[str, Any] | None) -> dict[str, Any]:
    if packet is None:
        return {"present": False}
    missing_count = sum(1 for item in packet["evidence_items"] if not item.get("exists"))
    return {
        "present": True,
        "evidence_item_count": len(packet["evidence_items"]),
        "missing_evidence_item_count": missing_count,
    }


def render_markdown(registry: dict[str, Any], packet_root: Path, packet_summaries: dict[str, dict[str, Any]]) -> str:
    lines = [
        "# LARQL Lifecycle Status",
        "",
        f"Registry id: `{registry['registry_id']}`",
        "",
        "## Lifecycle status table",
        "",
        "| Rule id | Status | Current step | Allowed next step | Closeout exists | Installed artifact exists | Transport repair required | Failed probe preserved |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    repo_root = Path.cwd()
    for entry in registry["rules"]:
        closeout_exists = (repo_root / entry["closeout_report"]).exists()
        installed_exists = (repo_root / entry["installed_rule_artifact"]).exists()
        lines.append(
            "| {rule_id} | {status} | {current} | {next_step} | {closeout} | {installed} | {transport} | {failed} |".format(
                rule_id=entry["rule_id"],
                status=entry["status"],
                current=entry["current_lifecycle_step"],
                next_step=entry["allowed_next_step"],
                closeout=str(closeout_exists).lower(),
                installed=str(installed_exists).lower(),
                transport=str(bool(entry.get("transport_repair_required", False))).lower(),
                failed=str(bool(entry.get("failed_probe_preserved", False))).lower(),
            )
        )

    lines.extend(
        [
            "",
            "## Evidence packet status table",
            "",
            "| Rule id | Packet present | Evidence items | Missing items |",
            "| --- | --- | --- | --- |",
        ]
    )
    for entry in registry["rules"]:
        summary = packet_summaries[entry["rule_id"]]
        lines.append(
            "| {rule_id} | {present} | {items} | {missing} |".format(
                rule_id=entry["rule_id"],
                present=str(summary["present"]).lower(),
                items=summary.get("evidence_item_count", ""),
                missing=summary.get("missing_evidence_item_count", ""),
            )
        )

    lines.extend(
        [
            "",
            "## Held / not-authorized reminder",
            "",
            "- no model call is made by this driver",
            "- no training data is written",
            "- no dataset artifact is written",
            "- no durable memory is written",
            "- no candidate is promoted",
            "- no model weights are mutated",
            "- no runtime rules are installed or modified",
            "- no automatic failure-to-curriculum capture is performed",
            "",
            "## Next machinery step",
            "",
            "Package a reusable status/navigation cleanup layer on top of the registry and packet outputs, without adding another hand-built LARQL rule.",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def write_status(registry_path: Path, packet_root: Path, out_path: Path) -> dict[str, Any]:
    repo_root = Path.cwd()
    registry = load_registry(registry_path)
    validate_registry(registry, repo_root)

    packet_summaries: dict[str, dict[str, Any]] = {}
    for entry in registry["rules"]:
        packet = load_packet_manifest(packet_root, entry["rule_id"])
        packet_summaries[entry["rule_id"]] = summarize_packet(packet)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    markdown = render_markdown(registry, packet_root, packet_summaries)
    out_path.write_text(markdown, encoding="utf-8")
    return {"registry": registry, "packet_summaries": packet_summaries, "markdown": markdown}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--packet-root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_status(args.registry, args.packet_root, args.out)
    except (OSError, ValueError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
