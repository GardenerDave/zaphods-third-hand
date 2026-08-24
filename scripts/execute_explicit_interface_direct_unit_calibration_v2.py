#!/usr/bin/env python3
"""Fail-closed, one-shot acquisition harness for explicit-interface V2.

This module is deliberately acquisition-only.  It imports the frozen
evaluator-free projection and never opens the scoring evaluator during
prepare or acquisition.  Supplier execution requires an explicit
``--execute`` flag and is not used by the model-free tests in this repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.project_explicit_interface_direct_unit_calibration_v2_inputs import load_acquisition_inputs


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_V2_FREEZE_COMMIT = "a00d8a72e3c547ea401b8ab0075a4260c85eb82a"
V2_FREEZE_NAME = "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_FREEZE_V2_2026-08-24.json"
V2_INTERFACE_NAME = "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_INTERFACE_V2_2026-08-24.json"
V2_RUNTIME_NAME = "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_RUNTIME_MANIFEST_V2_2026-08-24.json"
V2_PAYLOAD_NAME = "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_PAYLOAD_MANIFEST_V2_2026-08-24.json"
V2_EVALUATOR_NAME = "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_EVALUATOR_CASES_V2_2026-08-24.json"
V2_EVALUATOR_IMPL = ROOT / "scripts/evaluate_explicit_interface_direct_unit_calibration_v2.py"
V2_PROJECTION_IMPL = ROOT / "scripts/project_explicit_interface_direct_unit_calibration_v2_inputs.py"
HARNESS_FREEZE_NAME = "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_V2_EXECUTION_HARNESS_FREEZE_2026-08-24.json"
EXTERNAL_CWD = Path("/tmp")
EXTERNAL_WRAPPER = Path("/home/navigator/bin/zth-codex-teacher")
EXTERNAL_COMMAND_DEFAULT = str(EXTERNAL_WRAPPER)
LOCAL_MODEL = "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf"
LOCAL_SERVICE_ALIAS = "JARVIS_LOCAL"
LOCAL_WORKER_DEFAULT = "handoff"
FROZEN_LOCAL_BASE_URL = "http://192.168.1.13:8083/v1"
EXTERNAL_SERVICE_IDENTITY = "codex-cli-0.146.0 via preserved service mechanism"
EXPECTED_CODEX_CLI_VERSION = "codex-cli 0.146.0"
LOCAL_SERVICE_IDENTITY = f"{LOCAL_MODEL} via {LOCAL_SERVICE_ALIAS}"
DEFAULT_GUARD_STATE = ROOT / ".work" / "explicit_interface_direct_unit_calibration_v2" / "ACQUISITION_GUARD.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def write_json(path: Path, value: Any) -> str:
    data = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return sha_bytes(data)


def atomic_write_json(path: Path, value: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write((json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    temporary.replace(path)
    return sha_file(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def current_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def freeze_paths(artifact_dir: Path) -> tuple[Path, Path, Path, Path]:
    return (artifact_dir / V2_FREEZE_NAME, artifact_dir / V2_RUNTIME_NAME, artifact_dir / V2_PAYLOAD_NAME, artifact_dir / HARNESS_FREEZE_NAME)


def verify_v2_acquisition_artifacts(artifact_dir: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Verify acquisition artifacts without opening evaluator-case bytes."""
    freeze_path, runtime_path, payload_path, harness_freeze_path = freeze_paths(artifact_dir)
    freeze = read_json(freeze_path)
    runtime = read_json(runtime_path)
    payload = read_json(payload_path)
    harness_freeze = read_json(harness_freeze_path)
    if subprocess.run(["git", "merge-base", "--is-ancestor", EXPECTED_V2_FREEZE_COMMIT, "HEAD"], cwd=ROOT, check=False).returncode != 0:
        raise RuntimeError(f"V2 freeze is not an ancestor of HEAD {current_head()}")
    expected = freeze["artifact_hashes"]
    if sha_file(runtime_path) != expected["runtime_manifest"]:
        raise RuntimeError("V2 runtime manifest hash mismatch")
    if sha_file(payload_path) != expected["payload_manifest"]:
        raise RuntimeError("V2 payload manifest hash mismatch")
    if sha_file(V2_PROJECTION_IMPL) != expected["acquisition_input_projection"]:
        raise RuntimeError("acquisition input projection implementation hash mismatch")
    if harness_freeze["v2_freeze_commit"] != EXPECTED_V2_FREEZE_COMMIT:
        raise RuntimeError("execution harness is bound to the wrong V2 freeze")
    if harness_freeze["harness_sha256"] != sha_file(Path(__file__)):
        raise RuntimeError("execution harness implementation hash mismatch")
    if harness_freeze["acquisition_input_projection_sha256"] != sha_file(V2_PROJECTION_IMPL):
        raise RuntimeError("harness freeze projection hash mismatch")
    expected_wrapper_sha = harness_freeze.get("external_mechanism_enforcement", {}).get("wrapper_sha256")
    if not expected_wrapper_sha or sha_file(EXTERNAL_WRAPPER) != expected_wrapper_sha:
        raise RuntimeError("preserved external wrapper hash mismatch")
    if harness_freeze["schedule_sha256"] != sha_bytes(_canonical(harness_freeze["schedule"])):
        raise RuntimeError("expanded schedule hash mismatch")
    if runtime["case_order"] != harness_freeze["case_order"]:
        raise RuntimeError("schedule case order mismatch")
    if len(runtime["cases"]) != 16 or len(harness_freeze["schedule"]) != 32:
        raise RuntimeError("V2 case or schedule count mismatch")
    if harness_freeze["planned_local_calls"] != 16 or harness_freeze["planned_external_calls"] != 16:
        raise RuntimeError("supplier call budget mismatch")
    return freeze, runtime, payload, harness_freeze


