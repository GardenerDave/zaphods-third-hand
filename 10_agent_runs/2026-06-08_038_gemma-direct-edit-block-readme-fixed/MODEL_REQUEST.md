# Model Request

- In `local_harness/README.md`, replace the block from `- Without prewarm, the same tiny one-file run may burn multiple transient retries before succeeding.` through `- Runs launched inside the sandbox can look like provider failures even when the same run succeeds immediately outside the sandbox.` with `- Without prewarm, the same tiny one-file run may burn multiple transient retries before succeeding.
- The wrapper can now rerun Aider once automatically after a pure connection-retry failure with no edits, preserving attempt-by-attempt artifacts.
- Deterministic block replacement is now manager-routable when both block anchors are unique.
- Runs launched inside the sandbox can look like provider failures even when the same run succeeds immediately outside the sandbox.`.
- Edit only the listed file.
