# ZTH Agent Output Contract

Use this format when returning work from one independent external agent. Keep the headings intact so
`local_harness/zth_compare_agent_outputs.py` can compare multiple outputs.

Every agent output must declare the contract version before the first heading. The version lets
comparison and synthesis tools detect format drift across agents. Missing or mismatched versions
should be treated as contract warnings until a human decides compatibility.

Template starts here:

output_contract_version: zth.agent_output.v0.2

## Decision

<Accepted for follow-up | Needs rework | Blocked | No action recommended>

## Summary

<Brief result summary.>

## Files Inspected

- <path>

## Files Changed

- <path, or "None">

## Commands Run

- `<command, or "None">`

## Evidence

- <Specific observation, diff fact, command result, or file reference.>

## Assumptions

- <Assumption, or "None">

## Risks

- <Risk, or "None">

## Confidence

<low | medium | high>

## Suggested Next Step

<One concrete next step.>

## Optional Handoff Notes

<Anything useful for a later synthesis or human review step.>

## Example

output_contract_version: zth.agent_output.v0.2

## Decision

Needs rework

## Summary

The parser refactor looks directionally useful, but one fallback path is not covered by tests.

## Files Inspected

- `local_harness/icm_parsers.py`
- `local_harness/tests/test_icm_call.py`

## Files Changed

- None

## Commands Run

- `python3 -m pytest local_harness/tests`

## Evidence

- Existing tests pass.
- `parse_worker_response` has no direct test for empty `choices`.

## Assumptions

- The current OpenAI-compatible response shape remains the supported target.

## Risks

- A provider returning an empty `choices` list may produce unclear errors.

## Confidence

medium

## Suggested Next Step

Add one focused parser test for empty `choices` before changing parser behavior.

## Optional Handoff Notes

No file edits were made by this reviewer.
