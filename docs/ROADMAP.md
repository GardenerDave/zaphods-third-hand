# ZTH Project Roadmap

This roadmap is a repo-native planning paper trail for implemented, planned, and explicitly deferred work. It distinguishes shipped behavior from roadmap items. Roadmap entries are not implementation claims until code, docs, and tests exist.

## Naming Metaphor

Zaphod's Third Hand uses the Zaphod reference deliberately. In the joke, Zaphod is not simply "smarter"; he has carved out hidden space in his own head and has an extra arm for doing more than a normal body plan should allow.

For this project, that is the metaphor: do not force one model, one chat, or one overloaded operator brain to hold the whole workflow. Carve out explicit working space. Give the operator a third hand: supervised tools, role packets, model auditions, preflight gates, reports, and reviewable artifacts.

The metaphor does not imply autonomous control. ZTH is meant to add external
working memory and extra supervised execution capacity. Humans and agents may
operate inside scoped workflows, while lifecycle movement and other
authority-bearing decisions remain subject to authorized approval.

ZTH workflows are supervised, not autonomous. Humans and agents may both
operate inside the workflow, but authority boundaries are explicit.
Destructive actions, publication, promotion, disclosure, cleanup, and
lifecycle movement require authorized approval.

## Mutual Supervision and Human-Attention Throughput

The operating objective is to **maximize trusted work per unit of human attention**. ZTH provides procedural constraint and verification through scoped task packets, provenance, validators, repo health checks, scaffold contracts, closeout reports, and reviewable handoff evidence. Codex provides semantic critique and implementation through high-reasoning work, abstraction review, test design, and challenges to weak assumptions.

Humans retain decision authority over priority, taste, architecture, merge, release, promotion, policy exceptions, and lifecycle movement. This operating model should reduce repetitive review work without converting evidence or recommendations into unattended decisions.

This model is implemented first through the structured Agent Task Session harness: a reviewable wrapper around scoped Codex work, validation, plain-file handoff, and closeout guidance. It produces draft evidence for human review but does not merge, release, promote, or move lifecycle state on its own.

## Local-First Accessibility and Variant Economy

ZTH's long-term goal is AI accessibility under ordinary local constraints, not
requiring frontier-scale hardware as the default operating assumption. The
roadmap direction is local-first and supervised: make bounded useful work
possible on hardware people can actually own, inspect, route, and review.

This implies a different stance toward small local models. The roadmap does
not treat them as universal generalists that should absorb every task through a
single prompt or one monolithic capability claim. Instead, small models should
be treated as specialized workers inside a supervised bureaucracy: each worker
has guided capability, bounded scopes, explicit evidence, and no unattended
promotion.

If local models can be adapted at home through variants, deltas, adapters,
scaffolds, or other guided capability packaging, then the key roadmap question
shifts. It becomes less "Can a small model handle this task?" and more "Do I
have the right model variant, delta, adapter, scaffold, or capability card,
and enough local storage, to move this task through a supervised workflow?"

Under that thesis, storage, provenance, routing, and review become first-class
infrastructure. ZTH should treat artifact lineage, variant selection,
capability-card boundaries, evidence retention, and review checkpoints as core
operating concerns rather than afterthoughts.

Important target environments include cell phones, SBCs, used mini PCs, and
cheap local servers. The roadmap interest is broad AI accessibility across
those environments, with supervised routing and review doing more of the system
work than any single model instance.

This section is aspirational. It does not claim that ZTH has already solved
phone- or SBC-class training, reliable direct behavior editing, or fully
portable local variant management. Those remain roadmap-level problems that
require evidence, not authority, and must stay behind explicit review and no
unattended promotion boundaries.

## Architectural Direction Update

ZTH is moving from capability discovery toward integration and operational
usefulness. The roadmap now has a demonstrated bounded continuous handoff
milestone, and the next sequence is organized around dogfooding the existing
architecture on ZTH itself, supervised transaction handling, evidence-bearing
handoff, and ZTH-specific authority semantics layered over mature external
standards.

The project should increasingly own:

- authority and permission boundaries;
- allowed / held target semantics;
- qualification and capability profiles;
- validation and review;
- failure classification;
- evidence provenance;
- immutable experiment evidence;
- prompt-patch / correction methodology;
- teacher / worker learning trajectories;
- Project Historian integration.

The project should increasingly avoid owning generic infrastructure that
mature open-source tools or standards can provide. When a standard boundary is
adopted, ZTH should carry its own authority, provenance, validation,
qualification, and review semantics on top of that boundary instead of
replacing them.

Current strategic order:

1. Close the exact Worker-B raw-response capture gap and reproduce the bounded handoff once as a small evidence-closeout item.
1. Dogfood ZTH on ZTH for low-risk, read-only repository observation tasks.
1. Bring documentation ingestion and Project Historian integration into the dogfood loop.
1. Expand into supervised self-hardening on docs, tests, CLI polish, diagnostics, provenance, and evidence packaging.
1. Reduce operator choreography and improve task/status/review UX around the existing transaction flow.
1. Accumulate telemetry and scorecard evidence from real dogfood transactions.
1. Use that evidence for capability-aware, empirical routing.
1. Explore stewardship and curriculum mechanisms after the dogfood corpus is meaningful.
1. Broaden into systematic generalization research only after the above evidence exists.

