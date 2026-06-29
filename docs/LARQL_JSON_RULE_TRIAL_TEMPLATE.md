# LARQL JSON Rule Trial Template

This template captures the repeatable supervised lifecycle that was proven across two completed LARQL JSON-contract rule trials:

- absence-of-evidence
- unsupported-certainty / scope-claim

The template is for governed local rule trials. It is not a training workflow, a promotion workflow, or an unattended runtime-governance workflow.

## Standing Boundaries

- no unattended install
- no model call before explicit bounded approval
- no training data by default
- no dataset artifacts by default
- no durable memory by default
- no candidate promotion by default
- no model weight mutation
- no automatic failure-to-curriculum capture
- failure-to-curriculum capture is strictly opt-in only
- use supervised review gates

## Repeatable Lifecycle

### 1. Identify failure pattern

- Purpose: define the concrete failure class and the bounded corrective rule idea.
- Required inputs: reviewed failure evidence, source failure identifier, short description of the unsafe or overbroad behavior.
- Expected outputs: named failure pattern, candidate identifiers, initial rule concept, initial boundary statement.
- Authority boundary: evidence classification only; no runtime install, model call, training, promotion, or durable memory.
- Allowed next step: draft model-free candidate.
- Disallowed actions: model call, runtime-rule install, training-data write, dataset write, durable-memory write, candidate promotion, model mutation, automatic capture.
- Required review gate before proceeding: supervised review of the candidate scaffold after drafting.

### 2. Draft model-free candidate

- Purpose: write the candidate scaffold, identifiers, and first bounded contract or rule summary without calling a model.
- Required inputs: failure pattern, source failure id, candidate id, rule id, bounded rule intent.
- Expected outputs: candidate artifact with scoped rule description and explicit boundary flags.
- Authority boundary: draft only; not installed, not promoted, not captured into training.
- Allowed next step: review candidate.
- Disallowed actions: model call, install, training/data writes, durable memory, promotion, mutation, automatic capture.
- Required review gate before proceeding: candidate review.

### 3. Review candidate

- Purpose: confirm the candidate scaffold is structurally correct, bounded, and safe to advance.
- Required inputs: candidate artifact.
- Expected outputs: candidate review artifact approving or rejecting runtime-rule packet drafting.
- Authority boundary: review only; does not install a rule or authorize a model call.
- Allowed next step: draft runtime-rule packet when approved.
- Disallowed actions: model call, install, training/data writes, durable memory, promotion, mutation, automatic capture.
- Required review gate before proceeding: completed candidate review with explicit approved next step.

### 4. Draft runtime-rule packet

- Purpose: transform the approved candidate into a draft runtime-rule packet that states rule content, contract, and boundaries.
- Required inputs: approved candidate and candidate review.
- Expected outputs: runtime-rule packet with draft rule content, status `draft_not_installed`, and explicit non-authorization flags.
- Authority boundary: packet only; no runtime-rule install or modification.
- Allowed next step: review runtime-rule packet.
- Disallowed actions: install, modify runtime rules, model call, training/data writes, durable memory, promotion, mutation, automatic capture.
- Required review gate before proceeding: runtime-rule packet review.

### 5. Review runtime-rule packet

- Purpose: confirm the packet is structurally valid, still draft-only, and safe to hold at the install boundary.
- Required inputs: runtime-rule packet.
- Expected outputs: runtime-rule packet review approving or rejecting the install-approval boundary.
- Authority boundary: review only; no install or modification.
- Allowed next step: hold for explicit local install approval when approved.
- Disallowed actions: install, modify runtime rules, model call, training/data writes, durable memory, promotion, mutation, automatic capture.
- Required review gate before proceeding: explicit reviewed install boundary.

### 6. Require explicit local install approval

- Purpose: prevent unattended runtime-rule installation.
- Required inputs: reviewed runtime-rule packet plus explicit approval text that states the local-only install intent and prohibited actions.
- Expected outputs: install authorization basis only; this approval text is later captured as provenance.
- Authority boundary: approval is scoped to local runtime-rule artifact install only.
- Allowed next step: install local runtime-rule artifact only.
- Disallowed actions: training/data writes, durable memory, promotion, mutation, automatic capture, broader runtime-rule modification.
- Required review gate before proceeding: prior runtime-rule packet review plus explicit approval text.

### 7. Install local runtime-rule artifact only

- Purpose: write a local runtime-rule artifact under controlled local output paths.
- Required inputs: reviewed runtime-rule packet, reviewed packet review, explicit approval text.
- Expected outputs: installed local runtime-rule artifact and install record.
- Authority boundary: local artifact install only; not a general runtime-governance authorization.
- Allowed next step: draft runtime consultation probe.
- Disallowed actions: model call, training/data writes, durable memory, promotion, mutation, automatic capture, unrelated runtime-rule modification.
- Required review gate before proceeding: explicit install approval already captured.

