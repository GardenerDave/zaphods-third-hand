# Run 3C Resource-Economics Audit

This is a model-free post-hoc audit of the completed Run 3C artifacts. It does
not change the preregistered Run 3C result, and it does not assign economic
weights retroactively.

## Established Run 3C intervention result

From the 48 durable trajectory summaries:

| Arm | Local-teacher calls | External-teacher calls | Preregistered teacher calls |
|---|---:|---:|---:|
| Control | 24 | 11 | 35 |
| Treatment | 17 | 16 | 33 |

Treatment substituted 7 fewer local-teacher calls for 5 additional
external-teacher calls, for a net reduction of 2 preregistered teacher calls
(5.7%). This preserves the original Run 3C conclusion: treatment had 15/24
validated passes versus 14/24 for control, and the preregistered routing-success
criterion was met. The figures above remain intervention counts, not monetary
cost.

## Available cost signals

The authoritative evidence root is:

`.work/capability_batch_reviewed_v3c/run3c_execution_2026-08-20/`

| Signal | Availability and coverage | Source | Caveat |
|---|---|---|---|
| Call count | Available: 156 worker calls, 41 local-teacher calls, 27 external-teacher calls | `trajectory_summary.json`, `trajectory.jsonl`, teacher artifacts | Counts are calls, not normalized compute units. |
| Task count | Available: 24 tasks per arm | arm directories and summaries | A task may contain multiple worker/teacher calls. |
| Wall-clock elapsed interval | Available: 224/224 model calls | `trajectory.jsonl` start/capture timestamps | Start-to-capture includes transport, adapter, and response capture overhead; it is not pure model compute. |
| Server request timings | Available for 197/224 calls: 156 workers and 41 local teachers | `attempt-*.raw.json`, `local-teacher-*.json` metadata | External-teacher artifacts do not preserve server timing fields. |
| Prompt tokens | Available for 197/224 calls | usage metadata in worker/local-teacher artifacts | External teacher has no preserved usage metadata. |
| Completion tokens | Available for 197/224 calls | same | Same external-teacher gap. |
| Total tokens | Available for 197/224 calls | same | Same external-teacher gap; do not infer missing values. |
| Cached tokens | Available for 197/224 calls | usage metadata | Cache semantics are endpoint-specific and not a price. |
| Retry/attempt count | Available for all tasks and worker attempts | summaries and trajectory transitions | Teacher calls and worker retries are distinct event types. |
| Timeout exposure | Configured external timeout available: 120 seconds; no Run 3C arm timeout | preregistration and execution artifacts | Actual external timeout consumption is not measured. |
| Model identity | Available for worker/local teacher; external adapter identity recorded | metadata and teacher artifacts | Hardware is not identified in these artifacts. |
| Hardware/device identity | Unavailable | — | Do not infer GPU assignment from model identity. |
| GPU utilization | Unavailable | — | — |
| Energy/power | Unavailable | — | — |
| Monetary/API price | Unavailable | — | No price schedule was preregistered. |

## Directly supported resource totals

Worker token and server-timing telemetry is complete for every worker attempt.
Local-teacher telemetry is complete for every local-teacher call. External
teacher usage telemetry is absent, so no all-model token total or token-based
external comparison is reported.

| Resource class | Control calls | Control total tokens | Treatment calls | Treatment total tokens |
|---|---:|---:|---:|---:|
| Worker, all attempts | 83 | 34,786 | 73 | 28,422 |
| Local teacher | 24 | 133,351 | 17 | 91,999 |
| External teacher | 11 | unavailable | 16 | unavailable |

Worker tokens per final pass were 2,484.7 for control and 1,894.8 for
treatment. Local-teacher tokens per final pass were 9,525.1 and 6,133.3,
respectively. These are descriptive ratios over this experiment, not unit
costs. External-teacher token ratios cannot be calculated from the preserved
artifacts.

Summed start-to-response intervals, in seconds, are available as an operational
latency signal:

| Resource class | Control seconds | Treatment seconds |
|---|---:|---:|
| Worker calls | 505.6 | 468.5 |
| Local-teacher calls | 385.5 | 259.8 |
| External-teacher calls | 345.0 | 434.0 |

These sums should not be interpreted as end-to-end batch wall time or energy.

The three cost concepts remain separate:

1. **Preregistered intervention count:** local plus external teacher calls;
2. **Measured computational/resource use:** calls, tokens, and recorded elapsed
   timing where present;
3. **Economic cost:** unavailable until objective prices or explicitly frozen
   future weights exist.

## Routing-action economics

| Treatment action | Tasks | Treatment passes | Local calls | External calls | Teacher calls | Control teacher calls on same tasks | Difference (control minus treatment) |
|---|---:|---:|---:|---:|---:|---:|---:|
| deterministic patch retry | 12 | 7 | 13 | 6 | 19 | 18 | -1 |
| external teacher | 8 | 6 | 0 | 8 | 8 | 11 | 3 |
| fixed ladder after abstention | 4 | 2 | 4 | 2 | 6 | 6 | 0 |

The external-teacher action saved three teacher calls relative to control on
its eight paired tasks, while the deterministic-retry action used one more
teacher call than control on its twelve paired tasks. These are paired
descriptive associations; they do not establish that an action caused the
difference.

## Break-even analysis for a future weighted experiment

Let `L` be the cost of one local-teacher call and `E` the cost of one
external-teacher call. For the preregistered teacher-call component:

`control = 24L + 11E`

`treatment = 17L + 16E`

Treatment is cheaper when:

`17L + 16E < 24L + 11E`

`E/L < 7/5 = 1.4`

At `E/L = 1.4` the teacher-call components break even. Above that ratio,
control is cheaper on teacher-call cost alone; below it, treatment is cheaper.
This calculation intentionally excludes worker-call cost. If `W` is also
included, treatment is cheaper when `E/L < 1.4 + 2W/L`, because treatment used
10 fewer worker calls. No value for `W`, `L`, or `E` is assumed here.

## Run 4 decision problem

A cost-aware router must decide whether the expected reduction in local
teacher use and worker calls compensates for the additional external-teacher
use. In particular, the router needs objective relative costs for local versus
external calls, and preferably worker/teacher token or latency rates. Run 3C
shows resource substitution, not simply intervention avoidance: the
external-teacher routing action reduced calls on its paired tasks, while the
deterministic-retry action did not reduce teacher calls in aggregate on its
paired tasks.

## Recommended Run 4 metric design

Do not invent monetary weights from Run 3C. Before Run 4, add or verify:

- monotonic timestamps for request start, response capture, and adapter exit;
- worker, local-teacher, and external-teacher request/response token usage;
- model/server timing fields for the external adapter;
- stable model and hardware/device identity where operationally available;
- an operator-approved resource-weight manifest, versioned and frozen before
  task selection, if a weighted-cost metric is desired.

Until those inputs exist, the smallest defensible Run 4 primary cost metric is
the preregistered pair of direct counts reported separately:

`expensive_teacher_calls = local_teacher_calls + external_teacher_calls`

with secondary count metrics for worker calls, deterministic retries, and
teacher calls by source. A later weighted metric can be preregistered only
after its weights are grounded in an explicit, reviewable resource or pricing
policy.

No Run 4 fixtures or model calls were created by this audit.
