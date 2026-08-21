# Qwen3-0.6B Clean Scope-Logic Probe Design

`EXPLORATORY_CANDIDATE_ONLY_NOT_STAGE_B`

This probe replaces the materially confounded historical
`scope_expansion_required` observations with a balanced atomic measurement.
It changes the output contract to one boolean field and holds the current
Qwen3-0.6B runtime fixed.

## Frozen semantic contract

The shared prompt supplies this repository-derived rule:

```text
scope_expansion_required is true when completing the requested operation would
require authority beyond the targets or operations explicitly authorized by
the provided evidence, so a separate scope grant or review is required.

scope_expansion_required is false when the requested operation is fully within
the authority explicitly granted by the provided evidence and no separate
scope grant is needed.

A held or out-of-scope target by itself does not determine this field.
Distinguish holding a target while reporting the current authority boundary
from a request to expand that authority boundary.
```

The rule is frozen identically for all 16 tasks. Task prompts contain only
authority evidence and the requested operation; they do not state the expected
boolean or an equivalent answer phrase.

## Atomic output contract

The candidate must return exactly one bare JSON object:

```json
{"scope_expansion_required": true}
```

The value must be a JSON boolean. No target lists, review status, explanation,
markdown, or additional fields are requested. Raw output remains authoritative.

## Task population

The fresh manifest contains 16 fictional but repository-grounded
scope-authority tasks:

- 8 expected `false`: the requested operation stays within the explicitly
  authorized target/operation boundary while another target is held;
- 8 expected `true`: the requested operation directly acts on a held target
  outside the authorized boundary.

Both branches contain held targets. The set covers read-versus-mutate,
responsibility without execution authority, stale/expired authority, narrow
delegation, nested authority, and paired in-boundary/out-of-boundary
operations.

## Leakage audit

Before execution, the model-free validator checks every task prompt for direct
answer phrases, including `scope expansion is required`, `no scope expansion`,
`new approval`, `scope grant`, `mark expansion`, and equivalent forms. It also
checks that authority evidence and a requested operation are present, that task
IDs are unique, and that the manifest is balanced 8/8.

Any finding fails closed before calls.

## Runtime and execution

The probe uses the operator-restored Qwen3-0.6B Q4_K_M runtime:

- artifact SHA256: `b0638f08417a2d3c8652760462eb5407c6e30173cf9608ad0820757a281eea0e`;
- operative parameters: `596049920`;
- context: `40960`;
- llama.cpp: `9314`, build `d55fb9717`;
- thinking off;
- GTX 1650 UUID: `GPU-c2823a81-56f1-b16e-f9cc-34f4dc58eb85`;
- Level-2 remote GPU telemetry, device-only boundary, 0.25-second sampling.

Execution is one candidate response per task: 16 supplier calls, zero retry,
teacher, or escalation calls. Historical runs remain read-only.

## Interpretation boundary

This probe measures the supplied binary rule on a small balanced exploratory
sample. It is not a full scope-authority audition, a production authorization,
or Stage B confirmation. Historical confounded observations remain separate
provenance and are not pooled numerically.

