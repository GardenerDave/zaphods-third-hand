# Fact extraction plus deterministic scope policy

This exploratory probe reuses the frozen crossed-scope fixtures byte-for-byte
and tests a responsibility split:

`natural-language evidence -> supplier fact extraction -> deterministic normalization/comparison -> deterministic scope policy`

The supplier returns only four factual operands for each task:

- `authorized_target`
- `requested_target`
- `authorized_operation`
- `requested_operation`

It is not asked to decide authorization, scope expansion, review, or policy.
The external schema requires exactly those four strings and no boolean decision
field. Raw strings are preserved; operation morphology is normalized by the
frozen model-free map `reading/read -> read`, `inspecting/inspect -> inspect`,
`modifying/modify -> modify`, and `updating/update -> update`.

For these fixtures, the first authority sentence explicitly names one target
and one operation, and the request names one target and one operation. The
frozen deterministic policy is:

`target_match = normalized(authorized_target) == normalized(requested_target)`

`operation_match = normalized(authorized_operation) == normalized(requested_operation)`

`scope_expansion_required = NOT(target_match AND operation_match)`

The policy reproduces all 16 frozen expected scope labels model-free. The
fixture semantics are target-bound for final scope, while the extraction
fields remain factual operands. This is not a new semantic task family and is
not production routing evidence.

The supplier is Qwen3 1.7B-labeled / 2,031,739,904 operative parameters,
using the already frozen runtime and Level-2 GTX-1650 telemetry. Exactly one
structured extraction call is authorized per task: 16 calls total, with no
teacher, retries, escalations, or adaptation.
