import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


sys.path.insert(0, os.fspath(Path(__file__).resolve().parents[1]))

import preflight_audition_plan


SCRIPT = Path(__file__).resolve().parents[1] / "preflight_audition_plan.py"


def write_json(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def make_inputs(tmp_path: Path) -> dict[str, Path]:
    return {
        "raw": write_json(
            tmp_path / "results.json",
            {
                "schema_version": "llm_probe.results.v1",
                "run_id": "synthetic-run",
                "generated_at": "2026-06-21T12:00:00Z",
                "observations": [],
            },
        ),
        "manifest": write_json(
            tmp_path / "preflight" / "preflight_capability_manifest.json",
            {
                "output_contract_version": "zth.llm_probe_preflight.v0.1",
                "scope": "preflight_only",
                "promotion_performed": False,
                "requires_human_review": True,
                "preflight_status": "pass",
            },
        ),
        "model": write_json(
            tmp_path / "model.json",
            {
                "model_id": "synthetic-model",
                "base_url": "http://127.0.0.1:9999/v1",
            },
        ),
        "suite": write_json(
            tmp_path / "suite.json",
            {"suite_id": "synthetic-suite"},
        ),
        "board": write_json(
            tmp_path / "board.json",
            {
                "board_id": "synthetic-board",
                "suites": ["suite.json"],
            },
        ),
    }


def build_input(
    paths: dict[str, Path],
    tmp_path: Path,
    *,
    raw: bool = False,
    board: bool = False,
    write_plan: Path | None = None,
) -> preflight_audition_plan.PlanInput:
    return preflight_audition_plan.PlanInput(
        llm_probe_output=paths["raw"] if raw else None,
        manifest=None if raw else paths["manifest"],
        model=paths["model"],
        suite=None if board else paths["suite"],
        board=paths["board"] if board else None,
        out_dir=tmp_path / "audition-output",
        write_plan=write_plan,
    )


def test_missing_model_path_fails(tmp_path: Path) -> None:
    paths = make_inputs(tmp_path)
    plan_input = build_input(paths, tmp_path)
    plan_input = preflight_audition_plan.PlanInput(
        **{**plan_input.__dict__, "model": tmp_path / "missing-model.json"}
    )

    with pytest.raises(ValueError, match="model config is not a file"):
        preflight_audition_plan.build_plan(plan_input)


def test_missing_suite_and_board_fails(tmp_path: Path) -> None:
    paths = make_inputs(tmp_path)
    plan_input = build_input(paths, tmp_path)
    plan_input = preflight_audition_plan.PlanInput(
        **{**plan_input.__dict__, "suite": None}
    )

    with pytest.raises(ValueError, match="exactly one of --suite or --board"):
        preflight_audition_plan.build_plan(plan_input)


def test_both_suite_and_board_fail(tmp_path: Path) -> None:
    paths = make_inputs(tmp_path)
    plan_input = build_input(paths, tmp_path)
    plan_input = preflight_audition_plan.PlanInput(
        **{**plan_input.__dict__, "board": paths["board"]}
    )

    with pytest.raises(ValueError, match="exactly one of --suite or --board"):
        preflight_audition_plan.build_plan(plan_input)


def test_both_raw_input_and_manifest_fail(tmp_path: Path) -> None:
    paths = make_inputs(tmp_path)
    plan_input = build_input(paths, tmp_path, raw=True)
    plan_input = preflight_audition_plan.PlanInput(
        **{**plan_input.__dict__, "manifest": paths["manifest"]}
    )

    with pytest.raises(
        ValueError,
        match="exactly one of --llm-probe-output or --manifest",
    ):
        preflight_audition_plan.build_plan(plan_input)


def test_raw_input_places_ingest_before_single_audition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = make_inputs(tmp_path)
    plan = preflight_audition_plan.build_plan(
        build_input(paths, tmp_path, raw=True)
    )

    labels = [command.label for command in plan.commands]
    ingest_index = labels.index(
        "Import LLM-probe output as preflight-only evidence"
    )
    audition_index = labels.index(
        "Run the gated single-suite audition after review"
    )
    assert ingest_index < audition_index
    assert (
        plan.manifest_path
        == Path(".work/llm_probe_preflight/results/preflight_capability_manifest.json")
    )
    audition = plan.commands[audition_index]
    assert "local_harness/run_model_audition.py" in audition.command
    assert "--preflight-manifest" in audition.command


def test_existing_manifest_skips_ingest(tmp_path: Path) -> None:
    paths = make_inputs(tmp_path)
    plan = preflight_audition_plan.build_plan(build_input(paths, tmp_path))

    commands = [command.command for command in plan.commands]
    assert not any(
        "local_harness/llm_probe_preflight_ingest.py" in command
        for command in commands
    )
    assert any(
        "local_harness/run_model_audition.py" in command
        for command in commands
    )


def test_board_mode_prints_manifest_map_and_board_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = make_inputs(tmp_path)
    plan = preflight_audition_plan.build_plan(
        build_input(paths, tmp_path, board=True)
    )

    assert plan.mode == "board"
    assert any(
        command.label == "Write reviewed board preflight manifest map"
        for command in plan.commands
    )
    board_command = next(
        command
        for command in plan.commands
        if command.label == "Run the gated board audition after review"
    )
    assert "local_harness/run_model_audition_board.py" in board_command.command
    assert "--preflight-manifest-map" in board_command.command
    assert "--preflight-manifest" not in board_command.command


def test_write_plan_creates_parents_and_markdown(tmp_path: Path) -> None:
    paths = make_inputs(tmp_path)
    plan_path = tmp_path / "plans" / "review.md"
    result = subprocess.run(
        [
            sys.executable,
            os.fspath(SCRIPT),
            "--manifest",
            os.fspath(paths["manifest"]),
            "--model",
            os.fspath(paths["model"]),
            "--suite",
            os.fspath(paths["suite"]),
            "--out-dir",
            os.fspath(tmp_path / "audition-output"),
            "--write-plan",
            os.fspath(plan_path),
            "--print-commands",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    content = plan_path.read_text(encoding="utf-8")
    assert content.startswith("# Preflight-to-Audition Operator Plan")
    assert "Status: draft review material" in content
    assert "Passing checks are evidence, not authority." in content


def test_default_cli_writes_nothing(tmp_path: Path) -> None:
    paths = make_inputs(tmp_path)
    out_dir = tmp_path / "audition-output"
    result = subprocess.run(
        [
            sys.executable,
            os.fspath(SCRIPT),
            "--manifest",
            os.fspath(paths["manifest"]),
            "--model",
            os.fspath(paths["model"]),
            "--suite",
            os.fspath(paths["suite"]),
            "--out-dir",
            os.fspath(out_dir),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert not out_dir.exists()
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "board.json",
        "model.json",
        "preflight",
        "results.json",
        "suite.json",
    ]


def test_json_output_is_deterministic(tmp_path: Path) -> None:
    paths = make_inputs(tmp_path)
    plan = preflight_audition_plan.build_plan(build_input(paths, tmp_path))

    first = preflight_audition_plan.render_json(plan)
    second = preflight_audition_plan.render_json(plan)

    assert first == second
    payload = json.loads(first)
    assert payload["schema_version"] == "zth.preflight_audition_plan.v0.1"
    assert payload["mode"] == "single-suite"
    assert payload["source_evidence"]["derived"] is False


def test_safety_notes_cover_required_boundaries(tmp_path: Path) -> None:
    paths = make_inputs(tmp_path)
    plan = preflight_audition_plan.build_plan(build_input(paths, tmp_path))
    notes = " ".join(plan.safety_notes).lower()

    assert "does not run models" in notes
    assert "does not start model endpoints" in notes
    assert "does not perform cleanup" in notes
    assert "delete .work" in notes
    assert "does not promote" in notes
    assert "evidence, not authority" in notes
