#!/usr/bin/env python3
"""Offline capability cards and advisory intervention recommendations.

This module reads completed ZTH trajectory artifacts only.  It never calls a
model and never executes an intervention.  Transport-invalid attempts are
preserved as exclusions, not capability failures.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


RESOURCE_TIERS = {
    "none": 0,
    "deterministic_patch_retry": 1,
    "local_teacher": 2,
    "external_teacher": 3,
}
EVIDENCE_MIN_OBSERVATIONS = 3
EVIDENCE_MIN_RESCUE_RATE = 0.50
INTERVENTION_SOURCES = tuple(RESOURCE_TIERS)
SOURCE_COMMITS = {"run1": "d27c1e7dd72997eda1bf0b69b73f0a586cb3e395", "run2": "3fc3a44cfcefcac50a5fe06d0dbf35b6c9203815"}
FAILURE_CLASS_MAP = {
    "parse_json": ("serialization",),
    "required_fields": ("contract_shape",),
    "required_field_types": ("contract_shape",),
    "allowed_held_target_separation": ("contract_shape",),
    "reference_required_packet_schema": ("contract_shape", "reference_fact_application"),
    "reference_required_review_required": ("contract_shape", "reference_fact_application"),
    "reference_review_schema": ("contract_shape", "reference_fact_application"),
    "reference_required_allowed_targets": ("authority_boundary", "reference_fact_application"),
    "reference_required_held_targets": ("authority_boundary", "reference_fact_application"),
    "reference_forbidden_allowed_targets": ("authority_boundary", "reference_fact_application"),
    "reference_out_of_scope_target": ("authority_boundary", "reference_fact_application"),
    "reference_queue_handoff_status": ("authority_boundary", "reference_fact_application"),
    "reference_repo_mutation_status": ("authority_boundary", "reference_fact_application"),
    "reference_review_status": ("authority_boundary", "reference_fact_application"),
    "reference_expected_review_status": ("authority_boundary", "reference_fact_application"),
    "reference_source_review_status": ("authority_boundary", "reference_fact_application"),
    "reference_required_authority_boundary_terms": ("authority_boundary", "reference_fact_application"),
    "reference_requires_scope_expansion_flag": ("authority_boundary", "unsupported_inference"),
    "reference_uncertainty": ("unsupported_inference",),
    "reference_unsafe_cleanup": ("destructive_restraint",),
    "reference_required_inspection_commands": ("destructive_restraint",),
}


class CapabilityEvidenceError(ValueError):
    """Raised when durable evidence is malformed or incomplete."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CapabilityEvidenceError(f"cannot read JSON evidence: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CapabilityEvidenceError(f"evidence must be an object: {path}")
    return value


def failure_signature(task_family: str, validation: Mapping[str, Any] | None) -> dict[str, Any]:
    """Normalize deterministic failed check IDs into a routing-safe key."""
    validation = validation or {}
    structural = validation.get("structural_checks")
    semantic = validation.get("semantic_checks")
    checks = validation.get("checks", [])
    if not isinstance(structural, list):
        structural = [c for c in checks if isinstance(c, dict) and not c.get("reference_fact")]
    if not isinstance(semantic, list):
        semantic = [c for c in checks if isinstance(c, dict) and c.get("reference_fact")]

    def failed_ids(items: Any) -> list[str]:
        if not isinstance(items, list):
            raise CapabilityEvidenceError("validation check collection must be a list")
        ids = []
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("check_id"), str):
                raise CapabilityEvidenceError("validation checks require check_id objects")
            if item.get("status") == "failed":
                ids.append(item["check_id"])
        return sorted(set(ids))

    return {
        "task_family": task_family,
        "structural": failed_ids(structural),
        "semantic": failed_ids(semantic),
    }


def signature_key(signature: Mapping[str, Any]) -> str:
    normalized = {
        "task_family": signature.get("task_family"),
        "structural": sorted(signature.get("structural", [])),
        "semantic": sorted(signature.get("semantic", [])),
    }
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"))


