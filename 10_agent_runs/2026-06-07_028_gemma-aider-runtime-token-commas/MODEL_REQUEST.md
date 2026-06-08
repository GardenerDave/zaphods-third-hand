# Model Request

- Update `parse_token_count()` so it also accepts comma-separated numeric token counts.
- Keep current behavior for plain integers and `k` suffix values.
- Add a focused test in `test_aider_runtime.py` that proves `Tokens: 1,200 sent, 345 received.` is parsed into `1200` and `345`.
- Edit only the listed files.
