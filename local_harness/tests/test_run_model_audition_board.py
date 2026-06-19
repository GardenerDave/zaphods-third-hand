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


def write_preflight_manifest(path: Path, status: str) -> None:
    write_json(
        path,
        {
            "output_contract_version": "zth.llm_probe_preflight.v0.1",
            "scope": "preflight_only",
            "promotion_performed": False,
            "requires_human_review": True,
            "source_sha256": "synthetic-source-sha256",
            "source_run_id": "synthetic-preflight-run",
            "input_format": "llm_probe_verified_yaml",
            "input_schema_version": "llm_probe.verified_yaml.v1",
            "model_ids_observed": ["fake-model"],
            "probe_ids_observed": ["synthetic-probe"],
            "status_counts": {status: 1},
            "valid_record_count": 1,
            "invalid_record_count": 0,
            "preflight_status": status,
        },
    )


def write_preflight_map(
    path: Path,
    models: dict[str, str],
    *,
    schema_version: str = "zth.preflight_manifest_map.v0.1",
) -> None:
    write_json(
        path,
        {
            "schema_version": schema_version,
            "models": models,
        },
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


def config_from_map(
    tmp_path: Path,
    files: dict[str, Path],
    *,
    status: str,
    extra_args: list[str] | None = None,
) -> tuple[BoardRunConfig, Path, Path]:
    manifest_path = tmp_path / "preflight" / "preflight_capability_manifest.json"
    map_path = tmp_path / "preflight_manifest_map.json"
    write_preflight_manifest(manifest_path, status)
    write_preflight_map(
        map_path,
        {"fake-model": "preflight/preflight_capability_manifest.json"},
    )
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
            "--preflight-manifest-map",
            str(map_path),
            *(extra_args or []),
        ]
    )
    return build_board_config_from_args(args), manifest_path, map_path


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
    assert "preflight_manifest_map" not in metadata


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


def test_board_with_pass_manifest_runs_and_passes_gate_to_every_suite(
    tmp_path: Path,
) -> None:
    files = make_board_files(tmp_path)
    config, manifest_path, map_path = config_from_map(
        tmp_path,
        files,
        status="pass",
    )

    card = run_board(config, client=fake_client)

    assert card["overall"] == 1.0
    assert "preflight_status" not in card
    assert "preflight_gate" not in card
    board_metadata = load_json(config.out_dir / "board_metadata.json")
    assert board_metadata["preflight_manifest_map"]["path"] == str(
        map_path.resolve()
    )
    assert board_metadata["preflight_manifest_map"]["selected_manifest"] == str(
        manifest_path.resolve()
    )
    for suite_id in ("suite_a_v0", "suite_b_v0"):
        metadata = load_json(
            config.out_dir / "suites" / suite_id / "run_metadata.json"
        )
        assert metadata["preflight_gate"]["preflight_status"] == "pass"
        assert metadata["preflight_gate"]["basis"] == "preflight_pass"


def test_board_with_intermittent_manifest_blocks_by_default(
    tmp_path: Path,
) -> None:
    files = make_board_files(tmp_path)
    config, _, _ = config_from_map(tmp_path, files, status="intermittent")

    with pytest.raises(ValueError, match="status=intermittent"):
        run_board(config, client=fake_client)

    assert not config.out_dir.exists()


def test_board_with_intermittent_manifest_allows_explicit_override(
    tmp_path: Path,
) -> None:
    files = make_board_files(tmp_path)
    config, _, _ = config_from_map(
        tmp_path,
        files,
        status="intermittent",
        extra_args=["--allow-intermittent-preflight"],
    )

    run_board(config, client=fake_client)

    for suite_id in ("suite_a_v0", "suite_b_v0"):
        gate = load_json(
            config.out_dir / "suites" / suite_id / "run_metadata.json"
        )["preflight_gate"]
        assert gate["basis"] == "allow_intermittent_preflight"
        assert gate["overrides"]["allow_intermittent_preflight"] is True


def test_board_with_unknown_manifest_allows_explicit_override(
    tmp_path: Path,
) -> None:
    files = make_board_files(tmp_path)
    config, _, _ = config_from_map(
        tmp_path,
        files,
        status="unknown",
        extra_args=["--allow-unknown-preflight"],
    )

    run_board(config, client=fake_client)

    for suite_id in ("suite_a_v0", "suite_b_v0"):
        gate = load_json(
            config.out_dir / "suites" / suite_id / "run_metadata.json"
        )["preflight_gate"]
        assert gate["basis"] == "allow_unknown_preflight"
        assert gate["overrides"]["allow_unknown_preflight"] is True


