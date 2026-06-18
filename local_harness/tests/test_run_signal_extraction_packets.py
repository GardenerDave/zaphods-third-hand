import json
import os
import tempfile
import unittest
import io
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
import urllib.error

import sys

sys.path.insert(0, os.fspath(Path(__file__).resolve().parents[1]))

import chatgpt_export_ingest
import context_chunker
import run_signal_extraction_packets
import signal_extraction_packets


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "examples" / "chatgpt_export_fixture"


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_jsonl_from_text(text: str) -> list[dict[str, object]]:
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def build_packet_fixture(temp_root: Path) -> Path:
    sources_dir = temp_root / "sources"
    chunks_dir = temp_root / "chunks"
    packets_dir = temp_root / "extraction_packets"
    chatgpt_export_ingest.ingest_export(FIXTURE_DIR, sources_dir)
    context_chunker.plan_manifest(
        sources_dir / "manifests" / "conversations.jsonl",
        chunks_dir,
        profile="small-model-offset",
    )
    signal_extraction_packets.generate_packets(chunks_dir, packets_dir)
    return packets_dir / "packets.jsonl"


def packet_raw_output_path(out_dir: Path, packet_id: object) -> Path:
    return out_dir / "raw_outputs" / f"{run_signal_extraction_packets.safe_filename(packet_id)}.jsonl"


class FakeHTTPResponse:
    def __init__(self, payload: dict[str, object]):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def fake_openai_payload(content_suffix: str = "001") -> dict[str, object]:
    content = json.dumps(
        {
            "raw_signal_id": f"raw-from-model-{content_suffix}",
            "claim": "Synthetic model extracted claim.",
            "signal_type": "current_state",
            "status_hint": "current",
            "confidence": "high",
            "conversation_id": "synthetic-conv-model",
            "chunk_id": "chunk-synthetic-model",
            "chunk_pass": "pass_A",
            "turn_start": 1,
            "turn_end": 2,
            "source_path": "synthetic",
            "evidence_note": "Synthetic fake endpoint evidence.",
        },
        sort_keys=True,
    )
    return {
        "model": "fake-signal-model",
        "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": content}}],
    }


def pretty_qwen_trial_json() -> str:
    return json.dumps(
        {
            "raw_signal_id": "signal-001",
            "claim": "The synthetic note says to keep generated files reviewable.",
            "signal_type": "command_or_setting",
            "status_hint": "current",
            "confidence": "high",
            "conversation_id": "conv_synthetic_001",
            "chunk_id": "chunk-ea052fa37a4c124c",
            "chunk_pass": "pass_A",
            "turn_start": 2,
            "turn_end": 2,
            "source_path": "/tmp/zth_chatgpt_export_test/sources/normalized/conv_synthetic_001_synthetic-export-fixture.md",
            "evidence_note": "Direct statement from the assistant in Turn 0002.",
        },
        indent=2,
    )


def pretty_synthetic_signal(raw_signal_id: str, claim: str) -> str:
    return json.dumps(
        {
            "raw_signal_id": raw_signal_id,
            "claim": claim,
            "signal_type": "current_state",
            "status_hint": "current",
            "confidence": "high",
            "conversation_id": "conv_synthetic_001",
            "chunk_id": "chunk-synthetic-001",
            "chunk_pass": "pass_A",
            "turn_start": 1,
            "turn_end": 2,
            "source_path": "synthetic",
            "evidence_note": "Synthetic normalization test evidence.",
        },
        indent=2,
    )


