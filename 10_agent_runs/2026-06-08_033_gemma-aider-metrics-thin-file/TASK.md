# Local Agent Task

Measure whether the smaller split runtime surface is now small enough for a one-file real-code Aider edit to complete without relying on the direct-edit fallback.

Target behavior:
- Run a bounded Gemma-local Aider task on `local_harness/aider_metrics.py`.
- Use a prompt shape that does not match the deterministic direct-edit fallback parser.
- Confirm whether Aider itself can complete the code edit on this smaller file.
