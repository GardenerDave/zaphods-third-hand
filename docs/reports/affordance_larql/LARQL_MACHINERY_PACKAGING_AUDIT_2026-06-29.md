# LARQL Machinery and Packaging Audit

Date: 2026-06-29

This audit reviews the completed hand-built LARQL JSON rule-trial workflow and identifies the smallest reusable machinery layer needed to make the pattern repeatable.

## Completed rule trials

The repo now contains three completed hand-built rule trials:

- absence-of-evidence
- unsupported-certainty / scope-claim
- unsupported-file-target authority

Each trial followed the same supervised lifecycle, with rule-specific identifiers and rule content.

## Repeated lifecycle stages

Across the three trials, the same stages appeared in order:

1. identify a failure pattern
2. draft a model-free candidate
3. review the candidate
4. draft a runtime-rule packet
5. review the runtime-rule packet
6. require explicit local install approval
7. install a local runtime-rule artifact only
8. draft a runtime consultation probe
9. require explicit bounded model-call approval
10. run a strict JSON model-context probe
11. independently review the model-context probe
12. record a pass/failure closeout

That shape is already documented in `docs/LARQL_JSON_RULE_TRIAL_TEMPLATE.md`, and the three rule paths show it is not theoretical.

## Duplicated script patterns

The scripts repeat the same categories of logic with only rule-specific names and contracts changing:

- candidate scripts write a draft JSON report with identifiers, explicit negative authority flags, and a next-step field
- candidate review scripts validate identifiers, required fields, contract shape, and boundary flags before approving the next draft step
- runtime-rule packet scripts consume the approved candidate and candidate review, then draft a packet with the rule content and a strict non-install boundary
- packet review scripts independently check that the packet remains draft-only and held at the install boundary
- install scripts require explicit approval text, compute provenance hashes, and write a local runtime-rule artifact plus install record
- consultation probe scripts turn the installed rule into a prompt/context packet and keep the probe model-free
- JSON model-context probe scripts build the prompt, call the endpoint once when authorized, score the bounded response, and capture raw evidence
- JSON model-context probe review scripts independently validate probe JSON, prompt, and raw response without trusting the scorer alone
- closeout docs summarize what was proved, what was not proved, and what remains held

The duplicated structure is clear; the variations are mostly:

- identifiers
- contract strings
- allowed/blocked claims
- file paths
- report types and verdict names

## Duplicated test patterns

The tests repeat the same mechanical checks:

- help output works
- valid artifacts produce the expected report
- missing or mutated required inputs are rejected
- authority flags remain false unless explicitly required for the current step
- model calls are absent in model-free steps
- bounded model calls are only allowed in the explicitly approved probe step
- contract-specific exact values, required list items, and banned phrases are enforced

The test shape is stable enough that the next layer should be shared helpers and a reusable lifecycle driver, not new handwritten per-step test logic.

## Shared JSON contract machinery already present

The repo already has a reusable helper in `local_harness/larql_json_contract.py` that supports the important shared checks:

- parsing exactly one JSON object
- rejecting markdown fences
- rejecting prose before or after JSON
- checking required keys
- checking exact values
- checking false booleans
- checking required list items
- checking prompt phrases
- checking banned prompt phrases
- checking banned response phrases
- checking authorization drift
- returning a check dictionary for report generation

That helper is the correct first reuse boundary. It is small, explicit, and already proven by the two JSON-contract rule paths.

## Missing reusable registry pieces

What is still missing is a registry layer that can describe each rule trial family once and then drive the right file names, report types, and step sequence from that manifest.

The registry should probably hold:

- rule family id
- source failure id
- candidate id
- rule id
- current lifecycle step
- allowed next step
- file naming conventions
- artifact directory conventions
- report type / verdict mapping
- approval text requirements for install and bounded model-call steps

Without that layer, each trial still has too much bespoke wiring.

## Missing lifecycle-driver pieces

A reusable lifecycle driver is still missing.

The driver should be able to:

- read the registry entry
- enforce the current step
- resolve the expected inputs and output paths
- invoke the right step-specific builder
- persist the report artifacts
- fail closed on missing or mismatched state

That driver should come after the registry manifest, not before it.

## Missing evidence-packet generation pieces

The workflow still lacks a one-command evidence packet collector that can gather the key artifacts for a completed trial into a compact review bundle.

At minimum, the collector should know how to gather:

- candidate
- candidate review
- runtime-rule packet
- runtime-rule packet review
- install record
- installed runtime rule
- consultation probe
- JSON model-context probe
- independent review
- closeout report

That bundle is what makes the workflow easy to audit, demo, and compare across rule families.

## Missing demo documentation pieces

The repo has closeout reports, but it still lacks one simple demo document showing a single completed LARQL rule trial from start to closeout in one place.

The demo doc should explain:

- what the workflow is
- why each review gate exists
- where the evidence lives
- how the JSON contract narrows the model response
- what counts as a pass
- what remains intentionally held

## Risks if we overbuild too soon

If we jump directly to a generic framework before stabilizing the manifest and evidence bundle shape, we risk:

- over-abstracting the step-specific checks
- losing the simple file-based evidence flow
- burying approval boundaries inside framework code
- making the workflow harder to audit
- coupling the next rule family to assumptions not yet proven

The current three-trial evidence argues for reuse, but not for a heavy general-purpose engine yet.

## Proposed minimal next implementation order

1. rule registry manifest
2. reusable lifecycle status/index generator
3. one-command evidence packet collector
4. demo README showing one completed rule from start to closeout
5. optional generic lifecycle driver after the repeated shapes are stable

## Recommendation for the next single commit

The next single commit should add the rule registry manifest and the smallest index generator needed to surface completed-trial status from it.

That is the best next step because it creates a reusable machinery layer without hiding the existing explicit review gates or the file-based evidence trail.

## Reusable machinery boundary

The right near-term machinery boundary is:

- a registry that describes the rule family and lifecycle state
- a status/index generator that can summarize completed trials
- shared JSON-contract helpers already in `local_harness/larql_json_contract.py`

The next commit should stay there. It should not create another hand-built LARQL rule yet.

