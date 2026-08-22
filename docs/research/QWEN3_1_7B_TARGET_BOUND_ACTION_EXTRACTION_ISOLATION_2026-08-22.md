# Qwen3 1.7B-labeled target-bound action extraction isolation

This exploratory probe followed the model-free action-head audit and used a
fresh eight-task, four-pair role-reversal design. It did not modify prior
evidence or test authorization, scope, membership, or policy.

## Bindings

- Run: `.work/model_size_supplier_floor/qwen3_1_7b_target_bound_action_extraction_isolation/run_20260822T034500Z/`
- Supplier: Qwen3 1.7B-labeled / 2,031,739,904 operative parameters
- Artifact SHA256: `72c5c3cb38fa32d5256e2fe30d03e7a64c6c79e668ad84057e3bd66e250b24fb`
- Task manifest SHA256: `869ad935f4fafcceb0d2ebd3b2266fa239f49ce9786dd5e7de421fe26a1fe409`
- Design SHA256: `1037b1754912aa3513147ba813930cd3db15278e0240413900029eae6bffe147`
- Probe manifest SHA256: `d198aad13e6d34a678d08df840f5c438ec5979386dcacff0453b80c789a83718`
- Aggregate SHA256: `53124d32394b37e9b0c31a6cbd7d7b91ca6f7f23c5d1cda90d63bfa2b476a54b`

The task set passed model-free role, lexical, position, and forbidden-term
audits before inference. All eight calls were distinct, with zero teacher
calls, retries, escalations, or adaptations.

## Results

- Parse-valid: 8/8
- Contract-valid: 8/8
- Exact target-bound-operation extraction: 5/8
- Pairwise role-reversal success: 1/4 pairs fully correct
- Secondary-action selections: 1/8
- Expected answer position first: 3/4 correct
- Expected answer position second: 2/4 correct

| Pair | Expected outcome | Classification | Detail |
|---|---:|---|---|
| action-pair-001 inspect/document | 1/2 | ONE_DIRECTION_CORRECT | task 002 returned `update` |
| action-pair-002 update/announce | 1/2 | ONE_DIRECTION_CORRECT | task 004 returned secondary `update` |
| action-pair-003 read/catalog | 2/2 | BOTH_RELATIONS_CORRECT | both directions correct |
| action-pair-004 alter/submit | 1/2 | ONE_DIRECTION_CORRECT | task 008 returned `delta` |

By verb pair: inspect/document 1/2, update/announce 1/2, read/catalog 2/2,
alter/submit 1/2. The only direct secondary-action selection was `update` in
task 004. The other two errors were unexpected outputs (`update` in task 002
and `delta` in task 008), not normalized into any expected action.

There is no demonstrated positional or lexical shortcut effect in this small
sample: both answer positions occur, both roles are balanced, and no single
position or verb identity perfectly predicts the output. The probe therefore
supports partial target-bound relation extraction, not a demonstrated robust
capability.

## Interpretation

`PRIMARY_CHARACTERIZATION=TARGET_BOUND_ACTION_EXTRACTION_PARTIAL`

`MODEL_ROLE=SEMANTIC_RELATION_EXTRACTION`

The supplier can resolve the target-bound action in some role reversals, but
three of four pairs are asymmetric. The remaining direct secondary-action
selection and unrelated outputs do not justify a clean positional or lexical
attribution.

`NEXT_DECISION=REPAIR_TARGET_ACTION_BINDING_INTERFACE`

The next repair should make the target-action relation more explicit while
retaining two-action role reversals. This remains exploratory architecture
evidence and does not change production routing or establish a model-size
floor.

## Resources

Level-2 GTX-1650 device-only telemetry: median / mean / p95 latency
`1332.3575 / 1334.740125 / 1416.081 ms`; mean / median energy
`40.0925 / 40.7375 J/action`; total `320.74 J`. These are descriptive
device-only measurements.
