# Supervised Capability Mining Run 1 synthesis

This report is deterministic evidence extraction from `.work/capability_batch_reviewed_v1`. No model calls were made, no trajectory artifacts were changed, and no prompt patch or curriculum example was activated. All findings below link to task IDs and the structured inventory in `synthesis/run_1_synthesis.json`.

## Outcome

The 1.7B passed 1 of 24 tasks unaided. The local 30B rescued 8 tasks; the external teacher rescued 9 after local retries failed. Six tasks remained unresolved. The hierarchy therefore demonstrates useful rescue behavior, but the dominant failure mechanism is contract/serialization compliance rather than a clean separation between reasoning families.

Task-family distribution: {"contradiction-handling": {"passes": 1, "trials": 1, "unresolved": 0}, "destructive-action-restraint": {"passes": 2, "trials": 2, "unresolved": 0}, "evidence-grounding": {"passes": 0, "trials": 1, "unresolved": 1}, "queue-authority-boundary": {"passes": 1, "trials": 4, "unresolved": 3}, "scope-authority-boundary": {"passes": 6, "trials": 8, "unresolved": 2}, "strict-structured-output": {"passes": 2, "trials": 2, "unresolved": 0}, "triage-routing": {"passes": 4, "trials": 4, "unresolved": 0}, "unsupported-certainty": {"passes": 2, "trials": 2, "unresolved": 0}}

## What the 1.7B can do alone

One strict-structured-output task passed on the first attempt (`capability-reviewed-logic-structured-output-001`). The remaining first-attempt failures show that the worker can often express parts of the requested reasoning, but deterministic acceptance frequently requires exact JSON, field, phrase, target, and lifecycle compliance.

## Local-teacher rescues

There are 8 local-teacher rescue trajectories and 4 evidence clusters. The recurring reusable behavior is: enumerate the declared JSON contract, preserve exact authority/lifecycle values, keep allowed and held targets disjoint, and make destructive actions conditional on inspection and review. See `intervention_clusters.json` for trajectory-level membership.

## Codex rescues

There are 9 external-teacher rescues. In all nine, the local retry remained unsuccessful before external escalation. The strongest evidence-supported distinction is that the external packet was more field-specific: it supplied complete schemas, exact target spellings, required phrases, and explicit mappings from conceptual constraints to output fields. This supports category A/D in the requested taxonomy—local diagnosis was often directionally correct but too generic, while Codex reformulated equivalent guidance into a form the worker followed better. Category B is not supported by these trajectories; category C is supported in cases where local guidance omitted a required semantic fact or exact value.

## Unresolved hard cases

Six tasks remain unresolved. Five are primarily output-contract difficulty and one (`capability-reviewed-logic-evidence-inference-001`) is also a review candidate for validator/fixture-stage interpretation because semantic phrase checks passed while structural JSON parsing failed. No trajectory justifies changing a validator or fixture; these are review flags only. Full attempt histories and diagnostics are in `unresolved_hard_cases.json`.

## Reusable candidate patches

Five candidates are recorded with `status: ready_for_review`. They are not installed or promoted:

1. strict JSON and complete declared contract;
2. explicit lifecycle/status checklist;
3. exact allowed/held target separation;
4. authority and review-only boundary wording;
5. field-level semantic checklist for conceptual reference facts.

Each candidate has evidence trajectory IDs, expected checks, strength, and overconstraint risks in `candidate_prompt_patches.json`.

## Candidate curriculum evidence

The structured curriculum file contains successful local and external corrections plus six unresolved negative/hard examples. Each entry preserves original attempt artifacts, validation diagnostics, teacher intervention artifacts, corrected reference output where available, resulting worker verdict, and review-only provenance. No automatic training authority is present.

## Teacher-gap analysis

The recurring 30B gap is insufficiently explicit diagnosis against the actual worker contract: “use valid JSON” was often not enough. The most promising bounded improvements are a teacher output checklist keyed to the contract, richer deterministic diagnostics naming missing fields/values, and reference facts that are explicitly expressible in declared fields. Fine-tuning is premature until those interventions are measured.

