import json
import os
import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, os.fspath(Path(__file__).resolve().parents[1]))

import report_distiller_metrics


class ReportDistillerMetricsTests(unittest.TestCase):
    def test_discover_runs_parses_full_metrics_with_chunk_tsv(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_dir = Path(temp_dir) / "run_records"
            run_dir = runs_dir / "run-001"
            run_dir.mkdir(parents=True)
            chunk_tsv = run_dir / "chunk_metrics.tsv"
            chunk_tsv.write_text(
                "chunk_prompt\tchunk_summary\tstatus\tattempts\telapsed_seconds\tprompt_estimated_tokens\toutput_estimated_tokens\tprompt_bytes\toutput_bytes\terror_log\n"
                "a\tb\tcompleted\t1\t1\t10\t8\t40\t32\t\n"
                "c\td\tfailed\t2\t2\t11\t9\t44\t36\terr.log\n",
                encoding="utf-8",
            )
            metrics = {
                "source_id": "s1",
                "short_title": "t1",
                "status": "completed",
                "compact_mode": "1",
                "chunked_mode": "1",
                "chunk_line_size": "50",
                "chunk_max_tokens": "600",
                "session_max_tokens": "900",
                "patch_max_tokens": "700",
                "call_timeout_seconds": "300",
                "total_elapsed_seconds": 12,
                "run_completed_at": "2026-06-11T05:30:12Z",
                "source": {"bytes": 100, "lines": 4, "estimated_tokens": 25},
                "prompts": {
                    "session_prompt_bytes": 200,
                    "session_prompt_lines": 8,
                    "session_prompt_estimated_tokens": 50,
                    "patch_prompt_bytes": 120,
                    "patch_prompt_lines": 5,
                    "patch_prompt_estimated_tokens": 30,
                },
                "outputs": {
                    "session_bytes": 80,
                    "session_lines": 3,
                    "session_estimated_tokens": 20,
                    "patch_bytes": 40,
                    "patch_lines": 2,
                    "patch_estimated_tokens": 10,
                },
                "stages": {
                    "chunk_split": {"elapsed_seconds": 1},
                    "chunk_summary": {
                        "elapsed_seconds": 2,
                        "attempted": 2,
                        "succeeded": 1,
                        "failed": 1,
                        "retry_count": 1,
                        "chunk_metrics_file": os.fspath(chunk_tsv),
                    },
                    "session": {"elapsed_seconds": 7},
                    "review_patch": {"elapsed_seconds": 5},
                },
            }
            (run_dir / "METRICS.json").write_text(json.dumps(metrics), encoding="utf-8")

            runs = report_distiller_metrics.discover_runs(runs_dir, 5, completed_only=False)

            self.assertEqual(1, len(runs))
            run = runs[0]
            self.assertEqual("completed", run.status)
            self.assertEqual(2, run.chunk_rows)
            self.assertEqual(1, run.chunk_row_failures)
            self.assertEqual(50, run.chunk_line_size)
            self.assertEqual(600, run.chunk_max_tokens)
            self.assertEqual(900, run.session_max_tokens)
            self.assertEqual(700, run.patch_max_tokens)
            self.assertEqual(300, run.call_timeout_seconds)
            self.assertEqual(1, run.chunk_split_seconds)
            self.assertEqual(2, run.chunk_summary_seconds)
            self.assertEqual("compact+chunked", report_distiller_metrics.format_mode(run))

            payload = report_distiller_metrics.serialize_run(run)
            self.assertEqual(900, payload["settings"]["session_max_tokens"])
            self.assertEqual(2, payload["stages"]["chunk_summary_elapsed_seconds"])

    def test_discover_runs_parses_partial_metrics(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_dir = Path(temp_dir) / "run_records"
            run_dir = runs_dir / "run-002"
            run_dir.mkdir(parents=True)
            metrics = {
                "source_id": "s2",
                "short_title": "t2",
                "status": "completed",
                "compact_mode": "1",
                "chunked_mode": "0",
            }
            (run_dir / "METRICS.json").write_text(json.dumps(metrics), encoding="utf-8")

            runs = report_distiller_metrics.discover_runs(runs_dir, 5, completed_only=False)

            self.assertEqual(1, len(runs))
            run = runs[0]
            self.assertEqual(0, run.total_elapsed_seconds)
            self.assertEqual(0, run.source_bytes)
            self.assertEqual(0, run.session_prompt_estimated_tokens)
            self.assertEqual(0, run.patch_estimated_tokens)

    def test_completed_only_filters_failed_runs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_dir = Path(temp_dir) / "run_records"
            completed_dir = runs_dir / "run-completed"
            failed_dir = runs_dir / "run-failed"
            completed_dir.mkdir(parents=True)
            failed_dir.mkdir(parents=True)
            (completed_dir / "METRICS.json").write_text(
                json.dumps({"status": "completed", "source_id": "ok", "short_title": "ok"}),
                encoding="utf-8",
            )
            (failed_dir / "METRICS.json").write_text(
                json.dumps({"status": "failed", "source_id": "bad", "short_title": "bad"}),
                encoding="utf-8",
            )

            runs = report_distiller_metrics.discover_runs(runs_dir, 10, completed_only=True)

            self.assertEqual(1, len(runs))
            self.assertEqual("completed", runs[0].status)


if __name__ == "__main__":
    unittest.main()
