from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

import local_harness.run_manual_supervised_attempt_batch as batch_runner


def _write_tasks_jsonl(path: Path, entries: list[dict[str, object]]) -> Path:
    lines = [json.dumps(entry) for entry in entries]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _make_tasks_file(tmp_path: Path) -> Path:
    return _write_tasks_jsonl(
        tmp_path / "tasks.jsonl",
        [
            {"task_id": "task_a", "messy_input": "task a input"},
            {"task_id": "task_b", "messy_input": "task b input"},
        ],
    )


def test_valid_jsonl_task_loading(tmp_path: Path):
    tasks_jsonl = _make_tasks_file(tmp_path)
    tasks = batch_runner._read_jsonl_tasks(tasks_jsonl)
    assert [task["task_id"] for task in tasks] == ["task_a", "task_b"]


@pytest.mark.parametrize(
    "line, expected",
    [
        ("{", "invalid JSON"),
        (json.dumps(["not", "an", "object"]), "must be a JSON object"),
    ],
)
def test_invalid_jsonl_fails_clearly(tmp_path: Path, line: str, expected: str):
    tasks_jsonl = tmp_path / "tasks.jsonl"
    tasks_jsonl.write_text(line + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match=expected):
        batch_runner._read_jsonl_tasks(tasks_jsonl)


@pytest.mark.parametrize(
    "entry, expected",
    [
        ({"messy_input": "x"}, "missing task_id"),
        ({"task_id": "task_a"}, "missing messy_input"),
    ],
)
def test_missing_required_task_fields_fail_clearly(tmp_path: Path, entry: dict[str, object], expected: str):
    tasks_jsonl = _write_tasks_jsonl(tmp_path / "tasks.jsonl", [entry])
    with pytest.raises(ValueError, match=expected):
        batch_runner._read_jsonl_tasks(tasks_jsonl)


def test_dry_run_writes_plan_ledger_and_summary_without_calling_endpoint(tmp_path: Path):
    tasks_jsonl = _make_tasks_file(tmp_path)
    out_dir = tmp_path / "out"
    calls: list[str] = []

    def fail(*args, **kwargs):
        calls.append("called")
        raise AssertionError("should not call manual runner in dry-run")

    with patch.object(batch_runner.manual_attempt, "run_session", side_effect=fail), patch.object(
        batch_runner.manual_attempt, "run_call_local", side_effect=fail
    ), patch.object(batch_runner.manual_attempt, "run_ingest", side_effect=fail):
        result = batch_runner.run_batch(
            tasks_jsonl=tasks_jsonl,
            out_dir=out_dir,
            endpoint="http://example.invalid/v1",
            model="model-x",
            dry_run=True,
            timestamp="20260708T010101Z",
        )

    assert calls == []
    assert result["ledger_path"].is_file()
    assert result["summary_path"].is_file()
    assert (out_dir / "runs" / "task_a" / "task_input.txt").is_file()
    assert (out_dir / "runs" / "task_b" / "task_input.txt").is_file()


def test_refuses_to_overwrite_existing_nonempty_out_dir_by_default(tmp_path: Path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "existing.txt").write_text("x", encoding="utf-8")
    with pytest.raises(FileExistsError, match="not empty"):
        batch_runner.run_batch(
            tasks_jsonl=_make_tasks_file(tmp_path),
            out_dir=out_dir,
            endpoint="http://example.invalid/v1",
            model="model-x",
        )


def test_task_id_filtering_and_max_tasks(tmp_path: Path):
    tasks_jsonl = _make_tasks_file(tmp_path)
    out_dir = tmp_path / "out"
    with patch.object(batch_runner.manual_attempt, "run_session") as run_session, patch.object(
        batch_runner.manual_attempt, "run_call_local"
    ) as run_call_local, patch.object(batch_runner.manual_attempt, "run_ingest") as run_ingest:
        batch_runner.run_batch(
            tasks_jsonl=tasks_jsonl,
            out_dir=out_dir,
            endpoint="http://example.invalid/v1",
            model="model-x",
            task_ids=["task_b"],
            max_tasks=1,
            dry_run=True,
        )
    assert run_session.call_count == 0
    assert (out_dir / "runs" / "task_b" / "task_input.txt").is_file()
    assert not (out_dir / "runs" / "task_a").exists()


