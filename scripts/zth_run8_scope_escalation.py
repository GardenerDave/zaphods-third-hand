#!/usr/bin/env python3
"""Execute the separately frozen Run 8 repaired scope escalation protocol."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from local_harness.run8_scope_fixture_pack import verify_manifest
from scripts import zth_run7_scope_escalation as repaired


TARGET_COUNT = 20
SEED = 20260827


def _load_context(prereg_path: Path, repo_root: Path, *, require_runtime: bool) -> dict[str, Any]:
    prereg = repaired._read_json(prereg_path)
    if prereg.get("model_calls_made") is not False:
        raise repaired.Run4ADriverError("Run 8 preregistration is not model-free")

    policy_binding = prereg["policy_freeze"]
    policy_path = repo_root / policy_binding["path"]
    policy = repaired._read_json(policy_path)
    if repaired.sha256_file(policy_path) != policy_binding["file_sha256"] or repaired._policy_digest(policy) != policy_binding["canonical_sha256"]:
        raise repaired.Run4ADriverError("Run 8 policy binding mismatch")
    repaired.verify_policy()

    source = prereg["policy_source"]
    if repaired.sha256_file(repo_root / source["path"]) != source["sha256"]:
        raise repaired.Run4ADriverError("Run 8 policy source binding mismatch")

    repair_binding = prereg["repair_freeze"]
    repair_path = repo_root / repair_binding["path"]
    if repaired.sha256_file(repair_path) != repair_binding["file_sha256"]:
        raise repaired.Run4ADriverError("Run 8 repair freeze binding mismatch")
    repair = repaired._read_json(repair_path)
    if repair["repair"]["driver"]["sha256"] != repaired.sha256_file(repo_root / repair["repair"]["driver"]["path"]):
        raise repaired.Run4ADriverError("Run 8 repaired driver binding mismatch")
    if repair["historical_run7"]["preregistration"]["sha256"] != prereg["historical_run7"]["preregistration_sha256"] or repair["historical_run7"]["driver"]["sha256"] != prereg["historical_run7"]["driver_sha256"]:
        raise repaired.Run4ADriverError("Run 8 historical provenance binding mismatch")
    if repair["repair"].get("scientific_evidence_produced", True):
        raise repaired.Run4ADriverError("Run 8 repair freeze already contains scientific evidence")

    historical_prereg = repo_root / prereg["historical_run7"]["preregistration_path"]
    if repaired.sha256_file(historical_prereg) != prereg["historical_run7"]["preregistration_sha256"]:
        raise repaired.Run4ADriverError("Run 8 historical preregistration mismatch")
    historical_result = repo_root / prereg["historical_run7"]["result_path"]
    if repaired.sha256_file(historical_result) != prereg["historical_run7"]["result_sha256"]:
        raise repaired.Run4ADriverError("Run 8 historical result binding mismatch")
    forensic = repo_root / prereg["forensic_report"]["path"]
    if repaired.sha256_file(forensic) != prereg["forensic_report"]["sha256"]:
        raise repaired.Run4ADriverError("Run 8 forensic report binding mismatch")
    repair_note = repo_root / prereg["repair_note"]["path"]
    if repaired.sha256_file(repair_note) != prereg["repair_note"]["sha256"]:
        raise repaired.Run4ADriverError("Run 8 repair note binding mismatch")

    criteria_path = repo_root / prereg["difficulty_criteria"]["path"]
    if repaired.sha256_file(criteria_path) != prereg["difficulty_criteria"]["sha256"]:
        raise repaired.Run4ADriverError("Run 8 difficulty criteria binding mismatch")
    provenance_path = repo_root / prereg["fixture_provenance"]["path"]
    if repaired.sha256_file(provenance_path) != prereg["fixture_provenance"]["sha256"]:
        raise repaired.Run4ADriverError("Run 8 provenance binding mismatch")

    pack_binding = prereg["fixture_pack"]
    pack_dir = repo_root / pack_binding["path"]
    manifest = verify_manifest(pack_dir, repo_root)
    if repaired.sha256_file(pack_dir / "manifest.json") != pack_binding["manifest_file_sha256"] or manifest["manifest_sha256"] != pack_binding["manifest_sha256"] or manifest["pack_sha256"] != pack_binding["pack_sha256"]:
        raise repaired.Run4ADriverError("Run 8 fixture pack binding mismatch")
    if repaired.sha256_file(pack_dir / "novelty_audit.json") != pack_binding["novelty_audit_file_sha256"] or manifest["novelty_audit_sha256"] != pack_binding["novelty_audit_sha256"]:
        raise repaired.Run4ADriverError("Run 8 novelty audit binding mismatch")

    resource_binding = prereg["resource_manifest"]
    resource_path = repo_root / resource_binding["path"]
    if repaired.sha256_file(resource_path) != resource_binding["sha256"]:
        raise repaired.Run4ADriverError("Run 8 resource manifest mismatch")
    resource = repaired._read_json(resource_path)
    if resource.get("manifest_sha256") != resource_binding["canonical_sha256"]:
        raise repaired.Run4ADriverError("Run 8 resource canonical digest mismatch")
    for item in prereg["validators"]:
        if repaired.sha256_file(repo_root / item["path"]) != item["sha256"]:
            raise repaired.Run4ADriverError(f"Run 8 validator binding mismatch: {item['path']}")
    if repaired.sha256_file(repo_root / prereg["driver"]["path"]) != prereg["driver"]["sha256"]:
        raise repaired.Run4ADriverError("Run 8 driver binding mismatch")

    timeouts = prereg["timeouts_seconds"]
    effective = {"worker": int(os.environ.get("ZTH_CAPABILITY_WORKER_TIMEOUT", timeouts["worker"])), "local_teacher": int(os.environ.get("ZTH_CAPABILITY_TEACHER_TIMEOUT", timeouts["local_teacher"])), "external_teacher": int(timeouts["external_teacher"])}
    if effective != timeouts:
        raise repaired.Run4ADriverError("Run 8 timeout binding mismatch")
    configured = {"worker": os.environ.get("ZTH_CAPABILITY_WORKER_MODEL"), "local_teacher": os.environ.get("ZTH_CAPABILITY_TEACHER_MODEL"), "external_teacher": os.environ.get("ZTH_EXTERNAL_TEACHER_IDENTITY")}
    if require_runtime and any(configured[k] != prereg["models"][k] for k in configured):
        raise repaired.Run4ADriverError("Run 8 runtime identity mismatch")
    if prereg["pair_order_seed"] != SEED or manifest["candidate_count"] != 24 or manifest["target_included_count"] != TARGET_COUNT:
        raise repaired.Run4ADriverError("Run 8 selection binding mismatch")
    tasks = {row["task_id"]: repaired.load_task_fixture(repo_root / row["path"]) for row in manifest["fixtures"]}
    return {"preregistration": prereg, "preregistration_path": prereg_path, "policy": policy, "manifests": {"scope": manifest}, "tasks": tasks, "effective_timeouts": effective}


def git_head(repo_root: Path) -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True, capture_output=True, check=True).stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    repo_root = Path.cwd()
    context = _load_context(args.preregistration, repo_root, require_runtime=args.execute)
    context["git_head"] = git_head(repo_root)
    if not args.execute:
        print(repaired.json.dumps({"status": "dry_run_valid", "model_calls": 0, "control": "external_direct", "treatment": "validation_gated_economic_escalation", "pair_order_seed": SEED}, sort_keys=True))
        return 0
    result = repaired.run_experiment(context, args.output_dir, worker=repaired._default_worker, local_teacher=repaired._default_local_teacher, external_teacher=repaired._default_external_teacher)
    print(repaired.json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
