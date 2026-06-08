# XX Backend

This folder contains small backend utilities for ICM workflow support.

## Local-Agent Run Validator

`validate_agent_run.py` checks whether a single-worker local-agent run folder contains the required promoted-artifact shape:

```text
TASK.md
INPUT.md
MODEL_REQUEST.md
OUTPUT.md
REVIEW.md
METRICS.json
ACCEPTED.md
```

The validator checks file presence only. It does not read raw worker `OUTPUT.md` content.

Usage:

```text
python3 validate_agent_run.py <run-folder>
```

Exit codes:

- `0`: all required files are present.
- `1`: the path is invalid or one or more required files are missing.

Run tests from this folder:

```text
python3 -m unittest discover -s tests
```
