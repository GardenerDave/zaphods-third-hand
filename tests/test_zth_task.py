from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from local_harness import zth_task
from local_harness.agent_task_session import validate_task_session
from local_harness.agent_task_session_record import (
    record_execution,
    record_review,
)
from local_harness.historian_context_query import HistorianAskBindError
from local_harness.zth_preflight import (
    STATUS_FAIL,
    STATUS_PASS,
    GitStatus,
    HistorianBaseline,
    PreflightResult,
)


REPO_FILES = {
    "docs/DOGFOOD_RUNNER.md": "runner doc\n",
    "local_harness/README.md": "harness readme\n",
    "tests/test_placeholder.py": "# placeholder\n",
    ".work/keep.txt": "private\n",
    ".env.local": "export SOMETHING=1\n",
    "sources/note.md": "source\n",
    "outputs/note.md": "output\n",
    "config/secrets.json": "{}\n",
    "id_rsa": "key\n",
    "cert.pem": "cert\n",
}


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    for relative, content in REPO_FILES.items():
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    (repo / "empty_dir").mkdir(exist_ok=True)
    return repo


def make_preflight(status: str) -> PreflightResult:
    zth = GitStatus(
        repo=Path("/repo"),
        exists=True,
        git_repo=True,
        head="a" * 40 if status == STATUS_PASS else None,
        head_error=None,
        clean=True if status == STATUS_PASS else False,
        changed=() if status == STATUS_PASS else (("??", "dirty.txt"),),
        status_error=None,
        git_error=None,
    )
    historian = GitStatus(
        repo=Path("/historian"),
        exists=True,
        git_repo=True,
        head="b" * 40,
        head_error=None,
        clean=True,
        changed=(),
        status_error=None,
        git_error=None,
    )
    return PreflightResult(
        status=status,
        zth=zth,
        historian=historian,
        historian_baseline=HistorianBaseline(),
        checks=(),
        errors=() if status == STATUS_PASS else ("dirty worktree",),
    )


VALID_INTERPRETATION = {
    "goal": "Fix the ambiguous boundary wording in docs/DOGFOOD_RUNNER.md.",
    "candidate_allowed_paths": ["docs/DOGFOOD_RUNNER.md"],
    "non_goals": ["Do not change any runtime behavior."],
    "required_checks": [
        "python3 -m pytest tests/test_placeholder.py -q",
        "git diff --check",
    ],
    "historian_questions": [
        "Which wording decisions constrain boundary language in ZTH docs?"
    ],
    "reasoning_summary": "The objective names one document; the fix is a scoped wording change.",
    "uncertainties": ["Whether the exact bullet must stay a bullet list item."],
}


def fake_model_call(payload: dict[str, Any] | None = None):
    effective = json.dumps(payload if payload is not None else VALID_INTERPRETATION)

    def call(**_kwargs: Any) -> str:
        return effective

    return call


def fake_ask_bind(captured: list[Any] | None = None, questions_to_paths: dict[str, str] | None = None):
    paths = questions_to_paths or {
        question: f"ctx-{index}.json" for index, question in enumerate(["default"])
    }

    def bind(*, questions: list[str], output_dir: Path, **_kwargs: Any) -> dict[str, Any]:
        if captured is not None:
            captured.append(
                {
                    "questions": list(questions),
                    "output_dir": output_dir,
                }
            )
        bound = []
        for index, question in enumerate(questions):
            context_path = output_dir / paths.get(question, f"ctx-{index}.json")
            context_path.parent.mkdir(parents=True, exist_ok=True)
            context_path.write_text("{}", encoding="utf-8")
            markdown_path = context_path.with_suffix(".md")
            markdown_path.write_text("# ctx\n", encoding="utf-8")
            bound.append(
                {
                    "question": question,
                    "historian_query_id": f"op-q{index}",
                    "historian_query_dir": "/historian/.work/historian_queries/op-q" + str(index),
                    "historian_context_path": str(context_path),
                    "historian_context_markdown_path": str(markdown_path),
                    "cited_record_ids": [f"REC-{index}"],
                    "retrieval_corpus_fingerprint": "f" * 64,
                    "retrieval_revision": "0" * 40,
                }
            )
        return {"status": "ok", "bound": bound, "bound_count": len(bound)}

    return bind


