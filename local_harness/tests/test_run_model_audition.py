from __future__ import annotations

import json
from pathlib import Path

import pytest

from local_harness.run_model_audition import (
    AuditionConfig,
    build_arg_parser,
    build_config_from_args,
    load_json,
    run_audition,
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


def make_audition_files(tmp_path: Path) -> dict[str, Path]:
    root = tmp_path / "auditions"

    suite = root / "suites" / "baseline_suite_v0.json"
    prompt = root / "prompts" / "json_task_v0.md"
    fixtures = root / "fixtures" / "baseline_micro_v0.jsonl"
    scorer = root / "scorers" / "json_schema_basic_v0.json"

    prompt.parent.mkdir(parents=True, exist_ok=True)
    prompt.write_text(
        "Case: {{case_id}}\n"
        "Task: {{task_type}}\n"
        "Input: {{input}}\n"
        "Expected: {{expected_json}}\n",
        encoding="utf-8",
    )

    write_jsonl(
        fixtures,
        [
            {
                "case_id": "route_001",
                "task_type": "classification",
                "input": "Classify this as hardware.",
                "expected": {"label": "hardware"},
            },
            {
                "case_id": "route_002",
                "task_type": "classification",
                "input": "Classify this as repo code.",
                "expected": {"label": "repo_code"},
            },
        ],
    )

    write_json(
        scorer,
        {
            "profile_id": "json_schema_basic_v0",
            "metrics": [
                {"id": "completed", "type": "completion", "weight": 0.10},
                {"id": "json_parse", "type": "json_parse", "weight": 0.30},
                {
                    "id": "required_keys",
                    "type": "required_keys",
                    "weight": 0.30,
                    "keys": ["label"],
                },
                {
                    "id": "expected_field_match",
                    "type": "expected_field_match",
                    "weight": 0.30,
                },
            ],
        },
    )

    write_json(
        suite,
        {
            "suite_id": "baseline_suite_v0",
            "prompt_file": "../prompts/json_task_v0.md",
            "fixtures_file": "../fixtures/baseline_micro_v0.jsonl",
            "scorer_profile": "../scorers/json_schema_basic_v0.json",
            "defaults": {
                "temperature": 0,
                "max_tokens": 300,
                "timeout_seconds": 900,
            },
        },
    )

    return {
        "suite": suite,
        "prompt": prompt,
        "fixtures": fixtures,
        "scorer": scorer,
    }


def fake_client(request_body: dict, runtime_config: dict) -> dict:
    content = request_body["messages"][0]["content"]
    label = "repo_code" if "repo code" in content else "hardware"

    return {
        "choices": [
            {
                "message": {
                    "content": json.dumps({"label": label}),
                }
            }
        ]
    }


def config_for(
    tmp_path: Path,
    files: dict[str, Path],
    out_dir: Path | None = None,
) -> AuditionConfig:
    return AuditionConfig(
        run_id="test_run",
        model_id="fake-model",
        base_url="http://127.0.0.1:8080/v1",
        api_key="not-needed",
        suite_id="baseline_suite_v0",
        suite_file=files["suite"],
        prompt_file=files["prompt"],
        fixtures_file=files["fixtures"],
        scorer_profile=files["scorer"],
        temperature=0,
        max_tokens=300,
        timeout_seconds=900,
        out_dir=out_dir or tmp_path / "out",
    )


def test_load_suite_resolves_relative_paths(tmp_path: Path) -> None:
    files = make_audition_files(tmp_path)
    parser = build_arg_parser()
    args = parser.parse_args(
        [
            "--model-id",
            "fake-model",
            "--base-url",
            "http://127.0.0.1:8080/v1",
            "--suite",
            str(files["suite"]),
            "--out-dir",
            str(tmp_path / "out"),
        ]
    )

    config = build_config_from_args(args)

    assert config.prompt_file == files["prompt"].resolve()
    assert config.fixtures_file == files["fixtures"].resolve()
    assert config.scorer_profile == files["scorer"].resolve()
    assert config.max_tokens == 300


def test_cli_overrides_suite_paths(tmp_path: Path) -> None:
    files = make_audition_files(tmp_path)
    override_prompt = tmp_path / "override_prompt.md"
    override_prompt.write_text("Override {{input}}", encoding="utf-8")

    parser = build_arg_parser()
    args = parser.parse_args(
        [
            "--model-id",
            "fake-model",
            "--base-url",
            "http://127.0.0.1:8080/v1",
            "--suite",
            str(files["suite"]),
            "--prompt-file",
            str(override_prompt),
            "--temperature",
            "0.7",
            "--max-tokens",
            "123",
            "--timeout-seconds",
            "45",
            "--out-dir",
            str(tmp_path / "out"),
        ]
    )

    config = build_config_from_args(args)

    assert config.prompt_file == override_prompt.resolve()
    assert config.temperature == 0.7
    assert config.max_tokens == 123
    assert config.timeout_seconds == 45


def test_runner_writes_metadata(tmp_path: Path) -> None:
    files = make_audition_files(tmp_path)
    config = config_for(tmp_path, files)

    run_audition(config, client=fake_client)

    metadata = load_json(config.out_dir / "run_metadata.json")
    assert metadata["run_id"] == "test_run"
    assert metadata["model_id"] == "fake-model"
    assert metadata["suite_id"] == "baseline_suite_v0"
    assert metadata["runner"] == "local_harness/run_model_audition.py"


def test_runner_writes_case_manifest(tmp_path: Path) -> None:
    files = make_audition_files(tmp_path)
    config = config_for(tmp_path, files)

    run_audition(config, client=fake_client)

    rows = [
        json.loads(line)
        for line in (config.out_dir / "case_manifest.jsonl").read_text().splitlines()
    ]

    assert [row["case_id"] for row in rows] == ["route_001", "route_002"]
    assert all(row["status"] == "completed" for row in rows)


def test_runner_writes_raw_output(tmp_path: Path) -> None:
    files = make_audition_files(tmp_path)
    config = config_for(tmp_path, files)

    run_audition(config, client=fake_client)

    raw = load_json(config.out_dir / "raw_outputs" / "route_001.json")

    assert raw["case_id"] == "route_001"
    assert raw["request"]["model"] == "fake-model"
    assert json.loads(raw["text"])["label"] == "hardware"


def test_runner_writes_score_file(tmp_path: Path) -> None:
    files = make_audition_files(tmp_path)
    config = config_for(tmp_path, files)

    run_audition(config, client=fake_client)

    score = load_json(config.out_dir / "scores" / "route_001.json")

    assert score["case_id"] == "route_001"
    assert score["overall"] == 1.0
    assert score["failure_modes"] == []


def test_runner_writes_capability_card(tmp_path: Path) -> None:
    files = make_audition_files(tmp_path)
    config = config_for(tmp_path, files)

    card = run_audition(config, client=fake_client)

    written = load_json(config.out_dir / "capability_card.json")

    assert written == card
    assert written["case_count"] == 2
    assert written["completed_count"] == 2
    assert written["failed_count"] == 0
    assert written["overall"] == 1.0
    assert (config.out_dir / "capability_card.md").exists()


def test_resume_skips_existing_case(tmp_path: Path) -> None:
    files = make_audition_files(tmp_path)
    out_dir = tmp_path / "out"
    config = config_for(tmp_path, files, out_dir=out_dir)

    run_audition(config, client=fake_client)

    resumed_config = AuditionConfig(**{**config.__dict__, "resume": True})
    run_audition(resumed_config, client=fake_client)

    rows = [
        json.loads(line)
        for line in (out_dir / "case_manifest.jsonl").read_text().splitlines()
    ]

    assert rows[-2]["status"] == "skipped_existing"
    assert rows[-1]["status"] == "skipped_existing"


def test_non_empty_out_dir_without_resume_refuses(tmp_path: Path) -> None:
    files = make_audition_files(tmp_path)
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "existing.txt").write_text("keep", encoding="utf-8")

    config = config_for(tmp_path, files, out_dir=out_dir)

    with pytest.raises(FileExistsError):
        run_audition(config, client=fake_client)


def test_limit_and_case_id_filter(tmp_path: Path) -> None:
    files = make_audition_files(tmp_path)
    base = config_for(tmp_path, files)
    config = AuditionConfig(
        **{
            **base.__dict__,
            "case_id": "route_002",
            "limit": 1,
        }
    )

    run_audition(config, client=fake_client)

    rows = [
        json.loads(line)
        for line in (config.out_dir / "case_manifest.jsonl").read_text().splitlines()
    ]

    assert len(rows) == 1
    assert rows[0]["case_id"] == "route_002"
