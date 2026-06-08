import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys

sys.path.insert(0, os.fspath(Path(__file__).resolve().parents[1]))

import run_aider_worker


class RunAiderWorkerTests(unittest.TestCase):
    def test_run_aider_worker_uses_gemma_profile_defaults(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "2026-06-07_004_aider-worker-wrapper"
            target = Path(temp_dir) / "target.txt"
            target.write_text("placeholder\n", encoding="utf-8")
            target_path = os.fspath(target)
            completed = run_aider_worker.subprocess.CompletedProcess(
                args=["aider"],
                returncode=0,
                stdout=(
                    "► **THINKING**\n"
                    "draft\n"
                    "► **ANSWER**\n"
                    "Tokens: 1.0k sent, 167 received.\n"
                    f"Applied edit to {target_path}\n"
                ),
                stderr="",
            )
            prewarm_result = {"attempted": True, "success": True, "response_preview": "ok"}
            with patch.object(run_aider_worker, "run_endpoint_prewarm", return_value=prewarm_result) as mocked_prewarm:
                with patch.object(run_aider_worker.subprocess, "run", return_value=completed) as mocked_run:
                    exit_code = run_aider_worker.main(
                        [
                            os.fspath(run_folder),
                            "--init-stubs",
                            target_path,
                        ]
                    )

            self.assertEqual(0, exit_code)
            self.assertTrue((run_folder / "OUTPUT.md").is_file())
            self.assertTrue((run_folder / "METRICS.json").is_file())
            self.assertTrue((run_folder / "REVIEW.md").is_file())
            self.assertTrue((run_folder / "ACCEPTED.md").is_file())

            metrics = json.loads((run_folder / "METRICS.json").read_text(encoding="utf-8"))
            self.assertEqual(0, metrics["exit_code"])
            self.assertEqual([target_path], metrics["selected_files"])
            self.assertEqual("gemma-local", metrics["profile"])
            self.assertTrue(metrics["prewarm"]["success"])
            self.assertTrue(metrics["bundle_read_inputs"])
            self.assertTrue(metrics["aider_summary"]["thinking_block_present"])
            self.assertEqual(1000, metrics["aider_summary"]["tokens_sent"])
            self.assertEqual(167, metrics["aider_summary"]["tokens_received"])
            self.assertTrue(metrics["aider_summary"]["all_selected_files_edited"])
            self.assertTrue(metrics["preflight"]["validated_shape_match"])
            mocked_prewarm.assert_called_once()

            called_command = mocked_run.call_args.args[0]
            self.assertIn("--message-file", called_command)
            self.assertIn("--no-auto-commits", called_command)
            self.assertIn("--no-dirty-commits", called_command)
            self.assertIn("--no-stream", called_command)
            self.assertIn("--openai-api-base", called_command)
            self.assertIn("http://localhost:8083/v1", called_command)
            called_env = mocked_run.call_args.kwargs["env"]
            self.assertEqual("1", called_env["AIDER_MINIMAL_PROMPT"])
            self.assertEqual("1", called_env["AIDER_SKIP_EXAMPLE_CHAT"])
            self.assertEqual("dummy", called_env["OPENAI_API_KEY"])
            self.assertTrue(called_env["AIDER_DUMP_REQUEST_JSON"].endswith("AIDER_REQUEST.json"))
            self.assertTrue(called_env["AIDER_DUMP_EVENTS_FILE"].endswith("AIDER_EVENTS.jsonl"))

            effective_prompt = (run_folder / "AIDER_MESSAGE.md").read_text(encoding="utf-8")
            self.assertIn("Gemma local rules:", effective_prompt)

    def test_run_aider_worker_records_debug_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "debug-artifacts"
            target = Path(temp_dir) / "target.txt"
            target.write_text("placeholder\n", encoding="utf-8")

            def fake_run(*args, **kwargs):
                env = kwargs["env"]
                Path(env["AIDER_DUMP_REQUEST_JSON"]).write_text(
                    json.dumps({"model": "openai/gemma4", "messages": [{"role": "user", "content": "x"}]}) + "\n",
                    encoding="utf-8",
                )
                Path(env["AIDER_DUMP_EVENTS_FILE"]).write_text(
                    json.dumps({"event": "send_completion_start", "model": "openai/gemma4"}) + "\n"
                    + json.dumps(
                        {
                            "event": "send_completion_success",
                            "model": "openai/gemma4",
                            "response_preview": "Applied patch",
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
                return run_aider_worker.subprocess.CompletedProcess(
                    args=["aider"],
                    returncode=0,
                    stdout=f"Applied edit to {os.fspath(target)}\n",
                    stderr="",
                )

            with patch.object(run_aider_worker, "run_endpoint_prewarm", return_value=None):
                with patch.object(run_aider_worker.subprocess, "run", side_effect=fake_run):
                    exit_code = run_aider_worker.main(
                        [
                            os.fspath(run_folder),
                            "--init-stubs",
                            os.fspath(target),
                        ]
                    )

            self.assertEqual(0, exit_code)
            metrics = json.loads((run_folder / "METRICS.json").read_text(encoding="utf-8"))
            self.assertTrue((run_folder / "AIDER_REQUEST.json").is_file())
            self.assertTrue((run_folder / "AIDER_EVENTS.jsonl").is_file())
            self.assertEqual(
                os.fspath(run_folder / "AIDER_REQUEST.json"),
                metrics["aider_debug"]["request_dump_path"],
            )
            self.assertEqual(
                os.fspath(run_folder / "AIDER_EVENTS.jsonl"),
                metrics["aider_debug"]["events_path"],
            )
            self.assertEqual(1, metrics["aider_debug"]["event_summary"]["success_count"])
            self.assertEqual(
                ["Applied patch"],
                metrics["aider_debug"]["event_summary"]["success_previews"],
            )

    def test_run_aider_worker_retries_after_connection_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "retry-on-connection"
            target = Path(temp_dir) / "target.txt"
            target.write_text("placeholder\n", encoding="utf-8")
            first = run_aider_worker.subprocess.CompletedProcess(
                args=["aider"],
                returncode=0,
                stdout=(
                    "litellm.InternalServerError: InternalServerError: OpenAIException - Connection error.\n"
                    "Retrying in 0.2 seconds...\n"
                ),
                stderr="",
            )
            second = run_aider_worker.subprocess.CompletedProcess(
                args=["aider"],
                returncode=0,
                stdout=(
                    "► **ANSWER**\n"
                    "Tokens: 400 sent, 120 received.\n"
                    f"Applied edit to {os.fspath(target)}\n"
                ),
                stderr="",
            )

            with patch.object(
                run_aider_worker,
                "run_endpoint_prewarm",
                side_effect=[
                    {"attempted": True, "success": True, "response_preview": "ok"},
                    {"attempted": True, "success": True, "response_preview": "ok"},
                ],
            ) as mocked_prewarm:
                with patch.object(run_aider_worker.subprocess, "run", side_effect=[first, second]) as mocked_run:
                    exit_code = run_aider_worker.main(
                        [
                            os.fspath(run_folder),
                            "--init-stubs",
                            os.fspath(target),
                        ]
                    )

            self.assertEqual(0, exit_code)
            self.assertEqual(2, mocked_run.call_count)
            self.assertEqual(2, mocked_prewarm.call_count)
            metrics = json.loads((run_folder / "METRICS.json").read_text(encoding="utf-8"))
            self.assertTrue(metrics["manager_retry_triggered"])
            self.assertEqual(2, len(metrics["aider_attempts"]))
            self.assertEqual(2, metrics["final_attempt_number"])
            self.assertEqual(1, metrics["aider_summary"]["applied_edit_count"])
            output = (run_folder / "OUTPUT.md").read_text(encoding="utf-8")
            self.assertIn("# Aider Attempt 1", output)
            self.assertIn("# Aider Attempt 2", output)

    def test_run_aider_worker_fails_when_required_inputs_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "missing-inputs"
            run_folder.mkdir()
            exit_code = run_aider_worker.main([os.fspath(run_folder), "local_harness/run_aider_worker.py"])

        self.assertEqual(1, exit_code)

    def test_run_aider_worker_returns_failure_on_connection_error_output(self):
        completed = run_aider_worker.subprocess.CompletedProcess(
            args=["aider"],
            returncode=0,
            stdout=(
                "litellm.InternalServerError: InternalServerError: OpenAIException - Connection error.\n"
                "Retrying in 0.2 seconds...\n"
            ),
            stderr="",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "connection-error"
            with patch.object(run_aider_worker, "run_endpoint_prewarm", return_value=None):
                with patch.object(run_aider_worker.subprocess, "run", return_value=completed):
                    exit_code = run_aider_worker.main(
                        [
                            os.fspath(run_folder),
                            "--init-stubs",
                            "local_harness/run_aider_worker.py",
                        ]
                    )

        self.assertEqual(1, exit_code)

    def test_run_aider_worker_returns_failure_on_manager_timeout(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "manager-timeout"
            target = Path(temp_dir) / "target.txt"
            target.write_text("placeholder\n", encoding="utf-8")
            timeout_error = run_aider_worker.subprocess.TimeoutExpired(
                cmd=["aider"],
                timeout=110,
                output="partial output\n",
                stderr="provider stalled\n",
            )

            with patch.object(run_aider_worker, "run_endpoint_prewarm", return_value=None):
                with patch.object(run_aider_worker.subprocess, "run", side_effect=timeout_error):
                    exit_code = run_aider_worker.main(
                        [
                            os.fspath(run_folder),
                            "--init-stubs",
                            os.fspath(target),
                        ]
                    )

            self.assertEqual(1, exit_code)
            metrics = json.loads((run_folder / "METRICS.json").read_text(encoding="utf-8"))
            self.assertEqual(124, metrics["exit_code"])
            self.assertTrue(metrics["aider_summary"]["manager_timeout_detected"])
            self.assertTrue(metrics["aider_summary"]["fatal_error_detected"])
            output = (run_folder / "OUTPUT.md").read_text(encoding="utf-8")
            self.assertIn("Manager timeout expired", output)

    def test_run_aider_worker_applies_direct_edit_fallback_after_timeout(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "direct-edit-success"
            target = Path(temp_dir) / "target.txt"
            target.write_text("value=old\n", encoding="utf-8")
            (run_folder / "TASK.md").parent.mkdir(parents=True, exist_ok=True)
            (run_folder / "TASK.md").write_text("task\n", encoding="utf-8")
            (run_folder / "INPUT.md").write_text("input\n", encoding="utf-8")
            (run_folder / "MODEL_REQUEST.md").write_text(
                (
                    "# Model Request\n\n"
                    f"- In `{os.fspath(target)}`, replace `old` with `new`.\n"
                    "- Edit only the listed file.\n"
                ),
                encoding="utf-8",
            )
            timeout_error = run_aider_worker.subprocess.TimeoutExpired(
                cmd=["aider"],
                timeout=110,
                output="partial output\n",
                stderr="provider stalled\n",
            )

            with patch.object(run_aider_worker, "run_endpoint_prewarm", return_value=None):
                with patch.object(run_aider_worker.subprocess, "run", side_effect=timeout_error):
                    exit_code = run_aider_worker.main(
                        [
                            os.fspath(run_folder),
                            "--no-direct-edit-short-circuit",
                            os.fspath(target),
                        ]
                    )

            self.assertEqual(0, exit_code)
            self.assertEqual("value=new\n", target.read_text(encoding="utf-8"))
            metrics = json.loads((run_folder / "METRICS.json").read_text(encoding="utf-8"))
            self.assertTrue(metrics["aider_summary"]["direct_edit_fallback_triggered"])
            self.assertFalse(metrics["aider_summary"]["direct_edit_short_circuit_triggered"])
            self.assertFalse(metrics["aider_summary"]["fatal_error_detected"])
            self.assertTrue((run_folder / "AIDER_DIRECT_EDIT.json").is_file())
            self.assertEqual(
                os.fspath(run_folder / "AIDER_DIRECT_EDIT.json"),
                metrics["aider_debug"]["direct_edit_path"],
            )

    def test_run_aider_worker_short_circuits_direct_edit_before_aider(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "direct-edit-shortcut"
            target = Path(temp_dir) / "target.txt"
            target.write_text("value=old\n", encoding="utf-8")
            (run_folder / "TASK.md").parent.mkdir(parents=True, exist_ok=True)
            (run_folder / "TASK.md").write_text("task\n", encoding="utf-8")
            (run_folder / "INPUT.md").write_text("input\n", encoding="utf-8")
            (run_folder / "MODEL_REQUEST.md").write_text(
                (
                    "# Model Request\n\n"
                    f"- In `{os.fspath(target)}`, replace `old` with `new`.\n"
                    "- Edit only the listed file.\n"
                ),
                encoding="utf-8",
            )

            with patch.object(run_aider_worker, "run_endpoint_prewarm") as mocked_prewarm:
                with patch.object(run_aider_worker.subprocess, "run") as mocked_run:
                    exit_code = run_aider_worker.main([os.fspath(run_folder), os.fspath(target)])

            self.assertEqual(0, exit_code)
            self.assertEqual("value=new\n", target.read_text(encoding="utf-8"))
            mocked_prewarm.assert_not_called()
            mocked_run.assert_not_called()

            metrics = json.loads((run_folder / "METRICS.json").read_text(encoding="utf-8"))
            self.assertTrue(metrics["aider_summary"]["direct_edit_short_circuit_triggered"])
            self.assertFalse(metrics["aider_summary"]["direct_edit_fallback_triggered"])
            self.assertFalse(metrics["aider_summary"]["fatal_error_detected"])
            self.assertEqual(0, metrics["final_attempt_number"])
            self.assertTrue(metrics["preflight"]["direct_edit_candidate"]["eligible"])
            output = (run_folder / "OUTPUT.md").read_text(encoding="utf-8")
            self.assertIn("# Direct Edit Shortcut", output)

    def test_run_aider_worker_short_circuits_direct_edit_on_larger_file_within_limit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "direct-edit-shortcut-large"
            target = Path(temp_dir) / "target.txt"
            target.write_text("old\n" + ("x" * 20000), encoding="utf-8")
            (run_folder / "TASK.md").parent.mkdir(parents=True, exist_ok=True)
            (run_folder / "TASK.md").write_text("task\n", encoding="utf-8")
            (run_folder / "INPUT.md").write_text("input\n", encoding="utf-8")
            (run_folder / "MODEL_REQUEST.md").write_text(
                (
                    "# Model Request\n\n"
                    f"- In `{os.fspath(target)}`, replace `old` with `new`.\n"
                    "- Edit only the listed file.\n"
                ),
                encoding="utf-8",
            )

            with patch.object(run_aider_worker, "run_endpoint_prewarm") as mocked_prewarm:
                with patch.object(run_aider_worker.subprocess, "run") as mocked_run:
                    exit_code = run_aider_worker.main([os.fspath(run_folder), os.fspath(target)])

            self.assertEqual(0, exit_code)
            self.assertTrue(target.read_text(encoding="utf-8").startswith("new\n"))
            mocked_prewarm.assert_not_called()
            mocked_run.assert_not_called()

            metrics = json.loads((run_folder / "METRICS.json").read_text(encoding="utf-8"))
            self.assertTrue(metrics["aider_summary"]["direct_edit_short_circuit_triggered"])
            self.assertTrue(metrics["preflight"]["direct_edit_candidate"]["eligible"])
            self.assertGreater(metrics["preflight"]["direct_edit_candidate"]["file_bytes"], 16384)
            self.assertEqual(24576, metrics["preflight"]["direct_edit_candidate"]["file_size_limit_bytes"])

    def test_run_aider_worker_short_circuits_insert_after_before_aider(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "direct-edit-insert-after"
            target = Path(temp_dir) / "target.txt"
            target.write_text("alpha\nbeta\n", encoding="utf-8")
            (run_folder / "TASK.md").parent.mkdir(parents=True, exist_ok=True)
            (run_folder / "TASK.md").write_text("task\n", encoding="utf-8")
            (run_folder / "INPUT.md").write_text("input\n", encoding="utf-8")
            (run_folder / "MODEL_REQUEST.md").write_text(
                (
                    "# Model Request\n\n"
                    f"- In `{os.fspath(target)}`, insert `inserted\\n` after `alpha\\n`.\n"
                    "- Edit only the listed file.\n"
                ).replace("\\n", "\n"),
                encoding="utf-8",
            )

            with patch.object(run_aider_worker, "run_endpoint_prewarm") as mocked_prewarm:
                with patch.object(run_aider_worker.subprocess, "run") as mocked_run:
                    exit_code = run_aider_worker.main([os.fspath(run_folder), os.fspath(target)])

            self.assertEqual(0, exit_code)
            self.assertEqual("alpha\ninserted\nbeta\n", target.read_text(encoding="utf-8"))
            mocked_prewarm.assert_not_called()
            mocked_run.assert_not_called()

            metrics = json.loads((run_folder / "METRICS.json").read_text(encoding="utf-8"))
            self.assertTrue(metrics["aider_summary"]["direct_edit_short_circuit_triggered"])
            self.assertEqual("insert_after", metrics["preflight"]["direct_edit_candidate"]["operation"])
            self.assertTrue(metrics["preflight"]["direct_edit_candidate"]["eligible"])
            direct_edit = json.loads((run_folder / "AIDER_DIRECT_EDIT.json").read_text(encoding="utf-8"))
            self.assertEqual("insert_after", direct_edit["operation"])

    def test_run_aider_worker_short_circuits_insert_before_before_aider(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "direct-edit-insert-before"
            target = Path(temp_dir) / "target.txt"
            target.write_text("alpha\nbeta\n", encoding="utf-8")
            (run_folder / "TASK.md").parent.mkdir(parents=True, exist_ok=True)
            (run_folder / "TASK.md").write_text("task\n", encoding="utf-8")
            (run_folder / "INPUT.md").write_text("input\n", encoding="utf-8")
            (run_folder / "MODEL_REQUEST.md").write_text(
                (
                    "# Model Request\n\n"
                    f"- In `{os.fspath(target)}`, insert `inserted\\n` before `beta\\n`.\n"
                    "- Edit only the listed file.\n"
                ).replace("\\n", "\n"),
                encoding="utf-8",
            )

            with patch.object(run_aider_worker, "run_endpoint_prewarm") as mocked_prewarm:
                with patch.object(run_aider_worker.subprocess, "run") as mocked_run:
                    exit_code = run_aider_worker.main([os.fspath(run_folder), os.fspath(target)])

            self.assertEqual(0, exit_code)
            self.assertEqual("alpha\ninserted\nbeta\n", target.read_text(encoding="utf-8"))
            mocked_prewarm.assert_not_called()
            mocked_run.assert_not_called()

            metrics = json.loads((run_folder / "METRICS.json").read_text(encoding="utf-8"))
            self.assertTrue(metrics["aider_summary"]["direct_edit_short_circuit_triggered"])
            self.assertEqual("insert_before", metrics["preflight"]["direct_edit_candidate"]["operation"])
            self.assertTrue(metrics["preflight"]["direct_edit_candidate"]["eligible"])
            direct_edit = json.loads((run_folder / "AIDER_DIRECT_EDIT.json").read_text(encoding="utf-8"))
            self.assertEqual("insert_before", direct_edit["operation"])

    def test_run_aider_worker_decodes_escaped_newlines_in_literal_insert(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "direct-edit-insert-escaped-newline"
            target = Path(temp_dir) / "target.txt"
            target.write_text("alpha\nbeta\n", encoding="utf-8")
            (run_folder / "TASK.md").parent.mkdir(parents=True, exist_ok=True)
            (run_folder / "TASK.md").write_text("task\n", encoding="utf-8")
            (run_folder / "INPUT.md").write_text("input\n", encoding="utf-8")
            (run_folder / "MODEL_REQUEST.md").write_text(
                (
                    "# Model Request\n\n"
                    f"- In `{os.fspath(target)}`, insert `inserted\\n` after `alpha\\n`.\n"
                    "- Edit only the listed file.\n"
                ),
                encoding="utf-8",
            )

            with patch.object(run_aider_worker, "run_endpoint_prewarm") as mocked_prewarm:
                with patch.object(run_aider_worker.subprocess, "run") as mocked_run:
                    exit_code = run_aider_worker.main([os.fspath(run_folder), os.fspath(target)])

            self.assertEqual(0, exit_code)
            self.assertEqual("alpha\ninserted\nbeta\n", target.read_text(encoding="utf-8"))
            mocked_prewarm.assert_not_called()
            mocked_run.assert_not_called()

            metrics = json.loads((run_folder / "METRICS.json").read_text(encoding="utf-8"))
            self.assertTrue(metrics["preflight"]["direct_edit_candidate"]["eligible"])

    def test_run_aider_worker_short_circuits_block_replace_before_aider(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "direct-edit-block-replace"
            target = Path(temp_dir) / "target.txt"
            target.write_text("alpha\nbeta\ngamma\nomega\n", encoding="utf-8")
            (run_folder / "TASK.md").parent.mkdir(parents=True, exist_ok=True)
            (run_folder / "TASK.md").write_text("task\n", encoding="utf-8")
            (run_folder / "INPUT.md").write_text("input\n", encoding="utf-8")
            (run_folder / "MODEL_REQUEST.md").write_text(
                (
                    "# Model Request\n\n"
                    f"- In `{os.fspath(target)}`, replace the block from `beta\\n` through `gamma\\n` with `delta\\nepsilon\\n`.\n"
                    "- Edit only the listed file.\n"
                ).replace("\\n", "\n"),
                encoding="utf-8",
            )

            with patch.object(run_aider_worker, "run_endpoint_prewarm") as mocked_prewarm:
                with patch.object(run_aider_worker.subprocess, "run") as mocked_run:
                    exit_code = run_aider_worker.main([os.fspath(run_folder), os.fspath(target)])

            self.assertEqual(0, exit_code)
            self.assertEqual("alpha\ndelta\nepsilon\nomega\n", target.read_text(encoding="utf-8"))
            mocked_prewarm.assert_not_called()
            mocked_run.assert_not_called()

            metrics = json.loads((run_folder / "METRICS.json").read_text(encoding="utf-8"))
            self.assertTrue(metrics["aider_summary"]["direct_edit_short_circuit_triggered"])
            self.assertEqual("replace_block", metrics["preflight"]["direct_edit_candidate"]["operation"])
            self.assertTrue(metrics["preflight"]["direct_edit_candidate"]["eligible"])
            self.assertEqual(1, metrics["preflight"]["direct_edit_candidate"]["operations"][0]["start_anchor_match_count"])
            self.assertEqual(1, metrics["preflight"]["direct_edit_candidate"]["operations"][0]["end_anchor_match_count"])
            direct_edit = json.loads((run_folder / "AIDER_DIRECT_EDIT.json").read_text(encoding="utf-8"))
            self.assertEqual("replace_block", direct_edit["operation"])

    def test_run_aider_worker_short_circuits_batch_direct_edit_before_aider(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "direct-edit-batch"
            target = Path(temp_dir) / "target.txt"
            target.write_text("alpha\nbeta\nomega\n", encoding="utf-8")
            (run_folder / "TASK.md").parent.mkdir(parents=True, exist_ok=True)
            (run_folder / "TASK.md").write_text("task\n", encoding="utf-8")
            (run_folder / "INPUT.md").write_text("input\n", encoding="utf-8")
            (run_folder / "MODEL_REQUEST.md").write_text(
                (
                    "# Model Request\n\n"
                    f"- In `{os.fspath(target)}`, replace `beta\\n` with `gamma\\n`.\n"
                    f"- In `{os.fspath(target)}`, insert `delta\\n` after `gamma\\n`.\n"
                    "- Edit only the listed file.\n"
                ).replace("\\n", "\n"),
                encoding="utf-8",
            )

            with patch.object(run_aider_worker, "run_endpoint_prewarm") as mocked_prewarm:
                with patch.object(run_aider_worker.subprocess, "run") as mocked_run:
                    exit_code = run_aider_worker.main([os.fspath(run_folder), os.fspath(target)])

            self.assertEqual(0, exit_code)
            self.assertEqual("alpha\ngamma\ndelta\nomega\n", target.read_text(encoding="utf-8"))
            mocked_prewarm.assert_not_called()
            mocked_run.assert_not_called()

            metrics = json.loads((run_folder / "METRICS.json").read_text(encoding="utf-8"))
            self.assertTrue(metrics["aider_summary"]["direct_edit_short_circuit_triggered"])
            self.assertEqual("batch", metrics["preflight"]["direct_edit_candidate"]["operation"])
            self.assertEqual(2, metrics["preflight"]["direct_edit_candidate"]["operation_count"])
            self.assertEqual(["replace", "insert_after"], metrics["preflight"]["direct_edit_candidate"]["operation_types"])
            direct_edit = json.loads((run_folder / "AIDER_DIRECT_EDIT.json").read_text(encoding="utf-8"))
            self.assertEqual("batch", direct_edit["operation"])
            self.assertEqual(2, direct_edit["operation_count"])

    def test_run_aider_worker_short_circuits_multi_file_batch_before_aider(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "direct-edit-multi-file-batch"
            target_a = Path(temp_dir) / "target-a.txt"
            target_b = Path(temp_dir) / "target-b.txt"
            target_a.write_text("alpha\nbeta\n", encoding="utf-8")
            target_b.write_text("gamma\ndelta\n", encoding="utf-8")
            (run_folder / "TASK.md").parent.mkdir(parents=True, exist_ok=True)
            (run_folder / "TASK.md").write_text("task\n", encoding="utf-8")
            (run_folder / "INPUT.md").write_text("input\n", encoding="utf-8")
            (run_folder / "MODEL_REQUEST.md").write_text(
                (
                    "# Model Request\n\n"
                    f"- In `{os.fspath(target_a)}`, replace `beta\\n` with `theta\\n`.\n"
                    f"- In `{os.fspath(target_b)}`, insert `epsilon\\n` before `delta\\n`.\n"
                    "- Edit only the listed files.\n"
                ).replace("\\n", "\n"),
                encoding="utf-8",
            )

            with patch.object(run_aider_worker, "run_endpoint_prewarm") as mocked_prewarm:
                with patch.object(run_aider_worker.subprocess, "run") as mocked_run:
                    exit_code = run_aider_worker.main(
                        [os.fspath(run_folder), os.fspath(target_a), os.fspath(target_b)]
                    )

            self.assertEqual(0, exit_code)
            self.assertEqual("alpha\ntheta\n", target_a.read_text(encoding="utf-8"))
            self.assertEqual("gamma\nepsilon\ndelta\n", target_b.read_text(encoding="utf-8"))
            mocked_prewarm.assert_not_called()
            mocked_run.assert_not_called()

            metrics = json.loads((run_folder / "METRICS.json").read_text(encoding="utf-8"))
            self.assertTrue(metrics["aider_summary"]["direct_edit_short_circuit_triggered"])
            self.assertEqual("multi_file_batch", metrics["preflight"]["direct_edit_candidate"]["operation"])
            self.assertEqual(2, metrics["preflight"]["direct_edit_candidate"]["target_file_count"])
            self.assertEqual(
                [os.fspath(target_a), os.fspath(target_b)],
                metrics["preflight"]["direct_edit_candidate"]["target_files"],
            )
            direct_edit = json.loads((run_folder / "AIDER_DIRECT_EDIT.json").read_text(encoding="utf-8"))
            self.assertEqual("multi_file_batch", direct_edit["operation"])
            self.assertEqual(
                [os.fspath(target_a), os.fspath(target_b)],
                direct_edit["target_files"],
            )

    def test_run_aider_worker_short_circuits_multi_file_batch_when_aider_budget_would_block(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "direct-edit-multi-file-batch-over-budget"
            target_a = Path(temp_dir) / "target-a.txt"
            target_b = Path(temp_dir) / "target-b.txt"
            target_a.write_text("old\n" + ("a" * 14000), encoding="utf-8")
            target_b.write_text("old\n" + ("b" * 14000), encoding="utf-8")
            (run_folder / "TASK.md").parent.mkdir(parents=True, exist_ok=True)
            (run_folder / "TASK.md").write_text("task\n", encoding="utf-8")
            (run_folder / "INPUT.md").write_text("input\n", encoding="utf-8")
            (run_folder / "MODEL_REQUEST.md").write_text(
                (
                    "# Model Request\n\n"
                    f"- In `{os.fspath(target_a)}`, replace `old` with `new-a`.\n"
                    f"- In `{os.fspath(target_b)}`, replace `old` with `new-b`.\n"
                    "- Edit only the listed files.\n"
                ),
                encoding="utf-8",
            )

            with patch.object(run_aider_worker, "run_endpoint_prewarm") as mocked_prewarm:
                with patch.object(run_aider_worker.subprocess, "run") as mocked_run:
                    exit_code = run_aider_worker.main(
                        [os.fspath(run_folder), os.fspath(target_a), os.fspath(target_b)]
                    )

            self.assertEqual(0, exit_code)
            self.assertTrue(target_a.read_text(encoding="utf-8").startswith("new-a\n"))
            self.assertTrue(target_b.read_text(encoding="utf-8").startswith("new-b\n"))
            mocked_prewarm.assert_not_called()
            mocked_run.assert_not_called()

            metrics = json.loads((run_folder / "METRICS.json").read_text(encoding="utf-8"))
            self.assertFalse(metrics["preflight"]["within_budget"])
            self.assertTrue(metrics["preflight"]["direct_edit_budget_bypass_available"])
            self.assertTrue(metrics["aider_summary"]["direct_edit_short_circuit_triggered"])
            self.assertEqual("multi_file_batch", metrics["preflight"]["direct_edit_candidate"]["operation"])

    def test_run_aider_worker_short_circuits_mixed_batch_before_aider(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "direct-edit-mixed-batch"
            target_a = Path(temp_dir) / "target-a.txt"
            target_b = Path(temp_dir) / "target-b.txt"
            target_a.write_text("alpha\nbeta\nomega\n", encoding="utf-8")
            target_b.write_text("gamma\ndelta\n", encoding="utf-8")
            (run_folder / "TASK.md").parent.mkdir(parents=True, exist_ok=True)
            (run_folder / "TASK.md").write_text("task\n", encoding="utf-8")
            (run_folder / "INPUT.md").write_text("input\n", encoding="utf-8")
            (run_folder / "MODEL_REQUEST.md").write_text(
                (
                    "# Model Request\n\n"
                    f"- In `{os.fspath(target_a)}`, apply excerpt patches.\n"
                    "```text\n"
                    "<<<<<<< SEARCH\n"
                    "beta\n"
                    "=======\n"
                    "theta\n"
                    ">>>>>>> REPLACE\n"
                    "```\n"
                    f"- In `{os.fspath(target_b)}`, insert `epsilon\\n` before `delta\\n`.\n"
                    "- Edit only the listed files.\n"
                ).replace("\\n", "\n"),
                encoding="utf-8",
            )

            with patch.object(run_aider_worker, "run_endpoint_prewarm") as mocked_prewarm:
                with patch.object(run_aider_worker.subprocess, "run") as mocked_run:
                    exit_code = run_aider_worker.main(
                        [os.fspath(run_folder), os.fspath(target_a), os.fspath(target_b)]
                    )

            self.assertEqual(0, exit_code)
            self.assertEqual("alpha\ntheta\nomega\n", target_a.read_text(encoding="utf-8"))
            self.assertEqual("gamma\nepsilon\ndelta\n", target_b.read_text(encoding="utf-8"))
            mocked_prewarm.assert_not_called()
            mocked_run.assert_not_called()

            metrics = json.loads((run_folder / "METRICS.json").read_text(encoding="utf-8"))
            self.assertTrue(metrics["aider_summary"]["direct_edit_short_circuit_triggered"])
            self.assertEqual("mixed_batch", metrics["preflight"]["direct_edit_candidate"]["operation"])
            self.assertTrue(metrics["preflight"]["direct_edit_candidate"]["contains_excerpt_patch"])
            self.assertEqual(
                ["excerpt_patch", "insert_before"],
                metrics["preflight"]["direct_edit_candidate"]["operation_types"],
            )
            direct_edit = json.loads((run_folder / "AIDER_DIRECT_EDIT.json").read_text(encoding="utf-8"))
            self.assertEqual("mixed_batch", direct_edit["operation"])

    def test_run_aider_worker_short_circuits_longer_mixed_batch_with_excerpt_budget(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "direct-edit-mixed-batch-long"
            target_a = Path(temp_dir) / "target-a.txt"
            target_b = Path(temp_dir) / "target-b.txt"
            old_block = "".join(f"old line {index:03d}\n" for index in range(120))
            new_block = "".join(f"new line {index:03d}\n" for index in range(120))
            target_a.write_text("alpha\n" + old_block + "omega\n", encoding="utf-8")
            target_b.write_text("left\nright\n", encoding="utf-8")
            (run_folder / "TASK.md").parent.mkdir(parents=True, exist_ok=True)
            (run_folder / "TASK.md").write_text("task\n", encoding="utf-8")
            (run_folder / "INPUT.md").write_text("input\n", encoding="utf-8")
            (run_folder / "MODEL_REQUEST.md").write_text(
                (
                    "# Model Request\n\n"
                    f"- In `{os.fspath(target_a)}`, apply excerpt patches.\n"
                    "```text\n"
                    "<<<<<<< SEARCH\n"
                    f"{old_block}"
                    "=======\n"
                    f"{new_block}"
                    ">>>>>>> REPLACE\n"
                    "```\n"
                    f"- In `{os.fspath(target_b)}`, replace `left` with `start`.\n"
                    "- Edit only the listed files.\n"
                ),
                encoding="utf-8",
            )

            with patch.object(run_aider_worker, "run_endpoint_prewarm") as mocked_prewarm:
                with patch.object(run_aider_worker.subprocess, "run") as mocked_run:
                    exit_code = run_aider_worker.main(
                        [os.fspath(run_folder), os.fspath(target_a), os.fspath(target_b)]
                    )

            self.assertEqual(0, exit_code)
            self.assertEqual("alpha\n" + new_block + "omega\n", target_a.read_text(encoding="utf-8"))
            self.assertEqual("start\nright\n", target_b.read_text(encoding="utf-8"))
            mocked_prewarm.assert_not_called()
            mocked_run.assert_not_called()

            metrics = json.loads((run_folder / "METRICS.json").read_text(encoding="utf-8"))
            self.assertTrue(metrics["aider_summary"]["direct_edit_short_circuit_triggered"])
            self.assertGreater(
                metrics["preflight"]["direct_edit_candidate"]["prompt_char_count"],
                run_aider_worker.DIRECT_EDIT_MULTI_FILE_MAX_PROMPT_CHARS,
            )
            self.assertEqual(
                run_aider_worker.DIRECT_EDIT_EXCERPT_PATCH_MAX_PROMPT_CHARS,
                metrics["preflight"]["direct_edit_candidate"]["prompt_char_limit"],
            )
            self.assertEqual("mixed_batch", metrics["preflight"]["direct_edit_candidate"]["operation"])

    def test_run_aider_worker_short_circuits_excerpt_patch_before_aider(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "direct-edit-excerpt-patch"
            target = Path(temp_dir) / "target.txt"
            target.write_text("alpha\nbeta\nomega\n", encoding="utf-8")
            (run_folder / "TASK.md").parent.mkdir(parents=True, exist_ok=True)
            (run_folder / "TASK.md").write_text("task\n", encoding="utf-8")
            (run_folder / "INPUT.md").write_text("input\n", encoding="utf-8")
            (run_folder / "MODEL_REQUEST.md").write_text(
                (
                    "# Model Request\n\n"
                    f"- In `{os.fspath(target)}`, apply excerpt patches.\n"
                    "```text\n"
                    "<<<<<<< SEARCH\n"
                    "beta\n"
                    "=======\n"
                    "gamma\n"
                    ">>>>>>> REPLACE\n"
                    "<<<<<<< SEARCH\n"
                    "gamma\n"
                    "=======\n"
                    "delta\n"
                    ">>>>>>> REPLACE\n"
                    "```\n"
                    "- Edit only the listed file.\n"
                ),
                encoding="utf-8",
            )

            with patch.object(run_aider_worker, "run_endpoint_prewarm") as mocked_prewarm:
                with patch.object(run_aider_worker.subprocess, "run") as mocked_run:
                    exit_code = run_aider_worker.main([os.fspath(run_folder), os.fspath(target)])

            self.assertEqual(0, exit_code)
            self.assertEqual("alpha\ndelta\nomega\n", target.read_text(encoding="utf-8"))
            mocked_prewarm.assert_not_called()
            mocked_run.assert_not_called()

            metrics = json.loads((run_folder / "METRICS.json").read_text(encoding="utf-8"))
            self.assertTrue(metrics["aider_summary"]["direct_edit_short_circuit_triggered"])
            self.assertEqual("excerpt_patch", metrics["preflight"]["direct_edit_candidate"]["operation"])
            self.assertEqual(1, metrics["preflight"]["direct_edit_candidate"]["operation_count"])
            self.assertEqual(["excerpt_patch"], metrics["preflight"]["direct_edit_candidate"]["operation_types"])
            self.assertEqual(2, metrics["preflight"]["direct_edit_candidate"]["operations"][0]["patch_count"])
            direct_edit = json.loads((run_folder / "AIDER_DIRECT_EDIT.json").read_text(encoding="utf-8"))
            self.assertEqual("excerpt_patch", direct_edit["operation"])

    def test_run_aider_worker_short_circuits_longer_excerpt_patch_before_aider(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "direct-edit-excerpt-patch-long"
            target = Path(temp_dir) / "target.txt"
            old_block = "".join(f"old line {index:02d}\n" for index in range(80))
            new_block = "".join(f"new line {index:02d}\n" for index in range(80))
            target.write_text("alpha\n" + old_block + "omega\n", encoding="utf-8")
            (run_folder / "TASK.md").parent.mkdir(parents=True, exist_ok=True)
            (run_folder / "TASK.md").write_text("task\n", encoding="utf-8")
            (run_folder / "INPUT.md").write_text("input\n", encoding="utf-8")
            (run_folder / "MODEL_REQUEST.md").write_text(
                (
                    "# Model Request\n\n"
                    f"- In `{os.fspath(target)}`, apply excerpt patches.\n"
                    "```text\n"
                    "<<<<<<< SEARCH\n"
                    f"{old_block}"
                    "=======\n"
                    f"{new_block}"
                    ">>>>>>> REPLACE\n"
                    "```\n"
                    "- Edit only the listed file.\n"
                ),
                encoding="utf-8",
            )

            with patch.object(run_aider_worker, "run_endpoint_prewarm") as mocked_prewarm:
                with patch.object(run_aider_worker.subprocess, "run") as mocked_run:
                    exit_code = run_aider_worker.main([os.fspath(run_folder), os.fspath(target)])

            self.assertEqual(0, exit_code)
            self.assertEqual("alpha\n" + new_block + "omega\n", target.read_text(encoding="utf-8"))
            mocked_prewarm.assert_not_called()
            mocked_run.assert_not_called()

            metrics = json.loads((run_folder / "METRICS.json").read_text(encoding="utf-8"))
            self.assertTrue(metrics["aider_summary"]["direct_edit_short_circuit_triggered"])
            self.assertGreater(metrics["preflight"]["direct_edit_candidate"]["prompt_char_count"], 1200)
            self.assertEqual(
                run_aider_worker.DIRECT_EDIT_EXCERPT_PATCH_MAX_PROMPT_CHARS,
                metrics["preflight"]["direct_edit_candidate"]["prompt_char_limit"],
            )
            self.assertTrue(metrics["preflight"]["direct_edit_candidate"]["eligible"])

    def test_run_aider_worker_records_block_direct_edit_classification_when_start_anchor_not_unique(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "direct-edit-block-no-unique-start"
            target = Path(temp_dir) / "target.txt"
            target.write_text("beta\nalpha\nbeta\ngamma\n", encoding="utf-8")
            (run_folder / "TASK.md").parent.mkdir(parents=True, exist_ok=True)
            (run_folder / "TASK.md").write_text("task\n", encoding="utf-8")
            (run_folder / "INPUT.md").write_text("input\n", encoding="utf-8")
            (run_folder / "MODEL_REQUEST.md").write_text(
                (
                    "# Model Request\n\n"
                    f"- In `{os.fspath(target)}`, replace the block from `beta\\n` through `gamma\\n` with `delta\\n`.\n"
                    "- Edit only the listed file.\n"
                ).replace("\\n", "\n"),
                encoding="utf-8",
            )
            timeout_error = run_aider_worker.subprocess.TimeoutExpired(
                cmd=["aider"],
                timeout=110,
                output="partial output\n",
                stderr="provider stalled\n",
            )

            with patch.object(run_aider_worker, "run_endpoint_prewarm", return_value=None):
                with patch.object(run_aider_worker.subprocess, "run", side_effect=timeout_error):
                    exit_code = run_aider_worker.main([os.fspath(run_folder), os.fspath(target)])

            self.assertEqual(1, exit_code)
            self.assertEqual("beta\nalpha\nbeta\ngamma\n", target.read_text(encoding="utf-8"))
            classification = json.loads((run_folder / "AIDER_DIRECT_EDIT.json").read_text(encoding="utf-8"))
            self.assertEqual("no_unique_start_anchor", classification["status"])
            self.assertEqual(2, classification["operations"][0]["start_anchor_match_count"])

    def test_run_aider_worker_records_excerpt_patch_classification_when_search_not_unique(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "direct-edit-excerpt-patch-no-unique"
            target = Path(temp_dir) / "target.txt"
            target.write_text("beta\nalpha\nbeta\n", encoding="utf-8")
            (run_folder / "TASK.md").parent.mkdir(parents=True, exist_ok=True)
            (run_folder / "TASK.md").write_text("task\n", encoding="utf-8")
            (run_folder / "INPUT.md").write_text("input\n", encoding="utf-8")
            (run_folder / "MODEL_REQUEST.md").write_text(
                (
                    "# Model Request\n\n"
                    f"- In `{os.fspath(target)}`, apply excerpt patches.\n"
                    "```text\n"
                    "<<<<<<< SEARCH\n"
                    "beta\n"
                    "=======\n"
                    "gamma\n"
                    ">>>>>>> REPLACE\n"
                    "```\n"
                    "- Edit only the listed file.\n"
                ),
                encoding="utf-8",
            )
            timeout_error = run_aider_worker.subprocess.TimeoutExpired(
                cmd=["aider"],
                timeout=110,
                output="partial output\n",
                stderr="provider stalled\n",
            )

            with patch.object(run_aider_worker, "run_endpoint_prewarm", return_value=None):
                with patch.object(run_aider_worker.subprocess, "run", side_effect=timeout_error):
                    exit_code = run_aider_worker.main([os.fspath(run_folder), os.fspath(target)])

            self.assertEqual(1, exit_code)
            self.assertEqual("beta\nalpha\nbeta\n", target.read_text(encoding="utf-8"))
            classification = json.loads((run_folder / "AIDER_DIRECT_EDIT.json").read_text(encoding="utf-8"))
            self.assertEqual("no_unique_patch_match", classification["status"])
            self.assertEqual(2, classification["operations"][0]["patch_summaries"][0]["match_count"])

    def test_run_aider_worker_records_direct_edit_classification_when_no_unique_match(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "direct-edit-no-match"
            target = Path(temp_dir) / "target.txt"
            target.write_text("old old\n", encoding="utf-8")
            (run_folder / "TASK.md").parent.mkdir(parents=True, exist_ok=True)
            (run_folder / "TASK.md").write_text("task\n", encoding="utf-8")
            (run_folder / "INPUT.md").write_text("input\n", encoding="utf-8")
            (run_folder / "MODEL_REQUEST.md").write_text(
                (
                    "# Model Request\n\n"
                    f"- In `{os.fspath(target)}`, replace `old` with `new`.\n"
                    "- Edit only the listed file.\n"
                ),
                encoding="utf-8",
            )
            timeout_error = run_aider_worker.subprocess.TimeoutExpired(
                cmd=["aider"],
                timeout=110,
                output="partial output\n",
                stderr="provider stalled\n",
            )

            with patch.object(run_aider_worker, "run_endpoint_prewarm", return_value=None):
                with patch.object(run_aider_worker.subprocess, "run", side_effect=timeout_error):
                    exit_code = run_aider_worker.main([os.fspath(run_folder), os.fspath(target)])

            self.assertEqual(1, exit_code)
            self.assertEqual("old old\n", target.read_text(encoding="utf-8"))
            metrics = json.loads((run_folder / "METRICS.json").read_text(encoding="utf-8"))
            self.assertFalse(metrics["aider_summary"]["direct_edit_fallback_triggered"])
            self.assertTrue(metrics["aider_summary"]["fatal_error_detected"])
            self.assertTrue((run_folder / "AIDER_DIRECT_EDIT.json").is_file())
            classification = json.loads((run_folder / "AIDER_DIRECT_EDIT.json").read_text(encoding="utf-8"))
            self.assertEqual("no_unique_match", classification["status"])
            self.assertEqual(2, classification["operations"][0]["match_count"])


if __name__ == "__main__":
    unittest.main()
