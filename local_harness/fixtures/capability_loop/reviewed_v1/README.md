# Reviewed capability-mining fixture pack v1

This pack contains reviewed, bounded tasks adapted from existing ZTH logic
probes, prompt-patch cases, front-door chain cases, and queue-handoff review
fixtures. It is evidence-only: no fixture authorizes execution, queue
insertion, repository mutation, promotion, training, deployment, or acceptance.

Each JSON file records its source fixture/probe and uses the fixture-selected
`zth_output_contract` validator. The worker cannot select or change the
validator. Natural worker performance determines whether the supervised ladder
escalates.
