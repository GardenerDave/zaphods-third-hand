import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys

sys.path.insert(0, os.fspath(Path(__file__).resolve().parents[1]))

import run_single_worker
from icm_call import WorkerResponse


class RunSingleWorkerTests(unittest.TestCase):
    def test_run_single_worker_scaffolds_and_validates(self):
        response = WorkerResponse(
            status="ok",
            content="# Local Agent Report\n\nok\n",
            request_url="http://localhost:8083/v1/chat/completions",
            model="gemma-test.gguf",
            configured_model="gemma-test.gguf",
            finish_reason="stop",
            usage={"prompt_tokens": 10, "completion_tokens": 5},
            timings={"predicted_ms": 123.0},
            raw_response={"choices": []},
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "2026-06-07_001_doc-audit"
            with patch.object(run_single_worker, "call_worker", return_value=response):
                exit_code = run_single_worker.main(
                    [
                        os.fspath(run_folder),
                        "handoff",
                        "--init-stubs",
                        "Reply with exactly: ok",
                    ]
                )

            self.assertEqual(0, exit_code)
            for filename in (
                "TASK.md",
                "INPUT.md",
                "MODEL_REQUEST.md",
                "OUTPUT.md",
                "REVIEW.md",
                "METRICS.json",
                "ACCEPTED.md",
            ):
                self.assertTrue((run_folder / filename).is_file(), filename)

            metrics = json.loads((run_folder / "METRICS.json").read_text(encoding="utf-8"))
            self.assertEqual("ok", metrics["status"])


if __name__ == "__main__":
    unittest.main()
