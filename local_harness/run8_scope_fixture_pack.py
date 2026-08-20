"""Freshness and manifest helpers for frozen Run 8 scope fixtures."""

from __future__ import annotations

import hashlib
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from local_harness.capability_cards import failure_classes, failure_signature
from local_harness.supervised_capability_loop import _validator_result, load_task_fixture

PACK_ROOT = "local_harness/fixtures/capability_loop"
PACK_DIRECTORY = "run8_scope"
FAMILY = "scope-authority-boundary"
RESOLUTION = "failure_class"
CANDIDATE_COUNT = 24
TARGET_COUNT = 20
PAIR_ORDER_SEED = 20260827
SIMILARITY_THRESHOLD = 0.80
DIFFICULTY_PATH = "docs/research/RUN_8_SCOPE_DIFFICULTY_CRITERIA_FREEZE_2026-08-20.json"
PROVENANCE_PATH = "docs/research/RUN_8_FIXTURE_PROVENANCE_2026-08-20.md"


class Run8FixtureError(ValueError):
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
    return sorted(p for p in pack_dir.glob("*.json") if p.name not in {"manifest.json", "novelty_audit.json"})


def prior_tasks(repo_root: Path) -> list[dict[str, Any]]:
    result = []
    for pack_dir in sorted((repo_root / PACK_ROOT).glob("reviewed*")):
        if pack_dir.name == PACK_DIRECTORY:
            continue
        for path in fixture_paths(pack_dir):
            result.append(load_task_fixture(path))
    run7 = repo_root / PACK_ROOT / "run7_scope"
    for path in fixture_paths(run7):
        result.append(load_task_fixture(path))
    return result


def representative_output(task: dict[str, Any]) -> dict[str, Any]:
    facts = task["validator"]["reference_facts"]
    return {"allowed_targets": facts["required_allowed_targets"], "held_targets": facts["required_held_targets"], "scope_expansion_required": facts["requires_scope_expansion_flag"], "review_status": facts["review_status"]}


def novelty_audit(pack_dir: Path, repo_root: Path) -> dict[str, Any]:
    new_tasks = [load_task_fixture(p) for p in fixture_paths(pack_dir)]
    old_tasks = prior_tasks(repo_root)
    old_ids = {t["task_id"] for t in old_tasks}; old_prompts = {t["prompt"] for t in old_tasks}; old_norm = {normalize(t["prompt"]) for t in old_tasks}
    old_sources = {t.get("provenance", {}).get("source_document") for t in old_tasks}; old_anchors = {(t.get("provenance", {}).get("source_document"), t.get("provenance", {}).get("source_anchor")) for t in old_tasks}
    result: dict[str, Any] = {"schema": "zth_run8_scope_novelty_audit_v1", "model_outputs_consulted": False, "prior_fixture_packs": sorted(p.name for p in (repo_root / PACK_ROOT).glob("reviewed*")) + ["run7_scope"], "similarity_threshold": SIMILARITY_THRESHOLD, "task_id_collisions": [], "exact_prompt_duplicates": [], "normalized_prompt_duplicates": [], "high_similarity_pairs": [], "source_document_collisions": [], "source_anchor_collisions": [], "novelty_classification": {}}
    seen_prompts: set[str] = set(); seen_norm: set[str] = set()
    for task in new_tasks:
        task_id = task["task_id"]; source = task["provenance"]["source_document"]; anchor = (source, task["provenance"]["source_anchor"]); normalized = normalize(task["prompt"])
        result["novelty_classification"][task_id] = "new_source" if source not in old_sources else "new_scenario_same_family"
        if task_id in old_ids: result["task_id_collisions"].append(task_id)
        if task["prompt"] in old_prompts or task["prompt"] in seen_prompts: result["exact_prompt_duplicates"].append(task_id)
        if normalized in old_norm or normalized in seen_norm: result["normalized_prompt_duplicates"].append(task_id)
        if source in old_sources: result["source_document_collisions"].append({"task_id": task_id, "source_document": source})
        if anchor in old_anchors: result["source_anchor_collisions"].append({"task_id": task_id, "source_document": source, "source_anchor": anchor[1]})
        for prior in old_tasks:
            ratio = SequenceMatcher(None, normalized, normalize(prior["prompt"])).ratio()
            if ratio >= SIMILARITY_THRESHOLD: result["high_similarity_pairs"].append({"candidate_task_id": task_id, "prior_task_id": prior["task_id"], "ratio": round(ratio, 6)})
        seen_prompts.add(task["prompt"]); seen_norm.add(normalized)
    result["counts"] = {"candidates": len(new_tasks), "new_source": sum(v == "new_source" for v in result["novelty_classification"].values()), "new_scenario_same_family": sum(v == "new_scenario_same_family" for v in result["novelty_classification"].values()), "source_document_reuse": len(result["source_document_collisions"]), "source_anchor_reuse": len(result["source_anchor_collisions"]), "within_pack_source_document_reuse": max(0, len(new_tasks) - len({t["provenance"]["source_document"] for t in new_tasks})), "within_pack_source_anchor_reuse": len(new_tasks) - len({(t["provenance"]["source_document"], t["provenance"]["source_anchor"]) for t in new_tasks})}
    return result


def pair_orders(task_ids: list[str]) -> dict[str, list[str]]:
    result = {}
    for task_id in sorted(task_ids):
        digest = hashlib.sha256(f"{PAIR_ORDER_SEED}:{task_id}".encode()).hexdigest()
        result[task_id] = ["control", "treatment"] if int(digest[0], 16) < 8 else ["treatment", "control"]
    return result


