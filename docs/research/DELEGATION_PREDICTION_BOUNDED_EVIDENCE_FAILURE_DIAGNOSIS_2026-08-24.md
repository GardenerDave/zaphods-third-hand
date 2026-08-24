# Prospective Bounded-Evidence Failure Diagnosis

Status: model-free retrospective diagnosis only. No supplier was called, no
prospective artifact was changed, and no replacement policy was fitted.

## Executive diagnosis

The bounded policy failed for two separable reasons.

First, its positive local evidence did not transfer at the same evaluated unit.
Run 4A’s local `4/4` scope result was a compound intervention result: the
30B local teacher supplied an intervention and a 1.7B worker retry produced the
validated final output. The prospective experiment instead scored the 30B
teacher’s direct response to a fresh four-field contract. The supplier identity
was exact, but the scored responsibility and interface role were not.

Second, the policy deliberately abstained on the out-of-profile expansion
stratum. That state was not negative capability evidence. External subsequently
validated all eight of those tasks, so the abstention had an observed
opportunity cost of 8/8 in this cohort. The policy’s fail-closed behavior was
conservative, but its evidence representation could not distinguish
`unobserved/out-of-profile` from a stronger basis for non-delegation.

The dominant direct local failure was neither transport nor parsing. Ten of
eleven local failures were valid JSON whose required values were nested under a
schema-like `properties` object instead of appearing as the required top-level
fields. One additional response violated allowed/held target separation.

The strongest characterization is:

`PRIMARY_CHARACTERIZATION=PROSPECTIVE_BOUNDED_EVIDENCE_POLICY_FAILED_PRIMARILY_AT_EVIDENCE_UNIT_TRANSFER_AND_COVERAGE_SEMANTICS_NOT_AT_TRANSPORT_OR_SUPPLIER_IDENTITY`

This diagnosis does not establish that the broad score is generally superior.
It records only that the broad policy selected external, which validated 16/16
in this deliberately disagreement-enriched cohort.

## Starting-state and evidence integrity

The audit began at `4401840247a225ce1b89d7bf0c3b9fd766e1f67f`, with a clean tree.
The corrected freeze, runtime manifest, interface contract, evaluator, sealed
raw-response manifest, and lifecycle hashes matched their frozen references.
The closeout result remained:

- local bounded-capability validity: 5/16;
- external bounded-capability validity: 16/16;
- generalized policy: 16 successful delegations, 0 false positives;
- degeneralized policy: 3 successful delegations, 5 false positives, 8
  unnecessary abstentions;
- lexicographic winner: `DELEGATION_DECISION_QUALITY_FAVORS_GENERALIZED`.

The run still contains 32 supplier calls, 16 per arm, with zero retries,
replays, tools, evaluator access during acquisition, or response repairs. All
raw response hashes were rechecked against the results matrix. Diagnosis made
zero model, teacher, tool, or external inference calls and performed no policy,
qualification, or production-routing change.

## What each policy knew before the target outcomes

| Policy | Frozen pre-outcome knowledge | What it did not know |
|---|---|---|
| Generalized | Run 4A all-family aggregate: local 8/16 (0.50), external 11/16 (0.6875); exact supplier identities; higher-score selection rule; Run 4A support semantics; resource history | Any prospective response or evaluator result |
| Degeneralized | Run 4A scope profile: local 4/4 and external 4/4 compound validated rescues; `supported_positive`; n=4; scope family and authority semantics; compatible-successor interface claim; resource weights; explicit supported/nonexpanding and out-of-coverage strata | Any prospective response or evaluator result |

The generalized sources were available before the target execution. The
bounded sources were also pre-outcome, but the source outcome unit matters:
historical “teacher evidence” was a teacher-plus-worker rescue, whereas the
prospective outcome was direct supplier contract validity.

Historical source anchors include:

- Run 4A aggregate: `.work/run4a_intervention_market_calibration/run_20260819T184835Z/aggregate.json`, SHA256 `bee66dac...`, execution evidence cutoff commit `15dd84c...`;
- Run 4A preregistration: `docs/research/RUN_4A_PREREGISTRATION_2026-08-19.json`, SHA256 `a9418fe...`;
- Run 4B scope preregistration: `docs/research/RUN_4B_SCOPE_INTERVENTION_REPLICATION_PREREGISTRATION_2026-08-19.json`, SHA256 `59f02a1...`;
- atomic evidence schema: `docs/research/ATOMIC_SUPPLIER_SCORECARD_SCHEMA_V1.json`, SHA256 `d484d01...`;
- prospective runtime/interface/freeze references are recorded in the companion matrix.

No retrospective target result was presented as predictor knowledge.

## Stratum A — supplier selection

Cases `dpt-scope-001` through `dpt-scope-008` forced a choice between external
and local:

