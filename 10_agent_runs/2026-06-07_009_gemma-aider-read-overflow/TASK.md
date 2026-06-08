# Local Agent Task

Measure the current read-context limit for the `gemma-local` Aider wrapper.

The manager goal is to verify that a task with one tiny editable file and several real repo `--read` inputs now exceeds the current single-shot preflight budget.

If the run is blocked, preserve that as a negative example before changing the wrapper.
