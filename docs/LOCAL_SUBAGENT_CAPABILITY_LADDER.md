# Local-Subagent Capability Ladder

ZTH uses supervised workflow layers around a model endpoint. This document
defines the current capability ladder so the repository can distinguish
bounded evidence from authority.

The ladder is intentionally conservative:

- model endpoint alone is not an agent;
- validation is not acceptance;
- a generated patch is not an applied patch;
- a test pass is not merge or release authority;
- failure capture is explicit and opt-in;
- exported patterns remain candidates;
- independent coding capability has not been demonstrated.

## Shared boundary rules

Across every layer below:

- Codex remains the supervising implementation authority.
- The local model is an inference worker and candidate subagent only.
- The model may inspect evidence that Codex provides through approved tools or
  prompts.
- The model may not authorize its own work, mutate the authoritative repo, or
  move lifecycle state.
- Validation output is evidence, not acceptance.
- Success on one bounded task does not promote a broader capability claim.

## 1. Model Call

Current demonstrated status: demonstrated.

Input authority:

- a single prompt or packet supplied by Codex;
- optional bounded excerpts or machine-readable artifacts;
- no direct repository mutation authority.

Output authority:

- candidate text, structured output, or patch draft only;
- no acceptance authority;
- no commit, merge, push, or release authority.

Allowed tools:

- none directly from the model call itself;
- only the prompt contents provided by Codex.

Prohibited actions:

- direct shell execution;
- direct file writes;
- self-approval;
- claims of completed work without evidence.

Required validators:

- output-contract validation when a structured response is expected;
- semantic review by Codex.

Required supervisor review:

- always.

Evidence needed for promotion:

- repeated bounded outputs that satisfy the relevant output contract;
- reviewed evidence that the outputs are useful for the next supervised layer.

Failure conditions:

- unsupported certainty;
- contract mismatch;
- scope expansion;
- authority boundary violation.

Retry behavior:

- retry only with a revised prompt or bounded evidence packet;
- increase packet depth monotonically after a failure.

Provenance requirements:

- preserve the exact prompt, raw output, validation result, and review result.

Current status:

- demonstrated as a bounded inference worker only.

## 2. Bounded Advisory Subagent

Current demonstrated status: demonstrated.

Input authority:

- a bounded task summary;
- explicit allowed targets or evidence categories;
- explicit held targets;
- explicit stop conditions.

Output authority:

- diagnosis;
- structured recommendations;
- target shortlist;
- test suggestions;
- claim audit;
- no execution authority.

Allowed tools:

- approved read-only inspection tools used by Codex on its behalf;
- structured-output generation requested by Codex.

Prohibited actions:

- direct command execution;
- file edits;
- self-acceptance;
- authority expansion beyond the packet.

Required validators:

- schema validation when a structured response is required;
- Codex fact check against repository evidence.

Required supervisor review:

- always before any downstream use.

Evidence needed for promotion:

- repeated bounded analysis that stays within target and authority limits;
- correct separation of evidence from inference.

Failure conditions:

- unsupported certainty;
- invented files or commands;
- scope expansion;
- claim drift from repository evidence.

Retry behavior:

- re-ask with more evidence or narrower targets;
- do not weaken the boundary to obtain a nicer answer.

Provenance requirements:

- preserve the prompt packet and raw model output;
- record the review classification and any corrections.

Current status:

- demonstrated.

## 3. Patch-Drafting Subagent

Current demonstrated status: probable, not yet promoted.

Input authority:

- a bounded failing case or review target;
- exact allowed file set;
- explicit held targets;
- explicit acceptance checks.

Output authority:

- candidate diff or explicit no-patch result;
- proposed tests;
- remaining uncertainty.

Allowed tools:

- patch drafting only;
- no authority to apply the patch to the authoritative branch.

Prohibited actions:

- touching held targets;
- inventing APIs, files, or behavior;
- claiming the patch is accepted.

Required validators:

