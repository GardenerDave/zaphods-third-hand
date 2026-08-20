#!/usr/bin/env python3
"""Freshness, satisfiability, and manifest helpers for Run 5 mixed fixtures."""

from __future__ import annotations

import hashlib
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from local_harness.capability_cards import failure_classes, failure_signature
from local_harness.supervised_capability_loop import _validator_result, load_task_fixture


PACKS = {
    "triage": {"directory": "reviewed_run5_triage", "family": "triage-routing", "resolution": "task_family", "count": 15, "target": 12},
    "scope": {"directory": "reviewed_run5_scope", "family": "scope-authority-boundary", "resolution": "failure_class", "count": 15, "target": 12},
}
PACK_ROOT = "local_harness/fixtures/capability_loop"
PAIR_ORDER_SEED = 20260824
SIMILARITY_THRESHOLD = 0.80
EXCLUDED_PACKS = {spec["directory"] for spec in PACKS.values()}
# Future reviewed packs must not retroactively alter the historical Run 5
# novelty input universe or invalidate its frozen manifests.
FUTURE_PACKS = {"reviewed_run6_triage", "reviewed_run6_scope"}


class Run5FixtureError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical(value).encode())


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def fixture_paths(pack_dir: Path) -> list[Path]:
    return sorted(path for path in pack_dir.glob("*.json") if path.name not in {"manifest.json", "novelty_audit.json"})


def prior_tasks(repo_root: Path) -> list[dict[str, Any]]:
    result = []
    fixture_root = repo_root / PACK_ROOT
    for pack_dir in sorted(fixture_root.glob("reviewed*")):
        if pack_dir.name in EXCLUDED_PACKS or pack_dir.name in FUTURE_PACKS:
            continue
        for path in fixture_paths(pack_dir):
            result.append(load_task_fixture(path))
    return result


def representative_output(task: dict[str, Any]) -> dict[str, Any]:
    facts = task["validator"]["reference_facts"]
    if task["task_family"] == "triage-routing":
        phrase = " ".join(facts["must_include"])
        return {"route": phrase, "rationale": phrase, "review_status": facts["review_status"]}
    return {
        "allowed_targets": facts["required_allowed_targets"],
        "held_targets": facts["required_held_targets"],
        "scope_expansion_required": facts["requires_scope_expansion_flag"],
        "review_status": facts["review_status"],
    }


def novelty_audit(pack_dir: Path, repo_root: Path) -> dict[str, Any]:
    new_tasks = [load_task_fixture(path) for path in fixture_paths(pack_dir)]
    old_tasks = prior_tasks(repo_root)
    old_ids = {task["task_id"] for task in old_tasks}
    old_prompts = {task["prompt"] for task in old_tasks}
    old_normalized = {normalize(task["prompt"]) for task in old_tasks}
    old_sources = {task.get("provenance", {}).get("source_document") for task in old_tasks}
    old_anchors = {(task.get("provenance", {}).get("source_document"), task.get("provenance", {}).get("source_anchor")) for task in old_tasks}
    result: dict[str, Any] = {
        "schema": "zth_run5_mixed_novelty_audit_v1",
        "model_outputs_consulted": False,
        "prior_fixture_packs": sorted(pack.name for pack in (repo_root / PACK_ROOT).glob("reviewed*") if pack.name not in FUTURE_PACKS),
        "similarity_threshold": SIMILARITY_THRESHOLD,
        "task_id_collisions": [], "exact_prompt_duplicates": [], "normalized_prompt_duplicates": [],
        "high_similarity_pairs": [], "source_document_collisions": [], "source_anchor_collisions": [],
        "novelty_classification": {},
    }
    seen_prompts: set[str] = set()
    seen_normalized: set[str] = set()
    for task in new_tasks:
        task_id = task["task_id"]
        source = task["provenance"]["source_document"]
        anchor = (source, task["provenance"]["source_anchor"])
        result["novelty_classification"][task_id] = "new_source" if source not in old_sources else "new_scenario_same_family"
        if task_id in old_ids:
            result["task_id_collisions"].append(task_id)
        normalized = normalize(task["prompt"])
        if task["prompt"] in old_prompts or task["prompt"] in seen_prompts:
            result["exact_prompt_duplicates"].append(task_id)
        if normalized in old_normalized or normalized in seen_normalized:
            result["normalized_prompt_duplicates"].append(task_id)
        if source in old_sources:
            result["source_document_collisions"].append({"task_id": task_id, "source_document": source})
        if anchor in old_anchors:
            result["source_anchor_collisions"].append({"task_id": task_id, "source_document": source, "source_anchor": anchor[1]})
        for prior in old_tasks:
            ratio = SequenceMatcher(None, normalized, normalize(prior["prompt"])).ratio()
            if ratio >= SIMILARITY_THRESHOLD:
                result["high_similarity_pairs"].append({"candidate_task_id": task_id, "prior_task_id": prior["task_id"], "ratio": round(ratio, 6)})
        seen_prompts.add(task["prompt"])
        seen_normalized.add(normalized)
    result["counts"] = {
        "candidates": len(new_tasks),
        "new_source": sum(value == "new_source" for value in result["novelty_classification"].values()),
        "new_scenario_same_family": sum(value == "new_scenario_same_family" for value in result["novelty_classification"].values()),
        "source_document_reuse": len(result["source_document_collisions"]),
        "source_anchor_reuse": len(result["source_anchor_collisions"]),
    }
    return result


