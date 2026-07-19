# Model Audition Reports

This directory contains durable snapshots from ZTH model audition runs.

Model audition reports compare models on repeatable prompts, fixtures, scorer profiles, suites, and boards. They are useful for tracking model behavior over time, but they are not production role assignments.

Some reports use the optional small-model harness, which can download candidate
GGUFs and manage temporary local llama.cpp servers for exploratory evaluation.
That server lifecycle is evidence-gathering support only; it is not production
model-server management or evidence of production readiness.

## In Plain English

A model audition report says:

> These models were tested this way, on these small probes, and this is what happened.

It does not say:

> This model is now approved as the router, coder, reviewer, or production agent.

That decision belongs to later human review and policy layers.

## What to Preserve

When saving audition results, prefer preserving:

- `comparison.md`
- `comparison.json`
- selected `board_capability_card.json` files
- selected `board_capability_card.md` files
- short notes explaining why the result mattered

Avoid preserving every raw scratch run. Keep `.work/` disposable unless a result has review value.

## Suggested Report Folder Shape

Use a dated folder name when the report represents a specific comparison run.

Example:

    docs/reports/model_auditions/qwen_local_models_2026-06-18/

Suggested files:

    comparison.md
    comparison.json
    cards/
      qwen25_3b_full_board_smoke.json
      qwen25_coder7b_full_board_smoke.json
      qwen25_7b_instruct_full_board_smoke.json

## How to Read a Comparison Report

Look for:

- overall score;
- suite-level score;
- failure modes;
- runtime;
- missing outputs;
- scorer mismatches;
- prompt or endpoint compatibility problems.

A lower score is not always a worse model. It may indicate:

- the prompt was not appropriate for that model family;
- the output budget was too small;
- the endpoint returned reasoning in a separate channel;
- the scorer expected a stricter shape than the model produced;
- the model was too slow for the current runtime profile.

## Useful Questions

When reviewing a report, ask:

- Did the model actually fail, or did the harness/prompt profile not fit it?
- Were failures deterministic scoring failures or runtime failures?
- Did the model produce useful content in the wrong channel?
- Did the result expose a missing diagnostic?
- Should this become a regression fixture?
- Should the model be retested with a different prompt, timeout, or output budget?

## Evidence Types

- Board/capability-card auditions use suites, fixtures, scorer profiles, board
  comparisons, capability cards, and optional preflight gates.
- Exploratory small-model auditions preserve raw prompt responses and
  mechanical scores from GGUF-backed or existing local/LAN endpoints.
- Direct supervised patch probes test whether a model can produce one bounded
  artifact from a constrained packet. They are not board auditions and do not
  produce capability cards.

Keep these evidence types in separate output directories. Their schemas and
review purposes differ, and none of them promotes, assigns, or
production-certifies a model.

## Direct Supervised Patch-Probe Milestone

The `qwen3-1.7b-gpu-40k` run reached `ACCEPT`: the 1.7B model produced an
accepted constrained human patch checklist from a corrected supervised patch
packet.

This is evidence of guided capability: small models can perform bounded
complex work when tasks are decomposed, supervised, and validated. It is not
evidence of general intelligence. The demonstrated value is in packet design,
constrained output, validation, provenance, and operator acceptance gates.

The accepted artifact retains review caveats:

- some generated `stop_conditions` were weak or provenance-like rather than
  true operational stop rules;
- one acceptance check used broad “All board names” wording that may need
  operator tightening.

## Current Reports

- `qwen_local_models_2026-06-18/` — comparison of local Qwen model candidates across the baseline audition board.
- `SMALL_MODEL_AUDITION_2026-06-19.md` — exploratory small-model GGUF, endpoint, and prompt observations.
- `CODING_DELEGATION_DOGFOOD_2026-07-02.md` — blocked coding-delegation evidence showing the local 1.7B path was unavailable in this environment.
- `QWEN3_CODER_SUPERVISED_DOGFOOD_2026-07-11.md` — preserved logic-probe progression, fixture correction, and duration-diagnostic repair evidence.
- `QWEN3_CODER_TRIAGE_ROUTER_REVIEW_2026-07-12.md` — branch review of the
  reusable endpoint logic-probe workflow and authority scoring fix on
  `triage-router-supervised-attempts`.