### 8. Draft runtime consultation probe

- Purpose: convert the installed local rule into prompt/context material suitable for later bounded model injection.
- Required inputs: install record and installed runtime-rule artifact.
- Expected outputs: consultation probe record and consultation context packet.
- Authority boundary: consultation/context drafting only; no model call yet.
- Allowed next step: require explicit bounded model-call approval.
- Disallowed actions: model call, training/data writes, durable memory, promotion, mutation, automatic capture, runtime-rule modification.
- Required review gate before proceeding: install record and installed rule must already be valid and bounded.

### 9. Require explicit bounded model-call approval

- Purpose: separate context preparation from live endpoint use.
- Required inputs: drafted consultation context and explicit approval for one bounded probe call.
- Expected outputs: approval basis for one bounded model-context probe.
- Authority boundary: one bounded probe only; it does not authorize training, promotion, durable memory, or broader automation.
- Allowed next step: run strict JSON model-context probe.
- Disallowed actions: repeated uncontrolled probing, training/data writes, durable memory, promotion, mutation, automatic capture.
- Required review gate before proceeding: explicit bounded approval text.

### 10. Run strict JSON model-context probe

- Purpose: inject consultation context into a narrow JSON-only response contract and collect bounded evidence from one model call.
- Required inputs: consultation probe, consultation context, installed runtime rule, explicit bounded model-call approval, endpoint configuration.
- Expected outputs: prompt artifact, raw response artifact, probe report, deterministic scorer checks.
- Authority boundary: one bounded probe run; evidence only.
- Allowed next step: independently review model-context probe.
- Disallowed actions: training/data writes, durable memory, promotion, mutation, runtime-rule modification, automatic capture.
- Required review gate before proceeding: independent probe review.

### 11. Independently review model-context probe

- Purpose: verify the probe report, prompt, and raw response without trusting the scorer alone.
- Required inputs: probe report, prompt artifact, raw response artifact.
- Expected outputs: independent review artifact approving or rejecting the JSON-contract result.
- Authority boundary: review only; does not rerun the model and does not authorize downstream lifecycle changes.
- Allowed next step: record pass/failure closeout.
- Disallowed actions: model call, training/data writes, durable memory, promotion, mutation, runtime-rule modification, automatic capture.
- Required review gate before proceeding: completed independent review with explicit verdict.

### 12. Record pass/failure closeout

- Purpose: preserve the reviewed milestone or failure mode as durable documentation.
- Required inputs: reviewed probe result and relevant evidence references.
- Expected outputs: closeout report describing what was proved, what was not proved, and what remains held.
- Authority boundary: documentation only; no lifecycle advancement by implication.
- Allowed next step: explicit future experiment proposal or stop.
- Disallowed actions: training, promotion, durable memory, mutation, unattended generalization, automatic capture.
- Required review gate before proceeding: the closeout must accurately reflect the reviewed state.

## Generic JSON Contract Skeleton

```json
{
  "evidence_boundary": "<scoped evidence boundary>",
  "allowed_claim": "<scoped allowed claim>",
  "<global_or_unsafe_claim_authorized>": false,
  "held_claims": [
    "<held broad claim 1>",
    "<held broad claim 2>"
  ],
  "required_next_step": "<review or validation next step>",
  "evidence_to_preserve": [
    "<evidence item 1>",
    "<evidence item 2>"
  ]
}
```

Use the contract to force the model into a narrow, auditable claim shape. The schema is small on purpose. Each field should encode one governed boundary decision.

## When JSON Is Preferred Over Prose

Prefer JSON over prose when:

- a small model drifts in freeform explanation
- the task is epistemic-boundary enforcement
- exact boolean flags matter
- review needs deterministic structure
- the rule may later be audited or compared across model runs

JSON narrows model degrees of freedom. That improves small-model guided capability, but it does not replace supervised review.

## What the Two Completed Trials Prove

- the workflow is reusable across at least two distinct boundary types
- strict JSON contracts can preserve scoped claims
- small-model guided capability improves under shape constraints
- independent review remains necessary

## What the Two Completed Trials Do Not Prove

- not broad freeform compliance
- not autonomous correctness
- not general runtime governance
- not authorization for training or durable memory
- not proof that every LARQL rule will work

## Operator Notes

- Keep report types and verdict names specific to each rule family, even when the mechanics are shared.
- Keep install, model-call, and capture approvals explicit and separate.
- Preserve local evidence and reviewed closeouts even when a probe fails; failure artifacts are part of the supervised rule-trial record.
