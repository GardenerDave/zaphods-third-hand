import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock


sys.path.insert(0, os.fspath(Path(__file__).resolve().parents[1]))

import agent_task_session
import agent_task_session_record


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "local_harness" / "agent_task_session_record.py"

FROZEN_NOW = datetime(2026, 9, 2, 4, 15, 30, tzinfo=timezone.utc)


class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return FROZEN_NOW


class AgentTaskSessionRecordTests(unittest.TestCase):
    def create_session(self, root: Path, **overrides):
        arguments = {
            "name": "Add focused parser validation",
            "goal": "Add parser checks without changing unrelated behavior.",
            "branch": "agent-task-parser-validation",
            "allowed_paths": [
                "local_harness/example.py",
                "local_harness/tests/test_example.py",
            ],
            "required_checks": [
                "python3 -m pytest local_harness/tests/test_example.py",
                "python3 local_harness/repo_health_check.py",
            ],
            "session_root": root,
        }
        arguments.update(overrides)
        return agent_task_session.create_task_session(**arguments)

    def setUp(self):
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary_directory.cleanup)
        self.root = Path(self._temporary_directory.name)
        self.session = self.create_session(self.root)
        self.session_dir = self.session.output_dir

    def record_execution(self, **overrides):
        arguments = {
            "session_dir": self.session_dir,
            "outcomes": ["passed: 3 tests", "passed: health ok"],
        }
        arguments.update(overrides)
        return agent_task_session_record.record_execution(**arguments)

    def record_review(self, **overrides):
        arguments = {
            "session_dir": self.session_dir,
            "decision": "accepted",
            "reviewer": "operator-one",
            "reason": "checks and evidence reviewed",
        }
        arguments.update(overrides)
        return agent_task_session_record.record_review(**arguments)

    def test_record_execution_writes_valid_record(self):
        payload = self.record_execution(
            evidence_files=[str(ROOT / "docs" / "AGENT_TASK_SESSION.md")],
            note="implementation and focused tests complete",
        )
        record_path = self.session_dir / "execution" / f"{payload['execution_id']}.json"
        self.assertTrue(record_path.is_file())
        stored = json.loads(record_path.read_text(encoding="utf-8"))
        self.assertEqual(
            stored["schema_version"],
            agent_task_session_record.EXECUTION_RECORD_SCHEMA,
        )
        self.assertEqual(stored["task_id"], self.session.task_id)
        self.assertEqual(
            [entry["command"] for entry in stored["checks"]],
            list(self.session.required_checks),
        )
        self.assertEqual(
            [entry["outcome"] for entry in stored["checks"]],
            ["passed: 3 tests", "passed: health ok"],
        )
        self.assertEqual(len(stored["evidence_files"]), 1)
        evidence = stored["evidence_files"][0]
        self.assertEqual(
            evidence["repo_relative"], "docs/AGENT_TASK_SESSION.md"
        )
        self.assertEqual(
            evidence["sha256"],
            agent_task_session_record._sha256_file(
                ROOT / "docs" / "AGENT_TASK_SESSION.md"
            ),
        )
        self.assertEqual(stored["note"], "implementation and focused tests complete")
        self.assertEqual(
            stored["authority_boundaries"],
            list(agent_task_session_record.RECORD_BOUNDARIES),
        )

    def test_record_execution_does_not_mutate_source_packet(self):
        before = {
            path.name: path.read_bytes()
            for path in self.session_dir.iterdir()
            if path.is_file()
        }
        self.record_execution()
        after = {
            path.name: path.read_bytes()
            for path in self.session_dir.iterdir()
            if path.is_file()
        }
        for name, payload in before.items():
            self.assertEqual(after[name], payload)
        metadata = json.loads((self.session_dir / "task.yaml").read_text(encoding="utf-8"))
        self.assertEqual(metadata["status"], "draft")
        self.assertFalse(metadata["authority_granted"])

    def test_record_execution_requires_one_outcome_per_check(self):
        with self.assertRaises(agent_task_session_record.SessionRecordError) as raised:
            self.record_execution(outcomes=["passed: only one"])
        self.assertIn("one outcome per required check", str(raised.exception))
        self.assertFalse((self.session_dir / "execution").exists())

    def test_record_execution_rejects_empty_outcome(self):
        with self.assertRaises(agent_task_session_record.SessionRecordError):
            self.record_execution(outcomes=["passed: ok", "   "])

    def test_record_execution_rejects_missing_evidence_file(self):
        with self.assertRaises(agent_task_session_record.SessionRecordError) as raised:
            self.record_execution(evidence_files=[str(self.root / "missing.md")])
        self.assertIn("does not exist", str(raised.exception))

    def test_record_execution_fails_closed_on_invalid_base_session(self):
        (self.session_dir / "task.yaml").write_text("{}", encoding="utf-8")
        with self.assertRaises(agent_task_session_record.SessionRecordError) as raised:
            self.record_execution()
        self.assertIn("base task session is invalid", str(raised.exception))

    def test_record_execution_same_second_ids_do_not_collide(self):
        with mock.patch.object(agent_task_session_record, "datetime", FrozenDatetime):
            first = self.record_execution()
            second = self.record_execution(
                outcomes=["passed: rerun after rework", "passed: health ok"]
            )
        self.assertEqual(first["execution_id"], "execution_20260902t041530z")
        self.assertEqual(second["execution_id"], "execution_20260902t041530z-000001")
        validation = agent_task_session_record.validate_session_records(self.session_dir)
        self.assertEqual(
            validation.execution_ids,
            ("execution_20260902t041530z", "execution_20260902t041530z-000001"),
        )

    def test_validate_draft_session_has_no_records(self):
        validation = agent_task_session_record.validate_session_records(self.session_dir)
        self.assertEqual(validation.stage, agent_task_session_record.STAGE_DRAFT)
        self.assertEqual(validation.execution_count, 0)
        self.assertEqual(validation.review_count, 0)
        self.assertIsNone(validation.effective_review_decision)
        self.assertEqual(validation.required_checks, self.session.required_checks)

    def test_validate_executed_session_derives_stage(self):
        self.record_execution()
        validation = agent_task_session_record.validate_session_records(self.session_dir)
        self.assertEqual(validation.stage, agent_task_session_record.STAGE_EXECUTED)
        self.assertEqual(validation.execution_count, 1)
        self.assertIsNone(validation.effective_review_decision)

    def test_validate_reviewed_session_derives_effective_decision(self):
        self.record_execution()
        self.record_review()
        validation = agent_task_session_record.validate_session_records(self.session_dir)
        self.assertEqual(validation.stage, agent_task_session_record.STAGE_REVIEWED)
        self.assertEqual(validation.effective_review_decision, "accepted")
        self.assertEqual(validation.review_count, 1)

    def test_validate_fails_closed_when_evidence_file_drifts(self):
        evidence = self.root / "evidence.md"
        evidence.write_text("original evidence\n", encoding="utf-8")
        self.record_execution(evidence_files=[str(evidence)])
        evidence.write_text("tampered evidence\n", encoding="utf-8")
        with self.assertRaises(agent_task_session_record.SessionRecordError) as raised:
            agent_task_session_record.validate_session_records(self.session_dir)
        self.assertIn("drifted from its recorded hash", str(raised.exception))

    def test_validate_fails_closed_when_evidence_file_is_deleted(self):
        evidence = self.root / "evidence.md"
        evidence.write_text("original evidence\n", encoding="utf-8")
        self.record_execution(evidence_files=[str(evidence)])
        evidence.unlink()
        with self.assertRaises(agent_task_session_record.SessionRecordError) as raised:
            agent_task_session_record.validate_session_records(self.session_dir)
        self.assertIn("no longer exists", str(raised.exception))

    def test_validate_fails_closed_when_task_yaml_drifts(self):
        self.record_execution()
        task_yaml = self.session_dir / "task.yaml"
        original = task_yaml.read_text(encoding="utf-8")
        task_yaml.write_text(original + " ", encoding="utf-8")
        with self.assertRaises(agent_task_session_record.SessionRecordError) as raised:
            agent_task_session_record.validate_session_records(self.session_dir)
        self.assertIn("task.yaml drifted", str(raised.exception))

    def test_validate_fails_closed_when_task_yaml_content_changes(self):
        self.record_execution()
        task_yaml = self.session_dir / "task.yaml"
        metadata = json.loads(task_yaml.read_text(encoding="utf-8"))
        metadata["goal"] = "changed after execution"
        task_yaml.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaises(agent_task_session_record.SessionRecordError) as raised:
            agent_task_session_record.validate_session_records(self.session_dir)
        self.assertIn("base task session is invalid", str(raised.exception))

    def test_validate_fails_closed_on_tampered_record_boundaries(self):
        self.record_execution()
        record_path = next((self.session_dir / "execution").iterdir())
        payload = json.loads(record_path.read_text(encoding="utf-8"))
        payload["authority_boundaries"] = ["Execution authority granted."]
        record_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaises(agent_task_session_record.SessionRecordError) as raised:
            agent_task_session_record.validate_session_records(self.session_dir)
        self.assertIn("authority boundaries mismatch", str(raised.exception))

    def test_validate_fails_closed_on_unexpected_execution_file(self):
        self.record_execution()
        (self.session_dir / "execution" / "notes.txt").write_text("stray\n", encoding="utf-8")
        with self.assertRaises(agent_task_session_record.SessionRecordError) as raised:
            agent_task_session_record.validate_session_records(self.session_dir)
        self.assertIn("unexpected file in execution record directory", str(raised.exception))

    def test_record_review_requires_execution_evidence_first(self):
        with self.assertRaises(agent_task_session_record.SessionRecordError) as raised:
            self.record_review()
        self.assertIn("before execution evidence exists", str(raised.exception))
        self.assertFalse((self.session_dir / "review").exists())

    def test_record_review_rejects_unknown_decision(self):
        self.record_execution()
        with self.assertRaises(agent_task_session_record.SessionRecordError):
            self.record_review(decision="promoted")

    def test_record_review_rejects_blank_reviewer_and_reason(self):
        self.record_execution()
        with self.assertRaises(agent_task_session_record.SessionRecordError):
            self.record_review(reviewer="   ")
        with self.assertRaises(agent_task_session_record.SessionRecordError):
            self.record_review(reason="")

    def test_record_review_rejects_unknown_execution_id(self):
        self.record_execution()
        with self.assertRaises(agent_task_session_record.SessionRecordError) as raised:
            self.record_review(execution_id="execution_19990101t000000z")
        self.assertIn("execution id not found", str(raised.exception))

    def test_record_review_binds_explicit_execution_id(self):
        first = self.record_execution()
        second = self.record_execution(
            outcomes=["passed: rerun", "passed: health ok"]
        )
        payload = self.record_review(execution_id=first["execution_id"])
        self.assertEqual(payload["execution_id"], first["execution_id"])
        self.assertEqual(payload["execution_binding"], "explicit")
        self.assertNotEqual(payload["execution_id"], second["execution_id"])

    def test_record_review_second_decision_requires_supersedes(self):
        self.record_execution()
        first = self.record_review(decision="revision_requested")
        with self.assertRaises(agent_task_session_record.SessionRecordError) as raised:
            self.record_review(decision="accepted")
        self.assertIn(first["review_id"], str(raised.exception))
        self.assertIn("supersedes", str(raised.exception))

    def test_record_review_supersedes_must_target_latest_decision(self):
        self.record_execution()
        first = self.record_review(decision="revision_requested")
        second = self.record_review(
            decision="accepted", supersedes=first["review_id"]
        )
        with self.assertRaises(agent_task_session_record.SessionRecordError) as raised:
            self.record_review(decision="rejected", supersedes=first["review_id"])
        self.assertIn("must supersede the latest review decision", str(raised.exception))
        validation = agent_task_session_record.validate_session_records(self.session_dir)
        self.assertEqual(validation.effective_review_decision, "accepted")
        self.assertEqual(
            validation.review_ids,
            (first["review_id"], second["review_id"]),
        )

    def test_record_review_first_decision_must_not_supersede(self):
        self.record_execution()
        with self.assertRaises(agent_task_session_record.SessionRecordError) as raised:
            self.record_review(supersedes="review_19990101t000000z")
        self.assertIn("no existing review decision to supersede", str(raised.exception))

    def test_review_chain_survives_same_second_decisions(self):
        with mock.patch.object(agent_task_session_record, "datetime", FrozenDatetime):
            self.record_execution()
            first = self.record_review(decision="revision_requested")
            second = self.record_review(decision="accepted", supersedes=first["review_id"])
        self.assertEqual(second["review_id"], "review_20260902t041530z-000001")
        validation = agent_task_session_record.validate_session_records(self.session_dir)
        self.assertEqual(validation.effective_review_decision, "accepted")
        self.assertEqual(validation.review_count, 2)

    def test_validate_fails_closed_when_bound_execution_record_changes(self):
        self.record_execution()
        self.record_review()
        execution_path = next((self.session_dir / "execution").iterdir())
        payload = json.loads(execution_path.read_text(encoding="utf-8"))
        payload["note"] = "rewritten after review"
        execution_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaises(agent_task_session_record.SessionRecordError) as raised:
            agent_task_session_record.validate_session_records(self.session_dir)
        self.assertIn("execution hash mismatch", str(raised.exception))

    def test_validate_fails_closed_when_review_binds_missing_execution(self):
        self.record_execution()
        self.record_review()
        for path in (self.session_dir / "execution").iterdir():
            path.unlink()
        with self.assertRaises(agent_task_session_record.SessionRecordError):
            agent_task_session_record.validate_session_records(self.session_dir)


