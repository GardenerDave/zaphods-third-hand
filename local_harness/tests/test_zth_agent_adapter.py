import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


sys.path.insert(0, os.fspath(Path(__file__).resolve().parents[1]))

import zth_agent_packet
import zth_compare_agent_outputs


SAMPLE_OUTPUT_ONE = """# Agent One

## Decision

Needs rework

## Summary

Found one missing edge case.

## Files Inspected

- README.md
- local_harness/README.md

## Files Changed

- None

## Commands Run

- python3 -m pytest local_harness/tests

## Evidence

- Tests pass.

## Assumptions

- Endpoint docs are in scope.

## Risks

- Timeout behavior remains model-dependent.

## Confidence

medium

## Suggested Next Step

Add one focused timeout note.
"""


SAMPLE_OUTPUT_TWO = """# Agent Two

## Decision

Needs rework

## Summary

Docs should mention local endpoint variance.

## Files Inspected

- README.md
- docs/FIRST_SUCCESS.md

## Files Changed

- docs/FIRST_SUCCESS.md

## Commands Run

- python3 -m pytest local_harness/tests

## Evidence

- Endpoint setup is documented.

## Assumptions

- No live endpoint is required for tests.

## Risks

- Model aliases can be mismatched.

## Confidence

high

## Suggested Next Step

Add one focused timeout note.
"""


class ZthAgentPacketTests(unittest.TestCase):
    def test_packet_generation_validates_modes(self):
        with self.assertRaises(ValueError):
            zth_agent_packet.render_packet(
                task="Evaluate docs",
                role="correctness",
                mode="invalid",
                scope="docs",
            )

    def test_packet_generation_includes_required_sections_and_independence_rule(self):
        packet = zth_agent_packet.render_packet(
            task="Evaluate parser refactor",
            role="correctness",
            mode="standard",
            scope="local_harness docs",
            files=["README.md", "local_harness/README.md"],
            constraints=["No network calls"],
            acceptance=["Existing tests pass"],
            commands=["python3 -m pytest local_harness/tests"],
            risks=["Parser behavior drift"],
            do_not_touch=["outputs/"],
        )

        for heading in (
            "## Task",
            "## Role",
            "## Mode",
            "## Repo Scope",
            "## Relevant Files",
            "## Required Output Contract",
            "## Independence Rule",
        ):
            self.assertIn(heading, packet)
        self.assertIn("one independent external agent", packet)
        self.assertIn("Do not include, rely on, or react to another", packet)
        self.assertIn("agent's conclusions before synthesis/comparison", packet)
        self.assertIn("- README.md", packet)

    def test_packet_cli_stdout_and_output_paths_work(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "packet.md"
            exit_code = zth_agent_packet.main(
                [
                    "--task",
                    "Evaluate docs",
                    "--role",
                    "documentation verifier",
                    "--mode",
                    "quick",
                    "--scope",
                    "docs",
                    "--files",
                    "README.md",
                    "--output",
                    os.fspath(output_path),
                ]
            )
            self.assertEqual(0, exit_code)
            self.assertIn("## Task", output_path.read_text(encoding="utf-8"))

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = zth_agent_packet.main(
                [
                    "--task",
                    "Evaluate docs",
                    "--role",
                    "documentation verifier",
                    "--mode",
                    "quick",
                    "--scope",
                    "docs",
                ]
            )

        self.assertEqual(0, exit_code)
        self.assertIn("# ZTH Agent Role Packet", stdout.getvalue())


class ZthCompareAgentOutputsTests(unittest.TestCase):
    def test_compare_detects_missing_required_sections(self):
        output = zth_compare_agent_outputs.AgentOutput(
            path=Path("agent.md"),
            sections=zth_compare_agent_outputs.parse_sections("## Decision\n\nAccepted\n"),
        )

        missing = zth_compare_agent_outputs.missing_sections(output)

        self.assertIn("Summary", missing)
        self.assertIn("Files inspected", missing)

    def test_compare_reports_files_commands_and_risks_from_two_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            first = Path(temp_dir) / "agent1.md"
            second = Path(temp_dir) / "agent2.md"
            first.write_text(SAMPLE_OUTPUT_ONE, encoding="utf-8")
            second.write_text(SAMPLE_OUTPUT_TWO, encoding="utf-8")

            outputs = [
                zth_compare_agent_outputs.load_agent_output(first),
                zth_compare_agent_outputs.load_agent_output(second),
            ]
            report = zth_compare_agent_outputs.render_comparison(outputs)

        self.assertIn("README.md", report)
        self.assertIn("docs/FIRST_SUCCESS.md", report)
        self.assertIn("python3 -m pytest local_harness/tests", report)
        self.assertIn("Timeout behavior remains model-dependent.", report)
        self.assertIn("Model aliases can be mismatched.", report)
        self.assertIn("All agents reported decision: Needs rework", report)

    def test_compare_cli_stdout_and_output_paths_work(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            first = Path(temp_dir) / "agent1.md"
            second = Path(temp_dir) / "agent2.md"
            output_path = Path(temp_dir) / "comparison.md"
            first.write_text(SAMPLE_OUTPUT_ONE, encoding="utf-8")
            second.write_text(SAMPLE_OUTPUT_TWO, encoding="utf-8")

            exit_code = zth_compare_agent_outputs.main(
                [os.fspath(first), os.fspath(second), "--output", os.fspath(output_path)]
            )
            self.assertEqual(0, exit_code)
            self.assertIn("# ZTH Agent Output Comparison", output_path.read_text(encoding="utf-8"))

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = zth_compare_agent_outputs.main([os.fspath(first), os.fspath(second)])

        self.assertEqual(0, exit_code)
        self.assertIn("## Agreements", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
