#!/usr/bin/env python3
"""One-shot acquisition harness for the frozen explicit-interface V2 unit.

The acquisition path imports only the evaluator-free projection module.  It
does not import or open scoring/evaluator artifacts.  The default operation is
prepare-only; supplier execution requires an explicit ``--execute`` flag.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
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
V2_RUNTIME_NAME = "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_RUNTIME_MANIFEST_V2_2026-08-24.json"
V2_PAYLOAD_NAME = "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_PAYLOAD_MANIFEST_V2_2026-08-24.json"
V2_EVALUATOR_NAME = "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_EVALUATOR_CASES_V2_2026-08-24.json"
V2_EVALUATOR_IMPL = ROOT / "scripts/evaluate_explicit_interface_direct_unit_calibration_v2.py"
HARNESS_FREEZE_NAME = "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_V2_EXECUTION_HARNESS_FREEZE_2026-08-24.json"
EXTERNAL_CWD = Path("/tmp")


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


def current_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def freeze_paths(artifact_dir: Path) -> tuple[Path, Path, Path, Path]:
    return (artifact_dir / V2_FREEZE_NAME, artifact_dir / V2_RUNTIME_NAME, artifact_dir / V2_PAYLOAD_NAME, artifact_dir / HARNESS_FREEZE_NAME)


def verify_v2_acquisition_artifacts(artifact_dir: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    freeze_path, runtime_path, payload_path, harness_freeze_path = freeze_paths(artifact_dir)
    freeze = read_json(freeze_path)
    runtime = read_json(runtime_path)
    payload = read_json(payload_path)
    harness_freeze = read_json(harness_freeze_path)
    if subprocess.run(["git", "merge-base", "--is-ancestor", EXPECTED_V2_FREEZE_COMMIT, "HEAD"], cwd=ROOT, check=False).returncode != 0:
        raise RuntimeError(f"V2 freeze is not an ancestor of HEAD {current_head()}")
    expected = freeze["artifact_hashes"]
    checks = {"interface": artifact_dir / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_INTERFACE_V2_2026-08-24.json", "runtime_manifest": runtime_path, "payload_manifest": payload_path, "evaluator_cases": artifact_dir / V2_EVALUATOR_NAME}
    # The acquisition path deliberately does not open the evaluator-case file;
    # its expected hash is already materialized in the V2 freeze.
    if sha_file(checks["runtime_manifest"]) != expected["runtime_manifest"]:
        raise RuntimeError("V2 runtime manifest hash mismatch")
    if sha_file(checks["payload_manifest"]) != expected["payload_manifest"]:
        raise RuntimeError("V2 payload manifest hash mismatch")
    if harness_freeze["v2_freeze_commit"] != EXPECTED_V2_FREEZE_COMMIT:
        raise RuntimeError("execution harness is bound to the wrong V2 freeze")
    if harness_freeze["harness_sha256"] != sha_file(Path(__file__)):
        raise RuntimeError("execution harness implementation hash mismatch")
    if harness_freeze["schedule_sha256"] != sha_bytes(_canonical(harness_freeze["schedule"])):
        raise RuntimeError("expanded schedule hash mismatch")
    if runtime["case_order"] != harness_freeze["case_order"]:
        raise RuntimeError("schedule case order mismatch")
    if len(runtime["cases"]) != 16 or len(harness_freeze["schedule"]) != 32:
        raise RuntimeError("V2 case or schedule count mismatch")
    if harness_freeze["planned_local_calls"] != 16 or harness_freeze["planned_external_calls"] != 16:
        raise RuntimeError("supplier call budget mismatch")
    return freeze, runtime, payload, harness_freeze


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def build_schedule(runtime: dict[str, Any], inputs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_case = {case["case_id"]: case for case in runtime["cases"]}
    message_by_case = {item["case_id"]: item for item in inputs}
    schedule: list[dict[str, Any]] = []
    ordinal = 1
    family_positions: dict[str, int] = {}
    for case in runtime["cases"]:
        family = case["capability_family"]
        position = family_positions.get(family, 0)
        family_positions[family] = position + 1
        first = "local_teacher" if position % 2 == 0 else "external_teacher"
        arms = [first, "external_teacher" if first == "local_teacher" else "local_teacher"]
        source = message_by_case[case["case_id"]]
        for supplier_id in arms:
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


def prepare_inputs(artifact_dir: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    freeze, runtime, payload, harness_freeze = verify_v2_acquisition_artifacts(artifact_dir)
    # This is the only message projection used by acquisition.  It does not
    # import the evaluator or open evaluator-case records.
    inputs = load_acquisition_inputs(*freeze_paths(artifact_dir)[:3])
    schedule = harness_freeze["schedule"]
    validate_schedule(schedule, runtime)
    message_hashes = {item["case_id"]: item["supplier_message_sha256"] for item in inputs}
    for entry in schedule:
        if entry["supplier_message_sha256"] != message_hashes[entry["case_id"]]:
            raise RuntimeError("schedule supplier-message hash mismatch")
    return freeze, runtime, payload, harness_freeze, inputs


def prepare_run(output_dir: Path, artifact_dir: Path) -> dict[str, Any]:
    if output_dir.exists():
        raise RuntimeError("run directory already exists; refusing resume/replay")
    freeze, runtime, payload, harness_freeze, inputs = prepare_inputs(artifact_dir)
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
        "supplier_message_hashes": {item["case_id"]: item["supplier_message_sha256"] for item in inputs},
        "evaluator_file_access_during_acquisition": False,
        "evaluator_semantics_loaded_during_acquisition": False,
        "evaluator_runtime_influence": 0,
        "evaluator_supplier_visibility": False,
        "processes_started": 0,
        "second_acquisition_process_started": False,
        "retries": 0,
        "replays": 0,
        "evaluator_loaded_during_acquisition": False,
    }
    atomic_write_json(output_dir / "execution_manifest.json", manifest)
    return manifest


def observe_protocol(stdout: str, stderr: str) -> dict[str, Any]:
    combined = f"{stdout}\n{stderr}".casefold()
    tool_markers = ("tool call", "tool_calls", "function_call", "function call", "shell command")
    repo_markers = ("git status", "git diff", ".git/", "repository access", "working tree")
    return {"tool_calls_observed": any(marker in combined for marker in tool_markers), "repository_access_observed": any(marker in combined for marker in repo_markers), "evaluator_access_observed": "evaluator" in combined}


def capture_local(message: str) -> tuple[str, dict[str, Any]]:
    from local_harness.icm_call import call_worker
    from local_harness.icm_spec import resolve_worker_spec
    spec = resolve_worker_spec(os.environ.get("ZTH_CAPABILITY_TEACHER_NAME", "handoff"), base_url=os.environ.get("ZTH_CAPABILITY_TEACHER_BASE_URL"), model=os.environ.get("ZTH_CAPABILITY_TEACHER_MODEL"))
    started = time.monotonic()
    response = call_worker(spec, message, int(os.environ.get("ZTH_CAPABILITY_TEACHER_MAX_TOKENS", "1200")), timeout=int(os.environ.get("ZTH_CAPABILITY_TEACHER_TIMEOUT", "900")))
    elapsed = round((time.monotonic() - started) * 1000.0, 3)
    return response.content, {"status": response.status, "elapsed_ms": elapsed, "service_identity": "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf via JARVIS_LOCAL", "tool_calls_observed": False, "repository_access_observed": False, "evaluator_access_observed": False, "native_envelope_control": "BEST_AVAILABLE_OBSERVATION", "transport_classification": "model_response" if response.content.strip() else "empty_model_response"}


def capture_external(message: str) -> tuple[str, dict[str, Any]]:
    command = os.environ.get("ZTH_EXTERNAL_TEACHER_COMMAND")
    if not command:
        raise RuntimeError("ZTH_EXTERNAL_TEACHER_COMMAND is not configured")
    started = time.monotonic()
    completed = subprocess.run(shlex.split(command), input=message, text=True, capture_output=True, cwd=EXTERNAL_CWD, timeout=120, check=False)
    elapsed = round((time.monotonic() - started) * 1000.0, 3)
    observed = observe_protocol(completed.stdout, completed.stderr)
    if completed.returncode != 0:
        raise RuntimeError(f"external supplier exited {completed.returncode}: {completed.stderr[-4000:]}")
    return completed.stdout, {"status": "ok" if completed.stdout.strip() else "empty_content", "elapsed_ms": elapsed, "service_identity": "codex-cli-0.146.0 via preserved service mechanism", "observed_native_identity": os.environ.get("ZTH_EXTERNAL_TEACHER_NATIVE_IDENTITY", "BEST_AVAILABLE_OBSERVATION"), "stderr_sha256": sha_bytes(completed.stderr.encode("utf-8")), "stderr": completed.stderr, **observed, "native_envelope_control": "BEST_AVAILABLE_OBSERVATION", "transport_classification": "model_response" if completed.stdout.strip() else "empty_model_response"}


def execute(output_dir: Path, artifact_dir: Path) -> int:
    manifest = prepare_run(output_dir, artifact_dir)
    manifest["status"] = "RUNNING"
    manifest["processes_started"] = 1
    atomic_write_json(output_dir / "execution_manifest.json", manifest)
    _, runtime, _, harness_freeze, inputs = prepare_inputs(artifact_dir)
    input_by_key = {(item["case_id"], item["supplier_id"]): item for item in inputs}
    call_records: list[dict[str, Any]] = []
    for schedule_item in harness_freeze["schedule"]:
        key = (schedule_item["case_id"], schedule_item["supplier_id"])
        source = input_by_key[key]
        arm_dir = output_dir / "cases" / schedule_item["case_id"] / schedule_item["supplier_id"]
        arm_dir.mkdir(parents=True, exist_ok=False)
        message_bytes = source["supplier_message_text"].encode("utf-8")
        if sha_bytes(message_bytes) != source["supplier_message_sha256"]:
            raise RuntimeError("transmitted supplier message hash mismatch")
        (arm_dir / "supplier_message.txt").write_bytes(message_bytes)
        start = utc_now(); started_mono = time.monotonic()
        atomic_write_json(arm_dir / "call_started.json", {"schema": "zth.explicit_interface_v2.call_started", "ordinal": schedule_item["ordinal"], "case_id": schedule_item["case_id"], "capability_family": schedule_item["capability_family"], "interface_id": schedule_item["interface_id"], "supplier_id": schedule_item["supplier_id"], "supplier_message_sha256": source["supplier_message_sha256"], "started_at": start, "evaluator_file_access_during_acquisition": False, "evaluator_semantics_loaded_during_acquisition": False, "evaluator_runtime_influence": 0, "evaluator_supplier_visibility": False})
        try:
            capture: Callable[[str], tuple[str, dict[str, Any]]] = capture_local if schedule_item["supplier_id"] == "local_teacher" else capture_external
            content, metadata = capture(source["supplier_message_text"])
            content_bytes = content.encode("utf-8")
            response = {"schema": "zth.explicit_interface_v2.raw_supplier_response", "ordinal": schedule_item["ordinal"], "case_id": schedule_item["case_id"], "capability_family": schedule_item["capability_family"], "interface_id": schedule_item["interface_id"], "supplier_id": schedule_item["supplier_id"], "supplier_message_sha256": source["supplier_message_sha256"], "raw_supplier_content": content, "raw_supplier_content_sha256": sha_bytes(content_bytes), "metadata": metadata, "captured_at": utc_now()}
            response_hash = atomic_write_json(arm_dir / "response.json", response)
            disposition = "RESPONSE_CAPTURED"
            terminal = {"terminal_disposition": disposition, "response_artifact_sha256": response_hash, "raw_supplier_content_sha256": response["raw_supplier_content_sha256"]}
        except Exception as exc:
            failure = {"schema": "zth.explicit_interface_v2.infrastructure_failure", "ordinal": schedule_item["ordinal"], "case_id": schedule_item["case_id"], "supplier_id": schedule_item["supplier_id"], "error": str(exc)[-4000:], "captured_at": utc_now()}
            failure_hash = atomic_write_json(arm_dir / "infrastructure_failure.json", failure)
            disposition = "INFRASTRUCTURE_FAILURE"
            terminal = {"terminal_disposition": disposition, "failure_artifact_sha256": failure_hash}
        finished = utc_now()
        terminal.update({"ordinal": schedule_item["ordinal"], "case_id": schedule_item["case_id"], "capability_family": schedule_item["capability_family"], "interface_id": schedule_item["interface_id"], "supplier_id": schedule_item["supplier_id"], "supplier_message_sha256": source["supplier_message_sha256"], "frozen_supplier_identity": "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf via JARVIS_LOCAL" if schedule_item["supplier_id"] == "local_teacher" else "codex-cli-0.146.0 via preserved service mechanism", "started_at": start, "finished_at": finished, "elapsed_ms": round((time.monotonic() - started_mono) * 1000.0, 3), "retries": 0, "replays": 0})
        atomic_write_json(arm_dir / "call_finished.json", terminal)
        call_records.append(terminal)
    complete = len(call_records) == 32
    manifest["status"] = "TERMINAL_COMPLETE" if complete else "TERMINAL_INCOMPLETE"
    manifest["actual_supplier_calls"] = len(call_records)
    manifest["actual_local_calls"] = sum(item["supplier_id"] == "local_teacher" for item in call_records)
    manifest["actual_external_calls"] = sum(item["supplier_id"] == "external_teacher" for item in call_records)
    atomic_write_json(output_dir / "execution_manifest.json", manifest)
    raw_manifest = {"schema": "zth.explicit_interface_v2.raw_acquisition_manifest", "status": "SEALED_BEFORE_EVALUATION", "raw_explicit_v2_responses_sealed_before_evaluation": True, "evaluator_file_access_during_acquisition": False, "evaluator_semantics_loaded_during_acquisition": False, "evaluator_runtime_influence": 0, "evaluator_supplier_visibility": False, "planned_supplier_calls": 32, "actual_supplier_calls": len(call_records), "actual_local_calls": manifest["actual_local_calls"], "actual_external_calls": manifest["actual_external_calls"], "retries": 0, "replays": 0, "records": call_records}
    atomic_write_json(output_dir / "raw_response_manifest.json", raw_manifest)
    atomic_write_json(output_dir / "lifecycle.json", {"status": manifest["status"], "processes_started": 1, "second_acquisition_process_started": False, "supplier_calls": len(call_records), "model_calls": len(call_records), "external_inference_calls": manifest["actual_external_calls"], "retries": 0, "replays": 0, "evaluator_file_access_during_acquisition": False, "evaluator_semantics_loaded_during_acquisition": False, "evaluator_runtime_influence": 0})
    return 0


def write_harness_freeze(artifact_dir: Path) -> None:
    freeze_path, runtime_path, payload_path, _ = freeze_paths(artifact_dir)
    freeze = read_json(freeze_path)
    runtime = read_json(runtime_path)
    inputs = load_acquisition_inputs(freeze_path, runtime_path, payload_path)
    schedule = build_schedule(runtime, inputs)
    validate_schedule(schedule, runtime)
    artifact = {"schema": "zth.explicit_interface_direct_unit_calibration.execution_harness_freeze.v1", "status": "frozen_pre_response", "v2_freeze_commit": EXPECTED_V2_FREEZE_COMMIT, "v2_artifact_hashes": freeze["artifact_hashes"], "evaluator_implementation_sha256": freeze["artifact_hashes"]["evaluator_implementation"], "acquisition_input_projection_sha256": freeze["artifact_hashes"]["acquisition_input_projection"], "harness_sha256": sha_file(Path(__file__)), "case_order": runtime["case_order"], "schedule": schedule, "schedule_sha256": sha_bytes(_canonical(schedule)), "planned_local_calls": 16, "planned_external_calls": 16, "planned_supplier_calls": 32, "supplier_identities": {"local_teacher": "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf via JARVIS_LOCAL", "external_teacher": "codex-cli-0.146.0 via preserved service mechanism"}, "supplier_native_envelope_control": "BEST_AVAILABLE_OBSERVATION", "supplier_message_runtime_reconstruction": False, "matched_runtime_message_hash_across_arms": True, "processes_started": 1, "second_acquisition_process_started": False, "retries": 0, "replays": 0, "terminal_states": ["PREPARED", "RUNNING", "TERMINAL_COMPLETE", "TERMINAL_INCOMPLETE"], "raw_seal_before_evaluation": True, "firewall": {"evaluator_file_access_during_acquisition": False, "evaluator_semantics_loaded_during_acquisition": False, "evaluator_runtime_influence": 0, "evaluator_supplier_visibility": False, "evaluator_hash_checked_only_in_preflight": True}, "future_closeout": {"evaluator_implementation_imported_after_raw_seal": True, "evaluator_cases_loaded_after_raw_seal": True, "evaluator_sha256_must_match": True}}
    write_json(artifact_dir / HARNESS_FREEZE_NAME, artifact)


def preflight(artifact_dir: Path) -> None:
    verify_v2_acquisition_artifacts(artifact_dir)
    freeze = read_json(artifact_dir / V2_FREEZE_NAME)
    expected = freeze["artifact_hashes"]
    preflight_paths = {
        "interface": artifact_dir / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_INTERFACE_V2_2026-08-24.json",
        "runtime_manifest": artifact_dir / V2_RUNTIME_NAME,
        "payload_manifest": artifact_dir / V2_PAYLOAD_NAME,
        "evaluator_cases": artifact_dir / V2_EVALUATOR_NAME,
    }
    for key, path in preflight_paths.items():
        if sha_file(path) != expected[key]:
            raise RuntimeError(f"V2 {key} hash mismatch in preflight")
    if sha_file(V2_EVALUATOR_IMPL) != expected["evaluator_implementation"]:
        raise RuntimeError("evaluator implementation hash mismatch in preflight")
    if freeze["V2_TARGET_OUTCOMES"] != 0 or freeze["V2_SUPPLIER_CALLS"] != 0:
        raise RuntimeError("V2 is not unexecuted")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", type=Path, default=ROOT / "docs" / "research")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--write-freeze", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    artifact_dir = args.artifact_dir if args.artifact_dir.is_absolute() else ROOT / args.artifact_dir
    if args.preflight:
        preflight(artifact_dir); print(json.dumps({"status": "preflight_pass", "supplier_calls": 0}, sort_keys=True)); return 0
    if args.write_freeze:
        write_harness_freeze(artifact_dir); print(json.dumps({"status": "harness_freeze_written", "supplier_calls": 0}, sort_keys=True)); return 0
    if args.prepare_only and args.output_dir:
        output = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
        manifest = prepare_run(output, artifact_dir); print(json.dumps({"status": "prepare_only_pass", "planned_supplier_calls": manifest["planned_supplier_calls"], "supplier_calls": 0}, sort_keys=True)); return 0
    if args.execute and args.output_dir:
        output = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
        return execute(output, artifact_dir)
    parser.error("use --preflight, --write-freeze, --prepare-only --output-dir, or --execute --output-dir")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