def prepare(tmp_path: Path, **overrides: Any):
    repo = make_repo(tmp_path)
    work_root = repo / ".work" / "zth_tasks"
    session_root = tmp_path / "sessions"
    arguments: dict[str, Any] = dict(
        objective="Fix the pre-existing ambiguous authority wording reported by repo health in docs/DOGFOOD_RUNNER.md without changing runtime behavior.",
        historian_repo=tmp_path / "historian",
        zth_repo=repo,
        work_root=work_root,
        session_root=session_root,
        interpreter_endpoint="http://interpreter.invalid/v1",
        interpreter_model="test-model",
        model_call=fake_model_call(),
        preflight_runner=lambda **_kwargs: make_preflight(STATUS_PASS),
        ask_bind=fake_ask_bind(),
    )
    arguments.update(overrides)
    payload, exit_code = zth_task.prepare_task(**arguments)
    return SimpleNamespace(
        payload=payload,
        exit_code=exit_code,
        repo=repo,
        work_root=work_root,
        session_root=session_root,
        workspace=work_root / payload["task_id"],
    )


class TestPrepare:
    def test_prepare_success_end_to_end(self, tmp_path: Path) -> None:
        result = prepare(tmp_path)
        assert result.exit_code == 0
        assert result.payload["state"] == zth_task.STATE_READY_FOR_EXECUTION
        workspace = result.workspace
        for filename in (
            zth_task.OBJECTIVE_FILE,
            zth_task.PREFLIGHT_FILE,
            zth_task.INTERPRETATION_FILE,
            zth_task.SESSION_REF_FILE,
            zth_task.SUMMARY_FILE,
            zth_task.FAILURE_FILE,
        ):
            if filename == zth_task.FAILURE_FILE:
                assert not (workspace / filename).exists()
            else:
                assert (workspace / filename).is_file(), filename
        assert (workspace / "historian" / "index.json").is_file()
        session_ref = json.loads(
            (workspace / zth_task.SESSION_REF_FILE).read_text(encoding="utf-8")
        )
        session_dir = result.session_root / session_ref["session_task_id"]
        validation = validate_task_session(session_dir)
        assert list(validation.allowed_paths) == ["docs/DOGFOOD_RUNNER.md"]

    def test_objective_preserved_verbatim(self, tmp_path: Path) -> None:
        objective = (
            "Fix   the wording\nin docs/DOGFOOD_RUNNER.md   with odd spacing kept exactly."
        )
        result = prepare(tmp_path, objective=objective)
        assert result.exit_code == 0
        record = json.loads(
            (result.workspace / zth_task.OBJECTIVE_FILE).read_text(encoding="utf-8")
        )
        assert record["objective"] == objective
        import hashlib

        assert (
            record["objective_sha256"]
            == hashlib.sha256(objective.encode("utf-8")).hexdigest()
        )

    def test_task_id_unique_and_stable(self, tmp_path: Path) -> None:
        first = prepare(tmp_path)
        second = prepare(tmp_path)
        assert first.payload["task_id"] != second.payload["task_id"]
        for result in (first, second):
            record = json.loads(
                (result.workspace / zth_task.OBJECTIVE_FILE).read_text(encoding="utf-8")
            )
            assert record["task_id"] == result.workspace.name

    def test_preflight_failure_blocks(self, tmp_path: Path) -> None:
        result = prepare(
            tmp_path,
            preflight_runner=lambda **_kwargs: make_preflight(STATUS_FAIL),
        )
        assert result.exit_code == 1
        assert result.payload["state"] == zth_task.STATE_BLOCKED
        failure = json.loads(
            (result.workspace / zth_task.FAILURE_FILE).read_text(encoding="utf-8")
        )
        assert failure["stage"] == zth_task.STAGE_PREFLIGHT
        assert not (result.workspace / zth_task.SESSION_REF_FILE).exists()
        assert not result.session_root.exists() or not list(result.session_root.glob("*"))

    def test_missing_interpreter_configuration_blocks(self, tmp_path: Path) -> None:
        result = prepare(tmp_path, interpreter_endpoint=None, interpreter_model=None)
        assert result.exit_code == 1
        failure = json.loads(
            (result.workspace / zth_task.FAILURE_FILE).read_text(encoding="utf-8")
        )
        assert failure["stage"] == zth_task.STAGE_INTERPRETATION
        assert "ZTH_TASK_INTERPRETER_ENDPOINT" in failure["error"]

    def test_model_transport_failure_preserved(self, tmp_path: Path) -> None:
        def broken_call(**_kwargs: Any) -> str:
            raise zth_task.ZthTaskError("task interpreter endpoint call failed: refused")

        result = prepare(tmp_path, model_call=broken_call)
        assert result.exit_code == 1
        failure = json.loads(
            (result.workspace / zth_task.FAILURE_FILE).read_text(encoding="utf-8")
        )
        assert failure["stage"] == zth_task.STAGE_INTERPRETATION
        assert "refused" in failure["error"]

    def test_workspace_never_overwritten(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            zth_task, "_utc_now_iso", lambda **_kwargs: "2026-09-02T00:00:00Z"
        )
        first = prepare(tmp_path)
        with pytest.raises(zth_task.ZthTaskError, match="already exists"):
            zth_task.prepare_task(
                objective=first.payload["objective"],
                historian_repo=tmp_path / "historian",
                zth_repo=first.repo,
                work_root=first.work_root,
                session_root=first.session_root,
                interpreter_endpoint="http://interpreter.invalid/v1",
                interpreter_model="test-model",
                model_call=fake_model_call(),
                preflight_runner=lambda **_kwargs: make_preflight(STATUS_PASS),
                ask_bind=fake_ask_bind(),
            )


