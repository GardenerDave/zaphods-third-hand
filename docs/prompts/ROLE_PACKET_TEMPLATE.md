# ZTH Independent Agent Role Packet Template

Use this template for one independent agent. Give the same source-of-truth repo evidence to multiple
agents when needed, but do not include another agent's conclusions before synthesis/comparison.

## Task

<Describe the task in one or two concrete paragraphs.>

## Role

<Examples: correctness reviewer, pragmatism reviewer, implementation agent, documentation verifier,
red-team reviewer, synthesis agent.>

## Mode

<quick | standard | rig>

## Repo Scope

<Name the repo areas, packages, docs, or paths in scope.>

## Relevant Files

- <path>
- <path>

## Constraints

- <Constraint>
- <Constraint>

## Acceptance Criteria

- <Criterion>
- <Criterion>

## Known Risks

- <Risk>
- <Risk>

## Commands To Run

- `<command>`
- `<command>`

## Do-Not-Touch Areas

- <path or area>
- <path or area>

## Token Budget / Checkpoint Guidance

```yaml
token_budget_guidance:
  scope: narrow|normal|broad
  checkpoint_required: true|false
  checkpoint_rule: "Write findings incrementally after each major finding or every N findings."
  max_findings_before_checkpoint: 5
```

For broad roles, require checkpoints so useful findings are written before a model runs out of
budget or spends too long planning.

## Required Output Contract

Return your final response using `docs/prompts/AGENT_OUTPUT_CONTRACT.md`.

Required metadata:

```yaml
output_contract_version: zth.agent_output.v0.2
```

## Independence Rule

Use only the repo/context evidence in this packet. Do not include, rely on, or react to another
agent's conclusions before synthesis/comparison. Shared source-of-truth files are allowed;
cross-agent conclusions are not.
