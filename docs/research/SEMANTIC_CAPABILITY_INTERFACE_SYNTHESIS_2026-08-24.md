# Semantic Capability and Interface Synthesis

Status: completed research synthesis for the closed 2026-08-23/24 semantic
supplier/interface sequence. This document is additive; historical reports and
raw artifacts remain authoritative and unchanged.

## Executive summary

The sequence supports a stronger architectural unit than “model X can do task
Y”:

```text
supplier × capability × interface × evidence
```

The tested Qwen3 1.7B-labeled / 2.032B operative supplier could supply a
decision-critical bounded operation-class distinction when deterministic code
could not resolve it. Its observed competence then changed materially when the
surface labels in the interface changed, even though requests, definitions,
authority, semantic positions, model settings, and evaluator boundaries were
held constant within the relevant comparisons.

The result is not a supplier qualification and does not change production
routing. It is evidence that competence claims must stay indexed to the
responsibility and interface through which the supplier is actually delegated
work.

The sequence also motivates an emerging research direction,
**DEGENERALIZING BENCHMARKS**: progressively decompose broad benchmark claims
until the measured unit matches a bounded responsibility under a specific
supplier/interface/evidence configuration. This is a methodology hypothesis,
not a completed general theory.

## Evidence anchors

The synthesis was checked against these preserved freeze and closeout anchors:

| Slice | Freeze / design anchor | Closeout anchor |
|---|---|---|
| True semantic fallback V1 partial | `25b6051b910acece9dcc192533e86f0bf8db4cdb` | `3da279086a1864244f26bc09c9e527eb4f92fbce` |
| True semantic fallback V2 | `39adc0477d68b8c3fa6fae10ee34d8543ffc34d9` | `TRUE_SEMANTIC_FALLBACK_V2_2026-08-23.md` |
| Enum-order counterfactual | `f14023e7484584b975cbac93989daa0f01767e7b` | `SEMANTIC_ENUM_ORDER_COUNTERFACTUAL_V0_2026-08-23.md` |
| Semantic label counterfactual | `0a8018567b992ed5bd79a90a97497c2d4c773ea1` | `SEMANTIC_LABEL_COUNTERFACTUAL_V0_2026-08-23.md` |
| Semantic label factorial | `29a3eb0cde307266a575cd1b16ca4b682e2c089c` | `5ddf5b425ad1209aab6bbea196db82494a8b0046` |
| Inspect-label robustness | `e69c2d3c0470cf7add591471b881fc52d12cc268` | `1881319a1cd977903457d36cc82681b38d58a7d4` |

The current documentation synthesis and benchmark hypothesis note are at
`59e96b3f2f8554d295b0d2b2c388a37021fbf4ef`.

## Research question and boundaries

Zaphod’s Third Hand is intended to allocate bounded responsibilities to the
cheapest empirically qualified supplier under explicit authority constraints.
The semantic slice asked a narrow question: can a local model supply an
operation-class fact only when deterministic routing cannot, and how stable is
that supplier capability under controlled interface representations?

The sequence preserved these boundaries:

- deterministic routing owns model-necessity decisions;
- the model returns only a bounded operation-class candidate;
- runtime authority is independent environment state;
- evaluator expectations are scoring-only;
- target extraction, normalization, capability planning, and terminal checks
  remain deterministic;
- missing execution suppliers fail closed to `ready_for_review`;
- no result qualified a supplier or changed production routing.

## Chronology and evidence

| Experiment | Question / frozen intervention | Supplier / calls | Primary result | Weakened or falsified hypothesis | Supported bounded claim | Remaining uncertainty |
|---|---|---:|---|---|---|---|
| Deterministic-first semantic-fallback necessity audit | Audit six preserved fallback calls; test whether polite-wrapper presence requests were genuinely unresolved | Existing Qwen3 1.7B evidence; model-free audit of 6 preserved calls | All six had enough deterministic presence context; polite-wrapper calls were counterfactually avoidable | Polite wrappers implied genuine model necessity | Some model necessity was induced by routing/interface syntax | Genuine unresolved operation language still needed a clean test |
| True semantic fallback V1 partial | Enum-only operation-class fallback with neutral targets, shared authority, and two safe classes | Qwen3 1.7B-labeled / 2.032B operative; 1 of 6 planned calls observed | One genuine response returned `inspect` for an expected presence task; valid semantic failure preserved; planner then crashed | Target leakage, authority leakage, and output-contract failure were ruled out | First decision-critical genuine semantic supplier failure was captured | One observation was insufficient; planner needed repair |
| True semantic fallback V2 | Fresh oracle-clean baseline with repaired planner and six genuine fallback tasks plus four controls | Same supplier; 6 model calls, 1 bounded control tool call | All six semantic outputs were `inspect`: inspect 3/3, presence 0/3 | Broad interface failure was weakened by strict output compliance and inspect success | Genuine semantic fallback and model-to-capability-plan transition demonstrated; class collapse observed | Cause of class asymmetry remained unresolved |
| Enum-order counterfactual V0 | Reverse the two safe enum values while holding semantic position and all other inputs constant | Same supplier; 12 paired model calls | Both arms returned `inspect` 6/6; output changed 0/6 | First-enum/structured-order explanation materially weakened | Collapse was invariant to this enum-order perturbation | Label tokens, definitions, and interactions remained plausible causes |
| Semantic label counterfactual V0 | Replace both literal labels with neutral labels while preserving meanings and positions | Same supplier; 12 paired model calls | Current labels scored 3/6; neutral labels 6/6; presence recovered 3/3 and inspect stayed 3/3 | Missing underlying presence-vs-inspect distinction was weakened | Underlying bounded distinction and label-dependent observable competence demonstrated | Both labels changed together; individual causal contribution was not isolated |
| Semantic label factorial V0 | 2×2 original/neutral presence and inspect surface labels | Same supplier; 24 model calls | A 5/6, B 6/6, C 3/6, D 6/6; inspect stable 12/12; factorial presence-task inspect-label main effect +2/3 and interaction +2/3 | Simple “neutral is always better” and single-label certainty were weakened | Literal `inspect` had a bounded adverse effect on presence decisions, moderated by the competing label | Six-task slice; task-set variability and interaction mechanism remained |
| Semantic inspect-label robustness V0 | Hold presence label constant; test three inspect replacements on 12 fresh tasks | Same supplier; 48 model calls | A 6/12, B 10/12, C 9/12, D 11/12; presence A/B/C/D = 0/6, 4/6, 6/6, 6/6; inspect = 6/6, 6/6, 3/6, 5/6 | Universal replacement robustness and a single “good token” explanation were weakened | Interface representation reshapes the decision boundary; replacements trade presence recovery against inspect stability | No tested interface reached 12/12; transfer beyond this task family is unknown |

