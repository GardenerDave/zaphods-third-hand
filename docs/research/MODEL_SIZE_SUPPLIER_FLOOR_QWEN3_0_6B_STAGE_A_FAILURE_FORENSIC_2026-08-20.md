# Qwen3 0.6B Stage A Failure Forensic Analysis

## Scope and provenance

This is a model-free forensic analysis of the completed exploratory Stage A
screen. It does not replace the frozen result, modify any response or
validator artifact, or create confirmatory evidence.

- Stage A commit: `5a4caf7c3630471784599ec84dbd8bf089f09703`
- Stage A report:
  `docs/reports/model_auditions/SUPERVISED_CAPABILITY_MINING_QWEN3_0_6B_STAGE_A_2026-08-20.md`
- Stage A report SHA256:
  `51543cc07aa89922e86c554b669b8da689d151ace7f181f5f39cac3eb6eda14b`
- Terminal aggregate SHA256:
  `2e4c88d5e6fc1d6e12cc028791dff6557cc4733ab2c8f808c67d803f092141d0`
- Run directory:
  `.work/model_size_supplier_floor/qwen3_0_6b_stage_a/run_20260820T171851Z/`
- Frozen task IDs, in order: `run7-scope-001` through `run7-scope-012`
- Raw artifacts unchanged: `true`
- Terminal validator artifacts unchanged: `true`
- Model calls during this analysis: `0`

The frozen Stage A disposition remains:

`NOT_PROMISING_AT_THIS_SIZE`

That means not promising under the exact frozen supplier interface tested. It
does not, by itself, establish universal inability on the bounded capability.

## Frozen result versus forensic result

The original Stage A result remains `RAW_PARSE_VALID=0/12` and
`validated_passes=0/12`. Every response was transport-valid, but the frozen
validator received the original fenced text and reported `parse_json=failed`.

For this forensic analysis only, the response text was copied in memory and a
single generic wrapper removal was applied: remove one outer markdown code
fence. No fields, values, types, targets, or authority decisions were added or
changed. The existing deterministic validator was then run diagnostically on
the recovered JSON text.

## What the candidate emitted

All 12 responses had the same outer format: a single JSON object inside a
markdown code fence. There was no prose before or after the object, no
thinking/reasoning tag, no Python-style single-quoted dictionary, no JSON
array, no multiple-object response, no truncation, and no natural-language-
only response.

| Observable raw format | Count |
|---|---:|
| Valid bare JSON object before normalization | 0/12 |
| JSON object inside one markdown code fence | 12/12 |
| Prose before or after JSON | 0/12 |
| Thinking/reasoning tags | 0/12 |
| Python-style dict | 0/12 |
| Malformed JSON after fence removal | 0/12 |
| JSON array | 0/12 |
| Multiple JSON objects | 0/12 |
| Truncated JSON | 0/12 |
| Natural-language answer without JSON | 0/12 |

The recoverable objects were not uniform in field types:

| Task IDs | Recovered field types (`allowed`, `held`, `scope`, `review`) | Structural result | Reference-fact result | Boundary |
|---|---|---:|---:|---|
| 001, 008, 012 | list, list, bool, string | usable: 3/3 | failed: 0/3 | `SEMANTIC_FAILURE` |
| 002, 004, 005, 006, 007, 009, 010, 011 | includes string-valued fields where lists/bool were required | failed: 0/8 | failed: 0/8 | `FORMAT_PLUS_CONTRACT_FAILURE` |
| 003 | list, list, string, string; allowed/held overlap | failed: 0/1 | failed: 0/1 | `FORMAT_PLUS_CONTRACT_FAILURE` |

The per-task diagnostic classification was:

