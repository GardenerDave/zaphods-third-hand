import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, os.fspath(Path(__file__).resolve().parents[1]))

import change_closeout


REQUIRED_SECTIONS = (
    "## Summary",
    "## Files / Areas Changed",
    "## Behavior Changes",
    "## Validation Performed",
    "## Docs Pass",
    "## Safety / Authority Boundary Check",
    "## Things We Are Proud Of",
    "## Things We Are Not Proud Of",
    "## Simplification / Essential Complexity",
    "## Lifecycle Knowledge Captured",
    "## Promotion Readiness",
    "## Follow-Up Tasks",
    "## Open Questions",
)


class ChangeCloseoutTests(unittest.TestCase):
    def test_scaffold_generation_succeeds_with_required_sections(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "change.md"
            output = root / "nested" / "closeout.md"
            source.write_text("Implemented a reviewed change.\n", encoding="utf-8")

            records = change_closeout.generate_scaffold(
                [source],
                output,
                name="Tool Maker v1",
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(1, len(records))
        self.assertIn("# Change Closeout Report: Tool Maker v1", text)
        self.assertIn(
            'scaffold_contract_version: "change-closeout-v1"',
            text,
        )
        for section in REQUIRED_SECTIONS:
            self.assertIn(section, text)
        self.assertIn("docs_pass_status: incomplete", text)
        self.assertIn("requires_human_review: true", text)
        self.assertIn("promotion_recommendation: not_ready", text)

    def test_missing_input_file_fails_clearly(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            with self.assertRaisesRegex(ValueError, "input file does not exist"):
                change_closeout.generate_scaffold(
                    [root / "missing.md"],
                    root / "closeout.md",
                    name="Missing evidence",
                )

    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "change.md"
            output = root / "closeout.md"
            source.write_text("Evidence.\n", encoding="utf-8")
            output.write_text("Preserve this closeout.\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "output path already exists"):
                change_closeout.generate_scaffold(
                    [source],
                    output,
                    name="No overwrite",
                )

            self.assertEqual("Preserve this closeout.\n", output.read_text(encoding="utf-8"))

    def test_metadata_includes_source_names_count_and_stats(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            implementation = root / "implementation.py"
            tests = root / "tests.md"
            output = root / "closeout.md"
            implementation.write_text("print('change')\n", encoding="utf-8")
            tests.write_text("Tests passed with limitations.\n", encoding="utf-8")
            expected_total = len(
                implementation.read_text(encoding="utf-8")
            ) + len(tests.read_text(encoding="utf-8"))
            implementation_sha256 = hashlib.sha256(
                implementation.read_bytes()
            ).hexdigest()
            tests_sha256 = hashlib.sha256(tests.read_bytes()).hexdigest()

            records = change_closeout.generate_scaffold(
                [implementation, tests],
                output,
                name="Evidence closeout",
            )
            text = output.read_text(encoding="utf-8")

        self.assertIn(
            f"  - {change_closeout.yaml_string(records[0].source_label)}",
            text,
        )
        self.assertIn(
            f"  - {change_closeout.yaml_string(records[1].source_label)}",
            text,
        )
        self.assertIn("source_count: 2", text)
        self.assertIn(
            f"max_source_chars: {change_closeout.DEFAULT_MAX_SOURCE_CHARS}",
            text,
        )
        self.assertIn(f"total_source_characters: {expected_total}", text)
        self.assertIn(f"total_included_characters: {expected_total}", text)
        self.assertIn("any_truncated: false", text)
        self.assertIn('"bytes":', text)
        self.assertIn('"lines":', text)
        self.assertEqual(2, text.count('"sha256":'))
        self.assertIn(implementation_sha256, text)
        self.assertIn(tests_sha256, text)

    def test_duplicate_basenames_remain_distinguishable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = root / "first" / "README.md"
            second = root / "second" / "README.md"
            output = root / "closeout.md"
            first.parent.mkdir()
            second.parent.mkdir()
            first.write_text("First source.\n", encoding="utf-8")
            second.write_text("Second source.\n", encoding="utf-8")

            records = change_closeout.generate_scaffold(
                [first, second],
                output,
                name="Duplicate basenames",
            )
            text = output.read_text(encoding="utf-8")

        self.assertNotEqual(records[0].source_label, records[1].source_label)
        self.assertTrue(records[0].source_label.startswith("external/"))
        self.assertTrue(records[1].source_label.startswith("external/"))
        self.assertNotIn(os.fspath(root), records[0].source_label)
        self.assertNotIn(os.fspath(root), records[1].source_label)
        self.assertIn(
            f"  - {change_closeout.yaml_string(records[0].source_label)}",
            text,
        )
        self.assertIn(
            f"  - {change_closeout.yaml_string(records[1].source_label)}",
            text,
        )

    def test_repository_source_path_is_repository_relative(self):
        record = change_closeout.load_sources(
            [change_closeout.REPO_ROOT / "docs" / "README.md"],
            change_closeout.DEFAULT_MAX_SOURCE_CHARS,
        )[0]

        self.assertEqual("docs/README.md", record.source_path)
        self.assertEqual("docs/README.md", record.source_label)

    def test_change_name_is_preserved_and_normalized_to_one_line(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "change.md"
            output = root / "closeout.md"
            source.write_text("Evidence.\n", encoding="utf-8")

            change_closeout.generate_scaffold(
                [source],
                output,
                name="Tool Maker\nreflective layer",
            )
            text = output.read_text(encoding="utf-8")

        expected = "Tool Maker reflective layer"
        self.assertIn(f"# Change Closeout Report: {expected}", text)
        self.assertIn(f'change_name: "{expected}"', text)

    def test_source_packet_is_bounded_and_records_truncation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "large.log"
            output = root / "closeout.md"
            source.write_text("abcdefghij", encoding="utf-8")

            records = change_closeout.generate_scaffold(
                [source],
                output,
                name="Bounded closeout",
                max_source_chars=4,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual("abcd", records[0].included_text)
        self.assertTrue(records[0].truncated)
        self.assertIn('"included_characters": 4', text)
        self.assertIn('"truncated": true', text)
        self.assertIn("max_source_chars: 4", text)
        self.assertIn("total_source_characters: 10", text)
        self.assertIn("total_included_characters: 4", text)
        self.assertIn("any_truncated: true", text)
        self.assertNotIn("abcdefghij", text)

    def test_cli_writes_scaffold(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "change.md"
            output = root / "closeout.md"
            source.write_text("Reviewed change.\n", encoding="utf-8")

            exit_code = change_closeout.main(
                [
                    "--name",
                    "CLI closeout",
                    "--out",
                    os.fspath(output),
                    os.fspath(source),
                ]
            )

            self.assertEqual(0, exit_code)
            self.assertIn("CLI closeout", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