class TestSemanticInterpretation:
    def test_parse_valid(self) -> None:
        parsed = zth_task.parse_interpretation(json.dumps(VALID_INTERPRETATION))
        assert parsed["goal"] == VALID_INTERPRETATION["goal"]
        assert parsed["candidate_allowed_paths"] == ["docs/DOGFOOD_RUNNER.md"]

    def test_malformed_json_fails_closed(self) -> None:
        with pytest.raises(zth_task.ZthTaskError, match="not valid JSON"):
            zth_task.parse_interpretation("this is not json {")

    def test_missing_goal_rejected(self) -> None:
        payload = {key: value for key, value in VALID_INTERPRETATION.items()}
        payload["goal"] = "   "
        with pytest.raises(zth_task.ZthTaskError, match="goal"):
            zth_task.parse_interpretation(json.dumps(payload))

    def test_empty_candidate_paths_rejected(self) -> None:
        payload = dict(VALID_INTERPRETATION)
        payload["candidate_allowed_paths"] = []
        with pytest.raises(zth_task.ZthTaskError, match="candidate_allowed_paths"):
            zth_task.parse_interpretation(json.dumps(payload))

    def test_missing_checks_rejected(self) -> None:
        payload = dict(VALID_INTERPRETATION)
        payload["required_checks"] = []
        with pytest.raises(zth_task.ZthTaskError, match="empty verification plan|required_checks"):
            zth_task.parse_interpretation(json.dumps(payload))

    @pytest.mark.parametrize(
        "field", ["execution_authority", "approved", "auto_commit", "extra_notes"]
    )
    def test_authority_and_unknown_fields_rejected(self, field: str) -> None:
        payload = dict(VALID_INTERPRETATION)
        payload[field] = True
        with pytest.raises(zth_task.ZthTaskError) as excinfo:
            zth_task.parse_interpretation(json.dumps(payload))
        message = str(excinfo.value)
        assert "failing closed" in message
        if field != "extra_notes":
            assert "authority-bearing" in message

    def test_too_many_historian_questions_rejected(self) -> None:
        payload = dict(VALID_INTERPRETATION)
        payload["historian_questions"] = [f"q{i}" for i in range(6)]
        with pytest.raises(zth_task.ZthTaskError, match="bounded maximum"):
            zth_task.parse_interpretation(json.dumps(payload))

    def test_invalid_interpretation_failure_preserves_raw_output(self, tmp_path: Path) -> None:
        result = prepare(tmp_path, model_call=fake_model_call({"goal": "only goal"}))
        assert result.exit_code == 1
        failure = json.loads(
            (result.workspace / zth_task.FAILURE_FILE).read_text(encoding="utf-8")
        )
        assert failure["stage"] == zth_task.STAGE_INTERPRETATION
        assert failure["raw_model_output"] == json.dumps({"goal": "only goal"})
        assert not (result.workspace / zth_task.INTERPRETATION_FILE).exists()


