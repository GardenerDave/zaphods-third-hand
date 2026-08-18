# Supervised Capability Mining Run 2

Run 2 tested the frozen Run 1 deterministic context-complete retry on 20 genuinely fresh reviewed fixtures. No fixture, validator, patch, or treatment was changed after preregistration.

## Result

| Metric | Result |
| --- | ---: |
| fresh tasks | 20 |
| transport-valid tasks | 20/20 |
| infrastructure failures | 0 |
| baseline 1.7B passes | 0/20 |
| deterministic retry opportunities | 20 |
| deterministic retry passes/rescues | 9/20 (45%) |
| local-teacher escalated tasks | 11 |
| local-teacher calls / rescues | 21 / 1 |
| external-teacher escalated tasks / calls / rescues | 10 / 10 / 4 |
| final passes | 14/20 (70%) |
| unresolved | 6 |

All capability metrics were computed only from attempts with
`transport_classification=model_response`. The preflight canary also returned a
valid 1.7B response with usage metadata and a passing deterministic validator.

The frozen treatment was
`run1-experimental-distilled-strict-contract-v1`, file SHA256
`7cfb4453919ad945f0d149ec8af8763653b3734a54b86f23303b84a60dfdacf6`, with the
Run 1 context-complete renderer identity recorded in the preregistration.

## Cumulative solve rate and ladder economics

| Stop tier | Tasks | Share |
| --- | ---: | ---: |
| 1.7B baseline | 0 | 0% |
| 1.7B deterministic retry | 9 | 45% |
| 30B local-teacher recovery | 1 | 5% |
| External Codex recovery | 4 | 20% |
| Unresolved | 6 | 30% |

Cumulative solve rate was 0% after baseline, 45% after deterministic retry,
50% after local teacher, and 70% after external teacher. The run used 71 valid
worker calls, 21 local-teacher calls, and 10 external-teacher calls. Descriptive
calls per final pass were 5.07 worker, 1.50 local-teacher, and 0.71 external-
teacher calls. Deterministic retries avoided 9 teacher escalations; no
counterfactual claim is made about external calls avoided.

## Success criteria

- `teacher_free_generalization_replicated`: met (9 fresh failed baselines were rescued).
- `strong_teacher_free_replication`: not met (45%, below the preregistered 50% threshold).
- `run1_level_replication`: not met (45%, below 70%).

Thus Run 1’s teacher-free capability-compression result replicated on fresh
tasks as evidence of generalization, but not at Run 1’s observed strength.
This is not evidence of weight learning, permanent capability change, or
arbitrary out-of-distribution generalization.

## Family and novelty breakdown

| Task family | Tasks | Patch opportunities / passes | Local rescues | External rescues | Final passes | Unresolved |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| contradiction-handling | 3 | 3 / 2 | 0 | 0 | 2 | 1 |
| destructive-action-restraint | 3 | 3 / 1 | 0 | 1 | 2 | 1 |
| evidence-grounding | 3 | 3 / 1 | 0 | 1 | 2 | 1 |
| queue-authority-boundary | 4 | 4 / 3 | 0 | 0 | 3 | 1 |
| scope-authority-boundary | 4 | 4 / 0 | 1 | 1 | 2 | 2 |
| unsupported-certainty | 3 | 3 / 2 | 0 | 1 | 3 | 0 |

The 15 `new_source` tasks had 8/15 deterministic retries pass, 1 local
rescue, 2 external rescues, and 4 unresolved. The 5
`new_scenario_same_family` tasks had 1/5 deterministic retries pass, 2
external rescues, and 2 unresolved.

## Failure analysis

The six unresolved tasks and their final deterministic diagnostics are recorded
in `failure_analysis.json`. The supported recurring labels are contract-
following/serialization failure and reference-fact application failure. Scope
tasks most often retained target-membership or authority checks; evidence and
contradiction failures retained required fields or parseability. These are
post-run evidence classifications only. No new patch, fixture adjustment, or
teacher intervention was designed from them.

Teacher outputs and corrected references remain review-only curriculum evidence
with full per-task provenance. No patch promotion, training, queue insertion,
repository mutation, or acceptance occurred.

## Reproducibility and provenance

The preregistration, fixture manifest, exact task trajectories, prompt artifacts,
request metadata, validations, scorecard, ladder economics, family/novelty
breakdown, synthesis, and failure analysis are under
`.work/capability_batch_reviewed_v2/`. Transport-invalid attempts would have
been preserved and excluded; this run had none.

## Review conclusion

Run 2 kept 9/20 fresh tasks on the cheap 1.7B tier through the frozen
deterministic retry before any teacher was required. It demonstrates fresh-task
teacher-free generalization, but the 45% rescue rate does not replicate Run 1’s
80% level. The frozen mechanism remains experimental and unpromoted.