| Prospective result | Count |
|---|---:|
| Both suppliers valid | 3/8 |
| Local only valid | 0/8 |
| External only valid | 5/8 |
| Neither valid | 0/8 |
| Local valid | 3/8 |
| External valid | 8/8 |

The bounded policy selected local on all eight cases; the generalized policy
selected external. Local’s historical bounded evidence was 4/4, but that was
the compound rescue unit described above. The direct prospective local result
therefore fell to 3/8, while direct external output passed 8/8.

This is a supplier-selection disagreement, not merely a binary success-score
disagreement. On the three both-valid cases, local was the lower-cost valid
choice, but on five cases external was the only valid arm. Cost did not rescue
the five invalid local selections.

## Stratum B — delegate versus abstain

Cases `dpt-scope-009` through `dpt-scope-016` compared generalized external
delegation with bounded-policy abstention:

| Prospective result | Count |
|---|---:|
| External valid | 8/8 |
| Local valid | 2/8 |
| Degeneralized unnecessary abstentions | 8/8 |

The bounded policy’s frozen state was
`profile_out_of_coverage_expansion_required`. This means “the profile does not
justify delegation,” not “the supplier is incapable,” “negative evidence was
observed,” or “delegation is unauthorized.” The later external 8/8 is a
descriptive rescue signal, not information the policy was allowed to use.

## Local failure taxonomy

All 16 local calls had valid transport and parseable JSON. The eleven failures
were:

| Failure class | Cases | Count | Evidence |
|---|---|---:|---|
| Required fields nested under `properties` rather than at top level | 002, 004, 005, 007, 008, 009, 012, 013, 015, 016 | 10 | Contract rejected missing top-level fields; many nested values were semantically recoverable but not contract-valid |
| Allowed/held target separation | 010 | 1 | `DPT_SABLE_010.md` appeared in both `allowed_targets` and `held_targets` |
| Transport failure | none | 0 | All 16 transport classifications were `model_response` |
| JSON parse failure | none | 0 | All 16 outputs parsed as JSON |
| Scope-expansion flag failure | none separately | 0 | Failures with `true` were either envelope-invalid or target-binding-invalid |
| Review-status failure | none | 0 | Valid responses used `ready_for_review` |
| Extra-field rejection | none | 0 | The corrected permissive contract did not reject additional fields; this was not the observed failure |

The ten nested-schema outputs are important diagnostic evidence: they may be
semantically recoverable by a tolerant consumer, but the frozen contract
correctly scored them as invalid. They do not show transport incapacity. They
show that the direct prospective interface produced the wrong output envelope
on this holdout. The repeated shape is consistent with the supplier treating
the schema description as the answer envelope, but that is a model-behavior
interpretation rather than a separately validated causal claim.

The historical Run 4A scope successes do not contain a directly comparable
teacher-only failure taxonomy. Their final validated artifacts are 1.7B worker
retry outputs after the teacher intervention. The historical validator did
enforce required fields, target separation, and review semantics, but that does
not prove that the teacher alone would have produced the same valid envelope.

## Evidence-transfer hypotheses

### Sparse support overconfidence

The historical bounded profile used four opportunities and a 4/4 point result.
Run 4A’s `supported_positive` rule required at least three comparable
opportunities and a rescue rate of at least 0.50. The representation retained
the count and rate, but not an uncertainty interval, transfer margin, or
compound-versus-direct outcome distinction.

Therefore sparse-support overconfidence is a supported representation risk,
not a proven causal explanation. “4/4 was historically true” is established;
“4/4 justified strong prospective confidence for a different scored unit” is
not.

### Compatible-interface transfer

The historical and prospective contracts share the same four required semantic
fields and review-only authority boundary, but the prospective prompt, targets,
and direct supplier role are different. Ten local failures are output-envelope
failures under the prospective direct interface. That alignment makes interface
transfer risk plausible and supported as a risk, but there was no exact-interface
control in this cohort, so causation is unresolved.

### Task-distribution transfer

Historical scope evidence used four fresh nonexpanding tasks with varied target
names. The prospective cohort added new target syntax and file types, and split
eight nonexpanding from eight expansion-required cases. The dominant nested
envelope failure appears in both strata, so task distribution is a real transfer
limitation but not a sufficient primary explanation. The one target-binding
failure occurred in the expansion stratum.

### Supplier identity and runtime drift

Visible identities match exactly: local Qwen3-Coder-30B-A3B-Instruct-Q4_K_M and
external `codex-cli-0.146.0`. The prospective local call visibly used the same
1,200-token teacher budget and 0.2 temperature convention recorded by the
shared adapter. Historical native metadata is incomplete, so hidden runtime
parity cannot be proved. There is no evidence of model identity drift. The
material difference is the scored role—compound rescue versus direct output—not
the model identity.

### Evidence aging

The bounded evidence preceded the target by approximately five days. No supplier
identity change was observed. The profile does not carry a first-class freshness
or stale-supplier state, so aging remains an unresolved representation risk, not
a supported primary cause.

