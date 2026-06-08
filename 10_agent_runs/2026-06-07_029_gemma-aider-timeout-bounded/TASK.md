# Local Agent Task

Validate the new manager-side subprocess timeout handling on the same real two-file Aider surface.

Target behavior:
- Use the same code task shape as the runtime token-count probe.
- Keep the run bounded with a shorter model timeout and no manager rerun.
- Confirm the wrapper exits cleanly and records timeout failure state without manual intervention.