class RunSignalExtractionPacketsTests(unittest.TestCase):
    def test_normalize_valid_jsonl_preserves_jsonl_shape(self):
        raw = (
            json.dumps({"raw_signal_id": "raw-001", "claim": "Synthetic one."}) + "\n"
            + json.dumps({"raw_signal_id": "raw-002", "claim": "Synthetic two."}) + "\n"
        )

        result = run_signal_extraction_packets.normalize_model_output(raw)

        self.assertEqual("ok", result.status)
        self.assertEqual("jsonl", result.strategy)
        rows = read_jsonl_from_text(result.jsonl_text)
        self.assertEqual(["raw-001", "raw-002"], [row["raw_signal_id"] for row in rows])

    def test_normalize_pretty_json_object_to_single_jsonl_row(self):
        result = run_signal_extraction_packets.normalize_model_output(pretty_qwen_trial_json())

        self.assertEqual("ok", result.status)
        self.assertEqual("json_object", result.strategy)
        rows = read_jsonl_from_text(result.jsonl_text)
        self.assertEqual(1, len(rows))
        self.assertEqual("signal-001", rows[0]["raw_signal_id"])
        self.assertEqual("The synthetic note says to keep generated files reviewable.", rows[0]["claim"])

    def test_normalize_json_array_to_multiple_jsonl_rows(self):
        raw = json.dumps(
            [
                {"raw_signal_id": "raw-array-001", "claim": "Synthetic array one."},
                {"raw_signal_id": "raw-array-002", "claim": "Synthetic array two."},
            ],
            indent=2,
        )

        result = run_signal_extraction_packets.normalize_model_output(raw)

        self.assertEqual("ok", result.status)
        self.assertEqual("json_array", result.strategy)
        rows = read_jsonl_from_text(result.jsonl_text)
        self.assertEqual(["raw-array-001", "raw-array-002"], [row["raw_signal_id"] for row in rows])

    def test_normalize_multiple_pretty_json_objects_separated_by_blank_lines(self):
        raw = (
            pretty_synthetic_signal("raw-multi-001", "Synthetic multi object one.")
            + "\n\n"
            + pretty_synthetic_signal("raw-multi-002", "Synthetic multi object two.")
        )

        result = run_signal_extraction_packets.normalize_model_output(raw)

        self.assertEqual("ok", result.status)
        self.assertEqual("multi_json_objects", result.strategy)
        rows = read_jsonl_from_text(result.jsonl_text)
        self.assertEqual(["raw-multi-001", "raw-multi-002"], [row["raw_signal_id"] for row in rows])
        self.assertEqual(["Synthetic multi object one.", "Synthetic multi object two."], [row["claim"] for row in rows])

    def test_normalize_multiple_json_objects_separated_by_comma(self):
        raw = (
            pretty_synthetic_signal("raw-comma-001", "Synthetic comma object one.")
            + ",\n"
            + pretty_synthetic_signal("raw-comma-002", "Synthetic comma object two.")
        )

        result = run_signal_extraction_packets.normalize_model_output(raw)

        self.assertEqual("ok", result.status)
        self.assertEqual("multi_json_objects", result.strategy)
        rows = read_jsonl_from_text(result.jsonl_text)
        self.assertEqual(["raw-comma-001", "raw-comma-002"], [row["raw_signal_id"] for row in rows])

    def test_normalize_rejects_prose_between_json_objects(self):
        raw = (
            pretty_synthetic_signal("raw-prose-001", "Synthetic before prose.")
            + "\nThis prose should not be repaired.\n"
            + pretty_synthetic_signal("raw-prose-002", "Synthetic after prose.")
        )

        result = run_signal_extraction_packets.normalize_model_output(raw)

        self.assertEqual("error", result.status)
        self.assertEqual("failed", result.strategy)
        self.assertIn("Unexpected text between JSON regions", result.error)

    def test_normalize_rejects_incomplete_trailing_json_region(self):
        raw = pretty_synthetic_signal("raw-complete-001", "Synthetic complete object.") + "\n{\n  \"raw_signal_id\": \"raw-truncated\""

        result = run_signal_extraction_packets.normalize_model_output(raw)

        self.assertEqual("error", result.status)
        self.assertEqual("failed", result.strategy)
        self.assertIn("Incomplete trailing JSON region", result.error)

    def test_normalize_multiple_json_arrays_of_objects(self):
        raw = (
            json.dumps([{"raw_signal_id": "raw-array-a", "claim": "Synthetic array A."}], indent=2)
            + "\n,\n"
            + json.dumps([{"raw_signal_id": "raw-array-b", "claim": "Synthetic array B."}], indent=2)
        )

        result = run_signal_extraction_packets.normalize_model_output(raw)

        self.assertEqual("ok", result.status)
        self.assertEqual("multi_json_arrays", result.strategy)
        rows = read_jsonl_from_text(result.jsonl_text)
        self.assertEqual(["raw-array-a", "raw-array-b"], [row["raw_signal_id"] for row in rows])

        bad = run_signal_extraction_packets.normalize_model_output('[{"raw_signal_id": "raw-array-ok"}]\n[1]')
        self.assertEqual("error", bad.status)
        self.assertIn("non-object", bad.error)

    def test_normalize_markdown_fenced_json_object(self):
        raw = "```json\n" + pretty_qwen_trial_json() + "\n```"

        result = run_signal_extraction_packets.normalize_model_output(raw)

        self.assertEqual("ok", result.status)
        self.assertEqual("markdown_fenced_json", result.strategy)
        self.assertEqual("signal-001", read_jsonl_from_text(result.jsonl_text)[0]["raw_signal_id"])

    def test_normalize_markdown_fenced_jsonl_with_two_objects(self):
        raw = (
            "```jsonl\n"
            + json.dumps({"raw_signal_id": "raw-fenced-jsonl-001", "claim": "Synthetic fenced JSONL one."})
            + "\n"
            + json.dumps({"raw_signal_id": "raw-fenced-jsonl-002", "claim": "Synthetic fenced JSONL two."})
            + "\n```"
        )

        result = run_signal_extraction_packets.normalize_model_output(raw)

        self.assertEqual("ok", result.status)
        self.assertEqual("markdown_fenced_jsonl", result.strategy)
        rows = read_jsonl_from_text(result.jsonl_text)
        self.assertEqual(["raw-fenced-jsonl-001", "raw-fenced-jsonl-002"], [row["raw_signal_id"] for row in rows])

    def test_normalize_markdown_fenced_adjacent_json_objects(self):
        raw = (
            "```json\n"
            + pretty_synthetic_signal("raw-fenced-multi-001", "Synthetic fenced multi one.")
            + "\n"
            + pretty_synthetic_signal("raw-fenced-multi-002", "Synthetic fenced multi two.")
            + "\n```"
        )

        result = run_signal_extraction_packets.normalize_model_output(raw)

        self.assertEqual("ok", result.status)
        self.assertEqual("markdown_fenced_multi_json_objects", result.strategy)
        rows = read_jsonl_from_text(result.jsonl_text)
        self.assertEqual(["raw-fenced-multi-001", "raw-fenced-multi-002"], [row["raw_signal_id"] for row in rows])

    def test_normalize_markdown_fenced_json_array(self):
        raw = "```json\n" + json.dumps(
            [
                {"raw_signal_id": "raw-fenced-array-001", "claim": "Synthetic fenced array one."},
                {"raw_signal_id": "raw-fenced-array-002", "claim": "Synthetic fenced array two."},
            ],
            indent=2,
        ) + "\n```"

        result = run_signal_extraction_packets.normalize_model_output(raw)

        self.assertEqual("ok", result.status)
        self.assertEqual("markdown_fenced_json", result.strategy)
        rows = read_jsonl_from_text(result.jsonl_text)
        self.assertEqual(["raw-fenced-array-001", "raw-fenced-array-002"], [row["raw_signal_id"] for row in rows])

    def test_normalize_markdown_fenced_adjacent_json_arrays(self):
        raw = (
            "```json\n"
            + json.dumps([{"raw_signal_id": "raw-fenced-array-a", "claim": "Synthetic fenced array A."}], indent=2)
            + "\n,\n"
            + json.dumps([{"raw_signal_id": "raw-fenced-array-b", "claim": "Synthetic fenced array B."}], indent=2)
            + "\n```"
        )

        result = run_signal_extraction_packets.normalize_model_output(raw)

        self.assertEqual("ok", result.status)
        self.assertEqual("markdown_fenced_multi_json_arrays", result.strategy)
        rows = read_jsonl_from_text(result.jsonl_text)
        self.assertEqual(["raw-fenced-array-a", "raw-fenced-array-b"], [row["raw_signal_id"] for row in rows])

    def test_normalize_markdown_fenced_malformed_json_is_rejected(self):
        raw = '```json\n{"raw_signal_id": "raw-fenced-bad"\n```'

        result = run_signal_extraction_packets.normalize_model_output(raw)

        self.assertEqual("error", result.status)
        self.assertEqual("failed", result.strategy)
        self.assertIn("Incomplete trailing JSON region", result.error)

    def test_normalize_markdown_fenced_prose_is_rejected(self):
        fenced_prose = "```jsonl\nnot json\n```"
        outside_prose = (
            "Here is JSONL:\n```jsonl\n"
            + json.dumps({"raw_signal_id": "raw-outside-prose", "claim": "Synthetic outside prose."})
            + "\n```"
        )

        fenced_result = run_signal_extraction_packets.normalize_model_output(fenced_prose)
        outside_result = run_signal_extraction_packets.normalize_model_output(outside_prose)

        self.assertEqual("error", fenced_result.status)
        self.assertEqual("failed", fenced_result.strategy)
        self.assertIn("Markdown fenced content", fenced_result.error)
        self.assertEqual("error", outside_result.status)
        self.assertEqual("failed", outside_result.strategy)
        self.assertIn("outside the fence", outside_result.error)

    def test_normalize_leading_trailing_prose_with_one_clear_object(self):
        raw = "Here is the JSON:\n" + pretty_qwen_trial_json() + "\nDone."

        result = run_signal_extraction_packets.normalize_model_output(raw)

        self.assertEqual("ok", result.status)
        self.assertEqual("extracted_json", result.strategy)
        self.assertEqual("signal-001", read_jsonl_from_text(result.jsonl_text)[0]["raw_signal_id"])

    def test_normalize_rejects_unextractable_and_ambiguous_outputs(self):
        bad = run_signal_extraction_packets.normalize_model_output("no json here")
        ambiguous = run_signal_extraction_packets.normalize_model_output('first {"a": 1} second {"b": 2}')
        scalar = run_signal_extraction_packets.normalize_model_output('"just a string"')
        mixed_array = run_signal_extraction_packets.normalize_model_output('[{"a": 1}, 2]')

        self.assertEqual("error", bad.status)
        self.assertEqual("failed", bad.strategy)
        self.assertEqual("error", ambiguous.status)
        self.assertIn("Multiple JSON", ambiguous.error)
        self.assertEqual("error", scalar.status)
        self.assertIn("not an object", scalar.error)
        self.assertEqual("error", mixed_array.status)
        self.assertIn("non-object", mixed_array.error)

    def test_reads_packet_manifest_generated_by_synthetic_flow(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            packets_path = build_packet_fixture(Path(temp_dir))

            packets = run_signal_extraction_packets.read_jsonl(packets_path)

            self.assertEqual(2, len(packets))
            self.assertEqual({"pass_A", "pass_B_offset"}, {packet["chunk_pass"] for packet in packets})

    def test_dry_run_writes_manifest_and_summary_without_endpoint_calls(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            packets_path = build_packet_fixture(temp_root)
            out_dir = temp_root / "model_raw_signals"

            with patch.object(run_signal_extraction_packets, "call_openai_chat", side_effect=AssertionError("called")):
                summary = run_signal_extraction_packets.run_packets(
                    packets_path=packets_path,
                    out_dir=out_dir,
                    base_url="",
                    api_key="",
                    model="",
                    limit=1,
                    dry_run=True,
                )

            self.assertEqual(1, summary["selected_packet_count"])
            self.assertTrue(summary["dry_run"])
            self.assertFalse((out_dir / "raw_outputs").exists())
            manifest = read_jsonl(out_dir / "run_manifest.jsonl")
            self.assertEqual(1, len(manifest))
            self.assertEqual("dry_run", manifest[0]["status"])
            self.assertEqual("", manifest[0]["raw_output_path"])
            self.assertEqual("", manifest[0]["normalized_output_path"])
            self.assertEqual("not_run", manifest[0]["normalization_status"])
            self.assertEqual("", manifest[0]["normalization_strategy"])
            self.assertEqual(0, manifest[0]["attempt_count"])
            self.assertFalse(manifest[0]["resume_skipped"])
            self.assertEqual(1, manifest[0]["selected_index"])
            self.assertEqual(0, summary["attempted_count"])
            self.assertEqual(0, summary["retry_count"])

    def test_limit_one_selects_one_packet(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            packets_path = build_packet_fixture(temp_root)

            summary = run_signal_extraction_packets.run_packets(
                packets_path=packets_path,
                out_dir=temp_root / "out",
                base_url="",
                api_key="",
                model="",
                limit=1,
                dry_run=True,
            )

            self.assertEqual(1, summary["selected_packet_count"])

    def test_packet_id_selects_requested_packet(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            packets_path = build_packet_fixture(temp_root)
            packets = read_jsonl(packets_path)
            requested_packet = packets[1]

            run_signal_extraction_packets.run_packets(
                packets_path=packets_path,
                out_dir=temp_root / "out",
                base_url="",
                api_key="",
                model="",
                packet_id=str(requested_packet["packet_id"]),
                dry_run=True,
            )

            manifest = read_jsonl(temp_root / "out" / "run_manifest.jsonl")
            self.assertEqual(1, len(manifest))
            self.assertEqual(requested_packet["packet_id"], manifest[0]["packet_id"])

    def test_start_end_range_selects_expected_packets_and_composes_with_limit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            packets_path = build_packet_fixture(temp_root)
            packets = read_jsonl(packets_path)

            summary = run_signal_extraction_packets.run_packets(
                packets_path=packets_path,
                out_dir=temp_root / "range_only",
                base_url="",
                api_key="",
                model="",
                start_index=2,
                end_index=2,
                dry_run=True,
            )

            manifest = read_jsonl(temp_root / "range_only" / "run_manifest.jsonl")
            self.assertEqual(1, summary["selected_packet_count"])
            self.assertEqual(packets[1]["packet_id"], manifest[0]["packet_id"])
            self.assertEqual(2, manifest[0]["selected_index"])
            self.assertEqual(2, summary["start_index"])
            self.assertEqual(2, summary["end_index"])

            run_signal_extraction_packets.run_packets(
                packets_path=packets_path,
                out_dir=temp_root / "range_limit_first",
                base_url="",
                api_key="",
                model="",
                start_index=1,
                end_index=2,
                limit=1,
                dry_run=True,
            )
            first_manifest = read_jsonl(temp_root / "range_limit_first" / "run_manifest.jsonl")
            self.assertEqual(packets[0]["packet_id"], first_manifest[0]["packet_id"])

            run_signal_extraction_packets.run_packets(
                packets_path=packets_path,
                out_dir=temp_root / "range_limit_second",
                base_url="",
                api_key="",
                model="",
                start_index=2,
                limit=1,
                dry_run=True,
            )
            second_manifest = read_jsonl(temp_root / "range_limit_second" / "run_manifest.jsonl")
            self.assertEqual(packets[1]["packet_id"], second_manifest[0]["packet_id"])

    def test_invalid_ranges_fail_clearly(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            packets_path = build_packet_fixture(temp_root)

            with self.assertRaisesRegex(ValueError, "start-index"):
                run_signal_extraction_packets.run_packets(
                    packets_path=packets_path,
                    out_dir=temp_root / "bad_range",
                    base_url="",
                    api_key="",
                    model="",
                    start_index=2,
                    end_index=1,
                    dry_run=True,
                )

            with self.assertRaisesRegex(ValueError, "1 or greater"):
                run_signal_extraction_packets.run_packets(
                    packets_path=packets_path,
                    out_dir=temp_root / "bad_start",
                    base_url="",
                    api_key="",
                    model="",
                    start_index=0,
                    dry_run=True,
                )

    def test_fake_openai_compatible_response_writes_raw_output_and_ok_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            packets_path = build_packet_fixture(temp_root)
            out_dir = temp_root / "model_raw_signals"
            requests = []

            def fake_urlopen(request, timeout=120):
                requests.append(request)
                return FakeHTTPResponse(fake_openai_payload())

            with patch.object(run_signal_extraction_packets.urllib.request, "urlopen", side_effect=fake_urlopen):
                summary = run_signal_extraction_packets.run_packets(
                    packets_path=packets_path,
                    out_dir=out_dir,
                    base_url="http://127.0.0.1:9999/v1",
                    api_key="not-needed-for-local",
                    model="fake-signal-model",
                    limit=1,
                )

            self.assertEqual(1, summary["ok_count"])
            manifest = read_jsonl(out_dir / "run_manifest.jsonl")
            self.assertEqual("ok", manifest[0]["status"])
            self.assertEqual("not_run", manifest[0]["normalization_status"])
            self.assertEqual(1, manifest[0]["attempt_count"])
            self.assertFalse(manifest[0]["resume_skipped"])
            self.assertEqual(1, manifest[0]["selected_index"])
            self.assertTrue(Path(str(manifest[0]["raw_output_path"])).is_file())
            raw_text = Path(str(manifest[0]["raw_output_path"])).read_text(encoding="utf-8")
            self.assertIn("Synthetic model extracted claim.", raw_text)
            self.assertEqual("http://127.0.0.1:9999/v1/chat/completions", requests[0].full_url)
            payload = json.loads(requests[0].data.decode("utf-8"))
            self.assertEqual("fake-signal-model", payload["model"])
            self.assertEqual("You return raw signal JSONL only. No prose. No markdown fences.", payload["messages"][0]["content"])

    def test_endpoint_error_is_captured_without_stopping_whole_run(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            packets_path = build_packet_fixture(temp_root)
            out_dir = temp_root / "model_raw_signals"
            requests = []

            def fake_urlopen(request, timeout=120):
                requests.append(request)
                if len(requests) == 2:
                    raise urllib.error.HTTPError(
                        request.full_url,
                        500,
                        "synthetic failure",
                        hdrs=None,
                        fp=io.BytesIO(b'{"error":"synthetic server failure"}'),
                    )
                return FakeHTTPResponse(fake_openai_payload())

            with patch.object(run_signal_extraction_packets.urllib.request, "urlopen", side_effect=fake_urlopen):
                summary = run_signal_extraction_packets.run_packets(
                    packets_path=packets_path,
                    out_dir=out_dir,
                    base_url="http://127.0.0.1:9999/v1",
                    api_key="not-needed-for-local",
                    model="fake-signal-model",
                )

            self.assertEqual(2, summary["selected_packet_count"])
            self.assertEqual(1, summary["ok_count"])
            self.assertEqual(1, summary["error_count"])
            manifest = read_jsonl(out_dir / "run_manifest.jsonl")
            self.assertEqual(["ok", "error"], [row["status"] for row in manifest])
            self.assertIn("HTTP 500", manifest[1]["error"])
            self.assertEqual([1, 1], [row["attempt_count"] for row in manifest])

    def test_missing_packet_file_is_captured_as_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            packets_path = build_packet_fixture(temp_root)
            packets = read_jsonl(packets_path)
            packets[0]["packet_path"] = os.fspath(temp_root / "missing_packet.md")
            broken_packets = temp_root / "broken_packets.jsonl"
            broken_packets.write_text(json.dumps(packets[0], sort_keys=True) + "\n", encoding="utf-8")

            summary = run_signal_extraction_packets.run_packets(
                packets_path=broken_packets,
                out_dir=temp_root / "out",
                base_url="http://127.0.0.1:1/v1",
                api_key="",
                model="fake-model",
            )

            manifest = read_jsonl(temp_root / "out" / "run_manifest.jsonl")
            self.assertEqual(1, summary["error_count"])
            self.assertEqual("error", manifest[0]["status"])
            self.assertIn("packet_read_error", manifest[0]["error"])
            self.assertEqual(0, manifest[0]["attempt_count"])

    def test_resume_skips_completed_successful_packets_without_endpoint_call(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            packets_path = build_packet_fixture(temp_root)
            out_dir = temp_root / "model_raw_signals"

            with patch.object(
                run_signal_extraction_packets.urllib.request,
                "urlopen",
                return_value=FakeHTTPResponse(fake_openai_payload()),
            ):
                run_signal_extraction_packets.run_packets(
                    packets_path=packets_path,
                    out_dir=out_dir,
                    base_url="http://127.0.0.1:9999/v1",
                    api_key="not-needed-for-local",
                    model="fake-signal-model",
                    limit=1,
                )

            with patch.object(run_signal_extraction_packets, "call_openai_chat", side_effect=AssertionError("called")):
                summary = run_signal_extraction_packets.run_packets(
                    packets_path=packets_path,
                    out_dir=out_dir,
                    base_url="http://127.0.0.1:9999/v1",
                    api_key="not-needed-for-local",
                    model="fake-signal-model",
                    limit=1,
                    resume=True,
                )

            manifest = read_jsonl(out_dir / "run_manifest.jsonl")
            self.assertEqual(1, summary["resume_skipped_count"])
            self.assertEqual(0, summary["attempted_count"])
            self.assertEqual("ok", manifest[0]["status"])
            self.assertTrue(manifest[0]["resume_skipped"])
            self.assertEqual(0, manifest[0]["attempt_count"])

    def test_resume_does_not_skip_failed_packets(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            packets_path = build_packet_fixture(temp_root)
            out_dir = temp_root / "model_raw_signals"

            with patch.object(run_signal_extraction_packets, "call_openai_chat", return_value=("", "synthetic failure")):
                run_signal_extraction_packets.run_packets(
                    packets_path=packets_path,
                    out_dir=out_dir,
                    base_url="http://127.0.0.1:9999/v1",
                    api_key="not-needed-for-local",
                    model="fake-signal-model",
                    limit=1,
                )

            call_count = 0

            def fake_call(**kwargs):
                nonlocal call_count
                call_count += 1
                return (json.dumps({"raw_signal_id": "raw-retried", "claim": "Synthetic retried claim."}), "")

            with patch.object(run_signal_extraction_packets, "call_openai_chat", side_effect=fake_call):
                summary = run_signal_extraction_packets.run_packets(
                    packets_path=packets_path,
                    out_dir=out_dir,
                    base_url="http://127.0.0.1:9999/v1",
                    api_key="not-needed-for-local",
                    model="fake-signal-model",
                    limit=1,
                    resume=True,
                )

            manifest = read_jsonl(out_dir / "run_manifest.jsonl")
            self.assertEqual(1, call_count)
            self.assertEqual(0, summary["resume_skipped_count"])
            self.assertEqual(1, summary["attempted_count"])
            self.assertEqual("ok", manifest[0]["status"])
            self.assertFalse(manifest[0]["resume_skipped"])
            self.assertEqual(1, manifest[0]["attempt_count"])

    def test_resume_rebuilds_normalized_and_validated_outputs_from_existing_raw_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            packets_path = build_packet_fixture(temp_root)
            out_dir = temp_root / "model_raw_signals"
            pretty_output = pretty_qwen_trial_json()

            with patch.object(
                run_signal_extraction_packets.urllib.request,
                "urlopen",
                return_value=FakeHTTPResponse(
                    {
                        "model": "fake-signal-model",
                        "choices": [
                            {"finish_reason": "stop", "message": {"role": "assistant", "content": pretty_output}}
                        ],
                    }
                ),
            ):
                run_signal_extraction_packets.run_packets(
                    packets_path=packets_path,
                    out_dir=out_dir,
                    base_url="http://127.0.0.1:9999/v1",
                    api_key="not-needed-for-local",
                    model="fake-signal-model",
                    limit=1,
                    validate=True,
                )

            previous_manifest = read_jsonl(out_dir / "run_manifest.jsonl")
            Path(str(previous_manifest[0]["normalized_output_path"])).unlink()
            (out_dir / "combined_raw_signals.jsonl").unlink()

            with patch.object(run_signal_extraction_packets, "call_openai_chat", side_effect=AssertionError("called")):
                summary = run_signal_extraction_packets.run_packets(
                    packets_path=packets_path,
                    out_dir=out_dir,
                    base_url="http://127.0.0.1:9999/v1",
                    api_key="not-needed-for-local",
                    model="fake-signal-model",
                    limit=1,
                    resume=True,
                    validate=True,
                )

            manifest = read_jsonl(out_dir / "run_manifest.jsonl")
            self.assertEqual(1, summary["resume_skipped_count"])
            self.assertEqual(1, summary["normalized_count"])
            self.assertEqual("ok", manifest[0]["normalization_status"])
            self.assertTrue(Path(str(manifest[0]["normalized_output_path"])).is_file())
            self.assertTrue((out_dir / "combined_raw_signals.jsonl").is_file())
            validation_summary = json.loads((out_dir / "validated" / "validation_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(1, validation_summary["valid_count"])

    def test_resume_uses_output_files_after_single_packet_repair_manifest_overwrite(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            packets_path = build_packet_fixture(temp_root)
            out_dir = temp_root / "model_raw_signals"
            packets = read_jsonl(packets_path)

            with patch.object(
                run_signal_extraction_packets.urllib.request,
                "urlopen",
                return_value=FakeHTTPResponse(
                    {
                        "model": "fake-signal-model",
                        "choices": [
                            {
                                "finish_reason": "stop",
                                "message": {
                                    "role": "assistant",
                                    "content": pretty_synthetic_signal(
                                        "raw-repair-001",
                                        "Synthetic packet one completed before repair.",
                                    ),
                                },
                            }
                        ],
                    }
                ),
            ):
                run_signal_extraction_packets.run_packets(
                    packets_path=packets_path,
                    out_dir=out_dir,
                    base_url="http://127.0.0.1:9999/v1",
                    api_key="not-needed-for-local",
                    model="fake-signal-model",
                    start_index=1,
                    end_index=1,
                    validate=True,
                )

            with patch.object(
                run_signal_extraction_packets.urllib.request,
                "urlopen",
                return_value=FakeHTTPResponse(
                    {
                        "model": "fake-signal-model",
                        "choices": [
                            {
                                "finish_reason": "stop",
                                "message": {
                                    "role": "assistant",
                                    "content": pretty_synthetic_signal(
                                        "raw-repair-002",
                                        "Synthetic packet two completed during repair.",
                                    ),
                                },
                            }
                        ],
                    }
                ),
            ):
                run_signal_extraction_packets.run_packets(
                    packets_path=packets_path,
                    out_dir=out_dir,
                    base_url="http://127.0.0.1:9999/v1",
                    api_key="not-needed-for-local",
                    model="fake-signal-model",
                    start_index=2,
                    end_index=2,
                    resume=True,
                    validate=True,
                )

            repair_manifest = read_jsonl(out_dir / "run_manifest.jsonl")
            self.assertEqual([packets[1]["packet_id"]], [row["packet_id"] for row in repair_manifest])

            with patch.object(run_signal_extraction_packets, "call_openai_chat", side_effect=AssertionError("called")):
                summary = run_signal_extraction_packets.run_packets(
                    packets_path=packets_path,
                    out_dir=out_dir,
                    base_url="http://127.0.0.1:9999/v1",
                    api_key="not-needed-for-local",
                    model="fake-signal-model",
                    start_index=1,
                    end_index=2,
                    resume=True,
                    validate=True,
                )

            manifest = read_jsonl(out_dir / "run_manifest.jsonl")
            self.assertEqual(2, summary["resume_skipped_count"])
            self.assertEqual(0, summary["attempted_count"])
            self.assertEqual(2, summary["normalized_count"])
            self.assertEqual([packets[0]["packet_id"], packets[1]["packet_id"]], [row["packet_id"] for row in manifest])
            self.assertEqual([True, True], [row["resume_skipped"] for row in manifest])
            self.assertEqual(["normalized_output", "normalized_output"], [row["resume_source"] for row in manifest])
            validation_summary = json.loads((out_dir / "validated" / "validation_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(2, validation_summary["valid_count"])

    def test_resume_reruns_existing_raw_output_when_normalization_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            packets_path = build_packet_fixture(temp_root)
            packets = read_jsonl(packets_path)
            out_dir = temp_root / "model_raw_signals"
            raw_dir = out_dir / "raw_outputs"
            raw_dir.mkdir(parents=True)
            packet_raw_output_path(out_dir, packets[0]["packet_id"]).write_text("not json", encoding="utf-8")

            call_count = 0

            def fake_call(**kwargs):
                nonlocal call_count
                call_count += 1
                return (
                    pretty_synthetic_signal("raw-rerun-after-bad-raw", "Synthetic rerun after bad raw output."),
                    "",
                )

            with patch.object(run_signal_extraction_packets, "call_openai_chat", side_effect=fake_call):
                summary = run_signal_extraction_packets.run_packets(
                    packets_path=packets_path,
                    out_dir=out_dir,
                    base_url="http://127.0.0.1:9999/v1",
                    api_key="not-needed-for-local",
                    model="fake-signal-model",
                    limit=1,
                    resume=True,
                    validate=True,
                )

            manifest = read_jsonl(out_dir / "run_manifest.jsonl")
            self.assertEqual(1, call_count)
            self.assertEqual(0, summary["resume_skipped_count"])
            self.assertEqual(1, summary["attempted_count"])
            self.assertEqual("ok", manifest[0]["status"])
            self.assertFalse(manifest[0]["resume_skipped"])
            self.assertIn("raw-rerun-after-bad-raw", packet_raw_output_path(out_dir, packets[0]["packet_id"]).read_text(encoding="utf-8"))

    def test_resume_reruns_empty_existing_raw_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            packets_path = build_packet_fixture(temp_root)
            packets = read_jsonl(packets_path)
            out_dir = temp_root / "model_raw_signals"
            raw_dir = out_dir / "raw_outputs"
            raw_dir.mkdir(parents=True)
            packet_raw_output_path(out_dir, packets[0]["packet_id"]).write_text("", encoding="utf-8")

            call_count = 0

            def fake_call(**kwargs):
                nonlocal call_count
                call_count += 1
                return (
                    pretty_synthetic_signal("raw-rerun-empty", "Synthetic rerun after empty raw output."),
                    "",
                )

            with patch.object(run_signal_extraction_packets, "call_openai_chat", side_effect=fake_call):
                summary = run_signal_extraction_packets.run_packets(
                    packets_path=packets_path,
                    out_dir=out_dir,
                    base_url="http://127.0.0.1:9999/v1",
                    api_key="not-needed-for-local",
                    model="fake-signal-model",
                    limit=1,
                    resume=True,
                    validate=True,
                )

            self.assertEqual(1, call_count)
            self.assertEqual(0, summary["resume_skipped_count"])
            self.assertIn("raw-rerun-empty", packet_raw_output_path(out_dir, packets[0]["packet_id"]).read_text(encoding="utf-8"))

    def test_resume_regenerates_missing_normalized_output_from_raw_without_model_call(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            packets_path = build_packet_fixture(temp_root)
            packets = read_jsonl(packets_path)
            out_dir = temp_root / "model_raw_signals"
            raw_dir = out_dir / "raw_outputs"
            raw_dir.mkdir(parents=True)
            packet_raw_output_path(out_dir, packets[0]["packet_id"]).write_text(
                pretty_synthetic_signal("raw-existing-no-normalized", "Synthetic existing raw output."),
                encoding="utf-8",
            )

            with patch.object(run_signal_extraction_packets, "call_openai_chat", side_effect=AssertionError("called")):
                summary = run_signal_extraction_packets.run_packets(
                    packets_path=packets_path,
                    out_dir=out_dir,
                    base_url="http://127.0.0.1:9999/v1",
                    api_key="not-needed-for-local",
                    model="fake-signal-model",
                    limit=1,
                    resume=True,
                    validate=True,
                )

            manifest = read_jsonl(out_dir / "run_manifest.jsonl")
            self.assertEqual(1, summary["resume_skipped_count"])
            self.assertEqual(0, summary["attempted_count"])
            self.assertEqual(1, summary["normalized_count"])
            self.assertEqual("raw_output", manifest[0]["resume_source"])
            self.assertTrue(Path(str(manifest[0]["normalized_output_path"])).is_file())
            normalized_rows = read_jsonl(Path(str(manifest[0]["normalized_output_path"])))
            self.assertEqual("raw-existing-no-normalized", normalized_rows[0]["raw_signal_id"])

    def test_resume_regenerates_missing_normalized_output_from_fenced_jsonl_raw(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            packets_path = build_packet_fixture(temp_root)
            packets = read_jsonl(packets_path)
            out_dir = temp_root / "model_raw_signals"
            raw_dir = out_dir / "raw_outputs"
            raw_dir.mkdir(parents=True)
            raw_text = (
                "```jsonl\n"
                + json.dumps({"raw_signal_id": "raw-fenced-resume-001", "claim": "Synthetic fenced resume one."})
                + "\n"
                + json.dumps({"raw_signal_id": "raw-fenced-resume-002", "claim": "Synthetic fenced resume two."})
                + "\n```"
            )
            packet_raw_output_path(out_dir, packets[0]["packet_id"]).write_text(raw_text, encoding="utf-8")

            with patch.object(run_signal_extraction_packets, "call_openai_chat", side_effect=AssertionError("called")):
                summary = run_signal_extraction_packets.run_packets(
                    packets_path=packets_path,
                    out_dir=out_dir,
                    base_url="http://127.0.0.1:9999/v1",
                    api_key="not-needed-for-local",
                    model="fake-signal-model",
                    limit=1,
                    resume=True,
                    validate=True,
                )

            manifest = read_jsonl(out_dir / "run_manifest.jsonl")
            self.assertEqual(1, summary["resume_skipped_count"])
            self.assertEqual(0, summary["attempted_count"])
            self.assertEqual(1, summary["normalized_count"])
            self.assertEqual("ok", manifest[0]["normalization_status"])
            self.assertEqual("markdown_fenced_jsonl", manifest[0]["normalization_strategy"])
            normalized_rows = read_jsonl(Path(str(manifest[0]["normalized_output_path"])))
            self.assertEqual(["raw-fenced-resume-001", "raw-fenced-resume-002"], [row["raw_signal_id"] for row in normalized_rows])
            validation_summary = json.loads((out_dir / "validated" / "validation_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(2, validation_summary["valid_count"])

    def test_partial_manifest_does_not_cause_completed_raw_outputs_to_be_ignored(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            packets_path = build_packet_fixture(temp_root)
            packets = read_jsonl(packets_path)
            out_dir = temp_root / "model_raw_signals"
            raw_dir = out_dir / "raw_outputs"
            raw_dir.mkdir(parents=True)
            for index, packet in enumerate(packets[:2], start=1):
                packet_raw_output_path(out_dir, packet["packet_id"]).write_text(
                    pretty_synthetic_signal(f"raw-partial-{index:03d}", f"Synthetic partial manifest packet {index}."),
                    encoding="utf-8",
                )
            (out_dir / "run_manifest.jsonl").write_text(
                json.dumps(
                    {
                        "packet_id": packets[0]["packet_id"],
                        "status": "error",
                        "raw_output_path": str(packet_raw_output_path(out_dir, packets[0]["packet_id"])),
                        "error": "synthetic interrupted manifest row",
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            with patch.object(run_signal_extraction_packets, "call_openai_chat", side_effect=AssertionError("called")):
                summary = run_signal_extraction_packets.run_packets(
                    packets_path=packets_path,
                    out_dir=out_dir,
                    base_url="http://127.0.0.1:9999/v1",
                    api_key="not-needed-for-local",
                    model="fake-signal-model",
                    start_index=1,
                    end_index=2,
                    resume=True,
                    validate=True,
                )

            manifest = read_jsonl(out_dir / "run_manifest.jsonl")
            self.assertEqual(2, summary["resume_skipped_count"])
            self.assertEqual(0, summary["attempted_count"])
            self.assertEqual([True, True], [row["resume_skipped"] for row in manifest])
            self.assertEqual(["raw_output", "raw_output"], [row["resume_source"] for row in manifest])

    def test_retry_succeeds_after_mocked_transient_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            packets_path = build_packet_fixture(temp_root)
            out_dir = temp_root / "model_raw_signals"

            responses = [
                ("", "transient endpoint failure"),
                (json.dumps({"raw_signal_id": "raw-after-retry", "claim": "Synthetic retry success."}), ""),
            ]

            with patch.object(run_signal_extraction_packets, "call_openai_chat", side_effect=responses):
                summary = run_signal_extraction_packets.run_packets(
                    packets_path=packets_path,
                    out_dir=out_dir,
                    base_url="http://127.0.0.1:9999/v1",
                    api_key="not-needed-for-local",
                    model="fake-signal-model",
                    limit=1,
                    retries=1,
                )

            manifest = read_jsonl(out_dir / "run_manifest.jsonl")
            self.assertEqual(1, summary["ok_count"])
            self.assertEqual(1, summary["retry_count"])
            self.assertEqual(2, manifest[0]["attempt_count"])
            self.assertEqual("ok", manifest[0]["status"])

    def test_retry_failure_records_final_error_and_attempt_count(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            packets_path = build_packet_fixture(temp_root)
            out_dir = temp_root / "model_raw_signals"

            with patch.object(run_signal_extraction_packets, "call_openai_chat", return_value=("", "final synthetic failure")):
                summary = run_signal_extraction_packets.run_packets(
                    packets_path=packets_path,
                    out_dir=out_dir,
                    base_url="http://127.0.0.1:9999/v1",
                    api_key="not-needed-for-local",
                    model="fake-signal-model",
                    limit=1,
                    retries=2,
                )

            manifest = read_jsonl(out_dir / "run_manifest.jsonl")
            self.assertEqual(1, summary["error_count"])
            self.assertEqual(2, summary["retry_count"])
            self.assertEqual(3, manifest[0]["attempt_count"])
            self.assertIn("final synthetic failure", manifest[0]["error"])

    def test_progress_output_includes_running_ok_error_and_skip_lines(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            packets_path = build_packet_fixture(temp_root)
            out_dir = temp_root / "model_raw_signals"
            responses = [
                (json.dumps({"raw_signal_id": "raw-progress-ok", "claim": "Synthetic progress OK."}), ""),
                ("", "synthetic progress error"),
            ]

            output = io.StringIO()
            with patch.object(run_signal_extraction_packets, "call_openai_chat", side_effect=responses):
                with redirect_stdout(output):
                    run_signal_extraction_packets.run_packets(
                        packets_path=packets_path,
                        out_dir=out_dir,
                        base_url="http://127.0.0.1:9999/v1",
                        api_key="not-needed-for-local",
                        model="fake-signal-model",
                    )

            text = output.getvalue()
            self.assertIn("Running packet 1/2:", text)
            self.assertIn("OK packet 1/2:", text)
            self.assertIn("Running packet 2/2:", text)
            self.assertIn("ERROR packet 2/2:", text)

            first_packet_id = read_jsonl(packets_path)[0]["packet_id"]
            skip_output = io.StringIO()
            with patch.object(run_signal_extraction_packets, "call_openai_chat", side_effect=AssertionError("called")):
                with redirect_stdout(skip_output):
                    run_signal_extraction_packets.run_packets(
                        packets_path=packets_path,
                        out_dir=out_dir,
                        base_url="http://127.0.0.1:9999/v1",
                        api_key="not-needed-for-local",
                        model="fake-signal-model",
                        packet_id=str(first_packet_id),
                        resume=True,
                    )

            self.assertIn("SKIP packet 1/1:", skip_output.getvalue())

    def test_validate_normalizes_pretty_json_object_and_preserves_raw_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            packets_path = build_packet_fixture(temp_root)
            out_dir = temp_root / "model_raw_signals"
            pretty_output = pretty_qwen_trial_json()

            with patch.object(
                run_signal_extraction_packets.urllib.request,
                "urlopen",
                return_value=FakeHTTPResponse(
                    {
                        "model": "fake-signal-model",
                        "choices": [
                            {"finish_reason": "stop", "message": {"role": "assistant", "content": pretty_output}}
                        ],
                    }
                ),
            ):
                summary = run_signal_extraction_packets.run_packets(
                    packets_path=packets_path,
                    out_dir=out_dir,
                    base_url="http://127.0.0.1:9999/v1",
                    api_key="not-needed-for-local",
                    model="fake-signal-model",
                    limit=1,
                    validate=True,
                )

            self.assertTrue(summary["validated"])
            self.assertEqual(1, summary["normalized_count"])
            self.assertEqual(0, summary["normalization_error_count"])
            self.assertTrue((out_dir / "combined_raw_signals.jsonl").is_file())
            self.assertTrue((out_dir / "normalization_summary.json").is_file())
            self.assertTrue((out_dir / "validated" / "valid_raw_signals.jsonl").is_file())
            self.assertFalse((out_dir / "deduped_signals.jsonl").exists())
            manifest = read_jsonl(out_dir / "run_manifest.jsonl")
            self.assertEqual("ok", manifest[0]["normalization_status"])
            self.assertEqual("json_object", manifest[0]["normalization_strategy"])
            self.assertTrue(Path(str(manifest[0]["normalized_output_path"])).is_file())
            self.assertEqual(pretty_output, Path(str(manifest[0]["raw_output_path"])).read_text(encoding="utf-8"))
            normalized_rows = read_jsonl(Path(str(manifest[0]["normalized_output_path"])))
            self.assertEqual(1, len(normalized_rows))
            self.assertEqual("signal-001", normalized_rows[0]["raw_signal_id"])
            self.assertEqual(
                (out_dir / "combined_raw_signals.jsonl").read_text(encoding="utf-8"),
                Path(str(manifest[0]["normalized_output_path"])).read_text(encoding="utf-8"),
            )
            validation_summary = json.loads((out_dir / "validated" / "validation_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(1, validation_summary["valid_count"])
            self.assertEqual(0, validation_summary["invalid_count"])
            normalization_summary = json.loads((out_dir / "normalization_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(1, normalization_summary["selected_packet_count"])
            self.assertEqual(1, normalization_summary["ok_raw_output_count"])
            self.assertEqual(1, normalization_summary["normalized_count"])
            self.assertEqual(0, normalization_summary["normalization_error_count"])
            self.assertEqual(1, normalization_summary["strategies"]["json_object"])

    def test_validate_normalizes_multiple_pretty_json_objects_and_reports_strategy(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            packets_path = build_packet_fixture(temp_root)
            out_dir = temp_root / "model_raw_signals"
            raw_output = (
                pretty_synthetic_signal("raw-run-multi-001", "Synthetic runner multi object one.")
                + "\n\n"
                + pretty_synthetic_signal("raw-run-multi-002", "Synthetic runner multi object two.")
            )

            with patch.object(
                run_signal_extraction_packets.urllib.request,
                "urlopen",
                return_value=FakeHTTPResponse(
                    {
                        "model": "fake-signal-model",
                        "choices": [
                            {"finish_reason": "stop", "message": {"role": "assistant", "content": raw_output}}
                        ],
                    }
                ),
            ):
                summary = run_signal_extraction_packets.run_packets(
                    packets_path=packets_path,
                    out_dir=out_dir,
                    base_url="http://127.0.0.1:9999/v1",
                    api_key="not-needed-for-local",
                    model="fake-signal-model",
                    limit=1,
                    validate=True,
                )

            self.assertTrue(summary["validated"])
            self.assertEqual(1, summary["normalized_count"])
            self.assertEqual(0, summary["normalization_error_count"])
            manifest = read_jsonl(out_dir / "run_manifest.jsonl")
            self.assertEqual("ok", manifest[0]["normalization_status"])
            self.assertEqual("multi_json_objects", manifest[0]["normalization_strategy"])
            self.assertEqual(raw_output, Path(str(manifest[0]["raw_output_path"])).read_text(encoding="utf-8"))
            normalized_rows = read_jsonl(Path(str(manifest[0]["normalized_output_path"])))
            self.assertEqual(["raw-run-multi-001", "raw-run-multi-002"], [row["raw_signal_id"] for row in normalized_rows])
            normalization_summary = json.loads((out_dir / "normalization_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(1, normalization_summary["strategies"]["multi_json_objects"])
            validation_summary = json.loads((out_dir / "validated" / "validation_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(2, validation_summary["valid_count"])
            self.assertEqual(0, validation_summary["invalid_count"])
            self.assertFalse((out_dir / "deduped_signals.jsonl").exists())

    def test_validate_records_normalization_failure_without_dedupe(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            packets_path = build_packet_fixture(temp_root)
            out_dir = temp_root / "model_raw_signals"

            with patch.object(
                run_signal_extraction_packets.urllib.request,
                "urlopen",
                return_value=FakeHTTPResponse(
                    {
                        "model": "fake-signal-model",
                        "choices": [
                            {"finish_reason": "stop", "message": {"role": "assistant", "content": "not json"}}
                        ],
                    }
                ),
            ):
                summary = run_signal_extraction_packets.run_packets(
                    packets_path=packets_path,
                    out_dir=out_dir,
                    base_url="http://127.0.0.1:9999/v1",
                    api_key="not-needed-for-local",
                    model="fake-signal-model",
                    limit=1,
                    validate=True,
                )

            self.assertEqual(1, summary["ok_count"])
            self.assertEqual(0, summary["normalized_count"])
            self.assertEqual(1, summary["normalization_error_count"])
            manifest = read_jsonl(out_dir / "run_manifest.jsonl")
            self.assertEqual("error", manifest[0]["normalization_status"])
            self.assertEqual("failed", manifest[0]["normalization_strategy"])
            self.assertIn("Could not parse", manifest[0]["normalization_error"])
            self.assertEqual("", manifest[0]["normalized_output_path"])
            validation_summary = json.loads((out_dir / "validated" / "validation_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(0, validation_summary["valid_count"])
            self.assertEqual(0, validation_summary["invalid_count"])
            self.assertFalse((out_dir / "deduped_signals.jsonl").exists())

    def test_output_order_is_deterministic(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            packets_path = build_packet_fixture(temp_root)
            packet_ids = [row["packet_id"] for row in read_jsonl(packets_path)]

            run_signal_extraction_packets.run_packets(
                packets_path=packets_path,
                out_dir=temp_root / "out",
                base_url="",
                api_key="",
                model="",
                dry_run=True,
            )

            manifest_ids = [row["packet_id"] for row in read_jsonl(temp_root / "out" / "run_manifest.jsonl")]
            self.assertEqual(packet_ids, manifest_ids)

    def test_main_cli_dry_run_writes_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            packets_path = build_packet_fixture(temp_root)
            out_dir = temp_root / "model_raw_signals"

            exit_code = run_signal_extraction_packets.main(
                [
                    "--packets",
                    os.fspath(packets_path),
                    "--out-dir",
                    os.fspath(out_dir),
                    "--limit",
                    "1",
                    "--dry-run",
                ]
            )

            self.assertEqual(0, exit_code)
            summary = json.loads((out_dir / "run_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(1, summary["selected_packet_count"])
            self.assertTrue(summary["dry_run"])
            self.assertEqual(0, summary["normalized_count"])
            self.assertEqual(0, summary["normalization_error_count"])

    def test_fixture_contains_only_tiny_synthetic_data(self):
        fixture_text = (FIXTURE_DIR / "conversations.json").read_text(encoding="utf-8")
        raw_fixture_text = (FIXTURE_DIR / "raw_signals.jsonl").read_text(encoding="utf-8")

        self.assertIn("Synthetic Export Fixture", fixture_text)
        self.assertIn("synthetic", raw_fixture_text.lower())
        self.assertNotIn("@", fixture_text + raw_fixture_text)
        self.assertNotIn("Dell PowerEdge", raw_fixture_text)
        self.assertLess(len(fixture_text), 6000)
        self.assertLess(len(raw_fixture_text), 5000)


if __name__ == "__main__":
    unittest.main()
