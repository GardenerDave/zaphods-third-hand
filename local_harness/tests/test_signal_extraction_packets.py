import json
import os
import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, os.fspath(Path(__file__).resolve().parents[1]))

import chatgpt_export_ingest
import context_chunker
import signal_extraction_packets


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "examples" / "chatgpt_export_fixture"


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_chunk_fixture(temp_root: Path) -> Path:
    sources_dir = temp_root / "sources"
    chunks_dir = temp_root / "chunks"
    chatgpt_export_ingest.ingest_export(FIXTURE_DIR, sources_dir)
    context_chunker.plan_manifest(
        sources_dir / "manifests" / "conversations.jsonl",
        chunks_dir,
        profile="small-model-offset",
    )
    return chunks_dir


class SignalExtractionPacketsTests(unittest.TestCase):
    def test_reads_chunk_plans_and_creates_packet_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            chunk_root = build_chunk_fixture(temp_root)
            out_dir = temp_root / "extraction_packets"

            summary = signal_extraction_packets.generate_packets(chunk_root, out_dir)

            self.assertEqual(2, summary["packet_count"])
            self.assertTrue((out_dir / "packets.jsonl").is_file())
            self.assertTrue((out_dir / "packet_summary.json").is_file())
            self.assertTrue((out_dir / "packet_files").is_dir())
            self.assertEqual(2, len(list((out_dir / "packet_files").glob("packet_*.md"))))

    def test_packet_files_include_required_task_instructions_and_source_chunk(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            chunk_root = build_chunk_fixture(temp_root)
            out_dir = temp_root / "extraction_packets"

            signal_extraction_packets.generate_packets(chunk_root, out_dir)

            rows = read_jsonl(out_dir / "packets.jsonl")
            packet_text = Path(str(rows[0]["packet_path"])).read_text(encoding="utf-8")
            self.assertIn("# Raw Signal Extraction Packet", packet_text)
            self.assertIn("Expected Output: raw_signals_jsonl", packet_text)
            self.assertIn("Extract durable raw signals from the source chunk below.", packet_text)
            self.assertIn("Return JSONL only. One JSON object per line. No prose, no markdown fences.", packet_text)
            self.assertIn("- raw_signal_id", packet_text)
            self.assertIn("- current_state", packet_text)
            self.assertIn("- historical", packet_text)
            self.assertIn("- unknown", packet_text)
            self.assertIn("- This is review material, not canonical memory.", packet_text)
            self.assertIn("## Source Chunk", packet_text)
            self.assertIn("# Distiller Chunk", packet_text)
            self.assertIn("Please summarize the synthetic project note.", packet_text)

    def test_packet_files_include_max_signal_instructions_when_configured(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            chunk_root = build_chunk_fixture(temp_root)
            out_dir = temp_root / "extraction_packets"

            summary = signal_extraction_packets.generate_packets(chunk_root, out_dir, max_signals_per_packet=2)

            rows = read_jsonl(out_dir / "packets.jsonl")
            packet_text = Path(str(rows[0]["packet_path"])).read_text(encoding="utf-8")
            self.assertIn("Max Signals Per Packet: 2", packet_text)
            self.assertIn("Return JSONL only. One JSON object per line. No prose, no markdown fences.", packet_text)
            self.assertIn("Return at most 2 raw signal objects.", packet_text)
            self.assertIn("Prefer highest-confidence, durable, user-specific signals.", packet_text)
            self.assertIn("If more than 2 candidates exist, omit weaker or redundant candidates.", packet_text)
            self.assertIn("Stop after the 2nd object.", packet_text)
            self.assertIn("If no good signal exists, return nothing.", packet_text)
            self.assertEqual(2, rows[0]["max_signals_per_packet"])
            self.assertEqual(2, summary["max_signals_per_packet"])
            summary_payload = json.loads((out_dir / "packet_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(2, summary_payload["max_signals_per_packet"])

    def test_packet_files_do_not_include_cap_instructions_when_unset(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            chunk_root = build_chunk_fixture(temp_root)
            out_dir = temp_root / "extraction_packets"

            summary = signal_extraction_packets.generate_packets(chunk_root, out_dir)

            rows = read_jsonl(out_dir / "packets.jsonl")
            packet_text = Path(str(rows[0]["packet_path"])).read_text(encoding="utf-8")
            self.assertNotIn("Max Signals Per Packet:", packet_text)
            self.assertNotIn("Return at most", packet_text)
            self.assertNotIn("Stop after the", packet_text)
            self.assertNotIn("max_signals_per_packet", rows[0])
            self.assertIsNone(summary["max_signals_per_packet"])

    def test_packet_ids_are_deterministic_across_two_runs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            chunk_root = build_chunk_fixture(temp_root)
            first_out = temp_root / "first_packets"
            second_out = temp_root / "second_packets"

            signal_extraction_packets.generate_packets(chunk_root, first_out)
            signal_extraction_packets.generate_packets(chunk_root, second_out)

            first_rows = read_jsonl(first_out / "packets.jsonl")
            second_rows = read_jsonl(second_out / "packets.jsonl")
            self.assertEqual(
                [(row["packet_id"], row["conversation_id"], row["chunk_id"], row["chunk_pass"]) for row in first_rows],
                [(row["packet_id"], row["conversation_id"], row["chunk_id"], row["chunk_pass"]) for row in second_rows],
            )

    def test_pass_a_and_offset_chunks_both_produce_packets(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            chunk_root = build_chunk_fixture(temp_root)
            out_dir = temp_root / "extraction_packets"

            signal_extraction_packets.generate_packets(chunk_root, out_dir)

            rows = read_jsonl(out_dir / "packets.jsonl")
            self.assertEqual({"pass_A", "pass_B_offset"}, {row["chunk_pass"] for row in rows})

    def test_packet_manifest_paths_point_to_existing_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            chunk_root = build_chunk_fixture(temp_root)
            out_dir = temp_root / "extraction_packets"

            signal_extraction_packets.generate_packets(chunk_root, out_dir)

            for row in read_jsonl(out_dir / "packets.jsonl"):
                self.assertEqual("raw_signals_jsonl", row["expected_output"])
                self.assertTrue(Path(str(row["chunk_path"])).is_file())
                self.assertTrue(Path(str(row["packet_path"])).is_file())
                self.assertGreater(Path(str(row["packet_path"])).stat().st_size, 0)

    def test_main_cli_writes_packets(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            chunk_root = build_chunk_fixture(temp_root)
            out_dir = temp_root / "extraction_packets"

            exit_code = signal_extraction_packets.main(
                [
                    "--chunk-root",
                    os.fspath(chunk_root),
                    "--out-dir",
                    os.fspath(out_dir),
                ]
            )

            self.assertEqual(0, exit_code)
            self.assertTrue((out_dir / "packets.jsonl").is_file())

    def test_main_cli_accepts_max_signals_per_packet(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            chunk_root = build_chunk_fixture(temp_root)
            out_dir = temp_root / "extraction_packets"

            exit_code = signal_extraction_packets.main(
                [
                    "--chunk-root",
                    os.fspath(chunk_root),
                    "--out-dir",
                    os.fspath(out_dir),
                    "--max-signals-per-packet",
                    "2",
                ]
            )

            self.assertEqual(0, exit_code)
            summary = json.loads((out_dir / "packet_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(2, summary["max_signals_per_packet"])

    def test_rejects_invalid_max_signals_per_packet(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            chunk_root = build_chunk_fixture(temp_root)

            with self.assertRaisesRegex(ValueError, "max-signals-per-packet"):
                signal_extraction_packets.generate_packets(
                    chunk_root,
                    temp_root / "extraction_packets",
                    max_signals_per_packet=0,
                )

    def test_fixture_contains_only_tiny_synthetic_data(self):
        fixture_text = (FIXTURE_DIR / "conversations.json").read_text(encoding="utf-8")

        self.assertIn("Synthetic Export Fixture", fixture_text)
        self.assertIn("synthetic", fixture_text.lower())
        self.assertNotIn("@", fixture_text)
        self.assertLess(len(fixture_text), 6000)


if __name__ == "__main__":
    unittest.main()
