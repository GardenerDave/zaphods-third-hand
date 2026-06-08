Implement a narrow harness improvement in this repository.

Goal:
- Add a new manager-side helper script `local_harness/run_aider_worker.py`.

Requirements:
- Follow the existing style of `local_harness/run_single_worker.py`.
- The script should execute one supervised Aider run into the documented single-worker run-folder shape.
- It should accept a run folder, scaffold missing audit files with `--init-stubs`, read the Aider prompt from `MODEL_REQUEST.md`, and write command output to `OUTPUT.md`.
- It should write `METRICS.json` with at least timestamp, run folder, command, exit code, elapsed seconds, selected files, and error if any.
- It should create or preserve `REVIEW.md` and `ACCEPTED.md` stubs.
- It should call repo-local Aider through `_aider-chat/bin/python -m aider`.
- It should support CLI overrides for `--model`, `--openai-api-base`, `--map-tokens`, and file targets to edit.
- Keep the command non-destructive: no auto-commits, no dirty commits.
- Update `local_harness/README.md` with one focused example using the new wrapper.
- Add tests that mock subprocess execution rather than calling Aider for real.

Files you may edit:
- `local_harness/README.md`
- `local_harness/tests/test_run_single_worker.py`
- new `local_harness/run_aider_worker.py`
- new test file if needed

Do not edit unrelated files.
