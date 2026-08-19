# Reviewed capability-mining fixture pack v3

Run 3 uses 24 independently authored, bounded tasks selected after the Run 3
advisory policy freeze. The prompts are grounded in repository documentation
and workflow contracts not used as reviewed_v1/reviewed_v2 task prompts. They
do not copy historical worker or teacher outputs and do not grant execution,
queue insertion, repository mutation, promotion, training, deployment, or
acceptance authority.

Each fixture selects the deterministic `zth_output_contract` validator and
declares its own output contract and bounded reference facts. `provenance`
records the source document and novelty classification. The pack is
review-only and must be preregistered before any model call.