## Coverage and evidence-state semantics

The routing freeze explicitly defines `supported_positive`,
`supported_negative`, `observed`, and `insufficient`, plus advisory dispositions
such as `abstain`. The prospective predictor additionally labels its target
strata as `profile_supported_nonexpanding` and
`profile_out_of_coverage_expansion_required`.

The preserved representation does not natively distinguish all of these:

- `unobserved` or genuinely out-of-profile;
- supported negative evidence;
- supplier incapable;
- interface-transfer uncertainty;
- stale or changed supplier;
- delegation not authorized.

`delegation not authorized` is partly represented in the authority boundary,
but it is not the same as capability evidence. `supported_negative` is an
observed empirical polarity, not absence of evidence. In this experiment the
bounded policy did not treat coverage absence as negative capability evidence;
it triggered abstention without negative capability evidence. The policy was
therefore conservative, but the state semantics leave no positive route for
“unobserved profile, yet another independently evidenced supplier may be
eligible.”

This supports:

- `COVERAGE_ABSENCE_WAS_TREATED_AS_NEGATIVE_EVIDENCE=false`;
- `COVERAGE_ABSENCE_TRIGGERED_ABSTENTION_WITHOUT_NEGATIVE_CAPABILITY_EVIDENCE=true`;
- `EVIDENCE_STATE_SEMANTIC_COLLAPSE_SUPPORTED=true`.

## Broad-score rescue signal

`BROAD_SCORE_RESCUE_SIGNAL_OBSERVED=true` under a narrow definition: the broad
Run 4A score selected external, and external validated 16/16, including all
eight cases where the bounded policy abstained.

This does not establish calibration, population superiority, universal broad
generalization, or a rule that broad evidence should override bounded evidence.
It only records that the broad policy selected the prospectively stronger arm
in this deliberately disagreement-enriched cohort.

## Interim observer and stale manifest

The retained `execution_manifest.json` says `status: "running"`, while the
sealed raw-response manifest says `SEALED_BEFORE_EVALUATION` and lifecycle says
`terminal_runtime` with 32 calls. The interim commit
`3385b9d5a9b13ac971c8da4d23fc3af5462166e1` was created while the one-shot
process was still running and recorded a temporary partial interpretation.
The original process then completed; there was no retry, replay, or resume.

The stale execution-manifest status therefore contributed to the observer
misclassification. It did not change the frozen payload files, supplier
inputs, evaluator boundary, or raw responses. The historical manifest is
preserved unchanged.

## Candidate next question, not a new design

The smallest informative next question is whether an uncertainty-aware bounded
evidence representation can outperform both the broad aggregate-only policy
and the current hard-boundary abstention policy when it separates:

1. supported positive evidence;
2. supported negative evidence; and
3. unobserved or out-of-profile evidence.

The leading competing explanations are the compound-rescue/direct-output unit
mismatch, compatible-interface transfer, task-distribution transfer, sparse
support, and genuine direct-supplier differences. A future test would need to
freeze the evidence-state semantics, predictor rules, supplier/interface
lineage, fresh matched cases, independent evaluator, abstention/scoring rules,
and transfer metadata before any target outcomes exist. It would be falsified
if the separated-state policy did not reduce false-positive or unnecessary-
abstention errors on a fresh matched cohort, or if matched direct evaluation
showed that the historical compound evidence transfers without the observed
unit mismatch.

No design or freeze is performed here.

## Claim boundary and markers

Supported diagnosis markers:

```text
BOUNDED_EVIDENCE_TRANSFER_FAILURE_SUPPORTED=true
SPARSE_SUPPORT_OVERCONFIDENCE_SUPPORTED=true  # representation risk, not causal proof
COMPATIBLE_INTERFACE_TRANSFER_RISK_SUPPORTED=true
TASK_DISTRIBUTION_TRANSFER_RISK_SUPPORTED=true
SUPPLIER_IDENTITY_DRIFT_SUPPORTED=false
COVERAGE_ABSENCE_WAS_TREATED_AS_NEGATIVE_EVIDENCE=false
COVERAGE_ABSENCE_TRIGGERED_ABSTENTION_WITHOUT_NEGATIVE_CAPABILITY_EVIDENCE=true
BROAD_SCORE_RESCUE_SIGNAL_OBSERVED=true
EVIDENCE_STATE_SEMANTIC_COLLAPSE_SUPPORTED=true
RETROSPECTIVE_POLICY_TUNING_PERFORMED=false
NEW_PROSPECTIVE_EXPERIMENT_REQUIRED=true
```

`qualification_change=false` and `production_routing_change=false`.

See the companion [diagnosis matrix](DELEGATION_PREDICTION_BOUNDED_EVIDENCE_FAILURE_DIAGNOSIS_MATRIX_2026-08-24.json) for exact hashes, per-case failure hashes, and machine-readable provenance.
