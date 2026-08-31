from __future__ import annotations

import json
from pathlib import Path

from local_harness.validate_epistemic_observation_output import load_json, validate


def test_validate_epistemic_output_passes():
    payload = {
        "conclusion": {
            "established": ["transport qualification succeeded"],
            "not_established": ["semantic capability"],
        },
        "findings": [
            {
                "claim": "transport qualification succeeded",
                "evidence": [{"path": "docs/example.md", "detail": "bounded evidence"}],
            }
        ],
        "reason": "bounded",
    }
    assert validate(payload, {"docs/example.md"}) == []


def test_validate_epistemic_output_rejects_missing_conclusion_parts():
    payload = {"conclusion": {"established": [], "not_established": []}, "findings": [], "reason": ""}
    problems = validate(payload, set())
    assert any("established" in item for item in problems)
    assert any("not_established" in item for item in problems)
    assert any("findings" in item for item in problems)
    assert any("reason" in item for item in problems)


def test_load_json_requires_object(tmp_path: Path):
    path = tmp_path / "payload.json"
    path.write_text(json.dumps([]), encoding="utf-8")
    try:
        load_json(path)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
