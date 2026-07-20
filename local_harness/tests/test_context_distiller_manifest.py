import json
import tempfile
import unittest
import subprocess
from pathlib import Path

import os
import sys

sys.path.insert(0, os.fspath(Path(__file__).resolve().parents[1]))

import context_distiller_manifest


def write_source(root: Path, name: str, text: str) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def base_manifest(source_path: Path, *, profile: str = "comprehensive", source_id: str = "sample-source") -> dict[str, object]:
    return {
        "schema": 1,
        "source_id": source_id,
        "inputs": {
            "sources": [os.fspath(source_path)],
            "include_globs": [],
            "exclude_globs": [],
            "line_ranges": [],
            "chunk_indices": [],
        },
        "chunking": {
            "target_chars": 32,
            "overlap": 1,
            "offset": 1,
            "start_chunk": None,
            "end_chunk": None,
        },
        "passes": [
            {
                "id": "comprehensive",
                "profile": profile,
                "questions": [],
                "inputs_from_passes": [],
                "output": {"artifact_type": "review_bundle", "filename": "review.md"},
            }
        ],
        "synthesis": {
            "enabled": False,
            "input_passes": [],
            "profile": "synthesis",
            "output": {"artifact_type": "review_bundle", "filename": "review.md"},
        },
    }


class FakeModelRunner:
    def __init__(self, outputs: list[dict[str, object]]):
        self.outputs = outputs
        self.calls: list[dict[str, str]] = []

    def __call__(self, prompt_path: Path, metadata_out: Path) -> dict[str, object]:
        self.calls.append(
            {
                "prompt": prompt_path.read_text(encoding="utf-8"),
                "metadata_out": os.fspath(metadata_out),
            }
        )
        metadata_out.write_text(json.dumps({"call": len(self.calls)}), encoding="utf-8")
        return self.outputs[len(self.calls) - 1]


def review_payload(*, verdict: str = "pass", review_state: str = "complete", notes: str = "ok") -> dict[str, object]:
    return {
        "verdict": verdict,
        "review_state": review_state,
        "changed_paths": [],
        "verification": {
            "raw_output_structure": "pass",
            "changed_files_against_allowlist": "not_applicable",
            "narrowest_relevant_local_checks": "not_run",
        },
        "evidence": [
            {
                "path": "docs/README.md",
                "observation": "Repository-relative evidence is present.",
                "existence": "present",
            }
        ],
        "notes": notes,
    }


