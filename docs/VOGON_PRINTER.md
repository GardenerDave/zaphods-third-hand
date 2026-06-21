# Vogon Printer

Vogon Printer is the informal operator-facing name for ZTH's model-free
paperwork and verification family. These tools turn scope, evidence, and
review requirements into plain files, then check those files or the repository
without taking authority from the human operator.

It is a family name, not a new executable, workflow engine, agent runtime, or
implementation layer. The existing script names and output contracts remain
canonical.

## Family Members

| Tool | Role | Primary output or result |
|---|---|---|
| [Agent Task Session](AGENT_TASK_SESSION.md) | Prints a scoped work packet for Codex or another supervised agent. | `.work/agent_tasks/<task-id>/` |
| [Tool Maker](TOOL_MAKER.md) | Prints a lifecycle-draft scaffold from bounded workflow evidence. | A draft tool-lifecycle Markdown file |
| [Change Closeout](CHANGE_CLOSEOUT.md) | Prints a final-review scaffold for a completed or apparently completed change. | A draft closeout Markdown file |
| [`validate_scaffold.py`](../local_harness/validate_scaffold.py) | Checks Tool Maker and Change Closeout contract shape and metadata consistency. | `VALID` or a clear validation failure |
| [`repo_health_check.py`](../local_harness/repo_health_check.py) | Checks documentation links, public-surface privacy, boundary language, explicit private packets, diff hygiene, and optional tests. | Human-readable `PASS`/`FAIL`/`SKIP` evidence |
| [`git_sync_cleanup.py`](../local_harness/git_sync_cleanup.py) | Inspects local Git and remote-tracking state and prints cleanup advice. | A read-only sync/cleanup report |

The first three are packet or scaffold printers. The last three are
validators or advisors that keep the paperwork and repository state
reviewable. Grouping them does not make one tool the controller of another.

## Typical Sequence

Use only the steps that fit the work:

```text
messy task
    -> Agent Task Session
    -> separately authorized human or agent work
    -> required checks and repo health
    -> Change Closeout
    -> optional Tool Maker lifecycle extraction
    -> human decision
```

`validate_scaffold.py` can check Tool Maker and Change Closeout files.
`repo_health_check.py` can validate an explicitly named Agent Task Session
without scanning `.work/` by default. `git_sync_cleanup.py` can inspect
post-merge branch state after the human-controlled Git action has occurred.

No step automatically invokes the next one.

## Boundaries

Vogon Printer tools do not collectively or individually:

- execute an Agent Task Session;
- run commands copied from source evidence;
- accept generated context or edits;
- mark tasks or lifecycles complete;
- merge, release, promote, push, or delete branches;
- perform cleanup merely because it was recommended;
- establish production readiness;
- replace human review.

Passing validation is evidence about a file or repository condition, not
authority to proceed. Humans retain task activation, edit authorization,
acceptance, publication, lifecycle, merge, release, promotion, exception, and
cleanup decisions.

## Why the Name

The nickname emphasizes explicit paperwork: scope, evidence, checks, status,
and closeout should be printed into reviewable files instead of living in
hidden state or operator memory. Unlike the fictional bureaucracy, the goal is
not paperwork for its own sake. The goal is to maximize trusted work per unit
of human attention.

For commands and detailed contracts, use the linked tool documents and
[`local_harness/README.md`](../local_harness/README.md).
