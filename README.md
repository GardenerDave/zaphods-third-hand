# Zaphod's Third Hand

Zaphod's Third Hand, or ZTH, is a plain-file, human-supervised workflow kit for
using AI helpers without giving them direct control of your repository.

It helps turn chats, logs, model outputs, and role-work packets into reviewable
files that a human can inspect, compare, accept, reject, or refine.

## In Plain English

ZTH helps you use AI without handing it the steering wheel.

Instead of asking a model to "just do the project," ZTH breaks AI-assisted work
into small, inspectable steps:

1. Prepare source material.
2. Run a scoped tool or model.
3. Save the output as files.
4. Review the evidence.
5. Decide what, if anything, should be accepted.

The project is designed for people who want AI help, but still want a visible
audit trail and human control.

## What You Can Do Today

- Run a model-free smoke test to confirm the repo works.
- Distill transcripts or logs into reviewable summaries and patch files.
- Audition local or remote OpenAI-compatible models against repeatable test boards.
- Compare model capability cards without assigning production roles.
- Prepare supervised role packets for external agent or panel workflows.

## What It Is

- A local-first toolkit for context distillation and supervised AI workflows.
- A set of scripts, prompts, fixtures, scorer profiles, and workflow docs.
- A way to preserve evidence from AI-assisted work.
- A human-controlled process for accepting, rejecting, or reworking outputs.

## What It Is Not

- Not unattended automation.
- Not automatic lifecycle movement.
- Not automatic canonicalization of generated context.
- Not a hosted model service.
- Not a production model router.
- Not a replacement for human review.

## Fastest First Success

| User type | Usable now? |
|---|---|
| Has Python/Bash only | Partial: metrics smoke test |
| Has local OpenAI-compatible endpoint | Yes: Context Distiller and model auditions |
| Wants autonomous agent | No |
| Wants polished app | No |
| Wants supervised file workflow | Yes |

Start here:

1. Read [`docs/FIRST_SUCCESS.md`](docs/FIRST_SUCCESS.md).
2. Run the model-free smoke test:

        python3 local_harness/report_distiller_metrics.py --runs-dir examples --limit 3

3. If you have an OpenAI-compatible endpoint, continue with the optional endpoint
   smoke test and toy Context Distiller run in [`docs/FIRST_SUCCESS.md`](docs/FIRST_SUCCESS.md).

If you are new to this repo, begin with Context Distiller before using the
management-team or external-agent layers.

For the full documentation map, see [`docs/README.md`](docs/README.md).

## How ChatGPT Fits

You can use ChatGPT as an operator assistant while working with ZTH.

Useful things to paste into ChatGPT:

- Terminal output.
- Capability cards.
- Comparison reports.
- Failure modes.
- Small docs or prompt files.
- Git status output before committing.

Good questions to ask:

- What failed here?
- Is this a model problem, prompt problem, scorer problem, or runtime problem?
- What should I inspect before deleting `.work`?
- Should this result be committed as a durable report or treated as disposable run evidence?
- What is the smallest safe next commit?

ZTH works best when ChatGPT helps interpret evidence, but a human still decides
what gets committed.

## OpenAI-Compatible Endpoint Requirement

Core ZTH workflows expect an existing OpenAI-compatible endpoint for
model-backed runs. They connect to an endpoint supplied by the operator and do
not manage its production lifecycle.

The optional small-model audition harness can download candidate GGUFs and
start or stop temporary local llama.cpp servers for exploratory evaluation.
That lifecycle support is evidence-gathering tooling, not a hosted service,
production model-server manager, promotion mechanism, or production-readiness
claim.

Supported patterns are documented in:

- [`docs/OPENAI_COMPATIBLE_ENDPOINTS.md`](docs/OPENAI_COMPATIBLE_ENDPOINTS.md)
- [`local_harness/model_auditions/README.md`](local_harness/model_auditions/README.md) for optional exploratory GGUF and temporary llama.cpp lifecycle support

Common local options include llama.cpp server and LM Studio local server.
Generic OpenAI-compatible APIs also work when they expose compatible
chat-completions behavior.

## Product Layers

### Layer 1: Context Distiller

Use this first.

Purpose:

- Distill transcripts or logs into a session summary and review patch.
- Record run telemetry and audit artifacts.
- Keep outputs reviewable before acceptance.

Start with:

- [`docs/FIRST_SUCCESS.md`](docs/FIRST_SUCCESS.md)
- [`docs/CONTEXT_DISTILLER_WORKFLOW.md`](docs/CONTEXT_DISTILLER_WORKFLOW.md)

### Layer 2: Model Auditions

Use this when you want to compare models with the same tests.

Purpose:

- Run repeatable probes against local or remote OpenAI-compatible models.
- Use replaceable prompts, fixtures, scorer profiles, suites, and boards.
- Produce capability cards.
- Compare models without assigning production roles.
- Preserve selected results as durable report snapshots.

Start with:

