# Local 30B Supervises 1.7B Delegation Audition

Date: 2026-07-20

Status: failed

Branch: `feature/context-distiller-focused-passes-v1`

## Scope

Question: do the manifest chunk controls in `local_harness/context_distiller_manifest.py` actually affect the text written to `selected_input.txt` and sent to focused model passes?

Authority: review-only.

Tracked report note: this file was added during the corrected rerun. No implementation, canonical context, curriculum, or tracked prompt-library content was modified.

## Preflight History

The earlier endpoint-configuration run was an infrastructure preflight failure. It made no model calls and does not count as evidence against the model hierarchy or Aider readiness.

Aider readiness for that blocked attempt: not evaluated.

## Live Model IDs

- Supervisor: `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`
- Worker: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`

Both were resolved from live `/models` responses on the configured supervisor and worker endpoints. Endpoint aliases in this report are `supervisor` and `worker`; no private addresses are recorded.

## Delegation Plan

The live supervisor retry produced a validated plan under:

- `.work/model_delegation_audition/20260720_101004/supervisor_plan/attempt_002/model_content.json`
- `.work/model_delegation_audition/20260720_101004/supervisor_plan/validated_plan.json`

The validated plan contained three subtasks:

1. `analyze_manifest_chunk_controls`
2. `examine_chunker_integration`
3. `verify_workflow_documentation`

The earlier supervisor-plan attempt remained preserved as a failed structural attempt, with an audition-local prompt-patch candidate recorded under:

- `.work/model_delegation_audition/20260720_101004/prompt_patch_candidates/attempt_001/`

## Worker Calls

All three worker calls were live, independent, and structurally valid.

- `.work/model_delegation_audition/20260720_101004/worker_calls/analyze_manifest_chunk_controls/attempt_001/`
- `.work/model_delegation_audition/20260720_101004/worker_calls/examine_chunker_integration/attempt_001/`
- `.work/model_delegation_audition/20260720_101004/worker_calls/verify_workflow_documentation/attempt_001/`

Worker validation results:

- `analyze_manifest_chunk_controls`: passed
- `examine_chunker_integration`: passed
- `verify_workflow_documentation`: passed

Summary of the worker findings:

- The manifest runner writes `selected_input.txt` from source selection and line-range filtering in `local_harness/context_distiller_manifest.py`.
- `local_harness/context_chunker.py` contains chunk-planning helpers, but the manifest execution path does not invoke them directly.
- The workflow documentation describes manifest-mode chunk controls as part of the broader distiller workflow, but documentation is not the execution path.

## Supervisor Review

The first live supervisor review attempt was structurally invalid. It returned a different schema than requested.

- `.work/model_delegation_audition/20260720_101004/supervisor_review/attempt_001/`

I used the one permitted structural retry. The retry was also malformed JSON and did not normalize to the required exact contract.

- `.work/model_delegation_audition/20260720_101004/supervisor_review/attempt_002/`

Because the live supervisor review did not produce the required exact JSON contract, the delegation audition did not complete successfully.

## Final Classification

failed

The worker phase produced useful evidence, but the 30B integration/review step did not satisfy the required schema and could not be treated as a valid terminal review.

## Aider Readiness

Not justified.

This run does not establish Aider-backed readiness because the final supervisor review remained structurally invalid.

## What the Evidence Shows

Repository evidence points to a distinction between declared manifest controls and the actual execution path:

- `local_harness/context_distiller_manifest.py` writes `selected_input.txt` from selected sources and filtered source text.
- `local_harness/context_chunker.py` provides chunk helpers, but the manifest runner does not route `selected_input.txt` through those helpers.
- `docs/CONTEXT_DISTILLER_WORKFLOW.md` describes manifest mode, chunk controls, focused passes, and review boundaries, but it does not by itself prove the chunk helpers are invoked by the execution path.

The live worker and supervisor evidence therefore supports a narrow conclusion: the manifest controls are recorded and documented, while the execution path for `selected_input.txt` is driven by source selection and line-range filtering rather than by the chunker helpers.

## Run Artifacts

- Run root: `.work/model_delegation_audition/20260720_101004/`
- Supervisor plan validation: `.work/model_delegation_audition/20260720_101004/supervisor_plan/attempt_002/validation.json`
- Worker summary: `.work/model_delegation_audition/20260720_101004/worker_calls/worker_summary.json`
- Supervisor review attempt 1: `.work/model_delegation_audition/20260720_101004/supervisor_review/attempt_001/model_output.raw.json`
- Supervisor review attempt 2: `.work/model_delegation_audition/20260720_101004/supervisor_review/attempt_002/model_output.raw.json`

## Final Counts

- Supervisor plan attempts: 2
- Supervisor review attempts: 2
- Worker calls: 3
- Worker retries: 0
- Prompt-patch candidates: 1

## Notes

- The prior blocked attempt remains preserved as infrastructure preflight evidence.
- The live endpoints were reachable and the exact live model IDs were discovered from the endpoints themselves.
- No canonical context files were modified during this audition.
