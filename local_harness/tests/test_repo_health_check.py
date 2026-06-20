import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


sys.path.insert(0, os.fspath(Path(__file__).resolve().parents[1]))

import repo_health_check
import tool_maker


class RepoHealthCheckTests(unittest.TestCase):
    def test_markdown_link_checker_ignores_fenced_code_blocks(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "README.md"
            source.write_text(
                "# Example\n\n```markdown\n[missing](missing.md)\n```\n",
                encoding="utf-8",
            )

            result = repo_health_check.check_markdown_links(root, [source])

        self.assertEqual(repo_health_check.STATUS_PASS, result.status)

    def test_markdown_link_checker_handles_anchor_on_existing_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "README.md"
            target = root / "docs" / "GUIDE.md"
            target.parent.mkdir()
            target.write_text("# Setup\n", encoding="utf-8")
            source.write_text("[Setup](docs/GUIDE.md#setup)\n", encoding="utf-8")

            result = repo_health_check.check_markdown_links(root, [source])

        self.assertEqual(repo_health_check.STATUS_PASS, result.status)

    def test_markdown_link_checker_reports_missing_target(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "README.md"
            source.write_text("[Missing](docs/missing.md)\n", encoding="utf-8")

            result = repo_health_check.check_markdown_links(root, [source])

        self.assertEqual(repo_health_check.STATUS_FAIL, result.status)
        self.assertIn("README.md:1", result.details[0])
        self.assertIn("docs/missing.md", result.details[0])

    def test_privacy_checker_catches_stale_auth_variable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = root / "config.example.env"
            config.write_text("export ZTH_API_KEY=example\n", encoding="utf-8")

            result = repo_health_check.check_privacy(root)

        self.assertEqual(repo_health_check.STATUS_FAIL, result.status)
        self.assertIn("stale auth variable", result.details[0])

    def test_privacy_checker_catches_private_ip_in_public_surface(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readme = root / "README.md"
            readme.write_text("Endpoint: http://192.168.1.10:8080/v1\n", encoding="utf-8")

            result = repo_health_check.check_privacy(root)

        self.assertEqual(repo_health_check.STATUS_FAIL, result.status)
        self.assertIn("private RFC1918 address", result.details[0])

    def test_privacy_checker_excludes_historical_reports(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = root / "docs" / "reports" / "historical.md"
            report.parent.mkdir(parents=True)
            report.write_text(
                "Historical endpoint http://10.0.0.8 and ZTH_API_KEY.\n",
                encoding="utf-8",
            )

            result = repo_health_check.check_privacy(root)

        self.assertEqual(repo_health_check.STATUS_PASS, result.status)

    def test_boundary_checker_allows_not_an_auto_promoter(self):
        result = self.boundary_result("This helper is not an auto-promoter.\n")

        self.assertEqual(repo_health_check.STATUS_PASS, result.status)

    def test_boundary_checker_allows_does_not_judge_truth_safety(self):
        result = self.boundary_result(
            "The validator does not judge truth, safety, or completeness.\n"
        )

        self.assertEqual(repo_health_check.STATUS_PASS, result.status)

    def test_boundary_checker_allows_negation_across_wrapped_lines(self):
        result = self.boundary_result(
            "The helper does not fix files or\n"
            "validate semantic truth or safety.\n"
        )

        self.assertEqual(repo_health_check.STATUS_PASS, result.status)

    def test_boundary_checker_fails_positive_automatic_promotion_claim(self):
        result = self.boundary_result("The workflow automatically promotes models.\n")

        self.assertEqual(repo_health_check.STATUS_FAIL, result.status)
        self.assertIn("automatic promotion claim", result.details[0])

    def boundary_result(self, text: str) -> repo_health_check.CheckResult:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "README.md"
            source.write_text(text, encoding="utf-8")
            return repo_health_check.check_boundary_language(root, [source])

    def initialize_repo(self, root: Path, readme_text: str) -> None:
        (root / "README.md").write_text(readme_text, encoding="utf-8")
        subprocess.run(
            ["git", "init", "-q"],
            cwd=root,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "add", "README.md"],
            cwd=root,
            check=True,
            capture_output=True,
        )

    def test_cli_default_does_not_run_pytest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.initialize_repo(root, "# Healthy repository\n")
            with mock.patch.object(repo_health_check, "run_pytest_check") as pytest_check:
                with contextlib.redirect_stdout(io.StringIO()):
                    exit_code = repo_health_check.main([], repo_root=root)

        self.assertEqual(0, exit_code)
        pytest_check.assert_not_called()

    def test_cli_returns_nonzero_on_missing_link(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.initialize_repo(root, "[Missing](missing.md)\n")
            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = repo_health_check.main([], repo_root=root)

        self.assertEqual(1, exit_code)

    def test_scaffold_check_validates_explicit_generated_scaffold(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.md"
            scaffold = root / "lifecycle.md"
            source.write_text("Workflow evidence.\n", encoding="utf-8")
            tool_maker.generate_scaffold(
                [source],
                scaffold,
                name="Health check lifecycle",
            )

            result = repo_health_check.check_scaffolds(root, [scaffold])

        self.assertEqual(repo_health_check.STATUS_PASS, result.status)
        self.assertIn("tool-lifecycle", result.details[0])


if __name__ == "__main__":
    unittest.main()