def failure_classes(signature: Mapping[str, Any]) -> list[str]:
    """Map known deterministic check IDs to broad classes; unknowns stay visible."""
    classes: set[str] = set()
    check_ids = [*signature.get("structural", []), *signature.get("semantic", [])]
    for check_id in check_ids:
        classes.update(FAILURE_CLASS_MAP.get(check_id, (f"unclassified:{check_id}",)))
    return sorted(classes)


def _resolution_key(signature: Mapping[str, Any], resolution: str) -> str:
    family = signature.get("task_family")
    if resolution == "exact_signature":
        return signature_key(signature)
    if resolution == "semantic_signature":
        return json.dumps({"task_family": family, "semantic": sorted(signature.get("semantic", []))}, sort_keys=True, separators=(",", ":"))
    if resolution == "failure_class":
        return json.dumps({"task_family": family, "failure_classes": failure_classes(signature)}, sort_keys=True, separators=(",", ":"))
    if resolution == "task_family":
        return json.dumps({"task_family": family}, sort_keys=True, separators=(",", ":"))
    raise CapabilityEvidenceError(f"unknown evidence resolution: {resolution}")


EVIDENCE_RESOLUTIONS = ("exact_signature", "semantic_signature", "failure_class", "task_family")


def _valid_worker_attempts(task_dir: Path) -> list[dict[str, Any]]:
    trajectory_path = task_dir / "trajectory.jsonl"
    if not trajectory_path.is_file():
        raise CapabilityEvidenceError(f"missing trajectory: {trajectory_path}")
    attempts = []
    try:
        lines = trajectory_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise CapabilityEvidenceError(f"cannot read trajectory: {trajectory_path}: {exc}") from exc
    for line_number, line in enumerate(lines, 1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CapabilityEvidenceError(f"malformed trajectory {trajectory_path}:{line_number}: {exc}") from exc
        if not isinstance(record, dict) or record.get("record_type") != "worker_attempt":
            continue
        source = record.get("intervention_source")
        if source not in INTERVENTION_SOURCES:
            raise CapabilityEvidenceError(f"unknown intervention source in {trajectory_path}:{line_number}")
        transport = record.get("transport_classification")
        # Older Run 1 records predate the explicit transport fields.  In that
        # case consult the preserved raw response artifact; an explicit
        # request/http error is never treated as a model response.
        valid = record.get("transport_valid") is True and transport == "model_response"
        raw = None
        raw_ref = (record.get("artifact_refs") or {}).get("raw")
        if not valid and isinstance(raw_ref, str):
            raw_path = task_dir / raw_ref
            if raw_path.is_file():
                raw = _read_json(raw_path)
                raw_status = raw.get("status")
                raw_error = (raw.get("metadata") or {}).get("error")
                valid = raw_status in {"ok", "success", "model_response"} and not raw_error and bool(raw.get("content"))
        if not valid:
            # Keep this as an exclusion record for review, but never score it.
            continue
        validation = record.get("validation")
        if not isinstance(validation, dict):
            raise CapabilityEvidenceError(f"valid worker attempt lacks validation: {trajectory_path}:{line_number}")
        if validation.get("validation_status") not in {"passed", "failed"}:
            raise CapabilityEvidenceError(f"invalid validation status: {trajectory_path}:{line_number}")
        record = dict(record)
        record["transport_valid"] = True
        record["transport_classification"] = "model_response"
        attempts.append(record)
    return attempts


def _teacher_call_count(task_dir: Path, source: str) -> int:
    if source == "local_teacher":
        return len(list(task_dir.glob("local-teacher-*.json")))
    if source == "external_teacher":
        return int(_read_json(task_dir / "trajectory_summary.json").get("external_teacher_call_count", 0))
    return 0


def _task_observation(task_dir: Path, run_id: str) -> dict[str, Any] | None:
    summary_path = task_dir / "trajectory_summary.json"
    summary = _read_json(summary_path)
    task_id = summary.get("task_id")
    task_family = summary.get("task_family")
    if not isinstance(task_id, str) or not isinstance(task_family, str):
        raise CapabilityEvidenceError(f"summary lacks task_id/task_family: {summary_path}")
    attempts = _valid_worker_attempts(task_dir)
    if not attempts:
        # A task containing only transport-invalid calls remains reviewable
        # infrastructure evidence, but contributes no capability card.
        return None
    baseline = next((a for a in attempts if a.get("intervention_source") == "none"), None)
    if baseline is None:
        raise CapabilityEvidenceError(f"task has no valid baseline attempt: {task_id}")
    baseline_signature = failure_signature(task_family, baseline["validation"])
    baseline_pass = baseline["validation"].get("validation_status") == "passed"
    interventions = []
    for attempt in attempts:
        source = attempt["intervention_source"]
        if source == "none":
            continue
        patch_id = attempt.get("deterministic_patch_id")
        patch_hash = attempt.get("deterministic_patch_hash")
        intervention_id = patch_id if source == "deterministic_patch_retry" and patch_id else source
        interventions.append({
            "source": source,
            "intervention_id": intervention_id,
            "patch_id": patch_id,
            "patch_hash": patch_hash,
            "attempt": attempt.get("attempt"),
            "intervention_attempt_id": attempt.get("intervention_id"),
            "passed": attempt["validation"].get("validation_status") == "passed",
            "transport_valid": True,
            "artifact_refs": attempt.get("artifact_refs", {}),
            "artifact_hashes": attempt.get("artifact_hashes", {}),
        })
    return {
        "run_id": run_id,
        "task_id": task_id,
        "task_family": task_family,
        "worker_model": summary.get("worker_model"),
        "baseline_pass": baseline_pass,
        "baseline_signature": baseline_signature,
        "baseline_attempt": baseline.get("attempt"),
        "baseline_artifacts": baseline.get("artifact_refs", {}),
        "baseline_hashes": baseline.get("artifact_hashes", {}),
        "interventions": interventions,
        "infrastructure_error_count": int(summary.get("infrastructure_error_count", 0)),
        "external_teacher_calls": int(summary.get("external_teacher_call_count", 0)),
        "teacher_calls": {source: _teacher_call_count(task_dir, source) for source in ("local_teacher", "external_teacher")},
        "teacher_artifacts": [
            {"kind": "local_teacher", "ref": p.name, "sha256": _sha256(p)}
            for p in sorted(task_dir.glob("local-teacher-*.json"))
        ] + ([{"kind": "external_teacher", "ref": "external-teacher.json", "sha256": _sha256(task_dir / "external-teacher.json")}]
             if (task_dir / "external-teacher.json").is_file() else []),
        "source_summary": summary_path.as_posix(),
    }


def discover_task_dirs(run_roots: Iterable[Path]) -> list[tuple[str, Path]]:
    found = []
    for root in run_roots:
        for summary_path in sorted(root.rglob("trajectory_summary.json")):
            task_dir = summary_path.parent
            if task_dir.name in {"preflight", "reproducibility_canary"}:
                continue
            run_id = "run2" if "reviewed_v2" in root.as_posix() else "run1"
            found.append((run_id, task_dir))
    return found


def _evidence_status(eligible: int, rescue_rate: float) -> str:
    if eligible >= EVIDENCE_MIN_OBSERVATIONS and rescue_rate >= EVIDENCE_MIN_RESCUE_RATE:
        return "supported"
    if eligible >= 1:
        return "observed"
    return "insufficient"


def build_capability_cards(run_roots: Iterable[Path], *, generated_at: str | None = None) -> dict[str, Any]:
    all_tasks = discover_task_dirs(run_roots)
    observations = [obs for run_id, task_dir in all_tasks if (obs := _task_observation(task_dir, run_id)) is not None]
    if not observations:
        raise CapabilityEvidenceError("no task trajectories found")
    groups: dict[tuple[Any, ...], dict[str, Any]] = {}
    counted_teacher_calls: set[tuple[tuple[Any, ...], str, str]] = set()
    for obs in observations:
        base_sig = obs["baseline_signature"]
        entries = [{
            "source": "none", "intervention_id": "baseline_worker", "passed": obs["baseline_pass"],
            "attempt": obs["baseline_attempt"], "artifact_refs": obs["baseline_artifacts"], "artifact_hashes": obs["baseline_hashes"],
        }, *obs["interventions"]]
        for entry in entries:
            # Run 1 and Run 2 use compatible transport/validation semantics;
            # combine comparable evidence while retaining source_runs below.
            key = (obs["worker_model"], obs["task_family"], signature_key(base_sig), entry["source"], entry.get("intervention_id"))
            card = groups.setdefault(key, {
                "schema": "zth_capability_card_v1",
                "identity": {"worker_model": obs["worker_model"], "intervention_type": entry["source"], "intervention_id": entry.get("intervention_id"), "patch_id": entry.get("patch_id"), "patch_sha256": entry.get("patch_hash")},
                "context": {"source_runs": [obs["run_id"]], "task_family": obs["task_family"], "failure_signature": base_sig},
                "observations": {"eligible_attempts": 0, "eligible_task_opportunities": 0, "valid_model_attempts": 0, "successes": 0, "failures": 0, "rescued_tasks": 0, "task_ids": [], "rescued_task_ids": [], "attempts": [], "teacher_call_count": 0},
                "cost": {"worker_calls": 0, "local_teacher_calls": 0, "external_teacher_calls": 0},
                "provenance": {"source_runs": [obs["run_id"]], "source_commits": [SOURCE_COMMITS[obs["run_id"]]], "artifacts": []},
            })
            if obs["run_id"] not in card["context"]["source_runs"]:
                card["context"]["source_runs"].append(obs["run_id"])
            if SOURCE_COMMITS[obs["run_id"]] not in card["provenance"]["source_commits"]:
                card["provenance"]["source_commits"].append(SOURCE_COMMITS[obs["run_id"]])
            card["observations"]["eligible_attempts"] += 1
            card["observations"]["valid_model_attempts"] += 1
            card["observations"]["successes"] += int(entry["passed"])
            card["observations"]["failures"] += int(not entry["passed"])
            if obs["task_id"] not in card["observations"]["task_ids"]:
                card["observations"]["task_ids"].append(obs["task_id"])
                card["observations"]["eligible_task_opportunities"] += 1
            if entry["passed"] and obs["task_id"] not in card["observations"]["rescued_task_ids"] and entry["source"] != "none":
                card["observations"]["rescued_task_ids"].append(obs["task_id"])
            card["observations"]["attempts"].append({"task_id": obs["task_id"], "attempt": entry.get("attempt"), "intervention_attempt_id": entry.get("intervention_attempt_id"), "passed": entry["passed"], "artifact_refs": entry.get("artifact_refs", {}), "artifact_hashes": entry.get("artifact_hashes", {})})
            card["cost"]["worker_calls"] += 1
            if entry["source"] in {"local_teacher", "external_teacher"}:
                calls = obs["teacher_calls"][entry["source"]]
                call_key = (key, obs["task_id"], entry["source"])
                if call_key not in counted_teacher_calls:
                    counted_teacher_calls.add(call_key)
                    card["observations"]["teacher_call_count"] += calls
                    card["cost"]["local_teacher_calls"] += calls if entry["source"] == "local_teacher" else 0
                    card["cost"]["external_teacher_calls"] += calls if entry["source"] == "external_teacher" else 0
            for kind, ref in entry.get("artifact_refs", {}).items():
                card["provenance"]["artifacts"].append({"task_id": obs["task_id"], "kind": kind, "ref": ref})
            if entry["source"] in {"local_teacher", "external_teacher"}:
                card["provenance"]["artifacts"].extend({"task_id": obs["task_id"], **artifact} for artifact in obs["teacher_artifacts"])
    cards = []
    for card in groups.values():
        eligible = card["observations"]["eligible_attempts"]
        successes = card["observations"]["successes"]
        opportunities = card["observations"]["eligible_task_opportunities"]
        card["observations"]["rescued_tasks"] = len(card["observations"]["rescued_task_ids"])
        card["observations"]["rescue_rate"] = card["observations"]["rescued_tasks"] / opportunities if opportunities else 0.0
        card["evidence"] = {"sample_count": opportunities, "status": _evidence_status(opportunities, card["observations"]["rescue_rate"]), "limitations": "Counts are empirical and not statistical significance."}
        cards.append(card)
    cards.sort(key=lambda c: (c["context"]["task_family"], c["identity"]["intervention_type"], signature_key(c["context"]["failure_signature"])))
    return {"schema": "zth_capability_cards_bundle_v1", "generated_at": generated_at, "thresholds": {"min_observations_for_supported": EVIDENCE_MIN_OBSERVATIONS, "min_rescue_rate_for_supported": EVIDENCE_MIN_RESCUE_RATE}, "cards": cards, "source_task_count": len(all_tasks), "transport_excluded_task_count": len(all_tasks) - len(observations)}


def _card_id(card: Mapping[str, Any]) -> str:
    payload = {"identity": card.get("identity"), "context": card.get("context")}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def build_hierarchical_evidence(cards: Mapping[str, Any]) -> dict[str, Any]:
    """Aggregate cards at each explicit resolution without losing card provenance."""
    result: dict[str, Any] = {}
    for resolution in EVIDENCE_RESOLUTIONS:
        groups: dict[tuple[str, str], dict[str, Any]] = {}
        for card in cards.get("cards", []):
            sig = card["context"]["failure_signature"]
            key = (_resolution_key(sig, resolution), card["identity"]["intervention_type"])
            group = groups.setdefault(key, {
                "resolution": resolution,
                "resolution_key": key[0],
                "task_family": sig["task_family"],
                "intervention": key[1],
                "eligible_task_opportunities": 0,
                "worker_retry_attempts": 0,
                "rescued_task_ids": [],
                "task_ids": [],
                "teacher_call_count": 0,
                "source_runs": [],
                "source_card_ids": [],
            })
            obs = card["observations"]
            group["eligible_task_opportunities"] += int(obs.get("eligible_task_opportunities", len(obs.get("task_ids", []))))
            group["worker_retry_attempts"] += int(obs.get("eligible_attempts", 0))
            for task_id in obs.get("task_ids", []):
                if task_id not in group["task_ids"]:
                    group["task_ids"].append(task_id)
            for task_id in obs.get("rescued_task_ids", []):
                if task_id not in group["rescued_task_ids"]:
                    group["rescued_task_ids"].append(task_id)
            group["teacher_call_count"] += int(obs.get("teacher_call_count", 0))
            for run in card["context"].get("source_runs", []):
                if run not in group["source_runs"]:
                    group["source_runs"].append(run)
            group["source_card_ids"].append(_card_id(card))
        rows = []
        for group in groups.values():
            opportunities = group["eligible_task_opportunities"]
            rescued = len(group["rescued_task_ids"])
            rate = rescued / opportunities if opportunities else 0.0
            polarity = "supported_positive" if opportunities >= EVIDENCE_MIN_OBSERVATIONS and rate >= EVIDENCE_MIN_RESCUE_RATE else "supported_negative" if opportunities >= EVIDENCE_MIN_OBSERVATIONS else "observed" if opportunities else "insufficient"
            # A sufficiently sampled failure pattern can be supported-negative
            # even when it does not meet the positive rescue-rate threshold.
            status = "supported" if opportunities >= EVIDENCE_MIN_OBSERVATIONS else "observed" if opportunities else "insufficient"
            group.update({"rescued_tasks": rescued, "rescue_rate": rate, "evidence_status": status, "evidence_polarity": polarity})
            rows.append(group)
        result[resolution] = sorted(rows, key=lambda row: (row["task_family"], row["intervention"], row["resolution_key"]))
    return result


def _support_for_source(hierarchy: Mapping[str, Any], signature: Mapping[str, Any], source: str) -> list[dict[str, Any]]:
    values = []
    for resolution in EVIDENCE_RESOLUTIONS:
        key = _resolution_key(signature, resolution)
        values.extend(row for row in hierarchy.get(resolution, []) if row["resolution_key"] == key and row["intervention"] == source)
    return values


def recommend_intervention(*, task_family: str, validation: Mapping[str, Any], available_interventions: Iterable[str], cards: Mapping[str, Any]) -> dict[str, Any]:
    """Return an advisory recommendation using exact-to-family evidence backoff."""
    sig = failure_signature(task_family, validation)
    hierarchy = cards.get("hierarchy") or build_hierarchical_evidence(cards)
    available = {source for source in available_interventions if source in RESOURCE_TIERS}
    candidates = []
    for source in sorted(available, key=lambda value: RESOURCE_TIERS[value]):
        rows = _support_for_source(hierarchy, sig, source)
        by_resolution = {row["resolution"]: row for row in rows}
        selected = None
        for resolution in EVIDENCE_RESOLUTIONS:
            row = by_resolution.get(resolution)
            if row is None:
                continue
            if row["evidence_polarity"] == "supported_positive":
                selected = row
                break
        most_specific = next((by_resolution[r] for r in EVIDENCE_RESOLUTIONS if r in by_resolution), None)
        evidence_trace = [{"resolution": r, "evidence_status": by_resolution[r]["evidence_status"], "evidence_polarity": by_resolution[r]["evidence_polarity"], "eligible_task_opportunities": by_resolution[r]["eligible_task_opportunities"], "rescued_tasks": by_resolution[r]["rescued_tasks"], "rescue_rate": by_resolution[r]["rescue_rate"], "source_runs": by_resolution[r]["source_runs"]} for r in EVIDENCE_RESOLUTIONS if r in by_resolution]
        basis = selected or most_specific
        candidates.append({
            "intervention": source,
            "resource_tier": RESOURCE_TIERS[source],
            "evidence_resolution": basis["resolution"] if basis else "none",
            "evidence_status": basis["evidence_status"] if basis else "insufficient",
            "evidence_polarity": basis["evidence_polarity"] if basis else "insufficient",
            "eligible_task_opportunities": basis["eligible_task_opportunities"] if basis else 0,
            "worker_retry_attempts": basis["worker_retry_attempts"] if basis else 0,
            "rescued_tasks": basis["rescued_tasks"] if basis else 0,
            "rescue_rate": basis["rescue_rate"] if basis else 0.0,
            "source_runs": basis["source_runs"] if basis else [],
            "more_specific_evidence": evidence_trace,
            "supported_positive": selected is not None,
        })
    positive = [candidate for candidate in candidates if candidate["supported_positive"]]
    choice = sorted(positive, key=lambda candidate: (candidate["resource_tier"], -candidate["rescue_rate"]))[0] if positive else None
    negative = any(candidate["evidence_polarity"] == "supported_negative" for candidate in candidates)
    disposition = "recommend" if choice else "avoid" if negative else "abstain"
    reason = "Advisory evidence only; no intervention is executed or skipped automatically."
    if disposition == "avoid":
        reason = "Supported-negative evidence exists, but no available intervention has supported-positive evidence."
    elif disposition == "abstain":
        reason = "No available intervention has supported-positive evidence at any evidence resolution."
    return {
        "recommended_intervention": choice["intervention"] if choice else None,
        "routing_disposition": disposition,
        "evidence_resolution": choice["evidence_resolution"] if choice else "none",
        "evidence_status": choice["evidence_status"] if choice else "insufficient",
        "evidence_polarity": choice["evidence_polarity"] if choice else "insufficient",
        "reason": reason,
        "failure_signature": sig,
        "support": choice or {"eligible_task_opportunities": 0, "rescued_tasks": 0, "rescue_rate": 0.0, "source_runs": []},
        "more_specific_evidence": choice["more_specific_evidence"] if choice else [candidate["more_specific_evidence"] for candidate in candidates],
        "alternatives": candidates,
        "authority": "advisory_only",
    }


def build_accounting_audit(run_roots: Iterable[Path]) -> list[dict[str, Any]]:
    """Count task opportunities separately from worker attempts and teacher calls."""
    rows = []
    for run_id, root in (("run2" if "reviewed_v2" in root.as_posix() else "run1", root) for root in run_roots):
        tasks = []
        excluded = 0
        for _, task_dir in discover_task_dirs([root]):
            observation = _task_observation(task_dir, run_id)
            if observation is None:
                excluded += 1
            else:
                tasks.append(observation)
        sources = {"none": [], "deterministic_patch_retry": [], "local_teacher": [], "external_teacher": []}
        for task in tasks:
            sources["none"].append({"task_id": task["task_id"], "passed": task["baseline_pass"], "worker_attempts": 1, "teacher_calls": 0})
            for source in ("deterministic_patch_retry", "local_teacher", "external_teacher"):
                attempts = [item for item in task["interventions"] if item["source"] == source]
                if source in {"local_teacher", "external_teacher"} and not attempts:
                    continue
                if not attempts:
                    continue
                sources[source].append({"task_id": task["task_id"], "passed": any(item["passed"] for item in attempts), "worker_attempts": len(attempts), "teacher_calls": task["teacher_calls"].get(source, 0)})
        for source, values in sources.items():
            rows.append({"run": run_id, "intervention": source, "task_ids": [v["task_id"] for v in values], "eligible_task_opportunities": len(values), "worker_retry_attempts": sum(v["worker_attempts"] for v in values), "rescued_tasks": sum(1 for v in values if v["passed"] and source != "none"), "passes": sum(1 for v in values if v["passed"]), "teacher_calls": sum(v["teacher_calls"] for v in values), "infrastructure_exclusions": excluded})
    return rows


def write_evidence_bundle(bundle: Mapping[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "capability_cards.json").write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    hierarchy = build_hierarchical_evidence(bundle)
    for resolution, filename in (("exact_signature", "exact_signature_matrix.json"), ("semantic_signature", "semantic_signature_matrix.json"), ("failure_class", "failure_class_matrix.json"), ("task_family", "family_intervention_matrix.json")):
        rows = hierarchy[resolution]
        (output_dir / filename).write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    accounting = []
    for root in (Path(".work/capability_batch_reviewed_v1"), Path(".work/capability_batch_reviewed_v2/run")):
        if root.exists():
            accounting.extend(build_accounting_audit([root]))
    (output_dir / "accounting_audit.json").write_text(json.dumps(accounting, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    examples = []
    seen_signatures = set()
    for card in bundle["cards"]:
        if "run2" not in card["context"].get("source_runs", []):
            continue
        sig = card["context"]["failure_signature"]
        key = signature_key(sig)
        if key in seen_signatures:
            continue
        seen_signatures.add(key)
        validation = {
            "structural_checks": [{"check_id": check_id, "status": "failed"} for check_id in sig["structural"]],
            "semantic_checks": [{"check_id": check_id, "status": "failed"} for check_id in sig["semantic"]],
        }
        examples.append(recommend_intervention(task_family=sig["task_family"], validation=validation, available_interventions=INTERVENTION_SOURCES, cards={**bundle, "hierarchy": hierarchy}))
    (output_dir / "routing_evidence_summary.json").write_text(json.dumps({"authority": "advisory_only", "resource_order": RESOURCE_TIERS, "examples": examples, "evidence_resolutions": EVIDENCE_RESOLUTIONS}, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", action="append", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    bundle = build_capability_cards(args.run_root, generated_at=datetime.now(timezone.utc).isoformat())
    write_evidence_bundle(bundle, args.output_dir)
    print(json.dumps({"cards": len(bundle["cards"]), "source_task_count": bundle["source_task_count"], "output_dir": str(args.output_dir)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
