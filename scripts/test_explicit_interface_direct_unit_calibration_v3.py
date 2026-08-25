#!/usr/bin/env python3
"""Model-free regression tests for the V3 acquisition boundary."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import execute_explicit_interface_direct_unit_calibration_v3 as harness
import evaluate_explicit_interface_direct_unit_calibration_v3 as evaluator


class V3BoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.projection = harness.load_projection()
        cls.by_key = harness.validate_matched_messages(cls.projection)

    def test_schedule_is_balanced_and_matched(self) -> None:
        harness.validate_schedule(self.projection["schedule"], self.projection["cases"])
        self.assertEqual(len(self.projection["schedule"]), 32)
        self.assertEqual(sum(item["supplier_id"] == "local_teacher" for item in self.projection["schedule"]), 16)
        self.assertEqual(sum(item["supplier_id"] == "external_teacher" for item in self.projection["schedule"]), 16)
        for case in self.projection["cases"]:
            local = self.by_key[(case["case_id"], "local_teacher")]["supplier_message_bytes"]
            external = self.by_key[(case["case_id"], "external_teacher")]["supplier_message_bytes"]
            self.assertEqual(local, external)

    def test_exact_local_request_url_is_frozen(self) -> None:
        from local_harness.icm_spec import completion_url, resolve_worker_spec
        spec = resolve_worker_spec("handoff", base_url=harness.LOCAL_BASE_URL, model=harness.LOCAL_MODEL, api="openai-chat")
        self.assertEqual(spec.base_url, harness.LOCAL_BASE_URL)
        self.assertEqual(completion_url(spec), harness.LOCAL_BASE_URL + "/chat/completions")
        self.assertNotIn("<LAN_HOST>", completion_url(spec))

    def test_local_override_mismatch_fails_without_call(self) -> None:
        with mock.patch.dict("os.environ", {"ZTH_CAPABILITY_TEACHER_BASE_URL": "http://alternate.invalid/v1"}, clear=False):
            with self.assertRaises(RuntimeError):
                harness.validate_local_configuration()

    def test_external_invocation_receives_exact_frozen_runtime_environment(self) -> None:
        completed = mock.Mock(returncode=0, stdout=b"transport-test", stderr=b"")
        with mock.patch.object(harness.subprocess, "run", return_value=completed) as run:
            result = harness.capture_external(b"test")
        kwargs = run.call_args.kwargs
        self.assertEqual(kwargs["cwd"], harness.EXTERNAL_CWD)
        self.assertEqual(kwargs["env"]["HOME"], str(harness.EXTERNAL_HOME))
        self.assertEqual(kwargs["env"]["TMPDIR"], str(harness.EXTERNAL_TMPDIR))
        self.assertEqual(kwargs["env"]["CODEX_HOME"], str(harness.CODEX_HOME))
        self.assertEqual(result["terminal_disposition"], "RESPONSE_CAPTURED")

    def test_external_runtime_paths_are_frozen_outside_repository(self) -> None:
        runtime = harness.validate_external_runtime_paths(create=True)
        self.assertEqual(runtime["home"], "/tmp/zth_explicit_interface_v3_external_runtime/home")
        self.assertEqual(runtime["tmpdir"], "/tmp/zth_explicit_interface_v3_external_runtime/tmp")
        self.assertTrue(runtime["outside_repository"])

    def test_prepare_only_does_not_open_evaluator_or_claim_guard(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            guard = Path(directory) / "guard.json"
            with mock.patch.object(harness, "EVALUATOR_IMPL", Path(directory) / "unavailable-evaluator.py"):
                manifest = harness.prepare_run(output)
            self.assertEqual(manifest["status"], "PREPARED")
            self.assertFalse(guard.exists())
            self.assertFalse((output / "cases").exists())

    def test_second_execute_guard_rejects_before_running(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            first = base / "first"
            second = base / "second"
            guard = base / "guard.json"
            harness.prepare_run(first)
            harness.claim_guard(guard)
            second_manifest = harness.prepare_run(second)
            with self.assertRaises(RuntimeError):
                harness.claim_guard(guard)
            self.assertEqual(second_manifest["status"], "PREPARED")
            self.assertFalse((second / "cases").exists())

    def _make_terminal_run(self, directory: Path, complete: bool) -> tuple[dict, list[dict]]:
        projection = self.projection
        records = []
        by_key = self.by_key
        for item in projection["schedule"]:
            arm = directory / "cases" / item["case_id"] / item["supplier_id"]
            arm.mkdir(parents=True, exist_ok=True)
            (arm / "supplier_message.txt").write_bytes(by_key[(item["case_id"], item["supplier_id"])] ["supplier_message_bytes"])
            harness.atomic_write_json(arm / "call_started.json", {"ordinal": item["ordinal"]})
            if complete or item["ordinal"] != 32:
                harness.atomic_write_json(arm / "response.json", {"ordinal": item["ordinal"], "raw": "synthetic test-only"})
            harness.atomic_write_json(arm / "call_finished.json", {"ordinal": item["ordinal"], "case_id": item["case_id"], "supplier_id": item["supplier_id"], "terminal_disposition": "RESPONSE_CAPTURED"})
            records.append({"ordinal": item["ordinal"], "case_id": item["case_id"], "supplier_id": item["supplier_id"]})
        manifest = {"status": "RUNNING", "raw_explicit_v3_responses_sealed_before_evaluation": False}
        return manifest, records

    def test_successful_32_arm_seal_hashes_every_arm(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            manifest, records = self._make_terminal_run(run, complete=True)
            self.assertTrue(harness.seal_raw(run, manifest, records, "TERMINAL_COMPLETE"))
            sealed = json.loads((run / "raw_response_manifest.json").read_text())
            self.assertEqual(sealed["terminal_arm_artifact_count"], 32)
            self.assertTrue(json.loads((run / "execution_manifest.json").read_text())["raw_explicit_v3_responses_sealed_before_evaluation"])
            for item in sealed["terminal_arm_artifacts"]:
                for relative, digest in item["artifact_hashes"].items():
                    self.assertEqual(harness.sha_file(run / relative), digest)

    def test_failed_seal_never_sets_true(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            manifest, records = self._make_terminal_run(run, complete=False)
            with self.assertRaises(RuntimeError):
                harness.seal_raw(run, manifest, records, "TERMINAL_COMPLETE")
            self.assertFalse(manifest["raw_explicit_v3_responses_sealed_before_evaluation"])
            self.assertFalse((run / "raw_response_manifest.json").exists())

    def test_transport_failure_is_not_response_capture(self) -> None:
        result = {"content_bytes": b"request error", "terminal_disposition": "LOCAL_TRANSPORT_FAILURE", "metadata": {"transport_valid": False, "prohibited_actions_not_observed": False}}
        with tempfile.TemporaryDirectory() as directory:
            arm = Path(directory)
            item = {"ordinal": 1, "case_id": "case", "capability_family": "triage-routing", "interface_id": "iface", "supplier_id": "local_teacher", "supplier_message_sha256": "x"}
            terminal = harness._write_terminal_arm(arm, item, result, "now", 1.0)
            self.assertEqual(terminal["terminal_disposition"], "LOCAL_TRANSPORT_FAILURE")
            self.assertTrue((arm / "infrastructure_failure.json").exists())
            self.assertFalse((arm / "response.json").exists())

    def test_post_call_recording_failure_has_fallback_terminal_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            output = base / "run"
            guard = base / "guard.json"
            result = {"content_bytes": b"synthetic raw supplier output", "terminal_disposition": "RESPONSE_CAPTURED", "metadata": {"transport_valid": True, "prohibited_actions_not_observed": True}}
            with mock.patch.object(harness, "_write_terminal_arm", side_effect=RuntimeError("injected recorder failure")):
                exit_code = harness.execute(output, guard_state=guard, capture_overrides={"local_teacher": lambda _message: result})
            self.assertEqual(exit_code, 1)
            call_started = list(output.glob("cases/*/*/call_started.json"))
            fallback = list(output.glob("cases/*/*/terminal_recording_failure.json"))
            self.assertEqual(len(call_started), 1)
            self.assertEqual(len(fallback), 1)
            raw = json.loads((output / "raw_response_manifest.json").read_text(encoding="utf-8"))
            execution = json.loads((output / "execution_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(execution["status"], "TERMINAL_INCOMPLETE")
            self.assertEqual(execution["supplier_calls"], 1)
            self.assertFalse(execution["raw_explicit_v3_responses_sealed_before_evaluation"])
            self.assertFalse(raw["raw_explicit_v3_responses_sealed_before_evaluation"])
            self.assertEqual(len(raw["records"]), 1)
            self.assertEqual(raw["records"][0]["terminal_disposition"], "TERMINAL_RECORDING_FAILURE")

    def test_acquisition_module_has_no_scoring_import(self) -> None:
        source = Path(harness.__file__).read_text(encoding="utf-8")
        self.assertNotIn("import evaluate_explicit_interface_direct_unit_calibration_v3", source)
        self.assertNotIn("from evaluate_explicit_interface_direct_unit_calibration_v3", source)
        self.assertNotIn("read_json(artifact_dir / EVALUATOR_NAME)", source)

    def test_all_16_synthetic_positive_controls_validate_with_v3_evaluator(self) -> None:
        cases = json.loads((harness.DOCS / harness.EVALUATOR_NAME).read_text(encoding="utf-8"))["cases"]
        self.assertEqual(len(cases), 16)
        for case in cases:
            expected = case["expected"]
            if case["family"] == "triage-routing":
                response = {"route": expected["route_exact"], "rationale": " ".join(expected["rationale_required_facts"]), "review_status": expected["review_status_exact"]}
            else:
                response = {"known_facts": expected["known_facts_required"], "uncertainty": expected["uncertainty_required"], "review_status": expected["review_status_exact"], "next_step": " and ".join(expected["next_step_required"])}
            result = evaluator.evaluate(json.dumps(response), case, {"transport_valid": True, "prohibited_actions_not_observed": True})
            self.assertTrue(result["DIRECT_CAPABILITY_VALID"], case["case_id"])
            transport_failure = evaluator.evaluate(json.dumps(response), case, {"transport_valid": False, "prohibited_actions_not_observed": True})
            self.assertFalse(transport_failure["DIRECT_CAPABILITY_VALID"], case["case_id"])


if __name__ == "__main__":
    unittest.main()
