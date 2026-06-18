import json
import os
import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, os.fspath(Path(__file__).resolve().parents[1]))

import chatgpt_export_ingest


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "examples" / "chatgpt_export_fixture"


def read_manifest(out_dir: Path) -> list[dict[str, object]]:
    manifest_path = out_dir / "manifests" / "conversations.jsonl"
    return [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines()]


class ChatGPTExportIngestTests(unittest.TestCase):
    def test_fixture_export_parses_and_writes_normalized_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir) / "sources"

            rows = chatgpt_export_ingest.ingest_export(FIXTURE_DIR, out_dir)

            self.assertEqual(1, len(rows))
            manifest_path = out_dir / "manifests" / "conversations.jsonl"
            self.assertTrue(manifest_path.is_file())

            manifest_rows = read_manifest(out_dir)
            self.assertEqual(1, len(manifest_rows))
            row = manifest_rows[0]
            self.assertEqual("Synthetic Export Fixture", row["title"])
            self.assertEqual("synthetic-export-fixture", row["slug"])
            self.assertEqual(2, row["turn_count"])

            normalized_path = Path(str(row["normalized_path"]))
            self.assertTrue(normalized_path.is_file())
            self.assertEqual(normalized_path.read_bytes().__len__(), row["byte_count"])

            markdown = normalized_path.read_text(encoding="utf-8")
            self.assertIn("# ChatGPT Conversation Source", markdown)
            self.assertIn("Title: Synthetic Export Fixture", markdown)
            self.assertIn("### Turn 0001", markdown)
            self.assertIn("user", markdown)
            self.assertIn("Please summarize the synthetic project note.", markdown)
            self.assertIn("### Turn 0002", markdown)
            self.assertIn("assistant", markdown)
            self.assertIn("The synthetic note says to keep generated files reviewable.", markdown)
            self.assertLess(markdown.index("### Turn 0001"), markdown.index("### Turn 0002"))
            self.assertNotIn("Synthetic system setup", markdown)

    def test_main_cli_parses_fixture_successfully(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir) / "sources"

            exit_code = chatgpt_export_ingest.main(
                [
                    "--export-dir",
                    os.fspath(FIXTURE_DIR),
                    "--out-dir",
                    os.fspath(out_dir),
                ]
            )

            self.assertEqual(0, exit_code)
            self.assertTrue((out_dir / "normalized").is_dir())
            self.assertTrue((out_dir / "manifests" / "conversations.jsonl").is_file())

    def test_stable_ids_are_deterministic_across_runs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            first_out = Path(temp_dir) / "first"
            second_out = Path(temp_dir) / "second"

            chatgpt_export_ingest.ingest_export(FIXTURE_DIR, first_out)
            chatgpt_export_ingest.ingest_export(FIXTURE_DIR, second_out)

            first_rows = read_manifest(first_out)
            second_rows = read_manifest(second_out)

            first_stable_fields = [
                (
                    row["conversation_id"],
                    row["slug"],
                    Path(str(row["normalized_path"])).name,
                    row["source_hash"],
                )
                for row in first_rows
            ]
            second_stable_fields = [
                (
                    row["conversation_id"],
                    row["slug"],
                    Path(str(row["normalized_path"])).name,
                    row["source_hash"],
                )
                for row in second_rows
            ]
            self.assertEqual(first_stable_fields, second_stable_fields)

    def test_missing_optional_fields_do_not_crash(self):
        export = [
            {
                "mapping": {
                    "b": {
                        "id": "b",
                        "parent": None,
                        "children": [],
                        "message": {
                            "author": {
                                "role": "user",
                            },
                            "content": {
                                "content_type": "text",
                                "parts": [
                                    "Hello from a sparse synthetic export.",
                                    {"kind": "synthetic-non-string-part", "value": 1},
                                ],
                            },
                        },
                    }
                }
            }
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            export_dir = Path(temp_dir) / "export"
            out_dir = Path(temp_dir) / "out"
            export_dir.mkdir()
            (export_dir / "conversations.json").write_text(json.dumps(export), encoding="utf-8")

            rows = chatgpt_export_ingest.ingest_export(export_dir, out_dir)

            self.assertEqual(1, len(rows))
            row = read_manifest(out_dir)[0]
            self.assertEqual("Untitled", row["title"])
            self.assertEqual("unknown", row["created_at"])
            self.assertEqual("unknown", row["updated_at"])
            self.assertEqual(1, row["turn_count"])
            markdown = Path(str(row["normalized_path"])).read_text(encoding="utf-8")
            self.assertIn("Hello from a sparse synthetic export.", markdown)
            self.assertIn('"kind": "synthetic-non-string-part"', markdown)

    def test_empty_and_system_messages_are_skipped(self):
        export = [
            {
                "id": "skip-test",
                "title": "Skip Test",
                "current_node": "assistant-visible",
                "mapping": {
                    "system-hidden": {
                        "parent": None,
                        "message": {
                            "author": {"role": "system"},
                            "create_time": 1,
                            "content": {"content_type": "text", "parts": ["Do not include this setup."]},
                        },
                    },
                    "user-empty": {
                        "parent": "system-hidden",
                        "message": {
                            "author": {"role": "user"},
                            "create_time": 2,
                            "content": {"content_type": "text", "parts": ["   "]},
                        },
                    },
                    "assistant-visible": {
                        "parent": "user-empty",
                        "message": {
                            "author": {"role": "assistant"},
                            "create_time": 3,
                            "content": {"content_type": "text", "parts": ["Visible synthetic answer."]},
                        },
                    },
                },
            }
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            export_dir = Path(temp_dir) / "export"
            out_dir = Path(temp_dir) / "out"
            export_dir.mkdir()
            (export_dir / "conversations.json").write_text(json.dumps(export), encoding="utf-8")

            rows = chatgpt_export_ingest.ingest_export(export_dir, out_dir)

            self.assertEqual(1, len(rows))
            row = read_manifest(out_dir)[0]
            self.assertEqual(1, row["turn_count"])
            markdown = Path(str(row["normalized_path"])).read_text(encoding="utf-8")
            self.assertIn("Visible synthetic answer.", markdown)
            self.assertNotIn("Do not include this setup.", markdown)
            self.assertNotIn("### Turn 0002", markdown)

    def test_fallback_sorts_message_nodes_by_timestamp_and_node_id(self):
        export = [
            {
                "id": "fallback-test",
                "title": "Fallback Test",
                "current_node": "missing-node",
                "mapping": {
                    "node-b": {
                        "message": {
                            "author": {"role": "assistant"},
                            "create_time": 20,
                            "content": {"content_type": "text", "parts": ["second"]},
                        }
                    },
                    "node-a": {
                        "message": {
                            "author": {"role": "user"},
                            "create_time": 10,
                            "content": {"content_type": "text", "parts": ["first"]},
                        }
                    },
                    "node-c": {
                        "message": {
                            "author": {"role": "assistant"},
                            "create_time": 20,
                            "content": {"content_type": "text", "parts": ["third"]},
                        }
                    },
                },
            }
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            export_dir = Path(temp_dir) / "export"
            out_dir = Path(temp_dir) / "out"
            export_dir.mkdir()
            (export_dir / "conversations.json").write_text(json.dumps(export), encoding="utf-8")

            chatgpt_export_ingest.ingest_export(export_dir, out_dir)

            markdown = Path(str(read_manifest(out_dir)[0]["normalized_path"])).read_text(encoding="utf-8")
            self.assertLess(markdown.index("first"), markdown.index("second"))
            self.assertLess(markdown.index("second"), markdown.index("third"))

    def test_manifest_paths_point_to_existing_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir) / "sources"

            chatgpt_export_ingest.ingest_export(FIXTURE_DIR, out_dir)

            for row in read_manifest(out_dir):
                self.assertTrue(Path(str(row["normalized_path"])).is_file())

    def test_fixture_contains_only_tiny_synthetic_data(self):
        fixture_text = (FIXTURE_DIR / "conversations.json").read_text(encoding="utf-8")
        fixture = json.loads(fixture_text)

        self.assertEqual(1, len(fixture))
        self.assertIn("Synthetic Export Fixture", fixture_text)
        self.assertIn("synthetic", fixture_text.lower())
        self.assertNotIn("@", fixture_text)
        self.assertLess(len(fixture_text), 6000)


if __name__ == "__main__":
    unittest.main()
