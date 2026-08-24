# Semantic Inspect Label Robustness V0

Status: frozen model-free design; no inference has run.

Motivating evidence is the factorial closeout
`5ddf5b425ad1209aab6bbea196db82494a8b0046`. It found a bounded adverse
effect associated with the literal `inspect` label on presence tasks while
inspect-task classification remained stable. This confirmation holds the
presence label constant and auditions three inspect-label replacements.

## Frozen arms

| Arm | Presence label | Inspect label | Enum order |
|---|---|---|---|
| A | `observe_presence` | `inspect` | `inspect, observe_presence, unresolved` |
| B | `observe_presence` | `class_beta` | `class_beta, observe_presence, unresolved` |
| C | `observe_presence` | `operation_two` | `operation_two, observe_presence, unresolved` |
| D | `observe_presence` | `examine_target` | `examine_target, observe_presence, unresolved` |

All inspect labels map deterministically to canonical `inspect`. Only the
inspect surface token changes; definitions, requests, settings, semantic
positions, authority, and target extraction remain constant.

## Holdout and schedule

There are 12 fresh true-semantic-fallback requests, interleaved
presence/inspect, with six tasks in each class. Every task is run once in all
four arms: 48 planned calls. Runtime authority independently permits both
canonical classes and contains no evaluator answer.

The class-stratified schedule uses six Latin-derived rotations separately for
each semantic class. Each arm occurs 12 times overall. Within each class the
arm position counts differ by at most one, and no class is systematically
earlier or later for an arm.

The frozen evaluator is separate and is the sole scoring authority. The
prepared run contains no responses, no model calls, and no tool calls.

## Preregistered interpretation

The primary comparisons are all six unordered arm pairs: A/B, A/C, A/D, B/C,
B/D, and C/D. Presence and inspect denominators remain separate, with explicit
replacement-vector identity checks and bounded interpretation markers. The
confirmation does not qualify a supplier or change production routing.

The predecessor freeze `e40ffca5ebaf0a56cbf242c1e5632a0a21197ad9` is preserved
as an unexecuted superseded pre-inference freeze because its analysis omitted
the three replacement-stability comparisons. Its zero-call state means no
scientific model evidence was contaminated.

Authoritative prepared run:

`.work/model_size_supplier_floor/semantic_inspect_label_robustness_v0/run_20260824T022200Z`

Driver SHA256:

`2deff9cacf71c6d402b51c4347a5d2bb45c93b0cb9f98344c42be334c2d73bfd`
