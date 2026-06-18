import json
import os
import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, os.fspath(Path(__file__).resolve().parents[1]))

import chatgpt_export_ingest
import chatgpt_export_run_plan
import context_chunker
import signal_extraction_packets


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "examples" / "chatgpt_export_fixture"


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def build_packet_fixture(temp_root: Path) -> tuple[Path, Path, Path]:
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
    return sources_dir / "manifests" / "conversations.jsonl", chunks_dir, packets_dir / "packets.jsonl"


class ChatGPTExportRunPlanTests(unittest.TestCase):
    def test_planner_reads_synthetic_outputs_and_writes_expected_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            ingest_manifest, chunk_root, packets_path = build_packet_fixture(temp_root)
            out_dir = temp_root / "run_plan"

            summary = chatgpt_export_run_plan.write_run_plan(
                ingest_manifest=ingest_manifest,
                chunk_root=chunk_root,
                packets_path=packets_path,
                out_dir=out_dir,
                batch_size=1,
            )

            self.assertEqual(1, summary["conversation_count"])
            self.assertEqual(2, summary["chunk_count"])
            self.assertEqual(2, summary["packet_count"])
            self.assertEqual(1, summary["batch_size"])
            self.assertEqual(2, summary["batch_count"])
            self.assertEqual({"pass_A": 1, "pass_B_offset": 1}, summary["chunk_pass_counts"])
            self.assertEqual({"conv_synthetic_001": 2}, summary["conversation_packet_counts"])
            self.assertEqual(
                [{"conversation_id": "conv_synthetic_001", "packet_count": 2}],
                summary["largest_conversations_by_packets"],
            )
            self.assertTrue((out_dir / "run_plan_summary.json").is_file())
            self.assertTrue((out_dir / "batch_manifest.jsonl").is_file())
            self.assertTrue((out_dir / "batch_commands.sh").is_file())
            self.assertTrue((out_dir / "README.md").is_file())

    def test_batch_ranges_handle_packet_count_not_evenly_divisible_by_batch_size(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            ingest_manifest, chunk_root, packets_path = build_packet_fixture(temp_root)
            rows = read_jsonl(packets_path)
            expanded_rows = []
            for index in range(5):
                row = dict(rows[index % len(rows)])
                row["packet_id"] = f"packet-synthetic-plan-{index + 1:03d}"
                expanded_rows.append(row)
            write_jsonl(packets_path, expanded_rows)

            chatgpt_export_run_plan.write_run_plan(
                ingest_manifest=ingest_manifest,
                chunk_root=chunk_root,
                packets_path=packets_path,
                out_dir=temp_root / "run_plan",
                batch_size=2,
            )

            batches = read_jsonl(temp_root / "run_plan" / "batch_manifest.jsonl")
            self.assertEqual(
                [
                    {"batch_id": "batch-0001", "start_index": 1, "end_index": 2, "packet_count": 2, "status": "planned"},
                    {"batch_id": "batch-0002", "start_index": 3, "end_index": 4, "packet_count": 2, "status": "planned"},
                    {"batch_id": "batch-0003", "start_index": 5, "end_index": 5, "packet_count": 1, "status": "planned"},
                ],
                batches,
            )

    def test_batch_size_validation_rejects_zero_and_negative_values(self):
        with self.assertRaisesRegex(ValueError, "batch-size"):
            chatgpt_export_run_plan.write_run_plan(
                ingest_manifest=Path("missing.jsonl"),
                chunk_root=Path("missing_chunks"),
                packets_path=Path("missing_packets.jsonl"),
                out_dir=Path("missing_plan"),
                batch_size=0,
            )

        with self.assertRaisesRegex(ValueError, "batch-size"):
            chatgpt_export_run_plan.build_batch_rows(packet_count=3, batch_size=-1)

    def test_batch_manifest_rows_are_deterministic(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            ingest_manifest, chunk_root, packets_path = build_packet_fixture(temp_root)

            chatgpt_export_run_plan.write_run_plan(
                ingest_manifest=ingest_manifest,
                chunk_root=chunk_root,
                packets_path=packets_path,
                out_dir=temp_root / "first_plan",
                batch_size=1,
            )
            chatgpt_export_run_plan.write_run_plan(
                ingest_manifest=ingest_manifest,
                chunk_root=chunk_root,
                packets_path=packets_path,
                out_dir=temp_root / "second_plan",
                batch_size=1,
            )

            self.assertEqual(
                (temp_root / "first_plan" / "batch_manifest.jsonl").read_text(encoding="utf-8"),
                (temp_root / "second_plan" / "batch_manifest.jsonl").read_text(encoding="utf-8"),
            )

    def test_generated_shell_script_is_reviewable_and_contains_runner_controls(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            ingest_manifest, chunk_root, packets_path = build_packet_fixture(temp_root)
            out_dir = temp_root / "run_plan"

            chatgpt_export_run_plan.write_run_plan(
                ingest_manifest=ingest_manifest,
                chunk_root=chunk_root,
                packets_path=packets_path,
                out_dir=out_dir,
                batch_size=1,
                base_url="http://127.0.0.1:8081/v1",
                model="synthetic-local-model",
                retries=1,
                retry_delay_seconds=2,
            )

            script = (out_dir / "batch_commands.sh").read_text(encoding="utf-8")
            self.assertIn('# export ZTH_SIGNAL_EXTRACT_BASE_URL="http://127.0.0.1:8081/v1"', script)
            self.assertIn('# export ZTH_SIGNAL_EXTRACT_MODEL="synthetic-local-model"', script)
            self.assertIn("python3 local_harness/run_signal_extraction_packets.py", script)
            self.assertIn("--start-index 1", script)
            self.assertIn("--end-index 1", script)
            self.assertIn("--resume", script)
            self.assertIn("--validate", script)
            self.assertIn("--retries 1", script)
            self.assertIn("--retry-delay-seconds 2", script)
            nonblank_lines = [line for line in script.splitlines() if line.strip()]
            self.assertTrue(all(line.startswith("#") for line in nonblank_lines))

    def test_readme_is_written_with_safety_and_followup_guidance(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            ingest_manifest, chunk_root, packets_path = build_packet_fixture(temp_root)
            out_dir = temp_root / "run_plan"

            chatgpt_export_run_plan.write_run_plan(
                ingest_manifest=ingest_manifest,
                chunk_root=chunk_root,
                packets_path=packets_path,
                out_dir=out_dir,
                batch_size=1,
            )

            readme = (out_dir / "README.md").read_text(encoding="utf-8")
            self.assertIn("does not execute model calls", readme)
            self.assertIn("Run One Batch Manually", readme)
            self.assertIn("Resume", readme)
            self.assertIn("signal_dedupe.py", readme)
            self.assertIn("review material only", readme)

    def test_fixture_contains_only_tiny_synthetic_data(self):
        fixture_text = (FIXTURE_DIR / "conversations.json").read_text(encoding="utf-8")
        raw_fixture_text = (FIXTURE_DIR / "raw_signals.jsonl").read_text(encoding="utf-8")

        self.assertIn("Synthetic Export Fixture", fixture_text)
        self.assertIn("synthetic", raw_fixture_text.lower())
        self.assertNotIn("@", fixture_text + raw_fixture_text)
        self.assertLess(len(fixture_text), 6000)
        self.assertLess(len(raw_fixture_text), 5000)


if __name__ == "__main__":
    unittest.main()