Demonstrated bounded supervised handoff milestone:

- one bounded 1.7B semantic evidence-observation attempt is executed under the
  supervised handoff transaction;
- the raw response is preserved immutably and validated as semantic evidence;
- ZTH deterministically binds authoritative scope/policy state around that
  accepted semantic result;
- a review or explicit handoff decision is made;
- a second worker, such as 30B or Codex, receives the exact generated
  continuation in a separate recipient run directory with prompt and
  continuation hashes preserved;
- the operator does not manually reconstruct the downstream prompt or copy
  context between model runs;
- the second worker produces a validated semantic result;
- the downstream run is separately reviewed and closed out.

Automatic semantic routing is not required for this acceptance milestone. The
handoff may be explicit or triggered only by already-qualified deterministic
rules.

This milestone is now demonstrated in one fresh lineage. It is not evidence of
arbitrary-task generalization, unattended promotion, universal routing, or
autonomous authority. The remaining closeout item is exact durable
Historian-record capture plus one clean reproduction of the semantic-boundary
pattern on a different task.

Canonical transaction lifecycle:

```text
CREATED
    -> EVIDENCE_BOUND
    -> DISPATCHED
    -> CAPTURED
    -> VALIDATED
    -> REVIEW_REQUIRED
    -> ACCEPTED / REJECTED / ESCALATION_REQUESTED
    -> HANDOFF
    -> COMPLETE
```

Existing packet and runner records remain preserved. Over time, compatible
packet forms may become generated views or events of this canonical
transaction rather than independent orchestration systems. This is a
prospective architecture note only; it does not authorize destructive
migration of historical artifacts.

Standards at system boundaries:

- A2A: agent-to-agent task and artifact exchange.
- ACP: coding-agent sessions such as Codex, OpenHands, or similar agents.
- MCP: tools, resources, and read-only Project Historian context.

These standards solve different boundaries. ZTH retains authority, provenance,
qualification, validation, review, and failure semantics. Each standard still
requires qualification before adoption.

Model gateway safeguards:

- exact model identity remains explicit for qualified research;
- no silent fallback unless a frozen protocol explicitly permits it;
- retries remain governed by the experiment or protocol;
- endpoint and model provenance remain recorded;
- native or direct helpers remain available where exact backend behavior is
  scientifically required, including tokenization and template behavior.

The model gateway is infrastructure, not the ZTH research router.

Evaluation-framework direction for new experiments:

- Inspect AI is the candidate default framework for new research
  qualification and evaluation;
- Promptfoo is the candidate framework for cheaper prompt-patch,
  output-contract, and regression testing.

Historical experiments remain frozen and are not retrofitted merely to use
these tools. Potential ZTH-specific Inspect components remain candidates
pending qualification:

- fixture / dataset adapter;
- output-contract scorer;
- unsupported-certainty scorer;
- authority-boundary scorer;
- Historian evidence adapter;
- provenance exporter.

Coding-agent boundary:

ZTH should supervise coding agents rather than build another terminal,
workspace, editing, shell, or context-management runtime. The intended flow
is:

```text
ZTH task + authority
    -> ACP adapter
    -> Codex / OpenHands / another qualified coding agent
    -> result / proof
    -> ZTH validation and review
```

Codex is the likely first ACP-backed integration because it is already used
in the project, but that does not make it a permanent architectural
dependency.

Operational telemetry versus Project Historian:

- Operational telemetry answers, "What is happening right now?"
- Project Historian answers, "What evidence do we permanently trust about
  what happened?"

OpenTelemetry plus Langfuse or an equivalent self-hostable system may be
evaluated for the operational telemetry layer. Historian remains the durable
evidentiary layer and may reference trace IDs where useful.

Semantic escalation remains a parallel research lane because the recent
compact semantic-observer experiment completed the operational calls but did
not achieve adequate semantic or unsupported-certainty sensitivity. The
semantic observer therefore remains advisory/research-only, has no automatic
routing authority, and is not a dependency for practical supervised handoff.

## Bifurcation, Atomization, and Recomposition

Some repeated failure patterns are better treated as a signal that the current
task boundary may bundle multiple causal mechanisms. That signal is a prompt
to investigate decomposition, not proof that decomposition is always required.

The working sequence is:

1. Bifurcation: repeated failures or trajectory scattering suggest more than
   one causal mechanism may be in play.
1. Atomization: separate hidden responsibilities into independently testable
   units while preserving frozen variables, provenance, and lineage.
1. Generalization: ask whether the newly exposed boundary applies beyond the
   originating case and whether it is reusable.
1. Recomposition: reconnect successful atoms through explicit contracts only
   after their independent behavior is understood.

This yields a bounded research hypothesis: some apparent model capability
floors may actually be decomposition floors. A model can fail an entangled
task while succeeding on the isolated semantic or operational atoms that make
up that task. This is a hypothesis to measure, not a universal claim.

The roadmap should record capability-floor displacement when decomposition
changes the smallest model required for each atom. The minimum useful fields
are the atom name, the smallest successful model before decomposition, the
smallest successful model after decomposition, and whether the atom became
deterministic.

The decomposition role remains prospective and shadow-only:

- Planner asks what steps accomplish this task.
- Decomposer asks whether this is actually one task.

The Decomposer does not rewrite live tasks, launch child experiments, route
authority, promote outputs, or alter production gates. It only records
timestamped frozen observations for later scoring.

This principle is directly suggested by ZTH's own lineage from semantic router
entanglement to evidence-versus-candidate interpretation, semantic
representation versus deterministic policy, epistemic polarity, invariant
scope, candidate-versus-evidence typing, multi-label proposition extraction,
and now per-property classification.

Future semantic research should continue separately on stronger signals such
as structured contradiction checks, claim/evidence validation,
task-specific validators, combined weak signals, uncertainty calibration, and
targeted hard-case fixtures.

Scheduler deferral:

OpenAI Symphony, Temporal, and similar durable orchestration systems should be
evaluated only after the supervised handoff lifecycle is working reliably.
Useful concepts include isolated workspaces, durable workflow state, crash
reconciliation, bounded concurrency, and proof-of-work before closure. Any
scheduler adopted later must preserve ZTH authority boundaries rather than
silently expanding autonomy.

Work classification:

- Immediate: canonical supervised handoff transaction and Historian read-only
  context interface groundwork.
- Exact Worker-B raw-response capture / joinability closeout: the transaction
  context now carries an explicit binding block that ties the preserved raw
  output to the transaction, review, gate, and handoff IDs for inspection and
  regression protection.
- Near-term: common model transport abstraction, first coding-agent / ACP
  adapter, the 1.7B -> handoff -> 30B/Codex demonstration, and runtime
  lifecycle consolidation.
- Research parallel track: semantic escalation research, evaluation
  framework qualification for new experiments, and operational telemetry
  selection.
- Deferred: durable autonomous scheduling and any scheduler-first expansion.

Existing custom infrastructure that should be treated as legacy when mature
replacements cover the same role, but preserved for unique ZTH semantics or
historical evidence:

- packet and runner variants that become generated views of the canonical
  transaction;
- bespoke transport plumbing that is superseded by a qualified model gateway;
- custom agent/session wrappers that are replaced by ACP-backed adapters;
- custom experiment harness components that are superseded by qualified
  evaluation frameworks for new work;
- ad hoc telemetry capture that is superseded by a dedicated operational trace
  system.

## LARQL Direct Editing Status

ZTH's mainline steering path remains prompt and scaffold injection: bounded
packets, provenance, validators, supervised review, and reusable evidence
artifacts.

LARQL direct editing is parked as experimental research evidence. The
end-to-end direct-edit pipeline mechanically worked, but the tested
layer-0 continuation rank-1 edit did not produce behavior-level movement for
the file-scope task. That makes the result useful as bounded evidence, not as
the product path.

The product framing remains small-model guided capability: specialized workers
inside supervised workflows, with variants, deltas, adapters, and scaffolded
review used only when they improve evidence-backed capability.

Completed correction-aware supervised loop dogfood:
[`CORRECTION_AWARE_SUPERVISED_LOOP_DOGFOOD_2026-07-02.md`](reports/behavior_correction_cards/CORRECTION_AWARE_SUPERVISED_LOOP_DOGFOOD_2026-07-02.md).
ZTH converted a small-model file-scope failure into an explicit behavior
correction, produced corrected scoped output from a local 1.7B model,
validated it model-free, packaged it for supervised review, and recorded
explicit supervised acceptance without promotion or downstream mutation.

## Implemented

- LLM-probe preflight import scaffold.
- ZTH-owned local smoke-probe producer and versioned verified-YAML producer
  contract for supervised endpoint preflight evidence.
- Real LLM-probe verified YAML import.
- Source preservation and SHA-256 evidence for imported preflight data.
- `preflight_capability_manifest.json` as a conservative ZTH-owned preflight summary.
- Optional OKF-style markdown export for preflight evidence.
- Preflight regression comparison from canonical capability manifests.
- Direct audition preflight gate through `run_model_audition.py`.
- Board audition preflight gate through `run_model_audition_board.py`.
- Manifest-driven Context Distiller focused passes with explicit input/output
  controls, tracked focus profiles, plan-only rendering, synthesis-only review
  bundles, and legacy comprehensive compatibility.
- Human-review boundary: a preflight pass permits an audition to run; it does not promote, approve, rank, or assign a model.
- Agent Task Session packets with deterministic IDs, path allowlists, required checks, validation, JSON handoff, and optional closeout guidance.
- Model-free operator planner for reviewable import → manifest → gated suite or
  board audition commands. The planner does not execute the chain.
- Live local endpoint smoke through the ZTH producer → verified YAML →
  capability manifest → operator plan → unwaived gated audition chain. See
  [`LIVE_ZTH_SMOKE_PROBE_PREFLIGHT_2026-06-22.md`](reports/preflight_smoke/LIVE_ZTH_SMOKE_PROBE_PREFLIGHT_2026-06-22.md).
