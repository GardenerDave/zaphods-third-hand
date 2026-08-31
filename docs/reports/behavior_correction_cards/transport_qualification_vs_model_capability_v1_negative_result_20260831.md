# Transport Qualification vs Model Capability Correction Negative Result

- card id: `transport_qualification_vs_model_capability_v1`
- card sha256: `f3a6aa6b3c68c5932bd8e0bbfdcda6b0b59e86a9b4662835cc21d27af39b6900`
- positive control task: transport qualification versus model capability
- worker: `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`

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
