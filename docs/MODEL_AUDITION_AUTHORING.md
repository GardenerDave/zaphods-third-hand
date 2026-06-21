# Authoring Custom Model Auditions

This guide explains how to create small, custom suites for the ZTH
board/capability-card model audition workflow.

Model auditions are structured interviews, not general intelligence
benchmarks. A suite combines plain-file cases, a prompt template, and
deterministic scorer rules so humans can inspect repeatable evidence.

Audition scores do not promote models, assign production roles, or establish
production readiness. Humans decide what the evidence means.

## The Authoring Loop

A custom audition normally has these pieces:

1. **Model config** — identifies the model and existing OpenAI-compatible
   endpoint.
2. **Suite file** — connects the prompt, fixtures, scorer profile, and runtime
   defaults.
3. **Prompt template** — turns each fixture into the text sent to the model.
4. **Fixture JSONL** — provides one test case per nonblank line.
5. **Scorer profile** — lists deterministic metrics and weights.
6. **Optional board** — groups several suites for one model.

A practical loop is:

1. Start with three to six micro cases.
2. Write the fixture intent before tuning the prompt.
3. Use `--dry-run` to verify paths, rendered prompts, scores, and output
   layout without calling an endpoint.
4. Run the suite against one authorized endpoint.
5. Inspect `raw_outputs/`, `rendered_prompts/`, and `scores/`.
6. Decide whether a failure belongs to the model, prompt, fixture, scorer,
   timeout, output channel, or server template.
7. Revise one layer at a time and preserve useful evidence.

## Suggested Directory Shape

The bundled files use this structure:

```text
local_harness/auditions/
  models/
    <model>.json
  suites/
    <suite>.json
  prompts/
    <prompt>.md
  fixtures/
    <fixtures>.jsonl
  scorers/
    <profile>.json
  boards/
    <board>.json
```

Custom files may live elsewhere. Keep related files together and use relative
paths so a suite can be reviewed or copied as a unit.

## Model Configuration

A model file records endpoint configuration separately from the suite:

```json
{
  "model_ref": "custom_router",
  "model_id": "<MODEL_ID>",
  "base_url": "http://<ENDPOINT_HOST>:8080/v1",
  "api_key_env": "OPENAI_API_KEY",
  "api_key_default": ""
}
```

Fields used by the direct runner are:

- `model_id`: value sent in the request body;
- `base_url`: OpenAI-compatible `/v1` base URL;
- `api_key_env`: optional environment variable containing the API key;
- `api_key_default`: optional fallback, commonly empty for local endpoints.

`model_ref` is useful as a stable human-facing identifier and for board
preflight manifest lookup.

Do not commit real private endpoints, credentials, keys, or internal
hostnames. Use placeholders in checked-in examples and private configuration
for real values.

## Suite File Schema

A suite is a JSON object:

```json
{
  "suite_id": "custom_routing_micro_v0",
  "prompt_file": "../prompts/custom_routing_v0.md",
  "fixtures_file": "../fixtures/custom_routing_micro_v0.jsonl",
  "scorer_profile": "../scorers/custom_routing_basic_v0.json",
  "defaults": {
    "temperature": 0,
    "max_tokens": 200,
    "timeout_seconds": 120
  }
}
```

Required fields:

- `suite_id`: stable identifier written into run metadata and capability
  cards;
- `prompt_file`: prompt template path;
- `fixtures_file`: fixture JSONL path;
- `scorer_profile`: scorer profile JSON path.

Optional `defaults` fields:

- `temperature`: defaults to `0` when omitted;
- `max_tokens`: defaults to `300` when omitted;
- `timeout_seconds`: defaults to `900` when omitted.

Explicit CLI flags override suite defaults.

### Path Resolution

- The `--suite` path is resolved from the current working directory unless it
  is absolute.
- Relative `prompt_file`, `fixtures_file`, and `scorer_profile` values are
  resolved from the suite file's directory.
