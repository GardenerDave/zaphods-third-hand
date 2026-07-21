# Delegation Plan Neutrality and Supervisor Semantic Integration Calibration v1

Date: 2026-07-20

Status: failed

Branch: `feature/context-distiller-focused-passes-v1`

Source audition run ID: `20260720_101004`

Prior supervisor-review calibration: `.work/model_delegation_audition/20260720_101004/supervisor_review_calibration_v1/`

Authority: review-only

## Summary

This calibration tested whether removing directional framing from the preserved supervisor plan changed the final 30B semantic outcome.

The live supervisor endpoint returned the expected model ID:

- `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`

The plan was directional, but the neutralized evidence bundle removed the plan fields as substantive evidence. The live supervisor still produced a conclusion that overclaimed the preserved execution evidence, so the semantic failure was reproduced after removing plan bias.

## Plan Bias Audit

Plan bias was found in the preserved supervisor plan.

Directional fields included:

- `expected_facts`
- `stop_condition`
- `integration_rule`

These fields did not merely route investigation. They also asserted or implied the outcome to be found, so the plan was directional rather than neutral.

The neutralization result was recorded as:

- `directional`

## Neutral Evidence Bundle

Neutral evidence bundle hash:

- `573046686ab257eb6a949ef1d3f3e227c826e1361bbd44e85ab7f800686675ae`

The neutral bundle preserved:

- the original question
- subtask IDs
- validated worker outputs
- worker validation results
- selected source excerpts
- source hashes
- excerpt hashes
- retry history
- prompt-patch history

The bundle treated the supervisor plan as procedural metadata, not repository evidence.

## Live Review Calls

- Total live supervisor calls: 3
- Endpoint alias recorded in artifacts: `supervisor`
- Inference temperature: `0` on every call
- Thinking disabled: yes, on every call

Structural results:

- attempts 1 and 2: structurally valid
- attempt 3: structurally valid

Semantic result:

- all three attempts still overclaimed the preserved execution evidence

## What Changed

Removing directional plan content did not change the semantic outcome.

The live supervisor continued to claim that manifest chunk controls affect the focused-pass `selected_input.txt` output even though the preserved evidence only shows declared behavior, recorded controls, helper existence, and documentation claims. The semantic failure therefore was not caused solely by the preserved plan’s directional wording.

## Recommended Model-Free Checks

- audit whether plans contain expected outcomes in `expected_facts` and `stop_condition`
- keep procedural plan text separate from evidence bundles
- require explicit distinction between declared behavior and invoked execution-path evidence
- reject conclusions that rely on documentation alone

## Aider Readiness

Not justified.

## Final Classification

failed

## Review-Only Authority Statement

This calibration was review-only. It did not modify the Context Distiller implementation, canonical context, prompt library, or training curriculum, and it did not authorize Aider, merge, push, or unattended execution.