- `DOGFOOD_AND_PROMPT_PATCH_AB_CLOSEOUT_2026-07-16.md` — concise closeout covering the dogfood evidence chain and the fixture-based prompt patch A/B harness chain.
- `LIVE_PROMPT_PATCH_AB_SMOKE_CLOSED_LOOP_2026-07-16.md` — closeout for the first successful supervised live prompt patch A/B smoke trial.
- `LIVE_PROMPT_PATCH_AB_IMPROVED_CHALLENGE_2026-07-16.md` — closeout for the first improved supervised live prompt patch A/B challenge.
- `FULL_LIVE_TO_CANDIDATE_PROMPT_PATCH_AB_LOOP_2026-07-16.md` — closeout for the successful live-to-candidate prompt patch A/B loop.
- `FULL_LIVE_TO_CANDIDATE_PROMPT_PATCH_AB_LOOP_2026-07-16.md`, `SUPERVISED_WORKER_LOOP_120_TASK_DOGFOOD_CLOSEOUT_2026-07-17.md`, and the roadmap entry together mark the completed supervised local-worker evidence loop that feeds the next high-scale dogfood phase.
- `SUPERVISED_WORKER_LOOP_120_TASK_DOGFOOD_CLOSEOUT_2026-07-17.md` — closeout for the completed 120-task supervised dogfood batch, including queue/state validation and the preserved review bundle.
- `SUPERVISED_WORKER_LOOP_120_TASK_SYNTHESIS_2026-07-17.md` — compact decision synthesis for the completed 120-task supervised dogfood batch.
- `MESSY_INPUT_TRIAGE_PACKET_FIRST_DOGFOOD_2026-07-17.md` — first manual dogfood sample for the messy-input front door, including the validated packet and authority boundary.
- `MESSY_INPUT_TRIAGE_PACKET_WORKER_AUDITION_2026-07-17.md` — blocked local-worker audition attempt for the messy-input front door; endpoint missing, so no packet was produced.
- `MESSY_INPUT_TRIAGE_PACKET_WORKER_AUDITION_ATTEMPT_002_2026-07-17.md` — supervised local-worker audition attempt after the endpoint became available; both outputs parsed but failed the validator, so no packet was accepted.
- `MESSY_INPUT_TRIAGE_PACKET_WORKER_AUDITION_ATTEMPT_003_2026-07-17.md` — supervised local-worker audition attempt with the patched contract prompt; the parsed packet validated successfully, but router automation remains unproven.
- `MESSY_INPUT_TRIAGE_TO_BOUNDED_TASK_BRIDGE_2026-07-17.md` — manual bridge from validated messy-input triage evidence into a review-required bounded task draft; queue handoff and router automation remain unproven.
- `BOUNDED_TASK_PACKET_DRAFT_VALIDATOR_2026-07-17.md` — deterministic validator for the review-required bounded task draft bridge artifact; queue handoff and router automation remain unproven.
- `VALIDATED_MESSY_INPUT_TRIAGE_TO_BOUNDED_TASK_BRIDGE_2026-07-17.md` — deterministic bridge from validated messy-input triage evidence into a validated bounded task packet draft; queue handoff and router automation remain unproven.
- `TRIAGE_TO_BOUNDED_TASK_BRIDGE_FIXTURES_2026-07-17.md` — deterministic fixture suite for the validated bridge, covering pass cases and fail-closed queue/unsafe-action cases.
- `BOUNDED_TASK_REVIEW_PACKET_FIXTURES_2026-07-17.md` — deterministic fixture suite for the bounded-task-review packet, covering pass cases and fail-closed queue/repo-mutation/unsafe-next-step cases.
- `FRONT_DOOR_CHAIN_VALIDATOR_2026-07-17.md` — read-only deterministic validator for the full front-door chain; queue handoff and router automation remain unproven.
- `FRONT_DOOR_CHAIN_SCORECARD_2026-07-17.md` — read-only scorecard for the full front-door chain validator result; it classifies review readiness without granting queue handoff or downstream use.
- `FRONT_DOOR_CHAIN_REVIEW_COMMAND_2026-07-17.md` — read-only wrapper that validates and scores the full front-door chain in one command; it remains review-only and non-automated.
- `FRONT_DOOR_LANE_SYNTHESIS_2026-07-17.md` — synthesis of the completed supervised front-door lane from messy input to review-ready bounded work; it records what is proven and what remains unproven.
- `FRONT_DOOR_CHAIN_DIVERSE_FIXTURES_2026-07-17.md` — diverse messy-input fixture pack for the front-door lane; it broadens coverage without granting queue handoff or downstream use.
- `FRONT_DOOR_FIXTURE_EXPANSION_SYNTHESIS_2026-07-17.md` — synthesis of the diverse fixture expansion; it records the conservative validator behavior it exposed and what remains unproven.
- `FRONT_DOOR_CHAIN_BLOCKED_FIXTURES_2026-07-17.md` — blocked-case fixture pack for front-door calibration; it confirms the review wrapper fails closed on invalid or unsafe chains.
- `FRONT_DOOR_CALIBRATION_SYNTHESIS_2026-07-17.md` — calibration synthesis after both the passing and blocked front-door fixture packs; it records covered failure modes and what remains unproven.
- `QUEUE_HANDOFF_REVIEW_DESIGN_2026-07-17.md` — spec-only queue-handoff review design; it defines the boundary for a future queue-candidate step without authorizing queue insertion.
- `QUEUE_HANDOFF_REVIEW_VALIDATOR_2026-07-17.md` — fail-closed validator for queue-handoff review artifacts; it checks the design-only review boundary without writing a queue.
- `QUEUE_HANDOFF_REVIEW_FIXTURES_2026-07-17.md` — tracked fixture pack for queue-handoff review validation; it covers pass cases and fail-closed unsafe/malformed cases.
- `QUEUE_HANDOFF_REVIEW_CALIBRATION_SYNTHESIS_2026-07-17.md` — calibration synthesis after the validator and tracked pass/blocked fixtures; it records what is proven and what remains unimplemented.
- `QUEUE_APPROVAL_PATH_VALIDATOR_2026-07-18.md` — review-only validator scaffold for the future queue approval path; it validates manual queue-insertion candidates without queue writing.
- `QUEUE_APPROVAL_PATH_CALIBRATION_SYNTHESIS_2026-07-18.md` — calibration synthesis after the queue approval validator, fixtures, and regression tests; it records what is proven and what remains unimplemented.
- `QUEUE_APPROVAL_REVIEW_COMMAND_2026-07-18.md` — read-only queue approval review command; it wraps validation and emits explicit review output only.
- `QUEUE_APPROVAL_REVIEW_COMMAND_CALIBRATION_SYNTHESIS_2026-07-18.md` — calibration synthesis after the read-only queue approval review command; it records output-path safety, exit-status behavior, and what remains unimplemented.
- `DECLARATIVE_LONG_DURATION_MILESTONE_MAP_CALIBRATION_SYNTHESIS_2026-07-18.md` — calibration synthesis for the declarative long-duration dogfood milestone map; it records evidence-driven selection and the terminal closeout target.
- `LONG_DURATION_DOGFOOD_CLOSEOUT_2026-07-18.md` — closeout for the supervised long-duration dogfood run; it records the completed evidence trail and the operator review stop point.
- `LONG_DURATION_DOGFOOD_PRESENTATION_NOTES_2026-07-18.md` — presentation-ready notes for the evidence-backed dogfood loop; it is demo framing only and does not claim any queue or downstream authority.
- `LONG_DURATION_DOGFOOD_CRON_2026-07-18.md` — supervised long-duration dogfood cron design and usage notes; it generates review artifacts without auto-commit, push, or queue writing.

## Safety Reminder

Model audition reports are candidate fit evidence.

They can inform routing, role design, model selection, and future MTNG/ZTH policy layers, but they do not automatically assign production responsibilities.
