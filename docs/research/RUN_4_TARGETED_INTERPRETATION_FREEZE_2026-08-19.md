# Run 4 targeted economic-routing interpretation freeze

Status: reviewed model-free interpretation. This artifact records the
completed Run 4 result without changing its raw evidence, policy, resource
weights, or production routing authority.

## Established

- The valid Run 4 execution contained 12 comparable paired observations.
- `external_teacher` validated 10/12 tasks.
- `deterministic_patch_retry` validated 1/12 tasks.
- Paired outcomes were: 1 both-solve, 9 external-only, 0 deterministic-only,
  and 2 neither.
- The treatment reduced realized post-baseline elapsed time by 85.426%.
- Quality was not preserved.
- `cheapest_supported_positive` therefore failed its preregistered criterion
  on the targeted fresh triage-routing distribution.

## Derived descriptive quantities

- Incremental realized cost of external over deterministic:
  392,619.315 ms.
- Additional validated solves: 9.
- Descriptive incremental realized cost per additional validated solve:
  392,619.315 / 9 = 43,624.368 ms.

These are sample-specific descriptive quantities, not a universal price of
success or a population probability estimate.

## Provisional lesson

Binary `supported_positive` evidence does not establish economic
interchangeability when empirical capability differs materially.
No universal probability threshold or value-of-success constant is introduced.

## Research lanes

### Capability-price tradeoff

For triage-routing, the relevant comparison is `external_teacher` versus
`deterministic_patch_retry`. The fresh evidence shows a large capability
difference, so an explicit quality/failure-value decision is required before
cost alone can select the cheaper action.

### Pure-efficiency replication

For scope-authority-boundary, Run 4A observed local teacher 4/4 and external
teacher 4/4, while local teacher has the lower frozen expected action cost. The
apparent dominance is based on four paired opportunities per intervention.
`scope-authority-boundary / external_teacher` remains
`dominated_needs_replication`, not retired. This motivates the fresh paired
scope replication prepared separately as Run 4B.

## Provenance

- Run 4 closeout: `docs/reports/model_auditions/SUPERVISED_CAPABILITY_MINING_RUN_4_2026-08-19.md`
- Run 4 closeout SHA256:
  `495aa9ea116abf5fdecb3b0b7ac77990af5c2c91b33b3e864412dca34c8ca3cb`
- Run 4 execution manifest SHA256:
  `65058ed01a90733946b01e9175acf67c5aa036ee23be568d075613298963dbdd`
- Run 4 aggregate SHA256:
  `759db41231d76e94231b4ca0bace96cb17dd435742d3701594cd3b69017d9580`

Authority: review-only research interpretation; no evidence merge and no
production routing mutation.
