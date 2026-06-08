# Local Agent Task

Validate that eligible deterministic one-file requests now bypass prewarm and Aider entirely through the direct-edit short-circuit path.

Target behavior:
- Use a one-file real repo code task that fits the direct-edit shortcut envelope.
- Confirm that no Aider subprocess is launched.
- Confirm that the requested edit is applied and repo tests still pass.
