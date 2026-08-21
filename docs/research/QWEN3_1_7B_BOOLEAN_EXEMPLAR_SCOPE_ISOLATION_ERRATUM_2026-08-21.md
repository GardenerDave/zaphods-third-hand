# Erratum: Neutral Arm Scalar Accounting

This is an additive accounting correction. The completed boolean-exemplar
isolation report, matrix, raw responses, validator artifacts, and scorecards
are unchanged.

## Authoritative raw artifacts

The preserved `response.json` files resolve the apparent transcript
inconsistency:

| Task | Raw response text/bytes | Expected | Strict parser | Contract | Validator |
|---|---|---:|---|---|---|
| `cross-scope-002` Arm N | `false` / `66616c7365` | false | JSON scalar parsed; observed object value = none | invalid | failed; JSON object required |
| `cross-scope-004` Arm N | `true` / `74727565` | true | JSON scalar parsed; observed object value = none | invalid | failed; JSON object required |

The raw scalar literals were not contract-valid parsed booleans and were not
converted into valid supplier outputs.

## Corrected terminology

For the neutral arm:

- raw literal true count: 1;
- raw literal false count: 1;
- raw other count: 14 (the remaining responses were not literal scalar
  booleans);
- contract-valid parsed true count: 0;
- contract-valid parsed false count: 14;
- contract-invalid count: 2.

The existing `observed_true=0` and `observed_false=14` fields count only strict
object-parser values. They are not raw literal counts.

## Interpretation

The core finding remains unchanged:

- Arm T emitted true 16/16;
- Arm F emitted false 16/16;
- T→F flips were 16/16;
- `BOOLEAN_EXEMPLAR_BIAS_CONFIRMED` remains valid.

The worked boolean value dominated output selection under the prior interface.
Prior scope results using that interface are `PROMPT_EXEMPLAR_CONFOUNDED` as
semantic capability measurements, while remaining valid behavioral
observations under their frozen prompts.

The neutral arm is not a clean semantic measurement because it removed the
worked value but had two object-contract failures and predominantly selected
false. The next probe therefore uses a value-neutral natural-language
interface plus an external structure-only JSON Schema constraint that permits
both boolean values without a default, const, example, or enum restriction.

Raw artifact hashes:

- `cross-scope-002/N/response.json`:
  `429ab8fc2ec932bdd839ad496b9f5ffeccfd2aa39833cc34f4868d85f3591433`;
- `cross-scope-004/N/response.json`:
  `50ab4bb7143050fae1a09b4bfa9f43cab6d8fc437126ef198ad44ef90b4556e8`.