def build_manifest(pack_dir: Path, repo_root: Path, *, generated_at: str) -> tuple[dict[str, Any], dict[str, Any]]:
    if pack_dir != repo_root / PACK_ROOT / PACK_DIRECTORY: raise Run8FixtureError(f"unknown Run 8 pack: {pack_dir}")
    paths = fixture_paths(pack_dir)
    if len(paths) != CANDIDATE_COUNT: raise Run8FixtureError(f"expected {CANDIDATE_COUNT} candidates, found {len(paths)}")
    criteria = json.loads((repo_root / DIFFICULTY_PATH).read_text()); tasks = [load_task_fixture(p) for p in paths]
    if any(t["task_family"] != FAMILY for t in tasks) or len({t["task_id"] for t in tasks}) != CANDIDATE_COUNT: raise Run8FixtureError("family or task ID drift")
    allowed = set(criteria["allowed_structural_features"])
    for task in tasks:
        if _validator_result(json.dumps(representative_output(task), sort_keys=True), task, attempt_id=f"run8-satisfiability-{task['task_id']}")["validation_status"] != "passed": raise Run8FixtureError(f"unsatisfiable fixture: {task['task_id']}")
        calibration = task.get("calibration", {}); features = set(calibration.get("difficulty_features", []))
        if calibration.get("target_evidence_resolution") != RESOLUTION or calibration.get("target_evidence_key") != FAMILY or calibration.get("difficulty_band") != "enriched" or calibration.get("selection_basis") != "structural_only" or calibration.get("model_outputs_consulted") is not False: raise Run8FixtureError(f"fixture binding mismatch: {task['task_id']}")
        if len(features) < criteria["minimum_structural_features_per_candidate"] or not features <= allowed: raise Run8FixtureError(f"difficulty features mismatch: {task['task_id']}")
        failed = _validator_result(json.dumps({"allowed_targets": [], "held_targets": [], "scope_expansion_required": False, "review_status": "ready_for_review"}, sort_keys=True), task, attempt_id=f"run8-signature-{task['task_id']}")
        if calibration.get("target_failure_classes") != failure_classes(failure_signature(FAMILY, failed)): raise Run8FixtureError(f"failure-class binding mismatch: {task['task_id']}")
    audit = novelty_audit(pack_dir, repo_root)
    if any(audit[k] for k in ("task_id_collisions", "exact_prompt_duplicates", "normalized_prompt_duplicates", "high_similarity_pairs")): raise Run8FixtureError("freshness audit found a collision or high-similarity pair")
    records = [{"path": str(path.relative_to(repo_root)), "task_id": task["task_id"], "source_document": task["provenance"]["source_document"], "source_anchor": task["provenance"]["source_anchor"], "fixture_sha256": sha256_bytes(path.read_bytes()), "difficulty_features": task["calibration"]["difficulty_features"]} for path, task in zip(paths, tasks)]
    audit["audit_sha256"] = sha256_bytes(canonical(audit).encode()); task_ids = [t["task_id"] for t in tasks]
    manifest = {"schema": "zth_run8_scope_fixture_manifest_v1", "pack_id": pack_dir.name, "generated_at": generated_at, "model_outputs_consulted": False, "candidate_count": CANDIDATE_COUNT, "target_included_count": TARGET_COUNT, "task_family": FAMILY, "target_evidence_resolution": RESOLUTION, "difficulty_criteria_path": DIFFICULTY_PATH, "difficulty_criteria_sha256": sha256_bytes((repo_root / DIFFICULTY_PATH).read_bytes()), "fixtures": records, "candidate_order": task_ids, "eligibility": ["transport_valid=true", "transport_classification=model_response", "deterministic baseline validation failure", "target resolution=failure_class", "target evidence key=scope-authority-boundary", "frozen structural difficulty criteria satisfied"], "selection_rule": "Select the first 20 eligible failures in frozen candidate order; never use intervention outcomes for inclusion.", "reserve_rule": "Candidates not selected after baseline eligibility remain reserve-only; no adaptive replacement.", "pair_order": {"seed": PAIR_ORDER_SEED, "algorithm": "sha256(str(seed) + ':' + task_id), first hex digit < 8 means control-first", "orders": pair_orders(task_ids)}, "novelty_audit_path": str((pack_dir / "novelty_audit.json").relative_to(repo_root)), "novelty_audit_sha256": audit["audit_sha256"], "provenance_path": PROVENANCE_PATH, "provenance_sha256": sha256_bytes((repo_root / PROVENANCE_PATH).read_bytes()), "manifest_sha256": None, "pack_sha256": None}
    basis = dict(manifest); basis["manifest_sha256"] = None; manifest["manifest_sha256"] = sha256_bytes(canonical(basis).encode()); pack_basis = dict(manifest); pack_basis["pack_sha256"] = None; manifest["pack_sha256"] = sha256_bytes(canonical(pack_basis).encode())
    return manifest, audit


def verify_manifest(pack_dir: Path, repo_root: Path) -> dict[str, Any]:
    manifest = json.loads((pack_dir / "manifest.json").read_text()); expected, _ = build_manifest(pack_dir, repo_root, generated_at=manifest["generated_at"])
    if manifest != expected: raise Run8FixtureError(f"manifest drift: {pack_dir}")
    return manifest
