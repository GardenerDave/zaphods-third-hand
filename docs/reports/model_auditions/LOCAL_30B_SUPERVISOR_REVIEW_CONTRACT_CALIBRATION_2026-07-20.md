# 30B Supervisor Review Contract Calibration v1

Date: 2026-07-20

Status: failed

Branch: `feature/context-distiller-focused-passes-v1`

Source audition run ID: `20260720_101004`

Authority: review-only

## Summary

This calibration tested only the final 30B review serialization boundary using the preserved delegation-audition evidence bundle.

The live supervisor endpoint was reachable and returned the expected model ID:

- `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`

The calibration achieved three consecutive structurally valid review objects, but the generated conclusion remained semantically inconsistent with the preserved evidence. Because the full success condition required both structural and semantic acceptance, the calibration failed.

## Evidence Bundle

Fixed evidence bundle hash:

- `5fcdb0f3b39bed8738c34236ff9932b1ca2d414841099746099af33752a2d64e`

Preserved bundle sources:

- validated supervisor plan
- worker summary
- three validated worker outputs
- retry and prompt-patch summary

No additional substantive repository files were reread for evidence beyond the preserved audition artifacts.

## Strategies Tested

1. Strategy A, minimal strict contract
2. Strategy B, thinking disabled
3. Strategy C, minimal valid example
4. Strategy C with prompt-patch path normalization

Strategy D was not needed because the calibration reached the live-call cap without a full semantic pass.

Strategy E was not needed because the valid review objects were directly parseable.

## Live Calls

- Total live supervisor calls: 6
- Endpoint alias recorded in artifacts: `supervisor`
- Inference temperature: `0` for every attempt
- Thinking disabled: yes, for attempts 2 through 6

## Attempt Outcomes

- `attempt_001`: timeout failure
- `attempt_002`: malformed JSON / truncated response
- `attempt_003`: structurally invalid due to absolute prompt-patch path
- `attempt_004`: passed structural validation
- `attempt_005`: passed structural validation
- `attempt_006`: passed structural validation

The three consecutive structural passes were produced by attempts 4, 5, and 6 under the same evidence bundle hash.

## Structural Results

The passing attempts satisfied the exact review contract:

- exact top-level keys
- one worker assessment per declared subtask
- valid assessment enums
- nonempty conclusion
- repository-relative allowlisted evidence paths
- nonempty retry summary
- `ready_for_review: true`
- no execution authorization in the result

The only structural correction needed during calibration was normalization of the prompt-patch path to a `.work`-relative artifact path.

## Semantic Check

Semantic acceptance failed.

The generated conclusion stated that manifest chunk controls do affect the text written to `selected_input.txt` and sent to focused model passes, but the preserved evidence shows that the manifest runner writes `selected_input.txt` from source selection and line-range filtering, while the chunk helper code exists separately and is not demonstrated as the execution path that drives the focused-pass selected text.

Result:

- structural contract: satisfied
- semantic consistency with preserved evidence: failed

## Prompt-Patch Summary

One calibration-local prompt-patch candidate was preserved:

- `.work/model_delegation_audition/20260720_101004/prompt_patch_candidates/attempt_001`

No prompt-patch candidate was promoted to the tracked prompt library.

## Extraction

Deterministic extraction was not used.

## Remaining Limitations

- The live supervisor can serialize a valid review object.
- The generated review can still overstate the evidence and fail the semantic boundary.
- This calibration does not justify Aider-backed follow-on editing.

## Aider Readiness

Not justified.

## Final Classification

failed

## Review-Only Authority Statement

This calibration was review-only. It did not modify the Context Distiller implementation, canonical context, prompt library, or training curriculum, and it did not authorize Aider, merge, push, or unattended execution.
