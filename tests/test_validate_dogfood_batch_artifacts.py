from __future__ import annotations

import json
from pathlib import Path

import pytest

from local_harness.validate_dogfood_batch_artifacts import validate_dogfood_batch_artifacts
from scripts.overnight_queue_authority import AuthorityValidationError, load_registry, load_stage_definitions, render_queue_template, validate_allowed_targets


def _write_queue(path: Path, rows: list[tuple[str, str, str]]) -> None:
    lines = ["# priority\tslug\tdescription"]
    lines.extend("\t".join(row) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_queue_v2(path: Path, rows: list[tuple[str, str, str, list[str]]]) -> None:
    lines = ["# zth-roadmap-queue-schema: 2"]
    lines.extend("\t".join((priority, slug, description, json.dumps(targets))) for priority, slug, description, targets in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_state(path: Path, rows: list[tuple[str, str, str, str]]) -> None:
    lines = ["# timestamp\tslug\tstatus\trun_dir"]
    lines.extend("\t".join(row) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_run(run_dir: Path, *, raw_output: object = None, content: object = None) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "stage_packet.md").write_text("# packet\n", encoding="utf-8")
    (run_dir / "model_output.redacted.json").write_text('{"redacted": true}\n', encoding="utf-8")
    if raw_output is None:
        raw_output = {"allowed_targets": [], "held_targets": [], "reason": "ok"}
    if content is None:
        content = {
            "task_summary": "ok",
            "repo_observations": [],
            "allowed_targets": [],
            "held_targets": [],
            "proposed_next_action": "ok",
            "validation_plan": [],
            "reason": "ok",
        }
    (run_dir / "model_output.raw.json").write_text(json.dumps(raw_output) + "\n", encoding="utf-8")
    (run_dir / "model_content.json").write_text(json.dumps(content) + "\n", encoding="utf-8")


def _write_partial_content_run(run_dir: Path, *, content: object) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "stage_packet.md").write_text("# packet\n", encoding="utf-8")
    (run_dir / "model_output.raw.json").write_text(
        '{"allowed_targets": [], "held_targets": [], "reason": "ok"}\n',
        encoding="utf-8",
    )
    (run_dir / "model_output.redacted.json").write_text('{"redacted": true}\n', encoding="utf-8")
    (run_dir / "model_content.json").write_text(json.dumps(content) + "\n", encoding="utf-8")


def _make_paths(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    queue = tmp_path / "roadmap_queue.tsv"
    state = tmp_path / "state.tsv"
    runs_dir = tmp_path / "runs"
    stage_log = tmp_path / "stage.log"
    return queue, state, runs_dir, stage_log


def test_valid_completed_prefix(tmp_path: Path) -> None:
    queue, state, runs_dir, stage_log = _make_paths(tmp_path)
    _write_queue(
        queue,
        [
            ("1", "alpha", "A"),
            ("2", "beta", "B"),
            ("3", "gamma", "C"),
        ],
    )
    _write_state(
        state,
        [
            ("2026-07-16T00:00:00Z", "alpha", "packet_generated", "alpha"),
            ("2026-07-16T00:01:00Z", "beta", "packet_generated", "beta"),
        ],
    )
    _write_run(runs_dir / "alpha")
    _write_run(runs_dir / "beta")
    stage_log.write_text("No remaining dogfood stages.\n", encoding="utf-8")

    result = validate_dogfood_batch_artifacts(
        queue_path=queue,
        state_path=state,
        runs_dir=runs_dir,
        stage_log_path=stage_log,
    )

    assert result["validation_status"] == "passed"
    assert result["queue_total"] == 3
    assert result["completed_total"] == 2
    assert result["remaining_total"] == 1
    assert result["duplicate_state_slugs"] == []
    assert result["order_mismatches"] == []
    assert result["missing_artifacts"] == []
    assert result["json_errors"] == []
    assert result["exhaustion_visible"] is True


def test_full_valid_completion_with_exhaustion_visible(tmp_path: Path) -> None:
    queue, state, runs_dir, stage_log = _make_paths(tmp_path)
    _write_queue(queue, [("1", "alpha", "A"), ("2", "beta", "B")])
    _write_state(
        state,
        [
            ("2026-07-16T00:00:00Z", "alpha", "packet_generated", "alpha"),
            ("2026-07-16T00:01:00Z", "beta", "packet_generated", "beta"),
        ],
    )
    _write_run(runs_dir / "alpha")
    _write_run(runs_dir / "beta")
    stage_log.write_text("No remaining dogfood stages.\n", encoding="utf-8")

    result = validate_dogfood_batch_artifacts(
        queue_path=queue,
        state_path=state,
        runs_dir=runs_dir,
        stage_log_path=stage_log,
    )

    assert result["validation_status"] == "passed"
    assert result["exhaustion_visible"] is True


def test_schema_2_queue_is_accepted(tmp_path: Path) -> None:
    queue, state, runs_dir, stage_log = _make_paths(tmp_path)
    _write_queue_v2(
        queue,
        [
            ("1", "alpha", "A", ["docs/ROADMAP.md"]),
            ("2", "beta", "B", ["docs/reports/model_auditions/README.md"]),
        ],
    )
    _write_state(
        state,
        [
            ("2026-07-16T00:00:00Z", "alpha", "packet_generated", "alpha"),
            ("2026-07-16T00:01:00Z", "beta", "packet_generated", "beta"),
        ],
    )
    _write_run(runs_dir / "alpha")
    _write_run(runs_dir / "beta")
    stage_log.write_text("No remaining dogfood stages.\n", encoding="utf-8")
    result = validate_dogfood_batch_artifacts(queue_path=queue, state_path=state, runs_dir=runs_dir, stage_log_path=stage_log)
    assert result["validation_status"] == "passed"
    assert result["queue_total"] == 2


def test_schema_1_and_schema_2_are_distinct(tmp_path: Path) -> None:
    queue, state, runs_dir, stage_log = _make_paths(tmp_path)
    _write_queue(queue, [("1", "alpha", "A")])
    _write_state(state, [("2026-07-16T00:00:00Z", "alpha", "packet_generated", "alpha")])
    _write_run(runs_dir / "alpha")
    stage_log.write_text("No remaining dogfood stages.\n", encoding="utf-8")
    legacy = validate_dogfood_batch_artifacts(queue_path=queue, state_path=state, runs_dir=runs_dir, stage_log_path=stage_log)
    assert legacy["validation_status"] == "passed"
    _write_queue_v2(queue, [("1", "alpha", "A", ["docs/ROADMAP.md"])])
    schema2 = validate_dogfood_batch_artifacts(queue_path=queue, state_path=state, runs_dir=runs_dir, stage_log_path=stage_log)
    assert schema2["validation_status"] == "passed"


@pytest.mark.parametrize(
    "value, error",
    [
        ({"not": "a list"}, "authority_not_array"),
        ([], "empty_authority"),
        ([""], "empty_or_whitespace_target"),
        (["   "], "empty_or_whitespace_target"),
        (["/abs/path"], "absolute_target"),
        (["../escape"], "traversal_target"),
        (["docs/ROADMAP.md", "docs/ROADMAP.md"], "duplicate_target"),
        ([1], "authority_not_string"),
    ],
)
def test_validate_allowed_targets_rejects_invalid_values(value, error):
    with pytest.raises(AuthorityValidationError) as excinfo:
        validate_allowed_targets(value)
    assert error in str(excinfo.value)


def test_duplicate_state_slug(tmp_path: Path) -> None:
    queue, state, runs_dir, stage_log = _make_paths(tmp_path)
    _write_queue(queue, [("1", "alpha", "A"), ("2", "beta", "B")])
    _write_state(
        state,
        [
            ("2026-07-16T00:00:00Z", "alpha", "packet_generated", "alpha"),
            ("2026-07-16T00:01:00Z", "alpha", "packet_generated", "alpha_dup"),
        ],
    )
    _write_run(runs_dir / "alpha")
    _write_run(runs_dir / "alpha_dup")

    result = validate_dogfood_batch_artifacts(
        queue_path=queue,
        state_path=state,
        runs_dir=runs_dir,
        stage_log_path=stage_log,
    )

    assert result["validation_status"] == "failed"
    assert result["duplicate_state_slugs"] == ["alpha"]


def test_queue_state_order_mismatch(tmp_path: Path) -> None:
    queue, state, runs_dir, stage_log = _make_paths(tmp_path)
    _write_queue(queue, [("1", "alpha", "A"), ("2", "beta", "B")])
    _write_state(
        state,
        [
            ("2026-07-16T00:00:00Z", "beta", "packet_generated", "beta"),
            ("2026-07-16T00:01:00Z", "alpha", "packet_generated", "alpha"),
        ],
    )
    _write_run(runs_dir / "alpha")
    _write_run(runs_dir / "beta")

    result = validate_dogfood_batch_artifacts(
        queue_path=queue,
        state_path=state,
        runs_dir=runs_dir,
        stage_log_path=stage_log,
    )

    assert result["validation_status"] == "failed"
    assert result["order_mismatches"]
    assert result["order_mismatches"][0]["expected_slug"] == "alpha"
    assert result["order_mismatches"][0]["actual_slug"] == "beta"


def test_missing_artifact(tmp_path: Path) -> None:
    queue, state, runs_dir, stage_log = _make_paths(tmp_path)
    _write_queue(queue, [("1", "alpha", "A")])
    _write_state(state, [("2026-07-16T00:00:00Z", "alpha", "packet_generated", "alpha")])
    run_dir = runs_dir / "alpha"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "stage_packet.md").write_text("# packet\n", encoding="utf-8")
    (run_dir / "model_output.raw.json").write_text('{"allowed_targets": []}\n', encoding="utf-8")
    (run_dir / "model_output.redacted.json").write_text('{"redacted": true}\n', encoding="utf-8")

    result = validate_dogfood_batch_artifacts(
        queue_path=queue,
        state_path=state,
        runs_dir=runs_dir,
        stage_log_path=stage_log,
    )

    assert result["validation_status"] == "failed"
    assert result["missing_artifacts"]
    assert result["missing_artifacts"][0]["missing"] == ["model_content.json"]


def test_missing_raw_or_redacted_artifact(tmp_path: Path) -> None:
    queue, state, runs_dir, stage_log = _make_paths(tmp_path)
    _write_queue(queue, [("1", "alpha", "A"), ("2", "beta", "B")])
    _write_state(
        state,
        [
            ("2026-07-16T00:00:00Z", "alpha", "packet_generated", "alpha"),
            ("2026-07-16T00:01:00Z", "beta", "packet_generated", "beta"),
        ],
    )
    alpha = runs_dir / "alpha"
    beta = runs_dir / "beta"
    _write_run(alpha)
    _write_run(beta)
    (alpha / "model_output.redacted.json").unlink()
    (beta / "model_output.raw.json").unlink()

    result = validate_dogfood_batch_artifacts(
        queue_path=queue,
        state_path=state,
        runs_dir=runs_dir,
        stage_log_path=stage_log,
    )

    assert result["validation_status"] == "failed"
    assert len(result["missing_artifacts"]) == 2
    assert any(item["missing"] == ["model_output.redacted.json"] for item in result["missing_artifacts"])
    assert any(item["missing"] == ["model_output.raw.json"] for item in result["missing_artifacts"])


def test_rejects_non_packet_generated_status(tmp_path: Path) -> None:
    queue, state, runs_dir, stage_log = _make_paths(tmp_path)
    _write_queue(queue, [("1", "alpha", "A")])
    _write_state(state, [("2026-07-16T00:00:00Z", "alpha", "attempted", "alpha")])
    _write_run(runs_dir / "alpha")

    result = validate_dogfood_batch_artifacts(
        queue_path=queue,
        state_path=state,
        runs_dir=runs_dir,
        stage_log_path=stage_log,
    )

    assert result["validation_status"] == "failed"
    assert result["missing_artifacts"][0]["missing"] == ["packet_generated_status"]


def test_malformed_json(tmp_path: Path) -> None:
    queue, state, runs_dir, stage_log = _make_paths(tmp_path)
    _write_queue(queue, [("1", "alpha", "A")])
    _write_state(state, [("2026-07-16T00:00:00Z", "alpha", "packet_generated", "alpha")])
    run_dir = runs_dir / "alpha"
    _write_run(run_dir)
    (run_dir / "model_output.raw.json").write_text('{"allowed_targets": [}\n', encoding="utf-8")

    result = validate_dogfood_batch_artifacts(
        queue_path=queue,
        state_path=state,
        runs_dir=runs_dir,
        stage_log_path=stage_log,
    )

    assert result["validation_status"] == "failed"
    assert result["json_errors"]
    assert result["json_errors"][0]["path"].endswith("model_output.raw.json")


def test_incomplete_model_content_missing_required_fields(tmp_path: Path) -> None:
    queue, state, runs_dir, stage_log = _make_paths(tmp_path)
    _write_queue(queue, [("1", "alpha", "A")])
    _write_state(state, [("2026-07-16T00:00:00Z", "alpha", "packet_generated", "alpha")])
    _write_partial_content_run(
        runs_dir / "alpha",
        content={
            "allowed_targets": [],
            "held_targets": [],
            "reason": "ok",
        },
    )

    result = validate_dogfood_batch_artifacts(
        queue_path=queue,
        state_path=state,
        runs_dir=runs_dir,
        stage_log_path=stage_log,
    )

    assert result["validation_status"] == "failed"
    assert result["json_errors"]
    assert "missing required fields" in result["json_errors"][0]["error"]


def test_model_content_must_be_json_object(tmp_path: Path) -> None:
    queue, state, runs_dir, stage_log = _make_paths(tmp_path)
    _write_queue(queue, [("1", "alpha", "A")])
    _write_state(state, [("2026-07-16T00:00:00Z", "alpha", "packet_generated", "alpha")])
    run_dir = runs_dir / "alpha"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "stage_packet.md").write_text("# packet\n", encoding="utf-8")
    (run_dir / "model_output.raw.json").write_text('{"allowed_targets": [], "held_targets": [], "reason": "ok"}\n', encoding="utf-8")
    (run_dir / "model_output.redacted.json").write_text('{"redacted": true}\n', encoding="utf-8")
    (run_dir / "model_content.json").write_text('[]\n', encoding="utf-8")

    result = validate_dogfood_batch_artifacts(
        queue_path=queue,
        state_path=state,
        runs_dir=runs_dir,
        stage_log_path=stage_log,
    )

    assert result["validation_status"] == "failed"
    assert result["json_errors"]
    assert result["json_errors"][0]["error"].endswith("expected a JSON object")


