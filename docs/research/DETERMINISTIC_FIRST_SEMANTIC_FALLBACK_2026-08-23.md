# Deterministic-first semantic fallback closeout

Freeze commit: `170dc38`. This exploratory run preserves the paired-interface
evidence at `4bfc9e6` and uses the old `action` + `object_expression` supplier
only as a bounded fallback.

## Results

| measure | result |
|---|---:|
| tasks correct | 10/12 |
| deterministic-sufficient tasks correct | 6/6 |
| deterministic operation derivations | 6/12 |
| fallback routes planned | 4 |
| fallback routes terminally successful | 2/4 |
| fallback routes fail-closed | 2 |
| model calls | 4 |
| model calls avoided by deterministic derivation | 6 |
| authorized read-only tool calls | 4 |
| valid observations | 4 |
| terminal success | 8 |
| ready for review | 4 |

The six deterministic tasks completed with zero model calls. All four fallback
tasks received exactly one model call. Two produced normalized operation
expressions and completed the bounded observation path; two produced
unsupported multi-word action expressions and failed closed before any tool
call. No response was replayed or repaired.

## Bounded characterization

`DETERMINISTIC_FIRST_CAPABILITY_ROUTING_DEMONSTRATED=true`.
`MODEL_CALL_AVOIDANCE_FROM_CAPABILITY_DECOMPOSITION_DEMONSTRATED=true`.
`SEMANTIC_MODEL_FALLBACK_DEMONSTRATED=true` in the bounded partial sense:
the model fallback route worked for 2/4 fresh fallback tasks and contained the
other 2/4 without unsafe downstream execution.
`DYNAMIC_INTELLIGENCE_SURFACE_MINIMIZATION_DEMONSTRATED=true` in that bounded
sense. The primary characterization is
`DETERMINISTIC_FIRST_ROUTING_DEMONSTRATED_FALLBACK_PARTIAL`.

This does not claim general optimal routing, general semantic capability, or a
production change. Qualification promotion remains false.

## Safety and provenance

- runtime expected-field reads: 0;
- planner-hint input fields: 0;
- model output granted authority: 0;
- teacher/30B/external/retry calls: 0;
- duplicate calls: 0;
- target derivation: 12/12 deterministic;
- planned tool calls: 6; executed tool calls: 4;
- all tool access remained exact-target, read-only repository metadata;
- execution driver SHA256: `f02ba85381f81f01791e3f101529ce257fdc3b3488c0814d5844fa8dfdf809a9`;
- closeout driver SHA256: `a053108018481cbed8d1c555da970c30c27d0266b816d7f893189061d8d80891`.

The full per-task responsibility matrix, derivations, plans, fallback raw
responses, tool traces, contract evaluations, and response hashes are in the
run directory and tracked matrix JSON.

## Resource accounting

The four model calls had mean/median/p95 latency
`3654.825/3620.136/3894.887` ms and total/mean/median gross GPU-device energy
`368.575/92.144/92.715` J. These are descriptive measurements only.

## Next decision

`NEXT_DECISION=DIAGNOSE_SEMANTIC_FALLBACK_INTERFACE`.
No next experiment is executed automatically.
