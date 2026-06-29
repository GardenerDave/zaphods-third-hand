# Absence-of-Evidence LARQL Model Context Failure Mode — 2026-06-28

This report documents a failure mode discovered during the absence-of-evidence LARQL repair loop.

The failure class is absence-of-evidence epistemic-boundary drift: a small model kept drifting from a bounded search result into an unconditional or premature nonexistence-style conclusion, then toward irreversible lifecycle/file actions. A tested sub-hypothesis was forbidden-phrase priming / negative-instruction contamination, but the evidence shows that explanation is incomplete on its own.

The relevant identifiers are:

- `source_failure_id`: `absence_of_evidence_file_authority.real`
- `candidate_id`: `absence_of_evidence_file_authority`
- `rule_id`: `absence_of_evidence_file_authority_v0`

The installed local runtime rule was consulted into a runtime context packet and injected into a bounded model-context probe. The model-context runner produced evidence, and the probe scorer passed after prompt tightening. However, an independent review still rejected the result because the response continued to make an unconditional nonexistence-style claim from bounded search evidence.

That sequence matters:

1. A freeform model-context prompt was rejected by review.
2. A stronger prompt forbidding unconditional nonexistence claims was rejected by review.
3. A fixed five-part response scaffold was rejected by review.
4. The model-facing prompt was then repaired to remove the literal forbidden phrase, and the scorer passed, but independent review still rejected the output.

The conclusion is that the failure is broader than forbidden-phrase priming alone. Prompt wording alone was not enough to reliably enforce the absence-of-evidence boundary for this model/task.

What this proves:

- The installed LARQL rule can be consulted and injected into a model prompt.
- The model-context runner can produce evidence.
- The scorer alone can be insufficient.
- The independent review gate can catch semantic failures that scorer-only or prompt-only repair loops do not resolve.
- For this small model/task, prompt wording alone was not enough to reliably enforce the absence-of-evidence boundary.

What this does not prove:

- It does not prove LARQL failed as a governance mechanism.
- It does not prove the rule is wrong.
- It does not prove training is needed.
- It does not authorize training data, dataset artifacts, durable memory, candidate promotion, runtime-rule modification, model mutation, or automatic failure-to-curriculum capture.

Boundary facts:

| boundary | value |
| --- | --- |
| training_data_written | false |
| dataset_artifact_written | false |
| durable_memory_written | false |
| candidate_promotion_authorized | false |
| runtime_rule_modification_authorized | false |
| model_weights_mutated | false |
| automatic_failure_to_curriculum_capture_authorized | false |

Repair hypotheses:

1. Prompt contamination / forbidden-phrase priming

   - Tested by removing the literal forbidden phrase from the model-facing prompt.
   - Did not resolve the review rejection.

2. Stronger structured output

   - Tested with a five-part scaffold.
   - Did not resolve the review rejection.

3. Next possible repairs

   - Use a stricter machine-readable output contract.
   - Constrain the response to JSON fields.
   - Use post-generation rewriting only as a separate reviewed artifact.
   - Test a different small model.
   - Treat this as a candidate for optional future supervised fine-tuning data only after explicit opt-in approval.

Recommended next step:

Preserve this as a valuable failure artifact before attempting further prompt repair. Optionally create a new repair branch or probe using a JSON-only response format. Keep the review gate strict.

## Notes

This report is about evidence-boundary drift, not a model-role claim, and it uses supervised terminology only where training is explicitly discussed.
