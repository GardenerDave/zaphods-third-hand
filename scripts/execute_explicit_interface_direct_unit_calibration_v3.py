#!/usr/bin/env python3
"""Fail-closed, evaluator-free acquisition harness for Explicit-Interface V3.

The acquisition path consumes only the frozen acquisition projection.  The
scoring evaluator and evaluator-case artifact are intentionally absent from
this module and are permitted only in a later, separate closeout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

if __package__ in {None, ""}:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "research"
FREEZE_NAME = "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_FREEZE_V3_2026-08-24.json"
RUNTIME_NAME = "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_RUNTIME_MANIFEST_V3_2026-08-24.json"
PROJECTION_NAME = "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_ACQUISITION_PROJECTION_V3_2026-08-24.json"
PAYLOAD_NAME = "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_PAYLOAD_MANIFEST_V3_2026-08-24.json"
INTERFACE_NAME = "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_INTERFACE_V3_2026-08-24.json"
EVALUATOR_NAME = "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_EVALUATOR_CASES_V3_2026-08-24.json"
HARNESS_FREEZE_NAME = "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_V3_EXECUTION_HARNESS_FREEZE_2026-08-24.json"
EVALUATOR_IMPL = ROOT / "scripts" / "evaluate_explicit_interface_direct_unit_calibration_v3.py"
PROJECTION_IMPL = ROOT / "scripts" / "project_explicit_interface_direct_unit_calibration_v2_inputs.py"
EXPECTED_FREEZE_COMMIT = "46638a5ce8b461cd57676a1317a4a57d129c7d02"
LOCAL_BASE_URL = "http://192.168.1.16:8080/v1"
LOCAL_MODEL = "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf"
EXTERNAL_WRAPPER = Path("/home/navigator/bin/zth-codex-teacher")
EXTERNAL_WRAPPER_SHA256 = "2c5fcaf0727bdf466e21d660c927e63d23ecb67857949b2ef21e7e599297ceab"
EXPECTED_CODEX_VERSION = "codex-cli 0.146.0"
CODEX_HOME = Path("/tmp/zth_v3_codex_home")
EXTERNAL_CWD = Path("/tmp")
DEFAULT_RUN_ROOT = ROOT / ".work" / "model_size_supplier_floor" / "explicit_interface_direct_unit_calibration_v3"
DEFAULT_GUARD = DEFAULT_RUN_ROOT / "ACQUISITION_GUARD.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write_json(path: Path, value: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with tempfile.NamedTemporaryFile("wb", dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(data)
    temporary.replace(path)
    return sha_file(path)


def load_projection(artifact_dir: Path = DOCS) -> dict[str, Any]:
    projection = read_json(artifact_dir / PROJECTION_NAME)
    if projection.get("evaluator_information_included") is not False or projection.get("scoring_policy_included") is not False:
        raise RuntimeError("acquisition projection contains scoring information")
    if len(projection.get("cases", [])) != 16 or len(projection.get("schedule", [])) != 32:
        raise RuntimeError("V3 projection count mismatch")
    return projection


def validate_schedule(schedule: list[dict[str, Any]], cases: list[dict[str, Any]]) -> None:
    if [item["ordinal"] for item in schedule] != list(range(1, 33)):
        raise RuntimeError("schedule ordinals are not contiguous")
    case_ids = [case["case_id"] for case in cases]
    if len(case_ids) != 16 or len(set(case_ids)) != 16:
        raise RuntimeError("case set is not exactly 16 unique cases")
    by_case: dict[str, list[dict[str, Any]]] = {}
    for item in schedule:
        by_case.setdefault(item["case_id"], []).append(item)
    if set(by_case) != set(case_ids) or any(len(items) != 2 for items in by_case.values()):
        raise RuntimeError("schedule does not contain exactly two arms per case")
    if sum(item["supplier_id"] == "local_teacher" for item in schedule) != 16:
        raise RuntimeError("local call count mismatch")
    if sum(item["supplier_id"] == "external_teacher" for item in schedule) != 16:
        raise RuntimeError("external call count mismatch")
    for case_id, items in by_case.items():
        if sorted(item["supplier_id"] for item in items) != ["external_teacher", "local_teacher"]:
            raise RuntimeError(f"matched arm mismatch: {case_id}")
    for family in ("triage-routing", "unsupported-certainty"):
        family_ids = [case["case_id"] for case in cases if case["capability_family"] == family]
        firsts = [by_case[case_id][0]["first_arm_supplier_id"] for case_id in family_ids]
        if len(family_ids) != 8 or firsts.count("local_teacher") != 4 or firsts.count("external_teacher") != 4:
            raise RuntimeError(f"{family} first-arm balance mismatch")


def validate_matched_messages(projection: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    cases = projection["cases"]
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for case in cases:
        case_id = case["case_id"]
        text = case["supplier_message_text"]
        message = text.encode("utf-8")
        if sha_bytes(message) != case["supplier_message_sha256"]:
            raise RuntimeError(f"frozen supplier message hash mismatch: {case_id}")
        for supplier in ("local_teacher", "external_teacher"):
            by_key[(case_id, supplier)] = {**case, "supplier_id": supplier, "supplier_message_bytes": message}
    for case in cases:
        local = by_key[(case["case_id"], "local_teacher")]
        external = by_key[(case["case_id"], "external_teacher")]
        if local["supplier_message_bytes"] != external["supplier_message_bytes"]:
            raise RuntimeError(f"matched message bytes differ: {case['case_id']}")
    return by_key


def validate_local_configuration() -> dict[str, Any]:
    if "<LAN_HOST>" in LOCAL_BASE_URL or not LOCAL_BASE_URL.startswith("http://192.168.1.16:8080/v1"):
        raise RuntimeError("unresolved or incorrect local endpoint")
    from local_harness.icm_spec import resolve_worker_spec
    spec = resolve_worker_spec("handoff", base_url=LOCAL_BASE_URL, model=LOCAL_MODEL, api="openai-chat")
    if spec.base_url != LOCAL_BASE_URL or spec.model != LOCAL_MODEL:
        raise RuntimeError("local worker resolution diverged from frozen binding")
    for name in ("ZTH_CAPABILITY_TEACHER_BASE_URL", "ICM_HANDOFF_BASE_URL"):
        value = os.environ.get(name)
        if value and value.rstrip("/") != LOCAL_BASE_URL:
            raise RuntimeError(f"local endpoint override diverges: {name}")
    return {"worker": "handoff", "base_url": spec.base_url, "model": spec.model, "api": spec.api, "identity_check": "non_inference_configuration"}


def check_local_models(timeout: int = 10) -> dict[str, Any]:
    identity = validate_local_configuration()
    url = LOCAL_BASE_URL.rstrip("/") + "/models"
    request = urllib.request.Request(url, headers={"Authorization": "Bearer dummy"}, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
        status = response.status
    payload = json.loads(raw.decode("utf-8"))
    models = [item.get("id") for item in payload.get("data", []) if isinstance(item, dict)] if isinstance(payload, dict) else []
    if LOCAL_MODEL not in models:
        raise RuntimeError(f"frozen local model not exposed by /models: {models}")
    return {**identity, "models_url": url, "http_status": status, "observed_models": models, "models_response_sha256": sha_bytes(raw)}


def validate_external_identity() -> dict[str, Any]:
    if not EXTERNAL_WRAPPER.is_file() or not os.access(EXTERNAL_WRAPPER, os.X_OK):
        raise RuntimeError("external wrapper missing or not executable")
    wrapper_hash = sha_file(EXTERNAL_WRAPPER)
    if wrapper_hash != EXTERNAL_WRAPPER_SHA256:
        raise RuntimeError("external wrapper hash mismatch")
    codex = shutil.which("codex")
    if not codex:
        raise RuntimeError("codex executable unavailable")
    version = subprocess.run([codex, "--version"], cwd=EXTERNAL_CWD, capture_output=True, text=True, timeout=10, check=False)
    observed_version = (version.stdout + version.stderr).strip()
    if version.returncode != 0 or EXPECTED_CODEX_VERSION not in observed_version:
        raise RuntimeError(f"Codex version mismatch: {observed_version}")
    if not CODEX_HOME.is_dir() or not os.access(CODEX_HOME, os.R_OK | os.X_OK):
        raise RuntimeError("isolated CODEX_HOME is unavailable")
    status = subprocess.run([codex, "login", "status"], cwd=EXTERNAL_CWD, env={**os.environ, "CODEX_HOME": str(CODEX_HOME)}, capture_output=True, text=True, timeout=20, check=False)
    status_text = (status.stdout + status.stderr).casefold()
    if status.returncode != 0 or "logged in" not in status_text:
        raise RuntimeError("isolated Codex login status is not authenticated")
    if ROOT == EXTERNAL_CWD or ROOT in EXTERNAL_CWD.parents:
        raise RuntimeError("external cwd is inside the repository")
    return {"wrapper": str(EXTERNAL_WRAPPER), "wrapper_sha256": wrapper_hash, "codex_path": str(Path(codex).resolve()), "codex_version": observed_version, "codex_home": str(CODEX_HOME), "cwd": str(EXTERNAL_CWD), "authenticated": True, "tools_mechanically_disabled": False, "tool_calls_observed": "BEST_AVAILABLE_OBSERVATION", "repository_access_observed": "BEST_AVAILABLE_OBSERVATION"}


def preflight(artifact_dir: Path = DOCS) -> dict[str, Any]:
    freeze = read_json(artifact_dir / FREEZE_NAME)
    projection = load_projection(artifact_dir)
    validate_schedule(projection["schedule"], projection["cases"])
    validate_matched_messages(projection)
    if freeze["planned_supplier_calls"] != 32 or freeze["planned_local_calls"] != 16 or freeze["planned_external_calls"] != 16:
        raise RuntimeError("V3 planned call budget mismatch")
    expected = freeze["artifact_hashes"]
    for key, filename in (("interface", INTERFACE_NAME), ("runtime", RUNTIME_NAME), ("payload", PAYLOAD_NAME), ("evaluator_cases", EVALUATOR_NAME), ("projection", PROJECTION_NAME)):
        if sha_file(artifact_dir / filename) != expected[key]:
            raise RuntimeError(f"V3 artifact hash mismatch: {key}")
    if sha_file(EVALUATOR_IMPL) != expected["evaluator_implementation"] or sha_file(PROJECTION_IMPL) != expected["projection_implementation"]:
        raise RuntimeError("frozen implementation hash mismatch")
    harness_freeze = read_json(artifact_dir / HARNESS_FREEZE_NAME)
    if harness_freeze["schedule_sha256"] != sha_bytes(canonical(projection["schedule"])):
        raise RuntimeError("schedule hash mismatch")
    if harness_freeze["execution_harness_sha256"] != sha_file(Path(__file__)):
        raise RuntimeError("harness hash mismatch")
    if DEFAULT_GUARD.exists() or DEFAULT_RUN_ROOT.exists():
        raise RuntimeError("V3 acquisition guard or run directory already exists")
    local = check_local_models()
    external = validate_external_identity()
    return {"status": "preflight_pass", "local": local, "external": external, "schedule_sha256": harness_freeze["schedule_sha256"], "supplier_calls": 0, "model_calls": 0, "external_inference_calls": 0}


def prepare_run(output_dir: Path, artifact_dir: Path = DOCS) -> dict[str, Any]:
    if output_dir.exists():
        raise RuntimeError("run directory exists; refusing resume/replay")
    projection = load_projection(artifact_dir)
    validate_schedule(projection["schedule"], projection["cases"])
    validate_matched_messages(projection)
    output_dir.mkdir(parents=True, exist_ok=False)
    manifest = {"schema": "zth.explicit_interface_direct_unit_calibration_v3.execution_manifest", "status": "PREPARED", "freeze_commit": EXPECTED_FREEZE_COMMIT, "schedule": projection["schedule"], "schedule_sha256": sha_bytes(canonical(projection["schedule"])), "planned_supplier_calls": 32, "planned_local_calls": 16, "planned_external_calls": 16, "processes_started": 0, "second_acquisition_process_started": False, "retries": 0, "replays": 0, "evaluator_file_access_during_acquisition": False, "evaluator_semantics_loaded_during_acquisition": False, "evaluator_runtime_influence": 0, "evaluator_supplier_visibility": False, "raw_explicit_v3_responses_sealed_before_evaluation": False, "supplier_calls": 0}
    atomic_write_json(output_dir / "execution_manifest.json", manifest)
    return manifest


def claim_guard(path: Path) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    value = {"schema": "zth.explicit_interface_direct_unit_calibration_v3.one_shot_guard", "status": "ACQUISITION_CLAIMED", "claimed_at": utc_now(), "freeze_commit": EXPECTED_FREEZE_COMMIT, "harness_sha256": sha_file(Path(__file__)), "processes_started": 1, "second_acquisition_process_started": False}
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError as exc:
        raise RuntimeError("V3 one-shot guard already claimed") from exc
    try:
        os.write(fd, (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    finally:
        os.close(fd)
    return value


def observe_protocol(stdout: bytes, stderr: bytes) -> dict[str, Any]:
    text = (stdout + b"\n" + stderr).decode("utf-8", errors="replace").casefold()
    return {"prohibited_actions_not_observed": not any(x in text for x in ("tool call", "tool_calls", "function_call", "shell command", "exec_command", "apply_patch", "git status", "git diff")), "tool_calls_observed": "BEST_AVAILABLE_OBSERVATION", "repository_access_observed": "BEST_AVAILABLE_OBSERVATION", "observation_basis": "marker_scan_best_available_observation"}


def capture_local(message: bytes) -> dict[str, Any]:
    from local_harness.icm_call import call_worker
    from local_harness.icm_spec import resolve_worker_spec
    validate_local_configuration()
    spec = resolve_worker_spec("handoff", base_url=LOCAL_BASE_URL, model=LOCAL_MODEL, api="openai-chat")
    started = time.monotonic()
    response = call_worker(spec, message.decode("utf-8"), int(os.environ.get("ZTH_CAPABILITY_TEACHER_MAX_TOKENS", "1200")), timeout=int(os.environ.get("ZTH_CAPABILITY_TEACHER_TIMEOUT", "900")))
    elapsed = round((time.monotonic() - started) * 1000, 3)
    content = response.content.encode("utf-8")
    metadata = response.metadata()
    metadata.update({"transport_valid": response.status == "ok", "prohibited_actions_not_observed": True, "elapsed_ms": elapsed, "request_base_url": spec.base_url, "request_url_expected": LOCAL_BASE_URL.rstrip("/") + "/chat/completions"})
    return {"content_bytes": content, "metadata": metadata, "terminal_disposition": "RESPONSE_CAPTURED" if response.status == "ok" else "LOCAL_TRANSPORT_FAILURE", "status": response.status}


def capture_external(message: bytes) -> dict[str, Any]:
    command = os.environ.get("ZTH_EXTERNAL_TEACHER_COMMAND", str(EXTERNAL_WRAPPER))
    if shlex.split(command) != [str(EXTERNAL_WRAPPER)]:
        raise RuntimeError("external command is not the frozen wrapper")
    started = time.monotonic()
    try:
        result = subprocess.run(shlex.split(command), input=message, capture_output=True, cwd=EXTERNAL_CWD, env={**os.environ, "CODEX_HOME": str(CODEX_HOME)}, timeout=900, check=False)
        stdout, stderr, return_code = result.stdout, result.stderr, result.returncode
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        stdout, stderr, return_code, timed_out = exc.stdout or b"", exc.stderr or b"", None, True
    elapsed = round((time.monotonic() - started) * 1000, 3)
    protocol = observe_protocol(stdout, stderr)
    disposition = "EXTERNAL_TIMEOUT" if timed_out else "EXTERNAL_NONZERO_EXIT" if return_code != 0 else "RESPONSE_CAPTURED" if stdout else "EXTERNAL_TRANSPORT_FAILURE"
    return {"stdout_bytes": stdout, "stderr_bytes": stderr, "stdout_sha256": sha_bytes(stdout), "stderr_sha256": sha_bytes(stderr), "return_code": return_code, "timed_out": timed_out, "elapsed_ms": elapsed, "content_bytes": stdout, "terminal_disposition": disposition, "metadata": {"transport_valid": disposition == "RESPONSE_CAPTURED", "prohibited_actions_not_observed": protocol["prohibited_actions_not_observed"], "tool_calls_observed": protocol["tool_calls_observed"], "repository_access_observed": protocol["repository_access_observed"], "cwd": str(EXTERNAL_CWD), "cwd_outside_repository": True, "elapsed_ms": elapsed, "return_code": return_code}}


def _write_terminal_arm(arm_dir: Path, item: dict[str, Any], result: dict[str, Any], started: str, elapsed_ms: float) -> dict[str, Any]:
    if "stdout_bytes" in result:
        (arm_dir / "stdout.bin").write_bytes(result["stdout_bytes"])
        (arm_dir / "stderr.bin").write_bytes(result["stderr_bytes"])
    content = result.get("content_bytes", b"")
    disposition = result["terminal_disposition"]
    if disposition == "RESPONSE_CAPTURED":
        response = {"schema": "zth.explicit_interface_direct_unit_calibration_v3.raw_supplier_response", "ordinal": item["ordinal"], "case_id": item["case_id"], "supplier_id": item["supplier_id"], "supplier_message_sha256": item["supplier_message_sha256"], "raw_supplier_content": content.decode("utf-8", errors="replace"), "raw_supplier_content_sha256": sha_bytes(content), "metadata": result["metadata"], "captured_at": utc_now()}
        evidence_hash = atomic_write_json(arm_dir / "response.json", response)
    else:
        failure = {"schema": "zth.explicit_interface_direct_unit_calibration_v3.transport_failure", "ordinal": item["ordinal"], "case_id": item["case_id"], "supplier_id": item["supplier_id"], "terminal_disposition": disposition, "stdout_sha256": result.get("stdout_sha256"), "stderr_sha256": result.get("stderr_sha256"), "return_code": result.get("return_code"), "stdout_utf8_lossy_view": result.get("stdout_bytes", b"").decode("utf-8", errors="replace"), "stderr_utf8_lossy_view": result.get("stderr_bytes", b"").decode("utf-8", errors="replace"), "metadata": result.get("metadata", {}), "captured_at": utc_now()}
        evidence_hash = atomic_write_json(arm_dir / "infrastructure_failure.json", failure)
    terminal = {"schema": "zth.explicit_interface_direct_unit_calibration_v3.call_finished", "ordinal": item["ordinal"], "case_id": item["case_id"], "capability_family": item["capability_family"], "interface_id": item["interface_id"], "supplier_id": item["supplier_id"], "supplier_message_sha256": item["supplier_message_sha256"], "started_at": started, "finished_at": utc_now(), "elapsed_ms": elapsed_ms, "terminal_disposition": disposition, "evidence_artifact_sha256": evidence_hash, "retries": 0, "replays": 0}
    atomic_write_json(arm_dir / "call_finished.json", terminal)
    return terminal


def seal_raw(run_dir: Path, manifest: dict[str, Any], records: list[dict[str, Any]], status: str) -> bool:
    arm_hashes = []
    for record in records:
        arm_dir = run_dir / "cases" / record["case_id"] / record["supplier_id"]
        names = {path.name for path in arm_dir.glob("*") if path.is_file()}
        if not {"supplier_message.txt", "call_started.json", "call_finished.json"}.issubset(names):
            raise RuntimeError("terminal artifact coverage incomplete")
        if not ("response.json" in names or "infrastructure_failure.json" in names):
            raise RuntimeError("terminal evidence missing")
        arm_hashes.append({"ordinal": record["ordinal"], "case_id": record["case_id"], "supplier_id": record["supplier_id"], "artifact_hashes": {str(path.relative_to(run_dir)): sha_file(path) for path in sorted(arm_dir.glob("*")) if path.is_file()}})
    raw = {"schema": "zth.explicit_interface_direct_unit_calibration_v3.raw_acquisition_manifest", "status": "SEALED_BEFORE_EVALUATION" if status == "TERMINAL_COMPLETE" else "SEALED_INCOMPLETE", "raw_explicit_v3_responses_sealed_before_evaluation": False, "evaluator_file_access_during_acquisition": False, "evaluator_semantics_loaded_during_acquisition": False, "evaluator_runtime_influence": 0, "terminal_arm_artifacts": arm_hashes, "terminal_arm_artifact_count": len(arm_hashes), "records": records, "retries": 0, "replays": 0}
    atomic_write_json(run_dir / "raw_response_manifest.json", raw)
    atomic_write_json(run_dir / "lifecycle.json", {"status": status, "processes_started": 1, "supplier_calls": len(records), "terminal_arm_artifact_count": len(arm_hashes), "raw_seal_written": True})
    manifest.update({"status": status, "supplier_calls": len(records), "raw_explicit_v3_responses_sealed_before_evaluation": True})
    atomic_write_json(run_dir / "execution_manifest.json", manifest)
    raw["raw_explicit_v3_responses_sealed_before_evaluation"] = True
    atomic_write_json(run_dir / "raw_response_manifest.json", raw)
    return True


def execute(output_dir: Path, artifact_dir: Path = DOCS, guard_state: Path | None = None, capture_overrides: dict[str, Callable[[bytes], dict[str, Any]]] | None = None) -> int:
    projection = load_projection(artifact_dir)
    validate_schedule(projection["schedule"], projection["cases"])
    validate_matched_messages(projection)
    manifest = prepare_run(output_dir, artifact_dir)
    guard = guard_state or DEFAULT_GUARD
    try:
        claim_guard(guard)
    except RuntimeError as exc:
        manifest.update({"status": "REJECTED_BEFORE_ACQUISITION", "rejection": str(exc), "second_acquisition_process_started": False})
        atomic_write_json(output_dir / "execution_manifest.json", manifest)
        return 1
    manifest.update({"status": "RUNNING", "processes_started": 1})
    atomic_write_json(output_dir / "execution_manifest.json", manifest)
    records: list[dict[str, Any]] = []
    try:
        overrides = capture_overrides or {}
        by_key = validate_matched_messages(projection)
        for item in projection["schedule"]:
            arm_dir = output_dir / "cases" / item["case_id"] / item["supplier_id"]
            arm_dir.mkdir(parents=True, exist_ok=False)
            message = by_key[(item["case_id"], item["supplier_id"])]
            message_bytes = message["supplier_message_bytes"]
            if message_bytes != by_key[(item["case_id"], "local_teacher")]["supplier_message_bytes"] or message_bytes != by_key[(item["case_id"], "external_teacher")]["supplier_message_bytes"] or sha_bytes(message_bytes) != item["supplier_message_sha256"]:
                raise RuntimeError("live matched message validation failed")
            (arm_dir / "supplier_message.txt").write_bytes(message_bytes)
            started = utc_now(); mono = time.monotonic()
            atomic_write_json(arm_dir / "call_started.json", {"ordinal": item["ordinal"], "case_id": item["case_id"], "supplier_id": item["supplier_id"], "supplier_message_sha256": item["supplier_message_sha256"], "started_at": started})
            try:
                if item["supplier_id"] in overrides:
                    result = overrides[item["supplier_id"]](message_bytes)
                elif item["supplier_id"] == "local_teacher":
                    result = capture_local(message_bytes)
                else:
                    result = capture_external(message_bytes)
            except Exception as exc:
                result = {"content_bytes": b"", "terminal_disposition": "LOCAL_TRANSPORT_FAILURE" if item["supplier_id"] == "local_teacher" else "EXTERNAL_TRANSPORT_FAILURE", "metadata": {"error": str(exc), "transport_valid": False, "prohibited_actions_not_observed": False}}
            records.append(_write_terminal_arm(arm_dir, item, result, started, round((time.monotonic() - mono) * 1000, 3)))
        seal_raw(output_dir, manifest, records, "TERMINAL_COMPLETE")
        return 0
    except BaseException as exc:
        atomic_write_json(output_dir / "acquisition_failure.json", {"status": "TERMINAL_INCOMPLETE", "error_type": type(exc).__name__, "error": str(exc), "captured_at": utc_now(), "supplier_calls_completed": len(records)})
        try:
            seal_raw(output_dir, manifest, records, "TERMINAL_INCOMPLETE")
        except BaseException as seal_exc:
            manifest.update({"status": "TERMINAL_INCOMPLETE", "supplier_calls": len(records), "raw_explicit_v3_responses_sealed_before_evaluation": False, "raw_seal_failure": str(seal_exc)})
            atomic_write_json(output_dir / "execution_manifest.json", manifest)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--guard-state", type=Path)
    args = parser.parse_args()
    if args.preflight:
        print(json.dumps(preflight(), sort_keys=True))
        return 0
    if args.prepare_only and args.output_dir:
        manifest = prepare_run(args.output_dir)
        print(json.dumps({"status": "prepare_only_pass", "planned_supplier_calls": manifest["planned_supplier_calls"], "supplier_calls": 0}, sort_keys=True))
        return 0
    if args.execute and args.output_dir:
        return execute(args.output_dir, guard_state=args.guard_state)
    parser.error("use --preflight or --prepare-only/--execute with --output-dir")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
