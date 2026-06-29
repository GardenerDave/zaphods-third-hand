# What ZTH Proved: From Messy Note to Install-Boundary Hold

## One-sentence summary

ZTH proved that a supervised file workflow can turn one messy note into bounded, reviewable lifecycle artifacts while preserving provenance and authority boundaries all the way to an install-boundary hold.

## Non-technical explanation

A messy note came in. ZTH did not let that note directly change the project. Instead, it turned the note into a sequence of reviewable checkpoints. Each checkpoint kept track of what was known, what was still uncertain, and what was not authorized. The workflow stopped before install, so nothing irreversible happened. That matters because it shows a safer way to use imperfect AI and workflow tools: the system can still produce useful structure without giving the input free rein over the project.

## Intermediate explanation

This proof showed a narrow messy-input bridge. One noisy failure note was reduced into a bounded candidate scaffold, then moved through model-free review gates, then became a held runtime-rule packet draft, and then was reviewed and held at the install boundary. The key property is that the workflow stayed supervised at each step. It preserved provenance, held actions, required next steps, and authority boundaries instead of letting the input expand into broad project control.

No model call, registry mutation, runtime-rule creation, runtime-rule install, probe, training data, dataset artifact, durable memory, candidate promotion, packet promotion, or install authorization occurred. Failure-to-curriculum capture remained opt-in only. The result is guided capability under constraint, not an open-ended automation path.

## Technical explanation

The milestone is the `LARQL intake-to-install-boundary smoke proof`. The artifact chain is:

1. intake smoke candidate
2. intake review
3. candidate draft
4. candidate review
5. packet draft
6. packet review
7. full-chain review
8. milestone closeout

The important technical detail is that the packet-stage `allowed_claim` was separated from the intake-stage `source_allowed_claim`. That separation matters because the intake-stage claim says the noisy note can be reduced into a bounded scaffold, while the packet-stage rule claim is stricter: only listed files are authorized targets. The packet-stage claim is the one that governs the packet review boundary.

The install-boundary hold is a review boundary, not install authorization. It records that the chain can reach the edge of installation without crossing into install, promotion, or registry mutation. The completed registry remains unchanged. The chain preserves provenance across stages and keeps the authority boundaries explicit throughout.

What remains unproven is broader: arbitrary messy input is not solved generally, the candidate is not proven correct in the abstract, the runtime rule is not proven install-worthy, the completed registry is not proven in need of change, and the process is not autonomous. The non-claims section below states the stronger exclusions explicitly, including the absence of any claim of general intelligence.

## What this does not claim

- not general intelligence
- not autonomy
- not arbitrary messy-input mastery
- not permission to install a runtime rule
- not permission to mutate the completed registry
- not automatic training-data capture
- not automatic failure-to-curriculum capture

## Why it matters

Most AI workflows ask the model to be smarter. ZTH instead proves that a supervised workflow can extract useful work from limited intelligence by constraining authority. The important result is not “the model understands everything.” The important result is “the system can preserve boundaries while moving messy input toward reviewable artifacts.”

## Evidence

- `docs/reports/affordance_larql/LARQL_INTAKE_TO_INSTALL_BOUNDARY_CHAIN_REVIEW.md`
- `docs/reports/affordance_larql/LARQL_INTAKE_TO_INSTALL_BOUNDARY_MILESTONE_CLOSEOUT_2026-06-29.md`
- `docs/reports/affordance_larql/LARQL_PACKET_REVIEW_FROM_INTAKE_CANDIDATE_JOIN_SMOKE.md`
- `docs/reports/affordance_larql/LARQL_PACKET_FROM_INTAKE_CANDIDATE_JOIN_SMOKE.md`
- `docs/reports/affordance_larql/LARQL_CANDIDATE_REVIEW_FROM_INTAKE_JOIN_SMOKE.md`
- `docs/reports/affordance_larql/LARQL_CANDIDATE_FROM_INTAKE_JOIN_SMOKE.md`
- `docs/reports/affordance_larql/LARQL_INTAKE_REVIEW_JOIN_SMOKE.md`
- `docs/reports/affordance_larql/LARQL_INTAKE_SMOKE_REVIEW.md`

## Recommended next step

Stop and review before any install-boundary decision. Public narrative and docs consolidation should come before any install-boundary review. Any install-boundary review must be explicit and local.
