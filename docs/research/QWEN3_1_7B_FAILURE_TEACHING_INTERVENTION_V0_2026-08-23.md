# Qwen3 1.7B bounded teaching-intervention retest

This report records the first bounded ZTH failure-diagnosis -> teacher
intervention -> fresh retest loop. The preserved composition-v0-003 response
was not replayed or rescored.

## Diagnosis and intervention

The preserved failure localized deterministically to
`semantic.minimal_action_object_extraction`, interface
`router_v1_minimal_semantic_atom`, field `action`, predicate `action_allowed`.
The observed action was `exists`; the frozen allowed operation was
`determine`; no tool call was made. The localized class was
`ACTION_OPERATION_STATE_PREDICATE_CONFUSION`.

One local Qwen3-Coder 30B-A3B teacher call produced a contract-valid
`PROMPT_PATCH`. Deterministic intervention validation passed. The candidate
patch was bounded to the existing two-string interface and was stored as
`CANDIDATE_EXPERIMENTAL`; `qualification_change=false`.

The teacher saw no fresh holdout material. The student retest used eight fresh
tasks, each once in a baseline arm and once in a patched arm, for exactly 16
Qwen3 1.7B calls. There were no tool calls, retries, escalations, or external
calls.

## Fresh paired evidence

| Metric | Baseline | Patched |
|---|---:|---:|
| Parse-valid | 8/8 | 8/8 |
| Contract-valid | 8/8 | 8/8 |
| Action exact | 3/8 | 1/8 |
| Object exact | 8/8 | 6/8 |
| Both fields exact | 3/8 | 1/8 |
| Safe semantic binding | 3/8 | 6/8 |
| State-predicate-as-action | 1 | 0 |
| Invalid contracts | 0 | 0 |

Targeted operation-vs-state-predicate regime: action exact was 2/4 baseline
and 1/4 patched; state-predicate-as-action fell from 1 to 0. The direct
operation control regime fell from 1/4 to 0/4 action exact and from 4/4 to 2/4
object exact. Thus the patch did not satisfy the targeted-improvement
criterion and introduced material control-regime regression.

## Resource boundary

Student baseline energy was 426.2075 J total (53.2759 J/call mean); patched
energy was 544.755 J total (68.0944 J/call mean). Baseline latency was
2048.99 ms mean, 2080.861 ms median, 2292.678 ms p95. Patched latency was
2290.476 ms mean, 2342.253 ms median, 2497.251 ms p95. The teacher latency was
13752.167 ms. Teacher device-only energy was unavailable from the configured
telemetry, so it is not imputed.

Runtime evaluator reads were 0. The 30B did not execute the original task,
call a tool, grant authority, or modify the registry.

## Bounded characterization

`FAILURE_LOCALIZATION_TO_CAPABILITY_INTERFACE_DEMONSTRATED=true`

`BOUNDED_TEACHER_INTERVENTION_LOOP_DEMONSTRATED=true`

`TEACHER_PROPOSED_INTERVENTION_IMPROVED_FRESH_HOLDOUT=false`

`SUPPLIER_CAPABILITY_IMPROVEMENT_EVIDENCE_DEMONSTRATED=false`

`SELF_TEACHING_DEMONSTRATED=false`

`QUALIFICATION_PROMOTED=false`

`INTERVENTION_SUPPORTED=false`

`PRIMARY_CHARACTERIZATION=BOUNDED_TEACHER_INTERVENTION_COMPLETED_INTERVENTION_NOT_SUPPORTED`

`NEXT_DECISION=DIAGNOSE_INTERVENTION_FAILURE`

This is a small exploratory result, not a universal capability estimate and
not a qualification or production-routing decision.
