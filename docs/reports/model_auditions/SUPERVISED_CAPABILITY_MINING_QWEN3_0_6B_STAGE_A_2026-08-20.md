# Qwen3 0.6B Stage A Supplier-Floor Screening

**SCREENING_ONLY_NOT_CONFIRMATORY**

This report records an exploratory, candidate-only screen. It is not
confirmatory scientific evidence, does not alter production routing, and has
not been merged into capability cards.

## Disposition

The Qwen3 0.6B candidate is **NOT_PROMISING_AT_THIS_SIZE** for the bounded
scope-authority-boundary supplier role on this screening sample. All 12
responses were transport-valid, but none passed deterministic validation and
none satisfied the structured output contract. The deterministic validator
visibly caught every transport-valid failure; no escalation or retry was run.

This disposition is exploratory and is not a population-level capability
claim.

## Frozen bindings

- Candidate: `Qwen3-0.6B-Q4_K_M.gguf`
- Candidate parameters: `596049920`
- Candidate SHA256:
  `b0638f08417a2d3c8652760462eb5407c6e30173cf9608ad0820757a281eea0e`
- Runtime freeze:
  `docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_0_6B_STAGE_A_RUNTIME_FREEZE_2026-08-20.json`
- Runtime-freeze SHA256:
  `ad852445d582e5adb7d4cd13b4b12951838e46d6cdf16582aa2c9097c34724aa`
- Reference: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`
- Reference SHA256:
  `72c5c3cb38fa32d5256e2fe30d03e7a64c6c79e668ad84057e3bd66e250b24fb`
- Screening manifest SHA256:
  `9154cd143f78ce78fdaf04455b1ba2d0afd3e7a535cba3299c43c03b55ed9c50`
- Aggregate SHA256:
  `2e4c88d5e6fc1d6e12cc028791dff6557cc4733ab2c8f808c67d803f092141d0`
- Run directory:
  `.work/model_size_supplier_floor/qwen3_0_6b_stage_a/run_20260820T171851Z/`

The 12 frozen tasks were, in order:

`run7-scope-001`, `run7-scope-002`, `run7-scope-003`, `run7-scope-004`,
`run7-scope-005`, `run7-scope-006`, `run7-scope-007`, `run7-scope-008`,
`run7-scope-009`, `run7-scope-010`, `run7-scope-011`, and `run7-scope-012`.

No outcome-based replacement was used.

## Capability and contract results

| Measure | Result |
|---|---:|
| Tasks attempted | 12 |
| Transport-valid responses | 12/12 |
| Parse-valid responses | 0/12 |
| Contract-valid responses | 0/12 |
| Reference-fact-valid responses | 0/12 |
| Deterministic validated passes | 0/12 |
| Deterministic failures | 12/12 |
| Pass rate | 0% |

Every failed response had the following observable validator failures:

- `parse_json`
- `required_fields`
- `required_field_types`
- `reference_required_allowed_targets`
- `reference_required_held_targets`
- `reference_requires_scope_expansion_flag`
- `reference_review_status`

The raw responses and terminal validator JSON remain preserved. The failure
classes were `contract_failure` and `reference_fact_failure` for all 12
tasks. This screening therefore provides no evidence of a validated success
on the bounded capability.

## Latency and token telemetry

The canonical latency metric is candidate action wall-clock time.

| Metric | Result |
|---|---:|
| Median action latency | 1,666.006 ms |
| Mean action latency | 1,687.516 ms |
| P95 action latency | 1,929.085 ms |
| Prompt tokens, mean / median | 137.917 / 137.5 |
| Completion tokens, mean / median | 58.083 / 57.5 |
| Total tokens, mean / median | 196 / 196.5 |

Each task received exactly one candidate response. Retry count and escalation
count were both zero.

## Energy telemetry

Energy was measured as **Stage A Level-2 device telemetry** over the frozen
GTX 1650 device-only boundary. The production sampler used the remote
read-only HTTP transport and retained gross energy using:

`sum(power_watts * sample_interval_seconds)`

The public telemetry alias was `JARVIS_LOCAL`; no private endpoint address is
recorded here.

| Metric | Result |
|---|---:|
| Sampling interval | 0.25 s |
| Idle baseline window | 30 s / 120 samples |
| Idle mean / peak power | 7.372667 W / 7.41 W |
| Mean active power across actions | 30.187546 W |
| Peak observed active power | 32.68 W |
| Gross energy per action, mean | 54.093750 J |
| Gross energy per action, median | 54.077500 J |
| Gross energy across 12 actions | 649.125 J |
| Gross joules per validated success | unavailable; 0 validated successes |
| Energy break-even | `ENERGY_BREAK_EVEN_NOT_YET_AVAILABLE` |

These are GTX 1650 device measurements, not whole-system wall energy, and do
not represent monetary cost, hardware cost, FLOPs, or a confirmatory energy
floor.

## Exclusivity and provenance limitation

Immediately before screening, the candidate runtime was manually verified as
the only model resident on the frozen GTX 1650, and the 1.7B reference was not
loaded concurrently. The remote telemetry continuously verified the frozen
GPU identity. Telemetry endpoint v1 does not expose remote process-level
enumeration, so process-level exclusivity is recorded as **not independently
observable**, not as machine-verified.

All telemetry samples matched the frozen GPU UUID and measurement contract;
this limitation did not alter deterministic capability validation.

## Derived-aggregation correction

After terminal execution, a model-free review found that the initial derived
scorecard classification looked for `json_parse` while the frozen validator
uses `parse_json`. The terminal raw responses and validator artifacts were
unchanged. The aggregate was recomputed from those terminal validator files;
the prior derived aggregate SHA256 was:

`b09a4177e7f553f8869c7927aedca0b99758dee3b8f1dbf09f36b0df843624b3`

The corrected aggregate is the hash bound above. This correction changes no
scientific call, prompt, response, validator, fixture, or runtime artifact.

## Boundary

This screen answers only whether the installed 0.6B candidate appeared ready
for a separately designed confirmation study. On this bounded sample it did
not demonstrate non-trivial validated capability or structured-output
reliability. No Stage B experiment was preregistered, no stronger model was
called for escalation, and no capability-card or production-routing change
was made.
