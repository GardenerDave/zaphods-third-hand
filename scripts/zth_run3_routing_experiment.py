#!/usr/bin/env python3
"""Execute the frozen Run 3 two-arm comparison with durable, fail-closed state.

This driver is intentionally an experiment harness, not autonomous routing. It
consults the frozen advisory router only for the explicitly authorized Run 3
treatment arm and reuses the supervised capability-loop primitive for every
worker/teacher attempt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any, Callable

from local_harness.capability_cards import build_hierarchical_evidence, recommend_intervention
from local_harness.icm_call import call_worker
from local_harness.icm_spec import classify_worker_response, resolve_worker_spec
from local_harness.supervised_capability_loop import (
    _append_jsonl,
    _json_write,
    _response_payload,
    _transition,
    _validator_result,
    load_task_fixture,
    run_capability_loop,
    sha256_text,
    utc_now,
)

RESOURCE_ACTIONS = {
    "fixed_ladder": ("baseline", "deterministic_patch_retry", "local_teacher", "external_teacher"),
    "deterministic_patch_retry": ("baseline", "deterministic_patch_retry", "local_teacher", "external_teacher"),
    "local_teacher": ("baseline", "local_teacher", "external_teacher"),
    "external_teacher": ("baseline", "external_teacher"),
    "avoid_deterministic_patch_retry": ("baseline", "local_teacher", "external_teacher"),
}


class Run3StateError(RuntimeError):
    """Raised when durable state is incomplete or inconsistent."""


def require_valid_preflight(attempt: dict[str, Any]) -> None:
    """Require authoritative attempt metadata for the non-metric canary."""
    if attempt.get("transport_valid") is not True or attempt.get("transport_classification") != "model_response":
        raise Run3StateError("worker preflight is not a confirmed model response")


def arm_order(task_id: str, seed: str) -> list[str]:
    """Match the preregistered first-bit SHA256 ordering exactly."""
    digest = hashlib.sha256(f"{seed}:{task_id}".encode()).hexdigest()
    return ["control", "treatment"] if int(digest[0], 16) < 8 else ["treatment", "control"]


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture_pack_hash(manifest: dict[str, Any]) -> str:
    values = sorted(entry["fixture_sha256"] for entry in manifest["fixtures"])
    return hashlib.sha256(("\n".join(values) + "\n").encode()).hexdigest()


def load_execution_preregistration(
    preregistration_path: Path,
    *,
    repository_root: Path,
    fixtures_dir_override: Path | None = None,
    driver_path: Path | None = None,
) -> dict[str, Any]:
    """Load and verify experiment-specific execution authority before calls."""
    preregistration = json.loads(preregistration_path.read_text())
    pack = preregistration.get("fixture_pack")
    order = preregistration.get("execution_order")
    frozen = preregistration.get("frozen_inputs")
    if not isinstance(pack, dict) or not isinstance(order, dict) or not isinstance(frozen, dict):
        raise Run3StateError("preregistration lacks the required fixture_pack/execution_order/frozen_inputs schema")
    if preregistration.get("model_calls_made") is not False:
        raise Run3StateError("preregistration is not marked model_calls_made=false")
    fixtures_dir = repository_root / pack["path"]
    if fixtures_dir_override is not None and fixtures_dir_override.resolve() != fixtures_dir.resolve():
        raise Run3StateError("supplied fixture directory does not match preregistration")
    manifest_path = repository_root / pack["manifest_path"]
    if not fixtures_dir.is_dir() or not manifest_path.is_file():
        raise Run3StateError("preregistered fixture directory or manifest is missing")
    if _sha256_file(manifest_path) != pack["manifest_sha256"]:
        raise Run3StateError("fixture manifest hash mismatch")
    manifest = json.loads(manifest_path.read_text())
    entries = manifest.get("fixtures", [])
    if len(entries) != pack["task_count"] or len(entries) != 24:
        raise Run3StateError("fixture count does not match the preregistration")
    task_ids = [entry.get("task_id") for entry in entries]
    if task_ids != pack["task_ids"] or task_ids != sorted(task_ids) or len(set(task_ids)) != len(task_ids):
        raise Run3StateError("preregistered task list drift or ordering mismatch")
    if _fixture_pack_hash(manifest) != pack["pack_sha256"]:
        raise Run3StateError("fixture pack hash mismatch")
    for entry in entries:
        fixture_path = fixtures_dir / entry["path"]
        if not fixture_path.is_file() or _sha256_file(fixture_path) != entry["fixture_sha256"]:
            raise Run3StateError(f"fixture hash mismatch: {entry.get('task_id')}")
        fixture = json.loads(fixture_path.read_text())
        contract_hash = hashlib.sha256(json.dumps(fixture["output_contract"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        facts_hash = hashlib.sha256(json.dumps(fixture["validator"]["reference_facts"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if contract_hash != entry["output_contract_sha256"] or facts_hash != entry["reference_facts_sha256"]:
            raise Run3StateError(f"fixture contract/reference hash mismatch: {entry.get('task_id')}")
    seed = str(order.get("seed"))
    recorded_orders = order.get("arm_order", {})
    expected_orders = {task_id: arm_order(task_id, seed) for task_id in task_ids}
    if recorded_orders != expected_orders:
        raise Run3StateError("preregistered arm order does not match seed")
    if seed == "20260818":
        raise Run3StateError("Run 3B must not reuse the prior Run 3 seed")
    if driver_path is not None and frozen.get("driver_sha256") != _sha256_file(driver_path):
        raise Run3StateError("execution driver hash mismatch")
    for key in ("routing_policy_path", "execution_harness_freeze_path"):
        artifact = repository_root / frozen[key]
        if not artifact.is_file() or _sha256_file(artifact) != frozen[f"{key.replace('_path', '')}_sha256"]:
            raise Run3StateError(f"frozen artifact hash mismatch: {key}")
    return {"preregistration": preregistration, "preregistration_sha256": _sha256_file(preregistration_path), "fixtures_dir": fixtures_dir, "manifest": manifest, "seed": seed, "task_ids": task_ids, "arm_order": expected_orders}


def validate_runtime_bindings(
    execution: dict[str, Any],
    *,
    policy_sha256: str,
    bundle_path: Path,
    patch_id: str,
    patch_sha256: str,
    patch_path: Path,
    worker_model: str | None = None,
    local_teacher_model: str | None = None,
    external_teacher_identity: str | None = None,
    external_timeout: str | None = None,
) -> dict[str, Any]:
    """Verify CLI/config bindings against the frozen preregistration."""
    prereg = execution["preregistration"]
    frozen = prereg["frozen_inputs"]
    models = prereg["models"]
    if policy_sha256 != frozen["routing_policy_sha256"]:
        raise Run3StateError("supplied policy hash does not match preregistration")
    if not bundle_path.is_file() or _sha256_file(bundle_path) != frozen["capability_bundle_sha256"]:
        raise Run3StateError("capability evidence bundle hash mismatch")
    if patch_id != frozen["patch_id"] or patch_sha256 != frozen["patch_sha256"]:
        raise Run3StateError("supplied patch identity does not match preregistration")
    if not patch_path.is_file() or _sha256_file(patch_path) != frozen["patch_sha256"]:
        raise Run3StateError("patch file hash does not match preregistration")
    effective_models = {
        "worker": worker_model if worker_model is not None else os.environ.get("ZTH_CAPABILITY_WORKER_MODEL"),
        "local_teacher": local_teacher_model if local_teacher_model is not None else os.environ.get("ZTH_CAPABILITY_TEACHER_MODEL"),
        "external_teacher": external_teacher_identity if external_teacher_identity is not None else os.environ.get("ZTH_EXTERNAL_TEACHER_IDENTITY"),
    }
    for role, expected in models.items():
        if effective_models.get(role) != expected:
            raise Run3StateError(f"configured {role} identity does not match preregistration")
    configured_timeout = external_timeout if external_timeout is not None else os.environ.get("ZTH_RUN3_EXTERNAL_TEACHER_TIMEOUT", "120")
    try:
        timeout = int(configured_timeout)
    except (TypeError, ValueError) as exc:
        raise Run3StateError("external teacher timeout is not an integer") from exc
    if timeout != prereg.get("external_teacher_timeout_seconds"):
        raise Run3StateError("external teacher timeout does not match preregistration")
    return {"models": effective_models, "external_timeout_seconds": timeout}


def _valid_attempt_record(out_dir: Path) -> dict[str, Any] | None:
    raw_path = out_dir / "attempt-1.raw.json"
    metadata_path = out_dir / "attempt-1.metadata.json"
    trajectory = out_dir / "trajectory.jsonl"
    if not any(p.exists() for p in (raw_path, metadata_path, trajectory)):
        return None
    if not all(p.exists() for p in (raw_path, metadata_path, trajectory)):
        raise Run3StateError(f"incomplete baseline artifacts; refusing another call: {out_dir}")
    records = [json.loads(line) for line in trajectory.read_text().splitlines() if line.strip()]
    attempts = [r for r in records if r.get("record_type") == "worker_attempt" and r.get("attempt") == 1]
    if len(attempts) != 1:
        raise Run3StateError(f"baseline attempt is not uniquely durable: {out_dir}")
    record = attempts[0]
    raw = json.loads(raw_path.read_text())
    if record.get("artifact_hashes", {}).get("raw") != sha256_text(raw_path.read_text()):
        raise Run3StateError(f"baseline raw artifact hash mismatch: {out_dir}")
    if record.get("transport_classification") == "model_response" and not (out_dir / "attempt-1.validation.json").exists():
        raise Run3StateError(f"valid baseline lacks validation artifact: {out_dir}")
    return record


def _assert_no_incomplete_transitions(out_dir: Path) -> None:
    trajectory = out_dir / "trajectory.jsonl"
    if not trajectory.exists():
        return
    records = [json.loads(line) for line in trajectory.read_text().splitlines() if line.strip()]
    for record in records:
        transition = record.get("transition")
        if transition == "worker_call_started":
            attempt = record.get("attempt")
            if not (out_dir / f"attempt-{attempt}.raw.json").exists():
                raise Run3StateError(f"worker call has no durable response; refusing resume: {out_dir}")
        elif transition == "local_teacher_started":
            if not (out_dir / f"local-teacher-{record.get('attempt')}.json").exists():
                raise Run3StateError(f"local-teacher call has no durable response; refusing resume: {out_dir}")
        elif transition == "external_teacher_started":
            if not (out_dir / "external-teacher.json").exists() and not (out_dir / "external-teacher.infrastructure.json").exists():
                raise Run3StateError(f"external-teacher call has no durable response; refusing resume: {out_dir}")


def _baseline(task: dict[str, Any], out_dir: Path, worker: Callable[[str], Any] | None = None) -> dict[str, Any]:
    """Make exactly one baseline call, or recover its already durable record."""
    existing = _valid_attempt_record(out_dir)
    if existing is not None:
        return existing
    out_dir.mkdir(parents=True, exist_ok=True)
    trajectory = out_dir / "trajectory.jsonl"
    prompt = task["prompt"]
    prompt_path = out_dir / "attempt-1.prompt.txt"
    prompt_path.write_text(prompt, encoding="utf-8")
    _transition(trajectory, transition="worker_call_started", task_id=task["task_id"], attempt=1, source="none", intervention_id="none:1", prompt_artifact=prompt_path.name, prompt_sha256=sha256_text(prompt))
    if worker is None:
        spec = resolve_worker_spec(os.environ.get("ZTH_CAPABILITY_WORKER_NAME", "router"), base_url=os.environ.get("ZTH_CAPABILITY_WORKER_BASE_URL"), model=os.environ.get("ZTH_CAPABILITY_WORKER_MODEL"))
        worker = lambda p, s=spec: call_worker(s, p, int(os.environ.get("ZTH_CAPABILITY_WORKER_MAX_TOKENS", "768")), timeout=int(os.environ.get("ZTH_CAPABILITY_WORKER_TIMEOUT", "900")))
    response = worker(prompt)
    raw_payload = _response_payload(response)
    raw_path = out_dir / "attempt-1.raw.json"
    _json_write(raw_path, raw_payload)
    _transition(trajectory, transition="worker_output_captured", task_id=task["task_id"], attempt=1, source="none", intervention_id="none:1", artifact_ref=raw_path.name, artifact_hash=sha256_text(raw_path.read_text()))
    classification = raw_payload.get("metadata", {}).get("transport_classification") or classify_worker_response(raw_payload.get("status", ""), raw_payload.get("metadata", {}).get("error"))
    validation = None
    if classification == "model_response":
        validation = _validator_result(raw_payload["content"], task, attempt_id="attempt-1")
        validation_path = out_dir / "attempt-1.validation.json"
        _json_write(validation_path, validation)
        _transition(trajectory, transition="worker_output_validated", task_id=task["task_id"], attempt=1, source="none", intervention_id="none:1", validation=validation, artifact_ref=validation_path.name, artifact_hash=sha256_text(validation_path.read_text()))
    metadata = {
        "attempt": 1, "intervention_source": "none", "intervention_id": "none:1", "escalation_level": 0,
        "applied_patch_ids": [], "applied_patch_hashes": {}, "transport_valid": classification == "model_response",
        "transport_classification": classification, "validation_status": validation.get("validation_status") if validation else None,
        "endpoint_alias": raw_payload.get("metadata", {}).get("endpoint_alias", "JARVIS_LOCAL"),
        "request_provenance": raw_payload.get("metadata", {}).get("request_provenance"),
        "prompt_artifact": prompt_path.name, "prompt_sha256": sha256_text(prompt),
    }
    metadata_path = out_dir / "attempt-1.metadata.json"
    _json_write(metadata_path, metadata)
    record = {
        "record_type": "worker_attempt", **metadata, "raw_output": raw_payload.get("content", ""), "validation": validation,
        "transport_error": raw_payload.get("metadata", {}).get("error") if classification != "model_response" else None,
        "artifact_refs": {"raw": raw_path.name, "prompt": prompt_path.name, "metadata": metadata_path.name, **({"validation": "attempt-1.validation.json"} if validation else {})},
        "artifact_hashes": {"raw": sha256_text(raw_path.read_text()), "prompt": sha256_text(prompt_path.read_text()), "metadata": sha256_text(metadata_path.read_text()), **({"validation": sha256_text((out_dir / "attempt-1.validation.json").read_text())} if validation else {})},
        "worker_model": raw_payload.get("metadata", {}).get("model") or "unknown",
        "review_state": "ready_for_review" if validation and validation.get("validation_status") == "passed" else "infrastructure_error" if classification != "model_response" else "unresolved",
    }
    _append_jsonl(trajectory, record)
    return record


def derive_action(advisory: dict[str, Any]) -> str:
    """Translate frozen advisory evidence into preregistered experiment action."""
    disposition = advisory.get("routing_disposition")
    recommendation = advisory.get("recommended_intervention")
    if disposition == "recommend" and recommendation in RESOURCE_ACTIONS:
        return recommendation
    if disposition == "avoid":
        negative = [a for a in advisory.get("alternatives", []) if a.get("evidence_polarity") == "supported_negative"]
        avoided = sorted(negative, key=lambda a: (a.get("resource_tier", 99), a.get("intervention", "")))
        if avoided and avoided[0].get("intervention") == "deterministic_patch_retry":
            return "avoid_deterministic_patch_retry"
    return "fixed_ladder"


def route(task: dict[str, Any], validation: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    hierarchy = build_hierarchical_evidence(bundle)
    return recommend_intervention(task_family=task["task_family"], validation=validation, available_interventions=["deterministic_patch_retry", "local_teacher", "external_teacher"], cards={**bundle, "hierarchy": hierarchy})


def external_teacher(raw_prompt: str) -> tuple[str, str]:
    command = os.environ.get("ZTH_EXTERNAL_TEACHER_COMMAND")
    if not command:
        raise RuntimeError("external teacher unavailable: command not configured")
    completed = subprocess.run(shlex.split(command), input=raw_prompt, text=True, capture_output=True, timeout=int(os.environ.get("ZTH_RUN3_EXTERNAL_TEACHER_TIMEOUT", "120")), check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"external teacher command failed with exit code {completed.returncode}")
    return os.environ.get("ZTH_EXTERNAL_TEACHER_IDENTITY", "codex-unconfigured"), completed.stdout


def _run_one(task: dict[str, Any], arm: str, out_dir: Path, bundle: dict[str, Any], patch_config: dict[str, str]) -> None:
    summary_path = out_dir / "trajectory_summary.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text())
        if summary.get("arm") != arm:
            if summary.get("task_id") != task["task_id"]:
                raise Run3StateError(f"arm identity mismatch: {out_dir}")
            advisory_path = out_dir / "router_advisory.json"
            advisory = json.loads(advisory_path.read_text()) if advisory_path.exists() else None
            summary.update({"arm": arm, "router_advisory": advisory, "routing_disposition": advisory.get("routing_disposition") if advisory else None, "routing_evidence_resolution": advisory.get("evidence_resolution") if advisory else None, "routing_action": advisory.get("actual_action", "fixed_ladder") if advisory else "fixed_ladder", "policy_freeze_sha256": patch_config["policy_sha256"]})
            _json_write(summary_path, summary)
        return
    baseline = _baseline(task, out_dir)
    if baseline.get("transport_classification") != "model_response" or baseline.get("transport_valid") is not True:
        raise Run3StateError(f"baseline transport invalid; refusing to continue arm: {out_dir}")
    if baseline.get("validation", {}).get("validation_status") == "passed":
        transitions = [json.loads(line) for line in (out_dir / "trajectory.jsonl").read_text().splitlines() if line.strip()]
        if any(row.get("transition") in {"ready_for_review", "unresolved"} for row in transitions):
            raise Run3StateError(f"terminal transition exists without summary; refusing duplicate transition: {out_dir}")
        _transition(out_dir / "trajectory.jsonl", transition="ready_for_review", task_id=task["task_id"], source="none", disposition="ready_for_review", successful_intervention_source="none")
        _json_write(summary_path, {"task_id": task["task_id"], "task_family": task["task_family"], "arm": arm, "transport_valid": True, "capability_verdict_available": True, "pass": True, "first_attempt_pass": True, "unresolved": False, "successful_intervention_source": "none", "disposition": "ready_for_review"})
        return
    advisory_path = out_dir / "router_advisory.json"
    advisory = json.loads(advisory_path.read_text()) if advisory_path.exists() else route(task, baseline["validation"], bundle) if arm == "treatment" else None
    action = advisory.get("actual_action", derive_action(advisory)) if advisory else "fixed_ladder"
    if advisory:
        if not advisory_path.exists():
            advisory = {**advisory, "policy_freeze_sha256": patch_config["policy_sha256"], "actual_action": action, "authority": "advisory_only_with_explicit_experiment_harness_authorization"}
            _transition(out_dir / "trajectory.jsonl", transition="router_consulted", task_id=task["task_id"], source="advisory_router", advisory=advisory)
            _json_write(advisory_path, advisory)
    patch = patch_config if action in {"fixed_ladder", "deterministic_patch_retry"} else None
    teacher_passes = 0 if action == "external_teacher" else 2
    _assert_no_incomplete_transitions(out_dir)
    run_capability_loop(task, out_dir=out_dir, max_worker_attempts=1, max_teacher_passes=teacher_passes, deterministic_patch_retry=patch, external_teacher=external_teacher)
    summary = json.loads(summary_path.read_text())
    summary.update({"arm": arm, "router_advisory": advisory, "routing_disposition": advisory.get("routing_disposition") if advisory else None, "routing_evidence_resolution": advisory.get("evidence_resolution") if advisory else None, "routing_action": action, "policy_freeze_sha256": patch_config["policy_sha256"]})
    _json_write(summary_path, summary)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixtures_dir", type=Path, nargs="?")
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--patch-path", type=Path, required=True)
    parser.add_argument("--patch-id", required=True)
    parser.add_argument("--patch-sha256", required=True)
    parser.add_argument("--policy-sha256", required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    try:
        execution = load_execution_preregistration(
            args.preregistration,
            repository_root=Path.cwd(),
            fixtures_dir_override=args.fixtures_dir,
            driver_path=Path(__file__).resolve(),
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"invalid preregistration: {exc}") from exc
    except Run3StateError as exc:
        raise SystemExit(str(exc)) from exc
    fixtures = sorted(p for p in execution["fixtures_dir"].glob("*.json") if p.name != "manifest.json")
    try:
        bindings = validate_runtime_bindings(
            execution,
            policy_sha256=args.policy_sha256,
            bundle_path=args.bundle,
            patch_id=args.patch_id,
            patch_sha256=args.patch_sha256,
            patch_path=args.patch_path,
        )
    except Run3StateError as exc:
        raise SystemExit(str(exc)) from exc
    if args.out_dir.exists() and any(args.out_dir.iterdir()) and not args.resume:
        raise SystemExit("output directory is non-empty; use a new directory or explicit safe resume")
    manifest = {"schema": "zth_run3_execution_manifest_v1", "status": "running", "preregistration_path": str(args.preregistration), "preregistration_sha256": execution["preregistration_sha256"], "policy_sha256": args.policy_sha256, "capability_bundle_sha256": execution["preregistration"]["frozen_inputs"]["capability_bundle_sha256"], "patch_id": args.patch_id, "patch_sha256": args.patch_sha256, "driver_sha256": execution["preregistration"]["frozen_inputs"]["driver_sha256"], "fixture_pack_sha256": execution["preregistration"]["fixture_pack"]["pack_sha256"], "worker_model": bindings["models"]["worker"], "local_teacher_model": bindings["models"]["local_teacher"], "external_teacher_identity": bindings["models"]["external_teacher"], "external_timeout_seconds": bindings["external_timeout_seconds"], "seed": execution["seed"], "task_ids": execution["task_ids"], "arm_order": execution["arm_order"], "model_calls_started": False}
    args.out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.out_dir / "run3_execution_manifest.json"
    if args.resume:
        if not manifest_path.is_file() or json.loads(manifest_path.read_text()).get("status") != "running":
            raise SystemExit("safe resume requires a matching running execution manifest")
    else:
        _json_write(manifest_path, manifest)
    bundle = json.loads(args.bundle.read_text())
    patch_config = {"patch_id": args.patch_id, "patch_path": str(args.patch_path), "patch_sha256": args.patch_sha256, "policy_sha256": args.policy_sha256}
    manifest["model_calls_started"] = True
    _json_write(manifest_path, manifest)
    for fixture_path in fixtures:
        task = load_task_fixture(fixture_path)
        for arm in execution["arm_order"][task["task_id"]]:
            _run_one(task, arm, args.out_dir / arm / task["task_id"], bundle, patch_config)
    manifest["status"] = "completed"
    _json_write(manifest_path, manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
