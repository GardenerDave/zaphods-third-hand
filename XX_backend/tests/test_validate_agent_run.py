import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
import sys

sys.path.insert(0, os.fspath(Path(__file__).resolve().parents[1]))

from validate_agent_run import REQUIRED_FILES, main, validate_run_folder


class ValidateAgentRunTests(unittest.TestCase):
    def make_run_folder(self, missing=()):
        temp_dir = tempfile.TemporaryDirectory()
        folder = Path(temp_dir.name)
        missing_set = set(missing)
        for filename in REQUIRED_FILES:
            if filename not in missing_set:
                (folder / filename).write_text(f"{filename}\n", encoding="utf-8")
        return temp_dir, folder

    def test_valid_fixture_passes(self):
        temp_dir, folder = self.make_run_folder()
        with temp_dir:
            result = validate_run_folder(folder)

        self.assertTrue(result.valid)
        self.assertEqual((), result.missing_files)
        self.assertIsNone(result.path_error)

    def test_missing_required_file_fails_and_reports_filename(self):
        temp_dir, folder = self.make_run_folder(missing={"MODEL_REQUEST.md"})
        with temp_dir:
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main([os.fspath(folder)])

        self.assertEqual(1, exit_code)
        self.assertIn("MODEL_REQUEST.md", output.getvalue())

    def test_validator_checks_presence_only_without_reading_output(self):
        temp_dir, folder = self.make_run_folder()
        with temp_dir:
            with patch.object(Path, "read_text", side_effect=AssertionError("read_text called")):
                result = validate_run_folder(folder)

        self.assertTrue(result.valid)

    def test_invalid_path_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_path = Path(temp_dir) / "missing"
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main([os.fspath(missing_path)])

        self.assertEqual(1, exit_code)
        self.assertIn("path does not exist", output.getvalue())


if __name__ == "__main__":
    unittest.main()