def build_schedule(runtime: dict[str, Any], inputs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_case: dict[str, list[dict[str, Any]]] = {}
    for item in inputs:
        by_case.setdefault(item["case_id"], []).append(item)
    schedule: list[dict[str, Any]] = []
    ordinal = 1
    family_positions: dict[str, int] = {}
    for case in runtime["cases"]:
        family = case["capability_family"]
        position = family_positions.get(family, 0)
        family_positions[family] = position + 1
        first = "local_teacher" if position % 2 == 0 else "external_teacher"
        arms = [first, "external_teacher" if first == "local_teacher" else "local_teacher"]
        projected = {item["supplier_id"]: item for item in by_case.get(case["case_id"], [])}
        for supplier_id in arms:
            source = projected[supplier_id]
            schedule.append({
                "ordinal": ordinal,
                "case_id": case["case_id"],
                "capability_family": family,
                "interface_id": case["interface_id"],
                "supplier_id": supplier_id,
                "supplier_message_sha256": source["supplier_message_sha256"],
                "first_arm_supplier_id": first,
            })
            ordinal += 1
    return schedule


def validate_schedule(schedule: list[dict[str, Any]], runtime: dict[str, Any]) -> None:
    if [item["ordinal"] for item in schedule] != list(range(1, 33)):
        raise RuntimeError("schedule ordinals are not contiguous")
    if len({item["case_id"] for item in schedule}) != 16:
        raise RuntimeError("schedule does not cover 16 cases")
    if sum(item["supplier_id"] == "local_teacher" for item in schedule) != 16:
        raise RuntimeError("schedule local count mismatch")
    if sum(item["supplier_id"] == "external_teacher" for item in schedule) != 16:
        raise RuntimeError("schedule external count mismatch")
    for family in ("triage-routing", "unsupported-certainty"):
        family_cases = [case["case_id"] for case in runtime["cases"] if case["capability_family"] == family]
        firsts = [next(item["first_arm_supplier_id"] for item in schedule if item["case_id"] == case_id) for case_id in family_cases]
        if firsts.count("local_teacher") != 4 or firsts.count("external_teacher") != 4:
            raise RuntimeError(f"{family} first-arm balance mismatch")
        for case_id in family_cases:
            arms = [item["supplier_id"] for item in schedule if item["case_id"] == case_id]
            if sorted(arms) != ["external_teacher", "local_teacher"]:
                raise RuntimeError(f"matched arms missing for {case_id}")


def validate_matched_projected_messages(inputs: list[dict[str, Any]], schedule: list[dict[str, Any]], runtime: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    """Validate both projected arms independently, then compare exact bytes."""
    by_key = {(item["case_id"], item["supplier_id"]): item for item in inputs}
    if len(by_key) != 32 or len(inputs) != 32:
        raise RuntimeError("projection does not contain 32 distinct case-arm rows")
    schedule_by_key = {(item["case_id"], item["supplier_id"]): item for item in schedule}
    if set(schedule_by_key) != set(by_key):
        raise RuntimeError("schedule/projection arm keys differ")
    for case_id in runtime["case_order"]:
        local = by_key[(case_id, "local_teacher")]
        external = by_key[(case_id, "external_teacher")]
        local_bytes = local["supplier_message_text"].encode("utf-8")
        external_bytes = external["supplier_message_text"].encode("utf-8")
        frozen_hash = schedule_by_key[(case_id, "local_teacher")]["supplier_message_sha256"]
        if frozen_hash != schedule_by_key[(case_id, "external_teacher")]["supplier_message_sha256"]:
            raise RuntimeError(f"schedule arm hash mismatch: {case_id}")
        if local_bytes != external_bytes:
            raise RuntimeError(f"matched supplier message bytes differ: {case_id}")
        if sha_bytes(local_bytes) != frozen_hash or sha_bytes(external_bytes) != frozen_hash:
            raise RuntimeError(f"matched supplier message hash mismatch: {case_id}")
        if local["supplier_message_sha256"] != external["supplier_message_sha256"]:
            raise RuntimeError(f"projected arm hashes differ: {case_id}")
    return by_key


def validate_local_identity() -> dict[str, Any]:
    """Resolve local configuration without making a completion or health call."""
    from local_harness.icm_spec import resolve_worker_spec

    worker_name = os.environ.get("ZTH_CAPABILITY_TEACHER_NAME", LOCAL_WORKER_DEFAULT)
    if worker_name != LOCAL_WORKER_DEFAULT:
        raise RuntimeError(f"local worker alias mismatch: {worker_name}")
    alias = os.environ.get("ZTH_PUBLIC_HOST_ALIAS", LOCAL_SERVICE_ALIAS)
    if alias != LOCAL_SERVICE_ALIAS:
        raise RuntimeError(f"local service alias mismatch: {alias}")
    explicit_model = os.environ.get("ZTH_CAPABILITY_TEACHER_MODEL")
    env_model = os.environ.get("ICM_HANDOFF_MODEL")
    for value, label in ((explicit_model, "ZTH_CAPABILITY_TEACHER_MODEL"), (env_model, "ICM_HANDOFF_MODEL")):
        if value is not None and value != LOCAL_MODEL:
            raise RuntimeError(f"local model override mismatch in {label}: {value}")
    api_override = os.environ.get("ICM_HANDOFF_API")
    if api_override is not None and api_override != "openai-chat":
        raise RuntimeError(f"local API override mismatch: {api_override}")
    explicit_base_url = os.environ.get("ZTH_CAPABILITY_TEACHER_BASE_URL")
    inherited_base_url = os.environ.get("ICM_HANDOFF_BASE_URL")
    for value, label in ((explicit_base_url, "ZTH_CAPABILITY_TEACHER_BASE_URL"), (inherited_base_url, "ICM_HANDOFF_BASE_URL")):
        if value is not None and value.rstrip("/") != FROZEN_LOCAL_BASE_URL:
            raise RuntimeError(f"local endpoint override mismatch in {label}: {value}")
    resolved_base_url = (explicit_base_url or inherited_base_url or FROZEN_LOCAL_BASE_URL).rstrip("/")
    spec = resolve_worker_spec(worker_name, base_url=resolved_base_url, model=LOCAL_MODEL)
    if spec.model != LOCAL_MODEL:
        raise RuntimeError(f"resolved local model mismatch: {spec.model}")
    if spec.base_url != FROZEN_LOCAL_BASE_URL:
        raise RuntimeError(f"resolved local endpoint mismatch: {spec.base_url}")
    return {
        "frozen_identity": LOCAL_SERVICE_IDENTITY,
        "worker_name": worker_name,
        "resolved_model": spec.model,
        "resolved_api": spec.api,
        "resolved_base_url": spec.base_url,
        "frozen_base_url": FROZEN_LOCAL_BASE_URL,
        "endpoint_alias": alias,
        "identity_check": "configuration_only_no_inference",
    }


def validate_external_mechanism(command: str | None = None, expected_wrapper_sha256: str | None = None) -> dict[str, Any]:
    """Validate the exact preserved wrapper and CLI version without invoking a model."""
    configured = command if command is not None else os.environ.get("ZTH_EXTERNAL_TEACHER_COMMAND", EXTERNAL_COMMAND_DEFAULT)
    argv = shlex.split(configured)
    if argv != [EXTERNAL_COMMAND_DEFAULT]:
        raise RuntimeError("external command is not the preserved zth-codex-teacher wrapper")
    if not EXTERNAL_WRAPPER.is_file() or not os.access(EXTERNAL_WRAPPER, os.X_OK):
        raise RuntimeError("preserved external wrapper is missing or not executable")
    wrapper_sha256 = sha_file(EXTERNAL_WRAPPER)
    if expected_wrapper_sha256 is not None and wrapper_sha256 != expected_wrapper_sha256:
        raise RuntimeError("preserved external wrapper SHA256 differs from frozen value")
    wrapper_text = EXTERNAL_WRAPPER.read_text(encoding="utf-8")
    required = ("codex exec", "--ephemeral", "--sandbox read-only", "--skip-git-repo-check", "--output-last-message")
    missing = [term for term in required if term not in wrapper_text]
    if missing:
        raise RuntimeError(f"preserved external wrapper lacks controls: {missing}")
    codex_path = shutil.which("codex")
    if codex_path is None:
        raise RuntimeError("codex executable is not available on PATH")
    version_probe = subprocess.run([codex_path, "--version"], capture_output=True, text=True, timeout=10, check=False)
    observed_version = (version_probe.stdout + version_probe.stderr).strip()
    if version_probe.returncode != 0 or EXPECTED_CODEX_CLI_VERSION not in observed_version:
        raise RuntimeError(f"Codex CLI version mismatch: {observed_version}")
    return {
        "configured_command": configured,
        "wrapper_path": str(EXTERNAL_WRAPPER),
        "wrapper_sha256": wrapper_sha256,
        "expected_wrapper_sha256": expected_wrapper_sha256 or wrapper_sha256,
        "observed_codex_executable_path": str(Path(codex_path).resolve()),
        "observed_codex_version": observed_version,
        "expected_codex_cli_version": EXPECTED_CODEX_CLI_VERSION,
        "service_identity": EXTERNAL_SERVICE_IDENTITY,
        "cwd": str(EXTERNAL_CWD),
        "cwd_outside_repository": True,
        "read_only_sandbox_enforced_by_wrapper": True,
        "skip_git_repo_check_enforced_by_wrapper": True,
        "tools_not_mechanically_disabled": True,
        "tool_calls_observed": "BEST_AVAILABLE_OBSERVATION",
        "repository_access_observed": "BEST_AVAILABLE_OBSERVATION",
        "identity_check": "configuration_only_no_inference",
    }


def prepare_inputs(artifact_dir: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    freeze, runtime, payload, harness_freeze = verify_v2_acquisition_artifacts(artifact_dir)
    inputs = load_acquisition_inputs(*freeze_paths(artifact_dir)[:3])
    schedule = harness_freeze["schedule"]
    validate_schedule(schedule, runtime)
    by_key = validate_matched_projected_messages(inputs, schedule, runtime)
    return freeze, runtime, payload, harness_freeze, inputs, by_key


def prepare_run(output_dir: Path, artifact_dir: Path) -> dict[str, Any]:
    if output_dir.exists():
        raise RuntimeError("run directory already exists; refusing resume/replay")
    freeze, runtime, payload, harness_freeze, inputs, _ = prepare_inputs(artifact_dir)
    schedule = harness_freeze["schedule"]
    output_dir.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema": "zth.explicit_interface_direct_unit_calibration_v2.execution_manifest",
        "status": "PREPARED",
        "freeze_commit": EXPECTED_V2_FREEZE_COMMIT,
        "harness_freeze_sha256": sha_file(artifact_dir / HARNESS_FREEZE_NAME),
        "planned_supplier_calls": 32,
        "planned_local_calls": 16,
        "planned_external_calls": 16,
        "schedule_sha256": harness_freeze["schedule_sha256"],
        "schedule": schedule,
        "supplier_message_hashes": {item["case_id"]: item["supplier_message_sha256"] for item in inputs if item["supplier_id"] == "local_teacher"},
        "matched_runtime_message_hash_across_arms": True,
        "matched_runtime_message_bytes_across_arms": True,
        "supplier_message_runtime_reconstruction": False,
        "evaluator_file_access_during_acquisition": False,
        "evaluator_semantics_loaded_during_acquisition": False,
        "evaluator_runtime_influence": 0,
        "evaluator_supplier_visibility": False,
        "processes_started": 0,
        "second_acquisition_process_started": False,
        "retries": 0,
        "replays": 0,
        "evaluator_loaded_during_acquisition": False,
        "raw_explicit_v2_responses_sealed_before_evaluation": False,
    }
    atomic_write_json(output_dir / "execution_manifest.json", manifest)
    return manifest


def observe_protocol(stdout: bytes, stderr: bytes) -> dict[str, Any]:
    combined = (stdout + b"\n" + stderr).decode("utf-8", errors="replace").casefold()
    tool_markers = ("tool call", "tool_calls", "function_call", "function call", "shell command", "exec_command")
    repo_markers = ("git status", "git diff", ".git/", "repository access", "working tree", "apply_patch")
    return {
        "tool_calls_observed": any(marker in combined for marker in tool_markers),
        "repository_access_observed": any(marker in combined for marker in repo_markers),
        "evaluator_access_observed": "evaluator" in combined,
        "observation_basis": "marker_scan_best_available_observation",
    }


def capture_local(message_bytes: bytes) -> tuple[bytes, dict[str, Any]]:
    from local_harness.icm_call import call_worker
    from local_harness.icm_spec import resolve_worker_spec

    identity = validate_local_identity()
    message = message_bytes.decode("utf-8")
    spec = resolve_worker_spec(identity["worker_name"], base_url=os.environ.get("ZTH_CAPABILITY_TEACHER_BASE_URL"), model=LOCAL_MODEL)
    started = time.monotonic()
    response = call_worker(spec, message, int(os.environ.get("ZTH_CAPABILITY_TEACHER_MAX_TOKENS", "1200")), timeout=int(os.environ.get("ZTH_CAPABILITY_TEACHER_TIMEOUT", "900")))
    elapsed = round((time.monotonic() - started) * 1000.0, 3)
    content_bytes = response.content.encode("utf-8")
    metadata = response.metadata()
    metadata.update({
        "service_identity": LOCAL_SERVICE_IDENTITY,
        "resolved_runtime_identity": identity,
        "tool_calls_observed": False,
        "repository_access_observed": False,
        "evaluator_access_observed": False,
        "observation_basis": "direct_http_endpoint_no_supplier_tools",
        "native_envelope_control": "BEST_AVAILABLE_OBSERVATION",
        "elapsed_ms": elapsed,
        "transport_classification": "model_response" if content_bytes.strip() else "empty_model_response",
    })
    return content_bytes, metadata


def run_external_command(command: str, message_bytes: bytes, timeout: int = 120, validate: bool = True) -> dict[str, Any]:
    if validate:
        enforcement = validate_external_mechanism(command)
    else:
        enforcement = {"validation": "test_only_bypassed"}
    started = time.monotonic()
    started_at = utc_now()
    try:
        completed = subprocess.run(shlex.split(command), input=message_bytes, capture_output=True, cwd=EXTERNAL_CWD, timeout=timeout, check=False)
        timed_out = False
        return_code: int | None = completed.returncode
        stdout_bytes = completed.stdout
        stderr_bytes = completed.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        return_code = None
        stdout_bytes = exc.stdout or b""
        stderr_bytes = exc.stderr or b""
    elapsed = round((time.monotonic() - started) * 1000.0, 3)
    observed = observe_protocol(stdout_bytes, stderr_bytes)
    if timed_out:
        disposition = "EXTERNAL_TIMEOUT"
        status = "external_timeout"
    elif return_code != 0:
        disposition = "EXTERNAL_NONZERO_EXIT"
        status = "external_nonzero_exit"
    else:
        disposition = "RESPONSE_CAPTURED" if stdout_bytes else "EMPTY_RESPONSE"
        status = "ok" if stdout_bytes else "empty_content"
    return {
        "stdout_bytes": stdout_bytes,
        "stderr_bytes": stderr_bytes,
        "stdout_sha256": sha_bytes(stdout_bytes),
        "stderr_sha256": sha_bytes(stderr_bytes),
        "return_code": return_code,
        "started_at": started_at,
        "elapsed_ms": elapsed,
        "timed_out": timed_out,
        "terminal_disposition": disposition,
        "status": status,
        "content_bytes": stdout_bytes,
        "metadata": {
            "service_identity": EXTERNAL_SERVICE_IDENTITY,
            "observed_native_identity": os.environ.get("ZTH_EXTERNAL_TEACHER_NATIVE_IDENTITY", "BEST_AVAILABLE_OBSERVATION"),
            "cwd": str(EXTERNAL_CWD),
            "cwd_outside_repository": True,
            "native_envelope_control": "BEST_AVAILABLE_OBSERVATION",
            "transport_classification": "model_response" if disposition == "RESPONSE_CAPTURED" else "transport_or_empty_failure",
            "return_code": return_code,
            "elapsed_ms": elapsed,
            **observed,
            "enforcement": enforcement,
        },
    }


def capture_external(message_bytes: bytes) -> dict[str, Any]:
    command = os.environ.get("ZTH_EXTERNAL_TEACHER_COMMAND", EXTERNAL_COMMAND_DEFAULT)
    return run_external_command(command, message_bytes)


def claim_one_shot_guard(path: Path, harness_sha256: str, freeze_commit: str) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    value = {
        "schema": "zth.explicit_interface_direct_unit_calibration_v2.one_shot_guard",
        "status": "ACQUISITION_CLAIMED",
        "claimed_at": utc_now(),
        "freeze_commit": freeze_commit,
        "harness_sha256": harness_sha256,
        "processes_started": 1,
        "second_acquisition_process_started": False,
    }
    data = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError as exc:
        raise RuntimeError("one-shot acquisition guard already claimed; refusing second execution") from exc
    try:
        os.write(fd, data)
    finally:
        os.close(fd)
    return value


def _write_raw_and_lifecycle(output_dir: Path, manifest: dict[str, Any], records: list[dict[str, Any]], status: str) -> None:
    terminal_artifacts = []
    for record in records:
        arm_dir = output_dir / "cases" / record["case_id"] / record["supplier_id"]
        files = {}
        for path in sorted(arm_dir.rglob("*")):
            if path.is_file():
                files[str(path.relative_to(output_dir))] = sha_file(path)
        required = {"supplier_message.txt", "call_started.json", "call_finished.json"}
        if not required.issubset({Path(name).name for name in files}):
            raise RuntimeError(f"terminal arm artifact coverage incomplete: {record['case_id']} {record['supplier_id']}")
        if not any(name.endswith("response.json") or name.endswith("infrastructure_failure.json") for name in files):
            raise RuntimeError(f"terminal arm lacks response/failure evidence: {record['case_id']} {record['supplier_id']}")
        terminal_artifacts.append({"ordinal": record["ordinal"], "case_id": record["case_id"], "supplier_id": record["supplier_id"], "artifact_hashes": files})
    actual_local_calls = sum(item["supplier_id"] == "local_teacher" for item in records)
    actual_external_calls = sum(item["supplier_id"] == "external_teacher" for item in records)
    raw_manifest = {
        "schema": "zth.explicit_interface_v2.raw_acquisition_manifest",
        "status": "SEALED_BEFORE_EVALUATION",
        "raw_explicit_v2_responses_sealed_before_evaluation": True,
        "evaluator_file_access_during_acquisition": False,
        "evaluator_semantics_loaded_during_acquisition": False,
        "evaluator_runtime_influence": 0,
        "evaluator_supplier_visibility": False,
        "planned_supplier_calls": 32,
        "actual_supplier_calls": len(records),
        "actual_local_calls": actual_local_calls,
        "actual_external_calls": actual_external_calls,
        "retries": 0,
        "replays": 0,
        "terminal_arm_artifact_hashes": terminal_artifacts,
        "terminal_arm_artifact_count": len(terminal_artifacts),
        "records": records,
    }
    atomic_write_json(output_dir / "raw_response_manifest.json", raw_manifest)
    atomic_write_json(output_dir / "lifecycle.json", {
        "status": status,
        "processes_started": 1,
        "second_acquisition_process_started": False,
        "supplier_calls": len(records),
        "model_calls": len(records),
        "external_inference_calls": actual_external_calls,
        "retries": 0,
        "replays": 0,
        "evaluator_file_access_during_acquisition": False,
        "evaluator_semantics_loaded_during_acquisition": False,
        "evaluator_runtime_influence": 0,
    })
    # This is the final seal bit.  It is written only after all per-arm hashes,
    # the raw manifest, and lifecycle metadata have been written successfully.
    manifest["status"] = status
    manifest["actual_supplier_calls"] = len(records)
    manifest["actual_local_calls"] = actual_local_calls
    manifest["actual_external_calls"] = actual_external_calls
    manifest["raw_explicit_v2_responses_sealed_before_evaluation"] = True
    atomic_write_json(output_dir / "execution_manifest.json", manifest)


def execute(output_dir: Path, artifact_dir: Path, guard_state: Path | None = None, capture_overrides: dict[str, Callable[[bytes], Any]] | None = None, inject_exception_after: int | None = None) -> int:
    """Execute exactly one schedule, with outer fail-closed terminalization."""
    local_identity = validate_local_identity()
    _, runtime, _, harness_freeze, _, _ = prepare_inputs(artifact_dir)
    validate_schedule(harness_freeze["schedule"], runtime)
    external_identity = validate_external_mechanism(harness_freeze["external_mechanism_enforcement"]["configured_command"], harness_freeze["external_mechanism_enforcement"]["wrapper_sha256"])
    if output_dir.exists():
        raise RuntimeError("run directory already exists; refusing resume/replay")
    manifest = prepare_run(output_dir, artifact_dir)
    guard = guard_state or DEFAULT_GUARD_STATE
    try:
        claim_one_shot_guard(guard, sha_file(Path(__file__)), EXPECTED_V2_FREEZE_COMMIT)
    except RuntimeError as exc:
        manifest["status"] = "REJECTED_BEFORE_ACQUISITION"
        manifest["rejection"] = str(exc)
        manifest["processes_started"] = 0
        manifest["second_acquisition_process_started"] = False
        manifest["raw_explicit_v2_responses_sealed_before_evaluation"] = False
        atomic_write_json(output_dir / "execution_manifest.json", manifest)
        return 1
    # The guard is claimed after PREPARED and before RUNNING, so a second
    # execute attempt cannot claim a second acquisition process or create
    # supplier-opportunity evidence.
    manifest["resolved_local_identity"] = local_identity
    manifest["resolved_external_identity"] = external_identity
    manifest["status"] = "RUNNING"
    manifest["processes_started"] = 1
    atomic_write_json(output_dir / "execution_manifest.json", manifest)
    try:
        _, runtime, _, harness_freeze, inputs, input_by_key = prepare_inputs(artifact_dir)
        validate_schedule(harness_freeze["schedule"], runtime)
        call_records: list[dict[str, Any]] = []
        overrides = capture_overrides or {}
        for schedule_item in harness_freeze["schedule"]:
            if inject_exception_after is not None and len(call_records) >= inject_exception_after:
                raise RuntimeError("injected harness-level exception for fail-closed regression")
            key = (schedule_item["case_id"], schedule_item["supplier_id"])
            source = input_by_key[key]
            arm_dir = output_dir / "cases" / schedule_item["case_id"] / schedule_item["supplier_id"]
            arm_dir.mkdir(parents=True, exist_ok=False)
            message_bytes = source["supplier_message_text"].encode("utf-8")
            if message_bytes != input_by_key[(schedule_item["case_id"], "local_teacher")]["supplier_message_text"].encode("utf-8") or message_bytes != input_by_key[(schedule_item["case_id"], "external_teacher")]["supplier_message_text"].encode("utf-8"):
                raise RuntimeError("live matched supplier message bytes mismatch")
            if sha_bytes(message_bytes) != schedule_item["supplier_message_sha256"]:
                raise RuntimeError("transmitted supplier message hash mismatch")
            (arm_dir / "supplier_message.txt").write_bytes(message_bytes)
            start = utc_now(); started_mono = time.monotonic()
            atomic_write_json(arm_dir / "call_started.json", {
                "schema": "zth.explicit_interface_v2.call_started",
                "ordinal": schedule_item["ordinal"], "case_id": schedule_item["case_id"],
                "capability_family": schedule_item["capability_family"], "interface_id": schedule_item["interface_id"],
                "supplier_id": schedule_item["supplier_id"], "supplier_message_sha256": schedule_item["supplier_message_sha256"],
                "started_at": start, "evaluator_file_access_during_acquisition": False,
                "evaluator_semantics_loaded_during_acquisition": False, "evaluator_runtime_influence": 0,
                "evaluator_supplier_visibility": False,
            })
            try:
                if schedule_item["supplier_id"] in overrides:
                    captured = overrides[schedule_item["supplier_id"]](message_bytes)
                elif schedule_item["supplier_id"] == "local_teacher":
                    content_bytes, metadata = capture_local(message_bytes)
                    captured = {"content_bytes": content_bytes, "metadata": metadata}
                else:
                    captured = capture_external(message_bytes)
                if "stdout_bytes" in captured:
                    (arm_dir / "stdout.bin").write_bytes(captured["stdout_bytes"])
                    (arm_dir / "stderr.bin").write_bytes(captured["stderr_bytes"])
                    metadata = dict(captured["metadata"])
                    metadata.update({"stdout_sha256": captured["stdout_sha256"], "stderr_sha256": captured["stderr_sha256"], "return_code": captured["return_code"], "terminal_disposition": captured["terminal_disposition"], "timed_out": captured["timed_out"]})
                    content_bytes = captured["content_bytes"]
                    if captured["terminal_disposition"] != "RESPONSE_CAPTURED":
                        failure = {"schema": "zth.explicit_interface_v2.external_terminal_evidence", "ordinal": schedule_item["ordinal"], "case_id": schedule_item["case_id"], "supplier_id": schedule_item["supplier_id"], "raw_stdout_sha256": captured["stdout_sha256"], "raw_stderr_sha256": captured["stderr_sha256"], "raw_stdout_file": "stdout.bin", "raw_stderr_file": "stderr.bin", "stdout_utf8_lossy_view": captured["stdout_bytes"].decode("utf-8", errors="replace"), "stderr_utf8_lossy_view": captured["stderr_bytes"].decode("utf-8", errors="replace"), "metadata": metadata, "captured_at": utc_now()}
                        failure_hash = atomic_write_json(arm_dir / "infrastructure_failure.json", failure)
                        terminal = {"terminal_disposition": captured["terminal_disposition"], "failure_artifact_sha256": failure_hash}
                    else:
                        response = {"schema": "zth.explicit_interface_v2.raw_supplier_response", "ordinal": schedule_item["ordinal"], "case_id": schedule_item["case_id"], "capability_family": schedule_item["capability_family"], "interface_id": schedule_item["interface_id"], "supplier_id": schedule_item["supplier_id"], "supplier_message_sha256": schedule_item["supplier_message_sha256"], "raw_supplier_content": content_bytes.decode("utf-8", errors="replace"), "raw_supplier_content_sha256": sha_bytes(content_bytes), "metadata": metadata, "captured_at": utc_now()}
                        response_hash = atomic_write_json(arm_dir / "response.json", response)
                        terminal = {"terminal_disposition": "RESPONSE_CAPTURED", "response_artifact_sha256": response_hash, "raw_supplier_content_sha256": response["raw_supplier_content_sha256"]}
                else:
                    content_bytes = captured["content_bytes"]
                    response = {"schema": "zth.explicit_interface_v2.raw_supplier_response", "ordinal": schedule_item["ordinal"], "case_id": schedule_item["case_id"], "capability_family": schedule_item["capability_family"], "interface_id": schedule_item["interface_id"], "supplier_id": schedule_item["supplier_id"], "supplier_message_sha256": schedule_item["supplier_message_sha256"], "raw_supplier_content": content_bytes.decode("utf-8", errors="replace"), "raw_supplier_content_sha256": sha_bytes(content_bytes), "metadata": captured["metadata"], "captured_at": utc_now()}
                    response_hash = atomic_write_json(arm_dir / "response.json", response)
                    terminal = {"terminal_disposition": "RESPONSE_CAPTURED", "response_artifact_sha256": response_hash, "raw_supplier_content_sha256": response["raw_supplier_content_sha256"]}
            except Exception as exc:
                failure = {"schema": "zth.explicit_interface_v2.infrastructure_failure", "ordinal": schedule_item["ordinal"], "case_id": schedule_item["case_id"], "supplier_id": schedule_item["supplier_id"], "error": str(exc), "captured_at": utc_now()}
                failure_hash = atomic_write_json(arm_dir / "infrastructure_failure.json", failure)
                terminal = {"terminal_disposition": "INFRASTRUCTURE_FAILURE", "failure_artifact_sha256": failure_hash}
            finished = utc_now()
            terminal.update({"ordinal": schedule_item["ordinal"], "case_id": schedule_item["case_id"], "capability_family": schedule_item["capability_family"], "interface_id": schedule_item["interface_id"], "supplier_id": schedule_item["supplier_id"], "supplier_message_sha256": schedule_item["supplier_message_sha256"], "frozen_supplier_identity": LOCAL_SERVICE_IDENTITY if schedule_item["supplier_id"] == "local_teacher" else EXTERNAL_SERVICE_IDENTITY, "started_at": start, "finished_at": finished, "elapsed_ms": round((time.monotonic() - started_mono) * 1000.0, 3), "retries": 0, "replays": 0})
            atomic_write_json(arm_dir / "call_finished.json", terminal)
            call_records.append(terminal)
        _write_raw_and_lifecycle(output_dir, manifest, call_records, "TERMINAL_COMPLETE")
        return 0
    except BaseException as exc:
        failure = {"schema": "zth.explicit_interface_v2.acquisition_failure", "status": "TERMINAL_INCOMPLETE", "error_type": type(exc).__name__, "error": str(exc), "captured_at": utc_now(), "supplier_calls_completed": len(list(output_dir.glob("cases/*/*/call_finished.json")))}
        atomic_write_json(output_dir / "acquisition_failure.json", failure)
        records = []
        for path in sorted(output_dir.glob("cases/*/*/call_finished.json")):
            records.append(read_json(path))
        try:
            _write_raw_and_lifecycle(output_dir, manifest, records, "TERMINAL_INCOMPLETE")
        except BaseException as seal_exc:
            # A failed seal must never be represented as a successful raw
            # seal.  Preserve the failure and leave the marker false.
            manifest["status"] = "TERMINAL_INCOMPLETE"
            manifest["actual_supplier_calls"] = len(records)
            manifest["actual_local_calls"] = sum(item["supplier_id"] == "local_teacher" for item in records)
            manifest["actual_external_calls"] = sum(item["supplier_id"] == "external_teacher" for item in records)
            manifest["raw_explicit_v2_responses_sealed_before_evaluation"] = False
            manifest["raw_seal_failure"] = str(seal_exc)
            atomic_write_json(output_dir / "execution_manifest.json", manifest)
        return 1


def write_harness_freeze(artifact_dir: Path) -> None:
    freeze_path, runtime_path, payload_path, _ = freeze_paths(artifact_dir)
    freeze = read_json(freeze_path)
    runtime = read_json(runtime_path)
    inputs = load_acquisition_inputs(freeze_path, runtime_path, payload_path)
    schedule = build_schedule(runtime, inputs)
    validate_schedule(schedule, runtime)
    validate_matched_projected_messages(inputs, schedule, runtime)
    external = validate_external_mechanism()
    local = validate_local_identity()
    artifact = {
        "schema": "zth.explicit_interface_direct_unit_calibration.execution_harness_freeze.v2",
        "status": "frozen_pre_response", "v2_freeze_commit": EXPECTED_V2_FREEZE_COMMIT,
        "v2_artifact_hashes": freeze["artifact_hashes"],
        "evaluator_implementation_sha256": freeze["artifact_hashes"]["evaluator_implementation"],
        "acquisition_input_projection_sha256": freeze["artifact_hashes"]["acquisition_input_projection"],
        "harness_sha256": sha_file(Path(__file__)), "case_order": runtime["case_order"], "schedule": schedule,
        "schedule_sha256": sha_bytes(_canonical(schedule)), "planned_local_calls": 16, "planned_external_calls": 16, "planned_supplier_calls": 32,
        "supplier_identities": {"local_teacher": LOCAL_SERVICE_IDENTITY, "external_teacher": EXTERNAL_SERVICE_IDENTITY},
        "local_identity_enforcement": {"required_model": LOCAL_MODEL, "required_service_alias": LOCAL_SERVICE_ALIAS, "configuration_only_no_inference": True},
        "external_mechanism_enforcement": external,
        "supplier_native_envelope_control": "BEST_AVAILABLE_OBSERVATION",
        "supplier_message_runtime_reconstruction": False, "matched_runtime_message_hash_across_arms": True, "matched_runtime_message_bytes_across_arms": True,
        "one_shot_acquisition": {"processes_started": 1, "second_acquisition_process_started": False, "guard_claimed_after_prepared_before_running": True, "guard_claimed_immediately_before_first_opportunity": True, "prepare_only_does_not_claim": True, "second_execute_rejection_status": "REJECTED_BEFORE_ACQUISITION"},
        "retries": 0, "replays": 0, "terminal_states": ["PREPARED", "REJECTED_BEFORE_ACQUISITION", "RUNNING", "TERMINAL_COMPLETE", "TERMINAL_INCOMPLETE"], "fail_closed_terminalization": True, "raw_seal_before_evaluation": True,
        "firewall": {"evaluator_file_access_during_acquisition": False, "evaluator_semantics_loaded_during_acquisition": False, "evaluator_runtime_influence": 0, "evaluator_supplier_visibility": False, "evaluator_hash_checked_only_in_preflight": True},
        "future_closeout": {"evaluator_implementation_imported_after_raw_seal": True, "evaluator_cases_loaded_after_raw_seal": True, "evaluator_sha256_must_match": True},
        "resolved_local_identity_preflight": local,
    }
    write_json(artifact_dir / HARNESS_FREEZE_NAME, artifact)


def preflight(artifact_dir: Path) -> None:
    verify_v2_acquisition_artifacts(artifact_dir)
    freeze = read_json(artifact_dir / V2_FREEZE_NAME)
    expected = freeze["artifact_hashes"]
    paths = {
        "interface": artifact_dir / V2_INTERFACE_NAME, "runtime_manifest": artifact_dir / V2_RUNTIME_NAME,
        "payload_manifest": artifact_dir / V2_PAYLOAD_NAME, "evaluator_cases": artifact_dir / V2_EVALUATOR_NAME,
    }
    for key, path in paths.items():
        if sha_file(path) != expected[key]:
            raise RuntimeError(f"V2 {key} hash mismatch in preflight")
    if sha_file(V2_EVALUATOR_IMPL) != expected["evaluator_implementation"]:
        raise RuntimeError("evaluator implementation hash mismatch in preflight")
    if sha_file(V2_PROJECTION_IMPL) != expected["acquisition_input_projection"]:
        raise RuntimeError("projection implementation hash mismatch in preflight")
    validate_local_identity()
    _, runtime, _, harness_freeze, inputs, _ = prepare_inputs(artifact_dir)
    validate_external_mechanism(
        harness_freeze["external_mechanism_enforcement"]["configured_command"],
        harness_freeze["external_mechanism_enforcement"]["wrapper_sha256"],
    )
    validate_schedule(harness_freeze["schedule"], runtime)
    if freeze["V2_TARGET_OUTCOMES"] != 0 or freeze["V2_SUPPLIER_CALLS"] != 0:
        raise RuntimeError("V2 is not unexecuted")
    print(json.dumps({"status": "preflight_pass", "supplier_calls": 0, "model_calls": 0, "external_inference_calls": 0, "matched_runtime_message_hash_across_arms": True, "matched_runtime_message_bytes_across_arms": True, "supplier_message_runtime_reconstruction": False, "local_identity_check": "pass_no_inference", "external_mechanism_check": "pass_no_inference", "projection_sha256": sha_file(V2_PROJECTION_IMPL), "inputs": len(inputs)}, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", type=Path, default=ROOT / "docs" / "research")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--write-freeze", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--guard-state", type=Path)
    args = parser.parse_args()
    artifact_dir = args.artifact_dir if args.artifact_dir.is_absolute() else ROOT / args.artifact_dir
    if args.preflight:
        preflight(artifact_dir)
        return 0
    if args.write_freeze:
        write_harness_freeze(artifact_dir)
        print(json.dumps({"status": "harness_freeze_written", "supplier_calls": 0}, sort_keys=True))
        return 0
    if args.prepare_only and args.output_dir:
        output = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
        manifest = prepare_run(output, artifact_dir)
        print(json.dumps({"status": "prepare_only_pass", "planned_supplier_calls": manifest["planned_supplier_calls"], "supplier_calls": 0}, sort_keys=True))
        return 0
    if args.execute and args.output_dir:
        output = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
        guard = args.guard_state if args.guard_state is None or args.guard_state.is_absolute() else ROOT / args.guard_state
        return execute(output, artifact_dir, guard_state=guard)
    parser.error("use --preflight, --write-freeze, --prepare-only --output-dir, or --execute --output-dir")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
