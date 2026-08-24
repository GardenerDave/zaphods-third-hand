#!/usr/bin/env python3
"""One-shot Stage B acquisition; scoring is intentionally out of scope.

This module imports no evaluator and never interprets a supplier response.
It consumes only the frozen Stage B controller, runtime, and payload artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from local_harness.icm_call import call_worker
from local_harness.icm_spec import resolve_worker_spec


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/research"
FREEZE = DOCS / "CLEAN_GRANULARITY_REPLICATION_STAGE_B_FREEZE_2026-08-24.json"
RUNTIME = DOCS / "CLEAN_GRANULARITY_REPLICATION_STAGE_B_RUNTIME_MANIFEST_2026-08-24.json"
PAYLOADS = DOCS / "CLEAN_GRANULARITY_REPLICATION_STAGE_B_PAYLOAD_MANIFEST_2026-08-24.json"
INTERFACE = DOCS / "DIRECT_UNIT_CALIBRATION_INTERFACE_CONTRACT_V2_2026-08-24.json"
EXPECTED_ANCESTOR = "1f98bf7fb8d73f133d59e00ea067ad2611e3c94c"
LOCAL_IDENTITY = "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf"
EXTERNAL_IDENTITY = "codex-cli-0.146.0"
EXTERNAL_CWD = Path("/tmp")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_digest(path: Path) -> str:
    return digest(path.read_bytes())


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def write_json(path: Path, value: Any) -> str:
    data = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return digest(data)


def atomic_json(path: Path, value: Any) -> str:
    temp = path.with_name(path.name + ".tmp")
    result = write_json(temp, value)
    os.replace(temp, path)
    return result


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ancestor(commit: str) -> None:
    result = subprocess.run(["git", "merge-base", "--is-ancestor", commit, "HEAD"], cwd=ROOT, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"required commit is not an ancestor: {commit}")


def verify_frozen_hashes(freeze: dict[str, Any], *, include_scoring_artifacts: bool) -> None:
    artifact_paths = {
        "runtime": RUNTIME,
        "payload": PAYLOADS,
    }
    if include_scoring_artifacts:
        artifact_paths.update({
            "evaluator": DOCS / "CLEAN_GRANULARITY_REPLICATION_STAGE_B_EVALUATOR_CASES_2026-08-24.json",
            "policies": DOCS / "CLEAN_GRANULARITY_REPLICATION_STAGE_B_POLICIES_2026-08-24.json",
            "freshness": DOCS / "CLEAN_GRANULARITY_REPLICATION_STAGE_B_FRESHNESS_AUDIT_2026-08-24.json",
        })
    for key, path in artifact_paths.items():
        if file_digest(path) != freeze.get("freeze_artifact_hashes", {}).get(key):
            raise RuntimeError(f"frozen artifact hash mismatch: {key}")


def load_inputs(*, include_scoring_artifacts: bool = False) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    ancestor(EXPECTED_ANCESTOR)
    freeze = read_json(FREEZE)
    runtime = read_json(RUNTIME)
    payloads = read_json(PAYLOADS)
    verify_frozen_hashes(freeze, include_scoring_artifacts=include_scoring_artifacts)
    if freeze.get("freeze_status") != "frozen_unexecuted":
        raise RuntimeError("Stage B freeze is not frozen_unexecuted")
    if freeze.get("cohort", {}).get("target_outcomes") != 0:
        raise RuntimeError("Stage B already has target outcomes")
    if runtime.get("case_count") != 16 or len(runtime.get("execution_order", [])) != 32:
        raise RuntimeError("Stage B case/order count mismatch")
    if runtime.get("evaluator_information_included") is not False or runtime.get("policy_metadata_included") is not False:
        raise RuntimeError("runtime manifest exposes evaluator or policy metadata")
    if len(payloads.get("cases", [])) != 16 or payloads.get("evaluator_information_included") is not False:
        raise RuntimeError("payload manifest mismatch")
    if freeze.get("characterization", {}).get("STAGE_B_EVALUATOR_SYNTHETIC_SATISFIABILITY") != "16/16":
        raise RuntimeError("evaluator satisfiability provenance mismatch")
    if freeze.get("runtime_evaluator_isolation", {}).get("runtime_manifest_evaluator_influence") != 0:
        raise RuntimeError("runtime/evaluator isolation provenance mismatch")
    payload_by_id = {item["case_id"]: item for item in payloads["cases"]}
    runtime_ids = runtime["case_order"]
    if runtime_ids != [item["case_id"] for item in runtime["cases"]] or runtime_ids != payloads["case_order"]:
        raise RuntimeError("frozen case order mismatch")
    for case in runtime["cases"]:
        item = payload_by_id.get(case["case_id"])
        if item is None:
            raise RuntimeError(f"missing payload: {case['case_id']}")
        payload = item["experiment_authored_payload"]
        if payload["request"] != case["request"] or payload["authority_context"] != case["authority_context"]:
            raise RuntimeError(f"request/authority mismatch: {case['case_id']}")
        if digest(canonical(payload)) != item["payload_sha256"] or case.get("payload_sha256") != item["payload_sha256"]:
            raise RuntimeError(f"payload hash mismatch: {case['case_id']}")
        if item["supplier_arms"] != ["local_teacher", "external_teacher"]:
            raise RuntimeError(f"supplier arms mismatch: {case['case_id']}")
    if any(word in json.dumps(runtime).casefold() for word in ("evaluator_reference", "evaluator_path", "expected_answer", "scoring_outcome", "must_include", "must_not_include")):
        raise RuntimeError("evaluator/scoring field found in runtime manifest")
    if any(row["supplier_id"] not in {"local_teacher", "external_teacher"} for row in runtime["execution_order"]):
        raise RuntimeError("unknown supplier in execution order")
    if sum(row["supplier_id"] == "local_teacher" for row in runtime["execution_order"]) != 16:
        raise RuntimeError("local schedule count mismatch")
    if sum(row["supplier_id"] == "external_teacher" for row in runtime["execution_order"]) != 16:
        raise RuntimeError("external schedule count mismatch")
    return freeze, runtime, payloads


def preflight() -> int:
    freeze, runtime, payloads = load_inputs(include_scoring_artifacts=True)
    policies = read_json(DOCS / "CLEAN_GRANULARITY_REPLICATION_STAGE_B_POLICIES_2026-08-24.json")
    if policies.get("policy_decisions_frozen_pre_target_outcome") is not True or policies.get("stage_b_outcome_influence_on_policy") != 0:
        raise RuntimeError("policy freeze marker mismatch")
    print(json.dumps({
        "status": "preflight_pass",
        "freeze_sha256": file_digest(FREEZE),
        "policies_sha256": freeze["freeze_artifact_hashes"]["policies"],
        "runtime_sha256": file_digest(RUNTIME),
        "payload_sha256": file_digest(PAYLOADS),
        "interface_sha256": file_digest(INTERFACE),
        "case_count": len(runtime["cases"]),
        "triage_cases": sum(item["capability_family"] == "triage-routing" for item in runtime["cases"]),
        "unsupported_certainty_cases": sum(item["capability_family"] == "unsupported-certainty" for item in runtime["cases"]),
        "planned_local_calls": 16,
        "planned_external_calls": 16,
        "planned_supplier_calls": 32,
        "evaluator_loaded": False,
        "second_acquisition_process_started": False,
        "target_outcomes": 0,
    }, sort_keys=True))
    return 0


def local_capture(prompt: str) -> dict[str, Any]:
    spec = resolve_worker_spec(
        os.environ.get("ZTH_CAPABILITY_TEACHER_NAME", "handoff"),
        base_url=os.environ.get("ZTH_CAPABILITY_TEACHER_BASE_URL"),
        model=os.environ.get("ZTH_CAPABILITY_TEACHER_MODEL", LOCAL_IDENTITY),
    )
    started = time.monotonic()
    response = call_worker(spec, prompt, int(os.environ.get("ZTH_STAGE_B_LOCAL_MAX_TOKENS", "1000")), timeout=int(os.environ.get("ZTH_STAGE_B_LOCAL_TIMEOUT", "900")))
    elapsed = round((time.monotonic() - started) * 1000.0, 3)
    metadata = response.metadata()
    metadata.update({
        "endpoint_alias": os.environ.get("ZTH_PUBLIC_HOST_ALIAS", "JARVIS_LOCAL"),
        "tool_calls": 0,
        "repository_access": False,
        "evaluator_access": False,
        "supplier_native_envelope_control": "BEST_AVAILABLE_OBSERVATION",
        "request_elapsed_ms": elapsed,
    })
    return {"status": response.status, "content": response.content, "metadata": metadata}


def external_capture(prompt: str) -> dict[str, Any]:
    command = os.environ.get("ZTH_EXTERNAL_TEACHER_COMMAND", "/home/navigator/bin/zth-codex-teacher")
    identity = os.environ.get("ZTH_EXTERNAL_TEACHER_IDENTITY", EXTERNAL_IDENTITY)
    started = time.monotonic()
    completed = subprocess.run(shlex.split(command), input=prompt, text=True, capture_output=True, cwd=EXTERNAL_CWD, timeout=int(os.environ.get("ZTH_STAGE_B_EXTERNAL_TIMEOUT", "120")), check=False)
    elapsed = round((time.monotonic() - started) * 1000.0, 3)
    stderr = completed.stderr
    lower = stderr.casefold()
    tool_markers = [term for term in ("tool call", "shell", "apply_patch", "read_file", "write_file", "exec_command") if term in lower]
    repo_markers = [term for term in ("git status", "git diff", "repository", "workspace") if term in lower]
    return {
        "status": "ok" if completed.returncode == 0 and completed.stdout.strip() else ("empty_content" if completed.returncode == 0 else "external_nonzero_exit"),
        "content": completed.stdout,
        "metadata": {
            "identity": identity,
            "command_sha256": digest(command.encode()),
            "cwd": str(EXTERNAL_CWD),
            "request_elapsed_ms": elapsed,
            "exit_code": completed.returncode,
            "transport_classification": "model_response" if completed.returncode == 0 and completed.stdout.strip() else "transport_or_empty_failure",
            "tool_calls_observed": len(tool_markers),
            "tool_marker_terms_observed": tool_markers,
            "repository_marker_terms_observed": repo_markers,
            "repository_access_observed": bool(repo_markers),
            "evaluator_access": False,
            "native_envelope_control": "BEST_AVAILABLE_OBSERVATION",
            "stderr_sha256": digest(stderr.encode()),
        },
        "stderr": stderr,
    }


def execute(output_dir: Path) -> int:
    freeze, runtime, payloads = load_inputs()
    if output_dir.exists():
        raise RuntimeError("output directory exists; refusing replay or resume")
    output_dir.mkdir(parents=True, exist_ok=False)
    payload_by_id = {item["case_id"]: item for item in payloads["cases"]}
    payload_dir = output_dir / "experiment_payloads"
    for case_id in runtime["case_order"]:
        payload = payload_by_id[case_id]["experiment_authored_payload"]
        payload_bytes = canonical(payload)
        path = payload_dir / f"{case_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload_bytes)
        if digest(payload_bytes) != payload_by_id[case_id]["payload_sha256"]:
            raise RuntimeError(f"payload materialization mismatch: {case_id}")
    execution = {
        "schema": "zth_clean_granularity_replication_stage_b_execution_manifest_v1",
        "status": "PREPARED",
        "prepared_at": now(),
        "freeze_sha256": file_digest(FREEZE),
        "frozen_policy_artifact_sha256": freeze["freeze_artifact_hashes"]["policies"],
        "runtime_manifest_sha256": file_digest(RUNTIME),
        "payload_manifest_sha256": file_digest(PAYLOADS),
        "interface_sha256": file_digest(INTERFACE),
        "planned_supplier_calls": 32,
        "planned_local_calls": 16,
        "planned_external_calls": 16,
        "execution_order": runtime["execution_order"],
        "evaluator_loaded_during_acquisition": False,
        "retries": 0,
        "replays": 0,
        "second_acquisition_process_started": False,
        "schedule_frozen_before_first_call": True,
    }
    execution_path = output_dir / "execution_manifest.json"
    atomic_json(execution_path, execution)
    execution["status"] = "RUNNING"
    execution["started_at"] = now()
    atomic_json(execution_path, execution)

    records: list[dict[str, Any]] = []
    for ordinal, item in enumerate(runtime["execution_order"], start=1):
        case_id, supplier_id = item["case_id"], item["supplier_id"]
        arm_dir = output_dir / "cases" / case_id / supplier_id
        arm_dir.mkdir(parents=True, exist_ok=False)
        payload_bytes = (payload_dir / f"{case_id}.json").read_bytes()
        payload = json.loads(payload_bytes.decode("utf-8"))
        payload_hash = digest(payload_bytes)
        (arm_dir / "experiment_payload.json").write_bytes(payload_bytes)
        started_at = now()
        started = time.monotonic()
        write_json(arm_dir / "call_started.json", {
            "schema": "zth_clean_granularity_replication_stage_b_call_started_v1",
            "ordinal": ordinal,
            "case_id": case_id,
            "supplier_id": supplier_id,
            "supplier_identity": LOCAL_IDENTITY if supplier_id == "local_teacher" else EXTERNAL_IDENTITY,
            "experiment_payload_sha256": payload_hash,
            "supplier_prompt_sha256": digest(payload["prompt"].encode("utf-8")),
            "started_at": started_at,
            "tool_calls": 0 if supplier_id == "local_teacher" else "observed_after_call",
            "repository_access": False if supplier_id == "local_teacher" else "observed_after_call",
            "evaluator_access": False,
        })
        raw: dict[str, Any] | None = None
        failure: dict[str, Any] | None = None
        try:
            raw = local_capture(payload["prompt"]) if supplier_id == "local_teacher" else external_capture(payload["prompt"])
            stderr = raw.pop("stderr", "")
            if supplier_id == "external_teacher":
                (arm_dir / "stderr.txt").write_text(stderr, encoding="utf-8")
            content_bytes = str(raw.get("content", "")).encode("utf-8")
            raw.update({"case_id": case_id, "supplier_id": supplier_id, "ordinal": ordinal, "experiment_payload_sha256": payload_hash, "supplier_prompt_sha256": digest(payload["prompt"].encode("utf-8")), "captured_at": now(), "raw_content_sha256": digest(content_bytes)})
            response_hash = write_json(arm_dir / "response.json", raw)
            records.append({"ordinal": ordinal, "case_id": case_id, "supplier_id": supplier_id, "disposition": "response", "response_sha256": response_hash, "raw_content_sha256": raw["raw_content_sha256"], "payload_sha256": payload_hash, "tool_calls_observed": raw.get("metadata", {}).get("tool_calls", raw.get("metadata", {}).get("tool_calls_observed")), "repository_access_observed": raw.get("metadata", {}).get("repository_access", raw.get("metadata", {}).get("repository_access_observed", False))})
        except Exception as exc:
            failure = {"schema": "zth_clean_granularity_replication_stage_b_failure_v1", "ordinal": ordinal, "case_id": case_id, "supplier_id": supplier_id, "supplier_identity": LOCAL_IDENTITY if supplier_id == "local_teacher" else EXTERNAL_IDENTITY, "error": str(exc)[-4000:], "started_at": started_at, "captured_at": now(), "evaluator_access": False, "tool_calls_observed": 0 if supplier_id == "local_teacher" else "unknown", "repository_access_observed": False if supplier_id == "local_teacher" else "unknown"}
            if supplier_id == "external_teacher":
                (arm_dir / "stderr.txt").write_text(str(exc), encoding="utf-8")
            failure_hash = write_json(arm_dir / "infrastructure_failure.json", failure)
            records.append({"ordinal": ordinal, "case_id": case_id, "supplier_id": supplier_id, "disposition": "infrastructure_failure", "failure_sha256": failure_hash, "payload_sha256": payload_hash, "tool_calls_observed": failure["tool_calls_observed"], "repository_access_observed": failure["repository_access_observed"]})
        elapsed = round((time.monotonic() - started) * 1000.0, 3)
        write_json(arm_dir / "call_finished.json", {"schema": "zth_clean_granularity_replication_stage_b_call_finished_v1", "ordinal": ordinal, "case_id": case_id, "supplier_id": supplier_id, "finished_at": now(), "elapsed_ms": elapsed, "terminal_disposition": "response" if raw is not None else "infrastructure_failure"})

    complete = len(records) == 32 and len({(r["case_id"], r["supplier_id"]) for r in records}) == 32
    execution["status"] = "TERMINAL_COMPLETE" if complete else "TERMINAL_INCOMPLETE"
    execution["finished_at"] = now()
    execution["actual_supplier_calls"] = len(records)
    execution["actual_local_calls"] = sum(r["supplier_id"] == "local_teacher" for r in records)
    execution["actual_external_calls"] = sum(r["supplier_id"] == "external_teacher" for r in records)
    execution["terminal_dispositions"] = len(records)
    atomic_json(execution_path, execution)
    sealed = {
        "schema": "zth_clean_granularity_replication_stage_b_raw_response_manifest_v1",
        "status": "SEALED_BEFORE_EVALUATION" if complete else "SEALED_INCOMPLETE_BEFORE_EVALUATION",
        "raw_stage_b_responses_sealed_before_evaluation": True,
        "evaluator_loaded_during_acquisition": False,
        "planned_supplier_calls": 32,
        "actual_supplier_calls": len(records),
        "actual_local_calls": sum(r["supplier_id"] == "local_teacher" for r in records),
        "actual_external_calls": sum(r["supplier_id"] == "external_teacher" for r in records),
        "retries": 0,
        "replays": 0,
        "second_acquisition_process_started": False,
        "records": records,
    }
    write_json(output_dir / "raw_response_manifest.json", sealed)
    write_json(output_dir / "lifecycle.json", {"status": "terminal_complete" if complete else "terminal_incomplete", "processes_started": 1, "second_acquisition_process_started": False, "supplier_calls": len(records), "local_calls": sealed["actual_local_calls"], "external_calls": sealed["actual_external_calls"], "evaluator_loaded_during_acquisition": False, "raw_sealed_before_evaluation": True, "retries": 0, "replays": 0})
    if not complete:
        raise RuntimeError("acquisition terminally incomplete; no retry/resume permitted")
    print(json.dumps({"status": "acquisition_complete_raw_sealed", "run_dir": str(output_dir), "actual_supplier_calls": len(records), "actual_local_calls": sealed["actual_local_calls"], "actual_external_calls": sealed["actual_external_calls"], "evaluator_loaded_during_acquisition": False}, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.preflight:
        return preflight()
    if args.execute and args.output_dir:
        path = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
        return execute(path)
    parser.error("use --preflight or --execute --output-dir")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
