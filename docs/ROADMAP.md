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

## Integration Roadmap: Improve / Fable / TriDB Harvest

Recent external project review produced 16 integrations for ZTH. These are not separate side projects. They are staged additions to the existing supervised packet, attempt, validation, and provenance workflow.

The immediate objective is to strengthen the existing packet-to-attempt path. Later work adds measurement, lifecycle state, provenance, and retrieval only as the simpler plain-file system exposes the need.

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

This is the active next milestone and the highest-value / lowest-effort target. It remains the low-friction, high-value vertical slice for the next implementation push.

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

### Phase 2 - Measured Prompt-Patch and Model Behavior

This phase measures whether ZTH changes model behavior rather than merely changing output language.

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
- Privacy-impacting features require explicit docs before implementation.
- Workflow-changing gates should fail closed and preserve human override records.
- Optional evidence should remain optional.
