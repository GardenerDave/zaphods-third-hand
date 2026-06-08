# Local Agent Task

## Task
- Task ID: 2026-06-07_004_aider-worker-wrapper
- Assigned model: openai/gemma4 via Aider v0.86.2
- Role: code worker under manager supervision
- Objective: add a dedicated manager-side Aider worker wrapper for the sanitized harness bundle

## Inputs
- `local_harness/run_single_worker.py`
- `local_harness/README.md`
- `local_harness/tests/test_run_single_worker.py`
- `03_workflows/LOCAL_AGENT_ORCHESTRATION_WORKFLOW.md`
- `10_agent_runs/README.md`

## Required outputs
- New script `local_harness/run_aider_worker.py`
- README updates for Aider usage
- Tests for the new wrapper

## Constraints
- Keep the change narrow and local to the harness/tooling bundle.
- Reuse the existing single-worker run shape and review model where practical.
- Do not add dependencies.
- Do not modify unrelated workflow docs.
- Do not commit.

## Acceptance criteria
- Aider can be invoked through a dedicated wrapper script rather than a raw shell command.
- The wrapper writes auditable run artifacts compatible with this repo's local-agent workflow.
- README usage reflects the new wrapper.
- Tests cover the wrapper with mocked subprocess behavior.