- Direct supervised patch-probe milestone: `qwen3-1.7b-gpu-40k` reached
  `ACCEPT` on a corrected, constrained patch packet and produced a reviewed
  human patch checklist. This demonstrates guided capability inside a bounded
  supervised workflow, not general intelligence; weak `stop_conditions` and
  broad “All board names” wording remain review caveats. See the
  [model-audition report guidance](reports/model_auditions/README.md#direct-supervised-patch-probe-milestone).
- Manual supervised model-attempt runner added (`run_manual_supervised_attempt.py`), with prepare/ingest operator flow that keeps model use manual and supervised, records validation evidence, and requires explicit review metadata before downstream gate/handoff artifacts.
- Explicit `call-local` mode added to the manual supervised attempt runner for operator-invoked OpenAI-compatible local endpoint calls that write raw output plus call metadata for the existing supervised ingest/review path without granting execution, mutation, promotion, training, or curriculum-capture authority.
- Explicit `export-pattern` mode added to the manual supervised attempt runner for operator-invoked failure/correction/success pattern export into supervised training pattern candidate artifacts; export is evidence-only and does not grant training or curriculum-capture authority.
- Messy Input Triage Packet v1 validator for the supervised front door that turns messy input into a bounded, review-required triage packet before later packet assembly.
- First manual dogfood sample validates messy project input into a review-required triage packet; future work remains model production, scoring, routing, and handoff into bounded task queues.
- A supervised local-worker audition with a patched contract prompt validated a messy-input triage packet, but router automation and bounded queue handoff remain future work.
- Bounded task packet draft validator for the manual triage-to-bounded-task bridge, keeping queue handoff review-required and non-automated.
- Deterministic fixtures now cover the validated triage-to-bounded-task bridge; future work remains fixture expansion, scoring, and supervised queue-handoff review.
- Bounded task review packet fixtures now cover the next review-only bridge; future work remains fixture expansion, scoring, and supervised queue-handoff review.
- Full front-door chain now has a read-only deterministic validator; future work remains scoring and supervised queue-handoff review.
- Full front-door chain now has a read-only scorecard for review readiness; future work remains scoring calibration and supervised queue-handoff review.
- Full front-door chain now has a read-only review command that validates and scores in one step; future work remains scoring calibration and supervised queue-handoff review.
- Front-door lane synthesis recorded; future work shifts from building the lane to fixture expansion, scoring calibration, and supervised queue-handoff review.
- Diverse front-door chain fixtures added; future work remains scoring calibration and supervised queue-handoff review.
- Front-door fixture expansion synthesis recorded; future work shifts to blocked-case calibration and supervised queue-handoff review.
- Blocked front-door chain fixtures added; future work remains blocked/pass calibration and supervised queue-handoff review.
- Front-door calibration synthesis recorded; future work may consider supervised queue-handoff review design, not implementation.
- Review terminology spec added; front-door status language now uses `ready_for_review`, with historical `ready_for_human_review` retained only in older evidence.
- Queue-handoff review design added as spec-only; implementation remains blocked until a fail-closed validator, fixtures, and explicit approval path exist.
- Queue-handoff review validator added; queue writing remains unimplemented and blocked behind fixtures, explicit approval, and separate review.
- Queue-handoff review fixtures added; queue writing remains unimplemented and blocked behind explicit approval and separate review.
- Queue-handoff review calibration synthesis recorded; queue writing remains unimplemented and blocked behind separate approval-path design, validator, fixtures, and review.
- Queue approval path validator scaffold added; it validates review-only manual queue insertion candidates while queue writing, queue insertion, queue running, and automatic handoff remain unimplemented.
- Long-duration dogfood cron added for supervised review artifact generation; it does not auto-commit, push, queue-write, or mutate main unattended.
- Long-duration dogfood cron script tests added; the loop remains review-artifact-only and non-authoritative.
- Long-duration dogfood recommender now avoids repeating completed script-test work and can point to the next bounded validator-oriented target.
- Long-duration dogfood recommender now avoids repeating the completed queue approval scaffold and points to calibration synthesis.
- Queue approval path calibration synthesis recorded; approval remains review-only and queue insertion, queue writing, queue running, and automatic handoff remain unimplemented.
- Long-duration dogfood recommender now avoids repeating queue approval path calibration synthesis and points to a read-only queue approval review command target.
- Long-duration dogfood recommender now avoids repeating the read-only queue approval review command and points to queue approval review command calibration synthesis.
- Queue approval review command calibration synthesis recorded; the command remains read-only and queue insertion, queue writing, queue running, automatic handoff, and downstream-use authority remain unimplemented.
- Read-only queue approval review command added; it emits explicit review output artifacts while queue insertion, queue writing, queue running, automatic handoff, and downstream-use authority remain unimplemented.
- Long-duration dogfood recommender now uses a declarative milestone map so completed evidence-backed milestones are skipped automatically before recommending the next bounded target.
- Declarative long-duration milestone map calibration synthesis recorded; recommender selection is evidence-driven while queue writing, queue insertion, queue running, automatic handoff, and downstream-use authority remain unimplemented.
- Long-duration dogfood closeout recorded; the milestone map now advances to an operator review point while queue writing, queue insertion, queue running, automatic handoff, and downstream-use authority remain unimplemented.
- Bounded supervised capability-mining ladder added: deterministic worker validation, existing-patch rendering, bounded local-teacher intervention, explicit fail-closed external-teacher adapter, durable linked trajectories, and review-only scorecard aggregation. Automatic patch promotion, training, queue insertion, and acceptance remain unimplemented.
- Transport-aware capability attempts and an opt-in deterministic context-complete retry rung are available; transport failures remain infrastructure evidence and cannot enter capability validation or scorecards.
- Capability-mining Runs 1 and 2 are closed: Run 1's repaired holdout reached 8/10 deterministic retries, while Run 2's 20 fresh tasks reached 9/20. Teacher-free generalization replicated at lower strength; weight learning, permanent capability change, arbitrary out-of-distribution generalization, and universal patch applicability remain unproven.
- v0.4.0 release notes and presentation notes added for the evidence-backed long-duration dogfood loop; the project remains review-only with queue writing, queue insertion, queue running, automatic handoff, and downstream-use authority unimplemented.

## Completed Semantic Supplier/Interface Research

The bounded semantic supplier/interface sequence is completed as research and
evidence work through
[`SEMANTIC_INSPECT_LABEL_ROBUSTNESS_V0`](research/SEMANTIC_INSPECT_LABEL_ROBUSTNESS_V0_2026-08-24.md).
The chronology covers genuine semantic fallback, enum-order and label
counterfactuals, the four-arm label factorial, and the 48-call inspect-label
robustness confirmation. It does not qualify a supplier, change production
routing, or activate a new experiment.

The architectural takeaway is that observable competence is evaluated as a
supplier-capability-interface configuration under an explicit authority/context
boundary and supported by preserved evidence. ZTH retains the operational
mnemonic:

```text
supplier × capability × interface × evidence
```

The existing scorecard/capability-card direction should preserve this
boundedness rather than collapsing evidence into “model X is good at task Y.” A
single scalar may support broad comparison, but delegation-grade records need
coverage, conditional performance, failure modes, interface sensitivity,
freshness, transfer limits, and requalification conditions. Authority remains
independent, and unresolved delegation remains `review` or
`ready_for_review`.

## Queued Research Branches

### `SEMANTIC_INTERFACE_CALIBRATION`

Queued behind documentation and synthesis. Future work may study how
interface-specific evidence should affect bounded supplier development and
scorecards. No experiment is active from this roadmap update.

### `DEGENERALIZED_BENCHMARK_METHODOLOGY`

`EMERGING / REVISE / NOT YET VALIDATED AS GENERAL METHOD`. This is not a
completed general theory or a replacement for standard benchmarks. The working
definition is delegation-aware benchmark decomposition: narrow a broad
capability/performance claim into a responsibility-specific, interface- and
context-conditioned evidence profile before using it to delegate work. Supplier
identity is the evaluated mechanism and frozen evidence supports the claim;
neither is itself a benchmark-decomposition level.

### `DELEGATION_PREDICTION_TEST`

Queued validation target: compare whether a decomposed
responsibility/interface evidence profile predicts actual bounded routing
outcomes better than a generalized supplier score. This has not been tested.

Future work also needs cross-capability replication and cross-supplier/interface
transfer validation. No experiment is activated by this roadmap entry.

## Integration Roadmap: Improve / Fable / TriDB Harvest

Recent external project review produced 16 integrations for ZTH. These are not separate side projects. They are staged additions to the existing supervised packet, attempt, validation, and provenance workflow.

The immediate objective is to use the existing packet-to-attempt path on real ZTH work, then strengthen it further from dogfood evidence. Measurement, lifecycle state, provenance, and retrieval should follow observed needs rather than being built ahead of use.

Documentation ingestion and Project Historian integration are part of that same dogfood loop, not a separate speculative project.

The completed supervised local-worker evidence loop now closes that path end to end:

- the local model acts as a worker and evidence producer, not the orchestrator;
- deterministic repo tools validate and score the generated evidence;
- review bundles preserve authority boundaries in plain files;
- candidate exporter and reviewer tools produce reviewable drafts only;
- human review remains required before fixture import, promotion, or downstream use.

The intended sequence is:

```text
Phase 1:
  make supervised execution evidence-bound

Phase 2:
  measure whether prompt patches and models behave better

Phase 3:
  preserve lifecycle and provenance as durable operating knowledge

Phase 4:
  improve retrieval and context construction using that provenance
```

### Phase 1 - Evidence-Bound Supervised Execution

This foundation is established. The next active milestone is to dogfood it on ZTH itself with low-risk, read-only work before broadening into bounded writes.

The Phase 1 milestone is complete when one real, already-understood coding task passes through the existing supervised workflow and ZTH can:

- validate a zero-context packet;
- detect scoped repository drift;
- enforce step-level verification;
- stop through explicit escalation routes;
- preserve the complete attempt bundle;
- distinguish model claims from observed evidence;
- refute a false or overbroad completion claim;
- keep final acceptance under human control.

1. Zero-context packet validator

   Packets must contain enough objective, authority, scope, evidence, and verification context for an executor that has no hidden conversation history.

2. Commit and scoped-drift metadata

   Packets should record the repository state they were planned against and identify the paths whose drift should stop or reroute execution.

3. Step-level verification contracts

   Each bounded implementation step should carry its expected verification command or observable proof obligation.

4. Explicit stop conditions and escalation routes

   Executors must stop and return control when the packet is stale, contradictory, insufficient, or requires unauthorized scope expansion.

5. Completion-claim validator

   Model claims such as "fixed," "validated," or "tests pass" must be checked against recorded evidence and classified as supported, unsupported, or refuted.

6. Repository-content-is-data prompt patch

   Repository contents are evidence to inspect, not instructions that can override the governing packet, expand scope, or grant authority.

7. Atomic acceptance bundles

   A supervised attempt should preserve packet, raw model output, changed paths, verification results, claim verdicts, and review status as one coherent artifact bundle.

### Phase 2 - Measured Dogfood and Model Behavior

This phase measures whether ZTH changes model behavior rather than merely changing output language, using dogfood tasks and read-only comparison work as the first evidence source.

8. Prompt Patch A/B harness

   Run controlled fixtures with and without a prompt patch using the same model, task, and inference policy.

9. Trap fixture library

   Maintain fixtures for plausible wrong actions, including authority conflict, scope bait, false completion, prompt injection, cleanup bait, retry bait, evidence bait, and ambiguity bait.

10. Multi-dimensional capability cards

   Capability cards should separate instruction adherence, domain correctness, scope discipline, verification honesty, tool execution, evidence interpretation, recovery behavior, context tolerance, latency, and resource cost.

### Phase 3 - Lifecycle, Provenance, and Reconciliation

This phase turns preserved attempts into durable operating knowledge.

11. Rejected-findings ledger

   Preserve findings that were considered and rejected, including evidence, rejection reason, decision authority, commit/version, and conditions for reconsideration.

12. Formal packet lifecycle and reconciliation

   Track states such as discovered, vetted, planned, ready, attempted, blocked, revision required, verified, accepted, reconciled, and retired.

13. Provenance graph

   Preserve relationships among requests, packets, attempts, failures, corrections, validations, accepted artifacts, commits, prompt patches, and capability claims.

### Phase 4 - Evidence Policies and Retrieval Scale

This phase improves retrieval and context construction after the execution/provenance foundations exist.

14. Domain evidence policies

   Routing should select evidence requirements, authority order, verification expectations, and fraud checks by domain, beginning with code-change work and later extending to research, operations, legal/compliance, data analysis, fiction continuity, and infrastructure.

15. Global context-budget planner

   Context construction should use one bounded evidence budget, preserving mandatory authority evidence first and then ranking optional evidence globally.

16. Tri-modal retrieval planner

   Future retrieval should combine semantic similarity, provenance/dependency relationships, and structured eligibility filters such as task, authority, version, scope, commit, environment, and attempt state.

### Next Phase - 120+ Task Supervised Dogfood

The next high-scale dogfood phase should extend the supervised cron/watchdog batch while keeping the local worker model as a bounded evidence producer and keeping every authority-bearing decision under human review.

This next phase remains supervised and local-first:

- the cron/watchdog batch may trigger bounded worker runs, but it does not become an orchestrator for promotion or repository mutation;
- the local worker model produces bounded evidence only;
- no automatic repo edits, fixture imports, training capture, promotion, or downstream-use authority are granted;
- deterministic validation and review bundles are required for each completed stage;
- candidate export and candidate review remain review-only drafts, not import or promotion actions.

The completed supervised local-worker loop, the completed 120-task dogfood batch, and the malformed/partial packet plus review-bundle completeness regression coverage are now recorded in docs and tests. Remaining work is docs/index hygiene, roadmap maintenance, and future targeted regression coverage only.

Recommended acceptance criteria for the 120+ run:

- queue and state files validate cleanly;
- every completed task has the required evidence artifacts preserved;
- failure cases are retained as evidence, not cleaned up;
- candidate exports and reviews are produced only where the evidence path justifies them;
- the final closeout report summarizes queue counts, failures, reviewable candidates, and the non-authority boundary explicitly.

## Explicit Deferrals

The following are deferred unless future roadmap work explicitly promotes them:

- installing or depending on TriDB;
- adding a new database;
- replacing the current supervised runner;
- building a configurable workflow engine;
- generalized natural-language claim extraction;
- broad historical artifact migration;
- full domain-adapter implementation;
- automatic curriculum capture from failures;
- automatic model acceptance, promotion, merge, deployment, or publishing.

## Conversation-Derived Backlog

These items came from project use, failed runs, operator review, and
supervised agent workflow design. They are roadmap commitments only: they must
not be represented as implemented until code, docs, tests, and review evidence
exist. Some items have implemented foundations; the entries below preserve the
remaining hardening, generalization, or operating-guide work.

### 1. Supervised Agent Use

Clarify that ZTH is a supervised workflow system, not merely a
model-only one. Humans and agents may both operate inside ZTH packets,
scaffolds, closeouts, validators, and evidence structures.

The workflow may help an agent handle a large job, but it does not grant
unattended authority.

A supervised agent may:

- prepare packets;
- inspect bounded evidence;
- draft changes;
- run allowed checks;
- produce closeout material;
- identify next actions;
- flag uncertainty or missing evidence.

A supervised agent may not silently:

- promote work;
- erase evidence;
- publish results;
- upload private data;
- bypass approval gates;
- move lifecycle state;
- perform destructive cleanup.

### 2. Voluntary Hardware Report

Add an optional, double-opt-in hardware reporting path for reproducibility and
local model-fit analysis.

The first version should import an existing local system report format,
preferably `fastfetch --format json`, then sanitize and normalize it into a ZTH
hardware summary.

Constraints:

- disabled by default;
- requires explicit config or branch enablement;
- requires explicit command invocation;
- no silent generation;
- no automatic upload;
- no telemetry;
- disposable local output;
- not required for auditions, preflight checks, routing, OKF, promotion,
  scoring, ranking, or model selection;
- redacts hostname, username, serial numbers, MAC addresses, local IPs, exact
  disk IDs, private paths, and other stable identifiers by default;
- requires operator preview before inclusion in any packet.

This item extends the existing `hardware-report-opt-in` planned branch and
preserves its double-opt-in privacy requirements.

### 3. Model Interviewer Authoring Guide

Document how users can safely create custom model-interviewer material without
editing harness internals.

The guide should cover:

- suite files;
- fixture JSONL;
- prompt placeholders;
- scorer profiles;
- board definitions;
- model registry entries;
- failure-mode tags;
- mechanical scoring limits;
- what makes a useful interview criterion;
- how to avoid turning interviews into automatic promotion gates.

Capability reports should inform supervised review. They must not
automatically promote, approve, rank, or route models.

### 4. Logic Probes

Formalize logic probes as a reliability diagnostic layer for small models and
local endpoints.

Probe categories should include:

- authority boundaries;
- evidence vs. inference separation;
- destructive-action discipline;
- contradiction handling;
- scope control;
- structured-output reliability;
- failure-mode tagging;
- unsupported-command behavior;
- cleanup and evidence-preservation judgment.

Logic probes produce diagnostic evidence. They do not grant trust, promotion,
routing authority, or lifecycle authority.

### 5. Vogon Printer

Treat the Vogon Printer as a first-class family of model-free scaffold and
packet-printing tools.

The Vogon Printer should prepare:

- lifecycle forms;
- bounded evidence packets;
- prompt packets;
- role packets;
- checklist scaffolds;
- validation requests;
- closeout packets;
- handoff packets.

The Vogon Printer formats supervised work. It does not execute tasks, promote
outputs, or decide lifecycle movement.

### 6. Change Closeout Gate

Every meaningful change should have a standard closeout path.

A closeout should capture:

- what changed;
- what evidence was produced;
- what checks were run;
- what docs were updated;
- what safety boundaries were considered;
- what public/private sanitization was performed;
- whether the change is ready for promotion;
- known leftovers;
- operator or authorized-review status.

The closeout gate should make unfinished work visible instead of pretending
that a code change alone completes the lifecycle.

### 7. Evidence Lifecycle and Cleanup Advisor

Add inspection-first evidence lifecycle tooling and docs.

The system should help users inspect, preserve, archive, or discard run
evidence safely.

It should support:

- run evidence indexes;
- failed-run preservation hints;
- non-destructive cleanup recommendations;
- suggested archive/delete actions;
- explicit confirmation for destructive cleanup;
- warnings before deleting `.work`, logs, model outputs, reports, or
  failed-run artifacts.

Cleanup guidance should lead with inspection and learning commands before
destructive commands.

### 8. Context Distiller Canonicalization Gate

Formalize the rule that raw conversations are not canonical project memory.

The Context Distiller should distinguish:

- raw transcript;
- candidate fact;
- decision;
- open question;
- workflow rule;
- bug or failure;
- preference;
- accepted memory;
- rejected or noisy material.

Conversation-derived material should be promoted through reviewable
intermediate states rather than blindly appended to canonical docs.

### 9. Panel Synthesis Governance

Strengthen multi-role and multi-agent synthesis governance.

Roadmap capabilities should include:

- agreement maps;
- disagreement sections;
- blind-spot analysis;
- confidence thresholds;
- output-contract versioning;
- configurable role packets;
- pre-synthesis file-existence checks;
- incremental output writing per finding;
- bounded retry for mechanical failures only.

Multiple agents producing output does not itself create authority. Synthesis
remains supervised and evidence-bound.

### 10. Endpoint Safety Profile

Document and enforce safer local model endpoint practices.

The safety profile should cover:

- localhost-first defaults;
- warnings for `0.0.0.0`;
- LAN exposure risk;
- no-auth endpoint risk;
- the distinction between an audition harness and a production server;
- safe examples using `127.0.0.1`;
- explicit danger-zone docs for LAN tests;
- no assumption that the harness provides authentication.

Endpoint examples should not accidentally teach unsafe exposure as the default
path.

### 11. OKF Categorization Adapter

Add an OKF categorization adapter where OKF fits.

The adapter should:

- use OKF-compatible categories when appropriate;
- fail visibly when OKF is insufficient;
- preserve original source labels separately from mapped labels;
- provide project-local taxonomy escape hatches;
- avoid silently forcing ambiguous material into bad categories.

Unsupported mappings should fail forward visibly instead of degrading into
sloppy categorization.

### 12. Report Interviewer

Create a generic messy-report-to-dev-packet interviewer.

The workflow should turn informal reports such as “I clicked around and
something broke” into structured development packets.

Output should include:

- reproduction steps;
- expected behavior;
- actual behavior;
- environment;
- build or version information;
- logs/screenshots requested;
- suspected component;
- minimal viable dev issue;
- optional PR-readiness checklist.

The first use case may be ResonantOS-style beginner bug reports, but the tool
should remain generic.

### 13. Capability Card Operating Guide and Experiment Metrics Recorder

Document how humans and agents should interpret capability cards, model
audition reports, and exploratory experiment metrics.

The operating guide should explain:

- which model is useful for which role;
- which tasks require stronger reasoning;
- which tasks can be delegated to small models;
- known failure modes;
- context-window limits;
- prompt-length limits;
- timeout behavior;
- when a model is suitable only for triage;
- when a model should not be trusted for final synthesis.

The metrics recorder should capture repeatable experiment data for small-model,
quantization, and ternary-model experiments:

- model name;
- quantization;
- endpoint;
- prompt suite;
- context size;
- runtime;
- timeout;
- pass/fail;
- failure tags;
- token counts where available;
- notes;
- optional hardware report reference only when separately opted in.

Capability cards and metrics support supervised judgment. They do not
automatically promote, approve, rank, or route models.

## Planned Branches

### `hardware-report-opt-in`

Future voluntary hardware reports should be developed on a separate branch.

Requirements:

- Double opt-in:
  1. enabled in the hardware-report branch or config;
  2. explicitly called by the operator.
- Disposable:
  - existing workflows continue when absent;
  - the user can ignore or delete it;
  - no report is generated silently.
- Privacy boundaries:
  - no telemetry;
  - no uploads;
  - no serial numbers, MAC addresses, hostnames, usernames, exact disk IDs, or other stable identifiers by default.
- Preferred borrowed-source direction:
  - prefer wrapping and sanitizing `fastfetch` JSON first;
  - consider `inxi` or `lshw` import later;
  - treat `hw-probe` as manual/import-only because upload workflows are not appropriate by default.
- Relationship to preflight:
  - optional supporting context only;
  - not required for preflight import, auditions, OKF export, gating, scoring, ranking, or promotion.

## Future / Experimental

- LARQL Affordance Patch Probe v0 scaffold for classifying machine-specific
  failures into host-profile, LARQL patch, LoRA training, stacked, or
  review-only repair candidates. This is an experimental file workflow only;
  no model editing or training is performed.
- Affordance Dogfood Report v0 scaffold for reviewing one generated affordance
  candidate while keeping promotion held pending probes.
- Affordance Candidate Probe Runner v0 scaffold for packaging one generated
  affordance candidate's probe and regression prompts into dry-run artifacts or
  explicit supervised endpoint probes. Promotion remains held pending review.
- Provider config generation for LLM-probe from ZTH model configs.
- Output-failure heuristics such as empty response, degenerate output, and thinking-block leakage in ZTH audition scoring.
- Optional hardware report attachment to preflight or audition metadata.
- Preflight result history and trend reports.

## Explicit Non-Goals

- No automatic model promotion.
- No unattended lifecycle movement.
- No preflight status as ranking or score.
- No OKF export as internal source of truth.
- No required hardware reporting.
- No telemetry or uploads.
- No hidden hardware collection.
- No deletion or rewriting of evidence by default.

## Repo Audit Follow-Up (2026-07-06)

- A recent repo audit identified general repo-health follow-ups (stray files,
  packaging questions, one pre-existing unrelated test failure, historical
  report cleanup).
- This pass intentionally performs no broad cleanup and preserves existing
  evidence and dogfood artifacts.
- The next architecture work is the prompt patch library
  (`docs/PROMPT_PATCH_LIBRARY.md`), the triage/router packet layer
  (`docs/TRIAGE_ROUTER.md`), the orchestration boundary
  (`docs/ORCHESTRATION_BOUNDARY.md`), the messy input triage front door
  (`local_harness/validate_messy_input_triage_packet.py` and
  `docs/TRIAGE_ROUTER.md`), the model prompt packet renderer
  (`docs/MODEL_PROMPT_PACKET_RENDERER.md`), supervised model attempt
  recording (`docs/SUPERVISED_MODEL_ATTEMPT_RECORDER.md`), supervised
  attempt output validation (`docs/SUPERVISED_ATTEMPT_OUTPUT_VALIDATION.md`),
  supervised review decision records
  (`docs/SUPERVISED_REVIEW_DECISION_RECORD.md`), supervised downstream-use
  gate records (`docs/SUPERVISED_DOWNSTREAM_USE_GATE.md`), supervised
  handoff packets (`docs/SUPERVISED_HANDOFF_PACKET.md`), and supervised
  chain smoke integration proof (`docs/SUPERVISED_CHAIN_SMOKE.md`) as a
  model-free chain toward future workflow-specific supervised consumers.
- General audit issues remain a separate track and are only addressed when a
  library/router/orchestration change directly depends on them.

## Roadmap Discipline

- Roadmap items must not be represented as implemented until code, docs, and tests exist.
- Empirical capability cards and an advisory-only intervention router now extract transport-valid Run 1/Run 2 evidence by task family and normalized deterministic failure signature; execution routing, automatic rung skipping, patch promotion, training, and queue insertion remain unimplemented. A proposed Run 3 cost/solve experiment is design-only.
- Privacy-impacting features require explicit docs before implementation.
- Workflow-changing gates should fail closed and preserve human override records.
- Optional evidence should remain optional.