- Absolute prompt, fixture, and scorer paths remain absolute.
- CLI `--prompt-file`, `--fixtures-file`, and `--scorer-profile` overrides are
  resolved from the current working directory.
- Relative suite paths inside a board are resolved from the board file's
  directory.

For a suite stored under `suites/`, `../prompts/example.md` therefore points to
a sibling `prompts/` directory.

## Fixture JSONL Schema

Fixture files contain one JSON object per nonblank line:

```json
{"case_id":"route_001","task_type":"routing","input":"Classify a documentation update.","expected":{"label":"repo_code"},"expected_schema":{"label":"string","rationale":"string"},"metadata":{"difficulty":"micro","domain":"zth","allowed_labels":["repo_code","local_model_ops"]}}
```

Required fields:

- `case_id`: stable case identifier and output filename stem;
- `task_type`: task category available to the prompt template;
- `input`: case material presented to the model.

Common optional fields:

- `expected`: expected top-level values or scorer-specific expectations;
- `expected_schema`: schema guidance inserted into the prompt when requested;
- `metadata`: review context inserted into the prompt when requested.

Metadata is not automatically scored. Use it to document context such as:

- difficulty;
- domain;
- allowed labels;
- source category;
- ambiguity notes;
- other information useful to prompt rendering or human review.

### `expected.required_terms`

The `expected_contains` metric reads `expected.required_terms`.

If it is a list, every item becomes a required term. A single non-list value
becomes one required term. Matching is case-insensitive and searches both the
raw model text and strings flattened from parseable JSON.

The metric score is:

```text
found required terms / total required terms
```

No required terms means the metric passes with a score of `1.0`.

### Expected Field Matching

The `expected_field_match` metric parses the model output as JSON and compares
each top-level field in `expected` using exact value equality. Extra model
output fields do not reduce the score.

For example:

```json
"expected": {"label": "repo_code"}
```

expects the parsed response's `label` field to equal `repo_code`.

Do not put `required_terms` in the same `expected` object when using
`expected_field_match` unless the model is also expected to return a
`required_terms` field with exactly that value.

`expected_schema` is prompt material only. Use the `required_keys` scorer to
mechanically require response keys.

## Prompt Template Variables

The runner replaces these literal variables everywhere in the prompt file:

| Variable | Rendered value |
|---|---|
| `{{case_id}}` | Fixture `case_id` converted to text |
| `{{task_type}}` | Fixture `task_type` converted to text |
| `{{input}}` | Fixture `input` converted to text |
| `{{expected_schema}}` | Pretty, sorted JSON from `expected_schema`, or `{}` |
| `{{expected_json}}` | Pretty, sorted JSON from `expected`, or `{}` |
| `{{metadata_json}}` | Pretty, sorted JSON from `metadata`, or `{}` |

Use only the variables needed by the task. Showing expected answers to the
model can invalidate an audition, so include `{{expected_json}}` only when
that disclosure is intentional.

A small routing prompt might be:

```text
You are evaluating one routing case.

Return JSON only with keys `label` and `rationale`.

Case: {{case_id}}
Task type: {{task_type}}
Input:
{{input}}

Review context:
{{metadata_json}}
```

## Scorer Profile Schema

A scorer profile is a JSON object:

```json
{
  "profile_id": "custom_routing_basic_v0",
  "metrics": [
    {
      "id": "completed",
      "type": "completion",
      "weight": 0.1
    },
    {
      "id": "required_keys",
      "type": "required_keys",
      "weight": 0.2,
      "keys": ["label", "rationale"]
    },
    {
      "id": "expected_label",
      "type": "expected_field_match",
      "weight": 0.6
    },
    {
      "id": "runtime",
      "type": "runtime",
      "weight": 0.1,
      "target_seconds": 30
    }
  ]
}
```

- `profile_id`: stable profile identifier for readers and configuration
  management;
- `metrics`: ordered metric objects;
- `metrics[].id`: result key; if absent, the implementation falls back to the
  metric type;
