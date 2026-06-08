Task:
- # Model Request
- In `local_harness/icm_parsers.py`, reduce duplication by introducing one helper that builds the standard parse-error `WorkerResponse` object used by both OpenAI parser functions.
- Keep behavior exactly the same for status, content text shape, usage/timings passthrough, and error field.
- Update `local_harness/tests/test_icm_call.py` with one focused assertion that still validates parse-error status and error string for malformed OpenAI chat responses.
- Edit only the listed files.
Editable files:
- local_harness/icm_parsers.py
- local_harness/tests/test_icm_call.py
Gemma local rules:
- Edit only the listed files.
- Do not narrate plan or analysis.
- Return only valid Aider edits.
