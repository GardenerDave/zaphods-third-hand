#!/usr/bin/env python3
"""Execute the frozen prospective delegation-prediction supplier arms.

Acquisition deliberately loads only the runtime manifest and experiment-authored
interface contract. Evaluator cases are consumed only by the separate closeout.
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
RUNTIME_MANIFEST = ROOT / "docs/research/DELEGATION_PREDICTION_PROSPECTIVE_RUNTIME_MANIFEST_2026-08-24.json"
INTERFACE_CONTRACT = ROOT / "docs/research/DELEGATION_PREDICTION_PROSPECTIVE_INTERFACE_CONTRACT_V2_2026-08-24.json"
FREEZE = ROOT / "docs/research/DELEGATION_PREDICTION_PROSPECTIVE_FREEZE_V2_2026-08-24.json"
EXPECTED_FREEZE_COMMIT = "fc6902926a89d3572b457bea1d5cca5e4ba53f4d"
EXPECTED_INTERFACE_SHA256 = "c6726c65a40df77c6e681226c90f48c16e00348b5727ab15a14c6b7e61cb3f93"
EXPECTED_RUNTIME_SHA256 = "f10ff1ef98ecc0e452d59e842398a0b37a2760e4d7adf63a2be762d1d23f077c"
EXTERNAL_CWD = Path("/tmp")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def current_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def contains_authoritative_freeze() -> bool:
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", EXPECTED_FREEZE_COMMIT, "HEAD"],
        cwd=ROOT,
        check=False,
    ).returncode == 0


def output_schema(contract: dict[str, Any]) -> dict[str, Any]:
    return contract["experiment_authored_payload"]["output_schema"]


def make_prompt(case: dict[str, Any], contract: dict[str, Any]) -> str:
    # This projection contains only the frozen experiment-authored request,
    # authority context, and output contract. Controller/predictor metadata is
    # intentionally excluded.
    return (
        "Return exactly one JSON object and no prose.\n\n"
        "REQUEST:\n" + case["request"] + "\n\n"
        "AUTHORITY_CONTEXT:\n" + case["authority_context"] + "\n\n"
        "OUTPUT_CONTRACT:\n" + json.dumps(output_schema(contract), sort_keys=True, separators=(",", ":")) + "\n"
        "The response must contain the required fields and report the exact allowed and held targets from the request."
    )


def validate_inputs() -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    if not contains_authoritative_freeze():
        raise RuntimeError(f"authoritative freeze is not an ancestor of execution HEAD: {current_head()}")
    if digest_file(INTERFACE_CONTRACT) != EXPECTED_INTERFACE_SHA256:
        raise RuntimeError("interface contract hash mismatch")
    if digest_file(RUNTIME_MANIFEST) != EXPECTED_RUNTIME_SHA256:
        raise RuntimeError("runtime manifest hash mismatch")
    manifest = read_json(RUNTIME_MANIFEST)
    contract = read_json(INTERFACE_CONTRACT)
    freeze = read_json(FREEZE)
    cases = manifest["cases"]
    if len(cases) != 16 or [case["execution_order"] for case in cases] != list(range(1, 17)):
        raise RuntimeError("runtime case count/order mismatch")
    if sum(case["category"] == "SUPPLIER_SELECTION" for case in cases) != 8:
        raise RuntimeError("supplier-selection stratum mismatch")
    if sum(case["category"] == "DELEGATE_VS_ABSTAIN" for case in cases) != 8:
        raise RuntimeError("delegate-vs-abstain stratum mismatch")
    if sum(case["generalized_policy"]["expected_success"] != case["degeneralized_policy"]["expected_success"] for case in cases) != 8:
        raise RuntimeError("binary-success disagreement mismatch")
    if manifest.get("evaluator_access") is not False or contract["experiment_authored_payload"].get("evaluator_access") is not False:
        raise RuntimeError("evaluator access is not disabled")
    if contract["experiment_authored_payload"].get("tool_calls") != 0:
        raise RuntimeError("tool calls are not frozen to zero")
    if freeze["policies"]["supplier_selections_unchanged"] is not True:
        raise RuntimeError("supplier-selection freeze marker missing")
    return manifest, contract, cases


def write_json(path: Path, value: Any) -> str:
    data = json.dumps(value, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data.encode("utf-8"))
    return digest_bytes(data.encode("utf-8"))


def write_started(arm_dir: Path, *, case: dict[str, Any], role: str, supplier_identity: str, payload_hash: str) -> None:
    write_json(
        arm_dir / "call_started.json",
        {
            "schema": "zth_delegation_prediction_supplier_call_started_v1",
            "case_id": case["case_id"],
            "supplier_id": role,
            "supplier_identity": supplier_identity,
            "experiment_payload_sha256": payload_hash,
            "started_at": utc_now(),
            "tool_calls": 0,
            "repository_access": False,
            "evaluator_access": False,
        },
    )


def capture_local(prompt: str) -> tuple[dict[str, Any], str]:
    spec = resolve_worker_spec(
        os.environ.get("ZTH_CAPABILITY_TEACHER_NAME", "handoff"),
        base_url=os.environ.get("ZTH_CAPABILITY_TEACHER_BASE_URL"),
        model=os.environ.get("ZTH_CAPABILITY_TEACHER_MODEL"),
    )
    started = time.monotonic()
    response = call_worker(
        spec,
        prompt,
        int(os.environ.get("ZTH_CAPABILITY_TEACHER_MAX_TOKENS", "1200")),
        timeout=int(os.environ.get("ZTH_CAPABILITY_TEACHER_TIMEOUT", "900")),
    )
    captured = time.monotonic()
    metadata = response.metadata()
    metadata["request_elapsed_ms"] = round((captured - started) * 1000.0, 3)
    metadata["supplier_native_envelope_control"] = "BEST_AVAILABLE_OBSERVATION"
    metadata["tool_calls"] = 0
    metadata["repository_access"] = False
    metadata["evaluator_access"] = False
    return {"status": response.status, "content": response.content, "metadata": metadata}, "local_teacher"


def capture_external(prompt: str) -> tuple[dict[str, Any], str]:
    command = os.environ.get("ZTH_EXTERNAL_TEACHER_COMMAND")
    identity = os.environ.get("ZTH_EXTERNAL_TEACHER_IDENTITY", "codex-cli-0.146.0")
    if not command:
        raise RuntimeError("ZTH_EXTERNAL_TEACHER_COMMAND is not configured")
    started = time.monotonic()
    completed = subprocess.run(
        shlex.split(command),
        input=prompt,
        text=True,
        capture_output=True,
        cwd=EXTERNAL_CWD,
        timeout=120,
        check=False,
    )
    captured = time.monotonic()
    if completed.returncode != 0:
        raise RuntimeError(f"external supplier exited {completed.returncode}: {completed.stderr[-4000:]}")
    return {
        "status": "ok" if completed.stdout.strip() else "empty_content",
        "content": completed.stdout,
        "metadata": {
            "identity": identity,
            "command_sha256": digest_bytes(command.encode("utf-8")),
            "cwd": str(EXTERNAL_CWD),
            "request_elapsed_ms": round((captured - started) * 1000.0, 3),
            "transport_classification": "model_response" if completed.stdout.strip() else "empty_model_response",
            "tool_calls": 0,
            "repository_access": False,
            "evaluator_access": False,
            "native_envelope_control": "BEST_AVAILABLE_OBSERVATION",
        },
    }, "external_teacher"


def execute(output_dir: Path) -> int:
    manifest, contract, cases = validate_inputs()
    if output_dir.exists():
        if any(output_dir.rglob("response.json")) or any(output_dir.rglob("raw_response.json")):
            raise RuntimeError("prospective responses already exist; refusing replay")
        if any(output_dir.iterdir()):
            raise RuntimeError("output directory is non-empty; refusing ambiguous execution")
    output_dir.mkdir(parents=True, exist_ok=False)
    payload_dir = output_dir / "experiment_payloads"
    payload_hashes: dict[str, str] = {}
    for case in cases:
        prompt = make_prompt(case, contract)
        payload = {
            "request": case["request"],
            "authority_context": case["authority_context"],
            "output_contract": output_schema(contract),
            "prompt": prompt,
        }
        payload_hash = write_json(payload_dir / f"{case['case_id']}.json", payload)
        payload_hashes[case["case_id"]] = payload_hash
    write_json(
        output_dir / "execution_manifest.json",
        {
            "schema": "zth_delegation_prediction_prospective_execution_manifest_v1",
            "status": "running",
            "freeze_commit": EXPECTED_FREEZE_COMMIT,
            "runtime_manifest_sha256": digest_file(RUNTIME_MANIFEST),
            "interface_contract_sha256": digest_file(INTERFACE_CONTRACT),
            "planned_supplier_calls": 32,
            "planned_local_calls": 16,
            "planned_external_calls": 16,
            "execution_order": [
                {"case_id": case["case_id"], "supplier": role}
                for case in cases
                for role in ("local_teacher", "external_teacher")
            ],
            "experiment_payload_hashes": payload_hashes,
            "evaluator_loaded_during_acquisition": False,
            "retries": 0,
            "replays": 0,
            "tool_calls": 0,
        },
    )

    call_records: list[dict[str, Any]] = []
    for case in cases:
        case_dir = output_dir / "cases" / case["case_id"]
        payload_path = payload_dir / f"{case['case_id']}.json"
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        prompt = payload["prompt"]
        for role, identity, capture in (
            ("local_teacher", os.environ.get("ZTH_CAPABILITY_TEACHER_MODEL", "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf"), capture_local),
            ("external_teacher", os.environ.get("ZTH_EXTERNAL_TEACHER_IDENTITY", "codex-cli-0.146.0"), capture_external),
        ):
            arm_dir = case_dir / role
            arm_dir.mkdir(parents=True, exist_ok=False)
            payload_bytes = payload_path.read_bytes()
            (arm_dir / "experiment_payload.json").write_bytes(payload_bytes)
            payload_hash = digest_bytes(payload_bytes)
            write_started(arm_dir, case=case, role=role, supplier_identity=identity, payload_hash=payload_hash)
            started = time.time()
            try:
                raw, returned_role = capture(prompt)
                raw["case_id"] = case["case_id"]
                raw["supplier_id"] = returned_role
                raw["experiment_payload_sha256"] = payload_hash
                raw["captured_at"] = utc_now()
                raw["raw_response_sha256"] = digest_bytes(str(raw.get("content", "")).encode("utf-8"))
                response_hash = write_json(arm_dir / "response.json", raw)
                telemetry = raw.get("metadata", {}).get("resource_telemetry")
                write_json(arm_dir / "power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "resource_telemetry": telemetry, "available": telemetry is not None})
                record = {"case_id": case["case_id"], "supplier_id": role, "status": raw.get("status"), "response_sha256": response_hash, "transport_valid": raw.get("metadata", {}).get("transport_classification") == "model_response", "tool_calls": 0}
            except Exception as exc:
                failure = {"schema": "zth_delegation_prediction_supplier_failure_v1", "case_id": case["case_id"], "supplier_id": role, "error": str(exc)[-4000:], "captured_at": utc_now(), "tool_calls": 0, "repository_access": False, "evaluator_access": False}
                failure_hash = write_json(arm_dir / "infrastructure_failure.json", failure)
                record = {"case_id": case["case_id"], "supplier_id": role, "status": "infrastructure_failure", "failure_sha256": failure_hash, "transport_valid": False, "tool_calls": 0}
            record["elapsed_wall_ms"] = round((time.time() - started) * 1000.0, 3)
            call_records.append(record)

    sealed = {
        "schema": "zth_delegation_prediction_raw_response_manifest_v1",
        "status": "SEALED_BEFORE_EVALUATION",
        "raw_prospective_responses_sealed_before_evaluation": True,
        "evaluator_loaded_during_acquisition": False,
        "planned_supplier_calls": 32,
        "actual_supplier_calls": len(call_records),
        "actual_local_calls": sum(row["supplier_id"] == "local_teacher" for row in call_records),
        "actual_external_calls": sum(row["supplier_id"] == "external_teacher" for row in call_records),
        "retries": 0,
        "replays": 0,
        "tool_calls": 0,
        "records": call_records,
    }
    write_json(output_dir / "raw_response_manifest.json", sealed)
    write_json(output_dir / "lifecycle.json", {"status": "terminal_runtime", "model_calls": len(call_records), "supplier_calls": len(call_records), "local_calls": sealed["actual_local_calls"], "external_calls": sealed["actual_external_calls"], "teacher_calls": 0, "tool_calls": 0, "external_inference_calls": sealed["actual_external_calls"], "retries": 0, "replays": 0, "runtime_evaluator_influence": 0, "model_output_granted_authority": 0})
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.preflight:
        manifest, contract, cases = validate_inputs()
        payloads = [make_prompt(case, contract) for case in cases]
        assert len(payloads) == 16 and all("evaluator" not in prompt.lower() for prompt in payloads)
        assert all("generalized_policy" not in prompt and "degeneralized_policy" not in prompt for prompt in payloads)
        print(json.dumps({"status": "preflight_pass", "cases": len(manifest["cases"]), "payloads": len(payloads), "planned_supplier_calls": 32}, sort_keys=True))
        return 0
    if args.execute and args.output_dir:
        return execute(args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir)
    parser.error("use --preflight or --execute --output-dir")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