The V1 partial, V2 baseline, and all later counterfactuals are documented in
their individual closeouts. The final robustness raw artifacts and per-call
hashes are in
[`SEMANTIC_INSPECT_LABEL_ROBUSTNESS_V0_MATRIX_2026-08-24.json`](SEMANTIC_INSPECT_LABEL_ROBUSTNESS_V0_MATRIX_2026-08-24.json).

## Key research progression

### Model necessity was initially overstated

The first deterministic-first routing slice routed polite-wrapper requests to a
model because the operation token was inconveniently positioned. The
model-free necessity audit showed that the presence context, one safe target,
and ambiguity/risk checks already uniquely implied `observe_presence`.

This separated genuine semantic uncertainty from a syntactic/interface
condition that merely blocked deterministic resolution. The result expanded
model-call avoidance and narrowed the legitimate fallback boundary.

### Genuine semantic fallback was isolated

The oracle-clean true-fallback design used neutral targets, shared
class-independent authority, a separate evaluator, and the smallest unresolved
fact: `observe_presence` versus `inspect`. V2 showed that the model can own
this fact in a bounded routing path. The model did not select targets, tools,
authority, success, or escalation.

The result is `TRUE_SEMANTIC_FALLBACK_DEMONSTRATED` only in this bounded sense.
It is not broad natural-language competence or end-to-end task completion.

### The initial behavior collapsed toward inspect

Across the clean V2 baseline and the enum-order counterfactual, inspect cases
were correctly classified while presence cases often became inspect. Strict
JSON, enum, and admissibility compliance ruled out a general structured-output
or instruction-following failure.

### Enum order did not explain the collapse

Reversing the two safe enum positions produced no changed outputs: both arms
returned `inspect` for all six tasks. This materially weakened the
first-enum/structured-decoding hypothesis without disproving every possible
decoding interaction.

### Label substitution exposed interface dependence

Changing both labels to neutral tokens recovered all three presence decisions
while preserving inspect decisions. The factorial then held one label constant
at a time. Its strongest isolated comparison changed only the inspect label:
neutral `class_beta` preserved presence at 3/3, while literal `inspect` fell to
0/3 in the paired arm. The factorial therefore localized a bounded adverse
effect to the literal inspect surface label in the presence class, with a
nonzero interaction involving the competing presence label.

### The larger robustness holdout refined the claim

The 48-call confirmation showed that replacement behavior is not uniform:

- `class_beta`: presence 4/6, inspect 6/6;
- `operation_two`: presence 6/6, inspect 3/6;
- `examine_target`: presence 6/6, inspect 5/6.

All replacements improved presence over literal `inspect`, but none achieved
both perfect class performance. The correct conclusion is not “inspect is a
bad token” or “neutral labels are better.” It is that interface representation
measurably reshapes the supplier’s observable decision boundary.

## The competence unit: supplier × capability × interface × evidence

The sequence motivates indexing competence claims by four elements:

| Element | Meaning in ZTH |
|---|---|
| Supplier | The mechanism providing the responsibility: deterministic code, model, tool, review, or an explicitly bounded escalation supplier |
| Capability | The bounded responsibility being evaluated, such as operation-class classification, target extraction, observation, or post-observation policy |
| Interface | The concrete request, schema, labels, definitions, protocol, context, and authority boundary through which the responsibility is assigned |
| Evidence | Frozen requests, evaluator, runtime manifests, raw outputs, validations, telemetry, hashes, and closeout interpretation supporting the claim |

