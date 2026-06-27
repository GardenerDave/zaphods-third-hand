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
outputs remain evidence until an authorized reviewer decides the next action.
Humans and agents may perform scoped workflow steps, but acting agents do not
approve their own outputs or move lifecycle state.

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

## Vogon Printer

- [`VOGON_PRINTER.md`](VOGON_PRINTER.md) — navigation for the model-free
  Agent Task Session, Tool Maker, Change Closeout, scaffold validation, repo
  health, and Git sync/cleanup advisor family.

## Tool Maker

- [`TOOL_MAKER.md`](TOOL_MAKER.md) — supervised workflow-to-lifecycle
  extraction process with a model-free scaffold builder.
- [`templates/TOOL_LIFECYCLE_TEMPLATE.md`](templates/TOOL_LIFECYCLE_TEMPLATE.md)
  — blank reusable lifecycle draft.
- [`prompts/TOOL_MAKER_PROMPT.md`](../prompts/TOOL_MAKER_PROMPT.md) — compact
  extraction contract for supervised agents.

## Change Closeout

- [`CHANGE_CLOSEOUT.md`](CHANGE_CLOSEOUT.md) — supervised final review process
  with a model-free scaffold builder for behavior, validation, documentation,
  safety boundaries, and lifecycle knowledge.
- [`templates/CHANGE_CLOSEOUT_TEMPLATE.md`](templates/CHANGE_CLOSEOUT_TEMPLATE.md)
  — blank human-copyable closeout report.
- [`prompts/CHANGE_CLOSEOUT_PROMPT.md`](../prompts/CHANGE_CLOSEOUT_PROMPT.md) —
  compact supervised closeout contract.

## LLM-Probe Preflight and Comparison

- [`LLM_PROBE_PRODUCER_CONTRACT.md`](LLM_PROBE_PRODUCER_CONTRACT.md) —
  endpoint-backed ZTH smoke-probe producer, verified-YAML contract, local
  evidence layout, privacy rules, and producer-to-importer workflow.
- [`LLM_PROBE_PREFLIGHT.md`](LLM_PROBE_PREFLIGHT.md) — model-free import,
  source preservation, capability manifests, regression comparison, optional
  OKF-style export, and the optional board-audition gate boundary.
- [`PREFLIGHT_AUDITION_PLAN.md`](PREFLIGHT_AUDITION_PLAN.md) — model-free,
  read-only-by-default planning from raw LLM-probe evidence or an existing
  capability manifest to a gated suite or board audition command sequence.

## Model Auditions

- [`local_harness/auditions/README.md`](../local_harness/auditions/README.md) —
  endpoint-backed suites, fixtures, scorer profiles, boards, capability cards,
  comparisons, and optional preflight gates.
- [`MODEL_AUDITION_AUTHORING.md`](MODEL_AUDITION_AUTHORING.md) — maker/reference
  guide for custom suites, fixture JSONL, prompt templates, scorer profiles,
  boards, dry runs, and deterministic failure modes.

## Small-Model Exploratory Harness

- [`local_harness/model_auditions/README.md`](../local_harness/model_auditions/README.md)
  — GGUF download, optional temporary llama.cpp/tmux lifecycle, existing
  local/LAN endpoints, raw responses, and mechanical exploratory scoring.
- [`LOGIC_PROBES.md`](LOGIC_PROBES.md) — ZTH-specific logic and safety probes,
  model-free fixture validation/scoring, and optional endpoint-backed probe
  runs.

The exploratory small-model and logic-probe harnesses have outputs different
from the board/capability-card workflow. Neither currently consumes preflight
gates.

## Failure-Curriculum Training

- [`FAILURE_CURRICULUM_TRAINING.md`](FAILURE_CURRICULUM_TRAINING.md) —
  practical guide for supervised failure-curriculum adapter-training evidence,
  base-vs-adapter evaluation, and current safety boundaries.
- [`reports/failure_training/`](reports/failure_training/) — local-first smoke
  summaries and measured adapter behavior reports.

## Experiments

- [`experiments/LARQL_AFFORDANCE_PATCH_PROBE_V0.md`](experiments/LARQL_AFFORDANCE_PATCH_PROBE_V0.md)
  — experimental, model-free scaffold for classifying machine-specific failures
  into host-profile, LARQL patch, LoRA training, stacked, or review-only repair
  candidates. No model editing or training is performed.
- [`experiments/AFFORDANCE_DOGFOOD_REPORT_V0.md`](experiments/AFFORDANCE_DOGFOOD_REPORT_V0.md)
  — experimental, model-free report scaffold for reviewing one generated
  affordance candidate while holding promotion pending probes.
- [`experiments/AFFORDANCE_CANDIDATE_PROBE_RUNNER_V0.md`](experiments/AFFORDANCE_CANDIDATE_PROBE_RUNNER_V0.md)
  — experimental runner that packages one affordance candidate’s probe prompts
  and defaults to dry-run artifacts before any explicit endpoint-backed probe.
- [`experiments/AFFORDANCE_EXPERIMENT_ELIGIBILITY_V0.md`](experiments/AFFORDANCE_EXPERIMENT_ELIGIBILITY_V0.md)
  — model-free eligibility/reporting gate for deciding whether a probe-passing
  affordance candidate has enough evidence for a future experiment proposal.
- [`experiments/AFFORDANCE_EXPERIMENT_PROPOSAL_V0.md`](experiments/AFFORDANCE_EXPERIMENT_PROPOSAL_V0.md)
  — model-free proposal scaffold for turning eligible affordance evidence into
  a reviewable experiment proposal while holding promotion and implementation.
- [`experiments/AFFORDANCE_EXPERIMENT_DECISION_V0.md`](experiments/AFFORDANCE_EXPERIMENT_DECISION_V0.md)
  — model-free decision record for approving plan drafting, holding revision,
  or rejecting an affordance experiment proposal without executing it.
- [`experiments/AFFORDANCE_EXPERIMENT_PLAN_V0.md`](experiments/AFFORDANCE_EXPERIMENT_PLAN_V0.md)
  — model-free bounded plan scaffold for preparing execution-approval review
  material without running LARQL, LoRA, or comparison lanes.
- [`experiments/AFFORDANCE_EXPERIMENT_EXECUTION_APPROVAL_V0.md`](experiments/AFFORDANCE_EXPERIMENT_EXECUTION_APPROVAL_V0.md)
  — model-free approval record for one bounded affordance experiment lane;
  v0 can approve only the baseline prompt-context control lane.
- [`experiments/AFFORDANCE_BASELINE_EXECUTION_PACKET_V0.md`](experiments/AFFORDANCE_BASELINE_EXECUTION_PACKET_V0.md)
  — model-free packet scaffold for a later baseline prompt-context runner;
  it embeds a fixed prompt suite but does not call a model.

## Management-Team Workflows

The packet, lifecycle, routing, and evidence-note formats are model-free.
Actual role execution depends on the supervised executor chosen by the
operator and the authority recorded in the active packet.

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

- [`AGENT_TASK_SESSION.md`](AGENT_TASK_SESSION.md) — model-free scoped work
  packets, validation, JSON handoff, and optional closeout guidance for
  supervised Codex or external-agent tasks.
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
