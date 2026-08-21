# Qwen3.5-0.8B Atomic Supplier Audition

`SCREENING_ONLY_NOT_CONFIRMATORY`

This exploratory audition tested one candidate supplier on the frozen 16-task
scope-authority-boundary set. It did not call a teacher, retry, escalate,
modify historical evidence, update capability cards, or change production
routing.

## Frozen bindings

- Candidate: `Qwen/Qwen3.5-0.8B` / `Qwen3.5-0.8B-Q4_K_M.gguf`
- Operative loaded supplier parameters: **752393024**
- Upstream total parameter metadata: **873438784** (provenance, not the operative GGUF count)
- Artifact SHA256: `bd258782e35f7f458f8aced1adc053e6e92e89bc735ba3be89d38a06121dc517`; size: `532517120` bytes
- Quantization: `Q4_K_M`
- Runtime: llama.cpp `9314` / `d55fb9717`, context `40960`, thinking `off`
- Hardware: `NVIDIA GeForce GTX 1650`, UUID `GPU-c2823a81-56f1-b16e-f9cc-34f4dc58eb85`
- Telemetry: Level 2, GPU-device-only, remote read-only HTTP, public alias `JARVIS_LOCAL`, sampling interval `0.25 s`
- Run directory: `.work/model_size_supplier_floor/qwen3_5_0_8b_atomic_audition/run_20260821T004420Z`
- Execution manifest SHA256: `96770484dc302de63619f58ff88397937b01b654b4f376d54eda53b74c4d1808`
- Aggregate SHA256: `27a6757bfc7d3c356182d7a3d8995d32bc1967c35fa0eb7ef05e097d8ba5e330`

The Qwen3.5 architecture/generation differs from Qwen3-0.6B and Qwen3-1.7B;
these results provide upward-bracket information, not pure parameter-only
causal evidence.

## Execution result

All 16 responses were transport-valid and raw-parse-valid. None was fully
validator-valid.

| Measure | Result |
|---|---:|
| Tasks | 16 |
| Transport-valid | 16/16 |
| Raw parse-valid | 16/16 |
| Structural contract-valid | 11/16 |
| Validator structural all-checks-pass | 0/16 |
| Reference-fact-valid | 0/16 |
| Full validator passes | 0/16 |
| Supplier calls | 16 |
| Teacher calls | 0 |
| Retries / escalations | 0 / 0 |

The raw interface therefore worked for this explicit typed JSON prompt, while
semantic and authority validation remained unsuccessful at the full-task
level.

## Atomic profile

| Dimension | Result |
|---|---:|
| Allowed-target exact set | 8/16 |
| Allowed-target mean precision / recall | 0.677 / 0.875 |
| Held-target exact set | 6/16 |
| Held-target mean precision / recall | 0.531 / 0.625 |
| Observed no-overlap separation | 11/16 |
| Any allowed/held overlap | 5/16 |
| Scope expansion correct | 11/16 |
| Scope expansion false positive | 5/16 |
| Scope expansion false negative | 0/16 |
| Review-status exact ontology | 0/16 |

The branch-conditioned scope result was **3/8** on the false branch and **8/8** on the true branch. The five false positives occurred on false-branch tasks; there were no false negatives on true-branch tasks.

Semantic-field profile distribution (exact allowed set, exact held set,
scope-expansion boolean, exact review status):

| Profile | Count |
|---:|---:|
| 0/4 | 3 |
| 1/4 | 6 |
| 2/4 | 2 |
| 3/4 | 5 |
| 4/4 | 0 |

There were **5** 3/4 near misses:
`run6-scope-008, run7-scope-014, run7-scope-015, run7-scope-016, run7-scope-018`. Every one was blocked
by `review_status`, not by a target or scope-expansion field. Exact review
ontology was absent in all 16 responses; observed labels were preserved as
confusion pairs: `{"ready_for_review -> allowed": 2, "ready_for_review -> approved": 2, "ready_for_review -> pending": 9, "ready_for_review -> stale": 2, "ready_for_review -> unapproved": 1}`. No status aliases
were normalized.

Per-task atomic results:

