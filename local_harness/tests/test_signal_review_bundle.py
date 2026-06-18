import json
import os
import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, os.fspath(Path(__file__).resolve().parents[1]))

import raw_signal_validate
import signal_dedupe
import signal_review_bundle


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "examples" / "chatgpt_export_fixture"
RAW_SIGNALS_FIXTURE = FIXTURE_DIR / "raw_signals.jsonl"


def build_signals_fixture(temp_root: Path) -> Path:
    validated_dir = temp_root / "validated_signals"
    signals_dir = temp_root / "signals"
    raw_signal_validate.validate_raw_signals(RAW_SIGNALS_FIXTURE, validated_dir)
    signal_dedupe.process_signals(validated_dir / "valid_raw_signals.jsonl", signals_dir)
    return signals_dir


def read_all_files(root: Path) -> dict[str, str]:
    return {
        os.fspath(path.relative_to(root)): path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class SignalReviewBundleTests(unittest.TestCase):
    def test_reads_signal_dedupe_outputs_and_creates_bundle_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            signals_dir = build_signals_fixture(temp_root)
            out_dir = temp_root / "review_bundle"

            bundle = signal_review_bundle.build_review_bundle(signals_dir, out_dir)

            self.assertTrue((out_dir / "review_summary.md").is_file())
            self.assertTrue((out_dir / "review_bundle.json").is_file())
            self.assertEqual(4, bundle["deduped_signal_count"])
            self.assertEqual(2, bundle["duplicate_link_count"])
            self.assertEqual(1, bundle["conflict_candidate_count"])

    def test_creates_expected_canonical_candidate_markdown_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            signals_dir = build_signals_fixture(temp_root)
            out_dir = temp_root / "review_bundle"

            signal_review_bundle.build_review_bundle(signals_dir, out_dir)

            self.assertTrue((out_dir / "canonical_candidates" / "current_state.md").is_file())
            self.assertTrue((out_dir / "canonical_candidates" / "open_questions.md").is_file())
            self.assertTrue((out_dir / "canonical_candidates" / "conflicts.md").is_file())
            self.assertFalse((out_dir / "canonical_candidates" / "decisions.md").exists())

    def test_current_state_duplicate_collapse_appears_as_one_candidate_with_provenance(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            signals_dir = build_signals_fixture(temp_root)
            out_dir = temp_root / "review_bundle"

            signal_review_bundle.build_review_bundle(signals_dir, out_dir)

            current_state = (out_dir / "canonical_candidates" / "current_state.md").read_text(encoding="utf-8")
            self.assertEqual(1, current_state.count("The synthetic main inference host is Server Alpha."))
            self.assertIn("- raw-001", current_state)
            self.assertIn("- raw-002", current_state)
            self.assertIn("- raw-003", current_state)
            self.assertIn("- synthetic-conv-001", current_state)
            self.assertIn("- synthetic-conv-002", current_state)
            self.assertIn("- chunk-synthetic-001", current_state)
            self.assertIn("- chunk-synthetic-002", current_state)
            self.assertIn("- chunk-synthetic-003", current_state)

    def test_open_question_and_conflict_candidates_are_rendered(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            signals_dir = build_signals_fixture(temp_root)
            out_dir = temp_root / "review_bundle"

            signal_review_bundle.build_review_bundle(signals_dir, out_dir)

            open_questions = (out_dir / "canonical_candidates" / "open_questions.md").read_text(encoding="utf-8")
            conflicts = (out_dir / "canonical_candidates" / "conflicts.md").read_text(encoding="utf-8")
            self.assertIn("Should the synthetic onboarding note mention the chunk profile?", open_questions)
            self.assertIn("Conflict id:", conflicts)
            self.assertIn("synthetic primary host", conflicts)
            self.assertIn("Server Beta was the synthetic primary host.", conflicts)
            self.assertIn("Server Alpha is now the synthetic primary host.", conflicts)
            self.assertIn("raw-005", conflicts)
            self.assertIn("historical", conflicts)
            self.assertIn("raw-006", conflicts)
            self.assertIn("current", conflicts)

    def test_review_decision_checkboxes_and_safety_notes_are_present(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            signals_dir = build_signals_fixture(temp_root)
            out_dir = temp_root / "review_bundle"

            signal_review_bundle.build_review_bundle(signals_dir, out_dir)

            current_state = (out_dir / "canonical_candidates" / "current_state.md").read_text(encoding="utf-8")
            summary = (out_dir / "review_summary.md").read_text(encoding="utf-8")
            for checkbox in ("- [ ] Accept", "- [ ] Reject", "- [ ] Needs rework", "- [ ] Superseded", "- [ ] Uncertain"):
                self.assertIn(checkbox, current_state)
            self.assertIn("These files are review material only.", summary)
            self.assertIn("not canonical memory", summary)
            self.assertIn("must not be promoted automatically", summary)

    def test_json_bundle_counts_and_paths_are_correct(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            signals_dir = build_signals_fixture(temp_root)
            out_dir = temp_root / "review_bundle"

            signal_review_bundle.build_review_bundle(signals_dir, out_dir)

            bundle = json.loads((out_dir / "review_bundle.json").read_text(encoding="utf-8"))
            self.assertEqual(4, bundle["deduped_signal_count"])
            self.assertEqual(2, bundle["duplicate_link_count"])
            self.assertEqual(1, bundle["conflict_candidate_count"])
            self.assertEqual(3, bundle["candidate_file_count"])
            self.assertTrue(bundle["review_only"])
            self.assertEqual(
                [
                    "canonical_candidates/current_state.md",
                    "canonical_candidates/open_questions.md",
                    "canonical_candidates/conflicts.md",
                ],
                bundle["candidate_files"],
            )
            for relative_path in bundle["candidate_files"]:
                self.assertTrue((out_dir / relative_path).is_file())
            self.assertTrue(Path(bundle["review_summary_path"]).is_file())

    def test_review_summary_lists_candidate_files_and_counts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            signals_dir = build_signals_fixture(temp_root)
            out_dir = temp_root / "review_bundle"

            signal_review_bundle.build_review_bundle(signals_dir, out_dir)

            summary = (out_dir / "review_summary.md").read_text(encoding="utf-8")
            self.assertIn("Raw signals: 6", summary)
            self.assertIn("Deduped signals: 4", summary)
            self.assertIn("Duplicate links: 2", summary)
            self.assertIn("Conflict candidates: 1", summary)
            self.assertIn("- canonical_candidates/current_state.md", summary)
            self.assertIn("- canonical_candidates/conflicts.md", summary)

    def test_output_is_deterministic_across_two_runs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            signals_dir = build_signals_fixture(temp_root)
            first_out = temp_root / "first_review_bundle"
            second_out = temp_root / "second_review_bundle"

            signal_review_bundle.build_review_bundle(signals_dir, first_out)
            signal_review_bundle.build_review_bundle(signals_dir, second_out)

            first_files = read_all_files(first_out)
            second_files = read_all_files(second_out)
            first_files["review_bundle.json"] = first_files["review_bundle.json"].replace(
                os.fspath(first_out), "<OUT_DIR>"
            )
            second_files["review_bundle.json"] = second_files["review_bundle.json"].replace(
                os.fspath(second_out), "<OUT_DIR>"
            )
            self.assertEqual(first_files, second_files)

    def test_missing_optional_input_files_are_handled_gracefully(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            signals_dir = temp_root / "signals"
            signals_dir.mkdir()
            (signals_dir / "deduped_signals.jsonl").write_text(
                json.dumps(
                    {
                        "canonical_signal_id": "sig-synthetic-minimal",
                        "claim": "Synthetic minimal candidate.",
                        "signal_type": "unknown_type",
                        "status": "unknown",
                        "confidence": "unknown",
                        "supporting_raw_signal_ids": ["raw-minimal"],
                        "source_conversation_ids": [],
                        "source_chunk_ids": [],
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            out_dir = temp_root / "review_bundle"

            bundle = signal_review_bundle.build_review_bundle(signals_dir, out_dir)

            self.assertEqual(1, bundle["deduped_signal_count"])
            self.assertEqual(0, bundle["duplicate_link_count"])
            self.assertEqual(0, bundle["conflict_candidate_count"])
            current_state = (out_dir / "canonical_candidates" / "current_state.md").read_text(encoding="utf-8")
            self.assertIn("## Unclassified", current_state)
            self.assertIn("Synthetic minimal candidate.", current_state)

    def test_main_cli_writes_review_bundle(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            signals_dir = build_signals_fixture(temp_root)
            out_dir = temp_root / "review_bundle"

            exit_code = signal_review_bundle.main(
                [
                    "--signals-dir",
                    os.fspath(signals_dir),
                    "--out-dir",
                    os.fspath(out_dir),
                ]
            )

            self.assertEqual(0, exit_code)
            self.assertTrue((out_dir / "review_summary.md").is_file())
            self.assertTrue((out_dir / "review_bundle.json").is_file())

    def test_fixture_contains_only_tiny_synthetic_data(self):
        fixture_text = RAW_SIGNALS_FIXTURE.read_text(encoding="utf-8")

        self.assertIn("synthetic", fixture_text.lower())
        self.assertIn("Server Alpha", fixture_text)
        self.assertNotIn("@", fixture_text)
        self.assertNotIn("Dell PowerEdge", fixture_text)
        self.assertLess(len(fixture_text), 5000)


if __name__ == "__main__":
    unittest.main()