Authority/context is an important conditioning boundary and should be recorded
alongside the core expression where it affects delegation.

The implication is operational: a supplier must not inherit competence across
interfaces without evidence. Passing capability X through interface A does not
qualify capability X through interface B. Conversely, failure through one
interface does not prove absence of the underlying capability. The completed
label experiments demonstrate both directions of this caution.

## Scorecard implications

The existing atomic supplier scorecard is evidence-oriented, but future
scorecards and capability cards should be able to represent a bounded record at
least conceptually as:

```text
supplier
capability_id
interface_id/version
authority boundary/context
evidence set
observed metrics
known failure modes
qualification state
```

This is a documentation requirement, not a schema migration in this pass. A
score such as “model X is good at task Y” is too coarse for responsibility
delegation when interface changes can alter observed behavior. Existing
scorecards remain historical evidence and do not gain retroactive interface
qualification from this synthesis.

## Degeneralizing benchmarks

Status:

```text
EMERGING_RESEARCH_METHODOLOGY
NOT_YET_GENERALIZED
NOT_A_REPLACEMENT_FOR_STANDARD_BENCHMARKS
```

**Degeneralizing benchmarks** means starting from a broad benchmark or
capability claim and progressively decomposing it until the measured unit
corresponds to a bounded responsibility under a specific supplier/interface/
evidence configuration.

```text
general benchmark
    → capability family
    → bounded responsibility
    → interface/protocol
    → authority/context boundary
    → supplier
    → frozen evidence
```

The objective is not to discard generalized benchmarks. It is to identify where
a generalized score stops being predictive of the responsibility actually
being delegated. The semantic sequence motivates this because the same
supplier and underlying bounded distinction produced materially different
measurements under controlled interface changes.

### Tentative de-generalization loop

1. Observe a generalized benchmark or capability claim.
2. Identify the bounded responsibility actually needed.
3. Construct an independent evaluator.
4. Separate authority from model output.
5. Remove deterministic cases first.
6. Establish genuine supplier necessity.
7. Test the bounded supplier/interface pair.
8. Diagnose systematic failures.
9. Perturb one interface factor at a time.
10. Re-test on fresh holdouts.
11. Record competence and failure at the narrowest justified unit.
12. Escalate or generalize only when the evidence supports it.

This loop is a research proposal derived from one semantic task family. It has
not been validated as a general benchmark methodology.

## Implications for ZTH

ZTH is not primarily trying to find “the smartest model.” It is trying to
allocate bounded responsibilities to the cheapest empirically qualified
supplier under current authority constraints. The sequence shows why model
identity or a generalized score is insufficient for that decision.

Routing and scorecards should ask:

- which capability is being delegated;
- through which interface and protocol;
- under which authority/context boundary;
- with which frozen evidence;
- with what review or `ready_for_review` fallback when coverage is incomplete.

This supports heterogeneous supplier composition and intelligence-surface
minimization: deterministic code handles what it can, models supply only
genuinely missing bounded facts, tools observe within authority, and review
remains an explicit supplier/state rather than a model self-decision.

## Claim calibration

### Demonstrated

- Genuine bounded semantic fallback can occur.
- Model output can contribute a decision-critical semantic distinction.
- The tested supplier possesses the bounded presence-vs-inspect distinction
  under at least some interfaces.
- Enum order did not explain the observed collapse in the tested counterfactual.
- Interface label changes materially changed observed behavior.
- Different replacement labels produced different error tradeoffs.
- Interface-dependent observable competence was demonstrated.

### Supported or strongly motivated

- Supplier competence should be indexed by interface.
- Benchmark results may need decomposition before delegation decisions.
- Interface calibration is a meaningful supplier-development activity.

### Emerging hypothesis or methodology

- Generic benchmark insufficiency as a broader phenomenon.
- Degeneralizing benchmarks as a general methodology.
- Transfer of this interface effect beyond this semantic task family.

### Not demonstrated

- Generic benchmarks are useless.
- ZTH has solved benchmarking.
- The effect generalizes to all models or all capabilities.
- Any tested interface is production-qualified.
- The 1.7B supplier broadly qualifies for semantic routing.

## Roadmap branches and open questions

The completed research/evidence sequence runs through
`SEMANTIC_INSPECT_LABEL_ROBUSTNESS_V0`. No new experiment is activated by this
document.

Queued branches:

- **SEMANTIC_INTERFACE_CALIBRATION** — investigate how interface-specific
  evidence should inform bounded supplier development and scorecards.
- **DEGENERALIZED_BENCHMARK_METHODOLOGY** — document and, in a later reviewed
  phase, test whether the decomposition loop transfers to other bounded
  responsibilities.

Future questions include whether the method reproduces for other semantic
classes, how interface calibration can avoid evaluator leakage, how evidence
transfer across interfaces should be justified, how narrow a benchmark must be
before its score predicts delegated work, and whether deterministic decomposition
can reduce benchmark scope before model testing.

These are queued research questions, not implementation tasks or production
routing changes. Preserve `review` and `ready_for_review` as the authority
boundary for unresolved work.
