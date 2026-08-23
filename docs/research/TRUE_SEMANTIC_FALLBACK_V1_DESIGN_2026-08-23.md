# Oracle-clean true semantic fallback V1

This V1 supersedes the unexecuted contaminated freeze
`abbb0c1d44b1eadfdc8b23cbeaa33e8da7d994f6`. The V0 artifacts remain unchanged.
Its contamination was pre-inference only: runtime authority was built from the
intended class and target basenames exposed class labels. V0 produced zero
model calls, zero tool calls, and zero responses, so no scientific evidence is
rescored.

## Question

Can the existing 1.7B supplier provide a genuinely missing operation class when
one safe target is known, no ambiguity or risk exists, deterministic operation
derivation is unresolved, and both `observe_presence` and `inspect` remain
plausible?

## Oracle-clean design

V1 uses neutral `TSF_*` target names, interleaves three presence and three
inspect requests, and gives every task the same independently authored runtime
authority set:

```json
["observe_presence", "inspect"]
```

The evaluator alone stores the expected semantic class. Runtime cases contain
only request text and environment authority. The model receives only the
request and the enum contract:

```json
{"operation_class_candidate":"observe_presence|inspect|unresolved"}
```

It emits no target, tool, supplier, authority, success, or terminal decision.

## Eligibility

Only the six true-fallback tasks can call the model. Preflight must establish:

- exactly one safe target;
- safe bounded operation language;
- no multi-operation or multi-target ambiguity;
- unresolved frozen deterministic operation derivation;
- both bounded semantic classes remain candidates.

The two deterministic controls and two fail-closed controls plan zero model
calls. Presence classifications may use the existing exact-target read-only
observer. Inspect classifications are correctly review-gated because no
qualified inspect actuator exists.

## Evidence boundary

Semantic classification correctness is scored independently from authority,
tool availability, execution coverage, and terminal success. Any wrong class is
preserved as a genuine semantic result; authority never repairs it. Automatic
qualification promotion remains disabled.