class TestHistorianIntegration:
    def test_questions_forwarded_and_context_bound(self, tmp_path: Path) -> None:
        captured: list[Any] = []
        result = prepare(tmp_path, ask_bind=fake_ask_bind(captured))
        assert result.exit_code == 0
        assert len(captured) == 1
        assert captured[0]["questions"] == VALID_INTERPRETATION["historian_questions"]
        assert captured[0]["output_dir"] == result.workspace / "historian"
        index = json.loads(
            (result.workspace / "historian" / "index.json").read_text(encoding="utf-8")
        )
        assert index["bound_count"] == 1
        assert index["contexts"][0]["historian_query_id"] == "op-q0"
        assert index["contexts"][0]["cited_record_ids"] == ["REC-0"]
        assert index["advisory"].startswith("Historian answers are advisory")

    def test_context_references_in_packet(self, tmp_path: Path) -> None:
        result = prepare(tmp_path)
        session_ref = json.loads(
            (result.workspace / zth_task.SESSION_REF_FILE).read_text(encoding="utf-8")
        )
        session_dir = result.session_root / session_ref["session_task_id"]
        metadata = json.loads((session_dir / "task.yaml").read_text(encoding="utf-8"))
        assert metadata["context_references"] == [
            ".work/zth_tasks/" + result.payload["task_id"] + "/historian/index.json",
            ".work/zth_tasks/" + result.payload["task_id"] + "/historian/ctx-0.json",
        ]
        prompt = (session_dir / "codex_prompt.md").read_text(encoding="utf-8")
        assert "## Context Evidence References" in prompt
        assert "## Non-Goals" in prompt

    def test_zero_questions_binds_no_context(self, tmp_path: Path) -> None:
        payload = dict(VALID_INTERPRETATION)
        payload["historian_questions"] = []
        result = prepare(tmp_path, model_call=fake_model_call(payload))
        assert result.exit_code == 0
        index = json.loads(
            (result.workspace / "historian" / "index.json").read_text(encoding="utf-8")
        )
        assert index["bound_count"] == 0
        assert index["questions_asked"] == 0

    def test_historian_failure_blocks(self, tmp_path: Path) -> None:
        def broken_bind(**_kwargs: Any) -> dict[str, Any]:
            raise HistorianAskBindError("missing runtime")

        result = prepare(tmp_path, ask_bind=broken_bind)
        assert result.exit_code == 1
        failure = json.loads(
            (result.workspace / zth_task.FAILURE_FILE).read_text(encoding="utf-8")
        )
        assert failure["stage"] == zth_task.STAGE_HISTORIAN
        assert "missing runtime" in failure["error"]
        assert not (result.workspace / zth_task.SESSION_REF_FILE).exists()

    def test_historian_status_failed_blocks(self, tmp_path: Path) -> None:
        def failing_bind(**_kwargs: Any) -> dict[str, Any]:
            return {"status": "failed", "bound": [], "error": "Historian rejected the question"}

        result = prepare(tmp_path, ask_bind=failing_bind)
        assert result.exit_code == 1
        failure = json.loads(
            (result.workspace / zth_task.FAILURE_FILE).read_text(encoding="utf-8")
        )
        assert failure["stage"] == zth_task.STAGE_HISTORIAN


