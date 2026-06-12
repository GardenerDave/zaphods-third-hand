# ZTH Synthesis Output Template

Use this template after independent agent outputs are complete. Do not run synthesis before the
independent packets are finished and collected.

```yaml
output_contract_version: zth.synthesis_output.v0.2
```

## Decision

<Proceed | Needs rework | Blocked | No action recommended>

## Summary

<Brief synthesis summary.>

## Source Agent Outputs

- <agent output path>
- <agent output path>

## Cross-Agent Agreement Map

Use `docs/prompts/AGREEMENT_MAP_TEMPLATE.md` for detailed convergence entries.

## Disagreements

Each disagreement must include:

- Conflict topic:
- Agents involved:
- Each agent's assessment:
- Evidence basis:
- Synthesis resolution:
- Rationale:
- Confidence:

Disagreement is signal, not noise. Preserve unresolved disagreements for human review instead of
hiding them in a generic risks section.

## Blind Spots / Coverage Notes

Summarize findings from `local_harness/zth_coverage_auditor.py`, if run.

## Risks

- <Risk>

## Suggested Next Step

<One concrete next step.>

## Confidence

<low | medium | high>
