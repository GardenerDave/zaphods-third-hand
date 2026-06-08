# Accepted Artifact

## Finding

Aider is reachable from the copied local environment, but on the current `openai/gemma4` runtime it was not reliable for bounded coding work in this repo during this session.

## Accepted next use

- Keep Aider available as an optional worker path.
- Prefer direct harness scripts or manual implementation when Gemma shows context overflow, planning-only output, or timebox failures.
- Use the new `local_harness/run_aider_worker.py` wrapper for future supervised trials so failed runs still produce auditable artifacts.
