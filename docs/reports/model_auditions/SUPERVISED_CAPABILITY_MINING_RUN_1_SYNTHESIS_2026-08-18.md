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

## Direct teacher-pattern distillation audition

The selected cluster was `strict_json_plus_complete_fixture_specific_field_value_compliance`, supported by five external-teacher rescues: `capability-reviewed-frontdoor-dependency-uncertainty-001`, `capability-reviewed-frontdoor-docs-scope-001`, `capability-reviewed-logic-contradiction-001`, `capability-reviewed-patch-triage-contract-shape-001`, and `capability-reviewed-patch-unsupported-certainty-001`. The experimental candidate is recorded at `synthesis/run1_distilled_candidate_patch.json`; it was not added to the library.

The distilled instruction retained only: exact JSON-only serialization, every declared field/type, deterministic diagnostics as a checklist, exact values/phrases from dynamically supplied reference facts, no invented fields, and review-only authority. Teacher narratives and corrected answer literals were excluded.

| Metric | Baseline | Distilled candidate |
| --- | ---: | ---: |
| trials | 5 | 5 |
| passes | 0 | 0 |
| rescued by patch | 0 | — |
| regressions | 0 | 0 task-level |
| total failed checks | 24 | 18 |
| structural checks fixed | — | `parse_json`: 4; `required_field_types`: 4 |
| semantic checks fixed | — | 0 |

All five tasks historically passed after teacher intervention, but none passed with the distilled candidate alone. Four patched outputs became parseable and better typed, yet they still failed required fields and semantic checks. The outputs also repeatedly invented an `output_contract` schema because the fresh audition prompt supplied the distilled instruction without the fixture’s actual output contract/reference facts. One task additionally regressed on `duplicate_json_keys` and `reference_uncertainty`.

The evidence therefore points to task-specific contract/reference visibility—not corrected-reference hard-coding—as the missing ingredient. Teacher reasoning may still matter for difficult semantic cases, but this experiment cannot distinguish that from absent reference facts. No candidate enlargement, promotion, or second cluster test was performed.

## Context-complete distilled retry

Packet inspection found that the canonical worker path rendered the bounded task prompt and any selected patch text, but not the fixture `output_contract`, validator/reference facts, or prior validation diagnostics. The earlier distillation audition used the same incomplete shape: task prompt plus generic candidate text. The teacher path, by contrast, received task prompt, output contract, bounded reference facts, failed transitions/diagnostics, patch evidence, and authority boundaries.

The experiment renderer `local_harness/distilled_retry_packet.py` supplied the unchanged candidate `run1-experimental-distilled-strict-contract-v1` alongside clearly separated task context, declared output contract, bounded reference facts, baseline deterministic diagnostics, and review-only authority boundaries. No corrected teacher output or other patch was included.

Using the same five tasks, fresh canonical baselines all failed, then all five context-complete distilled retries passed:

| Metric | Result |
| --- | ---: |
| baseline passes | 0/5 |
| patch-retry opportunities | 5 |
| patch-retry passes | 5/5 |
| rescued by distilled patch | 5 |
| unresolved | 0 |
| task regressions | 0 |
| failed checks before/after | 24 / 0 |

Checks fixed across the five retries were `parse_json` (5), `required_field_types` (5), `required_fields` (5), and nine configured task-specific semantic checks: `reference_review_status`, `reference_queue_handoff_status`, `reference_repo_mutation_status`, `reference_source_review_status`, `reference_must_include`, `reference_required_authority_boundary_terms`, `reference_required_packet_schema`, `reference_required_review_required`, and `reference_requires_scope_expansion_flag` (one each). No structural or semantic regressions occurred.

The retry packet contained the same information categories represented in the successful teacher packets: contract shape, exact field names/types, reference values/constraints, diagnostics, and authority boundaries. This is the first evidence in Run 1 of teacher-free task-level reusable capability compression: baseline failure → deterministic diagnostics plus task facts plus unchanged distilled candidate → worker success. The candidate remains experimental and unpromoted.

## Preregistered holdout generalization

