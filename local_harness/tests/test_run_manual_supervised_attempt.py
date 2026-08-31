from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from local_harness.run_manual_supervised_attempt import run_prepare


class RunManualSupervisedAttemptTests(unittest.TestCase):
    def test_evidence_prompt_includes_prompt_patch_delta_when_selected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            evidence_a = root / "evidence_a.md"
            evidence_b = root / "evidence_b.md"
            evidence_a.write_text("alpha\n", encoding="utf-8")
            evidence_b.write_text("beta\n", encoding="utf-8")

            baseline = run_prepare(
                messy_input="Does transport qualification prove model capability?",
                out_dir=root / "baseline",
                timestamp="20260831T140000Z",
                overwrite=True,
                exclude_prompt_patches=["unsupported_certainty_v1"],
                evidence_files=[evidence_a, evidence_b],
                evidence_task_title="Task A",
                evidence_task_summary="Transport qualification versus model capability.",
            )
            patched = run_prepare(
                messy_input="Does transport qualification prove model capability?",
                out_dir=root / "patched",
                timestamp="20260831T140000Z",
                overwrite=True,
                include_prompt_patches=["unsupported_certainty_v1"],
                evidence_files=[evidence_a, evidence_b],
                evidence_task_title="Task A",
                evidence_task_summary="Transport qualification versus model capability.",
            )

            baseline_prompt = Path(baseline["prompt_to_paste_path"]).read_text(encoding="utf-8")
            patched_prompt = Path(patched["prompt_to_paste_path"]).read_text(encoding="utf-8")

        self.assertNotEqual(
            hashlib.sha256(baseline_prompt.encode("utf-8")).hexdigest(),
            hashlib.sha256(patched_prompt.encode("utf-8")).hexdigest(),
        )
        self.assertNotIn("unsupported_certainty_v1", baseline_prompt)
        self.assertIn("unsupported_certainty_v1", patched_prompt)


if __name__ == "__main__":
    unittest.main()