- output-contract validation;
- `git apply --check` on the candidate diff;
- focused tests on an isolated worktree.

Required supervisor review:

- always before patch application in any real worktree.

Evidence needed for promotion:

- repeated contract-valid patch drafts that obey allowed-target limits;
- successful supervised application in a disposable worktree;
- focused and broader tests that support the root cause.

Failure conditions:

- malformed diff;
- unauthorized targets;
- path traversal;
- semantic mismatch with the actual bug.

Retry behavior:

- keep the same or narrower target set;
- increase evidence and packet depth monotonically;
- cap retries per audition.

Provenance requirements:

- preserve failed and successful raw outputs, validation artifacts, and any
  human edits.

Current status:

- probable, but not yet adequately auditioned for promotion.

## 4. Tool-Using Implementation Subagent

Current demonstrated status: not demonstrated.

Input authority:

- a bounded tool request packet;
- explicit allowed tools;
- explicit denied tools;
- explicit target and sandbox limits.

Output authority:

- requested tool results only;
- candidate follow-up reasoning;
- no direct authority over the repository or the host.

Allowed tools:

- only the tools explicitly permitted by the supervisor and harness;
- read-only inspection tools and narrowly scoped sandbox actions.

Prohibited actions:

- unrestricted shell;
- network access unless explicitly authorized for inspection;
- package installation;
- Git push, merge, reset, clean, or branch deletion;
- writes outside the sandbox;
- self-acceptance.

Required validators:

- tool request schema validation;
- path and target authorization checks;
- sandbox enforcement;
- result parsing and review.

Required supervisor review:

- every tool request and every tool result.

Evidence needed for promotion:

- repeated correct tool selection;
- correct response to tool failures;
- correct adherence to target and sandbox limits;
- a viable supervised change produced without unauthorized actions.

Failure conditions:

- tool misuse;
- scope expansion;
- unauthorized command request;
- output that claims authority beyond the request.

Retry behavior:

- retry only with a narrower or better-specified tool request;
- preserve denied requests and failures as evidence.

Provenance requirements:

- log every request, denial, execution, and result;
- preserve the exact request and result payloads.

Current status:

- not demonstrated.

## 5. Independent Coding Agent

Current demonstrated status: not demonstrated.

Input authority:

- a bounded task statement is not enough on its own;
- the agent would need external supervision and explicit constraints to be
  considered at this level.

Output authority:

- would need to be able to carry a task end-to-end without self-granting
  authority;
- this has not been established here.

Allowed tools:

- none granted by this document;
- any future authority would still need to be externally bounded.

Prohibited actions:

- defining unlimited scope;
- approving its own patch;
- marking work complete;
- skipping tests;
- deleting evidence;
- claiming repository-wide certainty from partial inspection.

Required validators:

- stronger than the current supervised workflow has demonstrated;
- must include human-supervised evidence and independent verification.

Required supervisor review:

- yes, and the review would still need to remain authoritative.

Evidence needed for promotion:

- repeated independent task completion without authority violations;
- correct handling of ambiguity, tests, and stop conditions;
- no self-acceptance and no unsupported certainty.

Failure conditions:

- any self-granted authority;
- scope expansion;
- acceptance without evidence;
- destructive or unauthorized action.

Retry behavior:

- not applicable as a general capability claim until more evidence exists.

Provenance requirements:

- would need complete evidence trails for every task;
- this repository has not yet demonstrated that bar.

Current status:

- not demonstrated.

## Why this matters

ZTH supplies supervised agency around the model. That means the repository can
build reviewable workflows, but the model endpoint itself remains only an
inference worker. Validation, review, and pattern export are evidence layers;
they do not promote patches, approve lifecycle changes, or create training
authority.

## Promotion caution

A successful bounded example improves confidence only for the exact bounded
setting that was tested. It does not, by itself, justify a wider capability
claim. Promotion requires repeated evidence, reviewed provenance, and explicit
supervisor approval.