The holdout experiment was preregistered before the first worker call as `run1-distilled-strict-contract-holdout-001`. The frozen candidate was `run1-experimental-distilled-strict-contract-v1`, with canonical content hash `3231d72ed9805aef9c16ced7b6eded50bcf35a6ef665338c0cb2640117470459`, and the context-complete renderer was frozen at commit `0f2ae813e3b1b8ff9f2d6a86a71d39d3ceae3624`. The five derivation tasks were excluded. Selection used baseline-only structural and semantic failure evidence; historical teacher artifacts were not inspected until all holdout calls were complete.

The selected 10-task holdout contained 3 historically unresolved tasks, 3 historically rescued by the local teacher, and 4 historically rescued by the external teacher. Every fresh baseline failed, so every task received exactly one deterministic retry. There were 20 worker calls total, with no teacher or external-teacher calls, no existing patches, and no additional retries.

| Metric | Result |
| --- | ---: |
| holdout tasks | 10 |
| fresh baseline passes | 0/10 |
| retry opportunities | 10 |
| retry passes | 0/10 |
| teacher-free rescues | 0 |
| unresolved after retry | 10 |
| teacher-free holdout rescue rate | 0% (0/10) |
| final pass rate | 0/10 |
| task regressions | 0 |
| failed checks before / after | 50 / 50 |
| structural checks fixed / regressed | 0 / 0 |
| semantic checks fixed / regressed | 0 / 0 |

By historical disposition, rescue rates were 0/3 for local-teacher cases, 0/4 for external-teacher cases, and 0/3 for unresolved cases. Thus the preregistered result is `no_task_level_generalization`; neither `evidence_of_generalization` nor `strong_generalization` was met. This is evidence about holdout tasks within the Run 1 distribution, not a claim about arbitrary out-of-distribution behavior.

Every task retained the same five or six failed checks after retry as before it: the retry did not produce a parseable contract-compliant object, and no structural or semantic check moved. The per-task artifacts and exact before/after diagnostics are in `.work/capability_batch_reviewed_v1/holdout_distilled_strict_contract/holdout_summary.json` and its task directories.

Post-hoc comparison began only after the holdout results were frozen. The deterministic retry contained task facts, the declared output contract, bounded reference facts, fresh validator diagnostics, and authority boundaries. Historical teacher packets additionally contained teacher diagnosis/retry guidance and, in most successful external cases, corrected-reference examples. Since there were no holdout rescues, no information category can be credited as sufficient. The strongest evidence-supported remaining gap is teacher-generated diagnosis/guidance and/or corrected-reference/example effect; worker instruction-following or generation variability cannot be separated from those factors in this zero-rescue result. The comparison record, including teacher artifact hashes, is review-only at `holdout_distilled_strict_contract/posthoc_teacher_comparison.json`.

## Teacher-ingredient ablation

The recorded holdout contains six, rather than seven, tasks satisfying both requested selection criteria: fresh baseline failure and durable historical success after a teacher. The qualifying set was the three local-teacher rescues and three external-teacher rescues. The fourth external-tier holdout candidate, `capability-reviewed-queue-needs-repair-001`, is unresolved in its durable summary and was not padded into this experiment.

The directly preceding successful teacher artifacts were used without rewriting. Five contained a corrected-reference output; `capability-reviewed-blocked-queue-inserted-001` did not, so Arm B was unavailable for that task. The unchanged distilled patch and context-complete packet remained present in all available arms.

| Arm | Available tasks | Passes/rescues | Rescue rate | Structural fixed/regressed | Semantic fixed/regressed |
| --- | ---: | ---: | ---: | ---: | ---: |
| A: diagnosis + retry guidance | 6 | 0/6 | 0% | 0/0 | 0/0 |
| B: corrected-reference example | 5 | 0/5 | 0% | 0/0 | 0/0 |
| C: diagnosis + example | 6 | 0/6 | 0% | 0/0 | 0/0 |

All 17 available treatment calls failed the deterministic validator. No task-level regression or failed-check movement occurred relative to the frozen failed baselines. Every selected task is classified `teacher_artifact_insufficient`; no task is `diagnosis_sufficient`, `example_sufficient`, `either_sufficient`, or `combination_required`.

