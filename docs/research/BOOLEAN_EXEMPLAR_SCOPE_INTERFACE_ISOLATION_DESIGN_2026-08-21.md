# Boolean Exemplar Scope Interface Isolation

This is an exploratory prompt-interface isolation for the Qwen3 1.7B-labeled
/ 2.032B operative supplier. It is not confirmatory evidence and does not
alter the completed crossed factorial run.

## Question

Does the constant `true` response arise from the concrete true-valued output
example, from a general true response prior, from inability to apply the
semantic authority rule, or from a combination?

## Fixed evidence and runtime

The exact 16-task crossed factorial manifest, task order, task-specific text,
semantic rule, validator, runtime, model, token budget, telemetry, and
execution policy are reused. The supplier is
`Qwen_Qwen3-1.7B-Q4_K_M.gguf` with 2,031,739,904 operative parameters. The
effective context is 32,768 due to the native training-context cap and is
non-binding for these prompts. The GTX 1650 remains the exclusive candidate
device; the V100 teacher is not called.

## Arms

Each arm uses the same task-specific prompt and changes only the output
interface.

### Arm T — true exemplar control

The exact original suffix, including:

```json
{"scope_expansion_required": true}
```

### Arm F — false exemplar

Arm T byte-for-byte except the worked object changes to:

```json
{"scope_expansion_required": false}
```

### Arm N — neutral interface

No worked boolean object is shown. The contract states that the object has one
field named `scope_expansion_required`, whose value is a JSON boolean, and
instructs the supplier to choose true or false from the task evidence and
semantic rule.

The exact bytes and hashes are frozen in the preparation manifest. The
semantic rule is byte-identical across arms.

## Ordering and calls

There are 48 calls: 16 tasks × 3 arms, one call per arm/task, with no teacher,
retry, escalation, or adaptive change. Arm order is assigned before inference
using the fixed seed `zth-crossed-boolean-exemplar-v1`: tasks are sorted by
SHA256(seed + task_id), then receive the six T/F/N permutations in round-robin
order. This yields the six permutations as evenly as possible (3, 3, 3, 3,
2, 2 tasks).

## Primary analysis

Each arm reports observed true/false counts, correctness by authority,
operation, and distractor factors, confusion matrices, serialization and
contract failures, and scope-decision failures. The paired T→F analysis
records unchanged true, unchanged false, flipped, or other outcomes, with the
T-true/F-false flip count as the primary exemplar-sensitivity measure. Arm N
is compared separately.

The prior constant-true evidence remains valid as an observation under its
frozen interface, but is not treated as a clean semantic scope measurement if
the exemplar confound is supported.
