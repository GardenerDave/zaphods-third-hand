# V7 Curriculum Candidate Review

Status: draft

## Basis

This review is based on the v6 failure-curriculum helper dogfood pass.

Recorded basis:

- v6 eval rows: 48
- non-exact rows: 25
- extra-field rows: 5
- persistent extra-field rows: 7, 29, 33, 35, 36
- adapter JSON validity: 48/48
- adapter top-level key match: 43/48
- adapter exact match: 23/48

## Candidate Failure Buckets

### 1. Placeholder schema substitution

Rows 7 and 29 returned placeholder-style keys instead of the requested scalar
schema.

Target pattern: {"count": 3}

Observed pattern: {"key1": "value1", "key2": "value2", "key3": "value3"}

Candidate interpretation:

The adapter sometimes substitutes a generic example-object schema when the
requested output is a small scalar object.

### 2. Prefixed-key substitution

Row 33 changed the requested key name.

Target pattern: {"blocked": true}

Observed pattern: {"key_blocked": true}

Candidate interpretation:

The adapter preserved the boolean value but introduced an unsupported key prefix.

### 3. Generic-key substitution

Row 35 replaced a required semantic key with a generic key.

Target pattern: {"accepted": false}

Observed pattern: {"key": false}

Candidate interpretation:

The adapter preserved the boolean value but lost the required key name.

### 4. Source-content leakage after correct answer

Row 36 included the correct scalar result but leaked source-like code content in
an extra field.

Target pattern: {"files_changed": 2}

Observed pattern: {"files_changed": 2, "file1": "..."}

Candidate interpretation:

The adapter can satisfy the requested scalar contract and still continue with
unsupported source-content expansion.

### 5. Stop-condition over-generation

Some stop-condition outputs added unsupported extra stop rules.

Candidate interpretation:

The adapter learned the stop-condition genre but sometimes treats the field as
an invitation to enumerate plausible risks beyond the target.

### 6. Stop-condition phrasing drift

Some stop-condition outputs preserved rough meaning but changed wording,
punctuation, or grouping.

Candidate interpretation:

The adapter improved structured-output compliance but did not always preserve
exact target phrasing where exact target phrasing is part of the contract.

### 7. Evidence-limit type drift

At least one evidence-limit output preserved the answer but changed the
evidence-limit field type.

Candidate interpretation:

The adapter may compress explanatory string fields into numeric or shorthand
values when the prompt emphasizes brevity or JSON-only output.

### 8. Semantic paraphrase drift

Some text-field outputs remained valid JSON with matching keys but did not
preserve the required semantic content exactly.

Candidate interpretation:

The adapter is better at format obedience than semantic exactness.

## Recommended V7 Scope

V7 should be narrow.

Primary targets:

- exact-key/no-extra enforcement for scalar object outputs;
- no placeholder keys when a target schema is explicit;
- no prefixed keys;
- no generic replacement keys;
- no source-content leakage after satisfying a requested scalar answer;
- stop-condition array length discipline;
- stop-condition exact wording discipline when exact wording is required;
- preservation of expected field types.

Out of scope:

- broad reasoning improvement;
- architectural judgment;
- autonomous repair;
- adapter deployment;
- general project understanding;
- final reviewer authority.

## Candidate Curriculum Shape

Recommended v7 examples should be targeted rather than broad.

Useful example types:

1. Scalar object exactness

Prompt shape:

Return exactly this schema. Do not add keys.

Target shape:

{"count": 3}

2. Boolean key preservation

Prompt shape:

Return the required boolean field. Do not rename the key.

Target shapes:

{"blocked": true}

{"accepted": false}

3. No source expansion after scalar answer

Prompt shape:

Return only the number of files changed. Do not include file contents.

Target shape:

{"files_changed": 2}

4. Stop-condition array exactness

Prompt shape:

Return exactly two stop conditions. Do not add, combine, or rephrase them.

Target shape:

{"stop_conditions": ["tests fail", "git status is dirty"]}

5. Field type preservation

Prompt shape:

Return the evidence limit as a string field.

Target shape:

{"answer": "no", "evidence_limit": "evidence does not support the claim"}

## Stop / Continue Decision

Recommendation:

Build v7 only if the curriculum remains narrow and weighted toward the persistent
miss classes.

Do not simply add more examples broadly.

The v6 result already shows strong format improvement. V7 should test whether a
small targeted curriculum can reduce persistent schema attractors without
damaging the v6 gains.

## Acceptance Criteria For V7

A v7 run should be considered useful only if it preserves or improves:

- adapter JSON validity: 48/48;
- adapter top-level key match: at least 43/48;
- adapter exact match: better than 23/48;

and reduces:

- adapter extra-field rows below 5/48;
- placeholder schema substitutions;
- prefixed-key substitutions;
- generic-key substitutions;
- source-content leakage after correct scalar answers.

## Boundary

This review is supervised curriculum-planning evidence. It does not authorize
training, adapter promotion, deployment, or unsupervised model use.

Any v7 training run should remain manual, reviewed, and separately reported.
