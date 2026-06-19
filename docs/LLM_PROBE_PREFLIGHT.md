# LLM-Probe Preflight Import

The LLM-probe preflight importer turns one supported JSON result file or one
upstream-shaped LLM-probe `verified/<provider>.yaml` file into plain-file
evidence for human review.

It is an import and normalization layer only. It does not run a model, evaluate
role suitability, run LLM-probe, or make deployment decisions.

## What the Importer Does

`local_harness/llm_probe_preflight_ingest.py`:

- reads one `llm_probe.results.v1` JSON file or LLM-probe verified YAML file;
- adapts YAML model test results into the existing normalized observation shape;
- rejects unsupported JSON shapes and malformed core YAML shapes;
- preserves the source bytes as `source/results.json` or `source/results.yaml`;
- records the source SHA-256 and byte count;
- normalizes valid observations into JSONL;
- records malformed observations and explicit reasons in separate JSONL;
- writes a conservative ZTH-owned preflight capability manifest;
- writes factual counts and diagnostics in JSON and Markdown.

The importer makes no network calls and no model calls. The output directory
must be absent or empty so existing evidence is not overwritten accidentally.

## What the Importer Does Not Do

The preflight importer does not:

- run ZTH model auditions;
- call `run_model_audition.py` or `compare_model_auditions.py`;
- score or rank models;
- generate capability cards;
- assign role fit or gate roles;
- create model-registry entries or audition commands;
- promote, approve, or select a model;
- require OKF export for internal operation;
- execute LLM-probe or contact a provider.

Preflight observations are evidence to inspect, not authorization for later
actions.

## Supported JSON Input Shape

The existing normalized JSON contract remains supported with this exact
top-level shape:

```json
{
  "schema_version": "llm_probe.results.v1",
  "run_id": "synthetic-preflight-001",
  "generated_at": "2026-06-19T12:00:00Z",
  "observations": [
    {
      "model_id": "synthetic-model-a",
      "probe_id": "endpoint_response",
      "status": "pass",
      "observed_value": true,
      "latency_ms": 125,
      "diagnostics": [],
      "metadata": {
        "fixture": "synthetic"
      }
    }
  ]
}
```

Required observation fields are:

- `model_id`: non-empty string;
- `probe_id`: non-empty string;
- `status`: one of `pass`, `warn`, `fail`, `error`, or `skipped`;
- `observed_value`: the factual value reported by the probe.

Optional observation fields are:

- `latency_ms`: non-negative number or `null`;
- `diagnostics`: array of non-empty strings;
- `metadata`: JSON object.

Unknown top-level fields, missing top-level fields, unsupported schema versions,
invalid JSON, and non-array `observations` fail closed before an output
directory is created. Malformed individual observations are retained in
`invalid_records.jsonl` instead of being silently discarded.

The bundled sanitized JSON fixture is:

```text
examples/llm_probe_preflight_fixture/results.json
```

## Supported LLM-Probe YAML Shape

The YAML adapter accepts an upstream-shaped LLM-probe
`verified/<provider>.yaml` document:

```yaml
provider: synthetic-provider
last_run: "2026-03-31"
models:
  - id: synthetic-model
    tool_call: pass
    think_blocks: none
    avg_response_ms: 120
    tests:
      tool_call_basic: {passed: true, pass_rate: "3/3"}
      tool_call_large: {passed: true, pass_rate: "3/3"}
    last_tested: "2026-03-31"
```

Each entry under a model's `tests` mapping becomes one normalized observation.
`passed: true` maps to `status: "pass"` and `passed: false` maps to
`status: "fail"`. Provider, model-level probe facts, pass rate, last-tested
date, and source format remain visible in the observation.

Malformed individual models or tests are written to `invalid_records.jsonl`.
Malformed YAML, a missing top-level `models` field, or a non-list `models`
field fails closed before an output directory is created. Unknown top-level
YAML fields are ignored safely because real verified files may contain
additional upstream metadata.

The YAML path uses `yaml.safe_load`. PyYAML must already be available in the
environment; the importer does not install dependencies automatically. JSON
imports do not require PyYAML.

The bundled sanitized YAML fixture is:

```text
examples/llm_probe_preflight_fixture/verified-provider.yaml
```

## Generated Files

One successful JSON import writes:

```text
<out-dir>/
  source/
    results.json
  import_metadata.json
  probe_manifest.jsonl
  invalid_records.jsonl
  preflight_capability_manifest.json
  preflight_summary.json
  preflight_summary.md
```

A YAML import uses the same output shape except that the preserved source is:

```text
source/results.yaml
```

- `source/results.json` or `source/results.yaml` preserves the input bytes
  exactly.
- `import_metadata.json` records the importer, source paths, source SHA-256,
  source byte count, input format, input schema, and run ID.
- `probe_manifest.jsonl` contains one normalized row per valid observation.
- `invalid_records.jsonl` contains malformed observations, source indexes, raw
  records, and explicit validation reasons.
