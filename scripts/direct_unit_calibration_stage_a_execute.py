#!/usr/bin/env python3
"""One-shot, V2-only Stage A direct-unit calibration acquisition.

This driver intentionally has no import or path reference to the scoring-only
evaluator. It sends the exact prompt bytes from the frozen payload manifest and
records raw supplier/protocol evidence. It never retries, repairs, or scores.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
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
FREEZE = ROOT / "docs/research/DIRECT_UNIT_CALIBRATION_FREEZE_V2_2026-08-24.json"
INTERFACE = ROOT / "docs/research/DIRECT_UNIT_CALIBRATION_INTERFACE_CONTRACT_V2_2026-08-24.json"
RUNTIME = ROOT / "docs/research/DIRECT_UNIT_CALIBRATION_RUNTIME_MANIFEST_V2_2026-08-24.json"
PAYLOADS = ROOT / "docs/research/DIRECT_UNIT_CALIBRATION_PAYLOAD_MANIFEST_V2_2026-08-24.json"
EXTERNAL_CWD = Path("/tmp")
EXPECTED_HEAD_ANCESTOR = "0886fb4626ee64efafad8015d3bd5ea3b0e153e9"
LOCAL_IDENTITY = "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf"
EXTERNAL_IDENTITY = "codex-cli-0.146.0"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_digest(path: Path) -> str:
    return digest(path.read_bytes())


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def write_json(path: Path, value: Any) -> str:
    data = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return digest(data)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_ancestor(commit: str) -> None:
    result = subprocess.run(["git", "merge-base", "--is-ancestor", commit, "HEAD"], cwd=ROOT, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"required commit is not an ancestor: {commit}")


def load_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    assert_ancestor(EXPECTED_HEAD_ANCESTOR)
    freeze = read_json(FREEZE)
    interface = read_json(INTERFACE)
    runtime = read_json(RUNTIME)
    payloads = read_json(PAYLOADS)
    if freeze.get("freeze_characterization") != "DIRECT_UNIT_CALIBRATION_EXPERIMENT_CORRECTED_FREEZE_UNEXECUTED":
        raise RuntimeError("V2 freeze characterization mismatch")
    if runtime.get("case_count") != 16 or runtime.get("planned_new_supplier_calls") != 32:
        raise RuntimeError("V2 runtime count mismatch")
    if runtime.get("planned_new_local_calls") != 16 or runtime.get("planned_new_external_calls") != 16:
        raise RuntimeError("V2 arm budget mismatch")
    if freeze.get("preserved_protocol", {}).get("contradiction_reserve_included") is not False:
        raise RuntimeError("contradiction reserve is present")
    if freeze.get("preserved_protocol", {}).get("outcome_conditional_sample_extension_permitted") is not False:
        raise RuntimeError("adaptive sample extension is not disabled")
    if len(runtime["cases"]) != 16 or len(payloads["cases"]) != 16:
        raise RuntimeError("V2 case/payload count mismatch")
    if runtime["case_order"] != [case["case_id"] for case in runtime["cases"]]:
        raise RuntimeError("runtime case order is not explicit")
    if runtime["case_order"] != payloads["case_order"]:
        raise RuntimeError("runtime/payload order mismatch")
    payload_by_id = {case["case_id"]: case for case in payloads["cases"]}
    for case in runtime["cases"]:
        payload_record = payload_by_id.get(case["case_id"])
        if payload_record is None:
            raise RuntimeError(f"missing frozen payload: {case['case_id']}")
        payload = payload_record["experiment_authored_payload"]
        if payload["request"] != case["request"] or payload["authority_context"] != case["authority_context"]:
            raise RuntimeError(f"payload/request mismatch: {case['case_id']}")
        if digest(canonical(payload)) != payload_record["payload_sha256"]:
            raise RuntimeError(f"frozen payload hash mismatch: {case['case_id']}")
        if payload_record["supplier_arms"] != ["local_teacher", "external_teacher"]:
            raise RuntimeError(f"supplier arm mismatch: {case['case_id']}")
        if case["interface_id"] != payload_record["interface_id"] or case["interface_hash"] != payload_record["interface_hash"]:
            raise RuntimeError(f"interface lineage mismatch: {case['case_id']}")
    if any(key in json.dumps(runtime).lower() for key in ("evaluator_reference", "evaluator_path", "expected_answer", "scoring_outcome")):
        raise RuntimeError("evaluator metadata found in runtime manifest")
    return freeze, interface, runtime, payloads


def balanced_schedule(runtime: dict[str, Any]) -> list[dict[str, str]]:
    schedule: list[dict[str, str]] = []
    for index, case in enumerate(runtime["cases"], start=1):
        first, second = (("local_teacher", "external_teacher") if index % 2 else ("external_teacher", "local_teacher"))
        schedule.extend([{"case_id": case["case_id"], "supplier_id": first}, {"case_id": case["case_id"], "supplier_id": second}])
    if len(schedule) != 32 or sum(row["supplier_id"] == "local_teacher" for row in schedule) != 16:
        raise RuntimeError("balanced schedule mismatch")
    return schedule


def preflight() -> int:
    freeze, interface, runtime, payloads = load_inputs()
    schedule = balanced_schedule(runtime)
    print(json.dumps({
        "status": "preflight_pass",
        "freeze": file_digest(FREEZE),
        "interface": file_digest(INTERFACE),
        "runtime": file_digest(RUNTIME),
        "payload_manifest": file_digest(PAYLOADS),
        "cases": len(runtime["cases"]),
        "triage_cases": sum(c["capability_family"] == "triage-routing" for c in runtime["cases"]),
        "unsupported_certainty_cases": sum(c["capability_family"] == "unsupported-certainty" for c in runtime["cases"]),
        "planned_local_calls": 16,
        "planned_external_calls": 16,
        "planned_supplier_calls": 32,
        "schedule": schedule,
        "evaluator_loaded": False,
    }, sort_keys=True))
    return 0


def local_capture(prompt: str) -> dict[str, Any]:
    spec = resolve_worker_spec(
        os.environ.get("ZTH_CAPABILITY_TEACHER_NAME", "handoff"),
        base_url=os.environ.get("ZTH_CAPABILITY_TEACHER_BASE_URL"),
        model=os.environ.get("ZTH_CAPABILITY_TEACHER_MODEL", LOCAL_IDENTITY),
    )
    started = time.monotonic()
    response = call_worker(spec, prompt, int(os.environ.get("ZTH_DUC_LOCAL_MAX_TOKENS", "1000")), timeout=int(os.environ.get("ZTH_DUC_LOCAL_TIMEOUT", "900")))
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
    completed = subprocess.run(shlex.split(command), input=prompt, text=True, capture_output=True, cwd=EXTERNAL_CWD, timeout=int(os.environ.get("ZTH_DUC_EXTERNAL_TIMEOUT", "120")), check=False)
    elapsed = round((time.monotonic() - started) * 1000.0, 3)
    stderr = completed.stderr
    lower = stderr.casefold()
    tool_markers = [term for term in ("tool call", "shell", "apply_patch", "read_file", "write_file", "exec_command") if term in lower]
    repo_markers = [term for term in ("git status", "git diff", "repository", "workspace") if term in lower]
    if completed.returncode != 0:
        raise RuntimeError(f"external supplier exited {completed.returncode}: {stderr[-4000:]}")
    return {
        "status": "ok" if completed.stdout.strip() else "empty_content",
        "content": completed.stdout,
        "metadata": {
            "identity": identity,
            "command_sha256": digest(command.encode()),
            "cwd": str(EXTERNAL_CWD),
            "request_elapsed_ms": elapsed,
            "transport_classification": "model_response" if completed.stdout.strip() else "empty_model_response",
            "tool_calls_observed": len(tool_markers),
            "tool_marker_terms_observed": tool_markers,
            "repository_marker_terms_observed": repo_markers,
            "repository_access_observed": bool(repo_markers),
            "evaluator_access": False,
            "native_envelope_control": "BEST_AVAILABLE_OBSERVATION",
            "stderr_sha256": digest(stderr.encode()),
            "stderr": stderr[-8000:],
        },
    }


def execute(output_dir: Path) -> int:
    freeze, interface, runtime, payloads = load_inputs()
    if output_dir.exists():
        raise RuntimeError("output directory already exists; refusing replay or resume")
    output_dir.mkdir(parents=True, exist_ok=False)
    schedule = balanced_schedule(runtime)
    payload_by_id = {case["case_id"]: case for case in payloads["cases"]}
    payload_dir = output_dir / "experiment_payloads"
    for case_id in runtime["case_order"]:
        record = payload_by_id[case_id]
        payload_bytes = canonical(record["experiment_authored_payload"])
        path = payload_dir / f"{case_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload_bytes)
        if digest(payload_bytes) != record["payload_sha256"]:
            raise RuntimeError(f"payload materialization hash mismatch: {case_id}")
    execution_manifest = {
        "schema": "zth_direct_unit_calibration_execution_manifest_v1",
        "status": "running",
        "freeze_sha256": file_digest(FREEZE),
        "interface_sha256": file_digest(INTERFACE),
        "runtime_manifest_sha256": file_digest(RUNTIME),
        "payload_manifest_sha256": file_digest(PAYLOADS),
        "planned_supplier_calls": 32,
        "planned_local_calls": 16,
        "planned_external_calls": 16,
        "execution_order": schedule,
        "payload_hashes": {case["case_id"]: case["payload_sha256"] for case in payloads["cases"]},
        "evaluator_loaded_during_acquisition": False,
        "retries": 0,
        "replays": 0,
        "second_acquisition_process_started": False,
        "schedule_frozen_before_first_call": True,
    }
    write_json(output_dir / "execution_manifest.json", execution_manifest)
    records: list[dict[str, Any]] = []
    case_by_id = {case["case_id"]: case for case in runtime["cases"]}
    for ordinal, item in enumerate(schedule, start=1):
        case_id, supplier_id = item["case_id"], item["supplier_id"]
        arm_dir = output_dir / "cases" / case_id / supplier_id
        arm_dir.mkdir(parents=True, exist_ok=False)
        payload_path = payload_dir / f"{case_id}.json"
        payload_bytes = payload_path.read_bytes()
        payload_hash = digest(payload_bytes)
        (arm_dir / "experiment_payload.json").write_bytes(payload_bytes)
        started_at = now()
        started = time.monotonic()
        write_json(arm_dir / "call_started.json", {
            "schema": "zth_direct_unit_calibration_call_started_v1",
            "ordinal": ordinal,
            "case_id": case_id,
            "supplier_id": supplier_id,
            "supplier_identity": LOCAL_IDENTITY if supplier_id == "local_teacher" else EXTERNAL_IDENTITY,
            "experiment_payload_sha256": payload_hash,
            "started_at": started_at,
            "tool_calls": 0 if supplier_id == "local_teacher" else "observed_after_call",
            "repository_access": False,
            "evaluator_access": False,
        })
        raw: dict[str, Any] | None = None
        failure: dict[str, Any] | None = None
        stderr_path = arm_dir / "stderr.txt"
        try:
            prompt = json.loads(payload_bytes.decode())["prompt"]
            raw = local_capture(prompt) if supplier_id == "local_teacher" else external_capture(prompt)
            if supplier_id == "external_teacher":
                stderr_path.write_text(raw["metadata"].pop("stderr", ""), encoding="utf-8")
            raw.update({"case_id": case_id, "supplier_id": supplier_id, "ordinal": ordinal, "experiment_payload_sha256": payload_hash, "captured_at": now(), "raw_response_sha256": digest(str(raw.get("content", "")).encode())})
            response_hash = write_json(arm_dir / "response.json", raw)
            write_json(arm_dir / "power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "available": False, "resource_telemetry": raw.get("metadata", {}).get("resource_telemetry")})
            records.append({"ordinal": ordinal, "case_id": case_id, "supplier_id": supplier_id, "response_sha256": response_hash, "transport_valid": raw.get("metadata", {}).get("transport_classification") == "model_response", "tool_calls_observed": raw.get("metadata", {}).get("tool_calls", raw.get("metadata", {}).get("tool_calls_observed")), "repository_access_observed": raw.get("metadata", {}).get("repository_access", raw.get("metadata", {}).get("repository_access_observed", False)), "captured": True})
        except Exception as exc:
            stderr_path.write_text(str(exc), encoding="utf-8")
            failure = {"schema": "zth_direct_unit_calibration_failure_v1", "ordinal": ordinal, "case_id": case_id, "supplier_id": supplier_id, "supplier_identity": LOCAL_IDENTITY if supplier_id == "local_teacher" else EXTERNAL_IDENTITY, "error": str(exc)[-4000:], "started_at": started_at, "captured_at": now(), "tool_calls_observed": "unknown" if supplier_id == "external_teacher" else 0, "repository_access_observed": "unknown" if supplier_id == "external_teacher" else False, "evaluator_access": False}
            failure_hash = write_json(arm_dir / "infrastructure_failure.json", failure)
            records.append({"ordinal": ordinal, "case_id": case_id, "supplier_id": supplier_id, "failure_sha256": failure_hash, "transport_valid": False, "tool_calls_observed": failure["tool_calls_observed"], "repository_access_observed": failure["repository_access_observed"], "captured": False})
        elapsed = round((time.monotonic() - started) * 1000.0, 3)
        if raw is not None:
            write_json(arm_dir / "call_finished.json", {"ordinal": ordinal, "case_id": case_id, "supplier_id": supplier_id, "finished_at": now(), "elapsed_ms": elapsed, "response_exists": True})
        else:
            write_json(arm_dir / "call_finished.json", {"ordinal": ordinal, "case_id": case_id, "supplier_id": supplier_id, "finished_at": now(), "elapsed_ms": elapsed, "response_exists": False, "infrastructure_failure": True})
    sealed = {
        "schema": "zth_direct_unit_calibration_raw_response_manifest_v1",
        "status": "SEALED_BEFORE_EVALUATION",
        "raw_direct_unit_calibration_responses_sealed_before_evaluation": True,
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
    write_json(output_dir / "lifecycle.json", {"status": "terminal_runtime", "model_calls": len(records), "supplier_calls": len(records), "local_calls": sealed["actual_local_calls"], "external_calls": sealed["actual_external_calls"], "teacher_calls": 0, "tool_calls": 0, "external_inference_calls": sealed["actual_external_calls"], "retries": 0, "replays": 0, "runtime_evaluator_influence": 0, "model_output_granted_authority": 0})
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
        return execute(args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir)
    parser.error("use --preflight or --execute --output-dir")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
