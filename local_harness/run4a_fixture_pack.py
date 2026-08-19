#!/usr/bin/env python3
"""Freeze and audit the model-free Run 4A candidate fixture pack."""

from __future__ import annotations

import hashlib
import itertools
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from local_harness.supervised_capability_loop import _validator_result, load_task_fixture
from local_harness.supervised_reference_fact_validator import REFERENCE_FACT_SPECS


PACK_ID = "reviewed_v4a"
TARGET_BLOCKS = ("contradiction-handling", "triage-routing", "scope-authority-boundary", "unsupported-certainty")
INTERVENTIONS = ("deterministic_patch_retry", "local_teacher", "external_teacher")
ARM_ORDER_SEED = 20260821
SIMILARITY_THRESHOLD = 0.80
PRIOR_PACKS = ("reviewed_v1", "reviewed_v2", "reviewed_v3", "reviewed_v3b", "reviewed_v3c")
PERMUTATIONS = tuple(itertools.permutations(INTERVENTIONS))


class Run4AFixtureError(ValueError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_json(value: Any) -> str:
    return _sha256_bytes(_canonical(value).encode("utf-8"))


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def _paths(pack_dir: Path) -> list[Path]:
    return sorted(path for path in pack_dir.glob("*.json") if path.name not in {"manifest.json", "novelty_audit.json"})


def _prior_tasks(repo_root: Path) -> list[dict[str, Any]]:
    tasks = []
    for pack in PRIOR_PACKS:
        for path in sorted((repo_root / "local_harness/fixtures/capability_loop" / pack).glob("*.json")):
            if path.name == "manifest.json":
                continue
            tasks.append(load_task_fixture(path))
    return tasks


def representative_output(task: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic satisfiability witness from declared fixture facts."""
    facts = task["validator"].get("reference_facts", {})
    fields = task["output_contract"]["required_fields"]
    phrases = list(facts.get("must_include", []))
    output: dict[str, Any] = {}
    for field in fields:
        if field == "allowed_targets":
            output[field] = list(facts.get("required_allowed_targets", []))
        elif field == "held_targets":
            output[field] = list(facts.get("required_held_targets", []))
        elif field == "scope_expansion_required":
            output[field] = facts.get("requires_scope_expansion_flag", False)
        elif field == "review_required":
            output[field] = facts.get("required_review_required", True)
        elif field == "review_status":
            output[field] = facts.get("review_status", "ready_for_review")
        else:
            output[field] = " ".join([*phrases, "bounded review evidence"]).strip()
    return output


def novelty_audit(pack_dir: Path, repo_root: Path) -> dict[str, Any]:
    new_tasks = [load_task_fixture(path) for path in _paths(pack_dir)]
    old_tasks = _prior_tasks(repo_root)
    old_ids = {task["task_id"] for task in old_tasks}
    old_prompts = {task["prompt"] for task in old_tasks}
    old_normalized = {_normalize(task["prompt"]) for task in old_tasks}
    old_sources = {task.get("provenance", {}).get("source_document") for task in old_tasks}
    old_anchors = {(task.get("provenance", {}).get("source_document"), task.get("provenance", {}).get("source_anchor")) for task in old_tasks}
    source_collisions = []
    anchor_collisions = []
    exact_prompt_duplicates = []
    normalized_prompt_duplicates = []
    high_similarity_pairs = []
    task_id_collisions = []
    for task in new_tasks:
        provenance = task.get("provenance", {})
        source = provenance.get("source_document")
        anchor = (source, provenance.get("source_anchor"))
        if task["task_id"] in old_ids:
            task_id_collisions.append(task["task_id"])
        if source in old_sources:
            source_collisions.append({"task_id": task["task_id"], "source_document": source})
        if anchor in old_anchors:
            anchor_collisions.append({"task_id": task["task_id"], "source_document": source, "source_anchor": anchor[1]})
        if task["prompt"] in old_prompts:
            exact_prompt_duplicates.append(task["task_id"])
        if _normalize(task["prompt"]) in old_normalized:
            normalized_prompt_duplicates.append(task["task_id"])
        for old in old_tasks:
            ratio = SequenceMatcher(None, _normalize(task["prompt"]), _normalize(old["prompt"])).ratio()
            if ratio >= SIMILARITY_THRESHOLD:
                high_similarity_pairs.append({"candidate_task_id": task["task_id"], "prior_task_id": old["task_id"], "ratio": round(ratio, 6)})
    expected_new_source = {task["task_id"] for task in new_tasks if task.get("provenance", {}).get("source_document") not in old_sources}
    expected_novelty = {task["task_id"]: "new_source" if task["task_id"] in expected_new_source else "new_scenario_same_family" for task in new_tasks}
    mismatches = [task_id for task_id, expected in expected_novelty.items() if next(task for task in new_tasks if task["task_id"] == task_id).get("provenance", {}).get("novelty") != expected]
    return {
        "schema": "zth_run4a_novelty_audit_v1",
        "model_outputs_consulted": False,
        "prior_packs": list(PRIOR_PACKS),
        "similarity_threshold": SIMILARITY_THRESHOLD,
        "task_id_collisions": task_id_collisions,
        "exact_prompt_duplicates": exact_prompt_duplicates,
        "normalized_prompt_duplicates": normalized_prompt_duplicates,
        "high_similarity_pairs": high_similarity_pairs,
        "source_document_collisions": source_collisions,
        "source_anchor_collisions": anchor_collisions,
        "novelty_classification": expected_novelty,
        "novelty_mismatches": mismatches,
        "counts": {
            "candidates": len(new_tasks),
            "new_source": sum(value == "new_source" for value in expected_novelty.values()),
            "new_scenario_same_family": sum(value == "new_scenario_same_family" for value in expected_novelty.values()),
            "source_document_reuse": len(source_collisions),
            "source_anchor_reuse": len(anchor_collisions),
        },
    }


def intervention_orders(task_ids: list[str], seed: int = ARM_ORDER_SEED) -> dict[str, list[str]]:
    ordered = sorted(task_ids, key=lambda task_id: hashlib.sha256(f"{seed}:{task_id}".encode()).hexdigest())
    return {task_id: list(PERMUTATIONS[index % len(PERMUTATIONS)]) for index, task_id in enumerate(ordered)}


def build_manifest(pack_dir: Path, repo_root: Path, *, generated_at: str) -> tuple[dict[str, Any], dict[str, Any]]:
    paths = _paths(pack_dir)
    tasks = [load_task_fixture(path) for path in paths]
    if len(tasks) != 20:
        raise Run4AFixtureError(f"Run 4A requires 20 candidates, found {len(tasks)}")
    if {task["task_family"] for task in tasks} != set(TARGET_BLOCKS):
        raise Run4AFixtureError("Run 4A target blocks are incomplete")
    counts = {block: sum(task["task_family"] == block for task in tasks) for block in TARGET_BLOCKS}
    if counts != {block: 5 for block in TARGET_BLOCKS}:
        raise Run4AFixtureError(f"Run 4A block counts are not five each: {counts}")
    if len({task["task_id"] for task in tasks}) != 20:
        raise Run4AFixtureError("Run 4A task IDs are not unique")
    for task in tasks:
        for key in task["validator"].get("reference_facts", {}):
            spec = REFERENCE_FACT_SPECS.get(key)
            if spec is None or spec.source_metadata:
                raise Run4AFixtureError(f"fixture uses unsupported worker semantic fact: {key}")
        witness = json.dumps(representative_output(task), sort_keys=True)
        result = _validator_result(witness, task, attempt_id=f"run4a-satisfiability-{task['task_id']}")
        if result["validation_status"] != "passed":
            raise Run4AFixtureError(f"fixture is not satisfiable: {task['task_id']}: {result['diagnostics']}")
    audit = novelty_audit(pack_dir, repo_root)
    if any(audit[key] for key in ("task_id_collisions", "exact_prompt_duplicates", "normalized_prompt_duplicates", "high_similarity_pairs", "novelty_mismatches")):
        raise Run4AFixtureError("Run 4A novelty audit found a collision or high-similarity pair")
    task_records = []
    by_block: dict[str, list[str]] = {block: [] for block in TARGET_BLOCKS}
    for path, task in zip(paths, tasks):
        by_block[task["task_family"]].append(task["task_id"])
        task_records.append({
            "path": str(path.relative_to(repo_root)),
            "task_id": task["task_id"],
            "task_family": task["task_family"],
            "novelty": task["provenance"]["novelty"],
            "source_document": task["provenance"]["source_document"],
            "source_anchor": task["provenance"]["source_anchor"],
            "fixture_sha256": _sha256_bytes(path.read_bytes()),
            "output_contract_sha256": _sha256_json(task["output_contract"]),
            "reference_facts_sha256": _sha256_json(task["validator"].get("reference_facts", {})),
            "target_evidence_resolution": task["calibration"]["target_evidence_resolution"],
            "target_evidence_key": task["calibration"]["target_evidence_key"],
        })
    candidate_order = {block: sorted(ids) for block, ids in by_block.items()}
    included = {block: ids[:4] for block, ids in candidate_order.items()}
    reserves = {block: ids[4:] for block, ids in candidate_order.items()}
    orders = intervention_orders([task["task_id"] for task in tasks])
    manifest = {
        "schema": "zth_run4a_fixture_manifest_v1",
        "pack_id": PACK_ID,
        "generated_at": generated_at,
        "model_outputs_consulted": False,
        "candidate_count": 20,
        "target_blocks": list(TARGET_BLOCKS),
        "block_counts": counts,
        "fixtures": task_records,
        "candidate_order_by_block": candidate_order,
        "included_candidates_by_block": included,
        "reserve_candidates_by_block": reserves,
        "baseline_eligibility": ["transport_valid=true", "transport_classification=model_response", "deterministic baseline validation failure"],
        "reserve_rule": "The fifth lexicographic candidate in each block is reserve only; no replacement is permitted.",
        "arm_order": {"seed": ARM_ORDER_SEED, "algorithm": "sort task IDs by sha256(str(seed) + ':' + task_id), then assign lexicographic permutation list round-robin", "permutations": [list(p) for p in PERMUTATIONS], "orders": orders},
        "novelty_audit_path": str((pack_dir / "novelty_audit.json").relative_to(repo_root)),
        "novelty_audit_sha256": None,
        "pack_sha256": None,
        "manifest_sha256": None,
    }
    pack_basis = dict(manifest)
    pack_basis["pack_sha256"] = None
    pack_basis["manifest_sha256"] = None
    manifest["pack_sha256"] = _sha256_bytes(_canonical(pack_basis).encode())
    audit_basis = dict(audit)
    audit_digest = _sha256_bytes(_canonical(audit_basis).encode())
    manifest["novelty_audit_sha256"] = audit_digest
    manifest_basis = dict(manifest)
    manifest_basis["manifest_sha256"] = None
    manifest["manifest_sha256"] = _sha256_bytes(_canonical(manifest_basis).encode())
    audit["audit_sha256"] = audit_digest
    return manifest, audit


def write_manifest(pack_dir: Path, repo_root: Path, *, generated_at: str) -> dict[str, Any]:
    manifest, audit = build_manifest(pack_dir, repo_root, generated_at=generated_at)
    (pack_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (pack_dir / "novelty_audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def verify_manifest(pack_dir: Path, repo_root: Path) -> dict[str, Any]:
    manifest = json.loads((pack_dir / "manifest.json").read_text(encoding="utf-8"))
    expected, _ = build_manifest(pack_dir, repo_root, generated_at=manifest["generated_at"])
    if manifest != expected:
        raise Run4AFixtureError("Run 4A manifest is not self-verifying")
    return manifest


def main() -> int:
    import argparse
    from datetime import datetime, timezone
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.write:
        manifest = write_manifest(args.pack, args.repo_root, generated_at=datetime.now(timezone.utc).isoformat())
    else:
        manifest = verify_manifest(args.pack, args.repo_root)
    print(json.dumps({"manifest_sha256": manifest["manifest_sha256"], "pack_sha256": manifest["pack_sha256"], "candidate_count": manifest["candidate_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
