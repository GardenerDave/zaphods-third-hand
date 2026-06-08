# Accepted Output

- No worker output accepted from this run.
- Accepted finding: block replacement did not fail on logic or anchor matching; it failed because the deterministic manager prompt cap of `600` characters was too low.
- Accepted routing lesson: when direct-edit preflight says `prompt_too_long`, the wrapper will fall through to unstable whole-file Aider unless the deterministic envelope is widened.
