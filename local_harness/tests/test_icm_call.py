import hashlib
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import sys

sys.path.insert(0, os.fspath(Path(__file__).resolve().parents[1]))

import icm_call


class FakeHTTPResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeHTTPError(icm_call.urllib.error.HTTPError):
    def __init__(self, url, code, msg, hdrs, payload: bytes):
        super().__init__(url, code, msg, hdrs, fp=None)
        self._payload = payload
        self.read_calls = 0

    def read(self):  # type: ignore[override]
        self.read_calls += 1
        return self._payload


class IcmCallTests(unittest.TestCase):
    def test_resolve_worker_spec_applies_overrides(self):
        spec = icm_call.resolve_worker_spec(
            "handoff",
            base_url="http://localhost:8083/v1/",
            model="gemma-test.gguf",
            final_only=True,
        )

        self.assertEqual("http://localhost:8083/v1", spec.base_url)
        self.assertEqual("gemma-test.gguf", spec.model)
        self.assertTrue(spec.append_no_think)

    def test_call_worker_returns_chat_content(self):
        payload = {
            "model": "gemma-test.gguf",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": "ok"},
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 1},
        }
        with patch.object(
            icm_call.urllib.request,
            "urlopen",
            return_value=FakeHTTPResponse(payload),
        ):
            response = icm_call.call_worker(
                icm_call.resolve_worker_spec(
                    "handoff",
                    base_url="http://localhost:8083/v1",
                    model="gemma-test.gguf",
                ),
                "Reply with exactly: ok",
                max_tokens=8,
            )

        self.assertEqual("ok", response.content)
        self.assertEqual("ok", response.status)
        self.assertEqual("gemma-test.gguf", response.model)
        self.assertEqual("gemma-test.gguf", response.configured_model)
        self.assertFalse(response.model_resolution_attempted)

    def test_main_writes_request_intent_before_transport(self):
        payload = {
            "model": "gemma-test.gguf",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": "ok"},
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            intent_path = Path(temp_dir) / "worker_b_call_intent.json"
            prompt_path = Path(temp_dir) / "prompt.md"
            prompt_path.write_text("Reply with exactly: ok", encoding="utf-8")

            def fake_urlopen(request, timeout=30):
                self.assertTrue(intent_path.is_file())
                intent = json.loads(intent_path.read_text(encoding="utf-8"))
                self.assertEqual("prepared_not_sent", intent["state"])
                self.assertEqual("gemma-test.gguf", intent["worker_identity"])
                self.assertIn("request_body_sha256", intent)
                self.assertGreater(intent["request_body_length"], 0)
                return FakeHTTPResponse(payload)

            with patch.object(icm_call.urllib.request, "urlopen", side_effect=fake_urlopen):
                exit_code = icm_call.main(
                    [
                        "handoff",
                        "--base-url",
                        "http://localhost:8083/v1",
                        "--model",
                        "gemma-test.gguf",
                        "--request-intent-out",
                        os.fspath(intent_path),
                        "--prompt-file",
                        os.fspath(prompt_path),
                    ]
                )

            self.assertEqual(0, exit_code)
            intent = json.loads(intent_path.read_text(encoding="utf-8"))
            self.assertEqual("prepared_not_sent", intent["state"])
            transport_lines = (intent_path.with_name("worker_b_call_intent.transport_events.jsonl")).read_text(
                encoding="utf-8"
            ).splitlines()
            self.assertGreaterEqual(len(transport_lines), 3)
            self.assertEqual("transport_started", json.loads(transport_lines[0])["state"])
            self.assertEqual("response_received", json.loads(transport_lines[1])["state"])
            self.assertEqual("completed", json.loads(transport_lines[-1])["state"])
            self.assertEqual("gemma-test.gguf", json.loads(transport_lines[-1])["worker_identity"])
            self.assertEqual(hashlib.sha256(prompt_path.read_bytes()).hexdigest(), intent["source_continuation_sha256"])

    def test_main_with_prompt_file_and_positional_prompt_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            prompt_path = Path(temp_dir) / "prompt.md"
            prompt_path.write_text("Reply with exactly: ok", encoding="utf-8")
            exit_code = icm_call.main(
                [
                    "handoff",
                    "--base-url",
                    "http://localhost:8083/v1",
                    "--prompt-file",
                    os.fspath(prompt_path),
                    "Reply with exactly: ok",
                ]
            )
        self.assertEqual(1, exit_code)

    def test_render_request_only_emits_exact_request_body_without_network(self):
        def fail_urlopen(*args, **kwargs):
            raise AssertionError("network must not be used in render-only mode")

        with patch.object(icm_call.urllib.request, "urlopen", side_effect=fail_urlopen):
            with tempfile.TemporaryDirectory() as temp_dir:
                prompt = "Return exactly: ok"
                result = icm_call.main(
                    [
                        "handoff",
                        "--base-url",
                        "http://localhost:8083/v1",
                        "--model",
                        "gemma-test.gguf",
                        "--render-request-only",
                        prompt,
                    ]
                )

        self.assertEqual(0, result)
        self.assertTrue(True)

    def test_call_worker_reports_reasoning_only(self):
        payload = {
            "model": "gemma-test.gguf",
            "choices": [
                {
                    "finish_reason": "length",
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "reasoning_content": "thinking",
                    },
                }
            ],
        }
        with patch.object(
            icm_call.urllib.request,
            "urlopen",
            return_value=FakeHTTPResponse(payload),
        ):
            response = icm_call.call_worker(
                icm_call.resolve_worker_spec(
                    "handoff",
                    base_url="http://localhost:8083/v1",
                ),
                "Reply with exactly: ok",
                max_tokens=8,
            )

        self.assertEqual("reasoning_only", response.status)
        self.assertIn("thinking", response.content)

    def test_render_request_only_matches_actual_request_body(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            prompt_path = Path(temp_dir) / "prompt.md"
            prompt_path.write_text("Reply with exactly: ok", encoding="utf-8")
            stdout = io.StringIO()
            with patch.object(icm_call.urllib.request, "urlopen", side_effect=AssertionError("no network expected")):
                with redirect_stdout(stdout):
                    render = icm_call.main(
                        [
                            "handoff",
                            "--base-url",
                            "http://localhost:8083/v1",
                            "--model",
                            "gemma-test.gguf",
                            "--final-only",
                            "--prompt-file",
                            os.fspath(prompt_path),
                            "--render-request-only",
                        ]
                    )
            self.assertEqual(0, render)
            rendered = json.loads(stdout.getvalue())
            captured: dict[str, bytes] = {}

            def fake_urlopen(request, timeout=30):
                captured["body"] = request.data
                return FakeHTTPResponse(
                    {
                        "model": "gemma-test.gguf",
                        "choices": [
                            {
                                "finish_reason": "stop",
                                "message": {"role": "assistant", "content": "ok"},
                            }
                        ],
                    }
                )

            with patch.object(icm_call.urllib.request, "urlopen", side_effect=fake_urlopen):
                call_exit = icm_call.main(
                    [
                        "handoff",
                        "--base-url",
                        "http://localhost:8083/v1",
                        "--model",
                        "gemma-test.gguf",
                        "--final-only",
                        "--prompt-file",
                        os.fspath(prompt_path),
                    ]
                )

            self.assertEqual(0, call_exit)
            self.assertIn("body", captured)
            self.assertEqual(rendered["request_body_sha256"], hashlib.sha256(captured["body"]).hexdigest())
            self.assertEqual(rendered["request_body_length"], len(captured["body"]))
            self.assertIn("/no_think", rendered["prompt"])
            self.assertTrue(rendered["prompt"].endswith("/no_think"))

    def test_main_expected_request_body_hash_fails_closed_before_http(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            prompt_path = Path(temp_dir) / "prompt.md"
            prompt_path.write_text("Reply with exactly: ok", encoding="utf-8")
            with patch.object(icm_call.urllib.request, "urlopen", side_effect=AssertionError("no network expected")):
                exit_code = icm_call.main(
                    [
                        "handoff",
                        "--base-url",
                        "http://localhost:8083/v1",
                        "--model",
                        "gemma-test.gguf",
                        "--prompt-file",
                        os.fspath(prompt_path),
                        "--expected-request-body-sha256",
                        "0" * 64,
                ]
            )
        self.assertEqual(1, exit_code)

    def test_main_rejects_reuse_of_existing_request_intent_without_http(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            intent_path = Path(temp_dir) / "intent.json"
            intent_path.write_text("{}", encoding="utf-8")
            prompt_path = Path(temp_dir) / "prompt.md"
            prompt_path.write_text("Reply with exactly: ok", encoding="utf-8")
            with patch.object(icm_call.urllib.request, "urlopen", side_effect=AssertionError("no network expected")) as mocked_urlopen:
                exit_code = icm_call.main(
                    [
                        "handoff",
                        "--base-url",
                        "http://localhost:8083/v1",
                        "--model",
                        "gemma-test.gguf",
                        "--request-intent-out",
                        os.fspath(intent_path),
                        "--prompt-file",
                        os.fspath(prompt_path),
                    ]
                )

            self.assertEqual(1, exit_code)
            self.assertFalse(mocked_urlopen.called)
            self.assertEqual("{}", intent_path.read_text(encoding="utf-8"))

    def test_main_records_transport_error_with_request_intent(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            intent_path = Path(temp_dir) / "intent.json"
            prompt_path = Path(temp_dir) / "prompt.md"
            prompt_path.write_text("Reply with exactly: ok", encoding="utf-8")

            def fail_urlopen(request, timeout=30):
                raise icm_call.urllib.error.URLError("connection refused")

            with patch.object(icm_call.urllib.request, "urlopen", side_effect=fail_urlopen):
                exit_code = icm_call.main(
                    [
                        "handoff",
                        "--base-url",
                        "http://localhost:8083/v1",
                        "--model",
                        "gemma-test.gguf",
                        "--request-intent-out",
                        os.fspath(intent_path),
                        "--prompt-file",
                        os.fspath(prompt_path),
                    ]
                )

            self.assertEqual(1, exit_code)
            intent = json.loads(intent_path.read_text(encoding="utf-8"))
            self.assertEqual("prepared_not_sent", intent["state"])
            self.assertFalse(intent["transport_started"])
            events = (intent_path.with_name("intent.transport_events.jsonl").read_text(encoding="utf-8").splitlines())
            self.assertTrue(any('"state": "transport_started"' in line for line in events))
            self.assertTrue(any('"state": "transport_error"' in line for line in events))

    def test_call_worker_reads_http_error_body_once(self):
        payload = b'{"error":"boom"}'
        observed = {}

        def fake_urlopen(request, timeout=30):
            observed["exc"] = FakeHTTPError(
                request.full_url,
                500,
                "server error",
                hdrs=None,
                payload=payload,
            )
            raise observed["exc"]

        with patch.object(icm_call.urllib.request, "urlopen", side_effect=fake_urlopen):
            response = icm_call.call_worker(
                icm_call.resolve_worker_spec(
                    "handoff",
                    base_url="http://localhost:8083/v1",
                    model="gemma-test.gguf",
                ),
                "Reply with exactly: ok",
                max_tokens=8,
            )

        self.assertEqual("http_error", response.status)
        self.assertEqual("[HTTP error 500]\n{\"error\":\"boom\"}", response.content)
        self.assertEqual(1, observed["exc"].read_calls)

    def test_call_worker_resolves_openai_alias_to_first_model_id(self):
        models_payload = {"data": [{"id": "gemma-real.gguf"}]}
        chat_payload = {
            "model": "gemma-real.gguf",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": "ok"},
                }
            ],
        }
        requests = []

        def fake_urlopen(request, timeout=30):
            requests.append(request)
            if request.full_url.endswith("/models"):
                return FakeHTTPResponse(models_payload)
            return FakeHTTPResponse(chat_payload)

        with patch.object(icm_call.urllib.request, "urlopen", side_effect=fake_urlopen):
            response = icm_call.call_worker(
                icm_call.resolve_worker_spec(
                    "handoff",
                    base_url="http://localhost:8083/v1",
                    model="openai/gemma4",
                ),
                "Reply with exactly: ok",
                max_tokens=8,
            )

        self.assertEqual(2, len(requests))
        self.assertTrue(requests[0].full_url.endswith("/models"))
        self.assertTrue(requests[1].full_url.endswith("/chat/completions"))
        request_payload = json.loads(requests[1].data.decode("utf-8"))
        self.assertEqual("gemma-real.gguf", request_payload["model"])
        self.assertEqual("openai/gemma4", response.configured_model)
        self.assertEqual("gemma-real.gguf", response.model)
        self.assertTrue(response.model_resolution_attempted)
        self.assertIsNone(response.model_resolution_error)

    def test_call_worker_falls_back_when_model_discovery_fails(self):
        chat_payload = {
            "model": "openai/gemma4",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": "ok"},
                }
            ],
        }
        requests = []

        def fake_urlopen(request, timeout=30):
            requests.append(request)
            if request.full_url.endswith("/models"):
                raise icm_call.urllib.error.URLError("model discovery down")
            return FakeHTTPResponse(chat_payload)

        with patch.object(icm_call.urllib.request, "urlopen", side_effect=fake_urlopen):
            response = icm_call.call_worker(
                icm_call.resolve_worker_spec(
                    "handoff",
                    base_url="http://localhost:8083/v1",
                    model="openai/gemma4",
                ),
                "Reply with exactly: ok",
                max_tokens=8,
            )

        self.assertEqual(2, len(requests))
        request_payload = json.loads(requests[1].data.decode("utf-8"))
        self.assertEqual("openai/gemma4", request_payload["model"])
        self.assertEqual("openai/gemma4", response.configured_model)
        self.assertEqual("openai/gemma4", response.model)
        self.assertTrue(response.model_resolution_attempted)
        self.assertIn("model discovery down", response.model_resolution_error)

    def test_call_worker_skips_model_resolution_for_non_alias_model(self):
        chat_payload = {
            "model": "gemma-test.gguf",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": "ok"},
                }
            ],
        }
        requests = []

        def fake_urlopen(request, timeout=30):
            requests.append(request)
            return FakeHTTPResponse(chat_payload)

        with patch.object(icm_call.urllib.request, "urlopen", side_effect=fake_urlopen):
            response = icm_call.call_worker(
                icm_call.resolve_worker_spec(
                    "handoff",
                    base_url="http://localhost:8083/v1",
                    model="gemma-test.gguf",
                ),
                "Reply with exactly: ok",
                max_tokens=8,
            )

        self.assertEqual(1, len(requests))
        self.assertTrue(requests[0].full_url.endswith("/chat/completions"))
        self.assertFalse(response.model_resolution_attempted)

    def test_list_models_uses_models_endpoint(self):
        payload = {"data": [{"id": "gemma-test.gguf"}]}
        with patch.object(
            icm_call.urllib.request,
            "urlopen",
            return_value=FakeHTTPResponse(payload),
        ) as mocked_urlopen:
            result = icm_call.list_models(
                icm_call.resolve_worker_spec(
                    "handoff",
                    base_url="http://localhost:8083/v1",
                )
            )

        request = mocked_urlopen.call_args.args[0]
        self.assertEqual("http://localhost:8083/v1/models", request.full_url)
        self.assertEqual(payload, result)

    def test_main_writes_metadata_file(self):
        payload = {
            "model": "gemma-test.gguf",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": "ok"},
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            metadata_path = Path(temp_dir) / "metadata.json"
            with patch.object(
                icm_call.urllib.request,
                "urlopen",
                return_value=FakeHTTPResponse(payload),
            ):
                exit_code = icm_call.main(
                    [
                        "handoff",
                        "--base-url",
                        "http://localhost:8083/v1",
                        "--metadata-out",
                        os.fspath(metadata_path),
                        "Reply with exactly: ok",
                    ]
                )

            self.assertEqual(0, exit_code)
            written = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.assertEqual("ok", written["status"])
            self.assertIn("configured_model", written)
            self.assertIn("resolved_model", written)

    def test_call_worker_writes_request_intent_and_transitions(self):
        payload = {
            "model": "gemma-test.gguf",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": "ok"},
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            intent_path = Path(temp_dir) / "intent.json"
            with patch.object(
                icm_call.urllib.request,
                "urlopen",
                return_value=FakeHTTPResponse(payload),
            ) as mocked_urlopen:
                response = icm_call.call_worker(
                    icm_call.resolve_worker_spec(
                        "handoff",
                        base_url="http://localhost:8083/v1",
                        model="gemma-test.gguf",
                        final_only=True,
                    ),
                    "Reply with exactly: ok",
                    max_tokens=8,
                    request_intent_out=intent_path,
                )

            self.assertEqual("ok", response.content)
            self.assertTrue(mocked_urlopen.called)
            intent = json.loads(intent_path.read_text(encoding="utf-8"))
            self.assertEqual("prepared_not_sent", intent["state"])
            self.assertFalse(intent["transport_started"])
            self.assertIn("request_body_sha256", intent)
            self.assertIn("transformed_user_message_sha256", intent)
            events = (intent_path.with_name("intent.transport_events.jsonl").read_text(encoding="utf-8").splitlines())
            self.assertTrue(any('"state": "transport_started"' in line for line in events))
            self.assertTrue(any('"state": "completed"' in line for line in events))

    def test_call_worker_records_transport_error_intent(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            intent_path = Path(temp_dir) / "intent.json"

            def fail_urlopen(request, timeout=30):
                raise icm_call.urllib.error.URLError("connection refused")

            with patch.object(icm_call.urllib.request, "urlopen", side_effect=fail_urlopen):
                response = icm_call.call_worker(
                    icm_call.resolve_worker_spec(
                        "handoff",
                        base_url="http://localhost:8083/v1",
                        model="gemma-test.gguf",
                    ),
                    "Reply with exactly: ok",
                    max_tokens=8,
                    request_intent_out=intent_path,
                )

            self.assertEqual("request_error", response.status)
            intent = json.loads(intent_path.read_text(encoding="utf-8"))
            self.assertEqual("prepared_not_sent", intent["state"])
            self.assertFalse(intent["transport_started"])
            events = (intent_path.with_name("intent.transport_events.jsonl")).read_text(encoding="utf-8").splitlines()
            self.assertTrue(any('"state": "transport_error"' in line for line in events))
            self.assertFalse(any('"state": "completed"' in line for line in events))

if __name__ == "__main__":
    unittest.main()
