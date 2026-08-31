# 1p7b_structured_output_qualification_20260830

## Verdict

Structured-output enforcement verdict: `STRUCTURED_OUTPUT_ENFORCEMENT_PASS`

## Requalification

- Model: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`
- Endpoint: `http://192.168.1.16:8081/v1`
- Observed context: `32768`

## Frozen prompt

`Return exactly this text and nothing else: UNCONSTRAINED_SENTINEL`

## Frozen schema

```json
{
  "additionalProperties": false,
  "properties": {
    "forced_schema_value": {
      "type": "string"
    }
  },
  "required": [
    "forced_schema_value"
  ],
  "type": "object"
}
```

Schema SHA-256: `914c7a718634ee4407942dca42a22805edce5399a3d960fe0fc4eaef0f212705`

## Control A: unconstrained

Raw response:

```text
UNCONSTRAINED_SENTINEL
```

- Request-body SHA-256: `bf68c5d2cb7d924d3622eb211c49bfdb4b9af32a4089cc6697bd86d15157fd11`
- Request-body length: `192`
- Response SHA-256: `85dee76b361fa2e4f5817d0f947a3e318bd6c209e735c1f96c0e24e17a80309b`

The unconstrained control produced the plain sentinel text and did not attempt the structured schema.

## Control B: constrained

Raw response:

```json
{
  "forced_schema_value": "UNCONSTRAINED_SENTINEL"
}
```

- Request-body SHA-256: `4d383af71b5bbaa7d29142faeb2b73fdce1fa4f6aa5cbd6d48b654c4051a700f`
- Request-body length: `459`
- Response SHA-256: `1aca51ef12da875499156982e31b7c89194bd88348f23fc0d7b05269f8abd7ba`

The constrained control returned syntactically valid JSON matching the frozen schema exactly.

## Qualification

- schema artifact ↔ request schema equality: PASS
- request-body identity recorded: PASS
- unconstrained control: PASS
- constrained control: PASS
- schema conformance: PASS
- additional properties: none

## Interpretation

The deployed runtime demonstrated response-schema enforcement for this adversarial control. The structured request changed generation behavior from plain text to schema-conforming JSON while preserving the same model-visible prompt.

## Preservation

- Evidence archive: `docs/reports/evidence/1p7b_structured_output_qualification_20260830/`
- Archive manifest: `archive_manifest.json`
- Archive verification: `PASS` (`8` entries byte-matched against the source `.work` evidence)
