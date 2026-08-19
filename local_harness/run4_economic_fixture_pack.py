#!/usr/bin/env python3
"""Manifest and freshness audit for the targeted Run 4 economic fixtures."""

from __future__ import annotations

import hashlib
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from local_harness.supervised_capability_loop import _validator_result, load_task_fixture


PACK_ID = "reviewed_run4_economic_triage"
PRIOR_PACKS = ("reviewed_v1", "reviewed_v2", "reviewed_v3", "reviewed_v3b", "reviewed_v3c", "reviewed_v4a")
TASK_FAMILY = "triage-routing"
TARGET_COUNT = 12
CANDIDATE_COUNT = 15
PAIR_ORDER_SEED = 20260822
SIMILARITY_THRESHOLD = 0.80


class Run4EconomicFixtureError(ValueError):
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
    tasks = []
    for pack in PRIOR_PACKS:
        for path in sorted((repo_root / "local_harness/fixtures/capability_loop" / pack).glob("*.json")):
            if path.name in {"manifest.json", "novelty_audit.json"}:
                continue
            tasks.append(load_task_fixture(path))
    return tasks


def novelty_audit(pack_dir: Path, repo_root: Path) -> dict[str, Any]:
    new_tasks = [load_task_fixture(path) for path in fixture_paths(pack_dir)]
    old_tasks = prior_tasks(repo_root)
    old_ids = {task["task_id"] for task in old_tasks}
    old_prompts = {task["prompt"] for task in old_tasks}
    old_normalized = {normalize(task["prompt"]) for task in old_tasks}
    old_sources = {task.get("provenance", {}).get("source_document") for task in old_tasks}
    old_anchors = {(task.get("provenance", {}).get("source_document"), task.get("provenance", {}).get("source_anchor")) for task in old_tasks}
    result: dict[str, Any] = {
        "schema": "zth_run4_economic_novelty_audit_v1",
        "model_outputs_consulted": False,
        "prior_packs": list(PRIOR_PACKS),
        "similarity_threshold": SIMILARITY_THRESHOLD,
        "task_id_collisions": [],
        "exact_prompt_duplicates": [],
        "normalized_prompt_duplicates": [],
        "high_similarity_pairs": [],
        "source_document_collisions": [],
        "source_anchor_collisions": [],
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
        if task["prompt"] in old_prompts or task["prompt"] in seen_prompts:
            result["exact_prompt_duplicates"].append(task_id)
        normalized = normalize(task["prompt"])
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
    orders = {}
    for task_id in sorted(task_ids):
        digest = hashlib.sha256(f"{seed}:{task_id}".encode()).hexdigest()
        orders[task_id] = ["control", "treatment"] if int(digest[0], 16) < 8 else ["treatment", "control"]
    return orders


def build_manifest(pack_dir: Path, repo_root: Path, *, generated_at: str) -> tuple[dict[str, Any], dict[str, Any]]:
    paths = fixture_paths(pack_dir)
    if len(paths) != CANDIDATE_COUNT:
        raise Run4EconomicFixtureError(f"expected {CANDIDATE_COUNT} candidates, found {len(paths)}")
    tasks = [load_task_fixture(path) for path in paths]
    if any(task["task_family"] != TASK_FAMILY for task in tasks):
        raise Run4EconomicFixtureError("all Run 4 economic candidates must be triage-routing")
    if len({task["task_id"] for task in tasks}) != CANDIDATE_COUNT:
        raise Run4EconomicFixtureError("task IDs are not unique")
    for task in tasks:
        witness = {field: " ".join(task["validator"]["reference_facts"].get("must_include", [])) for field in task["output_contract"]["required_fields"]}
        witness["review_status"] = task["validator"]["reference_facts"].get("review_status", "ready_for_review")
        result = _validator_result(json.dumps(witness), task, attempt_id=f"run4-economic-satisfiability-{task['task_id']}")
        if result["validation_status"] != "passed":
            raise Run4EconomicFixtureError(f"unsatisfiable fixture: {task['task_id']}")
        calibration = task.get("calibration", {})
        if calibration.get("target_evidence_resolution") != "task_family" or calibration.get("target_evidence_key") != TASK_FAMILY:
            raise Run4EconomicFixtureError(f"target evidence binding mismatch: {task['task_id']}")
    audit = novelty_audit(pack_dir, repo_root)
    if any(audit[key] for key in ("task_id_collisions", "exact_prompt_duplicates", "normalized_prompt_duplicates", "high_similarity_pairs")):
        raise Run4EconomicFixtureError("freshness audit found a collision or high-similarity pair")
    records = []
    for path, task in zip(paths, tasks):
        records.append({
            "path": str(path.relative_to(repo_root)),
            "task_id": task["task_id"],
            "task_family": task["task_family"],
            "novelty": task["provenance"]["novelty"],
            "source_document": task["provenance"]["source_document"],
            "source_anchor": task["provenance"]["source_anchor"],
            "fixture_sha256": sha256_bytes(path.read_bytes()),
            "output_contract_sha256": sha256_json(task["output_contract"]),
            "reference_facts_sha256": sha256_json(task["validator"].get("reference_facts", {})),
            "target_evidence_resolution": task["calibration"]["target_evidence_resolution"],
            "target_evidence_key": task["calibration"]["target_evidence_key"],
        })
    task_ids = [task["task_id"] for task in tasks]
    manifest = {
        "schema": "zth_run4_economic_fixture_manifest_v1",
        "pack_id": PACK_ID,
        "generated_at": generated_at,
        "model_outputs_consulted": False,
        "candidate_count": CANDIDATE_COUNT,
        "target_included_count": TARGET_COUNT,
        "task_family": TASK_FAMILY,
        "fixtures": records,
        "candidate_order": task_ids,
        "eligibility": ["transport_valid=true", "transport_classification=model_response", "deterministic baseline validation failure", "target resolution=task_family", "target evidence key=triage-routing"],
        "selection_rule": "Select the first target count eligible candidates in frozen candidate order; never use intervention outcomes for inclusion.",
        "reserve_rule": "Candidates not selected after baseline eligibility remain reserve-only; no adaptive replacement.",
        "pair_order": {"seed": PAIR_ORDER_SEED, "algorithm": "sha256(str(seed) + ':' + task_id), first hex digit < 8 means control-first, otherwise treatment-first", "orders": pair_orders(task_ids)},
        "novelty_audit_path": str((pack_dir / "novelty_audit.json").relative_to(repo_root)),
        "novelty_audit_sha256": None,
        "manifest_sha256": None,
        "pack_sha256": None,
    }
    audit_digest = sha256_bytes(canonical(audit).encode())
    audit["audit_sha256"] = audit_digest
    manifest["novelty_audit_sha256"] = audit_digest
    manifest_basis = dict(manifest)
    manifest_basis["manifest_sha256"] = None
    manifest["manifest_sha256"] = sha256_bytes(canonical(manifest_basis).encode())
    pack_basis = dict(manifest)
    pack_basis["pack_sha256"] = None
    pack_basis["manifest_sha256"] = None
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
        raise Run4EconomicFixtureError("Run 4 economic fixture manifest drift")
    return manifest

