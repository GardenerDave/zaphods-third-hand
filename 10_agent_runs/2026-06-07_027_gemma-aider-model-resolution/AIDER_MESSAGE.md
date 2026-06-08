Task:
- # Model Request
- Implement actual-model resolution for OpenAI-style local model aliases in `icm_call.py`.
Requirements:
- In `local_harness/icm_call.py`, when the effective model looks like an OpenAI-style alias such as `openai/gemma4` and an OpenAI-compatible base URL is set, query `<base>/models` before the main worker request.
- If the endpoint returns one or more model ids, replace the alias with the first discovered actual model id for the outgoing worker call.
- Preserve explicit non-alias model values as-is.
- If model discovery fails, keep the original configured model and continue without crashing.
- Record enough response metadata to show the configured model and the resolved model actually used for the request.
- Add or update tests in `local_harness/tests/test_icm_call.py` for successful resolution, failure fallback, and explicit-model no-op behavior.
Editable files:
- local_harness/icm_call.py
- local_harness/tests/test_icm_call.py
Gemma local rules:
- Edit only the listed files.
- Do not narrate plan or analysis.
- Return only valid Aider edits.
