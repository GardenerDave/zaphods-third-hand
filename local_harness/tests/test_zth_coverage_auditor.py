import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


sys.path.insert(0, os.fspath(Path(__file__).resolve().parents[1]))

import zth_coverage_auditor


ALL_CATEGORIES_TEXT = """
Security auth review.
Data integrity database schema check.
Privacy compliance PII review.
Functional UX workflow behavior.
Performance resilience timeout retry analysis.
Operations deployment rollback monitoring.
Documentation onboarding README quickstart.
Testing regression pytest fixture coverage.
Safety supervision human approval.
"""


class ZthCoverageAuditorTests(unittest.TestCase):
    def test_all_categories_covered(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "packet.md"
            path.write_text(ALL_CATEGORIES_TEXT, encoding="utf-8")

            result = zth_coverage_auditor.audit_paths([path])
            report = zth_coverage_auditor.render_report([path], result)

        self.assertEqual([], result.blind_spots)
        self.assertIn("output_contract_version: zth.coverage_audit.v0.2", report)
        self.assertIn("## Covered Areas", report)
        self.assertIn("security:", report)
        self.assertIn("## Potential Blind Spots", report)
        self.assertIn("- None detected by this heuristic.", report)

    def test_missing_categories_are_reported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "packet.md"
            path.write_text("Security auth review only.\n", encoding="utf-8")

            result = zth_coverage_auditor.audit_paths([path])
            report = zth_coverage_auditor.render_report([path], result)

        self.assertIn("data integrity", result.blind_spots)
        self.assertIn("documentation/onboarding", report)
        self.assertIn("## Confidence", report)

    def test_empty_input_handling(self):
        result = zth_coverage_auditor.audit_paths([])
        report = zth_coverage_auditor.render_report([], result)

        self.assertEqual(set(zth_coverage_auditor.CATEGORY_KEYWORDS), set(result.blind_spots))
        self.assertIn("- None supplied.", report)
        self.assertIn("No input files were supplied.", report)
        self.assertIn("low", report)

    def test_cli_stdout_and_output_paths_work(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "packet.md"
            output_path = Path(temp_dir) / "coverage.md"
            input_path.write_text("Documentation onboarding and testing regression.\n", encoding="utf-8")

            exit_code = zth_coverage_auditor.main([os.fspath(input_path), "--output", os.fspath(output_path)])
            self.assertEqual(0, exit_code)
            self.assertIn("# ZTH Pre-Synthesis Coverage Audit", output_path.read_text(encoding="utf-8"))

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = zth_coverage_auditor.main([os.fspath(input_path)])

        self.assertEqual(0, exit_code)
        self.assertIn("documentation/onboarding", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
