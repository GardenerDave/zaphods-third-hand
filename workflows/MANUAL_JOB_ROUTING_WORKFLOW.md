# Manual Job Routing Workflow

Routing happens before moving a packet from `job_queue/` to `active_jobs/`.

Use the job packet objective, file allowlist, off-limits list, verification commands, and stop conditions to decide who or what should handle the work.

## Routing Categories

### Human Review

Use for decisions, acceptance, ambiguity, priority, and risk. No files should be modified until approved.

### Codex / CLI Agent

Use for narrow repository edits with explicit file allowlists. The agent must follow the job packet scope and verification commands, and must stop if repo state contradicts the packet.

### Aider

Use for interactive surgical coding patches. Best when a human is watching diffs and can answer questions. Use no-auto-commits unless explicitly allowed.

### Context Distiller

Use for turning source conversations or logs into session summaries and review patches. Use compact plus chunked mode for long sources. Review patches are not canonical until accepted.

### Human Terminal

Use for commands requiring judgement, credentials, machine movement, or risky filesystem operations.

## Routing Checklist

- What is the objective?
- What files are allowed?
- What files are off limits?
- What verification proves completion?
- What should cause the agent to stop?
- Is this safe to batch?
- Does this require human approval before execution?

## Batching Rule

- Batch only jobs with narrow scope and independent verification.
- Do not batch jobs that touch the same fragile file unless ordered.
- Do not batch uncertain architecture decisions.
- Prefer many small commits over one large scaffold commit.

## Stop Conditions

- Repo state contradicts packet.
- Required file is missing.
- Tool asks to modify unrelated files.
- Verification command fails.
- Generated output appears malformed.
- Agent attempts broad rewrite or scaffold drift.

## Do Not

- Do not automate routing by default.
- Do not treat review patches as canonical automatically.
- Do not move repo, outputs, source transcripts, or job records to a model worker.
- Do not approve unattended or batched execution without a separate validated workflow.