- [`local_harness/auditions/README.md`](local_harness/auditions/README.md)
- [`local_harness/model_auditions/README.md`](local_harness/model_auditions/README.md) for optional small-model download and temporary local-server support
- [`docs/reports/model_auditions/qwen_local_models_2026-06-18/comparison.md`](docs/reports/model_auditions/qwen_local_models_2026-06-18/comparison.md)

### Layer 3: Supervised Management-Team Workflow

Use this after Layer 1 is comfortable, or when you already have established
packet-based work.

Purpose:

- Route scoped work through role prompts under explicit human supervision.
- Preserve packet boundaries, allowlists, stop conditions, and manual lifecycle control.

Start with:

- [`docs/MANAGEMENT_TEAM_OVERVIEW.md`](docs/MANAGEMENT_TEAM_OVERVIEW.md)
- [`workflows/SUPERVISED_MANAGEMENT_TEAM_USAGE_RULES.md`](workflows/SUPERVISED_MANAGEMENT_TEAM_USAGE_RULES.md)
- [`workflows/MANUAL_JOB_ROUTING_WORKFLOW.md`](workflows/MANUAL_JOB_ROUTING_WORKFLOW.md)

### Advanced: External Agent Adapter

Use this only after the Context Distiller path is clear.

Purpose:

- Prepare role-specific packets for external multi-agent or panel systems.
- Keep agents independent until synthesis and comparison.
- Surface contract drift, agreement maps, disagreements, and coverage blind spots.
- Compare completed agent outputs without turning ZTH into an orchestrator.

Start with:

- [`docs/AGENT_ADAPTER.md`](docs/AGENT_ADAPTER.md)
- [`docs/prompts/ROLE_PACKET_TEMPLATE.md`](docs/prompts/ROLE_PACKET_TEMPLATE.md)
- [`docs/prompts/AGENT_OUTPUT_CONTRACT.md`](docs/prompts/AGENT_OUTPUT_CONTRACT.md)
- [`docs/prompts/SYNTHESIS_OUTPUT_TEMPLATE.md`](docs/prompts/SYNTHESIS_OUTPUT_TEMPLATE.md)
- [`docs/prompts/AGREEMENT_MAP_TEMPLATE.md`](docs/prompts/AGREEMENT_MAP_TEMPLATE.md)

## Safety Model

Default safety posture:

- Human-supervised operation only.
- No unattended execution.
- No batched execution by default.
- No automatic lifecycle movement.
- No automatic review-patch acceptance.
- No automatic canonical context updates.
- No production role assignment from audition scores alone.

All generated files remain review material until a human accepts follow-up work.

## Setup and Config

Copy config, edit it first, then load it:

    cp config.example.env config.env
    # Edit config.env first: set real ZTH_BASE_URL and ZTH_MODEL for your endpoint.
    set -a
    source config.env
    set +a

`ZTH_BASE_URL` and `ZTH_MODEL` must match your actual running endpoint and
accepted model id.

If you source placeholder values unchanged, endpoint smoke tests will fail.

Required for model-backed runs:

- `ZTH_BASE_URL`
- `ZTH_MODEL`

Optional:

- `ZTH_API_KEY`
- Distiller budget, time, and profile variables in [`config.example.env`](config.example.env)

## Dependency and Installation Notes

For core smoke tests and local harness usage, this repo uses Python standard
library modules and Bash scripts.

- No mandatory third-party Python packages are required for the model-free metrics smoke test.
- If your endpoint requires auth, provide credentials through environment variables only.

## Generated Outputs

Normal distiller runs write to:

- `outputs/sessions/`
- `outputs/review_patches/`
- `outputs/run_records/`

Model audition runs usually write to:

- `.work/model_auditions/`
- `.work/model_audition_comparisons/`

`.work` is local run evidence. Inspect useful failures before deleting it.
Commit durable summaries under `docs/reports/` when a result is worth preserving.

## Reports

Committed reports are evidence snapshots. They document what was run and what was
observed at a point in time.

Current model audition report:

- [`docs/reports/model_auditions/qwen_local_models_2026-06-18/comparison.md`](docs/reports/model_auditions/qwen_local_models_2026-06-18/comparison.md)

Reports are useful for comparison and regression tracking. They are not
production role assignments.

## Release and Repo Health

Before sharing or tagging:

- [`docs/REPO_HEALTH.md`](docs/REPO_HEALTH.md)
- [`docs/ALPHA_READINESS_CHECKLIST.md`](docs/ALPHA_READINESS_CHECKLIST.md)
- [`docs/SHARING_CHECKLIST.md`](docs/SHARING_CHECKLIST.md)

Advanced supervised Aider runs are documented in [`docs/AIDER_FIRST_SUCCESS.md`](docs/AIDER_FIRST_SUCCESS.md).
Complete the Context Distiller first-success path before using that workflow.

## License

Source-available for noncommercial use under PolyForm Noncommercial License 1.0.0.

Commercial or for-profit use requires explicit written permission.

See:

- [`LICENSE.md`](LICENSE.md)
- [`COMMERCIAL_USE.md`](COMMERCIAL_USE.md)

## Contributions

External contributions are not accepted yet.
