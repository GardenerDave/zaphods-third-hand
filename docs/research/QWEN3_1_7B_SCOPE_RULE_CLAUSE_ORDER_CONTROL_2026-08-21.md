# Qwen3 1.7B-labeled scope-rule clause-order control

`EXPLORATORY_NOT_CONFIRMATORY`

This closeout reports a paired interface-control experiment. It does not
modify or rescore the earlier neutral-constrained crossed-scope probe and does
not create Stage B evidence.

## Binding

The supplier was `Qwen_Qwen3-1.7B-Q4_K_M.gguf`, with 2,031,739,904 operative
parameters, artifact SHA256
`72c5c3cb38fa32d5256e2fe30d03e7a64c6c79e668ad84057e3bd66e250b24fb`, on the
operator-verified GTX 1650 runtime. The effective context was 32,768 under the
native training-context cap. The same 16 crossed tasks, neutral structured
schema, output instruction, runtime, and Level-2 GPU-device telemetry were
used in both arms.

Run directory: `.work/model_size_supplier_floor/qwen3_1_7b_scope_rule_clause_order_control/run_20260821T084255Z/`

The frozen task manifest SHA256 was
`2ceffafeded8942ce717af20f91bef07994b8d3ed6df1f09a3246b6135cb0c96`.
The neutral schema SHA256 was
`5b9aef0b84726bd3ad42147d84d73d332e69241966301aeb5b4f0dc5881193c5`.
The TF rule SHA256 was
`1d0a1b2ec5a0ac88989c1161e2a224741c926c8c50e6bb493ed859fa82058426`.
The FT rule SHA256 was
`09d104250027789591b188c2148940c866b11dc71e618e210758172fc6d5501a`.
The TF-to-FT diff SHA256 was
`0d94eab674b9992e1aa28722a4fd61f123632797ef9aceb34d4fc5fc505d3040`.
The only semantic change was reversal of the first two clauses; the
held-target clarification remained identical and last. No worked boolean
exemplar was present, and the schema allowed both boolean values.

## Execution

There were 32 supplier calls: 16 tasks in each arm, with zero teacher calls,
zero retries, and zero escalations. The temporal order was frozen at eight
TF-then-FT tasks and eight FT-then-TF tasks. All 32 responses were preserved;
all 32 scorecards and validators were produced. Both arms were 16/16
parse-valid and 16/16 contract-valid, with zero serialization or contract
failures.

## Arm results

| Measure | TF, true first | FT, false first |
|---|---:|---:|
| True selected | 16/16 | 0/16 |
| False selected | 0/16 | 16/16 |
| Correct | 8/16 | 8/16 |
| Inside-authority correct | 0/8 | 8/8 |
| Outside-authority correct | 8/8 | 0/8 |
| READ correct | 4/8 | 4/8 |
| MUTATE correct | 4/8 | 4/8 |
| Held distractor present correct | 4/8 | 4/8 |
| Held distractor absent correct | 4/8 | 4/8 |
| TP / FN / FP / TN | 8 / 0 / 8 / 0 | 0 / 8 / 0 / 8 |

The four operation-by-authority cells were:

| Cell | TF | FT |
|---|---:|---:|
| READ + INSIDE | 0/4 | 4/4 |
| READ + OUTSIDE | 4/4 | 0/4 |
| MUTATE + INSIDE | 0/4 | 4/4 |
| MUTATE + OUTSIDE | 4/4 | 0/4 |

Each distractor-present and distractor-absent subcell was 2/4 in both arms.
The observed response was therefore determined by clause order rather than by
operation type or distractor presence in this sample.

## Paired order effect

All 16 tasks flipped: TF TRUE to FT FALSE. The eight inside-authority tasks
changed from incorrect to correct. The eight outside-authority tasks changed
from correct to incorrect. Consequently, inside recovery was 8/8, outside
retention was 0/8, and net accuracy was unchanged at 8/16.

Paired classifications:

- `TF_INCORRECT_FT_CORRECT`: `cross-scope-001`, `cross-scope-002`,
  `cross-scope-005`, `cross-scope-006`, `cross-scope-009`,
  `cross-scope-010`, `cross-scope-013`, `cross-scope-014`.
- `TF_CORRECT_FT_INCORRECT`: `cross-scope-003`, `cross-scope-004`,
  `cross-scope-007`, `cross-scope-008`, `cross-scope-011`,
  `cross-scope-012`, `cross-scope-015`, `cross-scope-016`.
- `SAME_CORRECT`: 0.
- `SAME_INCORRECT`: 0.

This is an interface-order polarity effect, not balanced scope-rule use. The
FT arm materially repairs the previously missing inside/false branch, but it
simultaneously reverses the previously correct outside/true branch.

## Resource measurements

Measurements are Level-2 remote read-only telemetry at the GTX 1650 device
boundary only. The 30-second idle baseline averaged 7.375583 W with a peak of
7.39 W. These values are descriptive and are not used to infer causal energy
effects of clause order.

| Measure | TF | FT |
|---|---:|---:|
| Median latency | 1,072.217 ms | 1,343.958 ms |
| Mean latency | 1,006.291 ms | 1,375.911 ms |
| P95 latency | 1,224.036 ms | 1,643.432 ms |
| Mean gross GPU J/action | 29.7311 J | 38.8659 J |
| Median gross GPU J/action | 31.3550 J | 37.1863 J |
| Total gross GPU energy | 475.6975 J | 621.8550 J |

## Interpretation

Primary characterization: `SCOPE_RULE_ORDER_EFFECT_PARTIAL`.

The reversal is clearly material, but it does not produce a usable balanced
arm: it exchanges an all-TRUE response for an all-FALSE response. This is not
`SCOPE_RULE_ORDER_EFFECT_CONFIRMED`, because the FT arm does not retain the
outside-authority TRUE branch. It is also not a persistent TRUE bias in both
orders.

Capability interpretation: the supplier is sensitive to the tested semantic
interface order; these results do not establish interface-robust scope
reasoning or a parameter-size floor. The prior TF result remains an observation
under its frozen interface and should not be read as clean incapacity by
itself.

Scope interface state: `SCOPE_INTERFACE_STILL_UNSTABLE`.

Next decision: `VALIDATE_CANONICAL_SCOPE_INTERFACE_STABILITY`. A subsequent
experiment should first determine whether a separately frozen, order-balanced
scope interface can yield stable semantic measurement. The 596M and 752M
suppliers are not rerun by this closeout.

## Integrity

The prior neutral-constrained and generic-boolean evidence were read-only
inputs. The new run contains no private endpoint address. No teacher model was
called, no retry or escalation occurred, and no historical run was modified.

`SCOPE_RULE_CLAUSE_ORDER_CONTROL_COMPLETE=true`
