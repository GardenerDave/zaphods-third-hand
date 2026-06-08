import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys

sys.path.insert(0, os.fspath(Path(__file__).resolve().parents[1]))

import run_aider_worker


class AiderPrepTests(unittest.TestCase):
    def test_run_aider_worker_blocks_over_budget_before_subprocess(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "over-budget"
            run_folder.mkdir()
            (run_folder / "TASK.md").write_text("task\n", encoding="utf-8")
            (run_folder / "INPUT.md").write_text("input\n", encoding="utf-8")
            (run_folder / "MODEL_REQUEST.md").write_text(("very long prompt " * 200) + "\n", encoding="utf-8")

            with patch.object(run_aider_worker, "run_endpoint_prewarm", return_value=None):
                with patch.object(run_aider_worker.subprocess, "run") as mocked_run:
                    exit_code = run_aider_worker.main(
                        [
                            os.fspath(run_folder),
                            "--context-window",
                            "256",
                            "--completion-reserve",
                            "128",
                            "local_harness/run_aider_worker.py",
                        ]
                    )

            self.assertEqual(1, exit_code)
            mocked_run.assert_not_called()
            output = (run_folder / "OUTPUT.md").read_text(encoding="utf-8")
            self.assertIn("Preflight blocked the run", output)
            self.assertIn("Matches validated pilot shape", output)
            metrics = json.loads((run_folder / "METRICS.json").read_text(encoding="utf-8"))
            self.assertTrue(metrics["preflight_blocked"])

    def test_run_aider_worker_snapshots_read_only_inputs(self):
        completed = run_aider_worker.subprocess.CompletedProcess(
            args=["aider"],
            returncode=0,
            stdout="ok\n",
            stderr="",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "read-snapshot"
            run_folder.mkdir()
            read_source = Path(temp_dir) / "reference.txt"
            target = Path(temp_dir) / "target.txt"
            read_source.write_text("one\ntwo\nthree\nfour\n", encoding="utf-8")
            target.write_text("placeholder\n", encoding="utf-8")
            (run_folder / "TASK.md").write_text("task\n", encoding="utf-8")
            (run_folder / "INPUT.md").write_text("input\n", encoding="utf-8")
            (run_folder / "MODEL_REQUEST.md").write_text("small prompt\n", encoding="utf-8")

            with patch.object(run_aider_worker, "run_endpoint_prewarm", return_value=None):
                with patch.object(run_aider_worker.subprocess, "run", return_value=completed) as mocked_run:
                    exit_code = run_aider_worker.main(
                        [
                            os.fspath(run_folder),
                            "--read",
                            os.fspath(read_source),
                            "--read-head-lines",
                            "2",
                            os.fspath(target),
                        ]
                    )

            self.assertEqual(0, exit_code)
            snippet_dir = run_folder / "00_read_snippets"
            snippet_files = list(snippet_dir.iterdir())
            self.assertEqual(1, len(snippet_files))
            snippet_text = snippet_files[0].read_text(encoding="utf-8")
            self.assertIn("# Source:", snippet_text)
            self.assertIn("[truncated after 2 lines]", snippet_text)

            called_command = mocked_run.call_args.args[0]
            self.assertIn(str(snippet_files[0]), called_command)
            metrics = json.loads((run_folder / "METRICS.json").read_text(encoding="utf-8"))
            self.assertTrue(metrics["preflight"]["validated_shape_match"])
            self.assertEqual("fit-head", metrics["prepared_read_inputs"][0]["mode"])

    def test_run_aider_worker_fits_read_context_to_budget(self):
        completed = run_aider_worker.subprocess.CompletedProcess(
            args=["aider"],
            returncode=0,
            stdout="ok\n",
            stderr="",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "fit-budget"
            run_folder.mkdir()
            read_source = Path(temp_dir) / "reference.txt"
            read_source.write_text(("0123456789 " * 10 + "\n") * 40, encoding="utf-8")
            target = Path(temp_dir) / "target.txt"
            target.write_text("placeholder\n", encoding="utf-8")
            (run_folder / "TASK.md").write_text("task\n", encoding="utf-8")
            (run_folder / "INPUT.md").write_text("input\n", encoding="utf-8")
            (run_folder / "MODEL_REQUEST.md").write_text("small prompt\n", encoding="utf-8")

            with patch.object(run_aider_worker, "run_endpoint_prewarm", return_value=None):
                with patch.object(run_aider_worker.subprocess, "run", return_value=completed):
                    exit_code = run_aider_worker.main(
                        [
                            os.fspath(run_folder),
                            "--read",
                            os.fspath(read_source),
                            "--read-head-lines",
                            "40",
                            "--context-window",
                            "512",
                            "--completion-reserve",
                            "128",
                            "--protocol-overhead-tokens",
                            "128",
                            os.fspath(target),
                        ]
                    )

            self.assertEqual(0, exit_code)
            metrics = json.loads((run_folder / "METRICS.json").read_text(encoding="utf-8"))
            self.assertTrue(metrics["fit_read_context"])
            self.assertTrue(metrics["preflight"]["within_budget"])
            prepared = metrics["prepared_read_inputs"][0]
            self.assertLess(prepared["kept_line_count"], 40)
            self.assertIsNotNone(prepared["char_budget"])

    def test_run_aider_worker_bundles_multiple_read_inputs(self):
        completed = run_aider_worker.subprocess.CompletedProcess(
            args=["aider"],
            returncode=0,
            stdout="ok\n",
            stderr="",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "bundle-reads"
            run_folder.mkdir()
            read_a = Path(temp_dir) / "a.txt"
            read_b = Path(temp_dir) / "b.txt"
            target = Path(temp_dir) / "target.txt"
            read_a.write_text("alpha\nbeta\n", encoding="utf-8")
            read_b.write_text("gamma\ndelta\n", encoding="utf-8")
            target.write_text("placeholder\n", encoding="utf-8")
            (run_folder / "TASK.md").write_text("task\n", encoding="utf-8")
            (run_folder / "INPUT.md").write_text("input\n", encoding="utf-8")
            (run_folder / "MODEL_REQUEST.md").write_text("small prompt\n", encoding="utf-8")

            with patch.object(run_aider_worker, "run_endpoint_prewarm", return_value=None):
                with patch.object(run_aider_worker.subprocess, "run", return_value=completed) as mocked_run:
                    exit_code = run_aider_worker.main(
                        [
                            os.fspath(run_folder),
                            "--no-inline-read-digest",
                            "--read",
                            os.fspath(read_a),
                            "--read",
                            os.fspath(read_b),
                            os.fspath(target),
                        ]
                    )

            self.assertEqual(0, exit_code)
            called_command = mocked_run.call_args.args[0]
            read_flags = [index for index, value in enumerate(called_command) if value == "--read"]
            self.assertEqual(1, len(read_flags))
            bundle_path = called_command[read_flags[0] + 1]
            bundle_text = Path(bundle_path).read_text(encoding="utf-8")
            self.assertIn("## Source 1:", bundle_text)
            self.assertIn("## Source 2:", bundle_text)

            metrics = json.loads((run_folder / "METRICS.json").read_text(encoding="utf-8"))
            self.assertEqual([bundle_path], metrics["aider_read_inputs"])
            self.assertEqual(2, metrics["read_bundle"]["source_count"])

    def test_run_aider_worker_inlines_read_digest_for_multiple_reads(self):
        completed = run_aider_worker.subprocess.CompletedProcess(
            args=["aider"],
            returncode=0,
            stdout="ok\n",
            stderr="",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "inline-digest"
            run_folder.mkdir()
            read_a = Path(temp_dir) / "a.txt"
            read_b = Path(temp_dir) / "b.txt"
            target = Path(temp_dir) / "target.txt"
            read_a.write_text("alpha context\nbeta context\n", encoding="utf-8")
            read_b.write_text("gamma context\ndelta context\n", encoding="utf-8")
            target.write_text("placeholder\n", encoding="utf-8")
            (run_folder / "TASK.md").write_text("task\n", encoding="utf-8")
            (run_folder / "INPUT.md").write_text("input\n", encoding="utf-8")
            (run_folder / "MODEL_REQUEST.md").write_text("small prompt\n", encoding="utf-8")

            with patch.object(run_aider_worker, "run_endpoint_prewarm", return_value=None):
                with patch.object(run_aider_worker.subprocess, "run", return_value=completed) as mocked_run:
                    exit_code = run_aider_worker.main(
                        [
                            os.fspath(run_folder),
                            "--read",
                            os.fspath(read_a),
                            "--read",
                            os.fspath(read_b),
                            os.fspath(target),
                        ]
                    )

            self.assertEqual(0, exit_code)
            called_command = mocked_run.call_args.args[0]
            self.assertNotIn("--read", called_command)
            message_text = (run_folder / "AIDER_MESSAGE.md").read_text(encoding="utf-8")
            self.assertIn("Read-only digest:", message_text)
            self.assertIn(os.fspath(read_a), message_text)
            self.assertIn(os.fspath(read_b), message_text)

            metrics = json.loads((run_folder / "METRICS.json").read_text(encoding="utf-8"))
            self.assertEqual([], metrics["aider_read_inputs"])
            self.assertEqual(2, metrics["read_digest"]["source_count"])

    def test_validated_shape_match_for_tiny_prompt_and_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "tiny-shape"
            run_folder.mkdir()
            target = Path(temp_dir) / "tiny.txt"
            target.write_text("ok\n", encoding="utf-8")
            (run_folder / "TASK.md").write_text("task\n", encoding="utf-8")
            (run_folder / "INPUT.md").write_text("input\n", encoding="utf-8")
            (run_folder / "MODEL_REQUEST.md").write_text("Replace ok with ok2.\n", encoding="utf-8")

            args = run_aider_worker.parse_args(
                run_aider_worker.build_parser(),
                [os.fspath(run_folder), os.fspath(target)],
            )
            run_aider_worker.apply_profile_defaults(args)
            args.original_prompt_text = (run_folder / "MODEL_REQUEST.md").read_text(encoding="utf-8")
            effective_prompt, args.prompt_mode = run_aider_worker.build_effective_prompt(
                args,
                args.original_prompt_text,
            )
            prepared_reads, read_metadata = run_aider_worker.prepare_read_inputs(args, run_folder, effective_prompt)
            preflight = run_aider_worker.build_preflight(args, effective_prompt, prepared_reads, read_metadata)

        self.assertTrue(preflight["validated_shape_match"])
        self.assertEqual(
            preflight["estimated_total_input_tokens"] + preflight["protocol_overhead_tokens"],
            preflight["estimated_total_with_overhead_tokens"],
        )

    def test_validated_shape_match_allows_six_tiny_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "six-file-shape"
            run_folder.mkdir()
            targets = []
            for index in range(6):
                target = Path(temp_dir) / f"tiny_{index}.txt"
                target.write_text("ok\n", encoding="utf-8")
                targets.append(os.fspath(target))
            (run_folder / "TASK.md").write_text("task\n", encoding="utf-8")
            (run_folder / "INPUT.md").write_text("input\n", encoding="utf-8")
            (run_folder / "MODEL_REQUEST.md").write_text("Replace ok with ok2 in each file.\n", encoding="utf-8")

            args = run_aider_worker.parse_args(
                run_aider_worker.build_parser(),
                [os.fspath(run_folder), *targets],
            )
            run_aider_worker.apply_profile_defaults(args)
            args.original_prompt_text = (run_folder / "MODEL_REQUEST.md").read_text(encoding="utf-8")
            effective_prompt, args.prompt_mode = run_aider_worker.build_effective_prompt(
                args,
                args.original_prompt_text,
            )
            prepared_reads, read_metadata = run_aider_worker.prepare_read_inputs(args, run_folder, effective_prompt)
            preflight = run_aider_worker.build_preflight(args, effective_prompt, prepared_reads, read_metadata)

        self.assertTrue(preflight["validated_shape_match"])

    def test_validated_shape_match_allows_ten_tiny_files_and_one_read(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "ten-file-read-shape"
            run_folder.mkdir()
            targets = []
            for index in range(10):
                target = Path(temp_dir) / f"tiny_{index}.txt"
                target.write_text("ok\n", encoding="utf-8")
                targets.append(os.fspath(target))
            read_source = Path(temp_dir) / "reference.txt"
            read_source.write_text("ref line\n" * 8, encoding="utf-8")
            (run_folder / "TASK.md").write_text("task\n", encoding="utf-8")
            (run_folder / "INPUT.md").write_text("input\n", encoding="utf-8")
            (run_folder / "MODEL_REQUEST.md").write_text("Replace ok with ok2 in each file.\n", encoding="utf-8")

            args = run_aider_worker.parse_args(
                run_aider_worker.build_parser(),
                [os.fspath(run_folder), "--read", os.fspath(read_source), *targets],
            )
            run_aider_worker.apply_profile_defaults(args)
            args.original_prompt_text = (run_folder / "MODEL_REQUEST.md").read_text(encoding="utf-8")
            effective_prompt, args.prompt_mode = run_aider_worker.build_effective_prompt(
                args,
                args.original_prompt_text,
            )
            prepared_reads, read_metadata = run_aider_worker.prepare_read_inputs(args, run_folder, effective_prompt)
            preflight = run_aider_worker.build_preflight(args, effective_prompt, prepared_reads, read_metadata)

        self.assertTrue(preflight["validated_shape_match"])


if __name__ == "__main__":
    unittest.main()
