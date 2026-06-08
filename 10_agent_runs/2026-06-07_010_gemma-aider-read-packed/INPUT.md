# Input Bundle

- Editable file: `10_agent_runs/2026-06-07_010_gemma-aider-read-packed/TARGET.md`
- Read-only files:
  - `local_harness/run_aider_worker.py`
  - `local_harness/run_single_worker.py`
  - `local_harness/icm_call.py`
  - `local_harness/README.md`
  - `XX_backend/validate_agent_run.py`
  - `10_agent_runs/README.md`

This mirrors the earlier six-read overflow probe, but uses the updated wrapper that can shrink read snippets to fit the budget.
