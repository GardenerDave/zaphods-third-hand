# Local Agent Task

Use the split Gemma-local Aider path on a real code task instead of synthetic markdown targets.

Target behavior:
- Accept comma-separated token counts in Aider output summaries, such as `Tokens: 1,200 sent, 345 received.`
- Preserve existing `k`-suffix parsing.
- Add or update focused tests on the split runtime test surface.
