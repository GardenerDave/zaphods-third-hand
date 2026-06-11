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

    def test_missing_runs_dir_is_empty_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_dir = Path(temp_dir) / "missing"

            runs = report_distiller_metrics.discover_runs(runs_dir, 10, completed_only=False)
            payload = report_distiller_metrics.build_report_payload(
                runs,
                completed_only=False,
                min_recent_runs_for_chunked=report_distiller_metrics.DEFAULT_MIN_RECENT_RUNS_FOR_CHUNKED,
            )

            self.assertEqual([], runs)
            self.assertEqual(0, payload["run_count"])
            self.assertEqual("smoke", payload["recommended_profile"])
            self.assertEqual(
                report_distiller_metrics.DEFAULT_MIN_RECENT_RUNS_FOR_CHUNKED,
                payload["thresholds"]["min_recent_runs_for_chunked"],
            )
            self.assertEqual(
                "Recommend smoke profile: No runs found yet. Suggested settings: "
                "ZTH_DISTILLER_SESSION_MAX_TOKENS=320, ZTH_DISTILLER_PATCH_MAX_TOKENS=240, "
                "ZTH_DISTILLER_TIMEOUT=240.",
                payload["recommendation"],
            )

    def test_recommendation_prefers_smoke_when_retries_detected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_dir = Path(temp_dir) / "run_records"
            run_dir = runs_dir / "run-003"
            run_dir.mkdir(parents=True)
            (run_dir / "METRICS.json").write_text(
                json.dumps(
                    {
                        "source_id": "s3",
                        "short_title": "t3",
                        "status": "completed",
                        "compact_mode": "1",
                        "chunked_mode": "1",
                        "stages": {"chunk_summary": {"retry_count": 2}},
                    }
                ),
                encoding="utf-8",
            )

            runs = report_distiller_metrics.discover_runs(runs_dir, 5, completed_only=False)
            payload = report_distiller_metrics.build_report_payload(
                runs,
                completed_only=False,
                min_recent_runs_for_chunked=report_distiller_metrics.DEFAULT_MIN_RECENT_RUNS_FOR_CHUNKED,
            )

            self.assertEqual("smoke", payload["recommended_profile"])
            self.assertIn("Chunk retries detected", payload["recommendation"])

    def test_recommendation_prefers_normal_when_chunked_run_count_is_below_threshold(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_dir = Path(temp_dir) / "run_records"
            for idx in [4, 5]:
                run_dir = runs_dir / f"run-00{idx}"
                run_dir.mkdir(parents=True)
                (run_dir / "chunk_metrics.tsv").write_text(
                    "chunk_prompt\tchunk_summary\tstatus\tattempts\telapsed_seconds\tprompt_estimated_tokens\toutput_estimated_tokens\tprompt_bytes\toutput_bytes\terror_log\n"
                    "a\tb\tcompleted\t1\t1\t10\t8\t40\t32\t\n",
                    encoding="utf-8",
                )
                (run_dir / "METRICS.json").write_text(
                    json.dumps(
                        {
                            "source_id": f"s{idx}",
                            "short_title": f"t{idx}",
                            "status": "completed",
                            "compact_mode": "0",
                            "chunked_mode": "1",
                            "stages": {
                                "chunk_summary": {
                                    "attempted": 1,
                                    "succeeded": 1,
                                    "failed": 0,
                                    "retry_count": 0,
                                    "chunk_metrics_file": "chunk_metrics.tsv",
                                }
                            },
                        }
                    ),
                    encoding="utf-8",
                )

            runs = report_distiller_metrics.discover_runs(runs_dir, 5, completed_only=False)
            payload = report_distiller_metrics.build_report_payload(
                runs,
                completed_only=False,
                min_recent_runs_for_chunked=report_distiller_metrics.DEFAULT_MIN_RECENT_RUNS_FOR_CHUNKED,
            )

            self.assertEqual("normal", payload["recommended_profile"])
            self.assertIn("Need at least 3 recent runs", payload["recommendation"])

    def test_recommendation_threshold_override_allows_chunked_with_two_runs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_dir = Path(temp_dir) / "run_records"
            for idx in [9, 10]:
                run_dir = runs_dir / f"run-0{idx}"
                run_dir.mkdir(parents=True)
                (run_dir / "chunk_metrics.tsv").write_text(
                    "chunk_prompt\tchunk_summary\tstatus\tattempts\telapsed_seconds\tprompt_estimated_tokens\toutput_estimated_tokens\tprompt_bytes\toutput_bytes\terror_log\n"
                    "a\tb\tcompleted\t1\t1\t10\t8\t40\t32\t\n",
                    encoding="utf-8",
                )
                (run_dir / "METRICS.json").write_text(
                    json.dumps(
                        {
                            "source_id": f"s{idx}",
                            "short_title": f"t{idx}",
                            "status": "completed",
                            "compact_mode": "0",
                            "chunked_mode": "1",
                            "stages": {
                                "chunk_summary": {
                                    "attempted": 1,
                                    "succeeded": 1,
                                    "failed": 0,
                                    "retry_count": 0,
                                    "chunk_metrics_file": "chunk_metrics.tsv",
                                }
                            },
                        }
                    ),
                    encoding="utf-8",
                )

            runs = report_distiller_metrics.discover_runs(runs_dir, 5, completed_only=False)
            payload = report_distiller_metrics.build_report_payload(
                runs,
                completed_only=False,
                min_recent_runs_for_chunked=2,
            )

            self.assertEqual("chunked", payload["recommended_profile"])
            self.assertEqual(2, payload["thresholds"]["min_recent_runs_for_chunked"])

    def test_recommendation_prefers_chunked_when_recent_chunked_runs_are_clean(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_dir = Path(temp_dir) / "run_records"
            for idx in [6, 7, 8]:
                run_dir = runs_dir / f"run-00{idx}"
                run_dir.mkdir(parents=True)
                (run_dir / "chunk_metrics.tsv").write_text(
                    "chunk_prompt\tchunk_summary\tstatus\tattempts\telapsed_seconds\tprompt_estimated_tokens\toutput_estimated_tokens\tprompt_bytes\toutput_bytes\terror_log\n"
                    "a\tb\tcompleted\t1\t1\t10\t8\t40\t32\t\n",
                    encoding="utf-8",
                )
                (run_dir / "METRICS.json").write_text(
                    json.dumps(
                        {
                            "source_id": f"s{idx}",
                            "short_title": f"t{idx}",
                            "status": "completed",
                            "compact_mode": "0",
                            "chunked_mode": "1",
                            "stages": {
                                "chunk_summary": {
                                    "attempted": 1,
                                    "succeeded": 1,
                                    "failed": 0,
                                    "retry_count": 0,
                                    "chunk_metrics_file": "chunk_metrics.tsv",
                                }
                            },
                        }
                    ),
                    encoding="utf-8",
                )

            runs = report_distiller_metrics.discover_runs(runs_dir, 5, completed_only=False)
            payload = report_distiller_metrics.build_report_payload(
                runs,
                completed_only=False,
                min_recent_runs_for_chunked=report_distiller_metrics.DEFAULT_MIN_RECENT_RUNS_FOR_CHUNKED,
            )

            self.assertEqual("chunked", payload["recommended_profile"])
            self.assertIn("ZTH_DISTILLER_CHUNK_LINES", payload["recommendation"])

    def test_build_advisor_payload_includes_recent_run_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_dir = Path(temp_dir) / "run_records"
            run_dir = runs_dir / "run-011"
            run_dir.mkdir(parents=True)
            (run_dir / "METRICS.json").write_text(
                json.dumps(
                    {
                        "source_id": "s11",
                        "short_title": "t11",
                        "status": "completed",
                        "compact_mode": "0",
                        "chunked_mode": "1",
                        "total_elapsed_seconds": 44,
                        "stages": {
                            "chunk_summary": {
                                "attempted": 1,
                                "succeeded": 1,
                                "failed": 0,
                                "retry_count": 0,
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            runs = report_distiller_metrics.discover_runs(runs_dir, 5, completed_only=False)
            payload = report_distiller_metrics.build_advisor_payload(
                runs,
                completed_only=False,
                min_recent_runs_for_chunked=1,
            )

            self.assertEqual("chunked", payload["recommended_profile"])
            self.assertEqual("chunked", payload["recent_run"]["mode"])
            self.assertEqual(44, payload["recent_run"]["total_elapsed_seconds"])

    def test_build_advisor_payload_omits_recent_run_when_empty(self):
        payload = report_distiller_metrics.build_advisor_payload(
            [],
            completed_only=False,
            min_recent_runs_for_chunked=3,
        )

        self.assertEqual("smoke", payload["recommended_profile"])
        self.assertNotIn("recent_run", payload)

    def test_mixed_recent_window_with_failure_recommends_smoke(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_dir = Path(temp_dir) / "run_records"

            def write_run(run_name: str, status: str, completed_at: str) -> None:
                run_dir = runs_dir / run_name
                run_dir.mkdir(parents=True)
                (run_dir / "METRICS.json").write_text(
                    json.dumps(
                        {
                            "source_id": run_name,
                            "short_title": run_name,
                            "status": status,
                            "compact_mode": "1",
                            "chunked_mode": "1",
                            "run_completed_at": completed_at,
                            "stages": {"chunk_summary": {"retry_count": 0, "failed": 0}},
                        }
                    ),
                    encoding="utf-8",
                )

            write_run("run-older-ok", "completed", "2026-06-10T00:00:00Z")
            write_run("run-mid-ok", "completed", "2026-06-11T00:00:00Z")
            write_run("run-recent-fail", "failed", "2026-06-12T00:00:00Z")
            write_run("run-newest-ok", "completed", "2026-06-13T00:00:00Z")

            runs = report_distiller_metrics.discover_runs(runs_dir, 3, completed_only=False)
            payload = report_distiller_metrics.build_report_payload(
                runs,
                completed_only=False,
                min_recent_runs_for_chunked=report_distiller_metrics.DEFAULT_MIN_RECENT_RUNS_FOR_CHUNKED,
            )

            self.assertEqual(3, payload["run_count"])
            self.assertEqual("smoke", payload["recommended_profile"])
            self.assertIn("Recent failures detected", payload["recommendation"])

    def test_mixed_recent_window_completed_only_can_recommend_chunked(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_dir = Path(temp_dir) / "run_records"

            def write_run(run_name: str, status: str, completed_at: str) -> None:
                run_dir = runs_dir / run_name
                run_dir.mkdir(parents=True)
                (run_dir / "METRICS.json").write_text(
                    json.dumps(
                        {
                            "source_id": run_name,
                            "short_title": run_name,
                            "status": status,
                            "compact_mode": "1",
                            "chunked_mode": "1",
                            "run_completed_at": completed_at,
                            "stages": {
                                "chunk_summary": {
                                    "attempted": 1,
                                    "succeeded": 1,
                                    "failed": 0,
                                    "retry_count": 0,
                                }
                            },
                        }
                    ),
                    encoding="utf-8",
                )

            write_run("run-old-ok", "completed", "2026-06-10T00:00:00Z")
            write_run("run-mid-ok", "completed", "2026-06-11T00:00:00Z")
            write_run("run-recent-fail", "failed", "2026-06-12T00:00:00Z")
            write_run("run-newest-ok", "completed", "2026-06-13T00:00:00Z")

            runs = report_distiller_metrics.discover_runs(runs_dir, 3, completed_only=True)
            payload = report_distiller_metrics.build_report_payload(
                runs,
                completed_only=True,
                min_recent_runs_for_chunked=report_distiller_metrics.DEFAULT_MIN_RECENT_RUNS_FOR_CHUNKED,
            )

            self.assertEqual(3, payload["run_count"])
            self.assertEqual("chunked", payload["recommended_profile"])
            self.assertIn("Recent chunked runs completed without chunk failures", payload["recommendation"])


if __name__ == "__main__":
    unittest.main()
