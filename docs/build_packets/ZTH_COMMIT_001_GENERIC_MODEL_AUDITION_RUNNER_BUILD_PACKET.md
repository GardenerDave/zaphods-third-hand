# ZTH Build Packet — Commit 001: Generic Model Audition Runner MVP

## Commit message

```text
Add generic model audition runner
```

## Operator intent

Build only the first stable layer of the ZTH model audition harness.

This commit should prove that a model can be auditioned through a generic, file-driven runner using:

```text
model endpoint + suite config + prompt file + fixture file + scorer profile + output directory
```

This is not a role assignment system yet. It is not a board runner yet. It is not a comparison tool yet. It is the smallest useful harness foundation that can run one suite against one model and produce stable artifacts.

## Hard boundary for this commit

Implement only:

```text
local_harness/run_model_audition.py
local_harness/model_audition_scorers.py
local_harness/tests/test_run_model_audition.py
local_harness/tests/test_model_audition_scorers.py
```

Do not implement:

```text
model registry loading
baseline config pack
multi-suite board runner
cross-model comparison reporting
judge-model scoring
production role assignment
pytest execution of generated code
changes to existing extraction batch runners
changes to active .work outputs
```

Tests must be offline. No live model endpoint may be required.

---

# Build instruction for Codex/Aider

Implement Commit 001 for the Zaphod's Third Hand model audition harness.

Create a generic model audition runner and deterministic scorer primitives. The runner must accept explicit model connection arguments, a suite config, prompt file, fixture JSONL file, scorer profile JSON file, and output directory. It must render prompts, call an OpenAI-compatible `/chat/completions` endpoint through an injectable HTTP/client function, write raw outputs, score each case, write a case manifest, and aggregate a capability card.

Keep the implementation generic. Do not encode coding-specific, routing-specific, extraction-specific, or role-assignment behavior into the runner. Prompt files, fixture files, scorer profiles, and suite config should define the test shape.

All unit tests must use fake client responses or monkeypatch the HTTP call. No live endpoint access is allowed in tests.

---

# Files to add

```text
local_harness/run_model_audition.py
local_harness/model_audition_scorers.py
local_harness/tests/test_run_model_audition.py
local_harness/tests/test_model_audition_scorers.py
```

No other production files should be changed unless needed for import hygiene.

---

# CLI contract

The runner must support this form:

```bash
python3 local_harness/run_model_audition.py \
  --model-id "MODEL_ID" \
  --base-url "http://HOST:PORT/v1" \
  --api-key "not-needed-for-local" \
  --suite "local_harness/auditions/suites/baseline_suite_v0.json" \
  --out-dir ".work/model_auditions/RUN_ID"
```

Required args:

```text
--model-id
--base-url
--suite
--out-dir
```

Optional args:

```text
--api-key
--prompt-file
--fixtures-file
--scorer-profile
--temperature
--max-tokens
--timeout-seconds
--run-id
--dry-run
--limit
--case-id
--resume
```

Override rule:

```text
Suite config provides defaults.
CLI overrides suite config.
Explicit CLI path beats suite path.
```

Path resolution rule:

```text
Relative paths inside suite config are resolved relative to the suite file location.
CLI-provided paths are resolved relative to current working directory.
```

---

# Suite config schema

The runner must load a JSON suite config with at least:

```json
{
  "suite_id": "baseline_suite_v0",
  "prompt_file": "../prompts/json_task_v0.md",
  "fixtures_file": "../fixtures/baseline_micro_v0.jsonl",
  "scorer_profile": "../scorers/json_schema_basic_v0.json",
  "defaults": {
    "temperature": 0,
    "max_tokens": 300,
    "timeout_seconds": 900
  }
}
```

Recommended public function:

```python
def load_suite_config(suite_path: Path) -> dict:
    ...
```

The loaded config should include resolved absolute or normalized paths for prompt, fixtures, and scorer profile, while metadata output may preserve display paths as strings.

---

# Fixture schema

Fixture file is JSONL. Each row is one audition case.

Required fields:

```text
case_id
task_type
input
```

Optional fields:

```text
expected
metadata
expected_schema
tags
```

Example:

```json
{
  "case_id": "route_001",
  "task_type": "classification",
  "input": "User text or task payload goes here.",
  "expected": {
    "label": "hardware"
  },
  "metadata": {
    "difficulty": "micro",
    "domain": "zth"
  }
}
```

Validation behavior:

