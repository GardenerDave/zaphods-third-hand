#!/usr/bin/env python3
"""Model-free test of the actual V2 harness prepare path."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "research"
HARNESS = ROOT / "scripts" / "execute_explicit_interface_direct_unit_calibration_v2.py"
ARTIFACT_NAMES = (
    "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_FREEZE_V2_2026-08-24.json",
    "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_RUNTIME_MANIFEST_V2_2026-08-24.json",
    "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_PAYLOAD_MANIFEST_V2_2026-08-24.json",
    "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_V2_EXECUTION_HARNESS_FREEZE_2026-08-24.json",
)
EVALUATOR_NAME = "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_EVALUATOR_CASES_V2_2026-08-24.json"


def main() -> None:
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
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        manifest = json.loads((run_dir / "execution_manifest.json").read_text(encoding="utf-8"))
        assert manifest["status"] == "PREPARED"
        assert manifest["planned_supplier_calls"] == 32
        assert manifest["processes_started"] == 0
        assert manifest["evaluator_file_access_during_acquisition"] is False
        assert not list(run_dir.rglob("response.json"))
        assert not list(run_dir.rglob("infrastructure_failure.json"))
        schedule = manifest["schedule"]
        assert len(schedule) == 32
        assert sum(item["supplier_id"] == "local_teacher" for item in schedule) == 16
        assert sum(item["supplier_id"] == "external_teacher" for item in schedule) == 16
    print("PASS actual V2 harness prepare path with evaluator artifact absent; supplier calls=0")


if __name__ == "__main__":
    main()
