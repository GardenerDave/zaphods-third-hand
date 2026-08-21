# Erratum: Crossed Scope Factorial Interpretation

This additive erratum corrects interpretation language only. The crossed
factorial raw run, task manifest, validator artifacts, aggregate, and hashes
remain unchanged.

The Qwen3 1.7B-labeled / 2.032B operative supplier emitted `true` on all 16
tasks. Its output therefore had zero response variance:

- operation type did not affect the observed response;
- held-distractor presence did not affect the observed response;
- authority relation did not affect the observed response.

Outside-authority tasks scored correct only because `true` was their expected
value. This result does not independently demonstrate recognition of the
outside-authority branch. Likewise, the earlier statement that authority
status was the sole factor tracking correctness must not be read as evidence
that authority status affected the supplier response; it affected expected
truth, while the response was constant.

The concrete output example
`{"scope_expansion_required": true}` is a one-sided prompt-interface factor.
Its causal role is not established by the existing run.

`ONE_SIDED_BOOLEAN_EXEMPLAR_CONFOUND=UNRESOLVED`

The next authorized diagnostic is a three-arm interface isolation using the
same 16 factorial tasks: the original true exemplar, a false exemplar, and a
value-neutral interface. No prior evidence is rewritten by that diagnostic.
