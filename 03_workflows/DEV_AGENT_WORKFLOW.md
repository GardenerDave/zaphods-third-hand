# Development Agent Workflow

Author: [REDACTED]

## Operating Mode

Use context files first, then source files, then user clarification only when needed.

## Expected Loop

1. Read the relevant ICM context files.
2. Inspect current source code or artifact state.
3. Make the smallest coherent change set.
4. Preserve version traceability.
5. Update bug history and release notes when behavior changes.
6. Produce clean deliverables when asked.
7. Suggest the next move.

## End-Of-Work Next Move Function

Every completed ICM or development workflow run should end by suggesting the next useful move, even when the immediate task is complete.

Use this function after verification, cleanup, documentation updates, and commits:

```text
suggest_next_move(current_state, completed_work, verification_result, known_risks) -> next_move
```

The suggested next move should:

- Be a single concrete action, not a broad menu.
- Prefer the next step that compounds the work just completed.
- Mention why it is next when the reason is not obvious.
- Distinguish implementation work from manual/user testing.
- Avoid reopening completed work unless verification or diagnostics revealed a real concern.

Final responses should include the suggestion as a short `Suggested next move:` line after the status/commit summary.

## Codex Session Usage Note

`/status` is a Codex-specific session command, not a general workflow requirement. At the end of completed Codex-managed work, include a short reminder to check Codex usage with `/status`. Do not require local or offloaded agents to run or report Codex slash commands; they should report only their own relevant runtime or resource limits.

## Deliverable Format

- [REDACTED_AUTHOR] generally prefers integrated runnable project versions for app handoffs.
- Do not provide unwired module packs when the request is for a testable app version.
- Keep package roots short and version-scoped, such as `InternalCodename_v1.20.0/`.
- Written test notes can be enough to proceed when they clearly identify the bug class.

## Verification And Cleanup

- After source changes, use `npm run agent:verify` when working in the app package.
- `npm run agent:verify` delegates through `npm run check` to `npm run build`.
- The verification build may regenerate tracked `out/` files and create new hashed renderer bundles.
- Accepted cleanup pattern: run verification, record pass/fail, restore tracked generated `out/` files, remove new generated bundles, then do not rerun verification during cleanup.
- Commit only intended source and documentation files unless [REDACTED_AUTHOR] explicitly asks to include generated artifacts.
- After verification and artifact cleanup, make a local commit for the coherent change set unless [REDACTED_AUTHOR] explicitly asks to hold it uncommitted.
- Local commits are normal checkpoints; pushing to GitHub is a separate explicit action.
- Do not commit `node_modules`.
- Do not run `npm install` unless dependencies are missing, package files changed, or an error specifically requires it.

## Staged Workflow Pattern

For repeatable work, use stage-specific folders and markdown context files rather than one large prompt. Typical stages are issue intake, code inspection, patch plan, implementation, verification, and release notes. Each stage should define its inputs, outputs, constraints, and review checkpoint.

For local-model delegation, use `ICM/03_workflows/LOCAL_AGENT_ORCHESTRATION_WORKFLOW.md`. Local agents should produce draft reports or candidate outputs first; Codex/Nav or [REDACTED_AUTHOR] should review before canonical docs, app source, release records, or commits change.

## Important Project Preferences

- Minimize copy/paste friction.
- Maintain a dev-side error and bug tracking mindset.
- Keep the user focused on product behavior rather than implementation bookkeeping.
- Prefer Codex for coordination, context stewardship, review, and high-risk implementation decisions; offload low-risk, easily verified subtasks to local models when that agent setup is available.
- Preserve deterministic planning behavior until AI behavior is intentionally introduced.
- Be explicit when a source link, export, or snapshot is inaccessible.
- Track environment caveats such as native dependency/network build limits and VM timezone when they affect verification.