def test_ledger_includes_required_fields(tmp_path: Path):
    tasks_jsonl = _make_tasks_file(tmp_path)
    out_dir = tmp_path / "out"
    with patch.object(batch_runner.manual_attempt, "run_session"), patch.object(
        batch_runner.manual_attempt, "run_call_local"
    ), patch.object(batch_runner.manual_attempt, "run_ingest"):
        result = batch_runner.run_batch(
            tasks_jsonl=tasks_jsonl,
            out_dir=out_dir,
            endpoint="http://example.invalid/v1",
            model="model-x",
            dry_run=True,
        )
    record = json.loads(result["ledger_path"].read_text(encoding="utf-8").splitlines()[0])
    for key in [
        "task_id",
        "run_dir",
        "initial_validation_status",
        "retry_validation_status",
        "retries",
        "accepted",
        "pattern_exported",
        "failed_snapshot_preserved",
        "timeout_evidence_preserved",
        "target_authority_status",
        "duplicate_json_keys_status",
        "required_field_types_status",
        "notes",
    ]:
        assert key in record


def test_summary_includes_safety_boundaries(tmp_path: Path):
    tasks_jsonl = _make_tasks_file(tmp_path)
    out_dir = tmp_path / "out"
    with patch.object(batch_runner.manual_attempt, "run_session"), patch.object(
        batch_runner.manual_attempt, "run_call_local"
    ), patch.object(batch_runner.manual_attempt, "run_ingest"):
        batch_runner.run_batch(
            tasks_jsonl=tasks_jsonl,
            out_dir=out_dir,
            endpoint="http://example.invalid/v1",
            model="model-x",
            dry_run=True,
        )
    summary = (out_dir / "batch_summary.md").read_text(encoding="utf-8")
    assert "no model output executed/applied" in summary
    assert "no acceptance" in summary
    assert "no automatic failure-to-curriculum capture" in summary


def test_retry_limit_zero_does_not_create_retry_artifacts(tmp_path: Path):
    tasks_jsonl = _make_tasks_file(tmp_path)
    out_dir = tmp_path / "out"

    def fake_session(*args, **kwargs):
        return {"run_dir": out_dir / "runs" / "task_a" / "attempt_1"}

    def fake_call_local(*args, **kwargs):
        attempt_dir = out_dir / "runs" / "task_a" / "attempt_1"
        attempt_dir.mkdir(parents=True, exist_ok=True)
        (attempt_dir / "raw_model_output.txt").write_text("{}", encoding="utf-8")
        (attempt_dir / "local_model_call.json").write_text("{}", encoding="utf-8")
        return {"run_dir": attempt_dir}

    def fake_ingest(*args, **kwargs):
        attempt_dir = out_dir / "runs" / "task_a" / "attempt_1"
        (attempt_dir / "output_validation.json").write_text(json.dumps({"validation_status": "failed", "checks": []}), encoding="utf-8")
        (attempt_dir / "output_validation_report.txt").write_text("failed", encoding="utf-8")
        return {"validation_status": "failed"}

    with patch.object(batch_runner.manual_attempt, "run_session", side_effect=fake_session), patch.object(
        batch_runner.manual_attempt, "run_call_local", side_effect=fake_call_local
    ), patch.object(batch_runner.manual_attempt, "run_ingest", side_effect=fake_ingest), patch.object(
        batch_runner.manual_attempt, "_run_retry_contract"
    ) as retry_contract:
        batch_runner.run_batch(
            tasks_jsonl=_write_tasks_jsonl(tmp_path / "single.jsonl", [{"task_id": "task_a", "messy_input": "task a"}]),
            out_dir=out_dir,
            endpoint="http://example.invalid/v1",
            model="model-x",
            retry_limit=0,
        )
    assert retry_contract.call_count == 0


