# Architecture

Start here: [`README.md`](../README.md) ->
[`docs/README.md`](README.md) -> [`docs/FIRST_SUCCESS.md`](FIRST_SUCCESS.md).

## Operating Model

Zaphod's Third Hand is a plain-file, supervised workflow kit. Humans and agents
may prepare, transform, execute, and compare evidence inside explicit scope.
Humans retain decision authority over acceptance, model assignment, repository
changes, publication, destructive cleanup, and lifecycle movement.

The repository or operator environment owns:

- source material and private configuration;
- job and role packets;
- generated evidence and audit files;
- review, acceptance, and lifecycle decisions.

Endpoint-backed model workers receive bounded requests and return output. They
do not own repository files, source archives, job state, acceptance state, or
canonical project memory.

ZTH's mainline is prompt and scaffold steering plus artifact boundaries.
Direct weight editing and patched-model comparison remain in the repository as
parked research evidence, but they are not the architectural center of the
public workflow.

## Runtime Classes

| Runtime class | Meaning | Examples |
|---|---|---|
| Model-free | No model endpoint is required. | Export ingestion, chunk planning, packet generation, validation, dedupe, review bundles, preflight import/comparison, report generation, packet preparation, and output comparison. |
| Endpoint-backed | The live operation uses an existing OpenAI-compatible endpoint supplied by the operator. | Context Distiller generation, selected ChatGPT signal-extraction packets, board auditions, exploratory prompt runs, and model-backed Aider execution. |
| Optional local lifecycle | Exploratory tooling may download a GGUF and start or stop a temporary local llama.cpp server. | `local_harness/model_auditions/` only. |

Core endpoint-backed workflows expect an existing endpoint. The optional
small-model exploratory harness is the exception that can manage temporary
local llama.cpp/tmux sessions. It is not a production model-server manager.

## Common Evidence Boundary

Every workflow follows the same control pattern:

```text
source or packet
    -> bounded tool or supervised model call
    -> plain-file evidence
    -> authorized review
    -> explicit authorized decision, if any
```

Evidence creation does not itself:

- accept generated context as canonical;
- authorize repository edits or lifecycle movement;
- promote, approve, rank into a role, or assign a model;
- certify a model or endpoint as production-ready;
- approve unattended execution.

The correction-aware supervised loop is the clearest end-to-end example of the
current architecture in practice:

```text
behavior correction card
    -> explicit job-packet assignment
    -> behavior correction scaffold
    -> correction-aware prompt packet
    -> authorized local model attempt
    -> model-free output validation
    -> supervised review packet
    -> supervised review decision record
    -> accepted as corrected output only
```

That chain shows guided capability inside a supervised workflow. It does not
mean the model learned autonomously or that the accepted output was promoted.

## Vogon Printer Family

Vogon Printer is the informal documentation umbrella for ZTH's model-free
packet/scaffold printers and their read-only validators or advisors:

```text
Agent Task Session + Tool Maker + Change Closeout
    -> plain-file packets and review scaffolds

validate_scaffold + repo_health_check + git_sync_cleanup
    -> contract, repository-health, and Git-state evidence
```

This is not a new runtime or orchestration layer. The tools remain independent,
no tool automatically invokes the next, and humans retain execution,
acceptance, lifecycle, merge, release, promotion, and cleanup decisions.

See [`VOGON_PRINTER.md`](VOGON_PRINTER.md).

## Context Distiller

```text
source transcript or log
    -> compact or chunked endpoint-backed distillation
    -> session summary + review patch + run metrics
    -> human review
    -> accept, rework, reject, or route a separate update packet
```

The model-free metrics reporter can inspect bundled or completed run records
without an endpoint. Actual summary and review-patch generation requires an
existing OpenAI-compatible endpoint.

Session summaries and review patches are evidence. A human-reviewed, separately
authorized action is required before any proposed context becomes canonical.

The current head script writes active artifacts under `outputs/sessions/`,
`outputs/review_patches/`, and `outputs/run_records/`. It also creates
`outputs/context/` and `outputs/indexes/` as reserved context-artifact and
index/manifest locations; those two directories may remain empty in the
current workflow.

See [`CONTEXT_DISTILLER_WORKFLOW.md`](CONTEXT_DISTILLER_WORKFLOW.md).

## ChatGPT Export Ingestion and Signal Review

```text
private ChatGPT export
    -> normalize conversations                    [model-free]
    -> plan deterministic chunks                  [model-free]
    -> generate extraction packets                [model-free]
    -> run selected packets                       [endpoint-backed, optional]
    -> normalize and validate raw signals         [model-free]
    -> dedupe + identify conflict candidates      [model-free]
    -> build review bundle and candidate files    [model-free]
    -> human review and separate acceptance
```

Raw exports remain private source evidence. Normalized conversations, chunks,
packets, extracted signals, deduped signals, conflict candidates, and review
bundles are not canonical memory. Dedupe does not resolve conflicts, and review
bundle generation does not accept candidates.

See [`CHATGPT_EXPORT_DISTILLER.md`](CHATGPT_EXPORT_DISTILLER.md).

## LLM-Probe Preflight, Comparison, and Audition Gate

