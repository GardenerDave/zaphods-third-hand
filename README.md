# Zaphod's Third Hand

Zaphod's Third Hand is a reusable, file-based workflow kit for turning messy source material into durable project context and for coordinating a supervised management-team layer of AI roles.

It is designed for local-first work where the repository owner keeps control of files, source material, generated outputs, review notes, and lifecycle decisions.

## Who It Is For

This toolkit is for developers, researchers, maintainers, and project owners who want AI assistance without giving the model direct control over a repository. It is especially useful when you have long transcripts, logs, or planning notes that need to become reviewable project context.

## What Problem It Solves

Long projects accumulate transcripts, logs, decisions, partial plans, stale assumptions, and generated notes. Zaphod's Third Hand gives you a disciplined way to:

- Distill source transcripts or logs into structured context summaries.
- Generate review patches that humans can accept, reject, supersede, or rework.
- Route narrow work through job packets instead of ad hoc prompting.
- Use management-team role prompts under human supervision.
- Keep audit evidence for role runs and context updates.

## What It Does Not Do Yet

- It does not approve unattended execution.
- It does not approve batched execution.
- It does not automate lifecycle movement.
- It does not automatically canonicalize generated context.
- It does not replace human review.
- It does not decide what private source material is safe to share.

## Why The Workflow Is File-Based

The workflow is file-based because files are inspectable, diffable, and reviewable. Job packets, session summaries, review patches, and role-run evidence are plain Markdown. This keeps the human in control and makes it clear what changed, why it changed, and what still needs review.

## High-Level Architecture

Zaphod's Third Hand has three main parts:

- Head unit: the local repo and scripts that own files, outputs, audit records, and lifecycle state.
- Model worker: a replaceable OpenAI-compatible endpoint that returns text but does not own repo state.
- File workflow: job packets, generated outputs, review patches, and evidence notes that humans can inspect before accepting anything.

The context distiller is included infrastructure. You can use the role prompts and job lifecycle without running the distiller, or use the distiller when you need to compress transcripts and logs into reviewable summaries.

## How The Context Distiller Fits In

The context distiller reads a source transcript or log and produces:

- A session summary in `outputs/sessions/`.
- A context review patch in `outputs/review_patches/`.
- Run audit files in `outputs/run_records/`.

Generated review patches are not canonical until a human accepts them and a separate job packet applies the accepted update.

## How The Management-Team Roles Fit In

The management-team layer contains five role prompts:

- Manager: scopes and decomposes work.
- Tech Lead: refines scope, risks, dependencies, and verification.
- Implementer: makes narrow allowlisted edits when explicitly authorized.
- Reviewer: reviews evidence, diffs, outputs, and acceptance criteria.
- Integrator: assesses handoff, readiness, and narrow integration paths.

These roles are advisory by default. They do not move lifecycle packets, create packets, trigger agents, approve execution, or edit files unless an active job packet explicitly permits the action.

## Safety Model

Default safety posture:

- Supervised-only role usage.
- No unattended execution.
- No batched execution.
- No routing automation.
- No lifecycle automation.
- No automatic canonical context updates.
- No automatic review-patch acceptance.
- Human approval before role use, activation, file edits, lifecycle movement, and follow-up packet creation.

## How To Use This Tool

1. Configure an OpenAI-compatible model endpoint.
2. Add a source transcript or log that is safe for your local environment.
3. Run the context distiller in compact plus chunked mode for long sources.
4. Review the generated session and review patch.
5. Create a job packet for any accepted next step.
6. Activate the packet manually after human review.
7. Use role prompts only under human supervision.
8. Record acceptance, rework, or rejection decisions as evidence.

For a step-by-step beginner path, start with `QUICKSTART.md`.

If you only want to validate setup first, run the endpoint smoke check in `QUICKSTART.md` Step 1.5 before any distiller run.

Before tagging or sharing an early release, review `docs/ALPHA_READINESS_CHECKLIST.md`.

## Try Metrics Without A Model

You can inspect a sample telemetry report before configuring a model endpoint:

```bash
python3 local_harness/report_distiller_metrics.py --runs-dir examples --limit 3
```

This reads sanitized example data under `examples/sample_metrics_run/`. Real distiller runs write their metrics under `outputs/run_records/`.

Use `--json` if you want advisory profile guidance fields (`recommended_profile`, `recommended_settings`, `recommendation_reason`) for read-only tuning support.

## Basic Setup Assumptions

- You have Python 3 available.
- You have Bash available.
- You have access to an OpenAI-compatible chat-completions endpoint.
- You run commands from a repository that can store this package.
- You keep private source material out of public commits unless explicitly reviewed.

Configure the endpoint:

```bash
cp config.example.env config.env
# Edit config.env, then load it:
set -a
source config.env
set +a
```

Or export values directly:

```bash
export ZTH_BASE_URL="http://<LLAMA_CPP_BASE_URL>/v1"
export ZTH_MODEL="<MODEL_NAME>"
```

Run a distillation:

```bash
cd <REPO_ROOT>/zaphods-third-hand
./scripts/run_context_distiller_head.sh <SOURCE_ID> <SOURCE_FILE> <SHORT_TITLE> --compact --chunked
```

Expected generated paths:

```text
outputs/sessions/
outputs/review_patches/
outputs/run_records/
```

## Important Warning

Generated review patches are not canonical. A human must review and accept them before any canonical update is made, and that update should happen through a separate job packet with an explicit file allowlist.

## License

Zaphod's Third Hand is source-available for noncommercial use under the PolyForm Noncommercial License 1.0.0.

Commercial or for-profit use requires explicit written permission from the copyright holder. This is not OSI open source because commercial use is restricted.

Read:

- `LICENSE.md`
- `COMMERCIAL_USE.md`

## Contributions

External contributions are not accepted yet.

## Attribution Policy

When using AI assistance for commits or release notes in this repository, use wording such as "assisted by AI".

Do not add AI co-author commit trailers.
