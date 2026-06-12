# Zaphod's Third Hand

Zaphod's Third Hand is a file-based, supervised workflow kit for turning messy source material into reviewable context and running scoped AI role workflows without giving models direct control of your repository.

## What It Is

- A local-first toolkit for context distillation and supervised role-based execution.
- A set of scripts, prompts, and workflow docs that keep generated outputs inspectable.
- A human-controlled process for accepting, rejecting, or reworking outputs.

## What It Is Not

- Not unattended automation.
- Not automatic lifecycle movement.
- Not automatic canonicalization of generated context.
- Not a hosted model service.
- Not a replacement for human review.

## Fastest First Success

| User type | Usable now? |
|---|---|
| Has Python/Bash only | Partial: metrics smoke test |
| Has local OpenAI-compatible endpoint | Yes: Context Distiller |
| Wants autonomous agent | No |
| Wants polished app | No |
| Wants supervised file workflow | Yes |

Start here:

1. [`docs/FIRST_SUCCESS.md`](docs/FIRST_SUCCESS.md) for the smallest successful run.
2. Model-free smoke test:

```bash
python3 local_harness/report_distiller_metrics.py --runs-dir examples --limit 3
```

3. Optional endpoint smoke test and toy distiller run from [`docs/FIRST_SUCCESS.md`](docs/FIRST_SUCCESS.md).

If you are new to this repo, begin with Context Distiller before the management-team layer.

## OpenAI-Compatible Endpoint Requirement

This repo assumes an OpenAI-compatible endpoint for model-backed runs and does not install or manage a model server.

Supported patterns are documented in:

- [`docs/OPENAI_COMPATIBLE_ENDPOINTS.md`](docs/OPENAI_COMPATIBLE_ENDPOINTS.md)

Common local options include llama.cpp server and LM Studio local server. Generic OpenAI-compatible APIs also work when they expose compatible chat-completions behavior.

## Two Product Layers

### Layer 1: Context Distiller

Use this first.

Purpose:

- Distill transcripts/logs into a session summary and review patch.
- Record run telemetry and audit artifacts.
- Keep outputs reviewable before acceptance.

Start with:

- [`docs/FIRST_SUCCESS.md`](docs/FIRST_SUCCESS.md)
- [`docs/CONTEXT_DISTILLER_WORKFLOW.md`](docs/CONTEXT_DISTILLER_WORKFLOW.md)

### Layer 2: Supervised Management-Team Workflow

Use this after Layer 1 is comfortable, or when you already have established packet-based work.

Purpose:

- Route scoped work through role prompts under explicit human supervision.
- Preserve packet boundaries, allowlists, stop conditions, and manual lifecycle control.

Start with:

- [`docs/MANAGEMENT_TEAM_OVERVIEW.md`](docs/MANAGEMENT_TEAM_OVERVIEW.md)
- [`workflows/SUPERVISED_MANAGEMENT_TEAM_USAGE_RULES.md`](workflows/SUPERVISED_MANAGEMENT_TEAM_USAGE_RULES.md)
- [`workflows/MANUAL_JOB_ROUTING_WORKFLOW.md`](workflows/MANUAL_JOB_ROUTING_WORKFLOW.md)

## Safety Model

Default safety posture:

- Human-supervised operation only.
- No unattended execution.
- No batched execution by default.
- No automatic lifecycle movement.
- No automatic review-patch acceptance.
- No automatic canonical context updates.

All generated files remain review material until a human accepts follow-up work.

## Setup and Config

Copy config, edit it first, then load it:

```bash
cp config.example.env config.env
# Edit config.env first: set real ZTH_BASE_URL and ZTH_MODEL for your endpoint.
set -a
source config.env
set +a
```

`ZTH_BASE_URL` and `ZTH_MODEL` must match your actual running endpoint and accepted model id.

If you source placeholder values unchanged, endpoint smoke tests will fail.

Required for model-backed runs:

- `ZTH_BASE_URL`
- `ZTH_MODEL`

Optional:

- `ZTH_API_KEY`
- Distiller budget/time/profile variables in [`config.example.env`](config.example.env)

## Dependency and Installation Notes

For core smoke tests and local harness usage, this repo uses Python standard library modules and Bash scripts.

- No mandatory third-party Python packages are required for the model-free metrics smoke test.
- If your endpoint requires auth, provide credentials through environment variables only.

## Generated Outputs

Normal distiller runs write to:

- `outputs/sessions/`
- `outputs/review_patches/`
- `outputs/run_records/`

These outputs are intentionally file-based and reviewable.

## Release and Repo Health

Before sharing or tagging:

- [`docs/REPO_HEALTH.md`](docs/REPO_HEALTH.md)
- [`docs/ALPHA_READINESS_CHECKLIST.md`](docs/ALPHA_READINESS_CHECKLIST.md)
- [`docs/SHARING_CHECKLIST.md`](docs/SHARING_CHECKLIST.md)

## License

Source-available for noncommercial use under PolyForm Noncommercial License 1.0.0.

Commercial or for-profit use requires explicit written permission.

See:

- [`LICENSE.md`](LICENSE.md)
- [`COMMERCIAL_USE.md`](COMMERCIAL_USE.md)

## Contributions

External contributions are not accepted yet.