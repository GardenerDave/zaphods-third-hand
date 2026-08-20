# Model-Size Supplier Floor Research Design

Status: design-only phase document. No model has been selected, downloaded,
installed, called, or preregistered.

## Research question

What is the smallest model that can take repeatable stewardship of a bounded
ZTH capability while remaining economically useful under the confirmed
validation-and-escalation architecture?

This is not a generic model benchmark. Model size is treated as an economic
supplier variable. The relevant question is whether a supplier solves enough
validated work cheaply enough that the remaining failures and escalations cost
less than using the stronger supplier first.

The established architecture is:

```text
cheap evidenced supplier
    -> deterministic validation
    -> stronger supplier only on detected failure
    -> deterministic validation
    -> durable evidence
```

The completed 1.7B phase remains the reference. Run 8 observed 18/20 initial
local passes, 2/2 escalation rescues, 20/20 final treatment solves, 20/20
external-direct control solves, and 60.843% realized policy reduction.

## Supplier ladder

Qwen3 1.7B is the established reference supplier, not a candidate to
re-prove. Candidate research bands below it are:

| Band | Approximate size | Status |
|---|---:|---|
| A | ~1B | Research band; no exact model selected |
| B | ~500–700M | Research band; availability and suitability unknown |
| C | ~250–400M | Research band; availability and suitability unknown |
| D | ~100–200M | Research band; availability and suitability unknown |
| E | below ~100M | Consider only if prior results justify it |

These are size bands, not model selections. A band may have no suitable
current instruct/coding supplier.

## Stewardship definition

A model takes stewardship of a bounded capability only when the evidence shows
all of the following:

- repeatable deterministic validation;
- a known task and failure family;
- a stable input/output contract;
- bounded authority and review-only semantics;
- measured inference/resource cost;
- known escalation behavior;
- durable scorecard evidence;
- no requirement to match the stronger supplier universally.

An imperfect supplier may still be economically useful if validation reliably
identifies its failures and escalation economics remain favorable.

## Capability floor and economic floor

These are distinct limits.

### Capability floor

The smallest model that demonstrates non-trivial, repeatable validated success
on the bounded task family. This floor is about whether the supplier can do
useful work at all, not whether it is the cheapest option.

### Economic floor

The smallest model whose successful work saves enough resource to pay for its
failures and required escalations. This floor depends on measured supplier and
escalation costs and may be higher than the capability floor.

Neither floor is universal across task families.

## Frozen economic model

For a candidate supplier, define:

```text
C_small = measured local supplier action cost
p_fail = measured probability of a valid local failure that triggers escalation
C_escalation = measured stronger-supplier escalation action cost
C_reference = measured reference-first action cost
```

The expected sequential candidate cost is:

```text
C_small + p_fail * C_escalation
```

The candidate is economically cheaper when:

```text
C_small + p_fail * C_escalation < C_reference
```

Therefore the maximum economically tolerable failure rate is calculated for
each candidate as:

```text
p_fail < (C_reference - C_small) / C_escalation
```

The value must be recomputed from measured candidate costs. The historical
35% Run 7/8 break-even rate is not copied to smaller suppliers.

## Initial target capability

The first candidate domain is `scope-authority-boundary`. It is useful because
it has:

- an existing deterministic validator;
- a bounded authority/output contract;
- intervention-blind fresh-fixture methodology;
- a strong external reference supplier;
- frozen 1.7B local evidence;
- empirically exercised validation-gated escalation;
- durable artifact and resource accounting.

The task family is not redesigned by this document. Future experiments must
continue to justify any contemporaneous control or avoid silently pooling the
historical samples.

## Staged floor search

The search should move by substantial size bands rather than exhaustively
benchmark every model:

1. Survey candidates below 1.7B and select one candidate for model-free
   screening only.
2. If a screened candidate is clearly economically viable, move substantially
   downward in size.
3. If it is clearly non-viable, move upward or bracket the boundary.
4. Once adjacent bands bracket viability, perform confirmatory testing around
   that boundary.

This is a logarithmic or binary-search-like strategy where availability and
measured costs permit. The goal is the cheapest demonstrated steward, not a
leaderboard.

## Screening versus confirmation

### Stage A: screening

Screening is a cheap model-audition stage used only to decide whether a
candidate merits a separate preregistration. It may check:

- successful loading;
- output-contract compliance;
- non-zero deterministic solve rate;
- latency/resource measurement;
- basic repeatability;
- absence of catastrophic authority-boundary behavior.

Screening evidence is not confirmatory scientific evidence and cannot be
merged into capability cards.

### Stage B: preregistered confirmation

A confirmation experiment requires fresh fixtures, frozen model identity and
runtime, frozen resource measurements, intervention-blind selection, paired
reference comparison, deterministic validation, frozen escalation semantics,
and a preregistered economic criterion. The first Stage B experiment is not
created by this document.

## Supplier scorecard

Each eventual candidate record should preserve capability-family separation
and include:

- model identity and parameter count;
- quantization and file/storage size;
- RAM/VRAM requirement and hardware;
- prompt/context configuration;
- task family and evidence resolution;
- attempts, validated passes, validated failures, and failure classes;
- pass rate and repeatability observations;
- median, mean, and p95 latency;
- realized resource measure;
- escalation count and escalation rescue count;
- sequential final solve rate;
- expected and realized policy cost;
- candidate-specific break-even failure rate;
- economic viability classification;
- provenance and durable artifact bindings.

## Search movement rules

These are qualitative framework rules; numerical thresholds come only from
measured candidate costs and preregistered criteria.

- **Move down:** repeatable validated capability and comfortable margin inside
  the candidate-specific economic failure threshold.
- **Bracket:** useful validated capability, but observed economics close to
  break-even or insufficient evidence to distinguish the adjacent bands.
- **Move up:** success is too low to remain economically useful even with
  reliable escalation, or the failure pattern violates the bounded authority
  contract.
- **Stop lower search:** validated success approaches zero, fixed overhead
  dominates any possible savings, or no suitable model is available.

The 1.7B reference is not rerun merely because a smaller candidate is
introduced. A future contemporaneous 1.7B control requires separate scientific
justification and preregistration.

## Expected stewardship map

The eventual output should answer “What is the cheapest demonstrated supplier
for this responsibility?” rather than rank generic intelligence:

| Scope-authority-boundary | Status |
|---|---|
| ~1.7B | Established reference; economically supported in Run 8 |
| ~700M | Supported, unsupported, or bracketed after evidence |
| ~300M | Supported, unsupported, or bracketed after evidence |
| ~100M | Supported, unsupported, or not tested after evidence |

The entries below 1.7B are intentionally unfilled until candidate survey,
screening, and separately authorized confirmation occur.

## Authority boundary and next step

This phase defines research only. It does not select a model, download or
install anything, change routing, merge evidence, train, promote, retire, or
queue an intervention. The next separate step is a candidate-model survey and
selection. No first M-parameter experiment is preregistered here.
