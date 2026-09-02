from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest import mock

import pytest

from local_harness.historian_context import CONTEXT_BOUNDARIES
from local_harness.historian_context_query import (
    ENDPOINT_ENV,
    HISTORIAN_CONTEXT_SCHEMA,
    RUNNER_SCRIPT,
    HistorianAskBindError,
    ask_and_bind,
    ask_and_bind_many,
    main,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness" / "historian_context_query.py"

QUERY_ID = "op-11111111-2222-3333-4444-555555555555"
OTHER_QUERY_ID = "op-99999999-8888-7777-6666-555555555555"
QUESTION = "What historical decisions constrain this task?"
CITED_RECORDS = {
    "CLM-example-gap": "claim",
    "REV-example-separation": "revision",
}


def _write_record(records_dir: Path, record_id: str, kind: str) -> Path:
    kind_dir = records_dir / f"{kind}s"
    kind_dir.mkdir(parents=True, exist_ok=True)
    path = kind_dir / f"{record_id}.md"
    path.write_text(
        "---\n"
        f"id: {record_id}\n"
        f"kind: {kind}\n"
        "---\n"
        "\n"
        f"Body text for {record_id}.\n",
        encoding="utf-8",
    )
    return path


def _make_historian_repo(tmp_path: Path, *, with_runtime: bool = True) -> Path:
    repo = tmp_path / "project-historian-v1"
    (repo / "historian").mkdir(parents=True, exist_ok=True)
    (repo / "historian" / "service.py").write_text("# historian service marker\n", encoding="utf-8")
    records_dir = repo / "records"
    records_dir.mkdir(parents=True, exist_ok=True)
    for record_id, kind in CITED_RECORDS.items():
        _write_record(records_dir, record_id, kind)
    if with_runtime:
        runtime = repo / "interfaces/khoj/runtime/py312-cpu/bin"
        runtime.mkdir(parents=True, exist_ok=True)
        python = runtime / "python"
        python.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        python.chmod(python.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return repo


def _make_query_dir(
    repo: Path,
    query_id: str = QUERY_ID,
    question: str = QUESTION,
    *,
    cited_record_ids: list[str] | None = None,
) -> Path:
    query_dir = repo / ".work" / "historian_queries" / query_id
    reasoner_dir = query_dir / "reasoner"
    reasoner_dir.mkdir(parents=True, exist_ok=True)
    query_dir.joinpath("query.json").write_text(
        json.dumps([{"id": query_id, "question": question}]) + "\n",
        encoding="utf-8",
    )
    query_dir.joinpath("retrieval.json").write_text(
        json.dumps(
            {
                "corpus_fingerprint": "fingerprint-abc123",
                "revision": "rev-0007",
                "document_count": 48,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    result = {
        "query_id": query_id,
        "question": question,
        "parsed_response": {
            "answer": "Advisory answer over cited evidence.",
            "cited_record_ids": cited_record_ids or sorted(CITED_RECORDS),
            "evidence_used": cited_record_ids or sorted(CITED_RECORDS),
            "uncertainty_or_limitations": "The answer is advisory only.",
            "contradictions_or_missing_evidence": ["No broader claim is supported."],
        },
        "validation": {
            "schema_valid": {"valid": True},
            "grounding_valid": {"valid": True},
            "contract_valid": True,
        },
    }
    reasoner_dir.joinpath(f"{query_id}.result.json").write_text(
        json.dumps(result) + "\n", encoding="utf-8"
    )
    reasoner_dir.joinpath(f"{query_id}.transaction.json").write_text(
        json.dumps({"state": "COMPLETE"}) + "\n", encoding="utf-8"
    )
    return query_dir


def _ask_result(
    query_dir: Path,
    query_id: str = QUERY_ID,
    question: str = QUESTION,
    *,
    status: str = "ok",
    omit: tuple[str, ...] = (),
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "request_id": query_id,
        "question": question,
        "question_fingerprint": "deadbeef",
        "status": status,
        "error_code": None,
        "selected_record_ids": sorted(CITED_RECORDS),
        "answer": "Advisory answer over cited evidence.",
        "cited_record_ids": sorted(CITED_RECORDS),
        "evidence_used": sorted(CITED_RECORDS),
        "uncertainty_or_limitations": "The answer is advisory only.",
        "contradictions_or_missing_evidence": ["No broader claim is supported."],
        "validation": {"contract_valid": True},
        "runtime": {
            "work_root": str(query_dir.parent),
            "request_dir": str(query_dir),
            "retrieval_path": str(query_dir / "retrieval.json"),
            "reasoner_dir": str(query_dir / "reasoner"),
        },
    }
    if status != "ok":
        result["error_code"] = "reasoner_unavailable"
        result["error"] = "Historian reasoner endpoint is unavailable"
    for key in omit:
        result.pop(key, None)
    return result


def _completed(stdout: Any, returncode: int = 0, stderr: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


@pytest.fixture
def historian_repo(tmp_path: Path) -> Path:
    return _make_historian_repo(tmp_path)


@pytest.fixture
def endpoint(monkeypatch) -> str:
    value = "http://env-endpoint.example/v1"
    monkeypatch.setenv(ENDPOINT_ENV, value)
    return value

def _run_ask_and_bind(
    historian_repo: Path,
    output_dir: Path,
    result: dict[str, Any],
    *,
    endpoint: str | None = "http://explicit.example/v1",
    question: str = QUESTION,
    **kwargs: Any,
) -> dict[str, Any]:
    with mock.patch.object(
        subprocess, "run", return_value=_completed(json.dumps(result))
    ) as runner:
        summary = ask_and_bind(
            question=question,
            historian_repo=historian_repo,
            output_dir=output_dir,
            endpoint=endpoint,
            historian_python=Path(sys.executable),
            **kwargs,
        )
        summary["_runner_call"] = runner.call_args
    return summary


def test_single_ask_and_bind_success(tmp_path: Path, historian_repo: Path) -> None:
    query_dir = _make_query_dir(historian_repo)
    output_dir = tmp_path / "evidence"
    summary = _run_ask_and_bind(historian_repo, output_dir, _ask_result(query_dir))

    assert summary["historian_query_id"] == QUERY_ID
    assert summary["historian_query_dir"] == str(query_dir)
    assert summary["historian_context_path"] == str(
        output_dir / f"historian_context_{QUERY_ID}.json"
    )
    assert summary["historian_context_markdown_path"] == str(
        output_dir / f"historian_context_{QUERY_ID}.md"
    )
    assert summary["historian_context_schema"] == HISTORIAN_CONTEXT_SCHEMA
    assert summary["cited_record_ids"] == sorted(CITED_RECORDS)
    assert summary["retrieval_corpus_fingerprint"] == "fingerprint-abc123"
    assert summary["retrieval_revision"] == "rev-0007"
    assert summary["retrieval_document_count"] == 48
    assert Path(summary["historian_context_path"]).is_file()
    assert Path(summary["historian_context_markdown_path"]).is_file()
    context = json.loads(Path(summary["historian_context_path"]).read_text(encoding="utf-8"))
    assert context["schema_version"] == HISTORIAN_CONTEXT_SCHEMA
    assert context["boundaries"] == list(CONTEXT_BOUNDARIES)
    assert "not approval" in " ".join(summary["boundaries"])


def test_runner_invocation_shape(tmp_path: Path, historian_repo: Path, endpoint: str) -> None:
    query_dir = _make_query_dir(historian_repo)
    summary = _run_ask_and_bind(
        historian_repo, tmp_path / "evidence", _ask_result(query_dir), endpoint=None
    )
    call = summary["_runner_call"]
    command = call.args[0]
    assert isinstance(command, list)
    assert command[0] == sys.executable
    assert command[1] == str(RUNNER_SCRIPT)
    assert command[2] == QUESTION
    assert command[3] == "1536"
    assert call.kwargs["cwd"] == str(historian_repo)
    assert call.kwargs["capture_output"] is True
    assert "shell" not in call.kwargs or call.kwargs["shell"] is False


def test_endpoint_passed_through_environment_not_argv(
    tmp_path: Path, historian_repo: Path, endpoint: str
) -> None:
    query_dir = _make_query_dir(historian_repo)
    summary = _run_ask_and_bind(
        historian_repo, tmp_path / "evidence", _ask_result(query_dir), endpoint=None
    )
    call = summary["_runner_call"]
    assert call.kwargs["env"][ENDPOINT_ENV] == endpoint
    assert endpoint not in call.args[0]
    assert str(historian_repo) in call.kwargs["env"]["PYTHONPATH"]


def test_explicit_endpoint_overrides_environment(
    tmp_path: Path, historian_repo: Path, endpoint: str
) -> None:
    query_dir = _make_query_dir(historian_repo)
    summary = _run_ask_and_bind(
        historian_repo,
        tmp_path / "evidence",
        _ask_result(query_dir),
        endpoint="http://explicit.example/v1",
    )
    call = summary["_runner_call"]
    assert call.kwargs["env"][ENDPOINT_ENV] == "http://explicit.example/v1"


def test_missing_endpoint_fails_closed(
    tmp_path: Path, historian_repo: Path, monkeypatch
) -> None:
    monkeypatch.delenv(ENDPOINT_ENV, raising=False)
    with mock.patch.object(subprocess, "run") as runner:
        with pytest.raises(HistorianAskBindError, match=ENDPOINT_ENV):
            ask_and_bind(
                question=QUESTION,
                historian_repo=historian_repo,
                output_dir=tmp_path / "evidence",
                endpoint=None,
                historian_python=Path(sys.executable),
            )
        runner.assert_not_called()


def test_missing_historian_repo_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(HistorianAskBindError, match="does not exist"):
        ask_and_bind(
            question=QUESTION,
            historian_repo=tmp_path / "missing-repo",
            output_dir=tmp_path / "evidence",
            endpoint="http://explicit.example/v1",
        )


def test_historian_repo_without_service_module_fails_closed(tmp_path: Path) -> None:
    repo = tmp_path / "not-historian"
    (repo / "records").mkdir(parents=True)
    with pytest.raises(HistorianAskBindError, match="historian/service.py"):
        ask_and_bind(
            question=QUESTION,
            historian_repo=repo,
            output_dir=tmp_path / "evidence",
            endpoint="http://explicit.example/v1",
        )


def test_missing_runtime_fails_closed_with_actionable_error(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _make_historian_repo(tmp_path, with_runtime=False)
    monkeypatch.delenv(ENDPOINT_ENV, raising=False)
    with mock.patch.object(subprocess, "run") as runner:
        with pytest.raises(HistorianAskBindError, match="--historian-python"):
            ask_and_bind(
                question=QUESTION,
                historian_repo=repo,
                output_dir=tmp_path / "evidence",
                endpoint="http://explicit.example/v1",
            )
        runner.assert_not_called()


def test_failed_historian_result_fails_closed_and_preserves_query_dir(
    tmp_path: Path, historian_repo: Path
) -> None:
    query_dir = _make_query_dir(historian_repo)
    output_dir = tmp_path / "evidence"
    result = _ask_result(query_dir, status="failed")
    with mock.patch.object(subprocess, "run", return_value=_completed(json.dumps(result))):
        with pytest.raises(HistorianAskBindError) as raised:
            ask_and_bind(
                question=QUESTION,
                historian_repo=historian_repo,
                output_dir=output_dir,
                endpoint="http://explicit.example/v1",
                historian_python=Path(sys.executable),
            )
    assert "reasoner_unavailable" in str(raised.value)
    assert str(query_dir) in str(raised.value)
    assert query_dir.is_dir()
    assert not any(output_dir.iterdir()) if output_dir.exists() else True


def test_non_json_runner_output_fails_closed(tmp_path: Path, historian_repo: Path) -> None:
    _make_query_dir(historian_repo)
    with mock.patch.object(
        subprocess, "run", return_value=_completed("definitely not json")
    ):
        with pytest.raises(HistorianAskBindError, match="did not return a JSON result"):
            ask_and_bind(
                question=QUESTION,
                historian_repo=historian_repo,
                output_dir=tmp_path / "evidence",
                endpoint="http://explicit.example/v1",
                historian_python=Path(sys.executable),
            )


def test_runner_nonzero_exit_fails_closed(tmp_path: Path, historian_repo: Path) -> None:
    _make_query_dir(historian_repo)
    with mock.patch.object(
        subprocess, "run", return_value=_completed("", returncode=1, stderr="runner exploded")
    ):
        with pytest.raises(HistorianAskBindError, match="runner exploded"):
            ask_and_bind(
                question=QUESTION,
                historian_repo=historian_repo,
                output_dir=tmp_path / "evidence",
                endpoint="http://explicit.example/v1",
                historian_python=Path(sys.executable),
            )


def test_runner_timeout_fails_closed(tmp_path: Path, historian_repo: Path) -> None:
    _make_query_dir(historian_repo)
    with mock.patch.object(
        subprocess,
        "run",
        side_effect=subprocess.TimeoutExpired(cmd="historian", timeout=600),
    ):
        with pytest.raises(HistorianAskBindError, match="timed out"):
            ask_and_bind(
                question=QUESTION,
                historian_repo=historian_repo,
                output_dir=tmp_path / "evidence",
                endpoint="http://explicit.example/v1",
                historian_python=Path(sys.executable),
                timeout_seconds=600,
            )

def test_result_without_request_id_fails_closed(tmp_path: Path, historian_repo: Path) -> None:
    query_dir = _make_query_dir(historian_repo)
    result = _ask_result(query_dir, omit=("request_id",))
    with mock.patch.object(subprocess, "run", return_value=_completed(json.dumps(result))):
        with pytest.raises(HistorianAskBindError, match="refusing to guess"):
            ask_and_bind(
                question=QUESTION,
                historian_repo=historian_repo,
                output_dir=tmp_path / "evidence",
                endpoint="http://explicit.example/v1",
                historian_python=Path(sys.executable),
            )


def test_result_without_request_dir_fails_closed(tmp_path: Path, historian_repo: Path) -> None:
    query_dir = _make_query_dir(historian_repo)
    result = _ask_result(query_dir)
    result["runtime"] = {"work_root": str(query_dir.parent)}
    with mock.patch.object(subprocess, "run", return_value=_completed(json.dumps(result))):
        with pytest.raises(HistorianAskBindError, match="refusing to scan"):
            ask_and_bind(
                question=QUESTION,
                historian_repo=historian_repo,
                output_dir=tmp_path / "evidence",
                endpoint="http://explicit.example/v1",
                historian_python=Path(sys.executable),
            )


def test_request_dir_outside_work_root_fails_closed(tmp_path: Path, historian_repo: Path) -> None:
    outside = tmp_path / "elsewhere" / QUERY_ID
    outside.mkdir(parents=True)
    result = _ask_result(historian_repo / ".work" / "historian_queries" / QUERY_ID)
    result["runtime"]["request_dir"] = str(outside)
    with mock.patch.object(subprocess, "run", return_value=_completed(json.dumps(result))):
        with pytest.raises(HistorianAskBindError, match="outside the Historian query work root"):
            ask_and_bind(
                question=QUESTION,
                historian_repo=historian_repo,
                output_dir=tmp_path / "evidence",
                endpoint="http://explicit.example/v1",
                historian_python=Path(sys.executable),
            )


def test_request_dir_missing_on_disk_fails_closed(
    tmp_path: Path, historian_repo: Path
) -> None:
    result = _ask_result(historian_repo / ".work" / "historian_queries" / "op-does-not-exist")
    with mock.patch.object(subprocess, "run", return_value=_completed(json.dumps(result))):
        with pytest.raises(HistorianAskBindError, match="does not exist"):
            ask_and_bind(
                question=QUESTION,
                historian_repo=historian_repo,
                output_dir=tmp_path / "evidence",
                endpoint="http://explicit.example/v1",
                historian_python=Path(sys.executable),
            )


def test_query_artifact_id_mismatch_fails_closed(tmp_path: Path, historian_repo: Path) -> None:
    query_dir = _make_query_dir(historian_repo, query_id=OTHER_QUERY_ID)
    result = _ask_result(query_dir)
    with mock.patch.object(subprocess, "run", return_value=_completed(json.dumps(result))):
        with pytest.raises(HistorianAskBindError, match="does not match the returned request id"):
            ask_and_bind(
                question=QUESTION,
                historian_repo=historian_repo,
                output_dir=tmp_path / "evidence",
                endpoint="http://explicit.example/v1",
                historian_python=Path(sys.executable),
            )


def test_question_mismatch_fails_closed(tmp_path: Path, historian_repo: Path) -> None:
    query_dir = _make_query_dir(historian_repo, question="A different question entirely")
    result = _ask_result(query_dir)
    with mock.patch.object(subprocess, "run", return_value=_completed(json.dumps(result))):
        with pytest.raises(HistorianAskBindError, match="does not match the asked question"):
            ask_and_bind(
                question=QUESTION,
                historian_repo=historian_repo,
                output_dir=tmp_path / "evidence",
                endpoint="http://explicit.example/v1",
                historian_python=Path(sys.executable),
            )


def test_newest_directory_heuristic_is_not_used(tmp_path: Path, historian_repo: Path) -> None:
    query_dir = _make_query_dir(historian_repo)
    decoy_dir = _make_query_dir(historian_repo, query_id=OTHER_QUERY_ID)
    future = 4_102_444_800
    os.utime(decoy_dir, (future, future))
    os.utime(decoy_dir / "query.json", (future, future))

    summary = _run_ask_and_bind(historian_repo, tmp_path / "evidence", _ask_result(query_dir))

    assert summary["historian_query_id"] == QUERY_ID
    assert summary["historian_query_dir"] == str(query_dir)
    assert Path(summary["historian_context_path"]).is_file()
    assert not (tmp_path / "evidence" / f"historian_context_{OTHER_QUERY_ID}.json").exists()


def test_binder_failure_propagates_and_writes_no_artifact(
    tmp_path: Path, historian_repo: Path
) -> None:
    query_dir = _make_query_dir(
        historian_repo, cited_record_ids=["CLM-not-in-corpus"]
    )
    output_dir = tmp_path / "evidence"
    with mock.patch.object(
        subprocess, "run", return_value=_completed(json.dumps(_ask_result(query_dir)))
    ):
        with pytest.raises(HistorianAskBindError, match="binding failed"):
            ask_and_bind(
                question=QUESTION,
                historian_repo=historian_repo,
                output_dir=output_dir,
                endpoint="http://explicit.example/v1",
                historian_python=Path(sys.executable),
            )
    assert not output_dir.exists() or not any(output_dir.iterdir())


def test_overwrite_refused_then_allowed(tmp_path: Path, historian_repo: Path) -> None:
    query_dir = _make_query_dir(historian_repo)
    output_dir = tmp_path / "evidence"
    first = _run_ask_and_bind(historian_repo, output_dir, _ask_result(query_dir))
    context_path = Path(first["historian_context_path"])
    assert context_path.is_file()

    with mock.patch.object(
        subprocess, "run", return_value=_completed(json.dumps(_ask_result(query_dir)))
    ):
        with pytest.raises(HistorianAskBindError, match="already exists"):
            ask_and_bind(
                question=QUESTION,
                historian_repo=historian_repo,
                output_dir=output_dir,
                endpoint="http://explicit.example/v1",
                historian_python=Path(sys.executable),
            )

    with mock.patch.object(
        subprocess, "run", return_value=_completed(json.dumps(_ask_result(query_dir)))
    ):
        summary = ask_and_bind(
            question=QUESTION,
            historian_repo=historian_repo,
            output_dir=output_dir,
            endpoint="http://explicit.example/v1",
            historian_python=Path(sys.executable),
            overwrite=True,
        )
    assert summary["historian_query_id"] == QUERY_ID
    assert context_path.is_file()


def test_canonical_historian_records_are_not_modified(
    tmp_path: Path, historian_repo: Path
) -> None:
    query_dir = _make_query_dir(historian_repo)
    records_dir = historian_repo / "records"
    before = {
        path: path.read_bytes()
        for path in sorted(records_dir.rglob("*.md"))
    }
    _run_ask_and_bind(historian_repo, tmp_path / "evidence", _ask_result(query_dir))
    after = {
        path: path.read_bytes()
        for path in sorted(records_dir.rglob("*.md"))
    }
    assert before == after


def test_multiple_questions_bind_separate_artifacts(
    tmp_path: Path, historian_repo: Path
) -> None:
    first_dir = _make_query_dir(historian_repo, query_id=QUERY_ID)
    second_dir = _make_query_dir(historian_repo, query_id=OTHER_QUERY_ID, question="Second question?")
    output_dir = tmp_path / "evidence"
    results = {
        QUESTION: _ask_result(first_dir),
        "Second question?": _ask_result(second_dir, query_id=OTHER_QUERY_ID, question="Second question?"),
    }
    with mock.patch.object(
        subprocess,
        "run",
        side_effect=lambda *a, **k: _completed(
            json.dumps(results[a[0][2]])
        ),
    ):
        summary = ask_and_bind_many(
            questions=[QUESTION, "Second question?"],
            historian_repo=historian_repo,
            output_dir=output_dir,
            endpoint="http://explicit.example/v1",
            historian_python=Path(sys.executable),
        )
    assert summary["status"] == "ok"
    assert summary["bound_count"] == 2
    assert [bound["historian_query_id"] for bound in summary["bound"]] == [
        QUERY_ID,
        OTHER_QUERY_ID,
    ]
    assert (output_dir / f"historian_context_{QUERY_ID}.json").is_file()
    assert (output_dir / f"historian_context_{OTHER_QUERY_ID}.json").is_file()


def test_multi_question_stops_at_first_failure(
    tmp_path: Path, historian_repo: Path
) -> None:
    first_dir = _make_query_dir(historian_repo, query_id=QUERY_ID)
    second_dir = _make_query_dir(
        historian_repo, query_id=OTHER_QUERY_ID, question="Second question?"
    )
    output_dir = tmp_path / "evidence"
    results = [
        json.dumps(_ask_result(first_dir)),
        json.dumps(_ask_result(second_dir, query_id=OTHER_QUERY_ID, question="Second question?", status="failed")),
    ]
    with mock.patch.object(
        subprocess, "run", side_effect=lambda *a, **k: _completed(results.pop(0))
    ):
        summary = ask_and_bind_many(
            questions=[QUESTION, "Second question?"],
            historian_repo=historian_repo,
            output_dir=output_dir,
            endpoint="http://explicit.example/v1",
            historian_python=Path(sys.executable),
        )
    assert summary["status"] == "failed"
    assert summary["failed_question_index"] == 1
    assert summary["failed_question"] == "Second question?"
    assert [bound["historian_query_id"] for bound in summary["bound"]] == [QUERY_ID]
    assert (output_dir / f"historian_context_{QUERY_ID}.json").is_file()
    assert not (output_dir / f"historian_context_{OTHER_QUERY_ID}.json").exists()


def test_cli_help_exits_zero() -> None:
    completed = subprocess.run(
        [sys.executable, os.fspath(SCRIPT), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    assert "ask-bind" in completed.stdout

def _write_stub_runtime(tmp_path: Path, result: dict[str, Any], *, require_endpoint: bool = True) -> Path:
    result_file = tmp_path / "stub-result.json"
    result_file.write_text(json.dumps(result), encoding="utf-8")
    stub = tmp_path / "stub-historian-python"
    lines = ["#!/bin/sh"]
    if require_endpoint:
        lines.extend(
            [
                'if [ -z "$HISTORIAN_REASONER_ENDPOINT" ]; then',
                '  echo "missing endpoint environment" >&2',
                "  exit 3",
                "fi",
            ]
        )
    lines.append(f"cat '{result_file}'")
    stub.write_text("\n".join(lines) + "\n", encoding="utf-8")
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return stub


def test_cli_end_to_end_with_stub_runtime(tmp_path: Path) -> None:
    historian_repo = _make_historian_repo(tmp_path, with_runtime=False)
    query_dir = _make_query_dir(historian_repo)
    output_dir = tmp_path / "evidence"
    result = _ask_result(query_dir)
    stub = _write_stub_runtime(tmp_path, result)

    completed = subprocess.run(
        [
            sys.executable,
            os.fspath(SCRIPT),
            "ask-bind",
            "--question",
            QUESTION,
            "--historian-repo",
            os.fspath(historian_repo),
            "--output-dir",
            os.fspath(output_dir),
            "--historian-python",
            os.fspath(stub),
            "--endpoint",
            "http://stub-endpoint.example/v1",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    assert summary["status"] == "ok"
    assert summary["bound_count"] == 1
    bound = summary["bound"][0]
    assert bound["historian_query_id"] == QUERY_ID
    assert bound["historian_query_dir"] == str(query_dir)
    assert bound["cited_record_ids"] == sorted(CITED_RECORDS)
    assert Path(bound["historian_context_path"]).is_file()


def test_cli_end_to_end_reports_historian_failure(tmp_path: Path) -> None:
    historian_repo = _make_historian_repo(tmp_path, with_runtime=False)
    query_dir = _make_query_dir(historian_repo)
    output_dir = tmp_path / "evidence"
    result = _ask_result(query_dir, status="failed")
    stub = _write_stub_runtime(tmp_path, result)

    completed = subprocess.run(
        [
            sys.executable,
            os.fspath(SCRIPT),
            "ask-bind",
            "--question",
            QUESTION,
            "--historian-repo",
            os.fspath(historian_repo),
            "--output-dir",
            os.fspath(output_dir),
            "--historian-python",
            os.fspath(stub),
            "--endpoint",
            "http://stub-endpoint.example/v1",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 1
    summary = json.loads(completed.stdout)
    assert summary["status"] == "failed"
    assert "reasoner_unavailable" in summary["error"]
    assert not output_dir.exists() or not any(output_dir.iterdir())


def test_main_requires_at_least_one_question(tmp_path: Path, historian_repo: Path) -> None:
    with pytest.raises(HistorianAskBindError, match="at least one question"):
        ask_and_bind_many(
            questions=[],
            historian_repo=historian_repo,
            output_dir=tmp_path / "evidence",
            endpoint="http://explicit.example/v1",
        )