The result does not support diagnosis/retry guidance alone, corrected-reference examples alone, or their combination as sufficient causal explanations of the historical teacher successes. The observed historical teacher contribution remains unidentified at this worker budget and prompt arrangement; possible factors include teacher-generated semantic reasoning, teacher packet organization, or generation/instruction-following variability. The selected local and external cases showed the same zero-rescue result, so this ablation does not support a tier-specific ingredient difference.

Leakage review classified the five available corrected-reference examples as `mixed`: they use declared contract fields and bounded task/reference values, but also package diagnostic and authority-boundary prose not present as exact reference-fact values. No example was classified as a pure deterministic reformat or as proven teacher-generated inference in isolation. The missing-example case is recorded as `not_available`. Structured ablation results, source hashes, exact ingredients, and leakage classifications are review-only under `.work/capability_batch_reviewed_v1/teacher_ingredient_ablation/`.

## Historical retry-packet replay

No exact historical worker prompt artifact was preserved for the six qualifying tasks. The production path was reconstructed from the durable task prompt, the directly preceding successful teacher artifact, and the recorded intervention identity. The reconstructed H prompt is the original task prompt followed by `## Local teacher intervention` or `## External teacher intervention` and the parsed teacher JSON. It contained no selected existing patch. The current R arm was the prior combined ingredient packet: a structured JSON envelope containing task context, declared contract, bounded facts, baseline diagnostics, authority boundaries, the unchanged distilled patch, and nested teacher evidence.

The primary topology difference is that H places the teacher JSON directly after the task prompt, while R places the teacher material inside a later evidence section after explicit deterministic context and the distilled instruction. H does not separately render output-contract, reference-fact, diagnostic, or authority sections; R does. H also does not expose the distilled patch as a separate prompt section.

Historical request metadata preserved the 1.7B model identity and `finish_reason=stop`, but did not preserve max tokens, temperature, top-p, seed, stop fields, or context size. Current replay used the configured 1.7B worker, current max-token configuration, temperature 0.2, and no top-p/seed/stop fields. These unknowns prevent a claim of generation-condition parity.

Three fresh calls per arm/task were preregistered because historical generation was not explicitly deterministic: 36 calls total, with no teachers or adaptive retries.

| Arm | Calls | Passes | Pass rate | Tasks with a pass | Repeatable tasks |
| --- | ---: | ---: | ---: | ---: | ---: |
| H: reconstructed historical retry packet | 18 | 0 | 0% | 0/6 | 0/6 |
| R: reconstructed combined ingredient packet | 18 | 0 | 0% | 0/6 | 0/6 |

All six tasks remained at their frozen baseline failed checks in every call. Structural movement was 0 fixed / 0 regressed and semantic movement was 0 fixed / 0 regressed for both arms. There were no H-only successes, no R successes, and no tasks where both succeeded.

The formal preregistered `generation_variability_evidence` label is true because H did not reliably reproduce historical success, but this is weak evidence: missing historical sampling settings and the fact that H is reconstructed rather than exact leave prompt reconstruction and generation variability confounded. `packet_topology_evidence` and `repeatable_packet_topology_evidence` were not met.

The strongest current conclusion is therefore not that packet topology was irrelevant, but that historical teacher-assisted success is not replayably causal from the durable artifacts under fresh calls. The apparent teacher contribution remains unresolved between semantic reasoning, omitted historical retry inputs, packet organization, and generation/inference-condition differences. No packet redesign or new intervention was made. Replay artifacts, reconstructed prompt hashes, the exact field/category audit, and per-call validations are review-only under `.work/capability_batch_reviewed_v1/historical_retry_replay/`.

## Files

- `synthesis/run_1_synthesis.json`
- `synthesis/intervention_clusters.json`
- `synthesis/candidate_prompt_patches.json`
- `synthesis/candidate_curriculum.json`
- `synthesis/unresolved_hard_cases.json`
- `synthesis/teacher_gap_analysis.json`
