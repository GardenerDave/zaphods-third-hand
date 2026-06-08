import json
import os
import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
