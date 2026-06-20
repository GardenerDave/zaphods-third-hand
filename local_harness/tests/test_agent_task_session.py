import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


sys.path.insert(0, os.fspath(Path(__file__).resolve().parents[1]))

import agent_task_session


class AgentTaskSessionTests(unittest.TestCase):
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

    def test_scaffold_generation_creates_expected_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self.create_session(Path(temp_dir))

            self.assertTrue(session.output_dir.is_dir())
            self.assertEqual(
                set(agent_task_session.GENERATED_FILES),
                {path.name for path in session.output_dir.iterdir()},
            )
            metadata = json.loads(
                (session.output_dir / "task.yaml").read_text(encoding="utf-8")
            )

        self.assertEqual(agent_task_session.CONTRACT_VERSION, metadata["task_session_contract_version"])
        self.assertEqual("draft", metadata["status"])
        self.assertTrue(metadata["requires_human_review"])
        self.assertFalse(metadata["authority_granted"])
        self.assertFalse(metadata["agent_execution_performed"])

    def test_task_id_is_deterministic_and_filesystem_safe(self):
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            first = self.create_session(Path(first_dir))
            second = self.create_session(Path(second_dir))

        self.assertEqual(first.task_id, second.task_id)
        self.assertRegex(first.task_id, agent_task_session.TASK_ID_RE)
        self.assertTrue(first.task_id.startswith("add-focused-parser-validation-"))

    def test_generated_prompt_contains_scope_checks_and_authority_boundaries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self.create_session(Path(temp_dir))
            prompt = (session.output_dir / "codex_prompt.md").read_text(
                encoding="utf-8"
            )

        self.assertIn("local_harness/example.py", prompt)
        self.assertIn(
            "python3 -m pytest local_harness/tests/test_example.py",
            prompt,
        )
        self.assertIn("Human review is required", prompt)
        self.assertIn("Passing checks are evidence, not authority", prompt)
        self.assertIn("Do not mark the task complete automatically", prompt)
        self.assertIn("Do not merge, release, promote, clean up, delete", prompt)

    def test_status_remains_draft_and_human_reviewed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self.create_session(Path(temp_dir))
            status = (session.output_dir / "status.md").read_text(encoding="utf-8")

        self.assertIn("- Status: `draft`", status)
        self.assertIn("- Human review required: `true`", status)
        self.assertIn("- Authority granted by this packet: `false`", status)
        self.assertIn("does not mark the task complete", status)

    def test_duplicate_paths_and_checks_are_deduplicated_in_order(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = self.create_session(
                Path(temp_dir),
                allowed_paths=["docs/README.md", "docs/README.md", "README.md"],
                required_checks=["git diff --check", "git diff --check"],
            )

        self.assertEqual(("docs/README.md", "README.md"), session.allowed_paths)
        self.assertEqual(("git diff --check",), session.required_checks)

    def test_unsafe_allowed_paths_fail_closed(self):
        unsafe_paths = (
            "/tmp/absolute.py",
            "../outside.py",
            "docs/../README.md",
            ".git/config",
            "nested/.git/config",
            "",
        )
        for unsafe in unsafe_paths:
            with self.subTest(path=unsafe), tempfile.TemporaryDirectory() as temp_dir:
                with self.assertRaises(ValueError):
                    self.create_session(
                        Path(temp_dir),
                        allowed_paths=[unsafe],
                    )

    def test_empty_name_goal_paths_or_checks_fail(self):
        cases = (
            {"name": " "},
            {"goal": "\n"},
            {"allowed_paths": []},
            {"required_checks": []},
        )
        for override in cases:
            with self.subTest(override=override), tempfile.TemporaryDirectory() as temp_dir:
                with self.assertRaises(ValueError):
                    self.create_session(Path(temp_dir), **override)

    def test_invalid_explicit_task_id_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "task id"):
                self.create_session(
                    Path(temp_dir),
                    task_id="../unsafe",
                )

    def test_existing_task_directory_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            session = self.create_session(root, task_id="existing-task")
            marker = session.output_dir / "marker.txt"
            marker.write_text("preserve\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "already exists"):
                self.create_session(root, task_id="existing-task")

            self.assertEqual("preserve\n", marker.read_text(encoding="utf-8"))

    def test_cli_creates_packet_without_subprocess_execution(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = io.StringIO()
            with mock.patch.object(subprocess, "run") as run, contextlib.redirect_stdout(output):
                exit_code = agent_task_session.main(
                    [
                        "new",
                        "--name",
                        "CLI task",
                        "--goal",
                        "Prepare a scoped review packet.",
                        "--branch",
                        "cli-task",
                        "--allow",
                        "README.md",
                        "--check",
                        "git diff --check",
                    ],
                    session_root=Path(temp_dir),
                )

            run.assert_not_called()
            self.assertEqual(0, exit_code)
            self.assertIn("No agent, check, shell command, or Git operation was executed", output.getvalue())


if __name__ == "__main__":
    unittest.main()
