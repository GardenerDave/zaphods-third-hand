# Qwen3 0.6B Interface-Disambiguation Screen

**EXPLORATORY_NOT_CONFIRMATORY**

This paired diagnostic screen changed only the output-interface instruction.
It did not modify the completed Stage A run, its raw artifacts, its frozen
`NOT_PROMISING_AT_THIS_SIZE` disposition, the validator, or production
routing.

## Bindings

- Run directory:
  `.work/model_size_supplier_floor/qwen3_0_6b_interface_disambiguation/run_20260820T181000Z/`
- Same tasks and order as Stage A: `run7-scope-001` through
  `run7-scope-012`
- Candidate: `Qwen3-0.6B-Q4_K_M.gguf`
- Candidate SHA256:
  `b0638f08417a2d3c8652760462eb5407c6e30173cf9608ad0820757a281eea0e`
- Runtime-freeze SHA256:
  `ad852445d582e5adb7d4cd13b4b12951838e46d6cdf16582aa2c9097c34724aa`
- Prior Stage A report SHA256:
  `51543cc07aa89922e86c554b669b8da689d151ace7f181f5f39cac3eb6eda14b`
- Forensic report SHA256:
  `c3b95e43a9e9c5d68ca2f54f8920f02886bd8f0930561618ca1bf60bb57e361b`
- Interface-screen manifest SHA256:
  `5cbb191ca44318bb105980be489d9f9fda49c934ce601463a81cb73cc4b72f49`
- Aggregate SHA256:
  `3d4807e5079f079664333e23320f27c7fea9caac52be475aecb64777c4be68c7`
- Executed driver SHA256:
  `8fc8738e301a498755256459a8aa824c2bdcc9923527571cc7b696872da31e78`
- Prompt-interface suffix SHA256:
  `8386cb934c15b3a07b6a668075961c505a2c5ecd2d57980a5509c885c67ff4bc`

The screen used one candidate response per task, zero retries, zero
escalations, the same runtime and validator, and Level-2 remote telemetry on
the GTX 1650 device-only boundary.

## Changed interface instruction

The ambiguous field-name-list suffix was replaced with this frozen suffix:

```text
Return ONLY a bare JSON object.
Do not use markdown or code fences.
Do not include reasoning, explanation, or commentary.

The JSON object must have exactly these fields and types:

{
  "allowed_targets": ["string"],
  "held_targets": ["string"],
  "scope_expansion_required": true,
  "review_status": "string"
}

Rules:

- allowed_targets must be a JSON array of strings.
- held_targets must be a JSON array of strings.
- scope_expansion_required must be a JSON boolean: true or false.
- review_status must be a JSON string.
- Use the task evidence to determine the values.
- Do not copy the example values unless they are correct.
- Return the object only.

/no_think
```

The raw response remained authoritative. No fence stripping, type repair, or
other postprocessing was used for the primary result.

## Primary paired results

| Measure | Stage A | Interface screen |
|---|---:|---:|
| Transport-valid responses | 12/12 | 12/12 |
| Raw parse-valid responses | 0/12 | 6/12 |
| Raw contract-valid responses | 0/12 | 4/12 |
| Raw reference-fact-valid responses | 0/12 | 0/12 |
| Raw fully validated responses | 0/12 | 0/12 |
| Markdown-fenced responses | 12/12 | 6/12 |
| Retries | 0 | 0 |
| Escalations | 0 | 0 |

The interface instruction materially reduced the serialization failure: half
of the new responses were bare JSON and four responses were raw contract-valid
under the diagnostic contract accounting. However, every response still
failed deterministic reference-fact validation, and none fully validated.

The raw semantic result is therefore `0/12`, not a repaired or normalized
result.

## Secondary wrapper-only diagnostic

For comparison only, the same mechanically removable outer-fence operation
was applied in memory to every response. No semantic content was added or
changed.

| Diagnostic measure | Result |
|---|---:|
| Mechanically recoverable JSON objects | 12/12 |
| Diagnostic contract-valid objects | 10/12 |
| Diagnostic reference-fact-valid objects | 0/12 |
| Diagnostic fully validated objects | 0/12 |

The two diagnostic contract failures were allowed/held target overlaps. This
secondary result cannot substitute for the raw supplier-interface result.

## Failure details

All 12 tasks had at least one reference-fact failure. Among the six raw
parse-valid responses, all six reached semantic evaluation and failed it. The
remaining six had parse failure in addition to the downstream validator
failures recorded by the existing validator.

The raw contract failures consisted of:

- six parse failures from markdown-fenced responses;
- two allowed/held target overlaps among otherwise parse-valid responses;
- four raw responses that were parse-valid and contract-valid but still failed
  reference facts.

No response reached a fully validated result. This screen therefore shows
that clearer interface instructions improved direct serialization and some
contract compliance, but did not rescue bounded scope-authority performance.

## Latency and Level-2 telemetry

| Metric | Stage A | Interface screen |
|---|---:|---:|
| Median action latency | 1,666.006 ms | 1,853.448 ms |
| Mean action latency | 1,687.516 ms | 1,908.089 ms |
| P95 action latency | 1,929.085 ms | 2,134.687 ms |
| Mean gross energy/action | 54.093750 J | 59.899375 J |
| Median gross energy/action | 54.077500 J | 59.366250 J |

Interface-screen idle baseline was 7.365750 W mean and 7.39 W peak over 120
samples. Mean active power across actions was 29.297363 W and peak observed
power was 35.66 W. These are exploratory Level-2 GTX 1650 device telemetry,
not whole-system energy or an energy-floor claim.

## Interpretation

`INTERFACE_CHANGE_DID_NOT_RESCUE_CAPABILITY`

The output instruction improved raw usability—parse-valid responses increased
from 0/12 to 6/12 and raw contract-valid responses from 0/12 to 4/12—but no
response passed deterministic reference validation and no response fully
validated. The observed evidence does not support treating the 0.6B candidate
as a viable supplier for this bounded capability under either tested
interface.

This remains exploratory evidence. It does not modify Stage A, establish a
confirmatory capability result, or prove universal model incapability.

## Next model-size action

The appropriate next action is to bracket upward in model size. The clearer
interface recovered substantial serialization usability but left validated
semantic performance at zero; this does not justify moving down to a smaller
candidate or immediately designing Stage B for 0.6B.

No Stage B experiment was preregistered.
