# ZTH Documentation

Start with [`README.md`](../README.md) for the project overview.

This index groups the public documentation by operator task.

## Runtime Labels

- **Model-free:** no model endpoint is required.
- **Endpoint-backed:** the live operation requires an existing
  OpenAI-compatible endpoint.
- **Optional local lifecycle:** exploratory tooling may download a GGUF and
  start or stop a temporary local llama.cpp server.

These labels describe runtime dependencies, not authority. All generated
outputs remain evidence until a human reviews the next action.

## First Success / Quickstart

- [`FIRST_SUCCESS.md`](FIRST_SUCCESS.md) — shortest model-free smoke test and
  optional first endpoint-backed run.
- [`QUICKSTART.md`](../QUICKSTART.md) — broader operator walkthrough.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — current workflow and evidence map.
- [`ROADMAP.md`](ROADMAP.md) — implemented, planned, and explicitly deferred
  work.

## Endpoint Setup

- [`OPENAI_COMPATIBLE_ENDPOINTS.md`](OPENAI_COMPATIBLE_ENDPOINTS.md) —
  endpoint assumptions, local/LAN examples, security guidance, and the
  production boundary.
- [`local_harness/README.md`](../local_harness/README.md) — endpoint-backed
  local helper scripts and their generated evidence.

## Context Distiller

- [`CONTEXT_DISTILLER_WORKFLOW.md`](CONTEXT_DISTILLER_WORKFLOW.md) —
  endpoint-backed compact/chunked distillation, review patches, metrics, and
  human acceptance.
- [`OPERATOR_NOTES.md`](OPERATOR_NOTES.md) — operational findings and current
  local-harness caveats.

## ChatGPT Export Ingestion

- [`CHATGPT_EXPORT_DISTILLER.md`](CHATGPT_EXPORT_DISTILLER.md) — model-free
  ingestion, normalization, chunking, packet generation, validation, dedupe,
  and review-bundle steps, plus optional supervised endpoint-backed
  extraction.

## LLM-Probe Preflight and Comparison

- [`LLM_PROBE_PREFLIGHT.md`](LLM_PROBE_PREFLIGHT.md) — model-free import,
  source preservation, capability manifests, regression comparison, optional
  OKF-style export, and the optional board-audition gate boundary.

## Model Auditions

- [`local_harness/auditions/README.md`](../local_harness/auditions/README.md) —
  endpoint-backed suites, fixtures, scorer profiles, boards, capability cards,
  comparisons, and optional preflight gates.

## Small-Model Exploratory Harness

- [`local_harness/model_auditions/README.md`](../local_harness/model_auditions/README.md)
  — GGUF download, optional temporary llama.cpp/tmux lifecycle, existing
  local/LAN endpoints, raw responses, and mechanical exploratory scoring.

This harness has different outputs from the board/capability-card workflow and
does not currently consume preflight gates.

## Management-Team Workflows

The packet, lifecycle, routing, and evidence-note formats are model-free.
Actual role execution depends on the supervised executor chosen by the human.

- [`MANAGEMENT_TEAM_OVERVIEW.md`](MANAGEMENT_TEAM_OVERVIEW.md) — canonical role
  authority model.
- [`JOB_LIFECYCLE.md`](JOB_LIFECYCLE.md) — manual packet lifecycle.
- [`SUPERVISED_MANAGEMENT_TEAM_USAGE_RULES.md`](../workflows/SUPERVISED_MANAGEMENT_TEAM_USAGE_RULES.md)
  — approved supervised usage and prohibited automation.
- [`MANUAL_JOB_ROUTING_WORKFLOW.md`](../workflows/MANUAL_JOB_ROUTING_WORKFLOW.md)
  — human routing categories and stop conditions.
- [`SUPERVISED_ROLE_RUN_EVIDENCE_NOTE_FORMAT.md`](../workflows/SUPERVISED_ROLE_RUN_EVIDENCE_NOTE_FORMAT.md)
  — evidence-note contract; the note records authority and grants none.
- [`MANAGEMENT_TEAM_STATUS_INDEX.md`](../workflows/MANAGEMENT_TEAM_STATUS_INDEX.md)
  — current management-team workflow status.

## External-Agent / Aider Adapter

- [`AGENT_ADAPTER.md`](AGENT_ADAPTER.md) — model-free packet preparation,
  output comparison, and coverage auditing around externally executed agents.
- [`AIDER_FIRST_SUCCESS.md`](AIDER_FIRST_SUCCESS.md) — optional,
  endpoint-backed, tightly scoped supervised editing with review artifacts.
- [`docs/prompts/`](prompts/) — external-agent packet, output, synthesis, and
  agreement-map contracts.

## Reports

Report review and sanitization are model-free.

- [`reports/README.md`](reports/README.md) — durable evidence rules and report
  hygiene.
- [`reports/REPORT_TEMPLATE.md`](reports/REPORT_TEMPLATE.md) — reusable
  evidence-report structure and sanitization checklist.
- [`reports/model_auditions/README.md`](reports/model_auditions/README.md) —
  board/capability-card and exploratory small-model report guidance.

Reports preserve reviewed evidence. They do not promote models, accept
generated context, authorize lifecycle movement, or certify production
readiness.

## Release / Sanitization Checks

These checks are model-free.

- [`REPO_HEALTH.md`](REPO_HEALTH.md) — lightweight repository checks.
- [`ALPHA_READINESS_CHECKLIST.md`](ALPHA_READINESS_CHECKLIST.md) — alpha
  release-readiness review.
- [`SHARING_CHECKLIST.md`](SHARING_CHECKLIST.md) — pre-share checklist.
- [`SANITIZATION_NOTES.md`](SANITIZATION_NOTES.md) — tracked-file-safe
  sanitization policy and commands.
