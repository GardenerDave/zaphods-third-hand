import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import sys

sys.path.insert(0, os.fspath(Path(__file__).resolve().parents[1]))

import run_aider_worker


class AiderRuntimeTests(unittest.TestCase):
    def test_run_endpoint_prewarm_uses_chat_completions(self):
        class FakeResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps(
                    {"choices": [{"message": {"content": "ok"}}]}
                ).encode("utf-8")

        args = run_aider_worker.parse_args(
            run_aider_worker.build_parser(),
            ["fake-run", "--model", "openai/gemma4", "--openai-api-base", "http://localhost:8083/v1"],
        )
        run_aider_worker.apply_profile_defaults(args)
        env = {"OPENAI_API_KEY": "dummy"}

        with patch.object(run_aider_worker.urllib.request, "urlopen", return_value=FakeResponse()) as mocked_urlopen:
            result = run_aider_worker.run_endpoint_prewarm(args, env)

        self.assertTrue(result["success"])
        self.assertTrue(result["response_preview"] == "ok")
        request = mocked_urlopen.call_args.args[0]
        self.assertEqual("http://localhost:8083/v1/chat/completions", request.full_url)

    def test_summarize_aider_output_detects_unexpected_edit(self):
        summary = run_aider_worker.summarize_aider_output(
            "Applied edit to foo.py\nApplied edit to bar.py\n",
            ["foo.py"],
        )

        self.assertEqual(["foo.py", "bar.py"], summary["applied_edits"])
        self.assertEqual(["bar.py"], summary["unexpected_edit_paths"])
        self.assertTrue(not summary["thinking_block_present"])

    def test_summarize_aider_output_detects_connection_error(self):
        summary = run_aider_worker.summarize_aider_output(
            (
                "litellm.InternalServerError: InternalServerError: OpenAIException - Connection error.\n"
                "Retrying in 0.2 seconds...\n"
                "Retrying in 0.5 seconds...\n"
            ),
            ["foo.py"],
        )

        self.assertTrue(summary["connection_error_detected"])
        self.assertFalse(summary["timeout_hint_detected"])
        self.assertEqual(2, summary["provider_retry_count"])
        self.assertTrue(summary["fatal_error_detected"])

    def test_summarize_aider_output_handles_wrapped_applied_edit_paths(self):
        summary = run_aider_worker.summarize_aider_output(
            "Applied edit to \nfoo.py\nApplied edit to \nbar.py\n",
            ["foo.py", "bar.py"],
        )

        self.assertEqual(["foo.py", "bar.py"], summary["applied_edits"])
        self.assertTrue(summary["all_selected_files_edited"])

    def test_summarize_aider_output_parses_comma_separated_tokens(self):
        summary = run_aider_worker.summarize_aider_output(
            "Tokens: 1,200 sent, 345 received.\n",
            ["foo.py"],
        )

        self.assertEqual(1200, summary["tokens_sent"])
        self.assertEqual(345, summary["tokens_received"])


if __name__ == "__main__":
    unittest.main()
