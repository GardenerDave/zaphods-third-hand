# Manager Review

- Status: reviewed
- Real excerpt-patch probe targeted `local_harness/README.md` with a two-hunk SEARCH/REPLACE set.
- Preflight reported `prompt_char_count: 1620`, `prompt_char_limit: 1200`, `reason: prompt_too_long`, and no direct-edit eligibility under the old shared cap.
- The wrapper therefore fell through to whole-file Aider, prewarm succeeded, and the child process still exited only through manager timeout (`exit_code: 124`, `manager_timeout_detected: true`).
- Accepted finding: the excerpt patch grammar is useful, but the old shared `1200`-character deterministic prompt cap was too low for a practical two-hunk real-file patch.
