from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness" / "render_behavior_correction_scaffold.py"
CARD = ROOT / "docs" / "behavior_correction_cards" / "file_scope_hold_out_v1.json"


def run_renderer(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def packet_with_corrections(tmp_path: Path, ids: list[str] | None = None) -> Path:
    payload = {
        "packet_name": "job-packet",
        "behavior_corrections": ids if ids is not None else ["file_scope_hold_out_v1"],
    }
    path = tmp_path / "packet.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def test_renderer_help():
    result = run_renderer("--help")
    assert result.returncode == 0


def test_renderer_requires_packet(tmp_path: Path):
    result = run_renderer("--packet", tmp_path / "missing.json", "--out-dir", tmp_path / "out")
    assert result.returncode != 0


def test_renderer_renders_assigned_card(tmp_path: Path):
    packet = packet_with_corrections(tmp_path)
    out = tmp_path / "out"
    result = run_renderer("--packet", packet, "--out-dir", out)
    assert result.returncode == 0, result.stderr
    payload = json.loads((out / "behavior_correction_scaffold.json").read_text(encoding="utf-8"))
    assert payload["behavior_corrections"] == ["file_scope_hold_out_v1"]
    assert payload["auto_assigned"] is False
    assert payload["model_inference_performed"] is False
    assert payload["training_performed"] is False
    assert payload["delta_written"] is False
    assert payload["patched_model_materialized"] is False
    assert payload["promotion_authorized"] is False
    assert payload["automatic_failure_curriculum_capture_authorized"] is False
    assert payload["corrections"][0]["non_authorities"]


def test_renderer_no_corrections_is_explicit(tmp_path: Path):
    packet = packet_with_corrections(tmp_path, ids=[])
    out = tmp_path / "out"
    result = run_renderer("--packet", packet, "--out-dir", out)
    assert result.returncode == 0, result.stderr
    payload = json.loads((out / "behavior_correction_scaffold.json").read_text(encoding="utf-8"))
    assert payload["correction_count"] == 0
    assert payload["auto_assigned"] is False


def test_missing_correction_id_fails(tmp_path: Path):
    packet = packet_with_corrections(tmp_path, ids=["missing_card"])
    result = run_renderer("--packet", packet, "--out-dir", tmp_path / "out")
    assert result.returncode != 0


def test_invalid_correction_card_fails(tmp_path: Path):
    bad_card = tmp_path / "docs" / "behavior_correction_cards"
    bad_card.mkdir(parents=True)
    (bad_card / "file_scope_hold_out_v1.json").write_text("{}", encoding="utf-8")
    packet = packet_with_corrections(tmp_path)
    result = subprocess.run(
        ["python3", str(SCRIPT), "--packet", str(packet), "--out-dir", str(tmp_path / "out")],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0

