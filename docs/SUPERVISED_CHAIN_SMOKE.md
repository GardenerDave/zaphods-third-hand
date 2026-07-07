# Supervised Chain Smoke

The supervised chain smoke layer provides deterministic, model-free integration evidence for the end-to-end supervised bureaucracy chain.

Pipeline position:

```text
messy input
  -> triage/router packet
  -> orchestration packet
  -> model prompt packet
  -> supervised model attempt record
  -> supervised attempt output validation
  -> supervised review decision record
  -> supervised downstream-use gate record
  -> supervised handoff packet
  -> supervised chain smoke record/report (this layer)
```

## What this layer does

`local_harness/supervised_chain_smoke.py` provides:

- `run_supervised_chain_smoke(...)`
- `build_supervised_chain_smoke_record(...)`
- `validate_supervised_chain_smoke_record(...)`

`run_supervised_chain_smoke(...)` builds a deterministic fixture flow from one messy input string and validates each artifact in sequence:

- triage packet via deterministic router
- orchestration packet via prompt patch library selection
- model-facing prompt packet rendering
- supervised model attempt record using synthetic raw output
- output-contract validation evidence record
- supervised review decision record
- supervised downstream-use gate record
- supervised handoff packet
- final smoke record with chain checks and diagnostics

The smoke record captures chain IDs, all artifacts, check outcomes, diagnostics, authority boundaries, and provenance.

## Synthetic-only output provenance

This layer uses fixture/synthetic raw model output only and marks attempt provenance as:

```text
synthetic_fixture_output
```

No model or endpoint call is performed.

## Safety boundaries

This smoke integration proof does not grant authority to:

- execute commands
- modify files
- apply patches
- promote patches automatically
- train adapters automatically
- capture failures into curriculum by default

Smoke output is evidence, not authority.

## Renderer behavior

`local_harness/render_supervised_chain_smoke_report.py` renders a plain-text report with:

- smoke status
- chain IDs
- input summary
- artifact summary
- checks
- diagnostics
- authority boundaries
- provenance
- explicit review requirement statements

The renderer does not include execution instructions.

## Purpose

The purpose of this layer is integration assurance:

- detect schema drift
- detect lineage breaks
- detect authority leakage

It is not an authority layer and does not introduce autonomous execution behavior.
