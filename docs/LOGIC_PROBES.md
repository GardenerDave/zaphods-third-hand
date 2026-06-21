# Local Model Logic Probes

Logic probes are small ZTH-specific diagnostic cases for local or
OpenAI-compatible models. They ask whether a model can do useful bounded work
while preserving authority, evidence, scope, and destructive-action
boundaries.

They are not a general-intelligence benchmark, a promotion system, or an
autonomous agent loop. Results are mechanically scored evidence for human
review.

## What the Probes Test

The example fixture set covers:

- authority-boundary preservation;
- separation of evidence from inference;
- inspection before destructive action;
- allowed-path and scope discipline;
- cautious handling of contradictory merge evidence;
- strict structured-output reliability.

This emphasis differs from generic benchmarks. Logic probes do not try to
measure broad knowledge or produce a universal model ranking. They test failure
modes that matter in bounded ZTH workflows, especially whether a model fails
safely when a prompt contains an authority or cleanup trap.

## Runtime Modes

### Validate fixtures

Validate fixture shape without calling a model:

```bash
python3 local_harness/logic_probe.py validate \
  --fixtures local_harness/logic_probes.example.json
```

Validation checks the fixture schema, unique probe IDs, allowed categories,
scoring fields, regular expressions, JSON requirements, and destructive-order
configuration.

### Score saved responses

Score previously captured raw response files without calling a model:

```bash
python3 local_harness/logic_probe.py score \
  --fixtures local_harness/logic_probes.example.json \
  --responses .work/model_auditions/logic_probe_runs/<run-id>/raw \
  --out-dir .work/model_auditions/logic_probe_runs/<run-id>
```

The raw response directory must contain one directory per model and one JSON
file per probe:

```text
raw/
  <model-id>/
    <probe-id>.json
```

Each raw JSON object identifies `model_id` and `probe_id` and contains either a
string `response_text` or an `error`. Missing or malformed response evidence is
recorded as an `error` result rather than treated as a pass.

The scorer uses case-insensitive phrase checks, optional regular expressions,
strict JSON parsing and required-key checks, and configured
inspection-before-destruction ordering. It does not use a judge model.

### Run against endpoints

Call configured OpenAI-compatible `/v1/chat/completions` endpoints, preserve
the raw evidence, and invoke the same mechanical scorer:

```bash
python3 local_harness/logic_probe.py run \
  --fixtures local_harness/logic_probes.example.json \
  --models local_harness/model_auditions/models.example.json \
  --only-models lan_qwen3_4b \
  --out-dir .work/model_auditions/logic_probe_runs \
  --run-id <run-id>
```

The selected example is the checked-in endpoint-only LAN entry. Use
`--only-models` with another key or a comma-separated subset for a different
topology; omit it to probe every configured model. `--timeout` and
`--max-tokens` set per-request limits.

The command uses the existing exploratory small-model configuration shape.
Each model entry may provide a full `base_url`, or `host` plus `port`, and may
set `api_model` for the request's model value. See
[`local_harness/model_auditions/README.md`](../local_harness/model_auditions/README.md)
for local/LAN endpoint configuration and optional temporary llama.cpp server
lifecycle guidance.

`127.0.0.1` always means the same machine that is running
`logic_probe.py`. It does not reach a model server on another workstation.
When the model server is on the LAN, select or create an endpoint-only model
entry whose `base_url` uses that server's LAN address. The checked-in model
configuration includes an intentional LAN example; review and replace its
address for a different network.

The logic-probe runner does not start or stop servers and does not add
authentication headers. The endpoint must already be running and accessible.
Use only endpoints you are authorized to call.

If one endpoint or response fails, the harness preserves that failure in the
corresponding raw file and continues with the remaining probes and models.

## Output Layout

`run` writes:

```text
.work/model_auditions/logic_probe_runs/<run-id>/
  run_manifest.json
  raw/
    <model-id>/
      <probe-id>.json
  scored/
    <model-id>.json
  LOGIC_PROBE_SUMMARY.md
```

`run_manifest.json` records the run ID, UTC creation time, fixture and model
configuration paths, probe count, model count, and selected model IDs. It also
records that human review is required and no authority was granted.

Raw files preserve the prompt, request payload, endpoint, elapsed duration,
complete endpoint response, extracted response text, and any error. Scored
files contain per-probe status, score, failures, warnings, and matched checks.
The Markdown summary provides counts and conservative bounded-role review
suggestions.

The harness refuses to overwrite an existing run directory. The standalone
`score` command also refuses to overwrite existing scored output or the
summary.

## Interpreting Results

Statuses mean:

- `pass`: all configured checks passed and no critical failure was found;
- `mixed`: some positive requirements were met, but evidence is incomplete;
- `fail`: a critical mechanical failure was detected;
- `error`: endpoint, raw-file, response-shape, or harness evidence was
  unavailable or malformed.

Critical failures include configured forbidden actions, invalid strict JSON,
missing required JSON keys, and destructive action appearing before a
configured inspection step.

A pass is narrow. It means the response passed that fixture's mechanical
checks. It does not prove semantic correctness, safety in other prompts,
production readiness, or suitability for an unsupervised role. Review the raw
responses as well as the scores.

## Authority Boundary

Logic probe results are evidence only. They do not grant authority to execute,
edit, commit, merge, push, delete, clean up, promote, release, assign a model
role, or mark work complete.

The summary always marks autonomous implementation as `no`. Any bounded-role
suggestion remains a human-review prompt, not a ranking, assignment, or
lifecycle decision.

## Future Work

A Local Model Night Shift wrapper, cron scheduling, routing-table generation,
multi-model panels, dashboards, and automatic capability-card updates are
future possibilities. None are part of the current harness.

The current tool runs only when a human invokes it and produces plain-file
evidence for review.
