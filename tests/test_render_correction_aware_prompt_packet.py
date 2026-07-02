from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness" / "render_correction_aware_prompt_packet.py"
CARD = ROOT / "docs" / "behavior_correction_cards" / "file_scope_hold_out_v1.json"


def run_script(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def make_scaffold(tmp_path: Path, ids: list[str] | None = None, *, auto_assigned: bool = False, packet_level_only: bool = True) -> Path:
    ids = ["file_scope_hold_out_v1"] if ids is None else ids
    card = json.loads(CARD.read_text(encoding="utf-8"))
    scaffold = {
        "report_type": "behavior_correction_scaffold.v1",
        "behavior_corrections": ids,
        "corrections": [card] if ids else [],
        "correction_count": len(ids),
        "packet_level_only": packet_level_only,
        "auto_assigned": auto_assigned,
        "model_inference_performed": False,
        "training_performed": False,
        "delta_written": False,
        "patched_model_materialized": False,
        "promotion_authorized": False,
        "automatic_failure_curriculum_capture_authorized": False,
    }
    path = tmp_path / "scaffold.json"
    path.write_text(json.dumps(scaffold, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def make_packet(tmp_path: Path, ids: list[str] | None = None) -> Path:
    payload = {
        "packet_id": "job-001",
        "task_summary": "Choose only docs/README.md as allowed, hold docs/ROADMAP.md out.",
        "allowed_files": ["docs/README.md"],
        "requested_targets": ["docs/README.md", "docs/ROADMAP.md"],
        "expected_output_shape": "explicit allowed_targets/held_targets split",
        "notes": [
            "docs/README.md is explicitly authorized.",
            "docs/ROADMAP.md is plausible but not authorized and should be held out.",
        ],
        "behavior_corrections": ["file_scope_hold_out_v1"] if ids is None else ids,
    }
    path = tmp_path / "packet.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def test_help():
    assert run_script("--help").returncode == 0


def test_renders_assigned_packet(tmp_path: Path):
    packet = make_packet(tmp_path)
    scaffold = make_scaffold(tmp_path)
    out = tmp_path / "out"
    result = run_script("--job-packet", packet, "--correction-scaffold", scaffold, "--out-dir", out)
    assert result.returncode == 0, result.stderr
    payload = json.loads((out / "correction_aware_prompt_packet.json").read_text(encoding="utf-8"))
    assert payload["report_type"] == "correction_aware_prompt_packet.v1"
    assert payload["auto_assigned_corrections"] is False
    assert payload["packet_level_only"] is True
    assert payload["model_inference_performed"] is False
    assert payload["training_performed"] is False
    assert payload["delta_written"] is False
    assert payload["patched_model_materialized"] is False
    assert payload["promotion_authorized"] is False
    assert payload["automatic_failure_curriculum_capture_authorized"] is False
    assert payload["behavior_corrections"] == ["file_scope_hold_out_v1"]
    assert payload["packet_notes"] == [
        "docs/README.md is explicitly authorized.",
        "docs/ROADMAP.md is plausible but not authorized and should be held out.",
    ]
    assert "concrete_decision_facts" in payload
    assert payload["output_contract"]["install_authorized"] == "must be false"
    md = (out / "correction_aware_prompt_packet.md").read_text(encoding="utf-8")
    assert "Concrete decision facts" in md
    assert "docs/README.md is explicitly allowed" in md
    assert "docs/ROADMAP.md is requested/plausible but not authorized" in md
    assert "docs/ROADMAP.md must be held out" in md
    assert "scope_expansion_required should be true when requested targets exceed allowed_files" in md
    assert "docs/README.md is explicitly authorized." in md
    assert "docs/ROADMAP.md is plausible but not authorized and should be held out." in md
    assert "Hold out adjacent and unauthorized files explicitly" in md
    assert "does not authorize scope expansion" in md
    assert "allowed_targets: array of explicitly allowed files selected for the task" in md
    assert "held_targets: array of plausible/requested files not authorized by allowed_files" in md


def test_mismatch_fails(tmp_path: Path):
    packet = make_packet(tmp_path, ids=[])
    scaffold = make_scaffold(tmp_path, ids=["file_scope_hold_out_v1"])
    out = tmp_path / "out"
    result = run_script("--job-packet", packet, "--correction-scaffold", scaffold, "--out-dir", out)
    assert result.returncode != 0


def test_auto_assigned_fails(tmp_path: Path):
    packet = make_packet(tmp_path)
    scaffold = make_scaffold(tmp_path, auto_assigned=True)
    result = run_script("--job-packet", packet, "--correction-scaffold", scaffold, "--out-dir", tmp_path / "out")
    assert result.returncode != 0


def test_packet_level_only_false_fails(tmp_path: Path):
    packet = make_packet(tmp_path)
    scaffold = make_scaffold(tmp_path, packet_level_only=False)
    result = run_script("--job-packet", packet, "--correction-scaffold", scaffold, "--out-dir", tmp_path / "out")
    assert result.returncode != 0


def test_no_corrections_supported(tmp_path: Path):
    packet = make_packet(tmp_path, ids=[])
    scaffold = make_scaffold(tmp_path, ids=[])
    out = tmp_path / "out"
    result = run_script("--job-packet", packet, "--correction-scaffold", scaffold, "--out-dir", out)
    assert result.returncode == 0, result.stderr
    payload = json.loads((out / "correction_aware_prompt_packet.json").read_text(encoding="utf-8"))
    assert payload["behavior_corrections"] == []
    assert payload["auto_assigned_corrections"] is False
    assert "_No correction cards assigned._" in (out / "correction_aware_prompt_packet.md").read_text(encoding="utf-8")


def test_expected_output_shape_is_rendered_as_contract(tmp_path: Path):
    packet = make_packet(tmp_path)
    scaffold = make_scaffold(tmp_path)
    out = tmp_path / "out"
    result = run_script("--job-packet", packet, "--correction-scaffold", scaffold, "--out-dir", out)
    assert result.returncode == 0, result.stderr
    md = (out / "correction_aware_prompt_packet.md").read_text(encoding="utf-8")
    assert "allowed_targets: array of explicitly allowed files selected for the task" in md
    assert "held_targets: array of plausible/requested files not authorized by allowed_files" in md
    assert "scope_expansion_required: boolean, true when requested/candidate targets exceed allowed_files" in md
    assert "allowed_targets: []" not in md
    assert "held_targets: []" not in md
    assert "scope_expansion_required: false" not in md
