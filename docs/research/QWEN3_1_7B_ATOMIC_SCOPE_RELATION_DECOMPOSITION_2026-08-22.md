# Qwen3 1.7B-labeled Atomic Scope-Relation Decomposition

This exploratory, candidate-only decomposition ran after the model-free fixture
audit. It did not modify prior raw evidence or create Stage B evidence.

## Erratum and binding

The held-clarification isolation is corrected additively in
`QWEN3_1_7B_HELD_CLARIFICATION_POSITION_ISOLATION_INTERPRETATION_ERRATUM_2026-08-22.md`:

- clarification position effect: not observed;
- clarification removal: one changed observation, insufficient for a stable
  presence effect;
- corrected disposition: `HELD_CLARIFICATION_EFFECT_NOT_SUPPORTED`;
- next decision: `DECOMPOSE_SCOPE_RELATION`.

Frozen task manifest: `docs/research/CROSSED_SCOPE_FACTORIAL_PROBE_TASKS_2026-08-21.json`
(`2ceffafeded8942ce717af20f91bef07994b8d3ed6df1f09a3246b6135cb0c96`).

Run: `.work/model_size_supplier_floor/qwen3_1_7b_atomic_scope_relation_decomposition/run_20260822T020000Z/`
(`probe_manifest.json` SHA256 `efc5aa73f1e5c859a02ceb07d247d40f4b4ac15a606175d9445148be43d58c72`).

