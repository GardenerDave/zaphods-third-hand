# Historical Firewall-Marker Erratum

The preserved Stage B field `evaluator_loaded_during_acquisition=false` is not a claim that no evaluator file bytes were accessed. The prior harness accessed evaluator bytes for preflight hash verification while loading no evaluator JSON semantics.

| Historical property | Finding |
|---|---|
| evaluator file-byte access during acquisition | true |
| evaluator semantic load | false |
| evaluator runtime influence | false |
| evaluator supplier visibility | false |

This additive note does not rewrite the Stage B result or raw artifacts. The explicit-interface calibration freeze uses separate fields and requires acquisition to run without opening evaluator/scoring artifacts after preflight.
