# Semantic Label Factorial V0 Closeout

Status: completed model-free closeout from preserved raw artifacts. No model
call was replayed and no raw artifact was modified.

Freeze: `29a3eb0cde307266a575cd1b16ca4b682e2c089c`

Driver SHA256:
`263c2f3c55e9831587b5ee8a85446bd605c47f9d4b4f5bf57166bddb29285509`

Run: `.work/model_size_supplier_floor/semantic_label_factorial_v0/run_20260824T003000Z`

## Integrity

All five required artifact classes were complete at 24/24:

- `response.json`
- `candidate_validation.json`
- `call_started.json`
- `power_samples.json`
- `runtime_result.json`

All 24 calls were parse-valid, contract-valid, candidate-valid, and
candidate-admissible. Lifecycle values were model calls 24, tool calls 0,
retries 0, runtime evaluator influence 0, and model output granted authority
0. The frozen evaluator manifest was used as the scoring authority.

Per-call hashes and raw response content are preserved in
[the closeout matrix](</home/navigator/agent-workspace/zaphods-third-hand/docs/research/SEMANTIC_LABEL_FACTORIAL_V0_MATRIX_2026-08-24.json>).

## Arm results

| Arm | Semantic | Presence | Inspect | Presence outputs | Inspect outputs |
|---|---:|---:|---:|---:|---:|
| A | 5/6 | 2/3 | 3/3 | 2/6 | 4/6 |
| B | 6/6 | 3/3 | 3/3 | 3/6 | 3/6 |
| C | 3/6 | 0/3 | 3/3 | 0/6 | 6/6 |
| D | 6/6 | 3/3 | 3/3 | 3/6 | 3/6 |

All 12 inspect-task classifications were correct. No unresolved or rejected
outputs occurred.

## Direct contrasts

| Comparison | Output changed | Presence changed | Inspect changed | Overall accuracy delta | Presence delta | Inspect delta |
|---|---:|---:|---:|---:|---:|---:|
| A → C | 2/6 | 2/3 | 0/3 | -2/6 | -2/3 | 0/3 |
| A → D | 1/6 | 1/3 | 0/3 | +1/6 | +1/3 | 0/3 |
| B → C | 3/6 | 3/3 | 0/3 | -3/6 | -3/3 | 0/3 |
| B → D | 0/6 | 0/3 | 0/3 | 0/6 | 0/3 | 0/3 |

The strongest isolated comparison is B versus C: only the inspect surface
label changes, while presence accuracy falls from 3/3 to 0/3. Inspect-task
accuracy remains 3/3 in both arms.

## Factorial contrasts

Using the preregistered descriptive rates and formulas:

| Outcome | Presence-label main effect | Inspect-label main effect | Interaction contrast |
|---|---:|---:|---:|
| Overall | -1/6 (-0.166667) | +2/6 (+0.333333) | +2/6 (+0.333333) |
| Presence tasks | -1/3 (-0.333333) | +2/3 (+0.666667) | +2/3 (+0.666667) |
| Inspect tasks | 0 | 0 | 0 |

These are descriptive six-task contrasts; no significance or generalization
claim is made.

## Bounded characterization

Supported by the preserved evidence:

- `UNDERLYING_BOUNDED_SEMANTIC_DISTINCTION_DEMONSTRATED=true`
- `INTERFACE_DEPENDENT_OBSERVABLE_COMPETENCE_DEMONSTRATED=true`
- `INSPECT_LABEL_MAIN_EFFECT_OBSERVED=true`
- `LITERAL_INSPECT_LABEL_INTERFERENCE_SUPPORTED=true`
- `FACTORIAL_EFFECT_LOCALIZED_TO_PRESENCE_CLASS=true`
- `INSPECT_CLASS_STABILITY=12/12`
- `LABEL_INTERACTION_CONTRAST_NONZERO=true`
- `PRESENCE_TASK_LABEL_INTERACTION_CONTRAST_NONZERO=true`
- `qualification_change=false`

The bounded conclusion is that the supplier distinguishes presence from
inspection on this task family, but observable competence depends materially
on interface label choice. The literal `inspect` label has a bounded adverse
effect on presence classification, moderated by the competing presence-label
representation. This does not establish an unconditional inspect attractor,
general model incapacity, supplier qualification, or a production change.

The prior corrected label counterfactual had current labels at presence 0/3
and inspect 3/3, and neutral labels at presence 3/3 and inspect 3/3. The final
factorial replicates neutral/neutral presence recovery at 3/3 while showing
task-set variability in the original/original arm at 2/3.

## Telemetry

Measurement boundary: GPU-device-only, measurement level 2. Latency p95 is
the inclusive sample quantile over six calls per arm and 24 overall. Energy is
gross GPU-device energy; process-level remote exclusivity was not established.

| Scope | Mean latency ms | Median latency ms | p95 latency ms | Total energy J | Mean energy J |
|---|---:|---:|---:|---:|---:|
| A | 1133.734 | 1126.802 | 1201.669 | 204.510 | 34.085 |
| B | 1217.178 | 1204.345 | 1307.574 | 225.293 | 37.549 |
| C | 1111.019 | 1113.186 | 1191.121 | 208.528 | 34.755 |
| D | 1163.684 | 1151.702 | 1258.329 | 216.268 | 36.045 |
| Overall | 1156.404 | 1139.102 | 1281.818 | 854.598 | 35.608 |

Telemetry is descriptive only and is not treated as causal evidence.
