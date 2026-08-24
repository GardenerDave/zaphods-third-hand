#!/usr/bin/env python3
"""Evaluator-free acquisition-input projection for the V2 calibration."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_acquisition_inputs(
    freeze_path: Path,
    runtime_manifest_path: Path,
    payload_manifest_path: Path,
) -> list[dict[str, Any]]:
    """Load only frozen acquisition inputs; never opens evaluator records."""
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    runtime = json.loads(runtime_manifest_path.read_text(encoding="utf-8"))
    payload = json.loads(payload_manifest_path.read_text(encoding="utf-8"))
    expected = freeze["artifact_hashes"]
    assert _sha_file(runtime_manifest_path) == expected["runtime_manifest"]
    assert _sha_file(payload_manifest_path) == expected["payload_manifest"]
    assert runtime["case_order"] == payload["case_order"]
    payload_by_id = {case["case_id"]: case for case in payload["cases"]}
    inputs: list[dict[str, Any]] = []
    for ordinal, case in enumerate(runtime["cases"], 1):
        payload_case = payload_by_id[case["case_id"]]
        message = payload_case["supplier_message_text"]
        message_hash = hashlib.sha256(message.encode("utf-8")).hexdigest()
        assert message_hash == payload_case["supplier_message_sha256"] == case["supplier_message_sha256"]
        for supplier_id in runtime["supplier_arms"]:
            inputs.append({
                "ordinal": ordinal,
                "case_id": case["case_id"],
                "supplier_id": supplier_id,
                "capability_family": case["capability_family"],
                "interface_id": case["interface_id"],
                "interface_hash": case["interface_hash"],
                "supplier_message_text": message,
                "supplier_message_sha256": message_hash,
                "authority_context": case["authority_context"],
            })
    return inputs