class ContextDistillerManifestTests(unittest.TestCase):
    def test_plan_only_and_legacy_compatibility_share_planning_facts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            repo_like = temp_root / "repo"
            repo_like.mkdir()
            source = write_source(repo_like, "notes/source.md", "# hello\nworld\n")
            manifest = {
                "schema": 1,
                "source_id": "sample",
                "inputs": {
                    "sources": ["notes/source.md"],
                    "include_globs": [],
                    "exclude_globs": [],
                    "line_ranges": [],
                    "chunk_indices": [],
                },
                "chunking": dict(context_distiller_manifest.DEFAULT_CHUNKING),
                "passes": [
                    {
                        "id": "comprehensive",
                        "profile": "comprehensive",
                        "questions": [],
                        "inputs_from_passes": [],
                        "output": {"artifact_type": "review_bundle", "filename": "review.md"},
                    }
                ],
                "synthesis": {
                    "enabled": False,
                    "input_passes": [],
                    "profile": "synthesis",
                    "output": {"artifact_type": "review_bundle", "filename": "review.md"},
                },
            }
            explicit = context_distiller_manifest.render_plan(manifest, repo_root=repo_like)
            legacy = context_distiller_manifest.render_plan(
                context_distiller_manifest.build_legacy_manifest("sample", "notes/source.md", "review"),
                repo_root=repo_like,
            )
            self.assertEqual(explicit["selected_source_hashes"], legacy["selected_source_hashes"])
            self.assertEqual(explicit["passes"][0]["profile"], legacy["passes"][0]["profile"])
            self.assertEqual(explicit["passes"][0]["expected_output_path"], legacy["passes"][0]["expected_output_path"])

    def test_manifest_validation_rejects_missing_schema_and_unsafe_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            repo_like = temp_root / "repo"
            repo_like.mkdir()
            write_source(repo_like, "notes/source.md", "one\ntwo\n")
            manifest = {
                "source_id": "sample",
                "inputs": {"sources": ["notes/source.md"], "include_globs": [], "exclude_globs": [], "line_ranges": [], "chunk_indices": []},
                "chunking": dict(context_distiller_manifest.DEFAULT_CHUNKING),
                "passes": [],
                "synthesis": {"enabled": False, "input_passes": [], "profile": "synthesis", "output": {"artifact_type": "review_bundle", "filename": "review.md"}},
            }
            with self.assertRaisesRegex(context_distiller_manifest.DistillerManifestError, "unsupported manifest schema"):
                context_distiller_manifest.validate_manifest(manifest, repo_root=repo_like)
            manifest["schema"] = 1
            manifest["inputs"]["sources"] = ["/abs/path.txt"]
            with self.assertRaisesRegex(context_distiller_manifest.DistillerManifestError, "unsafe repository-relative path"):
                context_distiller_manifest.validate_manifest(manifest, repo_root=repo_like)

    def test_include_exclude_line_ranges_and_effective_chunk_settings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            repo_like = temp_root / "repo"
            repo_like.mkdir()
            source_a = write_source(repo_like, "notes/a.md", "a1\na2\na3\na4\n")
            source_b = write_source(repo_like, "notes/b.md", "b1\nb2\n")
            manifest = {
                "schema": 1,
                "source_id": "sample",
                "inputs": {
                    "sources": ["notes/a.md", "notes/b.md"],
                    "include_globs": ["notes/*.md"],
                    "exclude_globs": ["notes/b.md"],
                    "line_ranges": [[2, 3]],
                    "chunk_indices": [],
                },
                "chunking": {"target_chars": 4, "overlap": 0, "offset": 1, "start_chunk": 1, "end_chunk": 1},
                "passes": [
                    {"id": "comprehensive", "profile": "comprehensive", "questions": [], "inputs_from_passes": [], "output": {"artifact_type": "review_bundle", "filename": "review.md"}}
                ],
                "synthesis": {"enabled": False, "input_passes": [], "profile": "synthesis", "output": {"artifact_type": "review_bundle", "filename": "review.md"}},
            }
            plan = context_distiller_manifest.render_plan(manifest, repo_root=repo_like)
            self.assertEqual(["notes/a.md"], [item["source"] for item in plan["source_manifest"]["selected_sources"]])
            self.assertEqual(4, plan["chunking"]["target_chars"])
            self.assertEqual([[2, 3]], plan["source_manifest"]["selection"]["line_ranges"])
            self.assertEqual("passes/comprehensive/attempt_001/review.md", plan["passes"][0]["expected_output_path"])

    def test_duplicate_pass_ids_missing_dependency_cycle_and_collision_fail(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            repo_like = temp_root / "repo"
            repo_like.mkdir()
            write_source(repo_like, "notes/source.md", "one\ntwo\n")
            manifest = {
                "schema": 1,
                "source_id": "sample",
                "inputs": {"sources": ["notes/source.md"], "include_globs": [], "exclude_globs": [], "line_ranges": [], "chunk_indices": []},
                "chunking": dict(context_distiller_manifest.DEFAULT_CHUNKING),
                "passes": [
                    {"id": "a", "profile": "comprehensive", "questions": [], "inputs_from_passes": [], "output": {"artifact_type": "review_bundle", "filename": "a.md"}},
                    {"id": "a", "profile": "architecture", "questions": [], "inputs_from_passes": [], "output": {"artifact_type": "review_bundle", "filename": "b.md"}},
                ],
                "synthesis": {"enabled": False, "input_passes": [], "profile": "synthesis", "output": {"artifact_type": "review_bundle", "filename": "review.md"}},
            }
            with self.assertRaisesRegex(context_distiller_manifest.DistillerManifestError, "duplicate pass id"):
                context_distiller_manifest.validate_manifest(manifest, repo_root=repo_like)

            manifest["passes"] = [
                {"id": "a", "profile": "comprehensive", "questions": [], "inputs_from_passes": ["b"], "output": {"artifact_type": "review_bundle", "filename": "a.md"}},
                {"id": "b", "profile": "architecture", "questions": [], "inputs_from_passes": ["a"], "output": {"artifact_type": "review_bundle", "filename": "b.md"}},
            ]
            with self.assertRaisesRegex(context_distiller_manifest.DistillerManifestError, "dependency cycle detected"):
                context_distiller_manifest.validate_manifest(manifest, repo_root=repo_like)

    def test_plan_only_makes_no_model_call_and_validates_output_contract(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            repo_like = temp_root / "repo"
            repo_like.mkdir()
            write_source(repo_like, "notes/source.md", "one\ntwo\n")
            manifest = {
                "schema": 1,
                "source_id": "sample",
                "inputs": {"sources": ["notes/source.md"], "include_globs": [], "exclude_globs": [], "line_ranges": [], "chunk_indices": []},
                "chunking": dict(context_distiller_manifest.DEFAULT_CHUNKING),
                "passes": [
                    {"id": "comprehensive", "profile": "comprehensive", "questions": [], "inputs_from_passes": [], "output": {"artifact_type": "review_bundle", "filename": "review.md"}}
                ],
                "synthesis": {"enabled": False, "input_passes": [], "profile": "synthesis", "output": {"artifact_type": "review_bundle", "filename": "review.md"}},
            }
            fake = FakeModelRunner([review_payload()])
            result = context_distiller_manifest.run_manifest_job(
                manifest,
                out_root=temp_root / "out",
                repo_root=repo_like,
                model_runner=fake,
                plan_only=True,
            )
            self.assertEqual([], fake.calls)
            self.assertEqual("planned", result["status"]["state"])

    def test_independent_focused_prompts_and_synthesis_input_isolation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            repo_like = temp_root / "repo"
            repo_like.mkdir()
            write_source(repo_like, "notes/source.md", "alpha\nbeta\ngamma\ndelta\n")
            manifest = {
                "schema": 1,
                "source_id": "sample",
                "inputs": {"sources": ["notes/source.md"], "include_globs": [], "exclude_globs": [], "line_ranges": [], "chunk_indices": []},
                "chunking": dict(context_distiller_manifest.DEFAULT_CHUNKING),
                "passes": [
                    {"id": "architecture", "profile": "architecture", "questions": [], "inputs_from_passes": [], "output": {"artifact_type": "focused_distillation", "filename": "architecture.md"}},
                    {"id": "decisions", "profile": "decisions", "questions": [], "inputs_from_passes": [], "output": {"artifact_type": "focused_distillation", "filename": "decisions.md"}},
                    {"id": "failures", "profile": "failures-and-corrections", "questions": [], "inputs_from_passes": [], "output": {"artifact_type": "focused_distillation", "filename": "failures.md"}},
                ],
                "synthesis": {
                    "enabled": True,
                    "input_passes": ["architecture", "decisions", "failures"],
                    "profile": "synthesis",
                    "output": {"artifact_type": "review_bundle", "filename": "synthesis.md"},
                },
            }
            fake = FakeModelRunner([review_payload(notes="a"), review_payload(notes="b"), review_payload(notes="c"), review_payload(notes="s")])
            result = context_distiller_manifest.run_manifest_job(manifest, out_root=temp_root / "out", repo_root=repo_like, model_runner=fake)
            self.assertEqual(4, len(fake.calls))
            self.assertNotEqual(fake.calls[0]["prompt"], fake.calls[1]["prompt"])
            self.assertNotEqual(fake.calls[1]["prompt"], fake.calls[2]["prompt"])
            synthesis_prompt = fake.calls[3]["prompt"]
            self.assertIn('"verdict": "pass"', synthesis_prompt)
            self.assertIn("architecture", synthesis_prompt)
            self.assertIn("decisions", synthesis_prompt)
            self.assertIn("failures", synthesis_prompt)
            self.assertTrue((Path(result["job_dir"]) / "review_bundle" / "synthesis.md").is_file())

    def test_source_hash_provenance_and_recovery_attempts_are_linked(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            repo_like = temp_root / "repo"
            repo_like.mkdir()
            write_source(repo_like, "notes/source.md", "alpha\nbeta\n")
            manifest = {
                "schema": 1,
                "source_id": "sample",
                "inputs": {"sources": ["notes/source.md"], "include_globs": [], "exclude_globs": [], "line_ranges": [], "chunk_indices": []},
                "chunking": dict(context_distiller_manifest.DEFAULT_CHUNKING),
                "passes": [
                    {"id": "comprehensive", "profile": "comprehensive", "questions": [], "inputs_from_passes": [], "output": {"artifact_type": "review_bundle", "filename": "review.md"}}
                ],
                "synthesis": {"enabled": False, "input_passes": [], "profile": "synthesis", "output": {"artifact_type": "review_bundle", "filename": "review.md"}},
            }
            out_root = temp_root / "out"
            fake1 = FakeModelRunner([review_payload(notes="one")])
            context_distiller_manifest.run_manifest_job(manifest, out_root=out_root, repo_root=repo_like, model_runner=fake1)
            first_dir = out_root / "context_distiller_sample" / "passes" / "comprehensive" / "attempt_001"
            before = (first_dir / "model_output.raw.json").read_text(encoding="utf-8")
            fake2 = FakeModelRunner([review_payload(notes="two")])
            context_distiller_manifest.run_manifest_job(manifest, out_root=out_root, repo_root=repo_like, model_runner=fake2)
            second_dir = out_root / "context_distiller_sample" / "passes" / "comprehensive" / "attempt_002"
            self.assertTrue((second_dir / "recovery_manifest.json").is_file())
            self.assertEqual(before, (first_dir / "model_output.raw.json").read_text(encoding="utf-8"))
            self.assertEqual(
                json.loads((second_dir / "recovery_manifest.json").read_text(encoding="utf-8"))["prior_directory"],
                os.fspath(first_dir),
            )

    def test_shell_wrapper_runs_from_outside_repo_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            repo_root = Path(__file__).resolve().parents[2]
            repo_temp_dir = tempfile.TemporaryDirectory(dir=repo_root)
            self.addCleanup(repo_temp_dir.cleanup)
            repo_like = Path(repo_temp_dir.name)
            source_path = write_source(repo_like, "notes/source.md", "alpha\nbeta\n")
            source_rel = os.fspath(source_path.relative_to(repo_root))
            manifest = {
                "schema": 1,
                "source_id": "sample",
                "inputs": {"sources": [source_rel], "include_globs": [], "exclude_globs": [], "line_ranges": [], "chunk_indices": []},
                "chunking": dict(context_distiller_manifest.DEFAULT_CHUNKING),
                "passes": [
                    {"id": "comprehensive", "profile": "comprehensive", "questions": [], "inputs_from_passes": [], "output": {"artifact_type": "review_bundle", "filename": "review.md"}}
                ],
                "synthesis": {"enabled": False, "input_passes": [], "profile": "synthesis", "output": {"artifact_type": "review_bundle", "filename": "review.md"}},
            }
            manifest_path = temp_root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            wrapper = Path(__file__).resolve().parents[2] / "scripts" / "run_context_distiller.sh"
            result = subprocess.run(
                ["bash", os.fspath(wrapper), "--manifest", os.fspath(manifest_path), "--plan-only", "--out-root", os.fspath(temp_root / "out")],
                cwd="/tmp",
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn('"source_id": "sample"', result.stdout)

    def test_incomplete_result_is_distinct_from_ready_for_review(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            repo_like = temp_root / "repo"
            repo_like.mkdir()
            write_source(repo_like, "notes/source.md", "alpha\nbeta\n")
            manifest = {
                "schema": 1,
                "source_id": "sample",
                "inputs": {"sources": ["notes/source.md"], "include_globs": [], "exclude_globs": [], "line_ranges": [], "chunk_indices": []},
                "chunking": dict(context_distiller_manifest.DEFAULT_CHUNKING),
                "passes": [
                    {"id": "comprehensive", "profile": "comprehensive", "questions": [], "inputs_from_passes": [], "output": {"artifact_type": "review_bundle", "filename": "review.md"}}
                ],
                "synthesis": {"enabled": False, "input_passes": [], "profile": "synthesis", "output": {"artifact_type": "review_bundle", "filename": "review.md"}},
            }
            fake = FakeModelRunner([review_payload(verdict="incomplete", review_state="incomplete", notes="pending")])
            result = context_distiller_manifest.run_manifest_job(manifest, out_root=temp_root / "out", repo_root=repo_like, model_runner=fake)
            self.assertEqual("blocked", result["status"]["state"])
            self.assertFalse(result["status"]["ready_for_review"])
            validation = json.loads((Path(result["job_dir"]) / "passes" / "comprehensive" / "attempt_001" / "validation.json").read_text(encoding="utf-8"))
            self.assertEqual("incomplete", validation["semantic_state"])


if __name__ == "__main__":
    unittest.main()
