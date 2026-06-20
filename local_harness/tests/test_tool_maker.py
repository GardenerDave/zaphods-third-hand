import os
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, os.fspath(Path(__file__).resolve().parents[1]))

import tool_maker


REQUIRED_SECTIONS = (
    "## Purpose",
    "## When to Use",
    "## Inputs Required",
    "## Preconditions",
    "## Human Decisions Required",
    "## Workflow Steps",
    "## Useful Commands",
    "## Validation Checks",
    "## Failure Modes",
    "## Failed-but-Important Attempts",
    "## Things We Are Proud Of",
    "## Things We Are Not Proud Of",
    "## Simplification / Essential Complexity",
    "## Recovery / Rollback",
    "## Artifacts Produced",
    "## Promotion Criteria",
    "## Open Questions",
)


class ToolMakerTests(unittest.TestCase):
    def test_scaffold_generation_succeeds_with_required_sections(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "terminal.log"
            output = root / "nested" / "lifecycle.md"
            source.write_text("$ command\nsuccessful output\n", encoding="utf-8")

            records = tool_maker.generate_scaffold([source], output, name="Provider smoke")
            text = output.read_text(encoding="utf-8")

        self.assertEqual(1, len(records))
        self.assertIn("# Tool Lifecycle Draft: Provider smoke", text)
        for section in REQUIRED_SECTIONS:
            self.assertIn(section, text)
        self.assertIn("status: draft", text)
        self.assertIn("requires_human_review: true", text)
        self.assertIn("promotion_recommendation: not_ready", text)
        self.assertIn("## Things We Are Proud Of", text)
        self.assertIn("## Things We Are Not Proud Of", text)
        self.assertIn("## Simplification / Essential Complexity", text)
        self.assertIn(
            "Simplification does not mean removing safety, provenance, reversibility",
            text,
        )

    def test_missing_input_file_fails_clearly(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            missing = root / "missing.log"

            with self.assertRaisesRegex(ValueError, "input file does not exist"):
                tool_maker.generate_scaffold(
                    [missing],
                    root / "lifecycle.md",
                    name="Missing source",
                )

    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "notes.md"
            output = root / "lifecycle.md"
            source.write_text("Source evidence.\n", encoding="utf-8")
            output.write_text("Preserve this draft.\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "output path already exists"):
                tool_maker.generate_scaffold(
                    [source],
                    output,
                    name="No overwrite",
                )

            self.assertEqual("Preserve this draft.\n", output.read_text(encoding="utf-8"))

    def test_metadata_includes_source_names_count_and_stats(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chat = root / "chat.md"
            notes = root / "operator-notes.md"
            output = root / "lifecycle.md"
            chat.write_text("Intent and attempted steps.\n", encoding="utf-8")
            notes.write_text("Validation passed.\nFailure mattered.\n", encoding="utf-8")

            tool_maker.generate_scaffold([chat, notes], output, name="Evidence workflow")
            text = output.read_text(encoding="utf-8")

        self.assertIn('  - "chat.md"', text)
        self.assertIn('  - "operator-notes.md"', text)
        self.assertIn("source_count: 2", text)
        self.assertIn('"bytes":', text)
        self.assertIn('"lines":', text)
        self.assertIn('"included_characters":', text)

    def test_lifecycle_name_is_preserved_and_normalized_to_one_line(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "notes.md"
            output = root / "lifecycle.md"
            source.write_text("Notes.\n", encoding="utf-8")

            tool_maker.generate_scaffold(
                [source],
                output,
                name="ResonantOS local\nprovider smoke workflow",
            )
            text = output.read_text(encoding="utf-8")

        expected = "ResonantOS local provider smoke workflow"
        self.assertIn(f"# Tool Lifecycle Draft: {expected}", text)
        self.assertIn(f'lifecycle_name: "{expected}"', text)

    def test_source_packet_is_bounded_and_records_truncation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "large.log"
            output = root / "lifecycle.md"
            source.write_text("abcdefghij", encoding="utf-8")

            records = tool_maker.generate_scaffold(
                [source],
                output,
                name="Bounded source",
                max_source_chars=4,
            )
            text = output.read_text(encoding="utf-8")

        self.assertEqual("abcd", records[0].included_text)
        self.assertTrue(records[0].truncated)
        self.assertIn('"included_characters": 4', text)
        self.assertIn('"truncated": true', text)
        self.assertNotIn("abcdefghij", text)

    def test_cli_writes_scaffold(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "notes.md"
            output = root / "tool-lifecycle.md"
            source.write_text("Observed workflow.\n", encoding="utf-8")

            exit_code = tool_maker.main(
                [
                    "--name",
                    "CLI lifecycle",
                    "--out",
                    os.fspath(output),
                    os.fspath(source),
                ]
            )

            self.assertEqual(0, exit_code)
            self.assertIn("CLI lifecycle", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
