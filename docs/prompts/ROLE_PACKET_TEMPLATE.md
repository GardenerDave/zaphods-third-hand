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

## Required Output Contract

Return your final response using `docs/prompts/AGENT_OUTPUT_CONTRACT.md`.

## Independence Rule

Use only the repo/context evidence in this packet. Do not include, rely on, or react to another
agent's conclusions before synthesis/comparison. Shared source-of-truth files are allowed;
cross-agent conclusions are not.