def pair_orders(task_ids: list[str], seed: int = PAIR_ORDER_SEED) -> dict[str, list[str]]:
    result = {}
    for task_id in sorted(task_ids):
        digest = hashlib.sha256(f"{seed}:{task_id}".encode()).hexdigest()
        result[task_id] = ["control", "treatment"] if int(digest[0], 16) < 8 else ["treatment", "control"]
    return result


def build_manifest(pack_dir: Path, repo_root: Path, *, generated_at: str) -> tuple[dict[str, Any], dict[str, Any]]:
    spec = next((value for value in PACKS.values() if repo_root / PACK_ROOT / value["directory"] == pack_dir), None)
    if spec is None:
        raise Run5FixtureError(f"unknown Run 5 pack: {pack_dir}")
    paths = fixture_paths(pack_dir)
    if len(paths) != spec["count"]:
        raise Run5FixtureError(f"expected {spec['count']} candidates, found {len(paths)}")
    tasks = [load_task_fixture(path) for path in paths]
    if any(task["task_family"] != spec["family"] for task in tasks):
        raise Run5FixtureError("family drift")
    if len({task["task_id"] for task in tasks}) != spec["count"]:
        raise Run5FixtureError("task IDs are not unique")
    for task in tasks:
        witness = representative_output(task)
        result = _validator_result(json.dumps(witness, sort_keys=True), task, attempt_id=f"run5-satisfiability-{task['task_id']}")
        if result["validation_status"] != "passed":
            raise Run5FixtureError(f"unsatisfiable fixture: {task['task_id']}")
        calibration = task.get("calibration", {})
        if calibration.get("target_evidence_resolution") != spec["resolution"] or calibration.get("target_evidence_key") != spec["family"]:
            raise Run5FixtureError(f"target evidence binding mismatch: {task['task_id']}")
        if spec["resolution"] == "failure_class":
            failure_witness = {
                "allowed_targets": [],
                "held_targets": [],
                "scope_expansion_required": True,
                "review_status": "ready_for_review",
            }
            failed = _validator_result(json.dumps(failure_witness, sort_keys=True), task, attempt_id=f"run5-signature-{task['task_id']}")
            expected_classes = failure_classes(failure_signature(task["task_family"], failed))
            if calibration.get("target_failure_classes") != expected_classes:
                raise Run5FixtureError(f"failure class binding mismatch: {task['task_id']}")
    audit = novelty_audit(pack_dir, repo_root)
    if any(audit[key] for key in ("task_id_collisions", "exact_prompt_duplicates", "normalized_prompt_duplicates", "high_similarity_pairs")):
        raise Run5FixtureError("freshness audit found a collision or high-similarity pair")
    records = []
    for path, task in zip(paths, tasks):
        records.append({
            "path": str(path.relative_to(repo_root)), "task_id": task["task_id"], "task_family": task["task_family"],
            "novelty": task["provenance"]["novelty"], "source_document": task["provenance"]["source_document"],
            "source_anchor": task["provenance"]["source_anchor"], "fixture_sha256": sha256_bytes(path.read_bytes()),
            "output_contract_sha256": sha256_json(task["output_contract"]), "reference_facts_sha256": sha256_json(task["validator"].get("reference_facts", {})),
            "target_evidence_resolution": task["calibration"]["target_evidence_resolution"], "target_evidence_key": task["calibration"]["target_evidence_key"],
        })
    task_ids = [task["task_id"] for task in tasks]
    audit_digest = sha256_bytes(canonical(audit).encode())
    audit["audit_sha256"] = audit_digest
    manifest = {
        "schema": "zth_run5_mixed_fixture_manifest_v1", "pack_id": pack_dir.name, "generated_at": generated_at,
        "model_outputs_consulted": False, "candidate_count": spec["count"], "target_included_count": spec["target"],
        "task_family": spec["family"], "target_evidence_resolution": spec["resolution"], "fixtures": records,
        "candidate_order": task_ids,
        "eligibility": ["transport_valid=true", "transport_classification=model_response", "deterministic baseline validation failure", f"target resolution={spec['resolution']}", f"target evidence key={spec['family']}"],
        "selection_rule": "Select the first target count eligible candidates in frozen family-specific candidate order; never use intervention outcomes for inclusion.",
        "reserve_rule": "Candidates not selected after baseline eligibility remain family-specific reserve-only; no adaptive replacement.",
        "pair_order": {"seed": PAIR_ORDER_SEED, "algorithm": "sha256(str(seed) + ':' + task_id), first hex digit < 8 means control-first, otherwise treatment-first", "orders": pair_orders(task_ids)},
        "novelty_audit_path": str((pack_dir / "novelty_audit.json").relative_to(repo_root)), "novelty_audit_sha256": audit_digest,
        "manifest_sha256": None, "pack_sha256": None,
    }
    manifest_basis = dict(manifest); manifest_basis["manifest_sha256"] = None
    manifest["manifest_sha256"] = sha256_bytes(canonical(manifest_basis).encode())
    pack_basis = dict(manifest); pack_basis["pack_sha256"] = None
    manifest["pack_sha256"] = sha256_bytes(canonical(pack_basis).encode())
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
        raise Run5FixtureError(f"manifest drift: {pack_dir}")
    return manifest