- `metrics[].type`: selects the scorer implementation;
- `metrics[].weight`: contribution to the weighted overall score.

Only positive weights contribute to the overall weighted denominator. Metric
scores are clamped to the range `0.0` through `1.0`.

Metric-specific fields include:

- `keys` for `required_keys`;
- `target_seconds` for `runtime`, defaulting to `60` when omitted.

## Supported Metric Types

### `completion`

Scores `1.0` when stripped output text is nonempty, otherwise `0.0`.

### `json_parse`

Parses the full response as JSON. If strict parsing fails, it attempts to
recover the first JSON object or array embedded in the text.

### `required_keys`

Requires parseable JSON whose root is an object. Scores the fraction of
configured `keys` present. An empty key list scores `1.0`.

### `expected_field_match`

Requires a JSON object and compares every top-level `expected` fixture field
using exact equality. Scores the fraction that match.

### `expected_contains`

Uses `expected.required_terms` and scores the fraction found
case-insensitively in raw or parseable JSON output.

### `runtime`

Compares `wall_time_seconds` with `target_seconds`. Runs at or below the target
score `1.0`; slower runs score the target divided by actual time, bounded to
the `0.0`–`1.0` range.

## Current Failure Modes

The deterministic scorers may emit:

| Failure mode | Meaning |
|---|---|
| `empty_output` | The model returned no non-whitespace text. |
| `json_parse_failed` | Strict and embedded-JSON parsing both failed. |
| `json_not_object` | JSON parsed, but an object was required. |
| `missing_required_keys` | One or more configured keys were absent. |
| `expected_field_mismatch` | One or more expected top-level fields differed. |
| `expected_contains_missing` | One or more required terms were absent. |
| `runtime_missing` | No wall-time value was available to the runtime scorer. |
| `runtime_over_target` | Runtime exceeded the configured target. |
| `unknown_scorer_type:<type>` | The profile named an unsupported metric type. |

Runner-level case statuses such as `timeout`, `api_error`, and
`scoring_error` are recorded separately in the case manifest and score
evidence.

## Minimal Worked Example

Create this private or experimental structure:

```text
custom_auditions/
  models/custom_router.json
  suites/tiny_routing_v0.json
  prompts/tiny_routing_v0.md
  fixtures/tiny_routing_v0.jsonl
  scorers/tiny_routing_v0.json
```

### `models/custom_router.json`

```json
{
  "model_ref": "custom_router",
  "model_id": "<MODEL_ID>",
  "base_url": "http://<ENDPOINT_HOST>:8080/v1",
  "api_key_env": "OPENAI_API_KEY",
  "api_key_default": ""
}
```

### `suites/tiny_routing_v0.json`

```json
{
  "suite_id": "tiny_routing_v0",
  "prompt_file": "../prompts/tiny_routing_v0.md",
  "fixtures_file": "../fixtures/tiny_routing_v0.jsonl",
  "scorer_profile": "../scorers/tiny_routing_v0.json",
  "defaults": {
    "temperature": 0,
    "max_tokens": 160,
    "timeout_seconds": 120
  }
}
```

### `prompts/tiny_routing_v0.md`

```text
Return JSON only with keys `label` and `rationale`.

Allowed labels and review context:
{{metadata_json}}

Input:
{{input}}
```

### `fixtures/tiny_routing_v0.jsonl`

Each record below is one physical line:

```jsonl
{"case_id":"route_docs","task_type":"routing","input":"Update the operator guide for a command-line flag.","expected":{"label":"repo_code"},"expected_schema":{"label":"string","rationale":"string"},"metadata":{"difficulty":"micro","domain":"zth","allowed_labels":["repo_code","local_model_ops"]}}
{"case_id":"route_endpoint","task_type":"routing","input":"Diagnose a timeout from an existing OpenAI-compatible endpoint.","expected":{"label":"local_model_ops"},"expected_schema":{"label":"string","rationale":"string"},"metadata":{"difficulty":"micro","domain":"zth","allowed_labels":["repo_code","local_model_ops"]}}
```