class TestScopeBinding:
    @pytest.mark.parametrize(
        "candidate",
        [
            "../outside.py",
            "/absolute/path.py",
            ".git/config",
            "docs/*.md",
            "docs/DOGFOOD_RUNNER.md?",
            ".work/new_target.txt",
            "sources/note.md",
            "outputs/note.md",
            ".env.local",
            ".env.production",
            "config/secrets.json",
            "id_rsa",
            "cert.pem",
            "missing_dir/new_file.py",
        ],
    )
    def test_unsafe_candidates_rejected(self, candidate: str, tmp_path: Path) -> None:
        repo = make_repo(tmp_path)
        with pytest.raises(zth_task.ZthTaskError):
            zth_task.validate_candidate_path(repo, candidate)

    def test_existing_file_and_new_file_under_existing_dir_accepted(self, tmp_path: Path) -> None:
        repo = make_repo(tmp_path)
        assert (
            zth_task.validate_candidate_path(repo, "docs/DOGFOOD_RUNNER.md")
            == "docs/DOGFOOD_RUNNER.md"
        )
        assert (
            zth_task.validate_candidate_path(repo, "docs/new_file.md")
            == "docs/new_file.md"
        )

    def test_scope_failure_blocks_and_holds_paths(self, tmp_path: Path) -> None:
        payload = dict(VALID_INTERPRETATION)
        payload["candidate_allowed_paths"] = [
            "docs/DOGFOOD_RUNNER.md",
            ".env.local",
            "docs/*.md",
        ]
        result = prepare(tmp_path, model_call=fake_model_call(payload))
        assert result.exit_code == 1
        failure = json.loads(
            (result.workspace / zth_task.FAILURE_FILE).read_text(encoding="utf-8")
        )
        assert failure["stage"] == zth_task.STAGE_SCOPE_BINDING
        assert ".env.local" in failure["error"]
        assert "wildcard" in failure["error"]
        assert not result.session_root.exists() or not any(result.session_root.iterdir())

    def test_final_session_uses_deterministic_bound_scope(self, tmp_path: Path) -> None:
        payload = dict(VALID_INTERPRETATION)
        payload["candidate_allowed_paths"] = ["docs/DOGFOOD_RUNNER.md", "docs/"]
        payload["required_checks"] = [
            "python3 -m pytest tests/test_placeholder.py -q",
            "git diff --check",
        ]
        result = prepare(tmp_path, model_call=fake_model_call(payload))
        assert result.exit_code == 0
        session_ref = json.loads(
            (result.workspace / zth_task.SESSION_REF_FILE).read_text(encoding="utf-8")
        )
        metadata = json.loads(
            (
                result.session_root / session_ref["session_task_id"] / "task.yaml"
            ).read_text(encoding="utf-8")
        )
        assert metadata["allowed_paths"] == ["docs/DOGFOOD_RUNNER.md", "docs"]
        assert metadata["required_checks"] == payload["required_checks"]

    def test_semantic_proposal_preserved_separately_from_packet(self, tmp_path: Path) -> None:
        result = prepare(tmp_path)
        interpretation = json.loads(
            (result.workspace / zth_task.INTERPRETATION_FILE).read_text(encoding="utf-8")
        )
        assert interpretation["authority"].startswith("advisory")
        assert interpretation["advisory"] == zth_task.validate_interpretation(
            VALID_INTERPRETATION
        )
        session_ref = json.loads(
            (result.workspace / zth_task.SESSION_REF_FILE).read_text(encoding="utf-8")
        )
        assert session_ref["session_task_id"] != result.payload["task_id"]


