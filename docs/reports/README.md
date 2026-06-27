# ZTH Reports

Reports are durable evidence snapshots.

They preserve selected results from local runs, model auditions, comparisons, audits, and review passes so they can be inspected later without rerunning the original workflow.

## In Plain English

A report is the part of a run that was worth keeping.

Most ZTH run output is local evidence. It may live under `.work/` or another generated-output directory while you inspect it. If a result is useful for future comparison, review, or project history, copy or summarize it here.

Reports should help answer:

- What was tested?
- What inputs or configs were used?
- What did the system produce?
- What failed?
- What looked promising?
- What should a human inspect next?

## What Belongs Here

Good report candidates include:

- model audition comparison reports;
- capability cards selected for long-term comparison;
- review summaries;
- audit findings;
- regression snapshots;
- notable failure analyses;
- human-readable summaries of important local runs.

## What Does Not Belong Here

Do not use `docs/reports/` for:

- raw scratch output from every run;
- large temporary logs;
- secrets, API keys, or private credentials;
- unreviewed model output that should stay local;
- production role assignments.

A report can describe generated output, but it should not pretend generated output is accepted truth.

## Report Rules

Reports should be:

- human-readable;
- file-based;
- dated or otherwise traceable;
- honest about failure modes;
- clear about what was measured;
- clear about what was not measured.

Before committing a report, normalize operator-specific usernames, absolute
home/workspace paths, and real endpoint hosts. Prefer package-relative paths,
`<MODEL_ROOT>`, and `<LAN_HOST>`. Preserve observed behavior, scores, failure
modes, and human-review boundaries; sanitizing provenance metadata must not
turn evidence into an approval or promotion claim.

Reports may record reviewed evidence and human decisions, but the report itself
does not establish production readiness.

## Current Report Areas

- `model_auditions/` — model audition cards and comparison reports.
- `failure_training/` — supervised failure-curriculum and adapter-training
  evidence, local hardware smoke summaries, and measured base-vs-adapter
  behavior comparisons.
- `preflight_smoke/` — supervised preflight → manifest → planner → gated
  audition smoke evidence, including honest blockers and retry conditions.
  The current reports include a partial fixture-backed run, a tooling-blocker
  report, and the completed live ZTH smoke-probe chain.
- `affordance_probes/` — supervised affordance candidate probe reports,
  repeatability evidence, held-promotion summaries, and eligibility, proposal,
  decision, plan, execution-approval, baseline execution-packet, and baseline
  runner evidence for experimental host-affordance work.

## Safety Reminder

Reports are evidence.

They support human review, comparison, and future decision-making. They do not
accept generated context, promote or rank models into roles, assign model
roles, move lifecycle state, or approve code changes. Humans make acceptance,
publication, lifecycle, and follow-up decisions.
