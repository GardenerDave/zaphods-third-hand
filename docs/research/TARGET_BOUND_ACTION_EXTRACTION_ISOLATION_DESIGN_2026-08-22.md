# Target-bound action extraction isolation

Status: frozen exploratory design; no inference has been executed.

## Purpose

The preceding audit found four requested-operation extraction failures. In all
four, the supplier selected a secondary/output action-like phrase instead of
the operation directly applied to the requested target. This probe isolates
that relation without asking for authorization, scope, membership, policy, or
boolean decisions.

`TARGET_BOUND_OPERATION` means the operation the request directs the system to
perform on the named requested target. Reporting, recording, documenting,
logging, submitting, or announcing a result is secondary unless that action is
itself directly applied to the named target.

## Frozen task design

There are eight tasks in four matched pairs. Each pair preserves the same
target and two action verbs while reversing which verb is directly applied to
the target. Each verb appears once in each role within its pair. Sentence
positions are mixed: expected answers occur in both first and second action
positions, and no first/last-position or lexical shortcut perfectly predicts
the answer.

The exact tasks and model-free expected operands are frozen in
`TARGET_BOUND_ACTION_EXTRACTION_ISOLATION_TASKS_2026-08-22.json`.

## Output contract

The supplier returns exactly one string field, `target_bound_operation`, under
a structure-only JSON schema. There is no enum, example, boolean, authority
term, scope term, or explanation request.

## Analysis

Report exact extraction, pairwise role-reversal success, secondary-action
selections, answer position, and first/second action position. Classify each
pair as BOTH_RELATIONS_CORRECT, ONE_DIRECTION_CORRECT,
BOTH_SELECT_SAME_VERB, BOTH_SELECT_SECONDARY_ACTION, or OTHER.

The supplier owns semantic relation extraction. Deterministic code remains
responsible for canonicalization, equality, membership, scope composition, and
policy enforcement in later architecture work.
