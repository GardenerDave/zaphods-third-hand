from __future__ import annotations

import json
from pathlib import Path

import pytest

from local_harness.run_model_audition import load_json
from local_harness.run_model_audition_board import (
    BoardRunConfig,
    build_arg_parser,
    build_board_config_from_args,
    run_board,
)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def make_suite(root: Path, suite_id: str, case_id: str) -> Path:
    prompt = root / "prompts" / f"{suite_id}.md"
    fixtures = root / "fixtures" / f"{suite_id}.jsonl"
    scorer = root / "scorers" / f"{suite_id}.json"
    suite = root / "suites" / f"{suite_id}.json"

    prompt.parent.mkdir(parents=True, exist_ok=True)
    prompt.write_text("Input: {{input}}\nMetadata: {{metadata_json}}\n", encoding="utf-8")

    write_jsonl(
        fixtures,
        [
            {
                "case_id": case_id,
                "task_type": "routing",
                "input": "Classify this hardware task.",
                "expected": {"label": "hardware"},
                "metadata": {"labels": ["hardware", "repo_code"]},
            }
        ],
    )

    write_json(
        scorer,
        {
            "profile_id": f"{suite_id}_scorer",
            "metrics": [
                {"id": "completed", "type": "completion", "weight": 0.1},
                {"id": "json_parse", "type": "json_parse", "weight": 0.2},
                {
                    "id": "expected_field_match",
                    "type": "expected_field_match",
                    "weight": 0.7,
                },
            ],
        },
    )

    write_json(
        suite,
        {
            "suite_id": suite_id,
            "prompt_file": f"../prompts/{suite_id}.md",
            "fixtures_file": f"../fixtures/{suite_id}.jsonl",
            "scorer_profile": f"../scorers/{suite_id}.json",
            "defaults": {
                "temperature": 0,
                "max_tokens": 300,
                "timeout_seconds": 900,
            },
        },
    )

    return suite


def make_board_files(tmp_path: Path) -> dict[str, Path]:
    root = tmp_path / "auditions"
    suite_a = make_suite(root, "suite_a_v0", "case_a_001")
    suite_b = make_suite(root, "suite_b_v0", "case_b_001")
    board = root / "boards" / "local_test_board_v0.json"

    write_json(
        board,
        {
            "board_id": "local_test_board_v0",
            "description": "Test board.",
            "suites": [
                "../suites/suite_a_v0.json",
                "../suites/suite_b_v0.json",
            ],
            "defaults": {
                "temperature": 0,
                "max_tokens": 123,
                "timeout_seconds": 45,
            },
        },
    )

    return {
        "root": root,
        "board": board,
        "suite_a": suite_a,
        "suite_b": suite_b,
    }


def fake_client(request_body: dict, runtime_config: dict) -> dict:
    return {
        "choices": [
            {
                "message": {
                    "content": json.dumps({"label": "hardware"}),
                }
            }
        ]
    }


def config_for(tmp_path: Path, files: dict[str, Path]) -> BoardRunConfig:
    return BoardRunConfig(
        run_id="test_board_run",
        board_id="local_test_board_v0",
        board_file=files["board"],
        suite_files=[files["suite_a"], files["suite_b"]],
        model_id="fake-model",
        base_url="http://127.0.0.1:8080/v1",
        api_key="not-needed",
        out_dir=tmp_path / "out",
        temperature=0,
        max_tokens=123,
        timeout_seconds=45,
    )


def test_board_loads_suites(tmp_path: Path) -> None:
    files = make_board_files(tmp_path)
    parser = build_arg_parser()
    args = parser.parse_args(
        [
            "--model-id",
            "fake-model",
            "--base-url",
            "http://127.0.0.1:8080/v1",
            "--board",
            str(files["board"]),
            "--out-dir",
            str(tmp_path / "out"),
        ]
    )

    config = build_board_config_from_args(args)

    assert config.board_id == "local_test_board_v0"
    assert len(config.suite_files) == 2


def test_board_resolves_relative_suite_paths(tmp_path: Path) -> None:
    files = make_board_files(tmp_path)
    parser = build_arg_parser()
    args = parser.parse_args(
        [
            "--model-id",
            "fake-model",
            "--base-url",
            "http://127.0.0.1:8080/v1",
            "--board",
            str(files["board"]),
            "--out-dir",
            str(tmp_path / "out"),
        ]
    )

    config = build_board_config_from_args(args)

    assert config.suite_files[0] == files["suite_a"].resolve()
    assert config.suite_files[1] == files["suite_b"].resolve()


def test_board_runs_multiple_suites_with_fake_client(tmp_path: Path) -> None:
    files = make_board_files(tmp_path)
    config = config_for(tmp_path, files)

    card = run_board(config, client=fake_client)

    assert card["overall"] == 1.0
    assert card["suite_scores"] == {
        "suite_a_v0": 1.0,
        "suite_b_v0": 1.0,
    }
    assert (config.out_dir / "suites" / "suite_a_v0" / "capability_card.json").exists()
    assert (config.out_dir / "suites" / "suite_b_v0" / "capability_card.json").exists()


def test_board_writes_metadata(tmp_path: Path) -> None:
    files = make_board_files(tmp_path)
    config = config_for(tmp_path, files)

    run_board(config, client=fake_client)

    metadata = load_json(config.out_dir / "board_metadata.json")

    assert metadata["run_id"] == "test_board_run"
    assert metadata["board_id"] == "local_test_board_v0"
    assert metadata["model_id"] == "fake-model"
    assert metadata["suite_count"] == 2


def test_board_writes_manifest(tmp_path: Path) -> None:
    files = make_board_files(tmp_path)
    config = config_for(tmp_path, files)

    run_board(config, client=fake_client)

    rows = [
        json.loads(line)
        for line in (config.out_dir / "board_manifest.jsonl").read_text().splitlines()
    ]

    assert [row["suite_id"] for row in rows] == ["suite_a_v0", "suite_b_v0"]
    assert all(row["status"] == "completed" for row in rows)
    assert all(row["overall"] == 1.0 for row in rows)


def test_board_writes_board_capability_card(tmp_path: Path) -> None:
    files = make_board_files(tmp_path)
    config = config_for(tmp_path, files)

    card = run_board(config, client=fake_client)
    written = load_json(config.out_dir / "board_capability_card.json")

    assert written == card
    assert written["board_id"] == "local_test_board_v0"
    assert written["model_id"] == "fake-model"
    assert written["role_fit"]["status"] == "not_evaluated"
    assert (config.out_dir / "board_capability_card.md").exists()


def test_board_resume_skips_completed_suite(tmp_path: Path) -> None:
    files = make_board_files(tmp_path)
    config = config_for(tmp_path, files)

    run_board(config, client=fake_client)

    resumed_config = BoardRunConfig(**{**config.__dict__, "resume": True})
    run_board(resumed_config, client=fake_client)

    rows = [
        json.loads(line)
        for line in (config.out_dir / "board_manifest.jsonl").read_text().splitlines()
    ]

    assert rows[-2]["status"] == "skipped_existing"
    assert rows[-1]["status"] == "skipped_existing"


def test_board_refuses_non_empty_out_dir_without_resume(tmp_path: Path) -> None:
    files = make_board_files(tmp_path)
    config = config_for(tmp_path, files)

    config.out_dir.mkdir()
    (config.out_dir / "existing.txt").write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError):
        run_board(config, client=fake_client)
