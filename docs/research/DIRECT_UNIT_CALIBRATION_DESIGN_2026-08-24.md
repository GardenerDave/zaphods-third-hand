# Direct-Unit Calibration Evidence Program

Date: 2026-08-24
Status: design only; no calibration execution or new experiment freeze

## Purpose

The completed Scope V0 experiment supplied direct supplier observations, but the
historical evidence used by its predictors was mostly a compound teacher-plus-
worker rescue unit. This program creates an aligned evidence base for later
delegation research.

The calibration unit is:

```text
supplier × capability × interface × direct responsibility × validated direct artifact
```

Every scored artifact must be the direct response of the supplier being
measured. A deterministic parser/evaluator is part of validation. A downstream
model repair or rescue is a different competence unit and is excluded from the
direct score.

This calibration does not test whether broad or bounded evidence makes better
delegation decisions. It creates evidence that could support that later test.

## Preserved Scope V0 evidence

The sealed Scope V0 run is now historical evidence relative to any future
experiment. Its direct results were verified from the preserved responses and
scoring-only evaluator:

| Unit | Local direct | External direct |
|---|---:|---:|
| scope-authority-boundary, all 16 | 5/16 | 16/16 |
| supported non-expanding stratum, 8 | 3/8 | 8/8 |
| expansion-required stratum, 8 | 2/8 | 8/8 |

This evidence is eligible as future historical direct-unit evidence, but its
16 target IDs and text must never be reused as targets in a future prospective
holdout:

```text
SCOPE_V0_DIRECT_RESULTS_ELIGIBLE_AS_FUTURE_HISTORICAL_EVIDENCE=true
SCOPE_V0_RESULTS_MUST_NOT_BE_REUSED_AS_TARGETS_IN_FUTURE_PROSPECTIVE_TEST=true
```

It does not retroactively repair the Scope V0 predictor provenance. It becomes
usable only after its original outcomes were sealed and only for a later
design's pre-outcome evidence snapshot.

## Selected calibration units

The minimum program selects three units. Selection is based on deterministic
evaluation, bounded authority, interface control, and fresh fixture support—not
on an expectation that either supplier will perform better.

| Unit | Existing support | Direct-unit suitability | Selection role |
|---|---|---|---|
| `scope-authority-boundary` | Scope V0 direct responses; Run 4A/4B/5/6/7/8 fixture and validator lineage | High | Reuse sealed 16-task direct evidence; add no calls in the minimum program |
| `triage-routing` | Run 4A/5/6 fixture packs and deterministic validation | High | Fresh direct responsibility with a distinct output contract and bounded review authority |
| `unsupported-certainty` | Run 4A fixture/reference-fact and deterministic validator lineage | Medium-high | Fresh direct responsibility for evidence/claim restraint; requires a new model-free freshness pack before execution |

`contradiction-handling` remains a valid reserve candidate. It is not in the
minimum program because its existing contracts vary across fixture variants and
would increase interface-normalization work without being necessary to establish
three distinct direct responsibility units.

### Candidate audit

| Candidate | Evaluator | Fresh cases | Interface | Tools | Authority | Overlap | Cost |
|---|---|---|---|---|---|---|---|
| scope-authority-boundary | available | available | freezable | free | bounded | high, Scope V0 | existing evidence |
| triage-routing | available | available, Run 5 pattern | freezable | free | bounded | medium | moderate |
| unsupported-certainty | available | available, new pack required | freezable | free | bounded | medium | moderate |
| contradiction-handling | available | available | pending normalization | free | bounded | medium | moderate |

Selection is architectural and evaluator-driven, not outcome-driven. The
supplier set remains exactly:

- local: `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`;
- external: `codex-cli-0.146.0`.

Identity must be reverified before any later execution. This design contacts
neither supplier and authorizes no substitution.

## Competence-unit descriptor and interface controls

Each atomic observation must carry:

```text
supplier_id
model_runtime_identity
capability_family
bounded_responsibility
interface_id
interface_hash
supplier_role = DIRECT_RESPONDER
downstream_dependencies = [] for the direct score
validated_artifact
authority_context
evaluator_id
evidence_timestamp
```

The experiment-authored payload is matched across suppliers; native envelopes
are recorded separately:

```text
EXPERIMENT_AUTHORED_PAYLOAD_MATCHED_ACROSS_ARMS=true
DIRECT_RESPONSIBILITY_MATCHED_ACROSS_ARMS=true
```

No tools, repository access, evaluator expectations, teacher intervention, or
downstream repair are allowed in a direct calibration arm.

## Stage A: direct-unit calibration

