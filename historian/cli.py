from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .capability_profile import (
    CAPABILITY_PROFILE_PATH,
    load_capability_profiles,
    validate_capability_profile,
)


ROOT = Path(__file__).resolve().parents[1]
V2_MANIFEST = ROOT / "docs" / "v2_shared_memory_qualification_manifest.json"
FLEET_MANIFEST = ROOT / "docs" / "fleet_routing_v1_manifest.json"
FOCUSED_30B_MANIFEST = ROOT / "docs" / "focused_30b_shared_memory_v1_manifest.json"
FOCUSED_30B_FIXTURE = ROOT / "interfaces" / "reasoner" / "acceptance" / "focused_30b_shared_memory_v1_queries.json"


def _load_required_manifests() -> dict[str, dict]:
    manifests = {}
    for path in (V2_MANIFEST, FLEET_MANIFEST, FOCUSED_30B_MANIFEST):
        if path.exists():
            payload = json.loads(path.read_text())
            experiment = payload.get("experiment_name") or path.stem
            manifests[str(experiment)] = payload
    return manifests


def _validate_focused_fixture() -> None:
    if not FOCUSED_30B_FIXTURE.exists():
        return
    payload = json.loads(FOCUSED_30B_FIXTURE.read_text())
    if payload.get("schema") != "historian_focused_30b_shared_memory_v1_queries":
        raise ValueError("focused 30B fixture schema mismatch")
    tasks = payload.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != 6:
        raise ValueError("focused 30B fixture must contain six tasks")
    classes = [task.get("task_class") for task in tasks]
    if classes.count("historical_fact_recovery") != 2 or classes.count("historical_synthesis") != 2 or classes.count("evidence_boundary_reasoning") != 2:
        raise ValueError("focused 30B fixture must contain two tasks per class")
    if any(task.get("task_class") == "exact_causal_inference_from_incomplete_history" for task in tasks):
        raise ValueError("focused 30B fixture must not contain exact-causal tasks")
    ids = [task.get("id") for task in tasks]
    if len(ids) != len(set(ids)):
        raise ValueError("focused 30B fixture task ids must be unique")
    for task in tasks:
        if not set(task.get("required_citation_ids", [])) <= set(task.get("expected_record_ids", [])):
            raise ValueError(f"required citations must be a subset of expected records for {task.get('id')}")


def cmd_validate(_: argparse.Namespace) -> int:
    profile = load_capability_profiles()
    manifests = _load_required_manifests()
    validate_capability_profile(profile, manifests=manifests)
    _validate_focused_fixture()
    print(json.dumps({"status": "valid", "profile_sha256": __import__("hashlib").sha256(CAPABILITY_PROFILE_PATH.read_bytes()).hexdigest(), "manifest_count": len(manifests)}, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="historian.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate", help="Validate capability profiles and manifests")
    validate.set_defaults(func=cmd_validate)
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