def test_board_with_failed_manifest_blocks_without_waiver(
    tmp_path: Path,
) -> None:
    files = make_board_files(tmp_path)
    config, _, _ = config_from_map(
        tmp_path,
        files,
        status="fail",
        extra_args=[
            "--allow-intermittent-preflight",
            "--allow-unknown-preflight",
        ],
    )

    with pytest.raises(ValueError, match="status=fail"):
        run_board(config, client=fake_client)

    assert not config.out_dir.exists()


def test_board_with_failed_manifest_allows_recorded_waiver(
    tmp_path: Path,
) -> None:
    files = make_board_files(tmp_path)
    reason = "Human approved a constrained board audition."
    config, _, _ = config_from_map(
        tmp_path,
        files,
        status="fail",
        extra_args=["--waive-preflight", reason],
    )

    card = run_board(config, client=fake_client)

    assert card["overall"] == 1.0
    assert "preflight_status" not in card
    for suite_id in ("suite_a_v0", "suite_b_v0"):
        gate = load_json(
            config.out_dir / "suites" / suite_id / "run_metadata.json"
        )["preflight_gate"]
        assert gate["basis"] == "waiver"
        assert gate["overrides"]["waiver_reason"] == reason


def test_manifest_map_missing_model_fails_closed(tmp_path: Path) -> None:
    files = make_board_files(tmp_path)
    manifest_path = tmp_path / "preflight_capability_manifest.json"
    map_path = tmp_path / "preflight_manifest_map.json"
    write_preflight_manifest(manifest_path, "pass")
    write_preflight_map(map_path, {"another-model": str(manifest_path)})
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
            "--preflight-manifest-map",
            str(map_path),
        ]
    )

    with pytest.raises(ValueError, match="no entry for model"):
        build_board_config_from_args(args)

    assert not (tmp_path / "out").exists()


def test_manifest_map_can_explicitly_allow_missing_model(
    tmp_path: Path,
) -> None:
    files = make_board_files(tmp_path)
    map_path = tmp_path / "preflight_manifest_map.json"
    write_preflight_map(map_path, {})
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
            "--preflight-manifest-map",
            str(map_path),
            "--allow-missing-preflight-manifest",
        ]
    )
    config = build_board_config_from_args(args)

    run_board(config, client=fake_client)

    assert config.preflight_manifest is None
    for suite_id in ("suite_a_v0", "suite_b_v0"):
        metadata = load_json(
            config.out_dir / "suites" / suite_id / "run_metadata.json"
        )
        assert "preflight_gate" not in metadata


@pytest.mark.parametrize(
    "map_payload",
    [
        {},
        {
            "schema_version": "wrong-version",
            "models": {},
        },
        {
            "schema_version": "zth.preflight_manifest_map.v0.1",
            "models": [],
        },
        {
            "schema_version": "zth.preflight_manifest_map.v0.1",
            "models": {"fake-model": ""},
        },
        {
            "schema_version": "zth.preflight_manifest_map.v0.1",
            "models": {},
            "unexpected": True,
        },
    ],
)
def test_malformed_manifest_map_fails_closed(
    tmp_path: Path,
    map_payload: dict,
) -> None:
    files = make_board_files(tmp_path)
    map_path = tmp_path / "preflight_manifest_map.json"
    write_json(map_path, map_payload)
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
            "--preflight-manifest-map",
            str(map_path),
        ]
    )

    with pytest.raises((KeyError, ValueError), match="preflight manifest map|unsupported"):
        build_board_config_from_args(args)

    assert not (tmp_path / "out").exists()


def test_manifest_map_can_match_model_config_name(tmp_path: Path) -> None:
    files = make_board_files(tmp_path)
    model_file = tmp_path / "models" / "fake_board_model.json"
    manifest_path = tmp_path / "preflight_capability_manifest.json"
    map_path = tmp_path / "preflight_manifest_map.json"
    write_json(
        model_file,
        {
            "model_ref": "fake-board-model-ref",
            "model_id": "fake-model",
            "base_url": "http://127.0.0.1:8080/v1",
            "api_key_default": "not-needed",
        },
    )
    write_preflight_manifest(manifest_path, "pass")
    write_preflight_map(
        map_path,
        {"fake-board-model-ref": str(manifest_path)},
    )
    parser = build_arg_parser()
    args = parser.parse_args(
        [
            "--model",
            str(model_file),
            "--board",
            str(files["board"]),
            "--out-dir",
            str(tmp_path / "out"),
            "--preflight-manifest-map",
            str(map_path),
        ]
    )

    config = build_board_config_from_args(args)

    assert config.preflight_manifest == manifest_path.resolve()
    assert config.preflight_lookup_key == "fake-board-model-ref"


def test_board_preflight_override_flags_require_manifest_map(
    tmp_path: Path,
) -> None:
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
            "--allow-unknown-preflight",
        ]
    )

    with pytest.raises(ValueError, match="require --preflight-manifest-map"):
        build_board_config_from_args(args)