Supplier: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`, operative parameter count
`2,031,739,904`, artifact SHA256
`72c5c3cb38fa32d5256e2fe30d03e7a64c6c79e668ad84057e3bd66e250b24fb`.

The 16-task population is balanced 8/8 by expected scope, operation, authority,
and distractor factors. The atomic prompts omitted scope-expansion terminology
and asked only for `target_authorized` or `operation_authorized`. The two probes
used structure-only boolean schemas; both were 16/16 contract-valid.

## Fixture support and limitation

The model-free identity held for every task:

`scope_expansion_required = NOT (target_authorized AND operation_authorized)`.

The decomposition is therefore supported by the existing fixture facts. However,
the fixtures make the two atoms perfectly collinear: every inside-authority task
has both atoms true and every outside-authority task has both atoms false. This
experiment can test whether decomposition recovers the final scope mechanic, but
cannot independently rank target authorization against operation authorization.

## Atomic results

| Arm | Parse-valid | Contract-valid | Correct | True selected | False selected | Inside correct | Outside correct | Read correct | Mutate correct | Distractor present | Distractor absent |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `target_authorized` | 16/16 | 16/16 | 13/16 | 5/16 | 11/16 | 5/8 | 8/8 | 7/8 | 6/8 | 5/8 | 8/8 |
| `operation_authorized` | 16/16 | 16/16 | 13/16 | 9/16 | 7/16 | 7/8 | 6/8 | 6/8 | 7/8 | 7/8 | 6/8 |

Target-atom confusion matrix: `TP=5, FN=3, FP=0, TN=8`.

Operation-atom confusion matrix: `TP=7, FN=1, FP=2, TN=6`.

There were zero serialization failures and zero invalid-contract failures in
either arm; all six atomic errors were semantic judgment failures.

## Deterministic recombination

Observed atomic outputs were recombined without another model call:

`derived_scope_expansion_required = NOT (observed_target_authorized AND observed_operation_authorized)`.

- derived final scope: `13/16`;
- inside-authority: `5/8`;
- outside-authority: `8/8`;
- READ: `7/8`;
- MUTATE: `6/8`;
- held distractor present: `5/8`;
- held distractor absent: `8/8`;
- confusion matrix: `TP=8, FN=0, FP=3, TN=5`.

The three false positives were `cross-scope-001`, `cross-scope-005`, and
`cross-scope-013`. All were inside-authority tasks with a target-atom failure;
`cross-scope-001` also had an operation-atom failure.

## Task-level localization

| Task | Expected scope | Target observed | Operation observed | Derived scope | Target correct | Operation correct | Derived correct | Localization |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| cross-scope-001 | false | false | false | true | no | no | no | BOTH_ATOMIC_JUDGMENTS_FAIL |
| cross-scope-002 | false | true | true | false | yes | yes | yes | ATOMS_CORRECT_FINAL_DERIVATION_CORRECT |
| cross-scope-003 | true | false | false | true | yes | yes | yes | ATOMS_CORRECT_FINAL_DERIVATION_CORRECT |
| cross-scope-004 | true | false | true | true | yes | no | yes | OPERATION_JUDGMENT_FAILURE |
| cross-scope-005 | false | false | true | true | no | yes | no | TARGET_JUDGMENT_FAILURE |
| cross-scope-006 | false | true | true | false | yes | yes | yes | ATOMS_CORRECT_FINAL_DERIVATION_CORRECT |
| cross-scope-007 | true | false | false | true | yes | yes | yes | ATOMS_CORRECT_FINAL_DERIVATION_CORRECT |
| cross-scope-008 | true | false | false | true | yes | yes | yes | ATOMS_CORRECT_FINAL_DERIVATION_CORRECT |
| cross-scope-009 | false | true | true | false | yes | yes | yes | ATOMS_CORRECT_FINAL_DERIVATION_CORRECT |
| cross-scope-010 | false | true | true | false | yes | yes | yes | ATOMS_CORRECT_FINAL_DERIVATION_CORRECT |
| cross-scope-011 | true | false | false | true | yes | yes | yes | ATOMS_CORRECT_FINAL_DERIVATION_CORRECT |
| cross-scope-012 | true | false | false | true | yes | yes | yes | ATOMS_CORRECT_FINAL_DERIVATION_CORRECT |
| cross-scope-013 | false | false | true | true | no | yes | no | TARGET_JUDGMENT_FAILURE |
| cross-scope-014 | false | true | true | false | yes | yes | yes | ATOMS_CORRECT_FINAL_DERIVATION_CORRECT |
| cross-scope-015 | true | false | false | true | yes | yes | yes | ATOMS_CORRECT_FINAL_DERIVATION_CORRECT |
| cross-scope-016 | true | false | true | true | yes | no | yes | OPERATION_JUDGMENT_FAILURE |

Localization counts:

- `ATOMS_CORRECT_FINAL_DERIVATION_CORRECT`: 11;
- `TARGET_JUDGMENT_FAILURE`: 2;
- `OPERATION_JUDGMENT_FAILURE`: 2;
- `BOTH_ATOMIC_JUDGMENTS_FAIL`: 1;
- invalid atomic contract: 0.

## Comparison with direct scope prompts

The prior direct single-predicate scope probe scored `8/16`; the clarification-
absent arm scored `9/16`. This decomposition scored `13/16` after deterministic
recombination. The improvement is descriptive and not a pure interface-causal
claim: the decomposition changes the requested model judgments and moves final
composition out of the model.

The result supports the characterization
`ATOMS_WORK_DIRECT_SCOPE_COMPOSITION_FAILS` for this exploratory sample, with
the important qualification that the two atoms were not independently crossed
in the frozen fixtures. The model correctly supplied both atoms on 11/16 tasks,
and deterministic composition was correct on those 11 plus two tasks where a
single atom error did not change the final truth value. Direct whole-relation
judgment was weaker under the prior interfaces.

This is not evidence of a universal model-size threshold or production
authority. It is evidence that deterministic composition can reduce a compound
scope-field failure in this tested supplier/interface arrangement.

## Resources and execution integrity

Level-2 GTX 1650 device-only telemetry, 0.25-second sampling:

| Arm | Latency median / mean / p95 (ms) | Mean / median gross J/action | Total gross J |
|---|---:|---:|---:|
| target authorization | 1045.7585 / 1044.5855 / 1072.944 | 33.693125 / 33.8325 | 539.09 |
| operation authorization | 984.534 / 988.0838125 / 1030.976 | 29.18421875 / 28.06 | 466.9475 |

Idle baseline: mean 7.384545 W, peak 7.4 W, 30.060509 s, 121 samples.
These are GPU-device measurements, not whole-system energy claims.

Execution counts: 32 supplier calls, 0 teacher calls, 0 retries, 0 escalations.
The prepared run contained zero responses before execution and now contains 32
responses, 32 validators, and 32 scorecards. Prior raw runs and historical
evidence were not modified.

## Decision

`PRIMARY_CHARACTERIZATION=ATOMS_WORK_DIRECT_SCOPE_COMPOSITION_FAILS`

`NEXT_DECISION=VALIDATE_ATOMIC_SCOPE_COMPOSITION_STABILITY`

The next useful step is stability validation of this decomposition, ideally with
fixtures that independently cross target authorization and operation
authorization before drawing stronger architectural conclusions.