```text
existing LLM-probe JSON or verified YAML output
    -> ZTH preflight importer                     [model-free]
    -> preserved source + capability manifest
    -> optional manifest comparison               [model-free]
    -> optional board/capability-card gate
    -> board audition, if allowed                 [endpoint-backed]
    -> human review
```

The importer does not run LLM-probe or call a model. The capability manifest is
aggregate preflight evidence. Comparison is manifest-only and cannot claim
per-model/per-probe status transitions.

Only the board/capability-card audition workflow consumes preflight manifests.
A preflight pass means that an audition may run; it does not promote, approve,
assign, rank, or production-certify a model. Optional OKF-style export remains
an export view, not an internal source of truth.

See [`LLM_PROBE_PREFLIGHT.md`](LLM_PROBE_PREFLIGHT.md).

## Board / Capability-Card Auditions

```text
existing endpoint + model configuration
    + suites + fixtures + scorer profiles
    + optional preflight manifest
    -> single-suite or board audition
    -> case evidence + capability cards
    -> optional board-card comparison
    -> human review
```

This workflow uses
[`local_harness/auditions/`](../local_harness/auditions/README.md). It produces
suite and board capability-card schemas and can apply optional direct or
board-level preflight gates.

Scores and comparisons are evidence about the tested configuration. They do
not assign production roles or establish production readiness.

## Small-Model Exploratory Harness

```text
small-model configuration
    -> optional GGUF download
    -> optional temporary llama.cpp/tmux start
    -> raw prompt responses from local/LAN endpoint
    -> mechanical scores + rollup + summary
    -> exploratory evidence for human review
    -> optional temporary server stop
```

This workflow uses
[`local_harness/model_auditions/`](../local_harness/model_auditions/README.md).
It can use an already-running endpoint without managing a local process.

Its files and schemas differ from board/capability-card outputs. It does not
currently consume preflight gates. Temporary server lifecycle actions gather
evidence only; they do not promote a model or create a production service.

Keep board and exploratory run evidence in separate output directories.

## Management-Team Role Workflow

```text
human-created and human-activated packet
    -> one supervised role execution
    -> role output + role-run evidence note
    -> human review
    -> human lifecycle decision
```

Role output is advisory unless the active packet explicitly grants authority.
An evidence note records authority already granted and grants no new authority.
Only an explicitly authorized Implementer may edit files, and only files in the
active packet allowlist.

Record role-run evidence inside the active packet by default. Use a separate
operator-selected evidence-note path only when the active packet explicitly
allows that path.

Managers may draft packet content but may not activate, approve, authorize, or
move lifecycle state. No role output moves a packet or accepts generated
evidence.

Lifecycle records remain plain files under human-controlled states such as
`job_queue/`, `active_jobs/`, `completed_jobs/`, `failed_jobs/`, and
`blocked_jobs/`.

See [`MANAGEMENT_TEAM_OVERVIEW.md`](MANAGEMENT_TEAM_OVERVIEW.md) and
[`SUPERVISED_MANAGEMENT_TEAM_USAGE_RULES.md`](../workflows/SUPERVISED_MANAGEMENT_TEAM_USAGE_RULES.md).

## External-Agent and Aider Integration

### External-Agent Adapter

```text
bounded task + source-of-truth context
    -> ZTH role packet                            [model-free]
    -> independently executed external agent
    -> contracted agent output
    -> ZTH comparison / coverage audit            [model-free]
    -> human-reviewed follow-up decision
```

ZTH supplies a workbench, not an agent scheduler. External agent output does
not authorize edits, commits, future packets, canonicalization, or lifecycle
movement.

See [`AGENT_ADAPTER.md`](AGENT_ADAPTER.md).

### Aider

```text
human-scoped editable files + read-only context
    -> local preflight and request artifacts
    -> supervised endpoint-backed Aider run
    -> diff + output + metrics + review artifacts
    -> human acceptance or rejection
```

Aider is an optional integration path for tightly scoped edits. It is not
approved for broad autonomous coding, automatic commits, or lifecycle
movement.

Supervised single-worker and Aider wrappers use
`outputs/agent_runs/<run-id>/` for one run's task/request inputs, captured
output, metrics, and review/acceptance files. The folder is evidence for human
review; creating or populating it does not accept the result.

See [`AIDER_FIRST_SUCCESS.md`](AIDER_FIRST_SUCCESS.md).

## Human Decision Points

Humans decide:

- whether a model-backed step should run;
- whether a role packet is active and what authority it grants;
- whether generated evidence is accepted, rejected, or reworked;
- whether a canonical update or repository edit receives a separate packet;
- whether a model receives any later assignment;
- whether temporary LAN exposure or local server lifecycle is appropriate;
- whether reviewed evidence is suitable for a durable report.

No passing smoke test, preflight status, capability card, score, comparison,
role output, evidence note, or successful endpoint call replaces these
decisions.

## Output and Reporting Boundary

Normal run outputs remain local evidence under `outputs/`, `.work/`, `/tmp`, or
another operator-selected directory. Reviewed snapshots may be sanitized and
copied under [`docs/reports/`](reports/README.md).

Reports preserve observations. They do not change acceptance state, move
lifecycle records, assign model roles, or establish production readiness.
