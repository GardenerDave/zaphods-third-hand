# Delegation Prediction Competence-Unit Validity Audit

Date: 2026-08-24
Status: model-free retrospective validity analysis; no new experiment frozen or executed

## Scope and preserved result

This audit examines whether the historical evidence used by the two frozen
policies measured the same competence unit as the prospective
`DELEGATION_PREDICTION_TEST_SCOPE_V0` outcomes. It does not recalculate the
experiment, change the policies, or discard the observed result.

The prospective result remains:

- generalized policy: 16 successful delegations, 0 false-positive delegations;
- degeneralized policy: 3 successful delegations, 5 false-positive delegations,
  and 8 unnecessary abstentions;
- direct local capability validity: 5/16;
- direct external capability validity: 16/16;
- lexicographic winner: `DELEGATION_DECISION_QUALITY_FAVORS_GENERALIZED`.

The result is valid as a comparison of the two frozen delegation policies over
the observed direct supplier outcomes. The stronger interpretation—whether
benchmark granularity alone caused the difference—is not clean, because both
predictors transferred evidence from a different historical competence unit.

## Historical Run 4A competence unit

Run 4A did not score the teacher's response as the final capability artifact.
For both `local_teacher` and `external_teacher`, the intervention flow was:

1. the teacher received a failed bounded task, diagnostics, authority, and the
   teacher intervention prompt;
2. the teacher produced an intervention/diagnosis (the external path could also
   include a corrected reference output);
3. a Qwen3 1.7B worker received a retry packet containing the task, output
   contract, reference facts, diagnostics, teacher intervention, and authority;
4. the worker's retry response was deterministically validated;
5. `deterministically_validated_rescue` and the Run 4A capability verdict came
   from that worker retry.

Accordingly, the historical scored unit is:

| Field | Run 4A local teacher | Run 4A external teacher |
|---|---|---|
| Supplier identity | Qwen3-Coder-30B local teacher | codex-cli-0.146.0 external teacher |
| Capability | bounded task rescue, including scope-authority-boundary | same |
| Interface | Run 4A teacher intervention protocol plus worker retry packet | same role, external teacher envelope |
| Role/responsibility | provide an intervention that helps the worker repair a failed task | same |
| Downstream dependency | Qwen3 1.7B worker retry is required for the verdict | Qwen3 1.7B worker retry is required for the verdict |
| Validated artifact | worker retry's four-field output | worker retry's four-field output |

The all-family aggregate (local 8/16, external 11/16) and the scope-specific
4/4 figures therefore describe a teacher-plus-worker compound rescue, not
teacher-direct four-field completion. The scope-specific 4/4 is historically
true, but it is not a direct 30B-versus-Codex output score.

## Prospective competence unit

In `DELEGATION_PREDICTION_TEST_SCOPE_V0`, each supplier received the frozen
experiment-authored payload and directly produced the four-field
scope-authority response. There was no downstream worker rescue. The validated
artifact was the direct local or external response under the prospective V2
contract.

| Field | Prospective direct arm |
|---|---|
| Supplier identity | local Qwen3-Coder-30B or external codex-cli-0.146.0 |
| Capability | direct bounded scope-authority output |
| Interface | prospective V2 experiment-authored interface, a compatible successor to Run 4A |
| Role/responsibility | directly emit `allowed_targets`, `held_targets`, `scope_expansion_required`, and `review_status` |
| Downstream dependency | none |
| Validated artifact | direct supplier response |

Thus the prospective scored artifact was the direct teacher response, not the
historical worker-retry artifact.

## Alignment matrix

The supplier names match, but identity alone does not make the competence units
identical.

| Historical evidence | Supplier | Capability | Interface | Role | Downstream dependency | Validated artifact | Overall unit |
|---|---|---|---|---|---|---|---|
| Run 4A all-family, local | EXACT | COMPATIBLE_TRANSFER | COMPATIBLE_TRANSFER | CHANGED | CHANGED | CHANGED | NOT_COMPARABLE |
| Run 4A all-family, external | EXACT | COMPATIBLE_TRANSFER | COMPATIBLE_TRANSFER | CHANGED | CHANGED | CHANGED | NOT_COMPARABLE |
| Run 4A scope 4/4, local | EXACT | EXACT | COMPATIBLE_TRANSFER | CHANGED | CHANGED | CHANGED | NOT_COMPARABLE |
| Run 4A scope 4/4, external | EXACT | EXACT | COMPATIBLE_TRANSFER | CHANGED | CHANGED | CHANGED | NOT_COMPARABLE |

The direct prospective outcomes are genuine evidence about the direct supplier
unit. They are not evidence that the historical compound rescue scores had the
same meaning.

Markers:

```text
HISTORICAL_TO_PROSPECTIVE_COMPETENCE_UNIT_MATCH=false
GENERALIZED_PREDICTOR_UNIT_TRANSFER_REQUIRED=true
DEGENERALIZED_PREDICTOR_UNIT_TRANSFER_REQUIRED=true
PROSPECTIVE_POLICY_COMPARISON_RESULT_VALID=true
BENCHMARK_GRANULARITY_CAUSAL_INTERPRETATION_CLEAN=false
DIRECT_SUPPLIER_PROSPECTIVE_OUTCOMES_OBSERVED=true
```

