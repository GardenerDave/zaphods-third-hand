# Accepted Output

- Accepted finding: mixed excerpt-plus-literal batches are now live-proven through the manager-side direct-edit short-circuit.
- Accepted implementation note: the current mixed route uses the excerpt prompt budget, respects the selected-file ceiling, and can still bypass the Aider budget gate when direct-edit eligibility is already known.
- Accepted workflow rule: authored literal prompt text may use escaped newline/tab/carriage-return sequences inside backticks for direct-edit replace/insert/block operations.
