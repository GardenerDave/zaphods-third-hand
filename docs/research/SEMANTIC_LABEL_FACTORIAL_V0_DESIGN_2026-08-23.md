# Semantic Label Factorial V0

Status: frozen design; no inference has run.

This four-arm factorial follows the corrected semantic-label counterfactual.
That experiment held requests, definitions, authority, semantic positions,
model, and settings constant while changing both semantic label tokens. The
current-label arm scored 3/6 and the neutral-label arm scored 6/6, recovering
all three presence tasks. This successor isolates which literal label causes
the interference.

The four arms are:

| Arm | Presence label | Inspect label | Position 1 | Position 2 |
|---|---|---|---|---|
| A | `observe_presence` | `inspect` | `inspect` | `observe_presence` |
| B | `class_alpha` | `class_beta` | `class_beta` | `class_alpha` |
| C | `class_alpha` | `inspect` | `inspect` | `class_alpha` |
| D | `observe_presence` | `class_beta` | `class_beta` | `observe_presence` |

`unresolved` is position 3 in every arm. Canonical mappings are frozen
interface metadata, not runtime task expectations. Prompt definitions are the
same after deterministic label-token normalization. Runtime authority allows
both canonical operations for every task.

Six fresh genuine-semantic tasks are run in all four arms: three presence and
three inspect, interleaved P/I/P/I/P/I. The planned budget is 24 model calls,
with no tool calls. The schedule is a balanced Latin-style rotation:

```text
A B C D
B C D A
C D A B
D A B C
A C B D
B D A C
```

The factorial comparisons are A/C (presence label), A/D (inspect label), B/C,
and B/D. This is a bounded diagnostic interface experiment only. It does not
qualify a supplier, change production routing, teach, or modify the semantic
definitions.

## Superseding hardened freeze

The predecessor freeze `8e846966876625926e20eafa74ec25058155ed85` was
prepared with zero model calls and zero response files. It is preserved as an
unexecuted superseded pre-inference freeze. Model evidence was not
contaminated. A model-free audit found two control defects:

- global position counts passed, but arm positions were not balanced within
  the presence and inspect strata;
- the closeout constructed evaluator cases but used `specs()` as the scoring
  answer key.

The successor repairs only those control-plane issues. Its exact
class-stratified schedule is:

```text
slff-001: A B C D   (presence)
slff-002: D C B A   (inspect)
slff-003: B C D A   (presence)
slff-004: C B A D   (inspect)
slff-005: C D A B   (presence)
slff-006: B A D C   (inspect)
```

Within the presence stratum, arm positions are A `{1,3,4}`, B `{1,2,4}`,
C `{1,2,3}`, D `{2,3,4}`. Within inspect they are A `{2,3,4}`, B
`{1,2,3}`, C `{1,2,4}`, D `{1,3,4}`. The successor closeout scores only
from its frozen evaluator manifest and reports overall, presence, inspect,
output-distribution, and pairwise A/C, A/D, B/C, and B/D metrics.

The authoritative prepared successor run is
`.work/model_size_supplier_floor/semantic_label_factorial_v0/run_20260823T235000Z`.
It contains 24 planned calls, zero model calls, zero tool calls, and zero
responses. The successor remains an unexecuted freeze; no factorial result is
claimed here.