class TestStatusAndResume:
    def test_status_ready_for_execution(self, tmp_path: Path) -> None:
        result = prepare(tmp_path)
        status = zth_task.derive_task_status(
            result.payload["task_id"], work_root=result.work_root
        )
        assert status["state"] == zth_task.STATE_READY_FOR_EXECUTION
        assert status["task_session"]["task_id"] == json.loads(
            (result.workspace / zth_task.SESSION_REF_FILE).read_text(encoding="utf-8")
        )["session_task_id"]
        assert "handoff" in status["next_action"]

    def test_status_states_from_partial_artifacts(self, tmp_path: Path) -> None:
        result = prepare(tmp_path)
        workspace = result.workspace
        task_id = result.payload["task_id"]
        (workspace / zth_task.SESSION_REF_FILE).unlink()
        (workspace / "historian" / "index.json").unlink()
        status = zth_task.derive_task_status(task_id, work_root=result.work_root)
        assert status["state"] == zth_task.STATE_CREATED
        (workspace / "historian" / "index.json").write_text("{}", encoding="utf-8")
        status = zth_task.derive_task_status(task_id, work_root=result.work_root)
        assert status["state"] == zth_task.STATE_CONTEXT_BOUND

    def test_status_missing_task_fails_clearly(self, tmp_path: Path) -> None:
        with pytest.raises(zth_task.ZthTaskError, match="no front-door task workspace"):
            zth_task.derive_task_status("zth-task-missing-00000000", work_root=tmp_path)

    def test_status_corrupt_artifact_fails_clearly(self, tmp_path: Path) -> None:
        result = prepare(tmp_path)
        (result.workspace / zth_task.OBJECTIVE_FILE).write_text("{not json", encoding="utf-8")
        with pytest.raises(zth_task.ZthTaskError, match="corrupt objective artifact"):
            zth_task.derive_task_status(
                result.payload["task_id"], work_root=result.work_root
            )

    def test_status_blocked_on_failure_record(self, tmp_path: Path) -> None:
        result = prepare(
            tmp_path, preflight_runner=lambda **_kwargs: make_preflight(STATUS_FAIL)
        )
        status = zth_task.derive_task_status(
            result.payload["task_id"], work_root=result.work_root
        )
        assert status["state"] == zth_task.STATE_BLOCKED
        assert status["failure"]["stage"] == zth_task.STAGE_PREFLIGHT
        assert "never auto-repairs" in status["next_action"]

    def test_execution_and_review_discovered_through_real_recorder(self, tmp_path: Path) -> None:
        result = prepare(tmp_path)
        session_ref = json.loads(
            (result.workspace / zth_task.SESSION_REF_FILE).read_text(encoding="utf-8")
        )
        session_dir = result.session_root / session_ref["session_task_id"]
        record_execution(
            session_dir=session_dir,
            outcomes=["passed: 1 test", "clean"],
            evidence_files=[str(result.workspace / zth_task.INTERPRETATION_FILE)],
        )
        status = zth_task.derive_task_status(
            result.payload["task_id"], work_root=result.work_root
        )
        assert status["state"] == zth_task.STATE_EXECUTED
        assert status["executions"]
        assert status["review"]["decision"] is None
        assert "pending human review" in status["next_action"] or "record-review" in status["next_action"]
        record_review(
            session_dir=session_dir,
            decision="revision_requested",
            reviewer="test-human",
            reason="needs one more wording pass",
        )
        status = zth_task.derive_task_status(
            result.payload["task_id"], work_root=result.work_root
        )
        assert status["state"] == zth_task.STATE_REVIEWED
        assert status["review"]["decision"] == "revision_requested"
        assert "not lifecycle promotion" in status["next_action"]

    def test_status_reports_drifted_evidence_instead_of_executed(self, tmp_path: Path) -> None:
        result = prepare(tmp_path)
        session_ref = json.loads(
            (result.workspace / zth_task.SESSION_REF_FILE).read_text(encoding="utf-8")
        )
        session_dir = result.session_root / session_ref["session_task_id"]
        evidence = tmp_path / "check_output.txt"
        evidence.write_text("passed: 1 test\nclean\n", encoding="utf-8")
        record_execution(
            session_dir=session_dir,
            outcomes=["passed: 1 test", "clean"],
            evidence_files=[str(evidence)],
        )
        evidence.write_text("drifted", encoding="utf-8")
        status = zth_task.derive_task_status(
            result.payload["task_id"], work_root=result.work_root
        )
        assert status["state"] == zth_task.STATE_BLOCKED
        assert "no longer validates" in status["blocked_reason"]


