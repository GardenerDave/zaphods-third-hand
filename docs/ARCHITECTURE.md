# Architecture

## Overview

Zaphod's Third Hand separates repository ownership from model inference.

The head unit owns:

- Repository files.
- Source files.
- Audit trail.
- Job packets.
- Generated session summaries.
- Generated review patches.
- Role-run evidence.

The model worker only serves inference through an OpenAI-compatible endpoint.

For endpoint setup patterns, see `docs/OPENAI_COMPATIBLE_ENDPOINTS.md`.
For first-run onboarding, see `docs/FIRST_SUCCESS.md`.

## Head Unit

The head unit is the machine or environment where you run the repository. It is responsible for:

- Reading source files.
- Writing outputs.
- Preserving audit evidence.
- Running verification commands.
- Keeping lifecycle movement manual.

## Model Worker

The model worker receives prompts and returns text. It should not own repo files, job records, lifecycle state, source transcripts, or output folders.

## Job Lifecycle Folders

Recommended lifecycle folders:

```text
job_queue/
active_jobs/
completed_jobs/
failed_jobs/
blocked_jobs/
```

The folder names can be adapted, but the lifecycle principle should remain:

- Queue work first.
- Activate manually.
- Execute inside a narrow allowlist.
- Complete or fail with evidence.

## Context Distiller Pipeline

The context distiller is optional infrastructure included with the toolkit. Use it when source transcripts or logs need to become reviewable summaries; skip it when a project only needs the job lifecycle or role prompt layer.

The distiller pipeline:

1. Reads a source file.
2. Optionally splits it into chunks.
3. Summarizes each chunk.
4. Synthesizes a final session summary.
5. Generates a review patch.
6. Records run audit files.
7. Leaves canonical acceptance to a human-reviewed packet.

## Role Prompt Layer

The role prompt layer provides reusable role definitions for:

- Manager.
- Tech Lead.
- Implementer.
- Reviewer.
- Integrator.

Roles are advisory by default. Active packets define what a role may read, edit, verify, and hand off.

Unattended and batched role execution are not approved by default. They require separate design, validation, and human approval before use.

## Review And Acceptance Layer

Review patches and role outputs are not canonical automatically. They become durable project memory only after:

1. Human review.
2. Recorded acceptance/rework/rejection decision.
3. Separate packet for any canonical update.
