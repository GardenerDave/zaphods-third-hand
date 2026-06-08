# Local Agent Task

Validate the new direct-edit fallback on a real one-file code task after the Aider path stalls.

Target behavior:
- Run the bounded Gemma-local Aider wrapper on one real code file that is eligible for deterministic fallback.
- Confirm that the wrapper times out or stalls on the Aider path, then applies the direct-edit fallback successfully.
- Preserve test correctness after the edit.