class TestAuthorityBoundaries:
    def test_preparation_outputs_carry_authority_boundaries(self, tmp_path: Path) -> None:
        result = prepare(tmp_path)
        for artifact in (
            json.loads((result.workspace / zth_task.OBJECTIVE_FILE).read_text(encoding="utf-8")),
            json.loads((result.workspace / zth_task.INTERPRETATION_FILE).read_text(encoding="utf-8")),
            json.loads((result.workspace / zth_task.SESSION_REF_FILE).read_text(encoding="utf-8")),
        ):
            assert artifact["boundaries"] == list(zth_task.FRONTDOOR_BOUNDARIES)
        session_ref = json.loads(
            (result.workspace / zth_task.SESSION_REF_FILE).read_text(encoding="utf-8")
        )
        metadata = json.loads(
            (
                result.session_root / session_ref["session_task_id"] / "task.yaml"
            ).read_text(encoding="utf-8")
        )
        assert metadata["authority_granted"] is False
        assert metadata["requires_human_review"] is True

    def test_preflight_pass_is_not_authority(self, tmp_path: Path) -> None:
        result = prepare(tmp_path)
        objective_record = json.loads(
            (result.workspace / zth_task.OBJECTIVE_FILE).read_text(encoding="utf-8")
        )
        assert objective_record["boundaries"][3].startswith("A passing preflight is an observation")
        assert result.payload["boundaries"] == list(zth_task.FRONTDOOR_BOUNDARIES)

    def test_summary_text_states_no_authority(self, tmp_path: Path) -> None:
        result = prepare(tmp_path)
        text = render = zth_task.render_summary_text(result.payload)
        assert "STATUS: READY_FOR_EXECUTION" in text
        assert "grants no execution authority" in text


class TestHandoff:
    def test_handoff_emits_packet_and_record_command(self, tmp_path: Path) -> None:
        result = prepare(tmp_path)
        payload, exit_code = zth_task.handoff_task(
            result.payload["task_id"], work_root=result.work_root
        )
        assert exit_code == 0
        session_dir = payload["task_session"]["dir"]
        assert payload["handoff"]["agent_prompt_path"] == session_dir + "/codex_prompt.md"
        assert "record-execution" in payload["handoff"]["record_execution_command"]
        assert payload["handoff"]["record_execution_command"].count("--outcome") == 2

    def test_handoff_refuses_unready_task(self, tmp_path: Path) -> None:
        result = prepare(
            tmp_path, preflight_runner=lambda **_kwargs: make_preflight(STATUS_FAIL)
        )
        with pytest.raises(zth_task.ZthTaskError, match="execution-ready"):
            zth_task.handoff_task(result.payload["task_id"], work_root=result.work_root)

    def test_handoff_refuses_created_task(self, tmp_path: Path) -> None:
        result = prepare(tmp_path)
        (result.workspace / zth_task.SESSION_REF_FILE).unlink()
        (result.workspace / "historian" / "index.json").unlink()
        with pytest.raises(zth_task.ZthTaskError, match="execution-ready"):
            zth_task.handoff_task(result.payload["task_id"], work_root=result.work_root)


