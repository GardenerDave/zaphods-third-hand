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
