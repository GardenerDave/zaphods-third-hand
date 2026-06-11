import json
import os
import tempfile
import unittest
from pathlib import Path

import sys
import subprocess

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
                "model_usage": {
                    "session": {"prompt_tokens": 55, "completion_tokens": 18, "total_tokens": 73},
                    "review_patch": {"prompt_tokens": 31, "completion_tokens": 9, "total_tokens": 40},
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
            self.assertTrue(run.usage_available)
            self.assertEqual(86, run.total_prompt_tokens_actual)
            self.assertEqual(27, run.total_completion_tokens_actual)
            self.assertEqual(113, run.total_tokens_actual)
            self.assertEqual(1, run.chunk_split_seconds)
            self.assertEqual(2, run.chunk_summary_seconds)
            self.assertEqual("compact+chunked", report_distiller_metrics.format_mode(run))

            payload = report_distiller_metrics.serialize_run(run)
            self.assertEqual(900, payload["settings"]["session_max_tokens"])
            self.assertEqual(2, payload["stages"]["chunk_summary_elapsed_seconds"])
            self.assertEqual(86, payload["model_usage"]["total"]["prompt_tokens"])
            self.assertEqual(27, payload["model_usage"]["total"]["completion_tokens"])
            self.assertEqual(1600, payload["model_usage"]["tracked_completion_cap_tokens"])
            self.assertEqual(0.0169, payload["model_usage"]["completion_cap_utilization"])
            self.assertEqual(0.9, payload["model_usage"]["completion_to_output_estimate_ratio"])

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
            self.assertFalse(run.usage_available)

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
            self.assertEqual("low", payload["recommendation_confidence"])
            self.assertEqual("not_ready", payload["readiness"])
            self.assertIn("no_recent_runs", payload["blocking_signals"])
            self.assertEqual(0, payload["calibration_metrics"]["entries_analyzed"])
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
            self.assertEqual("low", payload["recommendation_confidence"])
            self.assertEqual("not_ready", payload["readiness"])
            self.assertIn("chunk_retries", payload["blocking_signals"])
            self.assertIn("Chunk retries", payload["confidence_reason"])

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
            self.assertEqual("medium", payload["recommendation_confidence"])
            self.assertEqual("needs_review", payload["readiness"])
            self.assertIn("insufficient_recent_window", payload["blocking_signals"])
            self.assertIn("need 3", payload["confidence_reason"])

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
            self.assertEqual("high", payload["recommendation_confidence"])
            self.assertEqual("ready", payload["readiness"])
            self.assertEqual([], payload["blocking_signals"])
            self.assertIn("stable", payload["confidence_reason"])

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
            self.assertEqual("high", payload["recommendation_confidence"])
            self.assertEqual("ready", payload["readiness"])

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
                        "session_max_tokens": "100",
                        "patch_max_tokens": "50",
                        "total_elapsed_seconds": 44,
                        "outputs": {
                            "session_estimated_tokens": 20,
                            "patch_estimated_tokens": 10,
                        },
                        "model_usage": {
                            "session": {"prompt_tokens": 80, "completion_tokens": 20},
                            "review_patch": {"prompt_tokens": 30, "completion_tokens": 10},
                        },
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
            self.assertEqual("high", payload["recommendation_confidence"])
            self.assertEqual("ready", payload["readiness"])
            self.assertEqual([], payload["blocking_signals"])
            self.assertIn("stable", payload["confidence_reason"])
            self.assertEqual(1, payload["confidence_signals"]["recent_completed_count"])
            self.assertEqual(0, payload["confidence_signals"]["recent_failed_count"])
            self.assertEqual(0, payload["confidence_signals"]["recent_chunk_retry_count"])
            self.assertTrue(payload["recent_run"]["model_usage_available"])
            self.assertEqual(110, payload["recent_run"]["prompt_tokens"])
            self.assertEqual(30, payload["recent_run"]["completion_tokens"])
            self.assertEqual(140, payload["recent_run"]["total_tokens"])
            self.assertEqual(150, payload["recent_run"]["tracked_completion_cap_tokens"])
            self.assertEqual(0.2, payload["recent_run"]["completion_cap_utilization"])
            self.assertEqual(1.0, payload["recent_run"]["completion_to_output_estimate_ratio"])

    def test_build_advisor_payload_omits_recent_run_when_empty(self):
        payload = report_distiller_metrics.build_advisor_payload(
            [],
            completed_only=False,
            min_recent_runs_for_chunked=3,
        )

        self.assertEqual("smoke", payload["recommended_profile"])
        self.assertEqual("low", payload["recommendation_confidence"])
        self.assertEqual("not_ready", payload["readiness"])
        self.assertIn("no_recent_runs", payload["blocking_signals"])
        self.assertIn("No recent runs", payload["confidence_reason"])
        self.assertNotIn("recent_run", payload)
        self.assertEqual(0, payload["confidence_signals"]["recent_completed_count"])
        self.assertEqual(0, payload["confidence_signals"]["recent_failed_count"])
        self.assertEqual(0, payload["confidence_signals"]["recent_chunk_retry_count"])


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
            self.assertEqual("low", payload["recommendation_confidence"])
            self.assertEqual("not_ready", payload["readiness"])
            self.assertIn("recent_failures", payload["blocking_signals"])
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
            self.assertEqual("high", payload["recommendation_confidence"])
            self.assertEqual("ready", payload["readiness"])
            self.assertEqual([], payload["blocking_signals"])
            self.assertIn("Recent chunked runs completed without chunk failures", payload["recommendation"])

    def test_cli_advisor_only_json_returns_advisor_payload_shape(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_dir = Path(temp_dir) / "run_records"
            run_dir = runs_dir / "run-100"
            run_dir.mkdir(parents=True)
            (run_dir / "METRICS.json").write_text(
                json.dumps(
                    {
                        "source_id": "s100",
                        "short_title": "t100",
                        "status": "completed",
                        "compact_mode": "0",
                        "chunked_mode": "1",
                        "stages": {"chunk_summary": {"attempted": 1, "succeeded": 1, "failed": 0, "retry_count": 0}},
                    }
                ),
                encoding="utf-8",
            )

            script = Path(report_distiller_metrics.__file__)
            proc = subprocess.run(
                [
                    sys.executable,
                    os.fspath(script),
                    "--runs-dir",
                    os.fspath(runs_dir),
                    "--advisor-only",
                    "--json",
                    "--min-recent-runs-for-chunked",
                    "1",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(0, proc.returncode)
            payload = json.loads(proc.stdout)
            self.assertIn("recommended_profile", payload)
            self.assertIn("recommendation_confidence", payload)
            self.assertIn("confidence_reason", payload)
            self.assertIn("readiness", payload)
            self.assertIn("readiness_reason", payload)
            self.assertIn("blocking_signals", payload)
            self.assertIn("interviewer_verdict", payload)
            self.assertIn("interviewer_verdict_reason", payload)
            self.assertIn("role_critique_summary", payload)
            self.assertIn("role_critiques_strict", payload)
            self.assertIn("recent_run", payload)
            self.assertIn("confidence_signals", payload)
            self.assertIn("calibration_metrics", payload)
            self.assertEqual(1, payload["thresholds"]["min_recent_runs_for_chunked"])
            self.assertNotIn("runs", payload)

    def test_cli_json_without_advisor_only_returns_full_payload(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_dir = Path(temp_dir) / "run_records"
            run_dir = runs_dir / "run-101"
            run_dir.mkdir(parents=True)
            (run_dir / "METRICS.json").write_text(
                json.dumps(
                    {
                        "source_id": "s101",
                        "short_title": "t101",
                        "status": "completed",
                        "compact_mode": "1",
                        "chunked_mode": "0",
                    }
                ),
                encoding="utf-8",
            )

            script = Path(report_distiller_metrics.__file__)
            proc = subprocess.run(
                [
                    sys.executable,
                    os.fspath(script),
                    "--runs-dir",
                    os.fspath(runs_dir),
                    "--json",
                    "--min-recent-runs-for-chunked",
                    "4",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(0, proc.returncode)
            payload = json.loads(proc.stdout)
            self.assertIn("runs", payload)
            self.assertIn("recommendation_confidence", payload)
            self.assertIn("confidence_reason", payload)
            self.assertIn("readiness", payload)
            self.assertIn("blocking_signals", payload)
            self.assertIn("interviewer_verdict", payload)
            self.assertIn("interviewer_verdict_reason", payload)
            self.assertIn("role_critique_summary", payload)
            self.assertIn("role_critiques_strict", payload)
            self.assertIn("calibration_metrics", payload)
            self.assertEqual(1, len(payload["runs"]))
            self.assertEqual(4, payload["thresholds"]["min_recent_runs_for_chunked"])

    def test_cli_advisor_only_text_includes_confidence_signals(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_dir = Path(temp_dir) / "run_records"
            run_dir = runs_dir / "run-102"
            run_dir.mkdir(parents=True)
            (run_dir / "METRICS.json").write_text(
                json.dumps(
                    {
                        "source_id": "s102",
                        "short_title": "t102",
                        "status": "failed",
                        "compact_mode": "1",
                        "chunked_mode": "1",
                        "stages": {"chunk_summary": {"retry_count": 2}},
                    }
                ),
                encoding="utf-8",
            )

            script = Path(report_distiller_metrics.__file__)
            proc = subprocess.run(
                [
                    sys.executable,
                    os.fspath(script),
                    "--runs-dir",
                    os.fspath(runs_dir),
                    "--advisor-only",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(0, proc.returncode)
            self.assertIn("Confidence signals:", proc.stdout)
            self.assertIn("Recommendation confidence:", proc.stdout)
            self.assertIn("Readiness:", proc.stdout)
            self.assertIn("Blocking signals:", proc.stdout)
            self.assertIn("Interviewer verdict:", proc.stdout)
            self.assertIn("Calibration:", proc.stdout)
            self.assertIn("Role critiques:", proc.stdout)
            self.assertIn("strict=False", proc.stdout)
            self.assertIn("completed=0", proc.stdout)
            self.assertIn("failed=1", proc.stdout)
            self.assertIn("chunk_retries=2", proc.stdout)
    def test_write_ledger_appends_unseen_runs_and_emits_calibration(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_dir = Path(temp_dir) / "run_records"
            for run_name, status, compact_mode, chunked_mode in [
                ("run-201", "completed", "0", "1"),
                ("run-202", "failed", "1", "0"),
            ]:
                run_dir = runs_dir / run_name
                run_dir.mkdir(parents=True)
                (run_dir / "METRICS.json").write_text(
                    json.dumps(
                        {
                            "source_id": run_name,
                            "short_title": run_name,
                            "status": status,
                            "compact_mode": compact_mode,
                            "chunked_mode": chunked_mode,
                            "stages": {"chunk_summary": {"retry_count": 0, "failed": 0}},
                        }
                    ),
                    encoding="utf-8",
                )

            script = Path(report_distiller_metrics.__file__)
            proc = subprocess.run(
                [
                    sys.executable,
                    os.fspath(script),
                    "--runs-dir",
                    os.fspath(runs_dir),
                    "--json",
                    "--write-ledger",
                    "--calibration-window",
                    "10",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(0, proc.returncode)
            payload = json.loads(proc.stdout)
            self.assertIn("calibration_metrics", payload)
            ledger_path = runs_dir / "interviewer_ledger.jsonl"
            self.assertTrue(ledger_path.is_file())
            lines = [line for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(2, len(lines))

            proc_second = subprocess.run(
                [
                    sys.executable,
                    os.fspath(script),
                    "--runs-dir",
                    os.fspath(runs_dir),
                    "--json",
                    "--write-ledger",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, proc_second.returncode)
            lines_second = [line for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(2, len(lines_second))

    def test_calibration_metrics_from_seeded_ledger(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_dir = Path(temp_dir) / "run_records"
            runs_dir.mkdir(parents=True)
            ledger_path = runs_dir / "interviewer_ledger.jsonl"
            seeded = [
                {
                    "run_dir": "a",
                    "recommendation_confidence": "high",
                    "actual_status": "completed",
                },
                {
                    "run_dir": "b",
                    "recommendation_confidence": "high",
                    "actual_status": "failed",
                },
                {
                    "run_dir": "c",
                    "recommendation_confidence": "low",
                    "actual_status": "completed",
                },
            ]
            ledger_path.write_text("\n".join(json.dumps(x) for x in seeded) + "\n", encoding="utf-8")

            metrics = report_distiller_metrics.build_calibration_metrics(runs_dir, calibration_window=10)

            self.assertEqual(3, metrics["entries_analyzed"])
            self.assertEqual(1, metrics["false_high_count"])
            self.assertEqual(1, metrics["false_low_count"])
            self.assertEqual(2, metrics["high_confidence_count"])
            self.assertEqual(0.5, metrics["confidence_high_success_rate"])

    def test_load_role_critiques_supports_json_array_and_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            role_file = Path(temp_dir) / "role_critiques.json"
            role_file.write_text(
                json.dumps(
                    [
                        {"role": "security", "focus_area": "auth", "severity": "high", "status": "open"},
                        {"role": "perf", "focus_area": "latency", "severity": "low", "status": "resolved"},
                    ]
                ),
                encoding="utf-8",
            )
            critiques = report_distiller_metrics.load_role_critiques(role_file)
            summary = report_distiller_metrics.summarize_role_critiques(critiques)
            self.assertEqual(2, summary["total_count"])
            self.assertEqual(1, summary["unresolved_count"])
            self.assertEqual(1, summary["blocking_count"])
            self.assertIn("security", summary["roles"])
            self.assertIn("auth", summary["focus_areas"])

    def test_interviewer_verdict_hold_on_blocking_role_critique(self):
        verdict, reason = report_distiller_metrics.interviewer_verdict(
            "ready",
            {"confidence_high_success_rate": 1.0, "false_high_count": 0},
            {"blocking_count": 1, "unresolved_count": 1},
            False,
        )
        self.assertEqual("hold", verdict)
        self.assertIn("blocking", reason)

    def test_interviewer_verdict_review_on_unresolved_role_critique(self):
        verdict, reason = report_distiller_metrics.interviewer_verdict(
            "ready",
            {"confidence_high_success_rate": 1.0, "false_high_count": 0},
            {"blocking_count": 0, "unresolved_count": 2},
            False,
        )
        self.assertEqual("proceed_with_review", verdict)
        self.assertIn("unresolved", reason)

    def test_interviewer_verdict_hold_on_unresolved_role_critique_when_strict(self):
        verdict, reason = report_distiller_metrics.interviewer_verdict(
            "ready",
            {"confidence_high_success_rate": 1.0, "false_high_count": 0},
            {"blocking_count": 0, "unresolved_count": 1},
            True,
        )
        self.assertEqual("hold", verdict)
        self.assertIn("strict", reason)

    def test_cli_role_critiques_file_influences_verdict(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_dir = Path(temp_dir) / "run_records"
            run_dir = runs_dir / "run-301"
            run_dir.mkdir(parents=True)
            (run_dir / "METRICS.json").write_text(
                json.dumps(
                    {
                        "source_id": "s301",
                        "short_title": "t301",
                        "status": "completed",
                        "compact_mode": "0",
                        "chunked_mode": "1",
                        "stages": {"chunk_summary": {"attempted": 1, "succeeded": 1, "failed": 0, "retry_count": 0}},
                    }
                ),
                encoding="utf-8",
            )
            role_file = Path(temp_dir) / "role_critiques.json"
            role_file.write_text(
                json.dumps([{"role": "qa", "focus_area": "tests", "severity": "critical", "status": "open"}]),
                encoding="utf-8",
            )

            script = Path(report_distiller_metrics.__file__)
            proc = subprocess.run(
                [
                    sys.executable,
                    os.fspath(script),
                    "--runs-dir",
                    os.fspath(runs_dir),
                    "--advisor-only",
                    "--json",
                    "--min-recent-runs-for-chunked",
                    "1",
                    "--role-critiques-file",
                    os.fspath(role_file),
                    "--role-critiques-strict",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, proc.returncode)
            payload = json.loads(proc.stdout)
            self.assertEqual("hold", payload["interviewer_verdict"])
            self.assertEqual(1, payload["role_critique_summary"]["blocking_count"])
            self.assertTrue(payload["role_critiques_strict"])

    def test_cli_role_critiques_strict_holds_for_nonblocking_unresolved(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_dir = Path(temp_dir) / "run_records"
            run_dir = runs_dir / "run-302"
            run_dir.mkdir(parents=True)
            (run_dir / "METRICS.json").write_text(
                json.dumps(
                    {
                        "source_id": "s302",
                        "short_title": "t302",
                        "status": "completed",
                        "compact_mode": "1",
                        "chunked_mode": "0",
                    }
                ),
                encoding="utf-8",
            )
            role_file = Path(temp_dir) / "role_critiques.jsonl"
            role_file.write_text(
                json.dumps({"role": "ux", "focus_area": "copy", "severity": "low", "status": "open"}) + "\n",
                encoding="utf-8",
            )

            script = Path(report_distiller_metrics.__file__)
            proc = subprocess.run(
                [
                    sys.executable,
                    os.fspath(script),
                    "--runs-dir",
                    os.fspath(runs_dir),
                    "--advisor-only",
                    "--json",
                    "--role-critiques-file",
                    os.fspath(role_file),
                    "--role-critiques-strict",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, proc.returncode)
            payload = json.loads(proc.stdout)
            self.assertEqual("hold", payload["interviewer_verdict"])
            self.assertEqual(1, payload["role_critique_summary"]["unresolved_count"])
            self.assertIn("strict", payload["interviewer_verdict_reason"])

    def test_interviewer_verdict_proceed_when_ready_and_calibration_clean(self):
        verdict, reason = report_distiller_metrics.interviewer_verdict(
            "ready",
            {
                "confidence_high_success_rate": 1.0,
                "false_high_count": 0,
            },
            {"blocking_count": 0, "unresolved_count": 0},
            False,
        )
        self.assertEqual("proceed", verdict)
        self.assertIn("ready", reason)

    def test_interviewer_verdict_proceed_with_review_on_false_high(self):
        verdict, _ = report_distiller_metrics.interviewer_verdict(
            "ready",
            {
                "confidence_high_success_rate": 0.8,
                "false_high_count": 1,
            },
            {"blocking_count": 0, "unresolved_count": 0},
            False,
        )
        self.assertEqual("proceed_with_review", verdict)

    def test_interviewer_verdict_hold_on_low_high_success_rate(self):
        verdict, _ = report_distiller_metrics.interviewer_verdict(
            "ready",
            {
                "confidence_high_success_rate": 0.4,
                "false_high_count": 0,
            },
            {"blocking_count": 0, "unresolved_count": 0},
            False,
        )
        self.assertEqual("hold", verdict)

    def test_interviewer_verdict_tracks_readiness_gate(self):
        verdict_not_ready, _ = report_distiller_metrics.interviewer_verdict("not_ready", {}, {"blocking_count": 0, "unresolved_count": 0}, False)
        verdict_needs_review, _ = report_distiller_metrics.interviewer_verdict("needs_review", {}, {"blocking_count": 0, "unresolved_count": 0}, False)
        self.assertEqual("hold", verdict_not_ready)
        self.assertEqual("proceed_with_review", verdict_needs_review)


if __name__ == "__main__":
    unittest.main()