The generalized predictor also transferred a historical compound aggregate to
direct supplier outcomes. Its external choice was successful in this cohort,
but that does not remove the unit-transfer limitation. The bounded predictor
transferred the historical 4/4 compound evidence to a direct compatible-successor
interface and therefore has the same limitation, plus the narrower scope and
cost evidence transfer.

## Coverage-state audit

The bounded predictor did distinguish the supported non-expanding profile from
the out-of-coverage expansion profile. The artifacts do not support saying
that out-of-profile was encoded as supported negative evidence:

```text
COVERAGE_ABSENCE_WAS_TREATED_AS_NEGATIVE_EVIDENCE=false
OUT_OF_PROFILE_STATE_DISTINGUISHED_FROM_NEGATIVE=true
COVERAGE_ABSENCE_TRIGGERED_ABSTENTION_WITHOUT_NEGATIVE_CAPABILITY_EVIDENCE=true
OUT_OF_PROFILE_FALLBACK_EVIDENCE_POLICY_DEFINED=false
EVIDENCE_STATE_SEMANTIC_COLLAPSE_SUPPORTED=false
EVIDENCE_STATE_ACTIONABILITY_GAP_SUPPORTED=true
```

The eight unnecessary abstentions remain fully observed: external validated
all eight out-of-profile tasks. The precise diagnosis is that the policy
mapped a distinguishable unknown/out-of-profile state to abstention without a
fallback action; it did not prove that the supplier was incapable.

## Direct-output historical evidence inventory

The preserved evidence was searched for a prior matched direct-output unit
using these suppliers, this bounded four-field responsibility, and no worker
rescue. No qualifying pre-target historical evidence was found.

| Evidence | Classification | Reason |
|---|---|---|
| Run 4A all-family and scope 4/4 | `COMPOUND_ONLY` | teacher intervention followed by validated 1.7B worker retry |
| Run 4B scope intervention replication | `COMPOUND_ONLY` | intervention/rescue design; final verdict remains downstream validated output |
| Run 6 validation-gated routing | `COMPOUND_ONLY` | local-first/control scope paths include worker retry and validation |
| Run 7 escalation | `COMPOUND_ONLY` | control and treatment artifacts contain worker retries; escalation is not teacher-direct evidence |
| Run 8 repaired escalation | `COMPOUND_ONLY` | explicit control/treatment description includes worker retry and deterministic validation |
| Prospective Scope V0 run | `EXACT_DIRECT_UNIT` for the direct outcome | direct response, but it is the held-out target evidence and cannot become historical predictor evidence |

The Run 7 report's phrase that external solved some tasks “directly” describes
the external-direct policy path in that experiment; the preserved artifacts
still contain a worker retry and do not establish a teacher-only four-field
score.

## Smallest corrective experiment concept

The cleanest next step is:

`DESIGN_DIRECT_UNIT_CALIBRATION_EXPERIMENT`

This is conceptually prior to another broad-versus-bounded policy comparison.
It should collect matched direct-output evidence for local and external under one
frozen scope-authority interface, with the same direct responsibility and an
independent evaluator, without a downstream worker rescue. The purpose is to
establish the historical evidence unit before asking whether broad or bounded
evidence predicts delegation better.

No implementation, cohort, threshold, or execution plan is frozen here.

The future primary question is:

> When historical evidence and prospective outcomes refer to the same
> supplier × capability × interface × responsibility, does bounded evidence
> predict delegation outcomes better than broad aggregate evidence?

Uncertainty-aware routing should follow, not precede, this alignment work:

```text
COMPETENCE_UNIT_ALIGNMENT_PRECEDES_POLICY_UNCERTAINTY_TUNING=true
```

Sample support, out-of-profile semantics, interface transfer, and broad-score
fallback remain useful hypotheses, but tuning them against the current 16
outcomes would confound policy repair with competence-unit repair.

## Claim boundary

Demonstrated:

- the frozen broad and bounded policies made different delegation decisions;
- direct supplier outcomes were observed and independently validated;
- the broad policy won the preregistered comparison in this disagreement-
  enriched cohort;
- the bounded policy abstained on out-of-profile cases that external later
  solved.

Not established by this sequence:

- that broad benchmark granularity caused the policy difference;
- that the bounded evidence policy was tested on historically aligned direct
  evidence;
- universal benchmark superiority or insufficiency;
- direct supplier qualification or production routing authority.

## Provenance anchors

The detailed machine-readable source inventory and hashes are in the companion
matrix. The primary source anchors are Run 4A execution commit
`15dd84cfa82d9c2cef47778111e811e11ecf7274`, the preserved Run 4A harness, the
prospective predictor specification, runtime manifest, interface contract V2,
evaluator, and the completed prospective diagnosis/closeout artifacts.

No inference, historical-artifact mutation, policy change, qualification
change, production-routing change, or network operation was performed for this
audit.
