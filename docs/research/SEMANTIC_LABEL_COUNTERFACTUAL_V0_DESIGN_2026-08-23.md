# Semantic Label Counterfactual V0

Status: frozen design; no inference has run.

This corrected successor supersedes the unexecuted `bc7aaa5f959bd362456f09b68f951f03dc58d86e` freeze. The predecessor had two pre-inference defects: Arm B admissibility used Arm A canonical labels, and two fixture requests did not match their preregistered semantic classes. No model response existed, so scientific evidence was not contaminated.

This successor follows the enum-order closeout. The enum-order experiment
produced `inspect` under both enum orders, with zero paired output changes;
therefore the literal-label hypothesis is tested next.

The paired arms use six fresh, genuinely unresolved semantic requests and the
same runtime request, neutral target, independent authority, preflight,
semantic information gap, model, settings, and counterbalanced order.

Arm A retains the current labels and enum positions:

```json
{"presence":"observe_presence","inspect":"inspect","enum":["inspect","observe_presence","unresolved"]}
```

Arm B replaces only the semantic label tokens while preserving their meanings
and positions:

```json
{"presence":"class_alpha","inspect":"class_beta","enum":["class_beta","class_alpha","unresolved"]}
```

The prompt definitions are generated from the same template. A pair audit
normalizes the label tokens and requires definition equivalence. The mapping
from neutral labels to canonical semantic meaning is frozen interface metadata
and is not derived from task expectations or runtime authority. Runtime
authority allows both canonical operations for every semantic task, so it
cannot classify or repair the model response.

Each task runs once in each arm in A/B, B/A, A/B, B/A, A/B, B/A order. The
prepared budget is 12 model calls and zero tool calls. The experiment changes
no definitions, examples, sampling settings, model, deterministic grammar,
authority, production interface, or qualification state.

Primary outcome: whether neutral labels recover the presence semantic class
after deterministic label mapping. No result automatically qualifies the
supplier or changes production routing.

Next decision after a later operator execution is selected from the frozen
label-counterfactual interpretation rules; this design itself makes no claim
about the outcome.