| Task | Branch | Parse | Contract | Allowed exact | Held exact | Scope observed/correct | Review observed | Sem fields | Full |
|---|---:|---:|---:|---:|---:|---|---|---:|---:|
| run6-scope-001 | false | true | true | true | false | true/false | pending | 1 | false |
| run6-scope-002 | false | true | false | false | false | true/false | approved | 0 | false |
| run6-scope-003 | false | true | false | false | false | false/true | approved | 1 | false |
| run6-scope-004 | false | true | false | false | false | false/true | pending | 1 | false |
| run6-scope-005 | false | true | true | false | false | true/false | pending | 0 | false |
| run6-scope-006 | false | true | true | true | true | true/false | pending | 2 | false |
| run6-scope-007 | false | true | false | false | false | true/false | stale | 0 | false |
| run6-scope-008 | false | true | true | true | true | false/true | allowed | 3 | false |
| run7-scope-013 | true | true | false | false | false | true/true | pending | 1 | false |
| run7-scope-014 | true | true | true | true | true | true/true | unapproved | 3 | false |
| run7-scope-015 | true | true | true | true | true | true/true | pending | 3 | false |
| run7-scope-016 | true | true | true | true | true | true/true | pending | 3 | false |
| run7-scope-017 | true | true | true | false | false | true/true | pending | 1 | false |
| run7-scope-018 | true | true | true | true | true | true/true | stale | 3 | false |
| run7-scope-019 | true | true | true | false | false | true/true | pending | 1 | false |
| run7-scope-020 | true | true | true | true | false | true/true | allowed | 2 | false |

## Resource measurements

Canonical latency was candidate action wall-clock time. Median / mean / p95
were **962.803 / 922.622 /
1076.251 ms**. Level-2 GPU-device telemetry recorded
mean gross energy **55.621563 J/action**
and median **57.260000 J/action**.
Energy per validated task is unavailable because there were zero full
validated successes. These are not whole-system energy values and no energy
floor is claimed.

The 30-second idle baseline was **7.379917 W**
mean, with **223.242500 J** gross
sampled energy. Process-level remote exclusivity was not independently
observable through telemetry endpoint v1; the operator runtime record stated
the candidate was the only model resident and the 1.7B reference was unloaded.

## Descriptive comparison

The Qwen3-0.6B explicit-interface profile had raw parse-valid `6/12`,
normalized contract-usable `10/12`, normalized exact review status `0/12`,
and normalized 3/4 profiles `5/12`. The present Qwen3.5 loaded supplier had
raw parse-valid `16/16`, but exact review status `0/16`, target partitioning
errors, and no full passes. The interface problem improved here, but the
semantic profile did not demonstrate complete stewardship.

Historical 1.7B paths generally demonstrated the exact `ready_for_review`
ontology on structured outputs, but those runs are not task-matched size-only
controls and the Qwen3.5 architecture is different.

## Interpretation

Practical characterization: **FRAGMENTED_PARTIAL_CAPABILITY**.

The candidate demonstrates machine-readable output and nonzero atomic target
and scope mechanics, especially on the positive scope-expansion branch, but
it systematically emits non-ontology review labels, has five authority
overlap cases, and fails the complete bounded scope-authority contract on all
16 tasks. Complete scope-authority stewardship is not demonstrated.

This is not evidence that the model lacks all bounded reasoning. It is evidence
that the tested supplier/interface/runtime combination did not provide a
complete steward for this responsibility.

## Next-size decision

**ISOLATE_ATOMIC_FAILURE_BEFORE_SIZE_MOVE.** The highest-information next
action is a model-free analysis/design that isolates review-status ontology
selection and the five false-branch scope-expansion/authority-partition errors
before choosing another model. If a future audition is authorized, it must
retain the same atomic scorecard and separately freeze any new task set; this
screen is exploratory and does not create Stage B evidence.

## Integrity boundaries

- Raw responses and terminal validator artifacts were preserved unchanged.
- Historical Run 1–8 evidence was not modified or merged.
- No teacher, external, retry, or escalation calls occurred.
- No production routing or capability card was changed.
- `model_calls=16`; this report itself is model-free.

This report is review-only and does not confer production authority.
