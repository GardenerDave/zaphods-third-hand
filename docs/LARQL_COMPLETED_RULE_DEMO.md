# LARQL Completed Rule Demo

This document shows one completed LARQL JSON rule trial end to end, using `unsupported_file_target_authority_v0` as the example.

The workflow is supervised and guided capability, not autonomous repository authority. It exists to turn a bounded failure pattern into a reviewable rule trial with explicit approvals, explicit review gates, and preserved evidence.

## What the workflow is

The LARQL JSON rule-trial workflow is a repeatable sequence for:

1. identifying a failure pattern,
2. drafting a model-free candidate,
3. reviewing the candidate,
4. drafting a runtime-rule packet,
5. reviewing the packet,
6. requiring explicit local install approval,
7. installing a local runtime-rule artifact only,
8. drafting consultation context,
9. requiring explicit bounded model-call approval,
10. running a strict JSON model-context probe,
11. independently reviewing the probe, and
12. recording a closeout.

It is not a training workflow, not a promotion workflow, and not an unattended runtime-governance workflow.

## The failure pattern this rule addresses

`unsupported_file_target_authority_v0` addresses a simple boundary failure:

- an `allowed_files` list was read as if it authorized broader repository edits;
- a requested target outside `allowed_files` was treated as implicitly okay;
- adjacent, generated, unrelated, or “while here” cleanup edits were treated as covered by the list.

That is the failure class the rule keeps bounded.

## Why `allowed_files` is an authority boundary

`allowed_files` is not a vague hint. It is the scope boundary.

If a file is not in `allowed_files`, then it is not authorized by that list. The correct response is to hold the out-of-scope file and request explicit scope expansion or review. The list does not authorize adjacent edits, generated-file edits, unrelated cleanup, or patch expansion.

## Compact lifecycle table

| Stage | Evidence |
| --- | --- |
| Candidate | model-free candidate scaffold |
| Candidate review | review approved the candidate for runtime-rule drafting |
| Runtime-rule packet | draft rule content and contract were written |
| Packet review | packet was held at the install boundary |
| Local runtime-rule install | local artifact only, with explicit approval text |
| Consultation context | rule content was packaged for later prompt injection |
| First JSON model-context probe failure | semantically correct JSON was wrapped in markdown fences |
| Transport hardening | prompt transport was tightened to require exact JSON-only output |
| Repaired JSON model-context probe pass | the model returned the exact JSON contract |
| Independent review | the probe was reviewed without trusting the scorer alone |
| Closeout | the pass was documented and preserved |
| Registry entry | the completed rule was indexed in the rule registry |
| Evidence packet | one command can now collect the relevant artifacts |

## Where the evidence lives

The main evidence trail is split across tracked docs and generated local evidence:

- registry: `docs/reports/affordance_larql/larql_rule_registry.json`
- registry status: `docs/reports/affordance_larql/LARQL_RULE_REGISTRY_STATUS.md`
- closeout: `docs/reports/affordance_larql/UNSUPPORTED_FILE_TARGET_AUTHORITY_JSON_MODEL_CONTEXT_PASS_CLOSEOUT_2026-06-29.md`
- machinery audit: `docs/reports/affordance_larql/LARQL_MACHINERY_PACKAGING_AUDIT_2026-06-29.md`
- evidence packet collector: `local_harness/larql_evidence_packet.py`

The preserved local probe evidence is in:

- first failed JSON model-context probe directory: `.work/affordance_larql_json_model_context_probes/unsupported_file_target_authority_v0/`
- repaired passing JSON model-context probe directory: `.work/affordance_larql_json_model_context_probes/unsupported_file_target_authority_v0_transport_repair1/`
- passing independent review: `.work/affordance_larql_json_model_context_probe_reviews/unsupported_file_target_authority_v0_transport_repair1/unsupported_file_target_authority_json_model_context_probe_review.json`

## How to generate the evidence packet

Use the registry entry to collect the relevant artifacts for the completed rule:

```bash
python3 local_harness/larql_evidence_packet.py \
  --registry docs/reports/affordance_larql/larql_rule_registry.json \
  --rule-id unsupported_file_target_authority_v0 \
  --out .work/larql_evidence_packets/unsupported_file_target_authority_v0
```

That writes a manifest and a short markdown summary for the selected rule.

## What the first live probe failure proved

The first live JSON model-context probe failed because the model wrapped valid JSON in markdown fences.

That failure proved a transport-contract problem, not a semantic rule failure. The rule idea remained intact; the response form was wrong.

## Why the transport repair was legitimate

The repair was legitimate because it changed the transport contract, not the rule boundary:

- the prompt was hardened to require one JSON object only;
- markdown fences were explicitly forbidden;
- prose outside JSON was explicitly forbidden;
- the scorer remained strict;
- markdown-fenced JSON remained a failure.

The repair made the transport narrower. It did not loosen the scorer and it did not change the authority boundary.

## What the final passing probe proved

The repaired probe showed that the model could return the exact JSON contract when the response shape was narrow and the context was bounded.

That proved:

- the JSON-contract path works for a file-target authority rule;
- independent review can approve the scorer result;
- the first failure was worth preserving because it showed the transport problem clearly;
- the final pass was genuine because it met the exact contract after repair.

## What remains intentionally not authorized

This workflow did not authorize:

- training data;
- dataset artifacts;
- durable memory;
- candidate promotion;
- model mutation;
- runtime-rule modification beyond the approved local artifact install;
- automatic failure-to-curriculum capture.

Failure-to-curriculum capture was not automatic and was not authorized.

## Why this is supervised guided capability

This is supervised guided capability because the workflow depends on explicit human review gates at each boundary:

- candidate review
- runtime-rule packet review
- install approval
- consultation drafting
- bounded model-call approval
- probe review

The system can produce evidence, but it does not grant itself authority.

## Next machinery step

The next machinery step is a reusable lifecycle status driver.

The registry and evidence packet collector now exist. The next useful layer is a small driver that can read registry entries and evidence-packet outputs, summarize lifecycle state, and show what step is complete or held without re-running the whole workflow.

That is the direction to take now: package and navigate the completed rule trials, do not add another hand-built rule yet.
