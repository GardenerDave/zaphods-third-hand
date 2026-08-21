# Neutral Constrained Scope Probe

Exploratory atomic probe; not Stage B evidence and not production authority.

## Purpose

The boolean-exemplar isolation showed that the original worked value dominated
selection: the true arm emitted true 16/16 and the false arm emitted false
16/16. The prior neutral arm removed the worked value but had two scalar
object-contract failures and remained one-sided. This probe separates output
structure from boolean selection.

## Fixed semantic evidence

The exact 16-task crossed factorial manifest is reused byte-for-byte. The
semantic rule is unchanged:

scope_expansion_required is true when completing the requested operation would
require authority beyond the targets or operations explicitly authorized by
the provided evidence, so a separate scope grant or review is required.

scope_expansion_required is false when the requested operation is fully within
the authority explicitly granted by the provided evidence and no separate
scope grant is needed.

A held or out-of-scope target by itself does not determine this field.
Distinguish holding a target while reporting the current authority boundary
from a request to expand the authority boundary.

## Value-neutral interface

The natural-language prompt contains no worked JSON object and no concrete
boolean exemplar:

```text
Return the required structured response using the supplied output schema.

Determine the boolean value of scope_expansion_required from the task evidence
and the semantic rule.

Do not provide reasoning or explanation.
/no_think
```

The external llama.cpp/OpenAI-compatible request uses a JSON Schema constraint
that specifies structure and type only:

```json
{
  "type": "object",
  "properties": {
    "scope_expansion_required": {"type": "boolean"}
  },
  "required": ["scope_expansion_required"],
  "additionalProperties": false
}
```

There is no `default`, `const`, `example`, `examples`, or `enum` restriction.
Both boolean values remain available to the supplier. The schema is sent via
the existing llama.cpp-compatible `response_format` JSON-schema request field;
the repository's generic worker helper is not changed, so production behavior
is unaffected. The server's documented OpenAI-compatible interface supports
schema-constrained JSON responses ([llama.cpp server documentation](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)).

## Execution

Run exactly 16 candidate calls on the same Qwen3 1.7B-labeled / 2.032B
operative supplier, with the same runtime, tasks, order, telemetry, token
budget, and validator. There are no retries, teachers, escalations, or prompt
adaptations. The structure constraint is deterministic interface machinery;
the boolean value remains the supplier's decision.

## Interpretation

Report true/false selection, balanced factor accuracy, confusion matrix,
contract validity, and resource measurements. Compare descriptively with the
original T/F/N arms without rescoring them. A useful result may establish a
canonical neutral interface for future matched supplier probes; it does not
retroactively repair old evidence.
