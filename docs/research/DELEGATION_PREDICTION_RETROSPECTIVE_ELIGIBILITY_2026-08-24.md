# Retrospective Delegation-Prediction Eligibility Audit

Status: model-free provenance and eligibility audit for
`CHRONOLOGICAL_RETROSPECTIVE_DELEGATION_PREDICTION_REPLAY`.

Authoritative audit HEAD: `29c577760f73ec3d24f071428d5377f54314a9e4`.

No predictor, prediction score, threshold, routing rule, supplier qualification, or
new experiment was created. Historical evidence and raw artifacts were not
modified.

## Decision

`RETROSPECTIVE_REPLAY_PARTIALLY_ELIGIBLE`

There is a useful 60-task retrospective cohort for a bounded,
policy-effectiveness/descriptive replay:

- Run 4: 12 selected triage tasks
- Run 5: 24 selected triage/scope tasks
- Run 6: 24 selected triage/scope tasks

All 60 rows have pre-target historical evidence, independently preserved
validated outcomes, and no exact target-fixture reuse. However, all 60 are
policy-entangled: prior decomposed evidence was explicitly used to construct
the later policy being evaluated. The exact interface also changed between the
capability-mining source and the routing targets.

Therefore there are:

- 60/60 temporally clean rows;
- 60/60 outcome-clean rows with respect to the current target outcome;
- 0/60 policy-independent rows;
- 0/60 strict independent-prediction rows;
- 60/60 rows potentially usable for a clearly labeled historical
  policy-effectiveness replay.

This cannot support an independent claim that a decomposed profile predicted
delegation better than a generalized score. The recommended next decision is:

`DESIGN_PROSPECTIVE_MATCHED_DELEGATION_COHORT`

The machine-readable row audit is
[DELEGATION_PREDICTION_RETROSPECTIVE_ELIGIBILITY_MATRIX_2026-08-24.json](DELEGATION_PREDICTION_RETROSPECTIVE_ELIGIBILITY_MATRIX_2026-08-24.json).

## 1. Authoritative chronology

| Evidence | Canonical artifacts and provenance | Tasks / calls | Result relevant to this audit |
|---|---|---:|---|
| Capability-mining Run 1 | `docs/reports/model_auditions/SUPERVISED_CAPABILITY_MINING_RUN_1_SYNTHESIS_2026-08-18.md`; closeout commit `696781d4efacf9061044eb2fb490848427783a81` | 24 baseline task attempts plus intervention/audition calls; not one comparable call total in the synthesis | 1/24 unaided; later rescue evidence and failure signatures; heterogeneous intervention history |
| Capability-mining Run 2 | `docs/reports/model_auditions/SUPERVISED_CAPABILITY_MINING_RUN_2_2026-08-18.md`; closeout commit `3fc3a44cfcefcac50a5fe06d0dbf35b6c9203815` | 20 fresh tasks; 102 valid calls: 71 worker, 21 local-teacher, 10 external-teacher | 0/20 baseline; 9/20 deterministic retries; 14/20 final; family-level failure/rescue evidence |
| Economic-routing Run 4 | `.work/run4_economic_routing/run_20260819T220012Z/`; policy commit `591dcb08323ba07c8171ac8728e400f8a37c35da`; execution commit `f8e8a95f12ebe4a7418334a7f8f66ec3172a90e8` | 12 selected triage pairs; 51 model calls | 10/12 control versus 1/12 treatment; resource reduced, quality not preserved |
| Economic-routing Run 5 | `.work/run5_mixed_economic_routing/run_20260819T013828Z/`; policy commit `411667614407ddcdebf4a3bbfdff1d66ca61ec44`; execution commit `5497bbc281df8e9758cdc76b24d33e7752e3eef7` | 24 selected tasks; 102 model calls | 22/24 control versus 21/24 treatment; resource reduced, quality not preserved |
| Economic-routing Run 6 | `.work/run6_sequential_economic_routing/run_20260820T030541Z/`; policy commit `8bf19f35470f0d40e49f883a5ec74621c5ba2c7a`; execution commit `4eb07b9427c2c3a3d808e6f314e772ee15cfcd5d` | 24 selected tasks; 102 model calls | 23/24 versus 23/24; resource reduced; all 12 scope local-first attempts passed, so escalation was not exercised |

The ordering is established by preserved commit dates and manifests, not run
number alone. Run 2 closed on 2026-08-18. Run 4 began after its policy freeze on
2026-08-19. Runs 5 and 6 froze their policies before their respective execution
manifests completed on 2026-08-20.

