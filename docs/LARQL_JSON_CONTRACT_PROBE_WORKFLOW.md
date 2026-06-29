# LARQL JSON Contract Probe Workflow

This workflow captures a reusable pattern from the absence-of-evidence
experiment: a LARQL rule is consulted, turned into a bounded runtime context,
compressed into a strict JSON contract prompt, run through a bounded model
call, scored mechanically, and then independently reviewed before any closeout
or follow-up action.

## Workflow Ladder

1. installed LARQL rule
2. runtime consultation context
3. JSON contract prompt
4. bounded model call
5. JSON contract scorer
6. independent JSON contract review
7. pass/fail closeout

## Why This Pattern Matters

JSON contracts narrow model degrees of freedom. That makes the task easier for
small models to satisfy in a guided capability setting, while still keeping the
output shape bounded and inspectable.

Scorers are useful, but they are not authoritative. The independent review
still matters because it can catch semantic drift that a scorer misses or
over-accepts.

Passing a JSON contract does not authorize candidate promotion, runtime-rule
modification, training, dataset creation, durable memory, model mutation, or
automatic failure-to-curriculum capture. Those remain separate, explicit,
reviewed decisions.

Training or export remains an explicit opt-in future step only.

## Boundary Reminder

This pattern is for bounded evidence handling, not autonomous authority. The
reviewer decides whether the evidence is actually acceptable for the next
state.

