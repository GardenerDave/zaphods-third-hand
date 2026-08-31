# Transport Qualification vs Model Capability Correction Negative Result

- card id: `transport_qualification_vs_model_capability_v1`
- tested_correction_sha256: `f3a6aa6b3c68c5932bd8e0bbfdcda6b0b59e86a9b4662835cc21d27af39b6900`
- current_held_card_sha256: `d631a031b65fcbb65c295c20175cbf51000fee9396bc6238ba1c2d6e71623397`
- positive control task: transport qualification versus model capability
- worker: `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`
- limitation: the positive-control prompt wording already exposed much of the intended epistemic distinction, so the negative result remains informative but is not a pure test of neutral framing

This correction was exercised through the existing correction-aware path and
reached the worker. The resulting response completed mechanically, and the
explanation became more cautious, but the headline claim still upgraded
transport qualification into model capability.

The frozen targeted correction therefore improved boundary language in the
explanation but did not correct the primary conclusion on its known positive
control failure.

Holdout transfer tests were not run because the positive control did not meet
the behavioral success criterion.

This report preserves the negative result without promoting the correction.
