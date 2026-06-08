# Direct Edit Shortcut

[direct-edit fallback]
Applied deterministic block replacement in local_harness/README.md
- start: `- Without prewarm, the same tiny one-file run may burn multiple transient retries before succeeding.`
- end: `- Runs launched inside the sandbox can look like provider failures even when the same run succeeds immediately outside the sandbox.`
- replacement: `- Without prewarm, the same tiny one-file run may burn multiple transient retries before succeeding.
- The wrapper can now rerun Aider once automatically after a pure connection-retry failure with no edits, preserving attempt-by-attempt artifacts.
- Deterministic block replacement is now manager-routable when both block anchors are unique.
- Runs launched inside the sandbox can look like provider failures even when the same run succeeds immediately outside the sandbox.`