class AgentTaskSessionRecordCLITests(unittest.TestCase):
    def run_script(self, *args):
        return subprocess.run(
            [sys.executable, os.fspath(SCRIPT), *map(str, args)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def setUp(self):
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary_directory.cleanup)
        self.root = Path(self._temporary_directory.name)
        session = agent_task_session.create_task_session(
            name="CLI coverage",
            goal="Cover the record CLI surface.",
            branch="cli-coverage",
            allowed_paths=["docs/example.md"],
            required_checks=["python3 -m pytest docs/test_example.py"],
            session_root=self.root,
        )
        self.session_dir = session.output_dir

    def test_cli_record_execution_validate_and_review(self):
        recorded = self.run_script(
            "record-execution",
            self.session_dir,
            "--outcome",
            "passed: 1 test",
            "--json",
        )
        self.assertEqual(recorded.returncode, 0, recorded.stderr)
        payload = json.loads(recorded.stdout)
        self.assertEqual(payload["task_id"], json.loads(
            (self.session_dir / "task.yaml").read_text(encoding="utf-8")
        )["task_id"])
        self.assertEqual(payload["evidence_file_count"], 0)
        self.assertTrue(Path(payload["execution_record_path"]).is_file())

        validated = self.run_script("validate", self.session_dir, "--json")
        self.assertEqual(validated.returncode, 0, validated.stderr)
        validation = json.loads(validated.stdout)
        self.assertEqual(validation["stage"], "executed")
        self.assertTrue(validation["valid"])

        reviewed = self.run_script(
            "record-review",
            self.session_dir,
            "--decision",
            "accepted",
            "--reviewer",
            "operator-two",
            "--reason",
            "evidence reviewed",
            "--json",
        )
        self.assertEqual(reviewed.returncode, 0, reviewed.stderr)
        review_payload = json.loads(reviewed.stdout)
        self.assertEqual(review_payload["decision"], "accepted")

        final = self.run_script("validate", self.session_dir, "--json")
        self.assertEqual(final.returncode, 0, final.stderr)
        self.assertEqual(json.loads(final.stdout)["stage"], "reviewed")

    def test_cli_record_execution_rejects_wrong_outcome_count(self):
        recorded = self.run_script(
            "record-execution",
            self.session_dir,
            "--outcome",
            "passed: one",
            "--outcome",
            "passed: two",
        )
        self.assertEqual(recorded.returncode, 1)
        self.assertIn("one outcome per required check", recorded.stderr)
        self.assertFalse((self.session_dir / "execution").exists())

    def test_cli_validate_reports_missing_session(self):
        result = self.run_script("validate", self.root / "does-not-exist")
        self.assertEqual(result.returncode, 1)
        self.assertIn("does not exist", result.stderr)


if __name__ == "__main__":
    unittest.main()
