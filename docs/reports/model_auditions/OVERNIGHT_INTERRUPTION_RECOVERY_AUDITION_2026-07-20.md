# Overnight Interruption Recovery Audition, 2026-07-20

Source commit: `60fcd3c18b8b74ff87c37063cea6b7081a21f97e`

Isolated repository: `/tmp/zth-audition-mini`

The supervised interruption-recovery audition passed. The controller preserved the interrupted evidence, recovered the unfinished stage in a distinct linked attempt, completed validation, and closed the queue exactly once.

Observed execution facts:

- First tick exit code: `75`
- Model-call count: `1`, then `1`
- Interrupted run directory: `20260720_040133_487736-worker-loop-001-roadmap-grounding-01`
- Recovered run directory: `20260720_040149_023113-worker-loop-001-roadmap-grounding-01`
- Prior lifecycle state: `model_output_captured`
- Recovery next-attempt number: `2`
- Queue hash: `6f21d92fd2d4a6eaa56b2d8a6634fa5a9383793d4c5031ce6577e743581960b1`
- Fixture hash: `a572ae7132bc6ed922f776fc3c8eb9a4256f529b0ace94504e6fbdb8468f83d9`

Interrupted-directory hashes before and after recovery:

- `model_output.raw.1.json`: `6b685280f66297f2ab460d8e57a6f8a5b6dd41cc3a488e17de5d99fc1973b55e`
- `stage_manifest.json`: `ed3b650a9bb3da3e7bd1429e83b2bcfe57aa1ece0a99a0eda31884c79efd2dad`
- `stage_packet.md`: `136f6717b641f18a4c851c795830f8293b9b5e3b8abbc7dab872404029e05a51`

Final status:

- queue total: `1`
- attempted: `1`
- ready for review: `1`
- semantic failures: `0`
- blocked: `0`
- remaining: `0`
- queue exhausted: `true`
- terminal consistency: `true`

The initial fixture-construction mistakes were in the temp test harness, not the controller: one malformed nested fixture payload and one isolated-copy omission of `docs/ROADMAP.md` caused false negative recovery attempts until corrected. A direct-wrapper import defect in `scripts/validate_dogfood_batch_artifacts.py` also surfaced while executing the wrapper outside the repository working directory and was fixed by adding the repo-root `sys.path` bootstrap. Those issues were test-environment and wrapper-path problems, not failures of the controller recovery logic itself.

Do not infer a live endpoint test from this run. No live endpoint was tested.

Preserved note:

> The supervised interruption-recovery audition passed. The controller preserved the interrupted evidence, recovered the unfinished stage in a distinct linked attempt, completed validation, and closed the queue exactly once.

## Verification

- `python3 -m py_compile scripts/validate_dogfood_batch_artifacts.py scripts/validate_overnight_dogfood_artifacts.py`
- `python3 -m pytest tests/test_long_duration_dogfood_scripts.py tests/test_validate_dogfood_batch_artifacts.py tests/test_validate_overnight_dogfood_artifacts.py -q`
- `git diff --check`

## Closeout

This report preserves the successful supervised interruption-recovery result without claiming any live endpoint validation.