Stage A consists of matched direct supplier observations under frozen,
family-specific interfaces. It preserves raw response, transport, parse,
contract, and semantic validation separately. Case selection cannot depend on
observed supplier performance.

Fresh cases are generated model-free using existing fixture-pack patterns and
novelty audits. They must not reuse Scope V0 IDs or text, and each case has an
independent evaluator expectation outside runtime input.

The minimum design reuses the 16 sealed Scope V0 direct tasks and adds:

- 4 fresh triage-routing cases;
- 4 fresh unsupported-certainty cases.

Each fresh case runs once for each supplier. This adds 8 new cases and 16 new
supplier calls, while yielding 24 task opportunities and 48 matched direct
observations including the sealed Scope V0 evidence.

The stronger design adds 8 fresh cases per selected fresh family: 8 triage and
8 unsupported-certainty, for 16 fresh cases and 32 new supplier calls. If the
normalized contradiction reserve is added, it becomes 24 fresh cases and 48
new supplier calls. Scope V0 calls are never counted as new calls.

Calibration succeeds when aligned atomic evidence exists across multiple
responsibility/interface units with deterministic validation and provenance. It
does not require disagreement, a supplier winner, significance, or a favorable
routing result.

## Atomic evidence and later aggregation

Preserve raw Bernoulli observations rather than only rates. Each summary retains
successes, failures, opportunities, capability-valid count, transport/parse/
contract/semantic failures, supplier/runtime identity, capability family,
responsibility ID, interface ID/hash, authority context, evidence timestamp,
freshness lineage, raw artifact hashes, and a scoring-only evaluator reference.

The same atomic evidence must later aggregate at:

```text
supplier
supplier × capability_family
supplier × capability_family × interface
supplier × capability_family × interface × responsibility
```

No threshold, confidence formula, weight, or fallback policy is selected here.
The evidence must distinguish point estimates such as 4/4 from 40/40.

Preserve metadata from which these states can later be derived:

```text
SUPPORTED_POSITIVE
SUPPORTED_NEGATIVE
OBSERVED_INSUFFICIENT
UNOBSERVED
OUT_OF_PROFILE
INTERFACE_TRANSFER_REQUIRED
SUPPLIER_OR_INTERFACE_CHANGED
```

The completed diagnosis remains authoritative that out-of-profile was
distinguished from negative evidence, while its actionability gap remains
unresolved:

```text
OUT_OF_PROFILE_STATE_DISTINGUISHED_FROM_NEGATIVE=true
EVIDENCE_STATE_ACTIONABILITY_GAP_SUPPORTED=true
```

## Stage B: clean granularity replication

Stage B begins only after all Stage A observations are sealed:

1. derive a broad direct aggregate from Stage A atomic observations;
2. derive a responsibility/interface-bounded profile from those same observations;
3. freeze both policies and evidence cutoffs;
4. identify only naturally occurring disagreement strata;
5. generate genuinely fresh target instances with a separate deterministic novelty process;
6. freeze an independent evaluator and runtime-only manifest;
7. execute matched supplier arms and compare delegation decisions.

Stage B targets must not appear in Stage A. Stage A outcomes must be sealed
before Stage B policy construction and target generation. A future policy must
not be selected because it is expected to create disagreement:

```text
FUTURE_POLICY_DISAGREEMENT_MUST_EMERGE_FROM_PRE_TARGET_EVIDENCE=true
```

The future gate is `CLEAN_GRANULARITY_REPLICATION_READY` only if aligned atomic
units exist, both summaries are reconstructable, at least one disagreement can
be specified without target outcomes, fresh holdouts remain available, and
supplier/interface identities remain usable. Otherwise use
`CALIBRATION_COMPLETE_NO_INFORMATIVE_GRANULARITY_DISAGREEMENT`.

This gate is not decided by the present design.

## Threats and boundaries

- Scope V0 is direct evidence but was not designed as Stage A; it is historical-
  for-future-use, not evidence for its own predictor.
- The families have different contracts; each interface is frozen separately.
- Small counts expose heterogeneity but do not establish population rates.
- Supplier-native envelopes may differ despite matched experiment payloads.
- Calibration cannot qualify a supplier or change routing.
- Expected supplier weakness is not a family-selection criterion.
- Uncertainty-aware routing and fallback policy design follow unit alignment.

Therefore:

```text
COMPETENCE_UNIT_ALIGNMENT_PRECEDES_POLICY_UNCERTAINTY_TUNING=true
```

No runtime cohort, target outcome, policy, threshold, or qualification decision
is created by this document.
