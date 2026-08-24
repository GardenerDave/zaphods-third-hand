#!/usr/bin/env python3
"""Model-free regression for the V2 acquisition-input loader boundary."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.project_explicit_interface_direct_unit_calibration_v2_inputs import load_acquisition_inputs


DOCS = ROOT / "docs" / "research"
FREEZE = DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_FREEZE_V2_2026-08-24.json"
RUNTIME = DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_RUNTIME_MANIFEST_V2_2026-08-24.json"
PAYLOAD = DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_PAYLOAD_MANIFEST_V2_2026-08-24.json"
EVALUATOR = DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_EVALUATOR_CASES_V2_2026-08-24.json"


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="explicit-interface-v2-firewall-") as directory:
        root = Path(directory)
        freeze_copy = root / FREEZE.name
        runtime_copy = root / RUNTIME.name
        payload_copy = root / PAYLOAD.name
        shutil.copy2(FREEZE, freeze_copy)
        shutil.copy2(RUNTIME, runtime_copy)
        shutil.copy2(PAYLOAD, payload_copy)
        assert not (root / EVALUATOR.name).exists()
        inputs = load_acquisition_inputs(freeze_copy, runtime_copy, payload_copy)
        assert len(inputs) == 32
        assert len({item["case_id"] for item in inputs}) == 16
        assert all(item["supplier_message_text"] for item in inputs)
        for case_id in {item["case_id"] for item in inputs}:
            hashes = {item["supplier_message_sha256"] for item in inputs if item["case_id"] == case_id}
            assert len(hashes) == 1
    print("PASS V2 acquisition-input loader works with evaluator artifact absent")


if __name__ == "__main__":
    main()
