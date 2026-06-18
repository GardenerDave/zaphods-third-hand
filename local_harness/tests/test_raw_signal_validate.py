import json
import os
import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, os.fspath(Path(__file__).resolve().parents[1]))

import raw_signal_validate
import signal_dedupe


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "examples" / "chatgpt_export_fixture"
RAW_SIGNALS_FIXTURE = FIXTURE_DIR / "raw_signals.jsonl"


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class RawSignalValidateTests(unittest.TestCase):
    def test_valid_synthetic_fixture_rows_pass(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir) / "validated"

            summary = raw_signal_validate.validate_raw_signals(RAW_SIGNALS_FIXTURE, out_dir)

            self.assertEqual(6, summary["input_row_count"])
            self.assertEqual(6, summary["valid_count"])
            self.assertEqual(0, summary["invalid_count"])
            self.assertTrue((out_dir / "valid_raw_signals.jsonl").is_file())
            self.assertTrue((out_dir / "invalid_raw_signals.jsonl").is_file())
            self.assertTrue((out_dir / "validation_summary.json").is_file())

    def test_missing_optional_fields_get_defaults_and_missing_id_is_deterministic(self):
        rows = [
            {"claim": "Synthetic claim without optional fields."},
            {"claim": "Synthetic claim with strange labels.", "signal_type": "weird", "status_hint": "later", "confidence": "sure"},
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            raw_path = temp_root / "raw_signals.jsonl"
            raw_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            first_out = temp_root / "first"
            second_out = temp_root / "second"

            first_summary = raw_signal_validate.validate_raw_signals(raw_path, first_out)
            raw_signal_validate.validate_raw_signals(raw_path, second_out)

            first_rows = read_jsonl(first_out / "valid_raw_signals.jsonl")
            second_rows = read_jsonl(second_out / "valid_raw_signals.jsonl")
            self.assertEqual(2, first_summary["generated_raw_signal_id_count"])
            self.assertEqual(3, first_summary["normalized_unknown_label_count"])
            self.assertEqual(first_rows[0]["raw_signal_id"], second_rows[0]["raw_signal_id"])
            self.assertEqual(first_rows[1]["raw_signal_id"], second_rows[1]["raw_signal_id"])
            self.assertEqual("unknown", first_rows[0]["signal_type"])
            self.assertEqual("unknown", first_rows[0]["status_hint"])
            self.assertEqual("unknown", first_rows[0]["confidence"])
            self.assertEqual("", first_rows[0]["conversation_id"])
            self.assertIsNone(first_rows[0]["turn_start"])
            self.assertIsNone(first_rows[0]["turn_end"])

    def test_invalid_json_and_empty_claim_rows_are_captured(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            raw_path = temp_root / "raw_signals.jsonl"
            raw_path.write_text(
                "\n".join(
                    [
                        json.dumps({"raw_signal_id": "raw-ok", "claim": "Synthetic valid claim."}),
                        "{not valid json",
                        json.dumps({"raw_signal_id": "raw-empty", "claim": "   "}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            out_dir = temp_root / "validated"

            summary = raw_signal_validate.validate_raw_signals(raw_path, out_dir)

            invalid_rows = read_jsonl(out_dir / "invalid_raw_signals.jsonl")
            self.assertEqual(3, summary["input_row_count"])
            self.assertEqual(1, summary["valid_count"])
            self.assertEqual(2, summary["invalid_count"])
            self.assertIn("invalid_json", invalid_rows[0]["reason"])
            self.assertEqual("empty_claim", invalid_rows[1]["reason"])
            self.assertEqual(2, invalid_rows[0]["line_number"])
            self.assertEqual(3, invalid_rows[1]["line_number"])

    def test_output_jsonl_is_valid_and_summary_counts_are_correct(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir) / "validated"

            raw_signal_validate.validate_raw_signals(RAW_SIGNALS_FIXTURE, out_dir)

            valid_rows = read_jsonl(out_dir / "valid_raw_signals.jsonl")
            invalid_rows = read_jsonl(out_dir / "invalid_raw_signals.jsonl")
            summary = json.loads((out_dir / "validation_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(6, len(valid_rows))
            self.assertEqual([], invalid_rows)
            self.assertEqual(6, summary["input_row_count"])
            self.assertEqual(6, summary["valid_count"])
            self.assertEqual(0, summary["invalid_count"])
            self.assertFalse(summary["deduped"])
            for row in valid_rows:
                self.assertIsInstance(row, dict)
                self.assertTrue(row["claim"])

    def test_validator_output_can_be_passed_to_signal_dedupe(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            validated_dir = temp_root / "validated"
            dedupe_dir = temp_root / "signals"

            raw_signal_validate.validate_raw_signals(RAW_SIGNALS_FIXTURE, validated_dir)
            summary = signal_dedupe.process_signals(validated_dir / "valid_raw_signals.jsonl", dedupe_dir)

            self.assertEqual(6, summary["raw_signal_count"])
            self.assertEqual(4, summary["deduped_signal_count"])
            self.assertEqual(2, summary["duplicate_link_count"])
            self.assertEqual(1, summary["conflict_candidate_count"])

    def test_main_cli_writes_validation_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir) / "validated"

            exit_code = raw_signal_validate.main(
                [
                    "--raw-signals",
                    os.fspath(RAW_SIGNALS_FIXTURE),
                    "--out-dir",
                    os.fspath(out_dir),
                ]
            )

            self.assertEqual(0, exit_code)
            self.assertTrue((out_dir / "valid_raw_signals.jsonl").is_file())

    def test_fixture_contains_only_tiny_synthetic_data(self):
        fixture_text = RAW_SIGNALS_FIXTURE.read_text(encoding="utf-8")

        self.assertIn("synthetic", fixture_text.lower())
        self.assertIn("Server Alpha", fixture_text)
        self.assertNotIn("@", fixture_text)
        self.assertNotIn("Dell PowerEdge", fixture_text)
        self.assertLess(len(fixture_text), 5000)


if __name__ == "__main__":
    unittest.main()