- `preflight_capability_manifest.json` summarizes source identity, observed
  model and probe IDs, status counts, record counts, and a conservative
  preflight status. It requires human review and is not a capability card.
- `preflight_summary.json` contains factual record, model, probe, status, and
  diagnostic counts.
- `preflight_summary.md` presents the same boundary and counts for human review.

## Output Contract

Generated metadata, summaries, valid observations, and invalid-record entries
include:

```json
{
  "output_contract_version": "zth.llm_probe_preflight.v0.1",
  "scope": "preflight_only",
  "promotion_performed": false
}
```

These fields are explicit invariants:

- `output_contract_version` identifies the current plain-file contract.
- `scope: "preflight_only"` prevents the import from being represented as an
  audition or deployment decision.
- `promotion_performed: false` records that importing evidence did not promote
  a model.

The capability manifest also records:

```json
{
  "requires_human_review": true,
  "preflight_status": "fail"
}
```

`preflight_status` is intentionally conservative:

- `unknown` when there are no valid records;
- `fail` when any valid record has `fail` or `error`;
- `intermittent` when at least one valid record has `warn` or `skipped` and
  none has `fail` or `error`;
- `pass` only when at least one valid record exists and every valid record has
  `pass`.

This status summarizes imported preflight evidence. It does not rank, promote,
approve, or assign a model to a role.

## Input Format Selection

The CLI accepts:

```text
--input-format auto|json|llm-probe-yaml
```

The default is `auto`:

- `.json` selects the existing normalized JSON loader;
- `.yaml` or `.yml` selects the LLM-probe verified YAML adapter;
- other extensions fail closed with a format-selection error.

The recorded input formats are:

- `zth_normalized_json`;
- `llm_probe_verified_yaml`.

## Run Manually

From the repository root:

```bash
tmpdir=$(mktemp -d)

python3 local_harness/llm_probe_preflight_ingest.py \
  --probe-output examples/llm_probe_preflight_fixture/results.json \
  --out-dir "$tmpdir/preflight"
```

Import an LLM-probe verified YAML file:

```bash
tmpdir=$(mktemp -d)

python3 local_harness/llm_probe_preflight_ingest.py \
  --probe-output examples/llm_probe_preflight_fixture/verified-provider.yaml \
  --input-format llm-probe-yaml \
  --out-dir "$tmpdir/preflight"
```

Inspect the resulting files directly:

```bash
find "$tmpdir/preflight" -type f -print | sort
python3 -m json.tool "$tmpdir/preflight/preflight_summary.json"
sed -n '1,240p' "$tmpdir/preflight/preflight_summary.md"
```

## Run the Focused Tests

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider \
  local_harness/tests/test_llm_probe_preflight_ingest.py
```

The tests cover source preservation, SHA-256 recording, JSONL validity,
invalid-record capture, factual summary counts, contract fields, forbidden
audition fields, conservative capability-manifest status rules, fail-closed
input handling, unchanged JSON import behavior, YAML adaptation, and the CLI
paths.

## Optional OKF-Style Export

`local_harness/llm_probe_preflight_okf_export.py` can convert one completed
preflight import directory into an optional linked Markdown bundle with YAML
frontmatter.

The export:

- reads the existing preflight files without modifying them;
- verifies required files, contract fields, source SHA-256, and record counts;
- writes provider, model, run, bundle-index, and export-log concepts;
- remains plain-file evidence for human review;
- is not required for importer or ZTH internal operation;
- does not become the source of truth;
- does not run LLM-probe;
- does not promote, rank, gate, or audition models.

Export a completed preflight directory:

```bash
python3 local_harness/llm_probe_preflight_okf_export.py \
  --preflight-dir "$tmpdir/preflight" \
  --out-dir "$tmpdir/okf/model-preflight"
```

The output shape is:

```text
<out-dir>/
  index.md
  log.md
  providers/
    index.md
    <provider-slug>.md
  models/
    index.md
    <model-slug>.md
  runs/
    index.md
    <run-slug>.md
```

Every Markdown file carries the preflight contract boundary in a namespaced
`zth` frontmatter object, including `scope: preflight_only` and
`promotion_performed: false`. Links inside the bundle are relative.

## Separation From Model Auditions

Preflight import and model auditions answer different questions.

The preflight importer asks:

> What did an external probe report, and can that evidence be preserved in a
> stable, reviewable shape?

ZTH model auditions ask:

> How do models behave on ZTH prompts, fixtures, deterministic scorers, suites,
> and boards?

Combining these layers would let imported external observations look like ZTH
audition results or model-selection decisions. Keeping them separate preserves
provenance and prevents a preflight pass from becoming an implicit promotion.
Importing verified YAML does not run LLM-probe and does not convert an upstream
test pass into a ZTH audition result.
If a human wants to audition a model after reviewing preflight evidence, that
is a separate, explicit workflow.
