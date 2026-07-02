from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "docs" / "behavior_correction_cards" / "file_scope_hold_out_v1.json"
VALIDATOR = ROOT / "local_harness" / "validate_behavior_correction_cards.py"


def run_validator(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(VALIDATOR), str(path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_example_card_validates():
    result = run_validator(CARD)
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_missing_required_field_fails(tmp_path: Path):
    card = json.loads(CARD.read_text(encoding="utf-8"))
    card.pop("validator_expectations")
    path = tmp_path / "missing.json"
    path.write_text(json.dumps(card), encoding="utf-8")
    result = run_validator(path)
    assert result.returncode != 0
    assert "missing required field: validator_expectations" in result.stderr


def test_non_authorities_required(tmp_path: Path):
    card = json.loads(CARD.read_text(encoding="utf-8"))
    card.pop("non_authorities")
    path = tmp_path / "missing_non_auth.json"
    path.write_text(json.dumps(card), encoding="utf-8")
    result = run_validator(path)
    assert result.returncode != 0
    assert "missing required field: non_authorities" in result.stderr
