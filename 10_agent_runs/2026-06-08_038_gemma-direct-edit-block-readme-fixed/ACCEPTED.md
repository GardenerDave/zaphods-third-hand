# Accepted Output

- Accepted finding: deterministic block replacement is now live-proven on a real one-file repo task through the manager-side direct-edit short-circuit.
- Accepted implementation note: the current deterministic manager envelope includes unique literal replacement, unique-anchor insertion, and unique-anchor block replacement with `prompt_char_limit: 1200` and `file_size_limit_bytes: 16384`.
- Accepted workflow rule: prefer the short-circuit path for eligible one-file block rewrites instead of sending them through whole-file Aider.
