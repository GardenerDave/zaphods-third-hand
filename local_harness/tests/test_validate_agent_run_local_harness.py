import tempfile
import unittest
from pathlib import Path
import os
import sys

sys.path.insert(0, os.fspath(Path(__file__).resolve().parents[1]))

import validate_agent_run


class ValidateAgentRunTests(unittest.TestCase):
    def test_validate_run_folder_accepts_complete_shape(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir)
            for filename in validate_agent_run.REQUIRED_FILES:
                (run_folder / filename).write_text("ok\n", encoding="utf-8")

            result = validate_agent_run.validate_run_folder(run_folder)

        self.assertTrue(result.valid)
        self.assertEqual((), result.missing_files)

    def test_validate_run_folder_reports_missing_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir)
            (run_folder / "TASK.md").write_text("ok\n", encoding="utf-8")

            result = validate_agent_run.validate_run_folder(run_folder)

        self.assertFalse(result.valid)
        self.assertIn("INPUT.md", result.missing_files)


if __name__ == "__main__":
    unittest.main()
