# Structured Worker-A V2

Experiment: `1p7b_worker_a_structured_v2_20260830`

Current HEAD for the experiment boundary: `4608687cd409b7ac37134b1f738da03ab439d42b`

## Verdicts

- canonical prompt-projection integrity: PASS
- acquisition contract identity: PASS
- captured-model provenance: PASS
- structured request integrity: PASS
- schema conformance: PASS
- semantic correction retention: PASS
- held-target preservation: PASS
- complete Worker-A contract: PASS

## Summary

The structured 1.7B acquisition used the canonical prepared prompt with deterministic projection and explicit inclusion of the two evidence-derived semantic corrections:

- `allowed_held_mapping_v1`
- `required_fields_boolean_v1`

The canonical baseline prompt material remained visible. The syntax-only corrections were not model-visible in the structured V2 projection. The persisted acquisition contract matched the projected prompt-visible contract, and the captured-model ingest preserved truthful worker identity plus acquisition provenance.

The raw model response satisfied the frozen semantic contract:

- `allowed_targets == ["docs/reports/"]`
- `held_targets == ["production automation", "automatic curriculum capture", "automatic promotion", "implementation_packet"]`
- `required_fields_present == true`

The unchanged validator passed all checks, including held-target preservation and target authority.

## Comparison with Structured V1

Structured V1 was a prompt-projection design deviation: it used a hand-authored prompt projection and a manual ingest provenance class, so the intended canonical projection was not cleanly tested. Structured V2 removes that ambiguity by keeping prompt projection machine-generated and by ingesting the exact captured model result with `--model-call-metadata-file`.

## Next step

Proceed to a fresh validated structured `1.7B -> ZTH -> 30B` continuous production handoff using this exact frozen Worker-A configuration.
