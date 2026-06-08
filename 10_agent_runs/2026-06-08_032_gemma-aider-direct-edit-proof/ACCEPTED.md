# Accepted Output

- Accepted finding: on this endpoint, a one-file real-code Aider run can still stall after dispatch while the manager-side direct-edit fallback completes the requested deterministic change successfully.
- Accepted operating rule: for one-file deterministic replacements that fit the fallback envelope, treat timeout-shaped Aider failure as recoverable rather than terminal.
- Accepted implementation note: the fallback was proven on `local_harness/tests/test_aider_runtime.py` with a unique literal replacement and preserved passing tests.
