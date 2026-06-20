import os
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, os.fspath(Path(__file__).resolve().parents[1]))

import change_closeout
import tool_maker
import validate_scaffold


class ValidateScaffoldTests(unittest.TestCase):
    def generate_tool(self, root: Path, *, source_count: int = 1) -> tuple[Path, list]:
        sources = []
        for index in range(source_count):
            source = root / f"tool-{index}" / "README.md"
            source.parent.mkdir(parents=True)
            source.write_text(f"Tool source {index}.\n", encoding="utf-8")
            sources.append(source)
        output = root / "tool-lifecycle.md"
        records = tool_maker.generate_scaffold(
            sources,
            output,
            name="Validation tool lifecycle",
        )
        return output, records

    def generate_closeout(self, root: Path) -> tuple[Path, list]:
        source = root / "change.md"
        source.write_text("Completed change evidence.\n", encoding="utf-8")
        output = root / "change-closeout.md"
        records = change_closeout.generate_scaffold(
            [source],
            output,
            name="Validation closeout",
        )
        return output, records

    def rewrite(self, path: Path, old: str, new: str, *, count: int = -1) -> None:
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, count), encoding="utf-8")

    def assert_validation_error(self, path: Path, message: str) -> None:
        with self.assertRaisesRegex(
            validate_scaffold.ScaffoldValidationError,
            message,
        ):
            validate_scaffold.validate_scaffold(path)

    def test_generated_tool_maker_scaffold_validates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path, _records = self.generate_tool(Path(temp_dir))

            kind = validate_scaffold.validate_scaffold(path)

        self.assertEqual("tool-lifecycle", kind)

    def test_generated_change_closeout_scaffold_validates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path, _records = self.generate_closeout(Path(temp_dir))

            kind = validate_scaffold.validate_scaffold(
                path,
                expected_kind="change-closeout",
            )

        self.assertEqual("change-closeout", kind)

    def test_missing_contract_version_fails_clearly(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path, _records = self.generate_tool(Path(temp_dir))
            self.rewrite(
                path,
                'scaffold_contract_version: "tool-lifecycle-v1"\n',
                "",
            )

            self.assert_validation_error(path, "missing scaffold_contract_version")

    def test_unknown_contract_version_fails_clearly(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path, _records = self.generate_tool(Path(temp_dir))
            self.rewrite(path, "tool-lifecycle-v1", "unknown-v9")

            self.assert_validation_error(path, "unknown scaffold_contract_version")

    def test_duplicate_source_labels_fail(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path, records = self.generate_tool(Path(temp_dir), source_count=2)
            self.rewrite(
                path,
                records[1].source_label,
                records[0].source_label,
            )

            self.assert_validation_error(path, "duplicate source labels")

    def test_source_count_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path, _records = self.generate_tool(Path(temp_dir))
            self.rewrite(path, "source_count: 1", "source_count: 2")

            self.assert_validation_error(path, "source_count mismatch")

    def test_source_material_label_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path, records = self.generate_tool(Path(temp_dir))
            quoted_label = tool_maker.yaml_string(records[0].source_label)
            self.rewrite(
                path,
                f"  - {quoted_label}",
                '  - "different/source.md"',
                count=1,
            )

            self.assert_validation_error(
                path,
                "source_material entries must match source_label",
            )

    def test_bad_sha256_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path, records = self.generate_tool(Path(temp_dir))
            self.rewrite(path, records[0].sha256, "ABC123")

            self.assert_validation_error(path, "64 lowercase hexadecimal")

    def test_any_truncated_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path, _records = self.generate_tool(Path(temp_dir))
            self.rewrite(path, "any_truncated: false", "any_truncated: true")

            self.assert_validation_error(path, "any_truncated does not match")

    def test_total_source_characters_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path, records = self.generate_tool(Path(temp_dir))
            self.rewrite(
                path,
                f"total_source_characters: {records[0].character_count}",
                "total_source_characters: 999",
            )

            self.assert_validation_error(
                path,
                "total_source_characters does not match",
            )

    def test_total_included_characters_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path, records = self.generate_tool(Path(temp_dir))
            self.rewrite(
                path,
                f"total_included_characters: {records[0].included_character_count}",
                "total_included_characters: 999",
            )

            self.assert_validation_error(
                path,
                "total_included_characters does not match",
            )

    def test_missing_required_heading_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path, _records = self.generate_tool(Path(temp_dir))
            self.rewrite(path, "## Validation Checks", "## Checks Omitted")

            self.assert_validation_error(path, "missing required heading")

    def test_invalid_enum_field_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path, _records = self.generate_closeout(Path(temp_dir))
            self.rewrite(
                path,
                "docs_pass_status: incomplete",
                "docs_pass_status: assumed",
            )

            self.assert_validation_error(path, "docs_pass_status")

    def test_original_sources_are_not_required_after_generation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path, _records = self.generate_tool(root)
            for source in root.glob("tool-*/README.md"):
                source.unlink()

            kind = validate_scaffold.validate_scaffold(path)

        self.assertEqual("tool-lifecycle", kind)


if __name__ == "__main__":
    unittest.main()
