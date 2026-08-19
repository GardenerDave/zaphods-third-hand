# Capability Cards and Advisory Routing

ZTH now extracts empirical capability cards from completed supervised
capability-mining trajectories. A card records what a worker/intervention has
actually demonstrated for a deterministic failure signature: task family,
failed structural and semantic checks, valid attempts, rescues, failures,
resource calls, and artifact provenance. Transport-invalid attempts are retained
as exclusions and never become capability failures.

Cards are evidence records, not model claims and not statistical certainty. The
current labels are deliberately conservative: `insufficient` means no valid
comparable opportunity, `observed` means at least one opportunity but too little
evidence, and `supported` means at least three comparable opportunities with at
least a 50% rescue rate.

The offline extractor reads durable Run 1 and Run 2 trajectories and writes
review-only artifacts under `.work/capability_cards/`. It keeps the runs
separate in provenance while normalizing equivalent attempt and validation
semantics. Teacher call counts remain distinct from tasks rescued after a
teacher intervention.

The advisory router matches a deterministic failure signature—not model prose—
against these cards. It may recommend the cheapest historically supported
intervention and show observed alternatives. It resolves evidence in this
order: exact signature, semantic signature, deterministic failure class, then
task family. A broader recommendation always reports its resolution and keeps
the more-specific observed or supported-negative evidence visible. Supported
negative evidence can produce `avoid`; absent supported-positive evidence
produces `abstain`. Every result returns `authority: advisory_only`.

The router does not call models, skip ladder stages, select teachers, promote
patches, train, insert queue work, or accept outputs. The resource order is
baseline 1.7B, deterministic 1.7B retry, local 30B teacher, external teacher,
then review/unresolved.

Run 1 demonstrated teacher-assisted recovery and an 8/10 repaired holdout for
the context-complete deterministic retry. Run 2 reproduced teacher-free
generalization on fresh tasks at 9/20 rescues, with family-dependent results.
Cards turn those observations into transparent routing evidence; they do not
claim weight learning, permanent capability change, optimal routing, or
arbitrary out-of-distribution generalization.

The derived evidence bundle separates task opportunities from worker retry
attempts and teacher calls. This matters for multi-pass teacher cases: a task
is one opportunity, while `local_teacher:1` and `local_teacher:2` remain two
worker attempts and two teacher calls. Run-level audit rows preserve the task
IDs behind those counts.

The proposed next experiment is documented in
[`RUN_3_ADVISORY_ROUTING_DESIGN.md`](reports/model_auditions/RUN_3_ADVISORY_ROUTING_DESIGN.md).
It remains unexecuted and requires freezing the evidence policy before fresh
task selection.
