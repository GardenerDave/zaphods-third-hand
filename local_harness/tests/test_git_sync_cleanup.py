import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


sys.path.insert(0, os.fspath(Path(__file__).resolve().parents[1]))

import git_sync_cleanup


def sample_state(
    *,
    current_branch: str = "main",
    clean: bool = True,
    main_status: str = "aligned",
    current_status: str = "current_branch_is_main",
    local_branches: dict[str, str] | None = None,
    merged_origin: list[str] | None = None,
    merged_main: list[str] | None = None,
    not_merged_origin: list[str] | None = None,
    remote_branches: dict[str, str] | None = None,
    remote_findings: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    local = local_branches or {"main": "a" * 40}
    remote = remote_branches or {"origin/main": "a" * 40}
    return {
        "current_branch": current_branch,
        "head_commit": local.get(current_branch, "b" * 40),
        "working_tree": {
            "state": "clean" if clean else "dirty",
            "clean": clean,
            "staged_changes": 0 if clean else 1,
            "unstaged_changes": 0,
            "untracked_files": 0,
            "entry_count": 0 if clean else 1,
        },
        "main_status": {
            "status": main_status,
            "local_main_commit": local.get("main"),
            "origin_main_commit": remote.get("origin/main"),
        },
        "current_branch_status": {
            "status": current_status,
            "commit": local.get(current_branch),
            "origin_main_commit": remote.get("origin/main"),
        },
        "local_branches": {
            "all": sorted(local),
            "merged_into_main": merged_main or [],
            "merged_into_origin_main": merged_origin or [],
            "not_merged_into_origin_main": not_merged_origin or [],
        },
        "local_branch_commits": local,
        "remote_branch_commits": remote,
        "remote_findings": remote_findings or [],
    }


class FakeGitReader:
    def __init__(self, state: dict[str, object]) -> None:
        self.state = state


class FakeProcessRunner:
    def __init__(self, result: git_sync_cleanup.CommandResult) -> None:
        self.result = result

    def __call__(
        self,
        _command: tuple[str, ...],
        _cwd: Path,
    ) -> git_sync_cleanup.CommandResult:
        return self.result


class GitSyncCleanupTests(unittest.TestCase):
    def test_git_reader_rejects_mutating_command_before_subprocess(self):
        process = mock.Mock()
        reader = git_sync_cleanup.GitReader(
            Path("/tmp/example-repo"),
            process_runner=process,
        )

        with self.assertRaisesRegex(
            git_sync_cleanup.AdvisorError,
            "refusing non-read-only Git command",
        ):
            reader.run("fetch", "--prune")

        process.assert_not_called()

    def test_clean_working_tree_classification(self):
        result = git_sync_cleanup.classify_working_tree("")

        self.assertEqual("clean", result["state"])
        self.assertTrue(result["clean"])
        self.assertEqual(0, result["untracked_files"])

    def test_dirty_working_tree_classification(self):
        result = git_sync_cleanup.classify_working_tree(
            "M  staged.md\n M unstaged.md\n?? untracked.md\n"
        )

        self.assertEqual("dirty", result["state"])
        self.assertEqual(1, result["staged_changes"])
        self.assertEqual(1, result["unstaged_changes"])
        self.assertEqual(1, result["untracked_files"])

    def test_local_main_aligned_when_refs_match(self):
        commit = "a" * 40

        relation = git_sync_cleanup.classify_relation(
            commit,
            commit,
            lambda _left, _right: False,
            missing_left="missing_local_main",
            missing_right="missing_origin_main",
        )

        self.assertEqual("aligned", relation)

    def test_local_main_behind_when_origin_has_extra_commit(self):
        local = "a" * 40
        origin = "b" * 40

        relation = git_sync_cleanup.classify_relation(
            local,
            origin,
            lambda left, right: (left, right) == (local, origin),
            missing_left="missing_local_main",
            missing_right="missing_origin_main",
        )

        self.assertEqual("behind", relation)

    def test_symbolic_remote_head_is_not_reported_as_branch(self):
        output = (
            "origin\t" + "a" * 40 + "\trefs/remotes/origin/main\n"
            "origin/main\t" + "a" * 40 + "\t\n"
        )
        reader = git_sync_cleanup.GitReader(
            Path("/tmp/example-repo"),
            process_runner=FakeProcessRunner(
                git_sync_cleanup.CommandResult(0, stdout=output)
            ),
        )

        refs = reader.list_refs("refs/remotes")

        self.assertEqual({"origin/main": "a" * 40}, refs)

    def test_merged_current_feature_recommends_safe_delete(self):
        state = sample_state(
            current_branch="feature",
            current_status="behind",
            local_branches={"main": "a" * 40, "feature": "b" * 40},
            merged_main=["feature"],
        )

        recommendations = git_sync_cleanup.build_recommendations(state)
        text = "\n".join(recommendations)

        self.assertIn("git switch main", text)
        self.assertIn("git branch -d feature", text)
        self.assertNotIn("git branch -D feature", text)

    def test_squash_merged_looking_branch_requires_inspection(self):
        state = sample_state(
            local_branches={"main": "a" * 40, "squashed-feature": "b" * 40},
            not_merged_origin=["squashed-feature"],
        )

        recommendations = git_sync_cleanup.build_recommendations(
            state,
            after_merge_branch="squashed-feature",
        )
        text = "\n".join(recommendations)

        self.assertIn("git log --oneline origin/main..squashed-feature", text)
        self.assertIn("git diff --stat origin/main...squashed-feature", text)
        self.assertIn("Only after a human confirms", text)
        self.assertIn("git branch -D squashed-feature", text)
        self.assertNotIn("safe to force-delete", text.lower())

    def test_remote_revert_branch_requires_inspection_before_deletion(self):
        branch = "origin/revert-7-example"
        state = sample_state(
            remote_branches={"origin/main": "a" * 40, branch: "b" * 40},
            remote_findings=[
                {
                    "branch": branch,
                    "reasons": ["revert_pattern", "no_matching_local_branch"],
                }
            ],
        )

        recommendations = git_sync_cleanup.build_recommendations(state)
        text = "\n".join(recommendations)

        self.assertLess(text.index("git log"), text.index("git push origin --delete"))
        self.assertIn("git diff --stat origin/main...origin/revert-7-example", text)
        self.assertIn("If a human confirms it was accidental", text)

    def test_run_health_uses_process_wrapper_and_reports_result(self):
        completed = git_sync_cleanup.CommandResult(
            returncode=0,
            stdout="[PASS] docs links\n",
        )
        with mock.patch.object(
            git_sync_cleanup,
            "run_process",
            return_value=completed,
        ) as runner:
            result = git_sync_cleanup.run_health_check(Path("/tmp/example-repo"))

        self.assertEqual("pass", result["status"])
        command, cwd = runner.call_args.args
        self.assertEqual(
            (sys.executable, "local_harness/repo_health_check.py"),
            command,
        )
        self.assertEqual(Path("/tmp/example-repo"), cwd)

    def test_json_output_contains_expected_top_level_keys(self):
        state = sample_state()
        with mock.patch.object(
            git_sync_cleanup,
            "collect_repository_state",
            return_value=state,
        ):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = git_sync_cleanup.main(
                    ["--json"],
                    repo_root=Path("/tmp/example-repo"),
                    reader=FakeGitReader(state),
                )

        payload = json.loads(output.getvalue())
        self.assertEqual(0, exit_code)
        for key in (
            "current_branch",
            "working_tree",
            "main_status",
            "current_branch_status",
            "local_branches",
            "remote_findings",
            "recommendations",
        ):
            self.assertIn(key, payload)

    def test_default_mode_does_not_run_mutating_commands(self):
        state = sample_state()
        with mock.patch.object(
            git_sync_cleanup,
            "collect_repository_state",
            return_value=state,
        ), mock.patch.object(git_sync_cleanup, "run_process") as process:
            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = git_sync_cleanup.main(
                    [],
                    repo_root=Path("/tmp/example-repo"),
                    reader=FakeGitReader(state),
                )

        self.assertEqual(0, exit_code)
        process.assert_not_called()
        recommendations = "\n".join(
            git_sync_cleanup.build_recommendations(state)
        )
        for command in (
            "git fetch",
            "git pull",
            "git branch -d",
            "git branch -D",
            "git reset",
            "git push",
            "git merge",
        ):
            self.assertNotIn(command, recommendations)


if __name__ == "__main__":
    unittest.main()