## 2. Generalized predictor candidates

### Primary candidate

The strongest reconstructable generalized candidate is:

`.work/capability_batch_reviewed_v2/scorecard.json::baseline_pass_rate`

- supplier: Qwen3 1.7B worker;
- value: `0.0` over 20 Run 2 tasks;
- evidence cutoff: Run 2 closeout commit
  `3fc3a44cfcefcac50a5fe06d0dbf35b6c9203815`;
- available before Runs 4–6: yes;
- target outcome contamination: no;
- plausible historical use: coarse evidence about baseline worker competence;
- limitation: it is a global aggregate and does not encode the target family,
  interface, authority context, or selected intervention.

Run 1's 1/24 unaided result is also prior evidence, but its synthesis combines
baseline, rescue, patch, holdout, and audition slices. It is therefore a
secondary historical comparison, not a clean replacement for the Run 2
baseline score.

The model-audition board contains broader aggregate scores and raw task
evidence, but it is not the preferred baseline here: the scorecards represent
different audition boards/interfaces and do not contain actual later delegation
outcomes. Treating them as a single supplier score would introduce a
supplier/interface mismatch rather than improve the replay.

No new generalized score was constructed.

## 3. Degeneralized profile candidates

The strongest historical profile is the capability-card/failure-signature
evidence assembled from Run 1 and Run 2:

- `.work/capability_cards/capability_cards.json`;
- `.work/capability_cards/family_intervention_matrix.json`;
- `.work/capability_cards/failure_class_matrix.json`.

The source commits are Run 1
`d27c1e7dd72997eda1bf0b69b73f0a586cb3e395` and Run 2
`3fc3a44cfcefcac50a5fe06d0dbf35b6c9203815`. The cards record task family,
failure signature, supplier/intervention identity, eligible opportunities,
success/failure polarity, rescue rate, and source artifacts. The generated
card file was produced at 2026-08-19 00:56 UTC, before all three target runs.

This profile is reconstructable before each target outcome. It is not a
post-target scorecard assembled by deleting later fields. The audit still
records the later policy bindings separately because historical availability
does not imply policy independence.

Other possible profile ingredients include Run 4A comparative evidence and
prior economic-routing summaries. They are valid historical evidence, but they
increase policy entanglement. They must not be silently treated as an
independent predictor.

## 4. Target outcome availability

The preserved target artifacts independently expose:

- validated task solve: yes, for both policy arms on all 60 selected rows;
- paired terminal outcome: yes, in Run 4 pair summaries and Run 5/6 scorecards;
- realized arm resource use: yes, elapsed time is preserved per arm;
- review/containment authority: yes, target artifacts retain review-only
  authority boundaries;
- escalation-needed: only partially observable. Run 6 scope records the
  sequential escalation field, but all 12 local-first attempts passed and
  therefore no escalation branch was exercised. Runs 4 and 5 do not provide a
  common independent escalation target for every row.

No target outcome was used to build the generalized or decomposed predictor
features in this audit.

## 5. Row construction and transfer

The matrix contains one row for each selected target task. Policy-arm outcomes
are nested in each row; no task is duplicated merely because it has control and
treatment arms.

Across all rows:

- exact task-ID reuse: false;
- exact fixture reuse: false, based on fresh run-specific fixture packs and
  preserved novelty/selection artifacts;
- same task family: true at the family-label level;
- related failure signatures: present;
- exact interface transfer: changed. The source capability-mining and target
  routing protocols are both supervised JSON plus deterministic validation, but
  their prompts, schemas, action bindings, and validators are versioned and not
  identical;
- authority/context transfer: compatible review-only boundaries, but
  target-specific authority facts differ;
- supplier/action transfer: the Qwen3 1.7B worker is related/identical as a
  worker identity, while the delegated intervention differs across policy arms
  and runs.

The source-to-target transfer is therefore close enough for a descriptive
policy-effectiveness replay, but not close enough to treat the profile as an
unqualified exact-interface competence predictor.

## 6. Temporal audit

The source evidence precedes every target outcome:

- Run 1/2 source commits precede Run 4, 5, and 6;
- the generated capability profile predates all three target executions;
- each target policy freeze precedes its own execution;
- each target execution manifest records a later completion time.

The task-level final timestamp is not preserved in each pair scorecard, so the
matrix uses the run completion time as a conservative upper bound and labels
that limitation. No row was admitted on filesystem mtime alone.

Classification:

- Run 4: 12/12 temporally clean;
- Run 5: 24/24 temporally clean;
- Run 6: 24/24 temporally clean.

