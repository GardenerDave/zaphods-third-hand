# Held-clarification position/presence isolation

Exploratory candidate-only experiment; not Stage B evidence.

This screen reuses the exact 16-task crossed scope manifest and the completed
single-predicate scope interface. It holds the main predicate, output mapping,
schema, runtime, and task evidence fixed while varying only the position or
presence of the final held-target clarification.

The three arms are:

- L: current control, clarification last;
- M: the identical clarification before the output-mapping sentence;
- A: clarification absent.

L must equal the completed single-predicate prompt byte-for-byte. M changes
only the clarification position. A removes only that sentence and its
separator. Six arm permutations are assigned deterministically across the 16
tasks as evenly as possible, for 48 total supplier calls.

The task manifest SHA256 is
`2ceffafeded8942ce717af20f91bef07994b8d3ed6df1f09a3246b6135cb0c96`.
The main predicate, mapping sentence, and clarification are frozen from the
single-predicate representation. The structure-only schema permits both
boolean values and contains no value cue.
