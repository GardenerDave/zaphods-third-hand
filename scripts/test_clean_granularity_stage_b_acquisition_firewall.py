#!/usr/bin/env python3
"""Model-free regression: acquisition input construction needs no evaluator."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import clean_granularity_replication_stage_b_execute as harness


def main() -> None:
    # Full scoring-hash verification is a preflight responsibility.  After it
    # succeeds, acquisition input construction is tested with scoring-only
    # artifacts absent.
    harness.preflight()
    with tempfile.TemporaryDirectory(prefix="stageb-firewall-") as directory:
        root = Path(directory)
        freeze = root / "freeze.json"
        runtime = root / "runtime.json"
        payload = root / "payload.json"
        shutil.copy2(harness.FREEZE, freeze)
        shutil.copy2(harness.RUNTIME, runtime)
        shutil.copy2(harness.PAYLOADS, payload)
        original = (harness.FREEZE, harness.RUNTIME, harness.PAYLOADS)
        harness.FREEZE, harness.RUNTIME, harness.PAYLOADS = freeze, runtime, payload
        try:
            harness.load_inputs()
        finally:
            harness.FREEZE, harness.RUNTIME, harness.PAYLOADS = original
    print("PASS evaluator/scoring artifacts may be absent during acquisition input construction")


if __name__ == "__main__":
    main()
