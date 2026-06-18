import json
import os
import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, os.fspath(Path(__file__).resolve().parents[1]))

import chatgpt_export_ingest
import context_chunker


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "examples" / "chatgpt_export_fixture"


def ingest_fixture(temp_root: Path) -> Path:
    source_dir = temp_root / "sources"
    chatgpt_export_ingest.ingest_export(FIXTURE_DIR, source_dir)
    return source_dir / "manifests" / "conversations.jsonl"


def read_plan(out_dir: Path, conversation_id: str) -> dict[str, object]:
    return json.loads((out_dir / conversation_id / "chunk_plan.json").read_text(encoding="utf-8"))


def write_manifest_for_markdown(temp_root: Path, conversation_id: str, markdown: str) -> Path:
    normalized_dir = temp_root / "sources" / "normalized"
    manifest_dir = temp_root / "sources" / "manifests"
    normalized_dir.mkdir(parents=True)
    manifest_dir.mkdir(parents=True)
    source_path = normalized_dir / f"{conversation_id}_synthetic.md"
    source_path.write_text(markdown, encoding="utf-8")
    row = {
        "conversation_id": conversation_id,
        "title": "Synthetic Chunk Fixture",
        "slug": "synthetic-chunk-fixture",
        "created_at": "2024-03-09T16:00:00Z",
        "updated_at": "2024-03-09T16:05:00Z",
        "normalized_path": os.fspath(source_path),
        "source_hash": f"synthetic-hash-{conversation_id}",
        "turn_count": markdown.count("### Turn"),
        "byte_count": len(markdown.encode("utf-8")),
    }
    manifest_path = manifest_dir / "conversations.jsonl"
    manifest_path.write_text(json.dumps(row, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


def synthetic_markdown(turn_count: int, extra_text: str = "") -> str:
    lines = [
        "# ChatGPT Conversation Source",
        "",
        "Conversation ID: synthetic-many-turns",
        "Title: Synthetic Chunk Fixture",
        "Created: 2024-03-09T16:00:00Z",
        "Updated: 2024-03-09T16:05:00Z",
        "Source export: synthetic",
        "Source hash: synthetic-hash",
        f"Turn count: {turn_count}",
        "",
        "## Turns",
        "",
    ]
    for index in range(1, turn_count + 1):
        role = "user" if index % 2 else "assistant"
        lines.extend(
            [
                f"### Turn {index:04d} \u2014 {role} \u2014 2024-03-09T16:00:{index:02d}Z",
                "",
                f"Synthetic turn {index} content. {extra_text}".strip(),
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def pass_by_name(plan: dict[str, object], name: str) -> dict[str, object]:
    for pass_row in plan["passes"]:
        if pass_row["name"] == name:
            return pass_row
    raise AssertionError(f"missing pass {name}")


class ContextChunkerTests(unittest.TestCase):
    def test_reads_ingestion_manifest_and_semantic_creates_pass_a_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            manifest = ingest_fixture(temp_root)
            out_dir = temp_root / "chunks"

            plans = context_chunker.plan_manifest(manifest, out_dir, profile="semantic")

            self.assertEqual(1, len(plans))
            plan = plans[0]
            self.assertEqual("semantic", plan["profile"])
            self.assertEqual(["pass_A"], [pass_row["name"] for pass_row in plan["passes"]])
            self.assertTrue((out_dir / str(plan["conversation_id"]) / "pass_A").is_dir())
            self.assertFalse((out_dir / str(plan["conversation_id"]) / "pass_B_offset").exists())

    def test_small_model_offset_creates_two_passes_and_chunk_headers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            manifest = ingest_fixture(temp_root)
            out_dir = temp_root / "chunks"

            plans = context_chunker.plan_manifest(manifest, out_dir, profile="small-model-offset")

            plan = plans[0]
            self.assertEqual(["pass_A", "pass_B_offset"], [pass_row["name"] for pass_row in plan["passes"]])
            pass_a = pass_by_name(plan, "pass_A")
            pass_b = pass_by_name(plan, "pass_B_offset")
            self.assertGreater(len(pass_a["chunks"]), 0)
            self.assertGreater(len(pass_b["chunks"]), 0)

            chunk_path = Path(pass_a["chunks"][0]["path"])
            chunk_text = chunk_path.read_text(encoding="utf-8")
            self.assertTrue(chunk_text.startswith("# Distiller Chunk\n\n"))
            self.assertIn("Conversation ID:", chunk_text)
            self.assertIn("Chunk Pass: pass_A", chunk_text)
            self.assertIn("Profile: small-model-offset", chunk_text)
            self.assertIn("Oversized: false", chunk_text)
            self.assertIn("Chunk Strategy: target_chars_preserve_turns", chunk_text)
            self.assertIn("## Source Turns", chunk_text)
            self.assertIn("### Turn 0001", chunk_text)
            self.assertIn("### Turn 0002", chunk_text)

    def test_chunks_preserve_turn_headings_order_and_are_not_empty(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            manifest = write_manifest_for_markdown(temp_root, "synthetic-many-turns", synthetic_markdown(4))
            out_dir = temp_root / "chunks"

            plan = context_chunker.plan_manifest(manifest, out_dir, profile="small-model")[0]
            chunk = pass_by_name(plan, "pass_A")["chunks"][0]
            chunk_text = Path(chunk["path"]).read_text(encoding="utf-8")

            self.assertGreater(len(chunk_text.strip()), 0)
            self.assertLess(chunk_text.index("### Turn 0001"), chunk_text.index("### Turn 0002"))
            self.assertLess(chunk_text.index("### Turn 0002"), chunk_text.index("### Turn 0003"))
            self.assertLess(chunk_text.index("### Turn 0003"), chunk_text.index("### Turn 0004"))

    def test_chunk_plan_points_to_existing_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            manifest = ingest_fixture(temp_root)
            out_dir = temp_root / "chunks"

            plan = context_chunker.plan_manifest(manifest, out_dir, profile="small-model-offset")[0]

            self.assertTrue((out_dir / str(plan["conversation_id"]) / "chunk_plan.json").is_file())
            for pass_row in plan["passes"]:
                for chunk in pass_row["chunks"]:
                    self.assertTrue(Path(chunk["path"]).is_file())
                    self.assertGreater(Path(chunk["path"]).stat().st_size, 0)

    def test_manifest_relative_source_paths_resolve_from_manifest_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            normalized_dir = temp_root / "sources" / "normalized"
            manifest_dir = temp_root / "sources" / "manifests"
            normalized_dir.mkdir(parents=True)
            manifest_dir.mkdir(parents=True)
            source_path = normalized_dir / "synthetic-relative.md"
            source_path.write_text(synthetic_markdown(2), encoding="utf-8")
            manifest_path = manifest_dir / "conversations.jsonl"
            manifest_path.write_text(
                json.dumps(
                    {
                        "conversation_id": "synthetic-relative",
                        "title": "Synthetic Relative",
                        "normalized_path": "../normalized/synthetic-relative.md",
                        "source_hash": "synthetic-relative-hash",
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            plan = context_chunker.plan_manifest(manifest_path, temp_root / "chunks", profile="small-model")[0]

            self.assertEqual(os.fspath(source_path), plan["source_path"])
            self.assertTrue(Path(pass_by_name(plan, "pass_A")["chunks"][0]["path"]).is_file())

    def test_stable_chunk_ids_are_deterministic_across_runs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            manifest = write_manifest_for_markdown(temp_root, "synthetic-stable", synthetic_markdown(5))
            first_out = temp_root / "first"
            second_out = temp_root / "second"

            first_plan = context_chunker.plan_manifest(
                manifest,
                first_out,
                profile="small-model-offset",
                target_chars=180,
            )[0]
            second_plan = context_chunker.plan_manifest(
                manifest,
                second_out,
                profile="small-model-offset",
                target_chars=180,
            )[0]

            first_ids = [
                (pass_row["name"], chunk["chunk_id"], chunk["turn_start"], chunk["turn_end"])
                for pass_row in first_plan["passes"]
                for chunk in pass_row["chunks"]
            ]
            second_ids = [
                (pass_row["name"], chunk["chunk_id"], chunk["turn_start"], chunk["turn_end"])
                for pass_row in second_plan["passes"]
                for chunk in pass_row["chunks"]
            ]
            self.assertEqual(first_ids, second_ids)

    def test_offset_pass_boundaries_differ_when_enough_turns_exist(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            manifest = write_manifest_for_markdown(temp_root, "synthetic-offset", synthetic_markdown(5))
            out_dir = temp_root / "chunks"

            plan = context_chunker.plan_manifest(
                manifest,
                out_dir,
                profile="small-model-offset",
                target_chars=12000,
                offset_turns=1,
            )[0]

            first_a = pass_by_name(plan, "pass_A")["chunks"][0]
            first_b = pass_by_name(plan, "pass_B_offset")["chunks"][0]
            self.assertEqual((1, 5), (first_a["turn_start"], first_a["turn_end"]))
            self.assertEqual((2, 5), (first_b["turn_start"], first_b["turn_end"]))

    def test_oversized_single_turn_is_marked_instead_of_split(self):
        long_text = "synthetic oversized content " * 40
        markdown = synthetic_markdown(1, extra_text=long_text)
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            manifest = write_manifest_for_markdown(temp_root, "synthetic-oversized", markdown)
            out_dir = temp_root / "chunks"

            plan = context_chunker.plan_manifest(manifest, out_dir, profile="small-model", target_chars=100)[0]

            chunks = pass_by_name(plan, "pass_A")["chunks"]
            self.assertEqual(1, len(chunks))
            self.assertTrue(chunks[0]["oversized"])
            self.assertGreater(chunks[0]["char_count"], 100)
            chunk_text = Path(chunks[0]["path"]).read_text(encoding="utf-8")
            self.assertIn("Oversized: true", chunk_text)
            self.assertEqual(1, chunk_text.count("### Turn 0001"))
            self.assertNotIn("### Turn 0002", chunk_text)

    def test_main_cli_writes_chunk_plan(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            manifest = ingest_fixture(temp_root)
            out_dir = temp_root / "chunks"

            exit_code = context_chunker.main(
                [
                    "--manifest",
                    os.fspath(manifest),
                    "--out-dir",
                    os.fspath(out_dir),
                    "--profile",
                    "small-model-offset",
                ]
            )

            self.assertEqual(0, exit_code)
            self.assertTrue(next(out_dir.glob("*/chunk_plan.json")).is_file())

    def test_fixture_contains_only_tiny_synthetic_data(self):
        fixture_text = (FIXTURE_DIR / "conversations.json").read_text(encoding="utf-8")

        self.assertIn("Synthetic Export Fixture", fixture_text)
        self.assertIn("synthetic", fixture_text.lower())
        self.assertNotIn("@", fixture_text)
        self.assertLess(len(fixture_text), 6000)


if __name__ == "__main__":
    unittest.main()
