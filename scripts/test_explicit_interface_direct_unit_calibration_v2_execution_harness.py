#!/usr/bin/env python3
"""Model-free regression suite for the V2 acquisition boundary."""

from __future__ import annotations

import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DOCS = ROOT / "docs" / "research"
MODULE = importlib.import_module("scripts.execute_explicit_interface_direct_unit_calibration_v2")
HARNESS = ROOT / "scripts" / "execute_explicit_interface_direct_unit_calibration_v2.py"
ARTIFACT_NAMES = (
    "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_FREEZE_V2_2026-08-24.json",
    "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_RUNTIME_MANIFEST_V2_2026-08-24.json",
    "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_PAYLOAD_MANIFEST_V2_2026-08-24.json",
    "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_V2_EXECUTION_HARNESS_FREEZE_2026-08-24.json",
)
EVALUATOR_NAME = "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_EVALUATOR_CASES_V2_2026-08-24.json"


def frozen_inputs():
    return MODULE.prepare_inputs(DOCS)


def test_matched_messages() -> None:
    _, runtime, _, harness_freeze, inputs, by_key = frozen_inputs()
    assert len(inputs) == 32
    MODULE.validate_matched_projected_messages(inputs, harness_freeze["schedule"], runtime)
    mutated = [dict(item) for item in inputs]
    target = next(item for item in mutated if item["case_id"] == runtime["case_order"][0] and item["supplier_id"] == "external_teacher")
    target["supplier_message_text"] += " mismatch"
    try:
        MODULE.validate_matched_projected_messages(mutated, harness_freeze["schedule"], runtime)
    except RuntimeError as exc:
        assert "bytes differ" in str(exc)
    else:
        raise AssertionError("intentional arm mismatch was accepted")
    assert by_key[(runtime["case_order"][0], "local_teacher")]["supplier_message_text"].encode() == by_key[(runtime["case_order"][0], "external_teacher")]["supplier_message_text"].encode()


def test_identity_and_projection_hash() -> None:
    identity = MODULE.validate_local_identity()
    assert identity["resolved_model"] == MODULE.LOCAL_MODEL
    old_model = os.environ.get("ZTH_CAPABILITY_TEACHER_MODEL")
    os.environ["ZTH_CAPABILITY_TEACHER_MODEL"] = "wrong-model"
    try:
        try:
            MODULE.validate_local_identity()
        except RuntimeError:
            pass
        else:
            raise AssertionError("mismatched local model was accepted")
    finally:
        if old_model is None:
            os.environ.pop("ZTH_CAPABILITY_TEACHER_MODEL", None)
        else:
            os.environ["ZTH_CAPABILITY_TEACHER_MODEL"] = old_model
    original_projection = MODULE.V2_PROJECTION_IMPL
    with tempfile.TemporaryDirectory() as directory:
        bad = Path(directory) / "projection.py"
        bad.write_text(original_projection.read_text(encoding="utf-8") + "\n# mutation\n", encoding="utf-8")
        MODULE.V2_PROJECTION_IMPL = bad
        try:
            try:
                MODULE.verify_v2_acquisition_artifacts(DOCS)
            except RuntimeError as exc:
                assert "projection" in str(exc)
            else:
                raise AssertionError("modified projection was accepted")
        finally:
            MODULE.V2_PROJECTION_IMPL = original_projection


def test_external_mechanism_and_complete_failure_evidence() -> None:
    mechanism = MODULE.validate_external_mechanism()
    assert mechanism["read_only_sandbox_enforced_by_wrapper"] is True
    try:
        MODULE.validate_external_mechanism("python3 -c pass")
    except RuntimeError:
        pass
    else:
        raise AssertionError("arbitrary external command was accepted")
    result = MODULE.run_external_command(
        "python3 -c 'import sys; sys.stdout.write(\"stdout-complete\"); sys.stderr.write(\"stderr-complete\"); sys.exit(7)'",
        b"test",
        validate=False,
    )
    assert result["terminal_disposition"] == "EXTERNAL_NONZERO_EXIT"
    assert result["stdout_bytes"] == b"stdout-complete"
    assert result["stderr_bytes"] == b"stderr-complete"
    assert result["stdout_sha256"] == MODULE.sha_bytes(b"stdout-complete")
    assert result["stderr_sha256"] == MODULE.sha_bytes(b"stderr-complete")


def test_terminal_failure_and_guard_without_supplier_calls() -> None:
    with tempfile.TemporaryDirectory(prefix="explicit-v2-boundary-") as directory:
        root = Path(directory)
        output = root / "run"
        guard = root / "guard.json"
        def stub(_message: bytes) -> dict[str, object]:
            return {"content_bytes": b"test-only-capture", "metadata": {"test_only": True}}

        assert MODULE.execute(
            output,
            DOCS,
            guard_state=guard,
            capture_overrides={"local_teacher": stub, "external_teacher": stub},
            inject_exception_after=1,
        ) == 1
        manifest = json.loads((output / "execution_manifest.json").read_text(encoding="utf-8"))
        raw = json.loads((output / "raw_response_manifest.json").read_text(encoding="utf-8"))
        assert manifest["status"] == "TERMINAL_INCOMPLETE"
        assert raw["raw_explicit_v2_responses_sealed_before_evaluation"] is True
        assert manifest["actual_supplier_calls"] == 1
        assert len(list((output / "cases").glob("*/*/call_finished.json"))) == 1
        assert guard.exists()
        try:
            MODULE.claim_one_shot_guard(guard, MODULE.sha_file(HARNESS), MODULE.EXPECTED_V2_FREEZE_COMMIT)
        except RuntimeError:
            pass
        else:
            raise AssertionError("second acquisition guard claim was accepted")


def test_prepare_only_firewall_and_zero_calls() -> None:
    with tempfile.TemporaryDirectory(prefix="explicit-interface-v2-harness-") as directory:
        root = Path(directory)
        artifact_dir = root / "artifacts"
        run_dir = root / "run"
        artifact_dir.mkdir()
        for name in ARTIFACT_NAMES:
            shutil.copy2(DOCS / name, artifact_dir / name)
        assert not (artifact_dir / EVALUATOR_NAME).exists()
        completed = subprocess.run(
            [sys.executable, str(HARNESS), "--artifact-dir", str(artifact_dir), "--prepare-only", "--output-dir", str(run_dir)],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        assert completed.returncode == 0, completed.stderr
        manifest = json.loads((run_dir / "execution_manifest.json").read_text(encoding="utf-8"))
        assert manifest["status"] == "PREPARED"
        assert manifest["planned_supplier_calls"] == 32
        assert manifest["processes_started"] == 0
        assert manifest["matched_runtime_message_bytes_across_arms"] is True
        assert not list(run_dir.rglob("response.json"))
        assert not list(run_dir.rglob("infrastructure_failure.json"))
        assert not (root / "guard.json").exists()


def main() -> None:
    test_matched_messages()
    test_identity_and_projection_hash()
    test_external_mechanism_and_complete_failure_evidence()
    test_terminal_failure_and_guard_without_supplier_calls()
    test_prepare_only_firewall_and_zero_calls()
    print("PASS V2 hardened acquisition boundary tests; supplier/model calls=0")


if __name__ == "__main__":
    main()
