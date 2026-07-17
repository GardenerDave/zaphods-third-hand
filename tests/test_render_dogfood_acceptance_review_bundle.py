from __future__ import annotations

import hashlib
import json
from pathlib import Path

from local_harness.render_dogfood_acceptance_review_bundle import (
    render_dogfood_acceptance_review_bundle,
)


def _write_queue(path: Path, rows: list[tuple[str, str, str]]) -> None:
    lines = ["# priority\tslug\tdescription"]
    lines.extend("\t".join(row) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_state(path: Path, rows: list[tuple[str, str, str, str]]) -> None:
    lines = ["# timestamp\tslug\tstatus\trun_dir"]
    lines.extend("\t".join(row) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_run(run_dir: Path, raw_payload: object = None, content_payload: object = None) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "stage_packet.md").write_text("# packet\n", encoding="utf-8")
    raw_payload = {"allowed_targets": [], "held_targets": [], "reason": "ok"} if raw_payload is None else raw_payload
    content_payload = (
        {
            "task_summary": "ok",
            "repo_observations": [],
            "allowed_targets": [],
            "held_targets": [],
            "proposed_next_action": "ok",
            "validation_plan": [],
            "reason": "ok",
        }
        if content_payload is None
        else content_payload
    )
    (run_dir / "model_output.raw.json").write_text(json.dumps(raw_payload) + "\n", encoding="utf-8")
    (run_dir / "model_output.redacted.json").write_text('{"redacted": true}\n', encoding="utf-8")
    (run_dir / "model_content.json").write_text(json.dumps(content_payload) + "\n", encoding="utf-8")


def _paths(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    return (
        tmp_path / "queue.tsv",
        tmp_path / "state.tsv",
        tmp_path / "runs",
        tmp_path / "stage.log",
    )


def test_valid_batch_writes_bundle(tmp_path: Path) -> None:
    queue, state, runs_dir, stage_log = _paths(tmp_path)
    out_dir = tmp_path / "bundle"
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

    bundle = render_dogfood_acceptance_review_bundle(
        queue_path=queue,
        state_path=state,
        runs_dir=runs_dir,
        out_dir=out_dir,
        stage_log_path=stage_log,
    )

    output_path = out_dir / "dogfood_acceptance_review_bundle.json"
    assert output_path.is_file()
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["bundle_schema"] == "dogfood_acceptance_review_bundle_v1"
    assert written["evidence_validation_status"] == "passed"
    assert written["acceptance_status"] == "not_reviewed"
    assert written["review_required"] is True
    assert written["downstream_use_status"] == "prohibited_until_review"
    assert written["authority_boundary"] == [
        "evidence_only",
        "no_auto_promotion",
        "no_unattended_execution",
        "no_training_capture",
        "no_cleanup_authority",
        "no_merge_authority",
        "no_deployment_authority",
    ]
    assert written["completed_stages"][0]["slug"] == "alpha"
    assert set(written["completed_stages"][0]["artifact_sha256"]) == {
        "stage_packet.md",
        "model_output.raw.json",
        "model_output.redacted.json",
        "model_content.json",
    }
    assert "allowed_targets" not in json.dumps(written)
    assert bundle["validation_result"]["validation_status"] == "passed"


def test_failed_validator_still_writes_bundle(tmp_path: Path) -> None:
    queue, state, runs_dir, stage_log = _paths(tmp_path)
    out_dir = tmp_path / "bundle"
    _write_queue(queue, [("1", "alpha", "A")])
    _write_state(state, [("2026-07-16T00:00:00Z", "alpha", "attempted", "alpha")])
    _write_run(runs_dir / "alpha")

    bundle = render_dogfood_acceptance_review_bundle(
        queue_path=queue,
        state_path=state,
        runs_dir=runs_dir,
        out_dir=out_dir,
        stage_log_path=stage_log,
    )

    assert bundle["evidence_validation_status"] == "failed"
    assert bundle["acceptance_status"] == "not_reviewed"
    assert bundle["review_required"] is True
    assert bundle["downstream_use_status"] == "prohibited_until_review"


def test_top_level_keys_are_stable(tmp_path: Path) -> None:
    queue, state, runs_dir, stage_log = _paths(tmp_path)
    out_dir = tmp_path / "bundle"
    _write_queue(queue, [("1", "alpha", "A")])
    _write_state(state, [("2026-07-16T00:00:00Z", "alpha", "packet_generated", "alpha")])
    _write_run(runs_dir / "alpha")
    stage_log.write_text("No remaining dogfood stages.\n", encoding="utf-8")

    bundle = render_dogfood_acceptance_review_bundle(
        queue_path=queue,
        state_path=state,
        runs_dir=runs_dir,
        out_dir=out_dir,
        stage_log_path=stage_log,
    )

    assert set(bundle) == {
        "authority_boundary",
        "acceptance_status",
        "bundle_schema",
        "completed_stages",
        "diagnostics",
        "downstream_use_status",
        "evidence_validation_status",
        "generated_at_utc",
        "inputs",
        "review_required",
        "validation_result",
    }


def test_hashes_match_file_bytes(tmp_path: Path) -> None:
    queue, state, runs_dir, stage_log = _paths(tmp_path)
    out_dir = tmp_path / "bundle"
    _write_queue(queue, [("1", "alpha", "A")])
    _write_state(state, [("2026-07-16T00:00:00Z", "alpha", "packet_generated", "alpha")])
    run_dir = runs_dir / "alpha"
    _write_run(run_dir)
    stage_log.write_text("No remaining dogfood stages.\n", encoding="utf-8")

    bundle = render_dogfood_acceptance_review_bundle(
        queue_path=queue,
        state_path=state,
        runs_dir=runs_dir,
        out_dir=out_dir,
        stage_log_path=stage_log,
    )

    expected = hashlib.sha256((run_dir / "model_output.raw.json").read_bytes()).hexdigest()
    assert bundle["completed_stages"][0]["artifact_sha256"]["model_output.raw.json"] == expected


def test_no_raw_model_output_contents_embedded(tmp_path: Path) -> None:
    queue, state, runs_dir, stage_log = _paths(tmp_path)
    out_dir = tmp_path / "bundle"
    _write_queue(queue, [("1", "alpha", "A")])
    _write_state(state, [("2026-07-16T00:00:00Z", "alpha", "packet_generated", "alpha")])
    _write_run(runs_dir / "alpha", raw_payload={"secret": "do not embed"})
    stage_log.write_text("No remaining dogfood stages.\n", encoding="utf-8")

    bundle = render_dogfood_acceptance_review_bundle(
        queue_path=queue,
        state_path=state,
        runs_dir=runs_dir,
        out_dir=out_dir,
        stage_log_path=stage_log,
    )

    text = json.dumps(bundle, sort_keys=True)
    assert "do not embed" not in text
    assert "secret" not in text


def test_bundle_preserves_validator_diagnostics_for_incomplete_content(tmp_path: Path) -> None:
    queue, state, runs_dir, stage_log = _paths(tmp_path)
    out_dir = tmp_path / "bundle"
    _write_queue(queue, [("1", "alpha", "A")])
    _write_state(state, [("2026-07-16T00:00:00Z", "alpha", "packet_generated", "alpha")])
    _write_run(
        runs_dir / "alpha",
        content_payload={
            "allowed_targets": [],
            "held_targets": [],
            "reason": "ok",
        },
    )
    stage_log.write_text("No remaining dogfood stages.\n", encoding="utf-8")

    bundle = render_dogfood_acceptance_review_bundle(
        queue_path=queue,
        state_path=state,
        runs_dir=runs_dir,
        out_dir=out_dir,
        stage_log_path=stage_log,
    )

    assert bundle["evidence_validation_status"] == "failed"
    assert bundle["diagnostics"]
    assert any("missing required fields" in item["error"] for item in bundle["validation_result"]["json_errors"])


def test_bundle_top_level_diagnostics_include_missing_artifact_summary(tmp_path: Path) -> None:
    queue, state, runs_dir, stage_log = _paths(tmp_path)
    out_dir = tmp_path / "bundle"
    _write_queue(queue, [("1", "alpha", "A")])
    _write_state(state, [("2026-07-16T00:00:00Z", "alpha", "packet_generated", "alpha")])
    run_dir = runs_dir / "alpha"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "stage_packet.md").write_text("# packet\n", encoding="utf-8")
    (run_dir / "model_output.raw.json").write_text('{"allowed_targets": [], "held_targets": [], "reason": "ok"}\n', encoding="utf-8")
    (run_dir / "model_content.json").write_text(
        json.dumps(
            {
                "task_summary": "ok",
                "repo_observations": [],
                "allowed_targets": [],
                "held_targets": [],
                "proposed_next_action": "ok",
                "validation_plan": [],
                "reason": "ok",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    stage_log.write_text("No remaining dogfood stages.\n", encoding="utf-8")

    bundle = render_dogfood_acceptance_review_bundle(
        queue_path=queue,
        state_path=state,
        runs_dir=runs_dir,
        out_dir=out_dir,
        stage_log_path=stage_log,
    )

    assert bundle["evidence_validation_status"] == "failed"
    assert bundle["acceptance_status"] == "not_reviewed"
    assert bundle["downstream_use_status"] == "prohibited_until_review"
    assert bundle["authority_boundary"]
    assert bundle["validation_result"]
    assert any("missing artifacts" in item for item in bundle["diagnostics"])
    assert any("model_output.redacted.json" in item for item in bundle["diagnostics"])
