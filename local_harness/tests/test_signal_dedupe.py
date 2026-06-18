import json
import os
import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, os.fspath(Path(__file__).resolve().parents[1]))

import signal_dedupe


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "examples" / "chatgpt_export_fixture"
RAW_SIGNALS_FIXTURE = FIXTURE_DIR / "raw_signals.jsonl"


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def run_fixture(temp_root: Path) -> Path:
    out_dir = temp_root / "signals"
    signal_dedupe.process_signals(RAW_SIGNALS_FIXTURE, out_dir)
    return out_dir


def server_alpha_row(rows: list[dict[str, object]]) -> dict[str, object]:
    for row in rows:
        if row["claim"] == "The synthetic main inference host is Server Alpha.":
            return row
    raise AssertionError("missing Server Alpha deduped row")


class SignalDedupeTests(unittest.TestCase):
    def test_cli_reads_synthetic_fixture_and_writes_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir) / "signals"

            exit_code = signal_dedupe.main(
                [
                    "--raw-signals",
                    os.fspath(RAW_SIGNALS_FIXTURE),
                    "--out-dir",
                    os.fspath(out_dir),
                ]
            )

            self.assertEqual(0, exit_code)
            for filename in (
                "deduped_signals.jsonl",
                "duplicate_links.jsonl",
                "conflict_candidates.jsonl",
                "dedupe_summary.json",
            ):
                self.assertTrue((out_dir / filename).is_file(), filename)

    def test_exact_and_near_duplicate_claims_collapse(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = run_fixture(Path(temp_dir))

            deduped = read_jsonl(out_dir / "deduped_signals.jsonl")
            duplicate_links = read_jsonl(out_dir / "duplicate_links.jsonl")
            summary = json.loads((out_dir / "dedupe_summary.json").read_text(encoding="utf-8"))
            alpha = server_alpha_row(deduped)

            self.assertEqual(4, len(deduped))
            self.assertEqual(4, summary["deduped_signal_count"])
            self.assertEqual(
                ["raw-001", "raw-002", "raw-003"],
                alpha["supporting_raw_signal_ids"],
            )
            self.assertEqual(2, len(duplicate_links))
            self.assertEqual("normalized_claim_match", duplicate_links[0]["reason"])
            self.assertEqual("high_token_overlap", duplicate_links[1]["reason"])
            self.assertEqual("raw-001", duplicate_links[0]["duplicate_of_raw_signal_id"])
            self.assertEqual("raw-001", duplicate_links[1]["duplicate_of_raw_signal_id"])

    def test_distinct_claims_remain_distinct(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = run_fixture(Path(temp_dir))

            deduped = read_jsonl(out_dir / "deduped_signals.jsonl")
            claims = {row["claim"] for row in deduped}

            self.assertIn("Should the synthetic onboarding note mention the chunk profile?", claims)
            self.assertIn("Server Beta was the synthetic primary host.", claims)
            self.assertIn("Server Alpha is now the synthetic primary host.", claims)

    def test_provenance_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = run_fixture(Path(temp_dir))

            alpha = server_alpha_row(read_jsonl(out_dir / "deduped_signals.jsonl"))

            self.assertEqual(
                ["synthetic-conv-001", "synthetic-conv-002"],
                alpha["source_conversation_ids"],
            )
            self.assertEqual(
                ["chunk-synthetic-001", "chunk-synthetic-002", "chunk-synthetic-003"],
                alpha["source_chunk_ids"],
            )
            self.assertEqual("high", alpha["confidence"])

    def test_conflict_candidates_are_written_for_historical_current_topic_groups(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = run_fixture(Path(temp_dir))

            conflicts = read_jsonl(out_dir / "conflict_candidates.jsonl")
            summary = json.loads((out_dir / "dedupe_summary.json").read_text(encoding="utf-8"))

            self.assertEqual(1, len(conflicts))
            self.assertEqual(1, summary["conflict_candidate_count"])
            conflict = conflicts[0]
            self.assertEqual("synthetic primary host", conflict["topic_key"])
            self.assertEqual("version_or_conflict_candidate", conflict["classification"])
            self.assertEqual(["raw-005", "raw-006"], [claim["raw_signal_id"] for claim in conflict["claims"]])
            self.assertEqual(["historical", "current"], [claim["status_hint"] for claim in conflict["claims"]])

    def test_stable_ids_are_deterministic_across_two_runs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            first_out = temp_root / "first"
            second_out = temp_root / "second"

            signal_dedupe.process_signals(RAW_SIGNALS_FIXTURE, first_out)
            signal_dedupe.process_signals(RAW_SIGNALS_FIXTURE, second_out)

            first_deduped = read_jsonl(first_out / "deduped_signals.jsonl")
            second_deduped = read_jsonl(second_out / "deduped_signals.jsonl")
            first_conflicts = read_jsonl(first_out / "conflict_candidates.jsonl")
            second_conflicts = read_jsonl(second_out / "conflict_candidates.jsonl")

            self.assertEqual(
                [row["canonical_signal_id"] for row in first_deduped],
                [row["canonical_signal_id"] for row in second_deduped],
            )
            self.assertEqual(
                [row["conflict_id"] for row in first_conflicts],
                [row["conflict_id"] for row in second_conflicts],
            )

    def test_missing_optional_fields_do_not_crash_and_empty_claims_are_counted(self):
        rows = [
            {"raw_signal_id": "raw-minimal", "claim": "Synthetic minimal claim."},
            {"raw_signal_id": "raw-empty", "claim": "   "},
            {"claim": "Synthetic claim without an explicit id."},
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            raw_path = temp_root / "raw_signals.jsonl"
            raw_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            out_dir = temp_root / "signals"

            summary = signal_dedupe.process_signals(raw_path, out_dir)

            deduped = read_jsonl(out_dir / "deduped_signals.jsonl")
            self.assertEqual(3, summary["raw_signal_count"])
            self.assertEqual(2, summary["deduped_signal_count"])
            self.assertEqual(1, summary["skipped_empty_claim_count"])
            self.assertEqual(["raw-empty"], summary["skipped_empty_raw_signal_ids"])
            self.assertEqual("unknown", deduped[0]["signal_type"])
            self.assertEqual("unknown", deduped[0]["status"])
            self.assertIn("raw-missing-0003", deduped[1]["supporting_raw_signal_ids"])

    def test_output_files_are_valid_jsonl_and_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = run_fixture(Path(temp_dir))

            for filename in ("deduped_signals.jsonl", "duplicate_links.jsonl", "conflict_candidates.jsonl"):
                rows = read_jsonl(out_dir / filename)
                self.assertGreaterEqual(len(rows), 1)
                for row in rows:
                    self.assertIsInstance(row, dict)

            summary = json.loads((out_dir / "dedupe_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(6, summary["raw_signal_count"])
            self.assertEqual(2, summary["duplicate_link_count"])
            self.assertEqual(0, summary["skipped_empty_claim_count"])

    def test_fixture_contains_only_tiny_synthetic_data(self):
        fixture_text = RAW_SIGNALS_FIXTURE.read_text(encoding="utf-8")

        self.assertIn("synthetic", fixture_text.lower())
        self.assertIn("Server Alpha", fixture_text)
        self.assertNotIn("@", fixture_text)
        self.assertNotIn("Dell PowerEdge", fixture_text)
        self.assertLess(len(fixture_text), 5000)


if __name__ == "__main__":
    unittest.main()
