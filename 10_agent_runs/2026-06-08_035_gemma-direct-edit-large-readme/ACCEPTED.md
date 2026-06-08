# Accepted Output

- Accepted finding: deterministic one-file replacements are now live-proven on files up to at least 10507 bytes through the manager-side direct-edit short-circuit.
- Accepted implementation note: the current guardrails are `prompt_char_limit: 600`, `file_size_limit_bytes: 16384`, exact target match, and exactly one unique literal replacement.
- Accepted workflow rule: use the short-circuit path to avoid wasting endpoint and Aider budget when a request fits this deterministic envelope.