```text
Fail fast if a JSONL row is invalid JSON.
Fail fast if required fields are missing.
Fail fast if case_id is duplicated.
```

---

# Prompt template contract

Prompt files are plain Markdown.

Commit 001 supports only simple string replacement:

```text
{{case_id}}
{{task_type}}
{{input}}
{{expected_schema}}
{{expected_json}}
```

No Jinja, no conditionals, no loops, no complex templating.

Replacement details:

```text
{{case_id}}        -> fixture["case_id"]
{{task_type}}      -> fixture["task_type"]
{{input}}          -> fixture["input"]
{{expected_schema}} -> JSON dump of fixture.get("expected_schema", {})
{{expected_json}}   -> JSON dump of fixture.get("expected", {})
```

Recommended public function:

```python
def render_prompt(template: str, fixture: dict) -> str:
    ...
```

---

# OpenAI-compatible API call

Use `/chat/completions`.

Request body:

```json
{
  "model": "MODEL_ID",
  "temperature": 0,
  "max_tokens": 300,
  "messages": [
    {
      "role": "user",
      "content": "rendered prompt"
    }
  ]
}
```

Use standard library where practical. If the repo already uses `requests`, using `requests` is acceptable.

The HTTP/client call must be isolated behind a function so tests can inject or monkeypatch it.

Recommended function shape:

```python
def call_chat_completions(
    *,
    base_url: str,
    api_key: str | None,
    model_id: str,
    prompt: str,
    temperature: float,
    max_tokens: int,
    timeout_seconds: int,
) -> dict:
    ...
```

Recommended extraction helper:

```python
def extract_text_from_chat_response(response: dict) -> str:
    ...
```

Expected extraction path:

```text
response["choices"][0]["message"]["content"]
```

If extraction fails, return an empty string and let scoring/manifest capture the failure.

---

# Output directory layout

For each run:

```text
out_dir/
├── run_metadata.json
├── case_manifest.jsonl
├── raw_outputs/
│   └── <case_id>.json
├── rendered_prompts/
│   └── <case_id>.md
├── scores/
│   └── <case_id>.json
├── capability_card.json
└── capability_card.md
```

Filename rule:

```text
Use case_id directly only after validating it is safe for filenames.
Allowed conservative pattern: letters, numbers, underscore, dash, dot.
Reject unsafe case_id values.
```

---

# run_metadata.json

Required fields:

```json
{
  "run_id": "qwen25_3b_baseline_20260618",
  "created_at": "ISO_TIMESTAMP",
  "model_id": "Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M",
  "base_url": "http://192.168.1.13:8082/v1",
  "suite_id": "baseline_suite_v0",
  "suite_file": "local_harness/auditions/suites/baseline_suite_v0.json",
  "prompt_file": "local_harness/auditions/prompts/json_task_v0.md",
  "fixtures_file": "local_harness/auditions/fixtures/baseline_micro_v0.jsonl",
  "scorer_profile": "local_harness/auditions/scorers/json_schema_basic_v0.json",
  "temperature": 0,
  "max_tokens": 300,
  "timeout_seconds": 900,
  "runner": "local_harness/run_model_audition.py"
}
```

`created_at` should be UTC ISO format.

`run_id` behavior:

```text
If --run-id is provided, use it.
Otherwise derive run_id from out_dir name.
```

---

# case_manifest.jsonl

Append one row per case attempted.

Schema:

```json
{
  "case_id": "route_001",
  "task_type": "classification",
  "status": "completed",
  "raw_output_path": "raw_outputs/route_001.json",
  "score_path": "scores/route_001.json",
  "wall_time_seconds": 12.34,
  "error": "",
  "timestamp": "ISO_TIMESTAMP"
}
```

Allowed statuses:

```text
completed
api_error
timeout
scoring_error
skipped_existing
```

Behavior:

```text
completed        -> API/client call succeeded and scoring succeeded.
api_error        -> API/client call raised an exception other than timeout.
timeout          -> API/client call timed out.
scoring_error    -> raw output exists but scoring raised an exception.
skipped_existing -> --resume was passed and existing score file was found.
```

---

# raw_outputs/<case_id>.json

Each raw output must preserve request info, full API response, extracted text, and timing.

Schema:

```json
{
  "case_id": "route_001",
  "request": {
    "model": "MODEL_ID",
    "temperature": 0,
    "max_tokens": 300
  },
  "response": {
    "full_api_response": {}
  },
  "text": "{\"label\":\"hardware\",\"confidence\":0.82}",
  "wall_time_seconds": 12.34
}
```

