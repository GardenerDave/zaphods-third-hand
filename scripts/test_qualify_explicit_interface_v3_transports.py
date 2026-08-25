#!/usr/bin/env python3
"""Model-free tests for the V3 transport qualification boundary."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import qualify_explicit_interface_v3_transports as module


MODEL_PAYLOAD = {
    "data": [{"id": module.LOCAL_MODEL}],
    "object": "list",
}


class FakeResponse:
    status = "ok"
    content = "TRANSPORT_OK"
    request_url = "http://192.168.1.16:8080/v1/chat/completions"

    def metadata(self):
        return {"status": self.status, "request_url": self.request_url}


class QualificationHarnessTests(unittest.TestCase):
    def test_request_path_uses_validated_url(self):
        result = module.request_path_regression()
        self.assertTrue(result["request_path_uses_validated_base_url"])
        self.assertTrue(result["placeholder_absent"])

    def test_success_records_terminal_and_counter(self):
        with tempfile.TemporaryDirectory() as raw_dir:
            run_dir = Path(raw_dir) / "run"
            raw_models = json.dumps(MODEL_PAYLOAD, separators=(",", ":")).encode()
            with patch.object(module, "fetch_models_raw", return_value=(raw_models, MODEL_PAYLOAD)), patch.object(module, "call_worker", return_value=FakeResponse()):
                result = module.local_requalification(run_dir, "http://192.168.1.16:8080/v1")
            self.assertTrue(result["transport_qualified"])
            self.assertEqual(result["completion_calls"], 1)
            terminal = json.loads((run_dir / "local_transport_requalification.terminal.json").read_text())
            self.assertEqual(terminal["terminal"], True)
            self.assertEqual(terminal["status"], "RESPONSE_CAPTURED")

    def test_failure_records_terminal_without_losing_call(self):
        with tempfile.TemporaryDirectory() as raw_dir:
            run_dir = Path(raw_dir) / "run"
            raw_models = json.dumps(MODEL_PAYLOAD, separators=(",", ":")).encode()
            with patch.object(module, "fetch_models_raw", return_value=(raw_models, MODEL_PAYLOAD)), patch.object(module, "call_worker", side_effect=RuntimeError("synthetic transport failure")):
                result = module.local_requalification(run_dir, "http://192.168.1.16:8080/v1")
            self.assertFalse(result["transport_qualified"])
            self.assertEqual(result["completion_calls"], 1)
            terminal = json.loads((run_dir / "local_transport_requalification.terminal.json").read_text())
            self.assertEqual(terminal["terminal"], True)
            self.assertEqual(terminal["status"], "INFRASTRUCTURE_FAILURE")

    def test_existing_run_is_refused(self):
        with tempfile.TemporaryDirectory() as raw_dir:
            run_dir = Path(raw_dir) / "run"
            run_dir.mkdir()
            with self.assertRaises(RuntimeError):
                module.run_local_requalification(run_dir, "http://192.168.1.16:8080/v1")


if __name__ == "__main__":
    unittest.main()
