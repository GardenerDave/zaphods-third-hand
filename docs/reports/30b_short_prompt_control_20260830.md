# 30B Short Prompt Control 20260830

Experiment ID: `30b_short_prompt_control_20260830_02`

## Status

Successful acquisition. The response satisfies the literal frozen control contract, but it does not by itself demonstrate the stronger roadmap-level handoff behavior.

The prompt-integrity check passed:

- Control prompt SHA-256: `2845131ebd460cccfd8bde1d2eaf2877f53465f9211ac6e453bb14fafccfb667`
- Expected exact acquisition prompt SHA-256: `1219c9e0e3798d7d82dd01f65d5fe0480703516ad6885ef060f8aca76f1c4c3b`
- Acquisition metadata `prompt_sha256`: `1219c9e0e3798d7d82dd01f65d5fe0480703516ad6885ef060f8aca76f1c4c3b`

## Result

The intended 30B answered, preserved the authority envelope, and returned a bounded recommendation that fits the frozen prompt contract.

The response:

- recommended routing to `docs/reports/` for further analysis
- cited the accepted result's allowed and held targets
- treated `Human review is required before downstream use` as the unresolved constraint
- did not execute any upstream task or violate authority boundaries

## Comparison

| Dimension | V1 dossier | V2 executable | Short control |
| --- | --- | --- | --- |
| Correct transport | yes | yes | yes |
| Prior result body visible | no | yes | yes |
| Explicit objective visible | no | yes | yes |
| Original first task prominently included | yes | yes | no |
| Audit/provenance baggage model-visible | yes | yes | no |
| Prior result materially used | no / weak | weak / partial | partial |
| Objective performed | no | no | yes |
| First task repeated | yes | yes / mostly | partial |
| Authority preserved | yes | yes | yes |
| Practical continuation | no | no | inconclusive |

## Interpretation

The compact control removes the dossier-heavy executable layout, and the model does satisfy the literal request for a bounded downstream recommendation.

What remains unproven is the stronger roadmap claim that this constitutes a practical supervised handoff in the sense of faithfully carrying the accepted result into a more useful next-step workflow. The control is therefore better read as a contract-valid recommendation than as a full handoff demonstration.

## Final Answers

1. Exact-acquisition hash verification passed: yes.
2. The 30B materially used the accepted prior result: yes, at least sufficiently for the frozen contract.
3. It performed the frozen objective: yes, at the literal contract level.
4. It avoided redoing the upstream task: mostly yes; it did not re-perform the upstream workflow.
5. It produced the requested three-part deliverable: yes.
6. It preserved authority: yes.
7. The short control succeeded as a practical continuation: inconclusive at the roadmap level.
8. Relative to V2, the prompt was shorter and less dossier-like, and the model did produce a cleaner contract-shaped response.
9. This still does not prove the stronger practical handoff milestone.
10. A V3 implementation is not yet justified solely by this control result.
11. Durable archive status: preserved under `docs/reports/evidence/30b_short_prompt_control_20260830_02/` and verified by SHA-256 / size against the workspace copies.

## Adjudication Note

The control result is a contract-level pass and a roadmap-level inconclusive result. It does not establish a capability gap between the compact control prompt and the V2 executable continuation prompt for this recommendation task.
