# LLM-Probe Preflight Import

The LLM-probe preflight importer turns one supported JSON result file into
plain-file evidence for human review.

It is an import and normalization layer only. It does not run a model, evaluate
role suitability, or make deployment decisions.

## What the Importer Does

`local_harness/llm_probe_preflight_ingest.py`:

- reads one `llm_probe.results.v1` JSON file;
- rejects unsupported or unknown top-level input shapes;
- preserves the source bytes as `source/results.json`;
- records the source SHA-256 and byte count;
- normalizes valid observations into JSONL;
- records malformed observations and explicit reasons in separate JSONL;
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
- export OKF data;
- accept YAML input.

Preflight observations are evidence to inspect, not authorization for later
actions.

## Supported Input Shape

The importer currently accepts JSON with this exact top-level shape:

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

The bundled sanitized fixture is:

```text
examples/llm_probe_preflight_fixture/results.json
```

## Generated Files

One successful import writes exactly:

```text
<out-dir>/
  source/
    results.json
  import_metadata.json
  probe_manifest.jsonl
  invalid_records.jsonl
  preflight_summary.json
  preflight_summary.md
```

- `source/results.json` preserves the input bytes exactly.
- `import_metadata.json` records the importer, source paths, source SHA-256,
  source byte count, input schema, and run ID.
- `probe_manifest.jsonl` contains one normalized row per valid observation.
- `invalid_records.jsonl` contains malformed observations, source indexes, raw
  records, and explicit validation reasons.
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

## Run Manually

From the repository root:

```bash
tmpdir=$(mktemp -d)

python3 local_harness/llm_probe_preflight_ingest.py \
  --probe-output examples/llm_probe_preflight_fixture/results.json \
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
audition fields, fail-closed input handling, and the CLI path.

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
If a human wants to audition a model after reviewing preflight evidence, that
is a separate, explicit workflow.
