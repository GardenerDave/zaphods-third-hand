#!/usr/bin/env python3
"""Model-free regression for the explicit-interface acquisition boundary."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "research"
RUNTIME = DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_RUNTIME_MANIFEST_2026-08-24.json"
PAYLOAD = DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_PAYLOAD_MANIFEST_2026-08-24.json"
EVALUATOR = DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_EVALUATOR_CASES_2026-08-24.json"


def main() -> None:
    runtime = json.loads(RUNTIME.read_text(encoding="utf-8"))
    payload = json.loads(PAYLOAD.read_text(encoding="utf-8"))
    evaluator = json.loads(EVALUATOR.read_text(encoding="utf-8"))
    assert runtime["evaluator_information_included"] is False
    assert runtime["scoring_information_included"] is False
    assert runtime["policy_information_included"] is False
    assert payload["evaluator_information_included"] is False
    runtime_bytes = RUNTIME.read_bytes()
    payload_bytes = PAYLOAD.read_bytes()
    with tempfile.TemporaryDirectory(prefix="explicit-interface-firewall-") as directory:
        root = Path(directory)
        (root / RUNTIME.name).write_bytes(runtime_bytes)
        (root / PAYLOAD.name).write_bytes(payload_bytes)
        # The acquisition-input projection is deliberately constructible with
        # the scoring-only evaluator absent.  This is the regression boundary;
        # no supplier transport is called here.
        assert not (root / EVALUATOR.name).exists()
        runtime_copy = json.loads((root / RUNTIME.name).read_text(encoding="utf-8"))
        payload_copy = json.loads((root / PAYLOAD.name).read_text(encoding="utf-8"))
        assert runtime_copy["case_order"] == payload_copy["case_order"]
        assert len(runtime_copy["cases"]) == 16
        assert all(case["payload_sha256"] for case in runtime_copy["cases"])
    assert evaluator["runtime_visibility"] == "scoring_only_after_raw_seal"
    print("PASS explicit-interface acquisition inputs do not require evaluator artifact")


if __name__ == "__main__":
    main()