def test_retry_limit_one_invokes_retry_contract_and_records_preservation(tmp_path: Path):
    tasks_jsonl = _write_tasks_jsonl(tmp_path / "single.jsonl", [{"task_id": "task_a", "messy_input": "task a"}])
    out_dir = tmp_path / "out"
    attempt_dir = out_dir / "runs" / "task_a" / "attempt_1"

    def fake_session(*args, **kwargs):
        attempt_dir.mkdir(parents=True, exist_ok=True)
        (attempt_dir / "prompt_to_paste.md").write_text("prompt", encoding="utf-8")
        (attempt_dir / "raw_model_output.txt").write_text("raw", encoding="utf-8")
        return {"run_dir": attempt_dir}

    def fake_call_local(*args, **kwargs):
        if kwargs.get("overwrite"):
            (attempt_dir / "raw_model_output.txt").write_text("retry", encoding="utf-8")
        (attempt_dir / "local_model_call.json").write_text("{}", encoding="utf-8")
        return {"run_dir": attempt_dir}

    def fake_ingest(*args, **kwargs):
        if not (attempt_dir / "output_validation.json").exists():
            validation = {"validation_status": "failed", "checks": [{"check_id": "target_authority", "status": "failed"}]}
            (attempt_dir / "output_validation.json").write_text(json.dumps(validation), encoding="utf-8")
            (attempt_dir / "output_validation_report.txt").write_text("failed", encoding="utf-8")
            return {"validation_status": "failed"}
        (attempt_dir / "output_validation.json").write_text(json.dumps({"validation_status": "passed", "checks": []}), encoding="utf-8")
        (attempt_dir / "output_validation_report.txt").write_text("passed", encoding="utf-8")
        return {"validation_status": "passed"}

    def fake_retry_contract(*, run_dir: Path, retry_id: int):
        for name in [
            "raw_model_output.failed_1.txt",
            "output_validation.failed_1.json",
            "output_validation_report.failed_1.txt",
            "retry_prompt_to_paste_1.md",
            "prompt_to_paste.md",
        ]:
            (run_dir / name).write_text(name, encoding="utf-8")
        return {"run_dir": run_dir, "retry_id": retry_id}

    with patch.object(batch_runner.manual_attempt, "run_session", side_effect=fake_session), patch.object(
        batch_runner.manual_attempt, "run_call_local", side_effect=fake_call_local
    ), patch.object(batch_runner.manual_attempt, "run_ingest", side_effect=fake_ingest), patch.object(
        batch_runner.manual_attempt, "_run_retry_contract", side_effect=fake_retry_contract
    ) as retry_contract:
        result = batch_runner.run_batch(
            tasks_jsonl=tasks_jsonl,
            out_dir=out_dir,
            endpoint="http://example.invalid/v1",
            model="model-x",
            retry_limit=1,
        )
    assert retry_contract.call_count == 1
    record = result["records"][0]
    assert record["failed_snapshot_preserved"] is True
    assert record["retry_validation_status"] in {"failed", "passed"}


def test_retry_validation_status_reflects_retry_validation_and_not_initial_validation(tmp_path: Path):
    tasks_jsonl = _write_tasks_jsonl(tmp_path / "single.jsonl", [{"task_id": "task_a", "messy_input": "task a"}])
    out_dir = tmp_path / "out"
    attempt_dir = out_dir / "runs" / "task_a" / "attempt_1"

    def fake_session(*args, **kwargs):
        attempt_dir.mkdir(parents=True, exist_ok=True)
        (attempt_dir / "prompt_to_paste.md").write_text("prompt", encoding="utf-8")
        (attempt_dir / "raw_model_output.txt").write_text("raw", encoding="utf-8")
        return {"run_dir": attempt_dir}

    def fake_call_local(*args, **kwargs):
        if kwargs.get("overwrite"):
            (attempt_dir / "raw_model_output.txt").write_text("retry", encoding="utf-8")
        (attempt_dir / "local_model_call.json").write_text("{}", encoding="utf-8")
        return {"run_dir": attempt_dir}

    initial_validation = {
        "validation_status": "failed",
        "checks": [
            {"check_id": "target_authority", "status": "failed"},
            {"check_id": "duplicate_json_keys", "status": "passed"},
            {"check_id": "required_field_types", "status": "failed"},
        ],
    }
    retry_validation = {
        "validation_status": "passed",
        "checks": [
            {"check_id": "target_authority", "status": "passed"},
            {"check_id": "duplicate_json_keys", "status": "passed"},
            {"check_id": "required_field_types", "status": "passed"},
        ],
    }

    def fake_ingest(*args, **kwargs):
        if not (attempt_dir / "output_validation.json").exists():
            (attempt_dir / "output_validation.json").write_text(json.dumps(initial_validation), encoding="utf-8")
            (attempt_dir / "output_validation_report.txt").write_text("initial", encoding="utf-8")
            return {"validation_status": "failed"}
        (attempt_dir / "output_validation.json").write_text(json.dumps(retry_validation), encoding="utf-8")
        (attempt_dir / "output_validation_report.txt").write_text("retry", encoding="utf-8")
        return {"validation_status": "passed"}

    def fake_retry_contract(*, run_dir: Path, retry_id: int):
        for name in [
            "raw_model_output.failed_1.txt",
            "output_validation.failed_1.json",
            "output_validation_report.failed_1.txt",
            "retry_prompt_to_paste_1.md",
            "prompt_to_paste.md",
        ]:
            (run_dir / name).write_text(name, encoding="utf-8")
        return {"run_dir": run_dir, "retry_id": retry_id}

    with patch.object(batch_runner.manual_attempt, "run_session", side_effect=fake_session), patch.object(
        batch_runner.manual_attempt, "run_call_local", side_effect=fake_call_local
    ), patch.object(batch_runner.manual_attempt, "run_ingest", side_effect=fake_ingest), patch.object(
        batch_runner.manual_attempt, "_run_retry_contract", side_effect=fake_retry_contract
    ):
        result = batch_runner.run_batch(
            tasks_jsonl=tasks_jsonl,
            out_dir=out_dir,
            endpoint="http://example.invalid/v1",
            model="model-x",
            retry_limit=1,
        )

    record = result["records"][0]
    assert record["initial_validation_status"] == "failed"
    assert record["retry_validation_status"] == "passed"
    assert record["target_authority_status"] == "passed"
    assert record["duplicate_json_keys_status"] == "passed"
    assert record["required_field_types_status"] == "passed"


