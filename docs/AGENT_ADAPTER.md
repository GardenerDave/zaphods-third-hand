# ZTH Agent Adapter

The ZTH Agent Adapter is a lightweight way to use Zaphod's Third Hand as a context workbench for
external multi-agent or panel systems.

ZTH is not becoming a panel system. External systems may coordinate panels, gates, or human review.
ZTH prepares role-specific packets, keeps repo/context evidence explicit, and compares completed
agent outputs after independent work is finished.

## Workbench, Not Orchestrator

Orchestration means scheduling agents, deciding gates, merging outputs, and choosing what happens next.

Workbench support means:

- Prepare a bounded packet for one role and one task.
- Include source-of-truth repo context, constraints, commands, and do-not-touch areas.
- Require a strict output contract.
- Compare completed outputs after agents have worked independently.

ZTH provides the workbench layer only. It does not run a scheduler, daemon, database, event bus, or
permanent agent runtime.

## Independence Rule

Packets may share source-of-truth repo context, but one agent's conclusions must not be included in
another agent's packet before synthesis/comparison.

Use this rule when preparing packets:

- Shared repo files, docs, tests, and command outputs are allowed.
- Another agent's recommendation, critique, or decision is not allowed until comparison time.
- Synthesis happens only after the independent outputs are complete.

This keeps parallel reviewers from anchoring on each other and makes disagreements visible.

## Recommended Flow

1. An external orchestrator or human operator chooses role, task, repo scope, and context budget.
2. ZTH generates a role-specific packet with `local_harness/zth_agent_packet.py`.
3. The packet is handed to one external agent.
4. The agent works independently and returns output using `docs/prompts/AGENT_OUTPUT_CONTRACT.md`.
5. Repeat for other independent agents, using only shared source-of-truth context.
6. Optionally run `local_harness/zth_coverage_auditor.py` before synthesis to expose blind spots.
7. ZTH compares completed outputs with `local_harness/zth_compare_agent_outputs.py`.
8. A human or external orchestrator decides what follow-up work, if any, should happen.

## Suggested Modes

- `quick`: small documentation or configuration edits with low blast radius.
- `standard`: normal repo changes where tests and review evidence are expected.
- `rig`: high-risk architecture, refactor, safety, security, or release decisions.

The mode is a communication contract. It does not grant autonomy or bypass human review.

## Contract Versioning

Every completed agent output should declare:

```yaml
output_contract_version: zth.agent_output.v0.2
```

The comparison utility reports missing or mismatched versions as contract warnings. This keeps
format drift visible before synthesis relies on incompatible outputs.

## Token Budget And Checkpoints

Role packets can include checkpoint guidance:

```yaml
token_budget_guidance:
  scope: narrow|normal|broad
  checkpoint_required: true|false
  checkpoint_rule: "Write findings incrementally after each major finding or every N findings."
  max_findings_before_checkpoint: 5
```

Use `broad` and `checkpoint_required: true` for roles such as functional/UX testing, red-team review,
large documentation audits, or any task likely to produce many findings. The goal is to get durable
intermediate findings written before the model runs out of budget or spends too long planning.

## Example Roles

- Correctness reviewer: checks behavior, tests, edge cases, and regressions.
- Pragmatism reviewer: checks scope, maintainability, operational cost, and simplicity.
- Implementation agent: proposes or performs bounded edits only when explicitly allowed.
- Documentation verifier: checks docs against current files and beginner workflow.
- Red-team reviewer: looks for safety, misuse, leakage, and boundary failures.
- Synthesis agent: compares completed outputs after independent work is done.

## CLI Tools

Generate one role packet:

```bash
python3 local_harness/zth_agent_packet.py \
  --task "Evaluate parser refactor" \
  --role correctness \
  --mode standard \
  --scope "local_harness docs" \
  --files README.md docs/FIRST_SUCCESS.md local_harness/README.md \
  --constraints "No network calls" "Do not change safety language" \
  --acceptance "Existing tests pass" "Packet follows output contract" \
  --commands "python3 -m pytest local_harness/tests" \
  --output /tmp/ZTH_AGENT_PACKET.md
```

Compare completed outputs:

```bash
python3 local_harness/zth_compare_agent_outputs.py agent1.md agent2.md agent3.md
```

Audit planned packets or completed outputs for obvious coverage blind spots:

```bash
python3 local_harness/zth_coverage_auditor.py packet1.md packet2.md agent-output.md
```

Use `docs/prompts/SYNTHESIS_OUTPUT_TEMPLATE.md` and `docs/prompts/AGREEMENT_MAP_TEMPLATE.md` when
turning independent outputs into a human-reviewed synthesis.

Recommended v0.2 sequence:

1. Generate independent role packets.
2. Run the coverage auditor before synthesis.
3. Compare completed outputs for contract drift, agreement maps, and disagreements.
4. Write synthesis with explicit disagreement resolution and human follow-up.

## Non-Goals

- No built-in multi-agent scheduler.
- No permanent agents.
- No service daemon, database, event bus, or agent runtime.
- No cloud dependency.
- No online neural memory or training.
- No mandatory large-model panel.
- No automatic lifecycle movement.
- No automatic canonicalization.
- No automatic review-patch acceptance.

## Safety Notes

The existing ZTH safety model still applies:

- Human-supervised operation only.
- No unattended execution.
- No batched execution by default.
- Generated outputs are review material until a human accepts follow-up work.
- External agent output does not authorize file edits, commits, lifecycle movement, or future packets.
