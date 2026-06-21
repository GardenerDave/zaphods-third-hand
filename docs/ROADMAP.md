# ZTH Project Roadmap

This roadmap is a repo-native planning paper trail for implemented, planned, and explicitly deferred work. It distinguishes shipped behavior from roadmap items. Roadmap entries are not implementation claims until code, docs, and tests exist.

## Naming Metaphor

Zaphod's Third Hand uses the Zaphod reference deliberately. In the joke, Zaphod is not simply "smarter"; he has carved out hidden space in his own head and has an extra arm for doing more than a normal body plan should allow.

For this project, that is the metaphor: do not force one model, one chat, or one overloaded operator brain to hold the whole workflow. Carve out explicit working space. Give the operator a third hand: supervised tools, role packets, model auditions, preflight gates, reports, and reviewable artifacts.

The metaphor does not imply autonomous control. ZTH is meant to add external working memory and extra supervised execution capacity while keeping lifecycle movement human-reviewed.

## Mutual Supervision and Human-Attention Throughput

The operating objective is to **maximize trusted work per unit of human attention**. ZTH provides procedural constraint and verification through scoped task packets, provenance, validators, repo health checks, scaffold contracts, closeout reports, and reviewable handoff evidence. Codex provides semantic critique and implementation through high-reasoning work, abstraction review, test design, and challenges to weak assumptions.

Humans retain decision authority over priority, taste, architecture, merge, release, promotion, policy exceptions, and lifecycle movement. This operating model should reduce repetitive review work without converting evidence or recommendations into unattended decisions.

This model is implemented first through the structured Agent Task Session harness: a reviewable wrapper around scoped Codex work, validation, plain-file handoff, and closeout guidance. It produces draft evidence for human review but does not merge, release, promote, or move lifecycle state on its own.

## Implemented

- LLM-probe preflight import scaffold.
- Real LLM-probe verified YAML import.
- Source preservation and SHA-256 evidence for imported preflight data.
- `preflight_capability_manifest.json` as a conservative ZTH-owned preflight summary.
- Optional OKF-style markdown export for preflight evidence.
- Preflight regression comparison from canonical capability manifests.
- Direct audition preflight gate through `run_model_audition.py`.
- Board audition preflight gate through `run_model_audition_board.py`.
- Human-review boundary: a preflight pass permits an audition to run; it does not promote, approve, rank, or assign a model.
- Agent Task Session packets with deterministic IDs, path allowlists, required checks, validation, JSON handoff, and optional closeout guidance.

## Next

- Operator convenience flow for the full import → manifest → gated audition chain.
- Real local endpoint smoke run using actual LLM-probe output.

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