| Task | Raw wrapper | Mechanically recoverable | Contract-usable | Reference-valid | Classification |
|---|---|---:|---:|---:|---|
| run7-scope-001 | fenced JSON object | yes | yes | no | semantic failure |
| run7-scope-002 | fenced JSON object | yes | no | no | format plus contract failure |
| run7-scope-003 | fenced JSON object | yes | no | no | format plus contract failure |
| run7-scope-004 | fenced JSON object | yes | no | no | format plus contract failure |
| run7-scope-005 | fenced JSON object | yes | no | no | format plus contract failure |
| run7-scope-006 | fenced JSON object | yes | no | no | format plus contract failure |
| run7-scope-007 | fenced JSON object | yes | no | no | format plus contract failure |
| run7-scope-008 | fenced JSON object | yes | yes | no | semantic failure |
| run7-scope-009 | fenced JSON object | yes | no | no | format plus contract failure |
| run7-scope-010 | fenced JSON object | yes | no | no | format plus contract failure |
| run7-scope-011 | fenced JSON object | yes | no | no | format plus contract failure |
| run7-scope-012 | fenced JSON object | yes | yes | no | semantic failure |

For `contract-usable`, a `not_applicable` authority check was treated as
neutral because the Stage A diagnostic call did not provide a separate
authorized-target list. A failed structural check was not neutral. This is a
forensic classification; it does not rewrite the Stage A aggregate's frozen
derived fields.

## Prompt-contract observation

The frozen driver constructs the final instruction as:

```text
Return only one JSON object with exactly these fields and no markdown: ["allowed_targets","held_targets","scope_expansion_required","review_status"]. Use the required JSON types. Do not include reasoning or commentary. /no_think
```

The fixture contract's `required_fields` value is a list of field names, not an
explicit JSON object schema or a worked object example. Thus the prompt says
“JSON object” while displaying a JSON array containing the field names. It
also says to use the required types without showing those types in the
example.

This is a concrete interface ambiguity. It does not prove that the ambiguity
caused the code fences or the later type/semantic failures, but it is relevant
to interpreting the screen as an interface-and-capability test rather than a
clean test of reasoning alone.

## Mechanically recovered validator results

| Diagnostic measure | Result |
|---|---:|
| Frozen raw parse-valid | 0/12 |
| Mechanically recoverable JSON objects | 12/12 |
| Recovered contract-usable objects | 3/12 |
| Recovered reference-fact-valid objects | 0/12 |
| Recovered fully validated objects | 0/12 |

The three structurally usable objects still failed semantic reference checks:

- `run7-scope-001`: target values, expansion flag, and review status did not
  match the frozen reference facts.
- `run7-scope-008`: target sets were structurally usable, but the expansion
  flag and review status did not match the frozen reference facts.
- `run7-scope-012`: target sets and expansion flag were usable, but review
  status did not match the frozen reference fact.

The remaining nine had at least one structural contract issue in addition to
reference-fact failures, primarily string-valued fields where lists or a
boolean were required; task 003 also put a target in both allowed and held
sets.

## Failure boundary

The evidence supports:

`MIXED_FORMAT_AND_SEMANTIC_FAILURE`

More precisely:

- The frozen raw interface failed for all 12 because the validator does not
  accept the emitted markdown fences.
- A generic fence stripper exposed an existing JSON object for all 12, so the
  raw parse failure does not by itself demonstrate absence of reasoning.
- Nine recovered objects still violated structural type/separation rules.
- Three recovered objects were structurally usable but failed deterministic
  scope-authority reference facts.
- No recovered object fully validated.

Therefore the stronger statement “Qwen3-0.6B lacks non-trivial
scope-authority capability” is **not established cleanly** by this screen.
The supported statement is narrower: Qwen3-0.6B was not viable under the
frozen Stage A interface and, after generic wrapper removal, most outputs
still had contract problems while the structurally usable subset had semantic
failures.

## Recommended next research action

Run one separately authorized, exploratory interface-disambiguation screen on
the same installed candidate, using a newly frozen prompt that shows an
explicit JSON object schema or example while keeping the validator,
scope-authority task family, and no-retry/no-escalation rule fixed. This is the
smallest action that separates the observed serialization/interface failure
from remaining structured-contract and semantic capability limits.

Do not alter this Stage A run, retrofit its results, or treat that future
screen as confirmatory evidence without a separately frozen design.