### `scorers/tiny_routing_v0.json`

```json
{
  "profile_id": "tiny_routing_v0",
  "metrics": [
    {"id": "completed", "type": "completion", "weight": 0.1},
    {"id": "json", "type": "json_parse", "weight": 0.1},
    {
      "id": "keys",
      "type": "required_keys",
      "weight": 0.2,
      "keys": ["label", "rationale"]
    },
    {
      "id": "expected_label",
      "type": "expected_field_match",
      "weight": 0.5
    },
    {
      "id": "runtime",
      "type": "runtime",
      "weight": 0.1,
      "target_seconds": 30
    }
  ]
}
```

### Dry Run

Dry-run creates the normal evidence files but does not call an endpoint. It
uses each fixture's `expected` object as synthetic model output:

```bash
python3 local_harness/run_model_audition.py \
  --model custom_auditions/models/custom_router.json \
  --suite custom_auditions/suites/tiny_routing_v0.json \
  --out-dir .work/model_auditions/tiny_routing_dry_run \
  --dry-run
```

Dry-run validates plumbing rather than model capability. Its synthetic
`expected` output may intentionally omit keys required from a real response,
so inspect the generated scores instead of assuming every dry-run score should
be `1.0`.

Inspect:

```bash
find .work/model_auditions/tiny_routing_dry_run -maxdepth 2 -type f -print | sort
sed -n '1,220p' .work/model_auditions/tiny_routing_dry_run/rendered_prompts/route_docs.md
python3 -m json.tool .work/model_auditions/tiny_routing_dry_run/scores/route_docs.json
```

### Endpoint Run

After privately replacing `<MODEL_ID>` and `<ENDPOINT_HOST>`:

```bash
python3 local_harness/run_model_audition.py \
  --model custom_auditions/models/custom_router.json \
  --suite custom_auditions/suites/tiny_routing_v0.json \
  --out-dir .work/model_auditions/tiny_routing_endpoint_run
```

The runner appends `/chat/completions` to the configured `/v1` base URL.

## Optional Board

A board groups suite files:

```json
{
  "board_id": "custom_micro_board_v0",
  "description": "Small custom audition board.",
  "suites": [
    "../suites/tiny_routing_v0.json",
    "../suites/another_micro_v0.json"
  ],
  "defaults": {
    "temperature": 0,
    "max_tokens": 200,
    "timeout_seconds": 120
  }
}
```

Board-relative suite paths resolve from the board file. Board defaults, when
present, override the corresponding suite defaults for every suite in that
board.

Run with:

```bash
python3 local_harness/run_model_audition_board.py \
  --model custom_auditions/models/custom_router.json \
  --board custom_auditions/boards/custom_micro_board_v0.json \
  --out-dir .work/model_auditions/custom_micro_board
```

## Good Authoring Practice

- Start with three to six cases; two are shown above only to keep the worked
  example compact.
- Keep the first suite micro-sized and focused on one behavior.
- Use low temperature, normally `0`, for deterministic auditions.
- Give case and suite IDs stable, readable names.
- Keep expected values narrow enough to score mechanically.
- Avoid showing expected answers in prompts unless intentional.
- Inspect `rendered_prompts/`, `raw_outputs/`, and `scores/` before trusting a
  capability card.
- Treat `json_parse_failed` as possible prompt or output-channel evidence, not
  automatically a model-capability verdict.
- Distinguish model failure from prompt ambiguity, scorer mismatch, timeout,
  token budget, hidden reasoning/output-channel behavior, and server-template
  mismatch.
- Commit only sanitized reports worth preserving. Reports are evidence
  snapshots, not model promotion, role assignment, or production
  certification.

## Human Review Boundary

Auditions create evidence. They do not:

- promote or approve a model;
- assign a production or lifecycle role;
- authorize implementation, deployment, or routing changes;
- establish production readiness;
- replace human review.

Humans retain interpretation, assignment, promotion, publication, and
follow-up decisions.