def test_missing_queue_or_state_handled_cleanly(tmp_path: Path) -> None:
    queue, state, runs_dir, stage_log = _make_paths(tmp_path)
    result = validate_dogfood_batch_artifacts(
        queue_path=queue,
        state_path=state,
        runs_dir=runs_dir,
        stage_log_path=stage_log,
    )
    assert result["validation_status"] == "failed"
    assert result["diagnostics"]
    assert "queue file does not exist" in result["diagnostics"][0]


def test_stage_log_exhaustion_visible_for_full_completion(tmp_path: Path) -> None:
    queue, state, runs_dir, stage_log = _make_paths(tmp_path)
    _write_queue(queue, [("1", "alpha", "A"), ("2", "beta", "B")])
    _write_state(
        state,
        [
            ("2026-07-16T00:00:00Z", "alpha", "packet_generated", "alpha"),
            ("2026-07-16T00:01:00Z", "beta", "packet_generated", "beta"),
        ],
    )
    _write_run(runs_dir / "alpha")
    _write_run(runs_dir / "beta")
    stage_log.write_text("Some line\nNo remaining dogfood stages.\n", encoding="utf-8")

    result = validate_dogfood_batch_artifacts(
        queue_path=queue,
        state_path=state,
        runs_dir=runs_dir,
        stage_log_path=stage_log,
    )

    assert result["validation_status"] == "passed"
    assert result["exhaustion_visible"] is True
