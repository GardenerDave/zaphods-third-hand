#!/usr/bin/env python3
"""Collect one LARQL evidence packet from the registry."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


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
    rules = payload.get("rules")
    if not isinstance(rules, list):
        raise ValueError("registry rules must be a list")
    seen: set[str] = set()
    for entry in rules:
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
    return payload


def find_rule(registry: dict[str, Any], rule_id: str) -> dict[str, Any]:
    matches = [entry for entry in registry["rules"] if entry.get("rule_id") == rule_id]
    if not matches:
        raise KeyError(f"unknown rule_id: {rule_id}")
    if len(matches) > 1:
        raise ValueError(f"duplicate rule_id: {rule_id}")
    return matches[0]


def sha256_for_path(path: Path) -> str | None:
    if path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    return None


def classify_path(path: Path) -> tuple[str, bool, str | None, str]:
    if path.is_file():
        return "file", True, sha256_for_path(path), ""
    if path.is_dir():
        return "directory", True, None, "directory"
    return "missing", False, None, "missing"


def collect_evidence(entry: dict[str, Any], repo_root: Path) -> list[dict[str, Any]]:
    paths = [entry["closeout_report"], entry["installed_rule_artifact"], *entry["evidence_paths"]]
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rel in paths:
        if rel in seen:
            continue
        seen.add(rel)
        path = repo_root / rel
        kind, exists, sha256, note = classify_path(path)
        item: dict[str, Any] = {
            "path": rel,
            "exists": exists,
            "kind": kind,
        }
        if sha256 is not None:
            item["sha256"] = sha256
        if note:
            item["note"] = note
        items.append(item)
    return items


def render_markdown(packet: dict[str, Any]) -> str:
    evidence_items = packet["evidence_items"]
    missing_count = sum(1 for item in evidence_items if not item["exists"])
    lines = [
        "# LARQL Evidence Packet",
        "",
        f"Rule id: `{packet['rule_id']}`",
        f"Status: `{packet['status']}`",
        f"Closeout: [{packet['closeout_report']}]({packet['closeout_report']})",
        "",
        "## Counts",
        "",
        f"- Evidence items: `{len(evidence_items)}`",
        f"- Missing items: `{missing_count}`",
        "",
        "## Evidence items",
        "",
        "| Path | Exists | Kind | SHA256 | Note |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in evidence_items:
        lines.append(
            "| {path} | {exists} | {kind} | {sha256} | {note} |".format(
                path=item["path"],
                exists=str(item["exists"]).lower(),
                kind=item["kind"],
                sha256=item.get("sha256", ""),
                note=item.get("note", ""),
            )
        )
    return "\n".join(lines).rstrip() + "\n"


def validate_packet(entry: dict[str, Any], packet: dict[str, Any]) -> None:
    required_packet_keys = {
        "report_type",
        "rule_id",
        "rule_family_id",
        "source_failure_id",
        "candidate_id",
        "status",
        "current_lifecycle_step",
        "allowed_next_step",
        "closeout_report",
        "installed_rule_artifact",
        "transport_repair_required",
        "failed_probe_preserved",
        "json_contract",
        "evidence_items",
    }
    if packet.get("report_type") != "larql_evidence_packet.v0":
        raise ValueError("unexpected report_type")
    if not required_packet_keys.issubset(packet):
        missing = sorted(required_packet_keys - set(packet))
        raise ValueError(f"packet missing required keys: {', '.join(missing)}")
    if packet["rule_id"] != entry["rule_id"]:
        raise ValueError("packet rule_id mismatch")
    if packet["json_contract"] != entry["json_contract"]:
        raise ValueError("packet json_contract mismatch")


def write_packet(registry_path: Path, rule_id: str, out_dir: Path) -> dict[str, Any]:
    repo_root = registry_path.resolve().parents[3]
    registry = load_registry(registry_path)
    entry = find_rule(registry, rule_id)
    evidence_items = collect_evidence(entry, repo_root)
    packet = {
        "report_type": "larql_evidence_packet.v0",
        "rule_id": entry["rule_id"],
        "rule_family_id": entry["rule_family_id"],
        "source_failure_id": entry["source_failure_id"],
        "candidate_id": entry["candidate_id"],
        "status": entry["status"],
        "current_lifecycle_step": entry["current_lifecycle_step"],
        "allowed_next_step": entry["allowed_next_step"],
        "closeout_report": entry["closeout_report"],
        "installed_rule_artifact": entry["installed_rule_artifact"],
        "transport_repair_required": bool(entry.get("transport_repair_required", False)),
        "failed_probe_preserved": bool(entry.get("failed_probe_preserved", False)),
        "json_contract": entry["json_contract"],
        "evidence_items": evidence_items,
    }
    validate_packet(entry, packet)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "evidence_packet_manifest.json").write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "evidence_packet_summary.md").write_text(render_markdown(packet), encoding="utf-8")
    return packet


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--rule-id", required=True)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_packet(args.registry, args.rule_id, args.out)
    except (OSError, ValueError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
