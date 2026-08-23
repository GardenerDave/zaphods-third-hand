# TRUE_SEMANTIC_FALLBACK_V2 model-free failure diagnosis

This diagnosis uses only preserved V1/V2 artifacts. No model, teacher, tool,
retry, response repair, grammar change, or qualification change was performed.

## Observed boundary

V2 returned `inspect` for all six balanced true-fallback tasks. The frozen
semantic classes were presence, inspect, presence, inspect, presence, inspect.
Thus:

```text
INSPECT_OUTPUTS=6/6
OBSERVE_PRESENCE_OUTPUTS=0/6
UNRESOLVED_OUTPUTS=0/6
SEMANTIC_CLASSIFICATION_CORRECT=3/6
PRESENCE_CORRECT=0/3
INSPECT_CORRECT=3/3
WRONG_SAFE_CLASSIFICATIONS=3
```

V1 independently returned `inspect` for its one preserved presence task. The
bounded developmental series is therefore 4/4 presence failures and 3/3
inspect successes, with `3/7` total correct across seven observations. This
is not treated as an IID benchmark or a universal accuracy estimate.

## What the run rules out

The six V2 tasks had one independently authorized neutral target, the same
allowed operation set `["observe_presence", "inspect"]`, no evaluator fields
in runtime, unresolved deterministic operation derivation, and both candidate
classes remaining. Request-target and request-operation mutation tests left
authority unchanged. All six responses were strict valid JSON, enum-valid, and
admissible. The downstream plans were written successfully and all six were
contained by `NO_QUALIFIED_EXECUTION_SUPPLIER` without tool calls.

The evidence therefore does not support these as explanations:

- `TARGET_LABEL_LEAK`;
- `REQUEST_DERIVED_TARGET_AUTHORITY`;
- `EXPECTED_CLASS_AUTHORITY_LEAK`;
- `EVALUATOR_RUNTIME_LEAK`;
- `DETERMINISTIC_OPERATION_ALREADY_AVAILABLE`;
- `MODEL_TARGET_EXTRACTION_FAILURE`;
- `OUTPUT_CONTRACT_FAILURE`;
- `AUTHORITY_DENIAL_AS_CLASSIFIER`.

## Hypothesis matrix

### H1 — CLASS_PRIOR_OR_OUTPUT_LABEL_BIAS

Support: every model-called task selected `inspect` despite a balanced 3/3
semantic holdout, and the choice was stable across V1 and V2.  
Contradiction/limit: there was no enum-order or label counterfactual, so this
cannot be separated from prompt or wording effects.  
Discriminator: hold requests and runtime constant while counterbalancing enum
order and using an equivalent output representation.

### H2 — CLASS_DEFINITION_ASYMMETRY

Support: `inspect` has a short direct definition (“examine or look at”), while
`observe_presence` has a longer state-oriented definition with several cues;
the model succeeded on all direct inspect paraphrases.  
Contradiction/limit: the definitions are explicit and the sample is small;
definition length alone is not causal evidence.  
Discriminator: a frozen, meaning-preserving definition-balance intervention
with no task or authority changes.

### H3 — INDIRECT_PRESENCE_LANGUAGE_NOT_BOUND_TO_EXISTENCE_CLASS

Support: all failed presence requests used indirect containment/storage
language (`part of this repository`, `stored here`, `contained in the
repository`), while inspect requests used direct examination language.
V1’s presence wording also failed.  
Contradiction/limit: the prompt explicitly defines presence broadly enough to
include being present or available; direct-vs-indirect language is confounded
with class.  
Discriminator: a balanced semantic holdout crossing direct and indirect
presence wording while holding class definitions and label order fixed.

### H4 — STRUCTURED_DECODING_OR_ENUM_ORDER_EFFECT

Support: all outputs selected one enum value and the frozen schema exposes an
ordered enum; a systematic decoding preference is possible.  
Contradiction/limit: no reversed-order or alias-schema arm exists.  
Discriminator: a pre-registered enum-order counterfactual with identical
requests, model settings, and downstream scoring.

### H5 — INTERFACE_LABEL_DIFFICULTY

Support: `observe_presence` is a compound technical label, whereas `inspect`
is a common verb, and the model consistently emits the common label.  
Contradiction/limit: the prompt supplies semantic definitions, so label
naturalness is only a candidate mechanism.  
Discriminator: compare semantically neutral/short canonical labels while
keeping the operation definitions and evaluator projection fixed.

### H6 — GENERAL_SEMANTIC_CAPABILITY_FAILURE

Support: presence classification failed across both V1 and V2.  
Contradiction: inspect classification succeeded 3/3, output structure was
perfect, and safe candidate admissibility was perfect. The observed boundary is
therefore not well described as general semantic or interface incapacity.
Discriminator: only retain this hypothesis if controlled class/definition/label
interventions fail to move presence classification.

## Diagnosis disposition

No single causal hypothesis is selected. The supported characterization is a
stable bounded class-specific collapse toward `inspect` across this small
developmental series. It is narrower than a general supplier failure, but its
mechanism remains unresolved.

`NEXT_DECISION=DESIGN_BOUNDED_SEMANTIC_CLASSIFICATION_INTERVENTION`

Potential interventions are not executed here. Qualification remains unchanged.