On API error, still write a raw output file if useful:

```json
{
  "case_id": "route_001",
  "request": {
    "model": "MODEL_ID",
    "temperature": 0,
    "max_tokens": 300
  },
  "response": {
    "full_api_response": null
  },
  "text": "",
  "error": "...",
  "wall_time_seconds": 0.12
}
```

---

# Scorer module contract

`local_harness/model_audition_scorers.py` must expose:

```python
def score_case(*, fixture: dict, model_text: str, scorer_profile: dict, runtime: dict) -> dict:
    ...
```

Score output:

```json
{
  "case_id": "route_001",
  "overall": 0.84,
  "metrics": {
    "completed": {
      "score": 1.0,
      "weight": 0.1,
      "details": {}
    },
    "json_parse": {
      "score": 1.0,
      "weight": 0.25,
      "details": {}
    }
  },
  "failure_modes": []
}
```

Overall calculation:

```text
overall = sum(metric_score * weight) / sum(weights actually present)
```

If total weight is zero, overall should be 0.0 and failure_modes should include `zero_metric_weight`.

Scores should be floats in [0.0, 1.0].

---

# Scorer profile schema

```json
{
  "profile_id": "json_schema_basic_v0",
  "metrics": [
    {
      "id": "completed",
      "type": "completion",
      "weight": 0.10
    },
    {
      "id": "json_parse",
      "type": "json_parse",
      "weight": 0.25
    },
    {
      "id": "required_keys",
      "type": "required_keys",
      "weight": 0.25,
      "keys": ["label", "confidence"]
    },
    {
      "id": "expected_field_match",
      "type": "expected_field_match",
      "weight": 0.25
    },
    {
      "id": "runtime",
      "type": "runtime",
      "weight": 0.15,
      "target_seconds": 60
    }
  ]
}
```

Unknown metric types should fail clearly with `ValueError`.

---

# Required deterministic scorer types

Implement only these five scorer types in Commit 001:

```text
completion
json_parse
required_keys
expected_field_match
runtime
```

## completion

Purpose: confirms that the model returned non-empty text.

Rules:

```text
score = 1.0 if stripped model_text is non-empty
score = 0.0 otherwise
failure mode: completion_empty
```

## json_parse

Purpose: confirms that model_text is parseable JSON.

Rules:

```text
score = 1.0 if json.loads(model_text) succeeds
score = 0.0 otherwise
failure mode: json_parse_failed
```

Details should include parse error string on failure.

Commit 001 should not attempt aggressive JSON repair. A small helper that strips Markdown code fences is acceptable, but do not build a repair engine.

## required_keys

Purpose: confirms parsed JSON includes required top-level keys.

Metric config:

```json
{
  "id": "required_keys",
  "type": "required_keys",
  "weight": 0.25,
  "keys": ["label", "confidence"]
}
```

Rules:

```text
If JSON parsing fails: score = 0.0.
If no keys are configured: score = 1.0.
Otherwise: score = present_required_key_count / required_key_count.
Failure mode: required_keys_missing when any key is missing.
```

Details should include:

```json
{
  "required": ["label", "confidence"],
  "present": ["label"],
  "missing": ["confidence"]
}
```

## expected_field_match

Purpose: compares simple expected fields against parsed JSON.

Fixture shape:

```json
{
  "expected": {
    "label": "hardware"
  }
}
```

Rules:

```text
If fixture has no expected dict: score = 1.0.
If JSON parsing fails: score = 0.0.
Compare only simple scalar expected fields at top level.
score = matched_expected_fields / comparable_expected_fields.
Failure mode: expected_field_mismatch when any comparable field differs.
```

Comparable scalar types:

```text
str
int
float
bool
null
```

For nested structures in Commit 001, either skip them or compare exact JSON values. Keep behavior deterministic and documented in test names.

## runtime

Purpose: rewards completion within a target runtime.

Metric config:

```json
{
  "id": "runtime",
  "type": "runtime",
  "weight": 0.15,
  "target_seconds": 60
}
```

Runtime input:

```python
runtime = {"wall_time_seconds": 12.34}
```

Rules:

```text
If wall_time_seconds <= target_seconds: score = 1.0.
If wall_time_seconds > target_seconds: score = max(0.0, target_seconds / wall_time_seconds).
If target_seconds missing or <= 0: score = 1.0.
Failure mode: slow_runtime when wall_time_seconds > target_seconds.
```

