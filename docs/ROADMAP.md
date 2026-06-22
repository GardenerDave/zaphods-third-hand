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

## Conversation-Derived Backlog

These items came from project use, failed runs, operator review, and
supervised agent workflow design. They are roadmap commitments only: they must
not be represented as implemented until code, docs, tests, and review evidence
exist. Some items have implemented foundations; the entries below preserve the
remaining hardening, generalization, or operating-guide work.

### 1. Supervised Agent Use

Clarify that ZTH is a supervised workflow system, not merely a
human-supervised one. Humans and agents may both operate inside ZTH packets,
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

## Roadmap Discipline

- Roadmap items must not be represented as implemented until code, docs, and tests exist.
- Privacy-impacting features require explicit docs before implementation.
- Workflow-changing gates should fail closed and preserve human override records.
- Optional evidence should remain optional.
