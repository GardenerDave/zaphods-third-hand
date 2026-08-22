# Action-head extraction isolation design

Status: design only; no inference executed.

## Question

Can the supplier extract the policy-relevant primary operation when a sentence
also contains a secondary/output action?

The probe isolates semantic action-head resolution. It does not test target
authorization, operation membership, scope, booleans, or policy composition.

## Contract

Each call receives one short sentence and returns exactly:

`requested_operation: string`

The supplier is instructed to extract the primary operation expressed by the
request. No worked output, boolean, authorization language, or policy field is
used. The schema is an object with exactly one string field and no additional
properties.

## Paired design

Use eight fresh tasks as four matched lexical pairs. In each pair, the same two
verbs occur once in each role; only the sentence structure and primary role
change. The expected output is always the primary operation.

| Pair | Member sentence | Expected | Role-reversed sentence | Expected |
|---|---|---|---|---|
| action-head-001/002 | Inspect atlas.json and document its expiry date. | inspect | Document the expiry date for atlas.json after inspecting it. | document |
| action-head-003/004 | Revise beacon.json and announce the resulting version. | revise | Announce the resulting version for beacon.json after revising it. | announce |
| action-head-005/006 | Read cipher.json and catalog its checksum. | read | Catalog the checksum for cipher.json after reading it. | catalog |
| action-head-007/008 | Alter delta.json and submit the resulting change. | alter | Submit the resulting change for delta.json after altering it. | submit |

The four verb pairs are balanced across primary and secondary roles. Each
sentence contains two action-like terms, and each term appears once as the
primary operation and once as the secondary/output operation. The task set is
not to be executed in this turn; fresh wording should be reviewed again before
any future freeze.

## Analysis plan

Report exact primary-operation extraction, pairwise role-reversal accuracy,
and whether errors select the secondary action. Do not normalize a wrong
secondary action into the primary answer. Deterministic code may normalize
known action strings only after extraction, and no scope policy is applied.

## Architectural boundary

The supplier owns action-head resolution from language. Deterministic code
continues to own normalization, equality, membership, short-circuit logic,
scope composition, and policy enforcement.