## What to test next

Review the five candidates without activation; then run a small A/B set that separates JSON-contract compliance from semantic reasoning, measures exact field/value adherence, and includes paired cases with the same reasoning but different output contracts. Keep deterministic validation authoritative and retain all failed attempts.

## Prompt-patch overlap audit and bounded A/B audition

The existing `PromptPatchLibrary` contains 7 candidate patches. The five Run 1 concepts overlap the library as follows: strict JSON is already covered by `output_contract_v1`; lifecycle precision, authority/review-only boundaries, and target separation are compositions of existing patches with missing exact-value behavior; the field-level semantic checklist needs an extension to existing contract/evidence patches. The complete mapping and patch inventory are in `synthesis/patch_overlap_audit.json` and `synthesis/existing_prompt_patch_inventory.json`.

The selected patch was `output_contract_v1`, because its recorded failure signature directly matches the dominant Run 1 prose/non-JSON/missing-field failures. A six-task paired audition used fresh 1.7B baseline and patched calls, the existing fixture-selected deterministic validators, and no teacher escalation. Results are recorded under `.work/capability_batch_reviewed_v1/patch_ab_output_contract_v1/`.

| Metric | Result |
| --- | ---: |
| trials | 6 |
| baseline passes | 0 |
| patched passes | 0 |
| rescued by patch | 0 |
| baseline-only passes | 0 |
| both pass | 0 |
| both fail | 6 |
| intervention helped | 0 |
| intervention hurt | 0 |
| no effect | 6 |

The patch changed the structural `parse_json` check from failure to pass in all six patched attempts, but every patched attempt still failed deterministic required-field and/or semantic checks. It therefore did not demonstrate reusable capability compression from teacher-required to 1.7B-plus-patch for this audition. No additional patch was tested, and `output_contract_v1` was not promoted or activated globally.

## Existing-patch provenance drift and composition audition

History shows that `repository_content_is_data_v1` and `messy_input_triage_packet_contract_v1` were fixture-only identifiers. The seven-patch library was created without either entry; later commits added the identifiers to prompt-patch A/B fixture cases, not to `examples/prompt_patches/`. They are therefore historical fixture provenance, not accidentally missing selectable patches. They were not restored.

The previous six-task A/B accounting was rebuilt from its existing artifacts. It recorded 6/6 structural `parse_json` fixes, no structural regressions, no semantic fixes, one semantic regression (`reference_priority_conflict`), 30 failed checks before versus 25 after, and six tasks with partial deterministic improvement. Task-level results remained 0/6 rescues.

The only composition audition used existing `output_contract_v1 + scope_boundary_v1` on four Run 1 tasks: `capability-reviewed-patch-combined-scope-contract-001`, `capability-reviewed-patch-output-contract-001`, `capability-reviewed-patch-repository-content-data-001`, and `capability-reviewed-patch-scope-boundary-001`. Each task received fresh baseline, single-patch, and composition worker calls; deterministic validation and all teacher escalation remained unchanged/disabled.

| Metric | Baseline | `output_contract_v1` | Composition |
| --- | ---: | ---: | ---: |
| passes | 0 | 0 | 0 |
| trials | 4 | 4 | 4 |
| total failed checks | 16 | 19 | 18 |
| structural checks fixed vs baseline | — | 0 | 0 |
| semantic checks fixed vs baseline | — | 0 | 0 |

There were no task-level rescues, no composition regressions at the task-verdict level, and no both-fail cases with partial improvement. One task (`capability-reviewed-patch-output-contract-001`) regressed at check level: `required_fields` and `reference_required_json_fields` failed under the patched arms although the baseline task also failed. This experiment does not demonstrate task-level reusable capability compression; testing stopped after this one composition as required.

## Files

- `synthesis/run_1_synthesis.json`
- `synthesis/intervention_clusters.json`
- `synthesis/candidate_prompt_patches.json`
- `synthesis/candidate_curriculum.json`
- `synthesis/unresolved_hard_cases.json`
- `synthesis/teacher_gap_analysis.json`