No temporal-leakage row was found. Ambiguous task-level terminal times are
documented, not silently treated as precise timestamps.

## 7. Outcome and exact-task leakage

The target selections were frozen from eligible baseline failures:

- Run 4 selected the first 12 eligible candidates from 15;
- Runs 5 and 6 selected the first 12 eligible candidates within each family
  from 15.

The preserved manifests show no adaptive replacement after target outcomes.
The target task IDs and fixture packs are fresh relative to Run 1/2 source
tasks.

Thus the audit classifies all rows as outcome-clean with respect to the current
target result and free of exact-task reuse. This does not make them
policy-independent: prior outcomes from earlier runs were used in later policy
construction.

## 8. Policy-construction leakage and entanglement

This is the decisive limitation.

### Run 4

The Run 4 policy freeze directly binds the Run 4A comparative-evidence freeze,
created at commit `e278c2f2c1a6c3f98420fc334f3596cf43ea2331`, before the Run 4
policy freeze. The policy then selects interventions from empirical rescue
rates and expected costs. The evidence was available before the Run 4 outcome,
but it helped construct the policy being evaluated.

### Run 5

The Run 5 policy freeze binds Run 4 closeout, Run 4 interpretation, Run 4A
comparative evidence, and Run 4B scope evidence. The family action matrix
explicitly changes the scope action based on that evidence. This is direct
predictor-to-policy entanglement.

### Run 6

The Run 6 policy freeze binds the Run 5 interpretation freeze and explicitly
labels the sequential reconstruction exploratory. The Run 6 closeout provenance
also records the prior Run 4A/4B evidence lineage through the Run 5 basis. The
Run 6 target outcome was not available at policy freeze, but the policy is still
downstream of prior evidence and therefore not an independent predictor test.

Classification for all three target runs:

`PREDICTOR_USED_TO_BUILD_POLICY`

not merely “historical evidence happened to exist.” The current target outcome
was not used in policy construction, so this is policy entanglement rather than
target-outcome leakage.

## 9. Run-specific eligibility

| Run | Selected rows | Temporal clean | Outcome clean | Policy-independent | Family-compatible policy replay | Strict eligible |
|---|---:|---:|---:|---:|---:|---:|
| Run 4 | 12 | 12 | 12 | 0 | 12 | 0 |
| Run 5 | 24 | 24 | 24 | 0 | 24 | 0 |
| Run 6 | 24 | 24 | 24 | 0 | 24 | 0 |
| **Total** | **60** | **60** | **60** | **0** | **60** | **0** |

Run 6 should not be used to claim escalation-prediction validity: its
escalation branch had zero opportunities. Run 4 and Run 5 also differ in policy
and action structure, so they should not be collapsed into one homogeneous
prediction cohort.

## 10. What can and cannot be replayed

A bounded retrospective analysis could legitimately ask:

> Given the prior evidence and the historically frozen policy, what policy
> choice and policy-level outcome followed on these later tasks?

That is a historical policy-effectiveness/descriptive replay. It can preserve
the policy-entangled nature of the decision and compare runs/families without
pretending to estimate an independent predictor.

The proposed benchmark thesis asks a stronger question:

> Did the decomposed profile predict later delegation outcomes better than a
> generalized score?

The preserved data cannot answer that cleanly because the decomposed profile
was used to construct the target policies, and its exact interface/context
transfer is not identical. Computing accuracy, AUC, thresholds, or fitted
weights would therefore create a post-hoc predictor comparison, not repair the
provenance problem.

## 11. Final eligibility decision

`RETROSPECTIVE_REPLAY_PARTIALLY_ELIGIBLE` is the correct status because a
substantial, temporally ordered, independently validated, family-compatible
cohort exists for a policy-effectiveness replay. It is not
`RETROSPECTIVE_REPLAY_ELIGIBLE` for the stronger independent-prediction claim:
the strict clean intersection is 0/60.

The correct next step is:

`DESIGN_PROSPECTIVE_MATCHED_DELEGATION_COHORT`

A prospective cohort should freeze generalized and decomposed evidence
snapshots before task assignment, keep policy construction and predictor
evaluation separable, version the exact interface/context, and reserve later
outcomes exclusively for validation.

## 12. Preserved boundaries

This audit did not:

- run inference;
- build a predictor;
- calculate prediction accuracy or fit thresholds;
- modify historical raw evidence;
- modify production routing;
- merge capability evidence;
- qualify a supplier;
- freeze or execute the delegation-prediction experiment.