class TestInterpreterCall:
    def test_call_interpreter_model_contract(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, Any] = {}

        class FakeResponse:
            def __init__(self, body: bytes) -> None:
                self._body = body

            def read(self) -> bytes:
                return self._body

            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *_args: Any) -> None:
                return None

        def fake_urlopen(request: Any, timeout: int) -> FakeResponse:
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse(
                json.dumps(
                    {"choices": [{"message": {"content": '{"goal": "ok"}'}}]}
                ).encode("utf-8")
            )

        monkeypatch.setattr(zth_task.urllib.request, "urlopen", fake_urlopen)
        content = zth_task.call_interpreter_model(
            endpoint="http://endpoint.invalid/v1/",
            model="m",
            system_prompt="s",
            user_prompt="u",
            max_tokens=128,
            timeout_seconds=30,
        )
        assert content == '{"goal": "ok"}'
        assert captured["url"] == "http://endpoint.invalid/v1/chat/completions"
        assert captured["timeout"] == 30
        assert captured["payload"]["temperature"] == 0
        assert captured["payload"]["seed"] == 42
        assert captured["payload"]["stream"] is False
        assert (
            captured["payload"]["response_format"]["json_schema"]["name"]
            == "zth_task_interpretation"
        )

    def test_call_interpreter_model_http_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import urllib.error

        def fake_urlopen(request: Any, timeout: int) -> Any:
            raise urllib.error.HTTPError(
                request.full_url, 500, "boom", hdrs=None, fp=None
            )

        monkeypatch.setattr(zth_task.urllib.request, "urlopen", fake_urlopen)
        with pytest.raises(zth_task.ZthTaskError, match="HTTP 500"):
            zth_task.call_interpreter_model(
                endpoint="http://endpoint.invalid/v1",
                model="m",
                system_prompt="s",
                user_prompt="u",
                max_tokens=16,
                timeout_seconds=5,
            )


class TestCli:
    def test_cli_prepare_and_status(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        repo = make_repo(tmp_path)
        work_root = repo / ".work" / "zth_tasks"
        session_root = tmp_path / "sessions"
        monkeypatch.setenv("ZTH_TASK_INTERPRETER_ENDPOINT", "http://interpreter.invalid/v1")
        monkeypatch.setenv("ZTH_TASK_INTERPRETER_MODEL", "test-model")
        original_prepare = zth_task.prepare_task

        def redirected_prepare(**kwargs: Any) -> tuple[dict[str, Any], int]:
            return original_prepare(
                **{
                    **kwargs,
                    "zth_repo": repo,
                    "work_root": work_root,
                    "session_root": session_root,
                    "model_call": fake_model_call(),
                    "preflight_runner": lambda **_kwargs: make_preflight(STATUS_PASS),
                    "ask_bind": fake_ask_bind(),
                }
            )

        monkeypatch.setattr(zth_task, "prepare_task", redirected_prepare)
        original_status = zth_task.derive_task_status

        def redirected_status(task_id: str, **kwargs: Any) -> dict[str, Any]:
            return original_status(task_id, work_root=work_root)

        monkeypatch.setattr(zth_task, "derive_task_status", redirected_status)
        exit_code = zth_task.main(
            [
                "prepare",
                "Fix the wording in docs/DOGFOOD_RUNNER.md.",
                "--historian-repo",
                str(tmp_path / "historian"),
                "--json",
            ]
        )
        assert exit_code == 0
        workspaces = list(work_root.glob("*"))
        assert len(workspaces) == 1
        task_id = workspaces[0].name
        status_code = zth_task.main(["status", task_id, "--json"])
        assert status_code == 0

    def test_cli_bare_objective_defaults_to_prepare(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen: dict[str, Any] = {}

        def fake_prepare(**kwargs: Any) -> tuple[dict[str, Any], int]:
            seen.update(kwargs)
            return {"task_id": "zth-task-x-12345678", "state": "ready_for_execution"}, 0

        monkeypatch.setattr(zth_task, "prepare_task", fake_prepare)
        exit_code = zth_task.main(
            [
                "Fix the wording in docs/DOGFOOD_RUNNER.md.",
                "--historian-repo",
                str(tmp_path / "historian"),
            ]
        )
        assert exit_code == 0
        assert seen["objective"] == "Fix the wording in docs/DOGFOOD_RUNNER.md."

    def test_cli_status_unknown_task(self, capsys: pytest.CaptureFixture[str]) -> None:
        exit_code = zth_task.main(["status", "zth-task-unknown-00000000"])
        assert exit_code == 1
        assert "error" in capsys.readouterr().err