def test_retry_call_local_failure_stops_retry_ingest_and_records_evidence(tmp_path: Path):
    tasks_jsonl = _write_tasks_jsonl(tmp_path / "single.jsonl", [{"task_id": "task_a", "messy_input": "task a"}])
    out_dir = tmp_path / "out"
    attempt_dir = out_dir / "runs" / "task_a" / "attempt_1"

    def fake_session(*args, **kwargs):
        attempt_dir.mkdir(parents=True, exist_ok=True)
        (attempt_dir / "prompt_to_paste.md").write_text("prompt", encoding="utf-8")
        (attempt_dir / "raw_model_output.txt").write_text("raw", encoding="utf-8")
        return {"run_dir": attempt_dir}

    def fake_call_local(*args, **kwargs):
        if not kwargs.get("overwrite"):
            (attempt_dir / "local_model_call.json").write_text("{}", encoding="utf-8")
            return {"run_dir": attempt_dir}
        (attempt_dir / "local_model_call.failed.json").write_text(json.dumps({"failure_reason": "timeout"}), encoding="utf-8")
        raise RuntimeError("timed out")

    def fake_ingest(*args, **kwargs):
        (attempt_dir / "output_validation.json").write_text(json.dumps({"validation_status": "failed", "checks": []}), encoding="utf-8")
        (attempt_dir / "output_validation_report.txt").write_text("failed", encoding="utf-8")
        return {"validation_status": "failed"}

    def fake_retry_contract(*, run_dir: Path, retry_id: int):
        for name in [
            "raw_model_output.failed_1.txt",
            "output_validation.failed_1.json",
            "output_validation_report.failed_1.txt",
            "retry_prompt_to_paste_1.md",
            "prompt_to_paste.md",
        ]:
            (run_dir / name).write_text(name, encoding="utf-8")
        return {"run_dir": run_dir, "retry_id": retry_id}

    with patch.object(batch_runner.manual_attempt, "run_session", side_effect=fake_session), patch.object(
        batch_runner.manual_attempt, "run_call_local", side_effect=fake_call_local
    ), patch.object(batch_runner.manual_attempt, "run_ingest", side_effect=fake_ingest) as retry_ingest, patch.object(
        batch_runner.manual_attempt, "_run_retry_contract", side_effect=fake_retry_contract
    ):
        result = batch_runner.run_batch(
            tasks_jsonl=tasks_jsonl,
            out_dir=out_dir,
            endpoint="http://example.invalid/v1",
            model="model-x",
            retry_limit=1,
        )

    record = result["records"][0]
    assert retry_ingest.call_count == 1
    assert record["retry_validation_status"] == "not_run"
    assert record["notes"].count("retry call-local failed") == 1
    assert record["timeout_evidence_preserved"] is True


def test_batch_runner_does_not_add_execution_or_promotion_behaviors(tmp_path: Path):
    tasks_jsonl = _make_tasks_file(tmp_path)
    out_dir = tmp_path / "out"
    with patch.object(batch_runner.manual_attempt, "run_session"), patch.object(
        batch_runner.manual_attempt, "run_call_local"
    ), patch.object(batch_runner.manual_attempt, "run_ingest"), patch.object(
        batch_runner.manual_attempt, "build_supervised_review_decision_record"
    ) as decision, patch.object(batch_runner.manual_attempt, "build_supervised_downstream_use_gate_record") as gate, patch.object(
        batch_runner.manual_attempt, "build_supervised_handoff_packet"
    ) as handoff:
        batch_runner.run_batch(
            tasks_jsonl=tasks_jsonl,
            out_dir=out_dir,
            endpoint="http://example.invalid/v1",
            model="model-x",
            dry_run=True,
        )
    assert decision.call_count == 0
    assert gate.call_count == 0
    assert handoff.call_count == 0
