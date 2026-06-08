# Accepted Output

- Accepted finding: mixed excerpt-plus-literal routing needs literal escape decoding for authored prompts that express line breaks as `\n`.
- Accepted next move: teach literal direct-edit parsing to decode escaped newline, tab, and carriage-return sequences, then rerun the same prompt unchanged.