---

# Capability card

`capability_card.json` aggregates all case scores.

Minimum schema:

```json
{
  "run_id": "qwen25_3b_baseline_20260618",
  "model_id": "Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M",
  "suite_id": "baseline_suite_v0",
  "overall": 0.72,
  "case_count": 5,
  "completed_count": 5,
  "failed_count": 0,
  "metric_averages": {
    "completed": 1.0,
    "json_parse": 0.8,
    "required_keys": 0.7,
    "expected_field_match": 0.6,
    "runtime": 0.5
  },
  "failure_modes": [
    "json_parse_failed"
  ],
  "runtime": {
    "total_wall_time_seconds": 123.4,
    "median_case_wall_time_seconds": 22.0
  }
}
```

Aggregation rules:

```text
case_count = number of fixture cases selected for this run, including failures and skipped_existing rows.
completed_count = manifest rows with status completed.
failed_count = manifest rows with api_error, timeout, or scoring_error.
overall = average of per-case score overall values for completed/scored cases.
metric_averages = average each metric across score files that include that metric.
failure_modes = sorted unique list from score files plus relevant run failures.
total_wall_time_seconds = sum case wall times from manifest/raw outputs.
median_case_wall_time_seconds = median wall time for cases with a wall time.
```

`capability_card.md` should be generated from the JSON and include:

```text
Title
Run/model/suite summary
Overall score
Case counts
Metric averages
Failure modes
Runtime summary
```

No production role recommendations.

---

# Resume and output safety

Without `--resume`:

```text
Fail if out_dir exists and is non-empty.
Do not overwrite existing runs accidentally.
```

With `--resume`:

```text
Skip cases with existing score files.
Append skipped_existing rows to case_manifest.jsonl.
Do not overwrite existing raw outputs.
Do not overwrite existing score files.
Continue remaining cases.
```

This mirrors the ZTH safety model: no ambiguous output reuse.

Recommended helper:

```python
def prepare_out_dir(out_dir: Path, *, resume: bool) -> None:
    ...
```

---

# Case selection options

Implement these options in Commit 001:

```text
--limit N      Run at most N cases after loading fixtures.
--case-id ID   Run only one matching case. May be repeated if argparse uses action='append'; one value is sufficient for MVP.
--dry-run      Resolve config and write metadata/case_manifest preview if desired, but do not call model.
```

Minimum acceptable dry-run behavior:

```text
Load and validate suite/prompt/fixtures/scorer profile.
Print or write resolved run metadata.
Do not call API.
Do not write raw_outputs or scores.
Exit successfully.
```

If dry-run behavior is too much for the first implementation, keep it conservative and test that no client call happens.

---

# Suggested implementation structure

`run_model_audition.py` should be both importable and executable.

Suggested functions:

```python
def parse_args(argv: list[str] | None = None) -> argparse.Namespace: ...
def utc_now_iso() -> str: ...
def load_json(path: Path) -> dict: ...
def load_jsonl(path: Path) -> list[dict]: ...
def load_suite_config(suite_path: Path) -> dict: ...
def resolve_run_config(args: argparse.Namespace) -> dict: ...
def render_prompt(template: str, fixture: dict) -> str: ...
def validate_fixture_cases(cases: list[dict]) -> None: ...
def prepare_out_dir(out_dir: Path, *, resume: bool) -> None: ...
def call_chat_completions(...) -> dict: ...
def extract_text_from_chat_response(response: dict) -> str: ...
def write_json(path: Path, data: dict) -> None: ...
def append_jsonl(path: Path, row: dict) -> None: ...
def build_capability_card(...) -> dict: ...
def write_capability_card_markdown(path: Path, card: dict) -> None: ...
def run_audition(config: dict, *, client=None) -> dict: ...
def main(argv: list[str] | None = None) -> int: ...
```

The `client` injectable should allow tests to avoid network calls.

Suggested fake client return shape for tests:

```python
def fake_client(**kwargs):
    return {
        "choices": [
            {
                "message": {
                    "content": '{"label":"hardware","confidence":0.82}'
                }
            }
        ]
    }
```

---

# Tests to add

## `local_harness/tests/test_run_model_audition.py`

Required tests:

```text
test_load_suite_resolves_relative_paths
test_cli_overrides_suite_paths
test_runner_writes_metadata
test_runner_writes_case_manifest
test_runner_writes_raw_output
test_runner_writes_score_file
test_runner_writes_capability_card
test_resume_skips_existing_case
test_non_empty_out_dir_without_resume_refuses
```

Strongly recommended additional tests:

```text
test_render_prompt_replaces_supported_tokens
test_duplicate_case_id_refuses
test_missing_required_fixture_field_refuses
test_case_id_filter_runs_only_selected_case
test_limit_runs_only_requested_number_of_cases
test_dry_run_does_not_call_client
```

Use `tmp_path` for all generated files.

Do not read or write real `.work` paths in tests.

## `local_harness/tests/test_model_audition_scorers.py`

Required tests:

```text
test_json_parse_scorer_pass
test_json_parse_scorer_fail
test_required_keys_scorer
test_expected_field_match_scorer
test_runtime_scorer
```

Strongly recommended additional tests:

```text
test_completion_scorer_empty_fails
test_score_case_weighted_overall
test_unknown_metric_type_refuses
test_expected_field_match_no_expected_passes
test_required_keys_partial_score
```

---

# Minimal test fixture layout inside tests

Tests can create temporary files like this:

```text
tmp_path/
├── suites/
│   └── suite.json
├── prompts/
│   └── prompt.md
├── fixtures/
│   └── cases.jsonl
└── scorers/
    └── scorer.json
```

Example `prompt.md`:

```text
Return JSON only.

Case: {{case_id}}
Task type: {{task_type}}
Input: {{input}}
Expected: {{expected_json}}
```

Example `cases.jsonl`:

```jsonl
{"case_id":"route_001","task_type":"classification","input":"Debugging llama.cpp timeout.","expected":{"label":"hardware"}}
```

Example `scorer.json`:

```json
{
  "profile_id": "json_schema_basic_v0",
  "metrics": [
    {"id": "completed", "type": "completion", "weight": 0.1},
    {"id": "json_parse", "type": "json_parse", "weight": 0.2},
    {"id": "required_keys", "type": "required_keys", "weight": 0.2, "keys": ["label", "confidence"]},
    {"id": "expected_field_match", "type": "expected_field_match", "weight": 0.3},
    {"id": "runtime", "type": "runtime", "weight": 0.2, "target_seconds": 60}
  ]
}
```

Example fake response:

```json
{
  "choices": [
    {
      "message": {
        "content": "{\"label\":\"hardware\",\"confidence\":0.82}"
      }
    }
  ]
}
```

---

# Acceptance commands

Run exactly:

```bash
python3 -m py_compile local_harness/run_model_audition.py local_harness/model_audition_scorers.py
python3 -m pytest local_harness/tests/test_run_model_audition.py local_harness/tests/test_model_audition_scorers.py
```

Optional broader check:

```bash
python3 -m pytest local_harness/tests
```

---

# Commit 001 is done when

```text
A fake model response can be scored end-to-end.
All required output files are written.
No live model is required by tests.
Prompt, fixtures, and scorer profile are file-driven.
Suite-relative paths resolve correctly.
CLI overrides suite config paths/defaults.
The runner refuses ambiguous output reuse.
Resume skips existing score files without overwriting them.
Capability card JSON and Markdown are emitted.
No model registry, board runner, comparison report, or role assignment exists yet.
```

---

# Manual review checklist before committing

```bash
git status --short
git diff -- local_harness/run_model_audition.py local_harness/model_audition_scorers.py local_harness/tests/test_run_model_audition.py local_harness/tests/test_model_audition_scorers.py
python3 -m py_compile local_harness/run_model_audition.py local_harness/model_audition_scorers.py
python3 -m pytest local_harness/tests/test_run_model_audition.py local_harness/tests/test_model_audition_scorers.py
git diff --check
```

Expected file scope:

```text
A  local_harness/run_model_audition.py
A  local_harness/model_audition_scorers.py
A  local_harness/tests/test_run_model_audition.py
A  local_harness/tests/test_model_audition_scorers.py
```

Any new files under `local_harness/auditions/` are Commit 002 creep unless they are temporary test files under `tmp_path`, which should not appear in git.

---

# Suggested final commit command

```bash
git add local_harness/run_model_audition.py \
        local_harness/model_audition_scorers.py \
        local_harness/tests/test_run_model_audition.py \
        local_harness/tests/test_model_audition_scorers.py

git commit -m "Add generic model audition runner"
```
